import math
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request

from app.core.config import settings


class SlidingWindowLimiter:
    """In-memory sliding-window limiter.

    State lives in this process only: with several API workers or instances, each keeps its own
    counts. Move to a shared store (e.g. Redis) before scaling out.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_seconds: int) -> float | None:
        """Record one hit. Returns None if allowed, else seconds until the next hit is allowed."""
        now = self._clock()
        hits = self._hits[key]
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            return hits[0] + window_seconds - now
        hits.append(now)
        return None

    def reset(self) -> None:
        self._hits.clear()


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    """The visitor's address. Behind `trusted_proxy_hops` proxies, each appends the address it received the
    request from to X-Forwarded-For, so the visitor is that many entries from the right; anything further left
    was sent by the client and can be forged."""
    hops = settings.trusted_proxy_hops
    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    if hops > 0 and forwarded:
        return forwarded[max(len(forwarded) - hops, 0)]
    return request.client.host if request.client else "unknown"


def enforce(key: str, limit: int, window_seconds: int) -> None:
    """Count one request for `key`; raise 429 with Retry-After when the limit is exceeded."""
    retry_after = limiter.hit(key, limit, window_seconds)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(math.ceil(retry_after))},
        )


def rate_limit(scope: str, limit: Callable[[], int], window_seconds: int):
    """FastAPI dependency limiting requests per client IP for one endpoint scope."""

    async def dependency(request: Request) -> None:
        enforce(f"{scope}:{client_ip(request)}", limit(), window_seconds)

    return dependency
