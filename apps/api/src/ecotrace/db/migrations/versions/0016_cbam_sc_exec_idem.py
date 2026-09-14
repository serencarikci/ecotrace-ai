"""CBAM Phase 4A stationary-combustion execution idempotency columns."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0016_cbam_sc_exec_idem'
down_revision: str | None = '0015_cbam_sc_calc_result'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
ALTER TABLE cbam_stationary_combustion_results
ADD COLUMN client_request_id UUID,
ADD COLUMN request_fingerprint VARCHAR(64),
ADD COLUMN calculation_reference_date DATE
"""
    )
    # Historical rows stay NULL. New API executions always set client_request_id.
    # Uniqueness is scoped to org + binding + client_request_id (SC table only).
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_sc_result_org_binding_client_request
ON cbam_stationary_combustion_results (
    organization_id,
    reporting_period_binding_id,
    client_request_id
)
WHERE client_request_id IS NOT NULL
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_results_client_request_id '
        'ON cbam_stationary_combustion_results (client_request_id)'
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_cbam_sc_results_client_request_id')
    op.execute('DROP INDEX IF EXISTS uq_cbam_sc_result_org_binding_client_request')
    op.execute(
        """
ALTER TABLE cbam_stationary_combustion_results
DROP COLUMN IF EXISTS calculation_reference_date,
DROP COLUMN IF EXISTS request_fingerprint,
DROP COLUMN IF EXISTS client_request_id
"""
    )
