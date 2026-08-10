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

INSTALLATION_STATUSES = ('draft', 'active', 'archived')
PERIOD_BINDING_STATUSES = (
    'draft',
    'data_collection',
    'data_ready',
    'expert_review',
    'rework',
    'approval_pending',
    'approved',
    'locked',
    'revised',
    'archived',
)
PRODUCT_PROFILE_STATUSES = ('draft', 'active', 'superseded', 'archived')


class CbamInstallationProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'cbam_installation_profiles'
    __table_args__ = (
        UniqueConstraint('organization_id', 'code', name='uq_cbam_installation_org_code'),
        Index('ix_cbam_installation_profiles_organization_id', 'organization_id'),
        Index('ix_cbam_installation_profiles_facility_id', 'facility_id'),
        Index('ix_cbam_installation_profiles_status', 'status'),
        Index(
            'uq_cbam_installation_one_active_per_facility',
            'organization_id',
            'facility_id',
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name='installation_status',
        ),
        CheckConstraint('row_version >= 1', name='installation_row_version_positive'),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('facilities.id', ondelete='RESTRICT'), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default='UTC')
    operator_identity_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamReportingPeriodBinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'cbam_reporting_period_bindings'
    __table_args__ = (
        UniqueConstraint(
            'organization_id',
            'reporting_period_id',
            name='uq_cbam_period_binding_org_period',
        ),
        Index('ix_cbam_reporting_period_bindings_organization_id', 'organization_id'),
        Index('ix_cbam_reporting_period_bindings_reporting_period_id', 'reporting_period_id'),
        Index('ix_cbam_reporting_period_bindings_status', 'status'),
        CheckConstraint('row_version >= 1', name='period_binding_row_version_positive'),
        CheckConstraint('revision_number >= 0', name='period_binding_revision_non_negative'),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    reporting_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('reporting_periods.id', ondelete='RESTRICT'),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_calculation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    revision_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default='0'
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamProductProfileVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_product_profile_versions'
    __table_args__ = (
        UniqueConstraint(
            'organization_id',
            'product_id',
            'version',
            name='uq_cbam_product_profile_org_product_version',
        ),
        Index('ix_cbam_product_profile_versions_organization_id', 'organization_id'),
        Index('ix_cbam_product_profile_versions_product_id', 'product_id'),
        Index('ix_cbam_product_profile_versions_status', 'status'),
        CheckConstraint(
            "status IN ('draft', 'active', 'superseded', 'archived')",
            name='product_profile_status',
        ),
        CheckConstraint('version >= 1', name='product_profile_version_positive'),
        CheckConstraint('row_version >= 1', name='product_profile_row_version_positive'),
        CheckConstraint(
            'valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from',
            name='product_profile_valid_dates',
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('products.id', ondelete='RESTRICT'), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    classification_ready: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default='false'
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamProductionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_production_records'
    __table_args__ = (
        Index('ix_cbam_production_records_organization_id', 'organization_id'),
        Index(
            'ix_cbam_production_records_org_binding',
            'organization_id',
            'reporting_period_binding_id',
        ),
        Index(
            'ix_cbam_production_records_org_installation',
            'organization_id',
            'installation_profile_id',
        ),
        Index('ix_cbam_production_records_status', 'status'),
        CheckConstraint("status IN ('active', 'archived')", name='production_record_status'),
        CheckConstraint('quantity > 0', name='production_quantity_positive'),
        CheckConstraint('row_version >= 1', name='production_row_version_positive'),
        CheckConstraint(
            'period_end IS NULL OR period_start IS NULL OR period_end >= period_start',
            name='production_period_dates',
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_reporting_period_bindings.id', ondelete='RESTRICT'),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_installation_profiles.id', ondelete='RESTRICT'),
        nullable=False,
    )
    product_profile_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_product_profile_versions.id', ondelete='RESTRICT'),
        nullable=True,
    )
    production_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default='MANUAL')
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='active')
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamActivityRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_activity_records'
    __table_args__ = (
        Index('ix_cbam_activity_records_organization_id', 'organization_id'),
        Index(
            'ix_cbam_activity_records_org_binding',
            'organization_id',
            'reporting_period_binding_id',
        ),
        Index(
            'ix_cbam_activity_records_org_installation',
            'organization_id',
            'installation_profile_id',
        ),
        Index(
            'ix_cbam_activity_records_binding_type',
            'reporting_period_binding_id',
            'activity_type',
        ),
        Index('ix_cbam_activity_records_status', 'status'),
        CheckConstraint("status IN ('active', 'archived')", name='activity_record_status'),
        CheckConstraint('quantity > 0', name='activity_quantity_positive'),
        CheckConstraint('row_version >= 1', name='activity_row_version_positive'),
        CheckConstraint(
            'period_end IS NULL OR period_start IS NULL OR period_end >= period_start',
            name='activity_period_dates',
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_reporting_period_bindings.id', ondelete='RESTRICT'),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_installation_profiles.id', ondelete='RESTRICT'),
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
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='active')
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamActivityProperty(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_activity_properties'
    __table_args__ = (
        UniqueConstraint(
            'activity_record_id',
            'property_code',
            name='uq_cbam_activity_property_record_code',
        ),
        Index('ix_cbam_activity_properties_organization_id', 'organization_id'),
        Index('ix_cbam_activity_properties_activity_record_id', 'activity_record_id'),
        CheckConstraint('numeric_value > 0', name='activity_property_value_positive'),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_activity_records.id', ondelete='CASCADE'),
        nullable=False,
    )
    property_code: Mapped[str] = mapped_column(String(64), nullable=False)
    numeric_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default='PRIMARY')
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamPurchasedInputRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_purchased_input_records'
    __table_args__ = (
        Index('ix_cbam_purchased_input_records_organization_id', 'organization_id'),
        Index(
            'ix_cbam_purchased_input_records_org_binding',
            'organization_id',
            'reporting_period_binding_id',
        ),
        Index(
            'ix_cbam_purchased_input_records_org_installation',
            'organization_id',
            'installation_profile_id',
        ),
        Index('ix_cbam_purchased_input_records_status', 'status'),
        CheckConstraint("status IN ('active', 'archived')", name='purchased_input_status'),
        CheckConstraint('quantity > 0', name='purchased_quantity_positive'),
        CheckConstraint(
            'consumed_quantity IS NULL OR consumed_quantity >= 0',
            name='consumed_quantity_non_negative',
        ),
        CheckConstraint('row_version >= 1', name='purchased_row_version_positive'),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_reporting_period_bindings.id', ondelete='RESTRICT'),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_installation_profiles.id', ondelete='RESTRICT'),
        nullable=False,
    )
    product_profile_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_product_profile_versions.id', ondelete='RESTRICT'),
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
        String(32), nullable=False, default='NOT_PROVIDED'
    )
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='active')
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )

class CbamAllocationRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_allocation_rules'
    __table_args__ = (
        Index('ix_cbam_allocation_rules_organization_id', 'organization_id'),
        Index(
            'ix_cbam_allocation_rules_org_binding',
            'organization_id',
            'reporting_period_binding_id',
        ),
        Index(
            'ix_cbam_allocation_rules_org_installation',
            'organization_id',
            'installation_profile_id',
        ),
        Index(
            'ix_cbam_allocation_rules_org_product',
            'organization_id',
            'product_profile_version_id',
        ),
        Index('ix_cbam_allocation_rules_status', 'status'),
        Index(
            'uq_cbam_allocation_one_active_per_scope',
            'organization_id',
            'reporting_period_binding_id',
            'installation_profile_id',
            text("COALESCE(product_profile_version_id, '00000000-0000-0000-0000-000000000000')"),
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')",
            name='allocation_rule_status',
        ),
        CheckConstraint(
            "allocation_method IN ('DIRECT_ASSIGNMENT', 'PRODUCTION_QUANTITY_RATIO', 'MANUAL_RATIO')",
            name='allocation_method',
        ),
        CheckConstraint(
            'allocation_ratio IS NULL OR (allocation_ratio >= 0 AND allocation_ratio <= 1)',
            name='allocation_ratio_bounds',
        ),
        CheckConstraint('row_version >= 1', name='allocation_rule_row_version_positive'),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_reporting_period_bindings.id', ondelete='RESTRICT'),
        nullable=False,
    )
    installation_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_installation_profiles.id', ondelete='RESTRICT'),
        nullable=False,
    )
    product_profile_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_product_profile_versions.id', ondelete='RESTRICT'),
        nullable=True,
    )
    allocation_method: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    allocation_ratio: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    numerator_production_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_production_records.id', ondelete='RESTRICT'),
        nullable=True,
    )
    denominator_production_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_production_records.id', ondelete='RESTRICT'),
        nullable=True,
    )
    numerator_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    denominator_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='DRAFT')
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamAllocationResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_allocation_results'
    __table_args__ = (
        Index('ix_cbam_allocation_results_organization_id', 'organization_id'),
        Index(
            'ix_cbam_allocation_results_org_binding',
            'organization_id',
            'reporting_period_binding_id',
        ),
        Index('ix_cbam_allocation_results_rule_id', 'allocation_rule_id'),
        Index(
            'ix_cbam_allocation_results_source',
            'source_type',
            'source_id',
        ),
        Index(
            'ix_cbam_allocation_results_current_lookup',
            'organization_id',
            'allocation_rule_id',
            'source_type',
            'source_id',
            'is_current',
        ),
        CheckConstraint(
            "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD')",
            name='allocation_source_type',
        ),
        CheckConstraint(
            'allocation_ratio >= 0 AND allocation_ratio <= 1',
            name='allocation_result_ratio_bounds',
        ),
        CheckConstraint('source_quantity > 0', name='allocation_source_quantity_positive'),
        CheckConstraint('allocated_quantity >= 0', name='allocation_allocated_non_negative'),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_reporting_period_bindings.id', ondelete='RESTRICT'),
        nullable=False,
    )
    allocation_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_allocation_rules.id', ondelete='RESTRICT'),
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
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )

class CbamReferenceSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_reference_sources'
    __table_args__ = (
        Index('ix_cbam_reference_sources_organization_id', 'organization_id'),
        Index('ix_cbam_reference_sources_status', 'status'),
        Index(
            'uq_cbam_reference_source_org_code',
            text("COALESCE(organization_id, '00000000-0000-0000-0000-000000000000')"),
            'code',
            unique=True,
        ),
        CheckConstraint(
            "source_type IN ('STANDARD_REFERENCE', 'PRIMARY_MEASUREMENT', "
            "'SUPPLIER_DECLARATION', 'MANUAL_APPROVED', 'OTHER')",
            name='reference_source_type',
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name='reference_source_status',
        ),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='ACTIVE')
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamFactorDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_factor_definitions'
    __table_args__ = (
        UniqueConstraint('code', name='uq_cbam_factor_definition_code'),
        Index('ix_cbam_factor_definitions_status', 'status'),
        Index('ix_cbam_factor_definitions_category', 'factor_category'),
        CheckConstraint(
            "factor_category IN ('ACTIVITY_PROPERTY', 'EMISSION_FACTOR', "
            "'EMBEDDED_EMISSION_FACTOR', 'ENERGY_FACTOR', 'OTHER')",
            name='factor_definition_category',
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name='factor_definition_status',
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
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='ACTIVE')


class CbamFactorValue(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_factor_values'
    __table_args__ = (
        Index('ix_cbam_factor_values_organization_id', 'organization_id'),
        Index('ix_cbam_factor_values_definition_status', 'factor_definition_id', 'status'),
        Index('ix_cbam_factor_values_activity_type_status', 'activity_type', 'status'),
        Index(
            'ix_cbam_factor_values_org_definition',
            'organization_id',
            'factor_definition_id',
        ),
        Index('ix_cbam_factor_values_validity', 'valid_from', 'valid_until'),
        CheckConstraint(
            "data_source_type IN ('PRIMARY', 'DEFAULT_REFERENCE')",
            name='factor_value_data_source_type',
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')",
            name='factor_value_status',
        ),
        CheckConstraint('numeric_value > 0', name='factor_value_positive'),
        CheckConstraint('row_version >= 1', name='factor_value_row_version_positive'),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True
    )
    factor_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_factor_definitions.id', ondelete='RESTRICT'),
        nullable=False,
    )
    reference_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_reference_sources.id', ondelete='RESTRICT'),
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
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='DRAFT')
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamFactorResolution(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_factor_resolutions'
    __table_args__ = (
        Index('ix_cbam_factor_resolutions_organization_id', 'organization_id'),
        Index(
            'ix_cbam_factor_resolutions_org_binding',
            'organization_id',
            'reporting_period_binding_id',
        ),
        Index(
            'ix_cbam_factor_resolutions_source',
            'source_type',
            'source_id',
        ),
        Index(
            'ix_cbam_factor_resolutions_binding_status',
            'reporting_period_binding_id',
            'resolution_status',
        ),
        CheckConstraint(
            "source_type IN ('ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD', 'ALLOCATION_RESULT')",
            name='factor_resolution_source_type',
        ),
        CheckConstraint(
            "resolution_status IN ("
            "'RESOLVED_PRIMARY', 'RESOLVED_DEFAULT', 'UNRESOLVED', 'AMBIGUOUS', "
            "'INCOMPATIBLE_UNIT', 'OUTSIDE_VALIDITY', 'BLOCKED'"
            ")",
            name='factor_resolution_status',
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_reporting_period_bindings.id', ondelete='RESTRICT'),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    factor_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_factor_definitions.id', ondelete='RESTRICT'),
        nullable=False,
    )
    resolution_status: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_activity_property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_activity_properties.id', ondelete='SET NULL'),
        nullable=True,
    )
    selected_factor_value_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_factor_values.id', ondelete='SET NULL'),
        nullable=True,
    )
    selected_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    selected_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_precedence: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolver_version: Mapped[str] = mapped_column(String(64), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CbamCalculationDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_calculation_definitions'
    __table_args__ = (
        UniqueConstraint('code', name='uq_cbam_calculation_definition_code'),
        Index('ix_cbam_calculation_definitions_status', 'status'),
        Index('ix_cbam_calculation_definitions_factor', 'factor_definition_id'),
        CheckConstraint(
            "calculation_type IN ('MULTIPLY_ACTIVITY_BY_FACTOR')",
            name='calculation_definition_type',
        ),
        CheckConstraint(
            "source_type IN ("
            "'ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD', 'ALLOCATION_RESULT'"
            ")",
            name='calculation_definition_source_type',
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name='calculation_definition_status',
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    calculation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    factor_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_factor_definitions.id', ondelete='RESTRICT'),
        nullable=False,
    )
    output_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='ACTIVE')


class CbamCalculationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_calculation_runs'
    __table_args__ = (
        Index('ix_cbam_calculation_runs_organization_id', 'organization_id'),
        Index(
            'ix_cbam_calculation_runs_org_binding',
            'organization_id',
            'reporting_period_binding_id',
        ),
        Index('ix_cbam_calculation_runs_status', 'status'),
        CheckConstraint(
            "status IN ("
            "'DRAFT', 'RUNNING', 'COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED', 'ARCHIVED'"
            ")",
            name='calculation_run_status',
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_reporting_period_bindings.id', ondelete='RESTRICT'),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='DRAFT')
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
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamCalculationResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_calculation_results'
    __table_args__ = (
        Index('ix_cbam_calculation_results_organization_id', 'organization_id'),
        Index('ix_cbam_calculation_results_run_status', 'calculation_run_id', 'status'),
        Index('ix_cbam_calculation_results_source', 'source_type', 'source_id'),
        Index('ix_cbam_calculation_results_factor_resolution', 'factor_resolution_id'),
        Index('ix_cbam_calculation_results_allocation', 'allocation_result_id'),
        Index(
            'ix_cbam_calculation_results_input_key_current',
            'organization_id',
            'input_fingerprint',
            unique=True,
            postgresql_where=text('is_current = true'),
        ),
        CheckConstraint(
            "source_type IN ("
            "'ACTIVITY_RECORD', 'PURCHASED_INPUT_RECORD', 'ALLOCATION_RESULT'"
            ")",
            name='calculation_result_source_type',
        ),
        CheckConstraint(
            "status IN ("
            "'CALCULATED', 'BLOCKED', 'INVALID_INPUT', 'INCOMPATIBLE_UNIT', "
            "'UNRESOLVED_FACTOR', 'AMBIGUOUS_FACTOR', 'UNSUPPORTED_FORMULA'"
            ")",
            name='calculation_result_status',
        ),
        CheckConstraint(
            "calculation_type IN ('MULTIPLY_ACTIVITY_BY_FACTOR')",
            name='calculation_result_type',
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_calculation_runs.id', ondelete='RESTRICT'),
        nullable=False,
    )
    calculation_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_calculation_definitions.id', ondelete='RESTRICT'),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    allocation_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_allocation_results.id', ondelete='SET NULL'),
        nullable=True,
    )
    factor_resolution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_factor_resolutions.id', ondelete='RESTRICT'),
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
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamExportTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_export_templates'
    __table_args__ = (
        Index('ix_cbam_export_templates_organization_id', 'organization_id'),
        Index('ix_cbam_export_templates_status', 'status'),
        Index(
            'uq_cbam_export_template_org_code_version',
            text("COALESCE(organization_id, '00000000-0000-0000-0000-000000000000')"),
            'code',
            'version',
            unique=True,
        ),
        CheckConstraint(
            "template_type IN ('INTERNAL_SKDM', 'OFFICIAL_CBAM_TEMPLATE', 'CUSTOMER_TEMPLATE')",
            name='export_template_type',
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')",
            name='export_template_status',
        ),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='DRAFT')
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamExportMapping(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_export_mappings'
    __table_args__ = (
        UniqueConstraint(
            'export_template_id',
            'mapping_code',
            name='uq_cbam_export_mapping_template_code',
        ),
        Index('ix_cbam_export_mappings_template_id', 'export_template_id'),
        CheckConstraint(
            "source_type IN ("
            "'ORGANIZATION', 'INSTALLATION', 'REPORTING_PERIOD', 'PRODUCT', "
            "'PRODUCTION_RECORD', 'ACTIVITY_RECORD', 'PURCHASED_INPUT', "
            "'ALLOCATION_RESULT', 'FACTOR_RESOLUTION', 'CALCULATION_RESULT', "
            "'CALCULATED_SUMMARY', 'CONSTANT'"
            ")",
            name='export_mapping_source_type',
        ),
        CheckConstraint(
            "destination_type IN ('CELL', 'NAMED_RANGE', 'TABLE_COLUMN', 'REPEATING_ROW')",
            name='export_mapping_destination_type',
        ),
        CheckConstraint(
            "value_type IN ("
            "'STRING', 'NUMBER', 'DATE', 'DATETIME', 'BOOLEAN', 'ENUM', 'UNIT'"
            ")",
            name='export_mapping_value_type',
        ),
        CheckConstraint(
            "transformation_code IN ("
            "'NONE', 'DECIMAL_TO_NUMBER', 'DATE_TO_EXCEL_DATE', "
            "'DATETIME_TO_EXCEL_DATETIME', 'ENUM_TO_DISPLAY_LABEL', "
            "'UNIT_DISPLAY', 'BOOLEAN_TO_YES_NO'"
            ") OR transformation_code IS NULL",
            name='export_mapping_transformation',
        ),
    )

    export_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_export_templates.id', ondelete='CASCADE'),
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

    __tablename__ = 'cbam_export_runs'
    __table_args__ = (
        Index('ix_cbam_export_runs_organization_id', 'organization_id'),
        Index(
            'ix_cbam_export_runs_org_binding',
            'organization_id',
            'reporting_period_binding_id',
        ),
        Index('ix_cbam_export_runs_status', 'status'),
        CheckConstraint(
            "status IN ("
            "'PENDING', 'RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', "
            "'FAILED', 'CANCELLED'"
            ")",
            name='export_run_status',
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    reporting_period_binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_reporting_period_bindings.id', ondelete='RESTRICT'),
        nullable=False,
    )
    export_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_export_templates.id', ondelete='RESTRICT'),
        nullable=False,
    )
    calculation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_calculation_runs.id', ondelete='SET NULL'),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default='PENDING')
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
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )


class CbamExportArtifact(Base, UUIDPrimaryKeyMixin, TimestampMixin):

    __tablename__ = 'cbam_export_artifacts'
    __table_args__ = (
        Index('ix_cbam_export_artifacts_organization_id', 'organization_id'),
        Index('ix_cbam_export_artifacts_export_run_id', 'export_run_id'),
        CheckConstraint(
            "artifact_type IN ('XLSX', 'CSV_SUMMARY', 'JSON_SUMMARY', 'HTML_REPORT')",
            name='export_artifact_type',
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False
    )
    export_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('cbam_export_runs.id', ondelete='CASCADE'),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)

