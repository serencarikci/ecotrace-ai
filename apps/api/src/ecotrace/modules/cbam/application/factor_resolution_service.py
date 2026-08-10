from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.catalogs import units_exactly_compatible
from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.factor_catalog_service import get_definition_by_code
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityProperty,
    CbamActivityRecord,
    CbamAllocationResult,
    CbamFactorDefinition,
    CbamFactorResolution,
    CbamFactorValue,
    CbamPurchasedInputRecord,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

RESOLVER_VERSION = 'factor-resolution-v1'

SOURCE_ACTIVITY = 'ACTIVITY_RECORD'
SOURCE_PURCHASED = 'PURCHASED_INPUT_RECORD'
SOURCE_ALLOCATION = 'ALLOCATION_RESULT'


class FactorResolutionResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    factor_definition_id: uuid.UUID
    resolution_status: str
    selected_activity_property_id: uuid.UUID | None
    selected_factor_value_id: uuid.UUID | None
    selected_value: Decimal | None
    selected_unit: str | None
    source_precedence: str | None
    resolution_reason: str
    resolver_version: str
    resolved_at: datetime
    is_current: bool
    superseded_at: datetime | None


@dataclass(slots=True)
class _Candidate:
    kind: str
    precedence: str
    value: Decimal
    unit: str
    property_id: uuid.UUID | None = None
    factor_value_id: uuid.UUID | None = None
    valid: bool = True
    invalid_reason: str | None = None


def _to_response(row: CbamFactorResolution) -> FactorResolutionResponse:
    return FactorResolutionResponse.model_validate(row)


def _as_of_date(
    *,
    activity_date: date | None,
    period_start: date | None,
    period_end: date | None,
) -> date:
    if activity_date is not None:
        return activity_date
    if period_end is not None:
        return period_end
    if period_start is not None:
        return period_start
    return datetime.now(UTC).date()


def _validity_ok(value: CbamFactorValue, as_of: date) -> bool:
    if value.valid_from is not None and as_of < value.valid_from:
        return False
    return not (value.valid_until is not None and as_of > value.valid_until)


def _pick_candidates(
    candidates: list[_Candidate],
) -> tuple[str, _Candidate | None, str]:
    for precedence, status, reason_ok, reason_ambiguous in (
        (
            'RECORD_PRIMARY',
            'RESOLVED_PRIMARY',
            'Primary value selected because an active supplier-provided or measured '
            'property was available for this source record.',
            'Resolution failed because two active primary candidates matched the same '
            'record and validity context.',
        ),
        (
            'ORG_PRIMARY',
            'RESOLVED_PRIMARY',
            'Primary value selected because an active organization-level PRIMARY factor '
            'value was available.',
            'Resolution failed because two active organization PRIMARY factor values '
            'matched the same activity and validity period.',
        ),
        (
            'DEFAULT_REFERENCE',
            'RESOLVED_DEFAULT',
            'Default reference selected because no compatible active primary value was '
            'available.',
            'Resolution failed because two active default references matched the same '
            'activity and validity period.',
        ),
    ):
        tier = [c for c in candidates if c.precedence == precedence and c.valid]
        if len(tier) == 1:
            return status, tier[0], reason_ok
        if len(tier) > 1:
            return 'AMBIGUOUS', None, reason_ambiguous

    invalid_units = [c for c in candidates if c.invalid_reason == 'INCOMPATIBLE_UNIT']
    outside = [c for c in candidates if c.invalid_reason == 'OUTSIDE_VALIDITY']
    if candidates and not any(c.valid for c in candidates):
        if invalid_units and not outside:
            return (
                'INCOMPATIBLE_UNIT',
                None,
                'Resolution failed because candidate units were incompatible with the '
                'required factor/property unit.',
            )
        if outside and not invalid_units:
            return (
                'OUTSIDE_VALIDITY',
                None,
                'Resolution failed because candidate values were outside their validity '
                'range for the source date.',
            )
        return (
            'UNRESOLVED',
            None,
            'Resolution failed because no compatible active primary or default value '
            'was available.',
        )
    return (
        'UNRESOLVED',
        None,
        'Resolution failed because no compatible active primary or default value '
        'was available.',
    )


def _collect_activity_property_candidates(
    db: Session,
    *,
    organization_id: uuid.UUID,
    activity: CbamActivityRecord,
    definition: CbamFactorDefinition,
    as_of: date,
) -> list[_Candidate]:
    if not definition.property_code:
        return []
    props = (
        db.execute(
            select(CbamActivityProperty).where(
                CbamActivityProperty.organization_id == organization_id,
                CbamActivityProperty.activity_record_id == activity.id,
                CbamActivityProperty.property_code == definition.property_code,
            )
        )
        .scalars()
        .all()
    )
    out: list[_Candidate] = []
    for prop in props:
        if prop.source_type != 'PRIMARY':
            continue
        out.append(
            _Candidate(
                kind='ACTIVITY_PROPERTY',
                precedence='RECORD_PRIMARY',
                value=prop.numeric_value,
                unit=prop.unit,
                property_id=prop.id,
                valid=True,
            )
        )
    _ = as_of
    return out


def _collect_factor_value_candidates(
    db: Session,
    *,
    organization_id: uuid.UUID,
    definition: CbamFactorDefinition,
    activity_type: str | None,
    as_of: date,
) -> list[_Candidate]:
    stmt = select(CbamFactorValue).where(
        CbamFactorValue.factor_definition_id == definition.id,
        CbamFactorValue.status == 'ACTIVE',
        or_(
            CbamFactorValue.organization_id == organization_id,
            CbamFactorValue.organization_id.is_(None),
        ),
    )
    if activity_type:
        stmt = stmt.where(
            or_(
                CbamFactorValue.activity_type == activity_type,
                CbamFactorValue.activity_type.is_(None),
            )
        )
    rows = list(db.execute(stmt).scalars().all())
    out: list[_Candidate] = []
    for row in rows:
        if row.organization_id not in (None, organization_id):
            continue
        precedence = (
            'ORG_PRIMARY' if row.data_source_type == 'PRIMARY' else 'DEFAULT_REFERENCE'
        )
        if row.data_source_type == 'PRIMARY' and row.organization_id is None:
            continue
        valid = True
        invalid_reason = None
        if not _validity_ok(row, as_of):
            valid = False
            invalid_reason = 'OUTSIDE_VALIDITY'
        out.append(
            _Candidate(
                kind='FACTOR_VALUE',
                precedence=precedence,
                value=row.numeric_value,
                unit=row.unit,
                factor_value_id=row.id,
                valid=valid,
                invalid_reason=invalid_reason,
            )
        )
    return out


def _resolve_core(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    definition: CbamFactorDefinition,
    activity_type: str | None,
    as_of: date,
    record_primary_candidates: list[_Candidate],
    purchased_primary: _Candidate | None = None,
) -> tuple[str, _Candidate | None, str]:
    preferred_unit = None
    if record_primary_candidates:
        preferred_unit = record_primary_candidates[0].unit
    if purchased_primary is not None:
        preferred_unit = purchased_primary.unit
    factor_candidates = _collect_factor_value_candidates(
        db,
        organization_id=organization_id,
        definition=definition,
        activity_type=activity_type,
        as_of=as_of,
    )
    if preferred_unit is not None:
        adjusted: list[_Candidate] = []
        for c in factor_candidates:
            if c.valid and not units_exactly_compatible(c.unit, preferred_unit):
                adjusted.append(
                    _Candidate(
                        kind=c.kind,
                        precedence=c.precedence,
                        value=c.value,
                        unit=c.unit,
                        property_id=c.property_id,
                        factor_value_id=c.factor_value_id,
                        valid=False,
                        invalid_reason='INCOMPATIBLE_UNIT',
                    )
                )
            else:
                adjusted.append(c)
        factor_candidates = adjusted

    candidates = list(record_primary_candidates)
    if purchased_primary is not None:
        candidates.append(purchased_primary)
    candidates.extend(factor_candidates)
    _ = (binding_id, source_type, source_id)
    return _pick_candidates(candidates)


def _supersede_current(
    db: Session,
    *,
    organization_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    definition_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    rows = (
        db.execute(
            select(CbamFactorResolution).where(
                CbamFactorResolution.organization_id == organization_id,
                CbamFactorResolution.source_type == source_type,
                CbamFactorResolution.source_id == source_id,
                CbamFactorResolution.factor_definition_id == definition_id,
                CbamFactorResolution.is_current.is_(True),
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.is_current = False
        row.superseded_at = now


def _persist(
    db: Session,
    *,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    definition: CbamFactorDefinition,
    status: str,
    selected: _Candidate | None,
    reason: str,
    audit_action: str,
    request_id: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> CbamFactorResolution:
    _supersede_current(
        db,
        organization_id=organization_id,
        source_type=source_type,
        source_id=source_id,
        definition_id=definition.id,
    )
    now = datetime.now(UTC)
    row = CbamFactorResolution(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        source_type=source_type,
        source_id=source_id,
        factor_definition_id=definition.id,
        resolution_status=status,
        selected_activity_property_id=selected.property_id if selected else None,
        selected_factor_value_id=selected.factor_value_id if selected else None,
        selected_value=selected.value if selected else None,
        selected_unit=selected.unit if selected else None,
        source_precedence=selected.precedence if selected else None,
        resolution_reason=reason,
        resolver_version=RESOLVER_VERSION,
        resolved_at=now,
        resolved_by_user_id=user.id,
        is_current=True,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action=audit_action,
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_factor_resolution',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'sourceType': source_type,
            'sourceId': str(source_id),
            'factorDefinitionId': str(definition.id),
            'factorDefinitionCode': definition.code,
            'resolutionStatus': status,
            'sourcePrecedence': selected.precedence if selected else None,
            'selectedActivityPropertyId': str(selected.property_id)
            if selected and selected.property_id
            else None,
            'selectedFactorValueId': str(selected.factor_value_id)
            if selected and selected.factor_value_id
            else None,
            'selectedValue': str(selected.value) if selected else None,
            'selectedUnit': selected.unit if selected else None,
        },
    )
    return row


def resolve_for_activity_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    factor_definition_code: str,
    *,
    reresolve: bool = False,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FactorResolutionResponse:
    require_cbam_configure(db, user, organization_id)
    activity = db.get(CbamActivityRecord, record_id)
    if activity is None or activity.organization_id != organization_id:
        raise NotFoundError('CBAM activity record not found.')
    if activity.status == 'archived':
        raise ValidationAppError('Archived activity records cannot be resolved.')
    get_binding_for_org(db, organization_id, activity.reporting_period_binding_id)
    definition = get_definition_by_code(db, factor_definition_code)
    as_of = _as_of_date(
        activity_date=activity.activity_date,
        period_start=activity.period_start,
        period_end=activity.period_end,
    )
    record_primary = _collect_activity_property_candidates(
        db,
        organization_id=organization_id,
        activity=activity,
        definition=definition,
        as_of=as_of,
    )
    status, selected, reason = _resolve_core(
        db,
        organization_id=organization_id,
        binding_id=activity.reporting_period_binding_id,
        source_type=SOURCE_ACTIVITY,
        source_id=activity.id,
        definition=definition,
        activity_type=activity.activity_type,
        as_of=as_of,
        record_primary_candidates=record_primary,
    )
    row = _persist(
        db,
        user=user,
        organization_id=organization_id,
        binding_id=activity.reporting_period_binding_id,
        source_type=SOURCE_ACTIVITY,
        source_id=activity.id,
        definition=definition,
        status=status,
        selected=selected,
        reason=reason,
        audit_action='cbam.factor_resolution.reresolved'
        if reresolve
        else 'cbam.factor_resolution.resolved',
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def resolve_for_purchased_input(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    factor_definition_code: str,
    *,
    reresolve: bool = False,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FactorResolutionResponse:
    require_cbam_configure(db, user, organization_id)
    purchased = db.get(CbamPurchasedInputRecord, record_id)
    if purchased is None or purchased.organization_id != organization_id:
        raise NotFoundError('CBAM purchased input record not found.')
    if purchased.status == 'archived':
        raise ValidationAppError('Archived purchased input records cannot be resolved.')
    get_binding_for_org(db, organization_id, purchased.reporting_period_binding_id)
    definition = get_definition_by_code(db, factor_definition_code)
    as_of = purchased.received_date or datetime.now(UTC).date()
    purchased_primary = None
    if definition.code == 'SUPPLIER_EMBEDDED_EMISSION' and (
        purchased.embedded_emission_value is not None
        and purchased.embedded_emission_unit
        and purchased.embedded_emission_source_type == 'PRIMARY'
    ):
        purchased_primary = _Candidate(
            kind='PURCHASED_EMBEDDED',
            precedence='RECORD_PRIMARY',
            value=purchased.embedded_emission_value,
            unit=purchased.embedded_emission_unit,
            valid=True,
        )
    status, selected, reason = _resolve_core(
        db,
        organization_id=organization_id,
        binding_id=purchased.reporting_period_binding_id,
        source_type=SOURCE_PURCHASED,
        source_id=purchased.id,
        definition=definition,
        activity_type=None,
        as_of=as_of,
        record_primary_candidates=[],
        purchased_primary=purchased_primary,
    )
    row = _persist(
        db,
        user=user,
        organization_id=organization_id,
        binding_id=purchased.reporting_period_binding_id,
        source_type=SOURCE_PURCHASED,
        source_id=purchased.id,
        definition=definition,
        status=status,
        selected=selected,
        reason=reason,
        audit_action='cbam.factor_resolution.reresolved'
        if reresolve
        else 'cbam.factor_resolution.resolved',
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def resolve_for_allocation_result(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    result_id: uuid.UUID,
    factor_definition_code: str,
    *,
    reresolve: bool = False,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FactorResolutionResponse:
    require_cbam_configure(db, user, organization_id)
    alloc = db.get(CbamAllocationResult, result_id)
    if alloc is None or alloc.organization_id != organization_id:
        raise NotFoundError('CBAM allocation result not found.')
    get_binding_for_org(db, organization_id, alloc.reporting_period_binding_id)
    definition = get_definition_by_code(db, factor_definition_code)
    activity_type = None
    as_of = datetime.now(UTC).date()
    record_primary: list[_Candidate] = []
    purchased_primary = None
    if alloc.source_type == SOURCE_ACTIVITY:
        activity = db.get(CbamActivityRecord, alloc.source_id)
        if activity is None or activity.organization_id != organization_id:
            raise NotFoundError('Underlying activity record not found for allocation result.')
        activity_type = activity.activity_type
        as_of = _as_of_date(
            activity_date=activity.activity_date,
            period_start=activity.period_start,
            period_end=activity.period_end,
        )
        record_primary = _collect_activity_property_candidates(
            db,
            organization_id=organization_id,
            activity=activity,
            definition=definition,
            as_of=as_of,
        )
    elif alloc.source_type == SOURCE_PURCHASED:
        purchased = db.get(CbamPurchasedInputRecord, alloc.source_id)
        if purchased is None or purchased.organization_id != organization_id:
            raise NotFoundError('Underlying purchased input not found for allocation result.')
        as_of = purchased.received_date or as_of
        if (
            definition.code == 'SUPPLIER_EMBEDDED_EMISSION'
            and purchased.embedded_emission_value is not None
            and purchased.embedded_emission_unit
            and purchased.embedded_emission_source_type == 'PRIMARY'
        ):
            purchased_primary = _Candidate(
                kind='PURCHASED_EMBEDDED',
                precedence='RECORD_PRIMARY',
                value=purchased.embedded_emission_value,
                unit=purchased.embedded_emission_unit,
                valid=True,
            )
    status, selected, reason = _resolve_core(
        db,
        organization_id=organization_id,
        binding_id=alloc.reporting_period_binding_id,
        source_type=SOURCE_ALLOCATION,
        source_id=alloc.id,
        definition=definition,
        activity_type=activity_type,
        as_of=as_of,
        record_primary_candidates=record_primary,
        purchased_primary=purchased_primary,
    )
    _ = alloc.allocated_quantity
    row = _persist(
        db,
        user=user,
        organization_id=organization_id,
        binding_id=alloc.reporting_period_binding_id,
        source_type=SOURCE_ALLOCATION,
        source_id=alloc.id,
        definition=definition,
        status=status,
        selected=selected,
        reason=reason,
        audit_action='cbam.factor_resolution.reresolved'
        if reresolve
        else 'cbam.factor_resolution.resolved',
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def get_factor_resolution(
    db: Session, user: User, organization_id: uuid.UUID, resolution_id: uuid.UUID
) -> FactorResolutionResponse:
    require_cbam_view(db, user, organization_id)
    row = db.get(CbamFactorResolution, resolution_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM factor resolution not found.')
    return _to_response(row)


def list_factor_resolutions(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    current_only: bool = True,
) -> Page[FactorResolutionResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamFactorResolution).where(
        CbamFactorResolution.organization_id == organization_id,
        CbamFactorResolution.reporting_period_binding_id == binding_id,
    )
    if current_only:
        stmt = stmt.where(CbamFactorResolution.is_current.is_(True))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamFactorResolution.resolved_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )
