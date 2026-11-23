from dataclasses import dataclass
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


@dataclass(frozen=True)
class LLMReply:
    text: str
    model: str  # the model that actually answered; a router such as openrouter/free picks one per request


class LLMClient(Protocol):
    model: str

    async def complete_json(self, system: str, user: str) -> LLMReply: ...


class OpenAICompatibleLLM:
    """Chat completions against any OpenAI-compatible API (OpenRouter by default)."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.model = model
        self._base_url = base_url
        self._client = AsyncOpenAI(
            # Retries happen in the chat service, where each one is recorded and may reach another model.
            api_key=api_key, base_url=base_url, timeout=settings.llm_timeout_seconds, max_retries=0
        )

    def _extra_body(self) -> dict | None:
        """OpenRouter-only request options: the data policy filter and the reasoning effort."""
        if "openrouter.ai" not in self._base_url:
            return None
        body = dict(_OPENROUTER_DATA_POLICIES[settings.llm_data_policy] or {})
        if settings.llm_reasoning_effort:
            body["reasoning"] = {"effort": settings.llm_reasoning_effort}
        return body or None

    async def complete_json(self, system: str, user: str) -> LLMReply:
        try:
            completion = await self._client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=settings.llm_max_output_tokens,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                extra_body=self._extra_body(),
            )
        except openai.OpenAIError as exc:
            raise LLMError(type(exc).__name__) from exc
        choice = completion.choices[0] if completion.choices else None
        content = choice.message.content if choice else None
        # Reasoning models can spend the whole token budget thinking and return nothing, or stop mid-JSON.
        if choice and choice.finish_reason == "length":
            raise LLMError(f"completion truncated at max tokens ({len(content or '')} chars of answer)")
        if not content:
            raise LLMError("empty completion")
        return LLMReply(content, completion.model or self.model)
