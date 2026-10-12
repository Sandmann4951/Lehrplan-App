"""Passwort-Hashing (Argon2id), Sitzungstoken und Hilfsfunktionen."""
from __future__ import annotations

import hashlib
import secrets
import string

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # Standardtyp ist Argon2id

MIN_PASSWORD_LENGTH = 10


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# Für konstante Laufzeit bei unbekannten E-Mail-Adressen
DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_temp_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    # Verwechselbare Zeichen vermeiden
    alphabet = "".join(c for c in alphabet if c not in "0O1lI")
    return "".join(secrets.choice(alphabet) for _ in range(length))


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Mindestens {MIN_PASSWORD_LENGTH} Zeichen."
    if len(password) > 200:
        return "Höchstens 200 Zeichen."
    return None


def normalize_email(email: str) -> str:
    return email.strip().lower()
