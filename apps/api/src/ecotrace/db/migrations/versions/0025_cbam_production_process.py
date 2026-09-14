"""CBAM Phase 9A: Conventional production processes + product-use distribution.

Revision ID: 0025_cbam_production_process
Revises: 0024_cbam_iea_allocation
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0025_cbam_production_process'
down_revision: str | None = '0024_cbam_iea_allocation'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_production_processes (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    installation_profile_id UUID NOT NULL,
    product_profile_version_id UUID,
    name VARCHAR(255),
    identifier VARCHAR(128),
    calculation_method VARCHAR(64) NOT NULL DEFAULT 'CONVENTIONAL',
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    produced_quantity NUMERIC(24, 8),
    produced_quantity_unit VARCHAR(32),
    marketed_quantity NUMERIC(24, 8),
    marketed_quantity_unit VARCHAR(32),
    non_cbam_quantity NUMERIC(24, 8),
    non_cbam_quantity_unit VARCHAR(32),
    has_measurable_heat BOOLEAN,
    heat_imported_quantity NUMERIC(24, 8),
    heat_imported_unit VARCHAR(32),
    heat_exported_quantity NUMERIC(24, 8),
    heat_exported_unit VARCHAR(32),
    heat_imported_ef NUMERIC(24, 8),
    heat_exported_ef NUMERIC(24, 8),
    heat_ef_unit VARCHAR(32),
    heat_factor_source VARCHAR(255),
    heat_factor_document TEXT,
    has_waste_gas BOOLEAN,
    waste_gas_imported_quantity NUMERIC(24, 8),
    waste_gas_imported_unit VARCHAR(32),
    waste_gas_exported_quantity NUMERIC(24, 8),
    waste_gas_exported_unit VARCHAR(32),
    waste_gas_provenance TEXT,
    data_quality_code VARCHAR(128),
    data_verification_code VARCHAR(128),
    data_quality_justification_code VARCHAR(128),
    notes TEXT,
    row_version INTEGER NOT NULL DEFAULT 1,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_production_processes PRIMARY KEY (id),
    CONSTRAINT fk_cbam_pp_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_pp_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pp_installation
        FOREIGN KEY (installation_profile_id)
        REFERENCES cbam_installation_profiles (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pp_product_profile
        FOREIGN KEY (product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pp_created_by
        FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_pp_updated_by
        FOREIGN KEY (updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT ck_cbam_pp_status CHECK (status IN ('draft', 'archived')),
    CONSTRAINT ck_cbam_pp_method CHECK (
        calculation_method IN ('CONVENTIONAL', 'PROCESS_EMISSIONS', 'MASS_BALANCE')
    ),
    CONSTRAINT ck_cbam_pp_row_version CHECK (row_version >= 1),
    CONSTRAINT ck_cbam_pp_produced_nonneg CHECK (
        produced_quantity IS NULL OR produced_quantity >= 0
    ),
    CONSTRAINT ck_cbam_pp_marketed_nonneg CHECK (
        marketed_quantity IS NULL OR marketed_quantity >= 0
    ),
    CONSTRAINT ck_cbam_pp_non_cbam_nonneg CHECK (
        non_cbam_quantity IS NULL OR non_cbam_quantity >= 0
    ),
    CONSTRAINT ck_cbam_pp_heat_false_clears CHECK (
        has_measurable_heat IS DISTINCT FROM FALSE
        OR (
            heat_imported_quantity IS NULL
            AND heat_exported_quantity IS NULL
            AND heat_imported_ef IS NULL
            AND heat_exported_ef IS NULL
            AND heat_imported_unit IS NULL
            AND heat_exported_unit IS NULL
            AND heat_ef_unit IS NULL
            AND heat_factor_source IS NULL
            AND heat_factor_document IS NULL
        )
    ),
    CONSTRAINT ck_cbam_pp_waste_false_clears CHECK (
        has_waste_gas IS DISTINCT FROM FALSE
        OR (
            waste_gas_imported_quantity IS NULL
            AND waste_gas_exported_quantity IS NULL
            AND waste_gas_imported_unit IS NULL
            AND waste_gas_exported_unit IS NULL
            AND waste_gas_provenance IS NULL
        )
    )
)
"""
    )
    op.execute(
        """
CREATE INDEX ix_cbam_pp_org_binding
ON cbam_production_processes (organization_id, reporting_period_binding_id)
"""
    )
    op.execute(
        """
CREATE INDEX ix_cbam_pp_org_status
ON cbam_production_processes (organization_id, status)
"""
    )
    op.execute(
        """
CREATE INDEX ix_cbam_pp_product_profile
ON cbam_production_processes (product_profile_version_id)
"""
    )
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_pp_org_binding_identifier_active
ON cbam_production_processes (organization_id, reporting_period_binding_id, identifier)
WHERE identifier IS NOT NULL AND status = 'draft'
"""
    )

    op.execute(
        """
CREATE TABLE cbam_production_process_product_uses (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    process_id UUID NOT NULL,
    target_product_profile_version_id UUID NOT NULL,
    quantity NUMERIC(24, 8) NOT NULL,
    unit VARCHAR(32) NOT NULL,
    notes TEXT,
    row_version INTEGER NOT NULL DEFAULT 1,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_pp_product_uses PRIMARY KEY (id),
    CONSTRAINT fk_cbam_ppu_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_ppu_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_ppu_process
        FOREIGN KEY (process_id)
        REFERENCES cbam_production_processes (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_ppu_target_profile
        FOREIGN KEY (target_product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_ppu_created_by
        FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_ppu_updated_by
        FOREIGN KEY (updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT ck_cbam_ppu_qty_nonneg CHECK (quantity >= 0),
    CONSTRAINT ck_cbam_ppu_row_version CHECK (row_version >= 1),
    CONSTRAINT uq_cbam_ppu_process_target UNIQUE (process_id, target_product_profile_version_id)
)
"""
    )
    op.execute(
        """
CREATE INDEX ix_cbam_ppu_org_binding
ON cbam_production_process_product_uses (organization_id, reporting_period_binding_id)
"""
    )
    op.execute(
        """
CREATE INDEX ix_cbam_ppu_process
ON cbam_production_process_product_uses (process_id)
"""
    )
    op.execute(
        """
CREATE INDEX ix_cbam_ppu_target_profile
ON cbam_production_process_product_uses (target_product_profile_version_id)
"""
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS cbam_production_process_product_uses')
    op.execute('DROP TABLE IF EXISTS cbam_production_processes')
