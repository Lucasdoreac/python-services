import os
from datetime import datetime
from hashlib import sha256
from flask import Flask, jsonify, request
from flask_cors import CORS

from configmodule import get_config
from SLL.email_service import send_magic_link


# App Factory
def create_app(config_class):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)

    from DAL import MongoDBConnectionFactory
    # Load MongoDB Factory
    MongoDBConnectionFactory.init_app(app.config['MONGO_URI'], app.config['MONGO_DATABASE'])

    from BLL import FlowController, AuthenticationController

    # Health check
    @app.route("/")
    def hello_world():
        return "<p>Hello, World!</p>"

    @app.route('/auth/send-link', methods=['POST'])
    def auth_mail():
        # inject controller
        authentication_controller = AuthenticationController()
        email = request.args.get('email')
        if not email.endswith('@udf.edu.br'):
            return jsonify({'error': 'Invalid email domain'}), 400

        # Generate hash
        now = datetime.now()
        hash_auth = sha256(str(now).encode()).hexdigest()

        # Save the hash and email in the database
        authentication_controller.insert_token(email, hash_auth)

        # Send the magic link via email
        magic_link = f"http://{request.remote_addr}/auth/callback?email={email}&hash={hash_auth}"
        if os.getenv('FLASK_ENV') == 'development':
            return jsonify({'magic_link': magic_link}), 201
        try:
            send_response = send_magic_link(email, email.split('@')[0], magic_link)
            if send_response.status_code != 200:
                return jsonify({'error': 'Email sender service unavailable: failed to send email'}), 503
        except Exception as e:
            return jsonify({'error': str(e)}), 503

        return jsonify({'message': 'Magic link sent successfully'}), 201

    @app.route('/auth/validate', methods=['GET'])
    def validate_hash():
        authentication_controller = AuthenticationController()
        valid_hash = authentication_controller.is_token_valid(token=request.args.get('token'), email=request.args.get('email'))

        return jsonify(valid_hash), 200


    @app.route('/buildings', methods=['GET'])
    def get_buildings():
        buildings = FlowController.find_all_buildings()
        return jsonify({'buildings': buildings}), 200

    @app.route('/rooms', methods=['GET'])
    def get_rooms():
        rooms = FlowController.find_all_rooms()
        return jsonify({'rooms': rooms}), 200

    @app.route('/types', methods=['GET'])
    def get_types():
        types_data = FlowController.find_all_types()
        return jsonify({'types': types_data}), 200

    @app.route('/types/<string:collection>', methods=['GET'])
    def get_type_by_collection(collection: str):
        return FlowController.find_type_by_collection(collection)


    @app.route('/reservations', methods=['POST'])
    def post_reservation():
        # Getting the json data from the request
        data = request.json
        if not data:
            return jsonify({'error': 'Missing date'}), 400
        return FlowController.register_reservation_from_json(data)

    @app.route('/reservations/<string:date>', methods=['GET'])
    def get_reservation_by_date(date: str):
        FlowController.filter_reservation_by_date(date)
        return FlowController.filter_reservation_by_date(date)


    @app.route('/events', methods=['POST'])
    def post_event():
        # Getting the json data from the request
        data = request.json
        if not data:
            return jsonify({'error': 'Missing date'}), 400
        return FlowController.register_event_from_json(data)

    @app.route('/events', methods=['GET'])
    def get_events():
        return FlowController.find_all_events()

    return app


if __name__ == '__main__':
    app = create_app(get_config())
    app.run(host=app.config['SERVER_HOST'], port=app.config['SERVER_PORT'])
