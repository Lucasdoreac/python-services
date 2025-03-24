from abc import ABC,abstractmethod
from bson import ObjectId
from auth_service.mongo import MongoDBConnectionFactory


class BaseRepository(ABC):
    def __init__(self):

        """
               Inicializa a conexão com o banco de dados e define a coleção de tipos.

               Atributos:
                   db: Instância do banco de dados obtida através do MongoDBConnectionFactory.
                   types_collection: Coleção 'types' presente no banco de dados.
        """

        self.db = MongoDBConnectionFactory.get_db()
        self.types_collection = self.db.types
        # self.collection = self.db[self.get_collection_name()]

    @abstractmethod
    def get_collection_name(self):

        """
                Retorna a coleção específica utilizada pelo repositório.

                Esse método deve ser implementado por classes que herdam de BaseRepository,
                retornando a coleção do MongoDB que será utilizada para as operações.

                Returns:
                    Collection: A coleção do MongoDB a ser utilizada.
        """

        pass

    def find_all(self):

        """
                Recupera todos os documentos da coleção e converte os ObjectId para string.

                Retorna uma lista com todos os documentos encontrados na coleção definida,
                garantindo que os campos ObjectId sejam convertidos para string para facilitar a serialização JSON.

                Returns:
                    list: Lista de documentos com os ObjectId convertidos para string.
        """

        return self.convert_id(list(self.get_collection_name().find({})))

    def find_by_id(self, _id):

        """
                Busca um documento na coleção utilizando o _id informado.

                Converte o _id recebido para ObjectId e procura o documento correspondente na coleção.
                Em seguida, converte os ObjectId dos campos para string.

                Args:
                    _id (str): Identificador do documento a ser buscado.

                Returns:
                    dict: Documento encontrado com os ObjectId convertidos para string, ou None se não for encontrado.
        """

        result = self.get_collection_name().find_one({'_id': ObjectId(_id)})
        return self.convert_id(result)

    @staticmethod
    def convert_id(data):

        """
               Converte os campos do tipo ObjectId para string para facilitar a serialização JSON.

               Se o dado for uma lista, aplica a conversão para cada documento da lista.
               Se for um dicionário, converte diretamente os ObjectId contidos nele.

               Args:
                   data (list or dict): Documento(s) a ser(em) convertido(s).

               Returns:
                   list or dict: Documento(s) com os ObjectId convertidos para string.
               """

        def convert(document):
            for key, value in document.items():
                if isinstance(value, ObjectId):
                    document[key] = str(value)
            return document

        if isinstance(data, list):
            return [convert(doc) for doc in data]
        elif isinstance(data, dict):
            return convert(data)
        return data