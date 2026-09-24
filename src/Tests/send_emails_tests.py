import pytest
from mongomock import MongoClient

from configmodule import get_config
from SLL import create_app


# Mesmo padrão de fixture de endpoints_tests.py: troca o MongoClient real por
# mongomock ANTES de create_app(), porque create_app() é quem chama
# MongoDBConnectionFactory.init_app(...) e, em seguida, importa (via
# blueprints) o módulo BLL.send_emails — que instancia SendEmailrepository()
# no import. Se importássemos BLL.send_emails no topo deste arquivo, isso
# rodaria na coleta do pytest, antes do monkeypatch, e quebraria com
# "MongoDBConnectionFactory has not been initialized".
@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    app = create_app(get_config())
    with app.app_context():
        yield app


class TestSendToCoordenacaoRecipients:

    def test_does_not_leak_coordinator_between_calls(self, monkeypatch, app):
        """Regressão: emails["coordenacao"] é uma lista de módulo (send_emails.py:16-17)
        e send_to_coordenacao fazia .append() nela a cada chamada (send_emails.py:55),
        então o coordenador do evento 1 continuava na lista de destinatários do
        evento 2 (e de todo evento seguinte, para sempre).
        """
        from BLL import send_emails  # import tardio: ver comentário da fixture 'app'

        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {"graduationId": f"grad-{event_id}"}),
        )
        monkeypatch.setattr(
            send_emails,
            "get_coordinator_by_graduation_id",
            lambda graduation_id: f"coord-{graduation_id}",
        )
        monkeypatch.setattr(
            send_emails,
            "find_teacher_email_by_id",
            lambda teacher_id: f"{teacher_id}@udf.edu.br",
        )

        captured_payloads = []

        class FakeResponse:
            status_code = 200

        def fake_post(url, json=None, headers=None):
            captured_payloads.append(json)
            return FakeResponse()

        monkeypatch.setattr(send_emails.requests, "post", fake_post)
        # Força o caminho de produção: em FLASK_ENV=development a função
        # retorna o HTML antes de montar/enviar o payload (send_emails.py:70-71).
        monkeypatch.setenv("FLASK_ENV", "production")

        send_emails.send_to_coordenacao("event-1")
        send_emails.send_to_coordenacao("event-2")

        assert len(captured_payloads) == 2
        first_recipients = captured_payloads[0]["to"]
        second_recipients = captured_payloads[1]["to"]

        assert "coord-grad-event-1@udf.edu.br" in first_recipients
        assert "coord-grad-event-2@udf.edu.br" in second_recipients
        assert "coord-grad-event-1@udf.edu.br" not in second_recipients
