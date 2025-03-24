from datetime import datetime,timedelta
from auth_service.DAL_auth import AuthenticationRepository
from hashlib import sha256

class AuthenticationController:
    """
       Controller responsável pela lógica de autenticação e gerenciamento de tokens.

       Implementa o padrão Singleton para garantir que apenas uma instância seja utilizada em toda a aplicação.
       Utiliza o repositório de autenticação para validar, inserir tokens e gerar hashes únicos.
    """

    _authentication_instance = None

    def __new__(cls, *args, **kwargs):
        """
                Garante que apenas uma instância da classe seja criada (padrão Singleton).

                Returns:
                    AuthenticationController: Instância única da classe.
        """

        if cls._authentication_instance is None:
            cls._authentication_instance = super(AuthenticationController, cls).__new__(cls)
        return cls._authentication_instance

    def __init__(self):
        """
                Inicializa o AuthenticationController instanciando o repositório de autenticação.
        """

        self.tokens_repository = AuthenticationRepository()

    def is_token_valid(self, token: str, email: str) -> bool:
        """
               Verifica se o token associado ao email é válido.

               Args:
                   token (str): Token a ser validado.
                   email (str): Email associado ao token.

               Returns:
                   bool: True se o token for válido, False caso contrário.
        """

        return self.tokens_repository.validate_authentication(email, token)

    def insert_token(self, email: str, token: str) -> str:
        """
               Insere um novo token para o email fornecido, definindo sua expiração para 1 dia a partir do momento da inserção.

               Args:
                   email (str): Email para o qual o token será inserido.
                   token (str): Token a ser inserido.

               Returns:
                   str: Resultado ou identificador retornado pelo repositório após a inserção do token.
        """

        expires_at = datetime.now() + timedelta(days=1)
        return self.tokens_repository.insert_authentication(email, token, expires_at)

    @property
    def generate_hash(self) -> str:
        """
                Gera um hash único utilizando o timestamp atual e o algoritmo SHA256.

                Returns:
                    str: Hash gerado a partir da data e hora atual.
        """

        now = datetime.now()
        return sha256(str(now).encode()).hexdigest()


