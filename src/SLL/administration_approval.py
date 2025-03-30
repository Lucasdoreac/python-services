import os
from flask import Flask, Blueprint, render_template, request, current_app, url_for
from BLL import send_to_reitoria, send_to_coordenacao, send_event_status

# Create a blueprint for handling templates and related routes.
templates_bp = Blueprint('templates_bp', __name__, template_folder='../templates')

@templates_bp.route('/administration_approval', methods=['GET', 'POST'])
def administration_approval():
    tokenId = request.args.get('tokenId')
    eventId = request.args.get('eventId')
    step = request.args.get('step')
    # Validate token and eventId as needed.
    if step and eventId and tokenId and tokenId != "something-that-needs-to-be-validated":
        if os.getenv("FLASK_ENV") != "development":
            if step == "0":
                # MinIO icon URLs (adjust paths as needed)
                pdf_link = f"{os.getenv('MINIO_URL')}/labtech/reservation-pdfs/{eventId}.pdf"
                pdf_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/pdf.png"
                request_changes_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/request-changes.png"
                approve_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/approve.png"
                reject_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/reject.png"

                # Example links (adjust to your routes)
                with current_app.test_request_context():
                    request_changes_link = url_for('templates_bp.request_changes', eventId=eventId, tokenId='tokenId', _external=True)
                    approve_link = url_for('templates_bp.approve', eventId=eventId, tokenId='tokenId', who='coordenacao', _external=True)
                    reject_link = url_for('templates_bp.reject', eventId=eventId, tokenId='tokenId', who='coordenacao', _external=True)

                return render_template(
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
            elif step == "1":
                # MinIO icon URLs (adjust paths as needed)
                pdf_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/pdf.png"
                request_changes_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/request-changes.png"
                approve_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/approve.png"
                reject_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/reject.png"

                # Example links (adjust to your routes)
                # Maybe Reitoria doesn't need a 'request changes' link. You can omit or include it as needed.
                request_changes_link = None
                with current_app.test_request_context():
                    approve_link = url_for('templates_bp.approve', eventId=eventId, tokenId='tokenId', who='reitoria',
                                           _external=True)
                    reject_link = url_for('templates_bp.reject', eventId=eventId, tokenId='tokenId', who='reitoria',
                                          _external=True)

                # Render the template with the appropriate data
                return render_template(
                    "email/para_aprovacao.html",
                    user_type="Reitoria",
                    pdf_link=f"{os.getenv('MINIO_URL')}/labtech/reservation-pdfs/{eventId}.pdf",
                    pdf_icon_url=pdf_icon_url,
                    request_changes_icon_url=request_changes_icon_url,
                    approve_icon_url=approve_icon_url,
                    reject_icon_url=reject_icon_url,
                    request_changes_link=request_changes_link,
                    approve_link=approve_link,
                    reject_link=reject_link
                )


        if step == "0":
            if os.getenv("FLASK_ENV") == "development":
                return send_to_coordenacao(eventId)
            send_to_coordenacao(eventId)
        elif step == "1":
            if os.getenv("FLASK_ENV") == "development":
                return send_to_reitoria(eventId)
            send_to_reitoria(eventId)
    else:
        return "Missing tokenId or eventId", 400

@templates_bp.route('/approve')
def approve():
    eventId = request.args.get('eventId')
    tokenId = request.args.get('tokenId')
    if tokenId != "something-that-needs-to-be-validated":
        who = request.args.get('who')
        send_event_status(eventId, True, who)
        if who == "coordenacao":
            if os.getenv("FLASK_ENV") == "development":
                return send_to_reitoria(eventId)
            send_to_reitoria(eventId)
        return "Evento aprovado!"
    return "Token inválido!", 400

@templates_bp.route('/reject')
def reject():
    eventId = request.args.get('eventId')
    who = request.args.get('who')
    tokenId = request.args.get('tokenId')
    if tokenId != "something-that-needs-to-be-validated":
        if os.getenv("FLASK_ENV") == "development":
            return send_event_status(eventId, False, who)
        send_event_status(eventId, False, who)
        return "Evento rejeitado!"
    return "Token inválido!", 400

@templates_bp.route('/request_changes')
def request_changes():
    # Add your business logic for requesting changes to the event here.
    return "Solicitando alterações no evento!"
