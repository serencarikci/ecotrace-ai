from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.modules.cbam.application.calculation_math import (
    CALCULATION_TYPE_STATIONARY_COMBUSTION_CO2,
    ENGINE_VERSION,
)
from ecotrace.modules.cbam.application.catalogs import (
    MASS_ACTIVITY_UNITS,
    VOLUME_ACTIVITY_UNITS,
)
from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.permissions import require_cbam_configure
from ecotrace.modules.cbam.application.stationary_combustion_catalog_service import (
    RESOLUTION_AMBIGUOUS,
    RESOLUTION_RESOLVED,
    RESOLUTION_UNRESOLVED,
    resolve_stationary_combustion_parameters,
)
from ecotrace.modules.cbam.application.stationary_combustion_current_result_service import (
    set_current_result_pointer,
)
from ecotrace.modules.cbam.application.stationary_combustion_eligibility import (
    ELIGIBLE_STATIONARY_COMBUSTION_ACTIVITY_TYPES,
)
from ecotrace.modules.cbam.application.stationary_combustion_math import (
    FORMULA_VERSION_STATIONARY_COMBUSTION_CO2,
    RESULT_UNIT_TCO2,
    ParameterProvenance,
    QuantifiedParameter,
    StationaryCombustionInputs,
    calculate_stationary_combustion_co2,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamCalculationDefinition,
    CbamCalculationRun,
    CbamStationaryCombustionParameterSet,
    CbamStationaryCombustionResult,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel

STATIONARY_COMBUSTION_DEFINITION_CODE = 'STATIONARY_COMBUSTION_CO2_V1'

DENSITY_COMMAND_PROVENANCE = ParameterProvenance(
    source_document='Execution command (explicit density)',
    source_table='StationaryCombustionExecutionCommand.density',
    dataset_version='command',
    source_reference='Caller-supplied density; not a catalog default',
)


class StationaryCombustionExecutionCommand(CamelModel):
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    activity_record_id: uuid.UUID
    fuel_code: str
    reference_date: date
    density_value: Decimal | None = None
    density_unit: str | None = None
    dataset_version: str | None = None
    requested_by_user_id: uuid.UUID | None = None
    calculation_run_id: uuid.UUID | None = None
    client_request_id: uuid.UUID | None = None
    request_fingerprint: str | None = None


class StationaryCombustionResultResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    calculation_run_id: uuid.UUID
    calculation_definition_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    activity_record_id: uuid.UUID
    fuel_id: uuid.UUID
    parameter_set_id: uuid.UUID
    calculation_type: str
    formula_version: str
    fuel_code: str
    fuel_name: str
    input_basis: str
    activity_quantity: Decimal
    activity_unit: str
    density_value: Decimal | None
    density_unit: str | None
    client_request_id: uuid.UUID | None = None
    request_fingerprint: str | None = None
    calculation_reference_date: date | None = None
    net_calorific_value: Decimal
    net_calorific_value_unit: str
    fossil_co2_emission_factor: Decimal
    fossil_co2_emission_factor_unit: str
    oxidation_factor: Decimal
    dataset_code: str
    dataset_version: str
    valid_from: date
    valid_until: date | None
    ncv_reference_source_id: uuid.UUID
    ncv_source_document: str
    ncv_source_table: str
    co2_reference_source_id: uuid.UUID
    co2_source_document: str
    co2_source_table: str
    oxidation_reference_source_id: uuid.UUID
    oxidation_source_document: str
    oxidation_source_table: str
    fuel_mass_kg: Decimal
    fuel_mass_gg: Decimal
    energy_content_tj: Decimal
    fossil_co2_kg: Decimal
    fossil_co2_tonnes: Decimal
    result_value: Decimal
    result_unit: str
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    is_current: bool = False
    is_stale: bool = False


class StationaryCombustionExecutionResponse(CamelModel):
    calculation_run_id: uuid.UUID
    calculation_run_status: str
    result: StationaryCombustionResultResponse


def _result_response(
    row: CbamStationaryCombustionResult,
    *,
    is_current: bool = False,
    is_stale: bool = False,
) -> StationaryCombustionResultResponse:
    data = StationaryCombustionResultResponse.model_validate(row)
    return data.model_copy(update={'is_current': is_current, 'is_stale': is_stale})


def get_stationary_combustion_result(
    db: Session,
    result_id: uuid.UUID,
) -> StationaryCombustionResultResponse | None:
    row = db.get(CbamStationaryCombustionResult, result_id)
    if row is None:
        return None
    return _result_response(row)


def _get_sc_definition(db: Session) -> CbamCalculationDefinition:
    from ecotrace.modules.cbam.application.calculation_service import (
        ensure_platform_calculation_definitions,
    )

    ensure_platform_calculation_definitions(db)
    row = db.execute(
        select(CbamCalculationDefinition).where(
            CbamCalculationDefinition.code == STATIONARY_COMBUSTION_DEFINITION_CODE,
            CbamCalculationDefinition.status == 'ACTIVE',
        )
    ).scalar_one_or_none()
    if row is None:
        raise BusinessRuleError(
            'Stationary-combustion calculation definition is not available.',
            details=[{'code': 'DEFINITION_MISSING', 'codeValue': STATIONARY_COMBUSTION_DEFINITION_CODE}],
        )
    return row


def _load_activity(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    activity_id: uuid.UUID,
) -> CbamActivityRecord:
    activity = db.get(CbamActivityRecord, activity_id)
    if activity is None or activity.status != 'active':
        raise NotFoundError('Activity record not found.')
    if activity.organization_id != organization_id:
        raise NotFoundError('Activity record not found.')
    if activity.reporting_period_binding_id != binding_id:
        raise ValidationAppError(
            'Activity does not belong to the requested reporting-period binding.',
            details=[
                {
                    'code': 'ACTIVITY_BINDING_MISMATCH',
                    'activityRecordId': str(activity_id),
                    'reportingPeriodBindingId': str(binding_id),
                }
            ],
        )
    return activity


def _assert_activity_eligible(activity: CbamActivityRecord, fuel_code: str) -> None:
    if activity.activity_type not in ELIGIBLE_STATIONARY_COMBUSTION_ACTIVITY_TYPES:
        raise ValidationAppError(
            f'Activity type {activity.activity_type!r} is not eligible for '
            'stationary-combustion calculation.',
            details=[
                {
                    'code': 'INELIGIBLE_ACTIVITY_TYPE',
                    'activityType': activity.activity_type,
                }
            ],
        )
    if activity.activity_type != fuel_code:
        raise ValidationAppError(
            f'Fuel code {fuel_code!r} is incompatible with activity type '
            f'{activity.activity_type!r}.',
            details=[
                {
                    'code': 'FUEL_ACTIVITY_TYPE_MISMATCH',
                    'fuelCode': fuel_code,
                    'activityType': activity.activity_type,
                }
            ],
        )


def _assert_density_rules(
    *,
    input_basis: str,
    density_value: Decimal | None,
    density_unit: str | None,
) -> None:
    has_value = density_value is not None
    has_unit = density_unit is not None
    if has_value != has_unit:
        raise ValidationAppError(
            'density_value and density_unit must both be provided or both omitted.',
            details=[{'code': 'DENSITY_PAIR_INCOMPLETE'}],
        )
    if input_basis == 'VOLUME':
        if density_value is None or density_unit is None:
            raise ValidationAppError(
                'Density value and unit are required for VOLUME fuels.',
                details=[{'code': 'DENSITY_REQUIRED'}],
            )
        if density_value <= 0:
            raise ValidationAppError(
                'Density must be greater than zero.',
                details=[{'code': 'DENSITY_INVALID'}],
            )
    elif input_basis == 'MASS':
        if density_value is not None or density_unit is not None:
            raise ValidationAppError(
                'Density must not be supplied for MASS fuels.',
                details=[{'code': 'DENSITY_NOT_ALLOWED'}],
            )


def _assert_unit_compatibility(*, input_basis: str, activity_unit: str) -> None:
    if input_basis == 'VOLUME' and activity_unit not in VOLUME_ACTIVITY_UNITS:
        raise ValidationAppError(
            f'Activity unit {activity_unit!r} is incompatible with VOLUME fuel basis.',
            details=[{'code': 'INCOMPATIBLE_UNIT', 'activityUnit': activity_unit}],
        )
    if input_basis == 'MASS' and activity_unit not in MASS_ACTIVITY_UNITS:
        raise ValidationAppError(
            f'Activity unit {activity_unit!r} is incompatible with MASS fuel basis.',
            details=[{'code': 'INCOMPATIBLE_UNIT', 'activityUnit': activity_unit}],
        )


def _fail_run(
    db: Session,
    run: CbamCalculationRun,
    *,
    user: User,
    summary: str,
    request_id: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    run.status = 'FAILED'
    run.completed_at = datetime.now(UTC)
    run.error_summary = summary
    run.calculated_count = 0
    run.blocked_count = 0
    run.invalid_count = 1
    write_audit_log(
        db,
        action='cbam.stationary_combustion_run.failed',
        actor_user_id=user.id,
        organization_id=run.organization_id,
        entity_type='cbam_calculation_run',
        entity_id=str(run.id),
        metadata={'errorSummary': summary},
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.flush()


def _existing_result_for_run_activity(
    db: Session,
    *,
    run_id: uuid.UUID,
    activity_id: uuid.UUID,
) -> CbamStationaryCombustionResult | None:
    return db.execute(
        select(CbamStationaryCombustionResult).where(
            CbamStationaryCombustionResult.calculation_run_id == run_id,
            CbamStationaryCombustionResult.activity_record_id == activity_id,
        )
    ).scalar_one_or_none()


def execute_stationary_combustion_calculation(
    db: Session,
    user: User,
    command: StationaryCombustionExecutionCommand,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = True,
) -> StationaryCombustionExecutionResponse:
    require_cbam_configure(db, user, command.organization_id)
    binding = get_binding_for_org(
        db, command.organization_id, command.reporting_period_binding_id
    )
    activity = _load_activity(
        db,
        organization_id=command.organization_id,
        binding_id=binding.id,
        activity_id=command.activity_record_id,
    )
    fuel_code = command.fuel_code.strip().upper()
    _assert_activity_eligible(activity, fuel_code)
    definition = _get_sc_definition(db)

    run: CbamCalculationRun | None = None
    if command.calculation_run_id is not None:
        run = db.execute(
            select(CbamCalculationRun).where(
                CbamCalculationRun.id == command.calculation_run_id,
                CbamCalculationRun.organization_id == command.organization_id,
            )
        ).scalar_one_or_none()
        if run is None:
            raise NotFoundError('Calculation run not found.')
        if run.reporting_period_binding_id != binding.id:
            raise ValidationAppError(
                'Calculation run does not belong to the requested reporting-period binding.',
                details=[{'code': 'RUN_BINDING_MISMATCH'}],
            )
        if run.status == 'ARCHIVED':
            raise ValidationAppError('Archived calculation runs cannot be executed.')
        if run.status == 'RUNNING':
            raise ValidationAppError('Calculation run is already running.')
        existing = _existing_result_for_run_activity(
            db, run_id=run.id, activity_id=activity.id
        )
        if existing is not None:
            raise ConflictError(
                'Stationary-combustion result already exists for this run and activity.',
                details=[
                    {
                        'code': 'STATIONARY_COMBUSTION_RESULT_EXISTS',
                        'calculationRunId': str(run.id),
                        'activityRecordId': str(activity.id),
                        'resultId': str(existing.id),
                    }
                ],
            )
    else:
        run = CbamCalculationRun(
            organization_id=command.organization_id,
            reporting_period_binding_id=binding.id,
            status='DRAFT',
            calculation_version=ENGINE_VERSION,
            created_by_user_id=command.requested_by_user_id or user.id,
        )
        db.add(run)
        db.flush()

    run.status = 'RUNNING'
    run.started_at = datetime.now(UTC)
    run.completed_at = None
    run.error_summary = None
    run.calculated_count = 0
    run.blocked_count = 0
    run.invalid_count = 0
    db.flush()

    write_audit_log(
        db,
        action='cbam.stationary_combustion_run.started',
        actor_user_id=user.id,
        organization_id=command.organization_id,
        entity_type='cbam_calculation_run',
        entity_id=str(run.id),
        metadata={
            'activityRecordId': str(activity.id),
            'fuelCode': fuel_code,
            'referenceDate': command.reference_date.isoformat(),
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    try:
        resolution = resolve_stationary_combustion_parameters(
            db,
            fuel_code=fuel_code,
            reference_date=command.reference_date,
            dataset_version=command.dataset_version,
        )
        if resolution.status == RESOLUTION_UNRESOLVED:
            raise BusinessRuleError(
                resolution.message,
                details=[{'code': 'UNRESOLVED_PARAMETER_SET', 'message': resolution.message}],
            )
        if resolution.status == RESOLUTION_AMBIGUOUS:
            raise BusinessRuleError(
                resolution.message,
                details=[
                    {
                        'code': 'AMBIGUOUS_PARAMETER_SET',
                        'message': resolution.message,
                        'candidateParameterSetIds': [
                            str(i) for i in resolution.candidate_parameter_set_ids
                        ],
                    }
                ],
            )
        if resolution.status != RESOLUTION_RESOLVED or resolution.parameters is None:
            raise BusinessRuleError(
                'Stationary-combustion parameters could not be resolved.',
                details=[{'code': 'UNRESOLVED_PARAMETER_SET'}],
            )

        params = resolution.parameters
        _assert_density_rules(
            input_basis=params.input_basis,
            density_value=command.density_value,
            density_unit=command.density_unit,
        )
        _assert_unit_compatibility(
            input_basis=params.input_basis,
            activity_unit=activity.unit,
        )

        density_param = None
        if command.density_value is not None and command.density_unit is not None:
            density_param = QuantifiedParameter(
                value=command.density_value,
                unit=command.density_unit,
                provenance=DENSITY_COMMAND_PROVENANCE,
            )

        param_row = db.get(CbamStationaryCombustionParameterSet, params.parameter_set_id)
        if param_row is None:
            raise BusinessRuleError(
                'Resolved parameter set row is missing.',
                details=[{'code': 'UNRESOLVED_PARAMETER_SET'}],
            )

        inputs = StationaryCombustionInputs(
            fuel_code=params.fuel_code,
            fuel_name=params.fuel_name,
            activity_quantity=activity.quantity,
            activity_unit=activity.unit,
            input_basis=params.input_basis,  # type: ignore[arg-type]
            density=density_param,
            net_calorific_value=QuantifiedParameter(
                value=params.net_calorific_value,
                unit=params.net_calorific_value_unit,
                provenance=ParameterProvenance(
                    source_document=params.ncv_provenance.source_document,
                    source_table=params.ncv_provenance.source_table,
                    dataset_version=params.dataset_version,
                    source_reference=params.dataset_code,
                ),
            ),
            co2_emission_factor=QuantifiedParameter(
                value=params.fossil_co2_emission_factor,
                unit=params.fossil_co2_emission_factor_unit,
                provenance=ParameterProvenance(
                    source_document=params.co2_provenance.source_document,
                    source_table=params.co2_provenance.source_table,
                    dataset_version=params.dataset_version,
                    source_reference=params.dataset_code,
                ),
            ),
            oxidation_factor=params.oxidation_factor,
            oxidation_factor_provenance=ParameterProvenance(
                source_document=params.oxidation_provenance.source_document,
                source_table=params.oxidation_provenance.source_table,
                dataset_version=params.dataset_version,
                source_reference=params.dataset_code,
            ),
        )
        outcome = calculate_stationary_combustion_co2(inputs)
        if not outcome.ok or outcome.derived is None or outcome.result_value is None:
            raise ValidationAppError(
                outcome.error_message or 'Stationary-combustion calculation failed.',
                details=[
                    {
                        'code': outcome.error_code or 'INVALID_CALCULATION_INPUT',
                        'message': outcome.error_message,
                    }
                ],
            )

        result = CbamStationaryCombustionResult(
            organization_id=command.organization_id,
            calculation_run_id=run.id,
            calculation_definition_id=definition.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_id=params.fuel_id,
            parameter_set_id=params.parameter_set_id,
            calculation_type=CALCULATION_TYPE_STATIONARY_COMBUSTION_CO2,
            formula_version=FORMULA_VERSION_STATIONARY_COMBUSTION_CO2,
            fuel_code=params.fuel_code,
            fuel_name=params.fuel_name,
            input_basis=params.input_basis,
            activity_quantity=activity.quantity,
            activity_unit=activity.unit,
            density_value=command.density_value,
            density_unit=command.density_unit,
            client_request_id=command.client_request_id,
            request_fingerprint=command.request_fingerprint,
            calculation_reference_date=command.reference_date,
            net_calorific_value=params.net_calorific_value,
            net_calorific_value_unit=params.net_calorific_value_unit,
            fossil_co2_emission_factor=params.fossil_co2_emission_factor,
            fossil_co2_emission_factor_unit=params.fossil_co2_emission_factor_unit,
            oxidation_factor=params.oxidation_factor,
            dataset_code=params.dataset_code,
            dataset_version=params.dataset_version,
            valid_from=params.valid_from,
            valid_until=params.valid_until,
            ncv_reference_source_id=params.ncv_provenance.reference_source_id,
            ncv_source_document=params.ncv_provenance.source_document,
            ncv_source_table=params.ncv_provenance.source_table,
            co2_reference_source_id=params.co2_provenance.reference_source_id,
            co2_source_document=params.co2_provenance.source_document,
            co2_source_table=params.co2_provenance.source_table,
            oxidation_reference_source_id=params.oxidation_provenance.reference_source_id,
            oxidation_source_document=params.oxidation_provenance.source_document,
            oxidation_source_table=params.oxidation_provenance.source_table,
            fuel_mass_kg=outcome.derived.fuel_mass_kg,
            fuel_mass_gg=outcome.derived.fuel_mass_gg,
            energy_content_tj=outcome.derived.energy_content_tj,
            fossil_co2_kg=outcome.derived.co2_emissions_kg,
            fossil_co2_tonnes=outcome.derived.co2_emissions_tonnes,
            result_value=outcome.result_value,
            result_unit=outcome.result_unit or RESULT_UNIT_TCO2,
            created_by_user_id=command.requested_by_user_id or user.id,
        )
        db.add(result)
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError as exc:
            # When commit=False the caller recovers idempotency races after rollback.
            if not commit:
                raise
            raise ConflictError(
                'Stationary-combustion result persistence conflict.',
                details=[{'code': 'STATIONARY_COMBUSTION_RESULT_CONFLICT'}],
            ) from exc

        run.status = 'COMPLETED'
        run.completed_at = datetime.now(UTC)
        run.calculated_count = 1
        run.blocked_count = 0
        run.invalid_count = 0
        run.error_summary = None
        write_audit_log(
            db,
            action='cbam.stationary_combustion_result.created',
            actor_user_id=user.id,
            organization_id=command.organization_id,
            entity_type='cbam_stationary_combustion_result',
            entity_id=str(result.id),
            metadata={
                'calculationRunId': str(run.id),
                'activityRecordId': str(activity.id),
                'fuelCode': params.fuel_code,
                'resultValue': str(result.result_value),
                'resultUnit': result.result_unit,
                'datasetVersion': params.dataset_version,
                'clientRequestId': (
                    str(command.client_request_id) if command.client_request_id else None
                ),
            },
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        # Authoritative current pointer (intentional success only; not on replay/failure).
        set_current_result_pointer(
            db,
            organization_id=command.organization_id,
            binding_id=binding.id,
            activity_id=activity.id,
            result_id=result.id,
        )
        db.flush()
        if commit:
            db.commit()
            db.refresh(result)
            db.refresh(run)
        return StationaryCombustionExecutionResponse(
            calculation_run_id=run.id,
            calculation_run_status=run.status,
            result=_result_response(result, is_current=True, is_stale=False),
        )
    except (ValidationAppError, BusinessRuleError, NotFoundError, ConflictError) as exc:
        if run is not None and run.status == 'RUNNING':
            _fail_run(
                db,
                run,
                user=user,
                summary=str(exc),
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if commit:
                db.commit()
        raise
