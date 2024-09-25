from flask import Blueprint, jsonify, request
from flasgger import swag_from

from BLL import FlowController

resources_bp = Blueprint('resources', __name__)


class ResourcesRoutes:

    @staticmethod
    @resources_bp.route('/buildings', methods=['GET'])
    @swag_from({
        "summary": "Obter todos os edifícios.",
        "description": "Endpoint para recuperar todos os edifícios.",
        "operationId": "getAllBuildings",
        "produces": [
            "application/json"
        ],
        "responses": {
            "200": {
                "description": "Lista dos edifícios retornada com sucesso",
                "schema": {
                    "type": "object",
                    "properties": {
                        "buildings": {
                            "type": "array",
                            "description": "Lista de edifícios disponíveis",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "_id": {
                                        "type": "string",
                                        "description": "ID do edifício",
                                        "example": "6619442be764a62988bbcf39"
                                    },
                                    "acronym": {
                                        "type": "string",
                                        "description": "Acrônimo do edifício",
                                        "example": "4R"
                                    },
                                    "address": {
                                        "type": "string",
                                        "description": "Endereço do edifício",
                                        "example": "SGAS I SGAS 903 - Brasília, DF, 70297-400"
                                    },
                                    "closeAt": {
                                        "type": "string",
                                        "description": "Horário de encerramento",
                                        "example": "09:00:00 PM"
                                    },
                                    "mapsLink": {
                                        "type": "string",
                                        "description": "Link no mapa",
                                        "example": "https://goo.gl/maps/Ln1oosDiNNL4Lzxb6"
                                    },
                                    "name": {
                                        "type": "string",
                                        "description": "Nome do edifício",
                                        "example": "Reitor Rezende - 4R"
                                    },
                                    "openAt": {
                                        "type": "string",
                                        "description": "Horário de abertura",
                                        "example": "08:00:00 AM"
                                    }
                                }
                            }
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
                            "example": "Erro interno do servidor"
                        }
                    }
                }
            }

        }
    })
    def get_buildings():
        buildings = FlowController.find_all_buildings()
        return jsonify({'buildings': buildings}), 200

    @staticmethod
    @resources_bp.route('/rooms', methods=['GET'])
    @swag_from({
        "summary": "Obter todas as salas.",
        "description": "Endpoint para recuperar todas as salas disponíveis.",
        "operationId": "getAllRooms",
        "produces": [
            "application/json"
        ],
        "responses": {
            "200": {
                "description": "Lista de salas retornada com sucesso",
                "schema": {
                    "type": "object",
                    "properties": {
                        "rooms": {
                            "type": "array",
                            "description": "Lista de todas as salas",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "_id": {
                                        "type": "string",
                                        "description": "ID da sala",
                                        "example": "661945b2e764a62988bbcf3d"
                                    },
                                    "name": {
                                        "type": "string",
                                        "description": "Nome da sala",
                                        "example": "Sala Online"
                                    },
                                    "type": {
                                        "type": "integer",
                                        "description": "Tipo da sala (0 para 'online', 1 para laboratório, etc.)",
                                        "example": 0
                                    },
                                    "buildingId": {
                                        "type": "string",
                                        "description": "ID do edifício onde a sala está localizada",
                                        "example": "6619442be764a62988bbcf39"
                                    },
                                    "floor": {
                                        "type": "string",
                                        "description": "Andar onde a sala está localizada",
                                        "example": "Terreo"
                                    },
                                    "roomNumber": {
                                        "type": "string",
                                        "description": "Número da sala",
                                        "example": "19"
                                    },
                                    "studentsCapacity": {
                                        "type": "integer",
                                        "description": "Capacidade de estudantes que a sala suporta",
                                        "example": 12
                                    },
                                    "studentCapacity": {
                                        "type": "integer",
                                        "description": "Capacidade de estudantes (pode ser um erro no nome do campo)",
                                        "example": 35
                                    },
                                    "id": {
                                        "type": "string",
                                        "description": "Identificador adicional para a sala",
                                        "example": "878979123423"
                                    }
                                },
                                "required": ["_id", "name"]
                            }
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
                            "example": "Erro interno do servidor"
                        }
                    }
                }
            }
        }
    })
    def get_rooms():
        rooms = FlowController.find_all_rooms()
        return jsonify({'rooms': rooms}), 200


resources_routes = ResourcesRoutes()
