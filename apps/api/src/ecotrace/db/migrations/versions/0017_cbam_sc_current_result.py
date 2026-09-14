"""CBAM Phase 5A stationary-combustion current-result pointers."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0017_cbam_sc_current_result'
down_revision: str | None = '0016_cbam_sc_exec_idem'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enables composite FK so pointer org/binding/activity must match the result row.
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_sc_result_id_org_binding_activity
ON cbam_stationary_combustion_results (
    id,
    organization_id,
    reporting_period_binding_id,
    activity_record_id
)
"""
    )
    op.execute(
        """
CREATE TABLE cbam_stationary_combustion_current_results (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    reporting_period_binding_id UUID NOT NULL
        REFERENCES cbam_reporting_period_bindings(id) ON DELETE RESTRICT,
    activity_record_id UUID NOT NULL
        REFERENCES cbam_activity_records(id) ON DELETE RESTRICT,
    current_result_id UUID NOT NULL
        REFERENCES cbam_stationary_combustion_results(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_cbam_sc_current_org_binding_activity UNIQUE (
        organization_id,
        reporting_period_binding_id,
        activity_record_id
    ),
    CONSTRAINT fk_cbam_sc_current_result_identity FOREIGN KEY (
        current_result_id,
        organization_id,
        reporting_period_binding_id,
        activity_record_id
    ) REFERENCES cbam_stationary_combustion_results (
        id,
        organization_id,
        reporting_period_binding_id,
        activity_record_id
    ) ON DELETE RESTRICT
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_current_organization_id '
        'ON cbam_stationary_combustion_current_results (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_current_binding_id '
        'ON cbam_stationary_combustion_current_results (reporting_period_binding_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_sc_current_result_id '
        'ON cbam_stationary_combustion_current_results (current_result_id)'
    )
    # One-time deterministic backfill: newest successful result per activity
    # (created_at DESC, id DESC). Does not rewrite result snapshots.
    op.execute(
        """
INSERT INTO cbam_stationary_combustion_current_results (
    id,
    organization_id,
    reporting_period_binding_id,
    activity_record_id,
    current_result_id,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    ranked.organization_id,
    ranked.reporting_period_binding_id,
    ranked.activity_record_id,
    ranked.id,
    now(),
    now()
FROM (
    SELECT
        r.id,
        r.organization_id,
        r.reporting_period_binding_id,
        r.activity_record_id,
        ROW_NUMBER() OVER (
            PARTITION BY
                r.organization_id,
                r.reporting_period_binding_id,
                r.activity_record_id
            ORDER BY r.created_at DESC, r.id DESC
        ) AS rn
    FROM cbam_stationary_combustion_results r
    INNER JOIN cbam_calculation_runs run ON run.id = r.calculation_run_id
    WHERE run.status = 'COMPLETED'
) ranked
WHERE ranked.rn = 1
"""
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS cbam_stationary_combustion_current_results')
    op.execute('DROP INDEX IF EXISTS uq_cbam_sc_result_id_org_binding_activity')
