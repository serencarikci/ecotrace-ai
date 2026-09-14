"""CBAM Phase 7A-0: monthly production-basis (workbook D/E) inputs.

Revision ID: 0021_cbam_monthly_prod_basis
Revises: 0020_cbam_prod_profile_link
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0021_cbam_monthly_prod_basis'
down_revision: str | None = '0020_cbam_prod_profile_link'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_monthly_production_basis (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    month_start DATE NOT NULL,
    total_production_quantity NUMERIC(24, 8),
    cbam_quantity NUMERIC(24, 8),
    quantity_unit VARCHAR(32) NOT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
    notes TEXT,
    row_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    CONSTRAINT pk_cbam_monthly_production_basis PRIMARY KEY (id),
    CONSTRAINT uq_cbam_monthly_prod_basis_org_binding_month
        UNIQUE (organization_id, reporting_period_binding_id, month_start),
    CONSTRAINT fk_cbam_monthly_prod_basis_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_monthly_prod_basis_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_monthly_prod_basis_created_by
        FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_monthly_prod_basis_updated_by
        FOREIGN KEY (updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT ck_cbam_monthly_prod_basis_month_canonical
        CHECK (EXTRACT(DAY FROM month_start) = 1),
    CONSTRAINT ck_cbam_monthly_prod_basis_total_nonneg
        CHECK (
            total_production_quantity IS NULL
            OR total_production_quantity >= 0
        ),
    CONSTRAINT ck_cbam_monthly_prod_basis_cbam_nonneg
        CHECK (cbam_quantity IS NULL OR cbam_quantity >= 0),
    CONSTRAINT ck_cbam_monthly_prod_basis_row_version
        CHECK (row_version >= 1),
    CONSTRAINT ck_cbam_monthly_prod_basis_source_type
        CHECK (source_type IN ('MANUAL', 'IMPORT', 'SYSTEM'))
)
"""
    )
    op.execute(
        """
CREATE INDEX ix_cbam_monthly_prod_basis_organization_id
    ON cbam_monthly_production_basis (organization_id)
"""
    )
    op.execute(
        """
CREATE INDEX ix_cbam_monthly_prod_basis_org_binding
    ON cbam_monthly_production_basis (organization_id, reporting_period_binding_id)
"""
    )
    op.execute(
        """
CREATE INDEX ix_cbam_monthly_prod_basis_binding_month
    ON cbam_monthly_production_basis (reporting_period_binding_id, month_start)
"""
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_cbam_monthly_prod_basis_binding_month')
    op.execute('DROP INDEX IF EXISTS ix_cbam_monthly_prod_basis_org_binding')
    op.execute('DROP INDEX IF EXISTS ix_cbam_monthly_prod_basis_organization_id')
    op.execute('DROP TABLE IF EXISTS cbam_monthly_production_basis')
