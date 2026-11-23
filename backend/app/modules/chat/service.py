import logging
import time
import uuid
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.auth.models import User
from app.modules.chat.citations import GenerationResult, MalformedOutput, parse_and_validate
from app.modules.chat.schemas import AnswerStatus, ChatRequest, ChatResponse, Claim, Source
from app.modules.conversations.models import Conversation, Message
from app.modules.generation import providers
from app.modules.generation.llm import LLMClient, LLMError, QuotaExhausted
from app.modules.generation.prompts import PROMPT_VERSION, Turn, system_prompt, user_prompt
from app.modules.query_understanding.period import reference_date
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
        "quota_exhausted": "Today's quota for the AI service has been used up, so no answer was generated. It resets at {time}.",
        "quota_exhausted_unknown": "The quota for the AI service has been used up, so no answer was generated. Please try again later.",
        "unconfigured": "Relevant sources were found, but the AI service is not configured. An answer cannot be prepared yet.",
        "api_key_required": "LLM_API_KEY must be configured to generate an evidence-based answer.",
        "no_evidence": "I could not find sufficient verified legal sources to answer. Please clarify the topic, transaction, or tax period; a definitive answer cannot be provided from the current knowledge base.",
        "no_verified_evidence": "The knowledge base does not contain relevant verified evidence.",
        "out_of_scope": "I can only help with questions about Indonesian taxation, specifically Income Tax (PPh) and Value Added Tax (PPN). Please ask a tax question.",
        "claims_removed": "Some statements could not be verified against the sources and were removed.",
        "general_notice": "This answer comes from the AI's general knowledge and has not been verified against regulations in Taxora's knowledge base. Check the current regulation, especially for rates, thresholds, and deadlines.",
    },
    "id": {
        "insufficient": "Bukti yang tersedia belum cukup untuk memverifikasi jawaban.",
        "failed": "Permintaan belum dapat diproses. Silakan coba kembali.",
        "llm_unavailable": "Layanan AI sedang tidak tersedia. Tidak ada jawaban yang dibuat.",
        "quota_exhausted": "Kuota harian layanan AI sudah habis, jadi tidak ada jawaban yang dibuat. Kuota direset pukul {time}.",
        "quota_exhausted_unknown": "Kuota layanan AI sudah habis, jadi tidak ada jawaban yang dibuat. Silakan coba lagi nanti.",
        "unconfigured": "Sumber terkait ditemukan, tetapi layanan AI belum dikonfigurasi. Jawaban belum dapat disusun.",
        "api_key_required": "Konfigurasi LLM_API_KEY diperlukan untuk menghasilkan jawaban berbasis evidence.",
        "no_evidence": "Saya belum menemukan sumber hukum terverifikasi yang cukup untuk menjawab. Coba perjelas topik, transaksi, atau periode pajak; jawaban definitif tidak dapat diberikan dari knowledge base saat ini.",
        "no_verified_evidence": "Knowledge base belum memuat evidence terverifikasi yang relevan.",
        "out_of_scope": "Saya hanya dapat membantu pertanyaan seputar perpajakan Indonesia, khususnya Pajak Penghasilan (PPh) dan Pajak Pertambahan Nilai (PPN). Silakan ajukan pertanyaan perpajakan.",
        "claims_removed": "Sebagian pernyataan tidak dapat diverifikasi terhadap sumber dan telah dihapus.",
        "general_notice": "Jawaban ini berasal dari pengetahuan umum AI dan belum diverifikasi dengan peraturan di knowledge base Taxora. Periksa peraturan yang berlaku, terutama untuk tarif, batasan, dan tenggat waktu.",
    },
}


# Earlier exchanges sent with a follow-up question, so "and the requirements?" can be resolved.
HISTORY_EXCHANGES = 2


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
    history = await _history(session, conversation.id)
    session.add(Message(conversation_id=conversation.id, role="user", content=body.question,
                        metadata_json={"response_language": body.response_language}))

    outcome = await _decide(body, session, user, request_id, history)

    latency_ms = round((time.monotonic() - started) * 1000)
    answer = Message(
        id=uuid.uuid4(), conversation_id=conversation.id, role="assistant", content=outcome.answer,
        metadata_json={"request_id": str(request_id), "answer_status": outcome.status.value,
                       "evidence_ids": [str(item["id"]) for item in outcome.evidence],
                       "cited_evidence_ids": [str(s.evidence_id) for s in outcome.sources],
                       "latency_ms": latency_ms, "response_language": body.response_language,
                       "prompt_version": PROMPT_VERSION, **outcome.trace},
    )
    session.add(answer)
    await session.flush()
    return ChatResponse(request_id=request_id, conversation_id=conversation.id, message_id=answer.id,
                        answer_status=outcome.status, answer=outcome.answer, claims=outcome.claims, sources=outcome.sources,
                        missing_information=outcome.missing, limitations=outcome.limitations, latency_ms=latency_ms)


async def _conversation_for(body: ChatRequest, session: AsyncSession, user: User) -> Conversation:
    if body.conversation_id:
        conversation = await session.get(Conversation, body.conversation_id)
        if conversation is None or conversation.user_id != user.id:
            raise ConversationNotFound
        conversation.updated_at = func.now()  # keeps the sidebar ordered by latest activity
        return conversation
    conversation = Conversation(user_id=user.id, title=body.question[:120])
    session.add(conversation)
    await session.flush()
    return conversation


async def _history(session: AsyncSession, conversation_id: uuid.UUID) -> list[Turn]:
    """The last exchanges of the conversation, oldest first. Out-of-scope turns are left out, so an injected
    question is never replayed into later prompts. Failed or unanswered turns stay: their question still
    gives a follow-up its meaning, and their answer is one of Taxora's fixed messages."""
    rows = (await session.scalars(
        select(Message).where(Message.conversation_id == conversation_id)
        .order_by(*Message.chronological(newest_first=True)).limit(HISTORY_EXCHANGES * 2)
    )).all()
    turns, pending_answer = [], None
    for message in rows:  # newest first: each assistant message precedes its question
        if message.role == "assistant":
            pending_answer = message
        elif pending_answer is not None:
            if pending_answer.metadata_json.get("answer_status") != "out_of_scope":
                turns.append(Turn(question=message.content, answer=pending_answer.content))
            pending_answer = None
    return list(reversed(turns))


async def _decide(body: ChatRequest, session: AsyncSession, user: User, request_id: uuid.UUID,
                  history: list[Turn]) -> Outcome:
    """Scope guard → retrieval → LLM → citation validation. Each step can stop early."""
    copy = CHAT_COPY[body.response_language]
    embedder = providers.get_embedder()
    # A follow-up ("bagaimana syaratnya?") is judged and searched together with the previous question.
    search_text = f"{history[-1].question}\n{body.question}" if history else body.question
    scope = await assess_scope(search_text, embedder)
    trace = {"scope": {"in_scope": scope.in_scope, "reason": scope.reason, "similarity": scope.similarity},
             "history_turns": len(history)}
    if not scope.in_scope:
        return Outcome(AnswerStatus.out_of_scope, copy["out_of_scope"], trace=trace)

    as_of = reference_date(search_text)
    trace["reference_date"] = as_of.isoformat()
    evidence = await hybrid_search(session, search_text, user.id, as_of, embedder)
    allow_general = settings.chat_allow_general_answers
    trace["general_answers_allowed"] = allow_general
    llm = providers.get_llm()
    if not evidence and (not allow_general or llm is None):
        return Outcome(AnswerStatus.insufficient_evidence, copy["no_evidence"],
                       limitations=[copy["no_verified_evidence"]], trace=trace)
    if llm is None:
        return Outcome(AnswerStatus.insufficient_evidence, copy["unconfigured"],
                       limitations=[copy["api_key_required"]], evidence=evidence, trace=trace)

    prompt = user_prompt(body.question, evidence, history)
    try:
        result = await _generate(llm, system_prompt(body.response_language, allow_general), prompt, evidence,
                                 request_id, trace)
    except QuotaExhausted as exc:
        trace["quota_resets_at"] = exc.resets_at.isoformat() if exc.resets_at else None
        return Outcome(AnswerStatus.failed, _quota_message(copy, exc), evidence=evidence, trace=trace)
    except LLMError:
        return Outcome(AnswerStatus.failed, copy["llm_unavailable"], evidence=evidence, trace=trace)
    except MalformedOutput:
        return Outcome(AnswerStatus.failed, copy["failed"], evidence=evidence, trace=trace)
    trace["rejected_claims"] = result.rejected_claims
    return _from_generation(result, evidence, copy, trace, allow_general)


async def _generate(llm: LLMClient, system: str, prompt: str, evidence: list[dict], request_id: uuid.UUID,
                    trace: dict) -> GenerationResult:
    """Ask the LLM, retrying when the reply is empty, truncated, or not the expected JSON. Records the
    model that produced the accepted reply (or the last attempt) and every failed attempt."""
    errors: list[str] = []
    trace["model"] = llm.model
    for attempt in range(1, max(1, settings.llm_attempts) + 1):
        try:
            reply = await llm.complete_json(system, prompt, attempt - 1)
            trace["model"] = reply.model
            return parse_and_validate(reply.text, evidence)
        except (LLMError, MalformedOutput) as exc:
            errors.append(f"{type(exc).__name__}: {exc}"[:200])
            trace["llm_errors"] = errors
            logger.warning("llm attempt %s failed request_id=%s error=%s", attempt, request_id, exc)
            if isinstance(exc, QuotaExhausted) or attempt >= settings.llm_attempts:
                raise  # another attempt cannot succeed before the quota resets
    raise AssertionError("unreachable")


# Shown in Indonesian time: Taxora's users are in Indonesia.
DISPLAY_TIMEZONE = ZoneInfo("Asia/Jakarta")


def _quota_message(copy: dict, exc: QuotaExhausted) -> str:
    if exc.resets_at is None:
        return copy["quota_exhausted_unknown"]
    local = exc.resets_at.astimezone(DISPLAY_TIMEZONE)
    return copy["quota_exhausted"].format(time=f"{local:%H.%M} WIB ({local:%d-%m-%Y})")


def _from_generation(result: GenerationResult, evidence: list[dict], copy: dict, trace: dict,
                     allow_general: bool = False) -> Outcome:
    if not result.in_scope:
        # The model's own text is discarded: only the fixed refusal is shown.
        return Outcome(AnswerStatus.out_of_scope, copy["out_of_scope"], evidence=evidence, trace=trace)
    if not result.claims and allow_general and result.answer:
        # No statement could be tied to a quoted regulation: show the answer, clearly labelled as unverified.
        return Outcome(AnswerStatus.general_answer, result.answer, missing=result.missing_information,
                       limitations=[copy["general_notice"], *result.limitations], evidence=evidence, trace=trace)
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
