import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionDep
from app.core.security import InvalidSessionToken, decode_access_token
from app.modules.auth.models import User


async def admin_from_config(session: AsyncSession) -> User:
    admin_id = uuid.uuid5(uuid.NAMESPACE_URL, "taxora:admin-service")
    user = await session.get(User, admin_id)
    if user is None:
        user = User(id=admin_id, role="admin")
        session.add(user)
        await session.flush()
    return user


async def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    session_cookie: Annotated[str | None, Cookie(alias=settings.auth_cookie_name)] = None,
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

    try:
        user_id = decode_access_token(token)
    except InvalidSessionToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return user


async def admin_user(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(admin_user)]
