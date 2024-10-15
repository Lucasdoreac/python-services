def get_swagger_specification(path, method = None):
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

