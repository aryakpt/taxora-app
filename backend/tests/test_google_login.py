"""Sign in with Google. Tokens are signed with a test RSA key standing in for Google's."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.audit.models import AuditLog
from app.modules.auth import google
from app.modules.auth.models import User

pytestmark = pytest.mark.db

CLIENT_ID = "test-client.apps.googleusercontent.com"
GOOGLE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def google_configured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", CLIENT_ID)

    async def signing_key(token):
        return GOOGLE_KEY.public_key()

    monkeypatch.setattr(google, "_signing_key", signing_key)


def credential(key=GOOGLE_KEY, **overrides) -> str:
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com", "aud": CLIENT_ID, "sub": "google-123", "iat": now,
        "exp": now + 600, "email": "Pengguna@Gmail.com", "email_verified": True, "name": "Pengguna Google",
        "picture": "https://lh3.googleusercontent.com/a/photo",
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256")


async def sign_in(client, token):
    return await client.post("/api/v1/auth/google", json={"credential": token})


async def test_first_google_sign_in_creates_an_account_and_a_session(client):
    response = await sign_in(client, credential())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "pengguna@gmail.com" and body["role"] == "user"
    assert body["full_name"] == "Pengguna Google" and body["avatar_url"] == "https://lh3.googleusercontent.com/a/photo"
    assert (await client.get("/api/v1/auth/me")).json()["id"] == body["id"]

    client.cookies.clear()
    again = await sign_in(client, credential(email="new-address@gmail.com"))  # same Google account
    assert again.json()["id"] == body["id"]
    async with SessionLocal() as session:
        actions = (await session.scalars(select(AuditLog.action))).all()
        user = await session.scalar(select(User))
    assert actions == ["auth.google.created"] and user.password_hash is None


async def test_an_existing_password_account_with_the_same_email_is_linked(client):
    registered = await client.post("/api/v1/auth/register", json={
        "email": "pengguna@gmail.com", "full_name": "Nama Sendiri", "password": "a-long-test-password-123"})
    client.cookies.clear()

    linked = await sign_in(client, credential())

    assert linked.json()["id"] == registered.json()["id"]
    assert linked.json()["full_name"] == "Nama Sendiri"  # the user's own name is kept
    client.cookies.clear()
    password_still_works = await client.post("/api/v1/auth/login", json={
        "email": "pengguna@gmail.com", "password": "a-long-test-password-123"})
    assert password_still_works.status_code == 200


async def test_an_email_linked_to_another_google_account_is_refused(client):
    await sign_in(client, credential(sub="google-first"))
    client.cookies.clear()

    response = await sign_in(client, credential(sub="google-second"))

    assert response.status_code == 409


@pytest.mark.parametrize("token", [
    credential(key=OTHER_KEY),                              # not signed by Google
    credential(aud="someone-elses-app.apps.googleusercontent.com"),
    credential(iss="https://evil.example"),
    credential(exp=int(time.time()) - 10),                  # expired
    credential(email_verified=False),
    credential(email=None),
    "not-a-jwt-at-all-but-long-enough",
])
async def test_invalid_google_credentials_are_rejected(client, token):
    response = await sign_in(client, token)

    assert response.status_code == 401
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_google_only_accounts_cannot_sign_in_with_a_password(client):
    await sign_in(client, credential())
    client.cookies.clear()

    response = await client.post("/api/v1/auth/login", json={"email": "pengguna@gmail.com", "password": "anything"})

    assert response.status_code == 401


async def test_providers_tell_the_login_page_whether_google_is_enabled(client, monkeypatch):
    assert (await client.get("/api/v1/auth/providers")).json() == {"google_client_id": CLIENT_ID}

    monkeypatch.setattr(settings, "google_client_id", "")
    assert (await client.get("/api/v1/auth/providers")).json() == {"google_client_id": None}
    assert (await sign_in(client, credential())).status_code == 401
