import logging
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.chat.citations import GenerationResult, MalformedOutput, parse_and_validate
from app.modules.chat.schemas import AnswerStatus, ChatRequest, ChatResponse, Claim, Source
from app.modules.conversations.models import Conversation, Message
from app.modules.generation import providers
from app.modules.generation.llm import LLMError
from app.modules.generation.prompts import PROMPT_VERSION, system_prompt, user_prompt
from app.modules.query_understanding.scope import assess_scope
from app.modules.retrieval.service import hybrid_search

logger = logging.getLogger("taxora.chat")


class ConversationNotFound(Exception):
    """The conversation does not exist or belongs to another user."""


CHAT_COPY = {
    "en": {
        "insufficient": "The available evidence is not sufficient to verify an answer.",
        "failed": "The request could not be processed. Please try again.",
        "llm_unavailable": "The AI service is temporarily unavailable. No answer was generated.",
        "unconfigured": "Relevant sources were found, but the AI service is not configured. An answer cannot be prepared yet.",
        "api_key_required": "LLM_API_KEY must be configured to generate an evidence-based answer.",
        "no_evidence": "I could not find sufficient verified legal sources to answer. Please clarify the topic, transaction, or tax period; a definitive answer cannot be provided from the current knowledge base.",
        "no_verified_evidence": "The knowledge base does not contain relevant verified evidence.",
        "missing_period": "Tax period or transaction date (if the question is time-sensitive).",
        "out_of_scope": "I can only help with questions about Indonesian taxation, specifically Income Tax (PPh) and Value Added Tax (PPN). Please ask a tax question.",
        "claims_removed": "Some statements could not be verified against the sources and were removed.",
    },
    "id": {
        "insufficient": "Bukti yang tersedia belum cukup untuk memverifikasi jawaban.",
        "failed": "Permintaan belum dapat diproses. Silakan coba kembali.",
        "llm_unavailable": "Layanan AI sedang tidak tersedia. Tidak ada jawaban yang dibuat.",
        "unconfigured": "Sumber terkait ditemukan, tetapi layanan AI belum dikonfigurasi. Jawaban belum dapat disusun.",
        "api_key_required": "Konfigurasi LLM_API_KEY diperlukan untuk menghasilkan jawaban berbasis evidence.",
        "no_evidence": "Saya belum menemukan sumber hukum terverifikasi yang cukup untuk menjawab. Coba perjelas topik, transaksi, atau periode pajak; jawaban definitif tidak dapat diberikan dari knowledge base saat ini.",
        "no_verified_evidence": "Knowledge base belum memuat evidence terverifikasi yang relevan.",
        "missing_period": "Periode pajak atau tanggal transaksi (jika pertanyaan bergantung pada waktu).",
        "out_of_scope": "Saya hanya dapat membantu pertanyaan seputar perpajakan Indonesia, khususnya Pajak Penghasilan (PPh) dan Pajak Pertambahan Nilai (PPN). Silakan ajukan pertanyaan perpajakan.",
        "claims_removed": "Sebagian pernyataan tidak dapat diverifikasi terhadap sumber dan telah dihapus.",
    },
}


@dataclass
class Outcome:
    status: AnswerStatus
    answer: str
    claims: list[Claim] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    trace: dict = field(default_factory=dict)


async def answer_question(body: ChatRequest, session: AsyncSession, user: User) -> ChatResponse:
    started = time.monotonic()
    request_id = uuid.uuid4()
    conversation = await _conversation_for(body, session, user)
    session.add(Message(conversation_id=conversation.id, role="user", content=body.question,
                        metadata_json={"tax_period": body.context.tax_period, "taxpayer_type": body.context.taxpayer_type,
                                       "response_language": body.response_language}))

    outcome = await _decide(body, session, user, request_id)
    if outcome.status not in (AnswerStatus.out_of_scope, AnswerStatus.failed) and not body.context.tax_period:
        outcome.missing.append(CHAT_COPY[body.response_language]["missing_period"])

    latency_ms = round((time.monotonic() - started) * 1000)
    session.add(Message(conversation_id=conversation.id, role="assistant", content=outcome.answer,
                        metadata_json={"request_id": str(request_id), "answer_status": outcome.status.value,
                                       "evidence_ids": [str(item["id"]) for item in outcome.evidence],
                                       "cited_evidence_ids": [str(s.evidence_id) for s in outcome.sources],
                                       "latency_ms": latency_ms, "response_language": body.response_language,
                                       "prompt_version": PROMPT_VERSION, **outcome.trace}))
    await session.flush()
    return ChatResponse(request_id=request_id, conversation_id=conversation.id, answer_status=outcome.status,
                        answer=outcome.answer, claims=outcome.claims, sources=outcome.sources,
                        missing_information=outcome.missing, limitations=outcome.limitations, latency_ms=latency_ms)


async def _conversation_for(body: ChatRequest, session: AsyncSession, user: User) -> Conversation:
    if body.conversation_id:
        conversation = await session.get(Conversation, body.conversation_id)
        if conversation is None or conversation.user_id != user.id:
            raise ConversationNotFound
        return conversation
    conversation = Conversation(user_id=user.id, title=body.question[:120])
    session.add(conversation)
    await session.flush()
    return conversation


async def _decide(body: ChatRequest, session: AsyncSession, user: User, request_id: uuid.UUID) -> Outcome:
    """Scope guard → retrieval → LLM → citation validation. Each step can stop early."""
    copy = CHAT_COPY[body.response_language]
    embedder = providers.get_embedder()
    scope = await assess_scope(body.question, embedder)
    trace = {"scope": {"in_scope": scope.in_scope, "reason": scope.reason, "similarity": scope.similarity}}
    if not scope.in_scope:
        return Outcome(AnswerStatus.out_of_scope, copy["out_of_scope"], trace=trace)

    evidence = await hybrid_search(session, body.question, user.id, body.context.tax_period, embedder)
    if not evidence:
        return Outcome(AnswerStatus.insufficient_evidence, copy["no_evidence"],
                       limitations=[copy["no_verified_evidence"]], trace=trace)
    llm = providers.get_llm()
    if llm is None:
        return Outcome(AnswerStatus.insufficient_evidence, copy["unconfigured"],
                       limitations=[copy["api_key_required"]], evidence=evidence, trace=trace)

    trace["model"] = llm.model
    try:
        raw = await llm.complete_json(
            system_prompt(body.response_language),
            user_prompt(body.question, evidence, body.context.tax_period,
                        body.context.taxpayer_type, body.context.transaction_type),
        )
        result = parse_and_validate(raw, evidence)
    except LLMError as exc:
        logger.warning("llm call failed request_id=%s error=%s", request_id, exc)
        return Outcome(AnswerStatus.failed, copy["llm_unavailable"], evidence=evidence, trace=trace)
    except MalformedOutput as exc:
        logger.warning("llm output rejected request_id=%s error=%s", request_id, exc)
        return Outcome(AnswerStatus.failed, copy["failed"], evidence=evidence, trace=trace)
    trace["rejected_claims"] = result.rejected_claims
    return _from_generation(result, evidence, copy, trace)


def _from_generation(result: GenerationResult, evidence: list[dict], copy: dict, trace: dict) -> Outcome:
    if not result.in_scope:
        # The model's own text is discarded: only the fixed refusal is shown.
        return Outcome(AnswerStatus.out_of_scope, copy["out_of_scope"], evidence=evidence, trace=trace)
    if not result.claims:
        return Outcome(AnswerStatus.insufficient_evidence, copy["insufficient"],
                       limitations=result.limitations, evidence=evidence, trace=trace)
    limitations = result.limitations + ([copy["claims_removed"]] if result.rejected_claims else [])
    status = AnswerStatus.clarification_needed if result.missing_information else AnswerStatus.answered
    return Outcome(
        status,
        result.answer or copy["insufficient"],
        claims=[Claim(text=c.text, evidence_ids=c.evidence_ids, quote=c.quote) for c in result.claims],
        sources=build_sources(result.claims, evidence),
        missing=result.missing_information,
        limitations=limitations,
        evidence=evidence,
        trace=trace,
    )


def build_sources(claims, evidence: list[dict]) -> list[Source]:
    """One source per cited evidence item, quoting the verified passage rather than the chunk start."""
    by_id = {item["id"]: item for item in evidence}
    quotes: dict[uuid.UUID, str] = {}
    for claim in claims:
        for evidence_id in claim.evidence_ids:
            quotes.setdefault(evidence_id, claim.quote)
    return [
        Source(evidence_id=evidence_id, regulation_number=by_id[evidence_id]["regulation_number"],
               title=by_id[evidence_id]["title"], article=by_id[evidence_id]["article"], quote=quote,
               source_url=by_id[evidence_id]["source_url"], verification_status=by_id[evidence_id]["status"],
               effective_from=by_id[evidence_id]["effective_from"],
               effective_until=by_id[evidence_id]["effective_until"])
        for evidence_id, quote in quotes.items()
    ]
