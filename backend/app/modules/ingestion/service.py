"""Ingestion workflow (PRD FR-09, §8.1).

    queued ─▶ processing ─▶ review_required ─(reviewer)─▶ approved ─(admin)─▶ published
                  └───────▶ failed ─(admin retry)─▶ queued

Processing runs in the background with its own database session, so a large document cannot time
out the admin's request. Nothing reaches retrieval until a version is published.
"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.generation import providers
from app.modules.generation.embeddings import EmbeddingError
from app.modules.ingestion import sources, storage
from app.modules.ingestion.extraction import ExtractionError, chunks, extract_text, structural_sections
from app.modules.ingestion.models import IngestionJob, JobStatus
from app.modules.ingestion.schemas import MetadataCorrection, RegulationMetadata, Rejection, VersionDates
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
        source_url=str(metadata.source_url) if metadata.source_url else None,
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
        except (EmbeddingError, storage.StorageError) as exc:  # outage or quota: retry processes it again
            await _fail(session, job_id, f"{exc} Gunakan retry untuk memproses ulang.")
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
    key = await storage.save(content)
    async with session.begin():
        job = await session.get(IngestionJob, job_id)
        job.storage_key, job.filename = key, job.filename or filename


async def _index(session: AsyncSession, job: IngestionJob) -> None:
    existing = await session.scalar(select(RegulationVersion).where(
        RegulationVersion.regulation_id == job.regulation_id, RegulationVersion.document_hash == job.storage_key
    ))
    if existing and existing.status == JobStatus.rejected.value:
        # The same file again after a rejection (one version per file): extract it afresh and review it again.
        await session.execute(delete(LegalProvision).where(LegalProvision.version_id == existing.id))
        sections = structural_sections(extract_text(await storage.load(job.storage_key)))
        detail = _summary(len(sections), await _build_provisions(session, existing, sections))
        existing.status, existing.verified_at = JobStatus.review_required.value, None
        await session.execute(update(IngestionJob).where(IngestionJob.version_id == existing.id)
                              .values(status=JobStatus.review_required.value))
        job.version_id, job.status, job.detail = existing.id, JobStatus.review_required.value, detail
        session.add(AuditLog(actor_id=job.requested_by, action="ingestion.resubmitted", resource_id=str(job.id)))
        return
    if existing:
        job.version_id, job.status = existing.id, existing.status
        job.detail = "Dokumen identik sudah pernah diproses; job ini memakai versi yang sudah ada."
        session.add(AuditLog(actor_id=job.requested_by, action="ingestion.duplicate", resource_id=str(job.id)))
        return

    text = extract_text(await storage.load(job.storage_key))
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

    piece_count = await _build_provisions(session, version, sections)
    job.version_id, job.status = version.id, JobStatus.review_required.value
    job.detail = _summary(len(sections), piece_count)
    session.add(AuditLog(actor_id=job.requested_by, action="ingestion.processed", resource_id=str(job.id)))


async def _build_provisions(session: AsyncSession, version: RegulationVersion, sections: list) -> int:
    """Store sections as provisions and their chunks with embeddings. Returns the number of chunks."""
    pieces: list[tuple[LegalProvision, str]] = []
    for ordinal, section in enumerate(sections):
        provision = LegalProvision(version_id=version.id, provision_type=section.kind,
                                   article_number=section.number, ordinal=ordinal, text=section.text)
        session.add(provision)
        pieces.extend((provision, piece) for piece in chunks(section.text))
    await session.flush()
    embedder = providers.get_embedder()
    if embedder is None:
        raise EmbeddingError("Layanan embedding belum dikonfigurasi (EMBEDDING_API_KEY atau LLM_API_KEY).")
    vectors = await embedder.embed_many([piece for _, piece in pieces])
    session.add_all(
        DocumentChunk(provision_id=provision.id, chunk_text=piece, token_count=len(piece.split()), embedding=vector)
        for (provision, piece), vector in zip(pieces, vectors, strict=True)
    )
    return len(pieces)


async def reindex(batch: int = 40, progress=None) -> int:
    """Embed every chunk that has no vector yet (after a model change, or a run stopped by a quota limit).
    Each batch is committed, so running it again continues where it stopped. Returns how many were embedded."""
    embedder = providers.get_embedder()
    if embedder is None:
        raise EmbeddingError("Layanan embedding belum dikonfigurasi (EMBEDDING_API_KEY atau LLM_API_KEY).")
    async with SessionLocal() as session:
        remaining = await session.scalar(select(func.count()).where(DocumentChunk.embedding.is_(None)))
    done = 0
    while True:
        async with SessionLocal() as session, session.begin():
            pending = (await session.scalars(
                select(DocumentChunk).where(DocumentChunk.embedding.is_(None)).order_by(DocumentChunk.id).limit(batch)
            )).all()
            if not pending:
                return done
            vectors = await embedder.embed_many([chunk.chunk_text for chunk in pending])
            for chunk, vector in zip(pending, vectors, strict=True):
                chunk.embedding = vector
        done += len(pending)
        if progress:
            progress(done, remaining)


def _summary(sections: int, pieces: int) -> str:
    return f"{sections} bagian diekstrak, {pieces} potongan diindeks."


async def reprocess(job_id: uuid.UUID) -> str:
    """Re-extract and re-index a version that is still under review, from the stored original. Used after
    the extractor improves. Approved or published versions are never changed: approval covers their text."""
    async with SessionLocal() as session, session.begin():
        job, version = await _job_and_version(session, job_id)
        if version is None or version.status != JobStatus.review_required.value:
            raise InvalidTransition("Hanya dokumen berstatus review_required yang bisa diproses ulang.")
        if not version.storage_key:
            raise InvalidTransition("Dokumen asli tidak tersimpan.")
        await session.execute(delete(LegalProvision).where(LegalProvision.version_id == version.id))
        sections = structural_sections(extract_text(await storage.load(version.storage_key)))
        detail = _summary(len(sections), await _build_provisions(session, version, sections))
        await session.execute(update(IngestionJob).where(IngestionJob.version_id == version.id).values(detail=detail))
        session.add(AuditLog(actor_id=None, action="ingestion.reprocessed", resource_id=str(job.id)))
    return detail


async def _fail(session: AsyncSession, job_id: uuid.UUID, message: str) -> None:
    async with session.begin():
        job = await session.get(IngestionJob, job_id)
        job.status, job.error = JobStatus.failed.value, message[:500]
        session.add(AuditLog(actor_id=job.requested_by, action="ingestion.failed", resource_id=str(job_id)))


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


async def recover_interrupted_jobs() -> int:
    """At startup, jobs left queued/processing by a stopped server are marked failed (retryable).

    On a single long-running server every such job is orphaned. On serverless hosting other instances may
    be processing right now, so only jobs untouched for INGESTION_STALE_MINUTES count (longer than a request
    may run).
    """
    stuck = IngestionJob.status.in_([JobStatus.queued.value, JobStatus.processing.value])
    if settings.ingestion_stale_minutes:
        stuck &= IngestionJob.updated_at < func.now() - timedelta(minutes=settings.ingestion_stale_minutes)
    async with SessionLocal() as session, session.begin():
        result = await session.execute(
            update(IngestionJob)
            .where(stuck)
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


REJECT_ACTION = "ingestion.rejected"


async def reject(session: AsyncSession, job_id: uuid.UUID, user: User, rejection: Rejection) -> IngestionJob:
    """A reviewer turns down a document under review, with the reason. It is never searched; an admin can
    delete it and submit a corrected one."""
    job, version = await _job_and_version(session, job_id)
    if version is None or version.status != JobStatus.review_required.value:
        current = version.status if version else job.status
        raise InvalidTransition(f"Hanya dokumen berstatus review_required yang bisa ditolak (status sekarang: {current}).")
    version.status = JobStatus.rejected.value
    await session.execute(update(IngestionJob).where(IngestionJob.version_id == version.id)
                          .values(status=JobStatus.rejected.value))
    session.add(AuditLog(actor_id=user.id, action=REJECT_ACTION, resource_id=str(job.id),
                         details={"reason": rejection.reason.strip()}))
    await session.flush()
    await session.refresh(job)
    return job


async def delete_document(session: AsyncSession, job_id: uuid.UUID, user: User) -> dict:
    """Delete a document: its version with provisions and chunks (database cascade), every job pointing to
    that version, the regulation if it has no other version left, and the stored PDF if nothing else uses it.
    Published documents can be deleted too: chat stops citing them at once. Jobs still being processed
    cannot be deleted. Answers already given keep their stored sources."""
    job, version = await _job_and_version(session, job_id)
    if job.status in (JobStatus.queued.value, JobStatus.processing.value):
        raise InvalidTransition("Dokumen yang masih diproses tidak bisa dihapus; tunggu sampai selesai.")
    regulation = await session.get(Regulation, job.regulation_id) if job.regulation_id else None
    jobs = (await session.scalars(select(IngestionJob).where(IngestionJob.version_id == version.id))).all() \
        if version else [job]
    keys = {key for key in [version.storage_key if version else None, *(j.storage_key for j in jobs)] if key}
    summary = {"regulation": f"{regulation.regulation_type} {regulation.regulation_number}" if regulation else None,
               "title": regulation.title if regulation else None, "status": version.status if version else job.status,
               "jobs": len(jobs)}
    for item in jobs:
        await session.delete(item)
    if version:
        await session.delete(version)
    await session.flush()
    if regulation and not await session.scalar(
            select(func.count()).select_from(RegulationVersion).where(RegulationVersion.regulation_id == regulation.id)):
        if not await session.scalar(select(func.count()).select_from(IngestionJob)
                                    .where(IngestionJob.regulation_id == regulation.id)):
            await session.delete(regulation)
    await session.flush()
    for key in keys:  # keep files another job or version still uses
        still_used = await session.scalar(select(func.count()).select_from(IngestionJob)
                                          .where(IngestionJob.storage_key == key)) or \
            await session.scalar(select(func.count()).select_from(RegulationVersion)
                                 .where(RegulationVersion.storage_key == key))
        if not still_used:
            await storage.delete(key)
    session.add(AuditLog(actor_id=user.id, action="ingestion.deleted", resource_id=str(job.id), details=summary))
    return summary


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


CORRECTABLE = (JobStatus.approved.value, JobStatus.published.value)
CORRECTION_ACTION = "ingestion.metadata_corrected"


async def correct_metadata(session: AsyncSession, job_id: uuid.UUID, user: User,
                           correction: MetadataCorrection) -> IngestionJob:
    """Fix wrong metadata of an approved or published document, with a reason. Old and new values are kept
    in the audit log. A published document stays published: retrieval uses the new dates immediately."""
    job, version = await _job_and_version(session, job_id)
    if version is None or version.status not in CORRECTABLE:
        raise InvalidTransition("Koreksi metadata hanya untuk dokumen yang sudah disetujui atau dipublikasikan. "
                                "Selama ditinjau, ubah tanggal lewat formulir tinjauan.")
    regulation = await session.get(Regulation, version.regulation_id)
    wanted = {
        "title": correction.title.strip(), "issuer": correction.issuer.strip(), "topic": correction.topic,
        "issued_at": correction.issued_at, "effective_from": correction.effective_from,
        "effective_until": correction.effective_until,
    }
    targets = {"title": regulation, "issuer": regulation, "topic": regulation,
               "issued_at": version, "effective_from": version, "effective_until": version}
    changes = {}
    for field_name, new in wanted.items():
        old = getattr(targets[field_name], field_name)
        if old != new:
            changes[field_name] = {"old": _plain(old), "new": _plain(new)}
            setattr(targets[field_name], field_name, new)
    if not changes:
        raise InvalidTransition("Tidak ada perubahan metadata.")
    session.add(AuditLog(actor_id=user.id, action=CORRECTION_ACTION, resource_id=str(job.id),
                         details={"reason": correction.reason.strip(), "changes": changes}))
    await session.flush()
    return job


def _plain(value):
    return value.isoformat() if isinstance(value, date) else value


async def rejection(session: AsyncSession, job_id: uuid.UUID) -> dict | None:
    row = (await session.execute(
        select(AuditLog, User.email).outerjoin(User, AuditLog.actor_id == User.id)
        .where(AuditLog.resource_id == str(job_id), AuditLog.action == REJECT_ACTION)
        .order_by(AuditLog.created_at.desc()).limit(1)
    )).first()
    return {"at": row[0].created_at, "by": row[1], "reason": (row[0].details or {}).get("reason")} if row else None


async def corrections(session: AsyncSession, job_id: uuid.UUID) -> list[dict]:
    rows = (await session.execute(
        select(AuditLog, User.email).outerjoin(User, AuditLog.actor_id == User.id)
        .where(AuditLog.resource_id == str(job_id), AuditLog.action == CORRECTION_ACTION)
        .order_by(AuditLog.created_at.desc())
    )).all()
    return [{"at": log.created_at, "by": email, **(log.details or {})} for log, email in rows]


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
        "corrections": await corrections(session, job.id),
        "rejection": await rejection(session, job.id),
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


def _search(text: str):
    """Every word must appear in the regulation type, number, or title, or in the file name or link."""
    conditions = []
    for word in text.split():
        pattern = "%" + word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(or_(*(column.ilike(pattern, escape="\\") for column in (
            Regulation.regulation_type, Regulation.regulation_number, Regulation.title,
            IngestionJob.filename, IngestionJob.source_url))))
    return and_(*conditions)


async def list_jobs(session: AsyncSession, page: int = 1, page_size: int = 10, status: str | None = None,
                    search: str = "") -> dict:
    """One page of jobs, newest first, optionally filtered by status and searched; with the count per status
    (for the filter) and the total that matches."""
    query = select(IngestionJob).outerjoin(Regulation, Regulation.id == IngestionJob.regulation_id)
    if search.strip():
        query = query.where(_search(search))
    counts = dict((await session.execute(
        query.with_only_columns(IngestionJob.status, func.count()).group_by(IngestionJob.status))).all())
    if status:
        query = query.where(IngestionJob.status == status)
    total = await session.scalar(query.with_only_columns(func.count()))
    jobs = (await session.scalars(query.order_by(IngestionJob.created_at.desc(), IngestionJob.id)
                                  .offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [await describe(session, job) for job in jobs], "total": total, "page": page,
            "page_size": page_size, "status_counts": counts}
