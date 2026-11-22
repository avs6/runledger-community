"""Security headers on every API response (review P-16).

The API serves JSON plus the interactive reference pages, so the policy is strict:
no framing, no MIME sniffing, no referrer leakage, HSTS when served over HTTPS, and a
restrictive CSP for JSON responses. The /reference and /docs pages load their UI from
a CDN, so they get a CSP that allows that origin only.
"""

from __future__ import annotations

from typing import Any

_BASE = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
_DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com; img-src 'self' data: https:; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
)
_DOCS_PREFIXES = ("/reference", "/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        csp = _DOCS_CSP if path.startswith(_DOCS_PREFIXES) else _API_CSP
        https = scope.get("scheme") == "https" or any(
            k == b"x-forwarded-proto" and v == b"https" for k, v in scope.get("headers", [])
        )

        async def send_with_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {k.lower() for k, _ in headers}
                extra = dict(_BASE)
                extra["Content-Security-Policy"] = csp
                if https:
                    extra["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                for name, value in extra.items():
                    if name.lower().encode() not in present:
                        headers.append((name.lower().encode(), value.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
