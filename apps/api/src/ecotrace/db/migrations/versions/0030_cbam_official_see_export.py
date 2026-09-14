"""CBAM Phase 12A: Official SEE Excel export audit + artifact metadata.

Revision ID: 0030_cbam_official_see
Revises: 0029_cbam_pee_v2

Stores Official SEE export run audit fields and artifact metadata.
XLSX bytes live on the export_storage filesystem (never in Postgres).
Idempotency unique on (organization_id, reporting_period_binding_id, client_request_id).

The revision id is abbreviated because alembic_version.version_num is varchar(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0030_cbam_official_see'
down_revision: str | None = '0029_cbam_pee_v2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_official_see_export_runs (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    client_request_id UUID NOT NULL,
    generation_status VARCHAR(64) NOT NULL,
    validation_status VARCHAR(64) NOT NULL,
    formula_parity_status VARCHAR(64) NOT NULL,
    mapping_version VARCHAR(64) NOT NULL,
    template_filename VARCHAR(512) NOT NULL,
    template_version VARCHAR(64) NOT NULL,
    template_sha256 VARCHAR(64) NOT NULL,
    pee_result_id UUID,
    dea_result_id UUID,
    iea_result_id UUID,
    process_snapshot_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    precursor_snapshot_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_fingerprint VARCHAR(64),
    output_sha256 VARCHAR(64),
    output_size_bytes INTEGER,
    failure_diagnostics JSONB,
    generated_by_user_id UUID,
    generated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_official_see_export_runs PRIMARY KEY (id),
    CONSTRAINT ck_cbam_ose_runs_generation_status CHECK (
        generation_status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')
    ),
    CONSTRAINT ck_cbam_ose_runs_validation_status CHECK (
        validation_status IN ('PENDING', 'PASSED', 'FAILED', 'SKIPPED')
    ),
    CONSTRAINT ck_cbam_ose_runs_parity_status CHECK (
        formula_parity_status IN (
            'PENDING', 'PASSED', 'FAILED', 'ENGINE_UNAVAILABLE'
        )
    ),
    CONSTRAINT fk_cbam_ose_runs_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_ose_runs_binding
        FOREIGN KEY (reporting_period_binding_id)
            REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_ose_runs_pee
        FOREIGN KEY (pee_result_id)
            REFERENCES cbam_product_embedded_emissions_results (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_ose_runs_dea
        FOREIGN KEY (dea_result_id)
            REFERENCES cbam_direct_emissions_allocation_results (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_ose_runs_iea
        FOREIGN KEY (iea_result_id)
            REFERENCES cbam_indirect_emissions_allocation_results (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_ose_runs_user
        FOREIGN KEY (generated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_ose_runs_org ON cbam_official_see_export_runs (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_ose_runs_org_binding ON cbam_official_see_export_runs '
        '(organization_id, reporting_period_binding_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_ose_runs_status ON cbam_official_see_export_runs '
        '(generation_status)'
    )
    op.execute(
        'CREATE UNIQUE INDEX uq_cbam_ose_runs_org_binding_client_request '
        'ON cbam_official_see_export_runs '
        '(organization_id, reporting_period_binding_id, client_request_id)'
    )

    op.execute(
        """
CREATE TABLE cbam_official_see_export_artifacts (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    export_run_id UUID NOT NULL,
    artifact_type VARCHAR(32) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    storage_uri VARCHAR(1024) NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_official_see_export_artifacts PRIMARY KEY (id),
    CONSTRAINT ck_cbam_ose_artifacts_type CHECK (artifact_type IN ('XLSX', 'JSON_SUMMARY')),
    CONSTRAINT fk_cbam_ose_artifacts_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_ose_artifacts_run
        FOREIGN KEY (export_run_id)
            REFERENCES cbam_official_see_export_runs (id) ON DELETE CASCADE
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_ose_artifacts_org '
        'ON cbam_official_see_export_artifacts (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_ose_artifacts_run '
        'ON cbam_official_see_export_artifacts (export_run_id)'
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS cbam_official_see_export_artifacts')
    op.execute('DROP TABLE IF EXISTS cbam_official_see_export_runs')
