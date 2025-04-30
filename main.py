from SLL import create_app
from configmodule import get_config

# Create the app at module level so Gunicorn can import it.
reservation_app = create_app(get_config())

if __name__ == '__main__':
    reservation_app.run(host=reservation_app.config['SERVER_HOST'], port=reservation_app.config['SERVER_PORT'])
