from __future__ import annotations
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import BusinessRuleError, ValidationAppError
from ecotrace.core.lca_constants import CRADLE_TO_GATE_STAGES, DISCLAIMER, END_OF_LIFE_STAGES, LCA_ENGINE_VERSION, LCA_METHODOLOGY_VERSION, USE_PHASE_STAGES
from ecotrace.modules.carbon_accounting.application.calculation_math import compute_emission_result, q_kg
from ecotrace.modules.carbon_accounting.application.matching_service import match_emission_factor
from ecotrace.modules.carbon_inventory.application.inventory_service import _load_gwp_map
from ecotrace.modules.emission_factors.infrastructure.models import EmissionFactor
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.lifecycle_assessment.infrastructure.models import LcaCalculationItem, LcaCalculationRun, LcaFunctionalUnit, LcaInventoryInput, LcaStudy, LcaSystemBoundary
from ecotrace.modules.product_carbon_footprint.infrastructure.models import ProductCarbonFootprint
from ecotrace.modules.reference_data.application.unit_conversion import convert_between, get_unit
from ecotrace.modules.reference_data.infrastructure.models import ActivityType
from ecotrace.shared.application.audit import write_audit_log

def validate_study_completeness(db: Session, study: LcaStudy) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    fu = db.execute(select(LcaFunctionalUnit).where(LcaFunctionalUnit.lca_study_id == study.id, LcaFunctionalUnit.is_primary.is_(True))).scalar_one_or_none()
    if fu is None:
        errors.append({'code': 'missing_functional_unit', 'message': 'Primary functional unit required.'})
    elif fu.quantity <= 0:
        errors.append({'code': 'invalid_functional_unit', 'message': 'Functional unit quantity must be positive.'})
    boundary = db.execute(select(LcaSystemBoundary).where(LcaSystemBoundary.lca_study_id == study.id)).scalar_one_or_none()
    if boundary is None:
        errors.append({'code': 'missing_boundary', 'message': 'System boundary required.'})
    inputs = list(db.execute(select(LcaInventoryInput).where(LcaInventoryInput.lca_study_id == study.id)).scalars().all())
    if not inputs:
        errors.append({'code': 'missing_inventory', 'message': 'At least one inventory input required.'})
    for inp in inputs:
        if inp.allocation_factor < 0 or inp.allocation_factor > 1:
            errors.append({'code': 'invalid_allocation', 'message': f'Input {inp.id} allocation factor out of range.', 'inventoryInputId': str(inp.id)})
        if inp.allocation_method == 'custom' and (not (inp.metadata_json or {}).get('allocationReason')):
            errors.append({'code': 'custom_allocation_reason', 'message': 'Custom allocation requires a reason.', 'inventoryInputId': str(inp.id)})
        if inp.allocation_method == 'economic' and (not (inp.metadata_json or {}).get('currency')):
            errors.append({'code': 'economic_allocation_currency', 'message': 'Economic allocation requires monetary data and currency.', 'inventoryInputId': str(inp.id)})
        if inp.source_type in {'supplier_specific', 'database'} and (not inp.source_reference):
            errors.append({'code': 'missing_source_reference', 'message': 'Source reference required for supplier-specific/database inputs.', 'inventoryInputId': str(inp.id)})
        if not inp.activity_type_id:
            errors.append({'code': 'missing_activity_type', 'message': 'Activity type required for factor matching.', 'inventoryInputId': str(inp.id)})
    return {'valid': len(errors) == 0, 'blockingErrorCount': len(errors), 'errors': errors, 'inventoryInputCount': len(inputs), 'disclaimer': DISCLAIMER}

def run_lca_calculation(db: Session, user: User, study: LcaStudy, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None, partial: bool=False) -> LcaCalculationRun:
    if study.status == 'approved':
        raise BusinessRuleError('Approved studies are immutable. Use recalculate to create a new run context.')
    validation = validate_study_completeness(db, study)
    if validation['blockingErrorCount'] and (not partial):
        raise BusinessRuleError('Study validation failed.', details=validation['errors'])
    fu = db.execute(select(LcaFunctionalUnit).where(LcaFunctionalUnit.lca_study_id == study.id, LcaFunctionalUnit.is_primary.is_(True))).scalar_one()
    inputs = list(db.execute(select(LcaInventoryInput).where(LcaInventoryInput.lca_study_id == study.id)).scalars().all())
    run_number = db.execute(select(func.coalesce(func.max(LcaCalculationRun.run_number), 0)).where(LcaCalculationRun.lca_study_id == study.id)).scalar_one() + 1
    for prev in db.execute(select(LcaCalculationRun).where(LcaCalculationRun.lca_study_id == study.id, LcaCalculationRun.status.in_(['completed', 'completed_with_errors']))).scalars():
        prev.status = 'superseded'
    gwp = _load_gwp_map(db, 'IPCC_AR6')
    run = LcaCalculationRun(lca_study_id=study.id, run_number=run_number, status='running', started_at=datetime.now(UTC), triggered_by_user_id=user.id, inventory_input_count=len(inputs), calculated_input_count=0, skipped_input_count=0, failed_input_count=0, engine_version=LCA_ENGINE_VERSION, methodology_version=LCA_METHODOLOGY_VERSION)
    db.add(run)
    db.flush()
    write_audit_log(db, action='lca.calculation_started', actor_user_id=user.id, organization_id=study.organization_id, entity_type='lca_calculation_run', entity_id=str(run.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'studyId': str(study.id), 'runNumber': run_number})
    total_kg = Decimal('0')
    calculated = skipped = failed = 0
    by_stage: dict[str, Decimal] = defaultdict(lambda: Decimal('0'))
    by_material: dict[str, Decimal] = defaultdict(lambda: Decimal('0'))
    by_supplier: dict[str, Decimal] = defaultdict(lambda: Decimal('0'))
    by_facility: dict[str, Decimal] = defaultdict(lambda: Decimal('0'))
    error_summary: list[dict[str, Any]] = []
    items: list[LcaCalculationItem] = []
    biogenic_total = Decimal('0')
    activity_ids = {i.activity_type_id for i in inputs if i.activity_type_id}
    activity_types = {a.id: a for a in db.execute(select(ActivityType).where(ActivityType.id.in_(activity_ids))).scalars().all()} if activity_ids else {}
    for inp in inputs:
        item_status = 'calculated'
        errors: list[dict[str, Any]] = []
        snapshot: dict[str, Any] = {'allocationMethod': inp.allocation_method, 'allocationFactor': str(inp.allocation_factor), 'sourceType': inp.source_type, 'sourceReference': inp.source_reference, 'gwpDataset': 'IPCC_AR6', 'gwpSnapshot': {k: str(v) for k, v in gwp.items()}, 'disclaimer': DISCLAIMER}
        emission_factor_id = None
        factor_source_id = None
        factor_value = None
        factor_unit = None
        matching_priority = None
        matching_reason = None
        formula = None
        normalized_qty = None
        normalized_unit = None
        allocated_qty = None
        total_item = None
        fu_item = None
        try:
            if not inp.activity_type_id:
                raise ValidationAppError('Missing activity type.')
            activity = activity_types.get(inp.activity_type_id)
            if activity is None:
                raise ValidationAppError('Activity type not found.')
            source_unit = get_unit(db, inp.unit_code)
            match = match_emission_factor(db, organization_id=study.organization_id, activity_type_id=inp.activity_type_id, activity_date=inp.valid_from, activity_unit_code=inp.unit_code, facility_id=inp.facility_id)
            if match.selected is None:
                item_status = 'skipped' if partial else 'failed'
                errors.extend(match.errors or [{'code': 'no_factor', 'message': 'No compatible emission factor.'}])
                matching_reason = match.explanation or match.reason
                if item_status == 'skipped':
                    skipped += 1
                else:
                    failed += 1
                    error_summary.append({'inventoryInputId': str(inp.id), 'errors': errors})
            else:
                factor: EmissionFactor = match.selected
                emission_factor_id = factor.id
                factor_source_id = factor.source_id
                matching_priority = match.priority
                matching_reason = match.reason
                factor_unit_obj = get_unit(db, factor.unit_code)
                normalized_qty = convert_between(inp.quantity, source_unit, factor_unit_obj)
                normalized_unit = factor.unit_code
                allocated_qty = (normalized_qty * inp.allocation_factor).quantize(Decimal('0.00000001'))
                result = compute_emission_result(normalized_quantity=allocated_qty, normalized_unit_code=normalized_unit, factor_value=factor.factor_value, factor_unit_code=factor.unit_code, co2_factor=factor.co2_factor, ch4_factor=factor.ch4_factor, n2o_factor=factor.n2o_factor, biogenic_co2_factor=factor.biogenic_co2_factor, ch4_gwp=gwp.get('CH4'), n2o_gwp=gwp.get('N2O'), other_gases_json=factor.other_gases_json)
                total_item = result['total_kg_co2e']
                factor_value = factor.factor_value
                factor_unit = factor.unit_code
                formula = result.get('formula')
                biogenic = result.get('biogenic_co2_kg') or Decimal('0')
                biogenic_total += biogenic
                snapshot.update({'emissionFactorId': str(factor.id), 'factorValue': str(factor.factor_value) if factor.factor_value is not None else None, 'result': {k: str(v) if isinstance(v, Decimal) else v for k, v in result.items()}})
                fu_item = q_kg(total_item / fu.quantity) if fu.quantity else None
                total_kg += total_item
                by_stage[inp.lifecycle_stage] += total_item
                if inp.material_id:
                    by_material[str(inp.material_id)] += total_item
                if inp.supplier_id:
                    by_supplier[str(inp.supplier_id)] += total_item
                if inp.facility_id:
                    by_facility[str(inp.facility_id)] += total_item
                calculated += 1
                item_status = 'calculated'
        except Exception as exc:
            item_status = 'failed'
            failed += 1
            errors.append({'code': 'calculation_error', 'message': str(exc)})
            error_summary.append({'inventoryInputId': str(inp.id), 'errors': errors})
        items.append(LcaCalculationItem(calculation_run_id=run.id, lca_study_id=study.id, inventory_input_id=inp.id, lifecycle_stage=inp.lifecycle_stage, material_id=inp.material_id, supplier_id=inp.supplier_id, activity_type_id=inp.activity_type_id, emission_factor_id=emission_factor_id, factor_source_id=factor_source_id, input_quantity=inp.quantity, input_unit_code=inp.unit_code, normalized_quantity=normalized_qty, normalized_unit_code=normalized_unit, factor_value=factor_value, factor_unit_code=factor_unit, allocation_factor=inp.allocation_factor, allocated_quantity=allocated_qty, total_kg_co2e=total_item, functional_unit_kg_co2e=fu_item, matching_priority=matching_priority, matching_reason=matching_reason, calculation_formula=formula, calculation_snapshot_json=snapshot, status=item_status, validation_errors_json=errors or None))
    db.add_all(items)
    fu_total = q_kg(total_kg / fu.quantity) if fu.quantity else Decimal('0')
    cradle = q_kg(sum((by_stage[s] for s in CRADLE_TO_GATE_STAGES), Decimal('0')))
    use_phase = q_kg(sum((by_stage[s] for s in USE_PHASE_STAGES), Decimal('0')))
    eol = q_kg(sum((by_stage[s] for s in END_OF_LIFE_STAGES), Decimal('0')))
    run.calculated_input_count = calculated
    run.skipped_input_count = skipped
    run.failed_input_count = failed
    run.total_kg_co2e = q_kg(total_kg)
    run.functional_unit_kg_co2e = fu_total
    run.completed_at = datetime.now(UTC)
    run.result_summary_json = {'byLifecycleStage': {k: str(q_kg(v)) for k, v in by_stage.items()}, 'byMaterial': {k: str(q_kg(v)) for k, v in by_material.items()}, 'bySupplier': {k: str(q_kg(v)) for k, v in by_supplier.items()}, 'byFacility': {k: str(q_kg(v)) for k, v in by_facility.items()}, 'cradleToGateKgCO2e': str(cradle), 'usePhaseKgCO2e': str(use_phase), 'endOfLifeKgCO2e': str(eol), 'biogenicCO2Kg': str(q_kg(biogenic_total)), 'disclaimer': DISCLAIMER}
    run.error_summary_json = error_summary or None
    if failed and calculated:
        run.status = 'completed_with_errors'
    elif failed and (not calculated):
        run.status = 'failed'
    else:
        run.status = 'completed'
    study.latest_run_id = run.id
    if run.status in {'completed', 'completed_with_errors'}:
        study.status = 'calculated'
        pcf = ProductCarbonFootprint(organization_id=study.organization_id, lca_study_id=study.id, calculation_run_id=run.id, product_id=study.product_id, product_variant_id=study.product_variant_id, product_batch_id=study.product_batch_id, functional_unit_quantity=fu.quantity, functional_unit_code=fu.unit_code, total_kg_co2e=fu_total, cradle_to_gate_kg_co2e=cradle, use_phase_kg_co2e=use_phase, end_of_life_kg_co2e=eol, biogenic_co2_kg=q_kg(biogenic_total), status='calculated')
        db.add(pcf)
    write_audit_log(db, action='lca.calculation_completed', actor_user_id=user.id, organization_id=study.organization_id, entity_type='lca_calculation_run', entity_id=str(run.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'status': run.status, 'totalKgCO2e': str(run.total_kg_co2e)})
    return run
