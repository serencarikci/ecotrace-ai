# EcoTrace AI CBAM Phase 4B Implementation Report

## 1. Result

**COMPLETED** — Phase 4B Emission Factor & Primary/Default Data Resolution Foundation meets the mandatory acceptance criteria.

Selection only. No emission multiplication, CO2/CO2e totals, automatic IPCC/DEFRA/EPA import, Excel, report generation, CN, shipment, or evidence upload.

## 2. Phase 4A baseline

Phase 4A remains intact:

- quantity allocation (`DIRECT_ASSIGNMENT`, `PRODUCTION_QUANTITY_RATIO`, `MANUAL_RATIO`)
- migrations `0008` / `0009` / `0010`
- SKDM tabs: Üretim / Faaliyet / Satın Alınan Girdiler / Alokasyon
- no emission calculation in allocation math

## 3. Scope

**Included**

- `CbamReferenceSource`, `CbamFactorDefinition`, `CbamFactorValue`, `CbamFactorResolution`
- reuse of existing `CbamActivityProperty` for primary property values
- deterministic precedence: RECORD_PRIMARY → ORG_PRIMARY → DEFAULT_REFERENCE → UNRESOLVED
- equal-rank ties → `AMBIGUOUS` (no silent pick)
- validity + unit compatibility checks
- explicit re-resolution with supersession history
- SKDM period tab **Faktörler**

**Excluded (fail-closed)**

- `activity × factor` / `allocated_quantity × factor`
- CO2 / CO2e / embedded-emission totals
- invented numerical factors
- automatic external factor download/import/scrape
- Excel / CBAM report / CN / shipment / evidence upload

## 4. Files changed (Phase 4B focus)

**Added**

- `apps/api/src/ecotrace/db/migrations/versions/0011_cbam_factor_resolution.py`
- `apps/api/src/ecotrace/modules/cbam/application/factor_catalog_seed.py`
- `apps/api/src/ecotrace/modules/cbam/application/reference_source_service.py`
- `apps/api/src/ecotrace/modules/cbam/application/factor_catalog_service.py`
- `apps/api/src/ecotrace/modules/cbam/application/factor_resolution_service.py`
- `apps/api/tests/unit/test_cbam_factor_resolution.py`
- `apps/api/tests/integration/test_cbam_phase4b_api.py`
- `docs/cbam/phase-4b-factor-resolution.md`
- `docs/cbam/factor-model.md`
- `docs/cbam/primary-data-precedence.md`
- `docs/cbam/reference-source-model.md`
- `docs/cbam/factor-resolution-rules.md`
- `docs/cbam/factor-resolution-limitations.md`
- `docs/cbam/phase-4b-implementation-report.md` (this file)

**Changed**

- `apps/api/src/ecotrace/modules/cbam/infrastructure/models.py`
- `apps/api/src/ecotrace/api/v1/cbam.py`
- `apps/api/src/ecotrace/modules/cbam/application/catalogs.py` (property units + exact scale compatibility)
- `apps/api/src/ecotrace/modules/cbam/application/activity_record_service.py` (property add)
- `apps/api/src/ecotrace/modules/cbam/application/module_status_service.py` → `factor_resolution_foundation_available`
- `apps/api/tests/conftest.py` (platform catalog seed)
- `apps/api/tests/unit/test_cbam_data_collection.py` (keyword scan adjusted for metadata-only source names)
- Frontend: `cbam-api.service.ts`, `period-detail.component.*`, related specs/shell status
- Docs: `docs/cbam.md`, `roadmap.md`, `implementation-roadmap.md`, `api-boundaries.md`, `blocked-calculation-decisions.md`, `docs/api-conventions.md`

## 5. Migration

`0011_cbam_factor_resolution` (after `0010_cbam_allocation_foundation`):

- `cbam_reference_sources`
- `cbam_factor_definitions`
- `cbam_factor_values`
- `cbam_factor_resolutions`

Seeds **metadata only**:

- sources: IPCC, DEFRA, EPA, PRIMARY_MEASUREMENT, SUPPLIER, MANUAL_APPROVED_REFERENCE
- definitions: `NET_CALORIFIC_VALUE`, `GENERIC_EMISSION_FACTOR`, `SUPPLIER_EMBEDDED_EMISSION`
- **no numerical factor values**

Verified on `ecotrace_test`:

1. `create_all` baseline + drop Phase 4B tables + stamp `0010`
2. `alembic upgrade` → `0011_cbam_factor_resolution`
3. `alembic downgrade` → `0010_cbam_allocation_foundation`
4. `alembic upgrade` → `0011_cbam_factor_resolution`
5. Result: `sources: 6`, `definitions: 3`

## 6. Reference-source domain

Platform (`organization_id` null) and organization-scoped sources.  
Source types: STANDARD_REFERENCE / PRIMARY_MEASUREMENT / SUPPLIER_DECLARATION / MANUAL_APPROVED / OTHER.  
Statuses: ACTIVE / INACTIVE / ARCHIVED.  
Metadata only — no scraping, no evidence storage.

## 7. Factor-definition domain

Semantic catalog for properties/factors that may later participate in calculation.  
Categories include ACTIVITY_PROPERTY, EMISSION_FACTOR, EMBEDDED_EMISSION_FACTOR, ENERGY_FACTOR, OTHER.  
No invented numerics.

## 8. Factor-value domain

Explicit approved values with `data_source_type` PRIMARY | DEFAULT_REFERENCE.  
Statuses DRAFT / ACTIVE / ARCHIVED; `row_version`; validity window; org scoping.  
Activation requires source metadata.

## 9. Primary-value reuse

`CbamActivityProperty` remains the record of measured/supplier primary properties.  
Resolution reads properties in place — values are not copied into factor tables for convenience.  
Purchased-input supplier embedded fields resolve as PRIMARY when present.

## 10. Resolution policy

Initial precedence (deterministic):

1. ACTIVE compatible PRIMARY on the source record
2. ACTIVE compatible organization-level PRIMARY factor value
3. ACTIVE compatible DEFAULT_REFERENCE factor value
4. UNRESOLVED

Equal-rank multiple candidates → AMBIGUOUS.  
Statuses also include INCOMPATIBLE_UNIT, OUTSIDE_VALIDITY, BLOCKED.  
`resolver_version = factor-resolution-v1`.

## 11. Resolution history

Each resolve/re-resolve creates a new `CbamFactorResolution`.  
Prior current rows are superseded (`superseded_at` / `is_current`).  
Historical selection is preserved.

## 12. APIs

Under `/api/v1/cbam/organizations/{organizationId}`:

- reference sources list/get/create/patch/archive
- factor definitions list/get; values list/create/get/patch/activate/archive
- activity property POST
- resolve for activity / purchased-input / allocation-result by `factorDefinitionCode`
- get resolution; list binding resolutions

Permissions: `cbam:view` read; `cbam:configure` mutate/resolve.

## 13. Frontend

SKDM period detail tab **Faktörler**:

- resolution table (Kaynak, Faaliyet/Girdi, Faktör/Özellik, Veri Kaynağı, Çözüm Durumu, Seçilen Değer, Birim, Referans, İşlem)
- Turkish status labels
- Çözümle / Yeniden Çözümle
- primary property form with help text
- “Tanımlı Varsayılan Referans” candidate list (not “Resmi Faktör”)
- no CO2/CO2e / emission result display

## 14. Audit

- `cbam.reference_source.created|updated|archived`
- `cbam.factor_value.created|updated|activated|archived`
- `cbam.factor_resolution.resolved|reresolved`

Resolution audit includes source record, factor definition, status, selected source type, selected property/factor id.

## 15. Concurrency

Mutable factor values use `row_version`; stale mutation → 409.  
Resolution reads current transactional state without long-held locks.

## 16. Tenant isolation

Organization scope enforced for factor values, resolutions, activity properties, purchased inputs, allocation results.  
Platform reference metadata intentionally global.  
Cross-tenant access follows CBAM 404 non-disclosure.

## 17. Tests

Coverage includes:

- primary → default → ambiguous scenario (DIESEL NCV 35.8 vs 36.0)
- validity (expired/future not selected)
- unit incompatibility
- purchased-input primary embedded resolution; no fabrication
- allocation-result resolution without multiplication; re-resolve history
- no-calc architecture keyword/pattern checks
- API integration + frontend Faktörler tab

## 18. Exact test results

| Check | Result |
|-------|--------|
| `pytest` CBAM suite (`tests/unit/test_cbam_*.py` + `tests/integration/test_cbam*.py`) | **76 passed** |
| `ruff check` (CBAM + Phase 4B paths) | All checks passed |
| `mypy` `modules/cbam` + `api/v1/cbam.py` | Success: no issues found in 28 source files |
| `ng test` `--include='**/cbam/**/*.spec.ts'` | **TOTAL: 13 SUCCESS** |
| `ng build --configuration=production` | Success (`dist/web`, exit 0) |
| Alembic `0010` → `0011` → `0010` → `0011` | Success; head `0011_cbam_factor_resolution` |

## 19. Migration results

Upgrade/downgrade/upgrade of `0011` verified on `ecotrace_test` after stamping at `0010` with Phase 4B tables absent. Prior CBAM tables preserved via additive migration.

## 20. No emission calculation

Confirmed: Phase 4B services persist selection metadata only. No `activity_quantity * emission_factor`, no allocated-quantity multiplication into emissions, no CO2e conversion helpers.

## 21. No CO2 / CO2e fields

No Phase 4B fields such as `calculated_emission`, `co2`, `co2e`, `total_emission`, `direct_emission_total`. Module status calculation/reporting flags remain false.

## 22. No automatic external factor lookup

No IPCC/DEFRA/EPA website fetch, spreadsheet scrape, or public factor API. Seeded rows are source/definition labels only.

## 23. No Excel / report

No openpyxl/xlsxwriter/report generation paths added in Phase 4B.

## 24. Remaining blocked decisions

See `blocked-calculation-decisions.md` — still unresolved:

- authoritative default factor source per activity + approved dataset versions
- exact IPCC/DEFRA/EPA precedence for all parameters
- geographic electricity factors, oxidation factors, GWP / CO2 vs CO2e
- supplier evidence requirements, sector formulas, embedded fallback rules
- Excel mapping, CN/shipment/report activation

## 25. Known limitations

- Initial precedence policy is intentionally simple (not a generic rules engine)
- Unit conversions limited to exact same-dimension scale pairs already supported (e.g. MJ↔GJ, kg↔t)
- Overlapping equal-rank candidates fail closed as AMBIGUOUS
- Platform source names are not claims of global regulatory authority
- Emission calculation engine remains a later phase after factor semantics are confirmed

## 26. Git status

Branch: `cbam-foundation`  
**No** Git stage/commit/push/merge/rebase/branch operations were performed for this phase.

Working tree contains Phase 2–4B uncommitted changes (foundation + data collection + allocation + factor resolution).
