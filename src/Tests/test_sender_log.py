"""Os remetentes de e-mail de aprovação funcionam fora de desenvolvimento (a linha de log não quebra o envio).

Antes: send_reservation_info_to_reitoria chamava AppLogger.log com `message=...`, argumento que
colide com o parâmetro posicional da função, e dava TypeError antes de enviar qualquer coisa;
com o status de falha passando a ser tratado, isso viraria um 503 em todo evento "class"/"exam".
"""

import pytest
import requests

from Tests.helpers import create_draft


@pytest.fixture
def production_sends(client, monkeypatch):
    from BLL import send_emails

    sent = []

    def post(url, json=None, headers=None, **kwargs):
        sent.append(json)
        response = requests.Response()
        response.status_code = 200
        return response

    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLOUD_FUNCTION_URL", "https://email.example.test")
    monkeypatch.setattr("requests.post", post)
    monkeypatch.setattr(send_emails, "get_coordinator_by_graduation_id", lambda _id: "teacher-1")
    monkeypatch.setattr(send_emails, "find_teacher_email_by_id", lambda _id: "coord@example.test")
    return send_emails, sent


@pytest.mark.parametrize(
    ("sender", "subject"),
    [
        ("send_reservation_info_to_reitoria", "Nova Reserva Criada"),
        ("send_to_coordenacao", "Evento para Aprovação - Coordenação"),
        ("send_to_reitoria", "Evento para Aprovação - Reitoria"),
    ],
)
def test_each_sender_reaches_the_cloud_function(client, production_sends, sender, subject):
    send_emails, sent = production_sends
    event_id = create_draft(client)

    response = getattr(send_emails, sender)(event_id)

    assert response.status_code == 200
    assert [payload["subject"] for payload in sent] == [subject]
