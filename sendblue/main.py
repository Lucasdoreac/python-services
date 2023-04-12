from sendblue import SendBlue

class MasterNode(object):
    def run(self):
        send_blue_api = SendBlue()
        send_blue_api.send_auth_mail(email="danrleywillian@gmail.com", nome="Danrley Pereira")

if __name__ == '__main__':
    MasterNode().run()
