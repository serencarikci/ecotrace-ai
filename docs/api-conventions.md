# API conventions

## Versioning

- All business endpoints live under `/api/v1`
- Health probes remain unversioned: `/health`, `/ready`

## Naming

| Layer | Convention |
|-------|------------|
| URL resources | plural nouns (`/organizations`, `/activity-records`) |
| JSON properties | camelCase |
| Python identifiers | snake_case |
| DB columns | snake_case |

Pydantic models use `alias_generator` to emit camelCase while accepting either form on input (`populate_by_name=True`).

## Pagination

Query:

- `page` (default 1)
- `pageSize` (default 20, max 100)

Response:

```json
{
  "items": [],
  "page": 1,
  "pageSize": 20,
  "totalItems": 0,
  "totalPages": 0
}
```

## Errors

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid data.",
    "details": [{ "field": "email", "message": "Invalid email format." }],
    "requestId": "..."
  }
}
```

Codes include: `VALIDATION_ERROR`, `AUTHENTICATION_ERROR`, `AUTHORIZATION_ERROR`, `NOT_FOUND`, `CONFLICT`, `BUSINESS_RULE_ERROR`, `RATE_LIMIT_EXCEEDED`, `INTERNAL_ERROR`, `INVALID_CREDENTIALS`, `TOKEN_REUSE_DETECTED`, `TOKEN_EXPIRED`.

## Authentication headers

```http
Authorization: Bearer <access_token>
```

Organization context for Operations resources is taken from the path (`/organizations/{organizationId}/...`), not a required header.

## Multi-organization access convention

Unauthorized access to another organization's resource returns **404** (resource existence is not revealed). Apply this consistently for facilities, assets, periods, activity records, attachments, and import jobs.

## Dates and decimals

- Date-time values: ISO 8601 UTC strings
- Date-only values: `YYYY-MM-DD`
- Quantities: decimal-safe serialization (`Decimal` / PostgreSQL `numeric`); do not use binary floating point for stored measurements

## Sorting whitelist (activity records)

Allowed `sortBy` values: `activityDate`, `createdAt`, `quantity`, `status`.

## Operations endpoint groups

- `/organizations/{organizationId}/facilities`
- `/organizations/{organizationId}/facilities/{facilityId}/production-lines`
- `/organizations/{organizationId}/production-lines/{productionLineId}`
- `/organizations/{organizationId}/equipment`
- `/organizations/{organizationId}/data-sources`
- `/organizations/{organizationId}/reporting-periods`
- `/organizations/{organizationId}/activity-records` (+ submit/approve/reject/correct/archive/revisions)
- `/organizations/{organizationId}/activity-records/{id}/attachments`
- `/organizations/{organizationId}/imports/activity-records`
- `/reference/units` and `/reference/activity-types` (writes: system admin)

## Multipart uploads

Attachment and CSV import endpoints accept `multipart/form-data` with a `file` field.

## Request IDs

- Client may send `X-Request-ID` (8–128 safe chars)
- Server echoes `X-Request-ID` on every response
- Invalid incoming IDs are replaced with a new UUID
