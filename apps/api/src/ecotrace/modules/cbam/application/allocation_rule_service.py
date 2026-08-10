from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.modules.cbam.application.allocation_math import (
    ALLOCATION_METHODS,
    compute_production_quantity_ratio,
    direct_assignment_ratio,
    validate_manual_ratio,
)
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    get_installation_for_org,
    get_product_profile_for_org,
    require_usable_installation,
    require_writable_binding,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import (
    CbamAllocationResult,
    CbamAllocationRule,
    CbamProductionRecord,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


class AllocationRuleCreate(CamelModel):
    installation_profile_id: uuid.UUID
    product_profile_version_id: uuid.UUID | None = None
    allocation_method: str
    name: str
    description: str | None = None
    allocation_ratio: Decimal | None = None
    numerator_production_record_id: uuid.UUID | None = None
    denominator_production_record_id: uuid.UUID | None = None
    rationale: str | None = None
    source_reference: str | None = None


class AllocationRuleUpdate(CamelModel):
    row_version: int
    name: str | None = None
    description: str | None = None
    product_profile_version_id: uuid.UUID | None = None
    allocation_method: str | None = None
    allocation_ratio: Decimal | None = None
    numerator_production_record_id: uuid.UUID | None = None
    denominator_production_record_id: uuid.UUID | None = None
    rationale: str | None = None
    source_reference: str | None = None


class AllocationRuleVersionRequest(CamelModel):
    row_version: int


class AllocationRuleResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    installation_profile_id: uuid.UUID
    product_profile_version_id: uuid.UUID | None
    allocation_method: str
    name: str
    description: str | None
    allocation_ratio: Decimal | None
    numerator_production_record_id: uuid.UUID | None
    denominator_production_record_id: uuid.UUID | None
    numerator_quantity: Decimal | None
    denominator_quantity: Decimal | None
    quantity_unit: str | None
    rationale: str | None
    source_reference: str | None
    status: str
    row_version: int
    archived_at: datetime | None


def _to_response(row: CbamAllocationRule) -> AllocationRuleResponse:
    return AllocationRuleResponse.model_validate(row)


def _get_rule(db: Session, organization_id: uuid.UUID, rule_id: uuid.UUID) -> CbamAllocationRule:
    row = db.get(CbamAllocationRule, rule_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM allocation rule not found.')
    return row


def _get_production(
    db: Session, organization_id: uuid.UUID, record_id: uuid.UUID
) -> CbamProductionRecord:
    row = db.get(CbamProductionRecord, record_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM production record not found.')
    return row


def _has_current_results(db: Session, rule_id: uuid.UUID) -> bool:
    return (
        db.execute(
            select(CbamAllocationResult.id)
            .where(
                CbamAllocationResult.allocation_rule_id == rule_id,
                CbamAllocationResult.is_current.is_(True),
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _assert_no_other_active(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    installation_id: uuid.UUID,
    product_profile_version_id: uuid.UUID | None,
    exclude_rule_id: uuid.UUID | None = None,
) -> None:
    stmt = select(CbamAllocationRule.id).where(
        CbamAllocationRule.organization_id == organization_id,
        CbamAllocationRule.reporting_period_binding_id == binding_id,
        CbamAllocationRule.installation_profile_id == installation_id,
        CbamAllocationRule.status == 'ACTIVE',
    )
    if product_profile_version_id is None:
        stmt = stmt.where(CbamAllocationRule.product_profile_version_id.is_(None))
    else:
        stmt = stmt.where(
            CbamAllocationRule.product_profile_version_id == product_profile_version_id
        )
    if exclude_rule_id is not None:
        stmt = stmt.where(CbamAllocationRule.id != exclude_rule_id)
    if db.execute(stmt.limit(1)).scalar_one_or_none() is not None:
        raise ConflictError(
            'An ACTIVE allocation rule already exists for this allocation scope.',
            details=[{'code': 'ACTIVE_RULE_EXISTS'}],
        )


def _apply_method_fields(row: CbamAllocationRule, *, db: Session, organization_id: uuid.UUID) -> None:
    method = row.allocation_method
    if method not in ALLOCATION_METHODS:
        raise ValidationAppError(f'Unsupported allocationMethod: {method}')

    if method == 'DIRECT_ASSIGNMENT':
        row.allocation_ratio = direct_assignment_ratio()
        row.numerator_production_record_id = None
        row.denominator_production_record_id = None
        row.numerator_quantity = None
        row.denominator_quantity = None
        row.quantity_unit = None
        return

    if method == 'MANUAL_RATIO':
        if row.allocation_ratio is None:
            raise ValidationAppError(
                'Manual allocation requires allocationRatio.',
                details=[{'field': 'allocationRatio', 'message': 'Required.'}],
            )
        rationale = (row.rationale or '').strip()
        if not rationale:
            raise ValidationAppError(
                'Manual allocation requires a non-empty rationale.',
                details=[{'field': 'rationale', 'message': 'Required.'}],
            )
        source_ref = (row.source_reference or '').strip()
        if not source_ref:
            raise ValidationAppError(
                'Manual allocation requires sourceReference or explanation.',
                details=[{'field': 'sourceReference', 'message': 'Required.'}],
            )
        row.rationale = rationale
        row.source_reference = source_ref
        row.allocation_ratio = validate_manual_ratio(row.allocation_ratio)
        row.numerator_production_record_id = None
        row.denominator_production_record_id = None
        row.numerator_quantity = None
        row.denominator_quantity = None
        row.quantity_unit = None
        return

    if row.numerator_production_record_id is None or row.denominator_production_record_id is None:
        raise ValidationAppError(
            'Production quantity ratio requires numerator and denominator production records.',
            details=[
                {'field': 'numeratorProductionRecordId', 'message': 'Required.'},
                {'field': 'denominatorProductionRecordId', 'message': 'Required.'},
            ],
        )
    numerator = _get_production(db, organization_id, row.numerator_production_record_id)
    denominator = _get_production(db, organization_id, row.denominator_production_record_id)
    if numerator.status == 'archived' or denominator.status == 'archived':
        raise BusinessRuleError('Archived production records cannot be used for allocation rules.')
    if numerator.reporting_period_binding_id != row.reporting_period_binding_id:
        raise ValidationAppError(
            'Numerator production record must belong to the same reporting-period binding.'
        )
    if denominator.reporting_period_binding_id != row.reporting_period_binding_id:
        raise ValidationAppError(
            'Denominator production record must belong to the same reporting-period binding.'
        )
    if numerator.installation_profile_id != row.installation_profile_id:
        raise ValidationAppError(
            'Numerator production record must belong to the rule installation.'
        )
    if denominator.installation_profile_id != row.installation_profile_id:
        raise ValidationAppError(
            'Denominator production record must belong to the rule installation.'
        )
    if numerator.unit != denominator.unit:
        raise ValidationAppError(
            'Numerator and denominator production units must match exactly '
            '(no silent unit conversion).',
            details=[{'field': 'unit', 'message': 'Incompatible units.'}],
        )
    ratio = compute_production_quantity_ratio(
        numerator=numerator.quantity,
        denominator=denominator.quantity,
    )
    row.allocation_ratio = ratio
    row.numerator_quantity = numerator.quantity
    row.denominator_quantity = denominator.quantity
    row.quantity_unit = numerator.unit


def validate_rule(db: Session, organization_id: uuid.UUID, rule: CbamAllocationRule) -> None:
    if not rule.name or not rule.name.strip():
        raise ValidationAppError('Allocation rule name is required.')
    rule.name = rule.name.strip()
    _apply_method_fields(rule, db=db, organization_id=organization_id)
    if rule.allocation_ratio is None:
        raise ValidationAppError('Allocation rule is missing a resolved allocationRatio.')


def list_allocation_rules(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    include_archived: bool = False,
) -> Page[AllocationRuleResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamAllocationRule).where(
        CbamAllocationRule.organization_id == organization_id,
        CbamAllocationRule.reporting_period_binding_id == binding_id,
    )
    if not include_archived:
        stmt = stmt.where(CbamAllocationRule.status != 'ARCHIVED')
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamAllocationRule.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_allocation_rule(
    db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID
) -> AllocationRuleResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(_get_rule(db, organization_id, rule_id))


def create_allocation_rule(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: AllocationRuleCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AllocationRuleResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    installation = get_installation_for_org(db, organization_id, payload.installation_profile_id)
    require_usable_installation(installation)
    product_id = payload.product_profile_version_id
    if product_id is not None:
        get_product_profile_for_org(db, organization_id, product_id)

    row = CbamAllocationRule(
        organization_id=organization_id,
        reporting_period_binding_id=binding.id,
        installation_profile_id=installation.id,
        product_profile_version_id=product_id,
        allocation_method=payload.allocation_method,
        name=payload.name,
        description=payload.description,
        allocation_ratio=payload.allocation_ratio,
        numerator_production_record_id=payload.numerator_production_record_id,
        denominator_production_record_id=payload.denominator_production_record_id,
        rationale=payload.rationale,
        source_reference=payload.source_reference,
        status='DRAFT',
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    validate_rule(db, organization_id, row)
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action='cbam.allocation_rule.created',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_allocation_rule',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'ruleId': str(row.id),
            'method': row.allocation_method,
            'ratio': str(row.allocation_ratio) if row.allocation_ratio is not None else None,
            'status': row.status,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def update_allocation_rule(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: AllocationRuleUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AllocationRuleResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_rule(db, organization_id, rule_id)
    if row.status != 'DRAFT':
        raise BusinessRuleError(
            'Only DRAFT allocation rules can be updated. Archive and create a new draft '
            'instead of mutating an ACTIVE rule that may have retained results.'
        )
    if _has_current_results(db, row.id):
        raise BusinessRuleError(
            'Allocation rules with retained current results cannot be silently mutated.'
        )
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity='CBAM allocation rule')
    data = payload.model_dump(exclude_unset=True, exclude={'row_version'})
    if 'product_profile_version_id' in data:
        pid = data['product_profile_version_id']
        if pid is not None:
            get_product_profile_for_org(db, organization_id, pid)
        row.product_profile_version_id = pid
    for field in (
        'name',
        'description',
        'allocation_method',
        'allocation_ratio',
        'numerator_production_record_id',
        'denominator_production_record_id',
        'rationale',
        'source_reference',
    ):
        if field in data:
            setattr(row, field, data[field])
    validate_rule(db, organization_id, row)
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.allocation_rule.updated',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_allocation_rule',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'ruleId': str(row.id),
            'method': row.allocation_method,
            'ratio': str(row.allocation_ratio) if row.allocation_ratio is not None else None,
            'fields': list(data.keys()),
            'rowVersion': row.row_version,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def activate_allocation_rule(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: AllocationRuleVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AllocationRuleResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_rule(db, organization_id, rule_id)
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity='CBAM allocation rule')
    if row.status == 'ARCHIVED':
        raise BusinessRuleError('Archived allocation rules cannot be activated.')
    if row.status == 'ACTIVE':
        raise BusinessRuleError('Allocation rule is already ACTIVE.')
    validate_rule(db, organization_id, row)
    _assert_no_other_active(
        db,
        organization_id=organization_id,
        binding_id=row.reporting_period_binding_id,
        installation_id=row.installation_profile_id,
        product_profile_version_id=row.product_profile_version_id,
        exclude_rule_id=row.id,
    )
    row.status = 'ACTIVE'
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.allocation_rule.activated',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_allocation_rule',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'ruleId': str(row.id),
            'method': row.allocation_method,
            'ratio': str(row.allocation_ratio) if row.allocation_ratio is not None else None,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def archive_allocation_rule(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: AllocationRuleVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AllocationRuleResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_rule(db, organization_id, rule_id)
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity='CBAM allocation rule')
    if row.status == 'ARCHIVED':
        raise BusinessRuleError('Allocation rule is already archived.')
    row.status = 'ARCHIVED'
    row.archived_at = datetime.now(UTC)
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.allocation_rule.archived',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_allocation_rule',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'ruleId': str(row.id),
            'method': row.allocation_method,
            'ratio': str(row.allocation_ratio) if row.allocation_ratio is not None else None,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)
