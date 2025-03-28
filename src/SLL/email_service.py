import os
import requests


def send_magic_link(email, username, magic_link):
    """ Sends a magic link email via the cloud function. """
    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send-email"
    payload = {
        'subject': 'Login Authorization',
        'content': f"Hello {username}, use this link to login: {magic_link}",
        'to': [email],
        'is_html': False
    }
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json=payload, headers=headers)
    return response
