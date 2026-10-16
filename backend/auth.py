import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import get_session
from backend.models import User


async def current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Autentikasi diperlukan")
    token = authorization.removeprefix("Bearer ")
    if token == settings.admin_token:
        role, key = "admin", "admin"
    elif token == settings.api_token:
        role, key = "user", "local-user"
    else:
        raise HTTPException(401, "Token tidak valid")
    user_id = uuid.uuid5(uuid.NAMESPACE_URL, f"taxora:{key}")
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        user = User(id=user_id, role=role)
        session.add(user)
        await session.flush()
    return user


async def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Akses administrator diperlukan")
    return user
