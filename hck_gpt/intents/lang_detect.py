# hck_gpt/intents/lang_detect.py
"""
Language Detector

Determines whether a user message is Polish or English using:
  1. Polish diacritics — very strong signal (ą ę ó ś ź ż ć ń ł)
  2. Common Polish function words
  3. Common English function words
  4. Fallback: Polish (primary language of PC Workman)

Returns: "pl" | "en"
"""
from __future__ import annotations

_PL_DIACRITICS = frozenset("ąęóśźżćńłĄĘÓŚŹŻĆŃŁ")

_PL_WORDS = frozenset({
    "czy", "jak", "mam", "jest", "co", "ile", "jaki", "jaka", "jakie",
    "mój", "moja", "moje", "się", "nie", "tak", "już", "dla", "przez",
    "przy", "więcej", "mniej", "gdzie", "kiedy", "który", "która",
    "pokaż", "sprawdź", "powiedz", "chcę", "chciałbym", "chciałabym",
    "bardzo", "dobrze", "trochę", "znowu", "jeszcze", "proszę",
    "masz", "mamy", "mają", "tego", "tej", "ten", "ta", "te",
    "tutaj", "tam", "teraz", "dzisiaj", "dzis", "wczoraj",
    "komputer", "procesor", "pamięć", "dysk", "karta", "płyta",
    "dobra", "spoko", "git", "dzięki", "cześć", "hej", "siema",
})

_EN_WORDS = frozenset({
    "what", "how", "my", "is", "are", "show", "tell", "check",
    "does", "do", "can", "will", "the", "and", "or", "its",
    "this", "that", "which", "where", "when", "why",
    "please", "want", "need", "have", "got", "get", "give",
    "computer", "processor", "memory", "disk", "card", "board",
    "hello", "hi", "hey", "thanks", "thank",
    "current", "running", "usage", "status", "info",
})


def detect_language(text: str) -> str:
    """
    Returns 'pl' or 'en' based on content analysis.
    Fast — no external dependencies.
    """
    if not text or not text.strip():
        return "pl"

    # Polish diacritics → instant PL detection
    if any(c in _PL_DIACRITICS for c in text):
        return "pl"

    tokens = set(text.lower().split())
    pl_score = len(tokens & _PL_WORDS)
    en_score = len(tokens & _EN_WORDS)

    if en_score > pl_score:
        return "en"
    return "pl"  # Default: Polish
