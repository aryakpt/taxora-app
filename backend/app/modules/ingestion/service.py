"""Ingestion workflow (PRD FR-09, §8.1).

    queued ─▶ processing ─▶ review_required ─(reviewer)─▶ approved ─(admin)─▶ published
                  └───────▶ failed ─(admin retry)─▶ queued

Processing runs in the background with its own database session, so a large document cannot time
out the admin's request. Nothing reaches retrieval until a version is published.
"""

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.generation import providers
from app.modules.ingestion import sources, storage
from app.modules.ingestion.extraction import ExtractionError, chunks, extract_text, structural_sections
from app.modules.ingestion.models import IngestionJob, JobStatus
from app.modules.ingestion.schemas import RegulationMetadata, VersionDates
from app.modules.regulations.models import DocumentChunk, LegalProvision, Regulation, RegulationVersion

logger = logging.getLogger("taxora.ingestion")


class JobNotFound(Exception):
    pass


class InvalidTransition(Exception):
    """The job is not in a state that allows the requested action. The message is safe to show."""


# --- submission ----------------------------------------------------------------------------

async def regulation_for(session: AsyncSession, metadata: RegulationMetadata) -> Regulation:
    """Find the regulation by type and number, or create it. New documents become its versions."""
    regulation_type = metadata.regulation_type.strip().upper()
    number = " ".join(metadata.regulation_number.split())
    query = select(Regulation).where(
        Regulation.regulation_type == regulation_type, Regulation.regulation_number == number
    )
    existing = await session.scalar(query)
    if existing:
        return existing
    regulation = Regulation(regulation_number=number, regulation_type=regulation_type, title=metadata.title.strip(),
                            issuer=metadata.issuer.strip(), topic=metadata.topic)
    try:
        async with session.begin_nested():
            session.add(regulation)
    except IntegrityError:  # created concurrently by another request
        return await session.scalar(query)
    return regulation


async def create_job(
    session: AsyncSession,
    user: User,
    metadata: RegulationMetadata,
    *,
    filename: str | None = None,
    storage_key: str | None = None,
) -> IngestionJob:
    regulation = await regulation_for(session, metadata)
    job = IngestionJob(
        source_url=str(metadata.source_url),
        filename=filename,
        status=JobStatus.queued.value,
        regulation_id=regulation.id,
        requested_by=user.id,
        storage_key=storage_key,
        metadata_json=metadata.version_metadata(),
    )
    session.add(job)
    await session.flush()
    session.add(AuditLog(actor_id=user.id, action="ingestion.created", resource_id=str(job.id)))
    return job


# --- background processing --------------------------------------------------------------------

async def run_job(job_id: uuid.UUID) -> None:
    """Process one queued job. Safe to call twice: only a queued job is claimed."""
    async with SessionLocal() as session:
        async with session.begin():
            job = await session.get(IngestionJob, job_id, with_for_update=True)
            if job is None or job.status != JobStatus.queued.value:
                return
            job.status, job.error, job.detail = JobStatus.processing.value, None, None
        try:
            await _ensure_stored(session, job_id)
            async with session.begin():
                await _index(session, await session.get(IngestionJob, job_id))
        except (sources.SourceRejected, ExtractionError) as exc:
            await _fail(session, job_id, str(exc))
        except Exception:
            logger.exception("ingestion failed job_id=%s", job_id)
            await _fail(session, job_id, "Kesalahan internal saat memproses dokumen. Lihat log server.")


async def _ensure_stored(session: AsyncSession, job_id: uuid.UUID) -> None:
    """Fetch and store the original once, committed separately so a retry never refetches it."""
    async with session.begin():
        job = await session.get(IngestionJob, job_id)
        if job.storage_key:
            return
        url = job.source_url
    content, filename = await sources.fetch_pdf(url)
    key = storage.save(content)
    async with session.begin():
        job = await session.get(IngestionJob, job_id)
        job.storage_key, job.filename = key, job.filename or filename


async def _index(session: AsyncSession, job: IngestionJob) -> None:
    existing = await session.scalar(select(RegulationVersion).where(
        RegulationVersion.regulation_id == job.regulation_id, RegulationVersion.document_hash == job.storage_key
    ))
    if existing:
        job.version_id, job.status = existing.id, existing.status
        job.detail = "Dokumen identik sudah pernah diproses; job ini memakai versi yang sudah ada."
        session.add(AuditLog(actor_id=job.requested_by, action="ingestion.duplicate", resource_id=str(job.id)))
        return

    text = extract_text(storage.load(job.storage_key))
    sections = structural_sections(text)
    meta = job.metadata_json
    version = RegulationVersion(
        regulation_id=job.regulation_id, source_url=job.source_url, document_hash=job.storage_key,
        storage_key=job.storage_key, status=JobStatus.review_required.value,
        issued_at=_date(meta.get("issued_at")), effective_from=_date(meta.get("effective_from")),
        effective_until=_date(meta.get("effective_until")), is_internal=bool(meta.get("is_internal")),
        allowed_user_ids=list(meta.get("allowed_user_ids", [])),
    )
    session.add(version)
    await session.flush()

    pieces: list[tuple[LegalProvision, str]] = []
    for ordinal, section in enumerate(sections):
        provision = LegalProvision(version_id=version.id, provision_type=section.kind,
                                   article_number=section.number, ordinal=ordinal, text=section.text)
        session.add(provision)
        pieces.extend((provision, piece) for piece in chunks(section.text))
    await session.flush()
    vectors = await providers.get_embedder().embed_many([piece for _, piece in pieces])
    session.add_all(
        DocumentChunk(provision_id=provision.id, chunk_text=piece, token_count=len(piece.split()), embedding=vector)
        for (provision, piece), vector in zip(pieces, vectors, strict=True)
    )
    job.version_id, job.status = version.id, JobStatus.review_required.value
    job.detail = f"{len(sections)} bagian diekstrak, {len(pieces)} potongan diindeks."
    session.add(AuditLog(actor_id=job.requested_by, action="ingestion.processed", resource_id=str(job.id)))


async def _fail(session: AsyncSession, job_id: uuid.UUID, message: str) -> None:
    async with session.begin():
        job = await session.get(IngestionJob, job_id)
        job.status, job.error = JobStatus.failed.value, message[:500]
        session.add(AuditLog(actor_id=job.requested_by, action="ingestion.failed", resource_id=str(job_id)))


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


async def recover_interrupted_jobs() -> int:
    """At startup, jobs left queued/processing by a stopped server are marked failed (retryable).

    Assumes a single API process: background jobs run in-process (FastAPI BackgroundTasks). With several
    workers, move processing to a dedicated job queue before relying on this.
    """
    async with SessionLocal() as session, session.begin():
        result = await session.execute(
            update(IngestionJob)
            .where(IngestionJob.status.in_([JobStatus.queued.value, JobStatus.processing.value]))
            .values(status=JobStatus.failed.value,
                    error="Proses terhenti karena server dimulai ulang. Gunakan retry untuk memproses ulang.")
        )
    return result.rowcount


# --- review workflow ---------------------------------------------------------------------------

async def _job_and_version(session: AsyncSession, job_id: uuid.UUID) -> tuple[IngestionJob, RegulationVersion | None]:
    job = await session.get(IngestionJob, job_id, with_for_update=True)
    if job is None:
        raise JobNotFound
    version = await session.get(RegulationVersion, job.version_id) if job.version_id else None
    return job, version


async def _move_version(
    session: AsyncSession, job_id: uuid.UUID, user: User, required: JobStatus, target: JobStatus
) -> IngestionJob:
    job, version = await _job_and_version(session, job_id)
    if version is None or version.status != required.value:
        current = version.status if version else job.status
        raise InvalidTransition(f"Hanya dokumen berstatus {required.value} yang bisa diubah ke {target.value} "
                                f"(status sekarang: {current}).")
    version.status = target.value
    if target is JobStatus.approved:
        version.verified_at = datetime.now(timezone.utc)
    # Every job that points at this version (duplicates included) follows its status.
    await session.execute(update(IngestionJob).where(IngestionJob.version_id == version.id)
                          .values(status=target.value))
    session.add(AuditLog(actor_id=user.id, action=f"ingestion.{target.value}", resource_id=str(job.id)))
    await session.flush()
    await session.refresh(job)
    return job


async def approve(session: AsyncSession, job_id: uuid.UUID, user: User) -> IngestionJob:
    return await _move_version(session, job_id, user, JobStatus.review_required, JobStatus.approved)


async def publish(session: AsyncSession, job_id: uuid.UUID, user: User) -> IngestionJob:
    return await _move_version(session, job_id, user, JobStatus.approved, JobStatus.published)


async def retry(session: AsyncSession, job_id: uuid.UUID, user: User) -> IngestionJob:
    job, _ = await _job_and_version(session, job_id)
    if job.status != JobStatus.failed.value:
        raise InvalidTransition(f"Hanya job berstatus failed yang bisa diulang (status sekarang: {job.status}).")
    job.status, job.error = JobStatus.queued.value, None
    session.add(AuditLog(actor_id=user.id, action="ingestion.retried", resource_id=str(job.id)))
    return job


async def update_dates(session: AsyncSession, job_id: uuid.UUID, user: User, dates: VersionDates) -> IngestionJob:
    """Correct the dates while the version is under review. After approval they are frozen, because the
    reviewer's approval covers them; a wrong date after that needs a new ingestion."""
    job, version = await _job_and_version(session, job_id)
    if version is None or version.status != JobStatus.review_required.value:
        raise InvalidTransition("Tanggal hanya bisa diubah saat dokumen berstatus review_required.")
    version.issued_at, version.effective_from, version.effective_until = (
        dates.issued_at, dates.effective_from, dates.effective_until)
    session.add(AuditLog(actor_id=user.id, action="ingestion.dates_updated", resource_id=str(job.id)))
    await session.flush()
    return job


# --- read models -------------------------------------------------------------------------------

async def describe(session: AsyncSession, job: IngestionJob) -> dict:
    regulation = await session.get(Regulation, job.regulation_id) if job.regulation_id else None
    version = await session.get(RegulationVersion, job.version_id) if job.version_id else None
    return {
        "id": job.id,
        "status": job.status,
        "source_url": job.source_url,
        "filename": job.filename,
        "error": job.error,
        "detail": job.detail,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "storage_available": bool(job.storage_key),
        "regulation": {"id": regulation.id, "type": regulation.regulation_type,
                       "number": regulation.regulation_number, "title": regulation.title,
                       "issuer": regulation.issuer, "topic": regulation.topic} if regulation else None,
        "version": {"id": version.id, "status": version.status, "document_hash": version.document_hash,
                    "issued_at": version.issued_at, "effective_from": version.effective_from,
                    "effective_until": version.effective_until, "verified_at": version.verified_at}
        if version else None,
    }


async def provisions(session: AsyncSession, job_id: uuid.UUID) -> list[dict]:
    """The extracted sections of the job's version, in document order, for the reviewer to check."""
    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise JobNotFound
    if job.version_id is None:
        return []
    chunk_counts = (
        select(DocumentChunk.provision_id, func.count().label("total"))
        .group_by(DocumentChunk.provision_id).subquery()
    )
    rows = (await session.execute(
        select(LegalProvision, func.coalesce(chunk_counts.c.total, 0))
        .outerjoin(chunk_counts, chunk_counts.c.provision_id == LegalProvision.id)
        .where(LegalProvision.version_id == job.version_id)
        .order_by(LegalProvision.ordinal)
    )).all()
    return [{"id": p.id, "kind": p.provision_type, "number": p.article_number, "text": p.text, "chunks": total}
            for p, total in rows]


async def list_jobs(session: AsyncSession) -> list[dict]:
    jobs = (await session.scalars(select(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(200))).all()
    return [await describe(session, job) for job in jobs]
