import pytest

from app.modules.query_understanding.language import detect_language


@pytest.mark.parametrize(("question", "language"), [
    ("apa itu ppn?", "id"),
    ("Berapa tarif PPh 21 untuk karyawan tetap?", "id"),
    ("Kapan PMK 28 Tahun 2026 mulai berlaku?", "id"),
    ("Siapa saja yang bisa mendapat pengembalian pendahuluan?", "id"),
    ("What is the VAT rate in Indonesia?", "en"),
    ("How is pajak penghasilan calculated for employees?", "en"),  # Indonesian tax terms, English question
    ("Do I need to file an SPT if my income is below PTKP?", "en"),
])
def test_the_question_decides_the_language(question, language):
    assert detect_language(question, fallback="en" if language == "id" else "id") == language


@pytest.mark.parametrize("question", ["halo", "PPh 21?", "PPN 12%", "NPWP"])
def test_unclear_questions_use_the_interface_language(question):
    assert detect_language(question, fallback="en") == "en"
    assert detect_language(question, fallback="id") == "id"
