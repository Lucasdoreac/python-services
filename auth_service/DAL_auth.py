from datetime import datetime,timedelta
from auth_service.BaseRepository import BaseRepository


class AuthenticationRepository(BaseRepository):
    """
        Repositório responsável por gerenciar as operações de autenticação no banco de dados.

        Este repositório utiliza a coleção 'authentications' para armazenar os registros de autenticação,
        e implementa métodos para inserir e validar esses registros.
    """


    def get_collection_name(self):
        """
                Retorna a coleção do MongoDB utilizada para armazenar os registros de autenticação.

                Returns:
                    Collection: A coleção 'authentications' do banco de dados.
        """

        return self.db.authentications

    def insert_authentication(self, email, token, expires_at):
        """
                Insere um novo registro de autenticação no banco de dados.

                Cria um documento contendo o email, o token (hash) e a data de expiração, e insere-o na coleção.

                Args:
                    email (str): Email do usuário.
                    token (str): Token (hash) de autenticação.
                    expires_at (datetime): Data e hora de expiração do token.

                Returns:
                    ObjectId: O identificador do documento inserido.
        """

        record = {
            "email": email,
            "hash": token,
            "expiresAt": expires_at
        }
        return self.get_collection_name().insert_one(record).inserted_id

    def validate_authentication(self, email, token):
        """
                Verifica se existe um registro de autenticação que corresponda ao email e token fornecidos e que não esteja expirado.

                Compara o token e o email informados com os registros da coleção, garantindo que a data de expiração seja maior que o horário atual.

                Args:
                    email (str): Email do usuário.
                    token (str): Token (hash) de autenticação.

                Returns:
                    bool: True se um registro válido for encontrado, caso contrário False.
        """

        current_time = datetime.now()
        query = {
            "email": email,
            "hash": token,
            "expiresAt": {"$gt": current_time}
        }
        return self.get_collection_name().find_one(query) is not None





