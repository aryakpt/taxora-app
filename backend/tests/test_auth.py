import uuid

import jwt
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.auth import create_access_token, decode_access_token, hash_password, verify_password
from backend.auth_routes import RegisterRequest
from backend.config import settings


def test_password_hash_verifies_without_storing_plaintext():
    raw_password = "a-long-test-password-123"
    encoded = hash_password(raw_password)

    assert encoded != raw_password
    assert verify_password(raw_password, encoded)
    assert not verify_password("not-the-password", encoded)


def test_session_token_round_trips_user_id():
    user_id = uuid.uuid4()

    assert decode_access_token(create_access_token(user_id)) == user_id


def test_expired_session_token_is_rejected():
    expired_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": 1, "exp": 2, "type": "access"},
        settings.auth_secret_key,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        decode_access_token(expired_token)

    assert error.value.status_code == 401


def test_registration_requires_a_long_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email="person@example.com", full_name="Tax User", password="short")
