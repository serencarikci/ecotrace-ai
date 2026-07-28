from __future__ import annotations
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Response
from sqlalchemy import text
from ecotrace.api.dependencies.auth import CurrentUser, DbSession
from ecotrace.core.config import get_settings
from ecotrace.core.database import check_database_connectivity
from ecotrace.core.exceptions import AuthorizationError, EcoTraceError
from ecotrace.core.phase7_constants import ANOMALY_ENGINE_VERSION, FORECAST_ENGINE_VERSION, PHASE7_ENGINE_VERSION
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.job_execution.application import job_service
from ecotrace.shared.application.org_access import require_system_admin
from ecotrace.shared.domain.schemas import CamelModel
from ecotrace.shared.infrastructure.prometheus_metrics import render_prometheus
from ecotrace.version import __version__
system_router = APIRouter(prefix='/system', tags=['System Operations'])

class VersionResponse(CamelModel):
    application_version: str
    api_version: str
    calculation_engine_version: str
    forecasting_engine_version: str
    anomaly_engine_version: str
    rag_pipeline_version: str
    phase7_engine_version: str
    build_commit: str | None = None
    build_timestamp: str | None = None
    environment: str

def _require_sys(user: User) -> None:
    require_system_admin(user)

@system_router.get('/health')
def system_health(db: DbSession, user: CurrentUser) -> dict[str, Any]:
    _require_sys(user)
    settings = get_settings()
    checks = {'database': _db_status(db), 'storage': _storage_status(settings.attachment_storage_path), 'reportStorage': _storage_status(settings.report_storage_path), 'knowledgeStorage': _storage_status(settings.knowledge_storage_path), 'scheduler': {'status': 'configured', 'enabled': settings.scheduler_enabled}, 'ai': {'status': 'ok', 'llmProvider': settings.ai_llm_provider, 'embeddingProvider': settings.ai_embedding_provider}, 'vectorSearch': {'status': 'ok', 'backend': settings.ai_vector_backend}}
    overall = 'ok' if all((isinstance(v, dict) and v.get('status') in {'ok', 'configured'} for v in checks.values())) else 'degraded'
    return {'status': overall, 'version': __version__, 'checks': checks, 'recentFailedJobs': job_service.recent_failures(db, user)}

@system_router.get('/health/database')
def health_database(db: DbSession, user: CurrentUser) -> dict[str, Any]:
    _require_sys(user)
    return _db_status(db)

@system_router.get('/health/storage')
def health_storage(user: CurrentUser) -> dict[str, Any]:
    _require_sys(user)
    settings = get_settings()
    return {'attachments': _storage_status(settings.attachment_storage_path), 'reports': _storage_status(settings.report_storage_path), 'knowledge': _storage_status(settings.knowledge_storage_path), 'backups': _storage_status(settings.backup_storage_path)}

@system_router.get('/health/scheduler')
def health_scheduler(user: CurrentUser) -> dict[str, Any]:
    _require_sys(user)
    settings = get_settings()
    return {'status': 'ok' if settings.scheduler_enabled else 'disabled', 'enabled': settings.scheduler_enabled, 'pollSeconds': settings.scheduler_poll_seconds, 'misfireGraceSeconds': settings.scheduler_misfire_grace_seconds}

@system_router.get('/health/ai')
def health_ai(user: CurrentUser) -> dict[str, Any]:
    _require_sys(user)
    settings = get_settings()
    return {'status': 'ok', 'llmProvider': settings.ai_llm_provider, 'llmModel': settings.ai_llm_model, 'embeddingProvider': settings.ai_embedding_provider, 'apiKeyConfigured': bool(settings.ai_llm_api_key)}

@system_router.get('/health/vector-search')
def health_vector(db: DbSession, user: CurrentUser) -> dict[str, Any]:
    _require_sys(user)
    settings = get_settings()
    ext_ok = False
    try:
        row = db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar()
        ext_ok = row is not None
    except Exception:
        ext_ok = False
    return {'status': 'ok' if settings.ai_vector_backend else 'unknown', 'backend': settings.ai_vector_backend, 'pgvectorExtension': ext_ok}

@system_router.get('/version', response_model=VersionResponse)
def system_version(user: CurrentUser) -> VersionResponse:
    _require_sys(user)
    settings = get_settings()
    return VersionResponse(application_version=__version__, api_version='v1', calculation_engine_version='ecotrace-carbon-0.3.0', forecasting_engine_version=FORECAST_ENGINE_VERSION, anomaly_engine_version=ANOMALY_ENGINE_VERSION, rag_pipeline_version='ecotrace-rag-0.6.0', phase7_engine_version=PHASE7_ENGINE_VERSION, build_commit=settings.build_commit, build_timestamp=settings.build_timestamp, environment=settings.app_env)

@system_router.get('/metrics')
def prometheus_metrics(user: CurrentUser) -> Response:
    _require_sys(user)
    settings = get_settings()
    if not settings.enable_metrics:
        raise AuthorizationError('Metrics disabled.')
    body = render_prometheus()
    return Response(content=body, media_type='text/plain; version=0.0.4')

def _db_status(db: DbSession) -> dict[str, Any]:
    try:
        check_database_connectivity(db)
        return {'status': 'ok'}
    except Exception as exc:
        raise EcoTraceError('Database health check failed.', code='SERVICE_UNAVAILABLE', status_code=503) from exc

def _storage_status(path: str) -> dict[str, Any]:
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / '.healthcheck'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink(missing_ok=True)
        return {'status': 'ok', 'pathConfigured': True}
    except Exception as exc:
        return {'status': 'error', 'error': str(exc)[:200]}
