# EcoTrace AI

**Version:** `0.3.0`

**Carbon, LCA and Sustainability Intelligence Platform**

EcoTrace AI is an enterprise-oriented sustainability platform for corporate carbon footprint management, Scope 1–3 emissions, LCA, ESG indicators, Digital Product Passport, industrial IoT ingestion, analytics, and AI-assisted sustainability insights.

This repository currently delivers identity/org foundations, organization operations & activity data, and a deterministic carbon accounting / emission calculation engine.

## Business problem

Organizations need a trustworthy system of record for environmental performance. Before carbon engines and AI copilots can be useful, they need:

- secure multi-user identity,
- organization-aware tenancy foundations,
- auditable API conventions,
- structured operational activity data (facilities, meters, periods, quantities),
- a modular architecture that can grow without rewrite,
- containerized, testable delivery.

## Current scope

**Platform foundation**

- Modular monorepo (`apps/api`, `apps/web`)
- FastAPI backend with Clean/Hexagonal-inspired module boundaries
- Angular frontend (standalone + Material)
- PostgreSQL + Alembic migrations
- JWT access tokens + rotating hashed refresh tokens
- User/role foundation and organization memberships
- Audit logging, Docker Compose, CI

**Operations & activity data**

- Facilities, production lines, equipment, data sources
- Units and activity types (global reference data)
- Reporting periods with lock/unlock
- Activity records with workflow, revisions, optimistic concurrency
- Attachments (local storage volume) and CSV activity imports
- Organization isolation (unauthorized cross-org access → **404**)

**Carbon accounting**

- Emission factor sources, versioned factors, org preferences
- Deterministic Decimal calculation engine (no LLM)
- Scope 1, location-based Scope 2, initial Scope 3
- Carbon inventories, calculation runs/items, immutable snapshots
- GWP reference dataset (**AR5-demo** — illustrative only)
- See [docs/carbon-accounting.md](docs/carbon-accounting.md)

See also [docs/operations.md](docs/operations.md) and [docs/foundation.md](docs/foundation.md).

## Future roadmap

| Focus | Status |
|------|--------|
| Facilities, production lines, activity data, CSV import | delivered |
| Emission factors, Scope 1–3 calculation engine | delivered |
| Analytics, dashboards, targets, scenarios | planned |
| Product LCA, PCF, Digital Product Passport | planned |
| AI Sustainability Copilot, RAG, embeddings | planned |
| IoT/MQTT/Kafka-ready ingestion, observability, hardening | planned |

## Architecture summary

EcoTrace AI is a **modular monolith**:

- Backend modules: `identity`, `organizations`, `facilities`, `operational_assets`, `reference_data`, `reporting_periods`, `activity_data`, `data_imports` (+ shared kernel)
- Frontend features: auth, dashboard, organizations, facilities, production lines, equipment, data sources, reporting periods, activity data, data imports, reference data, profile
- PostgreSQL as system of record; attachments on Docker volume `ecotrace_attachments`
- Nginx serves the Angular SPA and can proxy API paths

See [docs/architecture.md](docs/architecture.md).

## Technology stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, PyJWT, Argon2 (pwdlib), structlog, pytest, Ruff, MyPy

**Frontend:** Angular 19, TypeScript strict, Angular Material, RxJS, ESLint, Prettier, Jasmine/Karma

**Infra:** Docker, Docker Compose, Nginx, GitHub Actions

## Monorepo structure

```text
ecotrace-ai/
├── apps/api/          # FastAPI backend
├── apps/web/          # Angular frontend
├── docs/              # Architecture & security docs
├── scripts/           # DB wait / migrate / seed helpers
├── docker-compose.yml
└── Makefile
```

## Local development setup

### Prerequisites

- Docker Desktop / Docker Compose
- (Optional for local tooling) Python 3.12, Node.js 22 LTS

### Quick start with Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:4200
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

If host ports `5432` / `8000` / `4200` are already in use, set overrides in `.env`:

```bash
POSTGRES_HOST_PORT=5433
API_HOST_PORT=8001
WEB_HOST_PORT=4200
```

On first API start, migrations and seed run automatically.

### Make targets

```bash
make up
make down
make logs
make migrate
make seed
make import-sample
make test
make lint
make format
```

## Environment variables

See [.env.example](.env.example). Important variables:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing key (≥32 chars; insecure defaults blocked in production) |
| `DATABASE_URL` / `POSTGRES_*` | Database connectivity |
| `CORS_ALLOWED_ORIGINS` | Allowed browser origins |
| `INITIAL_ADMIN_*` | Seeded system administrator |
| `DEMO_*` | Seeded demo users |
| `ATTACHMENT_STORAGE_PATH` | Local attachment root (Docker: `/data/attachments`) |
| `MAX_ATTACHMENT_SIZE_MB` | Max upload size |
| `MAX_CSV_IMPORT_ROWS` | CSV import row limit (default 5000) |
| `ALLOWED_ATTACHMENT_TYPES` | Allowed extensions |
| `POSTGRES_HOST_PORT` / `API_HOST_PORT` / `WEB_HOST_PORT` | Host port overrides |

## Database migrations

```bash
make migrate
docker compose exec api alembic upgrade head
docker compose exec api alembic current   # 0003_phase3 (head)
```

Create a revision:

```bash
make migration name="add_example_table"
```

Schema is applied **only** through Alembic (no `create_all` on app startup in production flow).

## Seed data

```bash
make seed
# second run must remain idempotent
make seed
```

Seed creates roles, demo organization/users, units, activity types, İzmir/Manisa facilities, production lines, equipment, data sources, reporting periods, and sample activity records.

## Demo users (local development)

| Email | Password | Role |
|-------|----------|------|
| admin@ecotrace.dev | EcoTraceAdmin!2024 | system_admin |
| orgadmin@ecotrace.dev | EcoTraceOrgAdmin!2024 | organization_admin |
| analyst@ecotrace.dev | EcoTraceAnalyst!2024 | analyst |
| viewer@ecotrace.dev | EcoTraceViewer!2024 | viewer |

Demo organization: **EcoTrace Demo Industries** (`ecotrace-demo-industries`)

## Demo workflow

1. Login as `orgadmin@ecotrace.dev`
2. Open Facilities → create/edit a facility
3. Create a production line and equipment
4. Open Reporting Periods → create/lock/unlock
5. Open Activity Data → create draft → Submit
6. Approve as organization admin / sustainability manager
7. Upload an attachment on the activity detail page
8. Open Data Imports → download template → upload CSV → validate → execute
9. Open Carbon Inventories → validate → calculate → review results

UI: http://localhost:${WEB_HOST_PORT:-4200}  
API docs: http://localhost:${API_HOST_PORT:-8000}/docs

## API documentation

Interactive OpenAPI/Swagger UI: http://localhost:8000/docs (or your `API_HOST_PORT`)

Conventions: [docs/api-conventions.md](docs/api-conventions.md) · Operations: [docs/operations.md](docs/operations.md) · Carbon: [docs/carbon-accounting.md](docs/carbon-accounting.md)

## Testing

```bash
# Backend
cd apps/api && python3.12 -m pip install ".[dev]" && pytest

# Frontend
cd apps/web && npm install && npm test -- --watch=false --browsers=ChromeHeadless
```

CI workflows: backend (Ruff/MyPy/Alembic/Pytest/seed), frontend (lint/test/build), compose config validation.

## Linting and formatting

```bash
make lint
make format
```

## Security notes

- Passwords hashed with Argon2
- Refresh tokens stored as SHA-256 hashes only
- Refresh rotation + reuse detection
- Backend enforces organization isolation and role policies
- Attachments validated (type/size/path) and authorization-gated
- See [docs/security.md](docs/security.md)

## Known limitations

- Analytics dashboards, LCA/PCF/DPP, IoT ingestion, and AI copilots are not included yet
- CSV import only (no XLSX)
- Synchronous imports (no Celery/Redis/Kafka)
- Local filesystem attachments (object storage later)
- localStorage token storage (cookie strategy recommended for production)

## License

MIT — see [LICENSE](LICENSE).
