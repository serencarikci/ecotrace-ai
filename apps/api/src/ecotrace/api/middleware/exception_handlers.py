from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import EcoTraceError
from ecotrace.core.logging import get_logger

logger = get_logger(__name__)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_body(
    *,
    code: str,
    message: str,
    request_id: str | None,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "requestId": request_id,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EcoTraceError)
    async def handle_app_error(request: Request, exc: EcoTraceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                code=exc.code,
                message=exc.message,
                request_id=_request_id(request),
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details: list[dict[str, Any]] = []
        for err in exc.errors():
            loc = err.get("loc", ())
            field_parts = [str(p) for p in loc if p not in {"body", "query", "path", "header"}]
            details.append(
                {
                    "field": ".".join(field_parts) if field_parts else None,
                    "message": err.get("msg", "Invalid value"),
                }
            )
        return JSONResponse(
            status_code=422,
            content=error_body(
                code="VALIDATION_ERROR",
                message="The request contains invalid data.",
                request_id=_request_id(request),
                details=details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            401: "AUTHENTICATION_ERROR",
            403: "AUTHORIZATION_ERROR",
            404: "NOT_FOUND",
            409: "CONFLICT",
            429: "RATE_LIMIT_EXCEEDED",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        message = str(exc.detail) if exc.detail else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                code=code,
                message=message,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        settings = get_settings()
        logger.exception("unhandled_exception", error=str(exc))
        message = "An unexpected error occurred."
        details: list[dict[str, Any]] = []
        if settings.app_debug and not settings.is_production:
            details = [{"message": str(exc)}]
        return JSONResponse(
            status_code=500,
            content=error_body(
                code="INTERNAL_ERROR",
                message=message,
                request_id=_request_id(request),
                details=details,
            ),
        )
