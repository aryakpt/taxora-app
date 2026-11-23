from datetime import date
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AnswerStatus(str, Enum):
    answered = "answered"  # backed by quoted regulations
    general_answer = "general_answer"  # from the model's general knowledge, not verified against regulations
    clarification_needed = "clarification_needed"
    insufficient_evidence = "insufficient_evidence"
    out_of_scope = "out_of_scope"
    failed = "failed"


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    # Everything about the case (tax year, taxpayer, transaction) comes from the question itself.
    question: str = Field(min_length=3, max_length=4000)
    response_language: Literal["en", "id"] = "id"


class Claim(BaseModel):
    text: str
    evidence_ids: list[UUID] = []
    quote: str | None = None


class Source(BaseModel):
    evidence_id: UUID
    regulation_number: str
    title: str
    article: str | None
    quote: str
    source_url: str
    verification_status: str
    effective_from: date | None
    effective_until: date | None


class ChatResponse(BaseModel):
    request_id: UUID
    conversation_id: UUID
    message_id: UUID  # the stored answer, for feedback
    answer_status: AnswerStatus
    answer: str
    claims: list[Claim] = []
    sources: list[Source] = []
    missing_information: list[str] = []
    limitations: list[str] = []
    latency_ms: int

