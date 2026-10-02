"""Calls to the Auth service that survive its cold start.

Render free services sleep after 15 minutes and take ~60 s to wake. Measured on
Staging: a request from outside Render to the sleeping service is held until it
wakes, but the same request from another Render service (this API) gets an
immediate HTML 502 with ``x-render-routing: no-deploy`` and does NOT wake it, so
retrying from here cannot help. A bare ``requests.get`` turned that 502 into a
403 "Token validation failed". Here every call has a timeout, transient failures
are retried within a short budget, and the outcome is explicit: ``OK``,
``DENIED`` (Auth answered 4xx in JSON) or ``UNAVAILABLE``. When Auth is asleep
the answer is immediate and carries ``wake_url`` so the browser, whose requests
do wake the service, can wake it and retry.
"""

import os
import time
from urllib.parse import urlsplit

import requests

OK = "ok"
DENIED = "denied"
UNAVAILABLE = "unavailable"

CONNECT_TIMEOUT = 3.05
RETRY_DELAY = 2.0
TRANSIENT_STATUS = frozenset({500, 502, 503, 504})


def _budget_seconds():
    try:
        return max(1.0, float(os.getenv("AUTH_UPSTREAM_BUDGET_SECONDS", "25")))
    except ValueError:
        return 25.0


def _is_platform_page(response):
    """True for a non-JSON answer: Render's own wake-up/error page, not Auth's.

    Auth always answers in JSON, so an HTML 4xx/5xx means the request never
    reached the service and must not be read as "token denied".
    """
    content_type = (getattr(response, "headers", None) or {}).get("content-type")
    return bool(content_type) and "json" not in content_type.lower()


def is_asleep(response):
    """True for Render's answer to a request for a spun-down service."""
    headers = getattr(response, "headers", None) or {}
    return headers.get("x-render-routing", "").lower() == "no-deploy"


def unavailable_payload(response):
    """JSON body for a 503: a clear error, plus ``wake_url`` when Auth sleeps."""
    payload = {"error": "Authentication service unavailable; retry in a few seconds",
               "retry_after": 10}
    base = os.getenv("URL_AUTH")
    if base and is_asleep(response):
        payload["wake_url"] = f"{base.rstrip('/')}/health"
    return payload


def _note(method, url, attempt, outcome, response=None):
    """Stdout line for transient failures: the host's log viewer shows it.

    The body is logged only for non-JSON answers (the platform's own pages).
    For Auth's JSON answers only the top-level key names are logged, never
    values, so no e-mail or token can reach the retained logs.
    """
    extra = ""
    if response is not None:
        headers = getattr(response, "headers", None) or {}
        interesting = {k: v for k, v in headers.items()
                       if k.lower() == "server" or k.lower().startswith("x-render")}
        extra = f" content-type={headers.get('content-type', '-')} headers={interesting}"
        if _is_platform_page(response):
            body = (getattr(response, "text", "") or "")[:120].replace("\n", " ")
            extra += f" body={body!r}"
        else:
            try:
                payload = response.json()
                keys = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
            except (ValueError, AttributeError):
                keys = "unparsed"
            extra += f" json_keys={keys}"
    print(f"auth_upstream: {method} host={urlsplit(url).netloc} attempt={attempt} transient={outcome}{extra}", flush=True)


def call_auth(method, url, *, params=None, json=None, retry_read_timeouts=True,
              sleep=None, clock=None):
    """Return ``(outcome, response)``; ``response`` is None when unavailable.

    ``retry_read_timeouts`` must be False for calls with side effects (the Auth
    service may have processed a request whose answer was lost).
    """
    sleep = sleep or time.sleep
    clock = clock or time.monotonic
    deadline = clock() + _budget_seconds()
    last = None
    attempt = 0
    while True:
        attempt += 1
        remaining = deadline - clock()
        if remaining <= 0:
            return UNAVAILABLE, last
        try:
            kwargs = {"params": params, "timeout": (CONNECT_TIMEOUT, min(15.0, remaining))}
            if json is not None:
                kwargs["json"] = json
            response = getattr(requests, method.lower())(url, **kwargs)
        except requests.exceptions.ConnectionError as error:
            _note(method, url, attempt, type(error).__name__)
            last = None
        except requests.exceptions.Timeout as error:
            _note(method, url, attempt, type(error).__name__)
            if not retry_read_timeouts:
                return UNAVAILABLE, None
            last = None
        else:
            status = getattr(response, "status_code", 200 if response else 403)
            if status < 400:
                return OK, response
            if status not in TRANSIENT_STATUS and not _is_platform_page(response):
                return DENIED, response
            _note(method, url, attempt, status, response)
            if is_asleep(response):
                return UNAVAILABLE, response
            last = response
        if deadline - clock() <= RETRY_DELAY:
            return UNAVAILABLE, last
        sleep(RETRY_DELAY)
