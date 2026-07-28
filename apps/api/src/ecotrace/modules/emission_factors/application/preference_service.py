from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.emission_factors.infrastructure.models import (
    EmissionFactor,
    OrganizationEmissionFactorPreference,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_org_read, require_period_manage
from ecotrace.shared.domain.schemas import CamelModel


class PreferenceCreate(CamelModel):
    activity_type_id: uuid.UUID
    emission_factor_id: uuid.UUID
    priority: int = 1
    valid_from: date | None = None
    valid_to: date | None = None
    reason: str | None = None


class PreferenceUpdate(CamelModel):
    priority: int | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    reason: str | None = None
    is_active: bool | None = None


class PreferenceResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    activity_type_id: uuid.UUID
    emission_factor_id: uuid.UUID
    priority: int
    valid_from: date | None
    valid_to: date | None
    reason: str | None
    approved_by_user_id: uuid.UUID | None
    is_active: bool


def list_preferences(
    db: Session, user: User, organization_id: uuid.UUID, *, active_only: bool = True
) -> list[PreferenceResponse]:
    require_org_read(db, user, organization_id)
    stmt = select(OrganizationEmissionFactorPreference).where(
        OrganizationEmissionFactorPreference.organization_id == organization_id
    )
    if active_only:
        stmt = stmt.where(OrganizationEmissionFactorPreference.is_active.is_(True))
    rows = (
        db.execute(
            stmt.order_by(
                OrganizationEmissionFactorPreference.activity_type_id,
                OrganizationEmissionFactorPreference.priority,
            )
        )
        .scalars()
        .all()
    )
    return [PreferenceResponse.model_validate(r) for r in rows]


def create_preference(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: PreferenceCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PreferenceResponse:
    require_period_manage(db, user, organization_id)
    factor = db.get(EmissionFactor, payload.emission_factor_id)
    if factor is None or factor.status not in {"active", "superseded"}:
        raise ValidationAppError("Emission factor must exist and be active or superseded.")
    if factor.activity_type_id != payload.activity_type_id:
        raise BusinessRuleError("Preference activity type must match the factor activity type.")
    if payload.valid_from and payload.valid_to and payload.valid_to < payload.valid_from:
        raise ValidationAppError("validTo must not be earlier than validFrom.")
    row = OrganizationEmissionFactorPreference(
        organization_id=organization_id,
        activity_type_id=payload.activity_type_id,
        emission_factor_id=payload.emission_factor_id,
        priority=payload.priority,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        reason=payload.reason,
        approved_by_user_id=user.id,
        is_active=True,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="factor_preference.created",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="organization_emission_factor_preference",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return PreferenceResponse.model_validate(row)


def update_preference(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    preference_id: uuid.UUID,
    payload: PreferenceUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PreferenceResponse:
    require_period_manage(db, user, organization_id)
    row = db.get(OrganizationEmissionFactorPreference, preference_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("Preference not found.")
    data = payload.model_dump(exclude_unset=True)
    vf = data.get("valid_from", row.valid_from)
    vt = data.get("valid_to", row.valid_to)
    if vf and vt and vt < vf:
        raise ValidationAppError("validTo must not be earlier than validFrom.")
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(
        db,
        action="factor_preference.updated",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="organization_emission_factor_preference",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(row)
    return PreferenceResponse.model_validate(row)


def delete_preference(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    preference_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PreferenceResponse:
    require_period_manage(db, user, organization_id)
    row = db.get(OrganizationEmissionFactorPreference, preference_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("Preference not found.")
    row.is_active = False
    write_audit_log(
        db,
        action="factor_preference.removed",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="organization_emission_factor_preference",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return PreferenceResponse.model_validate(row)
