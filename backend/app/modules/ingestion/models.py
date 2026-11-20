import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class JobStatus(str, Enum):
    """PRD FR-09 statuses. A job follows its regulation version through review and publication."""

    queued = "queued"
    processing = "processing"
    review_required = "review_required"
    approved = "approved"
    published = "published"
    failed = "failed"


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    # Fetch server-generated values (updated_at) with RETURNING on every write; reading an expired
    # attribute later would need lazy IO, which async sessions do not allow.
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url: Mapped[str] = mapped_column(Text)
    filename: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default=JobStatus.queued.value)
    error: Mapped[str | None] = mapped_column(Text)
    # Informational outcome that is not an error, e.g. "identical document already ingested".
    detail: Mapped[str | None] = mapped_column(Text)
    regulation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regulations.id"))
    version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regulation_versions.id", ondelete="SET NULL"))
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # SHA-256 of the stored original file, once fetched or uploaded (see ingestion/storage.py).
    storage_key: Mapped[str | None] = mapped_column(String(64))
    # Version metadata from the request (dates, access), kept so a failed job can be retried.
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
