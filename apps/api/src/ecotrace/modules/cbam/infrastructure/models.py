from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

INSTALLATION_STATUSES = ("draft", "active", "archived")
PERIOD_BINDING_STATUSES = (
    "draft",
    "data_collection",
    "data_ready",
    "expert_review",
    "rework",
    "approval_pending",
    "approved",
    "locked",
    "revised",
    "archived",
)
PRODUCT_PROFILE_STATUSES = ("draft", "active", "superseded", "archived")


class CbamInstallationProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_installation_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_cbam_installation_org_code"),
        Index("ix_cbam_installation_profiles_organization_id", "organization_id"),
        Index("ix_cbam_installation_profiles_facility_id", "facility_id"),
        Index("ix_cbam_installation_profiles_status", "status"),
        Index(
            "uq_cbam_installation_one_active_per_facility",
            "organization_id",
            "facility_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="installation_status",
        ),
        CheckConstraint("row_version >= 1", name="installation_row_version_positive"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    operator_identity_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamReportingPeriodBinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_reporting_period_bindings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "reporting_period_id",
            name="uq_cbam_period_binding_org_period",
        ),
        Index("ix_cbam_reporting_period_bindings_organization_id", "organization_id"),
        Index("ix_cbam_reporting_period_bindings_reporting_period_id", "reporting_period_id"),
        Index("ix_cbam_reporting_period_bindings_status", "status"),
        CheckConstraint("row_version >= 1", name="period_binding_row_version_positive"),
        CheckConstraint("revision_number >= 0", name="period_binding_revision_non_negative"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reporting_periods.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_calculation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    revision_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamCnCodeDataset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_cn_code_datasets"
    __table_args__ = (
        UniqueConstraint("dataset_code", "dataset_version", name="uq_cbam_cn_dataset_code_version"),
        Index("ix_cbam_cn_code_datasets_status", "status"),
        CheckConstraint(
            "status IN ('ACTIVE', 'SUPERSEDED', 'ARCHIVED')",
            name="cbam_cn_dataset_status",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="cbam_cn_dataset_valid_dates",
        ),
    )

    dataset_code: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    source_workbook_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_workbook_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class CbamCnCode(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_cn_codes"
    __table_args__ = (
        UniqueConstraint("dataset_id", "cn_key", name="uq_cbam_cn_codes_dataset_cn_key"),
        UniqueConstraint(
            "dataset_id", "normalized_code", name="uq_cbam_cn_codes_dataset_normalized"
        ),
        Index("ix_cbam_cn_codes_dataset_id", "dataset_id"),
        Index("ix_cbam_cn_codes_normalized_code", "normalized_code"),
        Index("ix_cbam_cn_codes_cbam_sector", "cbam_sector"),
        Index("ix_cbam_cn_codes_status", "status"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="cbam_cn_codes_status",
        ),
        CheckConstraint("source_row >= 1", name="cbam_cn_codes_source_row_positive"),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_cn_code_datasets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cn_key: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_code: Mapped[str] = mapped_column(String(32), nullable=False)
    display_code: Mapped[str] = mapped_column(String(64), nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    cbam_sector: Mapped[str] = mapped_column(String(128), nullable=False)
    numbering_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    # Workbook-derived per-CN product-field applicability (Phase 6A+).
    # Always a full camelCase key → bool map; never inferred from sector name in the API.
    field_applicability: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class CbamCnControlledListValue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_cn_controlled_list_values"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "list_code",
            "value_code",
            name="uq_cbam_cn_list_dataset_code_value",
        ),
        Index("ix_cbam_cn_list_dataset_id", "dataset_id"),
        Index("ix_cbam_cn_list_list_code", "list_code"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="cbam_cn_list_status",
        ),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_cn_code_datasets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    list_code: Mapped[str] = mapped_column(String(64), nullable=False)
    value_code: Mapped[str] = mapped_column(String(128), nullable=False)
    value_label: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class CbamProductProfileVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_product_profile_versions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "product_id",
            "version",
            name="uq_cbam_product_profile_org_product_version",
        ),
        Index("ix_cbam_product_profile_versions_organization_id", "organization_id"),
        Index("ix_cbam_product_profile_versions_product_id", "product_id"),
        Index("ix_cbam_product_profile_versions_status", "status"),
        Index("ix_cbam_product_profile_cn_code_id", "cn_code_id"),
        CheckConstraint(
            "status IN ('draft', 'active', 'superseded', 'archived')",
            name="product_profile_status",
        ),
        CheckConstraint("version >= 1", name="product_profile_version_positive"),
        CheckConstraint("row_version >= 1", name="product_profile_row_version_positive"),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="product_profile_valid_dates",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    classification_ready: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cn_code_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_cn_codes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cn_normalized_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cn_display_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cn_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cn_sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cn_dataset_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cn_dataset_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reducing_agent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    steel_mill_identification_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    percent_mn: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    percent_cr: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    percent_ni: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    percent_other_alloys: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    percent_other_materials: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    missing_requirements: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    validation_issues: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamProductionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_production_records"
    __table_args__ = (
        Index("ix_cbam_production_records_organization_id", "organization_id"),
        Index(
            "ix_cbam_production_records_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index(
            "ix_cbam_production_records_org_installation",
            "organization_id",
            "installation_profile_id",
        ),
        Index("ix_cbam_production_records_status", "status"),
        Index(
            "ix_cbam_production_records_product_profile_version_id",
            "product_profile_version_id",
        ),
        Index(
            "ix_cbam_production_records_org_binding_profile",
            "organization_id",
            "reporting_period_binding_id",
            "product_profile_version_id",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="production_record_status"),
        CheckConstraint("quantity > 0", name="production_quantity_positive"),
        CheckConstraint("row_version >= 1", name="production_row_version_positive"),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="production_period_dates",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_installation_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_profile_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    production_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamActivityRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_activity_records"
    __table_args__ = (
        Index("ix_cbam_activity_records_organization_id", "organization_id"),
        Index(
            "ix_cbam_activity_records_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index(
            "ix_cbam_activity_records_org_installation",
            "organization_id",
            "installation_profile_id",
        ),
        Index(
            "ix_cbam_activity_records_binding_type",
            "reporting_period_binding_id",
            "activity_type",
        ),
        Index("ix_cbam_activity_records_status", "status"),
        CheckConstraint("status IN ('active', 'archived')", name="activity_record_status"),
        CheckConstraint("quantity > 0", name="activity_quantity_positive"),
        CheckConstraint("row_version >= 1", name="activity_row_version_positive"),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="activity_period_dates",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_installation_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_group: Mapped[str] = mapped_column(String(32), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    data_source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    measurement_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certificate_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    process_type_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    process_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    biogenic_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamActivityProperty(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_activity_properties"
    __table_args__ = (
        UniqueConstraint(
            "activity_record_id",
            "property_code",
            name="uq_cbam_activity_property_record_code",
        ),
        Index("ix_cbam_activity_properties_organization_id", "organization_id"),
        Index("ix_cbam_activity_properties_activity_record_id", "activity_record_id"),
        CheckConstraint("numeric_value > 0", name="activity_property_value_positive"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_activity_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    property_code: Mapped[str] = mapped_column(String(64), nullable=False)
    numeric_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PRIMARY")
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamPurchasedInputRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_purchased_input_records"
    __table_args__ = (
        Index("ix_cbam_purchased_input_records_organization_id", "organization_id"),
        Index(
            "ix_cbam_purchased_input_records_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index(
            "ix_cbam_purchased_input_records_org_installation",
            "organization_id",
            "installation_profile_id",
        ),
        Index("ix_cbam_purchased_input_records_status", "status"),
        CheckConstraint("status IN ('active', 'archived')", name="purchased_input_status"),
        CheckConstraint("quantity > 0", name="purchased_quantity_positive"),
        CheckConstraint(
            "consumed_quantity IS NULL OR consumed_quantity >= 0",
            name="consumed_quantity_non_negative",
        ),
        CheckConstraint("row_version >= 1", name="purchased_row_version_positive"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_installation_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_profile_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    input_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    consumed_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    consumed_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    embedded_emission_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    embedded_emission_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    embedded_emission_source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NOT_PROVIDED"
    )
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamAllocationRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_allocation_rules"
    __table_args__ = (
        Index("ix_cbam_allocation_rules_organization_id", "organization_id"),
        Index(
            "ix_cbam_allocation_rules_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index(
            "ix_cbam_allocation_rules_org_installation",
            "organization_id",
            "installation_profile_id",
        ),
        Index(
            "ix_cbam_allocation_rules_org_product",
            "organization_id",
            "product_profile_version_id",
        ),
        Index("ix_cbam_allocation_rules_status", "status"),
        Index(
            "uq_cbam_allocation_one_active_per_scope",
            "organization_id",
            "reporting_period_binding_id",
            "installation_profile_id",
            text("COALESCE(product_profile_version_id, '00000000-0000-0000-0000-000000000000')"),
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')",
            name="allocation_rule_status",
        ),
        CheckConstraint(
            "allocation_method IN ('DIRECT_ASSIGNMENT', 'PRODUCTION_QUANTITY_RATIO', 'MANUAL_RATIO')",
            name="allocation_method",
        ),
        CheckConstraint(
            "allocation_ratio IS NULL OR (allocation_ratio >= 0 AND allocation_ratio <= 1)",
            name="allocation_ratio_bounds",
        ),
        CheckConstraint("row_version >= 1", name="allocation_rule_row_version_positive"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_installation_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_profile_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    allocation_method: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    allocation_ratio: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    numerator_production_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_production_records.id", ondelete="RESTRICT"),
        nullable=True,
    )
    denominator_production_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_production_records.id", ondelete="RESTRICT"),
        nullable=True,
    )
    numerator_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    denominator_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamAllocationResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_allocation_results"
    __table_args__ = (
        Index("ix_cbam_allocation_results_organization_id", "organization_id"),
        Index(
            "ix_cbam_allocation_results_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_allocation_results_rule_id", "allocation_rule_id"),
        Index(
            "ix_cbam_allocation_results_source",
            "source_type",
            "source_id",
        ),
        Index(
            "ix_cbam_allocation_results_current_lookup",
            "organization_id",
            "allocation_rule_id",
            "source_type",
            "source_id",
            "is_current",
        ),
        CheckConstraint(
            "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD')",
            name="allocation_source_type",
        ),
        CheckConstraint(
            "allocation_ratio >= 0 AND allocation_ratio <= 1",
            name="allocation_result_ratio_bounds",
        ),
        CheckConstraint("source_quantity > 0", name="allocation_source_quantity_positive"),
        CheckConstraint("allocated_quantity >= 0", name="allocation_allocated_non_negative"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    allocation_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_allocation_rules.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    source_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    allocation_ratio: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    allocated_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    allocated_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    allocation_method: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamReferenceSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_reference_sources"
    __table_args__ = (
        Index("ix_cbam_reference_sources_organization_id", "organization_id"),
        Index("ix_cbam_reference_sources_status", "status"),
        Index(
            "uq_cbam_reference_source_org_code",
            text("COALESCE(organization_id, '00000000-0000-0000-0000-000000000000')"),
            "code",
            unique=True,
        ),
        CheckConstraint(
            "source_type IN ('STANDARD_REFERENCE', 'PRIMARY_MEASUREMENT', "
            "'SUPPLIER_DECLARATION', 'MANUAL_APPROVED', 'OTHER')",
            name="reference_source_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="reference_source_status",
        ),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamFactorDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_factor_definitions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_cbam_factor_definition_code"),
        Index("ix_cbam_factor_definitions_status", "status"),
        Index("ix_cbam_factor_definitions_category", "factor_category"),
        CheckConstraint(
            "factor_category IN ('ACTIVITY_PROPERTY', 'EMISSION_FACTOR', "
            "'EMBEDDED_EMISSION_FACTOR', 'ENERGY_FACTOR', 'OTHER')",
            name="factor_definition_category",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="factor_definition_status",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    factor_category: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    property_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_unit_family: Mapped[str | None] = mapped_column(String(32), nullable=True)
    output_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class CbamFactorValue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_factor_values"
    __table_args__ = (
        Index("ix_cbam_factor_values_organization_id", "organization_id"),
        Index("ix_cbam_factor_values_definition_status", "factor_definition_id", "status"),
        Index("ix_cbam_factor_values_activity_type_status", "activity_type", "status"),
        Index(
            "ix_cbam_factor_values_org_definition",
            "organization_id",
            "factor_definition_id",
        ),
        Index("ix_cbam_factor_values_validity", "valid_from", "valid_until"),
        CheckConstraint(
            "data_source_type IN ('PRIMARY', 'DEFAULT_REFERENCE')",
            name="factor_value_data_source_type",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')",
            name="factor_value_status",
        ),
        CheckConstraint("numeric_value > 0", name="factor_value_positive"),
        CheckConstraint("row_version >= 1", name="factor_value_row_version_positive"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    factor_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_factor_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reference_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reference_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    numeric_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    geography_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    facility_specific: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamFactorResolution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_factor_resolutions"
    __table_args__ = (
        Index("ix_cbam_factor_resolutions_organization_id", "organization_id"),
        Index(
            "ix_cbam_factor_resolutions_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index(
            "ix_cbam_factor_resolutions_source",
            "source_type",
            "source_id",
        ),
        Index(
            "ix_cbam_factor_resolutions_binding_status",
            "reporting_period_binding_id",
            "resolution_status",
        ),
        CheckConstraint(
            "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD', 'ALLOCATION_RESULT')",
            name="factor_resolution_source_type",
        ),
        CheckConstraint(
            "resolution_status IN ("
            "'RESOLVED_PRIMARY', 'RESOLVED_DEFAULT', 'UNRESOLVED', 'AMBIGUOUS', "
            "'INCOMPATIBLE_UNIT', 'OUTSIDE_VALIDITY', 'BLOCKED'"
            ")",
            name="factor_resolution_status",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    factor_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_factor_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resolution_status: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_activity_property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_activity_properties.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_factor_value_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_factor_values.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    selected_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_precedence: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolver_version: Mapped[str] = mapped_column(String(64), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CbamCalculationDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_calculation_definitions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_cbam_calculation_definition_code"),
        Index("ix_cbam_calculation_definitions_status", "status"),
        Index("ix_cbam_calculation_definitions_factor", "factor_definition_id"),
        CheckConstraint(
            "calculation_type IN ("
            "'MULTIPLY_ACTIVITY_BY_FACTOR', 'STATIONARY_COMBUSTION_CO2_V1', "
            "'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1'"
            ")",
            name="calc_def_type",
        ),
        CheckConstraint(
            "("
            "calculation_type = 'MULTIPLY_ACTIVITY_BY_FACTOR' "
            "AND factor_definition_id IS NOT NULL"
            ") OR ("
            "calculation_type = 'STATIONARY_COMBUSTION_CO2_V1' "
            "AND factor_definition_id IS NULL"
            ") OR ("
            "calculation_type = 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1' "
            "AND factor_definition_id IS NULL"
            ")",
            name="calc_def_factor_req",
        ),
        CheckConstraint(
            "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD', 'ALLOCATION_RESULT')",
            name="calculation_definition_source_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="calculation_definition_status",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    calculation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    factor_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_factor_definitions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    output_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class CbamCalculationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_calculation_runs"
    __table_args__ = (
        Index("ix_cbam_calculation_runs_organization_id", "organization_id"),
        Index(
            "ix_cbam_calculation_runs_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_calculation_runs_status", "status"),
        CheckConstraint(
            "status IN ("
            "'DRAFT', 'RUNNING', 'COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED', 'ARCHIVED'"
            ")",
            name="calculation_run_status",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    primary_factor_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_factor_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamCalculationResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_calculation_results"
    __table_args__ = (
        Index("ix_cbam_calculation_results_organization_id", "organization_id"),
        Index("ix_cbam_calculation_results_run_status", "calculation_run_id", "status"),
        Index("ix_cbam_calculation_results_source", "source_type", "source_id"),
        Index("ix_cbam_calculation_results_factor_resolution", "factor_resolution_id"),
        Index("ix_cbam_calculation_results_allocation", "allocation_result_id"),
        Index(
            "ix_cbam_calculation_results_input_key_current",
            "organization_id",
            "input_fingerprint",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        CheckConstraint(
            "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD', 'ALLOCATION_RESULT')",
            name="calculation_result_source_type",
        ),
        CheckConstraint(
            "status IN ("
            "'CALCULATED', 'BLOCKED', 'INVALID_INPUT', 'INCOMPATIBLE_UNIT', "
            "'UNRESOLVED_FACTOR', 'AMBIGUOUS_FACTOR', 'UNSUPPORTED_FORMULA'"
            ")",
            name="calculation_result_status",
        ),
        CheckConstraint(
            "calculation_type IN ('MULTIPLY_ACTIVITY_BY_FACTOR')",
            name="calculation_result_type",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_calculation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    calculation_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_calculation_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    allocation_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_allocation_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    factor_resolution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_factor_resolutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    source_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    factor_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    factor_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    result_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    calculation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    factor_resolution_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamExportTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_export_templates"
    __table_args__ = (
        Index("ix_cbam_export_templates_organization_id", "organization_id"),
        Index("ix_cbam_export_templates_status", "status"),
        Index(
            "uq_cbam_export_template_org_code_version",
            text("COALESCE(organization_id, '00000000-0000-0000-0000-000000000000')"),
            "code",
            "version",
            unique=True,
        ),
        CheckConstraint(
            "template_type IN ('INTERNAL_SKDM', 'OFFICIAL_CBAM_TEMPLATE', 'CUSTOMER_TEMPLATE')",
            name="export_template_type",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')",
            name="export_template_status",
        ),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamExportMapping(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_export_mappings"
    __table_args__ = (
        UniqueConstraint(
            "export_template_id",
            "mapping_code",
            name="uq_cbam_export_mapping_template_code",
        ),
        Index("ix_cbam_export_mappings_template_id", "export_template_id"),
        CheckConstraint(
            "source_type IN ("
            "'ORGANIZATION', 'INSTALLATION', 'REPORTING_PERIOD', 'PRODUCT', "
            "'PRODUCTION_RECORD', 'ACTIVITY_RECORD', 'PURCHASED_INPUT', "
            "'ALLOCATION_RESULT', 'FACTOR_RESOLUTION', 'CALCULATION_RESULT', "
            "'CALCULATED_SUMMARY', 'CONSTANT'"
            ")",
            name="export_mapping_source_type",
        ),
        CheckConstraint(
            "destination_type IN ('CELL', 'NAMED_RANGE', 'TABLE_COLUMN', 'REPEATING_ROW')",
            name="export_mapping_destination_type",
        ),
        CheckConstraint(
            "value_type IN ('STRING', 'NUMBER', 'DATE', 'DATETIME', 'BOOLEAN', 'ENUM', 'UNIT')",
            name="export_mapping_value_type",
        ),
        CheckConstraint(
            "transformation_code IN ("
            "'NONE', 'DECIMAL_TO_NUMBER', 'DATE_TO_EXCEL_DATE', "
            "'DATETIME_TO_EXCEL_DATETIME', 'ENUM_TO_DISPLAY_LABEL', "
            "'UNIT_DISPLAY', 'BOOLEAN_TO_YES_NO'"
            ") OR transformation_code IS NULL",
            name="export_mapping_transformation",
        ),
    )

    export_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_export_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    mapping_code: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_path: Mapped[str] = mapped_column(String(255), nullable=False)
    worksheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    destination_type: Mapped[str] = mapped_column(String(64), nullable=False)
    destination_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transformation_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CbamExportRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_export_runs"
    __table_args__ = (
        Index("ix_cbam_export_runs_organization_id", "organization_id"),
        Index(
            "ix_cbam_export_runs_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_export_runs_status", "status"),
        CheckConstraint(
            "status IN ("
            "'PENDING', 'RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', "
            "'FAILED', 'CANCELLED'"
            ")",
            name="export_run_status",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    export_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_export_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    calculation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_calculation_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="PENDING")
    template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    template_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    input_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamExportArtifact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_export_artifacts"
    __table_args__ = (
        Index("ix_cbam_export_artifacts_organization_id", "organization_id"),
        Index("ix_cbam_export_artifacts_export_run_id", "export_run_id"),
        CheckConstraint(
            "artifact_type IN ('XLSX', 'CSV_SUMMARY', 'JSON_SUMMARY', 'HTML_REPORT')",
            name="export_artifact_type",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    export_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_export_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class CbamStationaryCombustionFuel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_stationary_combustion_fuels"
    __table_args__ = (
        UniqueConstraint("code", name="uq_cbam_stationary_combustion_fuel_code"),
        Index("ix_cbam_stationary_combustion_fuels_status", "status"),
        CheckConstraint(
            "input_basis IN ('VOLUME', 'MASS')",
            name="sc_fuel_input_basis",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="sc_fuel_status",
        ),
        CheckConstraint(
            "default_activity_unit IN ('Sm3', 'm3', 'kg', 't', 'Gg')",
            name="sc_fuel_default_unit",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_basis: Mapped[str] = mapped_column(String(16), nullable=False)
    default_activity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class CbamStationaryCombustionParameterSet(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_stationary_combustion_parameter_sets"
    __table_args__ = (
        UniqueConstraint(
            "fuel_id",
            "dataset_code",
            "dataset_version",
            name="uq_cbam_sc_param_fuel_dataset_version",
        ),
        Index("ix_cbam_sc_param_sets_fuel_id", "fuel_id"),
        Index("ix_cbam_sc_param_sets_status", "status"),
        Index("ix_cbam_sc_param_sets_validity", "valid_from", "valid_until"),
        Index(
            "ix_cbam_sc_param_sets_fuel_status_validity",
            "fuel_id",
            "status",
            "valid_from",
            "valid_until",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')",
            name="sc_param_status",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="sc_param_validity_order",
        ),
        CheckConstraint(
            "net_calorific_value > 0",
            name="sc_param_ncv_positive",
        ),
        CheckConstraint(
            "net_calorific_value_unit IN ('TJ/Gg')",
            name="sc_param_ncv_unit",
        ),
        CheckConstraint(
            "fossil_co2_emission_factor > 0",
            name="sc_param_co2_positive",
        ),
        CheckConstraint(
            "fossil_co2_emission_factor_unit IN ('kgCO2/TJ')",
            name="sc_param_co2_unit",
        ),
        CheckConstraint(
            "oxidation_factor >= 0",
            name="sc_param_oxidation_non_neg",
        ),
        CheckConstraint(
            "("
            "reference_density IS NULL AND reference_density_unit IS NULL"
            ") OR ("
            "reference_density IS NOT NULL AND reference_density_unit IS NOT NULL "
            "AND reference_density > 0 AND reference_density_unit IN ('kg/Sm3', 'kg/m3')"
            ")",
            name="sc_param_density_pair",
        ),
    )

    fuel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_stationary_combustion_fuels.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dataset_code: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")

    net_calorific_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    net_calorific_value_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    fossil_co2_emission_factor: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    fossil_co2_emission_factor_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    oxidation_factor: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    reference_density: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    reference_density_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    ncv_reference_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reference_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ncv_source_document: Mapped[str] = mapped_column(Text, nullable=False)
    ncv_source_table: Mapped[str] = mapped_column(String(255), nullable=False)

    co2_reference_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reference_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    co2_source_document: Mapped[str] = mapped_column(Text, nullable=False)
    co2_source_table: Mapped[str] = mapped_column(String(255), nullable=False)

    oxidation_reference_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reference_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    oxidation_source_document: Mapped[str] = mapped_column(Text, nullable=False)
    oxidation_source_table: Mapped[str] = mapped_column(String(255), nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CbamStationaryCombustionResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_stationary_combustion_results"
    __table_args__ = (
        UniqueConstraint(
            "calculation_run_id",
            "activity_record_id",
            name="uq_cbam_sc_result_run_activity",
        ),
        Index("ix_cbam_sc_results_organization_id", "organization_id"),
        Index("ix_cbam_sc_results_run_id", "calculation_run_id"),
        Index("ix_cbam_sc_results_activity_id", "activity_record_id"),
        Index("ix_cbam_sc_results_binding_id", "reporting_period_binding_id"),
        Index("ix_cbam_sc_results_fuel_id", "fuel_id"),
        Index("ix_cbam_sc_results_parameter_set_id", "parameter_set_id"),
        Index("ix_cbam_sc_results_client_request_id", "client_request_id"),
        Index(
            "uq_cbam_sc_result_org_binding_client_request",
            "organization_id",
            "reporting_period_binding_id",
            "client_request_id",
            unique=True,
            postgresql_where=text("client_request_id IS NOT NULL"),
        ),
        Index(
            "uq_cbam_sc_result_id_org_binding_activity",
            "id",
            "organization_id",
            "reporting_period_binding_id",
            "activity_record_id",
            unique=True,
        ),
        CheckConstraint(
            "calculation_type = 'STATIONARY_COMBUSTION_CO2_V1'",
            name="sc_result_type",
        ),
        CheckConstraint(
            "input_basis IN ('VOLUME', 'MASS')",
            name="sc_result_input_basis",
        ),
        CheckConstraint("activity_quantity > 0", name="sc_result_activity_qty_pos"),
        CheckConstraint("net_calorific_value > 0", name="sc_result_ncv_pos"),
        CheckConstraint("fossil_co2_emission_factor > 0", name="sc_result_co2_pos"),
        CheckConstraint("oxidation_factor >= 0", name="sc_result_ox_nonneg"),
        CheckConstraint(
            "("
            "density_value IS NULL AND density_unit IS NULL"
            ") OR ("
            "density_value IS NOT NULL AND density_unit IS NOT NULL "
            "AND density_value > 0 AND density_unit IN ('kg/Sm3', 'kg/m3')"
            ")",
            name="sc_result_density_pair",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="sc_result_validity",
        ),
        CheckConstraint("result_unit = 'tCO2'", name="sc_result_unit"),
        CheckConstraint(
            "fuel_mass_kg >= 0 AND fuel_mass_gg >= 0",
            name="sc_result_mass_nonneg",
        ),
        CheckConstraint("energy_content_tj >= 0", name="sc_result_energy_nonneg"),
        CheckConstraint(
            "fossil_co2_kg >= 0 AND fossil_co2_tonnes >= 0 AND result_value >= 0",
            name="sc_result_co2_nonneg",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_calculation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    calculation_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_calculation_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_activity_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fuel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_stationary_combustion_fuels.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parameter_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_stationary_combustion_parameter_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    calculation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fuel_code: Mapped[str] = mapped_column(String(64), nullable=False)
    fuel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_basis: Mapped[str] = mapped_column(String(16), nullable=False)
    activity_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    activity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    density_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    density_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    client_request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    calculation_reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    net_calorific_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    net_calorific_value_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    fossil_co2_emission_factor: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    fossil_co2_emission_factor_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    oxidation_factor: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    dataset_code: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    ncv_reference_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reference_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ncv_source_document: Mapped[str] = mapped_column(Text, nullable=False)
    ncv_source_table: Mapped[str] = mapped_column(String(255), nullable=False)
    co2_reference_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reference_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    co2_source_document: Mapped[str] = mapped_column(Text, nullable=False)
    co2_source_table: Mapped[str] = mapped_column(String(255), nullable=False)
    oxidation_reference_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reference_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    oxidation_source_document: Mapped[str] = mapped_column(Text, nullable=False)
    oxidation_source_table: Mapped[str] = mapped_column(String(255), nullable=False)
    fuel_mass_kg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    fuel_mass_gg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    energy_content_tj: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    fossil_co2_kg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    fossil_co2_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    result_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    result_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamStationaryCombustionCurrentResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Authoritative current-result pointer per activity (Phase 5A). Snapshots stay immutable."""

    __tablename__ = "cbam_stationary_combustion_current_results"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "reporting_period_binding_id",
            "activity_record_id",
            name="uq_cbam_sc_current_org_binding_activity",
        ),
        Index("ix_cbam_sc_current_organization_id", "organization_id"),
        Index("ix_cbam_sc_current_binding_id", "reporting_period_binding_id"),
        Index("ix_cbam_sc_current_result_id", "current_result_id"),
        ForeignKeyConstraint(
            [
                "current_result_id",
                "organization_id",
                "reporting_period_binding_id",
                "activity_record_id",
            ],
            [
                "cbam_stationary_combustion_results.id",
                "cbam_stationary_combustion_results.organization_id",
                "cbam_stationary_combustion_results.reporting_period_binding_id",
                "cbam_stationary_combustion_results.activity_record_id",
            ],
            name="fk_cbam_sc_current_result_identity",
            ondelete="RESTRICT",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_activity_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    current_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_stationary_combustion_results.id", ondelete="RESTRICT"),
        nullable=False,
    )


class CbamMonthlyProductionBasis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Workbook D/E monthly production-basis inputs (Phase 7A-0). Allocation not computed here."""

    __tablename__ = "cbam_monthly_production_basis"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "reporting_period_binding_id",
            "month_start",
            name="uq_cbam_monthly_prod_basis_org_binding_month",
        ),
        Index("ix_cbam_monthly_prod_basis_organization_id", "organization_id"),
        Index(
            "ix_cbam_monthly_prod_basis_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index(
            "ix_cbam_monthly_prod_basis_binding_month",
            "reporting_period_binding_id",
            "month_start",
        ),
        CheckConstraint(
            "EXTRACT(DAY FROM month_start) = 1",
            name="ck_cbam_monthly_prod_basis_month_canonical",
        ),
        CheckConstraint(
            "total_production_quantity IS NULL OR total_production_quantity >= 0",
            name="ck_cbam_monthly_prod_basis_total_nonneg",
        ),
        CheckConstraint(
            "cbam_quantity IS NULL OR cbam_quantity >= 0",
            name="ck_cbam_monthly_prod_basis_cbam_nonneg",
        ),
        CheckConstraint("row_version >= 1", name="ck_cbam_monthly_prod_basis_row_version"),
        CheckConstraint(
            "source_type IN ('MANUAL', 'IMPORT', 'SYSTEM')",
            name="ck_cbam_monthly_prod_basis_source_type",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    month_start: Mapped[date] = mapped_column(Date, nullable=False)
    # Workbook D — "Tonaj üretim (Ton)" (total facility production for the month).
    total_production_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    # Workbook E — "SKDM kapsamında ithalatçı firmaya giden miktar (Ton)".
    cbam_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    quantity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamDirectEmissionsAllocationResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable completed direct-emissions allocation result (Phase 7A-2)."""

    __tablename__ = "cbam_direct_emissions_allocation_results"
    __table_args__ = (
        Index(
            "ix_cbam_dea_results_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_dea_results_created_at", "created_at"),
        Index(
            "uq_cbam_dea_result_org_binding_client_request",
            "organization_id",
            "reporting_period_binding_id",
            "client_request_id",
            unique=True,
        ),
        Index(
            "uq_cbam_dea_result_id_org_binding",
            "id",
            "organization_id",
            "reporting_period_binding_id",
            unique=True,
        ),
        CheckConstraint("status = 'COMPLETED'", name="ck_cbam_dea_results_status"),
        CheckConstraint(
            "balance_status IN ('BALANCED', 'UNBALANCED')",
            name="ck_cbam_dea_results_balance",
        ),
        CheckConstraint("result_unit = 'tCO2'", name="ck_cbam_dea_results_unit"),
        CheckConstraint(
            "balance_status <> 'BALANCED' OR remaining_fossil_co2_tonnes = 0",
            name="ck_cbam_dea_results_balanced_zero_remaining",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    methodology_code: Mapped[str] = mapped_column(String(128), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(32), nullable=False)
    workbook_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    workbook_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    workbook_formula_refs: Mapped[str] = mapped_column(Text, nullable=False)
    client_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    balance_status: Mapped[str] = mapped_column(String(32), nullable=False)
    facility_fossil_co2_tonnes_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    cbam_fossil_co2_tonnes_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    non_cbam_fossil_co2_tonnes_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    facility_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    cbam_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    non_cbam_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    allocated_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    remaining_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    result_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    workbook_reporting_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    workbook_gas: Mapped[str] = mapped_column(String(16), nullable=False)
    workbook_gwp: Mapped[str] = mapped_column(String(16), nullable=False)
    workbook_gwp_factor: Mapped[str] = mapped_column(String(16), nullable=False)
    source_result_count: Mapped[int] = mapped_column(Integer, nullable=False)
    month_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fuel_count: Mapped[int] = mapped_column(Integer, nullable=False)
    participating_production_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    product_profile_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    totals_by_month_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    totals_by_fuel_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamDeaMonthlyBasisSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_dea_monthly_basis_snapshots"
    __table_args__ = (
        UniqueConstraint("result_id", "month_start", name="uq_cbam_dea_mb_result_month"),
        Index("ix_cbam_dea_mb_basis_record", "basis_record_id"),
        Index("ix_cbam_dea_mb_result", "result_id"),
        CheckConstraint(
            "EXTRACT(DAY FROM month_start) = 1",
            name="ck_cbam_dea_mb_month_canonical",
        ),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_direct_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    basis_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_monthly_production_basis.id", ondelete="RESTRICT"),
        nullable=False,
    )
    basis_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    month_start: Mapped[date] = mapped_column(Date, nullable=False)
    total_production_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    cbam_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_total_production_tonnes: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    normalized_cbam_quantity_tonnes: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    monthly_share_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)


class CbamDeaSourceSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_dea_source_snapshots"
    __table_args__ = (
        UniqueConstraint("result_id", "source_result_id", name="uq_cbam_dea_src_result_source"),
        Index("ix_cbam_dea_src_result", "result_id"),
        Index("ix_cbam_dea_src_source_result", "source_result_id"),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_direct_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    source_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_stationary_combustion_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    activity_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    month_start: Mapped[date] = mapped_column(Date, nullable=False)
    fuel_code: Mapped[str] = mapped_column(String(64), nullable=False)
    fuel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_code: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    activity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    facility_fuel_mass_kg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    facility_fuel_mass_gg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    facility_energy_content_tj: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    facility_fossil_co2_kg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    facility_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    facility_result_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    monthly_share_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    cbam_fuel_mass_kg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    cbam_fuel_mass_gg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    cbam_energy_content_tj: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    cbam_fossil_co2_kg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    cbam_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    non_cbam_fuel_mass_kg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    non_cbam_fuel_mass_gg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    non_cbam_energy_content_tj: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    non_cbam_fossil_co2_kg: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    non_cbam_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)


class CbamDeaProductAllocation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_dea_product_allocations"
    __table_args__ = (
        UniqueConstraint(
            "result_id",
            "product_profile_version_id",
            name="uq_cbam_dea_prod_result_profile",
        ),
        Index("ix_cbam_dea_prod_result", "result_id"),
        Index("ix_cbam_dea_prod_profile", "product_profile_version_id"),
        CheckConstraint("result_unit = 'tCO2'", name="ck_cbam_dea_prod_unit"),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_direct_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    cn_normalized_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cn_display_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    production_record_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    production_quantity_snapshots: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    normalized_quantity_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    denominator_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    raw_share: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    raw_allocated_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    final_allocated_fossil_co2_tonnes: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False
    )
    rounding_adjustment: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    result_unit: Mapped[str] = mapped_column(String(32), nullable=False)


class CbamDirectEmissionsAllocationCurrent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_direct_emissions_allocation_current"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "reporting_period_binding_id",
            "methodology_code",
            name="uq_cbam_dea_current_org_binding_method",
        ),
        Index("ix_cbam_dea_current_result", "current_result_id"),
        ForeignKeyConstraint(
            ["current_result_id", "organization_id", "reporting_period_binding_id"],
            [
                "cbam_direct_emissions_allocation_results.id",
                "cbam_direct_emissions_allocation_results.organization_id",
                "cbam_direct_emissions_allocation_results.reporting_period_binding_id",
            ],
            name="fk_cbam_dea_current_result_identity",
            ondelete="RESTRICT",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    methodology_code: Mapped[str] = mapped_column(String(128), nullable=False)
    current_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_direct_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=False,
    )


class CbamPurchasedElectricityResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable purchased-electricity indirect-emissions snapshot (Phase 8A)."""

    __tablename__ = "cbam_purchased_electricity_results"
    __table_args__ = (
        Index("ix_cbam_pe_results_organization_id", "organization_id"),
        Index("ix_cbam_pe_results_binding_id", "reporting_period_binding_id"),
        Index("ix_cbam_pe_results_activity_id", "activity_record_id"),
        Index("ix_cbam_pe_results_run_id", "calculation_run_id"),
        Index("ix_cbam_pe_results_client_request_id", "client_request_id"),
        Index(
            "uq_cbam_pe_result_org_binding_client_request",
            "organization_id",
            "reporting_period_binding_id",
            "client_request_id",
            unique=True,
        ),
        Index(
            "uq_cbam_pe_result_id_org_binding_activity",
            "id",
            "organization_id",
            "reporting_period_binding_id",
            "activity_record_id",
            unique=True,
        ),
        CheckConstraint(
            "methodology_code = 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1'",
            name="pe_result_methodology",
        ),
        CheckConstraint(
            "factor_source_mode IN ('PLATFORM_DEFAULT', 'MANUAL')",
            name="pe_result_factor_mode",
        ),
        CheckConstraint("status = 'COMPLETED'", name="pe_result_status"),
        CheckConstraint("result_unit = 'tCO2e'", name="pe_result_unit"),
        CheckConstraint(
            "activity_unit IN ('kWh', 'MWh')",
            name="pe_result_activity_unit",
        ),
        CheckConstraint("activity_quantity >= 0", name="pe_result_activity_qty_nonneg"),
        CheckConstraint("electricity_mwh >= 0", name="pe_result_mwh_nonneg"),
        CheckConstraint("factor_value >= 0", name="pe_result_factor_nonneg"),
        CheckConstraint(
            "indirect_emissions_tco2e >= 0 AND result_value >= 0",
            name="pe_result_emissions_nonneg",
        ),
        CheckConstraint(
            "("
            "exported_electricity_quantity IS NULL AND exported_electricity_unit IS NULL "
            "AND exported_electricity_mwh IS NULL"
            ") OR ("
            "exported_electricity_quantity IS NOT NULL AND exported_electricity_unit IS NOT NULL "
            "AND exported_electricity_mwh IS NOT NULL "
            "AND exported_electricity_unit IN ('kWh', 'MWh') "
            "AND exported_electricity_quantity >= 0 AND exported_electricity_mwh >= 0"
            ")",
            name="pe_result_exported_pair",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_calculation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    calculation_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_calculation_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_activity_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    methodology_code: Mapped[str] = mapped_column(String(128), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(32), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    workbook_formula_refs: Mapped[str] = mapped_column(Text, nullable=False)
    client_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    calculation_reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    activity_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    activity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    factor_source_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    factor_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    factor_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    factor_tco2e_per_mwh: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    factor_value_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_factor_values.id", ondelete="SET NULL"),
        nullable=True,
    )
    factor_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_factor_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    factor_source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    factor_source_document: Mapped[str] = mapped_column(Text, nullable=False)
    factor_dataset_version: Mapped[str] = mapped_column(String(128), nullable=False)
    factor_reference_description: Mapped[str] = mapped_column(Text, nullable=False)
    factor_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    factor_valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    factor_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    exported_electricity_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    exported_electricity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    exported_electricity_mwh: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    result_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    result_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamPurchasedElectricityCurrentResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Authoritative current purchased-electricity result pointer per activity."""

    __tablename__ = "cbam_purchased_electricity_current_results"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "reporting_period_binding_id",
            "activity_record_id",
            name="uq_cbam_pe_current_org_binding_activity",
        ),
        Index("ix_cbam_pe_current_organization_id", "organization_id"),
        Index("ix_cbam_pe_current_binding_id", "reporting_period_binding_id"),
        Index("ix_cbam_pe_current_result_id", "current_result_id"),
        ForeignKeyConstraint(
            [
                "current_result_id",
                "organization_id",
                "reporting_period_binding_id",
                "activity_record_id",
            ],
            [
                "cbam_purchased_electricity_results.id",
                "cbam_purchased_electricity_results.organization_id",
                "cbam_purchased_electricity_results.reporting_period_binding_id",
                "cbam_purchased_electricity_results.activity_record_id",
            ],
            name="fk_cbam_pe_current_result_identity",
            ondelete="RESTRICT",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_activity_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    methodology_code: Mapped[str] = mapped_column(String(128), nullable=False)
    current_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_purchased_electricity_results.id", ondelete="RESTRICT"),
        nullable=False,
    )


class CbamIndirectEmissionsAllocationResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable completed purchased-electricity indirect-emissions allocation (Phase 8C)."""

    __tablename__ = "cbam_indirect_emissions_allocation_results"
    __table_args__ = (
        Index(
            "ix_cbam_iea_results_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_iea_results_created_at", "created_at"),
        Index(
            "uq_cbam_iea_result_org_binding_client_request",
            "organization_id",
            "reporting_period_binding_id",
            "client_request_id",
            unique=True,
        ),
        Index(
            "uq_cbam_iea_result_id_org_binding",
            "id",
            "organization_id",
            "reporting_period_binding_id",
            unique=True,
        ),
        CheckConstraint("status = 'COMPLETED'", name="ck_cbam_iea_results_status"),
        CheckConstraint(
            "balance_status IN ('BALANCED', 'UNBALANCED')",
            name="ck_cbam_iea_results_balance",
        ),
        CheckConstraint("electricity_unit = 'MWh'", name="ck_cbam_iea_results_elec_unit"),
        CheckConstraint("emissions_unit = 'tCO2e'", name="ck_cbam_iea_results_em_unit"),
        CheckConstraint(
            "balance_status <> 'BALANCED' OR ("
            "remaining_electricity_mwh = 0 AND remaining_indirect_emissions_tco2e = 0"
            ")",
            name="ck_cbam_iea_results_balanced_zero_remaining",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    methodology_code: Mapped[str] = mapped_column(String(128), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(32), nullable=False)
    workbook_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    workbook_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    workbook_formula_refs: Mapped[str] = mapped_column(Text, nullable=False)
    client_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    balance_status: Mapped[str] = mapped_column(String(32), nullable=False)
    facility_electricity_mwh_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    cbam_electricity_mwh_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    non_cbam_electricity_mwh_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    facility_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    cbam_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    non_cbam_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    allocated_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    remaining_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    facility_indirect_emissions_tco2e_raw: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    cbam_indirect_emissions_tco2e_raw: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    non_cbam_indirect_emissions_tco2e_raw: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    facility_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False
    )
    cbam_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    non_cbam_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False
    )
    allocated_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False
    )
    remaining_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False
    )
    exported_electricity_mwh: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    electricity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    emissions_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source_result_count: Mapped[int] = mapped_column(Integer, nullable=False)
    month_count: Mapped[int] = mapped_column(Integer, nullable=False)
    participating_production_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    product_profile_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    totals_by_month_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamIeaMonthlyBasisSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_iea_monthly_basis_snapshots"
    __table_args__ = (
        UniqueConstraint("result_id", "month_start", name="uq_cbam_iea_mb_result_month"),
        Index("ix_cbam_iea_mb_basis_record", "basis_record_id"),
        Index("ix_cbam_iea_mb_result", "result_id"),
        CheckConstraint(
            "EXTRACT(DAY FROM month_start) = 1",
            name="ck_cbam_iea_mb_month_canonical",
        ),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_indirect_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    basis_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    basis_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    month_start: Mapped[date] = mapped_column(Date, nullable=False)
    total_production_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    cbam_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_total_production_tonnes: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    normalized_cbam_quantity_tonnes: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    monthly_share_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)


class CbamIeaSourceSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_iea_source_snapshots"
    __table_args__ = (
        UniqueConstraint("result_id", "source_result_id", name="uq_cbam_iea_src_result_source"),
        Index("ix_cbam_iea_src_result", "result_id"),
        Index("ix_cbam_iea_src_source_result", "source_result_id"),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_indirect_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    source_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_purchased_electricity_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    activity_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    month_start: Mapped[date] = mapped_column(Date, nullable=False)
    activity_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    activity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    factor_source_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    factor_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    factor_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    factor_tco2e_per_mwh: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    factor_source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    factor_source_document: Mapped[str] = mapped_column(Text, nullable=False)
    factor_dataset_version: Mapped[str] = mapped_column(String(128), nullable=False)
    factor_reference_description: Mapped[str] = mapped_column(Text, nullable=False)
    factor_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    factor_valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    factor_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    facility_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    facility_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    monthly_share_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    cbam_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    cbam_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    non_cbam_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    non_cbam_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    exported_electricity_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    exported_electricity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    exported_electricity_mwh: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)


class CbamIeaProductAllocation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_iea_product_allocations"
    __table_args__ = (
        UniqueConstraint(
            "result_id",
            "product_profile_version_id",
            name="uq_cbam_iea_prod_result_profile",
        ),
        Index("ix_cbam_iea_prod_result", "result_id"),
        Index("ix_cbam_iea_prod_profile", "product_profile_version_id"),
        CheckConstraint("electricity_unit = 'MWh'", name="ck_cbam_iea_prod_elec_unit"),
        CheckConstraint("emissions_unit = 'tCO2e'", name="ck_cbam_iea_prod_em_unit"),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_indirect_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    cn_normalized_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cn_display_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    production_record_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    production_quantity_snapshots: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    normalized_quantity_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    denominator_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    raw_share: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    raw_allocated_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    final_allocated_electricity_mwh: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    electricity_rounding_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    raw_allocated_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    final_allocated_indirect_emissions_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False
    )
    emissions_rounding_adjustment: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    electricity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    emissions_unit: Mapped[str] = mapped_column(String(32), nullable=False)


class CbamIndirectEmissionsAllocationCurrent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_indirect_emissions_allocation_current"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "reporting_period_binding_id",
            "methodology_code",
            name="uq_cbam_iea_current_org_binding_method",
        ),
        Index("ix_cbam_iea_current_result", "current_result_id"),
        ForeignKeyConstraint(
            [
                "current_result_id",
                "organization_id",
                "reporting_period_binding_id",
            ],
            [
                "cbam_indirect_emissions_allocation_results.id",
                "cbam_indirect_emissions_allocation_results.organization_id",
                "cbam_indirect_emissions_allocation_results.reporting_period_binding_id",
            ],
            name="fk_cbam_iea_current_result_identity",
            ondelete="RESTRICT",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    methodology_code: Mapped[str] = mapped_column(String(128), nullable=False)
    current_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class CbamProductionProcess(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Binding-scoped Conventional production process draft (Phase 9A / SEE D_Processes)."""

    __tablename__ = "cbam_production_processes"
    __table_args__ = (
        Index(
            "ix_cbam_pp_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_pp_org_status", "organization_id", "status"),
        Index("ix_cbam_pp_product_profile", "product_profile_version_id"),
        CheckConstraint("status IN ('draft', 'archived')", name="ck_cbam_pp_status"),
        CheckConstraint(
            "calculation_method IN ('CONVENTIONAL', 'PROCESS_EMISSIONS', 'MASS_BALANCE')",
            name="ck_cbam_pp_method",
        ),
        CheckConstraint("row_version >= 1", name="ck_cbam_pp_row_version"),
        CheckConstraint(
            "produced_quantity IS NULL OR produced_quantity >= 0",
            name="ck_cbam_pp_produced_nonneg",
        ),
        CheckConstraint(
            "marketed_quantity IS NULL OR marketed_quantity >= 0",
            name="ck_cbam_pp_marketed_nonneg",
        ),
        CheckConstraint(
            "non_cbam_quantity IS NULL OR non_cbam_quantity >= 0",
            name="ck_cbam_pp_non_cbam_nonneg",
        ),
        CheckConstraint(
            "exported_electricity_quantity IS NULL OR exported_electricity_quantity >= 0",
            name="ck_cbam_pp_exported_elec_qty_nonneg",
        ),
        CheckConstraint(
            "exported_electricity_emission_factor IS NULL "
            "OR exported_electricity_emission_factor >= 0",
            name="ck_cbam_pp_exported_elec_ef_nonneg",
        ),
        CheckConstraint(
            "has_exported_electricity IS DISTINCT FROM FALSE OR ("
            "exported_electricity_quantity IS NULL "
            "AND exported_electricity_unit IS NULL "
            "AND exported_electricity_emission_factor IS NULL "
            "AND exported_electricity_ef_unit IS NULL "
            "AND exported_electricity_provenance IS NULL)",
            name="ck_cbam_pp_exported_elec_false_null",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_installation_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_profile_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    calculation_method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="CONVENTIONAL", server_default="CONVENTIONAL"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", server_default="draft"
    )
    produced_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    produced_quantity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    marketed_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    marketed_quantity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    non_cbam_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    non_cbam_quantity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    has_measurable_heat: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    heat_imported_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    heat_imported_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    heat_exported_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    heat_exported_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    heat_imported_ef: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    heat_exported_ef: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    heat_ef_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    heat_factor_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    heat_factor_document: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_waste_gas: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    waste_gas_imported_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    waste_gas_imported_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    waste_gas_exported_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    waste_gas_exported_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    waste_gas_provenance: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Phase 10D — workbook D_Processes!L71/L72 feeding T72 = -L71*L72.
    has_exported_electricity: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    exported_electricity_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    exported_electricity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    exported_electricity_emission_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    exported_electricity_ef_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    exported_electricity_provenance: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_quality_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data_verification_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data_quality_justification_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamProductionProcessProductUse(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Typed use of source process product in another CBAM product/profile (SEE L32:L40)."""

    __tablename__ = "cbam_production_process_product_uses"
    __table_args__ = (
        UniqueConstraint(
            "process_id",
            "target_product_profile_version_id",
            name="uq_cbam_ppu_process_target",
        ),
        Index(
            "ix_cbam_ppu_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_ppu_process", "process_id"),
        Index("ix_cbam_ppu_target_profile", "target_product_profile_version_id"),
        CheckConstraint("quantity >= 0", name="ck_cbam_ppu_qty_nonneg"),
        CheckConstraint("row_version >= 1", name="ck_cbam_ppu_row_version"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_production_processes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_product_profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamPrecursorDefaultDataset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_precursor_default_datasets"
    __table_args__ = (
        UniqueConstraint(
            "dataset_code", "dataset_version", name="uq_cbam_precursor_dv_dataset_code_version"
        ),
        Index("ix_cbam_precursor_dv_datasets_status", "status"),
        CheckConstraint(
            "status IN ('ACTIVE', 'SUPERSEDED', 'ARCHIVED')",
            name="ck_cbam_precursor_dv_dataset_status",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_cbam_precursor_dv_dataset_dates",
        ),
        CheckConstraint("value_count >= 0", name="ck_cbam_precursor_dv_dataset_value_count"),
    )

    dataset_code: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    source_workbook_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_workbook_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    regulation_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    value_count: Mapped[int] = mapped_column(Integer, nullable=False)


class CbamPrecursorDefaultValue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_precursor_default_values"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "source_sheet",
            "source_row",
            name="uq_cbam_precursor_dv_values_dataset_source",
        ),
        Index("ix_cbam_precursor_dv_values_dataset", "dataset_id"),
        Index("ix_cbam_precursor_dv_values_lookup", "dataset_id", "lookup_key"),
        Index(
            "ix_cbam_precursor_dv_values_country_cn",
            "dataset_id",
            "country_name",
            "cn_normalized_code",
        ),
        CheckConstraint("source_row >= 1", name="ck_cbam_precursor_dv_source_row"),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_precursor_default_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    country_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    is_other_countries_group: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    cn_normalized_code: Mapped[str] = mapped_column(String(32), nullable=False)
    cn_display_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    goods_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    goods_description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    production_route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    direct_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    direct_value_status: Mapped[str] = mapped_column(String(32), nullable=False)
    indirect_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    indirect_value_status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    total_value_status: Mapped[str] = mapped_column(String(32), nullable=False)
    direct_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    indirect_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    total_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unit_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    marked_up_totals_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    original_keys_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    lookup_key: Mapped[str] = mapped_column(String(512), nullable=False)


class CbamPurchasedPrecursor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_purchased_precursors"
    __table_args__ = (
        Index("ix_cbam_purch_prec_org", "organization_id"),
        Index(
            "ix_cbam_purch_prec_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_purch_prec_status", "status"),
        Index("ix_cbam_purch_prec_supplier", "supplier_id"),
        Index("ix_cbam_purch_prec_cn", "cn_normalized_code"),
        CheckConstraint("status IN ('draft', 'archived')", name="ck_cbam_purch_prec_status"),
        CheckConstraint(
            "data_source_mode IN ('SUPPLIER_DATA', 'EU_DEFAULT')",
            name="ck_cbam_purch_prec_mode",
        ),
        CheckConstraint("row_version >= 1", name="ck_cbam_purch_prec_row_version"),
        CheckConstraint("quantity IS NULL OR quantity >= 0", name="ck_cbam_purch_prec_qty_nonneg"),
        CheckConstraint(
            "non_cbam_quantity IS NULL OR non_cbam_quantity >= 0",
            name="ck_cbam_purch_prec_non_cbam_nonneg",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_installation_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    purchased_input_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_purchased_input_records.id", ondelete="RESTRICT"),
        nullable=True,
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    aggregated_goods_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cn_normalized_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cn_display_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    production_route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data_source_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    non_cbam_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    non_cbam_quantity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    specific_direct_embedded_emissions: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    specific_direct_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    specific_direct_source_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    electricity_consumption_intensity: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    electricity_intensity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    electricity_intensity_source_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    electricity_emission_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    electricity_ef_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    electricity_ef_source_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    specific_indirect_embedded_emissions: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    specific_indirect_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_justification_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provenance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_precursor_default_datasets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    default_value_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_precursor_default_values.id", ondelete="RESTRICT"),
        nullable=True,
    )
    default_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamPurchasedPrecursorProductUse(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_purchased_precursor_product_uses"
    __table_args__ = (
        UniqueConstraint(
            "precursor_id",
            "target_product_profile_version_id",
            name="uq_cbam_purch_prec_use_target",
        ),
        Index("ix_cbam_purch_prec_use_precursor", "precursor_id"),
        Index("ix_cbam_purch_prec_use_target", "target_product_profile_version_id"),
        CheckConstraint("quantity >= 0", name="ck_cbam_purch_prec_use_qty_nonneg"),
        CheckConstraint("row_version >= 1", name="ck_cbam_purch_prec_use_row_version"),
    )

    precursor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_purchased_precursors.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_product_profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamProductEmbeddedEmissionsResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Phase 10C immutable binding-scoped product embedded-emissions roll-up."""

    __tablename__ = "cbam_product_embedded_emissions_results"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "reporting_period_binding_id",
            "client_request_id",
            name="uq_cbam_pee_result_org_binding_client_request",
        ),
        UniqueConstraint(
            "id",
            "organization_id",
            "reporting_period_binding_id",
            name="uq_cbam_pee_result_id_org_binding",
        ),
        Index(
            "ix_cbam_pee_results_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_pee_results_created_at", "created_at", "id"),
        CheckConstraint("status = 'COMPLETED'", name="ck_cbam_pee_results_status"),
        CheckConstraint("result_unit = 'tCO2e'", name="ck_cbam_pee_results_unit"),
        CheckConstraint("specific_unit = 'tCO2e/t'", name="ck_cbam_pee_results_specific_unit"),
        CheckConstraint("dea_source_unit = 'tCO2'", name="ck_cbam_pee_results_dea_unit"),
        CheckConstraint(
            "product_count >= 1 AND precursor_contribution_count >= 0 "
            "AND internal_contribution_count >= 0",
            name="ck_cbam_pee_results_counts",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    methodology_code: Mapped[str] = mapped_column(String(128), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(32), nullable=False)
    workbook_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    workbook_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    workbook_formula_refs: Mapped[str] = mapped_column(Text, nullable=False)
    client_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    product_count: Mapped[int] = mapped_column(Integer, nullable=False)
    precursor_contribution_count: Mapped[int] = mapped_column(Integer, nullable=False)
    internal_contribution_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_direct_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    total_indirect_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    total_embedded_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    total_direct_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    total_indirect_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    total_embedded_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    result_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    specific_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    dea_source_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    workbook_gas: Mapped[str] = mapped_column(String(16), nullable=False)
    workbook_gwp: Mapped[str] = mapped_column(String(16), nullable=False)
    workbook_gwp_factor: Mapped[str] = mapped_column(String(16), nullable=False)
    dea_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_direct_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=True,
    )
    iea_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_indirect_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=True,
    )
    informational_codes_json: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    notes_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CbamProductEmbeddedEmissionsProduct(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per product-profile-version row of a Phase 10C roll-up result."""

    __tablename__ = "cbam_product_embedded_emissions_products"
    __table_args__ = (
        UniqueConstraint(
            "result_id",
            "product_profile_version_id",
            name="uq_cbam_pee_products_result_profile",
        ),
        UniqueConstraint("id", "result_id", name="uq_cbam_pee_products_id_result"),
        Index("ix_cbam_pee_products_result", "result_id"),
        Index("ix_cbam_pee_products_profile", "product_profile_version_id"),
        Index("ix_cbam_pee_products_process", "process_id"),
        Index(
            "ix_cbam_pee_products_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        CheckConstraint("result_unit = 'tCO2e'", name="ck_cbam_pee_products_unit"),
        CheckConstraint("specific_unit = 'tCO2e/t'", name="ck_cbam_pee_products_specific_unit"),
        CheckConstraint("dea_source_unit = 'tCO2'", name="ck_cbam_pee_products_dea_unit"),
        CheckConstraint("denominator_tonnes > 0", name="ck_cbam_pee_products_denominator_positive"),
        # V1 always snapshotted 0; V2 carries the workbook T72 term, so the historical
        # "must be zero" constraint was dropped in migration 0029 instead of relaxed.
        CheckConstraint(
            "exported_electricity_direct_tco2e <= 0",
            name="ck_cbam_pee_products_exported_electricity_nonpos",
        ),
        CheckConstraint(
            "precursor_contribution_count >= 0 AND production_record_count >= 0 "
            "AND internal_contribution_count >= 0",
            name="ck_cbam_pee_products_counts",
        ),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_embedded_emissions_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    cn_normalized_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cn_display_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Snapshot reference only: draft processes stay editable and deletable.
    process_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    process_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    process_produced_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    process_produced_quantity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    denominator_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    production_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    production_records_tonnes: Mapped[Decimal | None] = mapped_column(
        Numeric(36, 18), nullable=True
    )
    production_record_ids: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    dea_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_direct_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dea_product_allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    dea_direct_tco2: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    iea_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_indirect_emissions_allocation_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    iea_product_allocation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    iea_indirect_tco2e: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    has_measurable_heat: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    heat_attributed_tco2e: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    has_waste_gas: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    waste_gas_attributed_tco2e: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    exported_electricity_direct_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    exported_electricity_note_code: Mapped[str] = mapped_column(String(128), nullable=False)
    has_exported_electricity: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    exported_electricity_mwh: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    exported_electricity_emission_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(36, 18), nullable=True
    )
    own_direct_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    own_indirect_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    precursor_direct_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    precursor_indirect_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    internal_direct_tco2e_raw: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False, default=Decimal("0"), server_default="0"
    )
    internal_indirect_tco2e_raw: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False, default=Decimal("0"), server_default="0"
    )
    total_direct_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    total_indirect_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    total_embedded_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    own_direct_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    own_indirect_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    precursor_direct_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    precursor_indirect_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    internal_direct_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False, default=Decimal("0"), server_default="0"
    )
    internal_indirect_tco2e: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False, default=Decimal("0"), server_default="0"
    )
    total_direct_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    total_indirect_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    total_embedded_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    specific_direct_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    specific_indirect_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    specific_total_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    specific_direct: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    specific_indirect: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    specific_total: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    precursor_contribution_count: Mapped[int] = mapped_column(Integer, nullable=False)
    internal_contribution_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    result_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    specific_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    dea_source_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    components_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    provenance_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class CbamProductEmbeddedEmissionsPrecursorContribution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per (product row, precursor, product-use) contribution snapshot."""

    __tablename__ = "cbam_product_embedded_emissions_precursor_contributions"
    __table_args__ = (
        UniqueConstraint("result_id", "product_use_id", name="uq_cbam_pee_contrib_result_use"),
        Index("ix_cbam_pee_contrib_result", "result_id"),
        Index("ix_cbam_pee_contrib_product_row", "product_row_id"),
        Index("ix_cbam_pee_contrib_precursor", "precursor_id"),
        Index("ix_cbam_pee_contrib_product_use", "product_use_id"),
        ForeignKeyConstraint(
            ["product_row_id", "result_id"],
            [
                "cbam_product_embedded_emissions_products.id",
                "cbam_product_embedded_emissions_products.result_id",
            ],
            name="fk_cbam_pee_contrib_product_row",
            ondelete="RESTRICT",
        ),
        CheckConstraint("result_unit = 'tCO2e'", name="ck_cbam_pee_contrib_unit"),
        CheckConstraint("specific_unit = 'tCO2e/t'", name="ck_cbam_pee_contrib_specific_unit"),
        CheckConstraint("quantity_tonnes >= 0", name="ck_cbam_pee_contrib_qty_nonneg"),
        CheckConstraint(
            "data_source_mode IN ('SUPPLIER_DATA', 'EU_DEFAULT')",
            name="ck_cbam_pee_contrib_mode",
        ),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_embedded_emissions_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_row_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    product_profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Snapshot reference only: purchased precursors stay editable and deletable.
    precursor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    precursor_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    precursor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    precursor_cn_normalized_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    precursor_cn_display_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data_source_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    value_source: Mapped[str] = mapped_column(String(64), nullable=False)
    product_use_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_use_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    product_use_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    product_use_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    specific_direct: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    specific_indirect: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    contribution_direct_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    contribution_indirect_tco2e_raw: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    contribution_direct_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    contribution_indirect_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    default_dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    default_value_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    default_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    result_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    specific_unit: Mapped[str] = mapped_column(String(32), nullable=False)


class CbamProductEmbeddedEmissionsInternalContribution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Phase 10D per (consumer product row, supplier product) internal-flow snapshot.

    One row per internal product-use edge of the Leontief matrix. ``a_coefficient`` is the
    workbook ``A[consumer][supplier]`` entry and the contribution values are the solved
    supplier specific emissions multiplied by the consumed quantity.
    """

    __tablename__ = "cbam_product_embedded_emissions_internal_contributions"
    __table_args__ = (
        UniqueConstraint("result_id", "product_use_id", name="uq_cbam_pee_internal_result_use"),
        Index("ix_cbam_pee_internal_result", "result_id"),
        Index("ix_cbam_pee_internal_product_row", "product_row_id"),
        Index("ix_cbam_pee_internal_supplier_profile", "supplier_product_profile_version_id"),
        Index("ix_cbam_pee_internal_product_use", "product_use_id"),
        ForeignKeyConstraint(
            ["product_row_id", "result_id"],
            [
                "cbam_product_embedded_emissions_products.id",
                "cbam_product_embedded_emissions_products.result_id",
            ],
            name="fk_cbam_pee_internal_product_row",
            ondelete="RESTRICT",
        ),
        CheckConstraint("result_unit = 'tCO2e'", name="ck_cbam_pee_internal_unit"),
        CheckConstraint("specific_unit = 'tCO2e/t'", name="ck_cbam_pee_internal_specific_unit"),
        CheckConstraint("quantity_tonnes >= 0", name="ck_cbam_pee_internal_qty_nonneg"),
        CheckConstraint(
            "consumer_denominator_tonnes > 0", name="ck_cbam_pee_internal_denominator_positive"
        ),
        CheckConstraint(
            "consumer_product_profile_version_id <> supplier_product_profile_version_id",
            name="ck_cbam_pee_internal_no_self_reference",
        ),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_embedded_emissions_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_row_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    consumer_product_profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supplier_product_profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_profile_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Snapshot references only: draft processes and their uses stay editable.
    consumer_process_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    supplier_process_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    supplier_process_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    product_use_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_use_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    product_use_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    product_use_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    consumer_denominator_tonnes: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    a_coefficient: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    supplier_specific_direct: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    supplier_specific_indirect: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    contribution_direct_tco2e_raw: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    contribution_indirect_tco2e_raw: Mapped[Decimal] = mapped_column(
        Numeric(36, 18), nullable=False
    )
    contribution_direct_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    contribution_indirect_tco2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    result_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    specific_unit: Mapped[str] = mapped_column(String(32), nullable=False)


class CbamProductEmbeddedEmissionsCurrent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_product_embedded_emissions_current"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "reporting_period_binding_id",
            "methodology_code",
            name="uq_cbam_pee_current_org_binding_method",
        ),
        Index("ix_cbam_pee_current_result", "current_result_id"),
        ForeignKeyConstraint(
            ["current_result_id", "organization_id", "reporting_period_binding_id"],
            [
                "cbam_product_embedded_emissions_results.id",
                "cbam_product_embedded_emissions_results.organization_id",
                "cbam_product_embedded_emissions_results.reporting_period_binding_id",
            ],
            name="fk_cbam_pee_current_result_identity",
            ondelete="RESTRICT",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    methodology_code: Mapped[str] = mapped_column(String(128), nullable=False)
    current_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class CbamOfficialSeeExportRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Phase 12A Official SEE export run audit (xlsx on filesystem, not Postgres)."""

    __tablename__ = "cbam_official_see_export_runs"
    __table_args__ = (
        Index("ix_cbam_ose_runs_org", "organization_id"),
        Index(
            "ix_cbam_ose_runs_org_binding",
            "organization_id",
            "reporting_period_binding_id",
        ),
        Index("ix_cbam_ose_runs_status", "generation_status"),
        UniqueConstraint(
            "organization_id",
            "reporting_period_binding_id",
            "client_request_id",
            name="uq_cbam_ose_runs_org_binding_client_request",
        ),
        CheckConstraint(
            "generation_status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_cbam_ose_runs_generation_status",
        ),
        CheckConstraint(
            "validation_status IN ('PENDING', 'PASSED', 'FAILED', 'SKIPPED')",
            name="ck_cbam_ose_runs_validation_status",
        ),
        CheckConstraint(
            "formula_parity_status IN ('PENDING', 'PASSED', 'FAILED', 'ENGINE_UNAVAILABLE')",
            name="ck_cbam_ose_runs_parity_status",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_reporting_period_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    client_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    generation_status: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(64), nullable=False)
    formula_parity_status: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)
    template_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    template_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pee_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_product_embedded_emissions_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    dea_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_direct_emissions_allocation_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    iea_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_indirect_emissions_allocation_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    process_snapshot_ids: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    precursor_snapshot_ids: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_diagnostics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    generated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CbamOfficialSeeExportArtifact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cbam_official_see_export_artifacts"
    __table_args__ = (
        Index("ix_cbam_ose_artifacts_org", "organization_id"),
        Index("ix_cbam_ose_artifacts_run", "export_run_id"),
        CheckConstraint(
            "artifact_type IN ('XLSX', 'JSON_SUMMARY')",
            name="ck_cbam_ose_artifacts_type",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    export_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbam_official_see_export_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
