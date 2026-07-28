# Production Readiness

Checklist:

- [ ] Strong `SECRET_KEY` (≥48 chars, non-default)
- [ ] `APP_DEBUG=false`, `APP_ENV=production`
- [ ] Restricted CORS / trusted hosts / TLS + HSTS
- [ ] Persistent volumes for DB and file stores
- [ ] Scheduler service healthy
- [ ] Backup schedule + restore drill
- [ ] Metrics/log shipping configured
- [ ] Seed disabled in production (`RUN_SEED=false`)
- [ ] AI provider credentials reviewed if external providers enabled
