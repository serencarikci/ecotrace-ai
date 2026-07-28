from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase3"
down_revision: str | None = "0002_phase2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gwp_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_report_code", sa.String(length=64), nullable=False),
        sa.Column("gas_code", sa.String(length=32), nullable=False),
        sa.Column("gwp_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gwp_values"),
        sa.UniqueConstraint(
            "assessment_report_code",
            "gas_code",
            "effective_from",
            name="uq_gwp_values_dataset_gas_from",
        ),
    )
    op.create_index(
        "ix_gwp_values_assessment_report_code", "gwp_values", ["assessment_report_code"]
    )
    op.create_index("ix_gwp_values_gas_code", "gwp_values", ["gas_code"])
    op.create_index("ix_gwp_values_is_active", "gwp_values", ["is_active"])

    op.create_table(
        "emission_factor_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("methodology", sa.Text(), nullable=True),
        sa.Column("geographic_coverage", sa.String(length=255), nullable=True),
        sa.Column("license_name", sa.String(length=255), nullable=True),
        sa.Column("license_url", sa.String(length=1024), nullable=True),
        sa.Column("release_version", sa.String(length=64), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_emission_factor_sources"),
        sa.UniqueConstraint("code", name="uq_emission_factor_sources_code"),
    )
    op.create_index(
        "ix_emission_factor_sources_is_active", "emission_factor_sources", ["is_active"]
    )

    op.create_table(
        "emission_factors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("activity_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("subcategory", sa.String(length=128), nullable=True),
        sa.Column("geography_code", sa.String(length=64), nullable=False),
        sa.Column("facility_type", sa.String(length=64), nullable=True),
        sa.Column("technology_code", sa.String(length=64), nullable=True),
        sa.Column("fuel_type", sa.String(length=64), nullable=True),
        sa.Column("transportation_mode", sa.String(length=64), nullable=True),
        sa.Column("vehicle_type", sa.String(length=64), nullable=True),
        sa.Column("unit_code", sa.String(length=32), nullable=False),
        sa.Column("factor_value", sa.Numeric(24, 12), nullable=True),
        sa.Column("co2_factor", sa.Numeric(24, 12), nullable=True),
        sa.Column("ch4_factor", sa.Numeric(24, 12), nullable=True),
        sa.Column("n2o_factor", sa.Numeric(24, 12), nullable=True),
        sa.Column("other_gases_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("biogenic_co2_factor", sa.Numeric(24, 12), nullable=True),
        sa.Column("uncertainty_percentage", sa.Numeric(8, 4), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("supersedes_factor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "factor_value IS NULL OR factor_value >= 0",
            name="ck_emission_factors_factor_value_nonneg",
        ),
        sa.CheckConstraint(
            "co2_factor IS NULL OR co2_factor >= 0", name="ck_emission_factors_co2_factor_nonneg"
        ),
        sa.CheckConstraint(
            "ch4_factor IS NULL OR ch4_factor >= 0", name="ck_emission_factors_ch4_factor_nonneg"
        ),
        sa.CheckConstraint(
            "n2o_factor IS NULL OR n2o_factor >= 0", name="ck_emission_factors_n2o_factor_nonneg"
        ),
        sa.CheckConstraint(
            "biogenic_co2_factor IS NULL OR biogenic_co2_factor >= 0",
            name="ck_emission_factors_biogenic_co2_factor_nonneg",
        ),
        sa.CheckConstraint(
            "uncertainty_percentage IS NULL OR (uncertainty_percentage >= 0 AND uncertainty_percentage <= 100)",
            name="ck_emission_factors_uncertainty_pct_range",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_emission_factors_factor_valid_range",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["emission_factor_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["activity_type_id"], ["activity_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supersedes_factor_id"], ["emission_factors.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_emission_factors"),
        sa.UniqueConstraint("code", "version", name="uq_emission_factors_code_version"),
    )
    op.create_index("ix_emission_factors_source_id", "emission_factors", ["source_id"])
    op.create_index(
        "ix_emission_factors_activity_type_id", "emission_factors", ["activity_type_id"]
    )
    op.create_index("ix_emission_factors_scope", "emission_factors", ["scope"])
    op.create_index("ix_emission_factors_category", "emission_factors", ["category"])
    op.create_index("ix_emission_factors_geography_code", "emission_factors", ["geography_code"])
    op.create_index("ix_emission_factors_valid_from", "emission_factors", ["valid_from"])
    op.create_index("ix_emission_factors_valid_to", "emission_factors", ["valid_to"])
    op.create_index("ix_emission_factors_status", "emission_factors", ["status"])
    op.create_index("ix_emission_factors_is_active", "emission_factors", ["is_active"])

    op.create_table(
        "organization_emission_factor_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("emission_factor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_organization_emission_factor_preferences_org_ef_pref_valid_range",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["activity_type_id"], ["activity_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["emission_factor_id"], ["emission_factors.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_organization_emission_factor_preferences"),
    )
    op.create_index(
        "ix_org_ef_pref_organization_id",
        "organization_emission_factor_preferences",
        ["organization_id"],
    )
    op.create_index(
        "ix_org_ef_pref_activity_type_id",
        "organization_emission_factor_preferences",
        ["activity_type_id"],
    )
    op.create_index(
        "ix_org_ef_pref_emission_factor_id",
        "organization_emission_factor_preferences",
        ["emission_factor_id"],
    )
    op.create_index(
        "ix_org_ef_pref_valid_from", "organization_emission_factor_preferences", ["valid_from"]
    )
    op.create_index(
        "ix_org_ef_pref_valid_to", "organization_emission_factor_preferences", ["valid_to"]
    )

    op.create_table(
        "emission_factor_import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False),
        sa.Column("invalid_rows", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("error_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_emission_factor_import_jobs"),
    )
    op.create_index("ix_ef_import_jobs_status", "emission_factor_import_jobs", ["status"])

    op.create_table(
        "carbon_inventories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporting_period_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("calculation_methodology_version", sa.String(length=64), nullable=False),
        sa.Column("gwp_dataset_code", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("partial_calculation", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reporting_period_id"], ["reporting_periods.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["calculated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_carbon_inventories"),
    )
    op.create_index(
        "ix_carbon_inventories_organization_id", "carbon_inventories", ["organization_id"]
    )
    op.create_index(
        "ix_carbon_inventories_reporting_period_id", "carbon_inventories", ["reporting_period_id"]
    )
    op.create_index("ix_carbon_inventories_status", "carbon_inventories", ["status"])
    op.create_index("ix_carbon_inventories_created_at", "carbon_inventories", ["created_at"])

    op.create_table(
        "carbon_calculation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activity_record_count", sa.Integer(), nullable=False),
        sa.Column("calculated_record_count", sa.Integer(), nullable=False),
        sa.Column("skipped_record_count", sa.Integer(), nullable=False),
        sa.Column("failed_record_count", sa.Integer(), nullable=False),
        sa.Column("total_kg_co2e", sa.Numeric(24, 8), nullable=True),
        sa.Column("error_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("engine_version", sa.String(length=32), nullable=False),
        sa.Column("partial_calculation", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("gwp_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["inventory_id"], ["carbon_inventories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_carbon_calculation_runs"),
        sa.UniqueConstraint("inventory_id", "run_number", name="uq_carbon_runs_inventory_run"),
    )
    op.create_index(
        "ix_carbon_calculation_runs_inventory_id", "carbon_calculation_runs", ["inventory_id"]
    )
    op.create_index("ix_carbon_calculation_runs_status", "carbon_calculation_runs", ["status"])
    op.create_index(
        "ix_carbon_calculation_runs_created_at", "carbon_calculation_runs", ["created_at"]
    )

    op.create_table(
        "carbon_calculation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("emission_factor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("factor_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activity_quantity", sa.Numeric(24, 12), nullable=False),
        sa.Column("activity_unit_code", sa.String(length=32), nullable=False),
        sa.Column("normalized_quantity", sa.Numeric(24, 12), nullable=True),
        sa.Column("normalized_unit_code", sa.String(length=32), nullable=True),
        sa.Column("factor_value", sa.Numeric(24, 12), nullable=True),
        sa.Column("factor_unit_code", sa.String(length=32), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("subcategory", sa.String(length=128), nullable=True),
        sa.Column("co2_kg", sa.Numeric(24, 8), nullable=True),
        sa.Column("ch4_kg", sa.Numeric(24, 8), nullable=True),
        sa.Column("n2o_kg", sa.Numeric(24, 8), nullable=True),
        sa.Column("other_gases_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("biogenic_co2_kg", sa.Numeric(24, 8), nullable=True),
        sa.Column("total_kg_co2e", sa.Numeric(24, 8), nullable=True),
        sa.Column("matching_priority", sa.Integer(), nullable=True),
        sa.Column("matching_reason", sa.Text(), nullable=True),
        sa.Column("calculation_formula", sa.Text(), nullable=True),
        sa.Column(
            "calculation_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("validation_errors_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["calculation_run_id"], ["carbon_calculation_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["inventory_id"], ["carbon_inventories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["activity_record_id"], ["activity_records.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["emission_factor_id"], ["emission_factors.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["factor_source_id"], ["emission_factor_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_carbon_calculation_items"),
        sa.UniqueConstraint(
            "calculation_run_id",
            "activity_record_id",
            name="uq_carbon_calc_items_run_activity",
        ),
    )
    op.create_index(
        "ix_carbon_calc_items_inventory_id", "carbon_calculation_items", ["inventory_id"]
    )
    op.create_index(
        "ix_carbon_calc_items_calculation_run_id",
        "carbon_calculation_items",
        ["calculation_run_id"],
    )
    op.create_index(
        "ix_carbon_calc_items_activity_record_id",
        "carbon_calculation_items",
        ["activity_record_id"],
    )
    op.create_index(
        "ix_carbon_calc_items_emission_factor_id",
        "carbon_calculation_items",
        ["emission_factor_id"],
    )
    op.create_index("ix_carbon_calc_items_scope", "carbon_calculation_items", ["scope"])
    op.create_index("ix_carbon_calc_items_category", "carbon_calculation_items", ["category"])
    op.create_index("ix_carbon_calc_items_status", "carbon_calculation_items", ["status"])


def downgrade() -> None:
    op.drop_table("carbon_calculation_items")
    op.drop_table("carbon_calculation_runs")
    op.drop_table("carbon_inventories")
    op.drop_table("emission_factor_import_jobs")
    op.drop_table("organization_emission_factor_preferences")
    op.drop_table("emission_factors")
    op.drop_table("emission_factor_sources")
    op.drop_table("gwp_values")
