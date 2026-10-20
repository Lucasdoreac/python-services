import os
import requests
from flask import Blueprint, jsonify, request
from flasgger import swag_from

from .cluster_api.request_methods import GraphQlRequestMethods, catalog_headers
from . import AppLogger, Logmessage, LogType
from .swagger_docs import get_swagger_specification
from .auth_decorators import token_required


types_bp = Blueprint('types', __name__)


class TypesRoutes:
    @staticmethod
    @types_bp.route('/types', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='types', method='GET'))
    def get_types():
        try:
            url_base = os.getenv('URL_restapi')
            url = f"{url_base}/types/"
            response = requests.get(url, headers=catalog_headers())
            response.raise_for_status()

            data = response.json()  # Expected to be a list of objects

            # add reservation types (no need to add to shared resources)
            resources_collection = {
                "collection": "resources",
                "types": [
                    {"id": "humanas", "label": "Humanas"},
                    {"id": "tecnologias", "label": "Tecnologias"},
                    {"id": "servicos", "label": "Serviços"},
                    {"id": "materiais", "label": "Materiais"}
                ]
            }

            target_public_collection = {
                "collection": "targetPublic",
                "types": [
                    {"id": "alunosUDF", "label": "Alunos UDF"},
                    {"id": "professores", "label": "Professores"},
                    {"id": "publicoExterno", "label": "Público Externo"}
                ]
            }

            # Append the new collections to the original data list
            if isinstance(data, list):
                data.append(resources_collection)
                data.append(target_public_collection)
            else:
                # If the returned data is not a list, wrap it in a list first
                data = [data, resources_collection, target_public_collection]

            if data:
                return jsonify({'types': data}), 200

            AppLogger.log(
                Logmessage.TYPES_NOT_FOUND,
                LogType.INFO,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': "Type not found"}), 404

        except requests.exceptions.RequestException as e:
            return jsonify({'error': 'Failed to fetch data from external API.', 'details': str(e)}), 502
        except ValueError:
            return jsonify({'error': 'Invalid JSON response from external API.'}), 500

    @staticmethod
    @types_bp.route('/all-types', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='all-types', method='GET'))
    def get_all_types():

        types = GraphQlRequestMethods.get_all_types_request()
        if types:
            return jsonify({'types': types}), 200
        AppLogger.log(
            Logmessage.TYPES_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "types not found"}), 404

    @staticmethod
    @types_bp.route('/type-collection', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='type-collection', method='GET'))
    def get_type_by_collection_graphql():

        types = GraphQlRequestMethods.get_specific_type()
        if types:
            return jsonify({'types': types}), 200
        AppLogger.log(
            Logmessage.TYPES_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "types not found"}), 404

    @staticmethod
    @types_bp.route('/types/<string:collection>', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='types', method='GET', resource='collection'))
    def get_type_by_collection(collection: str):
        try:
            url_base = os.getenv('URL_restapi')

            url = f"{url_base}/types/?collection_name={collection}"

            response = requests.get(url, headers=catalog_headers())
            response.raise_for_status()

            data = response.json()
            types = [types_item for item in data for types_item in item.get('types', [])]

            if types:
                return jsonify({'types': types}), 200
            AppLogger.log(
                Logmessage.TYPES_NOT_FOUND,
                LogType.INFO,
                ip_address=request.remote_addr,
            )

            return jsonify({'error': "Type not found"}), 404

        except requests.exceptions.RequestException as e:
            # Handle errors in the external API call
            return jsonify({'error': 'Failed to fetch data from external API.', 'details': str(e)}), 502
        except ValueError:
            # Handle invalid JSON responses
            return jsonify({'error': 'Invalid JSON response from external API.'}), 500


types_routes = TypesRoutes()
