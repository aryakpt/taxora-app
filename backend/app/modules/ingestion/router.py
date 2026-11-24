import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Query, Response, status

from app.core.config import settings
from app.core.database import SessionDep
from app.modules.auth.dependencies import AdminUser, ReviewerUser
from app.modules.ingestion import service, storage
from app.modules.ingestion.models import IngestionJob, JobStatus
from app.modules.ingestion.schemas import MetadataCorrection, Rejection, UploadForm, UrlSubmission, VersionDates

router = APIRouter(prefix="/api/v1/admin/ingestion", tags=["admin"])


async def _job_or_404(session, job_id: uuid.UUID) -> IngestionJob:
    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "Job tidak ditemukan")
    return job


async def _start(job: IngestionJob, background: BackgroundTasks, session) -> None:
    """Process the job after the response (a long-running server), or before it (serverless hosting, where
    nothing is guaranteed to run once the response is sent; see INGESTION_INLINE)."""
    if not settings.ingestion_inline:
        background.add_task(service.run_job, job.id)
        return
    await session.commit()  # run_job uses its own session and must see the new job
    await service.run_job(job.id)
    await session.refresh(job)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_from_url(body: UrlSubmission, background: BackgroundTasks, session: SessionDep,
                          user: AdminUser):
    """Queue a document from an official PDF link. Processing continues after this response."""
    job = await service.create_job(session, user, body)
    await _start(job, background, session)
    return await service.describe(session, job)


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def create_from_upload(
    form: Annotated[UploadForm, Form()],
    background: BackgroundTasks,
    session: SessionDep,
    user: AdminUser,
):
    """Queue an uploaded PDF. `source_url` is optional: when given, it is the official link shown to users."""
    content = await form.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, f"Dokumen melebihi batas ukuran unggah ({settings.max_upload_bytes // 2**20} MB). "
                                 "Untuk dokumen besar, kirim tautan resminya.")
    if not content.startswith(b"%PDF"):
        raise HTTPException(415, "Hanya dokumen PDF yang diterima")
    try:
        key = await storage.save(content)
    except storage.StorageError as exc:
        raise HTTPException(503, str(exc)) from exc
    job = await service.create_job(session, user, form, filename=(form.file.filename or "upload.pdf")[:300],
                                   storage_key=key)
    await _start(job, background, session)
    return await service.describe(session, job)


@router.get("")
async def list_jobs(
    session: SessionDep,
    user: ReviewerUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    status: JobStatus | None = None,
    q: Annotated[str, Query(max_length=100)] = "",
):
    """Jobs for the Knowledge Admin table: newest first, paginated, filtered by status, searched by `q`."""
    return await service.list_jobs(session, page, page_size, status.value if status else None, q)


@router.get("/{job_id}")
async def get_job(job_id: uuid.UUID, session: SessionDep, user: ReviewerUser):
    return await service.describe(session, await _job_or_404(session, job_id))


@router.get("/{job_id}/provisions")
async def get_provisions(job_id: uuid.UUID, session: SessionDep, user: ReviewerUser):
    """Extracted sections, so the reviewer can compare them with the original document."""
    try:
        return await service.provisions(session, job_id)
    except service.JobNotFound as exc:
        raise HTTPException(404, "Job tidak ditemukan") from exc


@router.get("/{job_id}/document")
async def get_document(job_id: uuid.UUID, session: SessionDep, user: ReviewerUser):
    """The stored original PDF. Sent as a download, never rendered inline from the API origin."""
    job = await _job_or_404(session, job_id)
    if not job.storage_key:
        raise HTTPException(404, "Dokumen asli belum tersimpan")
    filename = "".join(c for c in (job.filename or "dokumen.pdf") if c.isalnum() or c in "._- ")[:100] or "dokumen.pdf"
    try:
        content = await storage.load(job.storage_key)
    except storage.DocumentNotFound as exc:
        raise HTTPException(404, "Dokumen asli tidak ditemukan di penyimpanan") from exc
    except storage.StorageError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    })


async def _transition(action, session, job_id: uuid.UUID, user):
    try:
        job = await action(session, job_id, user)
    except service.JobNotFound as exc:
        raise HTTPException(404, "Job tidak ditemukan") from exc
    except service.InvalidTransition as exc:
        raise HTTPException(409, str(exc)) from exc
    return await service.describe(session, job)


@router.post("/{job_id}/approve")
async def approve(job_id: uuid.UUID, session: SessionDep, user: ReviewerUser):
    """Reviewer confirms the extracted text and metadata match the official source."""
    return await _transition(service.approve, session, job_id, user)


@router.post("/{job_id}/publish")
async def publish(job_id: uuid.UUID, session: SessionDep, user: AdminUser):
    """Make an approved version available to retrieval and the regulation library."""
    return await _transition(service.publish, session, job_id, user)


@router.put("/{job_id}/dates")
async def update_dates(job_id: uuid.UUID, body: VersionDates, session: SessionDep, user: ReviewerUser):
    """Set the issued and effective dates while the version is under review."""
    return await _transition(lambda s, j, u: service.update_dates(s, j, u, body), session, job_id, user)


@router.put("/{job_id}/metadata")
async def correct_metadata(job_id: uuid.UUID, body: MetadataCorrection, session: SessionDep, user: AdminUser):
    """Correct the metadata of an approved or published document (dates, title, issuer, topic), with a reason."""
    return await _transition(lambda s, j, u: service.correct_metadata(s, j, u, body), session, job_id, user)


@router.post("/{job_id}/reject")
async def reject(job_id: uuid.UUID, body: Rejection, session: SessionDep, user: ReviewerUser):
    """Turn down a document under review, with the reason."""
    return await _transition(lambda s, j, u: service.reject(s, j, u, body), session, job_id, user)


@router.delete("/{job_id}")
async def delete_document(job_id: uuid.UUID, session: SessionDep, user: AdminUser):
    """Delete the document (any status except while processing): version, provisions, chunks, stored PDF."""
    try:
        return {"deleted": True, **await service.delete_document(session, job_id, user)}
    except service.JobNotFound as exc:
        raise HTTPException(404, "Job tidak ditemukan") from exc
    except service.InvalidTransition as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry(job_id: uuid.UUID, background: BackgroundTasks, session: SessionDep, user: AdminUser):
    result = await _transition(service.retry, session, job_id, user)
    if not settings.ingestion_inline:
        background.add_task(service.run_job, job_id)
        return result
    await session.commit()
    await service.run_job(job_id)
    return await service.describe(session, await _job_or_404(session, job_id))
