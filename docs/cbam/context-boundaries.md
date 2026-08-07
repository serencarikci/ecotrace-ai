# CBAM Context Boundaries and Integrations

## Convention conflicts

| Topic | Current EcoTrace convention | CBAM proposal | Resolution |
|-------|----------------------------|---------------|------------|
| API nesting | `/api/v1/organizations/{organizationId}/resource` | `/api/v1/cbam/...` | **Deliberate bounded-context-first exception:** `/api/v1/cbam/organizations/{organizationId}/...`. Does not change non-CBAM endpoints. Documented in [api-conventions.md](../api-conventions.md). |
| AuthZ | path org + membership | Same | `organizationId` never trusted without `ensure_org_access` / CBAM permission helpers; cross-tenant → 404 |
| JSON / pagination / errors | camelCase, Page, standard error envelope | Same | Follow api-conventions (not RFC7807 Problem Details) |
| Module layout | `modules/<name>/{application,infrastructure}` | `modules/cbam/...` | Match existing pattern |
| Schemas | `CamelModel` in services | Same | |
| Repositories | Session in application services | Same | No new UoW framework |
| Calculation reuse | LCA calls `compute_emission_result` | **Forbidden** for CBAM SEE | Anti-corruption rules below |
| Facilities/products | Shared columns | CBAM profiles/versions | Composition ADR |
| Evidence storage | `activity_data.attachment_service` | CBAM-owned or future shared port | **No shared port today** (D-042) |
| Idempotency-Key | Not a general platform feature | New CBAM capability | D-040 |

## Anti-corruption rules (testable — F-14)

Inside `modules/cbam`:

1. Importing ORM models from `carbon_accounting`, `carbon_inventory`, `lifecycle_assessment`, or `product_carbon_footprint` is **forbidden**.
2. Importing their calculation engines / entrypoints is **forbidden**.
3. Writing directly to tables owned by other modules is **forbidden**.
4. Cross-module access must use approved application-service ports, query ports, or stable shared contracts.
5. Source values required for calculation must be **copied** into immutable CBAM snapshots.
6. Importing `activity_data` ORM models or application internals for evidence is **forbidden** (use D-042 choice).
7. Allowed shared imports: Decimal helpers, `reference_data` unit conversion, auth/org access, audit writer, exception types, CamelModel/Page.

**Future architecture test (not implemented in this documentation task):** fail CI if `modules/cbam` imports forbidden packages/modules listed above.

## Integration matrix

| Module | Data owner | Read | Write | Direct FK OK? | Port/service required? | Snapshot required? | Locked CBAM affected by source change? |
|--------|------------|------|-------|---------------|------------------------|--------------------|----------------------------------------|
| identity | identity | user/role | no | actor UUID refs | `org_access` | actor id in audit/approval | No |
| organizations | organizations | org | no | `organization_id` FK | `ensure_org_access` | org id | No |
| facilities | facilities | facility master | no | `facility_id` on profile | validate-facility service | facility attrs in runs | No |
| operational_assets | operational_assets | optional | no | optional nullable FKs | validate | optional | No |
| activity_data | activity_data | optional import source | **no** into corporate table | no FK into CBAM calc | import adapter port (copy only) | copied into `CbamActivityRecord` | No |
| data_imports | data_imports | pattern only | CBAM own import jobs | no shared import_jobs required | copy patterns; add formula-injection policy | file + row snapshots | No |
| emission_factors | emission_factors | optional candidates | no | no live FK in approved run | factor read port | **always** | No |
| reporting_periods | reporting_periods | period dates/code | **no CBAM state on generic row** | `reporting_period_id` on binding | period read/validate | period code/dates | **No** — CBAM lock independent (D-031) |
| products | products | product master | no CN on product | `product_id` on profile versions | validate product | classification snapshot | No |
| materials / suppliers | respective | master | no | optional FKs | validate | when used | No |
| carbon_* / LCA / PCF | those modules | **none for SEE** | none | none | none | n/a | n/a |
| reporting (analytics) | reporting | none as CBAM report | CBAM owns reports | none | none | report artifacts | n/a |
| audit | shared | append-only | `write_audit_log` | none | shared helper | metadata | n/a |
| units | reference_data | conversion | no | none as live truth | conversion helpers | **D-037** pin conversion factors | No |

## CBAM lock interaction (F-01)

- Binding owns CBAM lock.
- Generic RP lock/unlock must not auto-lock/unlock CBAM.
- Optional guard only; ops preference D-031.

## Snapshot policy for locked/approved results

When a run reaches `calculated` (and when referenced by approved/locked period per D-030):

- Pin rule pack, factor set, CN/AGC catalog, product-profile version, route/process/boundary, activity/consumption/precursor/shipment value snapshots, allocation applications, unit conversion factors, precision context.
- Later master-data edits must not alter that run.
- Recalculation creates a new run.
