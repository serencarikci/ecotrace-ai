# CBAM table dictionary (active)

Active tables documented: **53**

Legacy / unused tables: **none** (empty `legacy_tables` in `tables.json`).

Source of truth: `apps/api/src/ecotrace/modules/cbam/infrastructure/models.py`.

## `cbam_activity_properties`

- **Model:** `CbamActivityProperty`
- **Purpose:** Optional typed numeric properties on an activity record
- **Primary key:** `id`
- **Important columns:** organization_id, activity_record_id, property_code, numeric_value, unit, source_type, source_reference, created_by_user_id
- **Foreign keys:** organizations.id; cbam_activity_records.id; users.id
- **Unique constraints:** "activity_record_id",             "property_code",             name="uq_cbam_activity_property_record_code",
- **Check constraints:** "numeric_value > 0"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_activity_records`

- **Model:** `CbamActivityRecord`
- **Purpose:** Fuel/electricity/other activity quantity inputs for a period
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, installation_profile_id, activity_group, activity_type, activity_date, period_start, period_end, quantity, unit, data_source_type, source_reference, measurement_method, supplier_name
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_installation_profiles.id; users.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status IN ('active', 'archived' | "quantity > 0" | "row_version >= 1" | "period_end IS NULL OR period_start IS NULL OR period_end >= period_start"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component, purchased-electricity, stationary-combustion · `CbamPurchasedElectricityService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_allocation_results`

- **Model:** `CbamAllocationResult`
- **Purpose:** Generic allocation result snapshots
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, allocation_rule_id, source_type, source_id, source_quantity, source_unit, allocation_ratio, allocated_quantity, allocated_unit, allocation_method, calculation_version, is_current, superseded_at
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_allocation_rules.id; users.id
- **Unique constraints:** —
- **Check constraints:** "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD' | "allocation_ratio >= 0 AND allocation_ratio <= 1" | "source_quantity > 0" | "allocated_quantity >= 0"
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_allocation_rules`

- **Model:** `CbamAllocationRule`
- **Purpose:** Generic allocation rules (direct/ratio/manual)
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, installation_profile_id, product_profile_version_id, allocation_method, name, description, allocation_ratio, numerator_production_record_id, denominator_production_record_id, numerator_quantity, denominator_quantity, quantity_unit, rationale
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_installation_profiles.id; cbam_product_profile_versions.id; cbam_production_records.id; cbam_production_records.id; users.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED' | "allocation_method IN ('DIRECT_ASSIGNMENT', 'PRODUCTION_QUANTITY_RATIO', 'MANUAL_RATIO' | "allocation_ratio IS NULL OR (allocation_ratio >= 0 AND allocation_ratio <= 1 | "row_version >= 1"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_calculation_definitions`

- **Model:** `CbamCalculationDefinition`
- **Purpose:** Platform calculation definition catalog
- **Primary key:** `id`
- **Important columns:** code, name, calculation_type, source_type, factor_definition_id, output_unit, formula_version, description, status
- **Foreign keys:** cbam_factor_definitions.id
- **Unique constraints:** "code", name="uq_cbam_calculation_definition_code"
- **Check constraints:** "calculation_type IN ("             "'MULTIPLY_ACTIVITY_BY_FACTOR', 'STATIONARY_COMBUSTION_CO2_V1', "             "'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1'"             " | "("             "calculation_type = 'MULTIPLY_ACTIVITY_BY_FACTOR' "             "AND factor_definition_id IS NOT NULL"             " | "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD', 'ALLOCATION_RESULT' | "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED'
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_calculation_results`

- **Model:** `CbamCalculationResult`
- **Purpose:** Generic calculation result rows
- **Primary key:** `id`
- **Important columns:** organization_id, calculation_run_id, calculation_definition_id, source_type, source_id, allocation_result_id, factor_resolution_id, source_quantity, source_unit, factor_value, factor_unit, result_value, result_unit, calculation_type
- **Foreign keys:** organizations.id; cbam_calculation_runs.id; cbam_calculation_definitions.id; cbam_allocation_results.id; cbam_factor_resolutions.id; users.id
- **Unique constraints:** —
- **Check constraints:** "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD', 'ALLOCATION_RESULT' | "status IN ("             "'CALCULATED', 'BLOCKED', 'INVALID_INPUT', 'INCOMPATIBLE_UNIT', "             "'UNRESOLVED_FACTOR', 'AMBIGUOUS_FACTOR', 'UNSUPPORTED_FORMULA'"             " | "calculation_type IN ('MULTIPLY_ACTIVITY_BY_FACTOR'
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_calculation_runs`

- **Model:** `CbamCalculationRun`
- **Purpose:** Generic calculation run headers
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, status, calculation_version, started_at, completed_at, error_summary, calculated_count, blocked_count, invalid_count, primary_factor_count, default_factor_count, created_by_user_id
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status IN ("             "'DRAFT', 'RUNNING', 'COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED', 'ARCHIVED'"             "
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_cn_code_datasets`

- **Model:** `CbamCnCodeDataset`
- **Purpose:** CN dataset/version packaging
- **Primary key:** `id`
- **Important columns:** dataset_code, dataset_version, content_checksum, source_workbook_name, source_workbook_sha256, source_template_version, valid_from, valid_until, status
- **Foreign keys:** —
- **Unique constraints:** "dataset_code", "dataset_version", name="uq_cbam_cn_dataset_code_version"
- **Check constraints:** "status IN ('ACTIVE', 'SUPERSEDED', 'ARCHIVED' | "valid_until IS NULL OR valid_until >= valid_from"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** product-profiles · `CbamProductProfileService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_cn_codes`

- **Model:** `CbamCnCode`
- **Purpose:** CN code catalog rows
- **Primary key:** `id`
- **Important columns:** dataset_id, cn_key, normalized_code, display_code, description_en, cbam_sector, numbering_label, source_sheet, source_row, status, field_applicability
- **Foreign keys:** cbam_cn_code_datasets.id
- **Unique constraints:** "dataset_id", "cn_key", name="uq_cbam_cn_codes_dataset_cn_key" | "dataset_id", "normalized_code", name="uq_cbam_cn_codes_dataset_normalized"
- **Check constraints:** "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED' | "source_row >= 1"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** product-profiles · `CbamProductProfileService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_cn_controlled_list_values`

- **Model:** `CbamCnControlledListValue`
- **Purpose:** CN controlled-list value catalog
- **Primary key:** `id`
- **Important columns:** dataset_id, list_code, value_code, value_label, sort_order, status
- **Foreign keys:** cbam_cn_code_datasets.id
- **Unique constraints:** "dataset_id",             "list_code",             "value_code",             name="uq_cbam_cn_list_dataset_code_value",
- **Check constraints:** "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED'
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** product-profiles · `CbamProductProfileService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_dea_monthly_basis_snapshots`

- **Model:** `CbamDeaMonthlyBasisSnapshot`
- **Purpose:** DEA monthly D/E input snapshots
- **Primary key:** `id`
- **Important columns:** result_id, organization_id, reporting_period_binding_id, basis_record_id, basis_row_version, month_start, total_production_quantity, cbam_quantity, quantity_unit, normalized_total_production_tonnes, normalized_cbam_quantity_tonnes, monthly_share_raw
- **Foreign keys:** cbam_direct_emissions_allocation_results.id; cbam_monthly_production_basis.id
- **Unique constraints:** "result_id", "month_start", name="uq_cbam_dea_mb_result_month"
- **Check constraints:** "EXTRACT(DAY FROM month_start
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** direct-emissions-allocation · `CbamDirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_dea_product_allocations`

- **Model:** `CbamDeaProductAllocation`
- **Purpose:** DEA per-product allocations
- **Primary key:** `id`
- **Important columns:** result_id, organization_id, reporting_period_binding_id, product_id, product_profile_version_id, profile_version, cn_normalized_code, cn_display_code, product_name, production_record_ids, production_quantity_snapshots, normalized_quantity_tonnes, denominator_tonnes, raw_share
- **Foreign keys:** cbam_direct_emissions_allocation_results.id; cbam_product_profile_versions.id
- **Unique constraints:** "result_id",             "product_profile_version_id",             name="uq_cbam_dea_prod_result_profile",
- **Check constraints:** "result_unit = 'tCO2'"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** direct-emissions-allocation · `CbamDirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_dea_source_snapshots`

- **Model:** `CbamDeaSourceSnapshot`
- **Purpose:** DEA source emission snapshots
- **Primary key:** `id`
- **Important columns:** result_id, organization_id, reporting_period_binding_id, source_result_id, source_run_id, activity_record_id, activity_date, month_start, fuel_code, fuel_name, dataset_code, dataset_version, activity_quantity, activity_unit
- **Foreign keys:** cbam_direct_emissions_allocation_results.id; cbam_stationary_combustion_results.id
- **Unique constraints:** "result_id", "source_result_id", name="uq_cbam_dea_src_result_source"
- **Check constraints:** —
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** direct-emissions-allocation · `CbamDirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_direct_emissions_allocation_current`

- **Model:** `CbamDirectEmissionsAllocationCurrent`
- **Purpose:** Pointer to current DEA result
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, methodology_code, current_result_id
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_direct_emissions_allocation_results.id
- **Unique constraints:** "organization_id",             "reporting_period_binding_id",             "methodology_code",             name="uq_cbam_dea_current_org_binding_method",
- **Check constraints:** —
- **Lifecycle:** current-pointer
- **Editable / immutable:** pointer-row
- **Current/history/stale:** yes-current-pointer
- **Delete/archive:** replace-pointer
- **Associated screen / API:** direct-emissions-allocation · `CbamDirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_direct_emissions_allocation_results`

- **Model:** `CbamDirectEmissionsAllocationResult`
- **Purpose:** DEA execution results
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, methodology_code, methodology_version, workbook_filename, workbook_sha256, workbook_formula_refs, client_request_id, request_fingerprint, status, balance_status, facility_fossil_co2_tonnes_raw, cbam_fossil_co2_tonnes_raw, non_cbam_fossil_co2_tonnes_raw
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status = 'COMPLETED'" | "balance_status IN ('BALANCED', 'UNBALANCED' | "result_unit = 'tCO2'" | "balance_status <> 'BALANCED' OR remaining_fossil_co2_tonnes = 0"
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** direct-emissions-allocation · `CbamDirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_export_artifacts`

- **Model:** `CbamExportArtifact`
- **Purpose:** Internal Excel artifact blobs/metadata
- **Primary key:** `id`
- **Important columns:** organization_id, export_run_id, artifact_type, file_name, storage_uri, mime_type, file_size_bytes, sha256
- **Foreign keys:** organizations.id; cbam_export_runs.id
- **Unique constraints:** —
- **Check constraints:** "artifact_type IN ('XLSX', 'CSV_SUMMARY', 'JSON_SUMMARY', 'HTML_REPORT'
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_export_mappings`

- **Model:** `CbamExportMapping`
- **Purpose:** Internal Excel sheet/cell mappings
- **Primary key:** `id`
- **Important columns:** export_template_id, mapping_code, source_type, source_path, worksheet_name, destination_type, destination_reference, value_type, required, transformation_code, notes
- **Foreign keys:** cbam_export_templates.id
- **Unique constraints:** "export_template_id",             "mapping_code",             name="uq_cbam_export_mapping_template_code",
- **Check constraints:** "source_type IN ("             "'ORGANIZATION', 'INSTALLATION', 'REPORTING_PERIOD', 'PRODUCT', "             "'PRODUCTION_RECORD', 'ACTIVITY_RECORD', 'PURCHASED_INPUT', "             "'ALLOCATION_RESULT', 'FACTOR_RESOLUTION', 'CALCULATION_R | "destination_type IN ('CELL', 'NAMED_RANGE', 'TABLE_COLUMN', 'REPEATING_ROW' | "value_type IN ('STRING', 'NUMBER', 'DATE', 'DATETIME', 'BOOLEAN', 'ENUM', 'UNIT' | "transformation_code IN ("             "'NONE', 'DECIMAL_TO_NUMBER', 'DATE_TO_EXCEL_DATE', "             "'DATETIME_TO_EXCEL_DATETIME', 'ENUM_TO_DISPLAY_LABEL', "             "'UNIT_DISPLAY', 'BOOLEAN_TO_YES_NO'"             "
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_export_runs`

- **Model:** `CbamExportRun`
- **Purpose:** Internal Excel export run headers
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, export_template_id, calculation_run_id, status, template_version, mapping_version, mapping_checksum, template_checksum, input_checksum, started_at, completed_at, error_message, warning_summary
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_export_templates.id; cbam_calculation_runs.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status IN ("             "'PENDING', 'RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', "             "'FAILED', 'CANCELLED'"             "
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_export_templates`

- **Model:** `CbamExportTemplate`
- **Purpose:** Internal Excel export templates
- **Primary key:** `id`
- **Important columns:** organization_id, code, name, template_type, version, mapping_version, storage_uri, checksum, status, description, activated_at, archived_at, created_by_user_id
- **Foreign keys:** organizations.id; users.id
- **Unique constraints:** —
- **Check constraints:** "template_type IN ('INTERNAL_SKDM', 'OFFICIAL_CBAM_TEMPLATE', 'CUSTOMER_TEMPLATE' | "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED'
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_factor_definitions`

- **Model:** `CbamFactorDefinition`
- **Purpose:** Factor definition catalog
- **Primary key:** `id`
- **Important columns:** code, name, factor_category, activity_type, property_code, input_unit_family, output_unit, description, status
- **Foreign keys:** —
- **Unique constraints:** "code", name="uq_cbam_factor_definition_code"
- **Check constraints:** "factor_category IN ('ACTIVITY_PROPERTY', 'EMISSION_FACTOR', "             "'EMBEDDED_EMISSION_FACTOR', 'ENERGY_FACTOR', 'OTHER' | "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED'
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_factor_resolutions`

- **Model:** `CbamFactorResolution`
- **Purpose:** Resolved factor applied to activity/purchased/allocation target
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, source_type, source_id, factor_definition_id, resolution_status, selected_activity_property_id, selected_factor_value_id, selected_value, selected_unit, source_precedence, resolution_reason, resolver_version, resolved_at
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_factor_definitions.id; cbam_activity_properties.id; cbam_factor_values.id; users.id
- **Unique constraints:** —
- **Check constraints:** "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD', 'ALLOCATION_RESULT' | "resolution_status IN ("             "'RESOLVED_PRIMARY', 'RESOLVED_DEFAULT', 'UNRESOLVED', 'AMBIGUOUS', "             "'INCOMPATIBLE_UNIT', 'OUTSIDE_VALIDITY', 'BLOCKED'"             "
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_factor_values`

- **Model:** `CbamFactorValue`
- **Purpose:** Versioned factor numeric values
- **Primary key:** `id`
- **Important columns:** organization_id, factor_definition_id, reference_source_id, activity_type, numeric_value, unit, valid_from, valid_until, geography_code, supplier_name, facility_specific, data_source_type, source_reference, notes
- **Foreign keys:** organizations.id; cbam_factor_definitions.id; cbam_reference_sources.id; users.id; users.id; users.id
- **Unique constraints:** —
- **Check constraints:** "data_source_type IN ('PRIMARY', 'DEFAULT_REFERENCE' | "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED' | "numeric_value > 0" | "row_version >= 1"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_iea_monthly_basis_snapshots`

- **Model:** `CbamIeaMonthlyBasisSnapshot`
- **Purpose:** IEA monthly D/E input snapshots
- **Primary key:** `id`
- **Important columns:** result_id, organization_id, reporting_period_binding_id, basis_record_id, basis_row_version, month_start, total_production_quantity, cbam_quantity, quantity_unit, normalized_total_production_tonnes, normalized_cbam_quantity_tonnes, monthly_share_raw
- **Foreign keys:** cbam_indirect_emissions_allocation_results.id
- **Unique constraints:** "result_id", "month_start", name="uq_cbam_iea_mb_result_month"
- **Check constraints:** "EXTRACT(DAY FROM month_start
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** indirect-emissions-allocation · `CbamIndirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_iea_product_allocations`

- **Model:** `CbamIeaProductAllocation`
- **Purpose:** IEA per-product allocations
- **Primary key:** `id`
- **Important columns:** result_id, organization_id, reporting_period_binding_id, product_id, product_profile_version_id, profile_version, cn_normalized_code, cn_display_code, product_name, production_record_ids, production_quantity_snapshots, normalized_quantity_tonnes, denominator_tonnes, raw_share
- **Foreign keys:** cbam_indirect_emissions_allocation_results.id; cbam_product_profile_versions.id
- **Unique constraints:** "result_id",             "product_profile_version_id",             name="uq_cbam_iea_prod_result_profile",
- **Check constraints:** "electricity_unit = 'MWh'" | "emissions_unit = 'tCO2e'"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** indirect-emissions-allocation · `CbamIndirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_iea_source_snapshots`

- **Model:** `CbamIeaSourceSnapshot`
- **Purpose:** IEA electricity source snapshots
- **Primary key:** `id`
- **Important columns:** result_id, organization_id, reporting_period_binding_id, source_result_id, source_run_id, activity_record_id, activity_date, month_start, activity_quantity, activity_unit, electricity_mwh, factor_source_mode, factor_value, factor_unit
- **Foreign keys:** cbam_indirect_emissions_allocation_results.id; cbam_purchased_electricity_results.id
- **Unique constraints:** "result_id", "source_result_id", name="uq_cbam_iea_src_result_source"
- **Check constraints:** —
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** indirect-emissions-allocation · `CbamIndirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_indirect_emissions_allocation_current`

- **Model:** `CbamIndirectEmissionsAllocationCurrent`
- **Purpose:** Pointer to current IEA result
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, methodology_code, current_result_id
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id
- **Unique constraints:** "organization_id",             "reporting_period_binding_id",             "methodology_code",             name="uq_cbam_iea_current_org_binding_method",
- **Check constraints:** —
- **Lifecycle:** current-pointer
- **Editable / immutable:** pointer-row
- **Current/history/stale:** yes-current-pointer
- **Delete/archive:** replace-pointer
- **Associated screen / API:** indirect-emissions-allocation · `CbamIndirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_indirect_emissions_allocation_results`

- **Model:** `CbamIndirectEmissionsAllocationResult`
- **Purpose:** IEA execution results
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, methodology_code, methodology_version, workbook_filename, workbook_sha256, workbook_formula_refs, client_request_id, request_fingerprint, status, balance_status, facility_electricity_mwh_raw, cbam_electricity_mwh_raw, non_cbam_electricity_mwh_raw
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status = 'COMPLETED'" | "balance_status IN ('BALANCED', 'UNBALANCED' | "electricity_unit = 'MWh'" | "emissions_unit = 'tCO2e'" | "balance_status <> 'BALANCED' OR ("             "remaining_electricity_mwh = 0 AND remaining_indirect_emissions_tco2e = 0"             "
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** indirect-emissions-allocation · `CbamIndirectEmissionsAllocationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_installation_profiles`

- **Model:** `CbamInstallationProfile`
- **Purpose:** SKDM installation profile linked to a facility/org
- **Primary key:** `id`
- **Important columns:** organization_id, facility_id, code, name, status, timezone, operator_identity_ref, metadata_json, row_version, created_by_user_id, updated_by_user_id
- **Foreign keys:** organizations.id; facilities.id; users.id; users.id
- **Unique constraints:** "organization_id", "code", name="uq_cbam_installation_org_code"
- **Check constraints:** "status IN ('draft', 'active', 'archived' | "row_version >= 1"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** installation-detail.component, installation-form.component, installation-list.component · `CbamInstallationService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_monthly_production_basis`

- **Model:** `CbamMonthlyProductionBasis`
- **Purpose:** Workbook D/E monthly total vs CBAM-sent quantities
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, month_start, total_production_quantity, cbam_quantity, quantity_unit, source_type, notes, row_version, created_by_user_id, updated_by_user_id
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; users.id; users.id
- **Unique constraints:** "organization_id",             "reporting_period_binding_id",             "month_start",             name="uq_cbam_monthly_prod_basis_org_binding_month",
- **Check constraints:** "EXTRACT(DAY FROM month_start | "total_production_quantity IS NULL OR total_production_quantity >= 0" | "cbam_quantity IS NULL OR cbam_quantity >= 0" | "row_version >= 1" | "source_type IN ('MANUAL', 'IMPORT', 'SYSTEM'
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** monthly-allocation-data · `CbamMonthlyProductionBasisService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_official_see_export_artifacts`

- **Model:** `CbamOfficialSeeExportArtifact`
- **Purpose:** Official SEE downloadable artifacts
- **Primary key:** `id`
- **Important columns:** organization_id, export_run_id, artifact_type, file_name, storage_uri, mime_type, file_size_bytes, sha256
- **Foreign keys:** organizations.id; cbam_official_see_export_runs.id
- **Unique constraints:** —
- **Check constraints:** "artifact_type IN ('XLSX', 'JSON_SUMMARY'
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** official-see-export · `CbamOfficialSeeExportService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_official_see_export_runs`

- **Model:** `CbamOfficialSeeExportRun`
- **Purpose:** Official SEE Excel generation runs
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, client_request_id, generation_status, validation_status, formula_parity_status, mapping_version, template_filename, template_version, template_sha256, pee_result_id, dea_result_id, iea_result_id, process_snapshot_ids
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_product_embedded_emissions_results.id; cbam_direct_emissions_allocation_results.id; cbam_indirect_emissions_allocation_results.id; users.id
- **Unique constraints:** "organization_id",             "reporting_period_binding_id",             "client_request_id",             name="uq_cbam_ose_runs_org_binding_client_request",
- **Check constraints:** "generation_status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED' | "validation_status IN ('PENDING', 'PASSED', 'FAILED', 'SKIPPED' | "formula_parity_status IN ('PENDING', 'PASSED', 'FAILED', 'ENGINE_UNAVAILABLE'
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** official-see-export · `CbamOfficialSeeExportService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_precursor_default_datasets`

- **Model:** `CbamPrecursorDefaultDataset`
- **Purpose:** EU default precursor dataset packaging
- **Primary key:** `id`
- **Important columns:** dataset_code, dataset_version, content_checksum, source_workbook_name, source_workbook_sha256, source_template_version, regulation_reference, valid_from, valid_until, status, value_count
- **Foreign keys:** —
- **Unique constraints:** "dataset_code", "dataset_version", name="uq_cbam_precursor_dv_dataset_code_version"
- **Check constraints:** "status IN ('ACTIVE', 'SUPERSEDED', 'ARCHIVED' | "valid_until IS NULL OR valid_until >= valid_from" | "value_count >= 0"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** purchased-precursors · `CbamPurchasedPrecursorService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_precursor_default_values`

- **Model:** `CbamPrecursorDefaultValue`
- **Purpose:** EU default precursor values
- **Primary key:** `id`
- **Important columns:** dataset_id, country_name, source_sheet, source_row, is_other_countries_group, cn_normalized_code, cn_display_code, goods_category, goods_description, production_route, direct_value, direct_value_status, indirect_value, indirect_value_status
- **Foreign keys:** cbam_precursor_default_datasets.id
- **Unique constraints:** "dataset_id",             "source_sheet",             "source_row",             name="uq_cbam_precursor_dv_values_dataset_source",
- **Check constraints:** "source_row >= 1"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** purchased-precursors · `CbamPurchasedPrecursorService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_product_embedded_emissions_current`

- **Model:** `CbamProductEmbeddedEmissionsCurrent`
- **Purpose:** Pointer to current PEE result
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, methodology_code, current_result_id
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id
- **Unique constraints:** "organization_id",             "reporting_period_binding_id",             "methodology_code",             name="uq_cbam_pee_current_org_binding_method",
- **Check constraints:** —
- **Lifecycle:** current-pointer
- **Editable / immutable:** pointer-row
- **Current/history/stale:** yes-current-pointer
- **Delete/archive:** replace-pointer
- **Associated screen / API:** product-embedded-emissions · `CbamProductEmbeddedEmissionsService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_product_embedded_emissions_internal_contributions`

- **Model:** `CbamProductEmbeddedEmissionsInternalContribution`
- **Purpose:** PEE internal process contribution lines
- **Primary key:** `id`
- **Important columns:** result_id, product_row_id, organization_id, reporting_period_binding_id, consumer_product_profile_version_id, supplier_product_profile_version_id, consumer_process_id, supplier_process_id, supplier_process_row_version, product_use_id, product_use_row_version, product_use_quantity, product_use_unit, quantity_tonnes
- **Foreign keys:** cbam_product_embedded_emissions_results.id; cbam_product_profile_versions.id; cbam_product_profile_versions.id
- **Unique constraints:** "result_id", "product_use_id", name="uq_cbam_pee_internal_result_use"
- **Check constraints:** "result_unit = 'tCO2e'" | "specific_unit = 'tCO2e/t'" | "quantity_tonnes >= 0" | "consumer_denominator_tonnes > 0" | "consumer_product_profile_version_id <> supplier_product_profile_version_id"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** product-embedded-emissions · `CbamProductEmbeddedEmissionsService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_product_embedded_emissions_precursor_contributions`

- **Model:** `CbamProductEmbeddedEmissionsPrecursorContribution`
- **Purpose:** PEE precursor contribution lines
- **Primary key:** `id`
- **Important columns:** result_id, product_row_id, organization_id, reporting_period_binding_id, product_profile_version_id, precursor_id, precursor_row_version, precursor_name, precursor_cn_normalized_code, precursor_cn_display_code, data_source_mode, value_source, product_use_id, product_use_row_version
- **Foreign keys:** cbam_product_embedded_emissions_results.id; cbam_product_profile_versions.id
- **Unique constraints:** "result_id", "product_use_id", name="uq_cbam_pee_contrib_result_use"
- **Check constraints:** "result_unit = 'tCO2e'" | "specific_unit = 'tCO2e/t'" | "quantity_tonnes >= 0" | "data_source_mode IN ('SUPPLIER_DATA', 'EU_DEFAULT'
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** product-embedded-emissions · `CbamProductEmbeddedEmissionsService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_product_embedded_emissions_products`

- **Model:** `CbamProductEmbeddedEmissionsProduct`
- **Purpose:** PEE per-product SEE rows
- **Primary key:** `id`
- **Important columns:** result_id, organization_id, reporting_period_binding_id, product_id, product_profile_version_id, profile_version, cn_normalized_code, cn_display_code, product_name, process_id, process_row_version, process_produced_quantity, process_produced_quantity_unit, denominator_tonnes
- **Foreign keys:** cbam_product_embedded_emissions_results.id; cbam_product_profile_versions.id; cbam_direct_emissions_allocation_results.id; cbam_indirect_emissions_allocation_results.id
- **Unique constraints:** "result_id",             "product_profile_version_id",             name="uq_cbam_pee_products_result_profile", | "id", "result_id", name="uq_cbam_pee_products_id_result"
- **Check constraints:** "result_unit = 'tCO2e'" | "specific_unit = 'tCO2e/t'" | "dea_source_unit = 'tCO2'" | "denominator_tonnes > 0" | "exported_electricity_direct_tco2e <= 0" | "precursor_contribution_count >= 0 AND production_record_count >= 0 "             "AND internal_contribution_count >= 0"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** product-embedded-emissions · `CbamProductEmbeddedEmissionsService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_product_embedded_emissions_results`

- **Model:** `CbamProductEmbeddedEmissionsResult`
- **Purpose:** Product embedded emissions (SEE) results
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, methodology_code, methodology_version, workbook_filename, workbook_sha256, workbook_formula_refs, client_request_id, request_fingerprint, status, product_count, precursor_contribution_count, internal_contribution_count, total_direct_tco2e_raw
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_direct_emissions_allocation_results.id; cbam_indirect_emissions_allocation_results.id; users.id
- **Unique constraints:** "organization_id",             "reporting_period_binding_id",             "client_request_id",             name="uq_cbam_pee_result_org_binding_client_request", | "id",             "organization_id",             "reporting_period_binding_id",             name="uq_cbam_pee_result_id_org_binding",
- **Check constraints:** "status = 'COMPLETED'" | "result_unit = 'tCO2e'" | "specific_unit = 'tCO2e/t'" | "dea_source_unit = 'tCO2'" | "product_count >= 1 AND precursor_contribution_count >= 0 "             "AND internal_contribution_count >= 0"
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** product-embedded-emissions · `CbamProductEmbeddedEmissionsService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_product_profile_versions`

- **Model:** `CbamProductProfileVersion`
- **Purpose:** Versioned CN/AGC/steel attributes; publish lifecycle
- **Primary key:** `id`
- **Important columns:** organization_id, product_id, version, status, valid_from, valid_to, classification_ready, product_name, cn_code_id, cn_normalized_code, cn_display_code, cn_description, cn_sector, cn_dataset_code
- **Foreign keys:** organizations.id; products.id; cbam_cn_codes.id; users.id; users.id
- **Unique constraints:** "organization_id",             "product_id",             "version",             name="uq_cbam_product_profile_org_product_version",
- **Check constraints:** "status IN ('draft', 'active', 'superseded', 'archived' | "version >= 1" | "row_version >= 1" | "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** product-profiles · `CbamProductProfileService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_production_process_product_uses`

- **Model:** `CbamProductionProcessProductUse`
- **Purpose:** Process→product use quantities
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, process_id, target_product_profile_version_id, quantity, unit, notes, row_version, created_by_user_id, updated_by_user_id
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_production_processes.id; cbam_product_profile_versions.id; users.id; users.id
- **Unique constraints:** "process_id",             "target_product_profile_version_id",             name="uq_cbam_ppu_process_target",
- **Check constraints:** "quantity >= 0" | "row_version >= 1"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** production-processes · `CbamProductionProcessService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_production_processes`

- **Model:** `CbamProductionProcess`
- **Purpose:** Production process master for period
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, installation_profile_id, product_profile_version_id, name, identifier, calculation_method, status, produced_quantity, produced_quantity_unit, marketed_quantity, marketed_quantity_unit, non_cbam_quantity, non_cbam_quantity_unit
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_installation_profiles.id; cbam_product_profile_versions.id; users.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status IN ('draft', 'archived' | "calculation_method IN ('CONVENTIONAL', 'PROCESS_EMISSIONS', 'MASS_BALANCE' | "row_version >= 1" | "produced_quantity IS NULL OR produced_quantity >= 0" | "marketed_quantity IS NULL OR marketed_quantity >= 0" | "non_cbam_quantity IS NULL OR non_cbam_quantity >= 0" | "exported_electricity_quantity IS NULL OR exported_electricity_quantity >= 0" | "exported_electricity_emission_factor IS NULL "             "OR exported_electricity_emission_factor >= 0" | "has_exported_electricity IS DISTINCT FROM FALSE OR ("             "exported_electricity_quantity IS NULL "             "AND exported_electricity_unit IS NULL "             "AND exported_electricity_emission_factor IS NULL "             "AN
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** production-processes · `CbamProductionProcessService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_production_records`

- **Model:** `CbamProductionRecord`
- **Purpose:** Produced quantity linked to a product profile version
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, installation_profile_id, product_profile_version_id, production_date, period_start, period_end, quantity, unit, notes, source_type, status, row_version, created_by_user_id
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_installation_profiles.id; cbam_product_profile_versions.id; users.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status IN ('active', 'archived' | "quantity > 0" | "row_version >= 1" | "period_end IS NULL OR period_start IS NULL OR period_end >= period_start"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_purchased_electricity_current_results`

- **Model:** `CbamPurchasedElectricityCurrentResult`
- **Purpose:** Pointer to current PE result
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, activity_record_id, methodology_code, current_result_id
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_activity_records.id; cbam_purchased_electricity_results.id
- **Unique constraints:** "organization_id",             "reporting_period_binding_id",             "activity_record_id",             name="uq_cbam_pe_current_org_binding_activity",
- **Check constraints:** —
- **Lifecycle:** current-pointer
- **Editable / immutable:** pointer-row
- **Current/history/stale:** yes-current-pointer
- **Delete/archive:** replace-pointer
- **Associated screen / API:** purchased-electricity · `CbamPurchasedElectricityService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_purchased_electricity_results`

- **Model:** `CbamPurchasedElectricityResult`
- **Purpose:** PE execution immutable results
- **Primary key:** `id`
- **Important columns:** organization_id, calculation_run_id, calculation_definition_id, reporting_period_binding_id, activity_record_id, methodology_code, methodology_version, formula_version, workbook_formula_refs, client_request_id, request_fingerprint, status, calculation_reference_date, activity_quantity
- **Foreign keys:** organizations.id; cbam_calculation_runs.id; cbam_calculation_definitions.id; cbam_reporting_period_bindings.id; cbam_activity_records.id; cbam_factor_values.id; cbam_factor_definitions.id; users.id
- **Unique constraints:** —
- **Check constraints:** "methodology_code = 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1'" | "factor_source_mode IN ('PLATFORM_DEFAULT', 'MANUAL' | "status = 'COMPLETED'" | "result_unit = 'tCO2e'" | "activity_unit IN ('kWh', 'MWh' | "activity_quantity >= 0" | "electricity_mwh >= 0" | "factor_value >= 0" | "indirect_emissions_tco2e >= 0 AND result_value >= 0" | "("             "exported_electricity_quantity IS NULL AND exported_electricity_unit IS NULL "             "AND exported_electricity_mwh IS NULL"             "
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** purchased-electricity · `CbamPurchasedElectricityService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_purchased_input_records`

- **Model:** `CbamPurchasedInputRecord`
- **Purpose:** Purchased input quantities for a period
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, installation_profile_id, product_profile_version_id, input_name, supplier_name, quantity, unit, received_date, consumed_quantity, consumed_unit, embedded_emission_value, embedded_emission_unit, embedded_emission_source_type
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_installation_profiles.id; cbam_product_profile_versions.id; users.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status IN ('active', 'archived' | "quantity > 0" | "consumed_quantity IS NULL OR consumed_quantity >= 0" | "row_version >= 1"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_purchased_precursor_product_uses`

- **Model:** `CbamPurchasedPrecursorProductUse`
- **Purpose:** Precursor→product use quantities
- **Primary key:** `id`
- **Important columns:** precursor_id, organization_id, reporting_period_binding_id, target_product_profile_version_id, quantity, unit, notes, row_version, created_by_user_id, updated_by_user_id
- **Foreign keys:** cbam_purchased_precursors.id; organizations.id; cbam_reporting_period_bindings.id; cbam_product_profile_versions.id; users.id; users.id
- **Unique constraints:** "precursor_id",             "target_product_profile_version_id",             name="uq_cbam_purch_prec_use_target",
- **Check constraints:** "quantity >= 0" | "row_version >= 1"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** purchased-precursors · `CbamPurchasedPrecursorService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_purchased_precursors`

- **Model:** `CbamPurchasedPrecursor`
- **Purpose:** Purchased precursor declarations (supplier/EU default)
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, installation_profile_id, purchased_input_record_id, supplier_id, name, identifier, aggregated_goods_category, cn_normalized_code, cn_display_code, country_of_origin, production_route, data_source_mode, quantity
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_installation_profiles.id; cbam_purchased_input_records.id; suppliers.id; cbam_precursor_default_datasets.id; cbam_precursor_default_values.id; users.id; users.id
- **Unique constraints:** —
- **Check constraints:** "status IN ('draft', 'archived' | "data_source_mode IN ('SUPPLIER_DATA', 'EU_DEFAULT' | "row_version >= 1" | "quantity IS NULL OR quantity >= 0" | "non_cbam_quantity IS NULL OR non_cbam_quantity >= 0"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** purchased-precursors · `CbamPurchasedPrecursorService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_reference_sources`

- **Model:** `CbamReferenceSource`
- **Purpose:** Reference/provenance sources for factors
- **Primary key:** `id`
- **Important columns:** organization_id, code, name, source_type, publisher, version_label, publication_year, reference_url, description, status, created_by_user_id, updated_by_user_id
- **Foreign keys:** organizations.id; users.id; users.id
- **Unique constraints:** —
- **Check constraints:** "source_type IN ('STANDARD_REFERENCE', 'PRIMARY_MEASUREMENT', "             "'SUPPLIER_DECLARATION', 'MANUAL_APPROVED', 'OTHER' | "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED'
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_reporting_period_bindings`

- **Model:** `CbamReportingPeriodBinding`
- **Purpose:** Binds installation/org to a reporting period with collection status
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_id, status, locked_at, locked_by_user_id, approved_at, approved_calculation_run_id, revision_number, notes, row_version, created_by_user_id, updated_by_user_id
- **Foreign keys:** organizations.id; reporting_periods.id; users.id; users.id; users.id
- **Unique constraints:** "organization_id",             "reporting_period_id",             name="uq_cbam_period_binding_org_period",
- **Check constraints:** "row_version >= 1" | "revision_number >= 0"
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** period-detail.component, period-list.component · `CbamPeriodWorkspaceServices` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_stationary_combustion_current_results`

- **Model:** `CbamStationaryCombustionCurrentResult`
- **Purpose:** Pointer to current SC result per binding
- **Primary key:** `id`
- **Important columns:** organization_id, reporting_period_binding_id, activity_record_id, current_result_id
- **Foreign keys:** organizations.id; cbam_reporting_period_bindings.id; cbam_activity_records.id; cbam_stationary_combustion_results.id
- **Unique constraints:** "organization_id",             "reporting_period_binding_id",             "activity_record_id",             name="uq_cbam_sc_current_org_binding_activity",
- **Check constraints:** —
- **Lifecycle:** current-pointer
- **Editable / immutable:** pointer-row
- **Current/history/stale:** yes-current-pointer
- **Delete/archive:** replace-pointer
- **Associated screen / API:** stationary-combustion · `CbamStationaryCombustionService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_stationary_combustion_fuels`

- **Model:** `CbamStationaryCombustionFuel`
- **Purpose:** Stationary combustion fuel catalog
- **Primary key:** `id`
- **Important columns:** code, name, input_basis, default_activity_unit, status, description
- **Foreign keys:** —
- **Unique constraints:** "code", name="uq_cbam_stationary_combustion_fuel_code"
- **Check constraints:** "input_basis IN ('VOLUME', 'MASS' | "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED' | "default_activity_unit IN ('Sm3', 'm3', 'kg', 't', 'Gg'
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** stationary-combustion · `CbamStationaryCombustionService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_stationary_combustion_parameter_sets`

- **Model:** `CbamStationaryCombustionParameterSet`
- **Purpose:** SC parameter sets (EF/NCV/etc.)
- **Primary key:** `id`
- **Important columns:** fuel_id, dataset_code, dataset_version, valid_from, valid_until, status, net_calorific_value, net_calorific_value_unit, fossil_co2_emission_factor, fossil_co2_emission_factor_unit, oxidation_factor, reference_density, reference_density_unit, ncv_reference_source_id
- **Foreign keys:** cbam_stationary_combustion_fuels.id; cbam_reference_sources.id; cbam_reference_sources.id; cbam_reference_sources.id
- **Unique constraints:** "fuel_id",             "dataset_code",             "dataset_version",             name="uq_cbam_sc_param_fuel_dataset_version",
- **Check constraints:** "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED' | "valid_until IS NULL OR valid_until >= valid_from" | "net_calorific_value > 0" | "net_calorific_value_unit IN ('TJ/Gg' | "fossil_co2_emission_factor > 0" | "fossil_co2_emission_factor_unit IN ('kgCO2/TJ' | "oxidation_factor >= 0" | "("             "reference_density IS NULL AND reference_density_unit IS NULL"             "
- **Lifecycle:** mutable-draft-or-master
- **Editable / immutable:** editable-via-API
- **Current/history/stale:** n/a
- **Delete/archive:** archive-or-restrict-FK
- **Associated screen / API:** stationary-combustion · `CbamStationaryCombustionService` · `cbam-api.service.ts` / `api/v1/cbam.py`

## `cbam_stationary_combustion_results`

- **Model:** `CbamStationaryCombustionResult`
- **Purpose:** SC execution immutable results
- **Primary key:** `id`
- **Important columns:** organization_id, calculation_run_id, calculation_definition_id, reporting_period_binding_id, activity_record_id, fuel_id, parameter_set_id, calculation_type, formula_version, fuel_code, fuel_name, input_basis, activity_quantity, activity_unit
- **Foreign keys:** organizations.id; cbam_calculation_runs.id; cbam_calculation_definitions.id; cbam_reporting_period_bindings.id; cbam_activity_records.id; cbam_stationary_combustion_fuels.id; cbam_stationary_combustion_parameter_sets.id; cbam_reference_sources.id; cbam_reference_sources.id; cbam_reference_sources.id; users.id
- **Unique constraints:** "calculation_run_id",             "activity_record_id",             name="uq_cbam_sc_result_run_activity",
- **Check constraints:** "calculation_type = 'STATIONARY_COMBUSTION_CO2_V1'" | "input_basis IN ('VOLUME', 'MASS' | "activity_quantity > 0" | "net_calorific_value > 0" | "fossil_co2_emission_factor > 0" | "oxidation_factor >= 0" | "("             "density_value IS NULL AND density_unit IS NULL"             " | "valid_until IS NULL OR valid_until >= valid_from" | "result_unit = 'tCO2'" | "fuel_mass_kg >= 0 AND fuel_mass_gg >= 0" | "energy_content_tj >= 0" | "fossil_co2_kg >= 0 AND fossil_co2_tonnes >= 0 AND result_value >= 0"
- **Lifecycle:** immutable-snapshot
- **Editable / immutable:** immutable
- **Current/history/stale:** yes-history-via-new-execution
- **Delete/archive:** no-inplace-keep-history
- **Associated screen / API:** stationary-combustion · `CbamStationaryCombustionService` · `cbam-api.service.ts` / `api/v1/cbam.py`

