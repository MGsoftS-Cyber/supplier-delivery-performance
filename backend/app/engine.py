"""Explainable, deadline-mature supplier performance; never a purchase decision."""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

ENGINE_VERSION = "1.0.0"


def ratio(a, b):
    return a / b if b else None


def summarize(rows, minimum_due):
    due = [x for x in rows if x["due"]]
    received = sum(x["received_qty"] for x in due)
    ordered = sum(x["ordered_qty"] for x in due)
    defective = sum(x["defect_qty"] for x in due)
    returned = sum(x["returned_qty"] for x in due)
    usable = sum(min(x["ordered_qty"], x["usable_qty"]) for x in due)
    otif = ratio(sum(x["otif"] for x in due), len(due))
    quality = ratio(received - defective - returned, received)
    fulfillment = ratio(sum(min(x["ordered_qty"], x["received_qty"]) for x in due), ordered)
    usable_fill = ratio(usable, ordered)
    # No silent weight renormalization: missing quantity evidence leaves score unavailable.
    score = 100 * (0.4 * otif + 0.3 * usable_fill + 0.3 * quality) if otif is not None and quality is not None else None
    eligible = len(due) >= minimum_due and score is not None
    return dict(
        records=len(rows),
        due_records=len(due),
        not_due=len(rows) - len(due),
        pending_overdue=sum(x["status"] == "Overdue pending" for x in due),
        late_receipts=sum(x["status"] == "Late receipt" for x in due),
        on_time_rate=ratio(sum(x["on_time"] for x in due), len(due)),
        otif_rate=otif,
        ordered_qty=ordered,
        received_qty=received,
        defect_qty=defective,
        returned_qty=returned,
        fulfillment_rate=fulfillment,
        usable_fill_rate=usable_fill,
        defect_rate=ratio(defective, received),
        return_rate=ratio(returned, received),
        retained_quality_rate=quality,
        score=score,
        eligible=eligible,
        average_late_days=mean([x["late_days"] for x in due if x["actual_date"]])
        if any(x["actual_date"] for x in due)
        else None,
        # Late-day average includes zero lateness for on-time due receipts, pending ages separate.
        max_overdue_days=max([x["overdue_days"] for x in due], default=0),
    )


def evaluate(data):
    cutoff = date.fromisoformat(data["coverage_end"])
    groups = defaultdict(list)
    deliveries = []
    for record in data["deliveries"]:
        x = dict(record)
        promised = date.fromisoformat(x["promised_date"])
        deadline = promised + timedelta(days=data["grace_days"])
        actual = date.fromisoformat(x["actual_date"]) if x["actual_date"] else None
        due = deadline <= cutoff
        on_time = actual is not None and actual <= deadline
        full = x["received_qty"] >= x["ordered_qty"]
        usable = x["received_qty"] - x["defect_qty"] - x["returned_qty"]
        status = (
            "Not yet due"
            if not due
            else "Overdue pending"
            if actual is None
            else "Late receipt"
            if not on_time
            else "On-time short"
            if not full
            else "On-time in full"
        )
        x.update(
            deadline=str(deadline),
            due=due,
            on_time=on_time,
            otif=on_time and full,
            usable_qty=usable,
            short_qty=max(0, x["ordered_qty"] - x["received_qty"]),
            status=status,
            late_days=max(0, (actual - deadline).days) if actual else None,
            overdue_days=max(0, (cutoff - deadline).days) if due and actual is None else 0,
        )
        deliveries.append(x)
        groups[x["supplier_id"]].append(x)
    suppliers = []
    for identifier, rows in sorted(groups.items()):
        stats = summarize(rows, data["minimum_due"])
        reasons = []
        if stats["due_records"] < data["minimum_due"]:
            reasons.append(
                f"Only {stats['due_records']} mature commitments; minimum ranking sample is {data['minimum_due']}."
            )
        if stats["score"] is None:
            reasons.append("Score unavailable: no mature commitments or no received units for quality evidence.")
        if stats["pending_overdue"]:
            reasons.append(f"{stats['pending_overdue']} overdue commitments have no receipt.")
        if stats["late_receipts"]:
            reasons.append(f"{stats['late_receipts']} mature commitments arrived after the adjusted deadline.")
        if stats["defect_qty"] or stats["returned_qty"]:
            reasons.append(
                f"{stats['defect_qty']} defective and {stats['returned_qty']} returned units in mature commitments."
            )
        if stats["usable_fill_rate"] is not None and stats["usable_fill_rate"] < 1:
            reasons.append(f"Usable quantity fulfillment is {stats['usable_fill_rate']:.1%}.")
        suppliers.append(
            dict(
                supplier_id=identifier,
                supplier_name=rows[0]["supplier_name"],
                **stats,
                reasons=reasons or ["No observed exception in the mature commitments."],
            )
        )
    ranked = sorted([x for x in suppliers if x["eligible"]], key=lambda x: (-x["score"], x["supplier_id"]))
    ranks = {x["supplier_id"]: i + 1 for i, x in enumerate(ranked)}
    for x in suppliers:
        x["rank"] = ranks.get(x["supplier_id"])
    monthly = []
    for month in sorted({x["promised_date"][:7] for x in deliveries if x["due"]}):
        stats = summarize(
            [x for x in deliveries if x["due"] and x["promised_date"].startswith(month)], data["minimum_due"]
        )
        monthly.append(dict(month=month, **stats))
    return dict(
        summary=dict(
            suppliers=len(suppliers), ranked_suppliers=len(ranked), **summarize(deliveries, data["minimum_due"])
        ),
        suppliers=suppliers,
        deliveries=deliveries,
        monthly=monthly,
        warnings=[
            "Ranking is descriptive: different products, destinations and sample sizes may not be comparable.",
            "Quality quantities are disjoint defect/return buckets at coverage end, not dated event histories.",
            "OTIF tests gross received quantity; usable fulfillment and quality are separate components.",
            "Not-yet-mature deadlines are excluded from performance denominators, even when already received.",
        ],
        conventions=dict(
            score="40% OTIF + 30% capped usable fulfillment + 30% retained quality",
            eligibility="Adjusted deadline <= coverage end; ranking also requires minimum_due",
            fulfillment="Sum min(received,ordered) per mature commitment / ordered units",
            quality="(received - defects - returns) / received for mature commitments",
            unit="One consistent base unit across dataset; no conversion",
            snapshot="Analysis date is dataset coverage end; no historical event reconstruction",
        ),
    )
