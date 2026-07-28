from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'products'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_products_org_code'), Index('ix_products_organization_id', 'organization_id'), Index('ix_products_sku', 'sku'), Index('ix_products_gtin', 'gtin'), Index('ix_products_product_type', 'product_type'), Index('ix_products_product_category', 'product_category'), Index('ix_products_is_active', 'is_active'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_type: Mapped[str] = mapped_column(String(64), nullable=False)
    product_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gtin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(2), nullable=True)
    default_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    weight_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    weight_unit_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expected_lifetime_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    expected_lifetime_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recyclability_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    recycled_content_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    repairability_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class ProductVariant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'product_variants'
    __table_args__ = (UniqueConstraint('product_id', 'code', name='uq_product_variants_product_code'), Index('ix_product_variants_organization_id', 'organization_id'), Index('ix_product_variants_product_id', 'product_id'), Index('ix_product_variants_sku', 'sku'), Index('ix_product_variants_gtin', 'gtin'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gtin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    weight_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    weight_unit_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class ProductBatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'product_batches'
    __table_args__ = (UniqueConstraint('organization_id', 'batch_code', name='uq_product_batches_org_code'), Index('ix_product_batches_organization_id', 'organization_id'), Index('ix_product_batches_product_id', 'product_id'), Index('ix_product_batches_facility_id', 'facility_id'), Index('ix_product_batches_production_date', 'production_date'), Index('ix_product_batches_status', 'status'), Index('ix_product_batches_batch_code', 'batch_code'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('facilities.id', ondelete='SET NULL'), nullable=True)
    production_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('production_lines.id', ondelete='SET NULL'), nullable=True)
    batch_code: Mapped[str] = mapped_column(String(64), nullable=False)
    production_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    total_weight: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    weight_unit_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='planned')
    traceability_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class BillOfMaterials(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'bills_of_materials'
    __table_args__ = (UniqueConstraint('product_id', 'version', name='uq_bom_product_version'), Index('ix_bills_of_materials_organization_id', 'organization_id'), Index('ix_bills_of_materials_product_id', 'product_id'), Index('ix_bills_of_materials_status', 'status'), Index('ix_bills_of_materials_valid_from', 'valid_from'), Index('ix_bills_of_materials_valid_to', 'valid_to'), Index('ix_bills_of_materials_version', 'version'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class BillOfMaterialItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'bill_of_material_items'
    __table_args__ = (Index('ix_bom_items_bill_of_material_id', 'bill_of_material_id'), Index('ix_bom_items_material_id', 'material_id'), Index('ix_bom_items_component_product_id', 'component_product_id'))
    bill_of_material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('bills_of_materials.id', ondelete='CASCADE'), nullable=False)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('materials.id', ondelete='RESTRICT'), nullable=True)
    component_product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='RESTRICT'), nullable=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    waste_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    recycled_content_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    source_country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    transport_distance_km: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    transport_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    allocation_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class ProductSustainabilityIndicator(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'product_sustainability_indicators'
    __table_args__ = (Index('ix_product_indicators_organization_id', 'organization_id'), Index('ix_product_indicators_product_id', 'product_id'), Index('ix_product_indicators_indicator_code', 'indicator_code'), Index('ix_product_indicators_status', 'status'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True)
    product_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_batches.id', ondelete='SET NULL'), nullable=True)
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='active')
