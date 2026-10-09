"""Strict delivery snapshot imports: one record per single receipt commitment."""

import csv
import io
import re
from datetime import date
from .schemas import DeliveryInput

HEADER = [
    "supplier_id",
    "supplier_name",
    "delivery_id",
    "ordered_date",
    "promised_date",
    "actual_date",
    "ordered_qty",
    "received_qty",
    "defect_qty",
    "returned_qty",
]


def preview_deliveries(text):
    rows, errors, seen = [], [], set()
    try:
        reader = csv.DictReader(io.StringIO(text), strict=True)
        if reader.fieldnames != HEADER:
            return dict(valid=False, rows=[], errors=[dict(row=1, message="Use header: " + ",".join(HEADER))])
        for number, raw in enumerate(reader, 2):
            if number > 10001:
                errors.append(dict(row=number, message="Maximum 10000 deliveries."))
                break
            try:
                for key in ["ordered_qty", "received_qty", "defect_qty", "returned_qty"]:
                    if not re.fullmatch(r"\d{1,10}", raw.get(key, "")):
                        raise ValueError("Quantities must be whole nonnegative units.")
                    raw[key] = int(raw[key])
                raw["actual_date"] = raw["actual_date"] or None
                item = DeliveryInput(**raw).model_dump(mode="json")
                if item["delivery_id"] in seen:
                    raise ValueError("Duplicate delivery ID.")
                seen.add(item["delivery_id"])
                rows.append(item)
            except (ValueError, TypeError):
                errors.append(
                    dict(row=number, message="Invalid/duplicate delivery: check dates, IDs and quantity consistency.")
                )
    except csv.Error:
        errors.append(dict(row=1, message="Malformed CSV quoting."))
    if not rows:
        errors.append(dict(row=1, message="At least one valid delivery is required."))
    return dict(valid=bool(rows) and not errors, rows=rows, errors=errors)


def normalize(deliveries, coverage_end):
    rows, seen, names = [], set(), {}
    for item in deliveries:
        x = item.model_dump(mode="json")
        if x["delivery_id"] in seen:
            raise ValueError("Duplicate delivery IDs are not accepted.")
        seen.add(x["delivery_id"])
        sid = x["supplier_id"]
        if sid in names and names[sid] != x["supplier_name"]:
            raise ValueError("Each supplier ID must have one consistent name in a dataset.")
        names[sid] = x["supplier_name"]
        if x["ordered_date"] > str(coverage_end) or (x["actual_date"] and x["actual_date"] > str(coverage_end)):
            raise ValueError("Coverage end must include every order and actual receipt date.")
        if (date.fromisoformat(x["promised_date"]) - coverage_end).days > 365:
            raise ValueError("Future promises are limited to 365 days beyond coverage.")
        rows.append(x)
    rows.sort(key=lambda x: (x["promised_date"], x["delivery_id"]))
    first = min(x["ordered_date"] for x in rows)
    if (coverage_end - date.fromisoformat(first)).days > 1826:
        raise ValueError("Dataset coverage is limited to 1826 days.")
    warnings = [
        "Snapshot quality counts are final at coverage end; no return/inspection event timeline is available.",
        "One row represents a single receipt commitment; split shipments require an event model outside this release.",
    ]
    if (date.today() - coverage_end).days > 7:
        warnings.append("Coverage is stale; refresh source records before purchasing decisions.")
    return rows, dict(
        count=len(rows),
        start=first,
        coverage_end=str(coverage_end),
        suppliers=len(names),
        received_records=sum(x["actual_date"] is not None for x in rows),
        warnings=warnings,
    )
