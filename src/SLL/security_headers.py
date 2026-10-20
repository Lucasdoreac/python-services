"""Response headers every answer carries, and the switch for the API docs."""

import os
from urllib.parse import urlsplit

from flask import request

from SLL.insecure_dev import insecure_dev_allowed


def docs_enabled():
    """Swagger UI and the spec are served as in main; ENABLE_API_DOCS=false (or 0/no/off) closes them."""
    return os.getenv("ENABLE_API_DOCS", "").strip().lower() not in ("0", "false", "no", "off")


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


def _configured(name):
    return bool((os.getenv(name) or "").strip())


def cors_open_by_default():
    """True when neither FRONTEND_URL nor CORS_ALLOWED_ORIGINS is set: the API answers any origin, as in main."""
    return not _configured("FRONTEND_URL") and not _configured("CORS_ALLOWED_ORIGINS")


def cors_origins():
    """Origins allowed to call the API from a browser.

    Without FRONTEND_URL and CORS_ALLOWED_ORIGINS, any origin is allowed ("*"),
    as the main branch did; app.py logs a warning in that case. When either is
    set, only the origin of FRONTEND_URL plus the exact origins listed in
    CORS_ALLOWED_ORIGINS (comma separated) are allowed, never "*".
    The development opt-out also opens everything.
    """
    if insecure_dev_allowed() or cors_open_by_default():
        return "*"
    origins = []
    for candidate in [os.getenv("FRONTEND_URL")] + (os.getenv("CORS_ALLOWED_ORIGINS") or "").split(","):
        origin = _origin(candidate)
        if origin and origin not in origins:
            origins.append(origin)
    return origins
