"""CBAM Phase 10D: process-level exported electricity (workbook D_Processes L71/L72).

Revision ID: 0028_cbam_process_exp_elec
Revises: 0027_cbam_pee_rollup

Additive only: six nullable columns plus non-negativity and "null when answered no"
guards. No existing row is touched.

The revision id is abbreviated because alembic_version.version_num is varchar(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0028_cbam_process_exp_elec"
down_revision: str | None = "0027_cbam_pee_rollup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
ALTER TABLE cbam_production_processes
    ADD COLUMN has_exported_electricity BOOLEAN,
    ADD COLUMN exported_electricity_quantity NUMERIC(24, 8),
    ADD COLUMN exported_electricity_unit VARCHAR(32),
    ADD COLUMN exported_electricity_emission_factor NUMERIC(24, 8),
    ADD COLUMN exported_electricity_ef_unit VARCHAR(32),
    ADD COLUMN exported_electricity_provenance TEXT;

ALTER TABLE cbam_production_processes
    ADD CONSTRAINT ck_cbam_pp_exported_elec_qty_nonneg
        CHECK (exported_electricity_quantity IS NULL OR exported_electricity_quantity >= 0),
    ADD CONSTRAINT ck_cbam_pp_exported_elec_ef_nonneg
        CHECK (
            exported_electricity_emission_factor IS NULL
            OR exported_electricity_emission_factor >= 0
        ),
    ADD CONSTRAINT ck_cbam_pp_exported_elec_false_null
        CHECK (
            has_exported_electricity IS DISTINCT FROM FALSE
            OR (
                exported_electricity_quantity IS NULL
                AND exported_electricity_unit IS NULL
                AND exported_electricity_emission_factor IS NULL
                AND exported_electricity_ef_unit IS NULL
                AND exported_electricity_provenance IS NULL
            )
        );
"""
    )


def downgrade() -> None:
    op.execute(
        """
ALTER TABLE cbam_production_processes
    DROP CONSTRAINT IF EXISTS ck_cbam_pp_exported_elec_false_null,
    DROP CONSTRAINT IF EXISTS ck_cbam_pp_exported_elec_ef_nonneg,
    DROP CONSTRAINT IF EXISTS ck_cbam_pp_exported_elec_qty_nonneg;

ALTER TABLE cbam_production_processes
    DROP COLUMN IF EXISTS exported_electricity_provenance,
    DROP COLUMN IF EXISTS exported_electricity_ef_unit,
    DROP COLUMN IF EXISTS exported_electricity_emission_factor,
    DROP COLUMN IF EXISTS exported_electricity_unit,
    DROP COLUMN IF EXISTS exported_electricity_quantity,
    DROP COLUMN IF EXISTS has_exported_electricity;
"""
    )
