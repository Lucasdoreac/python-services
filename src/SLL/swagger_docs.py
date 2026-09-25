def get_swagger_specification(path, method=None, resource=None):
    if path == '/health':
        return {
            "summary": "Health Check",
            "description": "Saúde da nossa aplicação",
            "tags": ["Health Check"],
            "responses": {
                "200": {
                    "description": "Sucesso",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "boolean",
                                "example": True
                            }
                        }
                    }
                }
            }
        }

    if path == 'events':
        if method == "POST":
            return {
                "summary": "Registrar um novo evento",
                "description": "Endpoint para registrar um novo evento com as informações fornecidas no corpo da requisição.",
                "tags": ["Events"],
                "operationId": "postEvents",
                "consumes": [
                    "application/json"
                ],
                "parameters": [
                    {
                        "name": "x-api-key",
                        "in": "header",
                        "type": "string",
                        "required": True,
                        "description": "Chave de API para autenticação"
                    },
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
                    "403": {
                        "description": "Erro de autenticação da api key",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Invalid or missing credentials"
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
            }

        if method == 'SUBMIT':
            return {
                "summary": "Enviar evento para aprovação reservando a sala",
                "description": "Reserva a sala e envia o evento (status requested) numa requisição só. "
                               "Se o evento não gravar, a reserva criada é desfeita; se o próprio evento "
                               "já tem a reserva (tentativa anterior), ela é reaproveitada.",
                "tags": ["Events"],
                "operationId": "submitEvent",
                "parameters": [{"name": "event_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {
                    "type": "object",
                    "required": ["roomId", "reservationDate"],
                    "properties": {
                        "roomId": {"type": "string"},
                        "reservationDate": {"type": "string", "example": "2026-10-01T10:00:00.000Z"},
                    },
                    "additionalProperties": True,
                }}}},
                "responses": {
                    "200": {"description": "Evento enviado; corpo {eventId}"},
                    "400": {"description": "Faltou roomId/reservationDate ou data inválida"},
                    "409": {"description": "Sala ocupada por outro evento; nada foi gravado"},
                    "500": {"description": "Evento não gravou; a reserva criada foi desfeita"},
                },
            }

        if method == 'GET':
            return {
                "summary": "Obter todos os eventos",
                "description": "Endpoint para recuperar todos os eventos registrados.",
                "tags": ["Events"],
                "operationId": "getAllEvents",
                "produces": [
                    "application/json"
                ],
                "parameters": [
                    {
                        "name": "x-api-key",
                        "in": "header",
                        "type": "string",
                        "required": True,
                        "description": "Chave de API para autenticação"
                    }],
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
                    "403": {
                        "description": "Erro de autenticação da api key",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Invalid or missing credentials"
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
            }

    if path == 'auth':
        if method == 'POST':
            return {
                "summary": "Enviar link de autenticação",
                "description": "Endpoint para enviar um link de autenticação para o email fornecido, apenas emails do domínio '@udf.edu.br' são permitidos.",
                "tags": ["Auth"],
                "operationId": "sendMagicLink",
                "parameters": [
                    {
                        "name": "email",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "O email para o qual o link de autenticação será enviado.",
                        "example": "usuario@udf.edu.br"
                    }
                ],
                "responses": {
                    "201": {
                        "description": "Link de autenticação enviado com sucesso",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "Mensagem de confirmação",
                                    "example": "Magic link sent successfully"
                                },
                                "magic_link": {
                                    "type": "string",
                                    "description": "Link mágico para autenticação",
                                    "example": "http://127.0.0.1:5000/auth/callback?email=usuario@udf.edu.br&hash=hash_auth"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Erro de validação de email",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Invalid email domain"
                                }
                            }
                        }
                    },
                    "503": {
                        "description": "Serviço de envio de email indisponível",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Email sender service unavailable: failed to send email"
                                }
                            }
                        }
                    }
                }
            }

        if method == 'GET':
            return {
                "summary": "Validar hash de autenticação",
                "description": "Endpoint para validar o hash de autenticação enviado para o email.",
                "tags": ["Auth"],
                "operationId": "getMagicLink",
                "parameters": [
                    {
                        "name": "token",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Client token para autenticação.",
                        "example": "hash_auth"
                    },
                    {
                        "name": "email",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "O email associado ao token de autenticação.",
                        "example": "usuario@udf.edu.br"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Hash validado com sucesso",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "valid": {
                                    "type": "boolean",
                                    "description": "Indica se o hash é válido ou não.",
                                    "example": True
                                }
                            }
                        }
                    },
                    "403": {
                        "description": "Erro de autenticação da api key",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Invalid or missing credentials"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Erro de validação de dados",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Invalid token or email"
                                }
                            }
                        }
                    }
                }
            }

    if path == 'reservations':
        if method == 'POST':
            return {
                "summary": "Criar uma nova reserva de sala",
                "description": "Endpoint para criar uma nova reserva para uma sala específica.",
                "tags": ["Reservations"],
                "operationId": "createRoomReservation",
                "parameters": [
                    {
                        "name": "token",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Client token para autenticação.",
                        "example": "hash_auth"
                    },
                    {
                        "name": "email",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "O email associado ao token de autenticação.",
                        "example": "usuario@udf.edu.br"
                    },
                    {
                        "name": "Parâmetros",
                        "description": "Parâmetros para efetuar a reserva",
                        "in": "body",
                        "required": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "room_id": {
                                    "type": "string",
                                    "description": "ID da sala a ser reservada",
                                    "example": "661945b2e764a62988bbcf3e"
                                },
                                "course_id": {
                                    "type": "string",
                                    "description": "ID do curso associado à reserva",
                                    "example": "66193fb3e764a62988bbcf32"
                                },
                                "date": {
                                    "type": "string",
                                    "format": "date",
                                    "description": "Data da reserva no formato AAAA-MM-DD",
                                    "example": "2024-09-25"
                                },
                                "start_time": {
                                    "type": "string",
                                    "format": "time",
                                    "description": "Hora de início da reserva no formato HH:MM:SS",
                                    "example": "19:00:00"
                                },
                                "end_time": {
                                    "type": "string",
                                    "format": "time",
                                    "description": "Hora de término da reserva no formato HH:MM:SS",
                                    "example": "21:00:00"
                                }
                            },
                            "required": ["room_id", "course_id", "date", "start_time", "end_time"]
                        }
                    }
                ],
                "produces": [
                    "application/json"
                ],
                "responses": {
                    "201":
                        {
                            "description": "Criação da reserva",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "success": {
                                        "type": "string",
                                        "description": "Reserva criada com sucesso",
                                        "example": "Reservation attempted"
                                    }
                                }
                            }
                        }

                },
                "403": {
                    "description": "Erro de autenticação de Client token",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "string",
                                "description": "Mensagem de erro",
                                "example": "Invalid or missing credentials"
                            }
                        }
                    }
                },
                "404": {
                    "description": "Erro ao criar reserva",
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

        if method == 'GET':
            if resource == 'date':
                return {
                    "summary": "Obter tipos por coleção específica",
                    "description": "Endpoint para recuperar os tipos de uma coleção específica, como 'rooms' ou 'ODS'.",
                    "tags": ["Reservations"],
                    "operationId": "getTypeByCollection",
                    "parameters": [
                        {
                            "name": "token",
                            "in": "query",
                            "type": "string",
                            "required": True,
                            "description": "Client token para autenticação.",
                            "example": "hash_auth"
                        },
                        {
                            "name": "email",
                            "in": "query",
                            "type": "string",
                            "required": True,
                            "description": "O email associado ao token de autenticação.",
                            "example": "usuario@udf.edu.br"
                        },
                        {
                            "name": "date",
                            "in": "path",
                            "description": "Data da reserva para obter as reservas cadastradas (YYYY-MM-DD).",
                            "required": True,
                            "type": "string",
                            "example": "2024-09-25"
                        }
                    ],
                    "produces": [
                        "application/json"
                    ],
                    "responses": {
                        "200": {
                            "description": "Lista de reservas retornada com sucesso",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "reservations": {
                                        "type": "array",
                                        "description": "Lista de reservas",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "_id": {
                                                    "type": "string",
                                                    "description": "ID da reserva",
                                                    "example": "66ef510f8a61a9f9e6f0c485"
                                                },
                                                "courseId": {
                                                    "type": "string",
                                                    "description": "ID do curso associado à reserva",
                                                    "example": "66193fb3e764a62988bbcf32"
                                                },
                                                "endAt": {
                                                    "type": "string",
                                                    "format": "date-time",
                                                    "description": "Data e hora de término da reserva (formato ISO 8601)",
                                                    "example": "Wed, 25 Sep 2024 21:00:00 GMT"
                                                },
                                                "roomId": {
                                                    "type": "string",
                                                    "description": "ID da sala reservada",
                                                    "example": "661945b2e764a62988bbcf3e"
                                                },
                                                "startAt": {
                                                    "type": "string",
                                                    "format": "date-time",
                                                    "description": "Data e hora de início da reserva (formato ISO 8601)",
                                                    "example": "Wed, 25 Sep 2024 19:00:00 GMT"
                                                }
                                            },
                                            "required": ["_id", "courseId", "endAt", "roomId", "startAt"]
                                        }
                                    }
                                },
                                "required": ["reservation"]
                            }
                        },
                        "403": {
                            "description": "Erro de autenticação de Client token",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {
                                        "type": "string",
                                        "description": "Mensagem de erro",
                                        "example": "Invalid or missing credentials"
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "Reserva não encontrada",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {
                                        "type": "string",
                                        "description": "Mensagem de erro",
                                        "example": "Reservation not found"
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
                }

    if path == 'buildings':
        if method == 'GET':
            return {
                "summary": "Obter todos os edifícios.",
                "description": "Endpoint para recuperar todos os edifícios.",
                "tags": ["Resources"],
                "operationId": "getAllBuildings",
                "produces": [
                    "application/json"
                ],
                "parameters": [
                    {
                        "name": "x-api-key",
                        "in": "header",
                        "type": "string",
                        "required": True,
                        "description": "Chave de API para autenticação"
                    },
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
                    "403": {
                        "description": "Erro de autenticação da api key",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Invalid or missing credentials"
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
            }

    if path == 'rooms/all-rooms':
        if method == 'GET':
            return {
                "summary": "Obter todas as salas.",
                "description": "Endpoint para recuperar todas as salas disponíveis.",
                "tags": ["Resources"],
                "operationId": "getAllRooms",
                "produces": [
                    "application/json"
                ],
                "parameters": [
                    {
                        "name": "email",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "O email associado ao token de autenticação.",
                        "example": "usuario@udf.edu.br"
                    },
                    {
                        "name": "token",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Client token para autenticação.",
                        "example": "hash_auth"
                    },
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
                                            "campus": {
                                                "type": "object",
                                                "description": "edifício associado à sala",
                                                "properties": {
                                                    "id": {
                                                        "type": "string",
                                                        "description": "ID do campus",
                                                        "example": "31d5d343-df75-4b65-b5a9-5151d886a509"
                                                    },
                                                    "name": {
                                                        "type": "string",
                                                        "description": "Nome do campus",
                                                        "example": "EDIFÍCIO REZENDE R. DE REZENDE"
                                                    }
                                                },
                                            },
                                            "name": {
                                                "type": "string",
                                                "description": "Nome da sala",
                                                "example": "ARQ I"
                                            },
                                        },
                                        "required": ["_id", "name"]
                                    }
                                }
                            }
                        }
                    },
                    "403": {
                        "description": "Erro de autenticação da api key",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Invalid or missing credentials"
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
            }

    if path == 'rooms/available-rooms':
        return {
            "summary": "Obter salas disponíveis.",
            "description": "Endpoint para recuperar salas disponíveis com base na data e horário especificados.",
            "tags": ["Resources"],
            "operationId": "get_available_rooms",
            "produces": [
                "application/json"
            ],
            "parameters": [
                {
                    "name": "email",
                    "in": "header",
                    "type": "string",
                    "required": True,
                    "description": "e-mail autenticado"
                },
                {
                    "name": "token",
                    "in": "header",
                    "type": "string",
                    "required": True,
                    "description": "token ativo"
                },
                {
                    "name": "date",
                    "in": "query",
                    "type": "string",
                    "required": True,
                    "description": "Data para filtrar as salas disponíveis (formato: YYYY-MM-DD)"
                },
                {
                    "name": "time",
                    "in": "query",
                    "type": "string",
                    "required": True,
                    "description": "Horário para filtrar as salas disponíveis (formato: HH:mm)"
                },
                {
                    "name": "page",
                    "in": "query",
                    "type": "integer",
                    "required": False,
                    "default": 1,
                    "description": "Número da página para paginação"
                },
                {
                    "name": "page_size",
                    "in": "query",
                    "type": "integer",
                    "required": False,
                    "default": 10,
                    "description": "Quantidade de itens por página"
                }
            ],
            "responses": {
                "200": {
                    "description": "Salas disponíveis retornadas com sucesso",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "Lista de salas disponíveis",
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
                                            "example": "Sala 101"
                                        },
                                        "type": {
                                            "type": "integer",
                                            "description": "Tipo da sala (0 para 'online', 1 para laboratório, etc.)",
                                            "example": 0
                                        }
                                    },
                                    "required": ["_id", "name"]
                                }
                            },
                            "pagination": {
                                "type": "object",
                                "description": "Informações de paginação",
                                "properties": {
                                    "page": {
                                        "type": "integer",
                                        "description": "Número atual da página",
                                        "example": 1
                                    },
                                    "page_size": {
                                        "type": "integer",
                                        "description": "Quantidade de itens por página",
                                        "example": 10
                                    },
                                    "total": {
                                        "type": "integer",
                                        "description": "Total de salas disponíveis",
                                        "example": 50
                                    },
                                    "pages": {
                                        "type": "integer",
                                        "description": "Total de páginas",
                                        "example": 5
                                    }
                                }
                            }
                        }
                    }
                },
                "400": {
                    "description": "Parâmetros obrigatórios ausentes",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "string",
                                "description": "Mensagem de erro",
                                "example": "Parâmetros 'date' e 'time' são obrigatórios."
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
        }
        if method == 'GET':
            pass

    if path == 'rooms/search-rooms':
        if method == 'GET':
            return {
                "summary": "Pesquisar salas pelo nome.",
                "description": "Endpoint para recuperar salas que correspondam parcial ou totalmente ao nome informado.",
                "tags": ["Resources"],
                "operationId": "searchRooms",
                "produces": [
                    "application/json"
                ],
                "parameters": [
                    {
                        "name": "email",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "O email associado ao token de autenticação.",
                        "example": "usuario@udf.edu.br"
                    },
                    {
                        "name": "token",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Client token para autenticação.",
                        "example": "hash_auth"
                    },
                    {
                        "name": "name",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Parte ou nome completo da sala para filtro.",
                        "example": "arq"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de salas retornada com sucesso",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "rooms": {
                                    "type": "array",
                                    "description": "Lista de salas encontradas",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "campus": {
                                                "type": "object",
                                                "description": "Edifício associado à sala",
                                                "properties": {
                                                    "name": {
                                                        "type": "string",
                                                        "description": "Nome do campus",
                                                        "example": "EDIFÍCIO REZENDE R. DE REZENDE"
                                                    }
                                                }
                                            },
                                            "id": {
                                                "type": "string",
                                                "description": "ID da sala",
                                                "example": "c0c29f38-6bf3-4538-bf54-4570dc85422c"
                                            },
                                            "name": {
                                                "type": "string",
                                                "description": "Nome da sala",
                                                "example": "ARQ I"
                                            }
                                        },
                                        "required": ["id", "name"]
                                    }
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Nenhuma sala encontrada com o critério especificado",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Room not found by search method"
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
            }

    if path == 'types':
        if method == 'GET':
            if resource is None:
                return {
                    "summary": "Obter todos os tipos de eventos.",
                    "description": "Endpoint para recuperar todos os eventos registrados.",
                    "tags": ["Types"],
                    "operationId": "getAllTypes",
                    "produces": [
                        "application/json"
                    ],
                    "parameters": [
                        {
                            "name": "email",
                            "in": "header",
                            "type": "string",
                            "required": True,
                            "description": "Email do usuário para autenticação.",
                            "example": "usuario@udf.edu.br"
                        },
                        {
                            "name": "token",
                            "in": "header",
                            "type": "string",
                            "required": True,
                            "description": "Token de autenticação do usuário.",
                            "example": "Bearer abcdef12345"
                        },
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
                        "403": {
                            "description": "Erro de autenticação da api key",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {
                                        "type": "string",
                                        "description": "Mensagem de erro",
                                        "example": "Invalid or missing credentials"
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
                        },
                        "502": {
                            "description": "Falha na sincronização de dados com uma API externa",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {
                                        "type": "string",
                                        "description": "Mensagem de erro",
                                        "example": "Failed to fetch data from external API."
                                    }
                                }
                            }
                        },
                    }
                }
    if path == 'courses':
        if method == 'GET':
            return {
                "summary": "Obter cursos",
                "description": "Endpoint para recuperar a lista de cursos disponíveis.",
                "tags": ["Resources"],
                "parameters": [
                    {
                        "name": "email",
                        "in": "header",
                        "type": "string",
                        "required": True,
                        "description": "Email do usuário para autenticação.",
                        "example": "usuario@udf.edu.br"
                    },
                    {
                        "name": "token",
                        "in": "header",
                        "type": "string",
                        "required": True,
                        "description": "Token de autenticação do usuário.",
                        "example": "Bearer abcdef12345"
                    },
                    {
                        "name": "course_name",
                        "in": "query",
                        "type": "string",
                        "description": "Filtrar cursos pelo nome.",
                        "example": "Python Programming"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de cursos retornada com sucesso.",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "courses": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"},
                                            "description": {"type": "string"}
                                        },
                                        "required": ["id", "name"]
                                    }
                                }
                            }
                        }
                    },
                    "401": {
                        "description": "Erro de autenticação de email e/ou token",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Email missing"
                                }
                            }
                        }
                    },
                    "500": {
                        "description": "Resposta de uma API externa com JSON inválido",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Invalid JSON response from external API."
                                }
                            }
                        }
                    },
                    "502": {
                        "description": "Falha na sincronização de dados com uma API externa",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Failed to fetch data from external API."
                                }
                            }
                        }
                    },
                }
            }
    if path == 'disciplines':
        if method == 'GET':
            return {
                "summary": "Obter disciplinas",
                "description": "Endpoint para listar disciplinas disponíveis.",
                "tags": ["Resources"],
                "parameters": [
                    {
                        "name": "email",
                        "in": "header",
                        "type": "string",
                        "required": True,
                        "description": "Email do usuário para autenticação.",
                        "example": "usuario@udf.edu.br"
                    },
                    {
                        "name": "token",
                        "in": "header",
                        "type": "string",
                        "required": True,
                        "description": "Token de autenticação do usuário.",
                        "example": "Bearer abcdef12345"
                    },
                    {
                        "name": "name",
                        "in": "query",
                        "type": "string",
                        "required": False,
                        "description": "Filtrar disciplinas pelo nome.",
                        "example": "SISTEMAS AUTOMOTIVOS"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de disciplinas retornada com sucesso",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "disciplines": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            }
                        }
                    },
                    "401": {
                        "description": "Erro de autenticação de email e/ou token",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Email missing"
                                }
                            }
                        }
                    },
                    "500": {
                        "description": "Resposta de uma API externa com JSON inválido",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Invalid JSON response from external API."
                                }
                            }
                        }
                    },
                    "502": {
                        "description": "Falha na sincronização de dados com uma API externa",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "Failed to fetch data from external API."
                                }
                            }
                        }
                    },
                }
            }
    if path == 'periods':
        if method == 'GET':
            return {
                "summary": "Obter todos os períodos de disponibilidade.",
                "description": "Endpoint para recuperar todos os períodos disponíveis.",
                "tags": ["Resources"],
                "operationId": "get_periods",
                "produces": [
                    "application/json"
                ],
                "parameters": [
                    {
                        "name": "email",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "O e-mail associado ao token de autenticação.",
                        "example": "usuario@udf.edu.br"
                    },
                    {
                        "name": "token",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Client token para autenticação.",
                        "example": "hash_auth"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de períodos retornada com sucesso",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "periods": {
                                    "type": "array",
                                    "description": "Lista de períodos de disponibilidade",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "Nome do período de disponibilidade",
                                                "example": "MANHÃ"
                                            }
                                        },
                                        "required": ["name"]
                                    }
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Nenhum período encontrado",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "periods not found"
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
            }
    if path == 'teachers':
        if method == 'GET':
            return {
                "summary": "Obter professores.",
                "description": "Endpoint para recuperar a lista de professores, com opção de filtrar pelo nome.",
                "tags": ["Resources"],
                "operationId": "getTeachers",
                "produces": [
                    "application/json"
                ],
                "parameters": [
                    {
                        "name": "email",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "O e-mail associado ao token de autenticação.",
                        "example": "usuario@udf.edu.br"
                    },
                    {
                        "name": "token",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Client token para autenticação.",
                        "example": "hash_auth"
                    },
                    {
                        "name": "name",
                        "in": "query",
                        "type": "string",
                        "required": False,
                        "description": "Nome (ou parte do nome) do professor para filtrar.",
                        "example": "PEDRO"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de professores retornada com sucesso",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "teachers": {
                                    "type": "array",
                                    "description": "Lista de professores encontrados",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {
                                                "type": "string",
                                                "description": "ID do professor",
                                                "example": "953b59ac-dff7-4ff0-9eef-ba1fdfeb7e89"
                                            },
                                            "name": {
                                                "type": "string",
                                                "description": "Nome do professor",
                                                "example": "PEDRO AUGUSTO DA SILVA SOARES"
                                            }
                                        },
                                        "required": ["id", "name"]
                                    }
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Nenhum professor encontrado",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro",
                                    "example": "teachers not found"
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
            }
    if path == 'all-types':
        if method == 'GET':
            return {
                "summary": "Obter todos os tipos.",
                "description": "Endpoint para recuperar todos os documentos de tipos no banco de dados.",
                "tags": ["Types"],
                "operationId": "getAllTypes",
                "produces": [
                    "application/json"
                ],
                "parameters": [
                    {
                        "name": "email",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "O email associado ao token de autenticação.",
                        "example": "usuario@udf.edu.br"
                    },
                    {
                        "name": "token",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Client token para autenticação.",
                        "example": "hash_auth"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de tipos retornada com sucesso.",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "types": {
                                    "type": "array",
                                    "description": "Lista dos grupos de tipos.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "collection": {
                                                "type": "string",
                                                "description": "Nome da coleção à qual esses tipos pertencem.",
                                                "example": "rooms"
                                            },
                                            "types": {
                                                "type": "array",
                                                "description": "Lista de tipos relacionados a essa coleção.",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "id": {
                                                            "type": "integer",
                                                            "description": "ID do tipo.",
                                                            "example": 0
                                                        },
                                                        "name": {
                                                            "type": "string",
                                                            "description": "Nome do tipo.",
                                                            "example": "Vídeo Chamada via Zoom ou Google Meet"
                                                        }
                                                    },
                                                    "required": ["id", "name"]
                                                }
                                            }
                                        },
                                        "required": ["collection", "types"]
                                    }
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Nenhum tipo encontrado.",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro.",
                                    "example": "types not found"
                                }
                            }
                        }
                    },
                    "500": {
                        "description": "Erro interno do servidor.",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro.",
                                    "example": "Erro interno do servidor"
                                }
                            }
                        }
                    }
                }
            }
    if path == 'type-collection':
        if method == 'GET':
            return {
                "summary": "Obter tipos por coleção.",
                "description": "Endpoint para recuperar os documentos de tipos associados a uma determinada coleção.",
                "tags": ["Types"],
                "operationId": "getTypeByCollection",
                "produces": [
                    "application/json"
                ],
                "parameters": [
                    {
                        "name": "email",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "O email associado ao token de autenticação.",
                        "example": "usuario@udf.edu.br"
                    },
                    {
                        "name": "token",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Client token para autenticação.",
                        "example": "hash_auth"
                    },
                    {
                        "name": "collection",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "Nome da coleção para filtrar os tipos.",
                        "example": "rooms"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de tipos retornada com sucesso.",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "types": {
                                    "type": "array",
                                    "description": "Lista de tipos da coleção especificada.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {
                                                "type": "integer",
                                                "description": "ID do tipo.",
                                                "example": 0
                                            },
                                            "name": {
                                                "type": "string",
                                                "description": "Nome do tipo.",
                                                "example": "Laboratório de Informática"
                                            }
                                        },
                                        "required": ["id", "name"]
                                    }
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Nenhum tipo encontrado para a coleção especificada.",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro.",
                                    "example": "types not found"
                                }
                            }
                        }
                    },
                    "500": {
                        "description": "Erro interno do servidor.",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Mensagem de erro.",
                                    "example": "Erro interno do servidor"
                                }
                            }
                        }
                    }
                }
            }
