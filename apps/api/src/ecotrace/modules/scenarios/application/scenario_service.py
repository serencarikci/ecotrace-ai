from __future__ import annotations
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.analytics_constants import SCENARIO_STATUSES, SCENARIO_TYPES
from ecotrace.core.carbon_constants import ENGINE_VERSION
from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
from ecotrace.modules.carbon_accounting.application.calculation_math import compute_emission_result, kg_to_tonnes
from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonCalculationItem, CarbonInventory
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.scenarios.infrastructure.models import ScenarioAssumption, ScenarioModel, ScenarioRun, ScenarioRunItem
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_org_read, require_planning_write
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class ScenarioCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    scenario_type: str
    baseline_inventory_id: uuid.UUID
    reporting_period_id: uuid.UUID | None = None

class ScenarioUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    scenario_type: str | None = None
    reporting_period_id: uuid.UUID | None = None

class AssumptionCreate(CamelModel):
    assumption_type: str
    facility_id: uuid.UUID | None = None
    activity_type_id: uuid.UUID | None = None
    category: str | None = None
    parameter_code: str
    baseline_value: Decimal | None = None
    scenario_value: Decimal | None = None
    unit_code: str | None = None
    change_percentage: Decimal | None = None
    metadata_json: dict[str, Any] | None = None

class ScenarioResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str | None
    scenario_type: str
    baseline_inventory_id: uuid.UUID
    reporting_period_id: uuid.UUID | None
    status: str
    created_by_user_id: uuid.UUID | None

class AssumptionResponse(CamelModel):
    id: uuid.UUID
    scenario_id: uuid.UUID
    assumption_type: str
    facility_id: uuid.UUID | None
    activity_type_id: uuid.UUID | None
    category: str | None
    parameter_code: str
    baseline_value: Decimal | None
    scenario_value: Decimal | None
    unit_code: str | None
    change_percentage: Decimal | None
    metadata_json: dict[str, Any] | None

class ScenarioRunResponse(CamelModel):
    id: uuid.UUID
    scenario_id: uuid.UUID
    run_number: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    triggered_by_user_id: uuid.UUID | None
    baseline_total_kg_co2e: Decimal | None
    scenario_total_kg_co2e: Decimal | None
    reduction_kg_co2e: Decimal | None
    reduction_percentage: Decimal | None
    result_summary_json: dict[str, Any] | None
    engine_version: str

def _scenario_response(row: ScenarioModel) -> ScenarioResponse:
    return ScenarioResponse.model_validate(row)

def _assumption_response(row: ScenarioAssumption) -> AssumptionResponse:
    return AssumptionResponse.model_validate(row)

def _run_response(row: ScenarioRun) -> ScenarioRunResponse:
    return ScenarioRunResponse.model_validate(row)

def _get_scenario(db: Session, organization_id: uuid.UUID, scenario_id: uuid.UUID) -> ScenarioModel:
    row = db.get(ScenarioModel, scenario_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Scenario not found.')
    return row

def list_scenarios(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, status: str | None=None) -> Page[ScenarioResponse]:
    require_org_read(db, user, organization_id)
    stmt = select(ScenarioModel).where(ScenarioModel.organization_id == organization_id)
    count_stmt = select(func.count()).select_from(ScenarioModel).where(ScenarioModel.organization_id == organization_id)
    if status:
        stmt = stmt.where(ScenarioModel.status == status)
        count_stmt = count_stmt.where(ScenarioModel.status == status)
    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(ScenarioModel.code).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_scenario_response(r) for r in rows], page=page, page_size=page_size, total_items=total)

def create_scenario(db: Session, user: User, organization_id: uuid.UUID, payload: ScenarioCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ScenarioResponse:
    require_planning_write(db, user, organization_id)
    if payload.scenario_type not in SCENARIO_TYPES:
        raise ValidationAppError('Invalid scenario type.')
    inventory = db.get(CarbonInventory, payload.baseline_inventory_id)
    if inventory is None or inventory.organization_id != organization_id:
        raise NotFoundError('Baseline inventory not found.')
    if inventory.latest_run_id is None:
        raise ValidationAppError('Baseline inventory has no completed calculation.')
    existing = db.execute(select(ScenarioModel).where(ScenarioModel.organization_id == organization_id, ScenarioModel.code == payload.code.strip())).scalar_one_or_none()
    if existing:
        raise ConflictError('Scenario code already exists.')
    row = ScenarioModel(organization_id=organization_id, code=payload.code.strip(), name=payload.name.strip(), description=payload.description, scenario_type=payload.scenario_type, baseline_inventory_id=payload.baseline_inventory_id, reporting_period_id=payload.reporting_period_id or inventory.reporting_period_id, status='draft', created_by_user_id=user.id)
    db.add(row)
    db.flush()
    write_audit_log(db, action='scenario.created', actor_user_id=user.id, organization_id=organization_id, entity_type='scenario_model', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    return _scenario_response(row)

def get_scenario(db: Session, user: User, organization_id: uuid.UUID, scenario_id: uuid.UUID) -> ScenarioResponse:
    require_org_read(db, user, organization_id)
    return _scenario_response(_get_scenario(db, organization_id, scenario_id))

def update_scenario(db: Session, user: User, organization_id: uuid.UUID, scenario_id: uuid.UUID, payload: ScenarioUpdate) -> ScenarioResponse:
    require_planning_write(db, user, organization_id)
    row = _get_scenario(db, organization_id, scenario_id)
    if row.status == 'archived':
        raise ValidationAppError('Archived scenarios cannot be updated.')
    data = payload.model_dump(exclude_unset=True)
    if 'scenario_type' in data and data['scenario_type'] not in SCENARIO_TYPES:
        raise ValidationAppError('Invalid scenario type.')
    for key, value in data.items():
        setattr(row, key, value)
    if row.status == 'calculated':
        row.status = 'ready'
    db.flush()
    return _scenario_response(row)

def list_assumptions(db: Session, user: User, organization_id: uuid.UUID, scenario_id: uuid.UUID) -> list[AssumptionResponse]:
    require_org_read(db, user, organization_id)
    _get_scenario(db, organization_id, scenario_id)
    rows = db.execute(select(ScenarioAssumption).where(ScenarioAssumption.scenario_id == scenario_id).order_by(ScenarioAssumption.created_at)).scalars().all()
    return [_assumption_response(r) for r in rows]

def add_assumption(db: Session, user: User, organization_id: uuid.UUID, scenario_id: uuid.UUID, payload: AssumptionCreate) -> AssumptionResponse:
    require_planning_write(db, user, organization_id)
    scenario = _get_scenario(db, organization_id, scenario_id)
    if scenario.status == 'archived':
        raise ValidationAppError('Cannot add assumptions to archived scenarios.')
    if payload.change_percentage is None and payload.scenario_value is None:
        raise ValidationAppError('Either changePercentage or scenarioValue is required.')
    row = ScenarioAssumption(scenario_id=scenario_id, assumption_type=payload.assumption_type, facility_id=payload.facility_id, activity_type_id=payload.activity_type_id, category=payload.category, parameter_code=payload.parameter_code, baseline_value=payload.baseline_value, scenario_value=payload.scenario_value, unit_code=payload.unit_code, change_percentage=payload.change_percentage, metadata_json=payload.metadata_json)
    db.add(row)
    if scenario.status == 'draft' or scenario.status == 'calculated':
        scenario.status = 'ready'
    db.flush()
    return _assumption_response(row)

def validate_scenario(db: Session, user: User, organization_id: uuid.UUID, scenario_id: uuid.UUID) -> dict[str, Any]:
    require_org_read(db, user, organization_id)
    scenario = _get_scenario(db, organization_id, scenario_id)
    errors: list[dict[str, str]] = []
    inventory = db.get(CarbonInventory, scenario.baseline_inventory_id)
    if inventory is None or inventory.organization_id != organization_id:
        errors.append({'code': 'missing_inventory', 'message': 'Baseline inventory missing.'})
    elif inventory.latest_run_id is None:
        errors.append({'code': 'no_run', 'message': 'Baseline inventory has no calculation run.'})
    elif inventory.status not in {'approved', 'calculated', 'in_review'}:
        errors.append({'code': 'inventory_status', 'message': f'Inventory status {inventory.status} is not usable for scenarios.'})
    assumptions = db.execute(select(ScenarioAssumption).where(ScenarioAssumption.scenario_id == scenario_id)).scalars().all()
    if not assumptions:
        errors.append({'code': 'no_assumptions', 'message': 'At least one assumption is required.'})
    for assumption in assumptions:
        if assumption.change_percentage is None and assumption.scenario_value is None:
            errors.append({'code': 'incomplete_assumption', 'message': f'Assumption {assumption.parameter_code} has no change value.'})
    valid = not errors
    if valid and scenario.status == 'draft':
        scenario.status = 'ready'
        db.flush()
    return {'valid': valid, 'errors': errors, 'assumptionCount': len(assumptions), 'scenarioStatus': scenario.status}

def _matches_assumption(activity: ActivityRecord, item: CarbonCalculationItem, assumption: ScenarioAssumption) -> bool:
    if assumption.facility_id and activity.facility_id != assumption.facility_id:
        return False
    if assumption.activity_type_id and activity.activity_type_id != assumption.activity_type_id:
        return False
    return not (assumption.category and item.category != assumption.category)

def _apply_quantity(baseline_qty: Decimal, assumption: ScenarioAssumption) -> tuple[Decimal, dict[str, Any]]:
    applied: dict[str, Any] = {'assumptionId': str(assumption.id), 'parameterCode': assumption.parameter_code, 'assumptionType': assumption.assumption_type}
    if assumption.change_percentage is not None:
        factor = Decimal('1') + assumption.change_percentage / Decimal('100')
        if factor < 0:
            factor = Decimal('0')
        qty = baseline_qty * factor
        applied['changePercentage'] = str(assumption.change_percentage)
        return (qty, applied)
    assert assumption.scenario_value is not None
    applied['scenarioValue'] = str(assumption.scenario_value)
    return (assumption.scenario_value, applied)

def _recalculate_item(item: CarbonCalculationItem, scenario_qty: Decimal) -> dict[str, Any]:
    snapshot = item.calculation_snapshot_json or {}
    factor = snapshot.get('factor') or {}
    gwp = snapshot.get('gwpValues') or {}

    def _dec(value: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))
    try:
        result = compute_emission_result(normalized_quantity=scenario_qty, normalized_unit_code=item.normalized_unit_code or item.activity_unit_code, factor_value=_dec(factor.get('factorValue')) if factor.get('factorValue') is not None else item.factor_value, factor_unit_code=factor.get('unitCode') or item.factor_unit_code or item.activity_unit_code, co2_factor=_dec(factor.get('co2Factor')), ch4_factor=_dec(factor.get('ch4Factor')), n2o_factor=_dec(factor.get('n2oFactor')), biogenic_co2_factor=_dec(factor.get('biogenicCo2Factor')), ch4_gwp=_dec(gwp.get('CH4')), n2o_gwp=_dec(gwp.get('N2O')), other_gases_json=item.other_gases_json)
        return result
    except Exception:
        baseline_qty = item.normalized_quantity or item.activity_quantity
        if baseline_qty and baseline_qty != 0 and (item.total_kg_co2e is not None):
            scaled = item.total_kg_co2e / baseline_qty * scenario_qty
            return {'total_kg_co2e': scaled, 'total_t_co2e': kg_to_tonnes(scaled), 'formula': 'scaled_from_baseline', 'co2_kg': None, 'ch4_kg': None, 'n2o_kg': None, 'biogenic_co2_kg': None, 'other_gases_json': item.other_gases_json}
        return {'total_kg_co2e': item.total_kg_co2e or Decimal('0'), 'total_t_co2e': kg_to_tonnes(item.total_kg_co2e or Decimal('0')), 'formula': 'unchanged', 'co2_kg': item.co2_kg, 'ch4_kg': item.ch4_kg, 'n2o_kg': item.n2o_kg, 'biogenic_co2_kg': item.biogenic_co2_kg, 'other_gases_json': item.other_gases_json}

def calculate_scenario(db: Session, user: User, organization_id: uuid.UUID, scenario_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ScenarioRunResponse:
    require_planning_write(db, user, organization_id)
    scenario = _get_scenario(db, organization_id, scenario_id)
    validation = validate_scenario(db, user, organization_id, scenario_id)
    if not validation['valid']:
        raise ValidationAppError('Scenario validation failed.', details=validation['errors'])
    inventory = db.get(CarbonInventory, scenario.baseline_inventory_id)
    assert inventory is not None and inventory.latest_run_id is not None
    items = list(db.execute(select(CarbonCalculationItem).where(CarbonCalculationItem.calculation_run_id == inventory.latest_run_id, CarbonCalculationItem.status == 'calculated', CarbonCalculationItem.total_kg_co2e.is_not(None))).scalars().all())
    assumptions = db.execute(select(ScenarioAssumption).where(ScenarioAssumption.scenario_id == scenario_id)).scalars().all()
    activity_ids = {i.activity_record_id for i in items}
    activities = {a.id: a for a in db.execute(select(ActivityRecord).where(ActivityRecord.id.in_(activity_ids))).scalars().all()} if activity_ids else {}
    next_number = db.execute(select(func.coalesce(func.max(ScenarioRun.run_number), 0)).where(ScenarioRun.scenario_id == scenario_id)).scalar_one() + 1
    run = ScenarioRun(scenario_id=scenario_id, run_number=next_number, status='running', started_at=datetime.now(UTC), triggered_by_user_id=user.id, engine_version=ENGINE_VERSION)
    db.add(run)
    db.flush()
    baseline_total = Decimal('0')
    scenario_total = Decimal('0')
    run_items: list[ScenarioRunItem] = []
    for item in items:
        activity = activities.get(item.activity_record_id)
        if activity is None:
            continue
        baseline_qty = item.normalized_quantity or item.activity_quantity
        scenario_qty = baseline_qty
        applied: dict[str, Any] | None = None
        for assumption in assumptions:
            if _matches_assumption(activity, item, assumption):
                scenario_qty, applied = _apply_quantity(baseline_qty, assumption)
                break
        result = _recalculate_item(item, scenario_qty)
        baseline_kg = item.total_kg_co2e or Decimal('0')
        scenario_kg = result['total_kg_co2e']
        baseline_total += baseline_kg
        scenario_total += scenario_kg
        run_items.append(ScenarioRunItem(scenario_run_id=run.id, baseline_calculation_item_id=item.id, activity_record_id=item.activity_record_id, facility_id=activity.facility_id, activity_type_id=activity.activity_type_id, scope=item.scope, category=item.category, baseline_quantity=baseline_qty, scenario_quantity=scenario_qty, unit_code=item.normalized_unit_code or item.activity_unit_code, baseline_kg_co2e=baseline_kg, scenario_kg_co2e=scenario_kg, reduction_kg_co2e=baseline_kg - scenario_kg, applied_assumption_json=applied, calculation_snapshot_json={'formula': result.get('formula'), 'engineVersion': ENGINE_VERSION}))
    reduction = baseline_total - scenario_total
    pct = None if baseline_total == 0 else reduction / baseline_total * Decimal('100')
    run.baseline_total_kg_co2e = baseline_total
    run.scenario_total_kg_co2e = scenario_total
    run.reduction_kg_co2e = reduction
    run.reduction_percentage = pct
    run.result_summary_json = {'baselineTotalKgCo2e': str(baseline_total), 'scenarioTotalKgCo2e': str(scenario_total), 'reductionKgCo2e': str(reduction), 'reductionPercentage': None if pct is None else str(pct), 'itemCount': len(run_items), 'baselineTotalTCo2e': str(kg_to_tonnes(baseline_total)), 'scenarioTotalTCo2e': str(kg_to_tonnes(scenario_total))}
    run.status = 'completed'
    run.completed_at = datetime.now(UTC)
    db.add_all(run_items)
    scenario.status = 'calculated'
    db.flush()
    write_audit_log(db, action='scenario.calculated', actor_user_id=user.id, organization_id=organization_id, entity_type='scenario_run', entity_id=str(run.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'scenarioId': str(scenario_id), 'runNumber': next_number})
    return _run_response(run)

def list_runs(db: Session, user: User, organization_id: uuid.UUID, scenario_id: uuid.UUID) -> list[ScenarioRunResponse]:
    require_org_read(db, user, organization_id)
    _get_scenario(db, organization_id, scenario_id)
    rows = db.execute(select(ScenarioRun).where(ScenarioRun.scenario_id == scenario_id).order_by(ScenarioRun.run_number.desc())).scalars().all()
    return [_run_response(r) for r in rows]

def get_run(db: Session, user: User, organization_id: uuid.UUID, scenario_id: uuid.UUID, run_id: uuid.UUID) -> ScenarioRunResponse:
    require_org_read(db, user, organization_id)
    _get_scenario(db, organization_id, scenario_id)
    row = db.get(ScenarioRun, run_id)
    if row is None or row.scenario_id != scenario_id:
        raise NotFoundError('Scenario run not found.')
    return _run_response(row)

def archive_scenario(db: Session, user: User, organization_id: uuid.UUID, scenario_id: uuid.UUID) -> ScenarioResponse:
    require_planning_write(db, user, organization_id)
    row = _get_scenario(db, organization_id, scenario_id)
    if row.status not in SCENARIO_STATUSES - {'archived'}:
        raise ValidationAppError('Scenario cannot be archived.')
    row.status = 'archived'
    db.flush()
    return _scenario_response(row)
