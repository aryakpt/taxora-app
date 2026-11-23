import asyncio
import os
from pathlib import Path

import pytest

# Must be set before any `app` import: settings and the engine are created at import time.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://taxora:taxora@localhost:5432/taxora_test"
)
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-auth-secret-key-with-more-than-32-bytes")
os.environ["LLM_API_KEY"] = ""  # tests never call a real provider; see the fake_ai fixture

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.modules.generation import providers  # noqa: E402
from tests.fakes import FakeEmbedder, FakeLLM  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


async def _database_reachable() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


def _upgrade_to_head() -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


@pytest.fixture(scope="session")
async def migrated_database():
    """Apply all Alembic migrations once per run; skip DB tests when Postgres is not running."""
    if not await _database_reachable():
        pytest.skip("Test database unavailable: run `make db-up` (docker compose up -d db)")
    # Alembic's env.py calls asyncio.run(), which cannot run inside pytest's active event loop.
    await asyncio.to_thread(_upgrade_to_head)


@pytest.fixture
async def clean_database(migrated_database):
    yield
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture(autouse=True)
def reset_rate_limits():
    limiter.reset()


@pytest.fixture(autouse=True)
def document_storage(tmp_path, monkeypatch):
    """Original documents go to a per-test temporary folder, never to backend/storage."""
    monkeypatch.setattr(settings, "document_storage_dir", tmp_path / "documents")
    return tmp_path / "documents"


@pytest.fixture(autouse=True)
def fake_ai(monkeypatch):
    """Replace AI providers in every test: no model download, no network calls.
    The LLM is unconfigured by default; tests opt in with `fake_ai.enable_llm()`."""

    class Providers:
        embedder = FakeEmbedder()
        llm = FakeLLM()
        llm_enabled = False

        def enable_llm(self, response: str | Exception = "{}") -> FakeLLM:
            self.llm_enabled, self.llm.response = True, response
            return self.llm

    state = Providers()
    monkeypatch.setattr(providers, "get_embedder", lambda: state.embedder)
    monkeypatch.setattr(providers, "get_llm", lambda: state.llm if state.llm_enabled else None)
    return state



@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_closest_marker("db"):
            item.fixturenames.append("clean_database")
