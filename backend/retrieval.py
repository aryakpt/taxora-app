from datetime import date

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai import AIProvider
from backend.config import settings
from backend.models import DocumentChunk, LegalProvision, Regulation, RegulationVersion


async def hybrid_search(session: AsyncSession, query: str, user_id, tax_period: str | None) -> list[dict]:
    ai = AIProvider()
    vector = await ai.embed(query)
    today = date.today()
    try:
        year = int(tax_period[:4]) if tax_period else today.year
        temporal_date = date(year, 12, 31)
    except (ValueError, TypeError):
        temporal_date = today
    base = select(
        DocumentChunk.id.label("chunk_id"), DocumentChunk.chunk_text, LegalProvision.id.label("provision_id"),
        LegalProvision.article_number, LegalProvision.paragraph_number, RegulationVersion.id.label("version_id"),
        RegulationVersion.source_url, RegulationVersion.status, RegulationVersion.effective_from,
        RegulationVersion.effective_until, RegulationVersion.is_internal, RegulationVersion.allowed_user_ids,
        Regulation.regulation_number, Regulation.title,
    ).join(LegalProvision, DocumentChunk.provision_id == LegalProvision.id).join(
        RegulationVersion, LegalProvision.version_id == RegulationVersion.id
    ).join(Regulation, RegulationVersion.regulation_id == Regulation.id).where(
        RegulationVersion.status == "published",
        (RegulationVersion.effective_from.is_(None) | (RegulationVersion.effective_from <= temporal_date)),
        (RegulationVersion.effective_until.is_(None) | (RegulationVersion.effective_until >= temporal_date)),
        ((RegulationVersion.is_internal.is_(False)) | RegulationVersion.allowed_user_ids.contains([str(user_id)])),
    )
    keyword_rows = (await session.execute(base.order_by(func.ts_rank_cd(
        func.to_tsvector("simple", DocumentChunk.chunk_text), func.plainto_tsquery("simple", query)
    ).desc()).limit(settings.retrieval_top_k * 3))).all()
    vector_rows = []
    if vector:
        vector_rows = (await session.execute(base.order_by(DocumentChunk.embedding.cosine_distance(vector)).limit(
            settings.retrieval_top_k * 3
        ))).all()
    # Reciprocal Rank Fusion keeps the two independent retrieval channels inspectable.
    ranks: dict[str, tuple[object, float]] = {}
    for rows in (keyword_rows, vector_rows):
        for rank, row in enumerate(rows, 1):
            key = str(row.chunk_id)
            old = ranks.get(key, (row, 0.0))
            ranks[key] = (row, old[1] + 1 / (60 + rank))
    ordered = sorted(ranks.values(), key=lambda item: item[1], reverse=True)[:settings.retrieval_top_k]
    return [{
        "id": row.chunk_id, "text": row.chunk_text, "regulation": f"{row.regulation_number} — {row.title}",
        "article": f"Pasal {row.article_number}" if row.article_number else None,
        "paragraph": row.paragraph_number, "source_url": row.source_url, "status": row.status,
        "effective_from": row.effective_from, "effective_until": row.effective_until,
        "regulation_number": row.regulation_number, "title": row.title,
    } for row, _ in ordered]
