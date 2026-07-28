from __future__ import annotations
from datetime import UTC, date, datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.carbon_constants import ENGINE_VERSION
from ecotrace.core.logging import get_logger
from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
from ecotrace.modules.carbon_accounting.application.calculation_math import kg_to_tonnes
from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonInventory
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reference_data.infrastructure.models import ActivityType
from ecotrace.modules.scenarios.infrastructure.models import ScenarioAssumption, ScenarioModel, ScenarioRun, ScenarioRunItem
from ecotrace.modules.sustainability_targets.infrastructure.models import EnvironmentalKpiDefinition, IntensityMetricDefinition, ReductionInitiative, SustainabilityBaseline, SustainabilityTarget, SustainabilityTargetRevision
logger = get_logger(__name__)
MARKER = 'seed:analytics:v1'

def _approve_demo_inventory(db: Session, org: Organization, actor: User) -> CarbonInventory | None:
    inventory = db.execute(select(CarbonInventory).where(CarbonInventory.organization_id == org.id, CarbonInventory.name == 'Demo Carbon Inventory 2024-01')).scalar_one_or_none()
    if inventory is None:
        return None
    if inventory.status != 'approved':
        inventory.status = 'approved'
        inventory.approved_at = datetime.now(UTC)
        inventory.approved_by_user_id = actor.id
        db.flush()
        logger.info('seed.analytics_inventory_approved', inventory_id=str(inventory.id))
    return inventory

def seed_analytics(db: Session, org: Organization, actor: User) -> None:
    inventory = _approve_demo_inventory(db, org, actor)
    if inventory is None or inventory.latest_run_id is None:
        logger.warning('seed.analytics_skipped_no_inventory')
        return
    electricity = db.execute(select(ActivityType).where(ActivityType.code == 'purchased_electricity')).scalar_one_or_none()
    intensity = db.execute(select(IntensityMetricDefinition).where(IntensityMetricDefinition.organization_id == org.id, IntensityMetricDefinition.code == 'emi_per_kwh_proxy')).scalar_one_or_none()
    if intensity is None:
        intensity = IntensityMetricDefinition(organization_id=org.id, code='emi_per_kwh_proxy', name='Emissions per electricity kWh (proxy)', description='Demo intensity using purchased electricity quantity as denominator.', numerator_type='total_emissions', denominator_activity_type_id=electricity.id if electricity else None, denominator_unit_code='kWh', display_unit='kgCO2e/kWh', aggregation_method='sum', is_active=True)
        db.add(intensity)
        db.flush()
    for code, name, kpi_type, unit in (('kpi_total_emissions', 'Total emissions', 'total_emissions', 'kgCO2e'), ('kpi_electricity', 'Purchased electricity', 'energy_consumption', 'kWh'), ('kpi_carbon_intensity', 'Carbon intensity', 'carbon_intensity', 'kgCO2e/kWh')):
        row = db.execute(select(EnvironmentalKpiDefinition).where(EnvironmentalKpiDefinition.organization_id == org.id, EnvironmentalKpiDefinition.code == code)).scalar_one_or_none()
        if row is None:
            db.add(EnvironmentalKpiDefinition(organization_id=org.id, code=code, name=name, description=f'Seeded KPI: {name}', kpi_type=kpi_type, activity_type_id=electricity.id if kpi_type == 'energy_consumption' and electricity else None, aggregation_method='sum', unit_code=unit, target_direction='decrease', is_active=True))
    db.flush()
    baseline = db.execute(select(SustainabilityBaseline).where(SustainabilityBaseline.organization_id == org.id, SustainabilityBaseline.code == 'BL-2024-CARBON')).scalar_one_or_none()
    if baseline is None:
        from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonCalculationItem
        total_kg = db.execute(select(CarbonCalculationItem.total_kg_co2e).where(CarbonCalculationItem.calculation_run_id == inventory.latest_run_id, CarbonCalculationItem.status == 'calculated')).scalars().all()
        baseline_value = sum((v or Decimal('0') for v in total_kg), Decimal('0'))
        if baseline_value <= 0:
            baseline_value = Decimal('1000')
        baseline = SustainabilityBaseline(organization_id=org.id, code='BL-2024-CARBON', name='2024 Carbon Baseline', description='Seeded primary carbon inventory baseline.', baseline_type='carbon_inventory', reporting_period_id=inventory.reporting_period_id, inventory_id=inventory.id, baseline_year=2024, baseline_value=baseline_value, baseline_unit='kgCO2e', is_primary=True, status='approved', approved_by_user_id=actor.id, approved_at=datetime.now(UTC))
        db.add(baseline)
        db.flush()
    elif baseline.status != 'approved':
        baseline.status = 'approved'
        baseline.approved_by_user_id = actor.id
        baseline.approved_at = datetime.now(UTC)
        if baseline.baseline_value is None:
            baseline.baseline_value = Decimal('1000')
        db.flush()
    baseline_value = baseline.baseline_value or Decimal('1000')
    target_specs = [('TGT-ABS-2030', 'Absolute emissions reduction 2030', 'absolute_emission_reduction', baseline_value, baseline_value * Decimal('0.7'), 2030), ('TGT-SCOPE2-2028', 'Scope 2 reduction 2028', 'absolute_emission_reduction', baseline_value * Decimal('0.4'), baseline_value * Decimal('0.25'), 2028), ('TGT-ENERGY-2027', 'Energy reduction 2027', 'energy_reduction', Decimal('10000'), Decimal('8000'), 2027)]
    targets: list[SustainabilityTarget] = []
    for code, name, ttype, base_v, tgt_v, year in target_specs:
        target_row = db.execute(select(SustainabilityTarget).where(SustainabilityTarget.organization_id == org.id, SustainabilityTarget.code == code)).scalar_one_or_none()
        if target_row is None:
            target_row = SustainabilityTarget(organization_id=org.id, code=code, name=name, description=f'Seeded target {code}', target_type=ttype, scope='scope_2' if 'SCOPE2' in code else None, baseline_id=baseline.id, baseline_value=base_v, target_value=tgt_v, target_unit='kgCO2e' if ttype != 'energy_reduction' else 'kWh', target_year=year, target_date=date(year, 12, 31), target_direction='decrease', status='active', owner_user_id=actor.id, approved_by_user_id=actor.id, approved_at=datetime.now(UTC), revision=1)
            db.add(target_row)
            db.flush()
            db.add(SustainabilityTargetRevision(target_id=target_row.id, revision=1, snapshot_json={'code': code, 'seed': MARKER}, changed_by_user_id=actor.id))
        targets.append(target_row)
    db.flush()
    initiative_specs = [('INI-RENEWABLE', 'On-site renewable electricity', 'renewable_energy', Decimal('200')), ('INI-EFFICIENCY', 'Boiler efficiency upgrade', 'energy_efficiency', Decimal('150')), ('INI-FLEET', 'Fleet route optimization', 'fleet_optimization', Decimal('80'))]
    for idx, (code, name, itype, reduction) in enumerate(initiative_specs):
        initiative_row = db.execute(select(ReductionInitiative).where(ReductionInitiative.organization_id == org.id, ReductionInitiative.code == code)).scalar_one_or_none()
        if initiative_row is None:
            db.add(ReductionInitiative(organization_id=org.id, target_id=targets[0].id if targets else None, code=code, name=name, description=f'Seeded initiative {code}', initiative_type=itype, planned_start_date=date(2025, 1, 1), planned_end_date=date(2026, 12, 31), expected_reduction_kg_co2e=reduction, expected_cost=Decimal('25000') + Decimal(idx * 5000), currency_code='EUR', status='planned' if idx == 0 else 'proposed', owner_user_id=actor.id))
    db.flush()
    existing_scenarios = db.execute(select(ScenarioModel).where(ScenarioModel.organization_id == org.id)).scalars().all()
    if len(existing_scenarios) >= 4:
        logger.info('seed.analytics_scenarios_present', count=len(existing_scenarios))
        logger.info('seed.analytics_completed')
        return
    electricity_type_id = electricity.id if electricity else None
    scenario_defs = [('SCN-RENEWABLE', 'Renewable electricity transition', 'renewable_energy_transition', Decimal('-40'), 'purchased_electricity'), ('SCN-ELEC-REDUCTION', 'Electricity demand reduction', 'electricity_reduction', Decimal('-15'), 'purchased_electricity'), ('SCN-GAS-REDUCTION', 'Natural gas reduction', 'natural_gas_reduction', Decimal('-20'), 'natural_gas_consumption'), ('SCN-CUSTOM', 'Custom activity adjustment', 'custom_activity_adjustment', Decimal('-10'), None)]
    renewable: ScenarioModel | None = None
    for code, name, stype, change_pct, type_code in scenario_defs:
        existing = db.execute(select(ScenarioModel).where(ScenarioModel.organization_id == org.id, ScenarioModel.code == code)).scalar_one_or_none()
        if existing:
            if code == 'SCN-RENEWABLE':
                renewable = existing
            continue
        activity_type_id = None
        if type_code:
            at = db.execute(select(ActivityType).where(ActivityType.code == type_code)).scalar_one_or_none()
            activity_type_id = at.id if at else electricity_type_id
        scenario = ScenarioModel(organization_id=org.id, code=code, name=name, description=f'Seeded scenario {code}', scenario_type=stype, baseline_inventory_id=inventory.id, reporting_period_id=inventory.reporting_period_id, status='ready', created_by_user_id=actor.id)
        db.add(scenario)
        db.flush()
        db.add(ScenarioAssumption(scenario_id=scenario.id, assumption_type='quantity_adjustment', activity_type_id=activity_type_id, parameter_code='quantity_change_pct', change_percentage=change_pct, unit_code='%'))
        if code == 'SCN-RENEWABLE':
            renewable = scenario
    db.flush()
    if renewable is not None:
        has_run = db.execute(select(ScenarioRun).where(ScenarioRun.scenario_id == renewable.id)).scalar_one_or_none()
        if has_run is None:
            items = list(db.execute(select(CarbonCalculationItem).where(CarbonCalculationItem.calculation_run_id == inventory.latest_run_id, CarbonCalculationItem.status == 'calculated', CarbonCalculationItem.total_kg_co2e.is_not(None))).scalars().all())
            assumption = db.execute(select(ScenarioAssumption).where(ScenarioAssumption.scenario_id == renewable.id)).scalar_one()
            activities = {a.id: a for a in db.execute(select(ActivityRecord).where(ActivityRecord.id.in_({i.activity_record_id for i in items}))).scalars().all()}
            factor = Decimal('1') + (assumption.change_percentage or Decimal('0')) / Decimal('100')
            baseline_total = Decimal('0')
            scenario_total = Decimal('0')
            run = ScenarioRun(scenario_id=renewable.id, run_number=1, status='completed', started_at=datetime.now(UTC), completed_at=datetime.now(UTC), triggered_by_user_id=actor.id, engine_version=ENGINE_VERSION)
            db.add(run)
            db.flush()
            for item in items:
                activity = activities.get(item.activity_record_id)
                baseline_qty = item.normalized_quantity or item.activity_quantity
                match = activity is not None and assumption.activity_type_id and (activity.activity_type_id == assumption.activity_type_id)
                scenario_qty = baseline_qty * factor if match else baseline_qty
                baseline_kg = item.total_kg_co2e or Decimal('0')
                scenario_kg = baseline_kg * (scenario_qty / baseline_qty) if baseline_qty else baseline_kg
                baseline_total += baseline_kg
                scenario_total += scenario_kg
                db.add(ScenarioRunItem(scenario_run_id=run.id, baseline_calculation_item_id=item.id, activity_record_id=item.activity_record_id, facility_id=activity.facility_id if activity else None, activity_type_id=activity.activity_type_id if activity else None, scope=item.scope, category=item.category, baseline_quantity=baseline_qty, scenario_quantity=scenario_qty, unit_code=item.normalized_unit_code or item.activity_unit_code, baseline_kg_co2e=baseline_kg, scenario_kg_co2e=scenario_kg, reduction_kg_co2e=baseline_kg - scenario_kg, applied_assumption_json={'seed': MARKER} if match else None))
            reduction = baseline_total - scenario_total
            run.baseline_total_kg_co2e = baseline_total
            run.scenario_total_kg_co2e = scenario_total
            run.reduction_kg_co2e = reduction
            run.reduction_percentage = None if baseline_total == 0 else reduction / baseline_total * Decimal('100')
            run.result_summary_json = {'baselineTotalKgCo2e': str(baseline_total), 'scenarioTotalKgCo2e': str(scenario_total), 'reductionKgCo2e': str(reduction), 'baselineTotalTCo2e': str(kg_to_tonnes(baseline_total)), 'scenarioTotalTCo2e': str(kg_to_tonnes(scenario_total)), 'seeded': True}
            renewable.status = 'calculated'
            db.flush()
    logger.info('seed.analytics_completed')
