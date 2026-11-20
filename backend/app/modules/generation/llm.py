from typing import Protocol

import openai
from openai import AsyncOpenAI

from app.core.config import settings


class LLMError(Exception):
    """The provider failed, timed out, or returned no content."""


class LLMClient(Protocol):
    model: str

    async def complete_json(self, system: str, user: str) -> str: ...


class OpenAICompatibleLLM:
    """Chat completions against any OpenAI-compatible API (OpenRouter by default)."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.model = model
        self._base_url = base_url
        self._client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=settings.llm_timeout_seconds, max_retries=1
        )

    def _extra_body(self) -> dict | None:
        if "openrouter.ai" in self._base_url and settings.llm_zero_data_retention:
            # Only route to providers that do not store prompts or use them for training.
            return {"provider": {"data_collection": "deny", "zdr": True}}
        return None

    async def complete_json(self, system: str, user: str) -> str:
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
        content = completion.choices[0].message.content if completion.choices else None
        if not content:
            raise LLMError("empty completion")
        return content
