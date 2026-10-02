
import pytest
import logging
from src.SLL.py_log import AppLogger,LogType,Logmessage,mask_email
from src import get_config


#TEST TOKEN FAILURE
def teste_log_token_successfully(caplog):
    token = "12345"
    email = "udf@udf.com"
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.TOKEN_FAILURE,
            LogType.INFO,
            token=token,
            email=email,
            ip_address=remote_addr,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = f"Token validation failed; email: {mask_email('udf@udf.com')}; token: sha256:5994471a; IP: localhost;"
    assert  expected_message in log_record.message


def teste_log_token_failure(caplog):
    token = '12345'
    email = "udf@udf.com"
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.TOKEN_FAILURE,
            LogType.INFO,
            email=email,
            ip_address=remote_addr,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    expected_message = "Erro na formatação da mensagem de log:'token'"
    assert  expected_message in log_record.message


#TEST MISSING API KEY
def teste_missing_api_key_successfully(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.MISSING_API_KEY,
            LogType.INFO,
            ip_address=remote_addr,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = "Invalid or missing API key:IP localhost;"
    assert expected_message in log_record.message


def teste_missing_api_key_failure(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.MISSING_API_KEY,
            LogType.INFO,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    expected_message = "Erro na formatação da mensagem de log:'ip_address'"
    assert expected_message in log_record.message


#MISSING EMAIL
def teste_missing_email_successfully(caplog):
    token = "1234"
    email = None
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.MISSING_EMAIL if not email else Logmessage.MISSING_TOKEN,
            LogType.INFO,
            token=token,
            email = email,
            ip_address=remote_addr,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = "Email missing; email: token: sha256:03ac6742; IP: localhost"
    assert expected_message in log_record.message


#INVALID EMAIL DOMAIN
def teste_invalid_email_domain_successfully(caplog):
    email = "udf@udf.com"
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.INVALID_EMAIL_DOMAIN,
            LogType.INFO,
            email=email,
            ip_address=remote_addr,
         )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = f"Invalid email domain; email: {mask_email('udf@udf.com')}; IP: localhost;"
    assert expected_message in log_record.message


def teste_invalid_email_domain_failure(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.INVALID_EMAIL_DOMAIN,
            LogType.INFO,
            ip_address=remote_addr,
         )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    expected_message = "Erro na formatação da mensagem de log:'email"
    assert expected_message in log_record.message


#FAILED SEND EMAIL
def teste_failed_send_email_successfully(caplog):
    remote_addr = 'localhost'
    email = 'coord@example.edu'
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.FAILED_SEND_EMAIL,
            LogType.INFO,
            ip_address=remote_addr,
            email=email,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = f"Email sender service unavailable: failed to send email; IP: localhost; Email: {mask_email('coord@example.edu')};"
    assert expected_message in log_record.message


def teste_failed_send_email_failure(caplog):
    remote_addr = 'localhost'
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.FAILED_SEND_EMAIL,
            LogType.INFO,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    expected_message = "Erro na formatação da mensagem de log:'ip_address'"
    assert expected_message in log_record.message


#MISSING DATA
def teste_missing_data_successfully(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.MISSING_DATA,
            LogType.INFO,
            ip_address=remote_addr,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = "Missing data;IP: localhost ;"
    assert expected_message in log_record.message


def teste_missing_data_failure(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.MISSING_DATA,
            LogType.INFO,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    expected_message = "Erro na formatação da mensagem de log:'ip_address'"
    assert expected_message in log_record.message


#EVENTS NOT FOUND
def teste_events_not_found_successfully(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.EVENTS_NOT_FOUND,
            LogType.INFO,
            ip_address=remote_addr,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = "Events not found; IP: localhost ;"
    assert expected_message in log_record.message


def teste_events_not_found_failure(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.EVENTS_NOT_FOUND,
            LogType.INFO,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    expected_message = "Erro na formatação da mensagem de log:'ip_address'"
    assert expected_message in log_record.message


#RESERVETION NOT FOUND
def teste_reservation_not_found_successfully(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.RESERVATION_NOT_FOUND,
            LogType.INFO,
            ip_address=remote_addr,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = "Reservation not found; IP: localhost;"
    assert expected_message in log_record.message


def teste_reservation_not_found_failure(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.RESERVATION_NOT_FOUND,
            LogType.INFO,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    expected_message = "Erro na formatação da mensagem de log:'ip_address'"
    assert expected_message in log_record.message


#CAMPUS NOT FOUND
def teste_campus_not_found_successfully(caplog):
    remote_addr= "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.CAMPUS_NOT_FOUND,
            LogType.INFO,
            ip_address=remote_addr,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = "Campus not found; IP: localhost;"
    assert expected_message in log_record.message


def teste_campus_not_found_failure(caplog):
    remote_addr= "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.CAMPUS_NOT_FOUND,
            LogType.INFO,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    expected_message = "Erro na formatação da mensagem de log:'ip_address'"
    assert expected_message in log_record.message


#ROOMS NOT FOUND
def teste_rooms_not_found_successfully(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.ROOMS_NOT_FOUND,
            LogType.INFO,
            ip_address=remote_addr,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "INFO"
    expected_message = "Rooms not found; IP: localhost;"
    assert expected_message in log_record.message


def teste_rooms_not_found(caplog):
    remote_addr = "localhost"
    with caplog.at_level(logging.INFO):
        AppLogger.log(
            Logmessage.ROOMS_NOT_FOUND,
            LogType.INFO,
        )

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "ERROR"
    expected_message = "Erro na formatação da mensagem de log:'ip_address'"
    assert expected_message in log_record.message


def test_tokens_never_reach_the_log_in_clear(caplog):
    from SLL.py_log import mask_email, mask_token

    secret = "super-secret-token-value"
    with caplog.at_level("INFO"):
        AppLogger.log(Logmessage.SENDING_EMAIL, LogType.INFO, email="a@udf.edu.br", event="e1", token=secret)
        AppLogger.log(Logmessage.EVENT_APPROVED_REJECTED_BY, LogType.INFO, event_id="e1", action="approved",
                      who="coord", token=secret)
    assert secret not in caplog.text
    assert mask_token(secret) in caplog.text
    assert mask_token(None) == "-" and mask_token("") == "-"
