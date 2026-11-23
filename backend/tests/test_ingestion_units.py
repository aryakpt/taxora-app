"""Unit tests for source fetching (SSRF guard), storage, and extraction. No database needed."""

import httpx
import pytest

from app.modules.ingestion import sources, storage
from app.modules.ingestion.extraction import ExtractionError, chunks, extract_text, structural_sections
from tests.pdf_fixture import FIXTURE_LINES, make_pdf

PDF = make_pdf(FIXTURE_LINES)


# --- URL allowlist -------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://peraturan.bpk.go.id/Download/1/fixture.pdf",
    "https://www.pajak.go.id/sites/default/files/fixture.pdf",
    "https://PERATURAN.BPK.GO.ID/x.pdf",
])
def test_official_https_sources_are_allowed(url):
    assert sources.check_url(url)


@pytest.mark.parametrize("url", [
    "http://peraturan.bpk.go.id/x.pdf",                 # not https
    "https://example.com/x.pdf",                        # not allowlisted
    "https://pajak.go.id.evil.example/x.pdf",           # allowlisted name as a prefix
    "https://evilpajak.go.id/x.pdf",                    # allowlisted name as a suffix without a dot
    "https://user:pass@pajak.go.id/x.pdf",              # credentials
    "https://pajak.go.id:8443/x.pdf",                   # custom port
    "https://169.254.169.254/latest/meta-data",         # cloud metadata address
    "file:///etc/passwd",
    "not a url",
])
def test_other_urls_are_rejected(url):
    with pytest.raises(sources.SourceRejected):
        sources.check_url(url)


def transport(routes: dict[str, httpx.Response]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return routes.get(str(request.url), httpx.Response(404))
    return httpx.MockTransport(handler)


async def test_fetch_follows_redirects_only_within_allowed_hosts():
    ok = transport({
        "https://pajak.go.id/a": httpx.Response(302, headers={"location": "/files/fixture.pdf"}),
        "https://pajak.go.id/files/fixture.pdf": httpx.Response(200, content=PDF),
    })
    content, filename = await sources.fetch_pdf("https://pajak.go.id/a", transport=ok)
    assert content == PDF and filename == "fixture.pdf"

    escape = transport({"https://pajak.go.id/a": httpx.Response(302, headers={"location": "http://10.0.0.5/admin"})})
    with pytest.raises(sources.SourceRejected):
        await sources.fetch_pdf("https://pajak.go.id/a", transport=escape)


async def test_fetch_rejects_html_pages_with_a_helpful_message():
    page = transport({"https://peraturan.bpk.go.id/Details/1": httpx.Response(200, html="<html>detail</html>")})

    with pytest.raises(sources.SourceRejected, match="tautan unduhan PDF langsung"):
        await sources.fetch_pdf("https://peraturan.bpk.go.id/Details/1", transport=page)


async def test_fetch_stops_reading_oversized_documents(monkeypatch):
    monkeypatch.setattr(sources.settings, "max_upload_bytes", 100)
    big = transport({"https://pajak.go.id/big.pdf": httpx.Response(200, content=b"%PDF" + b"x" * 500)})

    with pytest.raises(sources.SourceRejected, match="batas ukuran"):
        await sources.fetch_pdf("https://pajak.go.id/big.pdf", transport=big)


async def test_fetch_gives_up_on_redirect_loops():
    loop = transport({"https://pajak.go.id/a": httpx.Response(302, headers={"location": "https://pajak.go.id/a"})})

    with pytest.raises(sources.SourceRejected, match="redirect"):
        await sources.fetch_pdf("https://pajak.go.id/a", transport=loop)


# --- storage -------------------------------------------------------------------------------

async def test_storage_round_trip_is_content_addressed(document_storage):
    key = await storage.save(PDF)

    assert await storage.save(PDF) == key and len(key) == 64
    assert await storage.load(key) == PDF
    await storage.delete(key)
    with pytest.raises(storage.DocumentNotFound):
        await storage.load(key)


@pytest.mark.parametrize("key", ["../../etc/passwd", "a" * 63, "Z" * 64])
async def test_storage_rejects_keys_that_are_not_hashes(key):
    with pytest.raises(ValueError):
        await storage.load(key)


# --- extraction ----------------------------------------------------------------------------

def test_pdf_text_is_split_into_preamble_and_articles():
    sections = structural_sections(extract_text(PDF))

    assert [(s.kind, s.number) for s in sections] == [("preamble", None), ("article", "1"), ("article", "2")]
    assert sections[1].text.startswith("Atas penghasilan berupa sewa")


def test_amending_regulations_with_roman_articles_are_recognised():
    sections = structural_sections("Judul\nPasal I\nIsi perubahan.\nPasal II\nMulai berlaku.\nPasal 4A\nTambahan.")

    assert [s.number for s in sections] == [None, "I", "II", "4A"]


def test_attachments_are_separated_from_the_last_article_and_page_numbers_removed():
    text = extract_text(make_pdf([
        "Pasal 1", "Isi pasal satu.", "- 2 -", "Pasal 2", "Mulai berlaku pada tanggal tertentu.",
        "Ditetapkan di Jakarta", "LAMPIRAN", "FORMAT SURAT PERMOHONAN", "Pasal ini dirujuk di formulir",
    ]))
    sections = structural_sections(text)

    assert "- 2 -" not in text
    assert [(s.kind, s.number) for s in sections] == [("article", "1"), ("article", "2"), ("attachment", None)]
    assert "LAMPIRAN" not in sections[1].text
    assert sections[2].text.startswith("LAMPIRAN")


def test_chapter_headings_are_not_part_of_the_article_before_them():
    text = "\n".join([
        "Menimbang: contoh.", "BAB I", "KETENTUAN UMUM", "Pasal 1", "Definisi.",
        "Pasal 2", "Pihak yang berhak:", "a. satu; atau", "b. dua.",
        "BAB III", "PENGEMBALIAN BAGI WAJIB PAJAK", "DENGAN KRITERIA TERTENTU", "Bagian Kesatu", "Umum",
        "Pasal 3", "Isi pasal tiga.", "Pasal 4", "Isi pasal empat.",
    ])
    sections = structural_sections(text)

    assert [(s.number, s.text) for s in sections] == [
        (None, "Menimbang: contoh."), ("1", "Definisi."), ("2", "Pihak yang berhak:\na. satu; atau\nb. dua."),
        ("3", "Isi pasal tiga."), ("4", "Isi pasal empat.")]


UU_WITH_ELUCIDATION = "\n".join([
    "UNDANG-UNDANG NOMOR 1 TAHUN 2026", "Menimbang: contoh.",
    "Pasal 1", "Dalam undang-undang ini yang dimaksud dengan pajak adalah kontribusi wajib.",
    "Pasal 2", "Tarif pajak ditetapkan sebesar sepuluh persen.",
    "Disahkan di Jakarta",
    "PENJELASAN", "ATAS", "UNDANG-UNDANG NOMOR 1 TAHUN 2026",
    "I. UMUM", "Undang-undang ini menyederhanakan Pasal 2 undang-undang lama.",
    "II. PASAL DEMI PASAL",
    "Pasal 1", "Cukup jelas.",
    "Pasal 2", "Tarif berlaku untuk seluruh wajib pajak.",
])


def test_the_elucidation_is_kept_apart_from_the_articles_it_explains():
    sections = structural_sections(UU_WITH_ELUCIDATION)

    assert [(s.kind, s.number) for s in sections] == [
        ("preamble", None), ("article", "1"), ("article", "2"),
        ("elucidation", None), ("elucidation", "1"), ("elucidation", "2")]
    assert sections[2].text.startswith("Tarif pajak ditetapkan") and "PENJELASAN" not in sections[2].text
    assert sections[3].text.startswith("PENJELASAN") and "II. PASAL DEMI PASAL" in sections[3].text
    assert sections[5].text == "Tarif berlaku untuk seluruh wajib pajak."


def test_an_attachment_after_the_elucidation_is_recognised():
    sections = structural_sections(UU_WITH_ELUCIDATION + "\nLAMPIRAN\nTABEL TARIF\nsampai Rp5.400.000 0%")

    assert [(s.kind, s.number) for s in sections][-3:] == [
        ("elucidation", "1"), ("elucidation", "2"), ("attachment", None)]
    assert sections[-2].text == "Tarif berlaku untuk seluruh wajib pajak."


def test_an_attachment_before_the_elucidation_is_recognised():
    text = UU_WITH_ELUCIDATION.replace("Disahkan di Jakarta", "Disahkan di Jakarta\nLAMPIRAN\nFORMULIR")
    sections = structural_sections(text)

    assert [(s.kind, s.number) for s in sections] == [
        ("preamble", None), ("article", "1"), ("article", "2"), ("attachment", None),
        ("elucidation", None), ("elucidation", "1"), ("elucidation", "2")]
    assert sections[3].text == "LAMPIRAN\nFORMULIR"


def test_the_word_penjelasan_in_an_article_is_not_the_elucidation():
    sections = structural_sections("Pasal 1\nPenjelasan lebih lanjut diatur dalam PMK.\nPasal 2\nIsi.")

    assert [s.kind for s in sections] == ["article", "article"]


def test_the_word_bab_inside_a_sentence_is_not_a_heading():
    sections = structural_sections("Pasal 1\nSebagaimana diatur dalam BAB II dan\nBagian Kedua peraturan ini.\nPasal 2\nIsi.")

    assert "BAB II" in sections[0].text and "Bagian Kedua" in sections[0].text


@pytest.mark.parametrize("content", [make_pdf([]), b"%PDF-1.4 broken", b"not a pdf"])
def test_unreadable_or_textless_pdfs_are_reported(content):
    with pytest.raises(ExtractionError):
        extract_text(content)


def test_long_articles_are_split_with_overlap():
    parts = chunks("x" * 10_000)

    assert len(parts) == 3 and all(len(part) <= 4500 for part in parts)
    assert chunks("pendek") == ["pendek"]
