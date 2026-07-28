from __future__ import annotations
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from ecotrace.core.config import Settings, get_settings
from ecotrace.core.constants import TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH
_password_hash = PasswordHash((Argon2Hasher(),))

def normalize_email(email: str) -> str:
    return email.strip().lower()

def hash_password(password: str) -> str:
    return _password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _password_hash.verify(plain_password, hashed_password)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def _utcnow() -> datetime:
    return datetime.now(UTC)

def create_access_token(*, subject: str, roles: list[str], settings: Settings | None=None, extra_claims: dict[str, Any] | None=None) -> tuple[str, int]:
    cfg = settings or get_settings()
    now = _utcnow()
    expires_delta = timedelta(minutes=cfg.access_token_expire_minutes)
    expire = now + expires_delta
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {'sub': subject, 'type': TOKEN_TYPE_ACCESS, 'roles': roles, 'iat': int(now.timestamp()), 'exp': int(expire.timestamp()), 'jti': jti}
    if extra_claims:
        payload.update(extra_claims)
    encoded = jwt.encode(payload, cfg.secret_key, algorithm='HS256')
    token = encoded.decode('utf-8') if isinstance(encoded, bytes) else str(encoded)
    return (token, int(expires_delta.total_seconds()))

def create_refresh_token_jwt(*, subject: str, settings: Settings | None=None) -> tuple[str, datetime, str]:
    cfg = settings or get_settings()
    now = _utcnow()
    expire = now + timedelta(days=cfg.refresh_token_expire_days)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {'sub': subject, 'type': TOKEN_TYPE_REFRESH, 'iat': int(now.timestamp()), 'exp': int(expire.timestamp()), 'jti': jti}
    encoded = jwt.encode(payload, cfg.secret_key, algorithm='HS256')
    token = encoded.decode('utf-8') if isinstance(encoded, bytes) else str(encoded)
    return (token, expire, jti)

def decode_token(token: str, *, settings: Settings | None=None) -> dict[str, Any]:
    cfg = settings or get_settings()
    payload = jwt.decode(token, cfg.secret_key, algorithms=['HS256'])
    if not isinstance(payload, dict):
        raise jwt.InvalidTokenError('Invalid token payload')
    return payload

def require_token_type(payload: dict[str, Any], expected_type: str) -> None:
    token_type = payload.get('type')
    if token_type != expected_type:
        raise jwt.InvalidTokenError(f'Expected {expected_type} token')
