from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import CbamReferenceSource
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

SOURCE_TYPES = frozenset(
    {
        "STANDARD_REFERENCE",
        "PRIMARY_MEASUREMENT",
        "SUPPLIER_DECLARATION",
        "MANUAL_APPROVED",
        "OTHER",
    }
)


class ReferenceSourceCreate(CamelModel):
    code: str
    name: str
    source_type: str
    publisher: str | None = None
    version_label: str | None = None
    publication_year: int | None = None
    reference_url: str | None = None
    description: str | None = None


class ReferenceSourceUpdate(CamelModel):
    name: str | None = None
    publisher: str | None = None
    version_label: str | None = None
    publication_year: int | None = None
    reference_url: str | None = None
    description: str | None = None
    status: str | None = None


class ReferenceSourceResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    code: str
    name: str
    source_type: str
    publisher: str | None
    version_label: str | None
    publication_year: int | None
    reference_url: str | None
    description: str | None
    status: str


def _to_response(row: CbamReferenceSource) -> ReferenceSourceResponse:
    return ReferenceSourceResponse.model_validate(row)


def _get_visible(
    db: Session, organization_id: uuid.UUID, source_id: uuid.UUID
) -> CbamReferenceSource:
    row = db.get(CbamReferenceSource, source_id)
    if row is None:
        raise NotFoundError("CBAM reference source not found.")
    if row.organization_id is not None and row.organization_id != organization_id:
        raise NotFoundError("CBAM reference source not found.")
    return row


def list_reference_sources(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    include_archived: bool = False,
) -> Page[ReferenceSourceResponse]:
    require_cbam_view(db, user, organization_id)
    ensure_platform_factor_catalog(db)
    stmt = select(CbamReferenceSource).where(
        or_(
            CbamReferenceSource.organization_id.is_(None),
            CbamReferenceSource.organization_id == organization_id,
        )
    )
    if not include_archived:
        stmt = stmt.where(CbamReferenceSource.status != "ARCHIVED")
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamReferenceSource.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_reference_source(
    db: Session, user: User, organization_id: uuid.UUID, source_id: uuid.UUID
) -> ReferenceSourceResponse:
    require_cbam_view(db, user, organization_id)
    ensure_platform_factor_catalog(db)
    return _to_response(_get_visible(db, organization_id, source_id))


def create_reference_source(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: ReferenceSourceCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ReferenceSourceResponse:
    require_cbam_configure(db, user, organization_id)
    ensure_platform_factor_catalog(db)
    code = payload.code.strip().upper()
    if not code:
        raise ValidationAppError("code is required.")
    if payload.source_type not in SOURCE_TYPES:
        raise ValidationAppError("Invalid sourceType.")
    exists = db.execute(
        select(CbamReferenceSource.id).where(
            CbamReferenceSource.organization_id == organization_id,
            CbamReferenceSource.code == code,
        )
    ).scalar_one_or_none()
    if exists is not None:
        raise ConflictError("A reference source with this code already exists.")
    row = CbamReferenceSource(
        organization_id=organization_id,
        code=code,
        name=payload.name.strip(),
        source_type=payload.source_type,
        publisher=payload.publisher,
        version_label=payload.version_label,
        publication_year=payload.publication_year,
        reference_url=payload.reference_url,
        description=payload.description,
        status="ACTIVE",
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="cbam.reference_source.created",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_reference_source",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"code": row.code, "sourceType": row.source_type},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def update_reference_source(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    source_id: uuid.UUID,
    payload: ReferenceSourceUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ReferenceSourceResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_visible(db, organization_id, source_id)
    if row.organization_id is None:
        raise BusinessRuleError("Platform reference sources cannot be updated via org API.")
    if row.organization_id != organization_id:
        raise NotFoundError("CBAM reference source not found.")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in {"ACTIVE", "INACTIVE", "ARCHIVED"}:
        raise ValidationAppError("Invalid status.")
    for field, value in data.items():
        setattr(row, field, value)
    row.updated_by_user_id = user.id
    write_audit_log(
        db,
        action="cbam.reference_source.updated",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_reference_source",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def archive_reference_source(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    source_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ReferenceSourceResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_visible(db, organization_id, source_id)
    if row.organization_id is None:
        raise BusinessRuleError("Platform reference sources cannot be archived via org API.")
    if row.status == "ARCHIVED":
        raise BusinessRuleError("Reference source is already archived.")
    row.status = "ARCHIVED"
    row.updated_by_user_id = user.id
    write_audit_log(
        db,
        action="cbam.reference_source.archived",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_reference_source",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"code": row.code, "archivedAt": datetime.now(UTC).isoformat()},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)
