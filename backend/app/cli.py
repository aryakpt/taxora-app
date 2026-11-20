"""Operator commands. Run from backend/:

    .venv/bin/python -m app.cli set-role <email> <role>
    .venv/bin/python -m app.cli seed-dev-users
"""

import argparse
import asyncio
import sys

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User, UserRole

DEV_SEED_PASSWORD = "taxora-dev-password"
DEV_SEED_USERS = (
    ("admin@example.com", "Dev Admin", UserRole.admin),
    ("reviewer@example.com", "Dev Reviewer", UserRole.reviewer),
    ("user@example.com", "Dev User", UserRole.user),
)


class CommandError(Exception):
    pass


async def set_role(email: str, role: UserRole) -> str:
    """Change a registered user's role and record it in the audit log. Returns the previous role."""
    async with SessionLocal() as session, session.begin():
        user = await session.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
        if user is None:
            raise CommandError(f"No account with email {email!r}. The user must register first.")
        previous = user.role
        user.role = role.value
        session.add(AuditLog(actor_id=None, action=f"user.role.{previous}->{role.value}", resource_id=str(user.id)))
    return previous


async def seed_dev_users(password: str = DEV_SEED_PASSWORD) -> list[tuple[str, str, str]]:
    """Create one account per role with a known password, for local development only.

    Idempotent: existing seed accounts get their role and password reset.
    Returns (email, role, "created" | "reset") for each account.
    """
    if settings.app_env == "production":
        raise CommandError("Refusing to seed known-password accounts when APP_ENV=production.")
    results = []
    async with SessionLocal() as session, session.begin():
        for email, full_name, role in DEV_SEED_USERS:
            user = await session.scalar(select(User).where(func.lower(User.email) == email))
            outcome = "reset" if user else "created"
            if user is None:
                user = User(email=email, full_name=full_name)
                session.add(user)
            user.role = role.value
            user.password_hash = hash_password(password)
            await session.flush()
            session.add(AuditLog(actor_id=None, action=f"user.seeded.{outcome}", resource_id=str(user.id)))
            results.append((email, role.value, outcome))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    set_role_parser = commands.add_parser("set-role", help="change a user's role (user, reviewer, admin)")
    set_role_parser.add_argument("email")
    set_role_parser.add_argument("role", choices=[role.value for role in UserRole])
    commands.add_parser("seed-dev-users", help="create one development account per role (not in production)")
    args = parser.parse_args(argv)

    async def run():
        try:
            if args.command == "set-role":
                return await set_role(args.email, UserRole(args.role))
            return await seed_dev_users()
        finally:
            await engine.dispose()

    try:
        result = asyncio.run(run())
    except CommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.command == "set-role":
        print(f"{args.email}: {result} -> {args.role}. It applies to the next request; the user may need to reload the page.")
    else:
        for email, role, outcome in result:
            print(f"{outcome:>8}  {role:<9} {email}")
        print(f"Password for all seed accounts: {DEV_SEED_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
