"""CBAM Phase 3 data-collection records (production, activity, purchased inputs)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_cbam_data_collection"
down_revision: str | None = "0008_cbam_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_production_records (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    installation_profile_id UUID NOT NULL,
    product_profile_version_id UUID,
    production_date DATE,
    period_start DATE,
    period_end DATE,
    quantity NUMERIC(24, 8) NOT NULL,
    unit VARCHAR(32) NOT NULL,
    notes TEXT,
    source_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    row_version INTEGER DEFAULT 1 NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_production_records PRIMARY KEY (id),
    CONSTRAINT ck_cbam_production_records_production_record_status
        CHECK (status IN ('active', 'archived')),
    CONSTRAINT ck_cbam_production_records_production_quantity_positive
        CHECK (quantity > 0),
    CONSTRAINT ck_cbam_production_records_production_row_version_positive
        CHECK (row_version >= 1),
    CONSTRAINT ck_cbam_production_records_production_period_dates
        CHECK (period_end IS NULL OR period_start IS NULL OR period_end >= period_start),
    CONSTRAINT fk_cbam_production_records_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_production_records_binding
        FOREIGN KEY(reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_production_records_installation
        FOREIGN KEY(installation_profile_id)
        REFERENCES cbam_installation_profiles (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_production_records_product_profile
        FOREIGN KEY(product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_production_records_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_production_records_updated_by_user_id_users
        FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_production_records_organization_id "
        "ON cbam_production_records (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_production_records_org_binding "
        "ON cbam_production_records (organization_id, reporting_period_binding_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_production_records_org_installation "
        "ON cbam_production_records (organization_id, installation_profile_id)"
    )
    op.execute("CREATE INDEX ix_cbam_production_records_status ON cbam_production_records (status)")

    op.execute(
        """
CREATE TABLE cbam_activity_records (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    installation_profile_id UUID NOT NULL,
    activity_group VARCHAR(32) NOT NULL,
    activity_type VARCHAR(64) NOT NULL,
    activity_date DATE,
    period_start DATE,
    period_end DATE,
    quantity NUMERIC(24, 8) NOT NULL,
    unit VARCHAR(32) NOT NULL,
    data_source_type VARCHAR(32) NOT NULL,
    source_reference VARCHAR(512),
    measurement_method VARCHAR(255),
    supplier_name VARCHAR(255),
    certificate_reference VARCHAR(255),
    process_type_code VARCHAR(64),
    process_description TEXT,
    biogenic_status VARCHAR(32),
    notes TEXT,
    status VARCHAR(32) NOT NULL,
    row_version INTEGER DEFAULT 1 NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_activity_records PRIMARY KEY (id),
    CONSTRAINT ck_cbam_activity_records_activity_record_status
        CHECK (status IN ('active', 'archived')),
    CONSTRAINT ck_cbam_activity_records_activity_quantity_positive
        CHECK (quantity > 0),
    CONSTRAINT ck_cbam_activity_records_activity_row_version_positive
        CHECK (row_version >= 1),
    CONSTRAINT ck_cbam_activity_records_activity_period_dates
        CHECK (period_end IS NULL OR period_start IS NULL OR period_end >= period_start),
    CONSTRAINT fk_cbam_activity_records_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_activity_records_binding
        FOREIGN KEY(reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_activity_records_installation
        FOREIGN KEY(installation_profile_id)
        REFERENCES cbam_installation_profiles (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_activity_records_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_activity_records_updated_by_user_id_users
        FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_activity_records_organization_id "
        "ON cbam_activity_records (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_activity_records_org_binding "
        "ON cbam_activity_records (organization_id, reporting_period_binding_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_activity_records_org_installation "
        "ON cbam_activity_records (organization_id, installation_profile_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_activity_records_binding_type "
        "ON cbam_activity_records (reporting_period_binding_id, activity_type)"
    )
    op.execute("CREATE INDEX ix_cbam_activity_records_status ON cbam_activity_records (status)")

    op.execute(
        """
CREATE TABLE cbam_activity_properties (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    activity_record_id UUID NOT NULL,
    property_code VARCHAR(64) NOT NULL,
    numeric_value NUMERIC(24, 8) NOT NULL,
    unit VARCHAR(32) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    source_reference VARCHAR(512),
    created_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_activity_properties PRIMARY KEY (id),
    CONSTRAINT uq_cbam_activity_property_record_code
        UNIQUE (activity_record_id, property_code),
    CONSTRAINT ck_cbam_activity_properties_activity_property_value_positive
        CHECK (numeric_value > 0),
    CONSTRAINT fk_cbam_activity_properties_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_activity_properties_activity_record
        FOREIGN KEY(activity_record_id) REFERENCES cbam_activity_records (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_activity_properties_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_activity_properties_organization_id "
        "ON cbam_activity_properties (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_activity_properties_activity_record_id "
        "ON cbam_activity_properties (activity_record_id)"
    )

    op.execute(
        """
CREATE TABLE cbam_purchased_input_records (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    installation_profile_id UUID NOT NULL,
    product_profile_version_id UUID,
    input_name VARCHAR(255) NOT NULL,
    supplier_name VARCHAR(255),
    quantity NUMERIC(24, 8) NOT NULL,
    unit VARCHAR(32) NOT NULL,
    received_date DATE,
    consumed_quantity NUMERIC(24, 8),
    consumed_unit VARCHAR(32),
    embedded_emission_value NUMERIC(24, 8),
    embedded_emission_unit VARCHAR(32),
    embedded_emission_source_type VARCHAR(32) NOT NULL,
    source_reference VARCHAR(512),
    notes TEXT,
    status VARCHAR(32) NOT NULL,
    row_version INTEGER DEFAULT 1 NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_purchased_input_records PRIMARY KEY (id),
    CONSTRAINT ck_cbam_purchased_input_records_purchased_input_status
        CHECK (status IN ('active', 'archived')),
    CONSTRAINT ck_cbam_purchased_input_records_purchased_quantity_positive
        CHECK (quantity > 0),
    CONSTRAINT ck_cbam_purchased_input_records_consumed_quantity_non_negative
        CHECK (consumed_quantity IS NULL OR consumed_quantity >= 0),
    CONSTRAINT ck_cbam_purchased_input_records_purchased_row_version_positive
        CHECK (row_version >= 1),
    CONSTRAINT fk_cbam_purchased_input_records_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_purchased_input_records_binding
        FOREIGN KEY(reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purchased_input_records_installation
        FOREIGN KEY(installation_profile_id)
        REFERENCES cbam_installation_profiles (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purchased_input_records_product_profile
        FOREIGN KEY(product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purchased_input_records_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_purchased_input_records_updated_by_user_id_users
        FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_purchased_input_records_organization_id "
        "ON cbam_purchased_input_records (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_purchased_input_records_org_binding "
        "ON cbam_purchased_input_records (organization_id, reporting_period_binding_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_purchased_input_records_org_installation "
        "ON cbam_purchased_input_records (organization_id, installation_profile_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_purchased_input_records_status "
        "ON cbam_purchased_input_records (status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cbam_purchased_input_records")
    op.execute("DROP TABLE IF EXISTS cbam_activity_properties")
    op.execute("DROP TABLE IF EXISTS cbam_activity_records")
    op.execute("DROP TABLE IF EXISTS cbam_production_records")
