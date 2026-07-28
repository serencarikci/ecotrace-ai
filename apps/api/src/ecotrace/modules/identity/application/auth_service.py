from __future__ import annotations
import uuid
from datetime import UTC, datetime, timedelta
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from ecotrace.core.constants import TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH
from ecotrace.core.exceptions import AuthenticationError, BusinessRuleError
from ecotrace.core.logging import get_logger
from ecotrace.core.security import create_access_token, create_refresh_token_jwt, decode_token, hash_password, hash_token, normalize_email, require_token_type, verify_password
from ecotrace.modules.identity.infrastructure.models import RefreshToken, User
from ecotrace.modules.identity.presentation.schemas import MeResponse, OrganizationMembershipSummary, TokenResponse, UserSummary
from ecotrace.modules.organizations.infrastructure.models import OrganizationMembership
from ecotrace.shared.application.audit import write_audit_log
logger = get_logger(__name__)
_FAILED_LOGINS: dict[str, list[datetime]] = {}

def _lockout_active(email: str) -> bool:
    from ecotrace.core.config import get_settings
    settings = get_settings()
    window = timedelta(minutes=settings.login_lockout_minutes)
    key = normalize_email(email)
    now = datetime.now(UTC)
    attempts = [t for t in _FAILED_LOGINS.get(key, []) if now - t < window]
    _FAILED_LOGINS[key] = attempts
    return len(attempts) >= settings.login_max_failures

def _record_failed_login(email: str) -> None:
    key = normalize_email(email)
    _FAILED_LOGINS.setdefault(key, []).append(datetime.now(UTC))

def _clear_failed_logins(email: str) -> None:
    _FAILED_LOGINS.pop(normalize_email(email), None)

def _user_role_codes(user: User) -> list[str]:
    return sorted({role.code for role in user.roles})

def _to_user_summary(user: User) -> UserSummary:
    return UserSummary(id=user.id, email=user.email, full_name=user.full_name, roles=_user_role_codes(user))

def get_user_by_normalized_email(db: Session, email: str) -> User | None:
    normalized = normalize_email(email)
    stmt = select(User).options(selectinload(User.roles)).where(User.normalized_email == normalized)
    return db.execute(stmt).scalar_one_or_none()

def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    stmt = select(User).options(selectinload(User.roles)).where(User.id == user_id)
    return db.execute(stmt).scalar_one_or_none()

def authenticate_user(db: Session, *, email: str, password: str, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> TokenResponse:
    if _lockout_active(email):
        write_audit_log(db, action='auth.login_lockout', request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'email': normalize_email(email)})
        db.commit()
        raise AuthenticationError('Too many failed login attempts. Try again later.', code='ACCOUNT_LOCKOUT')
    user = get_user_by_normalized_email(db, email)
    generic_error = AuthenticationError('Invalid email or password.', code='INVALID_CREDENTIALS')
    if user is None or not verify_password(password, user.hashed_password):
        _record_failed_login(email)
        write_audit_log(db, action='auth.login_failure', request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'email': normalize_email(email)})
        db.commit()
        raise generic_error
    if not user.is_active:
        _record_failed_login(email)
        write_audit_log(db, action='auth.login_failure', actor_user_id=user.id, request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'reason': 'inactive_user'})
        db.commit()
        raise AuthenticationError('Invalid email or password.', code='INVALID_CREDENTIALS')
    _clear_failed_logins(email)
    access_token, expires_in = create_access_token(subject=str(user.id), roles=_user_role_codes(user))
    refresh_token, expires_at, _jti = create_refresh_token_jwt(subject=str(user.id))
    token_record = RefreshToken(user_id=user.id, token_hash=hash_token(refresh_token), expires_at=expires_at, user_agent=user_agent, ip_address=ip_address)
    db.add(token_record)
    user.last_login_at = datetime.now(UTC)
    write_audit_log(db, action='auth.login_success', actor_user_id=user.id, entity_type='user', entity_id=str(user.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(user)
    logger.info('auth.login_success', user_id=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in, user=_to_user_summary(user))

def refresh_tokens(db: Session, *, refresh_token: str, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
        require_token_type(payload, TOKEN_TYPE_REFRESH)
        subject = payload.get('sub')
        if not subject:
            raise AuthenticationError('Invalid refresh token.', code='INVALID_TOKEN')
        user_id = uuid.UUID(str(subject))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise AuthenticationError('Invalid refresh token.', code='INVALID_TOKEN') from exc
    token_hash = hash_token(refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    stored = db.execute(stmt).scalar_one_or_none()
    if stored is None:
        raise AuthenticationError('Invalid refresh token.', code='INVALID_TOKEN')
    now = datetime.now(UTC)
    if stored.revoked_at is not None:
        _revoke_user_refresh_tokens(db, stored.user_id)
        write_audit_log(db, action='auth.refresh_reuse_detected', actor_user_id=stored.user_id, entity_type='refresh_token', entity_id=str(stored.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
        db.commit()
        logger.warning('auth.refresh_reuse_detected', user_id=str(stored.user_id))
        raise AuthenticationError('Refresh token reuse detected. Please sign in again.', code='TOKEN_REUSE_DETECTED')
    if stored.expires_at <= now:
        stored.revoked_at = now
        db.commit()
        raise AuthenticationError('Refresh token expired.', code='TOKEN_EXPIRED')
    if stored.user_id != user_id:
        raise AuthenticationError('Invalid refresh token.', code='INVALID_TOKEN')
    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError('Invalid refresh token.', code='INVALID_TOKEN')
    new_refresh, new_expires_at, _ = create_refresh_token_jwt(subject=str(user.id))
    new_record = RefreshToken(user_id=user.id, token_hash=hash_token(new_refresh), expires_at=new_expires_at, user_agent=user_agent, ip_address=ip_address)
    db.add(new_record)
    db.flush()
    stored.revoked_at = now
    stored.replaced_by_token_id = new_record.id
    access_token, expires_in = create_access_token(subject=str(user.id), roles=_user_role_codes(user))
    write_audit_log(db, action='auth.refresh_rotation', actor_user_id=user.id, entity_type='refresh_token', entity_id=str(new_record.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=new_refresh, expires_in=expires_in, user=_to_user_summary(user))

def logout(db: Session, *, refresh_token: str, actor_user_id: uuid.UUID | None=None, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> None:
    token_hash = hash_token(refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    stored = db.execute(stmt).scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        write_audit_log(db, action='auth.logout', actor_user_id=actor_user_id or stored.user_id, entity_type='refresh_token', entity_id=str(stored.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
        db.commit()

def logout_all(db: Session, *, user_id: uuid.UUID, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> None:
    _revoke_user_refresh_tokens(db, user_id)
    write_audit_log(db, action='auth.logout_all', actor_user_id=user_id, entity_type='user', entity_id=str(user_id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()

def change_password(db: Session, *, user: User, current_password: str, new_password: str, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise AuthenticationError('Current password is incorrect.', code='INVALID_CREDENTIALS')
    if current_password == new_password:
        raise BusinessRuleError('New password must be different from the current password.')
    user.hashed_password = hash_password(new_password)
    _revoke_user_refresh_tokens(db, user.id)
    write_audit_log(db, action='auth.password_change', actor_user_id=user.id, entity_type='user', entity_id=str(user.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()

def get_me(user: User) -> MeResponse:
    return MeResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active, is_verified=user.is_verified, roles=_user_role_codes(user), last_login_at=user.last_login_at)

def list_my_organizations(db: Session, user: User) -> list[OrganizationMembershipSummary]:
    stmt = select(OrganizationMembership).options(selectinload(OrganizationMembership.organization), selectinload(OrganizationMembership.role)).where(OrganizationMembership.user_id == user.id, OrganizationMembership.is_active.is_(True))
    memberships = list(db.execute(stmt).scalars().all())
    return [OrganizationMembershipSummary(organization_id=m.organization_id, organization_name=m.organization.name, organization_slug=m.organization.slug, role_code=m.role.code, is_active=m.is_active) for m in memberships]

def resolve_user_from_access_token(db: Session, token: str) -> User:
    try:
        payload = decode_token(token)
        require_token_type(payload, TOKEN_TYPE_ACCESS)
        subject = payload.get('sub')
        if not subject:
            raise AuthenticationError()
        user_id = uuid.UUID(str(subject))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise AuthenticationError('Invalid or expired access token.') from exc
    user = get_user_by_id(db, user_id)
    if user is None:
        raise AuthenticationError('Invalid or expired access token.')
    return user

def _revoke_user_refresh_tokens(db: Session, user_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    stmt = select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    for token in db.execute(stmt).scalars().all():
        token.revoked_at = now

def require_active_user(user: User) -> User:
    if not user.is_active:
        raise AuthenticationError('User account is inactive.', code='USER_INACTIVE')
    return user

def user_has_role(user: User, role_code: str) -> bool:
    return any((role.code == role_code for role in user.roles))

def require_roles(user: User, *role_codes: str) -> None:
    codes = set(_user_role_codes(user))
    if not codes.intersection(role_codes):
        from ecotrace.core.exceptions import AuthorizationError
        raise AuthorizationError()
