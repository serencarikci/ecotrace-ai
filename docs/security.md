# Security — EcoTrace AI (v0.3.0)

## Password hashing

- Algorithm: **Argon2** via `pwdlib`
- Verification uses the library’s constant-time comparison path
- Passwords are never logged or returned by the API

## JWT strategy

- Access tokens: short-lived HS256 JWTs (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 15)
- Claims: `sub`, `type=access`, `roles`, `iat`, `exp`, `jti`
- Refresh tokens: longer-lived JWTs (`type=refresh`) with separate jti
- Production rejects insecure default `SECRET_KEY` values and `APP_DEBUG=true`

## Refresh token strategy

- Only **SHA-256 hashes** of refresh tokens are stored in `refresh_tokens`
- Rotation on every refresh: old token revoked, `replaced_by_token_id` set
- Reuse of a revoked refresh token revokes the user’s active refresh chain
- Logout revokes the presented refresh token; logout-all revokes all active tokens

## Token storage tradeoffs (frontend)

Tokens are stored in **localStorage** for a simple SPA MVP.

| Approach | Pros | Cons |
|----------|------|------|
| localStorage (current) | Easy Angular interceptors, works cross-tab | Vulnerable to XSS token theft |
| HttpOnly cookies (recommended prod) | Not readable by JS | Needs CSRF strategy + cookie domain setup |

## Organization authorization strategy

Convention: **hide existence with 404** when the caller has no membership (and is not `system_admin`).

This applies to Foundation organizations and all Operations org-scoped resources (facilities, assets, periods, activity records, attachments, import jobs).

| Actor | Org-scoped read | Structure write | Activity write | Approve | Lock period | Unlock | Reference write |
|-------|-----------------|-----------------|----------------|---------|-------------|--------|-----------------|
| system_admin | all | yes | yes | yes | yes | yes | yes |
| organization_admin | membership | yes | yes | yes | yes | yes | no |
| sustainability_manager | membership | view assets | yes | yes | yes | no | no |
| analyst | membership | view assets | draft/submit/import | no | no | no | no |
| viewer | membership | read-only | no | no | no | no | no |

Backend policies are mandatory; frontend role guards are UX only.

## Attachment security (Operations)

- Local storage under `ATTACHMENT_STORAGE_PATH`, isolated by `organizationId`
- Stored file names are generated; original names are never used as paths
- Path traversal blocked; extension + MIME + size validated
- SHA-256 checksum stored; file contents are not audit-logged
- Download requires organization authorization
- Soft-delete of metadata (`is_deleted`); retention keeps blob for later releases
- Entrypoint fixes volume ownership then drops privileges to non-root `ecotrace` user

## CSV import trust boundary

- UTF-8 only; required headers enforced
- Row-level validation; invalid rows never inserted as activity records
- Max rows: `MAX_CSV_IMPORT_ROWS` (default 5000)
- Duplicate detection is deterministic; double execute returns 409
- Imported file contents are not written to audit logs

## Audit logging

Foundation auth/org events plus Operations facility/asset/period/activity/attachment/import/reference events. Secrets, tokens, and full uploaded/import file bodies are never logged.

## Secret management

- Secrets via environment / `.env` (never committed)
- `.env.example` contains development placeholders only
- Production validation blocks known insecure secret defaults

## Current limitations

- No rate limiting middleware yet
- No MFA / SSO
- No hardware-backed key management
- localStorage token storage
- Local filesystem attachments (object storage abstraction reserved for later)

## Production hardening recommendations

1. Rotate `SECRET_KEY` via a secrets manager
2. Prefer cookie-based refresh tokens
3. Terminate TLS at the edge
4. Restrict CORS to exact production origins
5. Add rate limits on `/auth/login` and `/auth/refresh`
6. Replace local attachment storage with object storage
7. Enable OpenTelemetry tracing
8. Regular dependency scanning in CI
