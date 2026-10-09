# HTTP API

Prefix /api, live OpenAPI /docs. POST /auth/register and /auth/login return session cookie/user/CSRF token. GET /auth/session restores; POST /auth/logout revokes. Writes require accepted Origin and X-CSRF-Token. Store/dataset/analysis/demo writes additionally require Idempotency-Key (1–100 chars). Preserve key for identical retries; changed payload conflicts.

| Method/path | Purpose |
|---|---|
| GET /health | Liveness |
| GET, POST /v1/stores | Purchasing workspaces: name, base unit |
| POST /v1/imports/deliveries/preview | Parse row errors before save |
| GET, POST /v1/stores/{id}/datasets | Immutable delivery snapshots |
| POST /v1/stores/{id}/analyses | Save scorecard review |
| GET /v1/analyses | Latest 100 owner reviews |
| POST /v1/comparisons | 2–10 distinct analyses, same workspace/dataset |
| GET /v1/analyses/{id}/report?format=json | Complete frozen inputs/results |
| GET /v1/analyses/{id}/report?format=suppliers | Supplier CSV |
| GET /v1/analyses/{id}/report?format=deliveries | Delivery CSV |
| POST /v1/demo | Synthetic snapshot, empty workspace catalog only |

Analysis payload:
```json
{"dataset_id":"owned-id","scenario_name":"Supplier review","grace_days":0,"minimum_due":3}
```
Dataset payload:
```json
{"source":"Purchasing export","coverage_end":"2026-09-30","deliveries":[{"supplier_id":"SUP-A","supplier_name":"Atlas","delivery_id":"D001","ordered_date":"2026-09-01","promised_date":"2026-09-10","actual_date":"2026-09-11","ordered_qty":100,"received_qty":100,"defect_qty":2,"returned_qty":1}]}
```
Preview takes csv_text. Comparison takes analysis_ids. Supplier CSV fields include due count, on-time/OTIF/fill/defect/return rates, score and rank; unavailable values remain blank. Free-form supplier names with spreadsheet formula prefixes are escaped. JSON keeps original text.

401 unauthenticated; 403 CSRF/origin; 404 absent/foreign record; 409 duplicate/replay conflict; 422 invalid contract; 429 throttle. Preview row errors are response data; valid=false blocks saving. UUIDs do not replace ownership.
