from __future__ import annotations
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from ecotrace.core.config import get_settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        if settings.is_production and settings.trusted_hosts:
            host = request.headers.get('host', '').split(':')[0].lower()
            allowed = {h.lower() for h in settings.trusted_hosts}
            if host and host not in allowed and ('*' not in allowed):
                return JSONResponse({'detail': 'Invalid host header.'}, status_code=400)
        response = await call_next(request)
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'no-referrer')
        response.headers.setdefault('Content-Security-Policy', "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if settings.enable_hsts and settings.is_production:
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response
