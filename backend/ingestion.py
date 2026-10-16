import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai import AIProvider
from backend.config import settings
from backend.models import DocumentChunk, LegalProvision, Regulation, RegulationVersion


def structural_sections(text: str) -> list[tuple[str | None, str]]:
    matches = list(re.finditer(r"(?im)^\s*Pasal\s+([\w.-]+)\s*$", text))
    if not matches:
        cleaned = text.strip()
        return [(None, cleaned)] if cleaned else []
    sections = []
    if text[:matches[0].start()].strip():
        sections.append((None, text[:matches[0].start()].strip()))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1), text[match.end():end].strip()))
    return sections


async def process_document(session: AsyncSession, job, metadata: dict, content: bytes):
    if len(content) > settings.max_upload_bytes:
        raise ValueError("Dokumen melebihi batas ukuran")
    digest = hashlib.sha256(content).hexdigest()
    existing = await session.scalar(select(RegulationVersion).where(
        RegulationVersion.regulation_id == job.regulation_id,
        RegulationVersion.document_hash == digest,
    ))
    if existing:
        return existing
    if metadata.get("filename", "").lower().endswith(".pdf") or content[:4] == b"%PDF":
        reader = PdfReader(content)
        extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        extracted = content.decode("utf-8", errors="replace")
    if not extracted.strip():
        raise ValueError("Tidak ada teks yang dapat diekstrak; OCR belum dikonfigurasi")
    regulation = await session.get(Regulation, job.regulation_id)
    version = RegulationVersion(
        regulation_id=regulation.id, source_url=metadata["source_url"], document_hash=digest,
        issued_at=metadata.get("issued_at"), effective_from=metadata.get("effective_from"),
        effective_until=metadata.get("effective_until"), status="review_required",
        is_internal=metadata.get("is_internal", False),
        allowed_user_ids=[str(value) for value in metadata.get("allowed_user_ids", [])],
    )
    session.add(version)
    await session.flush()
    ai = AIProvider()
    for ordinal, (article, section) in enumerate(structural_sections(extracted)):
        provision = LegalProvision(version_id=version.id, provision_type="article", article_number=article,
                                   ordinal=ordinal, text=section)
        session.add(provision)
        await session.flush()
        # Preserve the provision as a unit; split only exceptionally long text with overlap.
        chunks = [section[i:i + 4500] for i in range(0, len(section), 4200)] or [section]
        for chunk in chunks:
            session.add(DocumentChunk(provision_id=provision.id, chunk_text=chunk,
                                      token_count=len(chunk.split()), embedding=await ai.embed(chunk)))
    return version


async def fetch_source(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/pdf" not in content_type and not url.lower().endswith(".pdf"):
            raise ValueError("URL harus menunjuk dokumen PDF yang diizinkan")
        return response.content, Path(url.split("?")[0]).name or "document.pdf"
