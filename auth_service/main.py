# from sendblue import SendBlue
from SLL_auth import create_app
from configmodule import get_config


class MasterNode(object):
    """
        Classe MasterNode responsável por iniciar e executar a aplicação.

        Esta classe utiliza a função `create_app` para criar a aplicação com base nas configurações
        obtidas através de `get_config`, e inicia o servidor utilizando os parâmetros definidos na configuração.
    """

    def run(self):
        """
                Cria e executa a aplicação.

                Obtém as configurações necessárias, instancia a aplicação e a executa utilizando o host e a porta
                especificados na configuração. Também contém um exemplo comentado de como enviar email via SendBlue.
        """

        app = create_app(get_config())
        app.run(host=app.config['SERVER_HOST'], port=app.config['SERVER_PORT'])
        # send_blue_api = SendBlue()
        # send_blue_api.send_auth_mail(email="danrleywillian@gmail.com", nome="Danrley Pereira")


if __name__ == '__main__':
    MasterNode().run()



