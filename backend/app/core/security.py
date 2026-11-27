import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

password_hasher = PasswordHash.recommended()


class InvalidSessionToken(Exception):
    """Raised when a session token is missing claims, tampered with, or expired."""


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: uuid.UUID, session_version: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_session_minutes),
        "type": "access",
        "ver": session_version,  # must equal users.session_version: raising it ends every session
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> tuple[uuid.UUID, int]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.auth_secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub", "type", "ver"]},
        )
        if payload["type"] != "access":
            raise InvalidTokenError("Invalid token type")
        if not isinstance(payload["ver"], int):
            raise InvalidTokenError("Invalid session version")
        return uuid.UUID(payload["sub"]), payload["ver"]
    except (InvalidTokenError, KeyError, ValueError, TypeError) as exc:
        raise InvalidSessionToken("Invalid or expired session") from exc
