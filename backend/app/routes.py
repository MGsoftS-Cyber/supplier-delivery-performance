"""Owner-scoped delivery analytics and export workflows."""

import csv
import io
import json
import hashlib
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from .database import get_db
from .security import current_user
from .models import Store, Dataset, Analysis
from .schemas import StoreInput, DatasetInput, CsvInput, PerformanceInput, ComparisonInput
from .services import mutation
from .imports import preview_deliveries, normalize
from .engine import evaluate, ENGINE_VERSION

router = APIRouter(prefix="/api/v1")
Key = Header(min_length=1, max_length=100)


def owned_store(db, identifier, user):
    obj = db.scalar(select(Store).where(Store.id == identifier, Store.user_id == user.id))
    if not obj:
        raise HTTPException(404, "Store not found in your account.")
    return obj


def owned_analysis(db, identifier, user):
    obj = db.scalar(select(Analysis).join(Store).where(Analysis.id == identifier, Store.user_id == user.id))
    if not obj:
        raise HTTPException(404, "Analysis not found in your account.")
    return obj


def store_view(x):
    return dict(id=x.id, name=x.name, unit=x.unit)


def dataset_view(x):
    return dict(
        id=x.id,
        store_id=x.store_id,
        source=x.source,
        coverage_end=x.coverage_end,
        quality=x.quality,
        deliveries=x.deliveries,
        created_at=x.created_at,
    )


def analysis_view(x):
    return dict(
        id=x.id,
        store_id=x.store_id,
        dataset_id=x.dataset_id,
        inputs=x.inputs,
        results=x.results,
        engine_version=x.engine_version,
        created_at=x.created_at,
    )


@router.get("/stores")
def stores(user=Depends(current_user), db=Depends(get_db)):
    return [store_view(x) for x in db.scalars(select(Store).where(Store.user_id == user.id))]


@router.post("/stores", status_code=201)
def create_store(data: StoreInput, idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)):
    def work():
        obj = Store(user_id=user.id, **data.model_dump())
        db.add(obj)
        db.flush()
        return store_view(obj)

    return mutation(db, user, "store", idempotency_key, data.model_dump(mode="json"), work)


@router.post("/imports/deliveries/preview")
def preview(data: CsvInput, user=Depends(current_user)):
    return preview_deliveries(data.csv_text)


@router.get("/stores/{identifier}/datasets")
def datasets(identifier: str, user=Depends(current_user), db=Depends(get_db)):
    owned_store(db, identifier, user)
    return [
        dataset_view(x)
        for x in db.scalars(select(Dataset).where(Dataset.store_id == identifier).order_by(Dataset.created_at.desc()))
    ]


@router.post("/stores/{identifier}/datasets", status_code=201)
def create_dataset(
    identifier: str, data: DatasetInput, idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)
):
    owned_store(db, identifier, user)
    try:
        rows, quality = normalize(data.deliveries, data.coverage_end)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    body = data.model_dump(mode="json")
    fingerprint = hashlib.sha256(
        json.dumps(
            dict(deliveries=rows, source=data.source, coverage_end=str(data.coverage_end)), sort_keys=True
        ).encode()
    ).hexdigest()

    def work():
        existing = db.scalar(select(Dataset).where(Dataset.store_id == identifier, Dataset.fingerprint == fingerprint))
        if existing:
            return dataset_view(existing)
        obj = Dataset(
            store_id=identifier,
            source=data.source,
            coverage_end=str(data.coverage_end),
            deliveries=rows,
            quality=quality,
            fingerprint=fingerprint,
        )
        db.add(obj)
        db.flush()
        return dataset_view(obj)

    return mutation(db, user, "dataset:" + identifier, idempotency_key, body, work)


@router.post("/stores/{identifier}/analyses", status_code=201)
def analyze(
    identifier: str, data: PerformanceInput, idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)
):
    store = owned_store(db, identifier, user)
    dataset = db.scalar(select(Dataset).where(Dataset.id == data.dataset_id, Dataset.store_id == identifier))
    if not dataset:
        raise HTTPException(404, "Dataset not found in this store.")
    inputs = dict(
        **data.model_dump(mode="json"),
        store=store_view(store),
        source=dataset.source,
        coverage_end=dataset.coverage_end,
        deliveries=dataset.deliveries,
        quality=dataset.quality,
    )
    try:
        results = evaluate(inputs)
        json.dumps(results, allow_nan=False)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

    def work():
        obj = Analysis(
            store_id=identifier, dataset_id=dataset.id, inputs=inputs, results=results, engine_version=ENGINE_VERSION
        )
        db.add(obj)
        db.flush()
        return analysis_view(obj)

    return mutation(db, user, "analysis:" + identifier, idempotency_key, data.model_dump(mode="json"), work)


@router.get("/analyses")
def analyses(user=Depends(current_user), db=Depends(get_db)):
    return [
        analysis_view(x)
        for x in db.scalars(
            select(Analysis).join(Store).where(Store.user_id == user.id).order_by(Analysis.created_at.desc()).limit(100)
        )
    ]


@router.post("/comparisons")
def compare(data: ComparisonInput, user=Depends(current_user), db=Depends(get_db)):
    items = [owned_analysis(db, i, user) for i in data.analysis_ids]
    if len({(x.store_id, x.dataset_id, x.inputs["coverage_end"]) for x in items}) != 1:
        raise HTTPException(422, "Compare the same workspace and dataset.")
    return dict(
        analyses=[analysis_view(x) for x in items],
        message="Compare grace and minimum sample rules on frozen delivery data.",
    )


@router.get("/analyses/{identifier}/report")
def report(identifier: str, format: str = "json", user=Depends(current_user), db=Depends(get_db)):
    obj = owned_analysis(db, identifier, user)
    if format == "json":
        text, media = json.dumps(analysis_view(obj), indent=2), "application/json"
    elif format in {"suppliers", "deliveries"}:
        output = io.StringIO()
        writer = csv.writer(output)
        keys = (
            [
                "supplier_id",
                "supplier_name",
                "due_records",
                "on_time_rate",
                "otif_rate",
                "fulfillment_rate",
                "usable_fill_rate",
                "defect_rate",
                "return_rate",
                "score",
                "rank",
            ]
            if format == "suppliers"
            else [
                "supplier_id",
                "delivery_id",
                "promised_date",
                "actual_date",
                "deadline",
                "due",
                "status",
                "ordered_qty",
                "received_qty",
                "defect_qty",
                "returned_qty",
                "usable_qty",
                "late_days",
                "overdue_days",
            ]
        )
        writer.writerow(keys)
        for row in obj.results[format]:
            # Free-form supplier names may contain spreadsheet formula prefixes.
            values = []
            for k in keys:
                value = row[k]
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    value = "'" + value
                values.append(value)
            writer.writerow(values)
        text, media = output.getvalue(), "text/csv"
    else:
        raise HTTPException(422, "Use json, suppliers or deliveries format.")
    ext = "json" if format == "json" else "csv"
    return Response(
        text,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="supplier-{format}-{obj.id}.{ext}"'},
    )


@router.post("/demo", status_code=201)
def demo(idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)):
    def work():
        if db.scalar(select(Store).where(Store.user_id == user.id)):
            raise HTTPException(409, "Demo requires an empty workspace catalog.")
        store = Store(user_id=user.id, name="Northstar Purchasing", unit="unit")
        db.add(store)
        db.flush()
        end = date.today()
        raw = []
        for sid, name, offset in [
            ("SUP-A", "Atlas Components", 0),
            ("SUP-B", "BluePeak Supply", 2),
            ("SUP-C", "Cedar Trading", 5),
            ("SUP-D", "Delta Logistics", 1),
        ]:
            for i in range(24):
                promise = end - timedelta(days=175 - i * 8)
                actual = promise + timedelta(days=offset + (i % 4) - 2)
                received = 100 if sid in {"SUP-A", "SUP-D"} else 80 if i % 3 == 0 else 100
                if actual > end or i % 11 == 0:
                    actual = None
                    received = 0
                raw.append(
                    dict(
                        supplier_id=sid,
                        supplier_name=name,
                        delivery_id=f"{sid}-{i:03d}",
                        ordered_date=str(promise - timedelta(days=14)),
                        promised_date=str(promise),
                        actual_date=str(actual) if actual else None,
                        ordered_qty=100,
                        received_qty=received,
                        defect_qty=0 if not received else (i % 3) * (offset + 1),
                        returned_qty=0 if not received else i % 2,
                    )
                )
        data = DatasetInput(source="Synthetic demonstration", coverage_end=end, deliveries=raw)
        rows, quality = normalize(data.deliveries, end)
        dataset = Dataset(
            store_id=store.id,
            source=data.source,
            coverage_end=str(end),
            deliveries=rows,
            quality=quality,
            fingerprint=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
        )
        db.add(dataset)
        db.flush()
        return dict(
            store_id=store.id,
            dataset_id=dataset.id,
            message="Synthetic supplier deliveries created. No external ERP connected.",
        )

    return mutation(db, user, "demo", idempotency_key, {}, work)
