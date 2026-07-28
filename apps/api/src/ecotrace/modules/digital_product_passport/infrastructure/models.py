from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Any
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class DigitalProductPassport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'digital_product_passports'
    __table_args__ = (UniqueConstraint('passport_code', name='uq_dpp_passport_code'), UniqueConstraint('public_slug', name='uq_dpp_public_slug'), Index('ix_dpp_organization_id', 'organization_id'), Index('ix_dpp_product_id', 'product_id'), Index('ix_dpp_product_batch_id', 'product_batch_id'), Index('ix_dpp_public_slug', 'public_slug'), Index('ix_dpp_passport_code', 'passport_code'), Index('ix_dpp_status', 'status'), Index('ix_dpp_published_at', 'published_at'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True)
    product_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_batches.id', ondelete='SET NULL'), nullable=True)
    product_carbon_footprint_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_carbon_footprints.id', ondelete='SET NULL'), nullable=True)
    passport_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, default='en')
    public_slug: Mapped[str] = mapped_column(String(128), nullable=False)
    qr_code_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    supersedes_passport_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('digital_product_passports.id', ondelete='SET NULL'), nullable=True)

class DigitalProductPassportSection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'digital_product_passport_sections'
    __table_args__ = (UniqueConstraint('passport_id', 'section_code', name='uq_dpp_section_code'), Index('ix_dpp_sections_passport_id', 'passport_id'))
    passport_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('digital_product_passports.id', ondelete='CASCADE'), nullable=False)
    section_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False, default='structured')
    structured_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class PassportDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'passport_documents'
    __table_args__ = (Index('ix_passport_documents_organization_id', 'organization_id'), Index('ix_passport_documents_passport_id', 'passport_id'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    passport_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('digital_product_passports.id', ondelete='CASCADE'), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
