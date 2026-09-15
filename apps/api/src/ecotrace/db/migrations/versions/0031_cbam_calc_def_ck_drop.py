"""Drop obsolete calculation-definition check constraints from 0015.

Revision ID: 0031_cbam_calc_def_ck
Revises: 0030_cbam_official_see

Migration 0023 replaced factor/type checks with ``calc_def_*`` names but did not
drop the legacy ``ck_cbam_calc_def_*`` constraints. Empty→head installs then
rejected PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1 definitions. This revision
is idempotent for databases that already applied the 0023 fix.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031_cbam_calc_def_ck"
down_revision: str | None = "0030_cbam_official_see"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
ALTER TABLE cbam_calculation_definitions
    DROP CONSTRAINT IF EXISTS ck_cbam_calc_def_type;
ALTER TABLE cbam_calculation_definitions
    DROP CONSTRAINT IF EXISTS ck_cbam_calc_def_factor_req;
"""
    )


def downgrade() -> None:
    # Do not recreate the obsolete constraints; 0023's calc_def_* remain authoritative.
    pass
