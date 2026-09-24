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


class TestCoordinatorLookupGuards:
    """Regressão: get_coordinator_by_graduation_id e find_teacher_email_by_id
    estouravam IndexError/KeyError (send_emails.py:377,382 antes do fix) quando
    o curso não existia, não tinha coordenador, ou o coordenador não batia com
    nenhum professor cadastrado -- isso virava 500 pra quem chamasse
    send_to_coordenacao (administration_approval e events_routes.put_event).
    """

    def test_get_coordinator_returns_none_when_course_not_found(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.GraphQlRequestMethods,
            "get_course_by_id",
            staticmethod(lambda graduation_id: []),
        )
        assert send_emails.get_coordinator_by_graduation_id("curso-inexistente") is None

    def test_get_coordinator_returns_none_when_field_missing(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.GraphQlRequestMethods,
            "get_course_by_id",
            staticmethod(lambda graduation_id: [{"id": graduation_id, "name": "Curso sem coordenador"}]),
        )
        assert send_emails.get_coordinator_by_graduation_id("curso-sem-coordenador") is None

    def test_get_coordinator_returns_none_when_graduation_id_missing(self, monkeypatch, app):
        from BLL import send_emails

        assert send_emails.get_coordinator_by_graduation_id(None) is None
        assert send_emails.get_coordinator_by_graduation_id("") is None

    def test_find_teacher_email_returns_none_when_teacher_not_found(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.GraphQlRequestMethods,
            "get_teachers_by_id",
            staticmethod(lambda teacher_id: []),
        )
        assert send_emails.find_teacher_email_by_id("professor-fantasma") is None

    def test_find_teacher_email_returns_none_when_id_missing(self, monkeypatch, app):
        from BLL import send_emails

        assert send_emails.find_teacher_email_by_id(None) is None
        assert send_emails.find_teacher_email_by_id("") is None


class TestSendToCoordenacaoWithoutCoordinator:
    """Fim a fim: evento cujo curso não tem coordenador identificável não pode
    mais derrubar o fluxo com 500 -- cai para a caixa padrão de Coordenação
    (emails["coordenacao"]) e o email sai normalmente.
    """

    def _patch_email_delivery(self, monkeypatch, send_emails):
        captured_payloads = []

        class FakeResponse:
            status_code = 200

        def fake_post(url, json=None, headers=None):
            captured_payloads.append(json)
            return FakeResponse()

        monkeypatch.setattr(send_emails.requests, "post", fake_post)
        monkeypatch.setenv("FLASK_ENV", "production")
        return captured_payloads

    def test_falls_back_to_default_mailbox_when_course_has_no_coordinator(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {"graduationId": "curso-sem-coordenador"}),
        )
        monkeypatch.setattr(
            send_emails.GraphQlRequestMethods,
            "get_course_by_id",
            staticmethod(lambda graduation_id: [{"id": graduation_id, "coordinator": None}]),
        )
        captured_payloads = self._patch_email_delivery(monkeypatch, send_emails)

        # Não deve levantar exceção (antes: IndexError/KeyError -> 500).
        send_emails.send_to_coordenacao("event-sem-coordenador")

        assert len(captured_payloads) == 1
        assert captured_payloads[0]["to"] == ", ".join(send_emails.emails["coordenacao"])

    def test_falls_back_when_event_has_no_graduation_id(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {}),  # evento sem graduationId
        )
        captured_payloads = self._patch_email_delivery(monkeypatch, send_emails)

        send_emails.send_to_coordenacao("event-sem-graduationId")

        assert len(captured_payloads) == 1
        assert captured_payloads[0]["to"] == ", ".join(send_emails.emails["coordenacao"])
