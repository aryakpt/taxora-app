"""Ingestion workflow end to end, with a fake source and labeled fixture PDFs (not real law)."""

import pytest
from sqlalchemy import func, select, text

from app.cli import set_role
from app.core.database import SessionLocal
from app.modules.audit.models import AuditLog
from app.modules.auth.models import UserRole
from app.modules.ingestion import sources
from app.modules.ingestion.models import IngestionJob, JobStatus
from app.modules.ingestion.service import recover_interrupted_jobs
from app.modules.regulations.models import DocumentChunk, LegalProvision, Regulation, RegulationVersion
from tests.pdf_fixture import FIXTURE_LINES, make_pdf

pytestmark = pytest.mark.db

PDF = make_pdf(FIXTURE_LINES)
URL = "https://peraturan.bpk.go.id/Download/1/fixture.pdf"
METADATA = {
    "source_url": URL, "regulation_number": "1 TAHUN 2026", "regulation_type": "fixture",
    "title": "[FIXTURE] Peraturan contoh", "issuer": "Test", "topic": "PPh", "effective_from": "2026-01-01",
}


@pytest.fixture
def source(monkeypatch):
    """Fake official source: URL -> PDF bytes or an exception. Counts fetches."""
    documents: dict[str, bytes | Exception] = {URL: PDF}
    fetched: list[str] = []

    async def fake_fetch(url: str, **_):
        fetched.append(url)
        result = documents[url]
        if isinstance(result, Exception):
            raise result
        return result, "fixture.pdf"

    monkeypatch.setattr(sources, "fetch_pdf", fake_fetch)
    return documents, fetched


async def sign_in_as(client, email: str, role: UserRole) -> None:
    client.cookies.clear()
    password = "a-long-test-password-123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "full_name": "T", "password": password})
    if registered.status_code == 409:
        await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    await set_role(email, role)


async def submit(client, **overrides):
    response = await client.post("/api/v1/admin/ingestion", json={**METADATA, **overrides})
    assert response.status_code == 202, response.text
    return (await client.get(f"/api/v1/admin/ingestion/{response.json()['id']}")).json()


async def count(model) -> int:
    async with SessionLocal() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def test_document_is_processed_reviewed_published_and_then_searchable(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)

    assert job["status"] == "review_required"
    assert job["regulation"]["type"] == "FIXTURE" and job["version"]["status"] == "review_required"
    assert await count(LegalProvision) == 3 and await count(DocumentChunk) == 3
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).where(DocumentChunk.embedding.is_(None))) == 0
    assert (await client.get("/api/v1/regulations")).json() == []  # not published yet

    await sign_in_as(client, "reviewer@example.com", UserRole.reviewer)
    approved = await client.post(f"/api/v1/admin/ingestion/{job['id']}/approve")
    assert approved.json()["status"] == "approved" and approved.json()["version"]["verified_at"]
    assert (await client.post(f"/api/v1/admin/ingestion/{job['id']}/publish")).status_code == 403

    await sign_in_as(client, "admin@example.com", UserRole.admin)
    published = await client.post(f"/api/v1/admin/ingestion/{job['id']}/publish")
    assert published.json()["status"] == "published"

    library = (await client.get("/api/v1/regulations")).json()
    assert [regulation["number"] for regulation in library] == ["1 TAHUN 2026"]
    chat = await client.post("/api/v1/chat", json={"question": "Berapa tarif pajak atas sewa?"})
    assert chat.json()["answer_status"] == "insufficient_evidence"  # evidence found, LLM not configured
    assert "dikonfigurasi" in chat.json()["answer"]

    async with SessionLocal() as session:
        actions = (await session.scalars(select(AuditLog.action).order_by(AuditLog.created_at))).all()
    assert [a for a in actions if a.startswith("ingestion.")] == [
        "ingestion.created", "ingestion.processed", "ingestion.approved", "ingestion.published"]


async def test_status_changes_must_follow_the_workflow(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    base = f"/api/v1/admin/ingestion/{job['id']}"

    assert (await client.post(f"{base}/publish")).status_code == 409   # not approved yet
    assert (await client.post(f"{base}/approve")).status_code == 200
    assert (await client.post(f"{base}/approve")).status_code == 409   # already approved
    assert (await client.post(f"{base}/retry")).status_code == 409     # not failed


async def test_reviewer_corrects_dates_only_while_under_review(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client, effective_from=None)
    base = f"/api/v1/admin/ingestion/{job['id']}"
    dates = {"issued_at": "2026-04-20", "effective_from": "2026-05-01", "effective_until": None}

    await sign_in_as(client, "user@example.com", UserRole.user)
    assert (await client.put(f"{base}/dates", json=dates)).status_code == 403

    await sign_in_as(client, "reviewer@example.com", UserRole.reviewer)
    updated = await client.put(f"{base}/dates", json=dates)
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"]["effective_from"] == "2026-05-01"
    assert updated.json()["version"]["issued_at"] == "2026-04-20"
    backwards = {"effective_from": "2026-05-01", "effective_until": "2026-01-01"}
    assert (await client.put(f"{base}/dates", json=backwards)).status_code == 422

    assert (await client.post(f"{base}/approve")).status_code == 200
    assert (await client.put(f"{base}/dates", json=dates)).status_code == 409  # frozen after approval
    async with SessionLocal() as session:
        actions = (await session.scalars(select(AuditLog.action))).all()
    assert "ingestion.dates_updated" in actions


CORRECTION = {"title": "[FIXTURE] Judul yang benar", "issuer": "Kementerian Keuangan", "topic": "PPh",
              "issued_at": "2026-04-29", "effective_from": "2027-01-01", "effective_until": None,
              "reason": "Tanggal berlaku keliru, lihat Pasal 2"}


async def test_admin_corrects_metadata_of_a_published_document_with_a_reason(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    base = f"/api/v1/admin/ingestion/{job['id']}"
    assert (await client.put(f"{base}/metadata", json=CORRECTION)).status_code == 409  # still under review
    await client.post(f"{base}/approve")
    await client.post(f"{base}/publish")
    asked = await client.post("/api/v1/chat", json={"question": "Berapa tarif pajak atas sewa?"})
    assert "dikonfigurasi" in asked.json()["answer"]  # in force: evidence found (LLM not configured)

    corrected = await client.put(f"{base}/metadata", json=CORRECTION)

    assert corrected.status_code == 200, corrected.text
    body = corrected.json()
    assert body["status"] == "published"  # stays published
    assert body["regulation"]["title"] == "[FIXTURE] Judul yang benar"
    assert body["version"]["effective_from"] == "2027-01-01" and body["version"]["issued_at"] == "2026-04-29"
    [entry] = body["corrections"]
    assert entry["reason"] == "Tanggal berlaku keliru, lihat Pasal 2" and entry["by"] == "admin@example.com"
    assert entry["changes"]["effective_from"] == {"old": "2026-01-01", "new": "2027-01-01"}
    assert "issuer" in entry["changes"] and "topic" not in entry["changes"]
    # Retrieval follows the new dates at once: not in force yet, so no evidence.
    asked = await client.post("/api/v1/chat", json={"question": "Berapa tarif pajak atas sewa?"})
    assert asked.json()["answer_status"] == "insufficient_evidence" and "dikonfigurasi" not in asked.json()["answer"]

    assert (await client.put(f"{base}/metadata", json=CORRECTION)).status_code == 409  # nothing changed
    assert (await client.put(f"{base}/metadata", json={**CORRECTION, "reason": "x"})).status_code == 422
    backwards = {**CORRECTION, "effective_until": "2026-01-01"}
    assert (await client.put(f"{base}/metadata", json=backwards)).status_code == 422

    await sign_in_as(client, "reviewer@example.com", UserRole.reviewer)
    assert (await client.put(f"{base}/metadata", json={**CORRECTION, "title": "y"})).status_code == 403


async def test_reviewer_can_read_extracted_sections_and_the_original(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    base = f"/api/v1/admin/ingestion/{job['id']}"

    await sign_in_as(client, "reviewer@example.com", UserRole.reviewer)
    sections = (await client.get(f"{base}/provisions")).json()
    assert [(s["kind"], s["number"], s["chunks"]) for s in sections] == [
        ("preamble", None, 1), ("article", "1", 1), ("article", "2", 1)]
    assert sections[1]["text"].startswith("Atas penghasilan berupa sewa")

    document = await client.get(f"{base}/document")
    assert document.status_code == 200 and document.content == PDF
    assert document.headers["content-disposition"].startswith("attachment")
    assert (await client.get("/api/v1/admin/ingestion/00000000-0000-0000-0000-000000000000/provisions")).status_code == 404

    await sign_in_as(client, "user@example.com", UserRole.user)
    assert (await client.get(f"{base}/provisions")).status_code == 403
    assert (await client.get(f"{base}/document")).status_code == 403


async def test_documents_under_review_can_be_reprocessed_but_approved_ones_cannot(client, source):
    from app.modules.ingestion import service

    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    async with SessionLocal() as session:
        before = set((await session.scalars(select(LegalProvision.id))).all())

    detail = await service.reprocess(job["id"])

    async with SessionLocal() as session:
        after = set((await session.scalars(select(LegalProvision.id))).all())
    assert detail.startswith("3 bagian") and len(after) == 3 and not before & after  # rebuilt
    assert await count(DocumentChunk) == 3  # old chunks went with their provisions

    await client.post(f"/api/v1/admin/ingestion/{job['id']}/approve")
    with pytest.raises(service.InvalidTransition):
        await service.reprocess(job["id"])


async def test_only_admins_submit_and_regular_users_see_nothing(client, source):
    await sign_in_as(client, "user@example.com", UserRole.user)
    assert (await client.post("/api/v1/admin/ingestion", json=METADATA)).status_code == 403
    assert (await client.get("/api/v1/admin/ingestion")).status_code == 403

    await sign_in_as(client, "reviewer@example.com", UserRole.reviewer)
    assert (await client.post("/api/v1/admin/ingestion", json=METADATA)).status_code == 403
    assert (await client.get("/api/v1/admin/ingestion")).status_code == 200


async def test_resubmitting_the_same_document_reuses_regulation_and_version(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    first = await submit(client)
    second = await submit(client, regulation_type=" Fixture ", regulation_number="1  TAHUN   2026")

    assert second["regulation"]["id"] == first["regulation"]["id"]
    assert second["version"]["id"] == first["version"]["id"]
    assert "identik" in second["detail"]
    assert await count(Regulation) == 1 and await count(RegulationVersion) == 1 and await count(DocumentChunk) == 3

    await client.post(f"/api/v1/admin/ingestion/{first['id']}/approve")
    assert (await client.get(f"/api/v1/admin/ingestion/{second['id']}")).json()["status"] == "approved"


async def test_a_changed_document_becomes_a_new_version_of_the_same_regulation(client, source):
    documents, _ = source
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    first = await submit(client)
    documents[URL] = make_pdf([*FIXTURE_LINES, "Pasal 3", "Ketentuan tambahan untuk pengujian."])
    second = await submit(client)

    assert second["regulation"]["id"] == first["regulation"]["id"]
    assert second["version"]["id"] != first["version"]["id"]
    assert await count(Regulation) == 1 and await count(RegulationVersion) == 2


async def test_failures_are_recorded_and_retry_does_not_refetch_stored_files(client, source):
    documents, fetched = source
    await sign_in_as(client, "admin@example.com", UserRole.admin)

    documents[URL] = sources.SourceRejected("Sumber mengembalikan HTTP 503")
    failed = await submit(client)
    assert failed["status"] == "failed" and failed["error"] == "Sumber mengembalikan HTTP 503"

    documents[URL] = make_pdf([])  # scanned document: no text layer
    retried = await client.post(f"/api/v1/admin/ingestion/{failed['id']}/retry")
    assert retried.status_code == 202
    job = (await client.get(f"/api/v1/admin/ingestion/{failed['id']}")).json()
    assert job["status"] == "failed" and "OCR" in job["error"]

    await client.post(f"/api/v1/admin/ingestion/{failed['id']}/retry")
    assert len(fetched) == 2  # the stored scan is reused, not downloaded again


async def test_unexpected_errors_are_not_leaked_to_admins(client, source):
    documents, _ = source
    documents[URL] = RuntimeError("connection string postgres://secret@db")
    await sign_in_as(client, "admin@example.com", UserRole.admin)

    job = await submit(client)

    assert job["status"] == "failed"
    assert "secret" not in job["error"] and "Kesalahan internal" in job["error"]


async def test_upload_with_metadata_is_processed(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    form = {key: value for key, value in METADATA.items()}

    response = await client.post("/api/v1/admin/ingestion/upload", data=form,
                                 files={"file": ("fixture.pdf", PDF, "application/pdf")})

    assert response.status_code == 202, response.text
    job = (await client.get(f"/api/v1/admin/ingestion/{response.json()['id']}")).json()
    assert job["status"] == "review_required" and job["filename"] == "fixture.pdf"
    _, fetched = source
    assert fetched == []

    not_pdf = await client.post("/api/v1/admin/ingestion/upload", data=form,
                                files={"file": ("x.pdf", b"<html>", "application/pdf")})
    assert not_pdf.status_code == 415


@pytest.mark.parametrize("overrides", [
    {"source_url": "https://example.com/fixture.pdf"},
    {"source_url": "http://peraturan.bpk.go.id/x.pdf"},
    {"effective_from": "2026-06-01", "effective_until": "2026-01-01"},
    {"allowed_user_ids": ["00000000-0000-0000-0000-000000000001"]},
])
async def test_invalid_metadata_is_rejected_before_queueing(client, source, overrides):
    await sign_in_as(client, "admin@example.com", UserRole.admin)

    response = await client.post("/api/v1/admin/ingestion", json={**METADATA, **overrides})

    assert response.status_code == 422
    assert await count(IngestionJob) == 0


async def test_jobs_interrupted_by_a_restart_are_marked_retryable():
    async with SessionLocal() as session, session.begin():
        session.add(IngestionJob(source_url=URL, status=JobStatus.processing.value))

    assert await recover_interrupted_jobs() == 1
    async with SessionLocal() as session:
        job = await session.scalar(select(IngestionJob))
    assert job.status == "failed" and "retry" in job.error


async def test_keyword_search_uses_the_full_text_index(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    await submit(client)

    async with SessionLocal() as session, session.begin():
        await session.execute(text("SET LOCAL enable_seqscan = off"))
        plan = "\n".join((await session.execute(text(
            "EXPLAIN SELECT id FROM document_chunks "
            "WHERE to_tsvector('simple'::regconfig, chunk_text) @@ to_tsquery('simple'::regconfig, 'sewa')"
        ))).scalars())
    assert "ix_document_chunks_fts" in plan
