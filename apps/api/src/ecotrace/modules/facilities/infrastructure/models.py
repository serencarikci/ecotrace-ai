from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Facility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "facilities"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_facilities_org_code"),
        Index("ix_facilities_organization_id", "organization_id"),
        Index("ix_facilities_organization_id_is_active", "organization_id", "is_active"),
        Index("ix_facilities_facility_type", "facility_type"),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="lat_range"
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="lon_range"
        ),
        CheckConstraint(
            "operational_end_date IS NULL OR operational_start_date IS NULL "
            "OR operational_end_date >= operational_start_date",
            name="ops_dates",
        ),
        CheckConstraint("char_length(country_code) = 2", name="facility_country_code_length"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    facility_type: Mapped[str] = mapped_column(String(64), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    district: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address_line: Mapped[str | None] = mapped_column(String(512), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    operational_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    operational_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
