# Production and extensions

Compose binds localhost:8086; PostgreSQL stays internal. Add HTTPS proxy, COOKIE_SECURE=true, explicit trusted ALLOWED_ORIGINS, strong credentials, ingress limits, monitoring and backups with restore tests. Align deployment timezone with source calendar policy. Run migrations once before replicas; entrypoint assumes one application instance.

SQLite tests do not prove PostgreSQL concurrency. Execute target-runtime migrations, repeated/concurrent request keys, rollback and load tests. Docker/PostgreSQL runtime was not executed here. Review dependencies and security before deployment.

Starter lacks shared-workspace roles, account recovery/email verification, SSO, billing, distributed rate limits, connectors and worker queues. Add these deliberately for commercial SaaS. Use indexed delivery/receipt/event facts and paginated metadata at scale. Avoid logging credentials or supplier data.

Future ERP adapter must identify original promise versions, line/commitment IDs, cancellations, agreed units, split receipts, inspection/return event times and source cutoffs. Reconcile before using scorecards for vendor decisions. Separate transport delay causes from supplier responsibility; this release only observes dates/quantities and does not assign causal blame. No automatic orders or external messages occur.
