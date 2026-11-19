from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionDep
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def serialize_user(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), email=user.email, full_name=user.full_name, role=user.role)


def set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_access_token(user.id),
        max_age=settings.auth_session_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, session: SessionDep):
    email = str(body.email).strip().lower()
    existing = await session.scalar(select(User).where(func.lower(User.email) == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(email=email, full_name=body.full_name, password_hash=hash_password(body.password), role="user")
    session.add(user)
    await session.flush()
    set_session_cookie(response, user)
    return serialize_user(user)


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, response: Response, session: SessionDep):
    email = str(body.email).strip().lower()
    user = await session.scalar(select(User).where(func.lower(User.email) == email))
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    set_session_cookie(response, user)
    return serialize_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
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
