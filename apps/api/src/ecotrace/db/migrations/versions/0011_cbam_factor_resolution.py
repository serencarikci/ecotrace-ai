"""CBAM Phase 4B factor resolution foundation (sources, definitions, values, resolutions)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011_cbam_factor_resolution"
down_revision: str | None = "0010_cbam_allocation_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_reference_sources (
    id UUID NOT NULL,
    organization_id UUID,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    publisher VARCHAR(255),
    version_label VARCHAR(64),
    publication_year INTEGER,
    reference_url VARCHAR(512),
    description TEXT,
    status VARCHAR(32) NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_reference_sources PRIMARY KEY (id),
    CONSTRAINT ck_cbam_reference_sources_reference_source_type
        CHECK (source_type IN (
            'STANDARD_REFERENCE',
            'PRIMARY_MEASUREMENT',
            'SUPPLIER_DECLARATION',
            'MANUAL_APPROVED',
            'OTHER'
        )),
    CONSTRAINT ck_cbam_reference_sources_reference_source_status
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')),
    CONSTRAINT fk_cbam_reference_sources_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_reference_sources_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_reference_sources_updated_by_user_id_users
        FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_reference_sources_organization_id "
        "ON cbam_reference_sources (organization_id)"
    )
    op.execute("CREATE INDEX ix_cbam_reference_sources_status ON cbam_reference_sources (status)")
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_reference_source_org_code
ON cbam_reference_sources (
    COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'),
    code
)
"""
    )

    op.execute(
        """
CREATE TABLE cbam_factor_definitions (
    id UUID NOT NULL,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    factor_category VARCHAR(64) NOT NULL,
    activity_type VARCHAR(64),
    property_code VARCHAR(64),
    input_unit_family VARCHAR(32),
    output_unit VARCHAR(32),
    description TEXT,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_factor_definitions PRIMARY KEY (id),
    CONSTRAINT uq_cbam_factor_definition_code UNIQUE (code),
    CONSTRAINT ck_cbam_factor_definitions_factor_definition_category
        CHECK (factor_category IN (
            'ACTIVITY_PROPERTY',
            'EMISSION_FACTOR',
            'EMBEDDED_EMISSION_FACTOR',
            'ENERGY_FACTOR',
            'OTHER'
        )),
    CONSTRAINT ck_cbam_factor_definitions_factor_definition_status
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED'))
)
"""
    )
    op.execute("CREATE INDEX ix_cbam_factor_definitions_status ON cbam_factor_definitions (status)")
    op.execute(
        "CREATE INDEX ix_cbam_factor_definitions_category "
        "ON cbam_factor_definitions (factor_category)"
    )

    op.execute(
        """
CREATE TABLE cbam_factor_values (
    id UUID NOT NULL,
    organization_id UUID,
    factor_definition_id UUID NOT NULL,
    reference_source_id UUID NOT NULL,
    activity_type VARCHAR(64),
    numeric_value NUMERIC(24, 8) NOT NULL,
    unit VARCHAR(64) NOT NULL,
    valid_from DATE,
    valid_until DATE,
    geography_code VARCHAR(64),
    supplier_name VARCHAR(255),
    facility_specific BOOLEAN NOT NULL DEFAULT FALSE,
    data_source_type VARCHAR(32) NOT NULL,
    source_reference VARCHAR(512),
    notes TEXT,
    status VARCHAR(32) NOT NULL,
    row_version INTEGER DEFAULT 1 NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE,
    created_by_user_id UUID,
    reviewed_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_factor_values PRIMARY KEY (id),
    CONSTRAINT ck_cbam_factor_values_factor_value_data_source_type
        CHECK (data_source_type IN ('PRIMARY', 'DEFAULT_REFERENCE')),
    CONSTRAINT ck_cbam_factor_values_factor_value_status
        CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
    CONSTRAINT ck_cbam_factor_values_factor_value_positive
        CHECK (numeric_value > 0),
    CONSTRAINT ck_cbam_factor_values_factor_value_row_version_positive
        CHECK (row_version >= 1),
    CONSTRAINT fk_cbam_factor_values_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_factor_values_definition
        FOREIGN KEY(factor_definition_id)
        REFERENCES cbam_factor_definitions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_factor_values_reference_source
        FOREIGN KEY(reference_source_id)
        REFERENCES cbam_reference_sources (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_factor_values_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_factor_values_reviewed_by_user_id_users
        FOREIGN KEY(reviewed_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_factor_values_updated_by_user_id_users
        FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_factor_values_organization_id ON cbam_factor_values (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_factor_values_definition_status "
        "ON cbam_factor_values (factor_definition_id, status)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_factor_values_activity_type_status "
        "ON cbam_factor_values (activity_type, status)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_factor_values_org_definition "
        "ON cbam_factor_values (organization_id, factor_definition_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_factor_values_validity "
        "ON cbam_factor_values (valid_from, valid_until)"
    )

    op.execute(
        """
CREATE TABLE cbam_factor_resolutions (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_id UUID NOT NULL,
    factor_definition_id UUID NOT NULL,
    resolution_status VARCHAR(64) NOT NULL,
    selected_activity_property_id UUID,
    selected_factor_value_id UUID,
    selected_value NUMERIC(24, 8),
    selected_unit VARCHAR(64),
    source_precedence VARCHAR(64),
    resolution_reason TEXT NOT NULL,
    resolver_version VARCHAR(64) NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_by_user_id UUID,
    superseded_at TIMESTAMP WITH TIME ZONE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_factor_resolutions PRIMARY KEY (id),
    CONSTRAINT ck_cbam_factor_resolutions_factor_resolution_source_type
        CHECK (source_type IN (
            'ACTIVITY_RECORD',
            'PURCHASED_INPUT_RECORD',
            'ALLOCATION_RESULT'
        )),
    CONSTRAINT ck_cbam_factor_resolutions_factor_resolution_status
        CHECK (resolution_status IN (
            'RESOLVED_PRIMARY',
            'RESOLVED_DEFAULT',
            'UNRESOLVED',
            'AMBIGUOUS',
            'INCOMPATIBLE_UNIT',
            'OUTSIDE_VALIDITY',
            'BLOCKED'
        )),
    CONSTRAINT fk_cbam_factor_resolutions_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_factor_resolutions_binding
        FOREIGN KEY(reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_factor_resolutions_definition
        FOREIGN KEY(factor_definition_id)
        REFERENCES cbam_factor_definitions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_factor_resolutions_activity_property
        FOREIGN KEY(selected_activity_property_id)
        REFERENCES cbam_activity_properties (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_factor_resolutions_factor_value
        FOREIGN KEY(selected_factor_value_id)
        REFERENCES cbam_factor_values (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_factor_resolutions_resolved_by_user_id_users
        FOREIGN KEY(resolved_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_factor_resolutions_organization_id "
        "ON cbam_factor_resolutions (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_factor_resolutions_org_binding "
        "ON cbam_factor_resolutions (organization_id, reporting_period_binding_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_factor_resolutions_source "
        "ON cbam_factor_resolutions (source_type, source_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_factor_resolutions_binding_status "
        "ON cbam_factor_resolutions (reporting_period_binding_id, resolution_status)"
    )

    op.execute(
        """
INSERT INTO cbam_reference_sources (
    id, organization_id, code, name, source_type, publisher, description, status
) VALUES
(
    'a1000000-0000-4000-8000-000000000001',
    NULL,
    'IPCC',
    'IPCC',
    'STANDARD_REFERENCE',
    'IPCC',
    'Platform source metadata only. No numerical factors are seeded.',
    'ACTIVE'
),
(
    'a1000000-0000-4000-8000-000000000002',
    NULL,
    'DEFRA',
    'DEFRA',
    'STANDARD_REFERENCE',
    'DEFRA',
    'Platform source metadata only. No numerical factors are seeded.',
    'ACTIVE'
),
(
    'a1000000-0000-4000-8000-000000000003',
    NULL,
    'EPA',
    'EPA',
    'STANDARD_REFERENCE',
    'EPA',
    'Platform source metadata only. No numerical factors are seeded.',
    'ACTIVE'
),
(
    'a1000000-0000-4000-8000-000000000004',
    NULL,
    'PRIMARY_MEASUREMENT',
    'Primary measurement',
    'PRIMARY_MEASUREMENT',
    NULL,
    'Customer/supplier measured value metadata label.',
    'ACTIVE'
),
(
    'a1000000-0000-4000-8000-000000000005',
    NULL,
    'SUPPLIER',
    'Supplier declaration',
    'SUPPLIER_DECLARATION',
    NULL,
    'Supplier-declared value metadata label.',
    'ACTIVE'
),
(
    'a1000000-0000-4000-8000-000000000006',
    NULL,
    'MANUAL_APPROVED_REFERENCE',
    'Manual approved reference',
    'MANUAL_APPROVED',
    NULL,
    'Manually approved organization/platform reference metadata label.',
    'ACTIVE'
)
"""
    )
    op.execute(
        """
INSERT INTO cbam_factor_definitions (
    id, code, name, factor_category, activity_type, property_code,
    input_unit_family, output_unit, description, status
) VALUES
(
    'b1000000-0000-4000-8000-000000000001',
    'NET_CALORIFIC_VALUE',
    'Net calorific value',
    'ACTIVITY_PROPERTY',
    NULL,
    'NET_CALORIFIC_VALUE',
    NULL,
    NULL,
    'Activity property definition. No numerical defaults are seeded.',
    'ACTIVE'
),
(
    'b1000000-0000-4000-8000-000000000002',
    'GENERIC_EMISSION_FACTOR',
    'Generic emission factor (metadata)',
    'EMISSION_FACTOR',
    NULL,
    NULL,
    NULL,
    NULL,
    'Placeholder emission-factor definition. No numerical factors are seeded.',
    'ACTIVE'
),
(
    'b1000000-0000-4000-8000-000000000003',
    'SUPPLIER_EMBEDDED_EMISSION',
    'Supplier embedded emission declaration',
    'EMBEDDED_EMISSION_FACTOR',
    NULL,
    NULL,
    NULL,
    NULL,
    'Resolves supplier-declared embedded emission fields on purchased inputs. '
    'No numerical defaults are seeded.',
    'ACTIVE'
)
"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cbam_factor_resolutions")
    op.execute("DROP TABLE IF EXISTS cbam_factor_values")
    op.execute("DROP TABLE IF EXISTS cbam_factor_definitions")
    op.execute("DROP TABLE IF EXISTS cbam_reference_sources")
