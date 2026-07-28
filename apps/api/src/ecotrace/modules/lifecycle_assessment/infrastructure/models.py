from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class LcaStudy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'lca_studies'
    __table_args__ = (UniqueConstraint('organization_id', 'code', name='uq_lca_studies_org_code'), Index('ix_lca_studies_organization_id', 'organization_id'), Index('ix_lca_studies_product_id', 'product_id'), Index('ix_lca_studies_product_variant_id', 'product_variant_id'), Index('ix_lca_studies_product_batch_id', 'product_batch_id'), Index('ix_lca_studies_status', 'status'), Index('ix_lca_studies_study_type', 'study_type'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True)
    product_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('product_batches.id', ondelete='SET NULL'), nullable=True)
    study_type: Mapped[str] = mapped_column(String(64), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    intended_application: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    methodology_version: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

class LcaFunctionalUnit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'lca_functional_units'
    __table_args__ = (Index('ix_lca_functional_units_lca_study_id', 'lca_study_id'),)
    lca_study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_studies.id', ondelete='CASCADE'), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_flow_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalization_basis: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class LcaSystemBoundary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'lca_system_boundaries'
    __table_args__ = (Index('ix_lca_system_boundaries_lca_study_id', 'lca_study_id'),)
    lca_study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_studies.id', ondelete='CASCADE'), nullable=False)
    boundary_type: Mapped[str] = mapped_column(String(64), nullable=False)
    included_stages_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    excluded_processes_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    cutoff_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    geographic_scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    temporal_scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    technology_scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assumptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)

class LcaInventoryInput(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'lca_inventory_inputs'
    __table_args__ = (Index('ix_lca_inventory_inputs_lca_study_id', 'lca_study_id'), Index('ix_lca_inventory_inputs_lifecycle_stage', 'lifecycle_stage'), Index('ix_lca_inventory_inputs_input_type', 'input_type'), Index('ix_lca_inventory_inputs_material_id', 'material_id'), Index('ix_lca_inventory_inputs_supplier_id', 'supplier_id'), Index('ix_lca_inventory_inputs_activity_type_id', 'activity_type_id'))
    lca_study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_studies.id', ondelete='CASCADE'), nullable=False)
    lifecycle_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    input_type: Mapped[str] = mapped_column(String(64), nullable=False)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('materials.id', ondelete='SET NULL'), nullable=True)
    component_product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='SET NULL'), nullable=True)
    activity_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('activity_types.id', ondelete='SET NULL'), nullable=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('facilities.id', ondelete='SET NULL'), nullable=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uncertainty_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    allocation_method: Mapped[str] = mapped_column(String(32), nullable=False, default='none')
    allocation_factor: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False, default=Decimal('1'))
    geography_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class LcaCalculationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'lca_calculation_runs'
    __table_args__ = (UniqueConstraint('lca_study_id', 'run_number', name='uq_lca_run_number'), Index('ix_lca_calculation_runs_lca_study_id', 'lca_study_id'), Index('ix_lca_calculation_runs_status', 'status'), Index('ix_lca_calculation_runs_created_at', 'created_at'))
    lca_study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_studies.id', ondelete='CASCADE'), nullable=False)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='queued')
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    inventory_input_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calculated_input_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_input_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_input_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    functional_unit_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(64), nullable=False)
    result_summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_summary_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)

class LcaCalculationItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'lca_calculation_items'
    __table_args__ = (Index('ix_lca_calculation_items_calculation_run_id', 'calculation_run_id'), Index('ix_lca_calculation_items_lifecycle_stage', 'lifecycle_stage'), Index('ix_lca_calculation_items_material_id', 'material_id'), Index('ix_lca_calculation_items_supplier_id', 'supplier_id'), Index('ix_lca_calculation_items_activity_type_id', 'activity_type_id'))
    calculation_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_calculation_runs.id', ondelete='CASCADE'), nullable=False)
    lca_study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_studies.id', ondelete='CASCADE'), nullable=False)
    inventory_input_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_inventory_inputs.id', ondelete='RESTRICT'), nullable=False)
    lifecycle_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    activity_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    emission_factor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('emission_factors.id', ondelete='SET NULL'), nullable=True)
    factor_source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('emission_factor_sources.id', ondelete='SET NULL'), nullable=True)
    input_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    input_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    normalized_unit_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    factor_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    factor_unit_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    allocation_factor: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False, default=Decimal('1'))
    allocated_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    total_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    functional_unit_kg_co2e: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    matching_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matching_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation_formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='failed')
    validation_errors_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class LcaDataQualityAssessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'lca_data_quality_assessments'
    __table_args__ = (Index('ix_lca_dq_lca_study_id', 'lca_study_id'), Index('ix_lca_dq_inventory_input_id', 'inventory_input_id'))
    lca_study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_studies.id', ondelete='CASCADE'), nullable=False)
    inventory_input_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('lca_inventory_inputs.id', ondelete='CASCADE'), nullable=True)
    temporal_score: Mapped[int] = mapped_column(Integer, nullable=False)
    geographic_score: Mapped[int] = mapped_column(Integer, nullable=False)
    technological_score: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    reliability_score: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    assessment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
