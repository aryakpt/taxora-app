from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionDep
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.audit.models import AuditLog
from app.modules.auth import google
from app.modules.auth.dependencies import CurrentUser, session_token, session_user
from app.modules.auth.models import User, UserRole
from app.modules.auth.schemas import GoogleLoginRequest, LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Verified when the email is unknown so both login failures take about the same time,
# which keeps response timing from revealing whether an account exists.
_DUMMY_PASSWORD_HASH = hash_password("taxora-timing-equalizer-not-a-real-password")

login_limit = rate_limit("auth.login", lambda: settings.auth_login_attempts_per_minute, window_seconds=60)
register_limit = rate_limit("auth.register", lambda: settings.auth_registrations_per_hour, window_seconds=3600)


def serialize_user(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), email=user.email, full_name=user.full_name, role=user.role,
                        avatar_url=user.avatar_url)


def set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_access_token(user.id, user.session_version),
        max_age=settings.auth_session_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_limit)],
)
async def register(body: RegisterRequest, response: Response, session: SessionDep):
    email = str(body.email).strip().lower()
    existing = await session.scalar(select(User).where(func.lower(User.email) == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        email=email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role=UserRole.user.value,
    )
    session.add(user)
    await session.flush()
    set_session_cookie(response, user)
    return serialize_user(user)


@router.post("/login", response_model=UserResponse, dependencies=[Depends(login_limit)])
async def login(body: LoginRequest, response: Response, session: SessionDep):
    email = str(body.email).strip().lower()
    user = await session.scalar(select(User).where(func.lower(User.email) == email))
    password_hash = user.password_hash if user and user.password_hash else _DUMMY_PASSWORD_HASH
    password_ok = verify_password(body.password, password_hash)
    if user is None or not user.password_hash or not password_ok:
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    set_session_cookie(response, user)
    return serialize_user(user)


@router.get("/providers")
async def providers():
    """Sign-in options the login page should offer. The Google client ID is public by design."""
    return {"google_client_id": settings.google_client_id or None}


@router.post("/google", response_model=UserResponse, dependencies=[Depends(login_limit)])
async def google_login(body: GoogleLoginRequest, response: Response, session: SessionDep):
    """Sign in with a Google ID token. The first sign-in creates an account (role user), or links an
    existing account with the same email, which Google has verified."""
    try:
        identity = await google.verify_credential(body.credential)
    except google.InvalidGoogleCredential as exc:
        raise HTTPException(status_code=401, detail="Google sign-in failed") from exc

    user = await session.scalar(select(User).where(User.google_sub == identity.subject))
    action = "auth.google.signed_in"
    password_removed = False
    if user is None:
        user = await session.scalar(select(User).where(func.lower(User.email) == identity.email))
        if user is not None and user.google_sub:
            # The email belongs to an account already linked to a different Google account.
            raise HTTPException(status_code=409, detail="This email is linked to another Google account")
        action = "auth.google.linked" if user else "auth.google.created"
        if user is None:
            user = User(email=identity.email, full_name=identity.name, role=UserRole.user.value)
            session.add(user)
        else:
            # Registration does not verify email, so whoever set this password may not own the address; Google
            # has just proved who does. Drop the password and end every session made with it, or someone who
            # registered the email first would keep a way into the owner's account.
            password_removed = user.password_hash is not None
            user.password_hash = None
            user.session_version += 1
        user.google_sub = identity.subject
    user.full_name = user.full_name or identity.name
    user.avatar_url = identity.picture or user.avatar_url
    await session.flush()
    if action != "auth.google.signed_in":
        session.add(AuditLog(actor_id=user.id, action=action, resource_id=str(user.id),
                             details={"password_removed": True} if password_removed else None))
    set_session_cookie(response, user)
    return serialize_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    session_cookie: Annotated[str | None, Cookie(alias=settings.auth_cookie_name)] = None,
):
    """Ends the session on the server too: the account's session version goes up, so this token (and the
    account's other sessions) stop working even if a copy was taken. Without a valid session it only clears
    the cookie."""
    user = await session_user(session, session_token(authorization, session_cookie))
    if user is not None:
        user.session_version += 1
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser):
    return serialize_user(user)
