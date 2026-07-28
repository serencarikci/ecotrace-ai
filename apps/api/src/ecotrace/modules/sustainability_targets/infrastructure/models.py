from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class IntensityMetricDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'intensity_metric_definitions'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_intensity_metric_org_code'), Index('ix_intensity_metric_definitions_organization_id', 'organization_id'), Index('ix_intensity_metric_definitions_code', 'code'), Index('ix_intensity_metric_definitions_is_active', 'is_active'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    numerator_type: Mapped[str] = mapped_column(String(64), nullable=False)
    denominator_activity_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_types.id', ondelete='SET NULL'), nullable=True)
    denominator_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    display_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregation_method: Mapped[str] = mapped_column(String(32), nullable=False, default='sum')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class EnvironmentalKpiDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'environmental_kpi_definitions'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_env_kpi_org_code'), Index('ix_environmental_kpi_definitions_organization_id', 'organization_id'), Index('ix_environmental_kpi_definitions_code', 'code'), Index('ix_environmental_kpi_definitions_kpi_type', 'kpi_type'), Index('ix_environmental_kpi_definitions_is_active', 'is_active'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kpi_type: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_types.id', ondelete='SET NULL'), nullable=True)
    aggregation_method: Mapped[str] = mapped_column(String(32), nullable=False, default='sum')
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    target_direction: Mapped[str] = mapped_column(String(16), nullable=False, default='decrease')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class SustainabilityBaseline(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'sustainability_baselines'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_baseline_org_code'), Index('ix_sustainability_baselines_organization_id', 'organization_id'), Index('ix_sustainability_baselines_baseline_type', 'baseline_type'), Index('ix_sustainability_baselines_reporting_period_id', 'reporting_period_id'), Index('ix_sustainability_baselines_inventory_id', 'inventory_id'), Index('ix_sustainability_baselines_status', 'status'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    baseline_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reporting_period_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('reporting_periods.id', ondelete='SET NULL'), nullable=True)
    inventory_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('carbon_inventories.id', ondelete='SET NULL'), nullable=True)
    baseline_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baseline_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    baseline_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class SustainabilityTarget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'sustainability_targets'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_target_org_code'), Index('ix_sustainability_targets_organization_id', 'organization_id'), Index('ix_sustainability_targets_target_type', 'target_type'), Index('ix_sustainability_targets_status', 'status'), Index('ix_sustainability_targets_target_year', 'target_year'), Index('ix_sustainability_targets_owner_user_id', 'owner_user_id'), Index('ix_sustainability_targets_facility_id', 'facility_id'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('facilities.id', ondelete='SET NULL'), nullable=True)
    baseline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('sustainability_baselines.id', ondelete='RESTRICT'), nullable=False)
    baseline_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    target_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_direction: Mapped[str] = mapped_column(String(16), nullable=False, default='decrease')
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class SustainabilityTargetRevision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'sustainability_target_revisions'
    __table_args__ = (Index('ix_target_revisions_target_id', 'target_id'),)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('sustainability_targets.id', ondelete='CASCADE'), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

class ReductionInitiative(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'reduction_initiatives'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_initiative_org_code'), Index('ix_reduction_initiatives_organization_id', 'organization_id'), Index('ix_reduction_initiatives_target_id', 'target_id'), Index('ix_reduction_initiatives_facility_id', 'facility_id'), Index('ix_reduction_initiatives_status', 'status'), Index('ix_reduction_initiatives_planned_start_date', 'planned_start_date'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('sustainability_targets.id', ondelete='SET NULL'), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiative_type: Mapped[str] = mapped_column(String(64), nullable=False)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('facilities.id', ondelete='SET NULL'), nullable=True)
    activity_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_types.id', ondelete='SET NULL'), nullable=True)
    planned_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_reduction_kg_co2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=Decimal('0'))
    actual_reduction_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    expected_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='proposed')
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
