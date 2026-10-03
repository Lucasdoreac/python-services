from __future__ import print_function
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from dotenv import load_dotenv

load_dotenv()


class SendBlue:
    def __init__(self) -> None:
        self.api_secret = os.getenv("APIKEYSECRET")
        self.smtp_password = os.getenv("SMTPPASSWORD")
        self.email = os.getenv("EMAIL")
        self.smtp_port = os.getenv("SMTPPORT")
        self.smtp_server = os.getenv("SMTPSERVER")
        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key["api-key"] = self.api_secret

    def send_auth_mail(self, email, nome, hashAuth=None):
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(self.configuration)
        )
        subject = "Autorização para logar na aplicação de eventos da UDF"
        sender = {"name": "LabTech", "email": "dw@danrleypereira.com.br"}
        replyTo = {"name": "LabTech", "email": "dw@danrleypereira.com.br"}
        html_content = """<html> <body><h1>Por favor clique no link abaixo para poder logar na aplicação de eventos da UDF</h1> <div><!--[if mso]> <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="http://{0}?auth={1}" style="height:53px;v-text-anchor:middle;width:200px;" arcsize="0%" stroke="f" fill="t"> <v:fill type="tile" src=""https://imgur.com/5BIp9d0.gif"" color="#49a9ce"/> <w:anchorlock/> <center style="color:#ffffff;font-family:sans-serif;font-size:13px;font-weight:bold;">Show me the button!</center> </v:roundrect><![endif]--><a href="http://{0}?auth={1}"style="background-color:#49a9ce;background-image:url("https://imgur.com/5BIp9d0.gif");border-radius:px;color:#ffffff;display:inline-block;font-family:sans-serif;font-size:13px;font-weight:bold;line-height:53px;text-align:center;text-decoration:none;width:200px;-webkit-text-size-adjust:none;mso-hide:all;">Logar!</a></div></body> </html>""".format(
            os.getenv("REACT"), hashAuth
        )
        to = [{"email": email, "name": nome}]
        params = {"parameter": "My param value", "subject": "New Subject"}
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            reply_to=replyTo,
            html_content=html_content,
            sender=sender,
            subject=subject,
        )

        try:
            api_response = api_instance.send_transac_email(send_smtp_email)
            print(api_response)
        except ApiException as e:
            print("Exception when calling SMTPApi->send_transac_email: %s" % type(e).__name__)
            raise Exception(
                "Exception when calling SMTPApi->send_transac_email: %s" % type(e).__name__
            )
