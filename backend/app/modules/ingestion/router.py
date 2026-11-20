import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, status

from app.core.config import settings
from app.core.database import SessionDep
from app.modules.auth.dependencies import AdminUser, ReviewerUser
from app.modules.ingestion import service, storage
from app.modules.ingestion.models import IngestionJob
from app.modules.ingestion.schemas import RegulationMetadata, UploadForm

router = APIRouter(prefix="/api/v1/admin/ingestion", tags=["admin"])


async def _job_or_404(session, job_id: uuid.UUID) -> IngestionJob:
    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "Job tidak ditemukan")
    return job


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_from_url(body: RegulationMetadata, background: BackgroundTasks, session: SessionDep,
                          user: AdminUser):
    """Queue a document from an official PDF link. Processing continues after this response."""
    job = await service.create_job(session, user, body)
    background.add_task(service.run_job, job.id)
    return await service.describe(session, job)


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def create_from_upload(
    form: Annotated[UploadForm, Form()],
    background: BackgroundTasks,
    session: SessionDep,
    user: AdminUser,
):
    """Queue an uploaded PDF. `source_url` is still required: it is the official link shown to users."""
    content = await form.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "Dokumen melebihi batas ukuran")
    if not content.startswith(b"%PDF"):
        raise HTTPException(415, "Hanya dokumen PDF yang diterima")
    key = storage.save(content)
    job = await service.create_job(session, user, form, filename=(form.file.filename or "upload.pdf")[:300],
                                   storage_key=key)
    background.add_task(service.run_job, job.id)
    return await service.describe(session, job)


@router.get("")
async def list_jobs(session: SessionDep, user: ReviewerUser):
    return await service.list_jobs(session)


@router.get("/{job_id}")
async def get_job(job_id: uuid.UUID, session: SessionDep, user: ReviewerUser):
    return await service.describe(session, await _job_or_404(session, job_id))


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


@router.post("/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry(job_id: uuid.UUID, background: BackgroundTasks, session: SessionDep, user: AdminUser):
    result = await _transition(service.retry, session, job_id, user)
    background.add_task(service.run_job, job_id)
    return result
