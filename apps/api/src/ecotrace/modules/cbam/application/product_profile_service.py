from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import CbamProductProfileVersion
from ecotrace.modules.cbam.infrastructure.product_reference_adapter import (
    require_product_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


class ProductProfileCreate(CamelModel):
    product_id: uuid.UUID
    version: int = 1
    valid_from: date | None = None
    valid_to: date | None = None


class ProductProfileVersionRequest(CamelModel):
    row_version: int


class ProductProfileResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    product_id: uuid.UUID
    version: int
    status: str
    valid_from: date | None
    valid_to: date | None
    classification_ready: bool
    row_version: int


def _to_response(row: CbamProductProfileVersion) -> ProductProfileResponse:
    return ProductProfileResponse(
        id=row.id,
        organization_id=row.organization_id,
        product_id=row.product_id,
        version=row.version,
        status=row.status,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        classification_ready=False,
        row_version=row.row_version,
    )


def _get_row(
    db: Session, organization_id: uuid.UUID, profile_id: uuid.UUID
) -> CbamProductProfileVersion:
    row = db.get(CbamProductProfileVersion, profile_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM product profile version not found.')
    return row


def list_product_profiles(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    product_id: uuid.UUID | None = None,
    status: str | None = None,
) -> Page[ProductProfileResponse]:
    require_cbam_view(db, user, organization_id)
    stmt = select(CbamProductProfileVersion).where(
        CbamProductProfileVersion.organization_id == organization_id
    )
    if product_id is not None:
        stmt = stmt.where(CbamProductProfileVersion.product_id == product_id)
    if status:
        stmt = stmt.where(CbamProductProfileVersion.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(
                CbamProductProfileVersion.product_id.asc(),
                CbamProductProfileVersion.version.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_product_profile(
    db: Session, user: User, organization_id: uuid.UUID, profile_id: uuid.UUID
) -> ProductProfileResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(_get_row(db, organization_id, profile_id))


def create_product_profile(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: ProductProfileCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductProfileResponse:
    require_cbam_configure(db, user, organization_id)
    product = require_product_in_organization(db, organization_id, payload.product_id)
    if payload.version < 1:
        raise ValidationAppError('Version must be >= 1.')
    if payload.valid_from and payload.valid_to and payload.valid_to < payload.valid_from:
        raise ValidationAppError('validTo must be on or after validFrom.')
    exists = db.execute(
        select(CbamProductProfileVersion.id).where(
            CbamProductProfileVersion.organization_id == organization_id,
            CbamProductProfileVersion.product_id == product.id,
            CbamProductProfileVersion.version == payload.version,
        )
    ).scalar_one_or_none()
    if exists:
        raise ConflictError(
            'A CBAM product profile version already exists for this product and version.'
        )
    row = CbamProductProfileVersion(
        organization_id=organization_id,
        product_id=product.id,
        version=payload.version,
        status='draft',
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        classification_ready=False,
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action='cbam.product_profile.created',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_product_profile_version',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'productId': str(row.product_id),
            'version': row.version,
            'status': row.status,
            'classificationReady': False,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def archive_product_profile(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    profile_id: uuid.UUID,
    payload: ProductProfileVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductProfileResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, profile_id)
    check_row_version(row.row_version, payload.row_version, entity='CBAM product profile version')
    if row.status != 'draft':
        raise BusinessRuleError(
            'Only draft product profile versions can be archived in Phase 2. '
            'Activate/supersede are deferred until D-029.'
        )
    previous = row.status
    row.status = 'archived'
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.product_profile.archived',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_product_profile_version',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'from': previous, 'to': row.status},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def reject_classification_ready_true() -> None:
    raise BusinessRuleError(
        'classificationReady cannot be set to true until CN/AGC classification is implemented.',
        details=[{'code': 'CLASSIFICATION_NOT_READY', 'phase': 2}],
    )
