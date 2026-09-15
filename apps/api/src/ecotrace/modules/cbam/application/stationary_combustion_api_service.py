from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.application.stationary_combustion_catalog_seed import (
    ensure_platform_stationary_combustion_catalog,
)
from ecotrace.modules.cbam.application.stationary_combustion_catalog_service import (
    RESOLUTION_AMBIGUOUS,
    RESOLUTION_RESOLVED,
    RESOLUTION_UNRESOLVED,
    resolve_stationary_combustion_parameters,
)
from ecotrace.modules.cbam.application.stationary_combustion_coverage_service import (
    StationaryCombustionActivityCoverageItem,
    list_stationary_combustion_activity_coverage,
)
from ecotrace.modules.cbam.application.stationary_combustion_current_result_service import (
    get_current_pointer,
    get_current_result_ids_for_binding,
    is_stationary_combustion_result_stale,
)
from ecotrace.modules.cbam.application.stationary_combustion_execution_service import (
    StationaryCombustionExecutionCommand,
    StationaryCombustionResultResponse,
    execute_stationary_combustion_calculation,
)
from ecotrace.modules.cbam.application.stationary_combustion_idempotency import (
    build_stationary_combustion_request_fingerprint,
)
from ecotrace.modules.cbam.application.stationary_combustion_summary_service import (
    StationaryCombustionPeriodSummaryResponse,
    get_stationary_combustion_period_summary,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamStationaryCombustionFuel,
    CbamStationaryCombustionResult,
)
from ecotrace.modules.cbam.infrastructure.reporting_period_reference_adapter import (
    require_reporting_period_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


class StationaryCombustionFuelResponse(CamelModel):
    code: str
    name: str
    input_basis: str
    default_activity_unit: str
    density_required: bool
    status: str


class StationaryCombustionSourceResponse(CamelModel):
    reference_source_id: uuid.UUID
    source_document: str
    source_table: str


class StationaryCombustionParametersResponse(CamelModel):
    fuel_code: str
    fuel_name: str
    input_basis: str
    default_activity_unit: str
    density_required: bool
    reference_density: Decimal | None
    reference_density_unit: str | None
    net_calorific_value: Decimal
    net_calorific_value_unit: str
    fossil_co2_emission_factor: Decimal
    fossil_co2_emission_factor_unit: str
    oxidation_factor: Decimal
    dataset_code: str
    dataset_version: str
    valid_from: date
    valid_until: date | None
    ncv_source: StationaryCombustionSourceResponse
    co2_source: StationaryCombustionSourceResponse
    oxidation_source: StationaryCombustionSourceResponse
    resolution_status: str
    parameter_set_id: uuid.UUID


class StationaryCombustionExecutionApiRequest(CamelModel):
    client_request_id: uuid.UUID
    activity_record_id: uuid.UUID
    fuel_code: str
    calculation_reference_date: date | None = None
    density_value: Decimal | None = None
    density_unit: str | None = None
    dataset_version: str | None = None


class StationaryCombustionExecutionApiResponse(CamelModel):
    run_id: uuid.UUID
    result_id: uuid.UUID
    status: str
    calculation_type: str
    calculation_version: str
    activity_record_id: uuid.UUID
    fuel_code: str
    reference_date: date
    result_value: Decimal
    result_unit: str
    client_request_id: uuid.UUID
    idempotent_replay: bool
    created_at: datetime


class StationaryCombustionResultSummaryResponse(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    activity_record_id: uuid.UUID
    fuel_code: str
    activity_quantity: Decimal
    activity_unit: str
    energy_content_tj: Decimal
    fossil_co2_tonnes: Decimal
    result_value: Decimal
    result_unit: str
    dataset_version: str
    client_request_id: uuid.UUID | None = None
    created_at: datetime
    is_current: bool = False
    is_stale: bool = False


def list_active_stationary_combustion_fuels(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
) -> list[StationaryCombustionFuelResponse]:
    require_cbam_view(db, user, organization_id)
    ensure_platform_stationary_combustion_catalog(db)
    rows = (
        db.execute(
            select(CbamStationaryCombustionFuel)
            .where(CbamStationaryCombustionFuel.status == "ACTIVE")
            .order_by(CbamStationaryCombustionFuel.code.asc())
        )
        .scalars()
        .all()
    )
    return [
        StationaryCombustionFuelResponse(
            code=row.code,
            name=row.name,
            input_basis=row.input_basis,
            default_activity_unit=row.default_activity_unit,
            density_required=row.input_basis == "VOLUME",
            status=row.status,
        )
        for row in rows
    ]


def get_stationary_combustion_parameters(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    fuel_code: str,
    *,
    reference_date: date,
    dataset_version: str | None = None,
) -> StationaryCombustionParametersResponse:
    require_cbam_view(db, user, organization_id)
    ensure_platform_stationary_combustion_catalog(db)
    code = fuel_code.strip().upper()
    fuel = db.execute(
        select(CbamStationaryCombustionFuel).where(CbamStationaryCombustionFuel.code == code)
    ).scalar_one_or_none()
    if fuel is None or fuel.status != "ACTIVE":
        raise NotFoundError("Stationary-combustion fuel not found.")

    resolution = resolve_stationary_combustion_parameters(
        db,
        fuel_code=code,
        reference_date=reference_date,
        dataset_version=dataset_version,
    )
    if resolution.status == RESOLUTION_AMBIGUOUS:
        raise ConflictError(
            resolution.message,
            details=[
                {
                    "code": "AMBIGUOUS_PARAMETER_SET",
                    "candidateParameterSetIds": [
                        str(i) for i in resolution.candidate_parameter_set_ids
                    ],
                }
            ],
        )
    if resolution.status == RESOLUTION_UNRESOLVED or resolution.parameters is None:
        raise ValidationAppError(
            resolution.message,
            details=[{"code": "UNRESOLVED_PARAMETER_SET", "message": resolution.message}],
        )
    if resolution.status != RESOLUTION_RESOLVED:
        raise ValidationAppError(
            "Stationary-combustion parameters could not be resolved.",
            details=[{"code": "UNRESOLVED_PARAMETER_SET"}],
        )

    params = resolution.parameters
    return StationaryCombustionParametersResponse(
        fuel_code=params.fuel_code,
        fuel_name=params.fuel_name,
        input_basis=params.input_basis,
        default_activity_unit=params.default_activity_unit,
        density_required=params.input_basis == "VOLUME",
        reference_density=params.reference_density,
        reference_density_unit=params.reference_density_unit,
        net_calorific_value=params.net_calorific_value,
        net_calorific_value_unit=params.net_calorific_value_unit,
        fossil_co2_emission_factor=params.fossil_co2_emission_factor,
        fossil_co2_emission_factor_unit=params.fossil_co2_emission_factor_unit,
        oxidation_factor=params.oxidation_factor,
        dataset_code=params.dataset_code,
        dataset_version=params.dataset_version,
        valid_from=params.valid_from,
        valid_until=params.valid_until,
        ncv_source=StationaryCombustionSourceResponse(
            reference_source_id=params.ncv_provenance.reference_source_id,
            source_document=params.ncv_provenance.source_document,
            source_table=params.ncv_provenance.source_table,
        ),
        co2_source=StationaryCombustionSourceResponse(
            reference_source_id=params.co2_provenance.reference_source_id,
            source_document=params.co2_provenance.source_document,
            source_table=params.co2_provenance.source_table,
        ),
        oxidation_source=StationaryCombustionSourceResponse(
            reference_source_id=params.oxidation_provenance.reference_source_id,
            source_document=params.oxidation_provenance.source_document,
            source_table=params.oxidation_provenance.source_table,
        ),
        resolution_status=RESOLUTION_RESOLVED,
        parameter_set_id=params.parameter_set_id,
    )


def _resolve_reference_date(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    activity: CbamActivityRecord,
    calculation_reference_date: date | None,
) -> date:
    if activity.activity_date is not None:
        return activity.activity_date
    if calculation_reference_date is None:
        raise ValidationAppError(
            "calculation_reference_date is required when the activity has no activity_date.",
            details=[{"code": "REFERENCE_DATE_REQUIRED"}],
        )
    binding = get_binding_for_org(db, organization_id, binding_id)
    period = require_reporting_period_in_organization(
        db, organization_id, binding.reporting_period_id
    )
    if (
        calculation_reference_date < period.start_date
        or calculation_reference_date > period.end_date
    ):
        raise ValidationAppError(
            "calculation_reference_date must fall inside the reporting period.",
            details=[
                {
                    "code": "REFERENCE_DATE_OUTSIDE_PERIOD",
                    "calculationReferenceDate": calculation_reference_date.isoformat(),
                    "periodStart": period.start_date.isoformat(),
                    "periodEnd": period.end_date.isoformat(),
                }
            ],
        )
    return calculation_reference_date


def _find_result_by_client_request(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    client_request_id: uuid.UUID,
) -> CbamStationaryCombustionResult | None:
    return db.execute(
        select(CbamStationaryCombustionResult).where(
            CbamStationaryCombustionResult.organization_id == organization_id,
            CbamStationaryCombustionResult.reporting_period_binding_id == binding_id,
            CbamStationaryCombustionResult.client_request_id == client_request_id,
        )
    ).scalar_one_or_none()


def _raise_idempotency_key_reused(
    *,
    client_request_id: uuid.UUID,
    existing_result_id: uuid.UUID,
) -> None:
    raise ConflictError(
        "clientRequestId was already used with a different execution request.",
        code="IDEMPOTENCY_KEY_REUSED",
        details=[
            {
                "code": "IDEMPOTENCY_KEY_REUSED",
                "clientRequestId": str(client_request_id),
                "existingResultId": str(existing_result_id),
            }
        ],
    )


def _execution_response_from_result(
    row: CbamStationaryCombustionResult,
    *,
    reference_date: date,
    client_request_id: uuid.UUID,
    idempotent_replay: bool,
) -> StationaryCombustionExecutionApiResponse:
    return StationaryCombustionExecutionApiResponse(
        run_id=row.calculation_run_id,
        result_id=row.id,
        status="COMPLETED",
        calculation_type=row.calculation_type,
        calculation_version=row.formula_version,
        activity_record_id=row.activity_record_id,
        fuel_code=row.fuel_code,
        reference_date=reference_date,
        result_value=row.result_value,
        result_unit=row.result_unit,
        client_request_id=client_request_id,
        idempotent_replay=idempotent_replay,
        created_at=row.created_at,
    )


def _replay_or_conflict(
    existing: CbamStationaryCombustionResult,
    *,
    fingerprint: str,
    reference_date: date,
    client_request_id: uuid.UUID,
) -> StationaryCombustionExecutionApiResponse:
    if existing.request_fingerprint != fingerprint:
        _raise_idempotency_key_reused(
            client_request_id=client_request_id,
            existing_result_id=existing.id,
        )
    return _execution_response_from_result(
        existing,
        reference_date=existing.calculation_reference_date or reference_date,
        client_request_id=client_request_id,
        idempotent_replay=True,
    )


def execute_stationary_combustion_api(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: StationaryCombustionExecutionApiRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> StationaryCombustionExecutionApiResponse:
    require_cbam_configure(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)

    activity = db.get(CbamActivityRecord, payload.activity_record_id)
    if activity is None or activity.status != "active":
        raise NotFoundError("Activity record not found.")
    if activity.organization_id != organization_id:
        raise NotFoundError("Activity record not found.")
    if activity.reporting_period_binding_id != binding_id:
        raise ValidationAppError(
            "Activity does not belong to the requested reporting-period binding.",
            details=[{"code": "ACTIVITY_BINDING_MISMATCH"}],
        )

    reference_date = _resolve_reference_date(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        activity=activity,
        calculation_reference_date=payload.calculation_reference_date,
    )
    fuel_code = payload.fuel_code.strip().upper()
    fingerprint = build_stationary_combustion_request_fingerprint(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        activity_record_id=payload.activity_record_id,
        fuel_code=fuel_code,
        reference_date=reference_date,
        density_value=payload.density_value,
        density_unit=payload.density_unit,
        dataset_version=payload.dataset_version,
    )

    existing = _find_result_by_client_request(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        client_request_id=payload.client_request_id,
    )
    if existing is not None:
        return _replay_or_conflict(
            existing,
            fingerprint=fingerprint,
            reference_date=reference_date,
            client_request_id=payload.client_request_id,
        )

    try:
        executed = execute_stationary_combustion_calculation(
            db,
            user,
            StationaryCombustionExecutionCommand(
                organization_id=organization_id,
                reporting_period_binding_id=binding_id,
                activity_record_id=payload.activity_record_id,
                fuel_code=fuel_code,
                reference_date=reference_date,
                density_value=payload.density_value,
                density_unit=payload.density_unit,
                dataset_version=payload.dataset_version,
                requested_by_user_id=user.id,
                client_request_id=payload.client_request_id,
                request_fingerprint=fingerprint,
            ),
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            commit=False,
        )
        db.commit()
        result = executed.result
        return StationaryCombustionExecutionApiResponse(
            run_id=executed.calculation_run_id,
            result_id=result.id,
            status=executed.calculation_run_status,
            calculation_type=result.calculation_type,
            calculation_version=result.formula_version,
            activity_record_id=result.activity_record_id,
            fuel_code=result.fuel_code,
            reference_date=reference_date,
            result_value=result.result_value,
            result_unit=result.result_unit,
            client_request_id=payload.client_request_id,
            idempotent_replay=False,
            created_at=result.created_at,
        )
    except IntegrityError:
        # Uniqueness race: discard this attempt (including any partial run) and recover.
        db.rollback()
        winner = _find_result_by_client_request(
            db,
            organization_id=organization_id,
            binding_id=binding_id,
            client_request_id=payload.client_request_id,
        )
        if winner is None:
            raise ConflictError(
                "Stationary-combustion result persistence conflict.",
                details=[{"code": "STATIONARY_COMBUSTION_RESULT_CONFLICT"}],
            ) from None
        return _replay_or_conflict(
            winner,
            fingerprint=fingerprint,
            reference_date=reference_date,
            client_request_id=payload.client_request_id,
        )


def list_stationary_combustion_results(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[StationaryCombustionResultSummaryResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamStationaryCombustionResult).where(
        CbamStationaryCombustionResult.organization_id == organization_id,
        CbamStationaryCombustionResult.reporting_period_binding_id == binding_id,
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(
                CbamStationaryCombustionResult.created_at.desc(),
                CbamStationaryCombustionResult.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    current_by_activity = get_current_result_ids_for_binding(
        db, organization_id=organization_id, binding_id=binding_id
    )
    activity_ids = {row.activity_record_id for row in rows}
    activities: dict[uuid.UUID, CbamActivityRecord] = {}
    if activity_ids:
        for activity in db.execute(
            select(CbamActivityRecord).where(CbamActivityRecord.id.in_(activity_ids))
        ).scalars():
            activities[activity.id] = activity

    items: list[StationaryCombustionResultSummaryResponse] = []
    for row in rows:
        is_current = current_by_activity.get(row.activity_record_id) == row.id
        activity_row = activities.get(row.activity_record_id)
        is_stale = (
            is_current
            and activity_row is not None
            and is_stationary_combustion_result_stale(activity_row, row)
        )
        items.append(
            StationaryCombustionResultSummaryResponse(
                result_id=row.id,
                run_id=row.calculation_run_id,
                activity_record_id=row.activity_record_id,
                fuel_code=row.fuel_code,
                activity_quantity=row.activity_quantity,
                activity_unit=row.activity_unit,
                energy_content_tj=row.energy_content_tj,
                fossil_co2_tonnes=row.fossil_co2_tonnes,
                result_value=row.result_value,
                result_unit=row.result_unit,
                dataset_version=row.dataset_version,
                client_request_id=row.client_request_id,
                created_at=row.created_at,
                is_current=is_current,
                is_stale=is_stale,
            )
        )
    return paginate(items, page=page, page_size=page_size, total_items=int(total))


def get_stationary_combustion_result_for_binding(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result_id: uuid.UUID,
) -> StationaryCombustionResultResponse:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    entity = db.get(CbamStationaryCombustionResult, result_id)
    if (
        entity is None
        or entity.organization_id != organization_id
        or entity.reporting_period_binding_id != binding_id
    ):
        raise NotFoundError("Stationary-combustion result not found.")
    pointer = get_current_pointer(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        activity_id=entity.activity_record_id,
    )
    is_current = pointer is not None and pointer.current_result_id == entity.id
    activity = db.get(CbamActivityRecord, entity.activity_record_id)
    is_stale = (
        is_current
        and activity is not None
        and is_stationary_combustion_result_stale(activity, entity)
    )
    from ecotrace.modules.cbam.application.stationary_combustion_execution_service import (
        _result_response,
    )

    return _result_response(entity, is_current=is_current, is_stale=is_stale)


def get_stationary_combustion_summary_for_binding(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> StationaryCombustionPeriodSummaryResponse:
    return get_stationary_combustion_period_summary(db, user, organization_id, binding_id)


def list_stationary_combustion_activity_coverage_for_binding(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[StationaryCombustionActivityCoverageItem]:
    return list_stationary_combustion_activity_coverage(
        db,
        user,
        organization_id,
        binding_id,
        page=page,
        page_size=page_size,
    )
