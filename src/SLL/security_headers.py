"""Response headers every answer carries, and the switch for the API docs."""

import os

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
