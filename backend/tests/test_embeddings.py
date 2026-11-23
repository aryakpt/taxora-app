"""The API embedder: batching, pacing, retries, and failures (mock transport, no network)."""

import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.modules.generation import embeddings
from app.modules.generation.embeddings import ApiEmbedder, EmbeddingError

QUOTA_429 = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                       "message": "Embed content tokens per minute limit exceeded on Free Tier. Please retry in 43.79s."}}


def embedder_with(responses, dims=4, **options):
    """`responses`: list of (status, body or None); None body = echo one vector per input."""
    sent = []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        status, body = responses[min(len(sent), len(responses)) - 1]
        if body is None:
            body = {"object": "list", "model": payload["model"], "data": [
                {"object": "embedding", "index": i, "embedding": [float(len(sent)), 0.0, 0.0, float(i)][:dims]}
                for i in range(len(payload["input"]))]}
        return httpx.Response(status, json=body)

    client = AsyncOpenAI(api_key="k", base_url="https://example.test/v1", max_retries=0,
                         http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return ApiEmbedder("k", "https://example.test/v1", "gemini-embedding-001", 4, client=client, **options), sent


@pytest.fixture
def slept(monkeypatch):
    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(embeddings.asyncio, "sleep", fake_sleep)
    return waits


async def test_texts_are_batched_by_size_and_estimated_tokens():
    embedder, sent = embedder_with([(200, None)], batch_tokens=300, batch_size=3)

    vectors = await embedder.embed_many(["a" * 600, "b" * 600, "c", "d", "e", "f"])

    assert [len(request["input"]) for request in sent] == [1, 3, 2]  # 600 chars ~ 208 tokens: "a" alone; then 3 per batch
    assert len(vectors) == 6 and sent[0]["dimensions"] == 4 and sent[0]["model"] == "gemini-embedding-001"


async def test_a_rate_limit_waits_for_the_delay_the_provider_asks_for(slept):
    embedder, sent = embedder_with([(429, QUOTA_429), (200, None)])

    vectors = await embedder.embed_many(["pasal satu", "pasal dua"])

    assert len(sent) == 2 and len(vectors) == 2
    assert slept == [pytest.approx(44.79)]


async def test_a_rate_limit_that_does_not_clear_becomes_an_error(slept):
    embedder, _ = embedder_with([(429, QUOTA_429)], max_wait_seconds=100)

    with pytest.raises(EmbeddingError, match="Batas pemakaian"):
        await embedder.embed_many(["pasal"])
    assert sum(slept) <= 100


@pytest.mark.parametrize("status", [400, 401, 500])
async def test_provider_errors_become_embedding_errors(status):
    embedder, _ = embedder_with([(status, {"error": {"message": "nope"}})])

    with pytest.raises(EmbeddingError):
        await embedder.embed("pasal")


async def test_vectors_of_the_wrong_size_are_rejected():
    embedder, _ = embedder_with([(200, None)], dims=3)

    with pytest.raises(EmbeddingError, match="tidak sesuai"):
        await embedder.embed("pasal")


async def test_the_same_question_is_embedded_once():
    embedder, sent = embedder_with([(200, None)])

    first = await embedder.embed("Berapa tarif PPN?")
    second = await embedder.embed("Berapa tarif PPN?")

    assert first == second and len(sent) == 1


async def test_requests_are_paced_under_the_tokens_per_minute_budget(slept, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: clock[0])

    async def advancing_sleep(seconds):
        slept.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(embeddings.asyncio, "sleep", advancing_sleep)
    embedder, sent = embedder_with([(200, None)], tokens_per_minute=500, batch_tokens=400)

    await embedder.embed_many(["x" * 1000, "y" * 1000])  # ~341 tokens each: one per batch, two batches

    assert len(sent) == 2
    assert sum(slept) >= 59  # the second batch waited for the first minute to pass


async def test_gemini_responses_without_an_index_keep_the_input_order():
    """Gemini's OpenAI-compatible endpoint answers with "index": null on every item."""
    def handler(request):
        inputs = json.loads(request.content)["input"]
        return httpx.Response(200, json={"object": "list", "model": "gemini-embedding-001", "data": [
            {"object": "embedding", "index": None, "embedding": [float(i), 1.0, 0.0, 0.0]} for i in range(len(inputs))]})

    client = AsyncOpenAI(api_key="k", base_url="https://example.test/v1", max_retries=0,
                         http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    embedder = ApiEmbedder("k", "https://example.test/v1", "gemini-embedding-001", 4, client=client)

    vectors = await embedder.embed_many(["pertama", "kedua", "ketiga"])

    assert [vector[0] for vector in vectors] == [0.0, 1.0, 2.0]
