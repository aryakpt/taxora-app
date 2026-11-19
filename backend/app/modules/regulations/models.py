import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


class Regulation(Base):
    __tablename__ = "regulations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regulation_number: Mapped[str] = mapped_column(String(100))
    regulation_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(Text)
    issuer: Mapped[str] = mapped_column(String(200))
    topic: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RegulationVersion(Base):
    __tablename__ = "regulation_versions"
    __table_args__ = (UniqueConstraint("regulation_id", "document_hash"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regulation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regulations.id", ondelete="CASCADE"))
    source_url: Mapped[str] = mapped_column(Text)
    document_hash: Mapped[str] = mapped_column(String(64))
    issued_at: Mapped[date | None] = mapped_column(Date)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="review_required")
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_user_ids: Mapped[list] = mapped_column(JSONB, default=list)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegalProvision(Base):
    __tablename__ = "legal_provisions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regulation_versions.id", ondelete="CASCADE"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("legal_provisions.id"))
    provision_type: Mapped[str] = mapped_column(String(30), default="article")
    article_number: Mapped[str | None] = mapped_column(String(30))
    paragraph_number: Mapped[str | None] = mapped_column(String(30))
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("legal_provisions.id", ondelete="CASCADE"))
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(Vector(settings.embedding_dimensions))
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    index_version: Mapped[str] = mapped_column(String(50), default="v1")
