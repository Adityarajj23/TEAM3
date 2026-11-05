"""Password hashing (Argon2), session tokens and CSRF tokens."""
from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()
SESSION_COOKIE = "tt_session"
CSRF_COOKIE = "tt_csrf"
CSRF_HEADER = "X-CSRF-Token"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        # Constant-ish time path for users that cannot log in
        _hasher.hash("timing-equaliser")
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


def constant_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
