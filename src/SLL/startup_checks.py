"""Configuration the API refuses to start without."""

import os

from SLL.insecure_dev import insecure_dev_allowed


def require_internal_api_key():
    """The Catalog is closed by default, so the API must hold its key.

    A missing, empty or blank INTERNAL_API_KEY stops the start with a clear
    error instead of letting every catalog call fail later with 403. Only
    ALLOW_INSECURE_DEV=true under FLASK_ENV=development skips the check.
    """
    if (os.getenv("INTERNAL_API_KEY") or "").strip():
        return
    if insecure_dev_allowed():
        return
    raise RuntimeError(
        "INTERNAL_API_KEY is not set: the API cannot call the Catalog service. "
        "Set it to a key listed in the Catalog's API_KEY_LIST "
        "(development only: FLASK_ENV=development and ALLOW_INSECURE_DEV=true)."
    )
