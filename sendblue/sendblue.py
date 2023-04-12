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

    def send_auth_mail(self, email, nome):
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(self.configuration)
        )
        subject = "Autorização para logar na aplicação de eventos da UDF"
        sender = {"name": "LabTech", "email": "dw@danrleypereira.com.br"}
        replyTo = {"name": "LabTech", "email": "dw@danrleypereira.com.br"}
        html_content = (
            "<html><body><h1>Por favor clique no link abaixo para poder logar na aplicação de eventos da UDF</h1></body></html>"
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
            print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)
