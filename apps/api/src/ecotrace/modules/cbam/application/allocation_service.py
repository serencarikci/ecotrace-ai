from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.allocation_math import (
    CALCULATION_VERSION,
    compute_allocated_quantity,
)
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    require_writable_binding,
)
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamAllocationResult,
    CbamAllocationRule,
    CbamPurchasedInputRecord,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

SOURCE_ACTIVITY = 'ACTIVITY_RECORD'
SOURCE_PURCHASED = 'PURCHASED_INPUT_RECORD'


class AllocationResultResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    allocation_rule_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    source_quantity: Decimal
    source_unit: str
    allocation_ratio: Decimal
    allocated_quantity: Decimal
    allocated_unit: str
    allocation_method: str
    calculation_version: str
    is_current: bool
    superseded_at: datetime | None
    created_at: datetime


def _to_response(row: CbamAllocationResult) -> AllocationResultResponse:
    return AllocationResultResponse.model_validate(row)


def _get_rule(db: Session, organization_id: uuid.UUID, rule_id: uuid.UUID) -> CbamAllocationRule:
    row = db.get(CbamAllocationRule, rule_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM allocation rule not found.')
    return row


def _get_result(
    db: Session, organization_id: uuid.UUID, result_id: uuid.UUID
) -> CbamAllocationResult:
    row = db.get(CbamAllocationResult, result_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM allocation result not found.')
    return row


def _require_active_rule(rule: CbamAllocationRule) -> None:
    if rule.status == 'ARCHIVED':
        raise BusinessRuleError('Archived allocation rules cannot be used for new allocations.')
    if rule.status != 'ACTIVE':
        raise BusinessRuleError('Allocation rule must be ACTIVE before normal allocation.')
    if rule.allocation_ratio is None:
        raise BusinessRuleError('ACTIVE allocation rule is missing allocationRatio.')


def _resolve_activity_source(
    db: Session, organization_id: uuid.UUID, rule: CbamAllocationRule, activity_id: uuid.UUID
) -> tuple[Decimal, str]:
    row = db.get(CbamActivityRecord, activity_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM activity record not found.')
    if row.status == 'archived':
        raise BusinessRuleError('Archived activity records cannot be allocated.')
    if row.reporting_period_binding_id != rule.reporting_period_binding_id:
        raise ValidationAppError('Activity record is outside the allocation rule reporting period.')
    if row.installation_profile_id != rule.installation_profile_id:
        raise ValidationAppError('Activity record installation does not match the allocation rule.')
    return row.quantity, row.unit


def _resolve_purchased_source(
    db: Session, organization_id: uuid.UUID, rule: CbamAllocationRule, input_id: uuid.UUID
) -> tuple[Decimal, str]:
    row = db.get(CbamPurchasedInputRecord, input_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM purchased input record not found.')
    if row.status == 'archived':
        raise BusinessRuleError('Archived purchased input records cannot be allocated.')
    if row.reporting_period_binding_id != rule.reporting_period_binding_id:
        raise ValidationAppError(
            'Purchased input record is outside the allocation rule reporting period.'
        )
    if row.installation_profile_id != rule.installation_profile_id:
        raise ValidationAppError(
            'Purchased input installation does not match the allocation rule.'
        )
    if row.consumed_quantity is None or row.consumed_unit is None:
        raise BusinessRuleError(
            'Purchased input allocation requires an explicit consumedQuantity '
            '(purchased quantity is not substituted).',
            details=[{'code': 'CONSUMED_QUANTITY_REQUIRED'}],
        )
    if row.consumed_quantity <= 0:
        raise ValidationAppError('consumedQuantity must be greater than zero for allocation.')
    return row.consumed_quantity, row.consumed_unit


def _supersede_current(
    db: Session,
    *,
    organization_id: uuid.UUID,
    rule_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    current_rows = (
        db.execute(
            select(CbamAllocationResult).where(
                CbamAllocationResult.organization_id == organization_id,
                CbamAllocationResult.allocation_rule_id == rule_id,
                CbamAllocationResult.source_type == source_type,
                CbamAllocationResult.source_id == source_id,
                CbamAllocationResult.is_current.is_(True),
            )
        )
        .scalars()
        .all()
    )
    for existing in current_rows:
        existing.is_current = False
        existing.superseded_at = now


def _persist_result(
    db: Session,
    *,
    user: User,
    rule: CbamAllocationRule,
    source_type: str,
    source_id: uuid.UUID,
    source_quantity: Decimal,
    source_unit: str,
    audit_action: str,
    request_id: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> CbamAllocationResult:
    assert rule.allocation_ratio is not None
    allocated = compute_allocated_quantity(
        source_quantity=source_quantity,
        allocation_ratio=rule.allocation_ratio,
    )
    _supersede_current(
        db,
        organization_id=rule.organization_id,
        rule_id=rule.id,
        source_type=source_type,
        source_id=source_id,
    )
    result = CbamAllocationResult(
        organization_id=rule.organization_id,
        reporting_period_binding_id=rule.reporting_period_binding_id,
        allocation_rule_id=rule.id,
        source_type=source_type,
        source_id=source_id,
        source_quantity=source_quantity,
        source_unit=source_unit,
        allocation_ratio=rule.allocation_ratio,
        allocated_quantity=allocated,
        allocated_unit=source_unit,
        allocation_method=rule.allocation_method,
        calculation_version=CALCULATION_VERSION,
        is_current=True,
        created_by_user_id=user.id,
    )
    db.add(result)
    db.flush()
    write_audit_log(
        db,
        action=audit_action,
        actor_user_id=user.id,
        organization_id=rule.organization_id,
        entity_type='cbam_allocation_result',
        entity_id=str(result.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'ruleId': str(rule.id),
            'sourceId': str(source_id),
            'sourceType': source_type,
            'method': rule.allocation_method,
            'ratio': str(rule.allocation_ratio),
            'sourceQuantity': str(source_quantity),
            'allocatedQuantity': str(allocated),
            'unit': source_unit,
            'calculationVersion': CALCULATION_VERSION,
        },
    )
    return result


def allocate_activity_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    rule_id: uuid.UUID,
    activity_record_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AllocationResultResponse:
    require_cbam_configure(db, user, organization_id)
    rule = _get_rule(db, organization_id, rule_id)
    binding = get_binding_for_org(db, organization_id, rule.reporting_period_binding_id)
    require_writable_binding(binding)
    _require_active_rule(rule)
    source_quantity, source_unit = _resolve_activity_source(
        db, organization_id, rule, activity_record_id
    )
    result = _persist_result(
        db,
        user=user,
        rule=rule,
        source_type=SOURCE_ACTIVITY,
        source_id=activity_record_id,
        source_quantity=source_quantity,
        source_unit=source_unit,
        audit_action='cbam.allocation.executed',
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(result)
    return _to_response(result)


def allocate_purchased_input(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    rule_id: uuid.UUID,
    input_record_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AllocationResultResponse:
    require_cbam_configure(db, user, organization_id)
    rule = _get_rule(db, organization_id, rule_id)
    binding = get_binding_for_org(db, organization_id, rule.reporting_period_binding_id)
    require_writable_binding(binding)
    _require_active_rule(rule)
    source_quantity, source_unit = _resolve_purchased_source(
        db, organization_id, rule, input_record_id
    )
    result = _persist_result(
        db,
        user=user,
        rule=rule,
        source_type=SOURCE_PURCHASED,
        source_id=input_record_id,
        source_quantity=source_quantity,
        source_unit=source_unit,
        audit_action='cbam.allocation.executed',
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(result)
    return _to_response(result)


def recalculate_allocation_result(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    result_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AllocationResultResponse:
    require_cbam_configure(db, user, organization_id)
    previous = _get_result(db, organization_id, result_id)
    if not previous.is_current:
        raise BusinessRuleError('Only current allocation results can be recalculated.')
    rule = _get_rule(db, organization_id, previous.allocation_rule_id)
    binding = get_binding_for_org(db, organization_id, rule.reporting_period_binding_id)
    require_writable_binding(binding)
    _require_active_rule(rule)
    if previous.source_type == SOURCE_ACTIVITY:
        source_quantity, source_unit = _resolve_activity_source(
            db, organization_id, rule, previous.source_id
        )
    elif previous.source_type == SOURCE_PURCHASED:
        source_quantity, source_unit = _resolve_purchased_source(
            db, organization_id, rule, previous.source_id
        )
    else:
        raise BusinessRuleError(f'Unsupported source type for recalculation: {previous.source_type}')
    result = _persist_result(
        db,
        user=user,
        rule=rule,
        source_type=previous.source_type,
        source_id=previous.source_id,
        source_quantity=source_quantity,
        source_unit=source_unit,
        audit_action='cbam.allocation.recalculated',
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(result)
    return _to_response(result)


def list_allocation_results(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    current_only: bool = True,
) -> Page[AllocationResultResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamAllocationResult).where(
        CbamAllocationResult.organization_id == organization_id,
        CbamAllocationResult.reporting_period_binding_id == binding_id,
    )
    if current_only:
        stmt = stmt.where(CbamAllocationResult.is_current.is_(True))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamAllocationResult.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_allocation_result(
    db: Session, user: User, organization_id: uuid.UUID, result_id: uuid.UUID
) -> AllocationResultResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(_get_result(db, organization_id, result_id))
