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

# No country names: "Indonesia" in an anchor made every question about Indonesia look like tax
# ("Siapa presiden pertama Indonesia?" scored 0.52). The last two cover tax questions in everyday words.
ANCHORS = (
    "Pertanyaan tentang Pajak Penghasilan (PPh)",
    "Pertanyaan tentang Pajak Pertambahan Nilai (PPN)",
    "Tarif, subjek, objek, dan dasar pengenaan pajak",
    "Kewajiban perpajakan wajib pajak: NPWP, SPT, faktur pajak, bukti potong",
    "Peraturan perpajakan: undang-undang, PMK, peraturan Direktur Jenderal Pajak",
    "Income tax and value added tax rules",
    "Potongan atas gaji, honorarium, sewa, jasa, dan hadiah yang disetor ke negara",
    "Pengembalian kelebihan pembayaran dan pelaporan penghasilan tahunan",
)

# General non-tax topics. With API embeddings every question scores high against the tax anchors (0.5-0.8),
# so the decision is the margin: closeness to tax minus closeness to these. Written as topics, not copies of
# test questions. Wording avoids tax vocabulary ("upah", not "gaji").
OTHER_ANCHORS = (
    "Pertanyaan umum tentang politik, sejarah, tokoh, dan pemerintahan",
    "Pengurusan dokumen kependudukan, perizinan, dan layanan publik",
    "Resep, makanan, minuman, dan memasak",
    "Hiburan, olahraga, film, musik, dan wisata",
    "Kesehatan, pendidikan, dan kehidupan sehari-hari",
    "Investasi, harga pasar, dan upah minimum",
    "Salam, obrolan ringan, dan permintaan menulis puisi atau cerita",
)


@dataclass(frozen=True)
class ScopeDecision:
    in_scope: bool
    reason: str  # "tax_term" | "similarity" | "off_topic"; chat also records "follow_up" (see chat/service.py)
    similarity: float | None = None  # margin: closeness to tax anchors minus closeness to other anchors


_CACHE_ATTRIBUTE = "_taxora_scope_anchor_vectors"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


async def _anchor_vectors(embedder: Embedder) -> tuple[list[list[float]], list[list[float]]]:
    """(tax anchors, other anchors), embedded once per embedder instance and cached on it."""
    vectors = getattr(embedder, _CACHE_ATTRIBUTE, None)
    if vectors is None:
        embedded = await embedder.embed_many([*ANCHORS, *OTHER_ANCHORS])
        vectors = (embedded[:len(ANCHORS)], embedded[len(ANCHORS):])
        setattr(embedder, _CACHE_ATTRIBUTE, vectors)
    return vectors


async def assess_scope(question: str, embedder: Embedder | None) -> ScopeDecision:
    if TAX_TERMS.search(question):
        return ScopeDecision(True, "tax_term")
    if embedder is None:  # no embedding service configured: only tax terms can pass
        return ScopeDecision(False, "off_topic")
    vector = await embedder.embed(question)
    tax, other = await _anchor_vectors(embedder)
    margin = max(_cosine(vector, a) for a in tax) - max(_cosine(vector, a) for a in other)
    in_scope = margin >= settings.scope_min_margin
    return ScopeDecision(in_scope, "similarity" if in_scope else "off_topic", round(margin, 3))
