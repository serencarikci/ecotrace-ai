# CBAM API endpoint reconciliation

Generated from `cbam-api.service.ts` and live OpenAPI on the local CBAM review API.

## Counts

| Metric | Count |
|--------|------:|
| Frontend HTTP methods (`HttpClient` call sites) | 99 |
| Unique frontend endpoint keys (HTTP method + normalized path) | 99 |
| CBAM backend OpenAPI operations | 155 |
| Path overlap (ignore HTTP method) | 92 |

## Backend endpoint categories

Every backend endpoint is in **exactly one** of the first five categories.

| Category | Count | Meaning |
|----------|------:|---------|
| FRONTEND_USED | 99 | Matched to current Angular client key |
| BACKEND_ONLY_VALID | 56 | Present in API; not called by current UI client |
| ADMIN_OR_INTERNAL | 0 | Admin/internal/debug style |
| LEGACY_BUT_SUPPORTED | 0 | Legacy naming still routed |
| UNREACHABLE_OR_OBSOLETE | 0 | Obsolete markers |
| UNMAPPED (FE key only) | 0 | FE key normalization did not match OpenAPI (documentation gap, not runtime removal) |

Backend category sum (excl. UNMAPPED): **155** / **155**.

## Why client method count ≠ backend route count

Do not compare raw TypeScript method counts to the full router inventory without classification.

- The Angular client defines **99** HTTP methods for screens it implements.
- The FastAPI CBAM router exposes **155** operations, including catalogs, alternate reads, execution variants, and test/tooling endpoints.
- A fair comparison is `FRONTEND_USED` vs `BACKEND_ONLY_*` after path normalization.

Full item lists: `api-endpoint-categories.json`.
