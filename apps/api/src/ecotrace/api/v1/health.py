from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ecotrace.api.dependencies.auth import DbSession
from ecotrace.core.config import get_settings
from ecotrace.core.database import check_database_connectivity
from ecotrace.core.exceptions import EcoTraceError
from ecotrace.shared.domain.schemas import CamelModel

health_router = APIRouter(tags=["Health"])
meta_router = APIRouter(tags=["Metadata"])


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    database: str


class MetaResponse(CamelModel):
    name: str
    version: str
    environment: str
    api_version: str


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Verifies that the API process is running.",
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@health_router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness probe",
    description="Verifies database connectivity.",
)
def ready(db: DbSession) -> ReadyResponse:
    try:
        check_database_connectivity(db)
        return ReadyResponse(status="ready", database="ok")
    except Exception as exc:
        raise EcoTraceError(
            "Database is not ready.",
            code="SERVICE_UNAVAILABLE",
            status_code=503,
        ) from exc


@meta_router.get(
    "/meta",
    response_model=MetaResponse,
    summary="Application metadata",
)
def meta() -> MetaResponse:
    settings = get_settings()
    return MetaResponse(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        api_version="v1",
    )
