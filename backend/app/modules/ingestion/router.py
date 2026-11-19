import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionDep
from app.modules.audit.models import AuditLog
from app.modules.auth.dependencies import AdminUser
from app.modules.auth.models import User
from app.modules.ingestion.models import IngestionJob
from app.modules.ingestion.pipeline import fetch_source, process_document
from app.modules.ingestion.schemas import IngestionRequest
from app.modules.regulations.models import Regulation, RegulationVersion

router = APIRouter(prefix="/api/v1/admin/ingestion", tags=["admin"])


@router.post("")
async def create_ingestion(body: IngestionRequest, session: SessionDep, user: AdminUser):
    regulation = Regulation(regulation_number=body.regulation_number, regulation_type=body.regulation_type,
                            title=body.title, issuer=body.issuer, topic=body.topic)
    session.add(regulation)
    await session.flush()
    job = IngestionJob(source_url=str(body.source_url), status="queued", regulation_id=regulation.id)
    session.add(job)
    await session.flush()
    session.add(AuditLog(actor_id=user.id, action="ingestion.created", resource_id=str(job.id)))
    try:
        content, filename = await fetch_source(str(body.source_url))
        job.filename, job.status = filename, "processing"
        await process_document(session, job, body.model_dump(mode="python"), content)
        job.status = "review_required"
    except Exception as exc:
        job.status, job.error = "failed", str(exc)[:500]
    return {"id": job.id, "status": job.status, "error": job.error}


@router.post("/upload")
async def upload_ingestion(user: AdminUser, file: UploadFile = File(...)):
    if file.content_type != "application/pdf" or not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Hanya dokumen PDF yang diterima")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "Dokumen melebihi batas ukuran")
    raise HTTPException(422, "Metadata peraturan harus disediakan melalui endpoint ingestion")


@router.get("")
async def list_ingestion(session: SessionDep, user: AdminUser):
    rows = (await session.scalars(select(IngestionJob).order_by(IngestionJob.created_at.desc()))).all()
    return [{"id": row.id, "source_url": row.source_url, "status": row.status, "error": row.error,
             "created_at": row.created_at} for row in rows]


@router.get("/{job_id}")
async def get_ingestion(job_id: uuid.UUID, session: SessionDep, user: AdminUser):
    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "Job tidak ditemukan")
    return {"id": job.id, "status": job.status, "error": job.error, "source_url": job.source_url}


async def set_ingestion_status(job_id: uuid.UUID, status: str, session: AsyncSession, user: User):
    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "Job tidak ditemukan")
    version = await session.scalar(
        select(RegulationVersion)
        .where(RegulationVersion.regulation_id == job.regulation_id)
        .order_by(RegulationVersion.created_at.desc())
    )
    if version is None:
        raise HTTPException(409, "Versi dokumen belum berhasil diproses")
    if status == "published" and version.status != "approved":
        raise HTTPException(409, "Dokumen harus disetujui sebelum dipublikasikan")
    version.status = status
    if status == "approved":
        version.verified_at = datetime.now(timezone.utc)
        job.status = "approved"
    else:
        job.status = "published"
    session.add(AuditLog(actor_id=user.id, action=f"ingestion.{status}", resource_id=str(job.id)))
    return {"id": job.id, "status": job.status}


@router.post("/{job_id}/approve")
async def approve_ingestion(job_id: uuid.UUID, session: SessionDep, user: AdminUser):
    return await set_ingestion_status(job_id, "approved", session, user)


@router.post("/{job_id}/publish")
async def publish_ingestion(job_id: uuid.UUID, session: SessionDep, user: AdminUser):
    return await set_ingestion_status(job_id, "published", session, user)
