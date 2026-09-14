"""CBAM Phase 2 foundation aggregates (installations, period bindings, product profiles)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008_cbam_foundation"
down_revision: str | None = "0007_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_installation_profiles (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    facility_id UUID NOT NULL,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    timezone VARCHAR(64) NOT NULL,
    operator_identity_ref VARCHAR(255),
    metadata_json JSONB,
    row_version INTEGER DEFAULT 1 NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_installation_profiles PRIMARY KEY (id),
    CONSTRAINT uq_cbam_installation_org_code UNIQUE (organization_id, code),
    CONSTRAINT ck_cbam_installation_profiles_installation_status
        CHECK (status IN ('draft', 'active', 'archived')),
    CONSTRAINT ck_cbam_installation_profiles_installation_row_version_positive
        CHECK (row_version >= 1),
    CONSTRAINT fk_cbam_installation_profiles_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_installation_profiles_facility_id_facilities
        FOREIGN KEY(facility_id) REFERENCES facilities (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_installation_profiles_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_installation_profiles_updated_by_user_id_users
        FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_installation_profiles_organization_id "
        "ON cbam_installation_profiles (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_installation_profiles_facility_id "
        "ON cbam_installation_profiles (facility_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_installation_profiles_status ON cbam_installation_profiles (status)"
    )
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_installation_one_active_per_facility
ON cbam_installation_profiles (organization_id, facility_id)
WHERE status = 'active'
"""
    )

    op.execute(
        """
CREATE TABLE cbam_reporting_period_bindings (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_id UUID NOT NULL,
    status VARCHAR(32) NOT NULL,
    locked_at TIMESTAMP WITH TIME ZONE,
    locked_by_user_id UUID,
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_calculation_run_id UUID,
    revision_number INTEGER DEFAULT 0 NOT NULL,
    notes TEXT,
    row_version INTEGER DEFAULT 1 NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_reporting_period_bindings PRIMARY KEY (id),
    CONSTRAINT uq_cbam_period_binding_org_period
        UNIQUE (organization_id, reporting_period_id),
    CONSTRAINT ck_cbam_reporting_period_bindings_period_binding_row_version_positive
        CHECK (row_version >= 1),
    CONSTRAINT ck_cbam_reporting_period_bindings_period_binding_revision_non_negative
        CHECK (revision_number >= 0),
    CONSTRAINT fk_cbam_reporting_period_bindings_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_reporting_period_bindings_reporting_period_id_reporting_periods
        FOREIGN KEY(reporting_period_id) REFERENCES reporting_periods (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_reporting_period_bindings_locked_by_user_id_users
        FOREIGN KEY(locked_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_reporting_period_bindings_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_reporting_period_bindings_updated_by_user_id_users
        FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_reporting_period_bindings_organization_id "
        "ON cbam_reporting_period_bindings (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_reporting_period_bindings_reporting_period_id "
        "ON cbam_reporting_period_bindings (reporting_period_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_reporting_period_bindings_status "
        "ON cbam_reporting_period_bindings (status)"
    )

    op.execute(
        """
CREATE TABLE cbam_product_profile_versions (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    product_id UUID NOT NULL,
    version INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL,
    valid_from DATE,
    valid_to DATE,
    classification_ready BOOLEAN DEFAULT false NOT NULL,
    row_version INTEGER DEFAULT 1 NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_cbam_product_profile_versions PRIMARY KEY (id),
    CONSTRAINT uq_cbam_product_profile_org_product_version
        UNIQUE (organization_id, product_id, version),
    CONSTRAINT ck_cbam_product_profile_versions_product_profile_status
        CHECK (status IN ('draft', 'active', 'superseded', 'archived')),
    CONSTRAINT ck_cbam_product_profile_versions_product_profile_version_positive
        CHECK (version >= 1),
    CONSTRAINT ck_cbam_product_profile_versions_product_profile_row_version_positive
        CHECK (row_version >= 1),
    CONSTRAINT ck_cbam_product_profile_versions_product_profile_valid_dates
        CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from),
    CONSTRAINT fk_cbam_product_profile_versions_organization_id_organizations
        FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_product_profile_versions_product_id_products
        FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_product_profile_versions_created_by_user_id_users
        FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_product_profile_versions_updated_by_user_id_users
        FOREIGN KEY(updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)
"""
    )
    op.execute(
        "CREATE INDEX ix_cbam_product_profile_versions_organization_id "
        "ON cbam_product_profile_versions (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_product_profile_versions_product_id "
        "ON cbam_product_profile_versions (product_id)"
    )
    op.execute(
        "CREATE INDEX ix_cbam_product_profile_versions_status "
        "ON cbam_product_profile_versions (status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cbam_product_profile_versions")
    op.execute("DROP TABLE IF EXISTS cbam_reporting_period_bindings")
    op.execute("DROP TABLE IF EXISTS cbam_installation_profiles")
