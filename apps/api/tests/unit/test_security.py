from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from ecotrace.core.config import Settings, reset_settings_cache
from ecotrace.core.constants import TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH
from ecotrace.core.security import (
    create_access_token,
    create_refresh_token_jwt,
    decode_token,
    hash_password,
    hash_token,
    normalize_email,
    require_token_type,
    verify_password,
)
from ecotrace.shared.domain.schemas import calculate_total_pages


def test_normalize_email() -> None:
    assert normalize_email("  Admin@EcoTrace.Dev ") == "admin@ecotrace.dev"


def test_password_hash_and_verify() -> None:
    hashed = hash_password("SecurePass!123")
    assert hashed != "SecurePass!123"
    assert verify_password("SecurePass!123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_generation_and_decode() -> None:
    token, expires_in = create_access_token(subject="user-1", roles=["system_admin"])
    assert expires_in > 0
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["type"] == TOKEN_TYPE_ACCESS
    assert payload["roles"] == ["system_admin"]
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload


def test_refresh_token_generation() -> None:
    token, expires_at, jti = create_refresh_token_jwt(subject="user-1")
    payload = decode_token(token)
    assert payload["type"] == TOKEN_TYPE_REFRESH
    assert payload["jti"] == jti
    assert expires_at > datetime.now(UTC)


def test_expired_token_rejection() -> None:
    settings = Settings(
        SECRET_KEY="test-secret-key-that-is-long-enough-32chars",
        INITIAL_ADMIN_PASSWORD="EcoTraceAdmin!2024",
        APP_ENV="test",
    )
    now = datetime.now(UTC)
    payload = {
        "sub": "user-1",
        "type": TOKEN_TYPE_ACCESS,
        "roles": [],
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
        "jti": "expired",
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token, settings=settings)


def test_require_token_type() -> None:
    with pytest.raises(jwt.InvalidTokenError):
        require_token_type({"type": TOKEN_TYPE_REFRESH}, TOKEN_TYPE_ACCESS)


def test_hash_token_deterministic() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abd")


def test_pagination_calculation() -> None:
    assert calculate_total_pages(0, 20) == 0
    assert calculate_total_pages(20, 20) == 1
    assert calculate_total_pages(21, 20) == 2
    assert calculate_total_pages(100, 0) == 0


def test_production_rejects_insecure_secret() -> None:
    reset_settings_cache()
    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY="change-me-to-a-long-random-secret-at-least-32-chars",
            INITIAL_ADMIN_PASSWORD="EcoTraceAdmin!2024",
            APP_ENV="production",
            APP_DEBUG="false",
        )


def test_cors_origins_parsing() -> None:
    settings = Settings(
        SECRET_KEY="test-secret-key-that-is-long-enough-32chars",
        INITIAL_ADMIN_PASSWORD="EcoTraceAdmin!2024",
        APP_ENV="test",
        CORS_ALLOWED_ORIGINS="http://a.com, http://b.com",
    )
    assert settings.cors_allowed_origins == ["http://a.com", "http://b.com"]
