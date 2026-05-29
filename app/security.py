from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        salt, _digest = hashed_password.split("$", 1)
    except ValueError:
        return False
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, hashed_password)


def create_session_token() -> str:
    return secrets.token_urlsafe(32)


def create_reset_token() -> str:
    return secrets.token_urlsafe(24)
