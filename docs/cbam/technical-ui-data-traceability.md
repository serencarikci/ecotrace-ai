# Technical UI → Data Traceability (CBAM / SKDM)

**Audience:** developers, architects, reviewers  
**Rule:** names below are taken from Angular components, `cbam-api.service.ts`, `api/v1/cbam.py`, and `modules/cbam/infrastructure/models.py`.  
**Do not treat** `docs/cbam/frontend-feature-map.md` as route truth — it is outdated proposal text.  
**Schema head:** `0032_cbam_prec_audit`. **Official SEE:** implemented (not blocked); LibreOffice required on API host — default Docker API image may omit it. **Present:** PEE V2, precursors, DEA/IEA, Official Excel UI.

### Authoritative inventories

The **acceptance-complete** field / action / table / API inventories live under [`docs/cbam/user-guide/inventories/`](user-guide/inventories/) and supersede the selected-row tables in this document for exhaustive coverage:

| Inventory | Authoritative files |
|-----------|---------------------|
| Fields (419) | [`fields.csv`](user-guide/inventories/fields.csv) · [`fields.json`](user-guide/inventories/fields.json) · index [`fields.md`](user-guide/inventories/fields.md) |
| Actions (148) | [`actions.csv`](user-guide/inventories/actions.csv) · [`actions.json`](user-guide/inventories/actions.json) · index [`actions.md`](user-guide/inventories/actions.md) |
| Tables (53 active) | [`table-dictionary.md`](user-guide/inventories/table-dictionary.md) · [`tables.json`](user-guide/inventories/tables.json) |
| Backend-only APIs (56) | [`api-backend-only-justified.md`](user-guide/inventories/api-backend-only-justified.md) · [`api-endpoint-categories.json`](user-guide/inventories/api-endpoint-categories.json) · [`api-reconciliation.md`](user-guide/inventories/api-reconciliation.md) |
| Counts | [`inventory-summary.json`](user-guide/inventories/inventory-summary.json) · field delta [`discovery-count-change.md`](user-guide/inventories/discovery-count-change.md) |

CSV/JSON are machine-authoritative; Markdown indexes are human-readable views. Sections below remain a concise critical-path overview only.

Base API prefix: `/api/v1` + `/organizations/{organization_id}/…` (client builds `orgBase()`).

## 1. Screen inventory (reachable)

| Screen | Route / parent | Angular component | Permission | Status |
|--------|----------------|-------------------|------------|--------|
| SKDM shell | `/app/cbam` | `CbamShellComponent` | `cbam:view` | Reachable |
| Installations list | `/app/cbam/installations` | `CbamInstallationListComponent` | view; configure for create | Reachable |
| Installation create | `/app/cbam/installations/new` | `CbamInstallationFormComponent` | configure | Reachable |
| Installation detail | `/app/cbam/installations/:installationId` | `CbamInstallationDetailComponent` | view/configure | Reachable |
| Periods list | `/app/cbam/periods` | `CbamPeriodListComponent` | view/configure | Reachable |
| Period detail hub | `/app/cbam/periods/:bindingId` | `CbamPeriodDetailComponent` | view/configure | Reachable |
| Product Profiles | Period tab | `ProductProfilesComponent` | configure mutates | Reachable |
| Production + monthly D/E | Period tab | inline + `MonthlyAllocationDataComponent` | configure mutates | Reachable |
| Activities | Period tab | inline in `period-detail` | configure mutates | Reachable |
| Direct Emissions | Period tab | `StationaryCombustionComponent` | configure executes | Reachable |
| Indirect Emissions | Period tab | `PurchasedElectricityComponent` | configure executes | Reachable |
| Processes | Period tab | `ProductionProcessesComponent` | configure mutates | Reachable |
| Purchased Inputs + precursors | Period tab | inline + `PurchasedPrecursorsComponent` | configure mutates | Reachable |
| Product Results | Period tab | `ProductEmbeddedEmissionsComponent` | configure executes | Reachable |
| Allocation (DEA/IEA/generic) | Period tab | DEA/IEA components + inline rules | configure executes | Reachable |
| Factors | Period tab | inline in `period-detail` | configure resolves | Reachable |
| Calculation | Period tab | inline in `period-detail` | configure executes | Reachable |
| Report / Excel + Official | Period tab | inline + `OfficialSeeExportComponent` | view download; configure generate | Reachable |

### Obsolete / proposal-only (not reachable as separate routes)

Evidence: `app.routes.ts` only registers the six CBAM paths above. `docs/cbam/frontend-feature-map.md` still lists proposed paths such as `…/shipments`, `…/evidence`, `…/approvals`, `installations/:id/processes` as standalone routes — **those routes are not registered**.

| Proposed path | Evidence | Guide handling |
|---------------|----------|----------------|
| `/app/cbam/product-profiles` (standalone) | Not in `app.routes.ts`; profiles live in period tab | Documented as tab only |
| `/app/cbam/periods/:id/shipments` etc. | Not in routes | Listed obsolete; not in user guide as active |

## 2. Field mapping (selected authoritative rows)

Source types: `USER_INPUT` · `PLATFORM_DEFAULT` · `MANUAL_OVERRIDE` · `CONTROLLED_LIST` · `CALCULATED` · `ALLOCATED` · `SNAPSHOT` · `DERIVED_STATUS` · `AUDIT` · `NOT_PERSISTED`

| Page | UI label | Component | Control / property | API | Req / column | Source type | Notes |
|------|----------|-----------|--------------------|-----|----------------|-------------|-------|
| Installation form | Code | `installation-form` | `code` | `POST …/installations` | `cbam_installation_profiles.code` | USER_INPUT | Unique per org |
| Installation form | Name | same | `name` | same / PATCH | `….name` | USER_INPUT | |
| Installation form | Timezone | same | `timezone` | same | `….timezone` | USER_INPUT | |
| Installation form | Operator ID | same | `operatorId` | same | `….operator_id` | USER_INPUT | Optional |
| Period list | Reporting Period | `period-list` | `reportingPeriodId` | `POST …/reporting-period-bindings` | `cbam_reporting_period_bindings.reporting_period_id` | USER_INPUT | FK to platform period |
| Product Profiles | CN code | `product-profiles` | CN search selection | `GET …/cn-codes`, `POST …/product-profile-versions` | `cbam_product_profile_versions.cn_code_id` | CONTROLLED_LIST | Catalog seeded |
| Product Profiles | Steel % fields | same | `percentMn` etc. | PATCH/POST profile | steel columns on profile version | USER_INPUT | Applicability-gated |
| Product Profiles | Publish | button | — | `POST …/product-profile-versions/{id}/publish` | status → published | DERIVED_STATUS | |
| Production | Quantity | period-detail | `quantity` | `POST …/production-records` | `cbam_production_records.quantity` | USER_INPUT | Requires ready profile |
| Production | Product profile | same | `productProfileVersionId` | same | `….product_profile_version_id` | USER_INPUT | |
| Monthly D/E | Total production | `monthly-allocation-data` | D quantity | `POST …/monthly-production-basis` | `cbam_monthly_production_basis.total_production_quantity` | USER_INPUT | Workbook D |
| Monthly D/E | Amount sent to importer | same | E quantity | same | `….cbam_quantity` | USER_INPUT | Workbook E |
| Monthly D/E | CBAM share | display | — | summary/readiness | computed | CALCULATED / NOT_PERSISTED display | Server authoritative |
| Activities | Activity Type | period-detail | `activityTypeCode` | `POST …/activity-records` | `cbam_activity_records.activity_type_id` | CONTROLLED_LIST | |
| Activities | Quantity/Unit/Date | same | fields | same | quantity/unit/date cols | USER_INPUT | |
| Direct Emissions | Fuel use record | `stationary-combustion` | activity id | `POST …/stationary-combustion/executions` | writes `cbam_stationary_combustion_results` | USER_INPUT selector | Snapshot of inputs |
| Direct Emissions | Density | same | density | execution body | snapshotted on result | USER_INPUT | Required for volume fuels |
| Direct Emissions | Result tCO2 | display | — | GET result/summary | result columns | CALCULATED + SNAPSHOT | Immutable |
| Direct Emissions | Current badge | display | `isCurrent` | current pointer table | `cbam_stationary_combustion_current_results` | DERIVED_STATUS | |
| Indirect Emissions | Factor value | `purchased-electricity` | manual factor | `POST …/purchased-electricity/executions` | snapshotted on `cbam_purchased_electricity_results` | MANUAL_OVERRIDE | Provenance required |
| Indirect Emissions | Platform default | same | source enum | GET default + execution | may be absent | PLATFORM_DEFAULT | No unverified TR seed |
| Indirect Emissions | Exported electricity | same | optional fields | execution | separate snapshot fields | USER_INPUT | Not subtracted |
| DEA | Calculate | `direct-emissions-allocation` | clientRequestId | `POST …/direct-emissions-allocation/executions` | `cbam_direct_emissions_allocation_results` (+ snapshots/products/current) | CALCULATED/ALLOCATED | Idempotent |
| IEA | Calculate | `indirect-emissions-allocation` | clientRequestId | `POST …/indirect-emissions-allocation/executions` | `cbam_indirect_emissions_allocation_*` | CALCULATED/ALLOCATED | Idempotent |
| Processes | Produced quantity | `production-processes` | form | `POST/PATCH …/production-processes` | `cbam_production_processes` | USER_INPUT | |
| Processes | Product uses | same | uses CRUD | `…/product-uses` | `cbam_production_process_product_uses` | USER_INPUT | Balance server-side |
| Processes | Heat / waste gas / export elec | same | conditional | PATCH process | typed columns | USER_INPUT | Null-cleared when disabled |
| Precursors | Mode | `purchased-precursors` | SUPPLIER_DATA / EU_DEFAULT | POST/PATCH precursors | mode column | USER_INPUT | No HYBRID |
| Precursors | EU default row | same | resolve | `POST …/default-values/resolve` | snapshot cols on precursor | SNAPSHOT | Immutable after save |
| Precursors | Embedded display | display | — | readiness/detail | calculated fields | CALCULATED | Not client math |
| Product Results | Calculate V2 | `product-embedded-emissions` | clientRequestId | `POST …/product-embedded-emissions/executions` | `cbam_product_embedded_emissions_*` + current | CALCULATED | Default V2 |
| Official Excel | Generate | `official-see-export` | clientRequestId | `POST …/official-see-export/executions` | `cbam_official_see_export_runs` / `_artifacts` | DERIVED_STATUS + AUDIT | Download only if validated |
| Official Excel | Download | same | artifact id | `GET …/official-see-export/artifacts/{id}/download` | artifact blob metadata | SNAPSHOT | Auth required |
| Factors | Resolve | period-detail | definition code | `POST …/factor-resolutions/…/resolve` | `cbam_factor_resolutions` | PLATFORM_DEFAULT / MANUAL | |
| Calculation | Execute run | period-detail | run id | `POST …/calculation-runs/{id}/execute` | `cbam_calculation_results` | CALCULATED | MULTIPLY_ACTIVITY_BY_FACTOR |
| Internal Excel | Generate | period-detail | — | `POST …/exports` | `cbam_export_runs` / `_artifacts` | SNAPSHOT | Distinct from Official |

Full HTTP surface and exhaustive field/action rows: see [`user-guide/inventories/`](user-guide/inventories/) (authoritative) and `user-guide/_inventory-generated.md` (155 backend routes).

## 3. Action → API map (execution-critical)

| User action | Permission | Method | Endpoint (org-scoped) | Tables written | Idempotency |
|-------------|------------|--------|----------------------|----------------|-------------|
| Create installation | configure | POST | `/installations` | `cbam_installation_profiles` | n/a |
| Activate / archive installation | configure | POST | `/installations/{id}/activate\|archive` | installation status | n/a |
| Create period binding | configure | POST | `/reporting-period-bindings` | `cbam_reporting_period_bindings` | n/a |
| Open data collection | configure | POST | `/reporting-period-bindings/{id}/open-data-collection` | binding status | n/a |
| Publish product profile | configure | POST | `/product-profile-versions/{id}/publish` | profile status | n/a |
| Save production | configure | POST/PATCH | `/…/production-records` | `cbam_production_records` | rowVersion |
| Save monthly D/E | configure | POST/PATCH/DELETE | `/…/monthly-production-basis` | `cbam_monthly_production_basis` | rowVersion |
| Save activity | configure | POST/PATCH | `/…/activity-records` | `cbam_activity_records` | rowVersion |
| Calculate SC | configure | POST | `/…/stationary-combustion/executions` | SC results + current | `clientRequestId` |
| Calculate PE | configure | POST | `/…/purchased-electricity/executions` | PE results + current | `clientRequestId` |
| Calculate DEA | configure | POST | `/…/direct-emissions-allocation/executions` | DEA result graph + current | `clientRequestId` |
| Calculate IEA | configure | POST | `/…/indirect-emissions-allocation/executions` | IEA result graph + current | `clientRequestId` |
| Save process / uses | configure | POST/PATCH/DELETE | `/…/production-processes…` | process + uses | rowVersion |
| Save precursor / uses | configure | POST/PATCH/DELETE | `/…/purchased-precursors…` | precursor + uses | rowVersion |
| Calculate PEE V2 | configure | POST | `/…/product-embedded-emissions/executions` | PEE result graph + current | `clientRequestId` |
| Generate Official SEE | configure | POST | `/…/official-see-export/executions` | export runs/artifacts | `clientRequestId` |
| Download Official artifact | view | GET | `/official-see-export/artifacts/{id}/download` | read | n/a |
| Generate internal export | configure | POST | `/…/exports` | export runs/artifacts | n/a |

## 4. Stale / current behavior

| Domain | Current pointer table | Stale when (examples) | Recalc |
|--------|----------------------|------------------------|--------|
| Stationary combustion | `cbam_stationary_combustion_current_results` | Activity qty/unit/date/fuel inputs change | New execution |
| Purchased electricity | `cbam_purchased_electricity_current_results` | Activity or factor provenance changes | New execution |
| DEA | `cbam_direct_emissions_allocation_current` | SC current or monthly basis or production profile quantities change | New execution |
| IEA | `cbam_indirect_emissions_allocation_current` | PE current or monthly basis changes | New execution |
| PEE | `cbam_product_embedded_emissions_current` | Upstream currents / processes / precursors change | New execution |
| Official SEE | run/artifact rows | Source PEE no longer valid for a new generate | New execution |

Historical immutable rows are preserved; pointers move.

## 5. Permissions & tenancy

- Guards: `canConfigureCbam()` in `roles.util.ts` (roles include `cbam:configure` / `cbam:view`).  
- All routes are organization-scoped; cross-org ids return non-disclosing 404.  
- Writable binding required for mutations (`draft` / `data_collection` in UI `canMutate` logic).

## 6. Official Excel technical notes

See `docs/cbam/official-see-export.md` for template SHA, mapping version, LibreOffice, parity, leakage. UI component: `official-see-export.component.ts`.
