"""The date a question is about, read from the question itself (there is no separate tax period field).

"tahun pajak 2025", "masa pajak Maret 2025", "untuk tahun 2024" set the year. "PMK 28 Tahun 2026" or
"UU Nomor 7 Tahun 1983" do not: there "Tahun" belongs to a regulation number, recognised by the number
right before it. Without a year the question is about today.
"""

import re
from datetime import date

_YEAR_PHRASE = re.compile(
    r"\b(?P<phrase>tahun(?:\s+pajak)?|masa\s+pajak(?:\s+[a-z]+)?|periode|tax\s+year|fiscal\s+year)\s+"
    r"(?P<year>(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_ENDS_WITH_NUMBER = re.compile(r"\d\s*$")


def mentioned_year(text: str) -> int | None:
    """The last tax year mentioned, ignoring regulation numbers."""
    years = [int(match["year"]) for match in _YEAR_PHRASE.finditer(text)
             if not _is_regulation_number(text, match)]
    return years[-1] if years else None


def _is_regulation_number(text: str, match: re.Match) -> bool:
    """A bare "Tahun" right after a number ("28 Tahun 2026"). "PPh 21 tahun pajak 2024" is a tax year;
    the ambiguous "PPh 21 tahun 2024" is read as a regulation number (no filter), the safer mistake."""
    return match["phrase"].lower() == "tahun" and bool(_ENDS_WITH_NUMBER.search(text[: match.start()]))


def reference_date(text: str, today: date | None = None) -> date:
    """End of the mentioned year (rules in force during that year), or today. A future year is capped at today."""
    today = today or date.today()
    year = mentioned_year(text)
    if year is None or year >= today.year:
        return today
    return date(year, 12, 31)
