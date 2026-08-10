"""CBAM Phase 6 Excel mapping and SKDM report export foundation."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0013_cbam_excel_export'
down_revision: str | None = '0012_cbam_minimal_calculation'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_export_templates (
    id UUID NOT NULL,
    organization_id UUID,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    template_type VARCHAR(64) NOT NULL,
    version VARCHAR(64) NOT NULL,
    mapping_version VARCHAR(64) NOT NULL,
    storage_uri VARCHAR(1024) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    description TEXT,
    activated_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE,
    created_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_export_templates PRIMARY KEY (id),
    CONSTRAINT ck_cbam_export_templates_export_template_type
        CHECK (template_type IN (
            'INTERNAL_SKDM', 'OFFICIAL_CBAM_TEMPLATE', 'CUSTOMER_TEMPLATE'
        )),
    CONSTRAINT ck_cbam_export_templates_export_template_status
        CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
    CONSTRAINT fk_cbam_export_templates_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_export_templates_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_export_templates_organization_id '
        'ON cbam_export_templates (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_export_templates_status ON cbam_export_templates (status)'
    )
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_export_template_org_code_version
ON cbam_export_templates (
    COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'),
    code,
    version
)
"""
    )

    op.execute(
        """
CREATE TABLE cbam_export_mappings (
    id UUID NOT NULL,
    export_template_id UUID NOT NULL,
    mapping_code VARCHAR(128) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_path VARCHAR(255) NOT NULL,
    worksheet_name VARCHAR(128) NOT NULL,
    destination_type VARCHAR(64) NOT NULL,
    destination_reference VARCHAR(255) NOT NULL,
    value_type VARCHAR(32) NOT NULL,
    required BOOLEAN NOT NULL DEFAULT false,
    transformation_code VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_export_mappings PRIMARY KEY (id),
    CONSTRAINT uq_cbam_export_mapping_template_code
        UNIQUE (export_template_id, mapping_code),
    CONSTRAINT ck_cbam_export_mappings_export_mapping_source_type
        CHECK (source_type IN (
            'ORGANIZATION', 'INSTALLATION', 'REPORTING_PERIOD', 'PRODUCT',
            'PRODUCTION_RECORD', 'ACTIVITY_RECORD', 'PURCHASED_INPUT',
            'ALLOCATION_RESULT', 'FACTOR_RESOLUTION', 'CALCULATION_RESULT',
            'CALCULATED_SUMMARY', 'CONSTANT'
        )),
    CONSTRAINT ck_cbam_export_mappings_export_mapping_destination_type
        CHECK (destination_type IN (
            'CELL', 'NAMED_RANGE', 'TABLE_COLUMN', 'REPEATING_ROW'
        )),
    CONSTRAINT ck_cbam_export_mappings_export_mapping_value_type
        CHECK (value_type IN (
            'STRING', 'NUMBER', 'DATE', 'DATETIME', 'BOOLEAN', 'ENUM', 'UNIT'
        )),
    CONSTRAINT ck_cbam_export_mappings_export_mapping_transformation
        CHECK (
            transformation_code IN (
                'NONE', 'DECIMAL_TO_NUMBER', 'DATE_TO_EXCEL_DATE',
                'DATETIME_TO_EXCEL_DATETIME', 'ENUM_TO_DISPLAY_LABEL',
                'UNIT_DISPLAY', 'BOOLEAN_TO_YES_NO'
            ) OR transformation_code IS NULL
        ),
    CONSTRAINT fk_cbam_export_mappings_export_template_id_cbam_export_templates
        FOREIGN KEY(export_template_id)
            REFERENCES cbam_export_templates (id) ON DELETE CASCADE
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_export_mappings_template_id '
        'ON cbam_export_mappings (export_template_id)'
    )

    op.execute(
        """
CREATE TABLE cbam_export_runs (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    export_template_id UUID NOT NULL,
    calculation_run_id UUID,
    status VARCHAR(64) NOT NULL,
    template_version VARCHAR(64) NOT NULL,
    mapping_version VARCHAR(64) NOT NULL,
    mapping_checksum VARCHAR(64) NOT NULL,
    template_checksum VARCHAR(64) NOT NULL,
    input_checksum VARCHAR(64),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    warning_summary TEXT,
    application_version VARCHAR(64),
    created_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_export_runs PRIMARY KEY (id),
    CONSTRAINT ck_cbam_export_runs_export_run_status
        CHECK (status IN (
            'PENDING', 'RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS',
            'FAILED', 'CANCELLED'
        )),
    CONSTRAINT fk_cbam_export_runs_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_export_runs_reporting_period_binding_id_cbam_reporting_period_bindings
        FOREIGN KEY(reporting_period_binding_id)
            REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_export_runs_export_template_id_cbam_export_templates
        FOREIGN KEY(export_template_id)
            REFERENCES cbam_export_templates (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_export_runs_calculation_run_id_cbam_calculation_runs
        FOREIGN KEY(calculation_run_id)
            REFERENCES cbam_calculation_runs (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_export_runs_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_export_runs_organization_id ON cbam_export_runs (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_export_runs_org_binding '
        'ON cbam_export_runs (organization_id, reporting_period_binding_id)'
    )
    op.execute('CREATE INDEX ix_cbam_export_runs_status ON cbam_export_runs (status)')

    op.execute(
        """
CREATE TABLE cbam_export_artifacts (
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
    CONSTRAINT pk_cbam_export_artifacts PRIMARY KEY (id),
    CONSTRAINT ck_cbam_export_artifacts_export_artifact_type
        CHECK (artifact_type IN (
            'XLSX', 'CSV_SUMMARY', 'JSON_SUMMARY', 'HTML_REPORT'
        )),
    CONSTRAINT fk_cbam_export_artifacts_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_export_artifacts_export_run_id_cbam_export_runs
        FOREIGN KEY(export_run_id) REFERENCES cbam_export_runs (id) ON DELETE CASCADE
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_export_artifacts_organization_id '
        'ON cbam_export_artifacts (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_export_artifacts_export_run_id '
        'ON cbam_export_artifacts (export_run_id)'
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS cbam_export_artifacts')
    op.execute('DROP TABLE IF EXISTS cbam_export_runs')
    op.execute('DROP TABLE IF EXISTS cbam_export_mappings')
    op.execute('DROP TABLE IF EXISTS cbam_export_templates')
