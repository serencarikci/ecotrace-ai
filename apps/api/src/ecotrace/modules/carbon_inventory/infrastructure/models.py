from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CarbonInventory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "carbon_inventories"
    __table_args__ = (
        Index("ix_carbon_inventories_organization_id", "organization_id"),
        Index("ix_carbon_inventories_reporting_period_id", "reporting_period_id"),
        Index("ix_carbon_inventories_status", "status"),
        Index("ix_carbon_inventories_created_at", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    reporting_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reporting_periods.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    calculation_methodology_version: Mapped[str] = mapped_column(String(64), nullable=False)
    gwp_dataset_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    partial_calculation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calculated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    error_summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class CarbonCalculationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "carbon_calculation_runs"
    __table_args__ = (
        UniqueConstraint("inventory_id", "run_number", name="uq_carbon_runs_inventory_run"),
        Index("ix_carbon_calculation_runs_inventory_id", "inventory_id"),
        Index("ix_carbon_calculation_runs_status", "status"),
        Index("ix_carbon_calculation_runs_created_at", "created_at"),
    )

    inventory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carbon_inventories.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    activity_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calculated_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    error_summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    partial_calculation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    gwp_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class CarbonCalculationItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "carbon_calculation_items"
    __table_args__ = (
        Index("ix_carbon_calc_items_inventory_id", "inventory_id"),
        Index("ix_carbon_calc_items_calculation_run_id", "calculation_run_id"),
        Index("ix_carbon_calc_items_activity_record_id", "activity_record_id"),
        Index("ix_carbon_calc_items_emission_factor_id", "emission_factor_id"),
        Index("ix_carbon_calc_items_scope", "scope"),
        Index("ix_carbon_calc_items_category", "category"),
        Index("ix_carbon_calc_items_status", "status"),
        UniqueConstraint(
            "calculation_run_id",
            "activity_record_id",
            name="uq_carbon_calc_items_run_activity",
        ),
    )

    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carbon_calculation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    inventory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carbon_inventories.id", ondelete="CASCADE"),
        nullable=False,
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activity_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    emission_factor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emission_factors.id", ondelete="RESTRICT"),
        nullable=True,
    )
    factor_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emission_factor_sources.id", ondelete="RESTRICT"),
        nullable=True,
    )
    activity_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    activity_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    normalized_unit_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    factor_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    factor_unit_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(128), nullable=True)
    co2_kg: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    ch4_kg: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    n2o_kg: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    other_gases_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    biogenic_co2_kg: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    total_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    matching_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matching_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation_formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="failed")
    validation_errors_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
