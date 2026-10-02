"""The one opt-out for secure-by-default settings, usable only in development.

``ALLOW_INSECURE_DEV=true`` is honoured only together with
``FLASK_ENV=development``; in any other environment it is ignored, so a copied
``.env`` cannot open a deployed service. The same name and rule are used by the
API, Auth and Catalog services.
"""

import os


def insecure_dev_allowed():
    return (os.getenv("FLASK_ENV") == "development"
            and os.getenv("ALLOW_INSECURE_DEV", "").strip().lower() in ("1", "true", "yes", "on"))
