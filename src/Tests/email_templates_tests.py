from pathlib import Path

from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[1]
templates = Environment(loader=FileSystemLoader(ROOT / "templates"))


def test_approval_email_uses_text_actions_and_one_public_brand_logo():
    html = templates.get_template("email/para_aprovacao.html").render(
        user_type="Coordenação",
        pdf_link="https://staging.example/events/test/pdf",
        pdf_icon_url="",
        request_changes_icon_url="",
        approve_icon_url="",
        reject_icon_url="",
        request_changes_link="https://staging.example/request-changes",
        approve_link="https://staging.example/approve",
        reject_link="https://staging.example/reject",
        logo_url="https://staging.example/static/email/dw-corp.png",
        is_staging=True,
    )

    assert "DW Corp" in html
    assert "AMBIENTE DE TESTE — STAGING" in html
    assert html.count("<img") == 1
    assert "MINIO" not in html
    assert "✔ Aprovar" in html
    assert "✖ Recusar" in html


def test_status_email_has_no_remote_status_or_pdf_icons():
    html = templates.get_template("email/status_evento.html").render(
        username="professor@udf.edu.br",
        is_approved=True,
        pdf_link="https://staging.example/events/test/pdf",
        pdf_icon_url="",
        approved_icon_url="",
        denied_icon_url="",
        who="Coordenação",
        logo_url="https://staging.example/static/email/dw-corp.png",
        is_staging=True,
    )

    assert html.count("<img") == 1
    assert "alt=\"Approved\"" not in html
    assert "alt=\"PDF Icon\"" not in html
    assert "AMBIENTE DE TESTE — STAGING" in html
