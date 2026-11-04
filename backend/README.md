# Creator Studio AI backend foundation

Initial SaaS backend slice: PostgreSQL persistence, registration/login, signed access tokens, per-user records, append-only credit ledger, credit reservations and job ownership.

## Local start

1. Copy `.env.example` to `.env` inside `backend/`.
2. Replace `JWT_SECRET` with a random secret of at least 32 bytes. Never commit `.env`.
3. From repository root run `docker compose -f docker-compose.saas.yml up --build`.
4. API docs: http://localhost:8000/docs; liveness: `/health/live`; readiness: `/health/ready`.

PostgreSQL initializes from `migrations/0001_initial.sql` only when the volume is first created. Reset local data only with `docker compose -f docker-compose.saas.yml down -v`.

## API

- POST `/api/v1/auth/register` — create account and grant configured starter credits.
- POST `/api/v1/auth/login` — obtain bearer token.
- GET `/api/v1/me` — current user.
- GET `/api/v1/credits` — credit balance.
- POST `/api/v1/jobs` — reserve configured credits and persist a user-owned queued job.
- GET `/api/v1/jobs/{id}` — read only the authenticated user's job.

## Deliberate boundaries

Provider execution is disabled. Job creation persists and reserves credits but does not call a provider or fake an image. Provider adapters, durable queue dispatch, storage, completion/failure settlement, upload validation and integration tests are not yet implemented. Payments are disabled. The old browser-side API-key flow has not yet been removed; frontend migration is the next slice.

Before public launch add rate limiting, email verification, password reset, abuse controls, audit events, HTTPS, secret manager and production CORS. Do not commercially republish upstream custom assets without written rights.
