"""Signed, expiring links for the event PDF.

Reviewers open the PDF from an e-mail without logging in, so the link itself
carries the proof: an expiry and an HMAC-SHA256 over the event id and that
expiry, keyed with LINK_SIGNING_KEY when set, otherwise with a key derived from
INTERNAL_API_KEY (HMAC-SHA256 over a fixed label, so the Catalog key itself is
never used as a signing key). Changing the key invalidates every issued link. A link works for one event only, stops
working at the expiry and cannot be forged without the key.
"""

import hashlib
import hmac
import os
import time


def _key():
    key = (os.getenv("LINK_SIGNING_KEY") or "").strip()
    if key:
        return key.encode("utf-8")
    internal = (os.getenv("INTERNAL_API_KEY") or "").strip()
    if not internal:
        raise RuntimeError("neither LINK_SIGNING_KEY nor INTERNAL_API_KEY is set")
    return hmac.new(internal.encode("utf-8"), b"pdf-link-v1", hashlib.sha256).digest()


def ttl_seconds():
    try:
        days = max(1, int(os.getenv("PDF_LINK_TTL_DAYS", "30")))
    except ValueError:
        days = 30
    return days * 86400


def _signature(event_id, expires_at):
    message = f"pdf:{event_id}:{int(expires_at)}".encode("utf-8")
    return hmac.new(_key(), message, hashlib.sha256).hexdigest()


def signed_query(event_id, now=None):
    """Query string (``exp=…&sig=…``) that authorizes the PDF of ``event_id``."""
    expires_at = int((time.time() if now is None else now) + ttl_seconds())
    return f"exp={expires_at}&sig={_signature(event_id, expires_at)}"


def verify(event_id, expires_at, signature, now=None):
    """True for a correct, unexpired signature for this event; never raises on bad input."""
    try:
        expires_at = int(expires_at)
        expected = _signature(event_id, expires_at)
    except (TypeError, ValueError, RuntimeError):
        return False
    if expires_at <= (time.time() if now is None else now):
        return False
    return hmac.compare_digest(expected, str(signature or ""))
