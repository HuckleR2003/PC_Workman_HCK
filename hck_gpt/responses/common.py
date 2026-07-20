"""hck_gpt.responses.common - shared helpers, imports and data for all
response modules. Extracted from the former 6.5k-line builder.py monolith
(2026-07-15 split). Response handlers live in r_*.py category modules;
ResponseBuilder in builder.py composes them as mixins."""
from __future__ import annotations

# hck_gpt/responses/builder.py
"""
Response Builder

Generates human-readable chatbot responses from a ParseResult + live context.

Design principles:
  - Always enrich responses with LIVE data (never hardcoded numbers)
  - Bilingual: PL when user writes PL, EN when user writes EN
  - Response variety - pools with random.choice() to avoid repetition
  - Short, scannable output (no walls of text)
  - Follow-up hints at end of key responses
  - Ready for LLM drop-in: builder.build() signature stays stable
"""

import random
from typing import List, Optional

from hck_gpt.intents.parser import ParseResult


# Pseudo-processes whose CPU% is meaningless / misleading as a "top consumer":
# System Idle Process reports ~100%×cores precisely when the machine is IDLE,
# so it must never appear as a culprit / top CPU hog in chat answers.
_IDLE_PROC_NAMES = frozenset({"system idle process", "idle", ""})


# ── Bilingual helper ──────────────────────────────────────────────────────────

def _t(lang: str, pl: str, en: str) -> str:
    """Return the Polish or English string based on detected language."""
    return en if lang == "en" else pl


def _pick(lang: str, pl_pool: list, en_pool: list) -> str:
    """Return a random string from the correct language pool."""
    pool = en_pool if lang == "en" else pl_pool
    return random.choice(pool) if pool else ""


# ── Shared follow-up hints ────────────────────────────────────────────────────

_FOLLOWUPS: dict[str, dict[str, list[str]]] = {
    "hw": {
        "pl": [
            "  💬 Możesz zapytać: 'jaki mam GPU' / 'ile RAM' / 'zdrowie systemu'",
            "  💬 Napisz 'specyfikacja' by zobaczyć pełne dane sprzętu",
            "  💬 Wpisz 'wydajność' by sprawdzić aktualne obciążenie",
            "  💬 Zapytaj 'jaki mam dysk' albo 'jaka płyta główna' po więcej",
        ],
        "en": [
            "  💬 Try: 'what GPU do I have' / 'how much RAM' / 'health check'",
            "  💬 Type 'specs' to see full hardware summary",
            "  💬 Type 'performance' to check current load",
            "  💬 Ask 'what disk do I have' or 'motherboard' for more details",
        ],
    },
    "health": {
        "pl": [
            "  💬 Napisz 'top procesy' by zobaczyć co obciąża CPU",
            "  💬 Wpisz 'temperatury' jeśli coś grzeje za mocno",
            "  💬 Sprawdź 'wydajność' po zmknięciu zbędnych programów",
            "  💬 Zapytaj 'dlaczego jest wolno' jeśli coś nie gra",
        ],
        "en": [
            "  💬 Type 'top processes' to see what's using CPU",
            "  💬 Type 'temperatures' if something runs hot",
            "  💬 Check 'performance' after closing unused apps",
            "  💬 Ask 'why is it slow' if something feels off",
        ],
    },
    "perf": {
        "pl": [
            "  💬 Wpisz 'stats' by zobaczyć dzisiejsze średnie",
            "  💬 Zapytaj 'czy CPU throttluje' by sprawdzić dławienie",
            "  💬 Wpisz 'co się zmieniło' by porównać z wczorajem",
        ],
        "en": [
            "  💬 Type 'stats' to see today's averages",
            "  💬 Ask 'is CPU throttling' to check power limits",
            "  💬 Type 'what changed' to compare with yesterday",
        ],
    },
    "security": {
        "pl": [
            "  💬 Wpisz 'top procesy' by zobaczyć co teraz najbardziej pracuje",
            "  💬 Zapytaj 'niepotrzebne programy' by wykryć bloatware w tle",
            "  💬 Sprawdź 'autostart' - zbędne wpisy startowe to ryzyko i obciążenie",
        ],
        "en": [
            "  💬 Type 'top processes' to see what's currently most active",
            "  💬 Ask 'unnecessary programs' to detect background bloat",
            "  💬 Check 'startup programs' - excess startup entries are a risk and a burden",
        ],
    },
    "disk": {
        "pl": [
            "  💬 Zapytaj 'dlaczego dysk jest zajęty' jeśli LED dysku miga non-stop",
            "  💬 Wpisz 'przyspiesz komputer' po kompleksowy plan optymalizacji",
            "  💬 Sprawdź 'jaki mam dysk' dla pełnych danych o modelu i partycjach",
        ],
        "en": [
            "  💬 Ask 'why is disk so active' if the drive LED is flashing non-stop",
            "  💬 Type 'speed up pc' for a full optimization plan",
            "  💬 Check 'what disk do I have' for full model and partition details",
        ],
    },
    "why": {
        "pl": [
            "  💬 Wpisz 'top procesy' by namierzyć winowajcę",
            "  💬 Zapytaj 'zdrowie systemu' po pełną diagnozę w jednym miejscu",
            "  💬 Napisz 'przyspiesz komputer' po konkretny plan naprawy",
        ],
        "en": [
            "  💬 Type 'top processes' to pinpoint the culprit",
            "  💬 Ask 'health check' for full diagnostics in one place",
            "  💬 Type 'speed up pc' for a concrete fix plan",
        ],
    },
    "process": {
        "pl": [
            "  💬 Podaj nazwę dowolnego procesu - wyjaśnię co robi",
            "  💬 Wpisz 'dlaczego ram wysoki' jeśli pamięć jest zajęta",
            "  💬 Sprawdź 'niepotrzebne programy' by odciążyć tło",
        ],
        "en": [
            "  💬 Name any process - I'll explain what it does",
            "  💬 Type 'why is ram high' if memory is full",
            "  💬 Check 'unnecessary programs' to reduce background load",
        ],
    },
    "session": {
        "pl": [
            "  💬 Wpisz 'stats' po dzisiejsze średnie CPU / RAM",
            "  💬 Zapytaj 'co się zmieniło w wydajności' po szczegółowe delty",
            "  💬 Sprawdź 'zdrowie systemu' dla aktualnego stanu na żywo",
        ],
        "en": [
            "  💬 Type 'stats' for today's CPU / RAM averages",
            "  💬 Ask 'what changed in performance' for detailed deltas",
            "  💬 Check 'health check' for current live system status",
        ],
    },
    "startup": {
        "pl": [
            "  💬 Zapytaj 'czy mogę wyłączyć X ze startu' o konkretny program",
            "  💬 Wpisz 'co zagraża mojemu PC' po pełny ranking ryzyk",
            "  💬 Sprawdź 'zdrowie systemu' po całościową diagnozę",
        ],
        "en": [
            "  💬 Ask 'is it safe to disable X from startup' for a specific program",
            "  💬 Type 'what risks does my pc have' for a full risk ranking",
            "  💬 Check 'health check' for a full system overview",
        ],
    },
}


def _followup(key: str, lang: str) -> str:
    pool = _FOLLOWUPS.get(key, {})
    lines = pool.get(lang, pool.get("pl", []))
    return random.choice(lines) if lines else ""


# ── Delta label - contextualises a live metric against 7-day typical ─────────

def _delta_label(current: float, typical, lang: str) -> str:
    """
    Compare current (live) value with typical (7-day avg).
    Returns a short contextual string, e.g.:
        EN: '-> within your norm  (avg 42%)'  /  '↑ +23% above your norm  (avg 42%)'
        PL: '-> norma  (śr. 42%)'             /  '↑ +23% vs typowe  (42%)'
    Returns '' when typical is None or zero.
    """
    if typical is None:
        return ""
    try:
        typ = float(typical)
    except (TypeError, ValueError):
        return ""
    if typ <= 0:
        return ""
    delta = current - typ
    if abs(delta) < 5:
        return (f"-> within your norm  (avg {typ:.0f}%)" if lang == "en"
                else f"-> norma  (śr. {typ:.0f}%)")
    elif delta > 0:
        return (f"↑ +{delta:.0f}% above your norm  (avg {typ:.0f}%)" if lang == "en"
                else f"↑ +{delta:.0f}% vs typowe  ({typ:.0f}%)")
    else:
        return (f"↓ {abs(delta):.0f}% below your norm  (avg {typ:.0f}%)" if lang == "en"
                else f"↓ {abs(delta):.0f}% poniżej normy  (śr. {typ:.0f}%)")


# ── Hardware profile - capability flags for personalised advice ───────────────

def _hw_profile(hw: dict) -> dict:
    """
    Derive hardware capability flags from stored hardware data.
    Used to tailor advice to the user's actual specs rather than generic tips.
    """
    ram_gb    = float(hw.get("ram_total_gb") or 16)
    cpu_cores = int(hw.get("cpu_cores")      or 4)
    disk      = (hw.get("disk_model")        or "").upper()

    # SSD detection - if any SSD/NVMe keyword present -> SSD
    _ssd_kw = ("SSD", "NVME", "NVM", "M.2", "PCIE", "SOLID STATE", "EVO",
               "870", "970", "980", "SA400", "MZ-", "CT", "ADATA", "KINGSTON")
    is_ssd = any(k in disk for k in _ssd_kw)
    # HDD flag only when we have a model name AND it's not SSD
    is_hdd = bool(disk) and not is_ssd

    return {
        "ram_gb":       ram_gb,
        "ram_low":      ram_gb <= 8,
        "ram_very_low": ram_gb <= 4,
        "cpu_cores":    cpu_cores,
        "few_cores":    cpu_cores <= 4,
        "is_hdd":       is_hdd,
        "is_ssd":       is_ssd,
    }


# ── Main class ────────────────────────────────────────────────────────────────


__all__ = [
    "random",
    "List",
    "Optional",
    "ParseResult",
    "_IDLE_PROC_NAMES",
    "_t",
    "_pick",
    "_FOLLOWUPS",
    "_followup",
    "_delta_label",
    "_hw_profile",
]
