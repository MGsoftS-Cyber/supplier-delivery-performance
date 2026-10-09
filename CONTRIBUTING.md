# Contributing

Read docs/METHODOLOGY.md before changing analytics. engine.py owns definitions, imports.py parsing/normalization, schemas.py contracts, routes.py ownership/workflow, services.py transactions and replay. React renders server results and captures assumptions.

Install backend requirements-dev.txt and frontend npm ci. Run backend `ruff check app tests migrations`, `ruff format --check app tests migrations`, `pytest -q`, `alembic upgrade head`, `alembic check`; frontend `npm run format:check` and `npm run build`. Use an isolated database for schema work.

Add meaningful tests for deadline maturity, grace, pending rows, quantity caps, quality evidence, ranking samples, ownership and retries. Preserve immutable historical outputs. Engine semantic changes require documentation/version review. Persistent schema changes require new Alembic revisions; do not edit old deployed migrations.

Unpack into a Git repository and push to your own GitHub repository. Included Actions runs checks and Docker build. Never commit .env, local databases or supplier payloads. PRs should explain final behavior, analytical definition changes, verification and limitations. Code comments explain why business boundaries matter, not just what each statement does.
