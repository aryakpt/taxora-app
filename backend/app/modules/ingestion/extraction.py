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
# The elucidation of a UU or PP: a standalone "PENJELASAN" line followed by "ATAS UNDANG-UNDANG ..." or
# "ATAS PERATURAN ...". It repeats "Pasal N" headings ("Pasal 2 Cukup jelas."), which are explanations,
# not the articles themselves.
ELUCIDATION_HEADING = re.compile(r"(?m)^[ \t]*PENJELASAN[ \t]*\n\s*ATAS\b")
# Page numbers printed as "- 12 -" on their own line. Layout, not legal text.
PAGE_NUMBER_LINE = re.compile(r"(?m)^[ \t]*-[ \t]*\d{1,4}[ \t]*-[ \t]*\n?")
MAX_CHUNK_CHARS = 4500
CHUNK_OVERLAP_CHARS = 300


class ExtractionError(ValueError):
    """The document has no extractable text. The message is safe to show admins."""


@dataclass(frozen=True)
class Section:
    # legal_provisions.provision_type: "preamble" | "article" | "attachment" | "elucidation" (PENJELASAN;
    # number None for the general part "I. UMUM", else the article it explains)
    kind: str
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
    """Split into preamble (title, considerations), one section per "Pasal", attachments ("LAMPIRAN"), and the
    elucidation ("PENJELASAN"), in document order. Paragraph (ayat) level splitting comes later."""
    articles = list(ARTICLE_HEADING.finditer(text))
    if not articles:
        cleaned = text.strip()
        return [Section("preamble", None, cleaned)] if cleaned else []

    elucidation = ELUCIDATION_HEADING.search(text, articles[0].end())
    body_end = elucidation.start() if elucidation else len(text)
    body_articles = [match for match in articles if match.start() < body_end]
    # The attachment can follow the articles (before the elucidation) or come after the elucidation.
    attachment = (ATTACHMENT_HEADING.search(text, body_articles[-1].end(), body_end)
                  or (ATTACHMENT_HEADING.search(text, _last_heading_end(text, elucidation)) if elucidation else None))

    sections = []
    if preamble := _without_heading(text[: articles[0].start()]):
        sections.append(Section("preamble", None, preamble))
    articles_end = attachment.start() if attachment and attachment.start() < body_end else body_end
    sections += _numbered(text, body_articles, articles_end, "article")
    if attachment and attachment.start() < body_end and (appendix := text[attachment.start():body_end].strip()):
        sections.append(Section("attachment", None, appendix))
    if elucidation:
        end = attachment.start() if attachment and attachment.start() > body_end else len(text)
        sections += _elucidation(text, elucidation.start(), end)
        if end < len(text) and (appendix := text[end:].strip()):
            sections.append(Section("attachment", None, appendix))
    return sections


def _numbered(text: str, headings: list[re.Match], end: int, kind: str) -> list[Section]:
    sections = []
    for index, match in enumerate(headings):
        stop = headings[index + 1].start() if index + 1 < len(headings) else end
        if body := _without_heading(text[match.end():stop]):
            sections.append(Section(kind, match.group(1), body))
    return sections


def _elucidation(text: str, start: int, end: int) -> list[Section]:
    """The general part ("I. UMUM") and one section per explained article ("Pasal 2  Cukup jelas.")."""
    headings = list(ARTICLE_HEADING.finditer(text, start, end))
    general_end = headings[0].start() if headings else end
    sections = [Section("elucidation", None, general)] if (general := text[start:general_end].strip()) else []
    return sections + _numbered(text, headings, end, "elucidation")


def _last_heading_end(text: str, elucidation: re.Match) -> int:
    """Where the last "Pasal" of the elucidation starts, so a "LAMPIRAN" after it is found but a mention
    inside the general part is not."""
    headings = list(ARTICLE_HEADING.finditer(text, elucidation.end()))
    return headings[-1].end() if headings else elucidation.end()


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
