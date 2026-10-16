from datetime import date
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class AnswerStatus(str, Enum):
    answered = "answered"
    clarification_needed = "clarification_needed"
    insufficient_evidence = "insufficient_evidence"
    failed = "failed"


class TaxContext(BaseModel):
    tax_period: str | None = None
    taxpayer_type: str | None = None
    transaction_type: str | None = None


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    question: str = Field(min_length=3, max_length=8000)
    context: TaxContext = Field(default_factory=TaxContext)
    response_language: Literal["en", "id"] = "id"


class Claim(BaseModel):
    text: str
    evidence_ids: list[UUID] = []


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


class IngestionRequest(BaseModel):
    source_url: HttpUrl
    regulation_number: str = Field(min_length=1, max_length=100)
    regulation_type: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=1000)
    issuer: str = Field(min_length=1, max_length=200)
    topic: str = Field(pattern="^(PPh|PPN|other)$")
    issued_at: date | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    is_internal: bool = False
    allowed_user_ids: list[UUID] = []
