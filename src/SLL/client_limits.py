"""Per-client request counters for the public login-link endpoint.

The Auth service only sees this API's address, so the per-address limit has to
live here, where the real client address is visible. Counters are in-process
fixed windows: each Gunicorn worker counts on its own (the effective limit is
the configured one times the workers) and a restart resets them.
"""

import ipaddress
import os
import threading
import time

_counters = {}
_lock = threading.Lock()


def window_seconds():
    try:
        return max(1, int(os.getenv("API_RATE_LIMIT_WINDOW_SECONDS", "900")))
    except ValueError:
        return 900


def client_ip(request):
    """Client address for per-client limits.

    Order: the platform's True-Client-IP header, then X-Forwarded-For, then the
    socket address. Measured on Render: X-Forwarded-For arrives as
    [values sent by the client, real client, two private hops], because each
    hop appends, so the entry TRUSTED_PROXY_HOPS places from the right
    (default 1) is a private proxy, not the client. True-Client-IP is set by the
    platform to the real client and a client-sent value is overwritten. The
    socket address is always the local proxy. Health checks carry no forwarding
    headers. TRUSTED_PROXY_HOPS only applies when the platform header is absent
    or invalid (other proxies, local runs).
    """
    platform = (request.headers.get("True-Client-IP") or "").strip()[:64]
    if platform:
        try:
            return str(ipaddress.ip_address(platform))
        except ValueError:
            pass
    try:
        hops = max(0, int(os.getenv("TRUSTED_PROXY_HOPS", "1")))
    except ValueError:
        hops = 1
    forwarded = [p.strip() for p in request.headers.get("X-Forwarded-For", "").split(",") if p.strip()]
    if hops and len(forwarded) >= hops:
        return forwarded[-hops]
    return request.remote_addr or "unknown"


def hit(key):
    """Record one event for ``key``; returns the count in the current window."""
    now = time.monotonic()
    with _lock:
        count, reset_at = _counters.get(key, (0, 0.0))
        if now >= reset_at:
            count, reset_at = 0, now + window_seconds()
        count += 1
        _counters[key] = (count, reset_at)
        if len(_counters) > 10000:
            for stale in [k for k, (_, r) in _counters.items() if now >= r]:
                _counters.pop(stale, None)
        return count


def reset():
    with _lock:
        _counters.clear()
