"""Run a command with production settings from deploy/.env.production, without printing any secret.

    python deploy/prodenv.py <command...>      e.g. python deploy/prodenv.py alembic upgrade head

The backend reads its settings from environment variables, which override backend/.env; every value that
could otherwise leak in from the development .env (database, keys, storage) is set here explicitly.
"""

import os
import secrets
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

ENV_FILE = Path(__file__).resolve().parent / ".env.production"
REQUIRED = ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_DB_POOLER_URL", "SUPABASE_DB_PASSWORD", "LLM_API_KEY")


def read_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    if not path.exists():
        sys.exit(f"Missing {path}. Copy deploy/env.production.example to it and fill it in.")
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return values


def database_url(pooler_url: str, password: str) -> str:
    """The Supabase pooler string, with the password URL-encoded, for SQLAlchemy + asyncpg over TLS."""
    if "[YOUR-PASSWORD]" not in pooler_url:
        sys.exit("SUPABASE_DB_POOLER_URL must be the string from Supabase with [YOUR-PASSWORD] left in it.")
    parts = urlsplit(pooler_url.replace("[YOUR-PASSWORD]", quote(password, safe="")))
    if parts.scheme not in ("postgres", "postgresql") or not parts.hostname:
        sys.exit("SUPABASE_DB_POOLER_URL does not look like a postgresql:// connection string.")
    return urlunsplit(("postgresql+asyncpg", parts.netloc, parts.path, "ssl=require", ""))


def production_env(values: dict[str, str]) -> dict[str, str]:
    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        sys.exit(f"Fill in {', '.join(missing)} in {ENV_FILE}.")
    return {
        "APP_ENV": "production",
        "AUTH_COOKIE_SECURE": "true",
        # Commands run here sign no sessions; the API's real key lives only on Render.
        "AUTH_SECRET_KEY": secrets.token_hex(32),
        "DATABASE_URL": database_url(values["SUPABASE_DB_POOLER_URL"], values["SUPABASE_DB_PASSWORD"]),
        "SUPABASE_URL": values["SUPABASE_URL"],
        "SUPABASE_SECRET_KEY": values["SUPABASE_SECRET_KEY"],
        "SUPABASE_STORAGE_BUCKET": values.get("SUPABASE_STORAGE_BUCKET", "documents"),
        "LLM_API_KEY": values["LLM_API_KEY"],
        "EMBEDDING_API_KEY": values["LLM_API_KEY"],
        "GOOGLE_CLIENT_ID": values.get("GOOGLE_CLIENT_ID", ""),
        "FRONTEND_ORIGIN": values.get("FRONTEND_ORIGIN", ""),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    os.execvpe(sys.argv[1], sys.argv[1:], {**os.environ, **production_env(read_env_file())})
