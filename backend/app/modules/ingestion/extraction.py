import io
import re
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError

# "Pasal 4", "Pasal 4A", and the Roman-numbered articles of amending regulations ("Pasal I", "Pasal II").
ARTICLE_HEADING = re.compile(r"(?m)^\s*Pasal\s+([0-9]+[A-Za-z]?|[IVXLC]+)\s*$")
# A standalone "LAMPIRAN" line after the last article starts the attachments (forms, tables).
ATTACHMENT_HEADING = re.compile(r"(?m)^\s*LAMPIRAN\s*$")
# Chapter / part / paragraph headings that open the next group of articles. They are printed just before
# the next "Pasal", so without this they end up at the tail of the previous article.
STRUCTURE_HEADING = re.compile(r"(?m)^[ \t]*(?:BAB[ \t]+[IVXLC]+|Bagian[ \t]+Ke[a-z]+|Paragraf[ \t]+\d+)[ \t]*$")
# Page numbers printed as "- 12 -" on their own line. Layout, not legal text.
PAGE_NUMBER_LINE = re.compile(r"(?m)^[ \t]*-[ \t]*\d{1,4}[ \t]*-[ \t]*\n?")
MAX_CHUNK_CHARS = 4500
CHUNK_OVERLAP_CHARS = 300


class ExtractionError(ValueError):
    """The document has no extractable text. The message is safe to show admins."""


@dataclass(frozen=True)
class Section:
    kind: str  # "preamble" | "article" | "attachment"  (legal_provisions.provision_type)
    number: str | None
    text: str


def extract_text(content: bytes) -> str:
    """Text layer of the PDF with page-number lines removed. Known limitation: pypdf occasionally
    splits a word ("kele bihan"); measured at about 1 in 200 occurrences on PMK 28/2026."""
    try:
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except (PdfReadError, ValueError, TypeError, KeyError) as exc:
        raise ExtractionError("File PDF tidak dapat dibaca") from exc
    if not text.strip():
        raise ExtractionError("Tidak ada teks yang dapat diekstrak (kemungkinan hasil scan); OCR belum tersedia")
    return PAGE_NUMBER_LINE.sub("", text)


def structural_sections(text: str) -> list[Section]:
    """Split into preamble (title, considerations), one section per "Pasal", and attachments.
    Paragraph (ayat) level splitting comes later."""
    articles = list(ARTICLE_HEADING.finditer(text))
    if not articles:
        cleaned = text.strip()
        return [Section("preamble", None, cleaned)] if cleaned else []

    attachment = ATTACHMENT_HEADING.search(text, articles[-1].end())
    body_end = attachment.start() if attachment else len(text)
    sections = []
    if preamble := _without_heading(text[: articles[0].start()]):
        sections.append(Section("preamble", None, preamble))
    for index, match in enumerate(articles):
        end = articles[index + 1].start() if index + 1 < len(articles) else body_end
        if body := _without_heading(text[match.end():end]):
            sections.append(Section("article", match.group(1), body))
    if attachment and (appendix := text[attachment.start():].strip()):
        sections.append(Section("attachment", None, appendix))
    return sections


def _without_heading(block: str) -> str:
    """Drop a trailing chapter/part heading, which belongs to the articles that follow. (Adding the chapter
    title to the embedding was measured on PMK 28/2026 and did not improve retrieval, so it is not kept.)"""
    found = STRUCTURE_HEADING.search(block)
    return (block[: found.start()] if found else block).strip()


def chunks(section: str) -> list[str]:
    """Keep an article whole when possible; split only very long ones, with overlap for context."""
    if len(section) <= MAX_CHUNK_CHARS:
        return [section]
    step = MAX_CHUNK_CHARS - CHUNK_OVERLAP_CHARS
    return [section[start:start + MAX_CHUNK_CHARS] for start in range(0, len(section), step)]
