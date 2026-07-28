from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Unit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("code", name="uq_units_code"),
        CheckConstraint("conversion_factor_to_base > 0", name="conversion_positive"),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    conversion_factor_to_base: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    base_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    decimal_precision: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class ActivityType(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "activity_types"
    __table_args__ = (UniqueConstraint("code", name="uq_activity_types_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    default_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    allowed_unit_dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_value_type: Mapped[str] = mapped_column(String(32), nullable=False, default="decimal")
    data_frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="monthly")
    requires_facility: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    requires_equipment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
