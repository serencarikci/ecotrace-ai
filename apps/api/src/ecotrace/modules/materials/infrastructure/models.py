from __future__ import annotations
import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Material(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'materials'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_materials_org_code'), Index('ix_materials_organization_id', 'organization_id'), Index('ix_materials_material_category', 'material_category'), Index('ix_materials_supplier_id', 'supplier_id'), Index('ix_materials_is_active', 'is_active'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_category: Mapped[str] = mapped_column(String(64), nullable=False)
    default_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    density_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    density_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recycled_content_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    renewable_content_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    hazardous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(2), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
