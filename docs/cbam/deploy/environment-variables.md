# External test deployment — environment variables (names only)

Values must come from the host secret store / CI secrets. Never commit values.

## Core API

- `APP_NAME`
- `APP_ENV` (`development` | `test` | `production`)
- `APP_DEBUG`
- `APP_VERSION`
- `API_V1_PREFIX`
- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `ENABLE_API_DOCS`
- `ENABLE_HSTS`
- `ENABLE_METRICS`
- `LOG_LEVEL`
- `PUBLIC_APP_BASE_URL`
- `PUBLIC_API_BASE_URL`
- `TRUSTED_HOSTS`
- `CORS_ALLOWED_ORIGINS`

## Database

- `DATABASE_URL`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `RUN_MIGRATIONS`
- `RUN_SEED`

## Storage / artifacts

- `REPORT_STORAGE_PATH`
- `ATTACHMENT_STORAGE_PATH`
- `KNOWLEDGE_STORAGE_PATH`
- `BACKUP_STORAGE_PATH`
- `OFFICIAL_SEE_MAX_FILE_SIZE_MB`
- `OFFICIAL_SEE_RETENTION_DAYS`
- `OFFICIAL_SEE_MAX_CONCURRENT_PER_ORG`

## LibreOffice / Official Excel

- `LIBREOFFICE_SOFFICE_PATH`
- `LIBREOFFICE_RECALC_TIMEOUT_SECONDS`
- `OFFICIAL_SEE_TEMPLATE_PATH`
- `LIBREOFFICE_TMP_ROOT`

## Bootstrap users (external test only; override defaults)

- `INITIAL_ADMIN_EMAIL`
- `INITIAL_ADMIN_PASSWORD`
- `INITIAL_ADMIN_FULL_NAME`
- `DEMO_ORG_ADMIN_EMAIL`
- `DEMO_ORG_ADMIN_PASSWORD`
- `DEMO_ANALYST_EMAIL`
- `DEMO_ANALYST_PASSWORD`
- `DEMO_VIEWER_EMAIL`
- `DEMO_VIEWER_PASSWORD`

## Frontend (Vercel build)

- `ECOTRACE_API_URL` (HTTPS API origin; written into production environment at build time)
- `API_URL` (optional alias consumed by `write-production-env.mjs`)

## Auth lockout

- `LOGIN_MAX_FAILURES`
- `LOGIN_LOCKOUT_MINUTES`
