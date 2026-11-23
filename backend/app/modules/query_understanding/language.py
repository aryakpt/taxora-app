"""Answer in the language of the question (Indonesian or English).

A count of common function words, no model call. Tax vocabulary is ignored because English questions
about Indonesian tax use Indonesian terms ("What is pajak penghasilan?"). When the question gives no clear
signal ("halo", "PPh 21?"), the interface language decides.
"""

import re
from typing import Literal

Language = Literal["id", "en"]

_INDONESIAN = frozenset(
    "yang dan di ke dari untuk dengan atau pada ini itu apa apakah bagaimana berapa siapa kapan mengapa kenapa "
    "dimana mana saya aku kami kita anda kamu dia adalah ialah akan bisa dapat boleh harus wajib sudah belum "
    "tidak bukan juga jika kalau karena agar supaya tentang oleh dalam atas bagi seperti lagi masih hanya "
    "tolong mohon bagaimanakah apakah berapakah ada saja sama serta maupun tetapi namun".split()
)
_ENGLISH = frozenset(
    "the a an is are was were be been what how which who whom whose when where why do does did can could "
    "should would will shall may might must have has had i my me we our you your it its this that these those "
    "of to in on for with from by about if or and but not no any some there please".split()
)


def detect_language(text: str, fallback: Language) -> Language:
    words = re.findall(r"[a-z]+", text.lower())
    indonesian = sum(word in _INDONESIAN for word in words)
    english = sum(word in _ENGLISH for word in words)
    if indonesian > english:
        return "id"
    if english > indonesian:
        return "en"
    return fallback
