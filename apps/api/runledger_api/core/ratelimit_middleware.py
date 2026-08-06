"""
FastAPI middleware that injects X-RateLimit-* headers from request.state.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        info = getattr(request.state, "rate_limit_info", None)
        if info:
            if "limit_requests" in info:
                response.headers["X-RateLimit-Limit-Requests"] = str(info["limit_requests"])
            if "remaining_requests" in info:
                response.headers["X-RateLimit-Remaining-Requests"] = str(
                    max(0, info["remaining_requests"])
                )
            if "limit_tokens" in info:
                response.headers["X-RateLimit-Limit-Tokens"] = str(info["limit_tokens"])
            if "remaining_tokens" in info:
                response.headers["X-RateLimit-Remaining-Tokens"] = str(
                    max(0, info["remaining_tokens"])
                )
            if "reset" in info:
                response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response
