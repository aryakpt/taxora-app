"""Decide, before retrieval and before any LLM call, whether a question is about Indonesian tax.

Two cheap checks, no LLM call (which keeps free-tier quota for real answers):
1. A tax-term match is always in scope.
2. Otherwise, the question's embedding must be close enough to a few tax-topic anchor sentences.

Off-topic questions that slip through still meet the LLM's own scope rule and citation checks.
"""

import math
import re
from dataclasses import dataclass

from app.core.config import settings
from app.modules.generation.embeddings import Embedder

TAX_TERMS = re.compile(
    r"\b(pajak|pph|ppn|ppnbm|npwp|pkp|spt|faktur|bupot|e-?bupot|bukti potong|dpp|djp|kup|pmk|tarif|"
    r"pemotongan|pemungutan|restitusi|tax|vat|withholding)\b",
    re.IGNORECASE,
)

ANCHORS = (
    "Pertanyaan tentang Pajak Penghasilan (PPh) di Indonesia",
    "Pertanyaan tentang Pajak Pertambahan Nilai (PPN) di Indonesia",
    "Tarif, subjek, objek, dan dasar pengenaan pajak",
    "Kewajiban perpajakan wajib pajak: NPWP, SPT, faktur pajak, bukti potong",
    "Peraturan perpajakan: undang-undang, PMK, peraturan Direktur Jenderal Pajak",
    "Indonesian income tax and value added tax rules",
)


@dataclass(frozen=True)
class ScopeDecision:
    in_scope: bool
    reason: str  # "tax_term" | "similarity" | "off_topic"
    similarity: float | None = None


_CACHE_ATTRIBUTE = "_taxora_scope_anchor_vectors"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


async def _anchor_vectors(embedder: Embedder) -> list[list[float]]:
    """Embedded once per embedder instance and cached on it."""
    vectors = getattr(embedder, _CACHE_ATTRIBUTE, None)
    if vectors is None:
        vectors = [await embedder.embed(anchor) for anchor in ANCHORS]
        setattr(embedder, _CACHE_ATTRIBUTE, vectors)
    return vectors


async def assess_scope(question: str, embedder: Embedder) -> ScopeDecision:
    if TAX_TERMS.search(question):
        return ScopeDecision(True, "tax_term")
    vector = await embedder.embed(question)
    similarity = max(_cosine(vector, anchor) for anchor in await _anchor_vectors(embedder))
    in_scope = similarity >= settings.scope_min_similarity
    return ScopeDecision(in_scope, "similarity" if in_scope else "off_topic", round(similarity, 3))
