from datetime import date

import pytest

from app.modules.query_understanding.period import mentioned_year, reference_date

TODAY = date(2026, 11, 23)


@pytest.mark.parametrize(("question", "year"), [
    ("Berapa tarif PPh 21 tahun pajak 2024?", 2024),
    ("Apakah faktur untuk masa pajak Maret 2025 masih bisa dibetulkan?", 2025),
    ("untuk tahun 2023 bagaimana?", 2023),
    ("What was the rule in tax year 2022?", 2022),
    ("Apakah PMK 28 Tahun 2026 berlaku?", None),                    # regulation number, not a tax year
    ("Menurut UU Nomor 7 Tahun 1983, apa itu PPh?", None),
    ("Apakah PMK 39/PMK.03/2018 masih berlaku?", None),
    ("Menurut PP 55 Tahun 2022, berapa tarif UMKM untuk tahun pajak 2024?", 2024),
    ("Berapa tarif PPN?", None),
])
def test_the_tax_year_is_read_from_the_question(question, year):
    assert mentioned_year(question) == year


def test_reference_date_is_the_end_of_a_past_year_or_today():
    assert reference_date("tahun pajak 2024", TODAY) == date(2024, 12, 31)
    assert reference_date("Berapa tarif PPN?", TODAY) == TODAY
    assert reference_date("tahun pajak 2030", TODAY) == TODAY  # future: rules known today
