# Visible field inventory

Authoritative machine inventory: [`fields.csv`](fields.csv) / [`fields.json`](fields.json).

Discovered / mapped / documented: **419** · Unexplained: **0**

All acceptance columns are present in CSV. Markdown index (subset):

| Screen | Exact UI label | Control | Table | Column | Source type | Service | Guide |
|---|---|---|---|---|---|---|---|
| cbam-shell.component | [display:status-line] | `class="status-line"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamModuleStatusService | user-guide/README.md |
| cbam-shell.component | [display:status-line status-error] | `class="status-line status-error"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamModuleStatusService | user-guide/README.md |
| cbam-shell.component | [display:status-panel] | `class="status-panel"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamModuleStatusService | user-guide/README.md |
| cbam-shell.component | [display:status-kicker] | `class="status-kicker"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamModuleStatusService | user-guide/README.md |
| cbam-shell.component | [display:status-message] | `class="status-message"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamModuleStatusService | user-guide/README.md |
| cbam-shell.component | [display:status-facts] | `class="status-facts"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamModuleStatusService | user-guide/README.md |
| direct-emissions-allocation | created | `table-column:created` | `NOT_PERSISTED` | `created` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | status | `table-column:status` | `cbam_direct_emissions_allocation_results` | `status` | DERIVED_STATUS | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | cbam | `table-column:cbam` | `NOT_PERSISTED` | `cbam` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | allocated | `table-column:allocated` | `NOT_PERSISTED` | `allocated` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | balance | `table-column:balance` | `NOT_PERSISTED` | `balance` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | [display:surface-card readiness-section] | `class="surface-card readiness-section"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | [display:readiness-status] | `class="readiness-status"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | [display:status-text] | `class="status-text"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | [display:readiness-message] | `class="readiness-message"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | [display:readonly-grid readiness-grid] | `class="readonly-grid readiness-grid"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| direct-emissions-allocation | [display:detail-status status-text] | `class="detail-status status-text"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamDirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | created | `table-column:created` | `NOT_PERSISTED` | `created` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | status | `table-column:status` | `cbam_indirect_emissions_allocation_results` | `status` | DERIVED_STATUS | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | cbam | `table-column:cbam` | `NOT_PERSISTED` | `cbam` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | allocated | `table-column:allocated` | `NOT_PERSISTED` | `allocated` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | balance | `table-column:balance` | `NOT_PERSISTED` | `balance` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | [display:surface-card readiness-section] | `class="surface-card readiness-section"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | [display:readiness-status] | `class="readiness-status"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | [display:status-text] | `class="status-text"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | [display:readiness-message] | `class="readiness-message"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | [display:readonly-grid readiness-grid] | `class="readonly-grid readiness-grid"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| indirect-emissions-allocation | [display:detail-status status-text] | `class="detail-status status-text"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamIndirectEmissionsAllocationService | user-guide/12-*.md |
| installation-detail.component | Name | `formControlName=name` | `cbam_installation_profiles` | `name` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-detail.component | Timezone | `formControlName=timezone` | `cbam_installation_profiles` | `timezone` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-detail.component | Operator ID | `formControlName=operatorIdentityRef` | `cbam_installation_profiles` | `operator_identity_ref` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-detail.component | Name | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-detail.component | Timezone | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-detail.component | Operator ID | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-form.component | Facility | `formControlName=facilityId` | `cbam_installation_profiles` | `facility_id` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-form.component | Code | `formControlName=code` | `cbam_installation_profiles` | `code` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-form.component | Name | `formControlName=name` | `cbam_installation_profiles` | `name` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-form.component | Timezone | `formControlName=timezone` | `cbam_installation_profiles` | `timezone` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-form.component | Operator ID (optional) | `formControlName=operatorIdentityRef` | `cbam_installation_profiles` | `operator_identity_ref` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-form.component | Facility | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-form.component | Code | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-form.component | Name | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-form.component | Timezone | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-form.component | Operator ID (optional) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-list.component | Search | `formControlName=search` | `NOT_PERSISTED` | `search` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-list.component | Status | `formControlName=status` | `cbam_installation_profiles` | `status` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-list.component | code | `table-column:code` | `cbam_installation_profiles` | `code` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-list.component | name | `table-column:name` | `cbam_installation_profiles` | `name` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-list.component | status | `table-column:status` | `cbam_installation_profiles` | `status` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-list.component | timezone | `table-column:timezone` | `cbam_installation_profiles` | `timezone` | USER_INPUT | CbamInstallationService | user-guide/README.md |
| installation-list.component | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-list.component | Search | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| installation-list.component | Status | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamInstallationService | user-guide/README.md |
| monthly-allocation-data | Total production | `formControlName=totalProductionQuantity` | `cbam_monthly_production_basis` | `total_production_quantity` | USER_INPUT | CbamMonthlyProductionBasisService | user-guide/05-*.md |
| monthly-allocation-data | Amount sent to the importer | `formControlName=cbamQuantity` | `cbam_monthly_production_basis` | `cbam_quantity` | USER_INPUT | CbamMonthlyProductionBasisService | user-guide/05-*.md |
| monthly-allocation-data | Unit | `formControlName=quantityUnit` | `cbam_monthly_production_basis` | `quantity_unit` | USER_INPUT | CbamMonthlyProductionBasisService | user-guide/05-*.md |
| monthly-allocation-data | Total production | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamMonthlyProductionBasisService | user-guide/05-*.md |
| monthly-allocation-data | Amount sent to the importer | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamMonthlyProductionBasisService | user-guide/05-*.md |
| monthly-allocation-data | Unit | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamMonthlyProductionBasisService | user-guide/05-*.md |
| monthly-allocation-data | [display:status-text] | `class="status-text"` | `NOT_PERSISTED` | `UI_STATUS` | NOT_PERSISTED | CbamMonthlyProductionBasisService | user-guide/05-*.md |
| official-see-export | status | `table-column:status` | `DERIVED_STATUS` | `status` | DERIVED_STATUS | CbamOfficialSeeExportService | user-guide/14-*.md |
| official-see-export | created | `table-column:created` | `NOT_PERSISTED` | `created` | NOT_PERSISTED | CbamOfficialSeeExportService | user-guide/14-*.md |
| official-see-export | template | `table-column:template` | `NOT_PERSISTED` | `template` | NOT_PERSISTED | CbamOfficialSeeExportService | user-guide/14-*.md |
| official-see-export | mapping | `table-column:mapping` | `NOT_PERSISTED` | `mapping` | NOT_PERSISTED | CbamOfficialSeeExportService | user-guide/14-*.md |
| official-see-export | validation | `table-column:validation` | `NOT_PERSISTED` | `validation` | NOT_PERSISTED | CbamOfficialSeeExportService | user-guide/14-*.md |
| official-see-export | parity | `table-column:parity` | `NOT_PERSISTED` | `parity` | NOT_PERSISTED | CbamOfficialSeeExportService | user-guide/14-*.md |
| official-see-export | size | `table-column:size` | `NOT_PERSISTED` | `size` | NOT_PERSISTED | CbamOfficialSeeExportService | user-guide/14-*.md |
| official-see-export | fileName | `table-column:fileName` | `cbam_official_see_export_artifacts` | `file_name` | USER_INPUT | CbamOfficialSeeExportService | user-guide/14-*.md |
| official-see-export | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamOfficialSeeExportService | user-guide/14-*.md |
| period-detail.component | Installation | `formControlName=installationProfileId` | `cbam_production_records` | `installation_profile_id` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Product | `formControlName=productId` | `NOT_PERSISTED` | `product_id` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Product profile | `formControlName=productProfileVersionId` | `cbam_production_records` | `product_profile_version_id` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Quantity | `formControlName=quantity` | `cbam_production_records` | `quantity` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Unit | `formControlName=unit` | `cbam_production_records` | `unit` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Date | `formControlName=productionDate` | `cbam_production_records` | `production_date` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Notes | `formControlName=notes` | `cbam_production_records` | `notes` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Activity Type | `formControlName=activityType` | `cbam_activity_records` | `activity_type` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Data source type | `formControlName=dataSourceType` | `cbam_activity_records` | `data_source_type` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Source Reference | `formControlName=sourceReference` | `cbam_activity_records` | `source_reference` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Measurement Method | `formControlName=measurementMethod` | `cbam_activity_records` | `measurement_method` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Supplier | `formControlName=supplierName` | `cbam_activity_records` | `supplier_name` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Certificate Reference | `formControlName=certificateReference` | `cbam_activity_records` | `certificate_reference` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Input Name | `formControlName=inputName` | `cbam_purchased_input_records` | `input_name` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Purchased Quantity | `formControlName=quantity` | `cbam_production_records` | `quantity` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Consumed Quantity | `formControlName=consumedQuantity` | `cbam_purchased_input_records` | `consumed_quantity` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Consumed Unit | `formControlName=consumedUnit` | `cbam_purchased_input_records` | `consumed_unit` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Embedded Emissions (supplier) | `formControlName=embeddedEmissionValue` | `cbam_purchased_input_records` | `embedded_emission_value` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Embedded Emission Unit | `formControlName=embeddedEmissionUnit` | `cbam_purchased_input_records` | `embedded_emission_unit` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Embedded Emission Source | `formControlName=embeddedEmissionSourceType` | `cbam_purchased_input_records` | `embedded_emission_source_type` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Method | `formControlName=allocationMethod` | `cbam_allocation_results` | `allocation_method` | SNAPSHOT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Name | `formControlName=name` | `cbam_allocation_rules` | `name` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Description | `formControlName=description` | `cbam_allocation_rules` | `description` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Target Production | `formControlName=numeratorProductionRecordId` | `cbam_allocation_rules` | `numerator_production_record_id` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Total Base Production | `formControlName=denominatorProductionRecordId` | `cbam_allocation_rules` | `denominator_production_record_id` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Allocation Ratio (0–1) | `formControlName=allocationRatio` | `cbam_allocation_results` | `allocation_ratio` | SNAPSHOT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Reason | `formControlName=rationale` | `cbam_allocation_rules` | `rationale` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Activity for Allocation | `formControlName=allocateActivityRecordId` | `NOT_PERSISTED` | `allocate_activity_record_id` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Purchased Input for Allocation | `formControlName=allocatePurchasedInputId` | `NOT_PERSISTED` | `allocate_purchased_input_id` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Activity Record | `formControlName=activityRecordId` | `NOT_PERSISTED` | `activity_record_id` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Property | `formControlName=propertyCode` | `cbam_factor_definitions` | `property_code` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Value | `formControlName=numericValue` | `cbam_factor_values` | `numeric_value` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Certificate / Source | `formControlName=sourceReference` | `cbam_activity_records` | `source_reference` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Factor Definition | `formControlName=factorDefinitionCode` | `NOT_PERSISTED` | `factor_definition_code` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Activity | `formControlName=activityRecordId` | `NOT_PERSISTED` | `activity_record_id` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Purchased Input | `formControlName=purchasedInputId` | `NOT_PERSISTED` | `purchased_input_id` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Allocation Result | `formControlName=allocationResultId` | `cbam_calculation_results` | `allocation_result_id` | SNAPSHOT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | installation | `table-column:installation` | `NOT_PERSISTED` | `installation` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | product | `table-column:product` | `NOT_PERSISTED` | `product` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | profile | `table-column:profile` | `NOT_PERSISTED` | `profile` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | profileLink | `table-column:profileLink` | `NOT_PERSISTED` | `profile_link` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | quantity | `table-column:quantity` | `cbam_production_records` | `quantity` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | unit | `table-column:unit` | `cbam_production_records` | `unit` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | date | `table-column:date` | `NOT_PERSISTED` | `date` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | status | `table-column:status` | `cbam_calculation_results` | `status` | SNAPSHOT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | type | `table-column:type` | `NOT_PERSISTED` | `type` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | dataSource | `table-column:dataSource` | `NOT_PERSISTED` | `data_source` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | name | `table-column:name` | `cbam_allocation_rules` | `name` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | consumed | `table-column:consumed` | `NOT_PERSISTED` | `consumed` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | embedded | `table-column:embedded` | `NOT_PERSISTED` | `embedded` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | method | `table-column:method` | `NOT_PERSISTED` | `method` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | ratio | `table-column:ratio` | `NOT_PERSISTED` | `ratio` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | sourceType | `table-column:sourceType` | `cbam_allocation_results` | `source_type` | SNAPSHOT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | sourceQuantity | `table-column:sourceQuantity` | `cbam_allocation_results` | `source_quantity` | SNAPSHOT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | allocated | `table-column:allocated` | `NOT_PERSISTED` | `allocated` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | rule | `table-column:rule` | `NOT_PERSISTED` | `rule` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | created | `table-column:created` | `NOT_PERSISTED` | `created` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | source | `table-column:source` | `NOT_PERSISTED` | `source` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | activity | `table-column:activity` | `NOT_PERSISTED` | `activity` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | factor | `table-column:factor` | `NOT_PERSISTED` | `factor` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | value | `table-column:value` | `NOT_PERSISTED` | `value` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | reference | `table-column:reference` | `NOT_PERSISTED` | `reference` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | factorSource | `table-column:factorSource` | `NOT_PERSISTED` | `factor_source` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | result | `table-column:result` | `NOT_PERSISTED` | `result` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | error | `table-column:error` | `NOT_PERSISTED` | `error` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | template | `table-column:template` | `NOT_PERSISTED` | `template` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | calc | `table-column:calc` | `NOT_PERSISTED` | `calc` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | checksum | `table-column:checksum` | `cbam_export_templates` | `checksum` | USER_INPUT | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Product | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Product profile | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Installation | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Quantity | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Unit | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Date | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Notes | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Activity Type | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Data Source Primary Data Default Reference Unknown Source Reference | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Measurement Method | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Supplier | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Certificate Reference | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Input Name | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Purchased Quantity | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Consumed Quantity | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Consumed Unit | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Embedded Emissions (supplier) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Embedded Emission Unit | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Embedded Emission Source | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Method | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Name | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Description | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Target Production | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Total Base Production | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Allocation Ratio (0–1) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Reason | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Source Reference | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Activity for Allocation | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Purchased Input for Allocation | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Activity Record | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Property | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Value | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Certificate / Source | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Factor Definition | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Activity | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Purchased Input | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Allocation Result | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | Template | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-detail.component | [display:full-width readiness-table] | `class="full-width readiness-table"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamPeriodWorkspaceServices | user-guide/README.md |
| period-list.component | Reporting Period | `formControlName=reportingPeriodId` | `cbam_reporting_period_bindings` | `reporting_period_id` | USER_INPUT | CbamReportingPeriodBindingService | user-guide/README.md |
| period-list.component | reportingPeriodId | `table-column:reportingPeriodId` | `cbam_reporting_period_bindings` | `reporting_period_id` | USER_INPUT | CbamReportingPeriodBindingService | user-guide/README.md |
| period-list.component | status | `table-column:status` | `cbam_reporting_period_bindings` | `status` | USER_INPUT | CbamReportingPeriodBindingService | user-guide/README.md |
| period-list.component | revisionNumber | `table-column:revisionNumber` | `cbam_reporting_period_bindings` | `revision_number` | USER_INPUT | CbamReportingPeriodBindingService | user-guide/README.md |
| period-list.component | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamReportingPeriodBindingService | user-guide/README.md |
| period-list.component | Reporting Period | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamReportingPeriodBindingService | user-guide/README.md |
| product-embedded-emissions | product | `table-column:product` | `NOT_PERSISTED` | `product` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | cn | `table-column:cn` | `NOT_PERSISTED` | `cn` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | profile | `table-column:profile` | `NOT_PERSISTED` | `profile` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | output | `table-column:output` | `NOT_PERSISTED` | `output` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | direct | `table-column:direct` | `NOT_PERSISTED` | `direct` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | indirect | `table-column:indirect` | `NOT_PERSISTED` | `indirect` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | total | `table-column:total` | `NOT_PERSISTED` | `total` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | specificDirect | `table-column:specificDirect` | `cbam_product_embedded_emissions_products` | `specific_direct` | USER_INPUT | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | specificIndirect | `table-column:specificIndirect` | `cbam_product_embedded_emissions_products` | `specific_indirect` | USER_INPUT | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | specificTotal | `table-column:specificTotal` | `cbam_product_embedded_emissions_products` | `specific_total` | USER_INPUT | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | status | `table-column:status` | `cbam_product_embedded_emissions_results` | `status` | DERIVED_STATUS | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | created | `table-column:created` | `NOT_PERSISTED` | `created` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | method | `table-column:method` | `NOT_PERSISTED` | `method` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | products | `table-column:products` | `NOT_PERSISTED` | `products` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | [display:surface-card readiness-section] | `class="surface-card readiness-section"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | [display:readiness-status] | `class="readiness-status"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | [display:status-text] | `class="status-text"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | [display:readiness-message] | `class="readiness-message"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | [display:readonly-grid readiness-grid] | `class="readonly-grid readiness-grid"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-embedded-emissions | [display:detail-status status-text] | `class="detail-status status-text"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamProductEmbeddedEmissionsService | user-guide/11-*.md |
| product-profiles | Profile name | `formControlName=productName` | `cbam_product_profile_versions` | `product_name` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | CN code | `formControlName=cnSearch` | `NOT_PERSISTED` | `cn_search` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Reducing material | `formControlName=reducingAgent` | `cbam_product_profile_versions` | `reducing_agent` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Steel mill ID | `formControlName=steelMillIdentificationNumber` | `cbam_product_profile_versions` | `steel_mill_identification_number` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Manganese (Mn), % | `formControlName=percentMn` | `cbam_product_profile_versions` | `percent_mn` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Chromium (Cr), % | `formControlName=percentCr` | `cbam_product_profile_versions` | `percent_cr` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Nickel (Ni), % | `formControlName=percentNi` | `cbam_product_profile_versions` | `percent_ni` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Other alloys, % | `formControlName=percentOtherAlloys` | `cbam_product_profile_versions` | `percent_other_alloys` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Other materials, % | `formControlName=percentOtherMaterials` | `cbam_product_profile_versions` | `percent_other_materials` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Valid from | `formControlName=validFrom` | `cbam_product_profile_versions` | `valid_from` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Valid to | `formControlName=validTo` | `cbam_product_profile_versions` | `valid_to` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | version | `table-column:version` | `cbam_product_profile_versions` | `version` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | status | `table-column:status` | `cbam_product_profile_versions` | `status` | USER_INPUT | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | cn | `table-column:cn` | `NOT_PERSISTED` | `cn` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | ready | `table-column:ready` | `NOT_PERSISTED` | `ready` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Profile name | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | CN code | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Reducing material | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Steel mill ID | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Manganese (Mn), % | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Chromium (Cr), % | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Nickel (Ni), % | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Other alloys, % | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Other materials, % | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Valid from | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | Valid to | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | [display:status-row] | `class="status-row"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamProductProfileService | user-guide/04-*.md |
| product-profiles | [display:readiness-summary] | `class="readiness-summary"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamProductProfileService | user-guide/04-*.md |
| production-processes | Installation | `formControlName=installationProfileId` | `cbam_production_processes` | `installation_profile_id` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Process name | `formControlName=name` | `cbam_production_processes` | `name` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Process identifier | `formControlName=identifier` | `cbam_production_processes` | `identifier` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Product profile | `formControlName=productProfileVersionId` | `cbam_production_processes` | `product_profile_version_id` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Calculation method | `formControlName=calculationMethod` | `cbam_production_processes` | `calculation_method` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Produced quantity | `formControlName=producedQuantity` | `cbam_production_processes` | `produced_quantity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Unit | `formControlName=producedQuantityUnit` | `cbam_production_processes` | `produced_quantity_unit` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Quantity | `formControlName=marketedQuantity` | `cbam_production_processes` | `marketed_quantity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Unit | `formControlName=marketedQuantityUnit` | `cbam_production_processes` | `marketed_quantity_unit` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Target product | `formControlName=targetProductProfileVersionId` | `cbam_production_process_product_uses` | `target_product_profile_version_id` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Quantity | `formControlName=quantity` | `cbam_production_process_product_uses` | `quantity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Unit | `formControlName=unit` | `cbam_production_process_product_uses` | `unit` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Quantity | `formControlName=nonCbamQuantity` | `cbam_production_processes` | `non_cbam_quantity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Unit | `formControlName=nonCbamQuantityUnit` | `cbam_production_processes` | `non_cbam_quantity_unit` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Has measurable heat | `formControlName=hasMeasurableHeat` | `cbam_production_processes` | `has_measurable_heat` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Imported heat amount ({{ heatQuantityUnit }}) | `formControlName=heatImportedQuantity` | `cbam_production_processes` | `heat_imported_quantity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Imported heat factor ({{ heatFactorUnit }}) | `formControlName=heatImportedEf` | `cbam_production_processes` | `heat_imported_ef` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Exported heat amount ({{ heatQuantityUnit }}) | `formControlName=heatExportedQuantity` | `cbam_production_processes` | `heat_exported_quantity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Exported heat factor ({{ heatFactorUnit }}) | `formControlName=heatExportedEf` | `cbam_production_processes` | `heat_exported_ef` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Factor source | `formControlName=heatFactorSource` | `cbam_production_processes` | `heat_factor_source` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Factor document | `formControlName=heatFactorDocument` | `cbam_production_processes` | `heat_factor_document` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Has waste gas | `formControlName=hasWasteGas` | `cbam_production_processes` | `has_waste_gas` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Imported waste gas ({{ wasteGasQuantityUnit }}) | `formControlName=wasteGasImportedQuantity` | `cbam_production_processes` | `waste_gas_imported_quantity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Exported waste gas ({{ wasteGasQuantityUnit }}) | `formControlName=wasteGasExportedQuantity` | `cbam_production_processes` | `waste_gas_exported_quantity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Provenance | `formControlName=wasteGasProvenance` | `cbam_production_processes` | `waste_gas_provenance` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Has exported electricity | `formControlName=hasExportedElectricity` | `cbam_production_processes` | `has_exported_electricity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Exported quantity ({{ exportedElectricityQuantityUnit }}) | `formControlName=exportedElectricityQuantity` | `cbam_production_processes` | `exported_electricity_quantity` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Emission factor ({{ exportedElectricityFactorUnit }}) | `formControlName=exportedElectricityEmissionFacto` | `cbam_production_processes` | `exported_electricity_emission_factor` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Provenance | `formControlName=exportedElectricityProvenance` | `cbam_production_processes` | `exported_electricity_provenance` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Data quality | `formControlName=dataQualityCode` | `cbam_production_processes` | `data_quality_code` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Data verification | `formControlName=dataVerificationCode` | `cbam_production_processes` | `data_verification_code` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Data quality justification | `formControlName=dataQualityJustificationCode` | `cbam_production_processes` | `data_quality_justification_code` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Notes | `formControlName=notes` | `cbam_production_processes` | `notes` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | name | `table-column:name` | `cbam_production_processes` | `name` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | product | `table-column:product` | `NOT_PERSISTED` | `product` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | method | `table-column:method` | `NOT_PERSISTED` | `method` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | status | `table-column:status` | `cbam_production_processes` | `status` | USER_INPUT | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | balance | `table-column:balance` | `DERIVED_STATUS` | `balance` | DERIVED_STATUS | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Installation | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Process name | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Process identifier | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Product profile | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Produced quantity | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Unit | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Quantity | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Target product | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Imported heat amount ({{ heatQuantityUnit }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Imported heat factor ({{ heatFactorUnit }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Exported heat amount ({{ heatQuantityUnit }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Exported heat factor ({{ heatFactorUnit }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Factor source | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Factor document | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Imported waste gas ({{ wasteGasQuantityUnit }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Exported waste gas ({{ wasteGasQuantityUnit }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Provenance | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Exported quantity ({{ exportedElectricityQuantityUnit }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Emission factor ({{ exportedElectricityFactorUnit }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Data quality | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Data verification | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Data quality justification | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | Notes | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamProductionProcessService | user-guide/09-*.md |
| production-processes | [display:result-badge] | `class="result-badge"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamProductionProcessService | user-guide/09-*.md |
| purchased-electricity | Electricity record | `formControlName=activityRecordId` | `cbam_purchased_electricity_results` | `activity_record_id` | USER_INPUT | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Factor source mode | `formControlName=factorSourceMode` | `cbam_purchased_electricity_results` | `factor_source_mode` | SNAPSHOT | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Factor value | `formControlName=manualValue` | `cbam_purchased_electricity_results` | `factor_value_snapshot` | MANUAL_OVERRIDE | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Factor unit | `formControlName=manualUnit` | `NOT_PERSISTED` | `manual_unit` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Source name | `formControlName=sourceName` | `NOT_PERSISTED` | `source_name` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Source document | `formControlName=sourceDocument` | `NOT_PERSISTED` | `source_document` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Dataset / version | `formControlName=datasetVersion` | `NOT_PERSISTED` | `dataset_version` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Reference description | `formControlName=referenceDescription` | `NOT_PERSISTED` | `reference_description` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Effective / reference date | `formControlName=effectiveDate` | `NOT_PERSISTED` | `effective_date` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Exported electricity | `formControlName=exportedQuantity` | `NOT_PERSISTED` | `exported_quantity` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Unit | `formControlName=exportedUnit` | `NOT_PERSISTED` | `exported_unit` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Evidence notes | `formControlName=evidenceNotes` | `cbam_purchased_electricity_results` | `evidence_notes` | SNAPSHOT | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | created | `table-column:created` | `NOT_PERSISTED` | `created` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | electricity | `table-column:electricity` | `NOT_PERSISTED` | `electricity` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | factorSource | `table-column:factorSource` | `NOT_PERSISTED` | `factor_source` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | factor | `table-column:factor` | `NOT_PERSISTED` | `factor` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | emissions | `table-column:emissions` | `NOT_PERSISTED` | `emissions` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | status | `table-column:status` | `cbam_purchased_electricity_results` | `status` | DERIVED_STATUS | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Electricity record | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Factor value | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Factor unit | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Source name | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Source document | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Dataset / version | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Reference description | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Effective / reference date | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Exported electricity | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Unit | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | Evidence notes | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-electricity | [display:result-badge] | `class="result-badge"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamPurchasedElectricityService | user-guide/08-*.md |
| purchased-precursors | Installation | `formControlName=installationProfileId` | `cbam_purchased_precursors` | `installation_profile_id` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Precursor name | `formControlName=name` | `cbam_purchased_precursors` | `name` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Precursor name | `formControlName=dataSourceMode` | `cbam_purchased_precursors` | `data_source_mode` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Identifier | `formControlName=identifier` | `cbam_purchased_precursors` | `identifier` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Aggregated goods category | `formControlName=aggregatedGoodsCategory` | `cbam_purchased_precursors` | `aggregated_goods_category` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Purchased input record | `formControlName=purchasedInputRecordId` | `cbam_purchased_precursors` | `purchased_input_record_id` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Supplier | `formControlName=supplierId` | `cbam_purchased_precursors` | `supplier_id` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | CN code | `formControlName=cnSearch` | `NOT_PERSISTED` | `cn_search` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Country of origin | `formControlName=countryOfOrigin` | `cbam_purchased_precursors` | `country_of_origin` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Production route | `formControlName=productionRoute` | `cbam_purchased_precursors` | `production_route` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Purchased quantity | `formControlName=quantity` | `cbam_purchased_precursors` | `quantity` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Unit | `formControlName=quantityUnit` | `cbam_purchased_precursors` | `quantity_unit` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Data source mode | `formControlName=dataSourceMode` | `cbam_purchased_precursors` | `data_source_mode` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Specific direct embedded emissions ({{ specificDirectUnit() }}) | `formControlName=specificDirectEmbeddedEmissions` | `cbam_purchased_precursors` | `specific_direct_embedded_emissions` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Direct value source | `formControlName=specificDirectSourceCode` | `cbam_purchased_precursors` | `specific_direct_source_code` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Electricity consumption intensity ({{ electricityIntensityUnit() }}) | `formControlName=electricityConsumptionIntensity` | `cbam_purchased_precursors` | `electricity_consumption_intensity` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Electricity intensity source | `formControlName=electricityIntensitySourceCode` | `cbam_purchased_precursors` | `electricity_intensity_source_code` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Electricity emission factor ({{ electricityEfUnit() }}) | `formControlName=electricityEmissionFactor` | `cbam_purchased_precursors` | `electricity_emission_factor` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Electricity factor source | `formControlName=electricityEfSourceCode` | `cbam_purchased_precursors` | `electricity_ef_source_code` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Country | `formControlName=country` | `NOT_PERSISTED` | `country` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | CN code | `formControlName=cn` | `NOT_PERSISTED` | `cn` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Production route | `formControlName=route` | `NOT_PERSISTED` | `route` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Goods description | `formControlName=description` | `NOT_PERSISTED` | `description` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Goods description | `formControlName=includeOtherCountries` | `NOT_PERSISTED` | `include_other_countries` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Justification for using a default value | `formControlName=defaultJustificationCode` | `cbam_purchased_precursors` | `default_justification_code` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Provenance notes | `formControlName=provenanceNotes` | `cbam_purchased_precursors` | `provenance_notes` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Evidence reference | `formControlName=evidenceReference` | `cbam_purchased_precursors` | `evidence_reference` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Target product | `formControlName=targetProductProfileVersionId` | `cbam_purchased_precursor_product_uses` | `target_product_profile_version_id` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Quantity | `formControlName=quantity` | `cbam_purchased_precursors` | `quantity` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Unit | `formControlName=unit` | `cbam_purchased_precursor_product_uses` | `unit` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Quantity | `formControlName=nonCbamQuantity` | `cbam_purchased_precursors` | `non_cbam_quantity` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Unit | `formControlName=nonCbamQuantityUnit` | `cbam_purchased_precursors` | `non_cbam_quantity_unit` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Notes | `formControlName=notes` | `cbam_purchased_precursors` | `notes` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | name | `table-column:name` | `cbam_purchased_precursors` | `name` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | mode | `table-column:mode` | `NOT_PERSISTED` | `mode` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | quantity | `table-column:quantity` | `cbam_purchased_precursors` | `quantity` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | status | `table-column:status` | `cbam_purchased_precursors` | `status` | USER_INPUT | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | balance | `table-column:balance` | `DERIVED_STATUS` | `balance` | DERIVED_STATUS | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | identity | `table-column:identity` | `NOT_PERSISTED` | `identity` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | direct | `table-column:direct` | `NOT_PERSISTED` | `direct` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | indirect | `table-column:indirect` | `NOT_PERSISTED` | `indirect` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Installation | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Precursor name | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Identifier | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Aggregated goods category | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Purchased input record | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Supplier | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | CN code | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Country of origin | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Production route | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Purchased quantity | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Unit | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Specific direct embedded emissions ({{ specificDirectUnit() }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Direct value source | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Electricity consumption intensity ({{ electricityIntensityUnit() }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Electricity intensity source | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Electricity emission factor ({{ electricityEfUnit() }}) | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Electricity factor source | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Country | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Goods description | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Justification for using a default value | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Provenance notes | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Evidence reference | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Target product | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Quantity | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | Notes | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamPurchasedPrecursorService | user-guide/10-*.md |
| purchased-precursors | [display:result-badge] | `class="result-badge"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamPurchasedPrecursorService | user-guide/10-*.md |
| stationary-combustion | Fuel use record | `formControlName=activityRecordId` | `cbam_stationary_combustion_results` | `activity_record_id` | USER_INPUT | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | Calculation date | `formControlName=calculationReferenceDate` | `cbam_stationary_combustion_results` | `calculation_reference_date` | SNAPSHOT | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | Density | `formControlName=densityValue` | `cbam_stationary_combustion_results` | `density_value` | SNAPSHOT | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | Density unit | `formControlName=densityUnit` | `cbam_stationary_combustion_results` | `density_unit` | USER_INPUT | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | fuel | `table-column:fuel` | `NOT_PERSISTED` | `fuel` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | activities | `table-column:activities` | `NOT_PERSISTED` | `activities` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | mass | `table-column:mass` | `NOT_PERSISTED` | `mass` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | energy | `table-column:energy` | `NOT_PERSISTED` | `energy` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | fossilCo2 | `table-column:fossilCo2` | `NOT_PERSISTED` | `fossil_co2` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | final | `table-column:final` | `NOT_PERSISTED` | `final` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | status | `table-column:status` | `cbam_activity_records` | `status` | SNAPSHOT | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | date | `table-column:date` | `NOT_PERSISTED` | `date` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | amount | `table-column:amount` | `NOT_PERSISTED` | `amount` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | dataset | `table-column:dataset` | `NOT_PERSISTED` | `dataset` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | actions | `table-column:actions` | `NOT_PERSISTED` | `actions` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | Fuel use record | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | Calculation date | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | Density | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | Density unit | `mat-label` | `NOT_PERSISTED` | `UI_ONLY` | NOT_PERSISTED | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | [display:summary-status] | `class="summary-status"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | [display:status-text] | `class="status-text"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamStationaryCombustionService | user-guide/07-*.md |
| stationary-combustion | [display:result-badge] | `class="result-badge"` | `DERIVED_STATUS` | `UI_STATUS` | DERIVED_STATUS | CbamStationaryCombustionService | user-guide/07-*.md |
