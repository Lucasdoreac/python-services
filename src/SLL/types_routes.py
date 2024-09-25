from flask import Blueprint, jsonify, request
from flasgger import swag_from

from BLL import FlowController

types_bp = Blueprint('types', __name__)


class TypesRoutes:
    @staticmethod
    @types_bp.route('/types', methods=['GET'])
    @swag_from({
        "summary": "Obter todos os tipos de eventos.",
        "description": "Endpoint para recuperar todos os eventos registrados.",
        "operationId": "getAllTypes",
        "produces": [
            "application/json"
        ],
        "responses": {
            "200": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "types": {
                            "type": "array",
                            "description": "Lista de coleções com seus respectivos tipos",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "_id": {
                                        "type": "string",
                                        "description": "ID da coleção",
                                        "example": "66199517d85d5425656d0c13"
                                    },
                                    "collection": {
                                        "type": "string",
                                        "description": "Nome da coleção",
                                        "example": "rooms"
                                    },
                                    "types": {
                                        "type": "array",
                                        "description": "Lista de tipos disponíveis na coleção",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {
                                                    "type": "integer",
                                                    "description": "ID do tipo",
                                                    "example": 0
                                                },
                                                "type": {
                                                    "type": "string",
                                                    "description": "Descrição do tipo",
                                                    "example": "online"
                                                },
                                                "nome": {
                                                    "type": "string",
                                                    "description": "Nome do tipo (apenas para coleção ODS)",
                                                    "example": "Educação de qualidade"
                                                }
                                            },
                                            "required": ["id", "type"]
                                        }
                                    }
                                },
                                "required": ["_id", "collection", "types"]
                            }
                        }
                    }
                }
            },
            "404": {
                "description": "Não encontrado",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Mensagem de erro",
                            "example": "There is no such type"
                        }
                    }
                }
            }
        }
    })
    def get_types():
        types_data = FlowController.find_all_types()
        return jsonify({'types': types_data}), 200

    @staticmethod
    @types_bp.route('/types/<string:collection>', methods=['GET'])
    @swag_from({
        "summary": "Obter tipos por coleção específica",
        "description": "Endpoint para recuperar os tipos de uma coleção específica, como 'rooms' ou 'ODS'.",
        "operationId": "getTypeByCollection",
        "parameters": [
            {
                "name": "collection",
                "in": "path",
                "description": "Nome da coleção para obter os tipos (e.g., rooms, ODS, events).",
                "required": True,
                "type": "string",
                "example": "ODS"
            }
        ],
        "produces": [
            "application/json"
        ],
        "responses": {
            "200": {
                "description": "Tipos retornados com sucesso",
                "schema": {
                    "type": "object",
                    "properties": {
                        "_id": {
                            "type": "string",
                            "description": "ID da coleção",
                            "example": "66199c62d85d5425656d0c18"
                        },
                        "collection": {
                            "type": "string",
                            "description": "Nome da coleção",
                            "example": "ODS"
                        },
                        "types": {
                            "type": "array",
                            "description": "Lista de tipos disponíveis na coleção",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "ID do tipo",
                                        "example": 1
                                    },
                                    "nome": {
                                        "type": "string",
                                        "description": "Nome do tipo",
                                        "example": "Erradicação da pobreza"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Descrição do tipo",
                                        "example": "EDP"
                                    }
                                },
                                "required": ["id", "type"]
                            }
                        }
                    },
                    "required": ["_id", "collection", "types"]
                }
            },
            "404": {
                "description": "Coleção não encontrada",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Mensagem de erro",
                            "example": "Collection not found"
                        }
                    }
                }
            },
            "500": {
                "description": "Erro interno do servidor",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Mensagem de erro",
                            "example": "Internal server error"
                        }
                    }
                }
            }
        }
    })
    def get_type_by_collection(collection: str):
        return FlowController.find_type_by_collection(collection)


types_routes = TypesRoutes()
