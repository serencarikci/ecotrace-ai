from __future__ import annotations
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.carbon_constants import ENGINE_VERSION, GWP_DATASET_AR5_DEMO, METHODOLOGY_VERSION
from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
from ecotrace.modules.carbon_accounting.application.calculation_math import compute_emission_result, kg_to_tonnes
from ecotrace.modules.carbon_accounting.application.matching_service import match_emission_factor
from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonCalculationItem, CarbonCalculationRun, CarbonInventory
from ecotrace.modules.emission_factors.infrastructure.models import EmissionFactor, EmissionFactorSource, GwpValue
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.reference_data.application.unit_conversion import convert_between, get_unit
from ecotrace.modules.reference_data.infrastructure.models import ActivityType
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_manage_structure, require_org_read, require_period_manage, require_write_operational
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class InventoryCreate(CamelModel):
    reporting_period_id: uuid.UUID
    name: str
    description: str | None = None
    gwp_dataset_code: str = GWP_DATASET_AR5_DEMO
    calculation_methodology_version: str = METHODOLOGY_VERSION

class InventoryUpdate(CamelModel):
    name: str | None = None
    description: str | None = None

class InventoryResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_id: uuid.UUID
    name: str
    description: str | None
    status: str
    calculation_methodology_version: str
    gwp_dataset_code: str
    version: int
    partial_calculation: bool
    calculated_at: datetime | None
    calculated_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    approved_by_user_id: uuid.UUID | None
    locked_at: datetime | None
    latest_run_id: uuid.UUID | None
    error_summary_json: dict[str, Any] | None

class CalculateRequest(CamelModel):
    partial_calculation: bool = False

class MatchPreviewRequest(CamelModel):
    activity_record_id: uuid.UUID | None = None
    activity_type_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    activity_date: date | None = None
    quantity: Decimal | None = None
    unit_code: str | None = None

class RunResponse(CamelModel):
    id: uuid.UUID
    inventory_id: uuid.UUID
    run_number: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    triggered_by_user_id: uuid.UUID | None
    activity_record_count: int
    calculated_record_count: int
    skipped_record_count: int
    failed_record_count: int
    total_kg_co2e: Decimal | None
    total_t_co2e: Decimal | None = None
    error_summary_json: dict[str, Any] | None
    engine_version: str
    partial_calculation: bool

class ItemResponse(CamelModel):
    id: uuid.UUID
    calculation_run_id: uuid.UUID
    inventory_id: uuid.UUID
    activity_record_id: uuid.UUID
    emission_factor_id: uuid.UUID | None
    factor_source_id: uuid.UUID | None
    activity_quantity: Decimal
    activity_unit_code: str
    normalized_quantity: Decimal | None
    normalized_unit_code: str | None
    factor_value: Decimal | None
    factor_unit_code: str | None
    scope: str | None
    category: str | None
    subcategory: str | None
    co2_kg: Decimal | None
    ch4_kg: Decimal | None
    n2o_kg: Decimal | None
    other_gases_json: dict[str, Any] | None
    biogenic_co2_kg: Decimal | None
    total_kg_co2e: Decimal | None
    total_t_co2e: Decimal | None = None
    matching_priority: int | None
    matching_reason: str | None
    calculation_formula: str | None
    calculation_snapshot_json: dict[str, Any] | None
    status: str
    validation_errors_json: list[Any] | dict[str, Any] | None

def _inventory_response(row: CarbonInventory) -> InventoryResponse:
    return InventoryResponse.model_validate(row)

def _run_response(row: CarbonCalculationRun) -> RunResponse:
    resp = RunResponse.model_validate(row)
    if row.total_kg_co2e is not None:
        resp.total_t_co2e = kg_to_tonnes(row.total_kg_co2e)
    return resp

def _item_response(row: CarbonCalculationItem) -> ItemResponse:
    resp = ItemResponse.model_validate(row)
    if row.total_kg_co2e is not None:
        resp.total_t_co2e = kg_to_tonnes(row.total_kg_co2e)
    return resp

def _get_inventory(db: Session, organization_id: uuid.UUID, inventory_id: uuid.UUID) -> CarbonInventory:
    row = db.get(CarbonInventory, inventory_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Carbon inventory not found.')
    return row

def _load_gwp_map(db: Session, dataset_code: str) -> dict[str, Decimal]:
    rows = db.execute(select(GwpValue).where(GwpValue.assessment_report_code == dataset_code, GwpValue.is_active.is_(True))).scalars().all()
    return {r.gas_code: r.gwp_value for r in rows}

def list_inventories(db: Session, user: User, organization_id: uuid.UUID, *, page: int=1, page_size: int=20, status: str | None=None, reporting_period_id: uuid.UUID | None=None) -> Page[InventoryResponse]:
    require_org_read(db, user, organization_id)
    stmt = select(CarbonInventory).where(CarbonInventory.organization_id == organization_id)
    count_stmt = select(func.count()).select_from(CarbonInventory).where(CarbonInventory.organization_id == organization_id)
    if status:
        stmt = stmt.where(CarbonInventory.status == status)
        count_stmt = count_stmt.where(CarbonInventory.status == status)
    if reporting_period_id:
        stmt = stmt.where(CarbonInventory.reporting_period_id == reporting_period_id)
        count_stmt = count_stmt.where(CarbonInventory.reporting_period_id == reporting_period_id)
    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(CarbonInventory.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_inventory_response(r) for r in rows], page=page, page_size=page_size, total_items=total)

def create_inventory(db: Session, user: User, organization_id: uuid.UUID, payload: InventoryCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> InventoryResponse:
    require_write_operational(db, user, organization_id)
    period = db.get(ReportingPeriod, payload.reporting_period_id)
    if period is None or period.organization_id != organization_id:
        raise ValidationAppError('Reporting period not found for organization.')
    gwp = _load_gwp_map(db, payload.gwp_dataset_code)
    if not gwp:
        raise ValidationAppError(f"Unknown or empty GWP dataset '{payload.gwp_dataset_code}'.")
    version = db.execute(select(func.coalesce(func.max(CarbonInventory.version), 0)).where(CarbonInventory.organization_id == organization_id, CarbonInventory.reporting_period_id == payload.reporting_period_id)).scalar_one() + 1
    row = CarbonInventory(organization_id=organization_id, reporting_period_id=payload.reporting_period_id, name=payload.name.strip(), description=payload.description, status='draft', calculation_methodology_version=payload.calculation_methodology_version, gwp_dataset_code=payload.gwp_dataset_code, version=version)
    db.add(row)
    db.flush()
    write_audit_log(db, action='inventory.created', actor_user_id=user.id, organization_id=organization_id, entity_type='carbon_inventory', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return _inventory_response(row)

def get_inventory(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID) -> InventoryResponse:
    require_org_read(db, user, organization_id)
    return _inventory_response(_get_inventory(db, organization_id, inventory_id))

def update_inventory(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID, payload: InventoryUpdate) -> InventoryResponse:
    require_write_operational(db, user, organization_id)
    row = _get_inventory(db, organization_id, inventory_id)
    if row.status == 'approved':
        raise BusinessRuleError('Approved inventories are immutable.')
    if row.status in {'under_review', 'calculating'}:
        raise BusinessRuleError('Inventory cannot be modified in its current status.')
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _inventory_response(row)

def _activity_date_for(record: ActivityRecord) -> date | None:
    return record.activity_date or record.period_start

def _extract_dimensions(record: ActivityRecord) -> dict[str, str | None]:
    meta = record.metadata_json or {}
    return {'technology_code': meta.get('technologyCode') or meta.get('technology_code'), 'fuel_type': meta.get('fuelType') or meta.get('fuel_type'), 'transportation_mode': meta.get('transportationMode') or meta.get('transportation_mode')}

def validate_inventory(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> dict[str, Any]:
    require_write_operational(db, user, organization_id)
    inventory = _get_inventory(db, organization_id, inventory_id)
    if inventory.status == 'approved':
        raise BusinessRuleError('Approved inventories cannot be revalidated for mutation.')
    records = list(db.execute(select(ActivityRecord).where(ActivityRecord.organization_id == organization_id, ActivityRecord.reporting_period_id == inventory.reporting_period_id, ActivityRecord.is_archived.is_(False))).scalars().all())
    summary: dict[str, Any] = {'valid': [], 'missingFactors': [], 'ambiguousFactors': [], 'incompatibleUnits': [], 'invalidDates': [], 'incompleteRecords': [], 'unapprovedRecords': [], 'duplicateRecords': [], 'blockingErrorCount': 0, 'warningCount': 0, 'activityRecordCount': len(records)}
    seen_ids: set[uuid.UUID] = set()
    gwp = _load_gwp_map(db, inventory.gwp_dataset_code)
    for record in records:
        if record.id in seen_ids:
            summary['duplicateRecords'].append({'activityRecordId': str(record.id)})
            summary['blockingErrorCount'] += 1
            continue
        seen_ids.add(record.id)
        entry: dict[str, Any] = {'activityRecordId': str(record.id)}
        if record.status != 'approved':
            summary['unapprovedRecords'].append(entry)
            summary['blockingErrorCount'] += 1
            continue
        if record.quantity is None or record.quantity < 0:
            summary['incompleteRecords'].append({**entry, 'reason': 'invalid_quantity'})
            summary['blockingErrorCount'] += 1
            continue
        if not record.normalized_unit_code:
            summary['incompleteRecords'].append({**entry, 'reason': 'missing_normalized_unit'})
            summary['blockingErrorCount'] += 1
            continue
        dims = _extract_dimensions(record)
        match = match_emission_factor(db, organization_id=organization_id, activity_type_id=record.activity_type_id, activity_date=_activity_date_for(record), activity_unit_code=record.normalized_unit_code, facility_id=record.facility_id, technology_code=dims['technology_code'], fuel_type=dims['fuel_type'], transportation_mode=dims['transportation_mode'])
        if match.ambiguous:
            summary['ambiguousFactors'].append({**entry, 'alternatives': [str(a.id) for a in match.alternatives], 'errors': match.errors})
            summary['blockingErrorCount'] += 1
            continue
        if match.selected is None:
            codes = {e.get('code') for e in match.errors}
            if 'missing_factor' in codes:
                summary['missingFactors'].append({**entry, 'errors': match.errors})
            else:
                summary['incompleteRecords'].append({**entry, 'errors': match.errors})
            summary['blockingErrorCount'] += 1
            continue
        factor = match.selected
        try:
            activity_unit = get_unit(db, record.normalized_unit_code)
            factor_unit = get_unit(db, factor.unit_code)
            if activity_unit.dimension != factor_unit.dimension:
                summary['incompatibleUnits'].append(entry)
                summary['blockingErrorCount'] += 1
                continue
        except Exception:
            summary['incompatibleUnits'].append(entry)
            summary['blockingErrorCount'] += 1
            continue
        if any((v is not None for v in (factor.ch4_factor, factor.n2o_factor))):
            if factor.ch4_factor is not None and 'CH4' not in gwp:
                summary['incompleteRecords'].append({**entry, 'reason': 'missing_gwp_ch4'})
                summary['blockingErrorCount'] += 1
                continue
            if factor.n2o_factor is not None and 'N2O' not in gwp:
                summary['incompleteRecords'].append({**entry, 'reason': 'missing_gwp_n2o'})
                summary['blockingErrorCount'] += 1
                continue
        summary['valid'].append({**entry, 'emissionFactorId': str(factor.id), 'matchingPriority': match.priority, 'matchingReason': match.reason})
    write_audit_log(db, action='inventory.validated', actor_user_id=user.id, organization_id=organization_id, entity_type='carbon_inventory', entity_id=str(inventory.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'blockingErrorCount': summary['blockingErrorCount']})
    db.commit()
    return summary

def calculate_inventory(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID, payload: CalculateRequest | None=None, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> RunResponse:
    require_period_manage(db, user, organization_id)
    inventory = _get_inventory(db, organization_id, inventory_id)
    if inventory.status == 'approved':
        raise BusinessRuleError('Approved inventories cannot be recalculated in place. Use recalculate.')
    partial = bool(payload.partial_calculation) if payload else False
    validation = validate_inventory(db, user, organization_id, inventory_id, request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    inventory = _get_inventory(db, organization_id, inventory_id)
    if validation['blockingErrorCount'] > 0 and (not partial):
        raise BusinessRuleError('Blocking validation errors exist. Resolve them or enable partialCalculation.', details=[{'blockingErrorCount': validation['blockingErrorCount']}])
    run_number = db.execute(select(func.coalesce(func.max(CarbonCalculationRun.run_number), 0)).where(CarbonCalculationRun.inventory_id == inventory.id)).scalar_one() + 1
    gwp = _load_gwp_map(db, inventory.gwp_dataset_code)
    gwp_snapshot = {k: str(v) for k, v in gwp.items()}
    inventory.status = 'calculating'
    inventory.partial_calculation = partial
    run = CarbonCalculationRun(inventory_id=inventory.id, run_number=run_number, status='running', started_at=datetime.now(UTC), triggered_by_user_id=user.id, engine_version=ENGINE_VERSION, partial_calculation=partial, gwp_snapshot_json=gwp_snapshot)
    db.add(run)
    db.flush()
    write_audit_log(db, action='calculation.started', actor_user_id=user.id, organization_id=organization_id, entity_type='carbon_calculation_run', entity_id=str(run.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'inventoryId': str(inventory.id), 'runNumber': run_number})
    records = list(db.execute(select(ActivityRecord).where(ActivityRecord.organization_id == organization_id, ActivityRecord.reporting_period_id == inventory.reporting_period_id, ActivityRecord.is_archived.is_(False))).scalars().all())
    activity_type_ids = {r.activity_type_id for r in records}
    activity_types = {a.id: a for a in db.execute(select(ActivityType).where(ActivityType.id.in_(activity_type_ids))).scalars().all()} if activity_type_ids else {}
    calculated = 0
    skipped = 0
    failed = 0
    total_kg = Decimal('0')
    errors: list[dict[str, Any]] = []
    items: list[CarbonCalculationItem] = []
    valid_ids = {uuid.UUID(v['activityRecordId']) for v in validation['valid']}
    for record in records:
        dims = _extract_dimensions(record)
        base_item = {'calculation_run_id': run.id, 'inventory_id': inventory.id, 'activity_record_id': record.id, 'activity_quantity': record.quantity, 'activity_unit_code': record.unit_code}
        if record.status != 'approved':
            skipped += 1
            items.append(CarbonCalculationItem(**base_item, status='skipped', validation_errors_json=[{'code': 'unapproved', 'message': 'Activity not approved.'}]))
            continue
        if record.id not in valid_ids and (not partial):
            failed += 1
            items.append(CarbonCalculationItem(**base_item, status='failed', validation_errors_json=[{'code': 'validation_failed', 'message': 'Failed pre-validation.'}]))
            continue
        match = match_emission_factor(db, organization_id=organization_id, activity_type_id=record.activity_type_id, activity_date=_activity_date_for(record), activity_unit_code=record.normalized_unit_code, facility_id=record.facility_id, technology_code=dims['technology_code'], fuel_type=dims['fuel_type'], transportation_mode=dims['transportation_mode'])
        if match.ambiguous or match.selected is None:
            failed += 1
            err = match.errors or [{'code': 'no_match', 'message': 'No factor matched.'}]
            errors.append({'activityRecordId': str(record.id), 'errors': err})
            items.append(CarbonCalculationItem(**base_item, status='failed', matching_reason=match.explanation, validation_errors_json=err))
            continue
        factor = match.selected
        try:
            activity_unit = get_unit(db, record.normalized_unit_code)
            factor_unit = get_unit(db, factor.unit_code)
            qty_in_factor_unit = convert_between(record.normalized_quantity, activity_unit, factor_unit)
            result = compute_emission_result(normalized_quantity=qty_in_factor_unit, normalized_unit_code=factor.unit_code, factor_value=factor.factor_value, factor_unit_code=factor.unit_code, co2_factor=factor.co2_factor, ch4_factor=factor.ch4_factor, n2o_factor=factor.n2o_factor, biogenic_co2_factor=factor.biogenic_co2_factor, ch4_gwp=gwp.get('CH4'), n2o_gwp=gwp.get('N2O'), other_gases_json=factor.other_gases_json)
            source = db.get(EmissionFactorSource, factor.source_id)
            activity_type = activity_types.get(record.activity_type_id)
            snapshot = {'engineVersion': ENGINE_VERSION, 'methodologyVersion': inventory.calculation_methodology_version, 'gwpDatasetCode': inventory.gwp_dataset_code, 'gwpValues': gwp_snapshot, 'activityRecordId': str(record.id), 'activityTypeId': str(record.activity_type_id), 'activityTypeCode': activity_type.code if activity_type is not None else None, 'facilityId': str(record.facility_id) if record.facility_id else None, 'quantity': str(record.quantity), 'unitCode': record.unit_code, 'normalizedQuantity': str(record.normalized_quantity), 'normalizedUnitCode': record.normalized_unit_code, 'quantityInFactorUnit': str(qty_in_factor_unit), 'factor': {'id': str(factor.id), 'code': factor.code, 'version': factor.version, 'scope': factor.scope, 'category': factor.category, 'geographyCode': factor.geography_code, 'unitCode': factor.unit_code, 'factorValue': str(factor.factor_value) if factor.factor_value is not None else None, 'co2Factor': str(factor.co2_factor) if factor.co2_factor is not None else None, 'ch4Factor': str(factor.ch4_factor) if factor.ch4_factor is not None else None, 'n2oFactor': str(factor.n2o_factor) if factor.n2o_factor is not None else None, 'biogenicCo2Factor': str(factor.biogenic_co2_factor) if factor.biogenic_co2_factor is not None else None, 'isDemo': factor.is_demo}, 'factorSource': {'id': str(source.id) if source else None, 'code': source.code if source else None, 'name': source.name if source else None, 'publisher': source.publisher if source else None, 'licenseName': source.license_name if source else None, 'isDemo': source.is_demo if source else None}, 'matchingPriority': match.priority, 'matchingReason': match.reason, 'formula': result['formula'], 'snapshotAt': datetime.now(UTC).isoformat(), 'disclaimer': 'Demo/reference emission factors are not authoritative and must not be used for regulatory reporting.' if factor.is_demo else None}
            items.append(CarbonCalculationItem(**base_item, emission_factor_id=factor.id, factor_source_id=factor.source_id, normalized_quantity=qty_in_factor_unit, normalized_unit_code=factor.unit_code, factor_value=factor.factor_value, factor_unit_code=factor.unit_code, scope=factor.scope, category=factor.category, subcategory=factor.subcategory, co2_kg=result['co2_kg'], ch4_kg=result['ch4_kg'], n2o_kg=result['n2o_kg'], other_gases_json=result['other_gases_json'], biogenic_co2_kg=result['biogenic_co2_kg'], total_kg_co2e=result['total_kg_co2e'], matching_priority=match.priority, matching_reason=match.reason, calculation_formula=result['formula'], calculation_snapshot_json=snapshot, status='calculated'))
            calculated += 1
            total_kg += result['total_kg_co2e']
        except Exception as exc:
            failed += 1
            err = [{'code': 'calculation_error', 'message': str(exc)}]
            errors.append({'activityRecordId': str(record.id), 'errors': err})
            items.append(CarbonCalculationItem(**base_item, emission_factor_id=factor.id if factor else None, factor_source_id=factor.source_id if factor else None, status='failed', validation_errors_json=err))
    db.add_all(items)
    run.activity_record_count = len(records)
    run.calculated_record_count = calculated
    run.skipped_record_count = skipped
    run.failed_record_count = failed
    run.total_kg_co2e = total_kg
    run.completed_at = datetime.now(UTC)
    run.error_summary_json = {'errors': errors, 'validation': {'blockingErrorCount': validation['blockingErrorCount'], 'missingFactors': len(validation['missingFactors']), 'ambiguousFactors': len(validation['ambiguousFactors'])}}
    if failed and calculated:
        run.status = 'completed_with_errors'
        inventory.status = 'calculated'
        inventory.partial_calculation = True
    elif failed and (not calculated):
        run.status = 'failed'
        inventory.status = 'failed'
    else:
        run.status = 'completed'
        inventory.status = 'calculated'
    inventory.calculated_at = run.completed_at
    inventory.calculated_by_user_id = user.id
    inventory.latest_run_id = run.id
    inventory.error_summary_json = run.error_summary_json
    write_audit_log(db, action='calculation.completed' if run.status != 'failed' else 'calculation.failed', actor_user_id=user.id, organization_id=organization_id, entity_type='carbon_calculation_run', entity_id=str(run.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'status': run.status, 'totalKgCo2e': str(total_kg), 'calculated': calculated, 'failed': failed})
    db.commit()
    db.refresh(run)
    return _run_response(run)

def submit_review(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> InventoryResponse:
    require_period_manage(db, user, organization_id)
    inventory = _get_inventory(db, organization_id, inventory_id)
    if inventory.status not in {'calculated'}:
        raise BusinessRuleError('Only calculated inventories can be submitted for review.')
    if inventory.latest_run_id and (inventory.partial_calculation or (inventory.error_summary_json and inventory.error_summary_json.get('errors'))):
        run = db.get(CarbonCalculationRun, inventory.latest_run_id)
        if run and run.status != 'completed':
            raise BusinessRuleError('Inventories with unresolved calculation errors cannot be submitted.')
    inventory.status = 'under_review'
    write_audit_log(db, action='inventory.submitted_for_review', actor_user_id=user.id, organization_id=organization_id, entity_type='carbon_inventory', entity_id=str(inventory.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(inventory)
    return _inventory_response(inventory)

def approve_inventory(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> InventoryResponse:
    require_manage_structure(db, user, organization_id)
    inventory = _get_inventory(db, organization_id, inventory_id)
    if inventory.status not in {'calculated', 'under_review'}:
        raise BusinessRuleError('Inventory is not ready for approval.')
    if inventory.partial_calculation:
        raise BusinessRuleError('Partial calculations cannot be approved while errors remain.')
    if inventory.latest_run_id:
        run = db.get(CarbonCalculationRun, inventory.latest_run_id)
        if run is None or run.status != 'completed' or run.failed_record_count > 0:
            raise BusinessRuleError('Inventories with unresolved errors cannot be approved.')
    existing = db.execute(select(CarbonInventory).where(CarbonInventory.organization_id == organization_id, CarbonInventory.reporting_period_id == inventory.reporting_period_id, CarbonInventory.status == 'approved', CarbonInventory.id != inventory.id)).scalar_one_or_none()
    if existing:
        existing.status = 'superseded'
    inventory.status = 'approved'
    inventory.approved_at = datetime.now(UTC)
    inventory.approved_by_user_id = user.id
    inventory.locked_at = inventory.approved_at
    write_audit_log(db, action='inventory.approved', actor_user_id=user.id, organization_id=organization_id, entity_type='carbon_inventory', entity_id=str(inventory.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(inventory)
    return _inventory_response(inventory)

def recalculate_inventory(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID, payload: CalculateRequest | None=None, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> RunResponse:
    require_period_manage(db, user, organization_id)
    inventory = _get_inventory(db, organization_id, inventory_id)
    if inventory.status == 'approved':
        clone = CarbonInventory(organization_id=organization_id, reporting_period_id=inventory.reporting_period_id, name=f'{inventory.name} (recalc)', description=inventory.description, status='draft', calculation_methodology_version=inventory.calculation_methodology_version, gwp_dataset_code=inventory.gwp_dataset_code, version=inventory.version + 1)
        db.add(clone)
        db.flush()
        write_audit_log(db, action='inventory.recalculated', actor_user_id=user.id, organization_id=organization_id, entity_type='carbon_inventory', entity_id=str(clone.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'fromInventoryId': str(inventory.id)})
        db.commit()
        return calculate_inventory(db, user, organization_id, clone.id, payload, request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    write_audit_log(db, action='inventory.recalculated', actor_user_id=user.id, organization_id=organization_id, entity_type='carbon_inventory', entity_id=str(inventory.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    return calculate_inventory(db, user, organization_id, inventory_id, payload, request_id=request_id, ip_address=ip_address, user_agent=user_agent)

def list_runs(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID) -> list[RunResponse]:
    require_org_read(db, user, organization_id)
    _get_inventory(db, organization_id, inventory_id)
    rows = db.execute(select(CarbonCalculationRun).where(CarbonCalculationRun.inventory_id == inventory_id).order_by(CarbonCalculationRun.run_number.desc())).scalars().all()
    return [_run_response(r) for r in rows]

def list_items(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID, *, page: int=1, page_size: int=50, run_id: uuid.UUID | None=None, status: str | None=None) -> Page[ItemResponse]:
    require_org_read(db, user, organization_id)
    inventory = _get_inventory(db, organization_id, inventory_id)
    target_run = run_id or inventory.latest_run_id
    if target_run is None:
        return paginate([], page=page, page_size=page_size, total_items=0)
    stmt = select(CarbonCalculationItem).where(CarbonCalculationItem.inventory_id == inventory_id, CarbonCalculationItem.calculation_run_id == target_run)
    count_stmt = select(func.count()).select_from(CarbonCalculationItem).where(CarbonCalculationItem.inventory_id == inventory_id, CarbonCalculationItem.calculation_run_id == target_run)
    if status:
        stmt = stmt.where(CarbonCalculationItem.status == status)
        count_stmt = count_stmt.where(CarbonCalculationItem.status == status)
    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(CarbonCalculationItem.created_at).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_item_response(r) for r in rows], page=page, page_size=page_size, total_items=total)

def get_item_detail(db: Session, user: User, organization_id: uuid.UUID, item_id: uuid.UUID) -> dict[str, Any]:
    require_org_read(db, user, organization_id)
    item = db.get(CarbonCalculationItem, item_id)
    if item is None:
        raise NotFoundError('Calculation item not found.')
    inventory = db.get(CarbonInventory, item.inventory_id)
    if inventory is None or inventory.organization_id != organization_id:
        raise NotFoundError('Calculation item not found.')
    activity = db.get(ActivityRecord, item.activity_record_id)
    factor = db.get(EmissionFactor, item.emission_factor_id) if item.emission_factor_id else None
    source = db.get(EmissionFactorSource, item.factor_source_id) if item.factor_source_id else None
    facility = db.get(Facility, activity.facility_id) if activity and activity.facility_id else None
    return {'item': _item_response(item), 'activity': {'id': str(activity.id) if activity else None, 'quantity': str(activity.quantity) if activity else None, 'unitCode': activity.unit_code if activity else None, 'normalizedQuantity': str(activity.normalized_quantity) if activity else None, 'normalizedUnitCode': activity.normalized_unit_code if activity else None, 'status': activity.status if activity else None, 'activityDate': activity.activity_date.isoformat() if activity and activity.activity_date else None, 'facilityId': str(activity.facility_id) if activity and activity.facility_id else None, 'facilityName': facility.name if facility else None, 'facilityCountry': facility.country_code if facility else None}, 'factor': factor_snapshot(factor) if factor else None, 'source': {'id': str(source.id) if source else None, 'code': source.code if source else None, 'name': source.name if source else None, 'publisher': source.publisher if source else None, 'isDemo': source.is_demo if source else None} if source else None, 'formula': item.calculation_formula, 'gasBreakdown': {'co2Kg': str(item.co2_kg) if item.co2_kg is not None else None, 'ch4Kg': str(item.ch4_kg) if item.ch4_kg is not None else None, 'n2oKg': str(item.n2o_kg) if item.n2o_kg is not None else None, 'biogenicCo2Kg': str(item.biogenic_co2_kg) if item.biogenic_co2_kg is not None else None, 'totalKgCo2e': str(item.total_kg_co2e) if item.total_kg_co2e is not None else None, 'totalTCo2e': str(kg_to_tonnes(item.total_kg_co2e)) if isinstance(item.total_kg_co2e, Decimal) else None}, 'matchingExplanation': item.matching_reason, 'matchingPriority': item.matching_priority, 'snapshot': item.calculation_snapshot_json, 'validation': item.validation_errors_json}

def factor_snapshot(factor: EmissionFactor) -> dict[str, Any]:
    return {'id': str(factor.id), 'code': factor.code, 'name': factor.name, 'version': factor.version, 'scope': factor.scope, 'category': factor.category, 'geographyCode': factor.geography_code, 'unitCode': factor.unit_code, 'factorValue': str(factor.factor_value) if factor.factor_value is not None else None, 'status': factor.status, 'isDemo': factor.is_demo}

def inventory_summary(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID) -> dict[str, Any]:
    require_org_read(db, user, organization_id)
    inventory = _get_inventory(db, organization_id, inventory_id)
    if not inventory.latest_run_id:
        return {'inventoryId': str(inventory.id), 'status': inventory.status, 'totalKgCo2e': '0', 'totalTCo2e': '0', 'scope1TotalKgCo2e': '0', 'scope2TotalKgCo2e': '0', 'scope3TotalKgCo2e': '0', 'categoryTotals': [], 'facilityTotals': [], 'activityTypeTotals': [], 'greenhouseGasTotals': {}, 'itemCounts': {'calculated': 0, 'failed': 0, 'skipped': 0}, 'errorCounts': 0}
    items = list(db.execute(select(CarbonCalculationItem).where(CarbonCalculationItem.calculation_run_id == inventory.latest_run_id)).scalars().all())
    calc_items = [i for i in items if i.status == 'calculated' and i.total_kg_co2e is not None]
    total = Decimal('0')
    for i in calc_items:
        assert i.total_kg_co2e is not None
        total += i.total_kg_co2e
    scope_totals = {'scope_1': Decimal('0'), 'scope_2': Decimal('0'), 'scope_3': Decimal('0')}
    category_map: dict[str, Decimal] = {}
    facility_map: dict[str, Decimal] = {}
    activity_map: dict[str, Decimal] = {}
    gas_totals = {'co2Kg': Decimal('0'), 'ch4Kg': Decimal('0'), 'n2oKg': Decimal('0'), 'biogenicCo2Kg': Decimal('0')}
    activity_ids = {i.activity_record_id for i in calc_items}
    activities = {a.id: a for a in db.execute(select(ActivityRecord).where(ActivityRecord.id.in_(activity_ids))).scalars().all()} if activity_ids else {}
    facility_ids = {a.facility_id for a in activities.values() if a.facility_id}
    facilities = {f.id: f for f in db.execute(select(Facility).where(Facility.id.in_(facility_ids))).scalars().all()} if facility_ids else {}
    type_ids = {a.activity_type_id for a in activities.values()}
    types = {t.id: t for t in db.execute(select(ActivityType).where(ActivityType.id.in_(type_ids))).scalars().all()} if type_ids else {}
    for item in calc_items:
        assert item.total_kg_co2e is not None
        if item.scope in scope_totals:
            scope_totals[item.scope] += item.total_kg_co2e
        if item.category:
            category_map[item.category] = category_map.get(item.category, Decimal('0')) + item.total_kg_co2e
        act = activities.get(item.activity_record_id)
        if act and act.facility_id:
            fac = facilities.get(act.facility_id)
            key = fac.name if fac else str(act.facility_id)
            facility_map[key] = facility_map.get(key, Decimal('0')) + item.total_kg_co2e
        if act:
            at = types.get(act.activity_type_id)
            key = at.code if at else str(act.activity_type_id)
            activity_map[key] = activity_map.get(key, Decimal('0')) + item.total_kg_co2e
        if item.co2_kg:
            gas_totals['co2Kg'] += item.co2_kg
        if item.ch4_kg:
            gas_totals['ch4Kg'] += item.ch4_kg
        if item.n2o_kg:
            gas_totals['n2oKg'] += item.n2o_kg
        if item.biogenic_co2_kg:
            gas_totals['biogenicCo2Kg'] += item.biogenic_co2_kg
    return {'inventoryId': str(inventory.id), 'status': inventory.status, 'partialCalculation': inventory.partial_calculation, 'totalKgCo2e': str(total), 'totalTCo2e': str(kg_to_tonnes(total)), 'scope1TotalKgCo2e': str(scope_totals['scope_1']), 'scope2TotalKgCo2e': str(scope_totals['scope_2']), 'scope3TotalKgCo2e': str(scope_totals['scope_3']), 'scope1TotalTCo2e': str(kg_to_tonnes(scope_totals['scope_1'])), 'scope2TotalTCo2e': str(kg_to_tonnes(scope_totals['scope_2'])), 'scope3TotalTCo2e': str(kg_to_tonnes(scope_totals['scope_3'])), 'categoryTotals': [{'category': k, 'kgCo2e': str(v), 'tCo2e': str(kg_to_tonnes(v))} for k, v in sorted(category_map.items())], 'facilityTotals': [{'facility': k, 'kgCo2e': str(v), 'tCo2e': str(kg_to_tonnes(v))} for k, v in sorted(facility_map.items())], 'activityTypeTotals': [{'activityType': k, 'kgCo2e': str(v), 'tCo2e': str(kg_to_tonnes(v))} for k, v in sorted(activity_map.items())], 'greenhouseGasTotals': {k: str(v) for k, v in gas_totals.items()}, 'itemCounts': {'calculated': sum((1 for i in items if i.status == 'calculated')), 'failed': sum((1 for i in items if i.status == 'failed')), 'skipped': sum((1 for i in items if i.status == 'skipped'))}, 'errorCounts': sum((1 for i in items if i.status == 'failed'))}

def preview_factor_match(db: Session, user: User, organization_id: uuid.UUID, payload: MatchPreviewRequest) -> dict[str, Any]:
    ensure_org_access(db, user, organization_id)
    activity_type_id = payload.activity_type_id
    facility_id = payload.facility_id
    activity_date = payload.activity_date
    unit_code = payload.unit_code
    dims: dict[str, str | None] = {'technology_code': None, 'fuel_type': None, 'transportation_mode': None}
    if payload.activity_record_id:
        record = db.get(ActivityRecord, payload.activity_record_id)
        if record is None or record.organization_id != organization_id:
            raise NotFoundError('Activity record not found.')
        activity_type_id = record.activity_type_id
        facility_id = record.facility_id
        activity_date = _activity_date_for(record)
        unit_code = record.normalized_unit_code
        dims = _extract_dimensions(record)
    if activity_type_id is None or unit_code is None:
        raise ValidationAppError('activityTypeId and unitCode are required when no activityRecordId.')
    match = match_emission_factor(db, organization_id=organization_id, activity_type_id=activity_type_id, activity_date=activity_date, activity_unit_code=unit_code, facility_id=facility_id, technology_code=dims['technology_code'], fuel_type=dims['fuel_type'], transportation_mode=dims['transportation_mode'])
    return {'selectedFactor': factor_snapshot(match.selected) if match.selected else None, 'matchingPriority': match.priority, 'matchingExplanation': match.explanation or match.reason, 'alternativeFactors': [factor_snapshot(f) for f in match.alternatives], 'ambiguityStatus': match.ambiguous, 'validationErrors': match.errors}
