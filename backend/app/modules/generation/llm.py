import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import openai
from openai import AsyncOpenAI

from app.core.config import settings

_OPENROUTER_DATA_POLICIES: dict[str, dict | None] = {
    "zero_retention": {"provider": {"data_collection": "deny", "zdr": True}},
    "no_training": {"provider": {"data_collection": "deny"}},
    "any": None,
}


class LLMError(Exception):
    """The provider failed, timed out, or returned no content."""


class Overloaded(LLMError):
    """The provider is temporarily out of capacity (Gemini: 503 "This model is currently experiencing high
    demand"). It affects every key, so a new key does not help; waiting a little or another model does."""


OVERLOAD_STATUSES = {500, 502, 503, 504, 529}


class QuotaExhausted(LLMError):
    """The account's request quota is used up (OpenRouter free tier: 50 or 1000 free-model requests a day).
    Retrying cannot help until `resets_at`."""

    def __init__(self, resets_at: datetime | None):
        super().__init__(f"quota exhausted until {resets_at.isoformat() if resets_at else 'unknown'}")
        self.resets_at = resets_at


def quota_exhaustion(exc: openai.APIStatusError) -> QuotaExhausted | None:
    """Recognise a daily-quota 429 from OpenRouter (as opposed to a briefly rate-limited model)."""
    if exc.status_code != 429:
        return None
    body = exc.body if isinstance(exc.body, dict) else {}
    error = body.get("error", body) if isinstance(body.get("error", body), dict) else {}
    metadata = error.get("metadata") or {}
    daily = metadata.get("limit_source") == "openrouter_free_tier_daily" or "per-day" in str(error.get("message", ""))
    if not daily:
        return None
    reset = (metadata.get("headers") or {}).get("X-RateLimit-Reset") or exc.response.headers.get("x-ratelimit-reset")
    try:
        resets_at = datetime.fromtimestamp(int(reset) / 1000, timezone.utc)
    except (TypeError, ValueError):
        resets_at = None
    return QuotaExhausted(resets_at)


@dataclass(frozen=True)
class LLMReply:
    text: str
    model: str  # the model that actually answered; a router such as openrouter/free picks one per request


class LLMClient(Protocol):
    model: str

    async def complete_json(self, system: str, user: str, attempt: int = 0) -> LLMReply: ...


class OpenAICompatibleLLM:
    """Chat completions against any OpenAI-compatible API (OpenRouter by default)."""

    def __init__(self, api_key: str, base_url: str, model: str, fallback_models: list[str] | None = None):
        self.model = model
        self.models = list(dict.fromkeys([model, *(fallback_models or [])]))
        self._base_url = base_url
        # Once the quota is used up, fail at once until it resets instead of calling the provider again.
        self._quota_exhausted: QuotaExhausted | None = None
        self._client = AsyncOpenAI(
            # Retries happen in the chat service, where each one is recorded and may reach another model.
            api_key=api_key, base_url=base_url, timeout=settings.llm_timeout_seconds, max_retries=0
        )

    @property
    def _is_openrouter(self) -> bool:
        return "openrouter.ai" in self._base_url

    def models_for(self, attempt: int) -> list[str]:
        """The configured models, starting at the one for this attempt: a retry goes to the next model."""
        start = attempt % len(self.models)
        return self.models[start:] + self.models[:start]

    def _extra_body(self, models: list[str] | None = None) -> dict | None:
        """OpenRouter-only request options: data policy, reasoning effort, and server-side fallbacks."""
        if not self._is_openrouter:
            return None
        body = dict(_OPENROUTER_DATA_POLICIES[settings.llm_data_policy] or {})
        if settings.llm_reasoning_effort:
            body["reasoning"] = {"effort": settings.llm_reasoning_effort}
        if models and len(models) > 1:
            body["models"] = models
        return body or None

    async def complete_json(self, system: str, user: str, attempt: int = 0) -> LLMReply:
        if self._quota_exhausted and not _passed(self._quota_exhausted.resets_at):
            raise self._quota_exhausted
        self._quota_exhausted = None
        models = self.models_for(attempt)
        try:
            completion = await self._client.chat.completions.create(
                model=models[0],
                temperature=0,
                max_tokens=settings.llm_max_output_tokens,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                extra_body=self._extra_body(models),
            )
        except openai.APIStatusError as exc:
            if quota := quota_exhaustion(exc):
                self._quota_exhausted = quota
                raise quota from exc
            error = Overloaded if exc.status_code in OVERLOAD_STATUSES else LLMError
            raise error(f"{models[0]}: {type(exc).__name__} ({exc.status_code})") from exc
        except openai.OpenAIError as exc:
            raise LLMError(type(exc).__name__) from exc
        choice = completion.choices[0] if completion.choices else None
        content = choice.message.content if choice else None
        # Reasoning models can spend the whole token budget thinking and return nothing, or stop mid-JSON.
        served_by = completion.model or models[0]
        if choice and choice.finish_reason == "length":
            raise LLMError(f"{served_by}: completion truncated at max tokens ({len(content or '')} chars of answer)")
        if not content:
            raise LLMError(f"{served_by}: empty completion")
        return LLMReply(content, served_by)


def _passed(moment: datetime | None) -> bool:
    """An unknown reset time is treated as passed, so the next request simply tries again."""
    return moment is None or moment.timestamp() <= time.time()
