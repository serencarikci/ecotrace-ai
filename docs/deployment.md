# Deployment

- Local: `docker compose up --build`
- Production example: `docker-compose.prod.yml` + `.env.production.example`
- Services: `postgres`, `api`, `scheduler`, `web`
- Validate production secrets at startup (`APP_ENV=production` fails on weak secrets / debug)
- Reverse-proxy TLS termination recommended; enable `ENABLE_HSTS=true` only behind HTTPS
- Health: `GET /health`, `GET /ready`; detailed `GET /api/v1/system/health*` requires system admin
