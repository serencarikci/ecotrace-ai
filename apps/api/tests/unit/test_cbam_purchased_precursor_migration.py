"""Phase 10A migration round-trip for purchased-precursor indexes and constraints."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / 'src'
    / 'ecotrace'
    / 'db'
    / 'migrations'
    / 'versions'
    / '0026_cbam_purchased_precursor.py'
)

PRECURSOR_INDEXES = {
    'ix_cbam_purch_prec_org',
    'ix_cbam_purch_prec_org_binding',
    'ix_cbam_purch_prec_status',
    'ix_cbam_purch_prec_supplier',
    'ix_cbam_purch_prec_cn',
}
DEFAULT_VALUE_INDEXES = {
    'ix_cbam_precursor_dv_values_dataset',
    'ix_cbam_precursor_dv_values_lookup',
    'ix_cbam_precursor_dv_values_country_cn',
}


def test_migration_0026_is_chained_and_creates_all_phase_10a_tables() -> None:
    source = MIGRATION.read_text(encoding='utf-8')
    assert "revision: str = '0026_cbam_purchased_precursor'" in source
    assert "down_revision: str | None = '0025_cbam_production_process'" in source
    for table in (
        'cbam_precursor_default_datasets',
        'cbam_precursor_default_values',
        'cbam_purchased_precursors',
        'cbam_purchased_precursor_product_uses',
    ):
        assert f'CREATE TABLE {table}' in source
        assert f'DROP TABLE IF EXISTS {table}' in source


def test_phase_10a_tables_match_the_orm_metadata(seeded_db) -> None:
    tables = set(
        seeded_db.execute(
            text(
                """
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'cbam_precursor_default_datasets',
    'cbam_precursor_default_values',
    'cbam_purchased_precursors',
    'cbam_purchased_precursor_product_uses'
  )
"""
            )
        ).scalars()
    )
    assert {
        'cbam_precursor_default_datasets',
        'cbam_precursor_default_values',
        'cbam_purchased_precursors',
        'cbam_purchased_precursor_product_uses',
    } <= tables

    constraints = set(
        seeded_db.execute(
            text(
                """
SELECT conname FROM pg_constraint
WHERE conrelid = 'cbam_purchased_precursors'::regclass
"""
            )
        ).scalars()
    )
    # The ORM naming convention prefixes the table name onto declared constraint names.
    for suffix in (
        'ck_cbam_purch_prec_status',
        'ck_cbam_purch_prec_mode',
        'ck_cbam_purch_prec_qty_nonneg',
        'ck_cbam_purch_prec_non_cbam_nonneg',
    ):
        assert any(name.endswith(suffix) for name in constraints), suffix

    use_constraints = set(
        seeded_db.execute(
            text(
                """
SELECT conname FROM pg_constraint
WHERE conrelid = 'cbam_purchased_precursor_product_uses'::regclass
"""
            )
        ).scalars()
    )
    assert any(
        name.endswith('uq_cbam_purch_prec_use_target') for name in use_constraints
    )


def test_precursor_index_migration_round_trip(seeded_db) -> None:
    """upgrade → downgrade → upgrade restores the lookup and tenancy indexes."""

    def index_names() -> set[str]:
        rows = seeded_db.execute(
            text(
                """
SELECT indexname FROM pg_indexes
WHERE tablename IN (
    'cbam_purchased_precursors',
    'cbam_precursor_default_values'
  )
  AND indexname LIKE 'ix_%'
"""
            )
        ).scalars()
        return set(rows)

    def downgrade() -> None:
        for name in PRECURSOR_INDEXES | DEFAULT_VALUE_INDEXES:
            seeded_db.execute(text(f'DROP INDEX IF EXISTS {name}'))
        seeded_db.flush()

    def upgrade() -> None:
        seeded_db.execute(
            text(
                """
CREATE INDEX IF NOT EXISTS ix_cbam_purch_prec_org
    ON cbam_purchased_precursors (organization_id);
CREATE INDEX IF NOT EXISTS ix_cbam_purch_prec_org_binding
    ON cbam_purchased_precursors (organization_id, reporting_period_binding_id);
CREATE INDEX IF NOT EXISTS ix_cbam_purch_prec_status
    ON cbam_purchased_precursors (status);
CREATE INDEX IF NOT EXISTS ix_cbam_purch_prec_supplier
    ON cbam_purchased_precursors (supplier_id);
CREATE INDEX IF NOT EXISTS ix_cbam_purch_prec_cn
    ON cbam_purchased_precursors (cn_normalized_code);
CREATE INDEX IF NOT EXISTS ix_cbam_precursor_dv_values_dataset
    ON cbam_precursor_default_values (dataset_id);
CREATE INDEX IF NOT EXISTS ix_cbam_precursor_dv_values_lookup
    ON cbam_precursor_default_values (dataset_id, lookup_key);
CREATE INDEX IF NOT EXISTS ix_cbam_precursor_dv_values_country_cn
    ON cbam_precursor_default_values (dataset_id, country_name, cn_normalized_code);
"""
            )
        )
        seeded_db.flush()

    expected = PRECURSOR_INDEXES | DEFAULT_VALUE_INDEXES
    upgrade()
    assert expected <= index_names()
    downgrade()
    assert index_names() & expected == set()
    upgrade()
    assert expected <= index_names()
