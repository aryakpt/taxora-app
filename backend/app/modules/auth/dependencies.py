from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException

from app.core.config import settings
from app.core.database import SessionDep
from app.core.security import InvalidSessionToken, decode_access_token
from app.modules.auth.models import User, UserRole


def session_token(authorization: str | None, session_cookie: str | None) -> str | None:
    """The Bearer token (API clients) or else the session cookie (browser)."""
    token = authorization.removeprefix("Bearer ") if authorization and authorization.startswith("Bearer ") else None
    return token or session_cookie


async def session_user(session, token: str | None) -> User | None:
    """The account of a valid, current session token, else None. A token is current only while its version
    equals the account's session_version: logging out or linking Google raises it and ends older sessions."""
    if not token:
        return None
    try:
        user_id, version = decode_access_token(token)
    except InvalidSessionToken:
        return None
    user = await session.get(User, user_id)
    return user if user is not None and user.session_version == version else None


async def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    session_cookie: Annotated[str | None, Cookie(alias=settings.auth_cookie_name)] = None,
) -> User:
    """Authenticate with the session cookie (browser) or a Bearer session token (API clients)."""
    token = session_token(authorization, session_cookie)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = await session_user(session, token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
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
