"""Add missing audit columns on purchased-precursor tables.

Revision ID: 0032_cbam_prec_audit
Revises: 0031_cbam_calc_def_ck

Migration 0026 omitted created_by_user_id / updated_by_user_id that the ORM
requires. Pytest create_all hid the gap; empty→head Alembic installs failed on
precursor writes. Idempotent ADD COLUMN for already-migrated databases.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0032_cbam_prec_audit"
down_revision: str | None = "0031_cbam_calc_def_ck"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
ALTER TABLE cbam_purchased_precursors
    ADD COLUMN IF NOT EXISTS created_by_user_id UUID;
ALTER TABLE cbam_purchased_precursors
    ADD COLUMN IF NOT EXISTS updated_by_user_id UUID;
ALTER TABLE cbam_purchased_precursor_product_uses
    ADD COLUMN IF NOT EXISTS created_by_user_id UUID;
ALTER TABLE cbam_purchased_precursor_product_uses
    ADD COLUMN IF NOT EXISTS updated_by_user_id UUID;
"""
    )
    # FKs may already exist on fresh installs that applied the fixed 0026.
    op.execute(
        """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_cbam_purch_prec_created_by'
    ) THEN
        ALTER TABLE cbam_purchased_precursors
            ADD CONSTRAINT fk_cbam_purch_prec_created_by
            FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_cbam_purch_prec_updated_by'
    ) THEN
        ALTER TABLE cbam_purchased_precursors
            ADD CONSTRAINT fk_cbam_purch_prec_updated_by
            FOREIGN KEY (updated_by_user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_cbam_purch_prec_use_created_by'
    ) THEN
        ALTER TABLE cbam_purchased_precursor_product_uses
            ADD CONSTRAINT fk_cbam_purch_prec_use_created_by
            FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_cbam_purch_prec_use_updated_by'
    ) THEN
        ALTER TABLE cbam_purchased_precursor_product_uses
            ADD CONSTRAINT fk_cbam_purch_prec_use_updated_by
            FOREIGN KEY (updated_by_user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;
"""
    )


def downgrade() -> None:
    op.execute(
        """
ALTER TABLE cbam_purchased_precursors
    DROP CONSTRAINT IF EXISTS fk_cbam_purch_prec_created_by;
ALTER TABLE cbam_purchased_precursors
    DROP CONSTRAINT IF EXISTS fk_cbam_purch_prec_updated_by;
ALTER TABLE cbam_purchased_precursor_product_uses
    DROP CONSTRAINT IF EXISTS fk_cbam_purch_prec_use_created_by;
ALTER TABLE cbam_purchased_precursor_product_uses
    DROP CONSTRAINT IF EXISTS fk_cbam_purch_prec_use_updated_by;
ALTER TABLE cbam_purchased_precursors DROP COLUMN IF EXISTS created_by_user_id;
ALTER TABLE cbam_purchased_precursors DROP COLUMN IF EXISTS updated_by_user_id;
ALTER TABLE cbam_purchased_precursor_product_uses DROP COLUMN IF EXISTS created_by_user_id;
ALTER TABLE cbam_purchased_precursor_product_uses DROP COLUMN IF EXISTS updated_by_user_id;
"""
    )
