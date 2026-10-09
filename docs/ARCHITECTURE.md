# Architecture

React dashboard → same-origin HTTP → FastAPI authentication/ownership → frozen dataset inputs → pure engine → saved analysis and reports. SQLAlchemy stores relational ownership with bounded JSON snapshots. Alembic versions schema. Atomic write/replay service prevents duplicate operations.

User owns Store (purchasing workspace) and LoginSession. Store has unique owner/name and common base unit. Dataset belongs to Store; source, coverage end, deliveries, quality and fingerprint are immutable. Unique store/fingerprint reuses identical revision (source/coverage affect fingerprint). Analysis belongs to Store/Dataset and stores complete inputs/results plus engine version. RequestRecord is unique by owner/scope/key and stores payload hash/response.

Suppliers are analytical entities derived from stable supplier IDs in each dataset, not separate editable vendor accounts. Names must be consistent per ID per dataset. No supplier login, contact messaging or order placement.

| File | Responsibility |
|---|---|
| main.py / security.py | App, sessions, Argon2, CSRF/origin, safe errors |
| schemas.py | Strict contracts and cross-field receipt checks |
| imports.py | CSV row errors, duplicate/name checks and snapshot coverage |
| engine.py | Due population, quantities, rates, scores and reasons |
| models.py / database.py | Ownership, JSON snapshots, request sessions |
| services.py | Payload fingerprint and atomic durable replay |
| routes.py | Owner-scoped imports, analyses, comparisons, CSV/JSON |
| frontend/src/main.jsx | Six views, scorecards, filters and review forms |
| frontend/src/api.js | Cookie-based JSON transport and CSRF attachment |

The pure engine has no database/network imports. Snapshot history preserves each result after new imports. GET dataset/analysis lists include data and are not paginated; first-release limits bound them but they may still be large. Higher-volume services need indexed delivery/receipt facts, metadata pagination and workers.
