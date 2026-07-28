from __future__ import annotations
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationAppError
from ecotrace.core.lca_constants import ALLOCATION_METHODS, CRADLE_TO_GATE_STAGES, DISCLAIMER, INPUT_TYPES, LCA_METHODOLOGY_VERSION, LCA_STUDY_TRANSITIONS, LCA_STUDY_TYPES, LIFECYCLE_STAGES, SOURCE_TYPES
from ecotrace.modules.facilities.application.facility_service import get_facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.lifecycle_assessment.application.calculation_engine import run_lca_calculation, validate_study_completeness
from ecotrace.modules.lifecycle_assessment.infrastructure.models import LcaCalculationItem, LcaCalculationRun, LcaDataQualityAssessment, LcaFunctionalUnit, LcaInventoryInput, LcaStudy, LcaSystemBoundary
from ecotrace.modules.materials.application.material_service import get_material
from ecotrace.modules.products.application.product_service import get_batch, get_product, get_variant
from ecotrace.modules.products.application.validators import require_allocation_factor, require_dq_score, require_non_negative, require_percentage, require_positive
from ecotrace.modules.reference_data.application.unit_conversion import get_unit
from ecotrace.modules.reference_data.infrastructure.models import ActivityType
from ecotrace.modules.suppliers.application.supplier_service import get_supplier
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_product_approve, require_product_write
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class StudyCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    product_id: uuid.UUID
    product_variant_id: uuid.UUID | None = None
    product_batch_id: uuid.UUID | None = None
    study_type: str
    goal: str | None = None
    intended_application: str | None = None
    audience: str | None = None
    reference_year: int | None = None

class StudyUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    goal: str | None = None
    intended_application: str | None = None
    audience: str | None = None
    reference_year: int | None = None
    product_variant_id: uuid.UUID | None = None
    product_batch_id: uuid.UUID | None = None

class StudyResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str | None
    product_id: uuid.UUID
    product_variant_id: uuid.UUID | None
    product_batch_id: uuid.UUID | None
    study_type: str
    goal: str | None
    intended_application: str | None
    audience: str | None
    status: str
    methodology_version: str
    reference_year: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_by_user_id: uuid.UUID | None
    reviewed_by_user_id: uuid.UUID | None
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    latest_run_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    disclaimer: str = DISCLAIMER

class FunctionalUnitUpsert(CamelModel):
    description: str
    quantity: Decimal
    unit_code: str
    reference_flow_description: str | None = None
    normalization_basis: str | None = None

class FunctionalUnitResponse(CamelModel):
    id: uuid.UUID
    lca_study_id: uuid.UUID
    description: str
    quantity: Decimal
    unit_code: str
    reference_flow_description: str | None
    normalization_basis: str | None
    is_primary: bool
    created_at: datetime
    updated_at: datetime

class BoundaryUpsert(CamelModel):
    boundary_type: str
    included_stages_json: list[str]
    excluded_processes_json: list[Any] | dict[str, Any] | None = None
    cutoff_criteria: str | None = None
    geographic_scope: str | None = None
    temporal_scope: str | None = None
    technology_scope: str | None = None
    assumptions: str | None = None
    limitations: str | None = None

class BoundaryResponse(CamelModel):
    id: uuid.UUID
    lca_study_id: uuid.UUID
    boundary_type: str
    included_stages_json: list[Any]
    excluded_processes_json: list[Any] | dict[str, Any] | None
    cutoff_criteria: str | None
    geographic_scope: str | None
    temporal_scope: str | None
    technology_scope: str | None
    assumptions: str | None
    limitations: str | None
    created_at: datetime
    updated_at: datetime

class InventoryCreate(CamelModel):
    lifecycle_stage: str
    input_type: str
    material_id: uuid.UUID | None = None
    component_product_id: uuid.UUID | None = None
    activity_type_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    description: str | None = None
    quantity: Decimal
    unit_code: str
    source_type: str
    source_reference: str | None = None
    data_quality_score: int | None = None
    uncertainty_percentage: Decimal | None = None
    allocation_method: str = 'none'
    allocation_factor: Decimal = Decimal('1')
    geography_code: str | None = None
    valid_from: Any | None = None
    valid_to: Any | None = None
    metadata_json: dict[str, Any] | None = None

class InventoryResponse(CamelModel):
    id: uuid.UUID
    lca_study_id: uuid.UUID
    lifecycle_stage: str
    input_type: str
    material_id: uuid.UUID | None
    component_product_id: uuid.UUID | None
    activity_type_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    supplier_id: uuid.UUID | None
    description: str | None
    quantity: Decimal
    unit_code: str
    source_type: str
    source_reference: str | None
    data_quality_score: int | None
    uncertainty_percentage: Decimal | None
    allocation_method: str
    allocation_factor: Decimal
    geography_code: str | None
    valid_from: Any | None
    valid_to: Any | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

class DataQualityCreate(CamelModel):
    inventory_input_id: uuid.UUID | None = None
    temporal_score: int
    geographic_score: int
    technological_score: int
    completeness_score: int
    reliability_score: int
    assessment_notes: str | None = None

class DataQualityResponse(CamelModel):
    id: uuid.UUID
    lca_study_id: uuid.UUID
    inventory_input_id: uuid.UUID | None
    temporal_score: int
    geographic_score: int
    technological_score: int
    completeness_score: int
    reliability_score: int
    overall_score: Decimal
    assessment_notes: str | None
    assessed_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

class RunResponse(CamelModel):
    id: uuid.UUID
    lca_study_id: uuid.UUID
    run_number: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    triggered_by_user_id: uuid.UUID | None
    inventory_input_count: int
    calculated_input_count: int
    skipped_input_count: int
    failed_input_count: int
    total_kg_co2e: Decimal | None
    functional_unit_kg_co2e: Decimal | None
    engine_version: str
    methodology_version: str
    result_summary_json: dict[str, Any] | None
    error_summary_json: dict[str, Any] | list[Any] | None
    created_at: datetime
    disclaimer: str = DISCLAIMER

class ItemResponse(CamelModel):
    id: uuid.UUID
    calculation_run_id: uuid.UUID
    lca_study_id: uuid.UUID
    inventory_input_id: uuid.UUID
    lifecycle_stage: str
    material_id: uuid.UUID | None
    supplier_id: uuid.UUID | None
    activity_type_id: uuid.UUID | None
    emission_factor_id: uuid.UUID | None
    total_kg_co2e: Decimal | None
    functional_unit_kg_co2e: Decimal | None
    status: str
    matching_reason: str | None
    calculation_formula: str | None
    validation_errors_json: list[Any] | dict[str, Any] | None

def get_study(db: Session, organization_id: uuid.UUID, study_id: uuid.UUID) -> LcaStudy:
    row = db.get(LcaStudy, study_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('LCA study not found.')
    return row

def _assert_editable(study: LcaStudy) -> None:
    if study.status == 'approved':
        raise BusinessRuleError('Approved studies are immutable.')

def _stages_for_type(study_type: str) -> frozenset[str]:
    if study_type == 'cradle_to_gate':
        return CRADLE_TO_GATE_STAGES
    if study_type == 'gate_to_gate':
        return frozenset({'manufacturing', 'packaging'})
    return LIFECYCLE_STAGES

def list_studies(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, search: str | None=None, status: str | None=None, study_type: str | None=None, product_id: uuid.UUID | None=None) -> Page[StudyResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(LcaStudy).where(LcaStudy.organization_id == organization_id)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(or_(LcaStudy.name.ilike(like), LcaStudy.code.ilike(like)))
    if status:
        stmt = stmt.where(LcaStudy.status == status)
    if study_type:
        stmt = stmt.where(LcaStudy.study_type == study_type)
    if product_id:
        stmt = stmt.where(LcaStudy.product_id == product_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(LcaStudy.code.asc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([StudyResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def create_study(db: Session, user: User, organization_id: uuid.UUID, payload: StudyCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> StudyResponse:
    require_product_write(db, user, organization_id)
    if payload.study_type not in LCA_STUDY_TYPES:
        raise ValidationAppError('Invalid study type.')
    get_product(db, organization_id, payload.product_id)
    if payload.product_variant_id:
        v = get_variant(db, organization_id, payload.product_variant_id)
        if v.product_id != payload.product_id:
            raise ValidationAppError('Variant does not belong to product.')
    if payload.product_batch_id:
        b = get_batch(db, organization_id, payload.product_batch_id)
        if b.product_id != payload.product_id:
            raise ValidationAppError('Batch does not belong to product.')
    code = payload.code.strip()
    if db.execute(select(LcaStudy.id).where(LcaStudy.organization_id == organization_id, LcaStudy.code == code)).scalar_one_or_none():
        raise ConflictError('Study code already exists.')
    row = LcaStudy(organization_id=organization_id, code=code, name=payload.name.strip(), description=payload.description, product_id=payload.product_id, product_variant_id=payload.product_variant_id, product_batch_id=payload.product_batch_id, study_type=payload.study_type, goal=payload.goal, intended_application=payload.intended_application, audience=payload.audience, status='draft', methodology_version=LCA_METHODOLOGY_VERSION, reference_year=payload.reference_year, started_at=datetime.now(UTC), created_by_user_id=user.id)
    db.add(row)
    db.flush()
    write_audit_log(db, action='lca_study.created', actor_user_id=user.id, organization_id=organization_id, entity_type='lca_study', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': code})
    db.commit()
    db.refresh(row)
    return StudyResponse.model_validate(row)

def update_study(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, payload: StudyUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> StudyResponse:
    require_product_write(db, user, organization_id)
    row = get_study(db, organization_id, study_id)
    _assert_editable(row)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(db, action='lca_study.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='lca_study', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return StudyResponse.model_validate(row)

def get_study_detail(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID) -> StudyResponse:
    ensure_org_access(db, user, organization_id)
    return StudyResponse.model_validate(get_study(db, organization_id, study_id))

def upsert_functional_unit(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, payload: FunctionalUnitUpsert, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FunctionalUnitResponse:
    require_product_write(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    _assert_editable(study)
    require_positive(payload.quantity, 'quantity')
    get_unit(db, payload.unit_code)
    existing = db.execute(select(LcaFunctionalUnit).where(LcaFunctionalUnit.lca_study_id == study.id, LcaFunctionalUnit.is_primary.is_(True))).scalar_one_or_none()
    if existing and study.status in {'calculated', 'under_review'}:
        study.status = 'data_collection'
    if existing:
        existing.description = payload.description
        existing.quantity = payload.quantity
        existing.unit_code = payload.unit_code
        existing.reference_flow_description = payload.reference_flow_description
        existing.normalization_basis = payload.normalization_basis
        row = existing
    else:
        row = LcaFunctionalUnit(lca_study_id=study.id, description=payload.description, quantity=payload.quantity, unit_code=payload.unit_code, reference_flow_description=payload.reference_flow_description, normalization_basis=payload.normalization_basis, is_primary=True)
        db.add(row)
    write_audit_log(db, action='lca_study.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='lca_functional_unit', entity_id=str(study.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return FunctionalUnitResponse.model_validate(row)

def upsert_boundary(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, payload: BoundaryUpsert, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BoundaryResponse:
    require_product_write(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    _assert_editable(study)
    allowed = _stages_for_type(study.study_type)
    for stage in payload.included_stages_json:
        if stage not in LIFECYCLE_STAGES:
            raise ValidationAppError(f'Unknown lifecycle stage: {stage}')
        if stage not in allowed and study.study_type == 'cradle_to_gate':
            raise ValidationAppError(f"Stage '{stage}' is not compatible with cradle_to_gate study type.")
    excluded = payload.excluded_processes_json
    if excluded:
        if isinstance(excluded, list):
            for item in excluded:
                if isinstance(item, dict) and (not item.get('reason')):
                    raise ValidationAppError('Excluded processes must include a reason.')
        elif isinstance(excluded, dict) and (not excluded.get('reason')):
            raise ValidationAppError('Excluded processes must include a reason.')
    existing = db.execute(select(LcaSystemBoundary).where(LcaSystemBoundary.lca_study_id == study.id)).scalar_one_or_none()
    if existing:
        for field in ('boundary_type', 'included_stages_json', 'excluded_processes_json', 'cutoff_criteria', 'geographic_scope', 'temporal_scope', 'technology_scope', 'assumptions', 'limitations'):
            setattr(existing, field, getattr(payload, field))
        row = existing
    else:
        row = LcaSystemBoundary(lca_study_id=study.id, **payload.model_dump())
        db.add(row)
    write_audit_log(db, action='lca_study.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='lca_system_boundary', entity_id=str(study.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'boundaryType': payload.boundary_type})
    db.commit()
    db.refresh(row)
    return BoundaryResponse.model_validate(row)

def _validate_inventory(db: Session, organization_id: uuid.UUID, study: LcaStudy, payload: InventoryCreate) -> None:
    if payload.lifecycle_stage not in LIFECYCLE_STAGES:
        raise ValidationAppError('Invalid lifecycle stage.')
    if payload.input_type not in INPUT_TYPES:
        raise ValidationAppError('Invalid input type.')
    if payload.source_type not in SOURCE_TYPES:
        raise ValidationAppError('Invalid source type.')
    if payload.allocation_method not in ALLOCATION_METHODS:
        raise ValidationAppError('Invalid allocation method.')
    require_non_negative(payload.quantity, 'quantity')
    get_unit(db, payload.unit_code)
    require_allocation_factor(payload.allocation_factor)
    require_percentage(payload.uncertainty_percentage, 'uncertaintyPercentage')
    if payload.data_quality_score is not None:
        require_dq_score(payload.data_quality_score, 'dataQualityScore')
    if payload.source_type in {'supplier_specific', 'database'} and (not payload.source_reference):
        raise ValidationAppError('Source reference is required for this source type.')
    if payload.allocation_method == 'custom':
        reason = (payload.metadata_json or {}).get('allocationReason')
        if not reason:
            raise ValidationAppError('Custom allocation requires allocationReason in metadata.')
    if payload.allocation_method == 'economic' and (not (payload.metadata_json or {}).get('currency')):
        raise ValidationAppError('Economic allocation requires currency in metadata.')
    if payload.material_id:
        get_material(db, organization_id, payload.material_id)
    if payload.component_product_id:
        get_product(db, organization_id, payload.component_product_id)
    if payload.supplier_id:
        get_supplier(db, organization_id, payload.supplier_id)
    if payload.facility_id:
        get_facility(db, organization_id, payload.facility_id)
    if payload.activity_type_id:
        at = db.get(ActivityType, payload.activity_type_id)
        if at is None or not at.is_active:
            raise NotFoundError('Activity type not found.')

def list_inventory(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, *, page: int, page_size: int, lifecycle_stage: str | None=None) -> Page[InventoryResponse]:
    ensure_org_access(db, user, organization_id)
    get_study(db, organization_id, study_id)
    stmt = select(LcaInventoryInput).where(LcaInventoryInput.lca_study_id == study_id)
    if lifecycle_stage:
        stmt = stmt.where(LcaInventoryInput.lifecycle_stage == lifecycle_stage)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(LcaInventoryInput.created_at.asc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([InventoryResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def add_inventory(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, payload: InventoryCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> InventoryResponse:
    require_product_write(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    _assert_editable(study)
    _validate_inventory(db, organization_id, study, payload)
    dup = db.execute(select(LcaInventoryInput.id).where(LcaInventoryInput.lca_study_id == study.id, LcaInventoryInput.lifecycle_stage == payload.lifecycle_stage, LcaInventoryInput.input_type == payload.input_type, LcaInventoryInput.material_id == payload.material_id, LcaInventoryInput.activity_type_id == payload.activity_type_id, LcaInventoryInput.supplier_id == payload.supplier_id, LcaInventoryInput.description == payload.description, LcaInventoryInput.unit_code == payload.unit_code, LcaInventoryInput.source_type == payload.source_type, LcaInventoryInput.source_reference == payload.source_reference)).scalar_one_or_none()
    if dup:
        raise ConflictError('Duplicate inventory line for the same source and stage.')
    row = LcaInventoryInput(lca_study_id=study.id, **payload.model_dump())
    db.add(row)
    if study.status == 'draft':
        study.status = 'data_collection'
    write_audit_log(db, action='lca_study.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='lca_inventory_input', entity_id=str(study.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return InventoryResponse.model_validate(row)

def validate_study(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> dict[str, Any]:
    require_product_write(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    result = validate_study_completeness(db, study)
    if result['valid'] and study.status in {'draft', 'data_collection'}:
        study.status = 'ready_for_calculation'
    write_audit_log(db, action='lca_study.validated', actor_user_id=user.id, organization_id=organization_id, entity_type='lca_study', entity_id=str(study.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'blockingErrorCount': result['blockingErrorCount']})
    db.commit()
    return result

def calculate_study(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None, partial: bool=False) -> RunResponse:
    require_product_write(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    _assert_editable(study)
    run = run_lca_calculation(db, user, study, request_id=request_id, ip_address=ip_address, user_agent=user_agent, partial=partial)
    db.commit()
    db.refresh(run)
    return RunResponse.model_validate(run)

def recalculate_study(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> RunResponse:
    require_product_write(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    if study.status == 'approved':
        study.status = 'ready_for_calculation'
        study.approved_at = None
        study.approved_by_user_id = None
    return calculate_study(db, user, organization_id, study_id, request_id=request_id, ip_address=ip_address, user_agent=user_agent)

def submit_study_review(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> StudyResponse:
    require_product_write(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    if 'under_review' not in LCA_STUDY_TRANSITIONS.get(study.status, frozenset()):
        raise BusinessRuleError(f"Cannot submit study from status '{study.status}'.")
    study.status = 'under_review'
    study.reviewed_by_user_id = user.id
    write_audit_log(db, action='lca_study.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='lca_study', entity_id=str(study.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'status': 'under_review'})
    db.commit()
    db.refresh(study)
    return StudyResponse.model_validate(study)

def approve_study(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> StudyResponse:
    require_product_approve(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    if study.status not in {'calculated', 'under_review'}:
        raise BusinessRuleError('Study must be calculated before approval.')
    study.status = 'approved'
    study.approved_by_user_id = user.id
    study.approved_at = datetime.now(UTC)
    study.completed_at = datetime.now(UTC)
    write_audit_log(db, action='lca_study.approved', actor_user_id=user.id, organization_id=organization_id, entity_type='lca_study', entity_id=str(study.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(study)
    return StudyResponse.model_validate(study)

def list_runs(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID) -> list[RunResponse]:
    ensure_org_access(db, user, organization_id)
    get_study(db, organization_id, study_id)
    rows = list(db.execute(select(LcaCalculationRun).where(LcaCalculationRun.lca_study_id == study_id).order_by(LcaCalculationRun.run_number.desc())).scalars().all())
    return [RunResponse.model_validate(r) for r in rows]

def get_results(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID) -> dict[str, Any]:
    ensure_org_access(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    if not study.latest_run_id:
        raise NotFoundError('No calculation results available.')
    run = db.get(LcaCalculationRun, study.latest_run_id)
    if run is None:
        raise NotFoundError('Calculation run not found.')
    items = list(db.execute(select(LcaCalculationItem).where(LcaCalculationItem.calculation_run_id == run.id).order_by(LcaCalculationItem.total_kg_co2e.desc().nullslast()).limit(50)).scalars().all())
    return {'run': RunResponse.model_validate(run).model_dump(by_alias=True), 'topItems': [ItemResponse.model_validate(i).model_dump(by_alias=True) for i in items], 'disclaimer': DISCLAIMER}

def create_data_quality(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID, payload: DataQualityCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> DataQualityResponse:
    require_product_write(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    _assert_editable(study)
    for field, value in (('temporalScore', payload.temporal_score), ('geographicScore', payload.geographic_score), ('technologicalScore', payload.technological_score), ('completenessScore', payload.completeness_score), ('reliabilityScore', payload.reliability_score)):
        require_dq_score(value, field)
    if payload.inventory_input_id:
        inp = db.get(LcaInventoryInput, payload.inventory_input_id)
        if inp is None or inp.lca_study_id != study.id:
            raise NotFoundError('Inventory input not found.')
    overall = (Decimal(payload.temporal_score) + Decimal(payload.geographic_score) + Decimal(payload.technological_score) + Decimal(payload.completeness_score) + Decimal(payload.reliability_score)) / Decimal('5')
    row = LcaDataQualityAssessment(lca_study_id=study.id, inventory_input_id=payload.inventory_input_id, temporal_score=payload.temporal_score, geographic_score=payload.geographic_score, technological_score=payload.technological_score, completeness_score=payload.completeness_score, reliability_score=payload.reliability_score, overall_score=overall.quantize(Decimal('0.0001')), assessment_notes=payload.assessment_notes, assessed_by_user_id=user.id)
    db.add(row)
    write_audit_log(db, action='lca_study.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='lca_data_quality_assessment', entity_id=str(study.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return DataQualityResponse.model_validate(row)

def get_study_scope(db: Session, user: User, organization_id: uuid.UUID, study_id: uuid.UUID) -> dict[str, Any]:
    ensure_org_access(db, user, organization_id)
    study = get_study(db, organization_id, study_id)
    fu = db.execute(select(LcaFunctionalUnit).where(LcaFunctionalUnit.lca_study_id == study.id)).scalar_one_or_none()
    boundary = db.execute(select(LcaSystemBoundary).where(LcaSystemBoundary.lca_study_id == study.id)).scalar_one_or_none()
    return {'study': StudyResponse.model_validate(study).model_dump(by_alias=True), 'functionalUnit': FunctionalUnitResponse.model_validate(fu).model_dump(by_alias=True) if fu else None, 'systemBoundary': BoundaryResponse.model_validate(boundary).model_dump(by_alias=True) if boundary else None, 'disclaimer': DISCLAIMER}
