from __future__ import annotations

import uuid
from typing import Any

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
from ecotrace.modules.cbam.infrastructure.facility_reference_adapter import (
    require_facility_in_organization,
)
from ecotrace.modules.cbam.infrastructure.models import CbamInstallationProfile
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

USABLE_INSTALLATION_STATUSES = ('draft', 'active')


class InstallationCreate(CamelModel):
    facility_id: uuid.UUID
    code: str
    name: str
    timezone: str = 'UTC'
    operator_identity_ref: str | None = None
    metadata_json: dict[str, Any] | None = None


class InstallationUpdate(CamelModel):
    row_version: int
    name: str | None = None
    timezone: str | None = None
    operator_identity_ref: str | None = None
    metadata_json: dict[str, Any] | None = None


class InstallationVersionRequest(CamelModel):
    row_version: int


class InstallationResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID
    code: str
    name: str
    status: str
    timezone: str
    operator_identity_ref: str | None
    metadata_json: dict[str, Any] | None
    row_version: int


def _to_response(row: CbamInstallationProfile) -> InstallationResponse:
    return InstallationResponse.model_validate(row)


def _get_row(
    db: Session, organization_id: uuid.UUID, profile_id: uuid.UUID
) -> CbamInstallationProfile:
    row = db.get(CbamInstallationProfile, profile_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM installation profile not found.')
    return row


def list_installations(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    search: str | None = None,
) -> Page[InstallationResponse]:
    require_cbam_view(db, user, organization_id)
    stmt = select(CbamInstallationProfile).where(
        CbamInstallationProfile.organization_id == organization_id
    )
    if status:
        stmt = stmt.where(CbamInstallationProfile.status == status)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(
            (CbamInstallationProfile.name.ilike(like)) | (CbamInstallationProfile.code.ilike(like))
        )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamInstallationProfile.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_installation(
    db: Session, user: User, organization_id: uuid.UUID, profile_id: uuid.UUID
) -> InstallationResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(_get_row(db, organization_id, profile_id))


def create_installation(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: InstallationCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> InstallationResponse:
    require_cbam_configure(db, user, organization_id)
    facility = require_facility_in_organization(db, organization_id, payload.facility_id)
    code = payload.code.strip()
    name = payload.name.strip()
    if not code or not name:
        raise ValidationAppError('Code and name are required.')
    exists = db.execute(
        select(CbamInstallationProfile.id).where(
            CbamInstallationProfile.organization_id == organization_id,
            CbamInstallationProfile.code == code,
        )
    ).scalar_one_or_none()
    if exists:
        raise ConflictError('A CBAM installation profile with this code already exists.')
    row = CbamInstallationProfile(
        organization_id=organization_id,
        facility_id=facility.id,
        code=code,
        name=name,
        status='draft',
        timezone=(payload.timezone or facility.timezone or 'UTC').strip(),
        operator_identity_ref=payload.operator_identity_ref,
        metadata_json=payload.metadata_json,
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action='cbam.installation.created',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_installation_profile',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'code': row.code, 'facilityId': str(row.facility_id), 'status': row.status},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def update_installation(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    profile_id: uuid.UUID,
    payload: InstallationUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> InstallationResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, profile_id)
    if row.status == 'archived':
        raise BusinessRuleError('Archived installation profiles cannot be updated.')
    check_row_version(row.row_version, payload.row_version, entity='CBAM installation profile')
    data = payload.model_dump(exclude_unset=True, exclude={'row_version'})
    if 'name' in data and data['name'] is not None:
        name = data['name'].strip()
        if not name:
            raise ValidationAppError('Name cannot be empty.')
        row.name = name
    if 'timezone' in data and data['timezone'] is not None:
        row.timezone = data['timezone'].strip() or row.timezone
    if 'operator_identity_ref' in data:
        row.operator_identity_ref = data['operator_identity_ref']
    if 'metadata_json' in data:
        row.metadata_json = data['metadata_json']
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.installation.updated',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_installation_profile',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'fields': list(data.keys()), 'rowVersion': row.row_version},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def activate_installation(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    profile_id: uuid.UUID,
    payload: InstallationVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> InstallationResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, profile_id)
    check_row_version(row.row_version, payload.row_version, entity='CBAM installation profile')
    if row.status != 'draft':
        raise BusinessRuleError('Only draft installation profiles can be activated.')
    other_active = db.execute(
        select(CbamInstallationProfile.id).where(
            CbamInstallationProfile.organization_id == organization_id,
            CbamInstallationProfile.facility_id == row.facility_id,
            CbamInstallationProfile.status == 'active',
            CbamInstallationProfile.id != row.id,
        )
    ).scalar_one_or_none()
    if other_active is not None:
        raise ConflictError(
            'Pilot constraint: at most one active CBAM installation profile per facility '
            '(temporary until D-041 is resolved). Archive or keep the other profile inactive.',
            details=[{'code': 'PILOT_INSTALLATION_CARDINALITY', 'decision': 'D-041'}],
        )
    previous = row.status
    row.status = 'active'
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.installation.activated',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_installation_profile',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'from': previous, 'to': row.status},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def archive_installation(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    profile_id: uuid.UUID,
    payload: InstallationVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> InstallationResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, profile_id)
    check_row_version(row.row_version, payload.row_version, entity='CBAM installation profile')
    if row.status == 'archived':
        raise BusinessRuleError('Installation profile is already archived.')
    previous = row.status
    row.status = 'archived'
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.installation.archived',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_installation_profile',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'from': previous, 'to': row.status},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def count_usable_installations(db: Session, organization_id: uuid.UUID) -> int:
    return int(
        db.execute(
            select(func.count()).where(
                CbamInstallationProfile.organization_id == organization_id,
                CbamInstallationProfile.status.in_(USABLE_INSTALLATION_STATUSES),
            )
        ).scalar_one()
    )
