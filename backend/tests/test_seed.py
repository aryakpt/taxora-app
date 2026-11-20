import pytest
from sqlalchemy import select

from app.cli import DEV_SEED_PASSWORD, CommandError, seed_dev_users
from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.auth.models import User

pytestmark = pytest.mark.db


async def roles_by_email() -> dict[str, str]:
    async with SessionLocal() as session:
        return {user.email: user.role for user in (await session.scalars(select(User))).all()}


async def test_seed_creates_one_account_per_role():
    results = await seed_dev_users()

    assert [outcome for *_, outcome in results] == ["created"] * 3
    assert await roles_by_email() == {
        "admin@example.com": "admin",
        "reviewer@example.com": "reviewer",
        "user@example.com": "user",
    }


async def test_seed_is_idempotent_and_restores_roles():
    await seed_dev_users()
    async with SessionLocal() as session, session.begin():
        admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
        admin.role = "user"

    results = await seed_dev_users()

    assert [outcome for *_, outcome in results] == ["reset"] * 3
    assert len(await roles_by_email()) == 3
    assert (await roles_by_email())["admin@example.com"] == "admin"


async def test_seeded_admin_can_sign_in_and_open_admin_routes(client):
    await seed_dev_users()

    login = await client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": DEV_SEED_PASSWORD})

    assert login.status_code == 200
    assert (await client.get("/api/v1/admin/ingestion")).status_code == 200


async def test_seed_refuses_to_run_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")

    with pytest.raises(CommandError):
        await seed_dev_users()
    assert await roles_by_email() == {}
