"""Tela de ofertas: marcar os dias da semana das aulas do semestre.

As ofertas vêm da planilha da UDF sem dia da semana, e sem dia a aula não
bloqueia sala (#29). Só quem está em OFFER_ADMIN_EMAILS (vazio = ninguém) usa
estas rotas; o login do Reservas não tem papéis."""
from datetime import date
from functools import wraps

from flasgger import swag_from
from flask import Blueprint, jsonify, request

from settings import get_offer_settings
from SLL.auth_decorators import token_required
from SLL.cluster_api.request_methods import GraphQlRequestMethods, RestApiRequestMethods
from SLL.py_log import AppLogger, LogType
from SLL.swagger_docs import get_swagger_specification

offers_admin_bp = Blueprint('offers_admin_bp', __name__)
PAGE_SIZE = 20


def offers_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_offer_settings().can_manage_offers(request.headers.get('email')):
            return jsonify({"error": "Sem permissão para gerenciar ofertas"}), 403
        return f(*args, **kwargs)
    return token_required(decorated)


def _flat(offer):
    name = lambda key: (offer.get(key) or {}).get("name")  # noqa: E731
    return {"id": offer["id"], "offerId": offer.get("offerId"), "weekdays": offer.get("weekdays") or [],
            "discipline": name("discipline"), "period": name("period"), "room": name("room"),
            "teacher": name("teacher"), "campus": name("campus")}


@offers_admin_bp.route('/auth/permissions', methods=['GET'])
@token_required
@swag_from(get_swagger_specification('auth', 'PERMISSIONS'))
def permissions():
    """O que a pessoa logada pode ver no front (hoje: a tela de ofertas)."""
    return jsonify({"manageOffers": get_offer_settings().can_manage_offers(request.headers.get('email'))})


@offers_admin_bp.route('/offers/manage', methods=['GET'])
@offers_admin_required
@swag_from(get_swagger_specification('offers', 'MANAGE'))
def list_offers():
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    semester = request.args.get('semester', 1 if today.month < 7 else 2, type=int)
    page = max(request.args.get('page', 1, type=int), 1)
    try:
        offers = GraphQlRequestMethods.get_offers_page(
            year=year, semester=semester, discipline=(request.args.get('discipline') or '').strip() or None,
            first=PAGE_SIZE, skip=(page - 1) * PAGE_SIZE)
    except Exception as e:
        AppLogger.log(f"Tela de ofertas: catálogo falhou: {e}", LogType.ERROR, ip_address=request.remote_addr)
        return jsonify({"error": "Catálogo indisponível"}), 502
    return jsonify({"offers": [_flat(o) for o in offers], "page": page, "pageSize": PAGE_SIZE,
                    "year": year, "semester": semester})


@offers_admin_bp.route('/offers/<string:offer_id>/weekdays', methods=['PUT'])
@offers_admin_required
@swag_from(get_swagger_specification('offers', 'WEEKDAYS'))
def set_weekdays(offer_id):
    weekdays = (request.get_json(silent=True) or {}).get("weekdays")
    try:
        status, body = RestApiRequestMethods.set_offer_weekdays(offer_id, weekdays)
    except Exception as e:
        AppLogger.log(f"Tela de ofertas: catálogo falhou: {e}", LogType.ERROR, ip_address=request.remote_addr)
        return jsonify({"error": "Catálogo indisponível"}), 502
    AppLogger.log(f"Oferta {offer_id}: dias da semana {weekdays} por {request.headers.get('email')} ({status})",
                  LogType.INFO, ip_address=request.remote_addr)
    return jsonify(body), status
