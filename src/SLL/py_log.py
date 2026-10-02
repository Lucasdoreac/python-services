import hashlib
import hmac
import re
import sys
import logging
import os
import logging.config
from enum import Enum
from datetime import datetime

# types of errors=
# Invalid or missing credentials
# Invalid or missing API key
# Token or email missing
# Token validation failed
# Invalid email domain
# Email sender service unavailable: failed to send email
# Missing data
# Events not found
# Reservation not found
# Rooms not found
#Campus not found
#Courses not found
#Disciplines not found
#Periods not found
#Teachers not found
# ID not informed or null

# Deactivate werkzeug logs
logging.getLogger('werkzeug').setLevel(logging.ERROR)

def _handlers():
    """Log to stdout, which the platform keeps; a file only when LOG_FILE asks for one.

    The file used to be the only destination (py_log.log inside the container): nothing
    reached the platform's logs and it vanished with each deploy.
    """
    handlers = [logging.StreamHandler(sys.stdout)]
    if os.getenv("LOG_FILE"):
        handlers.append(logging.FileHandler(os.getenv("LOG_FILE"), mode="a"))
    return handlers


logging.basicConfig(level=logging.INFO, handlers=_handlers(),
                    format="%(asctime)s - %(levelname)s - %(message)s")


class Logmessage(Enum):
    REQUEST_AUTHENTICATED = "Authenticated request; email_hash: {email_hash}; method: {method}; path: {path}; status: {status}; IP: {ip_address};"
    API_KEY_VALIDATED = "API key validated; key: {api_key}; IP: {ip_address};"
    TOKEN_VALIDATED = "Token validated; email: {email}; token: {token}; IP: {ip_address};"
    TOKEN_FAILURE = "Token validation failed; email: {email}; token: {token}; IP: {ip_address};"
    MISSING_CREDENTIALS = "Invalid or missing credentials"
    MISSING_API_KEY = "Invalid or missing API key:IP {ip_address};"
    MISSING_EMAIL = "Email missing; email: token: {token}; IP: {ip_address};"
    MISSING_TOKEN = "Token missing; email: {email}; IP: {ip_address};"
    INVALID_EMAIL_DOMAIN = "Invalid email domain; email: {email}; IP: {ip_address};"
    FAILED_SEND_EMAIL = "Email sender service unavailable: failed to send email; IP: {ip_address}; Email: {email};"
    SENDING_EMAIL = "Sending email; email: {email}; event: {event}; token: {token};"
    EVENT_APPROVED_REJECTED_BY = "Event {event_id} {action} by {who}; token: {token};"
    MISSING_DATA = "Missing data;IP: {ip_address} ;"
    EVENTS_NOT_FOUND = "Events not found; IP: {ip_address} ;"
    RESERVATION_NOT_FOUND = "Reservation not found; IP: {ip_address};"
    UPDATING_EVENT_STATUS = "Updating event status; event_id: {event_id}; reservation_id: {reservation_id} status: {status};"
    ROOMS_NOT_FOUND = "Rooms not found; IP: {ip_address};"
    CAMPUS_NOT_FOUND = "Campus not found; IP: {ip_address};"
    COURSES_NOT_FOUND = "Courses not found; IP: {ip_address};"
    DISCIPLINES_NOT_FOUND = "Disciplines not found; IP: {ip_address};"
    PERIODS_NOT_FOUND = "Periods not found; IP: {ip_address};"
    TEACHERS_NOT_FOUND = "Teachers not found; IP: {ip_address};"
    TYPES_NOT_FOUND = "Types not found; IP: {ip_address};"
    AUTH_SERVICE_UNAVAILABLE = "Authentication service unavailable;"
    INTERNAL_APIS_CRASHED = "Internal APIs crashed; IP: {ip_address}; Payload: {payload}; Endpoint: {endpoint}; Error: {error};"
    ID_NOT_INFORMED = "ID not informed or null; IP: {ip_address}; Collection: {collection}; ID: {id};"
    EVENT_OWNER_MISMATCH = "Event {event_id} update denied to a non-organizer; IP: {ip_address};"
    EVENT_APPROVAL_START_FAILED = "Event {event_id} approval start failed: {error}; IP: {ip_address};"



class LogType(Enum):
    INFO = logging.INFO
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    DEBUG = logging.DEBUG
    CRITICAL = logging.CRITICAL


def mask_token(token) -> str:
    """Short fingerprint of a token: correlates log lines without allowing reuse.

    Login tokens and approval tokens grant access, so they never reach the log.
    """
    if not token:
        return "-"
    return "sha256:" + hashlib.sha256(str(token).encode()).hexdigest()[:8]


_process_key = os.urandom(32)


def _audit_key() -> bytes:
    """Key for e-mail fingerprints, derived from INTERNAL_API_KEY (same pattern as the PDF links).

    A bare SHA-256 of an institutional address can be reversed by guessing names, so the
    fingerprint is keyed. Without INTERNAL_API_KEY (the API refuses to start without it) a
    random per-process key is used: still correlatable within a run, never reversible.
    """
    internal = (os.getenv("INTERNAL_API_KEY") or "").strip()
    if not internal:
        return _process_key
    return hmac.new(internal.encode("utf-8"), b"audit-email-v1", hashlib.sha256).digest()


def mask_email(email) -> str:
    """Short keyed fingerprint of an e-mail: tells callers apart without storing who they are."""
    if not email:
        return "-"
    digest = hmac.new(_audit_key(), str(email).strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()
    return "hmac:" + digest[:12]


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


_SECRET = re.compile(
    r"""(['"]?(?:token|hash|api[_-]?key|x-api-key|authorization|password|secret)['"]?\s*[:=]\s*['"]?)(?!sha256:|hmac:)([^'"\s,;&})]+)""",
    re.IGNORECASE,
)


def scrub_emails(text: str) -> str:
    """Replace every e-mail address in a log line with its keyed fingerprint, and the value of
    anything labelled token/hash/key/password with a short fingerprint.

    The log goes to the platform's retention, so no address or credential is written in clear,
    wherever it comes from (a field, a request payload, an exception text).
    """
    text = _SECRET.sub(lambda match: match.group(1) + mask_token(match.group(2)), text)
    return _EMAIL.sub(lambda match: mask_email(match.group(0)), text)


class AppLogger:

    @staticmethod
    def log(message: Logmessage, log_type: LogType, **kwargs):
        for secret in ("token", "api_key"):
            if secret in kwargs:
                kwargs[secret] = mask_token(kwargs[secret])
        try:
            current_date = datetime.timestamp(datetime.now())
            timestamp = datetime.timestamp(datetime.now())
            formatted_message = scrub_emails(
                f'{current_date} - {timestamp} - {message.value.format(**kwargs)}')
        except KeyError as e:
            logging.error(f"Erro na formatação da mensagem de log:{e}")
            return

        if log_type.value == logging.INFO:
            logging.info(formatted_message)
        elif log_type.value == logging.ERROR:
            logging.error(formatted_message)
        elif log_type.value == logging.WARNING:
            logging.warning(formatted_message)
        elif log_type.value == logging.DEBUG:
            logging.debug(formatted_message)
        elif log_type.value == logging.CRITICAL:
            logging.critical(formatted_message)
