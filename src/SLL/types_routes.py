from flask import Blueprint, jsonify
from flasgger import swag_from

from .swagger_docs import get_swagger_specification
from .auth_decorators import api_key_required
from BLL import FlowController

types_bp = Blueprint('types', __name__)


class TypesRoutes:
    @staticmethod
    @types_bp.route('/types', methods=['GET'])
    @api_key_required
    @swag_from(get_swagger_specification(path='types', method='GET'))
    def get_types():
        types_data = FlowController.find_all_types()
        return jsonify({'types': types_data}), 200

    @staticmethod
    @types_bp.route('/types/<string:collection>', methods=['GET'])
    @api_key_required
    @swag_from(get_swagger_specification(path='types', method='GET', resource='collection'))
    def get_type_by_collection(collection: str):
        return FlowController.find_type_by_collection(collection)


types_routes = TypesRoutes()
