"""The log goes to the platform's retention: no e-mail address and no raw token may reach it."""

import logging
import string
import subprocess
import sys
from pathlib import Path

import pytest

from SLL.py_log import AppLogger, Logmessage, LogType, mask_email, scrub_emails

ADDRESS = "pessoa.teste@udf.edu.br"
OTHER = "outra.pessoa@gmail.com"
RAW_TOKEN = "raw-token-0123456789-abcdef"


def sample_fields(message):
    """Fill every placeholder; the ones that can carry personal data carry an address and a token."""
    fields = {}
    for _, name, _, _ in string.Formatter().parse(message.value):
        if not name:
            continue
        if name in ("email", "who"):
            fields[name] = ADDRESS
        elif name == "token":
            fields[name] = RAW_TOKEN
        elif name in ("payload", "error"):
            fields[name] = f"{{'email': '{OTHER}', 'token': '{RAW_TOKEN}'}} for {ADDRESS}"
        else:
            fields[name] = "x"
    return fields


@pytest.mark.parametrize("message", list(Logmessage), ids=lambda m: m.name)
def test_no_message_writes_an_address_or_a_raw_token(message, caplog):
    with caplog.at_level(logging.DEBUG):
        AppLogger.log(message, LogType.INFO, **sample_fields(message))
    assert caplog.records, f"{message.name} wrote nothing"
    text = "\n".join(r.getMessage() for r in caplog.records)
    for forbidden in (ADDRESS, OTHER, RAW_TOKEN, "@udf.edu.br", "@gmail.com"):
        assert forbidden not in text, f"{message.name} wrote {forbidden}"


def test_an_address_becomes_the_same_fingerprint_the_audit_line_uses():
    line = scrub_emails(f"login by {ADDRESS} and {ADDRESS.upper()}")
    assert line == f"login by {mask_email(ADDRESS)} and {mask_email(ADDRESS)}"
    assert "@" not in line


def test_log_lines_go_to_stdout_not_only_to_a_file_in_the_container():
    # a fresh interpreter: pytest installs its own root handlers, so the import-time setup is checked here
    code = (
        "import logging, sys\n"
        "import SLL.py_log\n"
        "from SLL.py_log import AppLogger, Logmessage, LogType\n"
        "AppLogger.log(Logmessage.AUTH_SERVICE_UNAVAILABLE, LogType.ERROR)\n"
        "print([type(h).__name__ for h in logging.getLogger().handlers])\n"
    )
    src = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-c", code], cwd=src, capture_output=True, text=True,
                            env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(src), "PYTHONDONTWRITEBYTECODE": "1"})
    assert "Authentication service unavailable" in result.stdout, result.stderr
    assert "FileHandler" not in result.stdout.splitlines()[-1], "a file is written only when LOG_FILE is set"
