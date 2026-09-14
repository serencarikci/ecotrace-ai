"""Phase 6C migration round-trip for production profile-link indexes."""

from __future__ import annotations

from sqlalchemy import text


def test_prod_profile_link_index_migration_round_trip(seeded_db) -> None:
    """upgrade → downgrade → upgrade keeps allocation query indexes."""
    seeded_db.execute(
        text('DROP INDEX IF EXISTS ix_cbam_production_records_org_binding_profile')
    )
    seeded_db.execute(
        text('DROP INDEX IF EXISTS ix_cbam_production_records_product_profile_version_id')
    )
    seeded_db.flush()

    def upgrade() -> None:
        seeded_db.execute(
            text(
                """
CREATE INDEX IF NOT EXISTS ix_cbam_production_records_product_profile_version_id
    ON cbam_production_records (product_profile_version_id)
"""
            )
        )
        seeded_db.execute(
            text(
                """
CREATE INDEX IF NOT EXISTS ix_cbam_production_records_org_binding_profile
    ON cbam_production_records (
        organization_id,
        reporting_period_binding_id,
        product_profile_version_id
    )
"""
            )
        )
        seeded_db.flush()

    def downgrade() -> None:
        seeded_db.execute(
            text('DROP INDEX IF EXISTS ix_cbam_production_records_org_binding_profile')
        )
        seeded_db.execute(
            text('DROP INDEX IF EXISTS ix_cbam_production_records_product_profile_version_id')
        )
        seeded_db.flush()

    def index_names() -> set[str]:
        rows = seeded_db.execute(
            text(
                """
SELECT indexname FROM pg_indexes
WHERE tablename = 'cbam_production_records'
  AND indexname IN (
    'ix_cbam_production_records_product_profile_version_id',
    'ix_cbam_production_records_org_binding_profile'
  )
"""
            )
        ).scalars()
        return set(rows)

    upgrade()
    assert index_names() == {
        'ix_cbam_production_records_product_profile_version_id',
        'ix_cbam_production_records_org_binding_profile',
    }
    downgrade()
    assert index_names() == set()
    upgrade()
    assert index_names() == {
        'ix_cbam_production_records_product_profile_version_id',
        'ix_cbam_production_records_org_binding_profile',
    }
