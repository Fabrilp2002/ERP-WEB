"""Middleware de security headers HTTP para producción cloud."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Agrega defensas estándar sin cambiar la lógica de negocio."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' https://*.supabase.co data:; "
            "connect-src 'self' https://*.onrender.com https://*.railway.app https://*.supabase.co; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'none';"
        )
        # MutableHeaders no tiene .pop() — usar del con guard
        if "server" in response.headers:
            del response.headers["server"]
        return response
