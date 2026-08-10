# EcoTrace AI CBAM Phase 4A Implementation Report

## 1. Result

**COMPLETED** — Phase 4A Allocation Foundation meets the mandatory acceptance criteria.

Quantity allocation only. No emission-factor resolution, CO2e calculation, Excel/report generation, CN, or shipment logic.

## 2. Phase 3 baseline

Phase 3 remains intact:

- production / activity / purchased-input capture
- migrations `0008` / `0009`
- PRIMARY / DEFAULT_REFERENCE / UNKNOWN source typing
- purchased ≠ consumed
- SKDM tabs: Üretim / Faaliyet / Satın Alınan Girdiler

## 3. Scope

**Included**

- `CbamAllocationRule` + `CbamAllocationResult`
- Methods: `DIRECT_ASSIGNMENT`, `PRODUCTION_QUANTITY_RATIO`, `MANUAL_RATIO`
- Allocate activity + purchased-input quantities
- Explicit recalculation with `is_current` / `superseded_at`
- Organization-scoped APIs + Alokasyon UI tab
- Decimal-safe `allocated_quantity = source_quantity * allocation_ratio`

**Excluded (fail-closed)**

- Emission factors / IPCC / DEFRA / EPA
- CO2 / CO2e / embedded-emission calculation
- Excel / CBAM report generation
- CN / AGC / shipment / customer-export allocation
- Inventory valuation (FIFO/LIFO/WAVG)
- Silent mutation of retained historical results

## 4. Files added/changed (Phase 4A focus)

**Added**

- `apps/api/src/ecotrace/db/migrations/versions/0010_cbam_allocation_foundation.py`
- `apps/api/src/ecotrace/modules/cbam/application/allocation_math.py`
- `apps/api/src/ecotrace/modules/cbam/application/allocation_rule_service.py`
- `apps/api/src/ecotrace/modules/cbam/application/allocation_service.py`
- `apps/api/tests/unit/test_cbam_allocation.py`
- `apps/api/tests/integration/test_cbam_phase4a_api.py`
- `docs/cbam/phase-4a-allocation.md`
- `docs/cbam/allocation-model.md`
- `docs/cbam/allocation-methods.md`
- `docs/cbam/allocation-limitations.md`
- `docs/cbam/phase-4a-implementation-report.md` (this file)

**Changed**

- `apps/api/src/ecotrace/modules/cbam/infrastructure/models.py` (allocation models)
- `apps/api/src/ecotrace/api/v1/cbam.py` (allocation endpoints)
- `apps/api/src/ecotrace/modules/cbam/application/module_status_service.py`
- `apps/web/src/app/features/cbam/cbam-api.service.ts`
- `apps/web/src/app/features/cbam/period-detail.component.*`
- `apps/web/src/app/features/cbam/cbam-pages.scss`
- `apps/web/src/app/features/cbam/cbam-shell.component.spec.ts`
- Docs: `docs/cbam.md`, `docs/cbam/roadmap.md`, `docs/cbam/implementation-roadmap.md`, `docs/cbam/api-boundaries.md`, `docs/cbam/blocked-allocation-decisions.md`, `docs/api-conventions.md`

## 5. Migration

`0010_cbam_allocation_foundation` (after `0009_cbam_data_collection`):

- `cbam_allocation_rules`
- `cbam_allocation_results`
- unique partial index: one ACTIVE rule per scope (COALESCE null product)
- NUMERIC ratios/quantities; `row_version` on rules; audit user FKs

Verified:

1. stamp/prep at `0009`
2. `alembic upgrade head` → `0010_cbam_allocation_foundation`
3. `alembic downgrade 0009_cbam_data_collection`
4. `alembic upgrade head` → `0010_cbam_allocation_foundation (head)`

## 6. Allocation rule domain

Statuses: `DRAFT` / `ACTIVE` / `ARCHIVED`  
Scope: org + binding + installation + optional product profile  
Only DRAFT is PATCH-mutable; ACTIVE rules with results are not silently rewritten.

## 7. Allocation result domain

Persists source quantity/unit, ratio, allocated quantity/unit, method, `calculation_version=allocation-quantity-v1`.  
Supersession via `is_current` + `superseded_at`. Source records are never overwritten.

## 8. Supported methods

| Method | Behavior |
|--------|----------|
| DIRECT_ASSIGNMENT | ratio = 1.0 (explicit only) |
| PRODUCTION_QUANTITY_RATIO | numerator/denominator production records; exact unit match; snapshot quantities |
| MANUAL_RATIO | `[0,1]` + required rationale + source reference |

## 9. Application services

- `allocation_rule_service`: create/update draft/validate/activate/archive/list/get
- `allocation_service`: allocate activity/purchased, recalculate, list/get results
- `allocation_math`: Decimal-safe ratio/quantity helpers

## 10. APIs

Under `/api/v1/cbam/organizations/{organizationId}`:

- binding-scoped rule/result lists + create rule
- rule get/patch/activate/archive
- allocate activity / purchased input
- recalculate + get result

Permissions: `cbam:view` GET; `cbam:configure` mutations.

## 11. Frontend

SKDM period detail tab **Alokasyon**:

- rule list/create with method-dependent fields
- production-ratio preview (100/500 → 20%)
- manual rationale required in UI
- results table (no CO2e / factors)

## 12. Audit

- `cbam.allocation_rule.created|updated|activated|archived`
- `cbam.allocation.executed|recalculated`

Metadata includes rule id, source id, method, ratio, source/allocated quantities.

## 13. Concurrency

Stale `rowVersion` → `409 ConflictError`.

## 14. Tenant isolation

All reads/writes scoped by `organization_id`; cross-org access returns 403/404.

## 15. Tests executed

- CBAM Phase 1–4A pytest suite
- ruff (Phase 4A paths)
- mypy (cbam package + router)
- Angular CBAM specs
- Angular production build
- Alembic upgrade/downgrade/upgrade for `0010`

## 16. Exact test results

| Check | Result |
|-------|--------|
| `pytest` CBAM suite (unit+integration Phase 1–4A) | **69 passed** |
| `ruff check` (Phase 4A paths) | All checks passed |
| `mypy` cbam + `api/v1/cbam.py` | Success: no issues found in 24 source files |
| `ng test` `--include='src/app/features/cbam/**/*.spec.ts'` | **TOTAL: 13 SUCCESS** |
| `ng build --configuration=production` | Success (`dist/web`) |
| Alembic 0009→0010→0009→0010 | Success; current `0010_cbam_allocation_foundation (head)` |

Technical example covered by tests: 100 t / 500 t → ratio 0.2; 100 MWh × 0.2 → 20 MWh.

## 17. Migration verification

Upgrade/downgrade/upgrade of `0010` verified on `ecotrace_test` after stamping at `0009` with allocation tables absent.

## 18. Emission calculation absent

Confirmed: allocation math only multiplies `source_quantity * allocation_ratio`. No CO2/CO2e computation paths added.

## 19. Emission-factor resolution absent

No IPCC/DEFRA/EPA/APCC factor lookup in allocation services. Architecture forbidden-import scan remains clean.

## 20. Excel/report generation absent

No openpyxl/xlsxwriter/report generation in Phase 4A paths. Module status `calculationImplemented` / `reportingImplemented` remain `false`.

## 21. Remaining blocked decisions

Still blocked (see `blocked-allocation-decisions.md`):

- customer/export allocation
- shipment scope
- multi-stage production
- inventory valuation methods
- sector-specific / regulatory-specific allocation alternatives
- energy-content / economic / revenue allocation

## 22. Known limitations

- Production ratio requires exact matching units (no kg↔t conversion)
- Purchased allocation requires explicit `consumed_quantity` (fail closed)
- Only one ACTIVE rule per scope
- Installation-level rules allowed when product profile is null
- This is technical quantity allocation, not a regulatory CBAM calculation claim

## 23. Git status

Branch: `cbam-foundation`  
No Git stage/commit/push/merge/rebase/branch operations were performed for this phase.

Working tree contains Phase 2–4A uncommitted changes (foundation + data collection + allocation).
