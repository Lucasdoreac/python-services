import os
from datetime import datetime
from hashlib import sha256
from DAL.collections_repositories import SendEmailrepository
import requests
from flask import render_template, current_app, url_for
from DAL import ReservationManager
from SLL import AppLogger, Logmessage, LogType
from SLL.cluster_api.request_methods import GraphQlRequestMethods
from .index import events_repository, FlowController
from utils.enums import EmailStep, EventStatus


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


def send_reservation_info_to_reitoria(event_id, reservation_date=None, classification=None):
    """
    Sends an email to Reitoria with basic information about a newly created reservation.

    Args:
        event_id (int or str): Identifier of the created reservation/event.
        reservation_date (str, optional): Date string for the reservation.
        classification (str, optional): Classification provided directly.

    Returns:
        Response: HTTP response from the email sending service.
    """
    # 1. Fetch event data
    event = FlowController.find_event_by_event_id(event_id)
    if not event:
        raise ValueError(f"Event with ID {event_id} not found")

    # 2. Fetch associated reservations
    reservations = FlowController.find_reservation_by_event_id(event_id)

    # 3. Extract organizer information
    organizer = event.get("organizer", {})
    organizer_name = organizer.get("name", "Não informado")
    organizer_email = organizer.get("email", "Não informado")

    # 4. Get event classification
    event_classification = classification or event.get("eventTypeId", "Não informada")

    # 5. Extract room and campus information
    room_name = None
    campus_name = None

    if reservations and len(reservations) > 0 and isinstance(reservations[0], dict):
        room_id = reservations[0].get("roomId", None)
        if room_id is not None:
            try:
                room_obj = FlowController.find_room_by_id(room_id)
                if isinstance(room_obj, dict):
                    room_name = room_obj.get("name", None)
                    room_campus = room_obj.get("campus")

                    campus_obj = FlowController.find_campus_by_id(room_campus)
                    if isinstance(campus_obj, dict):
                        campus_name = campus_obj.get("name", None)
            except Exception as e:
                AppLogger.log(f"Error finding room: {str(e)}", LogType.ERROR, room_id=room_id)

    # 6. Format reservation date
    formatted_reservation_date = "Não informada"

    if reservation_date:
        formatted_reservation_date = reservation_date
    elif reservations and len(reservations) > 0 and "startAt" in reservations[0]:
        start_date_obj = reservations[0]["startAt"]
        if isinstance(start_date_obj, datetime):
            formatted_reservation_date = start_date_obj.strftime("%d/%m/%Y %H:%M")
        else:
            formatted_reservation_date = str(start_date_obj)

    # 7. Generate email content
    html_content = render_template(
        "email/reservation_info.html",
        organizer_name=organizer_name,
        organizer_email=organizer_email,
        classification=event_classification,
        room_name=room_name,
        room_campus=campus_name,
        reservation_date=formatted_reservation_date,
    )

    # 8. Return HTML content if in development mode
    if os.getenv("FLASK_ENV") == "development":
        return html_content

    # 9. Prepare and send email
    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send-email"
    payload = {
        'subject': 'Nova Reserva Criada',
        'content': html_content,
        'to': ", ".join(emails["reitoria"]),
        'is_html': True
    }
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }

    AppLogger.log(
        Logmessage.SENDING_EMAIL,
        LogType.INFO,
        email=emails["reitoria"],
        event=event_id,
        message="Notification of new reservation"
    )

    return requests.post(url, json=payload, headers=headers)

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
    """"
        deactivate the token after the action is taken
        Args:
            step (int): Step of the email process (0 for Coordenação, 1 for Reitoria).
            action (str): Action to be taken (approve or reject).
            eventId (str): ID of the event.
            tokenId (str): Token ID for verification.
        Returns:
            None
    """
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

def get_coordinator_by_graduation_id(graduationId: str)-> str:
    course = GraphQlRequestMethods.get_course_by_id(graduationId)
    course = course[0]
    return course['coordinator']

def find_teacher_email_by_id(teacherId: str) -> str:
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
