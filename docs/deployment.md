# Deployment

- Local: `docker compose up --build`
- Production example: `docker-compose.prod.yml` + `.env.production.example`
- Services: `postgres`, `api`, `scheduler`, `web`
- Validate production secrets at startup (`APP_ENV=production` fails on weak secrets / debug)
- Reverse-proxy TLS termination recommended; enable `ENABLE_HSTS=true` only behind HTTPS
- Health: `GET /health`, `GET /ready`; detailed `GET /api/v1/system/health*` requires system admin

## Frontend on Vercel (test SPA only)

The Angular app can be hosted on Vercel as a static SPA:

- Build: `cd apps/web && npm run build` (output `dist/web/browser`)
- SPA fallback: `apps/web/vercel.json` rewrites all routes to `index.html`
- Set production `environment.apiUrl` to the HTTPS API origin when the API is not same-origin
- Do **not** treat Vercel as the backend host

## Backend hosting (required for CBAM Official Excel)

Official Excel needs FastAPI + PostgreSQL + LibreOffice + writable artifact storage.
Supported shape today: Docker Compose (`docker-compose.prod.yml`) behind HTTPS reverse proxy.

Minimum backend requirements for a shared test environment:

- Separate test database and credentials
- `LIBREOFFICE_SOFFICE_PATH` or `/Applications/.../soffice` / Linux `soffice` installed
- Persistent `REPORT_STORAGE_PATH` (and attachment/knowledge/backup volumes)
- Long request timeout for Excel generation (minutes)
- Restricted `CORS_ALLOWED_ORIGINS` to the Vercel HTTPS origin
- `APP_DEBUG=false`, strong `SECRET_KEY`, no demo passwords from `.env.example`
- Protect or disable public Swagger/OpenAPI in shared test
- Tenant isolation for artifact download remains mandatory
