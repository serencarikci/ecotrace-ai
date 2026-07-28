from collections.abc import Generator
from typing import Annotated
from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from ecotrace.core.config import Settings, get_settings
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None

def create_db_engine(settings: Settings | None=None) -> Engine:
    cfg = settings or get_settings()
    return create_engine(cfg.sqlalchemy_database_uri, pool_pre_ping=True, pool_size=5, max_overflow=10, future=True)

def init_db(settings: Settings | None=None) -> None:
    global _engine, _SessionLocal
    _engine = create_db_engine(settings)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)

def get_engine() -> Engine:
    if _engine is None:
        init_db()
    assert _engine is not None
    return _engine

def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    return _SessionLocal

def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

def check_database_connectivity(db: Session) -> bool:
    db.execute(text('SELECT 1'))
    return True
DbSession = Annotated[Session, Depends(get_db)]
