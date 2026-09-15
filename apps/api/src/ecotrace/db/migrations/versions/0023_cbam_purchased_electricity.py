"""CBAM Phase 8A: purchased-electricity indirect emissions results + current pointer.

Revision ID: 0023_cbam_purchased_electricity
Revises: 0022_cbam_dea_allocation
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0023_cbam_purchased_electricity"
down_revision: str | None = "0022_cbam_dea_allocation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
ALTER TABLE cbam_calculation_definitions
    DROP CONSTRAINT IF EXISTS calc_def_type;
ALTER TABLE cbam_calculation_definitions
    DROP CONSTRAINT IF EXISTS calc_def_factor_req;
ALTER TABLE cbam_calculation_definitions
    DROP CONSTRAINT IF EXISTS ck_cbam_calc_def_type;
ALTER TABLE cbam_calculation_definitions
    DROP CONSTRAINT IF EXISTS ck_cbam_calc_def_factor_req;
ALTER TABLE cbam_calculation_definitions
    ADD CONSTRAINT calc_def_type CHECK (
        calculation_type IN (
            'MULTIPLY_ACTIVITY_BY_FACTOR',
            'STATIONARY_COMBUSTION_CO2_V1',
            'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1'
        )
    );
ALTER TABLE cbam_calculation_definitions
    ADD CONSTRAINT calc_def_factor_req CHECK (
        (
            calculation_type = 'MULTIPLY_ACTIVITY_BY_FACTOR'
            AND factor_definition_id IS NOT NULL
        ) OR (
            calculation_type = 'STATIONARY_COMBUSTION_CO2_V1'
            AND factor_definition_id IS NULL
        ) OR (
            calculation_type = 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1'
            AND factor_definition_id IS NULL
        )
    );
"""
    )
    op.execute(
        """
CREATE TABLE cbam_purchased_electricity_results (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    calculation_run_id UUID NOT NULL,
    calculation_definition_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    activity_record_id UUID NOT NULL,
    methodology_code VARCHAR(128) NOT NULL,
    methodology_version VARCHAR(32) NOT NULL,
    formula_version VARCHAR(64) NOT NULL,
    workbook_formula_refs TEXT NOT NULL,
    client_request_id UUID NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    calculation_reference_date DATE NOT NULL,
    activity_quantity NUMERIC(24, 8) NOT NULL,
    activity_unit VARCHAR(32) NOT NULL,
    electricity_mwh NUMERIC(36, 18) NOT NULL,
    factor_source_mode VARCHAR(32) NOT NULL,
    factor_value NUMERIC(24, 8) NOT NULL,
    factor_unit VARCHAR(64) NOT NULL,
    factor_tco2e_per_mwh NUMERIC(36, 18) NOT NULL,
    factor_value_id UUID,
    factor_definition_id UUID,
    factor_source_name VARCHAR(255) NOT NULL,
    factor_source_document TEXT NOT NULL,
    factor_dataset_version VARCHAR(128) NOT NULL,
    factor_reference_description TEXT NOT NULL,
    factor_effective_date DATE,
    factor_valid_from DATE,
    factor_valid_until DATE,
    exported_electricity_quantity NUMERIC(24, 8),
    exported_electricity_unit VARCHAR(32),
    exported_electricity_mwh NUMERIC(36, 18),
    indirect_emissions_tco2e NUMERIC(24, 8) NOT NULL,
    result_value NUMERIC(24, 8) NOT NULL,
    result_unit VARCHAR(32) NOT NULL,
    evidence_notes TEXT,
    created_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_pe_results PRIMARY KEY (id),
    CONSTRAINT fk_cbam_pe_results_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_pe_results_run
        FOREIGN KEY (calculation_run_id) REFERENCES cbam_calculation_runs (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pe_results_def
        FOREIGN KEY (calculation_definition_id)
        REFERENCES cbam_calculation_definitions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pe_results_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pe_results_activity
        FOREIGN KEY (activity_record_id) REFERENCES cbam_activity_records (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pe_results_factor_value
        FOREIGN KEY (factor_value_id) REFERENCES cbam_factor_values (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_pe_results_factor_def
        FOREIGN KEY (factor_definition_id)
        REFERENCES cbam_factor_definitions (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_pe_results_created_by
        FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT pe_result_methodology
        CHECK (methodology_code = 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1'),
    CONSTRAINT pe_result_factor_mode
        CHECK (factor_source_mode IN ('PLATFORM_DEFAULT', 'MANUAL')),
    CONSTRAINT pe_result_status CHECK (status = 'COMPLETED'),
    CONSTRAINT pe_result_unit CHECK (result_unit = 'tCO2e'),
    CONSTRAINT pe_result_activity_unit CHECK (activity_unit IN ('kWh', 'MWh')),
    CONSTRAINT pe_result_activity_qty_nonneg CHECK (activity_quantity >= 0),
    CONSTRAINT pe_result_mwh_nonneg CHECK (electricity_mwh >= 0),
    CONSTRAINT pe_result_factor_nonneg CHECK (factor_value >= 0),
    CONSTRAINT pe_result_emissions_nonneg
        CHECK (indirect_emissions_tco2e >= 0 AND result_value >= 0),
    CONSTRAINT pe_result_exported_pair CHECK (
        (
            exported_electricity_quantity IS NULL
            AND exported_electricity_unit IS NULL
            AND exported_electricity_mwh IS NULL
        ) OR (
            exported_electricity_quantity IS NOT NULL
            AND exported_electricity_unit IS NOT NULL
            AND exported_electricity_mwh IS NOT NULL
            AND exported_electricity_unit IN ('kWh', 'MWh')
            AND exported_electricity_quantity >= 0
            AND exported_electricity_mwh >= 0
        )
    )
);
CREATE INDEX ix_cbam_pe_results_organization_id
    ON cbam_purchased_electricity_results (organization_id);
CREATE INDEX ix_cbam_pe_results_binding_id
    ON cbam_purchased_electricity_results (reporting_period_binding_id);
CREATE INDEX ix_cbam_pe_results_activity_id
    ON cbam_purchased_electricity_results (activity_record_id);
CREATE INDEX ix_cbam_pe_results_run_id
    ON cbam_purchased_electricity_results (calculation_run_id);
CREATE INDEX ix_cbam_pe_results_client_request_id
    ON cbam_purchased_electricity_results (client_request_id);
CREATE UNIQUE INDEX uq_cbam_pe_result_org_binding_client_request
    ON cbam_purchased_electricity_results (
        organization_id, reporting_period_binding_id, client_request_id
    );
CREATE UNIQUE INDEX uq_cbam_pe_result_id_org_binding_activity
    ON cbam_purchased_electricity_results (
        id, organization_id, reporting_period_binding_id, activity_record_id
    );
"""
    )
    op.execute(
        """
CREATE TABLE cbam_purchased_electricity_current_results (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    activity_record_id UUID NOT NULL,
    methodology_code VARCHAR(128) NOT NULL,
    current_result_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_pe_current PRIMARY KEY (id),
    CONSTRAINT uq_cbam_pe_current_org_binding_activity UNIQUE (
        organization_id, reporting_period_binding_id, activity_record_id
    ),
    CONSTRAINT fk_cbam_pe_current_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_pe_current_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pe_current_activity
        FOREIGN KEY (activity_record_id) REFERENCES cbam_activity_records (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pe_current_result
        FOREIGN KEY (current_result_id)
        REFERENCES cbam_purchased_electricity_results (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pe_current_result_identity
        FOREIGN KEY (
            current_result_id,
            organization_id,
            reporting_period_binding_id,
            activity_record_id
        )
        REFERENCES cbam_purchased_electricity_results (
            id, organization_id, reporting_period_binding_id, activity_record_id
        ) ON DELETE RESTRICT
);
CREATE INDEX ix_cbam_pe_current_organization_id
    ON cbam_purchased_electricity_current_results (organization_id);
CREATE INDEX ix_cbam_pe_current_binding_id
    ON cbam_purchased_electricity_current_results (reporting_period_binding_id);
CREATE INDEX ix_cbam_pe_current_result_id
    ON cbam_purchased_electricity_current_results (current_result_id);
"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cbam_purchased_electricity_current_results")
    op.execute("DROP TABLE IF EXISTS cbam_purchased_electricity_results")
    op.execute(
        """
ALTER TABLE cbam_calculation_definitions
    DROP CONSTRAINT IF EXISTS calc_def_type;
ALTER TABLE cbam_calculation_definitions
    DROP CONSTRAINT IF EXISTS calc_def_factor_req;
ALTER TABLE cbam_calculation_definitions
    ADD CONSTRAINT calc_def_type CHECK (
        calculation_type IN (
            'MULTIPLY_ACTIVITY_BY_FACTOR',
            'STATIONARY_COMBUSTION_CO2_V1'
        )
    );
ALTER TABLE cbam_calculation_definitions
    ADD CONSTRAINT calc_def_factor_req CHECK (
        (
            calculation_type = 'MULTIPLY_ACTIVITY_BY_FACTOR'
            AND factor_definition_id IS NOT NULL
        ) OR (
            calculation_type = 'STATIONARY_COMBUSTION_CO2_V1'
            AND factor_definition_id IS NULL
        )
    );
"""
    )
