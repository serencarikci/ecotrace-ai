from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class GwpValue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'gwp_values'
    __table_args__ = (Index('ix_gwp_values_assessment_report_code', 'assessment_report_code'), Index('ix_gwp_values_gas_code', 'gas_code'), Index('ix_gwp_values_is_active', 'is_active'), UniqueConstraint('assessment_report_code', 'gas_code', 'effective_from', name='uq_gwp_values_dataset_gas_from'))
    assessment_report_code: Mapped[str] = mapped_column(String(64), nullable=False)
    gas_code: Mapped[str] = mapped_column(String(32), nullable=False)
    gwp_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')

class EmissionFactorSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'emission_factor_sources'
    __table_args__ = (UniqueConstraint('code', name='uq_emission_factor_sources_code'), Index('ix_emission_factor_sources_is_active', 'is_active'))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    geographic_coverage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    release_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')

class EmissionFactor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'emission_factors'
    __table_args__ = (UniqueConstraint('code', 'version', name='uq_emission_factors_code_version'), CheckConstraint('factor_value IS NULL OR factor_value >= 0', name='factor_value_nonneg'), CheckConstraint('co2_factor IS NULL OR co2_factor >= 0', name='co2_factor_nonneg'), CheckConstraint('ch4_factor IS NULL OR ch4_factor >= 0', name='ch4_factor_nonneg'), CheckConstraint('n2o_factor IS NULL OR n2o_factor >= 0', name='n2o_factor_nonneg'), CheckConstraint('biogenic_co2_factor IS NULL OR biogenic_co2_factor >= 0', name='biogenic_co2_factor_nonneg'), CheckConstraint('uncertainty_percentage IS NULL OR (uncertainty_percentage >= 0 AND uncertainty_percentage <= 100)', name='uncertainty_pct_range'), CheckConstraint('valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from', name='factor_valid_range'), Index('ix_emission_factors_source_id', 'source_id'), Index('ix_emission_factors_activity_type_id', 'activity_type_id'), Index('ix_emission_factors_scope', 'scope'), Index('ix_emission_factors_category', 'category'), Index('ix_emission_factors_geography_code', 'geography_code'), Index('ix_emission_factors_valid_from', 'valid_from'), Index('ix_emission_factors_valid_to', 'valid_to'), Index('ix_emission_factors_status', 'status'), Index('ix_emission_factors_is_active', 'is_active'))
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('emission_factor_sources.id', ondelete='RESTRICT'), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_types.id', ondelete='RESTRICT'), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geography_code: Mapped[str] = mapped_column(String(64), nullable=False, default='GLOBAL')
    facility_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    technology_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transportation_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    factor_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    co2_factor: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    ch4_factor: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    n2o_factor: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    other_gases_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    biogenic_co2_factor: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    uncertainty_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')
    supersedes_factor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('emission_factors.id', ondelete='SET NULL'), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class OrganizationEmissionFactorPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'organization_emission_factor_preferences'
    __table_args__ = (Index('ix_org_ef_pref_organization_id', 'organization_id'), Index('ix_org_ef_pref_activity_type_id', 'activity_type_id'), Index('ix_org_ef_pref_emission_factor_id', 'emission_factor_id'), Index('ix_org_ef_pref_valid_from', 'valid_from'), Index('ix_org_ef_pref_valid_to', 'valid_to'), CheckConstraint('valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from', name='org_ef_pref_valid_range'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    activity_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_types.id', ondelete='RESTRICT'), nullable=False)
    emission_factor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('emission_factors.id', ondelete='RESTRICT'), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')

class EmissionFactorImportJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'emission_factor_import_jobs'
    __table_args__ = (Index('ix_ef_import_jobs_status', 'status'),)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='pending')
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
