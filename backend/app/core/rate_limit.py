import math
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request


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
    # Behind a reverse proxy, run uvicorn with --proxy-headers so request.client is the real client.
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: Callable[[], int], window_seconds: int):
    """FastAPI dependency limiting requests per client IP for one endpoint scope."""

    async def dependency(request: Request) -> None:
        retry_after = limiter.hit(f"{scope}:{client_ip(request)}", limit(), window_seconds)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Please try again later.",
                headers={"Retry-After": str(math.ceil(retry_after))},
            )

    return dependency
