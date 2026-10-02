import platform

from SLL import create_app
from configmodule import get_config

# Printed to stdout so the host's log viewer shows the live CPU architecture.
print(f"runtime: machine={platform.machine()} system={platform.system()} python={platform.python_version()}", flush=True)

# Create the app at module level so Gunicorn can import it.
reservation_app = create_app(get_config())

if __name__ == '__main__':
    reservation_app.run(host=reservation_app.config['SERVER_HOST'], port=reservation_app.config['SERVER_PORT'])
