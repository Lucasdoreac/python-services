from __future__ import print_function
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = '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'

api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
    sib_api_v3_sdk.ApiClient(configuration))
subject = "from the Python SDK!"
sender = {"name": "Sendinblue", "email": "contact@sendinblue.com"}
replyTo = {"name": "Sendinblue", "email": "contact@sendinblue.com"}
html_content = "<html><body><h1>This is my first transactional email </h1></body></html>"
to = [{"email": "danrleywillian@gmail.com", "name": "Jane Doe"}]
bcc = ['']
cc = ['']
params = {"parameter": "My param value", "subject": "New Subject"}
send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
    to=to, reply_to=replyTo,  html_content=html_content, sender=sender, subject=subject)

try:
    api_response = api_instance.send_transac_email(send_smtp_email)
    print(api_response)
except ApiException as e:
    print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)
