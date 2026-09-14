from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.calculation_math import (
    CALCULATION_TYPE_MULTIPLY,
    CALCULATION_TYPE_PURCHASED_ELECTRICITY_INDIRECT,
    CALCULATION_TYPE_STATIONARY_COMBUSTION_CO2,
    ENGINE_VERSION,
    FORMULA_VERSION,
    multiply_activity_by_factor,
)
from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamAllocationResult,
    CbamCalculationDefinition,
    CbamCalculationResult,
    CbamCalculationRun,
    CbamFactorResolution,
    CbamPurchasedInputRecord,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

RESOLVED_OK = frozenset({'RESOLVED_PRIMARY', 'RESOLVED_DEFAULT'})


class CalculationDefinitionResponse(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    calculation_type: str
    source_type: str
    factor_definition_id: uuid.UUID | None
    output_unit: str | None
    formula_version: str
    description: str | None
    status: str


class CalculationRunCreate(CamelModel):
    pass


class CalculationRunExecuteRequest(CamelModel):
    calculation_definition_ids: list[uuid.UUID] | None = None
    allow_unallocated_activity: bool = True


class CalculationRunResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    status: str
    calculation_version: str
    started_at: datetime | None
    completed_at: datetime | None
    error_summary: str | None
    calculated_count: int
    blocked_count: int
    invalid_count: int
    primary_factor_count: int
    default_factor_count: int
    same_unit_total: Decimal | None = None
    same_unit_total_unit: str | None = None


class CalculationResultResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    calculation_run_id: uuid.UUID
    calculation_definition_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    allocation_result_id: uuid.UUID | None
    factor_resolution_id: uuid.UUID
    source_quantity: Decimal | None
    source_unit: str | None
    factor_value: Decimal | None
    factor_unit: str | None
    result_value: Decimal | None
    result_unit: str | None
    calculation_type: str
    formula_version: str
    status: str
    error_code: str | None
    error_message: str | None
    input_fingerprint: str
    is_current: bool
    superseded_at: datetime | None
    factor_resolution_status: str | None


def _def_response(row: CbamCalculationDefinition) -> CalculationDefinitionResponse:
    return CalculationDefinitionResponse.model_validate(row)


def _run_response(
    db: Session, row: CbamCalculationRun, *, include_total: bool = True
) -> CalculationRunResponse:
    same_total: Decimal | None = None
    same_unit: str | None = None
    if include_total:
        results = db.execute(
            select(CbamCalculationResult).where(
                CbamCalculationResult.calculation_run_id == row.id,
                CbamCalculationResult.status == 'CALCULATED',
                CbamCalculationResult.result_value.is_not(None),
                CbamCalculationResult.result_unit.is_not(None),
            )
        ).scalars().all()
        units = {r.result_unit for r in results if r.result_unit}
        if len(units) == 1:
            same_unit = next(iter(units))
            same_total = sum((r.result_value for r in results if r.result_value is not None), Decimal('0'))
    return CalculationRunResponse(
        id=row.id,
        organization_id=row.organization_id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        status=row.status,
        calculation_version=row.calculation_version,
        started_at=row.started_at,
        completed_at=row.completed_at,
        error_summary=row.error_summary,
        calculated_count=row.calculated_count,
        blocked_count=row.blocked_count,
        invalid_count=row.invalid_count,
        primary_factor_count=row.primary_factor_count,
        default_factor_count=row.default_factor_count,
        same_unit_total=same_total,
        same_unit_total_unit=same_unit,
    )


def _result_response(row: CbamCalculationResult) -> CalculationResultResponse:
    return CalculationResultResponse.model_validate(row)


def ensure_platform_calculation_definitions(db: Session) -> None:
    from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
    from ecotrace.modules.cbam.application.stationary_combustion_math import (
        FORMULA_VERSION_STATIONARY_COMBUSTION_CO2,
    )
    from ecotrace.modules.cbam.infrastructure.models import CbamFactorDefinition

    ensure_platform_factor_catalog(db)
    generic = db.execute(
        select(CbamCalculationDefinition.id).where(
            CbamCalculationDefinition.code == 'MULTIPLY_ACTIVITY_BY_GENERIC_EF'
        )
    ).scalar_one_or_none()
    if generic is None:
        ef = db.execute(
            select(CbamFactorDefinition).where(CbamFactorDefinition.code == 'GENERIC_EMISSION_FACTOR')
        ).scalar_one()
        embedded = db.execute(
            select(CbamFactorDefinition).where(
                CbamFactorDefinition.code == 'SUPPLIER_EMBEDDED_EMISSION'
            )
        ).scalar_one()
        seeds = (
            (
                'c1000000-0000-4000-8000-000000000001',
                'MULTIPLY_ACTIVITY_BY_GENERIC_EF',
                'Multiply activity quantity by generic emission factor',
                'ACTIVITY_RECORD',
                ef.id,
            ),
            (
                'c1000000-0000-4000-8000-000000000002',
                'MULTIPLY_ALLOCATION_BY_GENERIC_EF',
                'Multiply allocated quantity by generic emission factor',
                'ALLOCATION_RESULT',
                ef.id,
            ),
            (
                'c1000000-0000-4000-8000-000000000003',
                'MULTIPLY_PURCHASED_BY_GENERIC_EF',
                'Multiply purchased-input consumed quantity by generic emission factor',
                'PURCHASED_INPUT_RECORD',
                ef.id,
            ),
            (
                'c1000000-0000-4000-8000-000000000004',
                'MULTIPLY_PURCHASED_BY_SUPPLIER_EMBEDDED',
                'Multiply purchased-input consumed quantity by resolved supplier embedded intensity',
                'PURCHASED_INPUT_RECORD',
                embedded.id,
            ),
        )
        for sid, code, name, source_type, factor_id in seeds:
            db.add(
                CbamCalculationDefinition(
                    id=uuid.UUID(sid),
                    code=code,
                    name=name,
                    calculation_type=CALCULATION_TYPE_MULTIPLY,
                    source_type=source_type,
                    factor_definition_id=factor_id,
                    output_unit=None,
                    formula_version=FORMULA_VERSION,
                    description='Metadata-only definition. No numeric factors seeded.',
                    status='ACTIVE',
                )
            )
        db.flush()

    sc = db.execute(
        select(CbamCalculationDefinition.id).where(
            CbamCalculationDefinition.code == 'STATIONARY_COMBUSTION_CO2_V1'
        )
    ).scalar_one_or_none()
    if sc is None:
        db.add(
            CbamCalculationDefinition(
                id=uuid.UUID('c1000000-0000-4000-8000-000000000010'),
                code='STATIONARY_COMBUSTION_CO2_V1',
                name='Stationary combustion fossil CO2 (V1)',
                calculation_type=CALCULATION_TYPE_STATIONARY_COMBUSTION_CO2,
                source_type='ACTIVITY_RECORD',
                factor_definition_id=None,
                output_unit='tCO2',
                formula_version=FORMULA_VERSION_STATIONARY_COMBUSTION_CO2,
                description=(
                    'Typed stationary-combustion orchestration. Parameters come from the '
                    'fuel catalog; density must be supplied explicitly for VOLUME fuels. '
                    'Results persist in cbam_stationary_combustion_results.'
                ),
                status='ACTIVE',
            )
        )
        db.flush()

    pe = db.execute(
        select(CbamCalculationDefinition.id).where(
            CbamCalculationDefinition.code == 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1'
        )
    ).scalar_one_or_none()
    if pe is None:
        from ecotrace.modules.cbam.application.purchased_electricity_constants import (
            FORMULA_VERSION as PE_FORMULA_VERSION,
        )
        from ecotrace.modules.cbam.application.purchased_electricity_constants import (
            RESULT_UNIT as PE_RESULT_UNIT,
        )

        db.add(
            CbamCalculationDefinition(
                id=uuid.UUID('c1000000-0000-4000-8000-000000000011'),
                code='PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1',
                name='Purchased electricity indirect emissions (V1)',
                calculation_type=CALCULATION_TYPE_PURCHASED_ELECTRICITY_INDIRECT,
                source_type='ACTIVITY_RECORD',
                factor_definition_id=None,
                output_unit=PE_RESULT_UNIT,
                formula_version=PE_FORMULA_VERSION,
                description=(
                    'Typed purchased-electricity indirect emissions. '
                    'Formula: electricity_MWh × factor. Exported electricity is stored '
                    'separately and not subtracted. No platform Turkey default is seeded '
                    'without authoritative provenance. Results in '
                    'cbam_purchased_electricity_results.'
                ),
                status='ACTIVE',
            )
        )
        db.flush()


def list_calculation_definitions(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[CalculationDefinitionResponse]:
    require_cbam_view(db, user, organization_id)
    ensure_platform_calculation_definitions(db)
    stmt = select(CbamCalculationDefinition).where(
        CbamCalculationDefinition.status != 'ARCHIVED'
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamCalculationDefinition.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_def_response(r) for r in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def create_calculation_run(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> CalculationRunResponse:
    require_cbam_configure(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    ensure_platform_calculation_definitions(db)
    row = CbamCalculationRun(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        status='DRAFT',
        calculation_version=ENGINE_VERSION,
        created_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action='cbam.calculation_run.created',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_calculation_run',
        entity_id=str(row.id),
        metadata={
            'reportingPeriodBindingId': str(binding_id),
            'calculationVersion': ENGINE_VERSION,
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _run_response(db, row)


def _get_run(db: Session, organization_id: uuid.UUID, run_id: uuid.UUID) -> CbamCalculationRun:
    row = db.execute(
        select(CbamCalculationRun).where(
            CbamCalculationRun.id == run_id,
            CbamCalculationRun.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Calculation run not found.')
    return row


def get_calculation_run(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    run_id: uuid.UUID,
) -> CalculationRunResponse:
    require_cbam_view(db, user, organization_id)
    return _run_response(db, _get_run(db, organization_id, run_id))


def list_calculation_runs(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[CalculationRunResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamCalculationRun).where(
        CbamCalculationRun.organization_id == organization_id,
        CbamCalculationRun.reporting_period_binding_id == binding_id,
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamCalculationRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_run_response(db, r) for r in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def _fingerprint(
    *,
    binding_id: uuid.UUID,
    definition_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    allocation_result_id: uuid.UUID | None,
    factor_resolution_id: uuid.UUID,
    formula_version: str,
) -> str:
    alloc = str(allocation_result_id) if allocation_result_id else '-'
    return (
        f'{binding_id}:{definition_id}:{source_type}:{source_id}:'
        f'{alloc}:{factor_resolution_id}:{formula_version}'
    )


def _supersede_current(db: Session, organization_id: uuid.UUID, fingerprint: str) -> None:
    now = datetime.now(UTC)
    rows = db.execute(
        select(CbamCalculationResult).where(
            CbamCalculationResult.organization_id == organization_id,
            CbamCalculationResult.input_fingerprint == fingerprint,
            CbamCalculationResult.is_current.is_(True),
        )
    ).scalars().all()
    for row in rows:
        row.is_current = False
        row.superseded_at = now


def _resolve_source_quantity(
    db: Session,
    *,
    organization_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    allow_unallocated_activity: bool,
) -> tuple[Decimal | None, str | None, uuid.UUID | None, str | None, str | None]:
    if source_type == 'ALLOCATION_RESULT':
        alloc = db.execute(
            select(CbamAllocationResult).where(
                CbamAllocationResult.id == source_id,
                CbamAllocationResult.organization_id == organization_id,
                CbamAllocationResult.is_current.is_(True),
            )
        ).scalar_one_or_none()
        if alloc is None:
            return None, None, None, 'INVALID_INPUT', 'Allocation result not found or not current.'
        return (
            alloc.allocated_quantity,
            alloc.allocated_unit,
            alloc.id,
            None,
            None,
        )

    if source_type == 'ACTIVITY_RECORD':
        activity = db.execute(
            select(CbamActivityRecord).where(
                CbamActivityRecord.id == source_id,
                CbamActivityRecord.organization_id == organization_id,
                CbamActivityRecord.status == 'active',
            )
        ).scalar_one_or_none()
        if activity is None:
            return None, None, None, 'INVALID_INPUT', 'Activity record not found or archived.'
        if not allow_unallocated_activity:
            return (
                None,
                None,
                None,
                'BLOCKED',
                'Allocation is required. Unallocated activity calculation is not allowed for this run.',
            )
        return activity.quantity, activity.unit, None, None, None

    if source_type == 'PURCHASED_INPUT_RECORD':
        purchased = db.execute(
            select(CbamPurchasedInputRecord).where(
                CbamPurchasedInputRecord.id == source_id,
                CbamPurchasedInputRecord.organization_id == organization_id,
                CbamPurchasedInputRecord.status == 'active',
            )
        ).scalar_one_or_none()
        if purchased is None:
            return None, None, None, 'INVALID_INPUT', 'Purchased input not found or archived.'
        if purchased.consumed_quantity is None:
            return (
                None,
                None,
                None,
                'INVALID_INPUT',
                'Consumed quantity is required; purchased quantity is never substituted.',
            )
        consumed_unit = purchased.consumed_unit or purchased.unit
        return purchased.consumed_quantity, consumed_unit, None, None, None

    return None, None, None, 'UNSUPPORTED_FORMULA', f'Unsupported source type {source_type}.'


def _map_resolution_block(status: str) -> tuple[str, str, str]:
    if status == 'AMBIGUOUS':
        return (
            'AMBIGUOUS_FACTOR',
            'AMBIGUOUS_FACTOR',
            'More than one factor matches this record.',
        )
    if status == 'UNRESOLVED':
        return 'UNRESOLVED_FACTOR', 'UNRESOLVED_FACTOR', 'Factor could not be resolved.'
    if status == 'INCOMPATIBLE_UNIT':
        return 'INCOMPATIBLE_UNIT', 'INCOMPATIBLE_UNIT', 'Units do not match.'
    if status in {'OUTSIDE_VALIDITY', 'BLOCKED'}:
        return 'BLOCKED', 'BLOCKED', f'Factor resolution is blocked ({status}).'
    return 'BLOCKED', 'BLOCKED', f'Factor resolution is not usable for calculation ({status}).'


def _persist_result(
    db: Session,
    *,
    run: CbamCalculationRun,
    definition: CbamCalculationDefinition,
    resolution: CbamFactorResolution,
    user: User,
    source_quantity: Decimal | None,
    source_unit: str | None,
    allocation_result_id: uuid.UUID | None,
    factor_value: Decimal | None,
    factor_unit: str | None,
    result_value: Decimal | None,
    result_unit: str | None,
    status: str,
    error_code: str | None,
    error_message: str | None,
    request_id: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> CbamCalculationResult:
    fingerprint = _fingerprint(
        binding_id=run.reporting_period_binding_id,
        definition_id=definition.id,
        source_type=resolution.source_type,
        source_id=resolution.source_id,
        allocation_result_id=allocation_result_id,
        factor_resolution_id=resolution.id,
        formula_version=definition.formula_version,
    )
    _supersede_current(db, run.organization_id, fingerprint)
    row = CbamCalculationResult(
        organization_id=run.organization_id,
        calculation_run_id=run.id,
        calculation_definition_id=definition.id,
        source_type=resolution.source_type,
        source_id=resolution.source_id,
        allocation_result_id=allocation_result_id,
        factor_resolution_id=resolution.id,
        source_quantity=source_quantity,
        source_unit=source_unit,
        factor_value=factor_value,
        factor_unit=factor_unit,
        result_value=result_value,
        result_unit=result_unit,
        calculation_type=definition.calculation_type,
        formula_version=definition.formula_version,
        status=status,
        error_code=error_code,
        error_message=error_message,
        input_fingerprint=fingerprint,
        is_current=True,
        factor_resolution_status=resolution.resolution_status,
        created_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    action = (
        'cbam.calculation_result.created'
        if status == 'CALCULATED'
        else 'cbam.calculation_result.blocked'
    )
    write_audit_log(
        db,
        action=action,
        actor_user_id=user.id,
        organization_id=run.organization_id,
        entity_type='cbam_calculation_result',
        entity_id=str(row.id),
        metadata={
            'calculationRunId': str(run.id),
            'calculationDefinitionId': str(definition.id),
            'sourceType': resolution.source_type,
            'sourceId': str(resolution.source_id),
            'allocationResultId': str(allocation_result_id) if allocation_result_id else None,
            'factorResolutionId': str(resolution.id),
            'status': status,
            'resultValue': str(result_value) if result_value is not None else None,
            'resultUnit': result_unit,
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


def execute_calculation_run(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: CalculationRunExecuteRequest | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> CalculationRunResponse:
    require_cbam_configure(db, user, organization_id)
    run = _get_run(db, organization_id, run_id)
    if run.status not in {'DRAFT', 'FAILED', 'PARTIALLY_COMPLETED', 'COMPLETED'}:
        if run.status == 'RUNNING':
            raise ValidationAppError('Calculation run is already running.')
        if run.status == 'ARCHIVED':
            raise ValidationAppError('Archived calculation runs cannot be executed.')

    payload = payload or CalculationRunExecuteRequest()
    ensure_platform_calculation_definitions(db)

    def_stmt = select(CbamCalculationDefinition).where(
        CbamCalculationDefinition.status == 'ACTIVE'
    )
    if payload.calculation_definition_ids:
        def_stmt = def_stmt.where(
            CbamCalculationDefinition.id.in_(payload.calculation_definition_ids)
        )
    definitions = list(db.execute(def_stmt.order_by(CbamCalculationDefinition.code)).scalars())
    if not definitions:
        raise ValidationAppError('No active calculation definitions available for execution.')

    run.status = 'RUNNING'
    run.started_at = datetime.now(UTC)
    run.completed_at = None
    run.error_summary = None
    run.calculated_count = 0
    run.blocked_count = 0
    run.invalid_count = 0
    run.primary_factor_count = 0
    run.default_factor_count = 0
    db.flush()

    write_audit_log(
        db,
        action='cbam.calculation_run.executed',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_calculation_run',
        entity_id=str(run.id),
        metadata={
            'definitionIds': [str(d.id) for d in definitions],
            'allowUnallocatedActivity': payload.allow_unallocated_activity,
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    for definition in definitions:
        if definition.calculation_type != CALCULATION_TYPE_MULTIPLY:
            continue

        resolutions = db.execute(
            select(CbamFactorResolution).where(
                CbamFactorResolution.organization_id == organization_id,
                CbamFactorResolution.reporting_period_binding_id
                == run.reporting_period_binding_id,
                CbamFactorResolution.factor_definition_id == definition.factor_definition_id,
                CbamFactorResolution.source_type == definition.source_type,
                CbamFactorResolution.is_current.is_(True),
            )
        ).scalars().all()

        for resolution in resolutions:
            if definition.formula_version != FORMULA_VERSION or (
                definition.calculation_type != CALCULATION_TYPE_MULTIPLY
            ):
                _persist_result(
                    db,
                    run=run,
                    definition=definition,
                    resolution=resolution,
                    user=user,
                    source_quantity=None,
                    source_unit=None,
                    allocation_result_id=None,
                    factor_value=None,
                    factor_unit=None,
                    result_value=None,
                    result_unit=None,
                    status='UNSUPPORTED_FORMULA',
                    error_code='UNSUPPORTED_FORMULA',
                    error_message='Formula is not supported.',
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                run.blocked_count += 1
                continue

            if resolution.resolution_status not in RESOLVED_OK:
                status, code, message = _map_resolution_block(resolution.resolution_status)
                _persist_result(
                    db,
                    run=run,
                    definition=definition,
                    resolution=resolution,
                    user=user,
                    source_quantity=None,
                    source_unit=None,
                    allocation_result_id=(
                        resolution.source_id
                        if resolution.source_type == 'ALLOCATION_RESULT'
                        else None
                    ),
                    factor_value=resolution.selected_value,
                    factor_unit=resolution.selected_unit,
                    result_value=None,
                    result_unit=None,
                    status=status,
                    error_code=code,
                    error_message=message,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                if status in {'INVALID_INPUT'}:
                    run.invalid_count += 1
                else:
                    run.blocked_count += 1
                continue

            if resolution.selected_value is None or not resolution.selected_unit:
                _persist_result(
                    db,
                    run=run,
                    definition=definition,
                    resolution=resolution,
                    user=user,
                    source_quantity=None,
                    source_unit=None,
                    allocation_result_id=None,
                    factor_value=None,
                    factor_unit=None,
                    result_value=None,
                    result_unit=None,
                    status='UNRESOLVED_FACTOR',
                    error_code='UNRESOLVED_FACTOR',
                    error_message='Resolved factor is missing value/unit.',
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                run.blocked_count += 1
                continue

            qty, unit, alloc_id, err_code, err_msg = _resolve_source_quantity(
                db,
                organization_id=organization_id,
                source_type=resolution.source_type,
                source_id=resolution.source_id,
                allow_unallocated_activity=payload.allow_unallocated_activity,
            )
            if err_code is not None:
                status = err_code if err_code in {
                    'INVALID_INPUT',
                    'INCOMPATIBLE_UNIT',
                    'UNSUPPORTED_FORMULA',
                    'BLOCKED',
                } else 'BLOCKED'
                _persist_result(
                    db,
                    run=run,
                    definition=definition,
                    resolution=resolution,
                    user=user,
                    source_quantity=qty,
                    source_unit=unit,
                    allocation_result_id=alloc_id,
                    factor_value=resolution.selected_value,
                    factor_unit=resolution.selected_unit,
                    result_value=None,
                    result_unit=None,
                    status=status,
                    error_code=err_code,
                    error_message=err_msg,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                if status == 'INVALID_INPUT':
                    run.invalid_count += 1
                else:
                    run.blocked_count += 1
                continue

            assert qty is not None and unit is not None
            outcome = multiply_activity_by_factor(
                activity_quantity=qty,
                activity_unit=unit,
                factor_value=resolution.selected_value,
                factor_unit=resolution.selected_unit,
            )
            if not outcome.ok:
                status = outcome.error_code or 'BLOCKED'
                if status not in {
                    'CALCULATED',
                    'BLOCKED',
                    'INVALID_INPUT',
                    'INCOMPATIBLE_UNIT',
                    'UNRESOLVED_FACTOR',
                    'AMBIGUOUS_FACTOR',
                    'UNSUPPORTED_FORMULA',
                }:
                    status = 'BLOCKED'
                _persist_result(
                    db,
                    run=run,
                    definition=definition,
                    resolution=resolution,
                    user=user,
                    source_quantity=qty,
                    source_unit=unit,
                    allocation_result_id=alloc_id,
                    factor_value=resolution.selected_value,
                    factor_unit=resolution.selected_unit,
                    result_value=None,
                    result_unit=None,
                    status=status,
                    error_code=outcome.error_code,
                    error_message=outcome.error_message,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                if status == 'INVALID_INPUT':
                    run.invalid_count += 1
                else:
                    run.blocked_count += 1
                continue

            _persist_result(
                db,
                run=run,
                definition=definition,
                resolution=resolution,
                user=user,
                source_quantity=qty,
                source_unit=unit,
                allocation_result_id=alloc_id,
                factor_value=resolution.selected_value,
                factor_unit=resolution.selected_unit,
                result_value=outcome.result_value,
                result_unit=outcome.result_unit,
                status='CALCULATED',
                error_code=None,
                error_message=None,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            run.calculated_count += 1
            if resolution.resolution_status == 'RESOLVED_PRIMARY':
                run.primary_factor_count += 1
            elif resolution.resolution_status == 'RESOLVED_DEFAULT':
                run.default_factor_count += 1

    total = run.calculated_count + run.blocked_count + run.invalid_count
    run.completed_at = datetime.now(UTC)
    if total == 0:
        run.status = 'FAILED'
        run.error_summary = 'No eligible factor resolutions found for active definitions.'
    elif run.calculated_count == total:
        run.status = 'COMPLETED'
    elif run.calculated_count == 0:
        run.status = 'FAILED'
        run.error_summary = 'All eligible records were blocked or invalid.'
    else:
        run.status = 'PARTIALLY_COMPLETED'

    write_audit_log(
        db,
        action='cbam.calculation_run.completed',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_calculation_run',
        entity_id=str(run.id),
        metadata={
            'status': run.status,
            'calculatedCount': run.calculated_count,
            'blockedCount': run.blocked_count,
            'invalidCount': run.invalid_count,
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(run)
    return _run_response(db, run)


def list_calculation_results(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    run_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    current_only: bool = True,
) -> Page[CalculationResultResponse]:
    require_cbam_view(db, user, organization_id)
    _get_run(db, organization_id, run_id)
    stmt = select(CbamCalculationResult).where(
        CbamCalculationResult.organization_id == organization_id,
        CbamCalculationResult.calculation_run_id == run_id,
    )
    if current_only:
        stmt = stmt.where(CbamCalculationResult.is_current.is_(True))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamCalculationResult.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_result_response(r) for r in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def get_calculation_result(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    result_id: uuid.UUID,
) -> CalculationResultResponse:
    require_cbam_view(db, user, organization_id)
    row = db.execute(
        select(CbamCalculationResult).where(
            CbamCalculationResult.id == result_id,
            CbamCalculationResult.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Calculation result not found.')
    return _result_response(row)


def recalculate_result(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    result_id: uuid.UUID,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> CalculationResultResponse:
    require_cbam_configure(db, user, organization_id)
    old = db.execute(
        select(CbamCalculationResult).where(
            CbamCalculationResult.id == result_id,
            CbamCalculationResult.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if old is None:
        raise NotFoundError('Calculation result not found.')
    run = _get_run(db, organization_id, old.calculation_run_id)
    definition = db.execute(
        select(CbamCalculationDefinition).where(
            CbamCalculationDefinition.id == old.calculation_definition_id
        )
    ).scalar_one()
    resolution = db.execute(
        select(CbamFactorResolution).where(
            CbamFactorResolution.id == old.factor_resolution_id,
            CbamFactorResolution.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if resolution is None or not resolution.is_current:
        resolution = db.execute(
            select(CbamFactorResolution).where(
                CbamFactorResolution.organization_id == organization_id,
                CbamFactorResolution.reporting_period_binding_id
                == run.reporting_period_binding_id,
                CbamFactorResolution.source_type == old.source_type,
                CbamFactorResolution.source_id == old.source_id,
                CbamFactorResolution.factor_definition_id == definition.factor_definition_id,
                CbamFactorResolution.is_current.is_(True),
            )
        ).scalar_one_or_none()
    if resolution is None:
        raise ValidationAppError('No current factor resolution available for recalculation.')

    allow_unallocated = old.allocation_result_id is None
    if resolution.resolution_status not in RESOLVED_OK:
        status, code, message = _map_resolution_block(resolution.resolution_status)
        row = _persist_result(
            db,
            run=run,
            definition=definition,
            resolution=resolution,
            user=user,
            source_quantity=None,
            source_unit=None,
            allocation_result_id=old.allocation_result_id,
            factor_value=resolution.selected_value,
            factor_unit=resolution.selected_unit,
            result_value=None,
            result_unit=None,
            status=status,
            error_code=code,
            error_message=message,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    else:
        qty, unit, alloc_id, err_code, err_msg = _resolve_source_quantity(
            db,
            organization_id=organization_id,
            source_type=resolution.source_type,
            source_id=resolution.source_id,
            allow_unallocated_activity=allow_unallocated,
        )
        if err_code is not None:
            status = err_code if err_code in {
                'INVALID_INPUT',
                'INCOMPATIBLE_UNIT',
                'UNSUPPORTED_FORMULA',
                'BLOCKED',
            } else 'BLOCKED'
            row = _persist_result(
                db,
                run=run,
                definition=definition,
                resolution=resolution,
                user=user,
                source_quantity=qty,
                source_unit=unit,
                allocation_result_id=alloc_id,
                factor_value=resolution.selected_value,
                factor_unit=resolution.selected_unit,
                result_value=None,
                result_unit=None,
                status=status,
                error_code=err_code,
                error_message=err_msg,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        else:
            assert qty is not None and unit is not None and resolution.selected_value is not None
            assert resolution.selected_unit
            outcome = multiply_activity_by_factor(
                activity_quantity=qty,
                activity_unit=unit,
                factor_value=resolution.selected_value,
                factor_unit=resolution.selected_unit,
            )
            if not outcome.ok:
                status = outcome.error_code or 'BLOCKED'
                row = _persist_result(
                    db,
                    run=run,
                    definition=definition,
                    resolution=resolution,
                    user=user,
                    source_quantity=qty,
                    source_unit=unit,
                    allocation_result_id=alloc_id,
                    factor_value=resolution.selected_value,
                    factor_unit=resolution.selected_unit,
                    result_value=None,
                    result_unit=None,
                    status=status,
                    error_code=outcome.error_code,
                    error_message=outcome.error_message,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            else:
                row = _persist_result(
                    db,
                    run=run,
                    definition=definition,
                    resolution=resolution,
                    user=user,
                    source_quantity=qty,
                    source_unit=unit,
                    allocation_result_id=alloc_id,
                    factor_value=resolution.selected_value,
                    factor_unit=resolution.selected_unit,
                    result_value=outcome.result_value,
                    result_unit=outcome.result_unit,
                    status='CALCULATED',
                    error_code=None,
                    error_message=None,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

    write_audit_log(
        db,
        action='cbam.calculation_result.recalculated',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_calculation_result',
        entity_id=str(row.id),
        metadata={
            'previousResultId': str(old.id),
            'status': row.status,
            'factorResolutionId': str(resolution.id),
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _result_response(row)
