"""Serviço de envio de e-mails transacionais via Brevo (Sendinblue).

Usa o SDK oficial sib-api-v3-sdk para despachar e-mails transacionais usando a
chave de API configurada em BREVO_API_KEY.
"""
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from SLL import AppLogger, LogType


def send_brevo_email(to, subject, content, is_html=True):
    """Envia um e-mail transacional via API do Brevo.

    Args:
        to (list[str] | str): E-mail ou lista de e-mails destinatários.
        subject (str): Assunto do e-mail.
        content (str): Conteúdo em HTML ou texto puro.
        is_html (bool): Indica se o conteúdo é HTML.

    Returns:
        CreateSmtpEmail: Resposta da API do Brevo contendo message_id.
    """
    from settings import get_email_settings
    settings = get_email_settings()

    if not settings.brevo_api_key:
        raise ValueError("BREVO_API_KEY não configurada para envio real de e-mails")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = settings.brevo_api_key

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    sender = {"name": settings.brevo_sender_name, "email": settings.brevo_sender_email}

    recipients = [{"email": addr.strip()} for addr in (to if isinstance(to, list) else [to]) if addr.strip()]

    email_kwargs = {
        "to": recipients,
        "sender": sender,
        "subject": subject,
    }
    if is_html:
        email_kwargs["html_content"] = content
    else:
        email_kwargs["text_content"] = content

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(**email_kwargs)

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        AppLogger.log(f"E-mail Brevo enviado com sucesso para {to}: {subject}", LogType.INFO)
        return response
    except ApiException as e:
        AppLogger.log(f"Erro na API do Brevo ao enviar para {to}: {e}", LogType.ERROR)
        raise e
