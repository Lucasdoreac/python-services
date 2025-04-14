import logging
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

logging.basicConfig(level=logging.INFO, filename="py_log.log", filemode="a",
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
    SENDING_EMAIL = "Sending email; email: {email}; event: {event}; token: {token};"
    EVENT_APPROVED_REJECTED_BY = "Event {event_id} {action} by {who}; token: {token};"
    MISSING_DATA = "Missing data;IP: {ip_address} ;"
    EVENTS_NOT_FOUND = "Events not found;IP: {ip_address} ;"
    RESERVATION_NOT_FOUND = "Reservation not found;IP: {ip_address};"
    ROOMS_NOT_FOUND = "Rooms not found;IP: {ip_address};"
    CAMPUS_NOT_FOUND = "Campus not found;IP: {ip_address};"
    COURSES_NOT_FOUND = "Courses not found;IP: {ip_address};"
    DISCIPLINES_NOT_FOUND = "Disciplines not found;IP: {ip_address};"
    PERIODS_NOT_FOUND = "Periods not found;IP: {ip_address};"
    TEACHERS_NOT_FOUND = "Teachers not found;IP: {ip_address};"
    TYPES_NOT_FOUND = "Types not found;IP: {ip_address};"
    AUTH_SERVICE_UNAVAILABLE = "Authentication service unavailable;"
    ID_NOT_INFORMED = "ID not informed or null;IP: {ip_address};"


class LogType(Enum):
    INFO = logging.INFO
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    DEBUG = logging.DEBUG
    CRITICAL = logging.CRITICAL


class AppLogger:

    @staticmethod
    def log(message: Logmessage, log_type: LogType, **kwargs):
        try:
            current_date = datetime.timestamp(datetime.now())
            timestamp = datetime.timestamp(datetime.now())
            formatted_message = f'{current_date} - {timestamp} - {message.value.format(**kwargs)}'
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
