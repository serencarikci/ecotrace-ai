from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from ecotrace.api.dependencies.auth import DbSession
from ecotrace.core.config import get_settings
from ecotrace.core.database import check_database_connectivity
from ecotrace.core.exceptions import EcoTraceError
from ecotrace.modules.cbam.application.export_storage import sha256_file
from ecotrace.modules.cbam.application.official_see_export.constants import TEMPLATE_SHA256
from ecotrace.modules.cbam.application.official_see_export.recalc import soffice_available
from ecotrace.modules.cbam.application.official_see_export.service import (
    ensure_official_see_template,
)
from ecotrace.shared.domain.schemas import CamelModel

health_router = APIRouter(tags=["Health"])
meta_router = APIRouter(tags=["Metadata"])


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    database: str


class ComponentStatus(CamelModel):
    name: str
    status: str
    detail: str | None = None


class ComponentsReadyResponse(CamelModel):
    status: str
    components: list[ComponentStatus]


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
            "Database is not ready.", code="SERVICE_UNAVAILABLE", status_code=503
        ) from exc


def _component(name: str, ok: bool, detail: str | None = None) -> ComponentStatus:
    return ComponentStatus(name=name, status="ok" if ok else "unavailable", detail=detail)


@health_router.get(
    "/ready/components",
    response_model=ComponentsReadyResponse,
    summary="Component readiness",
    description=(
        "Factual checks for API, database, migrations, LibreOffice, "
        "Official SEE template, and artifact storage. Does not expose paths."
    ),
)
def ready_components(db: DbSession) -> ComponentsReadyResponse:
    settings = get_settings()
    components: list[ComponentStatus] = [_component("api_process", True)]

    db_ok = False
    try:
        check_database_connectivity(db)
        db_ok = True
        components.append(_component("database", True))
    except Exception:
        components.append(_component("database", False, "unreachable"))

    migration_ok = False
    if db_ok:
        try:
            row = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            migration_ok = row == "0032_cbam_prec_audit"
            components.append(
                _component(
                    "migrations",
                    migration_ok,
                    None if migration_ok else "not_at_expected_head",
                )
            )
        except Exception:
            components.append(_component("migrations", False, "unavailable"))
    else:
        components.append(_component("migrations", False, "database_unavailable"))

    lo_ok = soffice_available()
    components.append(
        _component("libreoffice", lo_ok, None if lo_ok else "recalculation_engine_unavailable")
    )

    template_ok = False
    try:
        path = ensure_official_see_template()
        template_ok = path.is_file() and sha256_file(path) == TEMPLATE_SHA256
        components.append(
            _component("official_see_template", template_ok, None if template_ok else "invalid")
        )
    except Exception:
        components.append(_component("official_see_template", False, "unavailable"))

    storage_ok = False
    try:
        root = Path(settings.report_storage_path)
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".healthcheck"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        storage_ok = True
        components.append(_component("artifact_storage", True))
    except Exception:
        components.append(_component("artifact_storage", False, "not_writable"))

    # Official SEE overall readiness for ops: LO + template + storage must all be ok.
    see_ops_ok = lo_ok and template_ok and storage_ok
    components.append(
        _component(
            "official_see_export",
            see_ops_ok,
            None if see_ops_ok else "dependencies_unavailable",
        )
    )

    overall = "ready" if all(c.status == "ok" for c in components) else "degraded"
    return ComponentsReadyResponse(status=overall, components=components)


@meta_router.get("/meta", response_model=MetaResponse, summary="Application metadata")
def meta() -> MetaResponse:
    settings = get_settings()
    return MetaResponse(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        api_version="v1",
    )
