from pymongo import MongoClient


class MongoDBConnectionFactory:
    """
        Fábrica de conexão com o MongoDB que gerencia a criação e o acesso à conexão de forma singleton.

        Esta classe utiliza variáveis estáticas para armazenar a instância do cliente MongoDB e o nome do
        banco de dados, garantindo que a conexão seja inicializada apenas uma vez durante a execução da aplicação.
    """

    _client = None
    _database = None

    @staticmethod
    def get_db():
        """
                Retorna a instância do banco de dados MongoDB configurado.

                Se a conexão não tiver sido inicializada através do método init_app, uma exceção será lançada.

                Returns:
                    Database: Instância do banco de dados MongoDB configurado.

                Raises:
                    Exception: Se a conexão com o MongoDB não tiver sido inicializada.
        """

        if MongoDBConnectionFactory._client is None:
            raise Exception("MongoDBConnectionFactory has not been initialized")
        return MongoDBConnectionFactory._client[MongoDBConnectionFactory._database]

    @staticmethod
    def init_app(uri, database):
        """
                Inicializa a conexão com o MongoDB utilizando a URI e o nome do banco de dados fornecidos.

                Caso a conexão já tenha sido inicializada, o método não realizará nenhuma ação adicional.

                Args:
                    uri (str): URI de conexão do MongoDB.
                    database (str): Nome do banco de dados a ser utilizado.
        """

        print("init app")
        if MongoDBConnectionFactory._client is None:
            MongoDBConnectionFactory._client = MongoClient(uri)
            MongoDBConnectionFactory._database = database
