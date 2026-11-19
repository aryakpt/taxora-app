import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal, get_session
from app.modules.auth.models import User

pytestmark = pytest.mark.db


async def count_users() -> int:
    async with SessionLocal() as session:
        return await session.scalar(select(func.count()).select_from(User))


async def test_session_commits_when_request_succeeds():
    dependency = get_session()
    session = await anext(dependency)
    session.add(User(email="committed@example.com", role="user"))

    with pytest.raises(StopAsyncIteration):
        await anext(dependency)

    assert await count_users() == 1


async def test_session_rolls_back_when_request_fails():
    dependency = get_session()
    session = await anext(dependency)
    session.add(User(email="rolled-back@example.com", role="user"))
    await session.flush()

    with pytest.raises(RuntimeError):
        await dependency.athrow(RuntimeError("handler failed"))

    assert await count_users() == 0


async def test_health_reports_database_ok(client):
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
