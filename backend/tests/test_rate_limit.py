import asyncio

import pytest
from sqlalchemy import text

from app.core import rate_limit
from app.core.config import settings
from app.core.database import engine


@pytest.mark.db
async def test_the_sliding_window_is_shared_through_the_database_and_recovers():
    assert await rate_limit.hit("k", limit=2, window_seconds=60) is None
    assert await rate_limit.hit("k", limit=2, window_seconds=60) is None
    assert 58 < await rate_limit.hit("k", limit=2, window_seconds=60) <= 60
    assert await rate_limit.hit("other", limit=2, window_seconds=60) is None

    # Another instance sees the same counts (they live in the database); once the hits age out, it allows again.
    async with engine.begin() as connection:
        await connection.execute(text("UPDATE rate_limit_hits SET at = at - interval '61 seconds'"))
    assert await rate_limit.hit("k", limit=2, window_seconds=60) is None


@pytest.mark.db
async def test_concurrent_requests_cannot_exceed_the_limit():
    results = await asyncio.gather(*(rate_limit.hit("burst", limit=3, window_seconds=60) for _ in range(8)))

    assert sum(result is None for result in results) == 3


@pytest.mark.db
async def test_login_is_rate_limited_per_client(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_login_attempts_per_minute", 2)
    attempt = {"email": "x@example.com", "password": "wrong"}

    statuses = [(await client.post("/api/v1/auth/login", json=attempt)).status_code for _ in range(3)]

    assert statuses[2] == 429
    blocked = await client.post("/api/v1/auth/login", json=attempt)
    assert int(blocked.headers["Retry-After"]) > 0


@pytest.mark.db
async def test_registration_is_rate_limited_per_client(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_registrations_per_hour", 1)
    body = {"full_name": "T", "password": "a-long-test-password-123"}

    first = await client.post("/api/v1/auth/register", json={**body, "email": "a@example.com"})
    second = await client.post("/api/v1/auth/register", json={**body, "email": "b@example.com"})

    assert first.status_code == 201
    assert second.status_code == 429
