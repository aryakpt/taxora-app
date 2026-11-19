from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException

from app.core.config import settings
from app.core.database import SessionDep
from app.core.security import InvalidSessionToken, decode_access_token
from app.modules.auth.models import User, UserRole


async def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    session_cookie: Annotated[str | None, Cookie(alias=settings.auth_cookie_name)] = None,
) -> User:
    """Authenticate with the session cookie (browser) or a Bearer session token (API clients)."""
    token = authorization.removeprefix("Bearer ") if authorization and authorization.startswith("Bearer ") else None
    token = token or session_cookie
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


def require_role(*roles: UserRole):
    allowed = {role.value for role in roles}

    async def dependency(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="You do not have permission for this action")
        return user

    return dependency


CurrentUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(require_role(UserRole.admin))]
ReviewerUser = Annotated[User, Depends(require_role(UserRole.reviewer, UserRole.admin))]
