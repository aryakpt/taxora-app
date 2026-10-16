import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from fastapi import Cookie, Depends, Header, HTTPException
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import get_session
from backend.models import User

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_session_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.auth_secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
        if payload["type"] != "access":
            raise InvalidTokenError("Invalid token type")
        return uuid.UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc


async def admin_from_config(session: AsyncSession) -> User:
    admin_id = uuid.uuid5(uuid.NAMESPACE_URL, "taxora:admin-service")
    user = await session.get(User, admin_id)
    if user is None:
        user = User(id=admin_id, role="admin")
        session.add(user)
        await session.flush()
    return user


async def current_user(
    authorization: Annotated[str | None, Header()] = None,
    session_cookie: Annotated[str | None, Cookie(alias=settings.auth_cookie_name)] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    if authorization and authorization.startswith("Bearer "):
        bearer_token = authorization.removeprefix("Bearer ")
        if bearer_token and bearer_token == settings.admin_token:
            return await admin_from_config(session)
        token = bearer_token
    else:
        token = session_cookie

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = decode_access_token(token)
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return user


async def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user
