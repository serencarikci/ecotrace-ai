from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, ConflictError
from ecotrace.modules.cbam.application.collection_guards import (
    MUTATION_BLOCKED_BINDING_STATUSES,
    WRITABLE_BINDING_STATUSES,
    get_binding_for_org,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.installation_service import count_usable_installations
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import CbamReportingPeriodBinding
from ecotrace.modules.cbam.infrastructure.reporting_period_reference_adapter import (
    require_reporting_period_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


class PeriodBindingCreate(CamelModel):
    reporting_period_id: uuid.UUID


class PeriodBindingUpdate(CamelModel):
    row_version: int


class PeriodBindingVersionRequest(CamelModel):
    row_version: int


class PeriodBindingResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_id: uuid.UUID
    status: str
    locked_at: datetime | None
    locked_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    approved_calculation_run_id: uuid.UUID | None
    revision_number: int
    row_version: int


def _to_response(row: CbamReportingPeriodBinding) -> PeriodBindingResponse:
    return PeriodBindingResponse.model_validate(row)


def _reject_if_locked(row: CbamReportingPeriodBinding) -> None:
    if row.status in MUTATION_BLOCKED_BINDING_STATUSES:
        raise BusinessRuleError(
            "Locked or approved CBAM reporting period bindings cannot be mutated "
            "(approve/lock transitions are deferred until D-030).",
            details=[{"code": "BLOCKED_DOMAIN", "decision": "D-030", "status": row.status}],
        )


def list_period_bindings(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
) -> Page[PeriodBindingResponse]:
    require_cbam_view(db, user, organization_id)
    stmt = select(CbamReportingPeriodBinding).where(
        CbamReportingPeriodBinding.organization_id == organization_id
    )
    if status:
        stmt = stmt.where(CbamReportingPeriodBinding.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamReportingPeriodBinding.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_period_binding(
    db: Session, user: User, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> PeriodBindingResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(get_binding_for_org(db, organization_id, binding_id))


def create_period_binding(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: PeriodBindingCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PeriodBindingResponse:
    require_cbam_configure(db, user, organization_id)
    period = require_reporting_period_in_organization(
        db, organization_id, payload.reporting_period_id
    )
    exists = db.execute(
        select(CbamReportingPeriodBinding.id).where(
            CbamReportingPeriodBinding.organization_id == organization_id,
            CbamReportingPeriodBinding.reporting_period_id == period.id,
        )
    ).scalar_one_or_none()
    if exists:
        raise ConflictError(
            "A CBAM reporting period binding already exists for this reporting period."
        )
    row = CbamReportingPeriodBinding(
        organization_id=organization_id,
        reporting_period_id=period.id,
        status="draft",
        revision_number=0,
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="cbam.period_binding.created",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_reporting_period_binding",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "reportingPeriodId": str(row.reporting_period_id),
            "status": row.status,
            "genericPeriodStatus": period.status,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def update_period_binding(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: PeriodBindingUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PeriodBindingResponse:
    require_cbam_configure(db, user, organization_id)
    row = get_binding_for_org(db, organization_id, binding_id)
    _reject_if_locked(row)
    if row.status not in WRITABLE_BINDING_STATUSES:
        raise BusinessRuleError(
            "This CBAM reporting period binding status cannot be updated in Phase 2.",
            details=[{"code": "BLOCKED_DOMAIN", "status": row.status}],
        )
    check_row_version(row.row_version, payload.row_version, entity="CBAM reporting period binding")
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action="cbam.period_binding.updated",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_reporting_period_binding",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"rowVersion": row.row_version},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def open_data_collection(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: PeriodBindingVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PeriodBindingResponse:
    require_cbam_configure(db, user, organization_id)
    row = get_binding_for_org(db, organization_id, binding_id)
    _reject_if_locked(row)
    check_row_version(row.row_version, payload.row_version, entity="CBAM reporting period binding")
    if row.status != "draft":
        raise BusinessRuleError(
            "Only draft→data_collection is allowed in Phase 2. "
            "Further transitions require completeness/lock decisions (D-012/D-013/D-030/D-035).",
            details=[
                {"code": "BLOCKED_DOMAIN", "from": row.status, "attempted": "data_collection"}
            ],
        )
    if count_usable_installations(db, organization_id) < 1:
        raise BusinessRuleError(
            "Open data collection requires at least one usable CBAM installation profile "
            "(status draft or active).",
            details=[{"code": "INSTALLATION_REQUIRED"}],
        )
    previous = row.status
    row.status = "data_collection"
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action="cbam.period_binding.data_collection_opened",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_reporting_period_binding",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"from": previous, "to": row.status},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def archive_period_binding(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: PeriodBindingVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PeriodBindingResponse:
    require_cbam_configure(db, user, organization_id)
    row = get_binding_for_org(db, organization_id, binding_id)
    _reject_if_locked(row)
    check_row_version(row.row_version, payload.row_version, entity="CBAM reporting period binding")
    if row.status != "draft":
        raise BusinessRuleError(
            "Only draft CBAM reporting period bindings can be archived in Phase 2."
        )
    previous = row.status
    row.status = "archived"
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action="cbam.period_binding.archived",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_reporting_period_binding",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"from": previous, "to": row.status},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)
