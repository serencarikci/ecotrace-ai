# Generated inventory (from source — do not edit by hand)

Generated for documentation build. Prefer the human guides; this file is evidence.

## Angular CBAM routes

| Route | Component |
|---|---|
| `/app/cbam` | `CbamShellComponent` |
| `/app/cbam/installations` | `CbamInstallationListComponent` |
| `/app/cbam/installations/new` | `CbamInstallationFormComponent` |
| `/app/cbam/installations/:installationId` | `CbamInstallationDetailComponent` |
| `/app/cbam/periods` | `CbamPeriodListComponent` |
| `/app/cbam/periods/:bindingId` | `CbamPeriodDetailComponent` |

## Period detail tabs (exact mat-tab labels)

- Product Profiles
- Production
- Activities
- Direct Emissions
- Indirect Emissions
- Processes
- Purchased Inputs
- Product Results
- Allocation
- Factors
- Calculation
- Report / Excel

## Embedded child components in period detail

| Parent | Selector | File |
|---|---|---|
| Product Profiles | `app-cbam-product-profiles` | `product-profiles/product-profiles.component.ts` |
| Production → Monthly allocation data | `app-cbam-monthly-allocation-data` | `monthly-allocation-data/monthly-allocation-data.component.ts` |
| Direct Emissions | `app-cbam-stationary-combustion` | `stationary-combustion/stationary-combustion.component.ts` |
| Indirect Emissions | `app-cbam-purchased-electricity` | `purchased-electricity/purchased-electricity.component.ts` |
| Processes | `app-cbam-production-processes` | `production-processes/production-processes.component.ts` |
| Purchased Inputs → Purchased precursors | `app-cbam-purchased-precursors` | `purchased-precursors/purchased-precursors.component.ts` |
| Product Results | `app-cbam-product-embedded-emissions` | `product-embedded-emissions/product-embedded-emissions.component.ts` |
| Allocation → Direct emissions allocation | `app-cbam-direct-emissions-allocation` | `direct-emissions-allocation/direct-emissions-allocation.component.ts` |
| Allocation → Indirect emissions allocation | `app-cbam-indirect-emissions-allocation` | `indirect-emissions-allocation/indirect-emissions-allocation.component.ts` |
| Report / Excel → Official Excel | `app-cbam-official-see-export` | `official-see-export/official-see-export.component.ts` |

## Active CBAM tables (53)

- `cbam_installation_profiles`
- `cbam_reporting_period_bindings`
- `cbam_cn_code_datasets`
- `cbam_cn_codes`
- `cbam_cn_controlled_list_values`
- `cbam_product_profile_versions`
- `cbam_production_records`
- `cbam_activity_records`
- `cbam_activity_properties`
- `cbam_purchased_input_records`
- `cbam_allocation_rules`
- `cbam_allocation_results`
- `cbam_reference_sources`
- `cbam_factor_definitions`
- `cbam_factor_values`
- `cbam_factor_resolutions`
- `cbam_calculation_definitions`
- `cbam_calculation_runs`
- `cbam_calculation_results`
- `cbam_export_templates`
- `cbam_export_mappings`
- `cbam_export_runs`
- `cbam_export_artifacts`
- `cbam_stationary_combustion_fuels`
- `cbam_stationary_combustion_parameter_sets`
- `cbam_stationary_combustion_results`
- `cbam_stationary_combustion_current_results`
- `cbam_monthly_production_basis`
- `cbam_direct_emissions_allocation_results`
- `cbam_dea_monthly_basis_snapshots`
- `cbam_dea_source_snapshots`
- `cbam_dea_product_allocations`
- `cbam_direct_emissions_allocation_current`
- `cbam_purchased_electricity_results`
- `cbam_purchased_electricity_current_results`
- `cbam_indirect_emissions_allocation_results`
- `cbam_iea_monthly_basis_snapshots`
- `cbam_iea_source_snapshots`
- `cbam_iea_product_allocations`
- `cbam_indirect_emissions_allocation_current`
- `cbam_production_processes`
- `cbam_production_process_product_uses`
- `cbam_precursor_default_datasets`
- `cbam_precursor_default_values`
- `cbam_purchased_precursors`
- `cbam_purchased_precursor_product_uses`
- `cbam_product_embedded_emissions_results`
- `cbam_product_embedded_emissions_products`
- `cbam_product_embedded_emissions_precursor_contributions`
- `cbam_product_embedded_emissions_internal_contributions`
- `cbam_product_embedded_emissions_current`
- `cbam_official_see_export_runs`
- `cbam_official_see_export_artifacts`

## Backend CBAM routes (155)

| Method | Path |
|---|---|
| GET | `/organizations/{organization_id}/module-status` |
| GET | `/organizations/{organization_id}/installations` |
| POST | `/organizations/{organization_id}/installations` |
| GET | `/organizations/{organization_id}/installations/{installation_id}` |
| PATCH | `/organizations/{organization_id}/installations/{installation_id}` |
| POST | `/organizations/{organization_id}/installations/{installation_id}/activate` |
| POST | `/organizations/{organization_id}/installations/{installation_id}/archive` |
| GET | `/organizations/{organization_id}/reporting-period-bindings` |
| POST | `/organizations/{organization_id}/reporting-period-bindings` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}` |
| PATCH | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/open-data-collection` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/archive` |
| GET | `/organizations/{organization_id}/cn-codes` |
| GET | `/organizations/{organization_id}/cn-codes/{cn_code_id}` |
| GET | `/organizations/{organization_id}/cn-controlled-lists/{list_code}` |
| GET | `/organizations/{organization_id}/product-profile-versions` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-profiles` |
| POST | `/organizations/{organization_id}/product-profile-versions` |
| PATCH | `/organizations/{organization_id}/product-profile-versions/{profile_id}` |
| POST | `/organizations/{organization_id}/product-profile-versions/{profile_id}/publish` |
| GET | `/organizations/{organization_id}/product-profile-versions/{profile_id}` |
| POST | `/organizations/{organization_id}/product-profile-versions/{profile_id}/archive` |
| GET | `/organizations/{organization_id}/activity-types` |
| GET | `/organizations/{organization_id}/units` |
| GET | `/organizations/{organization_id}/activity-property-types` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-profile-link-summary` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/monthly-production-basis` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/monthly-production-basis` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/monthly-production-basis-summary` |
| GET | `/organizations/{organization_id}/monthly-production-basis/{record_id}` |
| PATCH | `/organizations/{organization_id}/monthly-production-basis/{record_id}` |
| DELETE | `/organizations/{organization_id}/monthly-production-basis/{record_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/readiness` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/executions` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/results` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/results/{result_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/direct-emissions-allocation/summary` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/factors/default` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/readiness` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/summary` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/executions` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/results` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-electricity/results/{result_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/readiness` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/executions` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/results` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/results/{result_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation/summary` |
| GET | `/organizations/{organization_id}/production-processes/metadata` |
| GET | `/organizations/{organization_id}/production-processes/controlled-lists` |
| GET | `/organizations/{organization_id}/production-processes/controlled-lists/{list_code}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/summary` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}` |
| PATCH | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/readiness` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/archive` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/product-uses` |
| PATCH | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/product-uses/{use_id}` |
| DELETE | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-processes/{process_id}/product-uses/{use_id}` |
| GET | `/organizations/{organization_id}/purchased-precursors/metadata` |
| GET | `/organizations/{organization_id}/purchased-precursors/default-values/search` |
| POST | `/organizations/{organization_id}/purchased-precursors/default-values/resolve` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/summary` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}` |
| PATCH | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/readiness` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/archive` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/product-uses` |
| PATCH | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/product-uses/{use_id}` |
| DELETE | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-precursors/{precursor_id}/product-uses/{use_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/readiness` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/executions` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/results` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/results/{result_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/product-embedded-emissions/summary` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-records` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/production-records` |
| GET | `/organizations/{organization_id}/production-records/{record_id}` |
| PATCH | `/organizations/{organization_id}/production-records/{record_id}` |
| POST | `/organizations/{organization_id}/production-records/{record_id}/archive` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/activity-records` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/activity-records` |
| GET | `/organizations/{organization_id}/activity-records/{record_id}` |
| PATCH | `/organizations/{organization_id}/activity-records/{record_id}` |
| POST | `/organizations/{organization_id}/activity-records/{record_id}/archive` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-inputs` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/purchased-inputs` |
| GET | `/organizations/{organization_id}/purchased-inputs/{record_id}` |
| PATCH | `/organizations/{organization_id}/purchased-inputs/{record_id}` |
| POST | `/organizations/{organization_id}/purchased-inputs/{record_id}/archive` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/allocation-rules` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/allocation-rules` |
| GET | `/organizations/{organization_id}/allocation-rules/{rule_id}` |
| PATCH | `/organizations/{organization_id}/allocation-rules/{rule_id}` |
| POST | `/organizations/{organization_id}/allocation-rules/{rule_id}/activate` |
| POST | `/organizations/{organization_id}/allocation-rules/{rule_id}/archive` |
| POST | `/organizations/{organization_id}/allocation-rules/{rule_id}` |
| POST | `/organizations/{organization_id}/allocation-rules/{rule_id}` |
| POST | `/organizations/{organization_id}/allocation-results/{result_id}/recalculate` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/allocation-results` |
| GET | `/organizations/{organization_id}/allocation-results/{result_id}` |
| GET | `/organizations/{organization_id}/reference-sources` |
| POST | `/organizations/{organization_id}/reference-sources` |
| GET | `/organizations/{organization_id}/reference-sources/{source_id}` |
| PATCH | `/organizations/{organization_id}/reference-sources/{source_id}` |
| POST | `/organizations/{organization_id}/reference-sources/{source_id}/archive` |
| GET | `/organizations/{organization_id}/factor-definitions` |
| GET | `/organizations/{organization_id}/factor-definitions/{definition_id}` |
| GET | `/organizations/{organization_id}/factor-definitions/{definition_id}/values` |
| POST | `/organizations/{organization_id}/factor-definitions/{definition_id}/values` |
| GET | `/organizations/{organization_id}/factor-values/{value_id}` |
| PATCH | `/organizations/{organization_id}/factor-values/{value_id}` |
| POST | `/organizations/{organization_id}/factor-values/{value_id}/activate` |
| POST | `/organizations/{organization_id}/factor-values/{value_id}/archive` |
| POST | `/organizations/{organization_id}/activity-records/{record_id}/properties` |
| POST | `/organizations/{organization_id}/activity-records/{record_id}` |
| POST | `/organizations/{organization_id}/purchased-inputs/{record_id}` |
| POST | `/organizations/{organization_id}/allocation-results/{result_id}` |
| GET | `/organizations/{organization_id}/factor-resolutions/{resolution_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/factor-resolutions` |
| GET | `/organizations/{organization_id}/calculation-definitions` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/calculation-runs` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/calculation-runs` |
| GET | `/organizations/{organization_id}/calculation-runs/{run_id}` |
| POST | `/organizations/{organization_id}/calculation-runs/{run_id}/execute` |
| GET | `/organizations/{organization_id}/calculation-runs/{run_id}/results` |
| GET | `/organizations/{organization_id}/calculation-results/{result_id}` |
| POST | `/organizations/{organization_id}/calculation-results/{result_id}/recalculate` |
| GET | `/organizations/{organization_id}/export-templates` |
| GET | `/organizations/{organization_id}/export-templates/{template_id}` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/export-readiness` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/summary` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/exports` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/exports` |
| GET | `/organizations/{organization_id}/exports/{export_run_id}` |
| GET | `/organizations/{organization_id}/exports/{export_run_id}/artifacts` |
| GET | `/organizations/{organization_id}/export-artifacts/{artifact_id}/download` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/official-see-export/readiness` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/official-see-export/executions` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/official-see-export/runs` |
| GET | `/organizations/{organization_id}/official-see-export/runs/{run_id}` |
| GET | `/organizations/{organization_id}/official-see-export/runs/{run_id}/artifacts` |
| GET | `/organizations/{organization_id}/official-see-export/artifacts/{artifact_id}/download` |
| GET | `/organizations/{organization_id}/stationary-combustion/fuels` |
| GET | `/organizations/{organization_id}/stationary-combustion/fuels/{fuel_code}/parameters` |
| POST | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/executions` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/summary` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/activity-coverage` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/results` |
| GET | `/organizations/{organization_id}/reporting-period-bindings/{binding_id}/stationary-combustion/results/{result_id}` |
