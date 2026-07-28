from __future__ import annotations
import uuid
from datetime import date
from decimal import Decimal
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.analytics_constants import AVAIL_AVAILABLE, AVAIL_UNAVAILABLE, PROGRESS_ACHIEVED, PROGRESS_AT_RISK, PROGRESS_AT_RISK_TOLERANCE, PROGRESS_MISSED, PROGRESS_NOT_STARTED, PROGRESS_OFF_TRACK, PROGRESS_ON_TRACK, PROGRESS_UNAVAILABLE, TREND_DECREASED, TREND_INCREASED, TREND_UNAVAILABLE, TREND_UNCHANGED
from ecotrace.core.exceptions import AuthorizationError, NotFoundError, ValidationAppError
from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
from ecotrace.modules.carbon_accounting.application.calculation_math import kg_to_tonnes
from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonCalculationItem, CarbonCalculationRun, CarbonInventory
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.reference_data.infrastructure.models import ActivityType
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod
from ecotrace.modules.sustainability_targets.infrastructure.models import SustainabilityTarget
from ecotrace.shared.application.org_access import require_org_read, require_period_manage

def _d(value: Decimal | None) -> str | None:
    return None if value is None else str(value)

def _trend(current: Decimal | None, previous: Decimal | None) -> dict[str, Any]:
    if current is None or previous is None:
        return {'currentValue': _d(current), 'comparisonValue': _d(previous), 'absoluteChange': None, 'percentageChange': None, 'trendDirection': TREND_UNAVAILABLE, 'availability': AVAIL_UNAVAILABLE}
    change = current - previous
    pct = None if previous == 0 else change / previous * Decimal('100')
    if change > 0:
        direction = TREND_INCREASED
    elif change < 0:
        direction = TREND_DECREASED
    else:
        direction = TREND_UNCHANGED
    return {'currentValue': str(current), 'comparisonValue': str(previous), 'absoluteChange': str(change), 'percentageChange': None if pct is None else str(pct), 'trendDirection': direction, 'availability': AVAIL_AVAILABLE}

def resolve_inventory(db: Session, user: User, organization_id: uuid.UUID, inventory_id: uuid.UUID | None=None, *, allow_provisional: bool=False) -> CarbonInventory:
    require_org_read(db, user, organization_id)
    if inventory_id is not None:
        inv = db.get(CarbonInventory, inventory_id)
        if inv is None or inv.organization_id != organization_id:
            raise NotFoundError('Carbon inventory not found.')
        if inv.status != 'approved' and (not allow_provisional):
            raise AuthorizationError('Only approved inventories are available for analytics.')
        if allow_provisional and inv.status not in {'approved', 'calculated', 'in_review'} and (inv.latest_run_id is None):
            raise ValidationAppError('Inventory has no completed calculation.')
        return inv
    stmt = select(CarbonInventory).where(CarbonInventory.organization_id == organization_id, CarbonInventory.status == 'approved').order_by(CarbonInventory.approved_at.desc().nullslast(), CarbonInventory.created_at.desc()).limit(1)
    inv = db.execute(stmt).scalar_one_or_none()
    if inv is None and allow_provisional:
        stmt = select(CarbonInventory).where(CarbonInventory.organization_id == organization_id, CarbonInventory.latest_run_id.is_not(None)).order_by(CarbonInventory.calculated_at.desc().nullslast()).limit(1)
        inv = db.execute(stmt).scalar_one_or_none()
    if inv is None:
        raise NotFoundError('No analytics inventory available.')
    return inv

def inventory_metadata(db: Session, inventory: CarbonInventory) -> dict[str, Any]:
    period = db.get(ReportingPeriod, inventory.reporting_period_id)
    run = db.get(CarbonCalculationRun, inventory.latest_run_id) if inventory.latest_run_id else None
    return {'organizationId': str(inventory.organization_id), 'inventoryId': str(inventory.id), 'inventoryName': inventory.name, 'inventoryStatus': inventory.status, 'reportingPeriodId': str(inventory.reporting_period_id), 'reportingPeriodCode': period.code if period else None, 'calculationRunId': str(inventory.latest_run_id) if inventory.latest_run_id else None, 'calculatedAt': inventory.calculated_at.isoformat() if inventory.calculated_at else None, 'methodologyVersion': inventory.calculation_methodology_version, 'gwpDataset': inventory.gwp_dataset_code, 'provisional': inventory.status != 'approved', 'engineVersion': run.engine_version if run else None}

def _load_calculated_items(db: Session, inventory: CarbonInventory) -> list[CarbonCalculationItem]:
    if not inventory.latest_run_id:
        return []
    return list(db.execute(select(CarbonCalculationItem).where(CarbonCalculationItem.calculation_run_id == inventory.latest_run_id, CarbonCalculationItem.status == 'calculated', CarbonCalculationItem.total_kg_co2e.is_not(None))).scalars().all())

def aggregate_items(db: Session, items: list[CarbonCalculationItem], facility_id: uuid.UUID | None=None) -> dict[str, Any]:
    if facility_id is not None:
        activity_ids = {i.activity_record_id for i in items}
        activities = {a.id: a for a in db.execute(select(ActivityRecord).where(ActivityRecord.id.in_(activity_ids))).scalars().all()} if activity_ids else {}
        items = [i for i in items if activities.get(i.activity_record_id) and activities[i.activity_record_id].facility_id == facility_id]
    total = sum((i.total_kg_co2e or Decimal('0') for i in items), Decimal('0'))
    scopes = {'scope_1': Decimal('0'), 'scope_2': Decimal('0'), 'scope_3': Decimal('0')}
    categories: dict[str, Decimal] = {}
    facilities: dict[str, Decimal] = {}
    activity_types: dict[str, Decimal] = {}
    gases = {'co2Kg': Decimal('0'), 'ch4Kg': Decimal('0'), 'n2oKg': Decimal('0'), 'biogenicCo2Kg': Decimal('0')}
    sources: dict[str, Decimal] = {}
    activity_ids = {i.activity_record_id for i in items}
    activities = {a.id: a for a in db.execute(select(ActivityRecord).where(ActivityRecord.id.in_(activity_ids))).scalars().all()} if activity_ids else {}
    facility_ids = {a.facility_id for a in activities.values() if a.facility_id}
    facility_rows = {f.id: f for f in db.execute(select(Facility).where(Facility.id.in_(facility_ids))).scalars().all()} if facility_ids else {}
    type_ids = {a.activity_type_id for a in activities.values()}
    type_rows = {t.id: t for t in db.execute(select(ActivityType).where(ActivityType.id.in_(type_ids))).scalars().all()} if type_ids else {}
    for item in items:
        kg = item.total_kg_co2e or Decimal('0')
        if item.scope in scopes:
            scopes[item.scope] += kg
        if item.category:
            categories[item.category] = categories.get(item.category, Decimal('0')) + kg
        if item.factor_source_id:
            key = str(item.factor_source_id)
            sources[key] = sources.get(key, Decimal('0')) + kg
        gases['co2Kg'] += item.co2_kg or Decimal('0')
        gases['ch4Kg'] += item.ch4_kg or Decimal('0')
        gases['n2oKg'] += item.n2o_kg or Decimal('0')
        gases['biogenicCo2Kg'] += item.biogenic_co2_kg or Decimal('0')
        act = activities.get(item.activity_record_id)
        if act and act.facility_id:
            fac = facility_rows.get(act.facility_id)
            label = fac.name if fac else str(act.facility_id)
            facilities[label] = facilities.get(label, Decimal('0')) + kg
        if act:
            at = type_rows.get(act.activity_type_id)
            label = at.name if at else str(act.activity_type_id)
            activity_types[label] = activity_types.get(label, Decimal('0')) + kg

    def ranked(mapping: dict[str, Decimal]) -> list[dict[str, Any]]:
        rows = sorted(mapping.items(), key=lambda x: x[1], reverse=True)
        return [{'name': name, 'totalKgCo2e': str(value), 'totalTCo2e': str(kg_to_tonnes(value)), 'sharePercentage': str(value / total * Decimal('100') if total else Decimal('0'))} for name, value in rows]
    largest_source = ranked(categories)[0] if categories else None
    highest_facility = ranked(facilities)[0] if facilities else None
    return {'totalKgCo2e': str(total), 'totalTCo2e': str(kg_to_tonnes(total)), 'scopeTotals': {'scope1KgCo2e': str(scopes['scope_1']), 'scope2KgCo2e': str(scopes['scope_2']), 'scope3KgCo2e': str(scopes['scope_3']), 'scope1TCo2e': str(kg_to_tonnes(scopes['scope_1'])), 'scope2TCo2e': str(kg_to_tonnes(scopes['scope_2'])), 'scope3TCo2e': str(kg_to_tonnes(scopes['scope_3']))}, 'categoryTotals': ranked(categories), 'facilityTotals': ranked(facilities), 'activityTypeTotals': ranked(activity_types), 'factorSourceTotals': ranked(sources), 'greenhouseGasTotals': {k: str(v) for k, v in gases.items()}, 'largestEmissionSource': largest_source, 'highestEmittingFacility': highest_facility, 'itemCount': len(items)}

def dashboard(db: Session, user: User, organization_id: uuid.UUID, *, inventory_id: uuid.UUID | None=None, facility_id: uuid.UUID | None=None, comparison_inventory_id: uuid.UUID | None=None, allow_provisional: bool=False) -> dict[str, Any]:
    if allow_provisional:
        require_period_manage(db, user, organization_id)
    inventory = resolve_inventory(db, user, organization_id, inventory_id, allow_provisional=allow_provisional)
    items = _load_calculated_items(db, inventory)
    agg = aggregate_items(db, items, facility_id=facility_id)
    comparison = None
    if comparison_inventory_id:
        try:
            other = resolve_inventory(db, user, organization_id, comparison_inventory_id, allow_provisional=allow_provisional)
            other_items = _load_calculated_items(db, other)
            other_agg = aggregate_items(db, other_items, facility_id=facility_id)
            comparison = _trend(Decimal(agg['totalKgCo2e']), Decimal(other_agg['totalKgCo2e']))
            comparison['comparisonInventoryId'] = str(other.id)
        except (NotFoundError, AuthorizationError, ValidationAppError):
            comparison = _trend(Decimal(agg['totalKgCo2e']), None)
    approved_activity_count = db.execute(select(func.count()).select_from(ActivityRecord).where(ActivityRecord.organization_id == organization_id, ActivityRecord.status == 'approved')).scalar_one()
    error_count = 0
    if inventory.latest_run_id:
        error_count = db.execute(select(func.count()).select_from(CarbonCalculationItem).where(CarbonCalculationItem.calculation_run_id == inventory.latest_run_id, CarbonCalculationItem.status == 'failed')).scalar_one()
    return {'metadata': inventory_metadata(db, inventory), 'summary': {'totalEmissionsKgCo2e': agg['totalKgCo2e'], 'totalEmissionsTCo2e': agg['totalTCo2e'], 'scope1KgCo2e': agg['scopeTotals']['scope1KgCo2e'], 'scope2KgCo2e': agg['scopeTotals']['scope2KgCo2e'], 'scope3KgCo2e': agg['scopeTotals']['scope3KgCo2e'], 'approvedActivityRecordCount': int(approved_activity_count), 'calculationErrorCount': int(error_count), 'largestEmissionSource': agg['largestEmissionSource'], 'highestEmittingFacility': agg['highestEmittingFacility']}, 'scopeDistribution': agg['scopeTotals'], 'categoryDistribution': agg['categoryTotals'], 'facilityTotals': agg['facilityTotals'], 'activityTypeTotals': agg['activityTypeTotals'], 'greenhouseGasTotals': agg['greenhouseGasTotals'], 'comparison': comparison, 'empty': agg['itemCount'] == 0}

def breakdown(db: Session, user: User, organization_id: uuid.UUID, dimension: str, *, inventory_id: uuid.UUID | None=None, facility_id: uuid.UUID | None=None, allow_provisional: bool=False) -> dict[str, Any]:
    inventory = resolve_inventory(db, user, organization_id, inventory_id, allow_provisional=allow_provisional)
    agg = aggregate_items(db, _load_calculated_items(db, inventory), facility_id=facility_id)
    mapping = {'scopes': [{'name': 'scope_1', 'totalKgCo2e': agg['scopeTotals']['scope1KgCo2e']}, {'name': 'scope_2', 'totalKgCo2e': agg['scopeTotals']['scope2KgCo2e']}, {'name': 'scope_3', 'totalKgCo2e': agg['scopeTotals']['scope3KgCo2e']}], 'categories': agg['categoryTotals'], 'facilities': agg['facilityTotals'], 'activity-types': agg['activityTypeTotals'], 'gases': [{'name': k, 'totalKgCo2e': v} for k, v in agg['greenhouseGasTotals'].items()], 'factor-sources': agg['factorSourceTotals']}
    if dimension not in mapping:
        raise ValidationAppError('Unsupported breakdown dimension.')
    return {'metadata': inventory_metadata(db, inventory), 'items': mapping[dimension]}

def monthly_trends(db: Session, user: User, organization_id: uuid.UUID, *, inventory_id: uuid.UUID | None=None, allow_provisional: bool=False) -> dict[str, Any]:
    inventory = resolve_inventory(db, user, organization_id, inventory_id, allow_provisional=allow_provisional)
    items = _load_calculated_items(db, inventory)
    activity_ids = {i.activity_record_id for i in items}
    activities = {a.id: a for a in db.execute(select(ActivityRecord).where(ActivityRecord.id.in_(activity_ids))).scalars().all()} if activity_ids else {}
    buckets: dict[str, Decimal] = {}
    scope_buckets: dict[str, dict[str, Decimal]] = {}
    for item in items:
        act = activities.get(item.activity_record_id)
        raw_date = None
        if act is not None:
            raw_date = getattr(act, 'activity_date', None) or getattr(act, 'period_start', None)
        if isinstance(raw_date, date):
            key = f'{raw_date.year:04d}-{raw_date.month:02d}'
        else:
            key = 'unknown'
        kg = item.total_kg_co2e or Decimal('0')
        buckets[key] = buckets.get(key, Decimal('0')) + kg
        scope_buckets.setdefault(key, {'scope_1': Decimal('0'), 'scope_2': Decimal('0'), 'scope_3': Decimal('0')})
        if item.scope in scope_buckets[key]:
            scope_buckets[key][item.scope] += kg
    points = []
    ordered = sorted((k for k in buckets if k != 'unknown')) + (['unknown'] if 'unknown' in buckets else [])
    prev: Decimal | None = None
    for key in ordered:
        current = buckets[key]
        points.append({'period': key, 'totalKgCo2e': str(current), 'scope1KgCo2e': str(scope_buckets[key]['scope_1']), 'scope2KgCo2e': str(scope_buckets[key]['scope_2']), 'scope3KgCo2e': str(scope_buckets[key]['scope_3']), 'comparison': _trend(current, prev)})
        prev = current
    return {'metadata': inventory_metadata(db, inventory), 'points': points, 'empty': not points}

def compute_target_progress(baseline_value: Decimal, current_value: Decimal | None, target_value: Decimal, *, direction: str, elapsed_ratio: Decimal | None) -> dict[str, Any]:
    if current_value is None:
        return {'baselineValue': str(baseline_value), 'currentValue': None, 'targetValue': str(target_value), 'progressPercentage': None, 'remainingAmount': None, 'elapsedTimePercentage': None if elapsed_ratio is None else str(elapsed_ratio * 100), 'status': PROGRESS_UNAVAILABLE, 'expectedTrajectory': None, 'actualTrajectory': None, 'projectedCompletionStatus': PROGRESS_UNAVAILABLE}
    span = baseline_value - target_value if direction == 'decrease' else target_value - baseline_value
    moved = baseline_value - current_value if direction == 'decrease' else current_value - baseline_value
    if span == 0:
        progress = Decimal('100') if current_value == target_value else Decimal('0')
    else:
        progress = moved / span * Decimal('100')
    remaining = target_value - current_value if direction == 'increase' else current_value - target_value
    achieved = current_value <= target_value if direction == 'decrease' else current_value >= target_value
    if achieved:
        status = PROGRESS_ACHIEVED
    elif elapsed_ratio is None:
        status = PROGRESS_NOT_STARTED if progress <= 0 else PROGRESS_ON_TRACK
    elif progress <= 0 and elapsed_ratio > 0:
        status = PROGRESS_OFF_TRACK
    else:
        expected = elapsed_ratio * Decimal('100')
        gap = expected - progress
        tol = Decimal(PROGRESS_AT_RISK_TOLERANCE) * Decimal('100')
        if gap <= 0:
            status = PROGRESS_ON_TRACK
        elif gap <= tol:
            status = PROGRESS_AT_RISK
        else:
            status = PROGRESS_OFF_TRACK
        if elapsed_ratio >= 1 and (not achieved):
            status = PROGRESS_MISSED
    return {'baselineValue': str(baseline_value), 'currentValue': str(current_value), 'targetValue': str(target_value), 'progressPercentage': str(progress), 'remainingAmount': str(remaining), 'elapsedTimePercentage': None if elapsed_ratio is None else str(elapsed_ratio * Decimal('100')), 'status': status, 'expectedTrajectory': None if elapsed_ratio is None else str(elapsed_ratio * Decimal('100')), 'actualTrajectory': str(progress), 'projectedCompletionStatus': status}

def recommendations(db: Session, user: User, organization_id: uuid.UUID, *, inventory_id: uuid.UUID | None=None, allow_provisional: bool=False) -> list[dict[str, Any]]:
    inventory = resolve_inventory(db, user, organization_id, inventory_id, allow_provisional=allow_provisional)
    agg = aggregate_items(db, _load_calculated_items(db, inventory))
    recs: list[dict[str, Any]] = []
    total = Decimal(agg['totalKgCo2e'])
    if agg['highestEmittingFacility'] and total > 0:
        share = Decimal(agg['highestEmittingFacility']['sharePercentage'])
        if share >= Decimal('40'):
            recs.append({'code': 'facility_concentration', 'title': 'Investigate high-emitting facility', 'description': f"{agg['highestEmittingFacility']['name']} contributes {agg['highestEmittingFacility']['sharePercentage']}% of inventory emissions.", 'recommendationType': 'facility_investigation', 'priority': 'high' if share >= Decimal('50') else 'medium', 'evidence': agg['highestEmittingFacility'], 'affectedFacility': agg['highestEmittingFacility']['name'], 'affectedActivityType': None, 'estimatedReduction': None, 'sourceMetric': 'facilityShare', 'generatedAt': inventory.calculated_at.isoformat() if inventory.calculated_at else None})
    scope2 = Decimal(agg['scopeTotals']['scope2KgCo2e'])
    if total > 0 and scope2 / total >= Decimal('0.30'):
        recs.append({'code': 'scope2_share', 'title': 'Review renewable electricity scenario', 'description': 'Scope 2 share exceeds 30% of total emissions in the selected inventory.', 'recommendationType': 'renewable_electricity_scenario', 'priority': 'medium', 'evidence': {'scope2KgCo2e': str(scope2), 'totalKgCo2e': str(total)}, 'affectedFacility': None, 'affectedActivityType': None, 'estimatedReduction': None, 'sourceMetric': 'scope2Share', 'generatedAt': inventory.calculated_at.isoformat() if inventory.calculated_at else None})
    if agg['largestEmissionSource'] and agg['largestEmissionSource']['name'] in {'purchased_electricity', 'stationary_combustion'}:
        recs.append({'code': 'largest_source_efficiency', 'title': 'Prioritize efficiency on the largest emission source', 'description': f"Largest category is {agg['largestEmissionSource']['name']} ({agg['largestEmissionSource']['sharePercentage']}%).", 'recommendationType': 'efficiency_review', 'priority': 'high', 'evidence': agg['largestEmissionSource'], 'affectedFacility': None, 'affectedActivityType': None, 'estimatedReduction': None, 'sourceMetric': 'categoryShare', 'generatedAt': inventory.calculated_at.isoformat() if inventory.calculated_at else None})
    active_targets = db.execute(select(SustainabilityTarget).where(SustainabilityTarget.organization_id == organization_id, SustainabilityTarget.status == 'active')).scalars().all()
    for target in active_targets:
        progress = compute_target_progress(target.baseline_value, Decimal(agg['totalKgCo2e']) if target.target_type == 'absolute_emission_reduction' else None, target.target_value, direction=target.target_direction, elapsed_ratio=Decimal('0.5'))
        if progress['status'] in {PROGRESS_OFF_TRACK, PROGRESS_AT_RISK, PROGRESS_MISSED}:
            recs.append({'code': f'target_{target.code}', 'title': f'Review target {target.name}', 'description': f"Target progress status is {progress['status']}.", 'recommendationType': 'target_review', 'priority': 'critical' if progress['status'] == PROGRESS_OFF_TRACK else 'high', 'evidence': progress, 'affectedFacility': None, 'affectedActivityType': None, 'estimatedReduction': None, 'sourceMetric': 'targetProgress', 'generatedAt': inventory.calculated_at.isoformat() if inventory.calculated_at else None})
    return recs

def _numerator_kg(agg: dict[str, Any], numerator_type: str, category: str | None=None) -> Decimal:
    if numerator_type == 'total_emissions':
        return Decimal(agg['totalKgCo2e'])
    if numerator_type == 'scope_1':
        return Decimal(agg['scopeTotals']['scope1KgCo2e'])
    if numerator_type == 'scope_2':
        return Decimal(agg['scopeTotals']['scope2KgCo2e'])
    if numerator_type == 'scope_3':
        return Decimal(agg['scopeTotals']['scope3KgCo2e'])
    if numerator_type == 'selected_category' and category:
        for row in agg['categoryTotals']:
            if row['name'] == category:
                return Decimal(row['totalKgCo2e'])
        return Decimal('0')
    raise ValidationAppError('Unsupported intensity numerator type.')

def intensity_results(db: Session, user: User, organization_id: uuid.UUID, *, inventory_id: uuid.UUID | None=None, allow_provisional: bool=False) -> dict[str, Any]:
    from ecotrace.modules.sustainability_targets.infrastructure.models import IntensityMetricDefinition
    inventory = resolve_inventory(db, user, organization_id, inventory_id, allow_provisional=allow_provisional)
    period = db.get(ReportingPeriod, inventory.reporting_period_id)
    agg = aggregate_items(db, _load_calculated_items(db, inventory))
    defs = db.execute(select(IntensityMetricDefinition).where(IntensityMetricDefinition.organization_id == organization_id, IntensityMetricDefinition.is_active.is_(True))).scalars().all()
    results = []
    for definition in defs:
        numerator = _numerator_kg(agg, definition.numerator_type)
        denom_stmt = select(func.coalesce(func.sum(ActivityRecord.quantity), 0)).where(ActivityRecord.organization_id == organization_id, ActivityRecord.status == 'approved', ActivityRecord.is_archived.is_(False))
        if definition.denominator_activity_type_id:
            denom_stmt = denom_stmt.where(ActivityRecord.activity_type_id == definition.denominator_activity_type_id)
        if period is not None:
            denom_stmt = denom_stmt.where(ActivityRecord.reporting_period_id == period.id)
        denominator = Decimal(str(db.execute(denom_stmt).scalar_one()))
        if denominator <= 0:
            results.append({'definitionId': str(definition.id), 'code': definition.code, 'name': definition.name, 'displayUnit': definition.display_unit, 'numeratorKgCo2e': str(numerator), 'denominator': str(denominator), 'intensityValue': None, 'availability': AVAIL_UNAVAILABLE, 'warning': 'Denominator is zero; intensity cannot be calculated.'})
            continue
        results.append({'definitionId': str(definition.id), 'code': definition.code, 'name': definition.name, 'displayUnit': definition.display_unit, 'numeratorKgCo2e': str(numerator), 'denominator': str(denominator), 'intensityValue': str(numerator / denominator), 'availability': AVAIL_AVAILABLE, 'warning': None})
    return {'metadata': inventory_metadata(db, inventory), 'items': results}

def kpi_results(db: Session, user: User, organization_id: uuid.UUID, *, inventory_id: uuid.UUID | None=None, allow_provisional: bool=False) -> dict[str, Any]:
    from ecotrace.modules.sustainability_targets.infrastructure.models import EnvironmentalKpiDefinition
    inventory = resolve_inventory(db, user, organization_id, inventory_id, allow_provisional=allow_provisional)
    period = db.get(ReportingPeriod, inventory.reporting_period_id)
    agg = aggregate_items(db, _load_calculated_items(db, inventory))
    defs = db.execute(select(EnvironmentalKpiDefinition).where(EnvironmentalKpiDefinition.organization_id == organization_id, EnvironmentalKpiDefinition.is_active.is_(True))).scalars().all()
    items = []
    for definition in defs:
        value: Decimal | None = None
        availability = AVAIL_AVAILABLE
        warning = None
        if definition.kpi_type == 'total_emissions':
            value = Decimal(agg['totalKgCo2e'])
        elif definition.kpi_type == 'carbon_intensity':
            intensity = intensity_results(db, user, organization_id, inventory_id=inventory.id, allow_provisional=allow_provisional)
            if intensity['items']:
                value = Decimal(intensity['items'][0]['intensityValue']) if intensity['items'][0]['intensityValue'] is not None else None
                availability = intensity['items'][0]['availability']
                warning = intensity['items'][0]['warning']
            else:
                availability = AVAIL_UNAVAILABLE
                warning = 'No intensity metric definition available.'
        else:
            stmt = select(func.coalesce(func.sum(ActivityRecord.quantity), 0)).where(ActivityRecord.organization_id == organization_id, ActivityRecord.status == 'approved', ActivityRecord.is_archived.is_(False))
            if definition.activity_type_id:
                stmt = stmt.where(ActivityRecord.activity_type_id == definition.activity_type_id)
            if period is not None:
                stmt = stmt.where(ActivityRecord.reporting_period_id == period.id)
            value = Decimal(str(db.execute(stmt).scalar_one()))
        items.append({'definitionId': str(definition.id), 'code': definition.code, 'name': definition.name, 'kpiType': definition.kpi_type, 'unitCode': definition.unit_code, 'targetDirection': definition.target_direction, 'value': None if value is None else str(value), 'availability': availability, 'warning': warning})
    return {'metadata': inventory_metadata(db, inventory), 'items': items}
