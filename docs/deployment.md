# Deployment

- Local: `docker compose up --build`
- External-test stack (disposable): `docker-compose.external-test.yml`
- Production example: `docker-compose.prod.yml` + `.env.production.example`
- Services: `postgres`, `api`, `scheduler`, `web` (web optional when frontend is on Vercel)
- Validate production secrets at startup (`APP_ENV=production` fails on weak secrets / debug)
- Reverse-proxy TLS termination recommended; enable `ENABLE_HSTS=true` only behind HTTPS
- Health: `GET /health`, `GET /ready`, component readiness `GET /ready/components`
- Detailed `GET /api/v1/system/health*` requires system admin
- Legacy local stamp recovery (operator-only, never automatic): `docs/cbam/deploy/legacy-0007-phase7-recovery.md`

## Topology (external test)

| Layer | Role |
|---|---|
| Vercel | Angular SPA only (`apps/web`) |
| Backend host | Docker FastAPI + LibreOffice headless |
| Managed PostgreSQL | Empty DB → `alembic upgrade head` → seeds |
| Persistent artifact storage | Volume or object-storage adapter under `REPORT_STORAGE_PATH` |

Do **not** run FastAPI, PostgreSQL, or LibreOffice inside the Vercel frontend deployment.

## Frontend on Vercel (test SPA only)

- Build: `cd apps/web && ECOTRACE_API_URL=https://api.example.com npm run build:vercel`
- Output: `dist/web/browser`
- SPA fallback: `apps/web/vercel.json` rewrites `/app/**` and other routes to `index.html`
- Production API base URL comes from `ECOTRACE_API_URL` / `API_URL` (HTTPS required)
- Dev proxy (`proxy.conf.json`) remains local-only
- `vercel.json` must not contain secrets

## Backend hosting (required for CBAM Official Excel)

Official Excel needs FastAPI + PostgreSQL + LibreOffice + writable artifact storage.
Supported shape today: Docker image `apps/api/Dockerfile` (build from repo root) behind HTTPS reverse proxy.

### Provider checklist (choose manually — not auto-purchased)

- Docker / container runtime
- PostgreSQL 16+ (pgvector image compatible)
- LibreOffice-capable Linux image: build `apps/api/Dockerfile` from the **repo root** with **TDF LibreOffice 26.8.0** (aarch64 and x86-64 SHA pins; filename token `x86-64` on amd64 — no silent Debian 7.4 fallback). Tracked template: `apps/api/official-see/template.xlsx`.
- Persistent volume **or** object-storage adapter for reports/artifacts
- Memory: **≥ 4 GiB** recommended (LibreOffice + Excel); CPU: **≥ 2 vCPU**
- Request / proxy timeout: **≥ 5 minutes** for Official Excel generation
- HTTPS termination
- Environment secrets outside Git
- Health checks: `/health`, `/ready`, `/ready/components`

### Empty-database startup (required)

1. Create empty PostgreSQL database.  
2. Run `alembic upgrade head` (entrypoint default).  
3. Verify head `0032_cbam_prec_audit`.  
4. Run seeds twice; prove idempotency.  
5. Verify 53 `cbam_*` tables.  
6. **Never** use `alembic stamp` on new/production DBs.

### Artifact storage

Configure persistent storage outside the ephemeral container filesystem:

- Root path or object-storage adapter via `REPORT_STORAGE_PATH` (and related paths)
- Retention: `OFFICIAL_SEE_RETENTION_DAYS`
- Max size: `OFFICIAL_SEE_MAX_FILE_SIZE_MB`
- Concurrent Official Excel slots: `OFFICIAL_SEE_MAX_CONCURRENT_PER_ORG`
- Filename safety, tenant isolation, and download authorization are enforced in application code
- Do not commit generated workbooks

## Environment variable names (values never committed)

Core:

- `APP_NAME`, `APP_ENV`, `APP_DEBUG`, `APP_VERSION`
- `SECRET_KEY`, `INITIAL_ADMIN_PASSWORD`
- `CORS_ALLOWED_ORIGINS`, `TRUSTED_HOSTS`, `ENABLE_HSTS`
- `ENABLE_API_DOCS`
- `PUBLIC_APP_BASE_URL`, `PUBLIC_API_BASE_URL`

Database:

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `RUN_MIGRATIONS`, `RUN_SEED`

Storage:

- `ATTACHMENT_STORAGE_PATH`, `KNOWLEDGE_STORAGE_PATH`
- `REPORT_STORAGE_PATH`, `BACKUP_STORAGE_PATH`

LibreOffice / Official SEE:

- `LIBREOFFICE_SOFFICE_PATH`
- `LIBREOFFICE_RECALC_TIMEOUT_SECONDS`
- `LIBREOFFICE_TMP_ROOT`
- `OFFICIAL_SEE_TEMPLATE_PATH`
- `OFFICIAL_SEE_MAX_CONCURRENT_PER_ORG`
- `OFFICIAL_SEE_MAX_FILE_SIZE_MB`
- `OFFICIAL_SEE_RETENTION_DAYS`

Frontend build (Vercel):

- `ECOTRACE_API_URL` (or `API_URL`)
- `ALLOW_NON_HTTPS_API_URL` (local override only)

Optional retention / ops:

- `RETENTION_DAYS_NOTIFICATIONS`
- `RETENTION_DAYS_JOB_DETAILS`
- `RETENTION_DAYS_AGENT_EXECUTIONS`
- `SCHEDULER_ENABLED`, `ENABLE_METRICS`
- `SMTP_*`, `AI_*`

## Acceptance status (container-native)

- Linux **arm64** API image with **TDF LibreOffice 26.8.0.3** passed container-native Official SEE golden parity (local acceptance stack; evidence under `.tmp-validation/`, not committed).
- Empty-DB migrate + seed idempotency + `/ready/components` verified on that stack.
- **Public deployment has not been performed.**
- Unrelated host containers (other projects) restarting are **not** EcoTrace Official SEE release blockers.

## GitHub Actions vs Official SEE image

| Job | What it proves | LibreOffice 26.8 image / golden |
|-----|----------------|----------------------------------|
| Backend CI | ruff, mypy, alembic head, pytest (+ coverage floor), seed twice, **fast Dockerfile pin asserts** | Does **not** build the image; pins include TDF 26.8 aarch64 + **x86-64** SHA and tracked template SHA |
| **API Image CI** (`api-image-ci.yml`) | **Real** `docker build -f apps/api/Dockerfile` on **GitHub `ubuntu-latest` (linux/amd64)** + non-golden smoke (`soffice --version` 26.8, template SHA, uid 10001, writable `/data` + LO tmp) | Proves amd64 image **buildability**; **not** Official SEE golden PEE↔I/J/K parity |
| Frontend CI | lint, unit tests, production build (Node 22) | N/A |
| Compose CI | compose config / attachment volume | N/A |
| Local **arm64** acceptance | `ecotrace-api:external-test` + golden suite | **Authoritative** Linux Official SEE golden evidence |

TDF archive naming (authoritative index + metalink): directory `deb/x86_64/` + file `LibreOffice_26.8.0_Linux_x86-64_deb.tar.gz` (hyphen in filename). aarch64 uses `Linux_aarch64`. Never install Debian LibreOffice 7.4.

Do not claim GitHub amd64 CI covers Official SEE golden recalculation — that remains arm64 acceptance.
