"""CBAM Phase 5 minimal calculation engine (definitions, runs, results)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0012_cbam_minimal_calculation'
down_revision: str | None = '0011_cbam_factor_resolution'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_calculation_definitions (
    id UUID NOT NULL,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    calculation_type VARCHAR(64) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    factor_definition_id UUID NOT NULL,
    output_unit VARCHAR(64),
    formula_version VARCHAR(64) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_calculation_definitions PRIMARY KEY (id),
    CONSTRAINT uq_cbam_calculation_definition_code UNIQUE (code),
    CONSTRAINT ck_cbam_calculation_definitions_calculation_definition_type
        CHECK (calculation_type IN ('MULTIPLY_ACTIVITY_BY_FACTOR')),
    CONSTRAINT ck_cbam_calculation_definitions_calculation_definition_source_type
        CHECK (source_type IN (
            'ACTIVITY_RECORD',
            'PURCHASED_INPUT_RECORD',
            'ALLOCATION_RESULT'
        )),
    CONSTRAINT ck_cbam_calculation_definitions_calculation_definition_status
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')),
    CONSTRAINT fk_cbam_calculation_definitions_factor_definition_id_cbam_factor_definitions
        FOREIGN KEY(factor_definition_id) REFERENCES cbam_factor_definitions (id) ON DELETE RESTRICT
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_definitions_status '
        'ON cbam_calculation_definitions (status)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_definitions_factor '
        'ON cbam_calculation_definitions (factor_definition_id)'
    )

    op.execute(
        """
CREATE TABLE cbam_calculation_runs (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    status VARCHAR(32) NOT NULL,
    calculation_version VARCHAR(64) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_summary TEXT,
    calculated_count INTEGER NOT NULL DEFAULT 0,
    blocked_count INTEGER NOT NULL DEFAULT 0,
    invalid_count INTEGER NOT NULL DEFAULT 0,
    primary_factor_count INTEGER NOT NULL DEFAULT 0,
    default_factor_count INTEGER NOT NULL DEFAULT 0,
    created_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_calculation_runs PRIMARY KEY (id),
    CONSTRAINT ck_cbam_calculation_runs_calculation_run_status
        CHECK (status IN (
            'DRAFT',
            'RUNNING',
            'COMPLETED',
            'PARTIALLY_COMPLETED',
            'FAILED',
            'ARCHIVED'
        )),
    CONSTRAINT fk_cbam_calculation_runs_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_calculation_runs_reporting_period_binding_id_cbam_reporting_period_bindings
        FOREIGN KEY(reporting_period_binding_id)
            REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_calculation_runs_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_runs_organization_id '
        'ON cbam_calculation_runs (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_runs_org_binding '
        'ON cbam_calculation_runs (organization_id, reporting_period_binding_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_runs_status ON cbam_calculation_runs (status)'
    )

    op.execute(
        """
CREATE TABLE cbam_calculation_results (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    calculation_run_id UUID NOT NULL,
    calculation_definition_id UUID NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_id UUID NOT NULL,
    allocation_result_id UUID,
    factor_resolution_id UUID NOT NULL,
    source_quantity NUMERIC(24, 8),
    source_unit VARCHAR(32),
    factor_value NUMERIC(24, 8),
    factor_unit VARCHAR(64),
    result_value NUMERIC(24, 8),
    result_unit VARCHAR(64),
    calculation_type VARCHAR(64) NOT NULL,
    formula_version VARCHAR(64) NOT NULL,
    status VARCHAR(64) NOT NULL,
    error_code VARCHAR(64),
    error_message TEXT,
    input_fingerprint VARCHAR(255) NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT true,
    superseded_at TIMESTAMP WITH TIME ZONE,
    factor_resolution_status VARCHAR(64),
    created_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_calculation_results PRIMARY KEY (id),
    CONSTRAINT ck_cbam_calculation_results_calculation_result_source_type
        CHECK (source_type IN (
            'ACTIVITY_RECORD',
            'PURCHASED_INPUT_RECORD',
            'ALLOCATION_RESULT'
        )),
    CONSTRAINT ck_cbam_calculation_results_calculation_result_status
        CHECK (status IN (
            'CALCULATED',
            'BLOCKED',
            'INVALID_INPUT',
            'INCOMPATIBLE_UNIT',
            'UNRESOLVED_FACTOR',
            'AMBIGUOUS_FACTOR',
            'UNSUPPORTED_FORMULA'
        )),
    CONSTRAINT ck_cbam_calculation_results_calculation_result_type
        CHECK (calculation_type IN ('MULTIPLY_ACTIVITY_BY_FACTOR')),
    CONSTRAINT fk_cbam_calculation_results_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_calculation_results_calculation_run_id_cbam_calculation_runs
        FOREIGN KEY(calculation_run_id) REFERENCES cbam_calculation_runs (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_calculation_results_calculation_definition_id_cbam_calculation_definitions
        FOREIGN KEY(calculation_definition_id)
            REFERENCES cbam_calculation_definitions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_calculation_results_allocation_result_id_cbam_allocation_results
        FOREIGN KEY(allocation_result_id)
            REFERENCES cbam_allocation_results (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_calculation_results_factor_resolution_id_cbam_factor_resolutions
        FOREIGN KEY(factor_resolution_id)
            REFERENCES cbam_factor_resolutions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_calculation_results_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_results_organization_id '
        'ON cbam_calculation_results (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_results_run_status '
        'ON cbam_calculation_results (calculation_run_id, status)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_results_source '
        'ON cbam_calculation_results (source_type, source_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_results_factor_resolution '
        'ON cbam_calculation_results (factor_resolution_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_calculation_results_allocation '
        'ON cbam_calculation_results (allocation_result_id)'
    )
    op.execute(
        """
CREATE UNIQUE INDEX ix_cbam_calculation_results_input_key_current
ON cbam_calculation_results (organization_id, input_fingerprint)
WHERE is_current = true
"""
    )

    op.execute(
        """
INSERT INTO cbam_calculation_definitions (
    id, code, name, calculation_type, source_type, factor_definition_id,
    output_unit, formula_version, description, status
)
SELECT
    'c1000000-0000-4000-8000-000000000001',
    'MULTIPLY_ACTIVITY_BY_GENERIC_EF',
    'Multiply activity quantity by generic emission factor',
    'MULTIPLY_ACTIVITY_BY_FACTOR',
    'ACTIVITY_RECORD',
    fd.id,
    NULL,
    'multiply-activity-by-factor-v1',
    'result = activity_quantity × factor_value when units are dimensionally compatible. '
    'No numeric factors are seeded.',
    'ACTIVE'
FROM cbam_factor_definitions fd
WHERE fd.code = 'GENERIC_EMISSION_FACTOR'
"""
    )
    op.execute(
        """
INSERT INTO cbam_calculation_definitions (
    id, code, name, calculation_type, source_type, factor_definition_id,
    output_unit, formula_version, description, status
)
SELECT
    'c1000000-0000-4000-8000-000000000002',
    'MULTIPLY_ALLOCATION_BY_GENERIC_EF',
    'Multiply allocated quantity by generic emission factor',
    'MULTIPLY_ACTIVITY_BY_FACTOR',
    'ALLOCATION_RESULT',
    fd.id,
    NULL,
    'multiply-activity-by-factor-v1',
    'result = allocated_quantity × factor_value when units are dimensionally compatible. '
    'No numeric factors are seeded.',
    'ACTIVE'
FROM cbam_factor_definitions fd
WHERE fd.code = 'GENERIC_EMISSION_FACTOR'
"""
    )
    op.execute(
        """
INSERT INTO cbam_calculation_definitions (
    id, code, name, calculation_type, source_type, factor_definition_id,
    output_unit, formula_version, description, status
)
SELECT
    'c1000000-0000-4000-8000-000000000003',
    'MULTIPLY_PURCHASED_BY_GENERIC_EF',
    'Multiply purchased-input consumed quantity by generic emission factor',
    'MULTIPLY_ACTIVITY_BY_FACTOR',
    'PURCHASED_INPUT_RECORD',
    fd.id,
    NULL,
    'multiply-activity-by-factor-v1',
    'result = consumed_quantity × factor_value when units are dimensionally compatible. '
    'Purchased quantity is never substituted. No numeric factors are seeded.',
    'ACTIVE'
FROM cbam_factor_definitions fd
WHERE fd.code = 'GENERIC_EMISSION_FACTOR'
"""
    )
    op.execute(
        """
INSERT INTO cbam_calculation_definitions (
    id, code, name, calculation_type, source_type, factor_definition_id,
    output_unit, formula_version, description, status
)
SELECT
    'c1000000-0000-4000-8000-000000000004',
    'MULTIPLY_PURCHASED_BY_SUPPLIER_EMBEDDED',
    'Multiply purchased-input consumed quantity by resolved supplier embedded intensity',
    'MULTIPLY_ACTIVITY_BY_FACTOR',
    'PURCHASED_INPUT_RECORD',
    fd.id,
    NULL,
    'multiply-activity-by-factor-v1',
    'Uses only an already-resolved SUPPLIER_EMBEDDED_EMISSION value. '
    'No fabrication or GWP conversion.',
    'ACTIVE'
FROM cbam_factor_definitions fd
WHERE fd.code = 'SUPPLIER_EMBEDDED_EMISSION'
"""
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS cbam_calculation_results')
    op.execute('DROP TABLE IF EXISTS cbam_calculation_runs')
    op.execute('DROP TABLE IF EXISTS cbam_calculation_definitions')
