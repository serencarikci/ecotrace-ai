from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class ProductCarbonFootprint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'product_carbon_footprints'
    __table_args__ = (Index('ix_pcf_organization_id', 'organization_id'), Index('ix_pcf_product_id', 'product_id'), Index('ix_pcf_product_variant_id', 'product_variant_id'), Index('ix_pcf_product_batch_id', 'product_batch_id'), Index('ix_pcf_status', 'status'), UniqueConstraint('organization_id', 'product_id', 'lca_study_id', 'calculation_run_id', name='uq_pcf_study_run'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    lca_study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_studies.id', ondelete='RESTRICT'), nullable=False)
    calculation_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_calculation_runs.id', ondelete='RESTRICT'), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True)
    product_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_batches.id', ondelete='SET NULL'), nullable=True)
    functional_unit_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    functional_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    total_kg_co2e: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    cradle_to_gate_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    use_phase_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    end_of_life_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    biogenic_co2_kg: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='calculated')
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
