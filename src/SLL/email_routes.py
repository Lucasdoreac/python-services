"""Authenticated HTTP endpoint for transactional email delivery."""

import hmac
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import NamedTuple

import requests
from flask import Blueprint, jsonify, request

email_bp = Blueprint("email", __name__)
logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 15
SMTP_SSL_PORT = 465


class ProviderNotConfigured(Exception):
    """The provider has no credentials/sender configured in this environment."""


class ProviderFailed(Exception):
    """The provider is configured but did not accept the message."""


class SmtpSettings(NamedTuple):
    host: str
    port: int
    user: str
    password: str
    sender_email: str
    sender_name: str
    starttls: bool


def _smtp_settings():
    """Return the SMTP settings, or None when SMTP delivery is not configured."""
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    if not host or not user or not password:
        return None
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        logger.error("SMTP delivery is configured with a non-numeric SMTP_PORT")
        return None
    return SmtpSettings(
        host=host,
        port=port,
        user=user,
        password=password,
        sender_email=os.getenv("SMTP_SENDER_EMAIL", "").strip() or user,
        sender_name=os.getenv("SMTP_SENDER_NAME", "Reservas UDF"),
        starttls=os.getenv("SMTP_STARTTLS", "true").strip().casefold() != "false",
    )


def _send_brevo(recipients, subject, content, is_html):
    api_key = os.getenv("BREVO_API_KEY", "")
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "")
    sender_name = os.getenv("BREVO_SENDER_NAME", "Reservas UDF")
    if not api_key or not sender_email:
        raise ProviderNotConfigured()

    message = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": email.strip()} for email in recipients],
        "subject": subject,
        "htmlContent" if is_html else "textContent": content,
    }
    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=message,
            headers={"api-key": api_key, "accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = exc.response.status_code if exc.response is not None else None
        logger.error("Brevo transactional email request failed (status=%s)", status)
        raise ProviderFailed() from exc

    try:
        result = response.json() if response.content else {}
    except requests.JSONDecodeError:
        result = {}
    if not isinstance(result, dict):
        result = {}
    logger.info("Brevo accepted a transactional email (status=%s)", response.status_code)
    return {"status": "sent", "messageId": result.get("messageId")}


def _send_smtp(recipients, subject, content, is_html):
    settings = _smtp_settings()
    if settings is None:
        raise ProviderNotConfigured()

    addresses = [email.strip() for email in recipients]
    message = EmailMessage()
    try:
        message["From"] = formataddr((settings.sender_name, settings.sender_email))
        message["To"] = ", ".join(addresses)
        message["Subject"] = subject
        message.set_content(content, subtype="html" if is_html else "plain")
    except ValueError as exc:
        # Line breaks in a header value would allow header injection.
        logger.error("SMTP email rejected: invalid header value")
        raise ProviderFailed() from exc

    context = ssl.create_default_context()
    use_ssl = settings.port == SMTP_SSL_PORT
    try:
        if use_ssl:
            client = smtplib.SMTP_SSL(
                settings.host, settings.port, timeout=SMTP_TIMEOUT_SECONDS, context=context
            )
        else:
            client = smtplib.SMTP(settings.host, settings.port, timeout=SMTP_TIMEOUT_SECONDS)
        with client:
            if not use_ssl and settings.starttls:
                client.starttls(context=context)
            client.login(settings.user, settings.password)
            refused = client.send_message(message, to_addrs=addresses)
    except (smtplib.SMTPException, OSError) as exc:
        # Log only the error class: server replies can echo account details.
        logger.error("SMTP transactional email failed (%s)", type(exc).__name__)
        raise ProviderFailed() from exc

    if refused:
        logger.warning("SMTP server refused %d recipient(s)", len(refused))
    logger.info("SMTP accepted a transactional email")
    return {"status": "sent", "provider": "smtp"}


@email_bp.route("/send-email", methods=["POST"])
def send_email():
    """Deliver transactional email through Brevo and/or SMTP, or acknowledge a dry-run.

    ``EMAIL_PROVIDER=smtp`` sends only through SMTP. Otherwise Brevo is tried
    first and SMTP is used as the fallback when Brevo is not configured or fails.
    """
    expected_key = os.getenv("CLOUD_FUNCTION_API_KEY", "")
    supplied_key = request.headers.get("X-API-Key", "")
    if not expected_key or not hmac.compare_digest(supplied_key, expected_key):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    recipients = data.get("to")
    if isinstance(recipients, str):
        recipients = [recipients]
    if not isinstance(recipients, list) or not recipients or any(
        not isinstance(email, str) or not email.strip() for email in recipients
    ):
        return jsonify({"error": "Field 'to' must contain at least one email address"}), 400

    subject = data.get("subject")
    content = data.get("content")
    is_html = data.get("is_html", True)
    if not isinstance(subject, str) or not subject.strip():
        return jsonify({"error": "Field 'subject' is required"}), 400
    if not isinstance(content, str) or not content:
        return jsonify({"error": "Field 'content' is required"}), 400
    if not isinstance(is_html, bool):
        return jsonify({"error": "Field 'is_html' must be a boolean"}), 400

    if os.getenv("EMAIL_DRY_RUN", "true").strip().casefold() == "true":
        logger.info("Email accepted in dry-run; no message was sent")
        return jsonify({"status": "sent", "dry_run": True}), 200

    provider = os.getenv("EMAIL_PROVIDER", "").strip().casefold()
    senders = [_send_smtp] if provider == "smtp" else [_send_brevo, _send_smtp]

    any_provider_failed = False
    for send in senders:
        try:
            result = send(recipients, subject, content, is_html)
        except ProviderNotConfigured:
            continue
        except ProviderFailed:
            any_provider_failed = True
            continue
        return jsonify(result), 200

    if any_provider_failed:
        return jsonify({"error": "Email provider request failed"}), 502
    logger.error("Email delivery is enabled but no provider is fully configured")
    return jsonify({"error": "Email delivery is not configured"}), 503
