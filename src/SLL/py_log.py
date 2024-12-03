import logging
import logging.config
from enum import Enum
from datetime import date,datetime

#types of errors=

#Invalid or missing credentials
#Invalid or missing API key
#Token or email missing
#Token validation failed
#Invalid email domain
#Email sender service unavailable: failed to send email
#Missing data
#Events not found
#Reservation not found
#Building not found
#Rooms not found

logging.basicConfig(level=logging.INFO, filename="py_log.log", filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s")

class Logmessage(Enum):
    TOKEN_FAILURE = "Token validation failed; email: {email}; token: {token}; IP: {ip_address};"
    MISSING_CREDENTIALS = "Invalid or missing credentials"
    MISSING_API_KEY = "Invalid or missing API key:IP {ip_address}; "
    MISSING_EMAIL = "Email missing; email: token: {token}; IP: {ip_address};"
    MISSING_TOKEN = "Token missing; email: {email}; IP: {ip_address};"
    INVALID_EMAIL_DOMAIN = "Invalid email domain; email: {email}; IP: {ip_address};"
    FAILED_SEND_EMAIL = "Email sender service unavailable: failed to send email;IP: {ip_address} ;"
    MISSING_DATA = "Missing data;IP: {ip_address} ; "
    EVENTS_NOT_FOUND = "Events not found;IP: {ip_address} ;"
    RESERVATION_NOT_FOUND = "Reservation not found;IP: {ip_address} ;"
    BUILDING_NOT_FOUND = "Building not found;IP: {ip_address} ;"
    ROOMS_NOT_FOUND = "Rooms not found;IP: {ip_address} ;"


class LogType(Enum):
    INFO = logging.INFO
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    DEBUG = logging.DEBUG
    CRITICAL =logging.CRITICAL


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




