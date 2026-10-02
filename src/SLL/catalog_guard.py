"""Answer 503 + wake_url, at once, when the Catalog service is asleep.

Same Render free-plan behaviour as Auth (see auth_upstream): requests from this
API never wake a sleeping service, they get an instant HTML 502 with
``x-render-routing: no-deploy``. Routes that read the Catalog call this as a
``before_request``; a single cheap probe tells asleep from awake and an awake
answer is remembered for a few minutes so normal traffic pays nothing.
"""

import os
import time
from urllib.parse import urlsplit

import requests
from flask import jsonify

from SLL.auth_upstream import is_asleep

AWAKE_TTL_SECONDS = 300
PROBE_TIMEOUT = (3.05, 5)
_awake_until = 0.0


def _origin(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else None


def reset():
    global _awake_until
    _awake_until = 0.0


def ensure_catalog_awake():
    """``before_request`` hook; returns a 503 response only when it sleeps."""
    global _awake_until
    origin = _origin(os.getenv("URL_restapi", ""))
    if not origin or time.monotonic() < _awake_until:
        return None
    try:
        response = requests.get(f"{origin}/health", timeout=PROBE_TIMEOUT)
    except requests.exceptions.RequestException:
        return None  # not provably asleep: let the route report its own error
    if is_asleep(response):
        print(f"catalog_guard: Catalog asleep host={urlsplit(origin).netloc}", flush=True)
        reply = jsonify({
            "error": "Catalog service is starting; retry in a few seconds",
            "retry_after": 10,
            "wake_url": f"{origin}/health",
        })
        reply.headers["Retry-After"] = "10"
        return reply, 503
    _awake_until = time.monotonic() + AWAKE_TTL_SECONDS
    return None
