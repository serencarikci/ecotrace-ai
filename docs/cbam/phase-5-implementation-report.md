# EcoTrace AI CBAM Phase 5 Implementation Report

## 1. Result

**COMPLETED** — Phase 5 Minimal Calculation Engine meets the mandatory acceptance criteria.

Only explicit `MULTIPLY_ACTIVITY_BY_FACTOR` is supported. No guessed sector formulas, no automatic external factor import, no Excel/final CBAM report, no CN/shipment/certificate liability.

## 2. Phase 4B baseline

Phase 4B remains intact:

- reference sources / factor definitions / values / resolutions
- migration `0011`
- Faktörler UI
- primary/default precedence without emission math

## 3. Scope

**Included**

- `CbamCalculationDefinition` / `CbamCalculationRun` / `CbamCalculationResult`
- Decimal-safe multiply with intensity-unit validation
- Allocated quantity + purchased consumed quantity support
- Partial completion + explicit recalculation history
- SKDM **Hesaplama** tab

**Excluded**

- Full regulatory CBAM framework
- GWP / CO2→CO2e invent
- Automatic IPCC/DEFRA/EPA download
- Excel / final report / CN / shipment / evidence / financial obligation

## 4. Files changed

**Added**

- `apps/api/src/ecotrace/db/migrations/versions/0012_cbam_minimal_calculation.py`
- `apps/api/src/ecotrace/modules/cbam/application/calculation_math.py`
- `apps/api/src/ecotrace/modules/cbam/application/calculation_service.py`
- `apps/api/tests/unit/test_cbam_calculation.py`
- `apps/api/tests/integration/test_cbam_phase5_api.py`
- Docs: `phase-5-calculation.md`, `calculation-model.md`, `calculation-formulas.md`, `calculation-unit-rules.md`, `calculation-limitations.md`, this report

**Changed**

- CBAM models, catalogs (intensity units + kWh/MWh scale), module status, API router, conftest seed
- Frontend: `cbam-api.service.ts`, `period-detail.*`, `cbam-shell.*`
- Docs: `docs/cbam.md`, roadmap, api-boundaries, api-conventions, blocked-calculation-decisions, implementation-roadmap

## 5. Migration

`0012_cbam_minimal_calculation` after `0011_cbam_factor_resolution`.

Tables: definitions, runs, results. Seeds calculation definition metadata only (no numeric factors). Factor FKs resolved by definition code.

Verified: `0011` → `0012` → `0011` → `0012` → head `0012_cbam_minimal_calculation` (4 definitions).

## 6. Calculation definitions

Active metadata:

- `MULTIPLY_ACTIVITY_BY_GENERIC_EF`
- `MULTIPLY_ALLOCATION_BY_GENERIC_EF`
- `MULTIPLY_PURCHASED_BY_GENERIC_EF`
- `MULTIPLY_PURCHASED_BY_SUPPLIER_EMBEDDED`

Type: `MULTIPLY_ACTIVITY_BY_FACTOR` / `formula_version=multiply-activity-by-factor-v1`.

## 7. Calculation run model

Statuses: DRAFT / RUNNING / COMPLETED / PARTIALLY_COMPLETED / FAILED / ARCHIVED.  
Summary counts: calculated / blocked / invalid / primary / default.

## 8. Calculation result model

Persists source quantity/unit, factor value/unit, result value/unit, resolution id, optional allocation id, fingerprint, `is_current` supersession.

## 9. Formula support

Only `result = quantity × factor` when factor unit is an explicit intensity and denominator matches source unit (with documented scale pairs).

## 10. Unit handling

Allow-listed intensity units; CO2 vs CO2e preserved; no density/calorific/GWP invent.

## 11. Allocation integration

`ALLOCATION_RESULT` resolutions use `allocated_quantity`.

## 12. Factor-resolution integration

Calculation requires existing `RESOLVED_PRIMARY` / `RESOLVED_DEFAULT`. No silent auto-resolve.

## 13. Partial completion

Per-record failures continue; run becomes `PARTIALLY_COMPLETED` when mixed outcomes.

## 14. Recalculation

Explicit `/recalculate` creates a new current result and supersedes the previous one.

## 15. API

Under `/api/v1/cbam/organizations/{organizationId}`:

- GET calculation-definitions
- POST/GET binding calculation-runs
- POST execute
- GET results / GET result / POST recalculate

Permissions: view read; configure mutate/execute.

## 16. Frontend

**Hesaplama** tab: run/execute, summary (“Hesaplama Sonuç Özeti”), optional same-unit “Toplam Hesaplanan Değer”, blocked reasons, primary/default factor source labels. No Excel/final report buttons.

## 17. Audit

`cbam.calculation_run.created|executed|completed`, `cbam.calculation_result.created|blocked|recalculated`.

## 18. Tenant isolation

Organization scoping + CBAM 404 non-disclosure conventions retained.

## 19. Tests

Unit: multiply examples (100×0.5=50; 20×0.4=8), incompatible units, ambiguous block, allocation, purchased consumed, recalculation history, no-guessing.  
Integration: view denied execute, configure execute, recalculate.  
Frontend: Hesaplama tab + no export/financial affordances.

## 20. Exact results

| Check | Result |
|-------|--------|
| pytest CBAM suite | **84 passed** |
| ruff (CBAM + Phase 5 paths) | All checks passed |
| mypy cbam + router | Success: no issues found in 30 source files |
| ng test CBAM specs | **TOTAL: 13 SUCCESS** |
| ng build production | Success (`dist/web`, exit 0) |
| Alembic 0011↔0012 | Success; definitions=4 |

## 21. Migration verification

Upgrade/downgrade/upgrade of `0012` verified on `ecotrace_test` after preparing factor catalog at `0011`.

## 22. No guessed factor

Confirmed: migration/services do not seed IPCC/DEFRA/EPA numeric factors. Tests use synthetic fixtures only.

## 23. No guessed sector formula

Only `MULTIPLY_ACTIVITY_BY_FACTOR` is implemented; unknown formula versions → `UNSUPPORTED_FORMULA`.

## 24. No Excel/report generation

No openpyxl/xlsxwriter/report endpoints or UI export actions in Phase 5.

## 25. Remaining blocked decisions

See `blocked-calculation-decisions.md` (GWP, sector formulas, Excel mapping, certificate/financial liability, authoritative datasets, etc.).

## 26. Known limitations

- Only intensity-style factor units participate in multiply
- Same-unit technical sum is optional and not a regulatory total
- Factors must be resolved before calculation
- Unallocated activity calculation is an explicit execute flag

## 27. Git status

Branch: `cbam-foundation`  
**No** Git stage/commit/push/merge/rebase/branch operations were performed for this phase.
