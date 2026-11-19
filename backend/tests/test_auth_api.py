import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.auth.models import User

pytestmark = pytest.mark.db

ACCOUNT = {"email": "Person@Example.com", "full_name": "Tax User", "password": "a-long-test-password-123"}


async def test_registered_account_is_persisted_and_session_works(client):
    registered = await client.post("/api/v1/auth/register", json=ACCOUNT)
    assert registered.status_code == 201

    # A separate session proves the request transaction was committed, not just flushed.
    async with SessionLocal() as session:
        stored = await session.scalar(select(User).where(User.email == "person@example.com"))
    assert stored is not None
    assert stored.password_hash != ACCOUNT["password"]

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "person@example.com"


async def test_duplicate_email_is_rejected_case_insensitively(client):
    assert (await client.post("/api/v1/auth/register", json=ACCOUNT)).status_code == 201

    duplicate = await client.post("/api/v1/auth/register", json={**ACCOUNT, "email": "PERSON@example.com"})

    assert duplicate.status_code == 409


async def test_login_logout_cycle(client):
    await client.post("/api/v1/auth/register", json=ACCOUNT)
    await client.post("/api/v1/auth/logout")
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    wrong = await client.post("/api/v1/auth/login", json={"email": ACCOUNT["email"], "password": "wrong-password"})
    assert wrong.status_code == 401

    login = await client.post("/api/v1/auth/login", json={"email": ACCOUNT["email"], "password": ACCOUNT["password"]})
    assert login.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 200
