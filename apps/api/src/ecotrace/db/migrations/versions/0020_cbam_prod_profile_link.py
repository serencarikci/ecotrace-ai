"""CBAM Phase 6C: index production.profile links for allocation readiness queries.

Revision ID: 0020_cbam_prod_profile_link
Revises: 0019_cbam_cn_field_applicability
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0020_cbam_prod_profile_link'
down_revision: str | None = '0019_cbam_cn_field_applicability'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE INDEX IF NOT EXISTS ix_cbam_production_records_product_profile_version_id
    ON cbam_production_records (product_profile_version_id)
"""
    )
    op.execute(
        """
CREATE INDEX IF NOT EXISTS ix_cbam_production_records_org_binding_profile
    ON cbam_production_records (
        organization_id,
        reporting_period_binding_id,
        product_profile_version_id
    )
"""
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_cbam_production_records_org_binding_profile')
    op.execute('DROP INDEX IF EXISTS ix_cbam_production_records_product_profile_version_id')
