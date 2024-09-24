from flask import Blueprint, jsonify, request
from flasgger import swag_from

from BLL import FlowController
from .open_api import get_swagger_specification

events_bp = Blueprint('events', __name__)


class EventsRoutes:
    @staticmethod
    @events_bp.route('/events', methods=['POST'])
    @swag_from({
        "summary": "Registrar um novo evento",
        "description": "Endpoint para registrar um novo evento com as informações fornecidas no corpo da requisição.",
        "consumes": [
            "application/json"
        ],
        "parameters": [
            {
                "in": "body",
                "name": "event",
                "description": "Dados do novo evento",
                "required": True,
                "schema": {
                    "type": "object",
                    "required": [
                        "name",
                        "organizer",
                        "eventTypeId",
                        "odsTypeId",
                        "subscriptionLink",
                        "description",
                        "graduationId",
                        "targetPublic",
                        "resources",
                        "expectedSubscribers",
                        "studentsMonitors",
                        "eventLogo"
                    ],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nome do evento",
                            "example": "Event name"
                        },
                        "organizer": {
                            "type": "object",
                            "properties": {
                                "email": {
                                    "type": "string",
                                    "description": "Email do organizador",
                                    "example": "guilherme.amaral2004@gmail.com"
                                },
                                "id": {
                                    "type": "integer",
                                    "description": "ID do organizador",
                                    "example": 999865850
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Nome do organizador",
                                    "example": "guilherme"
                                }
                            }
                        },
                        "eventTypeId": {
                            "type": "string",
                            "description": "ID do tipo de evento",
                            "example": "eventTypeId"
                        },
                        "odsTypeId": {
                            "type": "string",
                            "description": "ID do tipo de ODS",
                            "example": "odsTypeId"
                        },
                        "subscriptionLink": {
                            "type": "string",
                            "description": "Link para inscrição",
                            "example": "subscriptionLink"
                        },
                        "description": {
                            "type": "string",
                            "description": "Descrição do evento",
                            "example": "description"
                        },
                        "graduationId": {
                            "type": "string",
                            "description": "ID da graduação",
                            "example": "graduationId"
                        },
                        "targetPublic": {
                            "type": "string",
                            "description": "Público alvo do evento",
                            "example": "targetPublic"
                        },
                        "resources": {
                            "type": "string",
                            "description": "Recursos necessários para o evento",
                            "example": "resources"
                        },
                        "expectedSubscribers": {
                            "type": "string",
                            "description": "Número esperado de inscritos",
                            "example": "expectedSubscribers"
                        },
                        "roomType": {
                            "type": "array",
                            "description": "Tipos de salas disponíveis para o evento",
                            "items": {
                                "type": "string",
                                "example": "roomType"
                            }
                        },
                        "entrepreneuralPath": {
                            "type": "string",
                            "description": "Caminho empreendedor relacionado ao evento",
                            "example": "entrepreneuralPath"
                        },
                        "extensionProject": {
                            "type": "string",
                            "description": "Projeto de extensão relacionado ao evento",
                            "example": "extensionProject"
                        },
                        "studentsMonitors": {
                            "type": "array",
                            "description": "IDs dos monitores estudantes do evento",
                            "items": {
                                "type": "integer",
                                "example": 31891942
                            }
                        },
                        "eventLogo": {
                            "type": "string",
                            "description": "Logo do evento",
                            "example": "eventLogo"
                        }
                    }
                }
            }
        ],
        "responses": {
            "201": {
                "description": "Evento criado com sucesso",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Mensagem de confirmação",
                            "example": "Evento registrado com sucesso!"
                        }
                    }
                }
            },
            "400": {
                "description": "Erro de validação ou dados faltando",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Mensagem de erro",
                            "example": "Missing date"
                        }
                    }
                }
            }
        }
    })
    # @swag_from(get_swagger_specification('/events', 'POST'))
    def post_event():
        # Getting the json data from the request
        data = request.json
        if not data:
            return jsonify({'error': 'Missing date'}), 400
        return FlowController.register_event_from_json(data)

    @staticmethod
    @events_bp.route('/events', methods=['GET'])
    @swag_from({
        "summary": "Obter todos os eventos",
        "description": "Endpoint para recuperar todos os eventos registrados.",
        "operationId": "getAllEvents",
        "produces": [
            "application/json"
        ],
        "responses": {
            "200": {
                "description": "Lista de eventos retornada com sucesso",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "_id": {
                                "type": "string",
                                "description": "ID do evento",
                                "example": "66237a7e9407655e516eea70"
                            },
                            "name": {
                                "type": "string",
                                "description": "Nome do evento",
                                "example": "Event name"
                            },
                            "description": {
                                "type": "string",
                                "description": "Descrição do evento",
                                "example": "description"
                            },
                            "entrepreneuralPath": {
                                "type": "string",
                                "description": "Caminho empreendedor relacionado ao evento",
                                "example": "entrepreneuralPath"
                            },
                            "eventLogo": {
                                "type": "string",
                                "description": "Logo do evento",
                                "example": "eventLogo"
                            },
                            "eventTypeId": {
                                "type": "string",
                                "description": "ID do tipo de evento",
                                "example": "eventTypeId"
                            },
                            "expectedSubscribers": {
                                "type": "string",
                                "description": "Número esperado de inscritos",
                                "example": "expectedSubscribers"
                            },
                            "extensionProject": {
                                "type": "string",
                                "description": "Projeto de extensão relacionado ao evento",
                                "example": "extensionProject"
                            },
                            "graduationId": {
                                "type": "string",
                                "description": "ID da graduação",
                                "example": "graduationId"
                            },
                            "odsTypeId": {
                                "type": "string",
                                "description": "ID do tipo de ODS",
                                "example": "odsTypeId"
                            },
                            "organizer": {
                                "type": "object",
                                "properties": {
                                    "email": {
                                        "type": "string",
                                        "description": "Email do organizador",
                                        "example": "guilherme.amaral2004@gmail.com"
                                    },
                                    "id": {
                                        "type": "integer",
                                        "description": "ID do organizador",
                                        "example": 999865850
                                    },
                                    "name": {
                                        "type": "string",
                                        "description": "Nome do organizador",
                                        "example": "guilherme"
                                    }
                                }
                            },
                            "resources": {
                                "type": "string",
                                "description": "Recursos necessários para o evento",
                                "example": "resources"
                            },
                            "roomType": {
                                "type": "array",
                                "description": "Tipos de salas disponíveis para o evento",
                                "items": {
                                    "type": "string",
                                    "example": "roomType"
                                }
                            },
                            "studentsMonitors": {
                                "type": "array",
                                "description": "IDs dos monitores estudantes do evento",
                                "items": {
                                    "type": "integer",
                                    "example": 31891942
                                }
                            },
                            "subscriptionLink": {
                                "type": "string",
                                "description": "Link para inscrição",
                                "example": "subscriptionLink"
                            },
                            "targetPublic": {
                                "type": "string",
                                "description": "Público alvo do evento",
                                "example": "targetPublic"
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
    # @swag_from(get_swagger_specification('/events', 'GET'))
    def get_events():
        return FlowController.find_all_events()


events_routes = EventsRoutes()
