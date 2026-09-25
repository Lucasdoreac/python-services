"""Só quem criou o evento altera, envia ou reserva sala para ele.

O e-mail do header já foi validado pelo token_required. Antes, qualquer pessoa
logada reescrevia o evento de outra, o enviava para aprovação ou reservava sala
em nome dele."""
from functools import wraps

from bson import ObjectId
from flask import jsonify, request

from BLL import FlowController
from SLL.py_log import AppLogger, LogType


def ownership_error(event_id):
    """None se a pessoa logada é a organizadora; senão a resposta (404 ou 403)."""
    event = FlowController.find_event_by_event_id(event_id) if ObjectId.is_valid(str(event_id)) else None
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    dono = ((event.get("organizer") or {}).get("email") or "").strip().lower()
    if dono != (request.headers.get('email') or "").strip().lower():
        AppLogger.log(f"Evento {event_id}: alteração recusada para quem não é o organizador",
                      LogType.WARNING, ip_address=request.remote_addr)
        return jsonify({'error': 'Only the organizer can change this event'}), 403
    return None


def owner_required(f):
    """Para rotas com <event_id> na URL."""
    @wraps(f)
    def decorated(event_id, *args, **kwargs):
        return ownership_error(event_id) or f(event_id, *args, **kwargs)
    return decorated
