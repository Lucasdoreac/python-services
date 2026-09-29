import os
import json
import logging
import requests


def is_email_dry_run():
    return os.getenv("EMAIL_DRY_RUN", "").strip().casefold() == "true"


def dry_run_response():
    response = requests.Response()
    response.status_code = 202
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps({
        "message": "EMAIL_DRY_RUN enabled; email not sent"
    }).encode("utf-8")
    logging.getLogger(__name__).info(
        "Email suppressed because EMAIL_DRY_RUN is enabled"
    )
    return response


def send_email(payload):
    """Send email unless the environment explicitly enables a delivery dry-run."""
    if is_email_dry_run():
        return dry_run_response()

    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send-email"
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }
    return requests.post(url, json=payload, headers=headers)


def send_magic_link(email, username, magic_link):
    """ Sends a magic link email via the cloud function. """
    payload = {
        'subject': 'Login Authorization',
        'content': f"Hello {username}, use this link to login: {magic_link}",
        'to': [email],
        'is_html': False
    }
    return send_email(payload)
