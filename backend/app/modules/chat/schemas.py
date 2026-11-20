from datetime import date
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AnswerStatus(str, Enum):
    answered = "answered"
    clarification_needed = "clarification_needed"
    insufficient_evidence = "insufficient_evidence"
    out_of_scope = "out_of_scope"
    failed = "failed"


class TaxContext(BaseModel):
    tax_period: str | None = Field(default=None, max_length=20)
    taxpayer_type: str | None = Field(default=None, max_length=50)
    transaction_type: str | None = Field(default=None, max_length=100)


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    question: str = Field(min_length=3, max_length=4000)
    context: TaxContext = Field(default_factory=TaxContext)
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
    answer_status: AnswerStatus
    answer: str
    claims: list[Claim] = []
    sources: list[Source] = []
    missing_information: list[str] = []
    limitations: list[str] = []
    latency_ms: int

