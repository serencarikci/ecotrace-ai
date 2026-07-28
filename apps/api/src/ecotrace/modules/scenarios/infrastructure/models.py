from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class ScenarioModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'scenario_models'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_scenario_org_code'), Index('ix_scenario_models_organization_id', 'organization_id'), Index('ix_scenario_models_baseline_inventory_id', 'baseline_inventory_id'), Index('ix_scenario_models_scenario_type', 'scenario_type'), Index('ix_scenario_models_status', 'status'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenario_type: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_inventory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('carbon_inventories.id', ondelete='RESTRICT'), nullable=False)
    reporting_period_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('reporting_periods.id', ondelete='SET NULL'), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

class ScenarioAssumption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'scenario_assumptions'
    __table_args__ = (Index('ix_scenario_assumptions_scenario_id', 'scenario_id'),)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('scenario_models.id', ondelete='CASCADE'), nullable=False)
    assumption_type: Mapped[str] = mapped_column(String(64), nullable=False)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('facilities.id', ondelete='SET NULL'), nullable=True)
    activity_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_types.id', ondelete='SET NULL'), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parameter_code: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    scenario_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    unit_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    change_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class ScenarioRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'scenario_runs'
    __table_args__ = (UniqueConstraint('scenario_id', 'run_number', name='uq_scenario_run_number'), Index('ix_scenario_runs_scenario_id', 'scenario_id'), Index('ix_scenario_runs_status', 'status'), Index('ix_scenario_runs_created_at', 'created_at'))
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('scenario_models.id', ondelete='CASCADE'), nullable=False)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='queued')
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    baseline_total_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    scenario_total_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    reduction_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    reduction_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    result_summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)

class ScenarioRunItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'scenario_run_items'
    __table_args__ = (Index('ix_scenario_run_items_scenario_run_id', 'scenario_run_id'), Index('ix_scenario_run_items_activity_record_id', 'activity_record_id'), Index('ix_scenario_run_items_facility_id', 'facility_id'), Index('ix_scenario_run_items_activity_type_id', 'activity_type_id'), Index('ix_scenario_run_items_scope', 'scope'), Index('ix_scenario_run_items_category', 'category'))
    scenario_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('scenario_runs.id', ondelete='CASCADE'), nullable=False)
    baseline_calculation_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('carbon_calculation_items.id', ondelete='SET NULL'), nullable=True)
    activity_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_records.id', ondelete='RESTRICT'), nullable=False)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('facilities.id', ondelete='SET NULL'), nullable=True)
    activity_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_types.id', ondelete='SET NULL'), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    baseline_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    scenario_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    baseline_kg_co2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    scenario_kg_co2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    reduction_kg_co2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    applied_assumption_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    calculation_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
