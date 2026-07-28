from __future__ import annotations

import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ecotrace.core.constants import REQUEST_ID_HEADER
from ecotrace.core.logging import bind_request_context, clear_request_context, get_logger
from ecotrace.shared.infrastructure.metrics import metrics

logger = get_logger(__name__)

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9\-_.]{8,128}$")


def _resolve_request_id(request: Request) -> str:
    incoming = request.headers.get(REQUEST_ID_HEADER)
    if incoming and _SAFE_REQUEST_ID.match(incoming):
        return incoming
    return str(uuid.uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        clear_request_context()
        request_id = _resolve_request_id(request)
        request.state.request_id = request_id
        request.state.user_id = None
        request.state.organization_id = None

        client_ip = None
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host

        user_agent = request.headers.get("User-Agent")
        bind_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request.failed",
                status_code=500,
                duration_ms=round(duration_ms, 2),
                user_id=getattr(request.state, "user_id", None),
                organization_id=getattr(request.state, "organization_id", None),
            )
            raise
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            response.headers[REQUEST_ID_HEADER] = request_id

            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault(
                "Permissions-Policy",
                "geolocation=(), microphone=(), camera=()",
            )

            logger.info(
                "request.completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                user_id=getattr(request.state, "user_id", None),
                organization_id=getattr(request.state, "organization_id", None),
            )
            metrics.timing(
                "http.request.duration_ms",
                duration_ms,
                tags={"method": request.method, "path": request.url.path},
            )
            return response
        finally:
            clear_request_context()
