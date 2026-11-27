import time
import uuid

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import (
    InvalidSessionToken,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.modules.auth.schemas import RegisterRequest


def test_password_hash_verifies_without_storing_plaintext():
    raw_password = "a-long-test-password-123"
    encoded = hash_password(raw_password)

    assert encoded != raw_password
    assert verify_password(raw_password, encoded)
    assert not verify_password("not-the-password", encoded)


def test_session_token_round_trips_user_id_and_session_version():
    user_id = uuid.uuid4()

    assert decode_access_token(create_access_token(user_id, 3)) == (user_id, 3)


def test_a_token_without_a_session_version_is_rejected():
    now = int(time.time())
    old_token = jwt.encode({"sub": str(uuid.uuid4()), "iat": now, "exp": now + 60, "type": "access"},
                           settings.auth_secret_key, algorithm="HS256")

    with pytest.raises(InvalidSessionToken):
        decode_access_token(old_token)


def test_expired_session_token_is_rejected():
    expired_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": 1, "exp": 2, "type": "access", "ver": 0},
        settings.auth_secret_key,
        algorithm="HS256",
    )

    with pytest.raises(InvalidSessionToken):
        decode_access_token(expired_token)


def test_registration_requires_a_long_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email="person@example.com", full_name="Tax User", password="short")


async def test_protected_route_rejects_anonymous_request_and_returns_request_id(client):
    response = await client.get("/api/v1/auth/me", headers={"X-Request-ID": "req-123"})

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == "req-123"
