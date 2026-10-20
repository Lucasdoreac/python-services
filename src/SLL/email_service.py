import os
import json
import logging
import requests

logger = logging.getLogger(__name__)


class EmailDeliveryFailed(RuntimeError):
    """A Cloud Function não aceitou a mensagem (não comprova entrega na caixa postal)."""


def require_email_acceptance(response):
    """Valida resposta HTTP; prévia HTML de development mantém seu contrato."""
    status = getattr(response, "status_code", None)
    if isinstance(status, int) and not 200 <= status < 300:
        raise EmailDeliveryFailed(status)


def recorded_decision_notice_failure():
    """A decisão continua gravada; falha de notificação não autoriza repeti-la."""
    return {
        "error": "Decisão registrada, mas uma notificação não foi aceita. Não repita a decisão.",
        "decisionRecorded": True,
        "notificationAccepted": False,
    }, 503


def recipient_allowlist():
    """Endereços exatos de EMAIL_RECIPIENT_ALLOWLIST (minúsculos); vazio quando a variável não existe.

    Opcional e desligada por padrão, para ambientes de homologação: com ela definida, só
    esses endereços recebem e-mail. Sem ela, os destinatários seguem como sempre.
    """
    return {
        address.strip().casefold()
        for address in (os.getenv("EMAIL_RECIPIENT_ALLOWLIST") or "").split(",")
        if address.strip()
    }


def _addresses(to):
    items = to.split(",") if isinstance(to, str) else (to or [])
    return [str(item).strip() for item in items if str(item).strip()]


def _accepted_without_sending():
    response = requests.Response()
    response.status_code = 202
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps({
        "message": "Nenhum destinatário permitido pela EMAIL_RECIPIENT_ALLOWLIST; e-mail não enviado"
    }).encode("utf-8")
    return response


def send_email(payload):
    """Envia pela Cloud Function (CLOUD_FUNCTION_URL), única saída de e-mail da API.

    Devolve a resposta HTTP da Cloud Function para o chamador decidir: quem inicia uma
    aprovação trata status que não seja 2xx como falha.
    """
    allowed = recipient_allowlist()
    if allowed:
        recipients = [a for a in _addresses(payload.get("to")) if a.casefold() in allowed]
        dropped = len(_addresses(payload.get("to"))) - len(recipients)
        if dropped:
            logger.info("EMAIL_RECIPIENT_ALLOWLIST removed %d recipient(s)", dropped)
        if not recipients:
            return _accepted_without_sending()
        payload = {**payload, "to": ", ".join(recipients) if isinstance(payload.get("to"), str) else recipients}

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
