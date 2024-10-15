# from sendblue import SendBlue
from SLL_auth import create_app
from configmodule import get_config


class MasterNode(object):
    def run(self):
        app = create_app(get_config())
        app.run(host=app.config['SERVER_HOST'], port=app.config['SERVER_PORT'])
        # send_blue_api = SendBlue()
        # send_blue_api.send_auth_mail(email="danrleywillian@gmail.com", nome="Danrley Pereira")


if __name__ == '__main__':
    MasterNode().run()



