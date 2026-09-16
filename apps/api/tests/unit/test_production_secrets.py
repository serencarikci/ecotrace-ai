"""Production fail-closed settings and seed guards (no secret values asserted in output)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ecotrace.core.config import Settings, reset_settings_cache
from ecotrace.core.constants import INSECURE_BOOTSTRAP_PASSWORD_DEFAULTS
from ecotrace.db import seed as seed_mod


def test_production_rejects_placeholder_secret_key() -> None:
    reset_settings_cache()
    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY="change-me-to-a-long-random-secret-at-least-32-chars",
            INITIAL_ADMIN_PASSWORD="ProdOnlyAdminPassphrase!NotInDefaults",
            APP_ENV="production",
            APP_DEBUG="false",
            CORS_ALLOWED_ORIGINS="https://app.example.com",
        )


def test_production_rejects_short_secret_key() -> None:
    reset_settings_cache()
    with pytest.raises(ValidationError, match="48 characters"):
        Settings(
            SECRET_KEY="x" * 40,
            INITIAL_ADMIN_PASSWORD="ProdOnlyAdminPassphrase!NotInDefaults",
            APP_ENV="production",
            APP_DEBUG="false",
            CORS_ALLOWED_ORIGINS="https://app.example.com",
        )


def test_production_rejects_default_admin_password() -> None:
    reset_settings_cache()
    assert "EcoTraceAdmin!2024" in INSECURE_BOOTSTRAP_PASSWORD_DEFAULTS
    with pytest.raises(ValidationError, match="INITIAL_ADMIN_PASSWORD"):
        Settings(
            SECRET_KEY="production-grade-secret-key-with-enough-entropy-0123456789ab",
            INITIAL_ADMIN_PASSWORD="EcoTraceAdmin!2024",
            APP_ENV="production",
            APP_DEBUG="false",
            CORS_ALLOWED_ORIGINS="https://app.example.com",
        )


def test_production_accepts_explicit_non_default_secrets() -> None:
    reset_settings_cache()
    settings = Settings(
        SECRET_KEY="production-grade-secret-key-with-enough-entropy-0123456789ab",
        INITIAL_ADMIN_PASSWORD="ProdOnlyAdminPassphrase!NotInDefaults",
        APP_ENV="production",
        APP_DEBUG="false",
        CORS_ALLOWED_ORIGINS="https://app.example.com",
    )
    assert settings.is_production
    assert settings.app_debug is False


def test_development_still_allows_example_bootstrap_defaults() -> None:
    reset_settings_cache()
    settings = Settings(
        SECRET_KEY="change-me-to-a-long-random-secret-at-least-32-chars",
        INITIAL_ADMIN_PASSWORD="EcoTraceAdmin!2024",
        APP_ENV="development",
    )
    assert settings.app_env == "development"


def test_run_seed_forbidden_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings_cache()
    settings = Settings(
        SECRET_KEY="production-grade-secret-key-with-enough-entropy-0123456789ab",
        INITIAL_ADMIN_PASSWORD="ProdOnlyAdminPassphrase!NotInDefaults",
        APP_ENV="production",
        APP_DEBUG="false",
        CORS_ALLOWED_ORIGINS="https://app.example.com",
    )
    monkeypatch.setattr(seed_mod, "get_settings", lambda: settings)
    with pytest.raises(RuntimeError, match="forbidden when APP_ENV=production"):
        seed_mod.run_seed(db=object())  # type: ignore[arg-type]
