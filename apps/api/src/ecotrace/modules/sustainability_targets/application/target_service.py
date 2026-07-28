from __future__ import annotations
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.analytics_constants import BASELINE_STATUSES, INITIATIVE_STATUSES, INITIATIVE_TRANSITIONS, INITIATIVE_TYPES, KPI_TYPES, NUMERATOR_TYPES, TARGET_DIRECTIONS, TARGET_TYPES
from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.modules.analytics.application.query_service import aggregate_items, compute_target_progress, resolve_inventory
from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonCalculationItem
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.sustainability_targets.infrastructure.models import EnvironmentalKpiDefinition, IntensityMetricDefinition, ReductionInitiative, SustainabilityBaseline, SustainabilityTarget, SustainabilityTargetRevision
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_org_read, require_planning_manage, require_planning_write
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class IntensityDefCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    numerator_type: str
    denominator_activity_type_id: uuid.UUID | None = None
    denominator_unit_code: str
    display_unit: str
    aggregation_method: str = 'sum'
    is_active: bool = True

class IntensityDefUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    numerator_type: str | None = None
    denominator_activity_type_id: uuid.UUID | None = None
    denominator_unit_code: str | None = None
    display_unit: str | None = None
    aggregation_method: str | None = None
    is_active: bool | None = None

class IntensityDefResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str | None
    numerator_type: str
    denominator_activity_type_id: uuid.UUID | None
    denominator_unit_code: str
    display_unit: str
    aggregation_method: str
    is_active: bool

class KpiDefCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    kpi_type: str
    activity_type_id: uuid.UUID | None = None
    aggregation_method: str = 'sum'
    unit_code: str
    target_direction: str = 'decrease'
    is_active: bool = True

class KpiDefUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    kpi_type: str | None = None
    activity_type_id: uuid.UUID | None = None
    aggregation_method: str | None = None
    unit_code: str | None = None
    target_direction: str | None = None
    is_active: bool | None = None

class KpiDefResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str | None
    kpi_type: str
    activity_type_id: uuid.UUID | None
    aggregation_method: str
    unit_code: str
    target_direction: str
    is_active: bool

class BaselineCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    baseline_type: str
    reporting_period_id: uuid.UUID | None = None
    inventory_id: uuid.UUID | None = None
    baseline_year: int | None = None
    baseline_value: Decimal | None = None
    baseline_unit: str | None = None
    is_primary: bool = False

class BaselineUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    reporting_period_id: uuid.UUID | None = None
    inventory_id: uuid.UUID | None = None
    baseline_year: int | None = None
    baseline_value: Decimal | None = None
    baseline_unit: str | None = None
    is_primary: bool | None = None

class BaselineResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str | None
    baseline_type: str
    reporting_period_id: uuid.UUID | None
    inventory_id: uuid.UUID | None
    baseline_year: int | None
    baseline_value: Decimal | None
    baseline_unit: str | None
    is_primary: bool
    status: str
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None

class TargetCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    target_type: str
    scope: str | None = None
    category: str | None = None
    facility_id: uuid.UUID | None = None
    baseline_id: uuid.UUID
    baseline_value: Decimal
    target_value: Decimal
    target_unit: str
    target_year: int
    target_date: date | None = None
    target_direction: str = 'decrease'
    owner_user_id: uuid.UUID | None = None

class TargetUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    scope: str | None = None
    category: str | None = None
    facility_id: uuid.UUID | None = None
    baseline_value: Decimal | None = None
    target_value: Decimal | None = None
    target_unit: str | None = None
    target_year: int | None = None
    target_date: date | None = None
    target_direction: str | None = None
    owner_user_id: uuid.UUID | None = None

class TargetResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str | None
    target_type: str
    scope: str | None
    category: str | None
    facility_id: uuid.UUID | None
    baseline_id: uuid.UUID
    baseline_value: Decimal
    target_value: Decimal
    target_unit: str
    target_year: int
    target_date: date | None
    target_direction: str
    status: str
    owner_user_id: uuid.UUID | None
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    revision: int

class InitiativeCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    initiative_type: str
    target_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    activity_type_id: uuid.UUID | None = None
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    expected_reduction_kg_co2e: Decimal = Decimal('0')
    expected_cost: Decimal | None = None
    currency_code: str | None = None
    owner_user_id: uuid.UUID | None = None

class InitiativeUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    target_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    activity_type_id: uuid.UUID | None = None
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    actual_start_date: date | None = None
    actual_end_date: date | None = None
    expected_reduction_kg_co2e: Decimal | None = None
    actual_reduction_kg_co2e: Decimal | None = None
    expected_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    currency_code: str | None = None
    owner_user_id: uuid.UUID | None = None

class InitiativeTransition(CamelModel):
    status: str

class InitiativeResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    target_id: uuid.UUID | None
    code: str
    name: str
    description: str | None
    initiative_type: str
    facility_id: uuid.UUID | None
    activity_type_id: uuid.UUID | None
    planned_start_date: date | None
    planned_end_date: date | None
    actual_start_date: date | None
    actual_end_date: date | None
    expected_reduction_kg_co2e: Decimal
    actual_reduction_kg_co2e: Decimal | None
    expected_cost: Decimal | None
    actual_cost: Decimal | None
    currency_code: str | None
    status: str
    owner_user_id: uuid.UUID | None

def _intensity_response(row: IntensityMetricDefinition) -> IntensityDefResponse:
    return IntensityDefResponse.model_validate(row)

def _kpi_response(row: EnvironmentalKpiDefinition) -> KpiDefResponse:
    return KpiDefResponse.model_validate(row)

def _baseline_response(row: SustainabilityBaseline) -> BaselineResponse:
    return BaselineResponse.model_validate(row)

def _target_response(row: SustainabilityTarget) -> TargetResponse:
    return TargetResponse.model_validate(row)

def _initiative_response(row: ReductionInitiative) -> InitiativeResponse:
    return InitiativeResponse.model_validate(row)

def _clear_primary(db: Session, organization_id: uuid.UUID, baseline_type: str) -> None:
    rows = db.execute(select(SustainabilityBaseline).where(SustainabilityBaseline.organization_id == organization_id, SustainabilityBaseline.baseline_type == baseline_type, SustainabilityBaseline.is_primary.is_(True))).scalars().all()
    for row in rows:
        row.is_primary = False

def list_intensity_defs(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int) -> Page[IntensityDefResponse]:
    require_org_read(db, user, organization_id)
    total = db.execute(select(func.count()).select_from(IntensityMetricDefinition).where(IntensityMetricDefinition.organization_id == organization_id)).scalar_one()
    rows = db.execute(select(IntensityMetricDefinition).where(IntensityMetricDefinition.organization_id == organization_id).order_by(IntensityMetricDefinition.code).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_intensity_response(r) for r in rows], page=page, page_size=page_size, total_items=total)

def create_intensity_def(db: Session, user: User, organization_id: uuid.UUID, payload: IntensityDefCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> IntensityDefResponse:
    require_planning_write(db, user, organization_id)
    if payload.numerator_type not in NUMERATOR_TYPES:
        raise ValidationAppError('Invalid numerator type.')
    existing = db.execute(select(IntensityMetricDefinition).where(IntensityMetricDefinition.organization_id == organization_id, IntensityMetricDefinition.code == payload.code.strip())).scalar_one_or_none()
    if existing:
        raise ConflictError('Intensity metric code already exists.')
    row = IntensityMetricDefinition(organization_id=organization_id, code=payload.code.strip(), name=payload.name.strip(), description=payload.description, numerator_type=payload.numerator_type, denominator_activity_type_id=payload.denominator_activity_type_id, denominator_unit_code=payload.denominator_unit_code, display_unit=payload.display_unit, aggregation_method=payload.aggregation_method, is_active=payload.is_active)
    db.add(row)
    db.flush()
    write_audit_log(db, action='intensity_metric.created', actor_user_id=user.id, organization_id=organization_id, entity_type='intensity_metric_definition', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    return _intensity_response(row)

def update_intensity_def(db: Session, user: User, organization_id: uuid.UUID, definition_id: uuid.UUID, payload: IntensityDefUpdate) -> IntensityDefResponse:
    require_planning_write(db, user, organization_id)
    row = db.get(IntensityMetricDefinition, definition_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Intensity metric definition not found.')
    data = payload.model_dump(exclude_unset=True)
    if 'numerator_type' in data and data['numerator_type'] not in NUMERATOR_TYPES:
        raise ValidationAppError('Invalid numerator type.')
    for key, value in data.items():
        setattr(row, key, value)
    db.flush()
    return _intensity_response(row)

def list_kpi_defs(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int) -> Page[KpiDefResponse]:
    require_org_read(db, user, organization_id)
    total = db.execute(select(func.count()).select_from(EnvironmentalKpiDefinition).where(EnvironmentalKpiDefinition.organization_id == organization_id)).scalar_one()
    rows = db.execute(select(EnvironmentalKpiDefinition).where(EnvironmentalKpiDefinition.organization_id == organization_id).order_by(EnvironmentalKpiDefinition.code).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_kpi_response(r) for r in rows], page=page, page_size=page_size, total_items=total)

def create_kpi_def(db: Session, user: User, organization_id: uuid.UUID, payload: KpiDefCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> KpiDefResponse:
    require_planning_write(db, user, organization_id)
    if payload.kpi_type not in KPI_TYPES:
        raise ValidationAppError('Invalid KPI type.')
    if payload.target_direction not in TARGET_DIRECTIONS:
        raise ValidationAppError('Invalid target direction.')
    existing = db.execute(select(EnvironmentalKpiDefinition).where(EnvironmentalKpiDefinition.organization_id == organization_id, EnvironmentalKpiDefinition.code == payload.code.strip())).scalar_one_or_none()
    if existing:
        raise ConflictError('KPI definition code already exists.')
    row = EnvironmentalKpiDefinition(organization_id=organization_id, code=payload.code.strip(), name=payload.name.strip(), description=payload.description, kpi_type=payload.kpi_type, activity_type_id=payload.activity_type_id, aggregation_method=payload.aggregation_method, unit_code=payload.unit_code, target_direction=payload.target_direction, is_active=payload.is_active)
    db.add(row)
    db.flush()
    write_audit_log(db, action='environmental_kpi.created', actor_user_id=user.id, organization_id=organization_id, entity_type='environmental_kpi_definition', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    return _kpi_response(row)

def update_kpi_def(db: Session, user: User, organization_id: uuid.UUID, definition_id: uuid.UUID, payload: KpiDefUpdate) -> KpiDefResponse:
    require_planning_write(db, user, organization_id)
    row = db.get(EnvironmentalKpiDefinition, definition_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('KPI definition not found.')
    data = payload.model_dump(exclude_unset=True)
    if 'kpi_type' in data and data['kpi_type'] not in KPI_TYPES:
        raise ValidationAppError('Invalid KPI type.')
    if 'target_direction' in data and data['target_direction'] not in TARGET_DIRECTIONS:
        raise ValidationAppError('Invalid target direction.')
    for key, value in data.items():
        setattr(row, key, value)
    db.flush()
    return _kpi_response(row)

def list_baselines(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, status: str | None=None) -> Page[BaselineResponse]:
    require_org_read(db, user, organization_id)
    stmt = select(SustainabilityBaseline).where(SustainabilityBaseline.organization_id == organization_id)
    count_stmt = select(func.count()).select_from(SustainabilityBaseline).where(SustainabilityBaseline.organization_id == organization_id)
    if status:
        stmt = stmt.where(SustainabilityBaseline.status == status)
        count_stmt = count_stmt.where(SustainabilityBaseline.status == status)
    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(SustainabilityBaseline.code).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_baseline_response(r) for r in rows], page=page, page_size=page_size, total_items=total)

def create_baseline(db: Session, user: User, organization_id: uuid.UUID, payload: BaselineCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BaselineResponse:
    require_planning_write(db, user, organization_id)
    if payload.baseline_type not in {'carbon_inventory', 'intensity', 'environmental_kpi'}:
        raise ValidationAppError('Invalid baseline type.')
    existing = db.execute(select(SustainabilityBaseline).where(SustainabilityBaseline.organization_id == organization_id, SustainabilityBaseline.code == payload.code.strip())).scalar_one_or_none()
    if existing:
        raise ConflictError('Baseline code already exists.')
    if payload.is_primary:
        _clear_primary(db, organization_id, payload.baseline_type)
    row = SustainabilityBaseline(organization_id=organization_id, code=payload.code.strip(), name=payload.name.strip(), description=payload.description, baseline_type=payload.baseline_type, reporting_period_id=payload.reporting_period_id, inventory_id=payload.inventory_id, baseline_year=payload.baseline_year, baseline_value=payload.baseline_value, baseline_unit=payload.baseline_unit, is_primary=payload.is_primary, status='draft')
    db.add(row)
    db.flush()
    write_audit_log(db, action='baseline.created', actor_user_id=user.id, organization_id=organization_id, entity_type='sustainability_baseline', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    return _baseline_response(row)

def get_baseline(db: Session, user: User, organization_id: uuid.UUID, baseline_id: uuid.UUID) -> BaselineResponse:
    require_org_read(db, user, organization_id)
    row = db.get(SustainabilityBaseline, baseline_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Baseline not found.')
    return _baseline_response(row)

def update_baseline(db: Session, user: User, organization_id: uuid.UUID, baseline_id: uuid.UUID, payload: BaselineUpdate) -> BaselineResponse:
    require_planning_write(db, user, organization_id)
    row = db.get(SustainabilityBaseline, baseline_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Baseline not found.')
    if row.status != 'draft':
        raise ValidationAppError('Only draft baselines can be updated.')
    data = payload.model_dump(exclude_unset=True)
    if data.get('is_primary'):
        _clear_primary(db, organization_id, row.baseline_type)
    for key, value in data.items():
        setattr(row, key, value)
    db.flush()
    return _baseline_response(row)

def approve_baseline(db: Session, user: User, organization_id: uuid.UUID, baseline_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BaselineResponse:
    require_planning_manage(db, user, organization_id)
    row = db.get(SustainabilityBaseline, baseline_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Baseline not found.')
    if row.status != 'draft':
        raise ValidationAppError('Only draft baselines can be approved.')
    if row.baseline_value is None:
        raise ValidationAppError('Baseline value is required before approval.')
    row.status = 'approved'
    row.approved_by_user_id = user.id
    row.approved_at = datetime.now(UTC)
    db.flush()
    write_audit_log(db, action='baseline.approved', actor_user_id=user.id, organization_id=organization_id, entity_type='sustainability_baseline', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    return _baseline_response(row)

def archive_baseline(db: Session, user: User, organization_id: uuid.UUID, baseline_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BaselineResponse:
    require_planning_manage(db, user, organization_id)
    row = db.get(SustainabilityBaseline, baseline_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Baseline not found.')
    if row.status not in BASELINE_STATUSES - {'archived'}:
        raise ValidationAppError('Baseline cannot be archived from current status.')
    row.status = 'archived'
    row.is_primary = False
    db.flush()
    write_audit_log(db, action='baseline.archived', actor_user_id=user.id, organization_id=organization_id, entity_type='sustainability_baseline', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    return _baseline_response(row)

def _target_snapshot(row: SustainabilityTarget) -> dict[str, Any]:
    return TargetResponse.model_validate(row).model_dump(mode='json', by_alias=True)

def list_targets(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, status: str | None=None) -> Page[TargetResponse]:
    require_org_read(db, user, organization_id)
    stmt = select(SustainabilityTarget).where(SustainabilityTarget.organization_id == organization_id)
    count_stmt = select(func.count()).select_from(SustainabilityTarget).where(SustainabilityTarget.organization_id == organization_id)
    if status:
        stmt = stmt.where(SustainabilityTarget.status == status)
        count_stmt = count_stmt.where(SustainabilityTarget.status == status)
    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(SustainabilityTarget.code).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_target_response(r) for r in rows], page=page, page_size=page_size, total_items=total)

def create_target(db: Session, user: User, organization_id: uuid.UUID, payload: TargetCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> TargetResponse:
    require_planning_write(db, user, organization_id)
    if payload.target_type not in TARGET_TYPES:
        raise ValidationAppError('Invalid target type.')
    if payload.target_direction not in TARGET_DIRECTIONS:
        raise ValidationAppError('Invalid target direction.')
    baseline = db.get(SustainabilityBaseline, payload.baseline_id)
    if baseline is None or baseline.organization_id != organization_id:
        raise NotFoundError('Baseline not found.')
    if baseline.status != 'approved':
        raise ValidationAppError('Targets require an approved baseline.')
    existing = db.execute(select(SustainabilityTarget).where(SustainabilityTarget.organization_id == organization_id, SustainabilityTarget.code == payload.code.strip())).scalar_one_or_none()
    if existing:
        raise ConflictError('Target code already exists.')
    row = SustainabilityTarget(organization_id=organization_id, code=payload.code.strip(), name=payload.name.strip(), description=payload.description, target_type=payload.target_type, scope=payload.scope, category=payload.category, facility_id=payload.facility_id, baseline_id=payload.baseline_id, baseline_value=payload.baseline_value, target_value=payload.target_value, target_unit=payload.target_unit, target_year=payload.target_year, target_date=payload.target_date, target_direction=payload.target_direction, status='draft', owner_user_id=payload.owner_user_id, revision=1)
    db.add(row)
    db.flush()
    db.add(SustainabilityTargetRevision(target_id=row.id, revision=1, snapshot_json=_target_snapshot(row), changed_by_user_id=user.id))
    write_audit_log(db, action='target.created', actor_user_id=user.id, organization_id=organization_id, entity_type='sustainability_target', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    return _target_response(row)

def get_target(db: Session, user: User, organization_id: uuid.UUID, target_id: uuid.UUID) -> TargetResponse:
    require_org_read(db, user, organization_id)
    row = db.get(SustainabilityTarget, target_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Target not found.')
    return _target_response(row)

def update_target(db: Session, user: User, organization_id: uuid.UUID, target_id: uuid.UUID, payload: TargetUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> TargetResponse:
    require_planning_write(db, user, organization_id)
    row = db.get(SustainabilityTarget, target_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Target not found.')
    if row.status in {'cancelled', 'archived'}:
        raise ValidationAppError('Cancelled or archived targets cannot be updated.')
    data = payload.model_dump(exclude_unset=True)
    if 'target_direction' in data and data['target_direction'] not in TARGET_DIRECTIONS:
        raise ValidationAppError('Invalid target direction.')
    for key, value in data.items():
        setattr(row, key, value)
    row.revision += 1
    db.add(SustainabilityTargetRevision(target_id=row.id, revision=row.revision, snapshot_json=_target_snapshot(row), changed_by_user_id=user.id))
    db.flush()
    write_audit_log(db, action='target.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='sustainability_target', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'revision': row.revision})
    return _target_response(row)

def approve_target(db: Session, user: User, organization_id: uuid.UUID, target_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> TargetResponse:
    require_planning_manage(db, user, organization_id)
    row = db.get(SustainabilityTarget, target_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Target not found.')
    if row.status != 'draft':
        raise ValidationAppError('Only draft targets can be approved.')
    row.status = 'active'
    row.approved_by_user_id = user.id
    row.approved_at = datetime.now(UTC)
    db.flush()
    write_audit_log(db, action='target.approved', actor_user_id=user.id, organization_id=organization_id, entity_type='sustainability_target', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    return _target_response(row)

def target_progress(db: Session, user: User, organization_id: uuid.UUID, target_id: uuid.UUID, *, inventory_id: uuid.UUID | None=None, allow_provisional: bool=False) -> dict[str, Any]:
    require_org_read(db, user, organization_id)
    row = db.get(SustainabilityTarget, target_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Target not found.')
    current: Decimal | None = None
    try:
        inventory = resolve_inventory(db, user, organization_id, inventory_id, allow_provisional=allow_provisional)
        agg = aggregate_items(db, list(db.execute(select(CarbonCalculationItem).where(CarbonCalculationItem.calculation_run_id == inventory.latest_run_id, CarbonCalculationItem.status == 'calculated', CarbonCalculationItem.total_kg_co2e.is_not(None))).scalars().all()) if inventory.latest_run_id else [], facility_id=row.facility_id)
        if row.target_type == 'absolute_emission_reduction':
            if row.scope == 'scope_1':
                current = Decimal(agg['scopeTotals']['scope1KgCo2e'])
            elif row.scope == 'scope_2':
                current = Decimal(agg['scopeTotals']['scope2KgCo2e'])
            elif row.scope == 'scope_3':
                current = Decimal(agg['scopeTotals']['scope3KgCo2e'])
            else:
                current = Decimal(agg['totalKgCo2e'])
    except Exception:
        current = None
    today = date.today()
    baseline_year = row.target_year - max(1, row.target_year - today.year)
    start_year = today.year if row.approved_at is None else row.approved_at.year
    span = max(1, row.target_year - start_year)
    elapsed = Decimal(str(min(1, max(0, (today.year - start_year) / span))))
    progress = compute_target_progress(row.baseline_value, current, row.target_value, direction=row.target_direction, elapsed_ratio=elapsed)
    return {'target': _target_response(row).model_dump(mode='json', by_alias=True), 'progress': progress, 'baselineYearHint': baseline_year}

def list_initiatives(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, status: str | None=None) -> Page[InitiativeResponse]:
    require_org_read(db, user, organization_id)
    stmt = select(ReductionInitiative).where(ReductionInitiative.organization_id == organization_id)
    count_stmt = select(func.count()).select_from(ReductionInitiative).where(ReductionInitiative.organization_id == organization_id)
    if status:
        stmt = stmt.where(ReductionInitiative.status == status)
        count_stmt = count_stmt.where(ReductionInitiative.status == status)
    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(ReductionInitiative.code).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_initiative_response(r) for r in rows], page=page, page_size=page_size, total_items=total)

def create_initiative(db: Session, user: User, organization_id: uuid.UUID, payload: InitiativeCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> InitiativeResponse:
    require_planning_write(db, user, organization_id)
    if payload.initiative_type not in INITIATIVE_TYPES:
        raise ValidationAppError('Invalid initiative type.')
    if payload.expected_reduction_kg_co2e < 0:
        raise ValidationAppError('Expected reduction must be non-negative.')
    if payload.target_id:
        target = db.get(SustainabilityTarget, payload.target_id)
        if target is None or target.organization_id != organization_id:
            raise NotFoundError('Target not found.')
    existing = db.execute(select(ReductionInitiative).where(ReductionInitiative.organization_id == organization_id, ReductionInitiative.code == payload.code.strip())).scalar_one_or_none()
    if existing:
        raise ConflictError('Initiative code already exists.')
    row = ReductionInitiative(organization_id=organization_id, target_id=payload.target_id, code=payload.code.strip(), name=payload.name.strip(), description=payload.description, initiative_type=payload.initiative_type, facility_id=payload.facility_id, activity_type_id=payload.activity_type_id, planned_start_date=payload.planned_start_date, planned_end_date=payload.planned_end_date, expected_reduction_kg_co2e=payload.expected_reduction_kg_co2e, expected_cost=payload.expected_cost, currency_code=payload.currency_code, status='proposed', owner_user_id=payload.owner_user_id)
    db.add(row)
    db.flush()
    write_audit_log(db, action='initiative.created', actor_user_id=user.id, organization_id=organization_id, entity_type='reduction_initiative', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    return _initiative_response(row)

def get_initiative(db: Session, user: User, organization_id: uuid.UUID, initiative_id: uuid.UUID) -> InitiativeResponse:
    require_org_read(db, user, organization_id)
    row = db.get(ReductionInitiative, initiative_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Initiative not found.')
    return _initiative_response(row)

def update_initiative(db: Session, user: User, organization_id: uuid.UUID, initiative_id: uuid.UUID, payload: InitiativeUpdate) -> InitiativeResponse:
    require_planning_write(db, user, organization_id)
    row = db.get(ReductionInitiative, initiative_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Initiative not found.')
    if row.status in {'cancelled', 'archived'}:
        raise ValidationAppError('Cancelled or archived initiatives cannot be updated.')
    data = payload.model_dump(exclude_unset=True)
    for key in ('expected_reduction_kg_co2e', 'actual_reduction_kg_co2e'):
        if key in data and data[key] is not None and (data[key] < 0):
            raise ValidationAppError('Reduction values must be non-negative.')
    for key, value in data.items():
        setattr(row, key, value)
    db.flush()
    return _initiative_response(row)

def transition_initiative(db: Session, user: User, organization_id: uuid.UUID, initiative_id: uuid.UUID, payload: InitiativeTransition, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> InitiativeResponse:
    require_planning_manage(db, user, organization_id)
    row = db.get(ReductionInitiative, initiative_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Initiative not found.')
    if payload.status not in INITIATIVE_STATUSES:
        raise ValidationAppError('Invalid initiative status.')
    allowed = INITIATIVE_TRANSITIONS.get(row.status, frozenset())
    if payload.status not in allowed:
        raise ValidationAppError(f'Cannot transition initiative from {row.status} to {payload.status}.')
    previous = row.status
    row.status = payload.status
    db.flush()
    write_audit_log(db, action='initiative.transitioned', actor_user_id=user.id, organization_id=organization_id, entity_type='reduction_initiative', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'from': previous, 'to': payload.status})
    return _initiative_response(row)
