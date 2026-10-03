import os
from datetime import datetime
from secrets import token_urlsafe
from DAL.collections_repositories import SendEmailrepository
from flask import render_template, current_app, url_for
from DAL import ReservationManager
from SLL import AppLogger, Logmessage, LogType
from SLL.cluster_api.request_methods import GraphQlRequestMethods
from .index import events_repository, FlowController
from utils.enums import EmailStep, EventStatus
from SLL.email_service import dry_run_response, is_email_dry_run, send_email
from SLL.signed_links import signed_query


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


def _pdf_link(event_id):
    """Link público do PDF, usando MinIO quando configurado e a API caso contrário."""
    minio_url = (os.getenv("MINIO_URL") or "").strip().rstrip("/")
    if minio_url:
        return f"{minio_url}/labtech/reservation-pdfs/{event_id}.pdf"

    scheme = os.getenv("SERVER_SCHEME", "http")
    server_name = os.getenv("SERVER_NAME", "localhost:5000")
    base = f"{scheme}://{server_name}/events/{event_id}/pdf"
    try:
        return f"{base}?{signed_query(event_id)}"
    except RuntimeError:
        return base  # development without LINK_SIGNING_KEY: the link will be refused


def _icon_url(name):
    minio_url = (os.getenv("MINIO_URL") or "").strip().rstrip("/")
    return f"{minio_url}/labtech/email-icones/{name}" if minio_url else ""

def send_to_coordenacao(event_id):
    """
    Sends an email to Coordenação for event approval.

    Args:
        email (str): Recipient's email address (Coordenação).
        event_id (int or str): Identifier of the event to be approved/rejected.

    Returns:
        Response: HTTP response from the email sending service.
    """
    if is_email_dry_run() and os.getenv("FLASK_ENV") != "development":
        return dry_run_response()
    recipients = list(emails["coordenacao"])
    try:
        course_id = FlowController.find_event_by_event_id(event_id)
        coordinator_id = get_coordinator_by_graduation_id(course_id['graduationId'])
        teacher_email = find_teacher_email_by_id(coordinator_id) if coordinator_id else None
        if teacher_email and teacher_email not in recipients:
            recipients.append(teacher_email)
    except (IndexError, KeyError, TypeError):
        AppLogger.log(
            "Coordinator email unavailable; using configured coordination recipients",
            LogType.WARNING,
            event_id=event_id,
        )
    if not recipients:
        raise ValueError("No coordination email recipient is available")

    group_id = token_urlsafe(24)
    reservation_manager = ReservationManager()
    send_email_repository.deactivate_active_for_event_step(
        event_id, EmailStep.COORDENACAO.value
    )
    if not reservation_manager.activate_approval_token_group(
        event_id, EmailStep.COORDENACAO.value, EventStatus.WAITING.value, group_id
    ):
        raise ValueError("Evento não está aguardando aprovação da Coordenação")
    tokens = {
        action: create_send_email_token(event_id, EmailStep.COORDENACAO, action, group_id)
        for action in ("approve", "reject", "request_changes")
    }
    # MinIO icon URLs (adjust paths as needed)
    pdf_link = _pdf_link(event_id)
    pdf_icon_url = _icon_url("pdf.png")
    request_changes_icon_url = _icon_url("request-changes.png")
    approve_icon_url = _icon_url("approve.png")
    reject_icon_url = _icon_url("reject.png")

    # Example links (adjust to your routes)
    with current_app.test_request_context():
        request_changes_link = url_for('templates_bp.request_changes', eventId=event_id,
                                       tokenId=tokens["request_changes"], _external=True)
        approve_link = url_for('templates_bp.approve', eventId=event_id, tokenId=tokens["approve"], _external=True)
        reject_link = url_for('templates_bp.reject', eventId=event_id, tokenId=tokens["reject"], _external=True)

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
    payload = {
        'subject': 'Evento para Aprovação - Coordenação',
        'content': html_content,
        'to': list(recipients),
        'is_html': True
    }
    AppLogger.log(Logmessage.SENDING_EMAIL, LogType.INFO, email=recipients, event=event_id)
    return send_email(payload)

def send_to_reitoria(event_id):
    """
    Sends an email to Reitoria for event approval.

    Args:
        email (str): Recipient's email address (Reitoria).
        event_id (int or str): Identifier of the event to be approved/rejected.

    Returns:
        Response: HTTP response from the email sending service.
    """
    if is_email_dry_run() and os.getenv("FLASK_ENV") != "development":
        return dry_run_response()
    group_id = token_urlsafe(24)
    reservation_manager = ReservationManager()
    send_email_repository.deactivate_active_for_event_step(
        event_id, EmailStep.REITORIA.value
    )
    if not reservation_manager.activate_approval_token_group(
        event_id,
        EmailStep.REITORIA.value,
        EventStatus.APPROVED_BY_COORDENACAO.value,
        group_id,
    ):
        raise ValueError("Evento não está aguardando aprovação da Reitoria")
    tokens = {
        action: create_send_email_token(event_id, EmailStep.REITORIA, action, group_id)
        for action in ("approve", "reject")
    }

    # MinIO icon URLs (adjust paths as needed)
    pdf_icon_url = _icon_url("pdf.png")
    request_changes_icon_url = _icon_url("request-changes.png")
    approve_icon_url = _icon_url("approve.png")
    reject_icon_url = _icon_url("reject.png")

    # Example links (adjust to your routes)
    # Only the Coordenação can ask for changes (issue #35); the Reitoria decides on what it approved.
    request_changes_link = None
    with current_app.test_request_context():
        approve_link = url_for('templates_bp.approve', eventId=event_id, tokenId=tokens["approve"], _external=True)
        reject_link = url_for('templates_bp.reject', eventId=event_id, tokenId=tokens["reject"], _external=True)

    # Render the template with the appropriate data
    html_content = render_template(
        "email/para_aprovacao.html",
        user_type="Reitoria",
        pdf_link=_pdf_link(event_id),
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
    payload = {
        'subject': 'Evento para Aprovação - Reitoria',
        'content': html_content,
        'to': list(emails["reitoria"]),
        'is_html': True
    }
    AppLogger.log(Logmessage.SENDING_EMAIL, LogType.INFO, email=emails["reitoria"], event=event_id)
    return send_email(payload)


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
    if is_email_dry_run() and os.getenv("FLASK_ENV") != "development":
        return dry_run_response()
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
                AppLogger.log(f"Error finding room: {type(e).__name__}", LogType.ERROR, room_id=room_id)

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
    payload = {
        'subject': 'Nova Reserva Criada',
        'content': html_content,
        'to': list(emails["reitoria"]),
        'is_html': True
    }
    AppLogger.log(
        Logmessage.SENDING_EMAIL,
        LogType.INFO,
        email=emails["reitoria"],
        event=event_id,
    )

    return send_email(payload)

def send_event_status(event_id, is_approved: bool, who: str, token: str = None):
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
    event = events_repository.find_by_id(event_id)
    email = event["organizer"]["email"]
    # MinIO icon URLs (adjust paths if needed)
    pdf_icon_url = _icon_url("pdf.png")
    approved_icon_url = _icon_url("approved.png")
    denied_icon_url = _icon_url("denied.png")

    # Render the template with the appropriate data
    html_content = render_template(
        "email/status_evento.html",
        username=email,
        is_approved=is_approved,
        pdf_link=_pdf_link(event_id),
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
    payload = {
        'subject': subject,
        'content': html_content,
        'to': [email],
        'is_html': True
    }
    return send_email(payload)

def send_change_request(event_id, message):
    """Tell the organizer what the Coordenação asked to change. No action link, no token."""
    event = events_repository.find_by_id(event_id)
    email = event["organizer"]["email"]
    base = (os.getenv("FRONTEND_URL") or "").strip().rstrip("/")
    html_content = render_template(
        "email/alteracoes_solicitadas.html",
        event_name=event.get("name") or "seu evento",
        message=message,
        my_events_link=f"{base}/event/mine" if base else None,
    )
    if os.getenv("FLASK_ENV") == "development":
        return html_content
    return send_email({
        "subject": "Alterações solicitadas no seu evento",
        "content": html_content,
        "to": [email],
        "is_html": True,
    })

def _expected_status(step):
    return (EventStatus.WAITING.value if step == EmailStep.COORDENACAO.value
            else EventStatus.APPROVED_BY_COORDENACAO.value)


APPROVAL_ACTIONS = ("approve", "reject", "request_changes")
MAX_CHANGE_MESSAGE = 1000


def verify_token_from_email(token_id, event_id, action):
    """Return an active token only when event, approval stage, and action match."""
    if action not in APPROVAL_ACTIONS:
        return None
    record = send_email_repository.get_send_email_by_token_id(token_id)
    if not record or record.get("active") is not True:
        return None
    if record.get("eventId") != event_id or record.get("action") != action:
        return None
    try:
        step = int(record["step"])
    except (KeyError, TypeError, ValueError):
        return None
    if step not in (EmailStep.COORDENACAO.value, EmailStep.REITORIA.value):
        return None
    if action == "request_changes" and step != EmailStep.COORDENACAO.value:
        return None  # only the Coordenação asks for changes (issue #35)
    event = events_repository.find_by_id(event_id)
    if not event or event.get("status") != _expected_status(step):
        return None
    current_group = (event.get("approvalTokenGroups") or {}).get(str(step))
    if not record.get("groupId") or current_group != record.get("groupId"):
        return None
    return record

send_email_repository = SendEmailrepository()

def create_send_email_token(event_id: str, step: EmailStep, action: str, group_id: str) -> str:
    tokenId = token_urlsafe(32)
    reservation_manager = ReservationManager()
    reservation_manager.insert_send_email(tokenId, step.value, event_id, action, group_id)
    return tokenId


def perform_approval_action(event_id: str, token_id: str, action: str, message: str | None = None):
    """Consume a scoped token and atomically transition the event from its expected status."""
    record = verify_token_from_email(token_id, event_id, action)
    if not record:
        return None
    step = int(record["step"])
    extra = None
    if action == "approve":
        new_status = (EventStatus.APPROVED_BY_COORDENACAO.value
                      if step == EmailStep.COORDENACAO.value
                      else EventStatus.APPROVED_BY_REITORIA.value)
    elif action == "reject":
        new_status = (EventStatus.REJECTED_BY_COORDENACAO.value
                      if step == EmailStep.COORDENACAO.value
                      else EventStatus.REJECTED_BY_REITORIA.value)
    elif action == "request_changes":
        new_status = EventStatus.REQUESTED_CHANGE.value
        extra = {"changeRequest": {
            "message": message,
            "requestedAt": datetime.now().isoformat(timespec="seconds"),
            "by": "coordenacao",
        }}
    else:
        return None

    if not ReservationManager().transition_event_status(
        event_id,
        token_id,
        action,
        _expected_status(step),
        new_status,
        step,
        record["groupId"],
        extra_event_fields=extra,
    ):
        return None
    if action == "request_changes":
        try:
            send_change_request(event_id, message)
        except Exception as error:  # the request is recorded; a failed notice only goes to the log
            AppLogger.log(
                Logmessage.CHANGE_REQUEST_NOTICE_FAILED,
                LogType.ERROR,
                event_id=event_id,
                error=type(error).__name__,
            )
    if action in ("approve", "reject"):
        send_event_status(
            event_id,
            action == "approve",
            "coordenacao" if step == EmailStep.COORDENACAO.value else "reitoria",
        )
        if action == "approve" and step == EmailStep.COORDENACAO.value:
            send_to_reitoria(event_id)
    return step, new_status

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
