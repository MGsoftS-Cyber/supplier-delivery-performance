# Supplier-performance methodology

## Input and cutoff

One record per single-receipt delivery commitment. Ordered quantity is positive integer <=1e9; other quantities are integer 0..1e9. IDs use letters/digits/underscore/hyphen up to 80 characters; name up to 120. Ordered date cannot be future. Promise cannot precede order. Actual receipt lies between order and today. Blank actual date requires all received/defect/return counts zero; positive actual receipt requires positive received units. Defects and returns are disjoint and their sum cannot exceed received.

CSV limit 2 million characters, maximum 10000 rows, maximum 1826 coverage days. Duplicate delivery IDs and inconsistent supplier names reject. Coverage end includes every order and actual receipt, cannot be future; future promises up to 365 days after coverage are allowed. User declares a complete end-of-day snapshot, not verified by a connector. Same base unit across all rows is required. Cancellation/mixed-product/unit normalization belongs upstream.

## Mature population

Adjusted deadline = promised date + grace_days (0–30). A commitment is due/mature when deadline <= coverage_end. This treats coverage as end of day. Actual received rows whose deadline is later are excluded until maturity, avoiding an early-receipt-only denominator. Pending mature rows count as failures; grace can change both classification and denominator population.

On time = actual receipt exists and <= adjusted deadline. In full = gross received_qty >= ordered_qty. OTIF = both, divided by all mature commitments. On-time rate also uses all mature commitments, including pending failures. This is a documented application denominator, not a claim of identical KPI conventions across businesses.

## Quantities and quality

Gross fulfillment = sum(min(received,ordered) for each mature row) / sum(ordered). Usable_qty = received - defects - returns. Usable fulfillment = sum(min(usable_qty,ordered) per mature row) / sum(ordered). Per-row caps stop overdelivery on one commitment masking shortage on another. OTIF still uses gross received; a full receipt with defects can pass OTIF while quality and usable fill fall.

Defect rate = sum defects / sum gross received for mature rows. Return rate = sum disjoint returns / received. Retained quality = (received - defects - returns)/received. If no received units, quality/rates are unavailable, not assumed perfect. With no mature records all performance ratios are unavailable.

Mean delay is mean max(0,actual-deadline) over mature received rows, including zeros for on-time receipts. It excludes pending rows. Max overdue age measures cutoff-deadline among mature pending records. Keep these populations distinct.

## Score and sample

Fixed score 0..100 = 100*(0.40*OTIF + 0.30*usable_fill + 0.30*retained_quality). Missing quality leaves score null; weights are not renormalized. minimum_due (1–100, default 3) determines ranking eligibility, together with score availability. Raw score can still display below minimum but rank is null. Sort eligible suppliers descending score; ties sort supplier ID. Ordinal tie ranks are deterministic, not evidence of superiority.

Reasons disclose insufficient sample, unavailable evidence, overdue pending, late receipts, rejected quantities and usable shortfall. Labels/ranks are descriptive. Minimum sample is a display rule, not a confidence interval. Global rates recompute totals over all rows; they are not averages of supplier percentages. Monthly groups use original promised month among currently mature rows; partial maturity and changing grace affect comparison.

## Snapshot limits

Analysis date is fixed to dataset coverage end. No arbitrary retrospective cutoff is offered because returns/defects have no event dates. Single aggregate receipt date/quantity cannot prove a split shipment was fully received before deadline; do not import cumulative split receipts as if this were supported. Live ERP connectors, predictive supplier risk, causal blame, cost metrics, automatic purchasing and supplier communication are future features.

Background: ASCM KPI/SCOR resources discuss timeliness, quantity and condition as reliability dimensions. This implementation uses its own disclosed mature-commitment denominator and 40/30/30 score, not a certified SCOR score. https://scor.ascm.org/performance/reliability/RL.1.1
