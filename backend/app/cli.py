"""Operator commands. Run from backend/:

    .venv/bin/python -m app.cli set-role <email> <role>
    .venv/bin/python -m app.cli seed-dev-users
    .venv/bin/python -m app.cli reprocess <job_id>
    .venv/bin/python -m app.cli ask-raw "<question>"
    .venv/bin/python -m app.cli eval-retrieval [--include-unreviewed]
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

RAW_SYSTEM_PROMPT = (
    "You are a general assistant. Answer the user's question in the language it is asked in. "
    'Return only a JSON object: {"answer": "..."}'
)

DEV_SEED_PASSWORD = "password123"
DEV_SEED_USERS = (
    ("admin@example.com", "Admin", UserRole.admin),
    ("reviewer@example.com", "Reviewer", UserRole.reviewer),
    ("user@example.com", "User", UserRole.user),
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

    Idempotent: existing seed accounts get their name, role, and password reset.
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
                user = User(email=email)
                session.add(user)
            user.full_name = full_name
            user.role = role.value
            user.password_hash = hash_password(password)
            await session.flush()
            session.add(AuditLog(actor_id=None, action=f"user.seeded.{outcome}", resource_id=str(user.id)))
            results.append((email, role.value, outcome))
    return results


async def ask_raw(question: str) -> tuple[str, str]:
    """Ask the configured LLM directly: no scope guard, no knowledge base, no citation checks. A baseline to
    compare Taxora's answers against (PRD §11). Returns (model, answer)."""
    import json

    from app.modules.generation import providers
    from app.modules.generation.llm import LLMError

    llm = providers.get_llm()
    if llm is None:
        raise CommandError("LLM_API_KEY is not set in backend/.env.")
    errors = []
    for attempt in range(max(1, settings.llm_attempts)):  # same retry policy as the chat, for a fair comparison
        try:
            reply = await llm.complete_json(RAW_SYSTEM_PROMPT, question, attempt)
            break
        except LLMError as exc:
            errors.append(str(exc))
    else:
        raise CommandError(f"The LLM gave no usable reply in {len(errors)} attempts: {'; '.join(errors)}")
    try:
        answer = json.loads(reply.text).get("answer", reply.text)
    except (ValueError, AttributeError):
        answer = reply.text
    return reply.model, str(answer)


async def reprocess(job_id: str) -> str:
    import uuid

    from app.modules.ingestion import service

    try:
        return await service.reprocess(uuid.UUID(job_id))
    except ValueError as exc:
        raise CommandError(f"Not a job id: {job_id!r}") from exc
    except service.JobNotFound as exc:
        raise CommandError("Job not found.") from exc
    except service.InvalidTransition as exc:
        raise CommandError(str(exc)) from exc


async def eval_retrieval(include_unreviewed: bool) -> dict:
    from app.modules.evaluation import retrieval
    from app.modules.generation import providers

    async with SessionLocal() as session, session.begin():
        return await retrieval.run(session, retrieval.load(), providers.get_embedder(),
                                   include_unreviewed=include_unreviewed)


def print_evaluation(summary: dict) -> None:
    def rate(item: dict) -> str:
        return f"{item['passed']}/{item['total']}"

    print(f"dataset {summary['dataset']} (reviewed by: {summary['dataset_reviewed_by'] or 'nobody yet'}), "
          f"statuses {', '.join(summary['statuses'])}, top {summary['top_k']}")
    for case in summary["cases"]:
        mark = {True: "PASS", False: "FAIL", None: "info"}[case["passed"]]
        where = f"rank {case['rank']}" if case["rank"] else ("refused" if not case["in_scope"] else "")
        found = "; ".join(case["retrieved"][:3]) or "-"
        print(f"  {mark}  {case['id']:<26} {where:<9} {found}")
    print(f"expected article in top {summary['top_k']}: {rate(summary['hit_rate'])}, "
          f"MRR {summary['mean_reciprocal_rank']}, off-topic refused: {rate(summary['out_of_scope_refused'])}, "
          f"not-in-KB questions with results: {summary['not_in_kb_with_results']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    set_role_parser = commands.add_parser("set-role", help="change a user's role (user, reviewer, admin)")
    set_role_parser.add_argument("email")
    set_role_parser.add_argument("role", choices=[role.value for role in UserRole])
    commands.add_parser("seed-dev-users", help="create one development account per role (not in production)")
    reprocess_parser = commands.add_parser("reprocess", help="re-extract a document that is still under review")
    reprocess_parser.add_argument("job_id")
    ask_parser = commands.add_parser("ask-raw", help="ask the LLM directly, without Taxora's sources or guards")
    ask_parser.add_argument("question")
    eval_parser = commands.add_parser("eval-retrieval", help="score the scope guard and retrieval on the dataset")
    eval_parser.add_argument("--include-unreviewed", action="store_true",
                             help="also search documents not yet published (evaluation only)")
    args = parser.parse_args(argv)

    async def run():
        try:
            if args.command == "set-role":
                return await set_role(args.email, UserRole(args.role))
            if args.command == "reprocess":
                return await reprocess(args.job_id)
            if args.command == "ask-raw":
                return await ask_raw(args.question)
            if args.command == "eval-retrieval":
                return await eval_retrieval(args.include_unreviewed)
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
    elif args.command == "reprocess":
        print(result)
    elif args.command == "ask-raw":
        model, answer = result
        print(f"[{model}] — no sources, no checks\n\n{answer}")
    elif args.command == "eval-retrieval":
        print_evaluation(result)
    else:
        for email, role, outcome in result:
            print(f"{outcome:>8}  {role:<9} {email}")
        print(f"Password for all seed accounts: {DEV_SEED_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
