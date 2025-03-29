import os
import requests
from flask import render_template


def send_to_coordenacao(email, event_id):
    """
    Sends an email to Coordenação for event approval.

    Args:
        email (str): Recipient's email address (Coordenação).
        event_id (int or str): Identifier of the event to be approved/rejected.

    Returns:
        Response: HTTP response from the email sending service.
    """
    # MinIO icon URLs (adjust paths as needed)
    pdf_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/pdf.png"
    request_changes_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/request-changes.png"
    approve_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/approve.png"
    reject_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/reject.png"

    # Example links (adjust to your routes)
    request_changes_link = f"https://seu-frontend.com/events/{event_id}/request-changes"
    approve_link = f"https://seu-frontend.com/events/{event_id}/approve"
    reject_link = f"https://seu-frontend.com/events/{event_id}/reject"

    # Render the template with the appropriate data
    html_content = render_template(
        "email/para_aprovacao.html",
        user_type="Coordenação",
        pdf_icon_url=pdf_icon_url,
        request_changes_icon_url=request_changes_icon_url,
        approve_icon_url=approve_icon_url,
        reject_icon_url=reject_icon_url,
        request_changes_link=request_changes_link,
        approve_link=approve_link,
        reject_link=reject_link
    )

    # Prepare the email payload
    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send-email"
    payload = {
        'subject': 'Evento para Aprovação - Coordenação',
        'content': html_content,
        'to': [email],
        'is_html': True
    }
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }

    # Send the request to your cloud function
    response = requests.post(url, json=payload, headers=headers)
    return response


def send_to_reitoria(email, event_id):
    """
    Sends an email to Reitoria for event approval.

    Args:
        email (str): Recipient's email address (Reitoria).
        event_id (int or str): Identifier of the event to be approved/rejected.

    Returns:
        Response: HTTP response from the email sending service.
    """
    # MinIO icon URLs (adjust paths as needed)
    pdf_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/pdf.png"
    request_changes_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/request-changes.png"
    approve_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/approve.png"
    reject_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/reject.png"

    # Example links (adjust to your routes)
    # Maybe Reitoria doesn't need a 'request changes' link. You can omit or include it as needed.
    request_changes_link = None  # or "https://seu-frontend.com/events/{event_id}/request-changes"
    approve_link = f"https://seu-frontend.com/events/{event_id}/approve"
    reject_link = f"https://seu-frontend.com/events/{event_id}/reject"

    # Render the template with the appropriate data
    html_content = render_template(
        "email/para_aprovacao.html",
        user_type="Reitoria",
        pdf_icon_url=pdf_icon_url,
        request_changes_icon_url=request_changes_icon_url,
        approve_icon_url=approve_icon_url,
        reject_icon_url=reject_icon_url,
        request_changes_link=request_changes_link,
        approve_link=approve_link,
        reject_link=reject_link
    )

    # Prepare the email payload
    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send-email"
    payload = {
        'subject': 'Evento para Aprovação - Reitoria',
        'content': html_content,
        'to': [email],
        'is_html': True
    }
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }

    # Send the request to your cloud function
    response = requests.post(url, json=payload, headers=headers)
    return response

def send_event_status(email, username, event_id, is_approved):
    """
    Sends an email to inform the user if the event was approved or denied.

    Args:
        email (str): Recipient's email address.
        username (str): The user’s name (e.g. "Professor").
        event_id (int or str): Identifier of the event.
        is_approved (bool): True if the event is approved, False otherwise.

    Returns:
        Response: HTTP response from the email sending service.
    """
    # MinIO icon URLs (adjust paths if needed)
    pdf_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/pdf.png"
    approved_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/approved.png"
    denied_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/denied.png"

    # Render the template with the appropriate data
    html_content = render_template(
        "email/status_evento.html",
        username=username,
        is_approved=is_approved,
        pdf_icon_url=pdf_icon_url,
        approved_icon_url=approved_icon_url,
        denied_icon_url=denied_icon_url
    )

    # Subject line changes based on approval or denial
    subject = "Evento Aprovado" if is_approved else "Evento Não Aprovado"

    # Prepare the email payload
    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send-email"
    payload = {
        'subject': subject,
        'content': html_content,
        'to': [email],
        'is_html': True
    }
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }

    # Send the request to your cloud function
    response = requests.post(url, json=payload, headers=headers)
    return response