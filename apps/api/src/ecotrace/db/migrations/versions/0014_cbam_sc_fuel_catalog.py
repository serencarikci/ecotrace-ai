"""CBAM Phase 2 stationary-combustion fuel reference catalog."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0014_cbam_sc_fuel_catalog"
down_revision: str | None = "0013_cbam_excel_export"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_stationary_combustion_fuels (
    id UUID NOT NULL,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    input_basis VARCHAR(16) NOT NULL,
    default_activity_unit VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_stationary_combustion_fuels PRIMARY KEY (id),
    CONSTRAINT uq_cbam_stationary_combustion_fuel_code UNIQUE (code),
    CONSTRAINT ck_sc_fuel_input_basis
        CHECK (input_basis IN ('VOLUME', 'MASS')),
    CONSTRAINT ck_sc_fuel_status
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')),
    CONSTRAINT ck_sc_fuel_default_unit
        CHECK (default_activity_unit IN ('Sm3', 'm3', 'kg', 't', 'Gg'))
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_stationary_combustion_fuels_status "
        "ON cbam_stationary_combustion_fuels (status)"
    )

    op.execute(
        """
CREATE TABLE cbam_stationary_combustion_parameter_sets (
    id UUID NOT NULL,
    fuel_id UUID NOT NULL,
    dataset_code VARCHAR(64) NOT NULL,
    dataset_version VARCHAR(64) NOT NULL,
    valid_from DATE NOT NULL,
    valid_until DATE,
    status VARCHAR(32) NOT NULL,
    net_calorific_value NUMERIC(24, 8) NOT NULL,
    net_calorific_value_unit VARCHAR(32) NOT NULL,
    fossil_co2_emission_factor NUMERIC(24, 8) NOT NULL,
    fossil_co2_emission_factor_unit VARCHAR(32) NOT NULL,
    oxidation_factor NUMERIC(24, 12) NOT NULL,
    reference_density NUMERIC(24, 8),
    reference_density_unit VARCHAR(32),
    ncv_reference_source_id UUID NOT NULL,
    ncv_source_document TEXT NOT NULL,
    ncv_source_table VARCHAR(255) NOT NULL,
    co2_reference_source_id UUID NOT NULL,
    co2_source_document TEXT NOT NULL,
    co2_source_table VARCHAR(255) NOT NULL,
    oxidation_reference_source_id UUID NOT NULL,
    oxidation_source_document TEXT NOT NULL,
    oxidation_source_table VARCHAR(255) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_stationary_combustion_parameter_sets PRIMARY KEY (id),
    CONSTRAINT uq_cbam_sc_param_fuel_dataset_version
        UNIQUE (fuel_id, dataset_code, dataset_version),
    CONSTRAINT ck_cbam_sc_param_status
        CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
    CONSTRAINT ck_cbam_sc_param_validity_order
        CHECK (valid_until IS NULL OR valid_until >= valid_from),
    CONSTRAINT ck_cbam_sc_param_ncv_positive
        CHECK (net_calorific_value > 0),
    CONSTRAINT ck_cbam_sc_param_ncv_unit
        CHECK (net_calorific_value_unit IN ('TJ/Gg')),
    CONSTRAINT ck_cbam_sc_param_co2_positive
        CHECK (fossil_co2_emission_factor > 0),
    CONSTRAINT ck_cbam_sc_param_co2_unit
        CHECK (fossil_co2_emission_factor_unit IN ('kgCO2/TJ')),
    CONSTRAINT ck_cbam_sc_param_oxidation_non_negative
        CHECK (oxidation_factor >= 0),
    CONSTRAINT ck_cbam_sc_param_density_pair
        CHECK (
            (reference_density IS NULL AND reference_density_unit IS NULL)
            OR (
                reference_density IS NOT NULL
                AND reference_density_unit IS NOT NULL
                AND reference_density > 0
                AND reference_density_unit IN ('kg/Sm3', 'kg/m3')
            )
        ),
    CONSTRAINT fk_cbam_sc_param_fuel_id
        FOREIGN KEY (fuel_id)
        REFERENCES cbam_stationary_combustion_fuels (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_param_ncv_source
        FOREIGN KEY (ncv_reference_source_id)
        REFERENCES cbam_reference_sources (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_param_co2_source
        FOREIGN KEY (co2_reference_source_id)
        REFERENCES cbam_reference_sources (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_sc_param_oxidation_source
        FOREIGN KEY (oxidation_reference_source_id)
        REFERENCES cbam_reference_sources (id) ON DELETE RESTRICT
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_sc_param_sets_fuel_id "
        "ON cbam_stationary_combustion_parameter_sets (fuel_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_sc_param_sets_status "
        "ON cbam_stationary_combustion_parameter_sets (status)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_sc_param_sets_validity "
        "ON cbam_stationary_combustion_parameter_sets (valid_from, valid_until)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_sc_param_sets_fuel_status_validity "
        "ON cbam_stationary_combustion_parameter_sets "
        "(fuel_id, status, valid_from, valid_until)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cbam_stationary_combustion_parameter_sets")
    op.execute("DROP TABLE IF EXISTS cbam_stationary_combustion_fuels")
