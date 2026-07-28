from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProductionLine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "production_lines"
    __table_args__ = (
        UniqueConstraint("facility_id", "code", name="uq_production_lines_facility_code"),
        Index("ix_production_lines_organization_id", "organization_id"),
        Index("ix_production_lines_facility_id", "facility_id"),
        CheckConstraint("capacity_value IS NULL OR capacity_value > 0", name="capacity_positive"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    production_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capacity_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    capacity_unit_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class Equipment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "equipment"
    __table_args__ = (
        UniqueConstraint("facility_id", "code", name="uq_equipment_facility_code"),
        Index("ix_equipment_organization_id", "organization_id"),
        Index("ix_equipment_facility_id", "facility_id"),
        Index("ix_equipment_production_line_id", "production_line_id"),
        Index("ix_equipment_equipment_type", "equipment_type"),
        Index("ix_equipment_is_active", "is_active"),
        CheckConstraint(
            "decommissioning_date IS NULL OR commissioning_date IS NULL "
            "OR decommissioning_date >= commissioning_date",
            name="equip_dates",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False
    )
    production_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_lines.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    equipment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    commissioning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    decommissioning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class DataSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "data_sources"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_data_sources_org_code"),
        Index("ix_data_sources_organization_id", "organization_id"),
        Index("ix_data_sources_facility_id", "facility_id"),
        Index("ix_data_sources_equipment_id", "equipment_id"),
        Index("ix_data_sources_source_type", "source_type"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
