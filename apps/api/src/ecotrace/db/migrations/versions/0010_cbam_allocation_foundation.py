"""CBAM Phase 4A allocation foundation (rules + quantity results)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0010_cbam_allocation_foundation'
down_revision: str | None = '0009_cbam_data_collection'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_allocation_rules (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    installation_profile_id UUID NOT NULL,
    product_profile_version_id UUID,
    allocation_method VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    allocation_ratio NUMERIC(24, 12),
    numerator_production_record_id UUID,
    denominator_production_record_id UUID,
    numerator_quantity NUMERIC(24, 8),
    denominator_quantity NUMERIC(24, 8),
    quantity_unit VARCHAR(32),
    rationale TEXT,
    source_reference VARCHAR(512),
    status VARCHAR(32) NOT NULL,
    row_version INTEGER DEFAULT 1 NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_allocation_rules PRIMARY KEY (id),
    CONSTRAINT ck_cbam_allocation_rules_allocation_rule_status
        CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
    CONSTRAINT ck_cbam_allocation_rules_allocation_method
        CHECK (allocation_method IN (
            'DIRECT_ASSIGNMENT',
            'PRODUCTION_QUANTITY_RATIO',
            'MANUAL_RATIO'
        )),
    CONSTRAINT ck_cbam_allocation_rules_allocation_ratio_bounds
        CHECK (
            allocation_ratio IS NULL
            OR (allocation_ratio >= 0 AND allocation_ratio <= 1)
        ),
    CONSTRAINT ck_cbam_allocation_rules_allocation_rule_row_version_positive
        CHECK (row_version >= 1),
    CONSTRAINT fk_cbam_allocation_rules_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_allocation_rules_binding
        FOREIGN KEY(reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_allocation_rules_installation
        FOREIGN KEY(installation_profile_id)
        REFERENCES cbam_installation_profiles (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_allocation_rules_product_profile
        FOREIGN KEY(product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_allocation_rules_numerator
        FOREIGN KEY(numerator_production_record_id)
        REFERENCES cbam_production_records (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_allocation_rules_denominator
        FOREIGN KEY(denominator_production_record_id)
        REFERENCES cbam_production_records (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_allocation_rules_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_allocation_rules_updated_by_user_id_users
        FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_rules_organization_id '
        'ON cbam_allocation_rules (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_rules_org_binding '
        'ON cbam_allocation_rules (organization_id, reporting_period_binding_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_rules_org_installation '
        'ON cbam_allocation_rules (organization_id, installation_profile_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_rules_org_product '
        'ON cbam_allocation_rules (organization_id, product_profile_version_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_rules_status '
        'ON cbam_allocation_rules (status)'
    )
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_allocation_one_active_per_scope
ON cbam_allocation_rules (
    organization_id,
    reporting_period_binding_id,
    installation_profile_id,
    COALESCE(product_profile_version_id, '00000000-0000-0000-0000-000000000000')
)
WHERE status = 'ACTIVE'
"""
    )

    op.execute(
        """
CREATE TABLE cbam_allocation_results (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    allocation_rule_id UUID NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_id UUID NOT NULL,
    source_quantity NUMERIC(24, 8) NOT NULL,
    source_unit VARCHAR(32) NOT NULL,
    allocation_ratio NUMERIC(24, 12) NOT NULL,
    allocated_quantity NUMERIC(24, 8) NOT NULL,
    allocated_unit VARCHAR(32) NOT NULL,
    allocation_method VARCHAR(64) NOT NULL,
    calculation_version VARCHAR(64) NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    superseded_at TIMESTAMP WITH TIME ZONE,
    created_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_allocation_results PRIMARY KEY (id),
    CONSTRAINT ck_cbam_allocation_results_allocation_source_type
        CHECK (source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD')),
    CONSTRAINT ck_cbam_allocation_results_allocation_result_ratio_bounds
        CHECK (allocation_ratio >= 0 AND allocation_ratio <= 1),
    CONSTRAINT ck_cbam_allocation_results_allocation_source_quantity_positive
        CHECK (source_quantity > 0),
    CONSTRAINT ck_cbam_allocation_results_allocation_allocated_non_negative
        CHECK (allocated_quantity >= 0),
    CONSTRAINT fk_cbam_allocation_results_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_allocation_results_binding
        FOREIGN KEY(reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_allocation_results_rule
        FOREIGN KEY(allocation_rule_id)
        REFERENCES cbam_allocation_rules (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_allocation_results_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_results_organization_id '
        'ON cbam_allocation_results (organization_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_results_org_binding '
        'ON cbam_allocation_results (organization_id, reporting_period_binding_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_results_rule_id '
        'ON cbam_allocation_results (allocation_rule_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_results_source '
        'ON cbam_allocation_results (source_type, source_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_allocation_results_current_lookup '
        'ON cbam_allocation_results ('
        'organization_id, allocation_rule_id, source_type, source_id, is_current)'
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS cbam_allocation_results')
    op.execute('DROP TABLE IF EXISTS cbam_allocation_rules')
