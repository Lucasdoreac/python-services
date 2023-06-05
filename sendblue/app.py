from flask import Flask, request, jsonify
from datetime import datetime
from hashlib import sha256
from flask_cors import CORS
import requests

import os
from dotenv import load_dotenv

load_dotenv()

from sendblue import SendBlue

app = Flask(__name__)
CORS(app)

@app.route('/auth-mail', methods=['POST'])
def auth_mail():
    email = request.args.get('email')
    if not email.endswith('@udf.edu.br'):
        return jsonify({'error': 'Invalid email domain'}), 400
    
    now = datetime.now()
    hashAuth = sha256(str(now).encode()).hexdigest()
    
    payload = {'email': email, 'hashAuth': hashAuth}
    response = requests.post(f'http://{os.getenv("DAL")}/users', json=payload)
    try:
        send_blue_api = SendBlue()
        send_blue_api.send_auth_mail(email, email.split('@')[0], hashAuth)
    except:
        return jsonify({'error': 'Email sender service unavailable: failed to send email'}), 503

    if response.status_code != 201:
        return jsonify({'error': 'Failed to create user'}), 500
    
    return jsonify({}), 201

# @app.route('/auth-mail', methods=['POST'])
# def auth_mail():
#     email = request.args.get('email')
#     if email is not None:
#         if not email.endswith('@udf.edu.br'):
#             return jsonify({'error': 'Invalid email domain'}), 400
#         # Generate hashAuth using current date object
#         now = str(datetime.datetime.now())
#         hash_object = hashlib.sha256(now.encode())
#         hashAuth = hash_object.hexdigest()

#         # Send POST request to another API
#         data = {
#             "email": email,
#             "hashAuth": hashAuth
#         }
#         response = requests.post('http://localhost:7412/users', json=data)
#         if response.status_code == 200:
#             return "Success"
#         else:
#             return "Error: " + response.content
#     else:
#         return "Error: Email not provided"

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
