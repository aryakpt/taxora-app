from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import UploadFile
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.modules.ingestion.sources import check_url


class RegulationMetadata(BaseModel):
    """Metadata an admin supplies for a regulation document (PRD §6.1-6.2). Never inferred by AI."""

    source_url: HttpUrl | None = Field(
        default=None, description="Official source link, cited to users. Must be on the allowlist. Optional for uploads.")
    regulation_number: str = Field(min_length=1, max_length=100, examples=["28 TAHUN 2026"])
    regulation_type: str = Field(min_length=1, max_length=30, examples=["PMK"])
    title: str = Field(min_length=1, max_length=1000)
    issuer: str = Field(min_length=1, max_length=200)
    topic: Literal["PPh", "PPN", "other"]
    issued_at: date | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    is_internal: bool = False
    allowed_user_ids: list[UUID] = []

    @field_validator("source_url", mode="before")
    @classmethod
    def empty_is_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("source_url")
    @classmethod
    def official_source(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None:
            check_url(str(value))
        return value

    @model_validator(mode="after")
    def coherent(self) -> "RegulationMetadata":
        if self.effective_from and self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("Tanggal berlaku sampai tidak boleh sebelum tanggal berlaku mulai")
        if self.allowed_user_ids and not self.is_internal:
            raise ValueError("allowed_user_ids hanya berlaku untuk dokumen internal")
        return self

    def version_metadata(self) -> dict:
        return {
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_until": self.effective_until.isoformat() if self.effective_until else None,
            "is_internal": self.is_internal,
            "allowed_user_ids": [str(user_id) for user_id in self.allowed_user_ids],
        }


class UrlSubmission(RegulationMetadata):
    """Submission by link: the PDF is downloaded from it, so the link is required."""

    source_url: HttpUrl = Field(description="Official PDF download link. Must be on the allowlist.")


class Rejection(BaseModel):
    reason: str = Field(min_length=5, max_length=500, description="What is wrong; shown to admins and kept in the audit log.")


class VersionDates(BaseModel):
    """Dates a reviewer confirms against the official text. All three are replaced together."""

    issued_at: date | None = None
    effective_from: date | None = None
    effective_until: date | None = None

    @model_validator(mode="after")
    def coherent(self) -> "VersionDates":
        if self.effective_from and self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("Tanggal berlaku sampai tidak boleh sebelum tanggal berlaku mulai")
        return self


class MetadataCorrection(VersionDates):
    """An admin's correction of an approved or published document. The legal text cannot be changed this
    way, and neither can the regulation's type and number (they identify it: re-submit instead)."""

    title: str = Field(min_length=1, max_length=1000)
    issuer: str = Field(min_length=1, max_length=200)
    topic: Literal["PPh", "PPN", "other"]
    reason: str = Field(min_length=5, max_length=500, description="Why the correction is needed; kept in the audit log.")


class UploadForm(RegulationMetadata):
    """Multipart form for uploads: the metadata fields plus the PDF itself."""

    file: UploadFile
