import hashlib
import logging
import logging.config
import os
import re
import sys
from enum import Enum
from datetime import datetime

from flask import has_request_context, request

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
    """O log vai para stdout (o que o host e o `docker logs` guardam) e continua no arquivo.

    O arquivo (py_log.log, ou LOG_FILE) era o único destino e some a cada deploy; mantê-lo
    preserva quem o lê. Se ele não puder ser aberto (diretório somente leitura), só o stdout fica.
    """
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(logging.FileHandler(os.getenv("LOG_FILE") or "py_log.log", mode="a"))
    except OSError:
        pass
    return handlers


logging.basicConfig(level=logging.INFO, handlers=_handlers(),
                    format="%(asctime)s - %(levelname)s - %(message)s")


class Logmessage(Enum):
    API_KEY_VALIDATED = "API key validated; key: {api_key}; IP: {ip_address};"
    TOKEN_VALIDATED = "Token validated; email: {email}; token: {token}; IP: {ip_address};"
    TOKEN_FAILURE = "Token validation failed; email: {email}; token: {token}; IP: {ip_address};"
    MISSING_CREDENTIALS = "Invalid or missing credentials"
    MISSING_API_KEY = "Invalid or missing API key:IP {ip_address};"
    MISSING_EMAIL = "Email missing; email: token: {token}; IP: {ip_address};"
    MISSING_TOKEN = "Token missing; email: {email}; IP: {ip_address};"
    INVALID_EMAIL_DOMAIN = "Invalid email domain; email: {email}; IP: {ip_address};"
    FAILED_SEND_EMAIL = "Email sender service unavailable: failed to send email; IP: {ip_address}; Email: {email};"
    SENDING_EMAIL = "Sending email; email: {email}; event: {event};"
    EVENT_APPROVED_REJECTED_BY = "Event {event_id} {action} by {who}; token: {token};"
    EVENT_REQUESTED_CHANGES_BY = "Event {event_id} requested changes by {who}; token: {token};"
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
    EVENT_APPROVAL_START_FAILED = "Event {event_id} approval start failed: {error}; rollback: {rollback}; IP: {ip_address};"
    EVENTS_LIST_FAILED = "Events listing failed: {error}; IP: {ip_address};"
    CHANGE_REQUEST_NOTICE_FAILED = "Change request notice for event {event_id} failed: {error};"
    NOTIFY_RESERVATION_FAILED = "Reservation notice for event {event_id} failed: {error}; IP: {ip_address};"



class LogType(Enum):
    INFO = logging.INFO
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    DEBUG = logging.DEBUG
    CRITICAL = logging.CRITICAL


def mask_token(token) -> str:
    """Impressão curta de um token: correlaciona linhas de log sem permitir reutilizá-lo.

    Tokens de login e de aprovação dão acesso, então nunca chegam ao log.
    """
    if not token:
        return "-"
    return "sha256:" + hashlib.sha256(str(token).encode()).hexdigest()[:8]


_SECRET = re.compile(
    r"""(['"]?(?:token|hash|api[_-]?key|x-api-key|authorization|password|secret)['"]?\s*[:=]\s*['"]?)(?!sha256:)([^'"\s,;&})]+)""",
    re.IGNORECASE,
)


def scrub_secrets(text: str) -> str:
    """Troca o valor de qualquer rótulo token/hash/chave/senha por uma impressão curta."""
    return _SECRET.sub(lambda match: match.group(1) + mask_token(match.group(2)), text)


class AppLogger:

    @staticmethod
    def log(message: Logmessage, log_type: LogType, **kwargs):
        for secret in ("token", "api_key"):
            if secret in kwargs:
                kwargs[secret] = mask_token(kwargs[secret])
        if "ip_address" not in kwargs and has_request_context():
            kwargs["ip_address"] = request.remote_addr
        try:
            current_date = datetime.timestamp(datetime.now())
            timestamp = datetime.timestamp(datetime.now())
            # Uma mensagem em texto simples (já montada por quem chama) é registrada como está.
            text = message.value.format(**kwargs) if isinstance(message, Logmessage) else str(message)
            formatted_message = scrub_secrets(f'{current_date} - {timestamp} - {text}')
        except KeyError as e:
            # {e} é só o nome do campo que faltou (definido pelo nosso código), não dado do usuário.
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
