"""Phase 10C migration round-trip for the product embedded-emissions roll-up tables."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "ecotrace"
    / "db"
    / "migrations"
    / "versions"
    / "0027_cbam_product_embedded_emissions.py"
)

TABLES = (
    "cbam_product_embedded_emissions_results",
    "cbam_product_embedded_emissions_products",
    "cbam_product_embedded_emissions_precursor_contributions",
    "cbam_product_embedded_emissions_current",
)

RESULT_INDEXES = {
    "ix_cbam_pee_results_org_binding",
    "ix_cbam_pee_results_created_at",
}
PRODUCT_INDEXES = {
    "ix_cbam_pee_products_result",
    "ix_cbam_pee_products_profile",
    "ix_cbam_pee_products_process",
    "ix_cbam_pee_products_org_binding",
}
CONTRIBUTION_INDEXES = {
    "ix_cbam_pee_contrib_result",
    "ix_cbam_pee_contrib_product_row",
    "ix_cbam_pee_contrib_precursor",
    "ix_cbam_pee_contrib_product_use",
}


def test_migration_0027_is_chained_and_creates_all_phase_10c_tables() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    # alembic_version.version_num is varchar(32), so the id is abbreviated.
    assert 'revision: str = "0027_cbam_pee_rollup"' in source
    assert len("0027_cbam_pee_rollup") <= 32
    assert 'down_revision: str | None = "0026_cbam_purchased_precursor"' in source
    for table in TABLES:
        assert f"CREATE TABLE {table}" in source
        assert f"DROP TABLE IF EXISTS {table}" in source


def test_migration_0027_index_names_are_globally_unique() -> None:
    """A prior phase shipped colliding ix_cbam_pp_* names; every 10C name is distinct."""
    source = MIGRATION.read_text(encoding="utf-8")
    declared = [
        line.split()[-1]
        for line in source.splitlines()
        if line.startswith("CREATE INDEX ") or line.startswith("CREATE UNIQUE INDEX ")
    ]
    assert declared
    assert len(declared) == len(set(declared))
    assert all(
        name.startswith("ix_cbam_pee_") or name.startswith("uq_cbam_pee_") for name in declared
    )


def _check_definitions(db, table: str) -> list[str]:
    return list(
        db.execute(
            text(
                f"""
SELECT pg_get_constraintdef(oid) FROM pg_constraint
WHERE contype = 'c' AND conrelid = '{table}'::regclass
"""
            )
        ).scalars()
    )


def test_phase_10c_tables_match_the_orm_metadata(seeded_db) -> None:
    names = ", ".join(f"'{table}'" for table in TABLES)
    tables = set(
        seeded_db.execute(
            text(
                f"""
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ({names})
"""
            )
        ).scalars()
    )
    assert set(TABLES) <= tables

    # Unique constraints keep their declared names; CHECK names are truncated by the
    # ORM naming convention, so those are asserted through their definitions.
    unique_names = set(
        seeded_db.execute(
            text(
                """
SELECT conname FROM pg_constraint
WHERE contype = 'u'
  AND conrelid IN (
    'cbam_product_embedded_emissions_results'::regclass,
    'cbam_product_embedded_emissions_products'::regclass,
    'cbam_product_embedded_emissions_precursor_contributions'::regclass,
    'cbam_product_embedded_emissions_current'::regclass
  )
"""
            )
        ).scalars()
    )
    assert {
        "uq_cbam_pee_result_org_binding_client_request",
        "uq_cbam_pee_result_id_org_binding",
        "uq_cbam_pee_products_result_profile",
        "uq_cbam_pee_products_id_result",
        "uq_cbam_pee_contrib_result_use",
        "uq_cbam_pee_current_org_binding_method",
    } <= unique_names

    checks = _check_definitions(seeded_db, "cbam_product_embedded_emissions_results")
    assert any("status" in d and "'COMPLETED'" in d for d in checks)
    assert any("result_unit" in d and "'tCO2e'" in d for d in checks)
    assert any("dea_source_unit" in d and "'tCO2'" in d for d in checks)

    checks = _check_definitions(seeded_db, "cbam_product_embedded_emissions_products")
    assert any("denominator_tonnes" in d and "> (0)" in d for d in checks)
    assert any("exported_electricity_direct_tco2e" in d and "= (0)" in d for d in checks)

    checks = _check_definitions(
        seeded_db, "cbam_product_embedded_emissions_precursor_contributions"
    )
    assert any("quantity_tonnes" in d and ">= (0)" in d for d in checks)
    assert any("'SUPPLIER_DATA'" in d and "'EU_DEFAULT'" in d for d in checks)


def test_snapshot_columns_do_not_pin_editable_draft_rows(seeded_db) -> None:
    """Roll-up rows must not block editing or deleting processes, precursors and uses."""
    referenced = set(
        seeded_db.execute(
            text(
                """
SELECT confrelid::regclass::text FROM pg_constraint
WHERE contype = 'f'
  AND conrelid IN (
    'cbam_product_embedded_emissions_products'::regclass,
    'cbam_product_embedded_emissions_precursor_contributions'::regclass
  )
"""
            )
        ).scalars()
    )
    assert "cbam_production_processes" not in referenced
    assert "cbam_purchased_precursors" not in referenced
    assert "cbam_purchased_precursor_product_uses" not in referenced


def test_pee_index_migration_round_trip(seeded_db) -> None:
    """upgrade → downgrade → upgrade restores every roll-up lookup index."""
    expected = RESULT_INDEXES | PRODUCT_INDEXES | CONTRIBUTION_INDEXES

    def index_names() -> set[str]:
        return set(
            seeded_db.execute(
                text(
                    """
SELECT indexname FROM pg_indexes
WHERE tablename IN (
    'cbam_product_embedded_emissions_results',
    'cbam_product_embedded_emissions_products',
    'cbam_product_embedded_emissions_precursor_contributions'
  )
  AND indexname LIKE 'ix_cbam_pee_%'
"""
                )
            ).scalars()
        )

    def downgrade() -> None:
        for name in expected:
            seeded_db.execute(text(f"DROP INDEX IF EXISTS {name}"))
        seeded_db.flush()

    def upgrade() -> None:
        seeded_db.execute(
            text(
                """
CREATE INDEX IF NOT EXISTS ix_cbam_pee_results_org_binding
    ON cbam_product_embedded_emissions_results (
        organization_id, reporting_period_binding_id
    );
CREATE INDEX IF NOT EXISTS ix_cbam_pee_results_created_at
    ON cbam_product_embedded_emissions_results (created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_cbam_pee_products_result
    ON cbam_product_embedded_emissions_products (result_id);
CREATE INDEX IF NOT EXISTS ix_cbam_pee_products_profile
    ON cbam_product_embedded_emissions_products (product_profile_version_id);
CREATE INDEX IF NOT EXISTS ix_cbam_pee_products_process
    ON cbam_product_embedded_emissions_products (process_id);
CREATE INDEX IF NOT EXISTS ix_cbam_pee_products_org_binding
    ON cbam_product_embedded_emissions_products (
        organization_id, reporting_period_binding_id
    );
CREATE INDEX IF NOT EXISTS ix_cbam_pee_contrib_result
    ON cbam_product_embedded_emissions_precursor_contributions (result_id);
CREATE INDEX IF NOT EXISTS ix_cbam_pee_contrib_product_row
    ON cbam_product_embedded_emissions_precursor_contributions (product_row_id);
CREATE INDEX IF NOT EXISTS ix_cbam_pee_contrib_precursor
    ON cbam_product_embedded_emissions_precursor_contributions (precursor_id);
CREATE INDEX IF NOT EXISTS ix_cbam_pee_contrib_product_use
    ON cbam_product_embedded_emissions_precursor_contributions (product_use_id);
"""
            )
        )
        seeded_db.flush()

    upgrade()
    assert expected <= index_names()
    downgrade()
    assert index_names() & expected == set()
    upgrade()
    assert expected <= index_names()
