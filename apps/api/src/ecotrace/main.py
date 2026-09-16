from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ecotrace import __version__
from ecotrace.api.middleware.exception_handlers import register_exception_handlers
from ecotrace.api.middleware.request_context import RequestContextMiddleware
from ecotrace.api.middleware.security_headers import SecurityHeadersMiddleware
from ecotrace.api.v1 import api_router
from ecotrace.api.v1.health import health_router
from ecotrace.core.config import get_settings
from ecotrace.core.database import init_db
from ecotrace.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger(__name__)
    logger.info(
        "application.startup",
        app_name=settings.app_name,
        environment=settings.app_env,
        version=__version__,
    )
    init_db(settings)
    Path(settings.attachment_storage_path).mkdir(parents=True, exist_ok=True)
    Path(settings.knowledge_storage_path).mkdir(parents=True, exist_ok=True)
    Path(settings.report_storage_path).mkdir(parents=True, exist_ok=True)
    Path(settings.backup_storage_path).mkdir(parents=True, exist_ok=True)
    # Propagate LibreOffice / template paths into process env for adapters.
    import os

    if settings.libreoffice_soffice_path:
        os.environ["LIBREOFFICE_SOFFICE_PATH"] = settings.libreoffice_soffice_path
    os.environ["LIBREOFFICE_RECALC_TIMEOUT_SECONDS"] = str(
        settings.libreoffice_recalc_timeout_seconds
    )
    if settings.official_see_template_path:
        os.environ["OFFICIAL_SEE_TEMPLATE_PATH"] = settings.official_see_template_path
    try:
        yield
    finally:
        logger.info("application.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    docs_url = "/docs" if settings.enable_api_docs else None
    redoc_url = "/redoc" if settings.enable_api_docs else None
    openapi_url = "/openapi.json" if settings.enable_api_docs else None
    app = FastAPI(
        title=settings.app_name,
        description="EcoTrace AI API — carbon accounting, LCA/DPP, analytics, grounded AI Sustainability Copilot, automation, anomaly detection, and forecasting.",
        version=__version__,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    # Trusted hosts: include testclient default host for automated tests.
    hosts = list(settings.trusted_hosts)
    if "testserver" not in hosts and settings.app_env != "production":
        hosts.append("testserver")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts or ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
