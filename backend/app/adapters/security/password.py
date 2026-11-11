"""
Argon2 password hashing and verification adapter.
Enforces minimum password length of 10 characters.
"""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.domain.errors import ValidationError

_hasher = PasswordHasher()


def hash_password(password: str, min_length: int = 10) -> str:
    """
    Hashes a password with Argon2.
    Raises ValidationError if password is shorter than min_length.
    """
    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters long")
    return _hasher.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verifies a plain password against an Argon2 hash.
    """
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
