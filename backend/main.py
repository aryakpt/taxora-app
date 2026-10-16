import json
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai import AIProvider
from backend.auth import admin_user, current_user
from backend.config import settings
from backend.db import get_session
from backend.ingestion import fetch_source, process_document
from backend.models import AuditLog, Conversation, DocumentChunk, Feedback, IngestionJob, LegalProvision, Message, Regulation, RegulationVersion, User
from backend.retrieval import hybrid_search
from backend.schemas import AnswerStatus, ChatRequest, ChatResponse, Claim, IngestionRequest, Source

app = FastAPI(title="Taxora API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])

CHAT_COPY = {
    "en": {
        "insufficient": "The available evidence is not sufficient to verify an answer.",
        "failed": "The request could not be processed. Please try again.",
        "unconfigured": "Relevant sources were found, but the AI service is not configured. An answer cannot be prepared yet.",
        "api_key_required": "OPENAI_API_KEY must be configured to generate an evidence-based answer.",
        "no_evidence": "I could not find sufficient verified legal sources to answer. Please clarify the topic, transaction, or tax period; a definitive answer cannot be provided from the current knowledge base.",
        "no_verified_evidence": "The knowledge base does not contain relevant verified evidence.",
        "missing_period": "Tax period or transaction date (if the question is time-sensitive).",
    },
    "id": {
        "insufficient": "Bukti yang tersedia belum cukup untuk memverifikasi jawaban.",
        "failed": "Permintaan belum dapat diproses. Silakan coba kembali.",
        "unconfigured": "Sumber terkait ditemukan, tetapi layanan AI belum dikonfigurasi. Jawaban belum dapat disusun.",
        "api_key_required": "Konfigurasi OPENAI_API_KEY diperlukan untuk menghasilkan jawaban berbasis evidence.",
        "no_evidence": "Saya belum menemukan sumber hukum terverifikasi yang cukup untuk menjawab. Coba perjelas topik, transaksi, atau periode pajak; jawaban definitif tidak dapat diberikan dari knowledge base saat ini.",
        "no_verified_evidence": "Knowledge base belum memuat evidence terverifikasi yang relevan.",
        "missing_period": "Periode pajak atau tanggal transaksi (jika pertanyaan bergantung pada waktu).",
    },
}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, session: AsyncSession = Depends(get_session), user: User = Depends(current_user)):
    started = time.monotonic()
    copy = CHAT_COPY[body.response_language]
    request_id = uuid.uuid4()
    conversation = await session.get(Conversation, body.conversation_id) if body.conversation_id else None
    if body.conversation_id and (conversation is None or conversation.user_id != user.id):
        raise HTTPException(404, "Percakapan tidak ditemukan")
    if conversation is None:
        conversation = Conversation(user_id=user.id, title=body.question[:120])
        session.add(conversation)
        await session.flush()
    session.add(Message(conversation_id=conversation.id, role="user", content=body.question,
                        metadata_json={"tax_period": body.context.tax_period, "taxpayer_type": body.context.taxpayer_type,
                                       "response_language": body.response_language}))
    evidence = await hybrid_search(session, body.question, user.id, body.context.tax_period)
    answer_status, claims, missing, limitations, answer = AnswerStatus.insufficient_evidence, [], [], [], ""
    sources = []
    if evidence:
        generated = await AIProvider().answer(body.question, evidence, body.context.tax_period, body.response_language)
        if generated:
            try:
                payload = json.loads(generated)
                valid_ids = {str(item["id"]) for item in evidence}
                for claim in payload.get("claims", []):
                    references = [uuid.UUID(ref) for ref in claim.get("evidence_ids", []) if ref in valid_ids]
                    if references:
                        claims.append(Claim(text=claim["text"], evidence_ids=references))
                answer = payload.get("answer", "")
                missing = payload.get("missing_information", [])
                limitations = payload.get("limitations", [])
                answer_status = AnswerStatus.clarification_needed if missing else AnswerStatus.answered
                if not claims:
                    answer_status = AnswerStatus.insufficient_evidence
                    answer = copy["insufficient"]
                cited_ids = {str(ref) for claim in claims for ref in claim.evidence_ids}
                sources = [Source(evidence_id=item["id"], regulation_number=item["regulation_number"], title=item["title"],
                                  article=item["article"], quote=item["text"][:600], source_url=item["source_url"],
                                  verification_status=item["status"], effective_from=item["effective_from"],
                                  effective_until=item["effective_until"])
                           for item in evidence if str(item["id"]) in cited_ids]
                if not sources:
                    answer_status = AnswerStatus.insufficient_evidence
                    answer = copy["insufficient"]
            except (ValueError, TypeError, KeyError):
                answer_status = AnswerStatus.failed
                answer = copy["failed"]
        else:
            answer = copy["unconfigured"]
            limitations.append(copy["api_key_required"])
    else:
        answer = copy["no_evidence"]
        limitations.append(copy["no_verified_evidence"])
    if not body.context.tax_period:
        missing.append(copy["missing_period"])
    assistant = Message(conversation_id=conversation.id, role="assistant", content=answer,
                         metadata_json={"request_id": str(request_id), "answer_status": answer_status.value,
                                        "evidence_ids": [str(item["id"]) for item in evidence], "latency_ms": round((time.monotonic()-started)*1000),
                                        "response_language": body.response_language})
    session.add(assistant)
    await session.flush()
    return ChatResponse(request_id=request_id, conversation_id=conversation.id, answer_status=answer_status,
                        answer=answer, claims=claims, sources=sources, missing_information=missing,
                        limitations=limitations, latency_ms=round((time.monotonic()-started)*1000))


@app.get("/api/v1/conversations")
async def conversations(session: AsyncSession = Depends(get_session), user: User = Depends(current_user)):
    rows = (await session.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()))).all()
    return [{"id": row.id, "title": row.title, "updated_at": row.updated_at} for row in rows]


@app.get("/api/v1/conversations/{conversation_id}")
async def conversation_detail(conversation_id: uuid.UUID, session: AsyncSession = Depends(get_session), user: User = Depends(current_user)):
    row = await session.get(Conversation, conversation_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    messages = (await session.scalars(select(Message).where(Message.conversation_id == row.id).order_by(Message.created_at))).all()
    return {"id": row.id, "title": row.title, "messages": [{"id": m.id, "role": m.role, "content": m.content, "metadata": m.metadata_json} for m in messages]}


@app.delete("/api/v1/conversations/{conversation_id}")
async def delete_conversation(conversation_id: uuid.UUID, session: AsyncSession = Depends(get_session), user: User = Depends(current_user)):
    row = await session.get(Conversation, conversation_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    await session.delete(row)
    return {"deleted": True}


@app.get("/api/v1/regulations")
async def regulations(session: AsyncSession = Depends(get_session), user: User = Depends(current_user)):
    rows = (await session.execute(select(Regulation, RegulationVersion).join(RegulationVersion).where(
        RegulationVersion.status == "published",
        ((RegulationVersion.is_internal.is_(False)) | RegulationVersion.allowed_user_ids.contains([str(user.id)]))
    ))).all()
    return [{"id": regulation.id, "number": regulation.regulation_number, "type": regulation.regulation_type,
             "title": regulation.title, "topic": regulation.topic, "version_id": version.id,
             "status": version.status, "source_url": version.source_url} for regulation, version in rows]


@app.get("/api/v1/regulations/{regulation_id}/provisions")
async def provisions(regulation_id: uuid.UUID, session: AsyncSession = Depends(get_session), user: User = Depends(current_user)):
    rows = (await session.execute(select(LegalProvision).join(RegulationVersion).where(
        RegulationVersion.regulation_id == regulation_id, RegulationVersion.status == "published",
        ((RegulationVersion.is_internal.is_(False)) | RegulationVersion.allowed_user_ids.contains([str(user.id)]))
    ))).scalars().all()
    return [{"id": p.id, "article_number": p.article_number, "paragraph_number": p.paragraph_number, "text": p.text} for p in rows]


@app.post("/api/v1/feedback")
async def feedback(body: dict, session: AsyncSession = Depends(get_session), user: User = Depends(current_user)):
    try:
        message_id = uuid.UUID(str(body["message_id"]))
        rating = body["rating"]
        if rating not in ("positive", "negative"):
            raise ValueError
    except (KeyError, ValueError):
        raise HTTPException(422, "Feedback tidak valid")
    message = await session.get(Message, message_id)
    conversation = await session.get(Conversation, message.conversation_id) if message else None
    if message is None or conversation is None or conversation.user_id != user.id or message.role != "assistant":
        raise HTTPException(404, "Jawaban tidak ditemukan")
    session.add(Feedback(user_id=user.id, message_id=message_id, rating=rating, reason=body.get("reason")))
    return {"saved": True}


@app.post("/api/v1/admin/ingestion")
async def create_ingestion(body: IngestionRequest, session: AsyncSession = Depends(get_session), user: User = Depends(admin_user)):
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
        version = await process_document(session, job, body.model_dump(mode="python"), content)
        job.status = "review_required"
    except Exception as exc:
        job.status, job.error = "failed", str(exc)[:500]
    return {"id": job.id, "status": job.status, "error": job.error}


@app.post("/api/v1/admin/ingestion/upload")
async def upload_ingestion(file: UploadFile = File(...), session: AsyncSession = Depends(get_session), user: User = Depends(admin_user)):
    if file.content_type != "application/pdf" or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Hanya dokumen PDF yang diterima")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "Dokumen melebihi batas ukuran")
    raise HTTPException(422, "Metadata peraturan harus disediakan melalui endpoint ingestion")


@app.get("/api/v1/admin/ingestion")
async def list_ingestion(session: AsyncSession = Depends(get_session), user: User = Depends(admin_user)):
    rows = (await session.scalars(select(IngestionJob).order_by(IngestionJob.created_at.desc()))).all()
    return [{"id": row.id, "source_url": row.source_url, "status": row.status, "error": row.error, "created_at": row.created_at} for row in rows]


@app.get("/api/v1/admin/ingestion/{job_id}")
async def get_ingestion(job_id: uuid.UUID, session: AsyncSession = Depends(get_session), user: User = Depends(admin_user)):
    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "Job tidak ditemukan")
    return {"id": job.id, "status": job.status, "error": job.error, "source_url": job.source_url}


async def set_ingestion_status(job_id: uuid.UUID, status: str, session: AsyncSession, user: User):
    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "Job tidak ditemukan")
    version = await session.scalar(select(RegulationVersion).where(RegulationVersion.regulation_id == job.regulation_id).order_by(RegulationVersion.created_at.desc()))
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


@app.post("/api/v1/admin/ingestion/{job_id}/approve")
async def approve_ingestion(job_id: uuid.UUID, session: AsyncSession = Depends(get_session), user: User = Depends(admin_user)):
    return await set_ingestion_status(job_id, "approved", session, user)


@app.post("/api/v1/admin/ingestion/{job_id}/publish")
async def publish_ingestion(job_id: uuid.UUID, session: AsyncSession = Depends(get_session), user: User = Depends(admin_user)):
    return await set_ingestion_status(job_id, "published", session, user)


@app.get("/api/v1/admin/evaluations")
async def evaluations(user: User = Depends(admin_user)):
    return {"available": False, "detail": "Dataset evaluasi hukum terverifikasi belum disediakan; tidak ada skor yang diklaim."}
