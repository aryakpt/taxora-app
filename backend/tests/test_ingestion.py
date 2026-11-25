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


EDIT = {"regulation_type": "fixture", "regulation_number": "1 TAHUN 2026", "title": "[FIXTURE] Judul yang benar",
        "issuer": "Kementerian Keuangan", "topic": "PPh", "issued_at": "2026-04-29", "effective_from": "2027-01-01",
        "effective_until": None, "reason": "Tanggal berlaku keliru, lihat Pasal 2"}


async def ask_rent(client) -> dict:
    return (await client.post("/api/v1/chat", json={"question": "Berapa tarif pajak atas sewa?"})).json()


async def test_editing_a_published_document_sends_it_back_to_review(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    base = f"/api/v1/admin/ingestion/{job['id']}"
    await client.post(f"{base}/approve")
    await client.post(f"{base}/publish")
    assert "dikonfigurasi" in (await ask_rent(client))["answer"]  # published: its evidence is found

    edited = await client.put(base, json={**EDIT, "effective_from": "2026-01-01"})

    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["status"] == "review_required" and body["version"]["status"] == "review_required"
    assert body["version"]["verified_at"] is None and body["regulation"]["title"] == "[FIXTURE] Judul yang benar"
    [entry] = body["corrections"]
    assert entry["reason"] == "Tanggal berlaku keliru, lihat Pasal 2" and entry["by"] == "admin@example.com"
    assert entry["back_to_review"] is True and entry["previous_status"] == "published"
    assert set(entry["changes"]) == {"title", "issuer", "issued_at"}
    # Out of the assistant until it is approved and published again.
    assert "dikonfigurasi" not in (await ask_rent(client))["answer"]
    assert (await client.post(f"{base}/approve")).status_code == 200
    assert (await client.post(f"{base}/publish")).status_code == 200
    assert "dikonfigurasi" in (await ask_rent(client))["answer"]


async def test_a_new_type_or_number_moves_the_document_to_that_regulation(client, source):
    documents, _ = source
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    first = await submit(client)
    other_url = "https://peraturan.bpk.go.id/Download/2/fixture.pdf"
    documents[other_url] = make_pdf([*FIXTURE_LINES, "Dokumen lain"])
    second = await submit(client, source_url=other_url, regulation_number="2 TAHUN 2026")

    moved = await client.put(f"/api/v1/admin/ingestion/{first['id']}",
                             json={**EDIT, "regulation_type": "pmk", "regulation_number": " 9  TAHUN 2026 "})

    assert moved.status_code == 200, moved.text
    assert moved.json()["regulation"]["type"] == "PMK" and moved.json()["regulation"]["number"] == "9 TAHUN 2026"
    async with SessionLocal() as session:  # the old regulation had only this document: removed
        numbers = sorted((await session.scalars(select(Regulation.regulation_number))).all())
    assert numbers == ["2 TAHUN 2026", "9 TAHUN 2026"]

    # Onto a regulation that already has the same file: refused, nothing changes.
    documents[URL] = PDF
    same_file = await submit(client, source_url=URL, regulation_number="3 TAHUN 2026")
    clash = await client.put(f"/api/v1/admin/ingestion/{same_file['id']}",
                             json={**EDIT, "regulation_type": "PMK", "regulation_number": "9 TAHUN 2026"})
    assert clash.status_code == 409 and "dokumen yang sama" in clash.json()["detail"]
    assert (await client.get(f"/api/v1/admin/ingestion/{second['id']}")).json()["regulation"]["number"] == "2 TAHUN 2026"


async def test_edit_rules(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    base = f"/api/v1/admin/ingestion/{job['id']}"

    under_review = await client.put(base, json=EDIT)  # still under review: stays there
    assert under_review.status_code == 200 and under_review.json()["status"] == "review_required"
    assert under_review.json()["corrections"][0]["back_to_review"] is False

    assert (await client.put(base, json=EDIT)).status_code == 409  # nothing changed
    assert (await client.put(base, json={**EDIT, "title": "Baru", "reason": "x"})).status_code == 422
    assert (await client.put(base, json={**EDIT, "effective_until": "2026-01-01"})).status_code == 422
    assert (await client.put(base, json={**EDIT, "regulation_number": " "})).status_code == 422
    async with SessionLocal() as session, session.begin():
        await session.execute(text("UPDATE ingestion_jobs SET status = 'processing'"))
    assert (await client.put(base, json={**EDIT, "title": "Baru"})).status_code == 409

    await sign_in_as(client, "reviewer@example.com", UserRole.reviewer)
    assert (await client.put(base, json={**EDIT, "title": "y"})).status_code == 403


async def test_a_failed_document_keeps_the_edited_dates_for_its_retry(client, source):
    documents, _ = source
    documents[URL] = sources.SourceRejected("Sumber tidak dapat dihubungi")
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    assert job["status"] == "failed"

    edited = await client.put(f"/api/v1/admin/ingestion/{job['id']}", json=EDIT)
    assert edited.status_code == 200 and edited.json()["status"] == "failed"

    documents[URL] = PDF
    await client.post(f"/api/v1/admin/ingestion/{job['id']}/retry")
    retried = (await client.get(f"/api/v1/admin/ingestion/{job['id']}")).json()
    assert retried["status"] == "review_required"
    assert retried["version"]["effective_from"] == "2027-01-01" and retried["regulation"]["title"] == "[FIXTURE] Judul yang benar"


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


async def test_an_upload_does_not_need_an_official_link_but_a_link_submission_does(client, source, document_storage):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    form = {key: value for key, value in METADATA.items() if key != "source_url"} | {"source_url": ""}

    uploaded = await client.post("/api/v1/admin/ingestion/upload", data=form,
                                 files={"file": ("fixture.pdf", PDF, "application/pdf")})
    without_link = await client.post("/api/v1/admin/ingestion", json={k: v for k, v in METADATA.items()
                                                                      if k != "source_url"})

    assert uploaded.status_code == 202, uploaded.text
    job = (await client.get(f"/api/v1/admin/ingestion/{uploaded.json()['id']}")).json()
    assert job["status"] == "review_required" and job["source_url"] is None
    assert without_link.status_code == 422


async def test_a_reviewer_rejects_with_a_reason_and_the_document_is_never_searched(client, source):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    base = f"/api/v1/admin/ingestion/{job['id']}"

    await sign_in_as(client, "user@example.com", UserRole.user)
    assert (await client.post(f"{base}/reject", json={"reason": "Pasal 2 terpotong"})).status_code == 403

    await sign_in_as(client, "reviewer@example.com", UserRole.reviewer)
    assert (await client.post(f"{base}/reject", json={"reason": "x"})).status_code == 422
    rejected = await client.post(f"{base}/reject", json={"reason": "Pasal 2 terpotong di halaman 3"})

    assert rejected.status_code == 200, rejected.text
    body = rejected.json()
    assert body["status"] == "rejected" and body["version"]["status"] == "rejected"
    assert body["rejection"]["reason"] == "Pasal 2 terpotong di halaman 3"
    assert body["rejection"]["by"] == "reviewer@example.com"
    assert (await client.post(f"{base}/approve")).status_code == 409
    assert (await client.post(f"{base}/reject", json={"reason": "lagi lagi"})).status_code == 409

    await sign_in_as(client, "admin@example.com", UserRole.admin)
    again = await submit(client)  # the same file again: extracted afresh and back under review
    assert again["status"] == "review_required" and again["version"]["status"] == "review_required"
    assert again["rejection"] is None and await count(LegalProvision) == 3


async def test_an_admin_deletes_a_published_document_and_everything_that_belongs_to_it(client, source,
                                                                                   document_storage):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    duplicate = await submit(client)  # same file: shares the version
    base = f"/api/v1/admin/ingestion/{job['id']}"
    await client.post(f"{base}/approve")
    await client.post(f"{base}/publish")
    stored_files = list(document_storage.rglob("*.pdf"))
    assert len(stored_files) == 1 and len((await client.get("/api/v1/regulations")).json()) == 1

    await sign_in_as(client, "reviewer@example.com", UserRole.reviewer)
    assert (await client.delete(base)).status_code == 403

    await sign_in_as(client, "admin@example.com", UserRole.admin)
    deleted = await client.delete(base)

    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["status"] == "published" and deleted.json()["jobs"] == 2
    assert (await client.get("/api/v1/regulations")).json() == []
    assert (await client.get(f"/api/v1/admin/ingestion/{duplicate['id']}")).status_code == 404
    for model in (DocumentChunk, LegalProvision, RegulationVersion, Regulation, IngestionJob):
        assert await count(model) == 0
    assert not stored_files[0].exists()
    async with SessionLocal() as session:
        actions = (await session.scalars(select(AuditLog.action))).all()
    assert "ingestion.deleted" in actions


async def test_a_document_still_being_processed_cannot_be_deleted(client, source):
    from sqlalchemy import update

    await sign_in_as(client, "admin@example.com", UserRole.admin)
    job = await submit(client)
    async with SessionLocal() as session, session.begin():
        await session.execute(update(IngestionJob).values(status="processing"))

    assert (await client.delete(f"/api/v1/admin/ingestion/{job['id']}")).status_code == 409
    assert (await client.delete("/api/v1/admin/ingestion/00000000-0000-0000-0000-000000000000")).status_code == 404


async def test_a_stored_file_used_by_another_document_is_kept(client, source, document_storage):
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    first = await submit(client)
    second = await submit(client, regulation_number="2 TAHUN 2026")  # same PDF, another regulation

    await client.delete(f"/api/v1/admin/ingestion/{first['id']}")

    assert len(list(document_storage.rglob("*.pdf"))) == 1
    assert (await client.get(f"/api/v1/admin/ingestion/{second['id']}/document")).status_code == 200


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


async def test_an_embedding_outage_fails_the_job_with_a_retryable_message(client, source, fake_ai, monkeypatch):
    from app.modules.generation.embeddings import EmbeddingError

    async def broken(texts):
        raise EmbeddingError("Batas pemakaian layanan embedding tercapai; coba lagi nanti.")

    monkeypatch.setattr(fake_ai.embedder, "embed_many", broken)
    await sign_in_as(client, "admin@example.com", UserRole.admin)

    job = await submit(client)

    assert job["status"] == "failed" and "Gunakan retry" in job["error"]
    assert await count(DocumentChunk) == 0  # nothing half-indexed


async def test_reindex_embeds_only_the_chunks_without_a_vector_and_can_resume(client, source):
    from sqlalchemy import update

    from app.modules.ingestion import service

    await sign_in_as(client, "admin@example.com", UserRole.admin)
    await submit(client)
    async with SessionLocal() as session, session.begin():
        await session.execute(update(DocumentChunk).values(embedding=None))
    progress = []

    done = await service.reindex(batch=2, progress=lambda d, t: progress.append((d, t)))

    assert done == 3 and progress == [(2, 3), (3, 3)]
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).where(DocumentChunk.embedding.is_(None))) == 0
    assert await service.reindex() == 0  # nothing left


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


# --- serverless hosting (INGESTION_INLINE, INGESTION_STALE_MINUTES) ---------------------------------

async def test_inline_ingestion_answers_with_the_processed_job(client, source, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ingestion_inline", True)
    await sign_in_as(client, "admin@example.com", UserRole.admin)

    response = await client.post("/api/v1/admin/ingestion", json=METADATA)

    assert response.status_code == 202
    assert response.json()["status"] == "review_required" and await count(DocumentChunk) == 3


async def test_with_a_stale_limit_only_old_unfinished_jobs_are_failed(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ingestion_stale_minutes", 10)
    async with SessionLocal() as session, session.begin():
        session.add(IngestionJob(source_url=URL, status=JobStatus.processing.value))  # another instance's
        old = IngestionJob(source_url=URL, status=JobStatus.processing.value)
        session.add(old)
    async with SessionLocal() as session, session.begin():
        await session.execute(text("UPDATE ingestion_jobs SET updated_at = now() - interval '11 minutes' "
                                   "WHERE id = :id"), {"id": old.id})

    assert await recover_interrupted_jobs() == 1
    async with SessionLocal() as session:
        statuses = sorted((await session.scalars(select(IngestionJob.status))).all())
    assert statuses == ["failed", "processing"]


# --- the Knowledge Admin table: pagination, status filter, search -----------------------------------------

async def test_the_job_table_is_paginated_filtered_and_searchable(client, source):
    documents, _ = source
    await sign_in_as(client, "admin@example.com", UserRole.admin)
    for number in range(1, 8):  # seven documents, different files and numbers
        url = f"https://peraturan.bpk.go.id/Download/{number}/fixture.pdf"
        documents[url] = make_pdf([*FIXTURE_LINES, f"Nomor {number}"])
        await submit(client, source_url=url, regulation_number=f"{number} TAHUN 2026", title=f"[FIXTURE] Aturan {number}")

    first = (await client.get("/api/v1/admin/ingestion", params={"page_size": 3})).json()
    last = (await client.get("/api/v1/admin/ingestion", params={"page_size": 3, "page": 3})).json()

    assert first["total"] == 7 and len(first["items"]) == 3 and len(last["items"]) == 1
    assert first["items"][0]["regulation"]["number"] == "7 TAHUN 2026"  # newest first
    assert first["status_counts"] == {"review_required": 7}

    found = (await client.get("/api/v1/admin/ingestion", params={"q": "fixture 5 tahun"})).json()
    assert [job["regulation"]["number"] for job in found["items"]] == ["5 TAHUN 2026"]
    assert (await client.get("/api/v1/admin/ingestion", params={"q": "100%_"})).json()["total"] == 0

    filtered = (await client.get("/api/v1/admin/ingestion", params={"status": "published"})).json()
    assert filtered["total"] == 0 and filtered["status_counts"] == {"review_required": 7}
    assert (await client.get("/api/v1/admin/ingestion", params={"page_size": 101})).status_code == 422
    assert (await client.get("/api/v1/admin/ingestion", params={"status": "nope"})).status_code == 422
