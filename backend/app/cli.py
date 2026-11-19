"""Operator commands. Run from backend/:  .venv/bin/python -m app.cli set-role <email> <role>"""

import argparse
import asyncio
import sys

from sqlalchemy import func, select

from app.core.database import SessionLocal, engine
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User, UserRole


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    set_role_parser = commands.add_parser("set-role", help="change a user's role (user, reviewer, admin)")
    set_role_parser.add_argument("email")
    set_role_parser.add_argument("role", choices=[role.value for role in UserRole])
    args = parser.parse_args(argv)

    async def run() -> str:
        try:
            return await set_role(args.email, UserRole(args.role))
        finally:
            await engine.dispose()

    try:
        previous = asyncio.run(run())
    except CommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{args.email}: {previous} -> {args.role}. It applies to the next request; the user may need to reload the page.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
