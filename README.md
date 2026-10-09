# SupplyIQ — Supplier & Delivery Performance

Idea 4: independent analytics for purchasing, e-commerce and logistics. Import promised/actual dates and quantities, review delays, fulfillment, defects and returns, compare supplier scorecards with reasons, and save/export evidence. Python 3.12/FastAPI; JavaScript/React 19; SQLAlchemy/Alembic; SQLite locally and PostgreSQL 17 in Compose. MIT license, version 1.0.0.

## Docker start

Copy `.env.example` to `.env`; replace POSTGRES_PASSWORD with a strong random URL-safe value. Run `docker compose up --build`, open http://localhost:8086 and create your account. No default account/password. Load demo data then Analyze supplier performance.

Docker/PostgreSQL runtime was not executed in delivery; verify on the target machine.

## Local start

```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8006
```
In a second terminal:
```sh
cd frontend
npm ci
npm run dev
```
Open http://localhost:5179. Vite forwards /api to 8006. For a single-server preview, `npm run build` in frontend and open http://localhost:8006. SQLite defaults to backend/supply.db. OpenAPI at /docs.

## Workflow

Create a purchasing workspace and common base unit. Preview `examples/deliveries.csv`, choose source and coverage end, save an immutable revision. Choose grace days (0–30) and minimum mature sample (1–100). Save a supplier review, inspect scorecards and reasons, filter delivery exceptions, compare assumption changes and download JSON/supplier/delivery CSV.

Exact header: `supplier_id,supplier_name,delivery_id,ordered_date,promised_date,actual_date,ordered_qty,received_qty,defect_qty,returned_qty`. One row per single-receipt commitment. Blank actual date requires zero received/defect/return units. Dates/quantities are validated. Defects and returns must be disjoint buckets. All quantities must use the workspace base unit; no conversion.

## Definitions

Only adjusted deadlines (promise + grace) on/before the dataset's end-of-day coverage cutoff enter denominators. Pending mature commitments count as timeliness/fulfillment failures. OTIF means actual receipt on time and gross received >= ordered. Fulfillment caps each row's received units to ordered units; excess on one row cannot offset another shortage. Usable fulfillment subtracts defects/returns before the cap. Quality = retained units / received units.

Score = 40% OTIF + 30% usable fulfillment + 30% retained quality. Missing quality leaves score unavailable. Minimum sample determines ranking eligibility, not statistical confidence. Rankings are descriptive and may not compare unlike products/routes fairly. No automatic purchase, supplier messaging or live ERP connector is implemented.

This release supports single receipt commitments, not a split shipment timeline. Coverage is user-declared, not verified remotely. Inspection/return quantities are snapshot totals without event dates. Analyses use coverage end rather than reconstructing earlier states. Cancellation policy and unit conversion belong upstream.

Read docs/METHODOLOGY.md, ARCHITECTURE.md, API.md, PRODUCTION.md, VERIFICATION.md and CONTRIBUTING.md. docs screenshots show synthetic data; no inventory reference image is included.
