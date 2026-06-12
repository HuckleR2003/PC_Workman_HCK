# hck_gpt/intents/lang_detect.py
"""
Language Detector

Determines whether a user message is Polish or English using:
  1. Polish diacritics - very strong signal (ą ę ó ś ź ż ć ń ł)
  2. Common Polish function words
  3. Common English function words
  4. Fallback: Polish (primary language of PC Workman)

Returns: "pl" | "en"
"""
from __future__ import annotations

_PL_DIACRITICS = frozenset("ąęóśźżćńłĄĘÓŚŹŻĆŃŁ")

_PL_WORDS = frozenset({
    # Question words / grammatical markers
    "czy", "jak", "mam", "jest", "co", "ile", "jaki", "jaka", "jakie",
    "moj", "moja", "moje", "moj", "sie", "nie", "tak", "juz", "dla", "przez",
    "przy", "wiecej", "mniej", "gdzie", "kiedy", "ktory", "ktora",
    "pokaz", "sprawdz", "powiedz", "chce", "chcialbym", "chcialabym",
    "bardzo", "dobrze", "troche", "znowu", "jeszcze", "prosze",
    "masz", "mamy", "maja", "tego", "tej", "ten", "ta", "te",
    "tutaj", "tam", "teraz", "dzisiaj", "dzis", "wczoraj",
    # Accented versions (auto-detected via diacritics, but just in case)
    "mój", "moja", "moje", "się", "już", "więcej", "gdzie", "który", "która",
    "pokaż", "sprawdź", "powiedz", "chcę", "chciałbym", "chciałabym",
    "bardzo", "dobrze", "trochę", "znowu", "jeszcze", "proszę",
    # Common Polish tech words (accent-stripped variants)
    "komputer", "procesor", "pamiec", "dysk", "karta", "plyta",
    "grzeje", "wolno", "szybko", "wysoki", "niski", "duzo", "malo",
    "program", "aplikacja", "sterownik", "usluga",
    "pc", "komp", "sprzet", "system", "windows",
    # Greetings / meta (ASCII safe)
    "dobra", "spoko", "git", "dzieki", "czesc", "hej", "siema", "hejka",
    "nara", "okej", "oki", "no", "dobranoc", "dobry", "wieczor", "ranek",
    # Common verbs
    "dziala", "nie dziala", "wolno", "zwalnia", "sie grzeje", "grzeje",
    "uruchom", "wylacz", "wlacz", "zamknij", "otworz",
})

_EN_WORDS = frozenset({
    # Question words / auxiliaries
    "what", "how", "my", "is", "are", "show", "tell", "check",
    "does", "do", "can", "will", "the", "and", "or", "its",
    "this", "that", "which", "where", "when", "why", "who",
    "i", "me", "it", "am", "was", "were", "has", "have", "had",
    "would", "could", "should", "just", "now", "right", "up",
    # Actions / intents
    "please", "want", "need", "got", "get", "give", "run",
    "see", "list", "find", "read", "open", "close", "kill",
    "stop", "start", "restart", "fix", "help", "test", "scan",
    # Nouns common in EN tech queries
    "computer", "processor", "memory", "disk", "card", "board",
    "specs", "spec", "top", "process", "processes", "game", "games",
    "cpu", "gpu", "ram", "ssd", "temp", "temps", "speed", "load",
    "driver", "drivers", "update", "startup", "boot", "crash",
    "battery", "fan", "fans", "network", "connection", "internet",
    # Greetings / meta / time-of-day
    "hello", "hi", "hey", "thanks", "thank", "ok", "okay",
    "good", "morning", "evening", "afternoon", "night",
    "bye", "goodbye", "you", "there", "mate", "bro",
    # Modifiers common in EN
    "current", "running", "usage", "status", "info", "much",
    "many", "all", "any", "most", "least", "high", "low", "fast",
    "slow", "hot", "cold", "old", "new", "best", "worst", "total",
    "free", "used", "available", "installed", "detected", "found",
})


def detect_language(text: str) -> str:
    """
    Returns 'pl' or 'en' based on content analysis.
    Fast - no external dependencies.
    """
    if not text or not text.strip():
        return "pl"

    # Polish diacritics -> instant PL detection
    if any(c in _PL_DIACRITICS for c in text):
        return "pl"

    tokens = set(text.lower().split())
    pl_score = len(tokens & _PL_WORDS)
    en_score = len(tokens & _EN_WORDS)

    if en_score > pl_score:
        return "en"
    return "pl"  # Default: Polish
