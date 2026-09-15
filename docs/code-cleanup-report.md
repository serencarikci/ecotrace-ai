# Code Cleanup Report — CBAM/SKDM MVP

Date: 2026-08-09  
Classification preserved: `READY_FOR_DOMAIN_VALIDATION`  
Scope: strict cleanup/simplification only (no feature work, no API/DB semantic changes, no Git operations).

## Inventory method

1. Static reference scan (AST + repository-wide symbol counts) over `apps/api/src/ecotrace/modules/cbam` and `apps/web/src/app/features/cbam`.
2. Confirm call/DI/route registration before delete.
3. Classify candidates: `SAFE_TO_DELETE` / `SAFE_TO_MERGE` / `KEEP` / `NEEDS_REVIEW`.
4. Apply only proven safe deletes/merges.
5. Re-run quality gates and Phase 7 regression.

## Changes applied

### Files deleted

None. No abandoned modules, empty folders, or placeholder-only packages were found under CBAM.

### Files merged / edited (no new files except this report)

| File | Change |
|------|--------|
| `apps/api/src/ecotrace/modules/cbam/application/export_template_service.py` | Removed unused `ExportMappingResponse`; removed unwired `archive_export_template`; dropped unused imports (`require_cbam_configure`, `write_audit_log`) |
| `apps/api/src/ecotrace/modules/cbam/application/export_storage.py` | Removed unused `MAX_TEMPLATE_BYTES` |
| `apps/api/src/ecotrace/modules/cbam/application/allocation_rule_service.py` | Removed unwired `preview_production_ratio` |
| `apps/api/src/ecotrace/modules/cbam/application/calculation_service.py` | Removed no-op `if formula_version ...: pass` dead branch |
| `apps/api/src/ecotrace/modules/cbam/application/period_binding_service.py` | Merged duplicate status frozensets + `_get_row` into `collection_guards` |
| `apps/api/src/ecotrace/modules/cbam/application/catalogs.py` | Added canonical `require_unit` |
| `apps/api/src/ecotrace/modules/cbam/application/production_record_service.py` | Use `require_unit` (removed local duplicate) |
| `apps/api/src/ecotrace/modules/cbam/application/purchased_input_service.py` | Use `require_unit` (removed local duplicate) |
| `apps/api/src/ecotrace/modules/cbam/application/activity_record_service.py` | Use `require_unit` |
| `apps/api/src/ecotrace/modules/cbam/__init__.py` | Replaced obsolete Phase-1-only module docstring |
| `apps/web/src/app/features/cbam/cbam-api.service.ts` | Removed unused `listCalculationDefinitions` + `CbamCalculationDefinition` |

### Folders deleted

None (no empty / `.gitkeep`-only / placeholder CBAM folders).

### Classes removed

| Class | Reason | Replacement |
|-------|--------|-------------|
| `ExportMappingResponse` | Defined, never referenced by routes/services/tests | N/A (internal mapping rows remain ORM entities) |
| `CbamCalculationDefinition` (frontend interface) | Only used by unused frontend wrapper | Backend calculation-definition API unchanged |

### Methods / symbols removed

| Symbol | Reason |
|--------|--------|
| `archive_export_template` | No API route, no callers, no tests |
| `preview_production_ratio` | No API route, no callers, no tests |
| `MAX_TEMPLATE_BYTES` | Constant never read |
| Dead `pass` branch in `execute_calculation_run` | No behavior; unsupported formula versions already handled later |
| `listCalculationDefinitions` (frontend) | Never called by components/specs |
| `period_binding_service._get_row` | Exact duplicate of `get_binding_for_org` |
| `PHASE2_WRITABLE_STATUSES` / `MUTATION_BLOCKED_STATUSES` | Exact duplicates of collection-guard constants |
| Local `_validate_unit` helpers (production/purchased) | Exact duplicate logic → `catalogs.require_unit` |

### Duplicate logic consolidated

1. **Period binding tenant lookup** → canonical `collection_guards.get_binding_for_org`.
2. **Writable / mutation-blocked binding statuses** → canonical `WRITABLE_BINDING_STATUSES` / `MUTATION_BLOCKED_BINDING_STATUSES`.
3. **Catalog unit validation** → canonical `catalogs.require_unit` used by production, purchased-input, and activity services.

### Unused imports removed

- `require_cbam_configure`, `write_audit_log` from `export_template_service.py` (after dead method removal).
- `NotFoundError` unused after period-binding merge (period binding now relies on guard errors).
- Frontend calculation-definition types/method imports eliminated with the unused wrapper.

### Unused dependencies removed

None. Verified still referenced:

- `openpyxl` — workbook export/tests
- `segno` — QR / non-CBAM features
- `httpx` — TestClient / HTTP stack

No npm dependency removals (all used by Angular toolchain or app code).

## TODO / placeholder findings

| Location | Finding | Classification |
|----------|---------|----------------|
| CBAM application/infrastructure | No `TODO` / `FIXME` / `HACK` / `PLACEHOLDER` / `NotImplemented` | — |
| `CalculationRunCreate` empty body (`pass`) | Intentional empty POST schema | **KEEP** |
| BLOCKED official CBAM mapping docs / flags | Intentional domain scope | **KEEP** |
| Status vocabulary tuples in `models.py` (`PERIOD_BINDING_STATUSES`, etc.) | Unused as runtime checks but document persisted status sets | **KEEP** (compatibility documentation) |

## Items intentionally kept

### Architecture-sensitive (do not remove)

- Ports/adapters: `FacilityRef`, `ReportingPeriodRef`, `ProductRef` + adapters
- `architecture_boundary.py` and architecture tests
- Tenant guards, `check_row_version`, audit writes
- Fail-closed factor resolution / calculation blocking paths
- Decimal-safe allocation & calculation math modules
- Export traceability (manifest, checksums, readiness)
- Full Alembic history `0008`–`0013` and Phase implementation reports
- Distinct VersionRequest DTOs even when fields look similar (domain language)

### Near-duplicates kept on purpose

- Service-local `_get_row` helpers for installation/product/activity/production rows (entity-specific, not identical to shared binding/installation guards in all call sites)
- `_reject_if_locked` vs `require_writable_binding` (different error messages / phase semantics)
- Frontend `CbamApiService` wrappers for live backend endpoints even when some UI screens do not yet call every method (except the one proven unused calculation-definitions wrapper)

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| CBAM Python files | 36 | 36 |
| CBAM Python LOC | 9968 | 9854 (−114) |
| CBAM frontend files | 18 | 18 |
| CBAM frontend LOC (ts/html/scss) | 4575 | 4548 (−27) |
| CBAM pytest collected | 99 | 99 |
| Angular CBAM specs executed | 13 | 13 |

LOC measured with line counts over `apps/api/src/ecotrace/modules/cbam/**/*.py` and `apps/web/src/app/features/cbam/**/*.{ts,html,scss}`.

## Quality gates (executed)

| Gate | Result |
|------|--------|
| Ruff (`src/ecotrace/modules/cbam` + CBAM tests) | PASS |
| mypy (`src/ecotrace/modules/cbam`, 36 files) | PASS |
| CBAM pytest (`pytest -k cbam`) | **99 passed** |
| Phase 7 E2E (`test_cbam_phase7_e2e.py`) | **7 passed** |
| Angular CBAM tests | **13 SUCCESS** |
| Angular production build | PASS (`dist/web`) |
| Alembic head | `0013_cbam_excel_export` |
| Alembic clean upgrade (empty DB → head) | PASS |
| Alembic `0013 → 0012 → 0013` | PASS |

## Regression (Phase 7)

Positive workflow assertions unchanged:

- allocation ratio `0.200000000000`
- allocated quantity `20.00000000`
- factor `0.40000000` tCO2e/MWh (`RESOLVED_DEFAULT`)
- calculation result `8.00000000` tCO2e
- workbook cells: allocated `20.0`, factor `0.4`, result `8.0`
- formula-injection neutralization preserved
- manifest + artifact checksum + audit actions present
- official mapping remains blocked

Negative scenarios unchanged:

- `UNRESOLVED`
- `AMBIGUOUS`
- `INCOMPATIBLE_UNIT`
- cross-tenant `404`
- stale `409`
- missing consumed quantity rejected

## Known remaining cleanup opportunities (intentionally deferred)

1. Broader non-CBAM frontend unused imports (e.g. Ops `JsonPipe` / `RouterLink` compiler warnings) — outside CBAM MVP cleanup risk envelope.
2. Possible further consolidation of entity `_get_row` helpers — deferred to avoid weakening explicit service boundaries.
3. Unused status vocabulary tuples in ORM module — kept as persisted-status documentation rather than deleted.
4. Product-profile UI still API-only (no dedicated Angular screens) — not dead backend code; keep.

## Git

No Git stage/commit/push/merge/rebase/branch operations were performed during this cleanup.
