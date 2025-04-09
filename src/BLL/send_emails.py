import os
from datetime import datetime
from hashlib import sha256
from DAL.collections_repositories import SendEmailrepository
import requests
from flask import render_template, current_app, url_for, request
from DAL import ReservationManager
from SLL import AppLogger, Logmessage, LogType
from sr_requests_module.request_methods import GraphQlRequestMethods
from .index import events_repository,FlowController
from BLL.enums import EmailStep, EventStatus


if os.getenv("FLASK_ENV") == "development":
    emails = {
        "reitoria": ["danrleywillian@gmail.com", "guilherme.amaral2004@gmail.com"],
        "coordenacao": ["dwcorpbrasil@gmail.com", "danrley.pereira@cs.udf.edu.br"]
    }
else:
    emails = {
        "reitoria": ["suelaine.santos@udf.edu.br"],
        "coordenacao": [],
        "reservas": ["bruno.silva@udf.edu.br"]
    }

def send_to_coordenacao(event_id):
    """
    Sends an email to Coordenação for event approval.

    Args:
        email (str): Recipient's email address (Coordenação).
        event_id (int or str): Identifier of the event to be approved/rejected.

    Returns:
        Response: HTTP response from the email sending service.
    """
    #crair email token de uso UNICO(so desativa token quando a acao for tomada ex: approve,rejected or requested change)
    tokenId = create_send_email_token(event_id, step=EmailStep.COORDENACAO)
    # MinIO icon URLs (adjust paths as needed)
    pdf_link = f"{os.getenv('MINIO_URL')}/labtech/reservation-pdfs/{event_id}.pdf"
    pdf_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/pdf.png"
    request_changes_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/request-changes.png"
    approve_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/approve.png"
    reject_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/reject.png"

    # Example links (adjust to your routes)
    with current_app.test_request_context():
        request_changes_link = url_for('templates_bp.request_changes', eventId=event_id, tokenId=tokenId, _external=True)
        approve_link = url_for('templates_bp.approve', eventId=event_id, tokenId=tokenId, who='coordenacao', _external=True)
        reject_link = url_for('templates_bp.reject', eventId=event_id, tokenId=tokenId, who='coordenacao', _external=True)

    course_id = FlowController.find_event_by_event_id(event_id)
    coordinator_id = get_coordinator_by_graduation_id(course_id['graduationId'])
    teacher_email = find_teacher_email_by_id(coordinator_id)
    emails["coordenacao"].append(teacher_email)

    # Render the template with the appropriate data
    html_content = render_template(
        "email/para_aprovacao.html",
        user_type="Coordenação",
        pdf_link=pdf_link,
        pdf_icon_url=pdf_icon_url,
        request_changes_icon_url=request_changes_icon_url,
        approve_icon_url=approve_icon_url,
        reject_icon_url=reject_icon_url,
        request_changes_link=request_changes_link,
        approve_link=approve_link,
        reject_link=reject_link
    )
    if os.getenv("FLASK_ENV") == "development":
        return html_content

    # Prepare the email payload
    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send-email"
    payload = {
        'subject': 'Evento para Aprovação - Coordenação',
        'content': html_content,
        'to': ", ".join(emails["coordenacao"]),
        'is_html': True
    }
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }

    AppLogger.log(Logmessage.SENDING_EMAIL, LogType.INFO, email=emails["coordenacao"], event=event_id, token=tokenId)
    # Send the request to your cloud function
    return requests.post(url, json=payload, headers=headers)

def send_to_reitoria(event_id):
    """
    Sends an email to Reitoria for event approval.

    Args:
        email (str): Recipient's email address (Reitoria).
        event_id (int or str): Identifier of the event to be approved/rejected.

    Returns:
        Response: HTTP response from the email sending service.
    """
    # crair email token de uso UNICO(so desativa token quando a acao for tomada ex: approve,rejected or requested change)
    tokenId = create_send_email_token(event_id, step=EmailStep.REITORIA)

    # MinIO icon URLs (adjust paths as needed)
    pdf_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/pdf.png"
    request_changes_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/request-changes.png"
    approve_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/approve.png"
    reject_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/reject.png"

    # Example links (adjust to your routes)
    # Maybe Reitoria doesn't need a 'request changes' link. You can omit or include it as needed.
    request_changes_link = None
    with current_app.test_request_context():
        approve_link = url_for('templates_bp.approve', eventId=event_id, tokenId=tokenId, who='reitoria', _external=True)
        reject_link = url_for('templates_bp.reject', eventId=event_id, tokenId=tokenId, who='reitoria', _external=True)

    # Render the template with the appropriate data
    html_content = render_template(
        "email/para_aprovacao.html",
        user_type="Reitoria",
        pdf_link=f"{os.getenv('MINIO_URL')}/labtech/reservation-pdfs/{event_id}.pdf",
        pdf_icon_url=pdf_icon_url,
        request_changes_icon_url=request_changes_icon_url,
        approve_icon_url=approve_icon_url,
        reject_icon_url=reject_icon_url,
        request_changes_link=request_changes_link,
        approve_link=approve_link,
        reject_link=reject_link
    )
    if os.getenv("FLASK_ENV") == "development":
        return html_content

    # Prepare the email payload
    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send-email"
    payload = {
        'subject': 'Evento para Aprovação - Reitoria',
        'content': html_content,
        'to': ", ".join(emails["reitoria"]),
        'is_html': True
    }
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }

    AppLogger.log(Logmessage.SENDING_EMAIL, LogType.INFO, email=emails["reitoria"], event=event_id, token=tokenId)
    # Send the request to your cloud function
    response = requests.post(url, json=payload, headers=headers)
    return response

def send_event_status(event_id, is_approved: bool, who: str, token:str):
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
    AppLogger.log(
        Logmessage.EVENT_APPROVED_REJECTED_BY,
        LogType.INFO,
        event_id=event_id,
        action='approved' if is_approved else 'rejected',
        who=who,
        token=token)
    event_status = ""
    if is_approved:
        if who == 'coordenacao':
            apply_token_action(0, 'approved', event_id, token)
            event_status = EventStatus.APPROVED_BY_COORDENACAO.value
        else:
            apply_token_action(1, 'approved', event_id, token)
            event_status = EventStatus.APPROVED_BY_REITORIA.value
    else:
        if who == 'coordenacao':
            apply_token_action(0, 'rejected', event_id, token)
            event_status = EventStatus.REJECTED_BY_COORDENACAO.value
        else:
            apply_token_action(1, 'rejected', event_id, token)
            event_status = EventStatus.REJECTED_BY_REITORIA.value

    event = events_repository.find_by_id(event_id)
    email = event["organizer"]["email"]
    event.pop("_id", None)
    event["status"] = event_status
    # update event status
    reservation_manager = ReservationManager()
    reservation_manager.update_event(event_id, event_data=event)
    # MinIO icon URLs (adjust paths if needed)
    pdf_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/pdf.png"
    approved_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/approved.png"
    denied_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/denied.png"

    # Render the template with the appropriate data
    html_content = render_template(
        "email/status_evento.html",
        username=email,
        is_approved=is_approved,
        pdf_link=f"{os.getenv('MINIO_URL')}/labtech/reservation-pdfs/{event_id}.pdf",
        pdf_icon_url=pdf_icon_url,
        approved_icon_url=approved_icon_url,
        denied_icon_url=denied_icon_url,
        who="Reitoria" if who == "reitoria" else "Coordenação",
    )
    if os.getenv("FLASK_ENV") == "development":
        return html_content

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

def verify_token_from_email(tokenId) -> bool:
    data = send_email_repository.get_send_email_by_token_id(tokenId)

    for record in data:
        if tokenId == record.get("tokenId") and record.get("active") is True:
            return True
        return False

def apply_token_action(step: int, action:str, eventId:str, tokenId: str) -> None:
    query = {
        'eventId': eventId,
        'step': step,
        'tokenId': tokenId,
    }

    new_values = {
        '$set': {
            'step': step,
            'active': False,
            'action': action,
            'update_at': datetime.now()  # Atualiza o timestamp de modificação
        }
    }

    send_email_repository.update_one(query, new_values)
    

send_email_repository = SendEmailrepository()

def create_send_email_token(event_id: str,step: EmailStep)-> str:
    now = datetime.now()
    tokenId = sha256(str(now).encode()).hexdigest()
    reservation_manager = ReservationManager()
    reservation_manager.insert_send_email(tokenId, step.value, event_id)
    return tokenId

def get_coordinator_by_graduation_id(graduationId: int)-> str:
    course = GraphQlRequestMethods.get_course_by_id(graduationId)
    course = course[0]
    return course['coordinator']

def find_teacher_email_by_id(teacherId: int) -> str:
    """
    Find a teacher's name by their ID.

    Args:
        id (str): The teacher's ID.

    Returns:
        str: The teacher's email.
    """
    teacher = GraphQlRequestMethods.get_teachers_by_id(teacherId)
    teacher = teacher[0]
    return teacher['email']