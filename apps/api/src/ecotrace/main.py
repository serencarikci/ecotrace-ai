from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ecotrace import __version__
from ecotrace.api.middleware.exception_handlers import register_exception_handlers
from ecotrace.api.middleware.request_context import RequestContextMiddleware
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
    from pathlib import Path

    Path(settings.attachment_storage_path).mkdir(parents=True, exist_ok=True)
    try:
        yield
    finally:
        logger.info("application.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "EcoTrace AI API — identity, activity data, and deterministic "
            "carbon accounting / emission calculation engine."
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
