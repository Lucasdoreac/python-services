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
from settings import get_email_settings




def _deliver(subject, html_content, to, event_id, token="-"):
    """Único ponto que decide se o e-mail sai.

    EMAIL_DRY_RUN (padrão: ligado) devolve o HTML sem enviar nada -- é o que
    o preview das rotas de aprovação usa. Desligado, faz o POST na cloud
    function. Antes cada função de envio repetia `if FLASK_ENV ==
    "development": return html_content` e montava seu próprio POST.
    """
    settings = get_email_settings()
    if settings.email_dry_run:
        AppLogger.log(
            f"EMAIL_DRY_RUN ligado: '{subject}' (evento {event_id}) não enviado; "
            f"destinatários: {to}",
            LogType.INFO,
        )
        return html_content

    AppLogger.log(Logmessage.SENDING_EMAIL, LogType.INFO, email=to, event=event_id, token=token)
    return requests.post(
        f"{settings.cloud_function_url}/send-email",
        json={'subject': subject, 'content': html_content, 'to': to, 'is_html': True},
        headers={'X-API-Key': settings.cloud_function_api_key, 'Content-Type': 'application/json'},
    )


def _pdf_link(event_id):
    minio_url = (os.getenv("MINIO_URL") or "").strip().rstrip("/")
    if minio_url:
        return f"{minio_url}/labtech/reservation-pdfs/{event_id}.pdf"
    scheme = os.getenv("SERVER_SCHEME", "http")
    server_name = os.getenv("SERVER_NAME", "localhost:5000")
    return f"{scheme}://{server_name}/events/{event_id}/pdf"


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
    #crair email token de uso UNICO(so desativa token quando a acao for tomada ex: approve,rejected or requested change)
    tokenId = create_send_email_token(event_id, step=EmailStep.COORDENACAO)
    pdf_link = _pdf_link(event_id)
    pdf_icon_url = _icon_url("pdf.png")
    request_changes_icon_url = _icon_url("request-changes.png")
    approve_icon_url = _icon_url("approve.png")
    reject_icon_url = _icon_url("reject.png")

    # Example links (adjust to your routes)
    with current_app.test_request_context():
        request_changes_link = url_for('templates_bp.request_changes', eventId=event_id, tokenId=tokenId, _external=True)
        approve_link = url_for('templates_bp.approve', eventId=event_id, tokenId=tokenId, who='coordenacao', _external=True)
        reject_link = url_for('templates_bp.reject', eventId=event_id, tokenId=tokenId, who='coordenacao', _external=True)

    course_id = FlowController.find_event_by_event_id(event_id)
    coordinator_id = get_coordinator_by_graduation_id(course_id.get('graduationId'))
    teacher_email = find_teacher_email_by_id(coordinator_id)
    # Lista local por chamada: antes, emails["coordenacao"] era global e compartilhada
    # entre todas as requisições. Um .append() nela (como havia antes)
    # acumulava o coordenador de cada evento anterior para sempre, vazando
    # destinatário de um evento para o email de outro.
    #
    # Guarda: curso sem coordenador cadastrado, ou coordenador sem professor
    # correspondente, não deve derrubar o fluxo com 500 (era o que acontecia
    # antes, via IndexError/KeyError em get_coordinator_by_graduation_id e
    # find_teacher_email_by_id). Cai para a caixa padrão de Coordenação
    # (EMAIL_RECIPIENTS_COORDENACAO) e segue o envio normalmente.
    if teacher_email:
        coordenacao_recipients = get_email_settings().email_recipients_coordenacao + [teacher_email]
    else:
        AppLogger.log(
            f"Evento {event_id}: sem coordenador identificável (curso {course_id.get('graduationId')}); "
            "usando caixa padrão de Coordenação.",
            LogType.WARNING,
        )
        coordenacao_recipients = list(get_email_settings().email_recipients_coordenacao)

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
    return _deliver(
        'Evento para Aprovação - Coordenação', html_content,
        ", ".join(coordenacao_recipients), event_id, tokenId,
    )

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

    pdf_icon_url = _icon_url("pdf.png")
    request_changes_icon_url = _icon_url("request-changes.png")
    approve_icon_url = _icon_url("approve.png")
    reject_icon_url = _icon_url("reject.png")

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
        pdf_link=_pdf_link(event_id),
        pdf_icon_url=pdf_icon_url,
        request_changes_icon_url=request_changes_icon_url,
        approve_icon_url=approve_icon_url,
        reject_icon_url=reject_icon_url,
        request_changes_link=request_changes_link,
        approve_link=approve_link,
        reject_link=reject_link
    )
    return _deliver(
        'Evento para Aprovação - Reitoria', html_content,
        ", ".join(get_email_settings().email_recipients_reitoria), event_id, tokenId,
    )


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

    # 8. Envia (ou devolve o HTML em dry-run)
    return _deliver(
        'Nova Reserva Criada', html_content,
        ", ".join(get_email_settings().email_recipients_reitoria), event_id,
    )

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
    # Subject line changes based on approval or denial
    subject = "Evento Aprovado" if is_approved else "Evento Não Aprovado"
    return _deliver(subject, html_content, [email], event_id, token)

def request_event_changes(event_id: str, message: str, token: str):
    """
    Coordenação pede mudança (issue #35): o evento vai para requested_change,
    a mensagem fica em event["changesRequested"] e a pessoa solicitante
    recebe o pedido com o link para editar o evento no front. A reserva da
    sala continua: o evento volta para aprovação quando for reenviado.
    """
    AppLogger.log(Logmessage.EVENT_CHANGES_REQUESTED, LogType.INFO, event_id=event_id, token=token)
    apply_token_action(EmailStep.COORDENACAO.value, 'requested_change', event_id, token)

    event = events_repository.find_by_id(event_id)
    email = event["organizer"]["email"]
    event.pop("_id", None)
    event["status"] = EventStatus.REQUESTED_CHANGE.value
    event["changesRequested"] = message
    ReservationManager().update_event(event_id, event_data=event)

    html_content = render_template(
        "email/mudancas_solicitadas.html",
        mensagem=message,
        edit_link=f"{get_email_settings().frontend_url.rstrip('/')}/event/type-selection?eventId={event_id}",
    )
    return _deliver("Evento: a Coordenação pediu mudanças", html_content, [email], event_id, token)


def token_step(tokenId):
    """Etapa (EmailStep) do token do e-mail, ou None se não existe."""
    records = send_email_repository.get_send_email_by_token_id(tokenId)
    return next((r.get("step") for r in records if r.get("tokenId") == tokenId), None)


# Enquanto o token está active, qual status o evento precisa ter pra essa
# etapa ainda estar de fato pendente. Se o evento já saiu desse status (foi
# decidido por outro caminho -- outro token, outra aba, um clique
# anterior), um token "active" órfão não deve mais funcionar.
_PENDING_EVENT_STATUS_BY_STEP = {
    EmailStep.COORDENACAO.value: EventStatus.WAITING.value,
    EmailStep.REITORIA.value: EventStatus.APPROVED_BY_COORDENACAO.value,
}


def verify_token_from_email(tokenId) -> bool:
    """
    Token de aprovação é de uso único: só é válido se (a) existe, (b) está
    active, e (c) o evento que ele decide ainda está pendente nessa etapa.

    Antes: sem (a) tratado, tokenId inexistente fazia a função "cair pro
    final" sem return -> None; e o guard em check_request só barrava
    `is False`, então `None is False` deixava passar um token forjado. E
    sem (c), um token que ficou "active" órfão (ex.: de uma visita anterior
    a /administration_approval, que sempre emitia um token novo) continuava
    válido pra aprovar/rejeitar mesmo depois do evento já ter sido decidido.
    """
    records = send_email_repository.get_send_email_by_token_id(tokenId)
    record = next((r for r in records if r.get("tokenId") == tokenId), None)

    if record is None or record.get("active") is not True:
        return False

    expected_status = _PENDING_EVENT_STATUS_BY_STEP.get(record.get("step"))
    if expected_status is None:
        return True

    event = FlowController.find_event_by_event_id(record.get("eventId"))
    return bool(event) and event.get("status") == expected_status

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
    # Uso único: qualquer token ainda "active" pra esse (evento, etapa) fica
    # órfão e reutilizável pra sempre assim que um novo é emitido (ex.: cada
    # visita a /administration_approval mintava um token novo, abandonando
    # o anterior). Desativa antes de criar o próximo.
    send_email_repository.deactivate_active_for_event_step(
        event_id,
        step.value,
        {'$set': {'active': False, 'update_at': datetime.now()}},
    )
    now = datetime.now()
    tokenId = sha256(str(now).encode()).hexdigest()
    reservation_manager = ReservationManager()
    reservation_manager.insert_send_email(tokenId, step.value, event_id)
    return tokenId

def get_coordinator_by_graduation_id(graduationId: str):
    """
    Retorna o id do coordenador do curso, ou None se o curso não existir ou
    não tiver coordenador cadastrado.

    Antes, course[0] e course['coordinator'] estouravam IndexError/KeyError
    nesses casos, virando um 500 pra quem chamou (send_to_coordenacao).
    """
    if not graduationId:
        AppLogger.log(Logmessage.COURSES_NOT_FOUND, LogType.WARNING, ip_address=None)
        return None
    course = GraphQlRequestMethods.get_course_by_id(graduationId)
    if not course:
        AppLogger.log(Logmessage.COURSES_NOT_FOUND, LogType.WARNING, ip_address=None)
        return None
    return course[0].get('coordinator') or None

def find_teacher_email_by_id(teacherId: str):
    """
    Find a teacher's email by their ID.

    Args:
        id (str): The teacher's ID.

    Returns:
        str | None: O email do professor, ou None se o id for vazio/nulo ou
        não corresponder a nenhum professor cadastrado (antes, teacher[0]
        estourava IndexError nesse caso).
    """
    if not teacherId:
        return None
    teacher = GraphQlRequestMethods.get_teachers_by_id(teacherId)
    if not teacher:
        AppLogger.log(Logmessage.TEACHERS_NOT_FOUND, LogType.WARNING, ip_address=None)
        return None
    return teacher[0].get('email') or None
