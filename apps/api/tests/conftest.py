from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_DEBUG", "true")
os.environ.setdefault("APP_VERSION", "0.3.0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-32chars")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "EcoTraceAdmin!2024")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault("POSTGRES_DB", "ecotrace_test")
os.environ.setdefault("POSTGRES_USER", "ecotrace")
os.environ.setdefault("POSTGRES_PASSWORD", "ecotrace_dev_password")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://ecotrace:ecotrace_dev_password@localhost:5433/ecotrace_test",
)
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:4200")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("ATTACHMENT_STORAGE_PATH", "/tmp/ecotrace-test-attachments")
os.environ.setdefault("MAX_ATTACHMENT_SIZE_MB", "5")
os.environ.setdefault("MAX_CSV_IMPORT_ROWS", "5000")
os.environ.setdefault("ALLOWED_ATTACHMENT_TYPES", "pdf,csv,xlsx,png,jpeg,jpg")

import ecotrace.modules.activity_data.infrastructure.models
import ecotrace.modules.carbon_inventory.infrastructure.models
import ecotrace.modules.data_imports.infrastructure.models
import ecotrace.modules.emission_factors.infrastructure.models
import ecotrace.modules.facilities.infrastructure.models
import ecotrace.modules.identity.infrastructure.models
import ecotrace.modules.operational_assets.infrastructure.models
import ecotrace.modules.organizations.infrastructure.models
import ecotrace.modules.reference_data.infrastructure.models
import ecotrace.modules.reporting_periods.infrastructure.models  # noqa: F401
from ecotrace.core.config import reset_settings_cache
from ecotrace.core.database import get_db, init_db
from ecotrace.db.base import Base
from ecotrace.db.seed import run_seed
from ecotrace.main import create_app


def _admin_database_url() -> str:
    return "postgresql+psycopg://ecotrace:ecotrace_dev_password@localhost:5433/postgres"


def _ensure_test_database() -> None:
    admin_engine = create_engine(_admin_database_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'ecotrace_test'")
        ).scalar()
        if not exists:
            conn.execute(text("CREATE DATABASE ecotrace_test"))
    admin_engine.dispose()


def _truncate_all(engine: Engine) -> None:
    with engine.begin() as conn:
        tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        if tables:
            conn.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    reset_settings_cache()
    _ensure_test_database()
    db_url = os.environ["DATABASE_URL"]
    eng = create_engine(db_url, pool_pre_ping=True, future=True)
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autoflush=False, autocommit=False, future=True)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(engine: Engine) -> Generator[TestClient, None, None]:
    reset_settings_cache()
    init_db()
    _truncate_all(engine)

    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def _override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        seed_session = session_factory()
        try:
            run_seed(seed_session)
        finally:
            seed_session.close()
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(engine: Engine) -> Generator[Session, None, None]:
    _truncate_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = session_factory()
    run_seed(session)
    try:
        yield session
    finally:
        session.close()
