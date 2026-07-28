from __future__ import annotations
import uuid
from typing import Any
from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Supplier(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'suppliers'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_suppliers_org_code'), Index('ix_suppliers_organization_id', 'organization_id'), Index('ix_suppliers_country_code', 'country_code'), Index('ix_suppliers_status', 'status'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address_line: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    supplier_type: Mapped[str] = mapped_column(String(64), nullable=False, default='other')
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    sustainability_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
