import re
import uuid
from datetime import date

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.generation.embeddings import Embedder
from app.modules.regulations.models import DocumentChunk, LegalProvision, Regulation, RegulationVersion

RRF_K = 60
# Must match the expression of the GIN index (migration 0004) exactly, or the index is not used.
SIMPLE = literal_column("'simple'::regconfig")

# Question words that carry no legal meaning; dropping them keeps keyword matches meaningful.
STOPWORDS = frozenset(
    "yang dan di ke dari untuk atau pada dengan ini itu apa apakah berapa bagaimana kapan siapa mengapa kenapa "
    "saya kami kita anda adalah akan bisa dapat jika kalau tidak ada sudah juga atas oleh dalam tentang "
    "the a an is are of for to in on and or what how when which who does do my".split()
)


# Regulation numbers such as "39/PMK.03/2018" or "PER-11/PJ/2025". PostgreSQL's parser keeps them as one
# token, so they must stay whole in the query to match. Only letters, digits, "/", ".", "-" are kept.
REGULATION_NUMBER = re.compile(r"[^\W_]+(?:[/.-][^\W_]+)*/[^\W_]+(?:[/.-][^\W_]+)*")


def keyword_tsquery(question: str) -> str | None:
    """OR-query of meaningful terms. A plain AND query would demand every word of a long natural
    question, which almost never matches. Terms are reduced to letters and digits (plus whole
    regulation numbers), so the result is always valid to_tsquery syntax."""
    lowered = question.lower()
    numbers = REGULATION_NUMBER.findall(lowered)
    words = [t for t in re.findall(r"[^\W_]+", lowered) if len(t) >= 2 and t not in STOPWORDS]
    return " | ".join(dict.fromkeys(numbers + words)) or None


def temporal_reference_date(tax_period: str | None) -> date:
    try:
        year = int(tax_period[:4]) if tax_period else None
        return date(year, 12, 31) if year else date.today()
    except (ValueError, TypeError):
        return date.today()


async def hybrid_search(
    session: AsyncSession,
    query: str,
    user_id: uuid.UUID,
    tax_period: str | None,
    embedder: Embedder,
) -> list[dict]:
    """Keyword + vector search over published, effective, permitted chunks, fused with Reciprocal
    Rank Fusion. Each channel only returns chunks above its relevance threshold, so an unrelated
    question returns no evidence instead of the "least bad" chunks."""
    reference_date = temporal_reference_date(tax_period)
    base = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.chunk_text,
            LegalProvision.article_number,
            LegalProvision.paragraph_number,
            RegulationVersion.source_url,
            RegulationVersion.status,
            RegulationVersion.effective_from,
            RegulationVersion.effective_until,
            Regulation.regulation_number,
            Regulation.title,
        )
        .join(LegalProvision, DocumentChunk.provision_id == LegalProvision.id)
        .join(RegulationVersion, LegalProvision.version_id == RegulationVersion.id)
        .join(Regulation, RegulationVersion.regulation_id == Regulation.id)
        .where(
            RegulationVersion.status == "published",
            RegulationVersion.effective_from.is_(None) | (RegulationVersion.effective_from <= reference_date),
            RegulationVersion.effective_until.is_(None) | (RegulationVersion.effective_until >= reference_date),
            RegulationVersion.is_internal.is_(False) | RegulationVersion.allowed_user_ids.contains([str(user_id)]),
        )
    )
    candidate_limit = settings.retrieval_top_k * 3

    keyword_rows = []
    terms = keyword_tsquery(query)
    if terms:
        document = func.to_tsvector(SIMPLE, DocumentChunk.chunk_text)
        tsquery = func.to_tsquery(SIMPLE, terms)
        keyword_rows = (await session.execute(
            base.where(document.op("@@")(tsquery))
            # Normalization 2 divides by document length, so long attachments do not win on size alone.
            .order_by(func.ts_rank_cd(document, tsquery, 2).desc())
            .limit(candidate_limit)
        )).all()

    vector = await embedder.embed(query)
    distance = DocumentChunk.embedding.cosine_distance(vector)
    vector_rows = (await session.execute(
        base.where(DocumentChunk.embedding.is_not(None), distance <= settings.retrieval_max_cosine_distance)
        .order_by(distance)
        .limit(candidate_limit)
    )).all()

    scores: dict[uuid.UUID, tuple[object, float]] = {}
    for rows, weight in ((keyword_rows, settings.retrieval_keyword_weight), (vector_rows, 1.0)):
        for rank, row in enumerate(rows, 1):
            _, score = scores.get(row.chunk_id, (row, 0.0))
            scores[row.chunk_id] = (row, score + weight / (RRF_K + rank))
    ordered = sorted(scores.values(), key=lambda item: item[1], reverse=True)[: settings.retrieval_top_k]
    return [
        {
            "id": row.chunk_id,
            "text": row.chunk_text,
            "regulation": f"{row.regulation_number} — {row.title}",
            "article": f"Pasal {row.article_number}" if row.article_number else None,
            "paragraph": row.paragraph_number,
            "source_url": row.source_url,
            "status": row.status,
            "effective_from": row.effective_from,
            "effective_until": row.effective_until,
            "regulation_number": row.regulation_number,
            "title": row.title,
        }
        for row, _ in ordered
    ]
