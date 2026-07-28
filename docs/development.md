# Development guide

## Setup

```bash
cp .env.example .env
docker compose up --build
```

Optional host port overrides when defaults are busy:

```bash
POSTGRES_HOST_PORT=5433
API_HOST_PORT=8001
WEB_HOST_PORT=4200
```

Optional local tooling:

```bash
# Backend
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"

# Frontend
cd apps/web
npm install
npm start
```

## Commands

| Command | Description |
|---------|-------------|
| `make up` | Build and start compose stack |
| `make down` | Stop stack |
| `make logs` | Tail logs |
| `make migrate` | Alembic upgrade head |
| `make seed` / `make seed` | Idempotent demo seed |
| `make import-sample` | CSV template endpoint hint |
| `make test` | Backend + frontend tests |
| `make test-backend` | Pytest |
| `make test-backend` | Operations focused pytest |
| `make test-frontend` | Angular unit tests |
| `make lint` / `make format` | Quality gates |

## Migrations

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic current   # expect 0003_phase3 (head)
docker compose exec api alembic revision --autogenerate -m "description"
```

Do not call `Base.metadata.create_all` in production startup. Tests may create schema for isolation.

## Seed

```bash
docker compose exec api python -m ecotrace.db.seed
# second run must remain idempotent
docker compose exec api python -m ecotrace.db.seed
```

Seed includes roles/users/org plus units, activity types, İzmir/Manisa facilities, lines, equipment, sources, periods, and sample activity records.

## Attachments

- Docker volume: `ecotrace_attachments` → `/data/attachments`
- Env: `ATTACHMENT_STORAGE_PATH`, `MAX_ATTACHMENT_SIZE_MB`, `ALLOWED_ATTACHMENT_TYPES`
- API entrypoint ensures directory ownership for the non-root app user

## CSV imports

- Template: `GET /api/v1/organizations/{organizationId}/imports/activity-records/template`
- Max rows: `MAX_CSV_IMPORT_ROWS` (default 5000)
- Synchronous validation + execute in Operations (no Celery/Redis)

## Tests

Backend integration tests expect PostgreSQL and will create `ecotrace_test` if missing.

```bash
cd apps/api
export DATABASE_URL=postgresql+psycopg://ecotrace:ecotrace_dev_password@localhost:5433/ecotrace_test
export ATTACHMENT_STORAGE_PATH=/tmp/ecotrace-test-attachments
pytest tests/ -v
```

Frontend:

```bash
cd apps/web
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  npm test -- --watch=false --browsers=ChromeHeadless
```

## Formatting

```bash
# Backend
ruff format src tests && ruff check --fix src tests

# Frontend
npx prettier --write "src/**/*.{ts,html,scss,json}"
```

## Debugging

- API logs: structured console in development, JSON in production
- Every response includes `X-Request-ID`
- Swagger: http://localhost:${API_HOST_PORT:-8000}/docs
- Check readiness: `GET /ready`

## Common issues

**API unhealthy / migrations failing**  
Ensure Postgres healthcheck is green and credentials in `.env` match compose.

**Attachment upload returns permission denied**  
Rebuild the API image so entrypoint can chown `/data/attachments` before dropping privileges.

**CORS errors in local `ng serve`**  
Confirm `CORS_ALLOWED_ORIGINS` includes `http://localhost:4200` and `environment.apiUrl` points to the API host/port.

**Login works in Swagger but not UI**  
Hard-refresh the SPA; check browser network for `/api/v1/auth/login` and token persistence keys `ecotrace.*`.
