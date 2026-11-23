"""Test doubles for AI providers. Labeled fixtures: none of this is real legal content."""

from app.modules.generation.llm import LLMReply

TAX_WORDS = ("pajak", "tax", "pph", "ppn", "gaji", "potong", "faktur", "tarif", "sewa", "penghasilan")


def fake_vector(text_value: str) -> list[float]:
    """Deterministic stand-in for real embeddings: tax-related text points one way, the rest another."""
    vector = [0.0] * 384
    vector[0 if any(word in text_value.lower() for word in TAX_WORDS) else 1] = 1.0
    return vector


class FakeEmbedder:
    async def embed(self, text_value: str) -> list[float]:
        return fake_vector(text_value)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [fake_vector(text_value) for text_value in texts]


class FakeLLM:
    """`response` is the reply (or exception) for every call; a list gives one per call, the last repeating."""

    model = "fake-router"

    def __init__(self):
        self.response: str | Exception | list[str | Exception] = "{}"
        self.calls: list[tuple[str, str]] = []

    async def complete_json(self, system: str, user: str) -> LLMReply:
        self.calls.append((system, user))
        responses = self.response if isinstance(self.response, list) else [self.response]
        result = responses[min(len(self.calls), len(responses)) - 1]
        if isinstance(result, Exception):
            raise result
        return LLMReply(result, f"fake-model-{len(self.calls)}")
