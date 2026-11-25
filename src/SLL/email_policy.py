"""Email recipient policy for authentication links."""


def is_email_allowed(email, additional_allowlist=""):
    """Allow UDF addresses and exact addresses from a scoped allowlist."""
    if not isinstance(email, str):
        return False

    normalized_email = email.strip().casefold()
    if not normalized_email or normalized_email.count("@") != 1:
        return False

    local_part, domain = normalized_email.split("@", 1)
    if not local_part or not domain:
        return False

    if domain == "udf.edu.br":
        return True

    allowed_addresses = {
        address.strip().casefold()
        for address in additional_allowlist.split(",")
        if address.strip()
    }
    return normalized_email in allowed_addresses
