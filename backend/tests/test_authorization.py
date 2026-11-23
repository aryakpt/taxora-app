import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.cli import CommandError, set_role
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User, UserRole

pytestmark = pytest.mark.db

ADMIN_ONLY = "/api/v1/admin/evaluations"
PASSWORD = "a-long-test-password-123"


async def register(client, email: str) -> None:
    response = await client.post("/api/v1/auth/register", json={"email": email, "full_name": "T", "password": PASSWORD})
    assert response.status_code == 201


async def test_admin_route_rejects_anonymous_and_regular_users(client):
    assert (await client.get(ADMIN_ONLY)).status_code == 401

    await register(client, "user@example.com")
    assert (await client.get(ADMIN_ONLY)).status_code == 403


async def test_reviewer_is_not_an_admin(client):
    await register(client, "reviewer@example.com")
    await set_role("reviewer@example.com", UserRole.reviewer)

    assert (await client.get(ADMIN_ONLY)).status_code == 403


async def test_promoted_admin_gains_access_and_change_is_audited(client):
    await register(client, "boss@example.com")
    previous = await set_role("BOSS@example.com", UserRole.admin)

    assert previous == "user"
    assert (await client.get(ADMIN_ONLY)).status_code == 200
    assert (await client.get("/api/v1/auth/me")).json()["role"] == "admin"
    async with SessionLocal() as session:
        actions = (await session.scalars(select(AuditLog.action))).all()
    assert actions == ["user.role.user->admin"]


async def test_set_role_requires_an_existing_account():
    with pytest.raises(CommandError):
        await set_role("nobody@example.com", UserRole.admin)


async def test_database_rejects_unknown_roles():
    async with SessionLocal() as session:
        session.add(User(email="weird@example.com", role="superuser"))
        with pytest.raises(IntegrityError):
            await session.flush()


async def test_former_static_admin_token_no_longer_grants_access(client):
    response = await client.get(ADMIN_ONLY, headers={"Authorization": "Bearer " + "x" * 64})

    assert response.status_code == 401


async def test_bearer_session_token_works_for_api_clients(client):
    await register(client, "api@example.com")
    client.cookies.clear()
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == "api@example.com"))

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {create_access_token(user.id)}"})

    assert response.status_code == 200


async def test_token_for_deleted_account_is_rejected(client):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {create_access_token(uuid.uuid4())}"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Account no longer exists"
