from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


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
