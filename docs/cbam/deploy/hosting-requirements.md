# Backend hosting requirements (provider-agnostic)

Do not bind to a specific vendor. Select any host that satisfies:

## Required capabilities

| Capability | Requirement |
|------------|-------------|
| Container runtime | Docker / OCI images |
| PostgreSQL | Managed Postgres 16+ with durable storage (pgvector optional but recommended for full product) |
| Image | EcoTrace API image with LibreOffice headless (`soffice`) |
| Persistent volume or object storage | Mount at `REPORT_STORAGE_PATH` (and preferably attachments/knowledge/backups) |
| HTTPS | Terminate TLS at edge; API serves behind HTTPS |
| Secrets | Environment injection; nothing secret in Git |
| Health checks | `GET /health` (liveness), `GET /ready` + `GET /ready/components` (readiness) |
| Request timeout | ≥ 5 minutes for Official Excel generate/recalc paths |

## Sizing recommendation (external testers)

| Resource | Recommendation |
|----------|----------------|
| API+LibreOffice memory | **4 GB** minimum (2 GB often fails under concurrent LO) |
| API CPU | **2 vCPU** |
| Postgres memory | **2 GB** |
| Disk (artifacts) | Start **20 GB** SSD volume; apply retention |

## Architecture split

1. **Vercel** — Angular SPA only (`apps/web`). No FastAPI, Postgres, or LibreOffice.  
2. **Backend host** — FastAPI container with LibreOffice.  
3. **Managed PostgreSQL** — separate service.  
4. **Persistent artifact storage** — volume or S3-compatible adapter mounted/configured as `REPORT_STORAGE_PATH`.

## Explicit non-goals for Vercel

- Do not run LibreOffice, Alembic, or PostgreSQL inside the frontend deployment.
