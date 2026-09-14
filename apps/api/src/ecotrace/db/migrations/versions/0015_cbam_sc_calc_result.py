"""CBAM Phase 3 stationary-combustion calculation result snapshot."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0015_cbam_sc_calc_result'
down_revision: str | None = '0014_cbam_sc_fuel_catalog'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Allow STATIONARY_COMBUSTION_CO2_V1 definitions without a factor definition.
    op.execute(
        'ALTER TABLE cbam_calculation_definitions '
        'DROP CONSTRAINT IF EXISTS ck_cbam_calculation_definitions_calculation_definition_type'
    )
    op.execute(
        """
ALTER TABLE cbam_calculation_definitions
ADD CONSTRAINT ck_cbam_calc_def_type
CHECK (calculation_type IN (
    'MULTIPLY_ACTIVITY_BY_FACTOR',
    'STATIONARY_COMBUSTION_CO2_V1'
))
"""
    )
    op.execute(
        'ALTER TABLE cbam_calculation_definitions '
        'ALTER COLUMN factor_definition_id DROP NOT NULL'
    )
    op.execute(
        """
ALTER TABLE cbam_calculation_definitions
ADD CONSTRAINT ck_cbam_calc_def_factor_req
CHECK (
    (
        calculation_type = 'MULTIPLY_ACTIVITY_BY_FACTOR'
        AND factor_definition_id IS NOT NULL
    )
    OR (
        calculation_type = 'STATIONARY_COMBUSTION_CO2_V1'
        AND factor_definition_id IS NULL
    )
)
"""
    )

    op.execute(
        """
CREATE TABLE cbam_stationary_combustion_results (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    calculation_run_id UUID NOT NULL,
    calculation_definition_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    activity_record_id UUID NOT NULL,
    fuel_id UUID NOT NULL,
    parameter_set_id UUID NOT NULL,
    calculation_type VARCHAR(64) NOT NULL,
    formula_version VARCHAR(64) NOT NULL,
    fuel_code VARCHAR(64) NOT NULL,
    fuel_name VARCHAR(255) NOT NULL,
    input_basis VARCHAR(16) NOT NULL,
    activity_quantity NUMERIC(24, 8) NOT NULL,
    activity_unit VARCHAR(32) NOT NULL,
    density_value NUMERIC(24, 8),
    density_unit VARCHAR(32),
    net_calorific_value NUMERIC(24, 8) NOT NULL,
    net_calorific_value_unit VARCHAR(32) NOT NULL,
    fossil_co2_emission_factor NUMERIC(24, 8) NOT NULL,
    fossil_co2_emission_factor_unit VARCHAR(32) NOT NULL,
    oxidation_factor NUMERIC(24, 12) NOT NULL,
    dataset_code VARCHAR(64) NOT NULL,
    dataset_version VARCHAR(64) NOT NULL,
    valid_from DATE NOT NULL,
    valid_until DATE,
    ncv_reference_source_id UUID NOT NULL,
    ncv_source_document TEXT NOT NULL,
    ncv_source_table VARCHAR(255) NOT NULL,
    co2_reference_source_id UUID NOT NULL,
    co2_source_document TEXT NOT NULL,
    co2_source_table VARCHAR(255) NOT NULL,
    oxidation_reference_source_id UUID NOT NULL,
    oxidation_source_document TEXT NOT NULL,
    oxidation_source_table VARCHAR(255) NOT NULL,
    fuel_mass_kg NUMERIC(36, 18) NOT NULL,
    fuel_mass_gg NUMERIC(36, 18) NOT NULL,
    energy_content_tj NUMERIC(36, 18) NOT NULL,
    fossil_co2_kg NUMERIC(36, 18) NOT NULL,
    fossil_co2_tonnes NUMERIC(36, 18) NOT NULL,
    result_value NUMERIC(24, 8) NOT NULL,
    result_unit VARCHAR(32) NOT NULL,
    created_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_stationary_combustion_results PRIMARY KEY (id),
    CONSTRAINT uq_cbam_sc_result_run_activity
        UNIQUE (calculation_run_id, activity_record_id),
    CONSTRAINT ck_cbam_sc_result_type
        CHECK (calculation_type = 'STATIONARY_COMBUSTION_CO2_V1'),
    CONSTRAINT ck_cbam_sc_result_input_basis
        CHECK (input_basis IN ('VOLUME', 'MASS')),
    CONSTRAINT ck_cbam_sc_result_activity_qty_pos
        CHECK (activity_quantity > 0),
    CONSTRAINT ck_cbam_sc_result_ncv_pos
        CHECK (net_calorific_value > 0),
    CONSTRAINT ck_cbam_sc_result_co2_pos
        CHECK (fossil_co2_emission_factor > 0),
    CONSTRAINT ck_cbam_sc_result_ox_nonneg
        CHECK (oxidation_factor >= 0),
    CONSTRAINT ck_cbam_sc_result_density_pair
        CHECK (
            (density_value IS NULL AND density_unit IS NULL)
            OR (
                density_value IS NOT NULL
                AND density_unit IS NOT NULL
                AND density_value > 0
                AND density_unit IN ('kg/Sm3', 'kg/m3')
            )
        ),
    CONSTRAINT ck_cbam_sc_result_validity
        CHECK (valid_until IS NULL OR valid_until >= valid_from),
    CONSTRAINT ck_cbam_sc_result_unit
        CHECK (result_unit = 'tCO2'),
    CONSTRAINT ck_cbam_sc_result_mass_nonneg
        CHECK (fuel_mass_kg >= 0 AND fuel_mass_gg >= 0),
    CONSTRAINT ck_cbam_sc_result_energy_nonneg
        CHECK (energy_content_tj >= 0),
    CONSTRAINT ck_cbam_sc_result_co2_nonneg
        CHECK (fossil_co2_kg >= 0 AND fossil_co2_tonnes >= 0 AND result_value >= 0),
    CONSTRAINT fk_cbam_sc_result_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_sc_result_run
        FOREIGN KEY (calculation_run_id)
        REFERENCES cbam_calculation_runs (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_result_def
        FOREIGN KEY (calculation_definition_id)
        REFERENCES cbam_calculation_definitions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_result_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_result_activity
        FOREIGN KEY (activity_record_id)
        REFERENCES cbam_activity_records (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_result_fuel
        FOREIGN KEY (fuel_id)
        REFERENCES cbam_stationary_combustion_fuels (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_result_param
        FOREIGN KEY (parameter_set_id)
        REFERENCES cbam_stationary_combustion_parameter_sets (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_result_ncv_src
        FOREIGN KEY (ncv_reference_source_id)
        REFERENCES cbam_reference_sources (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_result_co2_src
        FOREIGN KEY (co2_reference_source_id)
        REFERENCES cbam_reference_sources (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_result_ox_src
        FOREIGN KEY (oxidation_reference_source_id)
        REFERENCES cbam_reference_sources (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_result_user
        FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_results_organization_id '
        'ON cbam_stationary_combustion_results (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_results_run_id '
        'ON cbam_stationary_combustion_results (calculation_run_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_results_activity_id '
        'ON cbam_stationary_combustion_results (activity_record_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_results_binding_id '
        'ON cbam_stationary_combustion_results (reporting_period_binding_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_results_fuel_id '
        'ON cbam_stationary_combustion_results (fuel_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_results_parameter_set_id '
        'ON cbam_stationary_combustion_results (parameter_set_id)'
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS cbam_stationary_combustion_results')
    op.execute(
        'ALTER TABLE cbam_calculation_definitions '
        'DROP CONSTRAINT IF EXISTS ck_cbam_calc_def_factor_req'
    )
    # Existing rows must already satisfy NOT NULL for MULTIPLY-only historical data.
    op.execute(
        'DELETE FROM cbam_calculation_definitions '
        "WHERE calculation_type = 'STATIONARY_COMBUSTION_CO2_V1'"
    )
    op.execute(
        'ALTER TABLE cbam_calculation_definitions '
        'ALTER COLUMN factor_definition_id SET NOT NULL'
    )
    op.execute(
        'ALTER TABLE cbam_calculation_definitions '
        'DROP CONSTRAINT IF EXISTS ck_cbam_calc_def_type'
    )
    op.execute(
        """
ALTER TABLE cbam_calculation_definitions
ADD CONSTRAINT ck_cbam_calculation_definitions_calculation_definition_type
CHECK (calculation_type IN ('MULTIPLY_ACTIVITY_BY_FACTOR'))
"""
    )
