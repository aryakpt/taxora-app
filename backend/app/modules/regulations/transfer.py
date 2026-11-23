"""Copy published regulations, with their embeddings and original PDFs, from one database to another.

Used once to seed production from the development database: re-ingesting would spend the embedding quota
(about one request per chunk) and require reviewing every document again. Rows keep their ids, and existing
ids are skipped, so running it twice copies nothing new. Users are not copied: copied jobs lose their
requester (the column allows NULL), and nothing else refers to a user.
"""

from collections.abc import Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.modules.ingestion import storage
from app.modules.ingestion.models import IngestionJob
from app.modules.regulations.models import DocumentChunk, LegalProvision, Regulation, RegulationVersion

BATCH = 200


async def _rows(engine: AsyncEngine, statement) -> list[dict]:
    async with engine.connect() as connection:
        return [dict(row._mapping) for row in await connection.execute(statement)]


async def _insert(engine: AsyncEngine, table, rows: list[dict]) -> int:
    inserted = 0
    async with engine.begin() as connection:
        for start in range(0, len(rows), BATCH):
            result = await connection.execute(
                insert(table).values(rows[start:start + BATCH]).on_conflict_do_nothing(index_elements=["id"]))
            inserted += result.rowcount or 0
    return inserted


async def copy_published(source_url: str, target: AsyncEngine, source_documents: Path,
                         progress: Callable[[str], None] = print) -> dict:
    source = create_async_engine(source_url)
    try:
        versions = await _rows(source, select(RegulationVersion.__table__)
                               .where(RegulationVersion.status == "published"))
        version_ids = [row["id"] for row in versions]
        regulation_ids = {row["regulation_id"] for row in versions}
        if not version_ids:
            return {"versions": 0}
        regulations = await _rows(source, select(Regulation.__table__).where(Regulation.id.in_(regulation_ids)))
        provisions = await _rows(source, select(LegalProvision.__table__)
                                 .where(LegalProvision.version_id.in_(version_ids)))
        chunks = await _rows(source, select(DocumentChunk.__table__)
                             .where(DocumentChunk.provision_id.in_([row["id"] for row in provisions])))
        jobs = await _rows(source, select(IngestionJob.__table__).where(IngestionJob.version_id.in_(version_ids)))
    finally:
        await source.dispose()

    # Originals first: a copied version must never point to a file that is not there.
    local = storage.LocalStorage(source_documents)
    destination = storage.configured()
    keys = {row["storage_key"] for row in versions + jobs if row.get("storage_key")}
    for number, key in enumerate(sorted(keys), 1):
        await destination.put(key, await local.get(key))
        progress(f"  PDF {number}/{len(keys)} uploaded")

    for job in jobs:
        job["requested_by"] = None
    summary = {}
    for name, table, rows in (("regulations", Regulation.__table__, regulations),
                              ("versions", RegulationVersion.__table__, versions),
                              ("provisions", LegalProvision.__table__, provisions),
                              ("chunks", DocumentChunk.__table__, chunks),
                              ("jobs", IngestionJob.__table__, jobs)):
        summary[name] = f"{await _insert(target, table, rows)}/{len(rows)}"
        progress(f"  {name}: {summary[name]} inserted")
    summary["documents"] = len(keys)
    # Chunks the source never embedded (quota ran out) are copied without a vector; `reindex` on the target
    # embeds them with the target's own API key.
    summary["chunks_without_embedding"] = sum(1 for chunk in chunks if chunk["embedding"] is None)
    return summary
