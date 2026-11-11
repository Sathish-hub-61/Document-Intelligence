"""
JWT authentication service.
Issues short-lived (30 min default) access tokens carrying user_id only.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import jwt

from app.composition.settings import get_settings
from app.domain.errors import AuthenticationError

ALGORITHM = "HS256"


def create_access_token(user_id: UUID, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expire_minutes)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> UUID:
    """
    Decodes the JWT token and extracts the user_id (sub).
    Raises AuthenticationError if expired or invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Token payload missing subject")
        return UUID(user_id_str)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except (jwt.PyJWTError, ValueError):
        raise AuthenticationError("Invalid authentication token")
