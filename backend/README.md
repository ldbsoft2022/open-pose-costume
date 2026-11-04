# Creator Studio AI backend foundation

This backend is the SaaS API foundation. It provides PostgreSQL persistence, registration/login, bearer authentication, per-user ownership checks, an append-only credit ledger, credit reservations, job lifecycle endpoints, projects and virtual-character profiles.

## Local start

1. Copy `.env.example` to `.env` inside `backend/`.
2. Replace `JWT_SECRET` with a unique random secret of at least 32 bytes. Never commit `.env`.
3. From repository root run `docker compose -f docker-compose.saas.yml up --build`.
4. API docs: http://localhost:8000/docs; liveness: `/health/live`; readiness: `/health/ready`.

For a new local database volume, PostgreSQL applies migrations 0001 and 0002 at initialization. For an existing volume, apply the new migration manually:

```bash
docker compose -f docker-compose.saas.yml exec -T db psql -U creator -d creator_studio < backend/migrations/0002_job_idempotency_and_constraints.sql
```

Resetting the local development database destroys its data: `docker compose -f docker-compose.saas.yml down -v`.

## API

- POST `/api/v1/auth/register` — create account and grant configured starter credits.
- POST `/api/v1/auth/login` — obtain bearer token.
- GET `/api/v1/me` — current user.
- GET `/api/v1/credits` — credit balance.
- GET/POST `/api/v1/projects` — list/create the authenticated user's projects.
- GET/POST `/api/v1/characters` — list/create virtual-character profiles. Reference assets must belong to the same user.
- GET `/api/v1/jobs` and GET `/api/v1/jobs/{id}` — list/read only the authenticated user's jobs.
- POST `/api/v1/jobs/{id}/cancel` — cancel a queued job and refund its reservation.
- POST `/api/v1/jobs` — create an idempotent generation job using the `Idempotency-Key` header.

## Generation and billing safety

Image generation is fail-closed. The jobs endpoint returns HTTP 503 unless a server-side provider name, API base URL and API key are configured. This repository slice does not yet include a production provider adapter, durable queue dispatcher, object storage, provider callback handling or success-cost settlement. Do not configure fake credentials to bypass this guard.

The credit account row is locked during mutations; the ledger has globally unique idempotency keys and job reservations are unique per job. Failure/cancellation refunds are idempotent. A running job cannot be cancelled until provider-side cancellation is implemented. The API never claims to have generated an image when it has not.

## Security and production readiness

- Production startup rejects the default/short JWT secret and wildcard CORS.
- Use HTTPS, a production secret manager, rate limiting, email verification, password reset, abuse controls and audit events before public launch.
- Add object storage signed uploads/downloads, file magic-byte and image-dimension validation, deletion workflows and malware scanning policy.
- Add provider adapters with per-model price versions, provider request IDs, actual cost capture, timeouts, rate limits and retry policies before enabling generation.
- Payments are not enabled. Add verified raw-body webhook signatures, event idempotency and order/subscription state transitions before accepting money.
- User-uploaded real-person images require clear user rights/consent, privacy notices and deletion support.
- Do not commercially republish upstream custom assets without written commercial SaaS rights.
