import math
import random
from collections.abc import Callable
from datetime import datetime

from fastapi import HTTPException, Request
from sqlalchemy import BigInteger, DateTime, Identity, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base, engine

# Hits older than this are deleted now and then; it must exceed the longest window in use (1 hour).
RETENTION = "1 day"


class RateLimitHit(Base):
    """One counted request. Kept in PostgreSQL so every API instance (serverless functions included) shares
    the same counts; an in-memory counter would give each instance its own allowance."""

    __tablename__ = "rate_limit_hits"
    __table_args__ = (Index("ix_rate_limit_hits_key_at", "key", "at"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    key: Mapped[str] = mapped_column(String(200))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def hit(key: str, limit: int, window_seconds: int) -> float | None:
    """Count one hit in a sliding window. Returns None if allowed, else seconds until the next hit is allowed.

    Runs in its own transaction, so the hit stays counted even when the request itself fails and rolls back
    (a wrong password must still count). An advisory lock per key makes check-and-insert atomic across
    instances. The database clock is used, so instances agree on time."""
    window = {"key": key, "window": window_seconds}
    async with engine.begin() as connection:
        await connection.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})
        count, wait = (await connection.execute(text(
            "SELECT count(*), extract(epoch FROM min(at) + make_interval(secs => :window) - clock_timestamp()) "
            "FROM rate_limit_hits WHERE key = :key AND at > clock_timestamp() - make_interval(secs => :window)"
        ), window)).one()
        if count >= limit:
            return max(float(wait or 0), 1.0)
        await connection.execute(text("INSERT INTO rate_limit_hits (key, at) VALUES (:key, clock_timestamp())"),
                                 {"key": key})
        if random.random() < 0.01:
            await connection.execute(text(f"DELETE FROM rate_limit_hits WHERE at < now() - interval '{RETENTION}'"))
    return None


def client_ip(request: Request) -> str:
    """The visitor's address. Behind `trusted_proxy_hops` proxies, each appends the address it received the
    request from to X-Forwarded-For, so the visitor is that many entries from the right; anything further left
    was sent by the client and can be forged."""
    hops = settings.trusted_proxy_hops
    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    if hops > 0 and forwarded:
        return forwarded[max(len(forwarded) - hops, 0)]
    return request.client.host if request.client else "unknown"


async def enforce(key: str, limit: int, window_seconds: int) -> None:
    """Count one request for `key`; raise 429 with Retry-After when the limit is exceeded."""
    retry_after = await hit(key, limit, window_seconds)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(math.ceil(retry_after))},
        )


def rate_limit(scope: str, limit: Callable[[], int], window_seconds: int):
    """FastAPI dependency limiting requests per client IP for one endpoint scope."""

    async def dependency(request: Request) -> None:
        await enforce(f"{scope}:{client_ip(request)}", limit(), window_seconds)

    return dependency
