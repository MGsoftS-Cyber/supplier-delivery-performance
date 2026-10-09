"""Deadline populations, capped quantities, score evidence, ownership and snapshots."""

from datetime import date
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.engine import evaluate
from app.schemas import DeliveryInput, DatasetInput
from app.imports import normalize, preview_deliveries, HEADER


def row(
    identifier="D1",
    supplier="S1",
    promise="2026-01-10",
    actual="2026-01-10",
    ordered=100,
    received=100,
    defects=0,
    returns=0,
    name="Supplier A",
):
    return dict(
        delivery_id=identifier,
        supplier_id=supplier,
        supplier_name=name,
        ordered_date="2026-01-01",
        promised_date=promise,
        actual_date=actual,
        ordered_qty=ordered,
        received_qty=received,
        defect_qty=defects,
        returned_qty=returns,
    )


def data(rows, coverage="2026-01-31", grace=0, minimum=1):
    d = DatasetInput(source="test", coverage_end=coverage, deliveries=rows)
    records, quality = normalize(d.deliveries, d.coverage_end)
    return dict(deliveries=records, quality=quality, coverage_end=coverage, grace_days=grace, minimum_due=minimum)


def test_perfect_supplier():
    s = evaluate(data([row()]))["summary"]
    assert s["score"] == 100 and s["otif_rate"] == 1 and s["usable_fill_rate"] == 1


def test_late_and_pending_in_denominator():
    out = evaluate(data([row(), row("D2", actual="2026-01-13"), row("D3", actual=None, received=0)]))
    s = out["summary"]
    assert s["on_time_rate"] == pytest.approx(1 / 3)
    assert s["otif_rate"] == pytest.approx(1 / 3)
    assert s["pending_overdue"] == 1 and s["late_receipts"] == 1
    assert s["fulfillment_rate"] == pytest.approx(2 / 3)
    assert s["average_late_days"] == 1.5


def test_not_due_excludes_even_early_receipt():
    out = evaluate(data([row(), row("D2", promise="2026-02-10", actual="2026-01-25", defects=99)]))
    assert out["summary"]["due_records"] == 1 and out["summary"]["not_due"] == 1
    assert out["summary"]["defect_qty"] == 0 and out["summary"]["score"] == 100


def test_grace_changes_population_and_timeliness():
    rows = [row(actual="2026-01-12"), row("D2", promise="2026-01-30", actual=None, received=0)]
    strict = evaluate(data(rows))
    grace = evaluate(data(rows, grace=3))
    assert strict["summary"]["due_records"] == 2 and strict["summary"]["otif_rate"] == 0
    assert grace["summary"]["due_records"] == 1 and grace["summary"]["otif_rate"] == 1


def test_capping_each_commitment_prevents_overfill_offset():
    s = evaluate(data([row(received=150), row("D2", received=50)]))["summary"]
    assert s["fulfillment_rate"] == 0.75 and s["usable_fill_rate"] == 0.75
    assert s["otif_rate"] == 0.5


def test_defects_returns_and_exact_score():
    s = evaluate(data([row(defects=10, returns=5)]))["summary"]
    assert s["otif_rate"] == 1 and s["defect_rate"] == 0.1 and s["return_rate"] == 0.05
    assert s["usable_fill_rate"] == 0.85 and s["retained_quality_rate"] == 0.85
    assert s["score"] == pytest.approx(91)


def test_no_receipts_no_quality_or_score():
    s = evaluate(data([row(actual=None, received=0)]))["summary"]
    assert s["on_time_rate"] == 0 and s["fulfillment_rate"] == 0
    assert s["defect_rate"] is None and s["score"] is None
    assert not s["eligible"]


def test_future_only_unavailable_rates():
    s = evaluate(data([row(promise="2026-02-10", actual=None, received=0)]))["summary"]
    assert s["due_records"] == 0 and s["otif_rate"] is None and s["score"] is None


def test_minimum_sample_and_deterministic_ranks():
    rows = [row(supplier="S2"), row("D2", supplier="S1")]
    out = evaluate(data(rows, minimum=2))
    assert out["summary"]["ranked_suppliers"] == 0
    out = evaluate(data(rows))
    ranks = {s["supplier_id"]: s["rank"] for s in out["suppliers"]}
    assert ranks == {"S1": 1, "S2": 2}


def test_deadline_boundary():
    s = evaluate(data([row(promise="2026-01-31", actual="2026-01-31")]))["summary"]
    assert s["due_records"] == 1 and s["otif_rate"] == 1


@pytest.mark.parametrize(
    "change",
    [
        {"received_qty": -1},
        {"ordered_qty": 0},
        {"ordered_qty": 1.5},
        {"defect_qty": 90, "returned_qty": 20},
        {"actual_date": None, "received_qty": 1},
        {"actual_date": "2025-12-31"},
        {"promised_date": "2025-12-31"},
        {"received_qty": 0},
        {"supplier_id": "=BAD"},
    ],
)
def test_bad_contract(change):
    with pytest.raises(ValidationError):
        DeliveryInput(**{**row(), **change})


def test_duplicates_name_and_coverage():
    with pytest.raises(ValueError):
        data([row(), row()])
    with pytest.raises(ValueError):
        data([row(), row("D2", name="Changed name")])
    with pytest.raises(ValueError):
        data([row(actual="2026-02-01")])


def test_csv_invalid_and_duplicate():
    header = ",".join(HEADER) + "\n"
    text = "S1,Supplier A,D1,2026-01-01,2026-01-10,2026-01-10,100,100,0,0\n"
    assert preview_deliveries(header + text)["valid"]
    assert not preview_deliveries(header + text + text)["valid"]
    assert not preview_deliveries(header + text.replace(",100,100,", ",100,NaN,"))["valid"]


def login(client, email="owner@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "SupplyReview!2026"})
    assert r.status_code == 201, r.text
    return {"X-CSRF-Token": r.json()["csrf_token"], "Origin": "http://localhost:8006", "Idempotency-Key": str(uuid4())}


def seed(client):
    h = login(client)
    d = client.post("/api/v1/demo", headers=h)
    assert d.status_code == 201, d.text
    return (
        h,
        d.json(),
        dict(dataset_id=d.json()["dataset_id"], scenario_name="Supplier review", grace_days=0, minimum_due=3),
    )


def test_api_replay_conflict_reports(client):
    h, d, b = seed(client)
    url = f"/api/v1/stores/{d['store_id']}/analyses"
    h["Idempotency-Key"] = str(uuid4())
    a = client.post(url, json=b, headers=h)
    assert a.status_code == 201, a.text
    assert client.post(url, json=b, headers=h).json()["id"] == a.json()["id"]
    assert client.post(url, json={**b, "grace_days": 2}, headers=h).status_code == 409
    for fmt in ["json", "suppliers", "deliveries"]:
        r = client.get(f"/api/v1/analyses/{a.json()['id']}/report?format={fmt}")
        assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]


def test_owner_isolation(client):
    h, d, b = seed(client)
    a = client.post(f"/api/v1/stores/{d['store_id']}/analyses", json=b, headers=h).json()
    client.cookies.clear()
    other = login(client, "other@example.com")
    assert client.get(f"/api/v1/stores/{d['store_id']}/datasets").status_code == 404
    assert client.post(f"/api/v1/stores/{d['store_id']}/analyses", json=b, headers=other).status_code == 404
    assert client.get(f"/api/v1/analyses/{a['id']}/report").status_code == 404
    assert client.get("/api/v1/analyses").json() == []


def test_snapshot_dedup_and_csv_safety(client):
    h, d, b = seed(client)
    url = f"/api/v1/stores/{d['store_id']}"
    body = dict(source="upload", coverage_end=str(date.today()), deliveries=[row(name="=FORMULA")])
    h["Idempotency-Key"] = str(uuid4())
    dataset = client.post(url + "/datasets", json=body, headers=h).json()
    h["Idempotency-Key"] = str(uuid4())
    assert client.post(url + "/datasets", json=body, headers=h).json()["id"] == dataset["id"]
    b["dataset_id"] = dataset["id"]
    h["Idempotency-Key"] = str(uuid4())
    a = client.post(url + "/analyses", json=b, headers=h).json()
    assert "'=FORMULA" in client.get(f"/api/v1/analyses/{a['id']}/report?format=suppliers").text
    body["deliveries"].append(row("D2", name="=FORMULA"))
    h["Idempotency-Key"] = str(uuid4())
    assert client.post(url + "/datasets", json=body, headers=h).status_code == 201
    saved = client.get(f"/api/v1/analyses/{a['id']}/report").json()
    assert saved["inputs"] == a["inputs"] and saved["results"] == a["results"]


def test_comparison_and_csrf(client):
    assert client.get("/api/v1/stores").status_code == 401
    h, d, b = seed(client)
    url = f"/api/v1/stores/{d['store_id']}/analyses"
    a = client.post(url, json=b, headers=h).json()
    h["Idempotency-Key"] = str(uuid4())
    c = client.post(url, json={**b, "grace_days": 2}, headers=h).json()
    assert client.post("/api/v1/comparisons", json={"analysis_ids": [a["id"], c["id"]]}, headers=h).status_code == 200
    assert client.post("/api/v1/stores", json={"name": "No CSRF"}, headers={"Idempotency-Key": "a"}).status_code == 403
