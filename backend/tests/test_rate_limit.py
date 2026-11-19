import pytest

from app.core.config import settings
from app.core.rate_limit import SlidingWindowLimiter


def test_sliding_window_blocks_after_limit_and_recovers():
    now = [0.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0])

    assert limiter.hit("k", limit=2, window_seconds=60) is None
    assert limiter.hit("k", limit=2, window_seconds=60) is None
    assert limiter.hit("k", limit=2, window_seconds=60) == 60
    assert limiter.hit("other", limit=2, window_seconds=60) is None

    now[0] = 60.0
    assert limiter.hit("k", limit=2, window_seconds=60) is None


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
