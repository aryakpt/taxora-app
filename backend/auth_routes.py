from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import create_access_token, hash_password, verify_password, current_user
from backend.config import settings
from backend.db import get_session
from backend.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str | None
    full_name: str | None
    role: str


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
async def register(
    body: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
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
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
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
async def me(user: User = Depends(current_user)):
    return serialize_user(user)
