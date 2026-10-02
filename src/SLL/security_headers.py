"""Response headers every answer carries, and the switch for the API docs."""

import os
from urllib.parse import urlsplit

from flask import request

from SLL.insecure_dev import insecure_dev_allowed


def docs_enabled():
    """Swagger UI and the spec are off unless ENABLE_API_DOCS=true (or the development opt-out)."""
    return (os.getenv("ENABLE_API_DOCS", "").strip().lower() in ("1", "true", "yes", "on")
            or insecure_dev_allowed())


def apply_security_headers(response):
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Referrer-Policy", "no-referrer")
    if request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https":
        headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if response.mimetype == "application/json":
        headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    return response


def _origin(url):
    parts = urlsplit((url or "").strip())
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme in ("http", "https") and parts.netloc else None


def cors_origins():
    """Origins allowed to call the API from a browser.

    The origin of FRONTEND_URL plus the exact origins listed in
    CORS_ALLOWED_ORIGINS (comma separated). With neither, no origin is allowed:
    never "*". Only the development opt-out opens everything.
    """
    if insecure_dev_allowed():
        return "*"
    origins = []
    for candidate in [os.getenv("FRONTEND_URL")] + (os.getenv("CORS_ALLOWED_ORIGINS") or "").split(","):
        origin = _origin(candidate)
        if origin and origin not in origins:
            origins.append(origin)
    return origins
