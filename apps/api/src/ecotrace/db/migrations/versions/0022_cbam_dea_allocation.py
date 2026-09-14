"""CBAM Phase 7A-2: direct-emissions allocation immutable results + current pointer.

Revision ID: 0022_cbam_dea_allocation
Revises: 0021_cbam_monthly_prod_basis
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0022_cbam_dea_allocation'
down_revision: str | None = '0021_cbam_monthly_prod_basis'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_direct_emissions_allocation_results (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    methodology_code VARCHAR(128) NOT NULL,
    methodology_version VARCHAR(32) NOT NULL,
    workbook_filename VARCHAR(255) NOT NULL,
    workbook_sha256 VARCHAR(64) NOT NULL,
    workbook_formula_refs TEXT NOT NULL,
    client_request_id UUID NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    balance_status VARCHAR(32) NOT NULL,
    facility_fossil_co2_tonnes_raw NUMERIC(36, 18) NOT NULL,
    cbam_fossil_co2_tonnes_raw NUMERIC(36, 18) NOT NULL,
    non_cbam_fossil_co2_tonnes_raw NUMERIC(36, 18) NOT NULL,
    facility_fossil_co2_tonnes NUMERIC(24, 8) NOT NULL,
    cbam_fossil_co2_tonnes NUMERIC(24, 8) NOT NULL,
    non_cbam_fossil_co2_tonnes NUMERIC(24, 8) NOT NULL,
    allocated_fossil_co2_tonnes NUMERIC(24, 8) NOT NULL,
    remaining_fossil_co2_tonnes NUMERIC(24, 8) NOT NULL,
    result_unit VARCHAR(32) NOT NULL,
    workbook_reporting_unit VARCHAR(32) NOT NULL,
    workbook_gas VARCHAR(16) NOT NULL,
    workbook_gwp VARCHAR(16) NOT NULL,
    workbook_gwp_factor VARCHAR(16) NOT NULL,
    source_result_count INTEGER NOT NULL,
    month_count INTEGER NOT NULL,
    fuel_count INTEGER NOT NULL,
    participating_production_record_count INTEGER NOT NULL,
    product_profile_group_count INTEGER NOT NULL,
    totals_by_month_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    totals_by_fuel_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_dea_results PRIMARY KEY (id),
    CONSTRAINT fk_cbam_dea_results_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_dea_results_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_dea_results_created_by
        FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT ck_cbam_dea_results_status CHECK (status = 'COMPLETED'),
    CONSTRAINT ck_cbam_dea_results_balance CHECK (balance_status IN ('BALANCED', 'UNBALANCED')),
    CONSTRAINT ck_cbam_dea_results_unit CHECK (result_unit = 'tCO2'),
    CONSTRAINT ck_cbam_dea_results_nonneg CHECK (
        facility_fossil_co2_tonnes >= 0
        AND cbam_fossil_co2_tonnes >= 0
        AND non_cbam_fossil_co2_tonnes >= 0
        AND allocated_fossil_co2_tonnes >= 0
        AND remaining_fossil_co2_tonnes >= 0
    ),
    CONSTRAINT ck_cbam_dea_results_balanced_zero_remaining CHECK (
        balance_status <> 'BALANCED' OR remaining_fossil_co2_tonnes = 0
    )
)
"""
    )
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_dea_result_org_binding_client_request
ON cbam_direct_emissions_allocation_results (
    organization_id, reporting_period_binding_id, client_request_id
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_dea_results_org_binding '
        'ON cbam_direct_emissions_allocation_results '
        '(organization_id, reporting_period_binding_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_dea_results_created_at '
        'ON cbam_direct_emissions_allocation_results (created_at DESC, id DESC)'
    )
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_dea_result_id_org_binding
ON cbam_direct_emissions_allocation_results (
    id, organization_id, reporting_period_binding_id
)
"""
    )

    op.execute(
        """
CREATE TABLE cbam_dea_monthly_basis_snapshots (
    id UUID NOT NULL,
    result_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    basis_record_id UUID NOT NULL,
    basis_row_version INTEGER NOT NULL,
    month_start DATE NOT NULL,
    total_production_quantity NUMERIC(24, 8) NOT NULL,
    cbam_quantity NUMERIC(24, 8) NOT NULL,
    quantity_unit VARCHAR(32) NOT NULL,
    normalized_total_production_tonnes NUMERIC(36, 18) NOT NULL,
    normalized_cbam_quantity_tonnes NUMERIC(36, 18) NOT NULL,
    monthly_share_raw NUMERIC(36, 18) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_dea_monthly_basis_snapshots PRIMARY KEY (id),
    CONSTRAINT fk_cbam_dea_mb_result
        FOREIGN KEY (result_id) REFERENCES cbam_direct_emissions_allocation_results (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_dea_mb_basis
        FOREIGN KEY (basis_record_id) REFERENCES cbam_monthly_production_basis (id)
        ON DELETE RESTRICT,
    CONSTRAINT uq_cbam_dea_mb_result_month UNIQUE (result_id, month_start),
    CONSTRAINT ck_cbam_dea_mb_month_canonical CHECK (EXTRACT(DAY FROM month_start) = 1)
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_dea_mb_basis_record '
        'ON cbam_dea_monthly_basis_snapshots (basis_record_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_dea_mb_result '
        'ON cbam_dea_monthly_basis_snapshots (result_id)'
    )

    op.execute(
        """
CREATE TABLE cbam_dea_source_snapshots (
    id UUID NOT NULL,
    result_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    source_result_id UUID NOT NULL,
    source_run_id UUID NOT NULL,
    activity_record_id UUID NOT NULL,
    activity_date DATE NOT NULL,
    month_start DATE NOT NULL,
    fuel_code VARCHAR(64) NOT NULL,
    fuel_name VARCHAR(255) NOT NULL,
    dataset_code VARCHAR(64) NOT NULL,
    dataset_version VARCHAR(64) NOT NULL,
    activity_quantity NUMERIC(24, 8) NOT NULL,
    activity_unit VARCHAR(32) NOT NULL,
    facility_fuel_mass_kg NUMERIC(36, 18) NOT NULL,
    facility_fuel_mass_gg NUMERIC(36, 18) NOT NULL,
    facility_energy_content_tj NUMERIC(36, 18) NOT NULL,
    facility_fossil_co2_kg NUMERIC(36, 18) NOT NULL,
    facility_fossil_co2_tonnes NUMERIC(36, 18) NOT NULL,
    facility_result_value NUMERIC(24, 8) NOT NULL,
    monthly_share_raw NUMERIC(36, 18) NOT NULL,
    cbam_fuel_mass_kg NUMERIC(36, 18) NOT NULL,
    cbam_fuel_mass_gg NUMERIC(36, 18) NOT NULL,
    cbam_energy_content_tj NUMERIC(36, 18) NOT NULL,
    cbam_fossil_co2_kg NUMERIC(36, 18) NOT NULL,
    cbam_fossil_co2_tonnes NUMERIC(36, 18) NOT NULL,
    non_cbam_fuel_mass_kg NUMERIC(36, 18) NOT NULL,
    non_cbam_fuel_mass_gg NUMERIC(36, 18) NOT NULL,
    non_cbam_energy_content_tj NUMERIC(36, 18) NOT NULL,
    non_cbam_fossil_co2_kg NUMERIC(36, 18) NOT NULL,
    non_cbam_fossil_co2_tonnes NUMERIC(36, 18) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_dea_source_snapshots PRIMARY KEY (id),
    CONSTRAINT fk_cbam_dea_src_result
        FOREIGN KEY (result_id) REFERENCES cbam_direct_emissions_allocation_results (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_dea_src_sc_result
        FOREIGN KEY (source_result_id) REFERENCES cbam_stationary_combustion_results (id)
        ON DELETE RESTRICT,
    CONSTRAINT uq_cbam_dea_src_result_source UNIQUE (result_id, source_result_id)
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_dea_src_result ON cbam_dea_source_snapshots (result_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_dea_src_source_result '
        'ON cbam_dea_source_snapshots (source_result_id)'
    )

    op.execute(
        """
CREATE TABLE cbam_dea_product_allocations (
    id UUID NOT NULL,
    result_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    product_id UUID NOT NULL,
    product_profile_version_id UUID NOT NULL,
    profile_version INTEGER NOT NULL,
    cn_normalized_code VARCHAR(32),
    cn_display_code VARCHAR(64),
    product_name VARCHAR(255),
    production_record_ids JSONB NOT NULL,
    production_quantity_snapshots JSONB NOT NULL,
    normalized_quantity_tonnes NUMERIC(36, 18) NOT NULL,
    denominator_tonnes NUMERIC(36, 18) NOT NULL,
    raw_share NUMERIC(36, 18) NOT NULL,
    raw_allocated_fossil_co2_tonnes NUMERIC(36, 18) NOT NULL,
    final_allocated_fossil_co2_tonnes NUMERIC(24, 8) NOT NULL,
    rounding_adjustment NUMERIC(36, 18) NOT NULL,
    result_unit VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_dea_product_allocations PRIMARY KEY (id),
    CONSTRAINT fk_cbam_dea_prod_result
        FOREIGN KEY (result_id) REFERENCES cbam_direct_emissions_allocation_results (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_dea_prod_profile
        FOREIGN KEY (product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    CONSTRAINT uq_cbam_dea_prod_result_profile
        UNIQUE (result_id, product_profile_version_id),
    CONSTRAINT ck_cbam_dea_prod_unit CHECK (result_unit = 'tCO2')
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_dea_prod_result ON cbam_dea_product_allocations (result_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_dea_prod_profile '
        'ON cbam_dea_product_allocations (product_profile_version_id)'
    )

    op.execute(
        """
CREATE TABLE cbam_direct_emissions_allocation_current (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    methodology_code VARCHAR(128) NOT NULL,
    current_result_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_dea_current PRIMARY KEY (id),
    CONSTRAINT uq_cbam_dea_current_org_binding_method UNIQUE (
        organization_id, reporting_period_binding_id, methodology_code
    ),
    CONSTRAINT fk_cbam_dea_current_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_dea_current_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_dea_current_result_identity FOREIGN KEY (
        current_result_id, organization_id, reporting_period_binding_id
    ) REFERENCES cbam_direct_emissions_allocation_results (
        id, organization_id, reporting_period_binding_id
    ) ON DELETE RESTRICT
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_dea_current_result '
        'ON cbam_direct_emissions_allocation_current (current_result_id)'
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS cbam_direct_emissions_allocation_current')
    op.execute('DROP TABLE IF EXISTS cbam_dea_product_allocations')
    op.execute('DROP TABLE IF EXISTS cbam_dea_source_snapshots')
    op.execute('DROP TABLE IF EXISTS cbam_dea_monthly_basis_snapshots')
    op.execute('DROP TABLE IF EXISTS cbam_direct_emissions_allocation_results')
