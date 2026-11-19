import json
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.chat.schemas import AnswerStatus, ChatRequest, ChatResponse, Claim, Source
from app.modules.conversations.models import Conversation, Message
from app.modules.generation.provider import AIProvider
from app.modules.retrieval.service import hybrid_search


class ConversationNotFound(Exception):
    """The conversation does not exist or belongs to another user."""


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


async def answer_question(body: ChatRequest, session: AsyncSession, user: User) -> ChatResponse:
    started = time.monotonic()
    copy = CHAT_COPY[body.response_language]
    request_id = uuid.uuid4()
    conversation = await session.get(Conversation, body.conversation_id) if body.conversation_id else None
    if body.conversation_id and (conversation is None or conversation.user_id != user.id):
        raise ConversationNotFound
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
                                       "evidence_ids": [str(item["id"]) for item in evidence],
                                       "latency_ms": round((time.monotonic() - started) * 1000),
                                       "response_language": body.response_language})
    session.add(assistant)
    await session.flush()
    return ChatResponse(request_id=request_id, conversation_id=conversation.id, answer_status=answer_status,
                        answer=answer, claims=claims, sources=sources, missing_information=missing,
                        limitations=limitations, latency_ms=round((time.monotonic() - started) * 1000))
