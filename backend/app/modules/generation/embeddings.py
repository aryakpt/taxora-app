"""Text embeddings through an OpenAI-compatible API (Gemini by default).

The API replaced a local model (fastembed): the backend no longer loads a ~250 MB model into memory, so it
fits free hosting (512 MB), and the Gemini model retrieves far better. Free tier limits are enforced here:
requests are batched by estimated tokens and paced under a tokens-per-minute budget, and a 429 waits for
the delay the provider asks for.
"""

import asyncio
import logging
import re
import time
from collections import OrderedDict, deque
from typing import Protocol

import openai
from openai import AsyncOpenAI

logger = logging.getLogger("taxora.embeddings")


class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]: ...

    async def embed_many(self, texts: list[str]) -> list[list[float]]: ...


class EmbeddingError(Exception):
    """The embedding provider failed or kept refusing. The message is safe to show admins."""


def estimate_tokens(text: str) -> int:
    """Rough count for pacing (Indonesian legal text runs about 3-4 characters per token)."""
    return len(text) // 3 + 8


_RETRY_SECONDS = re.compile(r"retry in ([\d.]+)s|retryDelay['\"]?:\s*['\"]?(\d+)", re.IGNORECASE)


def retry_after(exc: openai.APIStatusError, default: float) -> float:
    match = _RETRY_SECONDS.search(str(exc.body) + str(exc))
    return float(match.group(1) or match.group(2)) + 1 if match else default


class ApiEmbedder:
    def __init__(self, api_key: str, base_url: str, model: str, dimensions: int, *,
                 tokens_per_minute: int = 0, batch_tokens: int = 8000, batch_size: int = 50,
                 max_wait_seconds: float = 900, client: AsyncOpenAI | None = None):
        self.model, self.dimensions = model, dimensions
        self.tokens_per_minute, self.batch_tokens, self.batch_size = tokens_per_minute, batch_tokens, batch_size
        self.max_wait_seconds = max_wait_seconds
        self._client = client or AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=60, max_retries=0)
        self._sent: deque[tuple[float, int]] = deque()  # (time, tokens) in the last minute
        self._pace = asyncio.Lock()
        self._cache: OrderedDict[str, list[float]] = OrderedDict()  # recent short texts (questions)

    async def embed(self, text: str) -> list[float]:
        if text in self._cache:
            self._cache.move_to_end(text)
            return self._cache[text]
        vector = (await self.embed_many([text]))[0]
        self._cache[text] = vector
        if len(self._cache) > 256:
            self._cache.popitem(last=False)
        return vector

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in self._batches(texts):
            vectors.extend(await self._request(batch))
        return vectors

    def _batches(self, texts: list[str]):
        batch, tokens = [], 0
        for text in texts:
            cost = estimate_tokens(text)
            if batch and (len(batch) >= self.batch_size or tokens + cost > self.batch_tokens):
                yield batch
                batch, tokens = [], 0
            batch.append(text)
            tokens += cost
        if batch:
            yield batch

    async def _wait_for_budget(self, tokens: int) -> None:
        if not self.tokens_per_minute:
            return
        async with self._pace:
            while True:
                now = time.monotonic()
                while self._sent and now - self._sent[0][0] >= 60:
                    self._sent.popleft()
                if not self._sent or sum(n for _, n in self._sent) + tokens <= self.tokens_per_minute:
                    self._sent.append((now, tokens))
                    return
                await asyncio.sleep(max(0.5, 60 - (now - self._sent[0][0])))

    async def _request(self, batch: list[str]) -> list[list[float]]:
        tokens = sum(estimate_tokens(text) for text in batch)
        waited = 0.0
        while True:
            await self._wait_for_budget(tokens)
            try:
                response = await self._client.embeddings.create(model=self.model, input=batch,
                                                                dimensions=self.dimensions)
            except openai.RateLimitError as exc:
                delay = retry_after(exc, default=30)
                if waited + delay > self.max_wait_seconds:
                    raise EmbeddingError("Batas pemakaian layanan embedding tercapai; coba lagi nanti.") from exc
                logger.info("embedding rate limited; waiting %.0fs", delay)
                waited += delay
                await asyncio.sleep(delay)
                continue
            except openai.OpenAIError as exc:
                raise EmbeddingError(f"Layanan embedding gagal ({type(exc).__name__}).") from exc
            items = response.data
            # Gemini's OpenAI-compatible endpoint sends "index": null; then the order is the input order.
            if all(item.index is not None for item in items):
                items = sorted(items, key=lambda item: item.index)
            vectors = [item.embedding for item in items]
            if len(vectors) != len(batch) or any(len(vector) != self.dimensions for vector in vectors):
                raise EmbeddingError("Layanan embedding mengembalikan hasil yang tidak sesuai.")
            return vectors
