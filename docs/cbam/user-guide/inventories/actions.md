# User action inventory

Authoritative machine inventory: [`actions.csv`](actions.csv) / [`actions.json`](actions.json).

Discovered / mapped / documented: **148** · Unexplained: **0**

| Screen | Action | Permission | Method | Endpoint | Tables written | Idempotency |
|---|---|---|---|---|---|---|
| direct-emissions-allocation | Retry | cbam:configure | GET | `POST …/direct-emissions-allocation/executions` | `—` | n/a-read |
| direct-emissions-allocation | Direct Emissions | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | Production | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | Monthly allocation data | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | @if (submitting()) { Working… } @else { {{ executeButtonLabel() }} } | cbam:configure | POST/PATCH | `POST …/direct-emissions-allocation/executions; GET readiness/summary/results` | `cbam_direct_emissions_allocation_results, cbam_dea_product_a` | clientRequestId-if-execution |
| direct-emissions-allocation | View details | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | Overview | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | Monthly attribution | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | Fuels | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | Products | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | Balance | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | Method and sources | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| direct-emissions-allocation | Audit | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Retry | cbam:configure | GET | `POST …/indirect-emissions-allocation/executions` | `—` | n/a-read |
| indirect-emissions-allocation | Indirect Emissions | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Production | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Monthly allocation data | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | @if (submitting()) { Working… } @else { {{ executeButtonLabel() }} } | cbam:configure | POST/PATCH | `POST …/indirect-emissions-allocation/executions; GET readiness/summary/results` | `cbam_indirect_emissions_allocation_results, cbam_iea_product` | clientRequestId-if-execution |
| indirect-emissions-allocation | View details | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Overview | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Monthly attribution | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Electricity sources | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Product allocations | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Exported electricity | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Balance | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| indirect-emissions-allocation | Method and audit | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| installation-detail.component | Back | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| installation-detail.component | Save | cbam:configure | POST/PATCH | `GET/PATCH …/installations/{id}; POST …/activate/archive` | `cbam_installation_profiles` | n/a-or-rowVersion |
| installation-detail.component | Activate | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/installations/{id}/activate` | `cbam_installation_profiles` | create-new-row-or-n/a |
| installation-detail.component | Archive | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/installations/{id}/archive` | `cbam_installation_profiles` | rowVersion |
| installation-form.component | Back | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| installation-form.component | Save | cbam:configure | POST/PATCH | `POST …/installations` | `cbam_installation_profiles` | n/a-or-rowVersion |
| installation-list.component | New Installation | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| installation-list.component | Filter | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| installation-list.component | View | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| monthly-allocation-data | Retry | cbam:configure | GET | `GET/POST …/monthly-production-basis` | `—` | n/a-read |
| monthly-allocation-data | Open Direct Emissions | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| monthly-allocation-data | Reload | cbam:view | GET | `GET/POST …/monthly-production-basis` | `—` | n/a-read |
| monthly-allocation-data | Save | cbam:configure | POST/PATCH | `GET/POST/PATCH/DELETE …/monthly-production-basis` | `cbam_monthly_production_basis` | n/a-or-rowVersion |
| monthly-allocation-data | Cancel | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| monthly-allocation-data | {{ row.record ? 'Edit' : 'Enter' }} | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| monthly-allocation-data | Delete | cbam:configure | DELETE | `/api/v1/cbam/organizations/{organization_id}/monthly-production-basis/{id}` | `cbam_monthly_production_basis` | rowVersion |
| official-see-export | Open related section | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| official-see-export | Refresh status | cbam:view | GET | `POST …/official-see-export/executions` | `—` | n/a-read |
| official-see-export | Download current official Excel | cbam:view | GET | `/api/v1/cbam/organizations/{organization_id}/official-see-export/artifacts/{id}/` | `—` | n/a-read |
| official-see-export | @if (submitting()) { Generating… } @else { Generate official Excel } | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/reporting-period-bindings/{id}/offi` | `cbam_official_see_export_runs, cbam_official_see_export_arti` | clientRequestId |
| official-see-export | Download | cbam:view | GET | `/api/v1/cbam/organizations/{organization_id}/official-see-export/runs/{id}/artif` | `—` | n/a-read |
| period-detail.component | Back | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| period-detail.component | Open Data Collection | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/reporting-period-bindings/{id}/open` | `cbam_reporting_period_bindings` | create-new-row-or-n/a |
| period-detail.component | Archive | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/reporting-period-bindings/{id}/arch` | `cbam_reporting_period_bindings` | rowVersion |
| period-detail.component | Save link | cbam:configure | POST/PATCH | `GET …/reporting-period-bindings/{id}; period-scoped CRUD` | `cbam_reporting_period_bindings, cbam_production_records, cba` | n/a-or-rowVersion |
| period-detail.component | Cancel | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| period-detail.component | Link profile | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| period-detail.component | Archive | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/production-records/{id}/archive` | `cbam_production_records` | rowVersion |
| period-detail.component | Save | cbam:configure | POST/PATCH | `GET …/reporting-period-bindings/{id}; period-scoped CRUD` | `cbam_reporting_period_bindings, cbam_production_records, cba` | n/a-or-rowVersion |
| period-detail.component | Archive | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/activity-records/{id}/archive` | `cbam_activity_records` | rowVersion |
| period-detail.component | Archive | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/purchased-inputs/{id}/archive` | `cbam_purchased_input_records` | rowVersion |
| period-detail.component | Activate | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/allocation-rules/{id}/activate` | `cbam_allocation_rules` | create-new-row-or-n/a |
| period-detail.component | Archive | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/allocation-rules/{id}/archive` | `cbam_allocation_rules` | rowVersion |
| period-detail.component | Allocate Activity | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/allocation-rules/{id}/allocate/acti` | `cbam_activity_records` | create-new-row-or-n/a |
| period-detail.component | Allocate Input | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/allocation-rules/{id}/allocate/purc` | `cbam_purchased_input_records` | create-new-row-or-n/a |
| period-detail.component | Recalculate | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/allocation-results/{id}/recalculate` | `cbam_allocation_results` | create-new-row-or-n/a |
| period-detail.component | Save Rule | cbam:configure | POST/PATCH | `GET …/reporting-period-bindings/{id}; period-scoped CRUD` | `cbam_reporting_period_bindings, cbam_production_records, cba` | n/a-or-rowVersion |
| period-detail.component | Resolve Again | cbam:view | POST | `/api/v1/cbam/organizations/{organization_id}/activity-records/{id}/factor-resolu` | `cbam_activity_records, cbam_purchased_input_records, cbam_al` | create-new-row-or-n/a |
| period-detail.component | Save Primary Value | cbam:configure | POST/PATCH | `GET …/reporting-period-bindings/{id}; period-scoped CRUD` | `cbam_reporting_period_bindings, cbam_production_records, cba` | n/a-or-rowVersion |
| period-detail.component | Resolve | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| period-detail.component | Calculate | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/reporting-period-bindings/{id}/calc` | `cbam_calculation_runs` | create-new-row-or-n/a |
| period-detail.component | {{ r.status }} — {{ r.calculatedCount }} calculated | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| period-detail.component | Recalculate | cbam:configure | POST | `/api/v1/cbam/organizations/{organization_id}/calculation-results/{id}/recalculat` | `cbam_calculation_results` | create-new-row-or-n/a |
| period-detail.component | Generate Excel | cbam:configure | POST/PATCH | `GET …/reporting-period-bindings/{id}; period-scoped CRUD` | `cbam_reporting_period_bindings, cbam_production_records, cba` | clientRequestId-if-execution |
| period-detail.component | Download | cbam:view | GET | `/api/v1/cbam/organizations/{organization_id}/exports/{id}/artifacts` | `—` | n/a-read |
| period-list.component | Add Draft Binding | cbam:configure | POST/PATCH | `GET/POST …/reporting-period-bindings` | `cbam_reporting_period_bindings` | n/a-or-rowVersion |
| period-list.component | View | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Retry | cbam:configure | GET | `POST …/product-embedded-emissions/executions` | `—` | n/a-read |
| product-embedded-emissions | Product Profiles | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Production | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Direct Emissions | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Indirect Emissions | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Processes | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Purchased Inputs | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Allocation | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | @if (submitting()) { Working… } @else { {{ executeButtonLabel() }} } | cbam:configure | POST/PATCH | `POST …/product-embedded-emissions/executions; GET readiness/summary/results` | `cbam_product_embedded_emissions_results, cbam_product_embedd` | n/a-or-rowVersion |
| product-embedded-emissions | {{ p.productName }} | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | View details | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Own emissions | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Purchased precursors | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Internal products | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-embedded-emissions | Totals | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-profiles | Retry | cbam:configure | POST/PATCH | `GET/POST/PATCH …/product-profile-versions; GET …/cn-codes/search` | `cbam_product_profile_versions, cbam_cn_codes` | n/a-or-rowVersion |
| product-profiles | Open product management | cbam:configure | POST/PATCH | `GET/POST/PATCH …/product-profile-versions; GET …/cn-codes/search` | `cbam_product_profile_versions, cbam_cn_codes` | n/a-or-rowVersion |
| product-profiles | {{ product.code }} {{ product.name }} | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-profiles | Retry | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-profiles | Create draft profile | cbam:configure | POST/PATCH | `GET/POST/PATCH …/product-profile-versions; GET …/cn-codes/search` | `cbam_product_profile_versions, cbam_cn_codes` | n/a-or-rowVersion |
| product-profiles | Retry CN search | cbam:configure | POST/PATCH | `GET/POST/PATCH …/product-profile-versions; GET …/cn-codes/search` | `cbam_product_profile_versions, cbam_cn_codes` | n/a-or-rowVersion |
| product-profiles | Retry reducing materials | cbam:configure | POST/PATCH | `GET/POST/PATCH …/product-profile-versions; GET …/cn-codes/search` | `cbam_product_profile_versions, cbam_cn_codes` | n/a-or-rowVersion |
| product-profiles | Save draft | cbam:configure | POST/PATCH | `GET/POST/PATCH …/product-profile-versions; GET …/cn-codes/search` | `cbam_product_profile_versions, cbam_cn_codes` | n/a-or-rowVersion |
| product-profiles | Publish | cbam:configure | POST/PATCH | `GET/POST/PATCH …/product-profile-versions; GET …/cn-codes/search` | `cbam_product_profile_versions, cbam_cn_codes` | n/a-or-rowVersion |
| product-profiles | Create new version | cbam:configure | POST/PATCH | `GET/POST/PATCH …/product-profile-versions; GET …/cn-codes/search` | `cbam_product_profile_versions, cbam_cn_codes` | n/a-or-rowVersion |
| product-profiles | Archive | cbam:configure | POST/PATCH | `GET/POST/PATCH …/product-profile-versions; GET …/cn-codes/search` | `cbam_product_profile_versions, cbam_cn_codes` | n/a-or-rowVersion |
| product-profiles | Cancel | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| product-profiles | Open | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| production-processes | Retry | cbam:configure | GET | `GET/POST/PATCH …/production-processes` | `—` | n/a-read |
| production-processes | Reload | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| production-processes | Create draft process | cbam:configure | POST/PATCH | `GET/POST/PATCH …/production-processes; product-uses CRUD` | `cbam_production_processes, cbam_production_process_product_u` | n/a-or-rowVersion |
| production-processes | Create draft | cbam:configure | POST/PATCH | `GET/POST/PATCH …/production-processes; product-uses CRUD` | `cbam_production_processes, cbam_production_process_product_u` | n/a-or-rowVersion |
| production-processes | Cancel | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| production-processes | Open | cbam:configure | GET | `/api/v1/cbam/organizations/{organization_id}/reporting-period-bindings/{id}/prod` | `—` | n/a-read |
| production-processes | Remove | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| production-processes | Add product use | cbam:configure | POST/PATCH | `GET/POST/PATCH …/production-processes; product-uses CRUD` | `cbam_production_processes, cbam_production_process_product_u` | n/a-or-rowVersion |
| production-processes | Direct Emissions Allocation | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| production-processes | Indirect Emissions Allocation | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| production-processes | Save draft | cbam:configure | POST/PATCH | `GET/POST/PATCH …/production-processes; product-uses CRUD` | `cbam_production_processes, cbam_production_process_product_u` | n/a-or-rowVersion |
| production-processes | Archive | cbam:configure | POST/PATCH | `GET/POST/PATCH …/production-processes; product-uses CRUD` | `cbam_production_processes, cbam_production_process_product_u` | n/a-or-rowVersion |
| production-processes | Confirm archive | cbam:configure | POST/PATCH | `GET/POST/PATCH …/production-processes; product-uses CRUD` | `cbam_production_processes, cbam_production_process_product_u` | n/a-or-rowVersion |
| production-processes | Cancel | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-electricity | Retry | cbam:configure | GET | `POST …/purchased-electricity/executions` | `—` | n/a-read |
| purchased-electricity | Go to Activities | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-electricity | {{ calculationActionLabel() }} | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-electricity | View details | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-electricity | Input | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-electricity | Calculation | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-electricity | Emission factor | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-electricity | Exported electricity | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-electricity | Sources | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-electricity | Audit | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-precursors | Retry | cbam:configure | GET | `GET/POST/PATCH …/purchased-precursors` | `—` | n/a-read |
| purchased-precursors | Reload | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-precursors | Create draft precursor | cbam:configure | POST/PATCH | `GET/POST/PATCH …/purchased-precursors; POST …/default-values/resolve` | `cbam_purchased_precursors, cbam_purchased_precursor_product_` | n/a-or-rowVersion |
| purchased-precursors | Create draft | cbam:configure | POST/PATCH | `GET/POST/PATCH …/purchased-precursors; POST …/default-values/resolve` | `cbam_purchased_precursors, cbam_purchased_precursor_product_` | n/a-or-rowVersion |
| purchased-precursors | Cancel | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-precursors | Open | cbam:configure | GET | `/api/v1/cbam/organizations/{organization_id}/reporting-period-bindings/{id}/purc` | `—` | n/a-read |
| purchased-precursors | Search default values | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-precursors | Resolve default value | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-precursors | Use this value | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-precursors | Edit | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-precursors | Remove | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-precursors | {{ editingUseId() ? 'Update product use' : 'Add product use' }} | cbam:configure | PATCH+POST | `/api/v1/cbam/organizations/{organization_id}/reporting-period-bindings/{id}/purc` | `cbam_purchased_precursors, cbam_purchased_precursor_product_` | rowVersion |
| purchased-precursors | Cancel | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| purchased-precursors | Save draft | cbam:configure | POST/PATCH | `GET/POST/PATCH …/purchased-precursors; POST …/default-values/resolve` | `cbam_purchased_precursors, cbam_purchased_precursor_product_` | n/a-or-rowVersion |
| purchased-precursors | Archive | cbam:configure | POST/PATCH | `GET/POST/PATCH …/purchased-precursors; POST …/default-values/resolve` | `cbam_purchased_precursors, cbam_purchased_precursor_product_` | n/a-or-rowVersion |
| purchased-precursors | Confirm archive | cbam:configure | POST/PATCH | `GET/POST/PATCH …/purchased-precursors; POST …/default-values/resolve` | `cbam_purchased_precursors, cbam_purchased_precursor_product_` | n/a-or-rowVersion |
| purchased-precursors | Cancel | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| stationary-combustion | Retry | cbam:configure | POST/PATCH | `POST …/stationary-combustion/executions; GET summary/results/fuels` | `cbam_stationary_combustion_results, cbam_stationary_combusti` | n/a-or-rowVersion |
| stationary-combustion | Go to Activities | cbam:configure | — | `UI-only (router/tab/section)` | `—` | n/a |
| stationary-combustion | Retry | cbam:configure | POST/PATCH | `POST …/stationary-combustion/executions; GET summary/results/fuels` | `cbam_stationary_combustion_results, cbam_stationary_combusti` | n/a-or-rowVersion |
| stationary-combustion | {{ calculationActionLabel() }} | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
| stationary-combustion | View details | cbam:view | GET | `/api/v1/cbam/organizations/{organization_id}/reporting-period-bindings/{id}/stat` | `—` | n/a-read |
| stationary-combustion | Close | cbam:view | — | `UI-only (router/tab/section)` | `—` | n/a |
