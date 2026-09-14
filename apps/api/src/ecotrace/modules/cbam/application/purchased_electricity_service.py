"""Purchased-electricity indirect emissions execution and reads."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.modules.cbam.application.calculation_service import (
    ensure_platform_calculation_definitions,
)
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    require_writable_binding,
)
from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.application.purchased_electricity_constants import (
    ELECTRICITY_ACTIVITY_TYPE,
    ELECTRICITY_FACTOR_UNITS,
    ELECTRICITY_QUANTITY_UNITS,
    EXECUTION_STATUS_COMPLETED,
    FACTOR_DEFINITION_CODE,
    FACTOR_SOURCE_MANUAL,
    FACTOR_SOURCE_PLATFORM_DEFAULT,
    FORMULA_VERSION,
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    RESULT_UNIT,
    TURKEY_DEFAULT_FACTOR_SEED_BLOCKER,
    WORKBOOK_FORMULA_REFS,
    ZERO,
)
from ecotrace.modules.cbam.application.purchased_electricity_idempotency import (
    build_purchased_electricity_request_fingerprint,
)
from ecotrace.modules.cbam.application.purchased_electricity_math import (
    calculate_indirect_electricity_emissions,
    to_mwh,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamCalculationDefinition,
    CbamCalculationRun,
    CbamFactorDefinition,
    CbamFactorValue,
    CbamPurchasedElectricityCurrentResult,
    CbamPurchasedElectricityResult,
    CbamReportingPeriodBinding,
)
from ecotrace.modules.cbam.infrastructure.reporting_period_reference_adapter import (
    require_reporting_period_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

FactorSourceMode = Literal['PLATFORM_DEFAULT', 'MANUAL']


class PurchasedElectricityManualFactor(CamelModel):
    value: Decimal
    unit: str
    source_name: str
    source_document: str
    dataset_version: str
    reference_description: str
    effective_date: date | None = None


class PurchasedElectricityExecuteRequest(CamelModel):
    client_request_id: uuid.UUID
    activity_record_id: uuid.UUID
    factor_source_mode: FactorSourceMode
    calculation_reference_date: date | None = None
    manual_factor: PurchasedElectricityManualFactor | None = None
    exported_electricity_quantity: Decimal | None = None
    exported_electricity_unit: str | None = None
    evidence_notes: str | None = None


class PurchasedElectricityExecutionResponse(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    status: str
    methodology_code: str
    methodology_version: str
    activity_record_id: uuid.UUID
    electricity_mwh: Decimal
    factor_source_mode: str
    factor_value: Decimal
    factor_unit: str
    indirect_emissions_tco2e: Decimal
    result_unit: str
    exported_electricity_mwh: Decimal | None
    client_request_id: uuid.UUID
    idempotent_replay: bool
    created_at: datetime


class PurchasedElectricityFactorResolution(CamelModel):
    resolved: bool
    factor_source_mode: str
    factor_value: Decimal | None
    factor_unit: str | None
    factor_value_id: uuid.UUID | None
    factor_definition_id: uuid.UUID | None
    source_name: str | None
    source_document: str | None
    dataset_version: str | None
    reference_description: str | None
    valid_from: date | None
    valid_until: date | None
    reference_date: date
    blocking_issue_codes: list[str]
    informational_issue_codes: list[str]


class PurchasedElectricityResultSummary(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    activity_record_id: uuid.UUID
    status: str
    is_current: bool
    is_stale: bool
    stale_reason_codes: list[str]
    electricity_mwh: Decimal
    factor_source_mode: str
    factor_value: Decimal
    factor_unit: str
    indirect_emissions_tco2e: Decimal
    result_unit: str
    exported_electricity_mwh: Decimal | None
    created_at: datetime


class PurchasedElectricityResultDetail(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    activity_record_id: uuid.UUID
    methodology_code: str
    methodology_version: str
    formula_version: str
    workbook_formula_refs: str
    client_request_id: uuid.UUID
    request_fingerprint: str
    status: str
    is_current: bool
    is_stale: bool
    stale_reason_codes: list[str]
    calculation_reference_date: date
    activity_quantity: Decimal
    activity_unit: str
    electricity_mwh: Decimal
    factor_source_mode: str
    factor_value: Decimal
    factor_unit: str
    factor_tco2e_per_mwh: Decimal
    factor_value_id: uuid.UUID | None
    factor_definition_id: uuid.UUID | None
    factor_source_name: str
    factor_source_document: str
    factor_dataset_version: str
    factor_reference_description: str
    factor_effective_date: date | None
    factor_valid_from: date | None
    factor_valid_until: date | None
    exported_electricity_quantity: Decimal | None
    exported_electricity_unit: str | None
    exported_electricity_mwh: Decimal | None
    indirect_emissions_tco2e: Decimal
    result_value: Decimal
    result_unit: str
    evidence_notes: str | None
    created_at: datetime
    created_by_user_id: uuid.UUID | None


class PurchasedElectricityPeriodSummary(CamelModel):
    reporting_period_binding_id: uuid.UUID
    methodology_code: str
    readiness_status: str
    allocation_ready: bool
    blocking_issue_codes: list[str]
    informational_issue_codes: list[str]
    eligible_activity_count: int
    valid_current_result_count: int
    missing_result_count: int
    stale_result_count: int
    total_electricity_mwh: Decimal | None
    total_indirect_emissions_tco2e: Decimal | None
    total_exported_electricity_mwh: Decimal | None
    result_unit: str


def _period(db: Session, organization_id: uuid.UUID, binding: CbamReportingPeriodBinding) -> Any:
    return require_reporting_period_in_organization(
        db, organization_id=organization_id, reporting_period_id=binding.reporting_period_id
    )


def _electricity_definition(db: Session) -> CbamFactorDefinition:
    ensure_platform_factor_catalog(db)
    row = db.execute(
        select(CbamFactorDefinition).where(CbamFactorDefinition.code == FACTOR_DEFINITION_CODE)
    ).scalar_one_or_none()
    if row is None:
        raise BusinessRuleError(
            'Electricity factor definition is missing.',
            details=[{'code': 'FACTOR_DEFINITION_MISSING'}],
        )
    return row


def _calc_definition(db: Session) -> CbamCalculationDefinition:
    ensure_platform_calculation_definitions(db)
    row = db.execute(
        select(CbamCalculationDefinition).where(
            CbamCalculationDefinition.code == METHODOLOGY_CODE
        )
    ).scalar_one_or_none()
    if row is None:
        raise BusinessRuleError(
            'Purchased-electricity calculation definition is missing.',
            details=[{'code': 'CALCULATION_DEFINITION_MISSING'}],
        )
    return row


def _date_covers(value: CbamFactorValue, reference_date: date) -> bool:
    if value.valid_from is not None and reference_date < value.valid_from:
        return False
    return not (value.valid_until is not None and reference_date > value.valid_until)


def resolve_platform_default_factor(
    db: Session,
    *,
    reference_date: date,
) -> PurchasedElectricityFactorResolution:
    definition = _electricity_definition(db)
    candidates = list(
        db.execute(
            select(CbamFactorValue).where(
                CbamFactorValue.factor_definition_id == definition.id,
                CbamFactorValue.status == 'ACTIVE',
                CbamFactorValue.data_source_type == 'DEFAULT_REFERENCE',
                CbamFactorValue.organization_id.is_(None),
            )
        ).scalars()
    )
    covering = [c for c in candidates if _date_covers(c, reference_date)]
    info = [TURKEY_DEFAULT_FACTOR_SEED_BLOCKER]
    if not covering:
        return PurchasedElectricityFactorResolution(
            resolved=False,
            factor_source_mode=FACTOR_SOURCE_PLATFORM_DEFAULT,
            factor_value=None,
            factor_unit=None,
            factor_value_id=None,
            factor_definition_id=definition.id,
            source_name=None,
            source_document=None,
            dataset_version=None,
            reference_description=None,
            valid_from=None,
            valid_until=None,
            reference_date=reference_date,
            blocking_issue_codes=['UNRESOLVED_PLATFORM_DEFAULT'],
            informational_issue_codes=info,
        )
    if len(covering) > 1:
        return PurchasedElectricityFactorResolution(
            resolved=False,
            factor_source_mode=FACTOR_SOURCE_PLATFORM_DEFAULT,
            factor_value=None,
            factor_unit=None,
            factor_value_id=None,
            factor_definition_id=definition.id,
            source_name=None,
            source_document=None,
            dataset_version=None,
            reference_description=None,
            valid_from=None,
            valid_until=None,
            reference_date=reference_date,
            blocking_issue_codes=['AMBIGUOUS_PLATFORM_DEFAULT'],
            informational_issue_codes=info,
        )
    row = covering[0]
    if row.unit not in ELECTRICITY_FACTOR_UNITS:
        return PurchasedElectricityFactorResolution(
            resolved=False,
            factor_source_mode=FACTOR_SOURCE_PLATFORM_DEFAULT,
            factor_value=None,
            factor_unit=row.unit,
            factor_value_id=row.id,
            factor_definition_id=definition.id,
            source_name=None,
            source_document=None,
            dataset_version=None,
            reference_description=None,
            valid_from=row.valid_from,
            valid_until=row.valid_until,
            reference_date=reference_date,
            blocking_issue_codes=['INCOMPATIBLE_FACTOR_UNIT'],
            informational_issue_codes=info,
        )
    return PurchasedElectricityFactorResolution(
        resolved=True,
        factor_source_mode=FACTOR_SOURCE_PLATFORM_DEFAULT,
        factor_value=row.numeric_value,
        factor_unit=row.unit,
        factor_value_id=row.id,
        factor_definition_id=definition.id,
        source_name=row.supplier_name or 'PLATFORM_DEFAULT',
        source_document=row.source_reference or 'DEFAULT_REFERENCE',
        dataset_version=row.source_reference or 'unspecified',
        reference_description=row.notes or row.source_reference or 'Platform default factor',
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        reference_date=reference_date,
        blocking_issue_codes=[],
        informational_issue_codes=info if not covering else [],
    )


def get_purchased_electricity_default_factor(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    reference_date: date | None = None,
) -> PurchasedElectricityFactorResolution:
    require_cbam_view(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    period = _period(db, organization_id, binding)
    ref = reference_date or period.start_date
    if ref < period.start_date or ref > period.end_date:
        raise ValidationAppError(
            'Reference date must fall inside the reporting period.',
            details=[{'code': 'REFERENCE_DATE_OUTSIDE_PERIOD'}],
        )
    return resolve_platform_default_factor(db, reference_date=ref)


def _validate_manual_factor(manual: PurchasedElectricityManualFactor | None) -> None:
    if manual is None:
        raise ValidationAppError(
            'Manual factor provenance is required.',
            details=[{'code': 'MANUAL_FACTOR_REQUIRED'}],
        )
    # Blank / missing value must not become zero (Pydantic rejects null; keep guard).
    if manual.value is None:
        raise ValidationAppError(
            'Manual factor value is required.',
            details=[{'code': 'MISSING_FACTOR'}],
        )
    if manual.value < ZERO:
        raise ValidationAppError(
            'Manual factor cannot be negative.',
            details=[{'code': 'NEGATIVE_FACTOR_VALUE'}],
        )
    if not (manual.unit or '').strip():
        raise ValidationAppError(
            'Manual factor unit is required.',
            details=[{'code': 'MISSING_FACTOR_UNIT'}],
        )
    if manual.unit not in ELECTRICITY_FACTOR_UNITS:
        raise ValidationAppError(
            'Manual factor unit is not a supported electricity intensity unit.',
            details=[{'code': 'INCOMPATIBLE_FACTOR_UNIT'}],
        )
    for field, code in (
        (manual.source_name, 'MANUAL_FACTOR_SOURCE_REQUIRED'),
        (manual.source_document, 'MANUAL_FACTOR_DOCUMENT_REQUIRED'),
        (manual.dataset_version, 'MANUAL_FACTOR_DATASET_REQUIRED'),
        (manual.reference_description, 'MANUAL_FACTOR_REFERENCE_REQUIRED'),
    ):
        if not (field or '').strip():
            raise ValidationAppError(
                'Manual factor provenance is incomplete.',
                details=[{'code': code}],
            )


def _resolve_reference_date(
    *,
    period: Any,
    activity: CbamActivityRecord,
    calculation_reference_date: date | None,
) -> date:
    if activity.activity_date is not None:
        ref = activity.activity_date
    elif calculation_reference_date is not None:
        ref = calculation_reference_date
    else:
        raise ValidationAppError(
            'Activity date or calculationReferenceDate is required.',
            details=[{'code': 'ACTIVITY_DATE_REQUIRED'}],
        )
    if ref < period.start_date or ref > period.end_date:
        raise ValidationAppError(
            'Reference date must fall inside the reporting period.',
            details=[{'code': 'REFERENCE_DATE_OUTSIDE_PERIOD'}],
        )
    return ref


def _current_pointer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    activity_id: uuid.UUID,
) -> CbamPurchasedElectricityCurrentResult | None:
    return db.execute(
        select(CbamPurchasedElectricityCurrentResult).where(
            CbamPurchasedElectricityCurrentResult.organization_id == organization_id,
            CbamPurchasedElectricityCurrentResult.reporting_period_binding_id == binding_id,
            CbamPurchasedElectricityCurrentResult.activity_record_id == activity_id,
        )
    ).scalar_one_or_none()


def _set_current_pointer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    activity_id: uuid.UUID,
    result_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    stmt = (
        pg_insert(CbamPurchasedElectricityCurrentResult)
        .values(
            id=uuid.uuid4(),
            organization_id=organization_id,
            reporting_period_binding_id=binding_id,
            activity_record_id=activity_id,
            methodology_code=METHODOLOGY_CODE,
            current_result_id=result_id,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            constraint='uq_cbam_pe_current_org_binding_activity',
            set_={
                'current_result_id': result_id,
                'methodology_code': METHODOLOGY_CODE,
                'updated_at': now,
            },
        )
    )
    db.execute(stmt)


def compute_stale_reasons(
    activity: CbamActivityRecord,
    result: CbamPurchasedElectricityResult,
) -> list[str]:
    reasons: list[str] = []
    if activity.quantity != result.activity_quantity or activity.unit != result.activity_unit:
        reasons.append('ACTIVITY_INPUT_CHANGED')
    if activity.activity_date is not None and activity.activity_date != result.calculation_reference_date:
        reasons.append('ACTIVITY_DATE_CHANGED')
    if activity.status != 'active':
        reasons.append('ACTIVITY_NOT_ACTIVE')
    if activity.activity_type != ELECTRICITY_ACTIVITY_TYPE:
        reasons.append('ACTIVITY_TYPE_CHANGED')
    return reasons


def _find_by_client_request(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    client_request_id: uuid.UUID,
) -> CbamPurchasedElectricityResult | None:
    return db.execute(
        select(CbamPurchasedElectricityResult).where(
            CbamPurchasedElectricityResult.organization_id == organization_id,
            CbamPurchasedElectricityResult.reporting_period_binding_id == binding_id,
            CbamPurchasedElectricityResult.client_request_id == client_request_id,
        )
    ).scalar_one_or_none()


def _execution_response(
    row: CbamPurchasedElectricityResult, *, idempotent_replay: bool
) -> PurchasedElectricityExecutionResponse:
    return PurchasedElectricityExecutionResponse(
        result_id=row.id,
        run_id=row.calculation_run_id,
        status=row.status,
        methodology_code=row.methodology_code,
        methodology_version=row.methodology_version,
        activity_record_id=row.activity_record_id,
        electricity_mwh=row.electricity_mwh,
        factor_source_mode=row.factor_source_mode,
        factor_value=row.factor_value,
        factor_unit=row.factor_unit,
        indirect_emissions_tco2e=row.indirect_emissions_tco2e,
        result_unit=row.result_unit,
        exported_electricity_mwh=row.exported_electricity_mwh,
        client_request_id=row.client_request_id,
        idempotent_replay=idempotent_replay,
        created_at=row.created_at,
    )


def execute_purchased_electricity(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: PurchasedElectricityExecuteRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PurchasedElectricityExecutionResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    period = _period(db, organization_id, binding)

    activity = db.get(CbamActivityRecord, payload.activity_record_id)
    if activity is None or activity.organization_id != organization_id:
        raise NotFoundError('Activity record not found.')
    if activity.reporting_period_binding_id != binding_id:
        raise ValidationAppError(
            'Activity does not belong to the requested reporting-period binding.',
            details=[{'code': 'ACTIVITY_BINDING_MISMATCH'}],
        )
    if activity.status != 'active':
        raise ValidationAppError(
            'Activity record is not active.',
            details=[{'code': 'ACTIVITY_NOT_ACTIVE'}],
        )
    if activity.activity_type != ELECTRICITY_ACTIVITY_TYPE:
        raise ValidationAppError(
            'Activity must be ELECTRICITY.',
            details=[{'code': 'INCOMPATIBLE_ACTIVITY_TYPE'}],
        )
    if activity.unit not in ELECTRICITY_QUANTITY_UNITS:
        raise ValidationAppError(
            'Electricity activity unit must be kWh or MWh.',
            details=[{'code': 'INCOMPATIBLE_ELECTRICITY_UNIT'}],
        )
    if activity.quantity < ZERO:
        raise ValidationAppError(
            'Electricity quantity cannot be negative.',
            details=[{'code': 'NEGATIVE_ELECTRICITY_QUANTITY'}],
        )

    reference_date = _resolve_reference_date(
        period=period,
        activity=activity,
        calculation_reference_date=payload.calculation_reference_date,
    )

    mode = payload.factor_source_mode
    factor_value: Decimal
    factor_unit: str
    factor_value_id: uuid.UUID | None = None
    factor_definition_id: uuid.UUID | None = None
    source_name: str
    source_document: str
    dataset_version: str
    reference_description: str
    factor_effective_date: date | None = None
    factor_valid_from: date | None = None
    factor_valid_until: date | None = None

    if mode == FACTOR_SOURCE_PLATFORM_DEFAULT:
        resolved = resolve_platform_default_factor(db, reference_date=reference_date)
        if not resolved.resolved:
            code = (
                resolved.blocking_issue_codes[0]
                if resolved.blocking_issue_codes
                else 'UNRESOLVED_PLATFORM_DEFAULT'
            )
            raise BusinessRuleError(
                'Platform electricity default factor could not be resolved.',
                details=[{'code': code}],
            )
        assert resolved.factor_value is not None and resolved.factor_unit is not None
        factor_value = resolved.factor_value
        factor_unit = resolved.factor_unit
        factor_value_id = resolved.factor_value_id
        factor_definition_id = resolved.factor_definition_id
        source_name = resolved.source_name or 'PLATFORM_DEFAULT'
        source_document = resolved.source_document or 'DEFAULT_REFERENCE'
        dataset_version = resolved.dataset_version or 'unspecified'
        reference_description = resolved.reference_description or 'Platform default'
        factor_valid_from = resolved.valid_from
        factor_valid_until = resolved.valid_until
    elif mode == FACTOR_SOURCE_MANUAL:
        _validate_manual_factor(payload.manual_factor)
        assert payload.manual_factor is not None
        manual = payload.manual_factor
        factor_value = manual.value
        factor_unit = manual.unit.strip()
        definition = _electricity_definition(db)
        factor_definition_id = definition.id
        source_name = manual.source_name.strip()
        source_document = manual.source_document.strip()
        dataset_version = manual.dataset_version.strip()
        reference_description = manual.reference_description.strip()
        factor_effective_date = manual.effective_date
    else:
        raise ValidationAppError(
            'Unsupported factor source mode.',
            details=[{'code': 'INVALID_FACTOR_SOURCE_MODE'}],
        )

    exported_qty = payload.exported_electricity_quantity
    exported_unit = payload.exported_electricity_unit
    exported_mwh: Decimal | None = None
    if exported_qty is not None or exported_unit is not None:
        if exported_qty is None or exported_unit is None:
            raise ValidationAppError(
                'Exported electricity quantity and unit must be provided together.',
                details=[{'code': 'EXPORTED_ELECTRICITY_INCOMPLETE'}],
            )
        if exported_unit not in ELECTRICITY_QUANTITY_UNITS:
            raise ValidationAppError(
                'Exported electricity unit must be kWh or MWh.',
                details=[{'code': 'INCOMPATIBLE_ELECTRICITY_UNIT'}],
            )
        try:
            exported_mwh = to_mwh(exported_qty, exported_unit)
        except ValueError as exc:
            raise ValidationAppError(
                'Exported electricity is invalid.',
                details=[{'code': str(exc)}],
            ) from exc

    fingerprint = build_purchased_electricity_request_fingerprint(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        activity_record_id=activity.id,
        factor_source_mode=mode,
        reference_date=reference_date,
        activity_quantity=activity.quantity,
        activity_unit=activity.unit,
        factor_value=factor_value,
        factor_unit=factor_unit,
        factor_value_id=factor_value_id,
        exported_quantity=exported_qty,
        exported_unit=exported_unit,
        manual_source_name=source_name if mode == FACTOR_SOURCE_MANUAL else None,
        manual_source_document=source_document if mode == FACTOR_SOURCE_MANUAL else None,
        manual_dataset_version=dataset_version if mode == FACTOR_SOURCE_MANUAL else None,
        manual_reference_description=(
            reference_description if mode == FACTOR_SOURCE_MANUAL else None
        ),
    )

    existing = _find_by_client_request(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        client_request_id=payload.client_request_id,
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise ConflictError(
                'clientRequestId was already used with a different execution request.',
                code='IDEMPOTENCY_KEY_REUSED',
                details=[
                    {
                        'code': 'IDEMPOTENCY_KEY_REUSED',
                        'clientRequestId': str(payload.client_request_id),
                        'existingResultId': str(existing.id),
                    }
                ],
            )
        return _execution_response(existing, idempotent_replay=True)

    outcome = calculate_indirect_electricity_emissions(
        electricity_quantity=activity.quantity,
        electricity_unit=activity.unit,
        factor_value=factor_value,
        factor_unit=factor_unit,
    )
    if (
        not outcome.ok
        or outcome.electricity_mwh is None
        or outcome.factor_tco2e_per_mwh is None
        or outcome.indirect_emissions_tco2e is None
    ):
        # Failed execution must not replace current.
        raise ValidationAppError(
            outcome.error_message or 'Electricity calculation failed.',
            details=[{'code': outcome.error_code or 'INVALID_CALCULATION_INPUT'}],
        )

    calc_definition = _calc_definition(db)
    now = datetime.now(UTC)
    run = CbamCalculationRun(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        status='COMPLETED',
        calculation_version=FORMULA_VERSION,
        started_at=now,
        completed_at=now,
        calculated_count=1,
        blocked_count=0,
        invalid_count=0,
        primary_factor_count=1 if mode == FACTOR_SOURCE_MANUAL else 0,
        default_factor_count=1 if mode == FACTOR_SOURCE_PLATFORM_DEFAULT else 0,
        created_by_user_id=user.id,
    )
    db.add(run)
    db.flush()

    result = CbamPurchasedElectricityResult(
        id=uuid.uuid4(),
        organization_id=organization_id,
        calculation_run_id=run.id,
        calculation_definition_id=calc_definition.id,
        reporting_period_binding_id=binding_id,
        activity_record_id=activity.id,
        methodology_code=METHODOLOGY_CODE,
        methodology_version=METHODOLOGY_VERSION,
        formula_version=FORMULA_VERSION,
        workbook_formula_refs=WORKBOOK_FORMULA_REFS,
        client_request_id=payload.client_request_id,
        request_fingerprint=fingerprint,
        status=EXECUTION_STATUS_COMPLETED,
        calculation_reference_date=reference_date,
        activity_quantity=activity.quantity,
        activity_unit=activity.unit,
        electricity_mwh=outcome.electricity_mwh,
        factor_source_mode=mode,
        factor_value=factor_value,
        factor_unit=factor_unit,
        factor_tco2e_per_mwh=outcome.factor_tco2e_per_mwh,
        factor_value_id=factor_value_id,
        factor_definition_id=factor_definition_id,
        factor_source_name=source_name,
        factor_source_document=source_document,
        factor_dataset_version=dataset_version,
        factor_reference_description=reference_description,
        factor_effective_date=factor_effective_date,
        factor_valid_from=factor_valid_from,
        factor_valid_until=factor_valid_until,
        exported_electricity_quantity=exported_qty,
        exported_electricity_unit=exported_unit,
        exported_electricity_mwh=exported_mwh,
        indirect_emissions_tco2e=outcome.indirect_emissions_tco2e,
        result_value=outcome.indirect_emissions_tco2e,
        result_unit=RESULT_UNIT,
        evidence_notes=payload.evidence_notes,
        created_by_user_id=user.id,
    )
    db.add(result)
    db.flush()
    _set_current_pointer(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        activity_id=activity.id,
        result_id=result.id,
    )
    write_audit_log(
        db,
        action='cbam.purchased_electricity.execute',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_purchased_electricity_result',
        entity_id=str(result.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'resultId': str(result.id),
            'activityRecordId': str(activity.id),
            'indirectEmissionsTco2e': str(result.indirect_emissions_tco2e),
            'exportedElectricityMwh': (
                str(result.exported_electricity_mwh)
                if result.exported_electricity_mwh is not None
                else None
            ),
        },
    )
    db.commit()
    db.refresh(result)
    return _execution_response(result, idempotent_replay=False)


def list_purchased_electricity_results(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
) -> Page[PurchasedElectricityResultSummary]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = (
        select(CbamPurchasedElectricityResult)
        .where(
            CbamPurchasedElectricityResult.organization_id == organization_id,
            CbamPurchasedElectricityResult.reporting_period_binding_id == binding_id,
        )
        .order_by(CbamPurchasedElectricityResult.created_at.desc())
    )
    total = db.execute(
        select(func.count()).select_from(
            select(CbamPurchasedElectricityResult.id)
            .where(
                CbamPurchasedElectricityResult.organization_id == organization_id,
                CbamPurchasedElectricityResult.reporting_period_binding_id == binding_id,
            )
            .subquery()
        )
    ).scalar_one()
    rows = list(
        db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars()
    )
    out: list[PurchasedElectricityResultSummary] = []
    for row in rows:
        pointer = _current_pointer(
            db,
            organization_id=organization_id,
            binding_id=binding_id,
            activity_id=row.activity_record_id,
        )
        is_current = pointer is not None and pointer.current_result_id == row.id
        stale: list[str] = []
        if is_current:
            activity = db.get(CbamActivityRecord, row.activity_record_id)
            if activity is not None:
                stale = compute_stale_reasons(activity, row)
        out.append(
            PurchasedElectricityResultSummary(
                result_id=row.id,
                run_id=row.calculation_run_id,
                activity_record_id=row.activity_record_id,
                status=row.status,
                is_current=is_current,
                is_stale=bool(stale),
                stale_reason_codes=stale,
                electricity_mwh=row.electricity_mwh,
                factor_source_mode=row.factor_source_mode,
                factor_value=row.factor_value,
                factor_unit=row.factor_unit,
                indirect_emissions_tco2e=row.indirect_emissions_tco2e,
                result_unit=row.result_unit,
                exported_electricity_mwh=row.exported_electricity_mwh,
                created_at=row.created_at,
            )
        )
    return paginate(out, page=page, page_size=page_size, total_items=int(total))


def get_purchased_electricity_result(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result_id: uuid.UUID,
) -> PurchasedElectricityResultDetail:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    row = db.execute(
        select(CbamPurchasedElectricityResult).where(
            CbamPurchasedElectricityResult.id == result_id,
            CbamPurchasedElectricityResult.organization_id == organization_id,
            CbamPurchasedElectricityResult.reporting_period_binding_id == binding_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Purchased-electricity result not found.')
    pointer = _current_pointer(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        activity_id=row.activity_record_id,
    )
    is_current = pointer is not None and pointer.current_result_id == row.id
    stale: list[str] = []
    if is_current:
        activity = db.get(CbamActivityRecord, row.activity_record_id)
        if activity is not None:
            stale = compute_stale_reasons(activity, row)
    return PurchasedElectricityResultDetail(
        result_id=row.id,
        run_id=row.calculation_run_id,
        organization_id=row.organization_id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        activity_record_id=row.activity_record_id,
        methodology_code=row.methodology_code,
        methodology_version=row.methodology_version,
        formula_version=row.formula_version,
        workbook_formula_refs=row.workbook_formula_refs,
        client_request_id=row.client_request_id,
        request_fingerprint=row.request_fingerprint,
        status=row.status,
        is_current=is_current,
        is_stale=bool(stale),
        stale_reason_codes=stale,
        calculation_reference_date=row.calculation_reference_date,
        activity_quantity=row.activity_quantity,
        activity_unit=row.activity_unit,
        electricity_mwh=row.electricity_mwh,
        factor_source_mode=row.factor_source_mode,
        factor_value=row.factor_value,
        factor_unit=row.factor_unit,
        factor_tco2e_per_mwh=row.factor_tco2e_per_mwh,
        factor_value_id=row.factor_value_id,
        factor_definition_id=row.factor_definition_id,
        factor_source_name=row.factor_source_name,
        factor_source_document=row.factor_source_document,
        factor_dataset_version=row.factor_dataset_version,
        factor_reference_description=row.factor_reference_description,
        factor_effective_date=row.factor_effective_date,
        factor_valid_from=row.factor_valid_from,
        factor_valid_until=row.factor_valid_until,
        exported_electricity_quantity=row.exported_electricity_quantity,
        exported_electricity_unit=row.exported_electricity_unit,
        exported_electricity_mwh=row.exported_electricity_mwh,
        indirect_emissions_tco2e=row.indirect_emissions_tco2e,
        result_value=row.result_value,
        result_unit=row.result_unit,
        evidence_notes=row.evidence_notes,
        created_at=row.created_at,
        created_by_user_id=row.created_by_user_id,
    )


def get_purchased_electricity_summary(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> PurchasedElectricityPeriodSummary:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    activities = list(
        db.execute(
            select(CbamActivityRecord).where(
                CbamActivityRecord.organization_id == organization_id,
                CbamActivityRecord.reporting_period_binding_id == binding_id,
                CbamActivityRecord.activity_type == ELECTRICITY_ACTIVITY_TYPE,
                CbamActivityRecord.status == 'active',
            )
        ).scalars()
    )
    eligible = [
        a
        for a in activities
        if a.unit in ELECTRICITY_QUANTITY_UNITS and a.quantity >= ZERO
    ]
    pointers = {
        p.activity_record_id: p
        for p in db.execute(
            select(CbamPurchasedElectricityCurrentResult).where(
                CbamPurchasedElectricityCurrentResult.organization_id == organization_id,
                CbamPurchasedElectricityCurrentResult.reporting_period_binding_id == binding_id,
            )
        ).scalars()
    }
    valid = 0
    stale_count = 0
    missing = 0
    total_mwh = ZERO
    total_emissions = ZERO
    total_exported = ZERO
    has_exported = False
    blocking: list[str] = []
    for activity in eligible:
        pointer = pointers.get(activity.id)
        if pointer is None:
            missing += 1
            continue
        result = db.get(CbamPurchasedElectricityResult, pointer.current_result_id)
        if result is None:
            missing += 1
            continue
        reasons = compute_stale_reasons(activity, result)
        if reasons:
            stale_count += 1
        else:
            valid += 1
            total_mwh += result.electricity_mwh
            total_emissions += result.indirect_emissions_tco2e
            if result.exported_electricity_mwh is not None:
                total_exported += result.exported_electricity_mwh
                has_exported = True
    if not eligible:
        blocking.append('ELECTRICITY_ACTIVITIES_REQUIRED')
        readiness = 'EMPTY'
    elif missing > 0:
        blocking.append('ELECTRICITY_RESULTS_INCOMPLETE')
        readiness = 'INCOMPLETE'
    elif stale_count > 0:
        blocking.append('ELECTRICITY_RESULTS_STALE')
        readiness = 'STALE'
    else:
        readiness = 'READY'
    # Non-blocking seed-data note always present until a provenance-backed default exists.
    info = [TURKEY_DEFAULT_FACTOR_SEED_BLOCKER]
    return PurchasedElectricityPeriodSummary(
        reporting_period_binding_id=binding_id,
        methodology_code=METHODOLOGY_CODE,
        readiness_status=readiness,
        allocation_ready=False,  # product allocation out of Phase 8A
        blocking_issue_codes=blocking,
        informational_issue_codes=info,
        eligible_activity_count=len(eligible),
        valid_current_result_count=valid,
        missing_result_count=missing,
        stale_result_count=stale_count,
        total_electricity_mwh=total_mwh if valid else None,
        total_indirect_emissions_tco2e=total_emissions if valid else None,
        total_exported_electricity_mwh=total_exported if has_exported else None,
        result_unit=RESULT_UNIT,
    )


def get_purchased_electricity_readiness(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> PurchasedElectricityPeriodSummary:
    return get_purchased_electricity_summary(db, user, organization_id, binding_id)


def get_exported_electricity_mwh_by_installation(
    db: Session,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> dict[uuid.UUID, Decimal]:
    """Facility exported MWh per installation from current, non-stale results.

    Read-only: consumers use this for reconciliation against process-level D_Processes
    L71 entries. Installations without any exported figure are absent from the mapping.
    """
    activities = {
        activity.id: activity
        for activity in db.execute(
            select(CbamActivityRecord).where(
                CbamActivityRecord.organization_id == organization_id,
                CbamActivityRecord.reporting_period_binding_id == binding_id,
                CbamActivityRecord.activity_type == ELECTRICITY_ACTIVITY_TYPE,
                CbamActivityRecord.status == 'active',
            )
        ).scalars()
    }
    totals: dict[uuid.UUID, Decimal] = {}
    for pointer in db.execute(
        select(CbamPurchasedElectricityCurrentResult).where(
            CbamPurchasedElectricityCurrentResult.organization_id == organization_id,
            CbamPurchasedElectricityCurrentResult.reporting_period_binding_id == binding_id,
        )
    ).scalars():
        activity = activities.get(pointer.activity_record_id)
        if activity is None:
            continue
        result = db.get(CbamPurchasedElectricityResult, pointer.current_result_id)
        if result is None or result.exported_electricity_mwh is None:
            continue
        if compute_stale_reasons(activity, result):
            continue
        key = activity.installation_profile_id
        totals[key] = totals.get(key, ZERO) + result.exported_electricity_mwh
    return totals
