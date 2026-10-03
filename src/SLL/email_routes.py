"""Authenticated HTTP endpoint for transactional email delivery."""

import hmac
import logging
import os

import requests
from flask import Blueprint, jsonify, request

from SLL.py_log import mask_email

email_bp = Blueprint("email", __name__)
logger = logging.getLogger(__name__)


def _allowed_recipients():
    """Addresses from EMAIL_RECIPIENT_ALLOWLIST (exact, case-insensitive), or None when it is unset or empty."""
    allowed = {item.strip().casefold() for item in os.getenv("EMAIL_RECIPIENT_ALLOWLIST", "").split(",")}
    allowed.discard("")
    return allowed or None


@email_bp.route("/send-email", methods=["POST"])
def send_email():
    """Deliver transactional email through Brevo, or acknowledge a dry-run."""
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

    # Test environments set EMAIL_RECIPIENT_ALLOWLIST so real people are never mailed: the filter sits here,
    # before the dry-run and provider branches, so it covers every delivery path. Production leaves it unset.
    allowed = _allowed_recipients()
    if allowed is not None:
        kept = [email for email in recipients if email.strip().casefold() in allowed]
        for email in recipients:
            if email.strip().casefold() not in allowed:
                logger.info("Recipient %s removed: not in EMAIL_RECIPIENT_ALLOWLIST", mask_email(email))
        recipients = kept
        if not recipients:
            return jsonify({
                "status": "skipped",
                "message": "Nenhum destinatário permitido pela lista de destinatários; nada foi enviado",
            }), 202

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

    api_key = os.getenv("BREVO_API_KEY", "")
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "")
    sender_name = os.getenv("BREVO_SENDER_NAME", "Reservas UDF")
    if not api_key or not sender_email:
        logger.error("Brevo delivery is enabled but sender configuration is incomplete")
        return jsonify({"error": "Email delivery is not configured"}), 503

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
        return jsonify({"error": "Email provider request failed"}), 502

    try:
        result = response.json() if response.content else {}
    except requests.JSONDecodeError:
        result = {}
    if not isinstance(result, dict):
        result = {}
    logger.info("Brevo accepted a transactional email (status=%s)", response.status_code)
    return jsonify({"status": "sent", "messageId": result.get("messageId")}), 200
