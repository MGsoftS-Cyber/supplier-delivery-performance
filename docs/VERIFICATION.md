# Verification record

Executed: 25 pytest tests; Ruff lint/format; SQLite Alembic upgrade/schema check; frontend Prettier and Vite build. Headless Chromium verifies registration, synthetic demo, two reviews, supplier reasons, exception filters, comparison, JSON/supplier/delivery downloads, invalid and valid CSV import, session restore, mobile width and logout. Screenshots use synthetic data.

Tests cover perfect/late/pending deliveries, deadline maturity, early received exclusion, grace population changes, per-row quantity caps, defects/returns and exact score, unavailable evidence, ranking sample/ties, schema boundaries, duplicates, snapshot persistence, owner isolation, CSV escaping and replay conflicts.

Not executed: Docker runtime, PostgreSQL runtime/concurrency, external connectors or production load. browser-smoke.cjs requires playwright-core and a compatible Chromium; run at repository root with SUPPLY_BROWSER and SUPPLY_URL configured. This release calculates descriptive metrics; it has no trained risk model to validate.
