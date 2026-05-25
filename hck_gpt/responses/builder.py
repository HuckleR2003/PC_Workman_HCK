# hck_gpt/responses/builder.py
"""
Response Builder

Generates human-readable chatbot responses from a ParseResult + live context.

Design principles:
  - Always enrich responses with LIVE data (never hardcoded numbers)
  - Bilingual: PL when user writes PL, EN when user writes EN
  - Response variety — pools with random.choice() to avoid repetition
  - Short, scannable output (no walls of text)
  - Follow-up hints at end of key responses
  - Ready for LLM drop-in: builder.build() signature stays stable
"""
from __future__ import annotations

import random
from typing import List, Optional

from hck_gpt.intents.parser import ParseResult


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
            "  💬 Sprawdź 'autostart' — zbędne wpisy startowe to ryzyko i obciążenie",
        ],
        "en": [
            "  💬 Type 'top processes' to see what's currently most active",
            "  💬 Ask 'unnecessary programs' to detect background bloat",
            "  💬 Check 'startup programs' — excess startup entries are a risk and a burden",
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
            "  💬 Podaj nazwę dowolnego procesu — wyjaśnię co robi",
            "  💬 Wpisz 'dlaczego ram wysoki' jeśli pamięć jest zajęta",
            "  💬 Sprawdź 'niepotrzebne programy' by odciążyć tło",
        ],
        "en": [
            "  💬 Name any process — I'll explain what it does",
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


# ── Delta label — contextualises a live metric against 7-day typical ─────────

def _delta_label(current: float, typical, lang: str) -> str:
    """
    Compare current (live) value with typical (7-day avg).
    Returns a short contextual string, e.g.:
        EN: '→ within your norm  (avg 42%)'  /  '↑ +23% above your norm  (avg 42%)'
        PL: '→ norma  (śr. 42%)'             /  '↑ +23% vs typowe  (42%)'
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
        return (f"→ within your norm  (avg {typ:.0f}%)" if lang == "en"
                else f"→ norma  (śr. {typ:.0f}%)")
    elif delta > 0:
        return (f"↑ +{delta:.0f}% above your norm  (avg {typ:.0f}%)" if lang == "en"
                else f"↑ +{delta:.0f}% vs typowe  ({typ:.0f}%)")
    else:
        return (f"↓ {abs(delta):.0f}% below your norm  (avg {typ:.0f}%)" if lang == "en"
                else f"↓ {abs(delta):.0f}% poniżej normy  (śr. {typ:.0f}%)")


# ── Hardware profile — capability flags for personalised advice ───────────────

def _hw_profile(hw: dict) -> dict:
    """
    Derive hardware capability flags from stored hardware data.
    Used to tailor advice to the user's actual specs rather than generic tips.
    """
    ram_gb    = float(hw.get("ram_total_gb") or 16)
    cpu_cores = int(hw.get("cpu_cores")      or 4)
    disk      = (hw.get("disk_model")        or "").upper()

    # SSD detection — if any SSD/NVMe keyword present → SSD
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

class ResponseBuilder:
    """
    Template-based bilingual response generator.
    Enriched with live data from SystemContext and UserKnowledge.
    """

    PREFIX = "hck_GPT:"

    def __init__(self) -> None:
        # Rotation guard: track last-used index per response pool key
        self._last_pool_idx: dict[str, int] = {}

    def _pick_fresh(self, key: str, lang: str, pl_pool: list, en_pool: list) -> str:
        """Pick from pool, avoiding the last-used index (rotation guard)."""
        pool = en_pool if lang == "en" else pl_pool
        if not pool:
            return ""
        last = self._last_pool_idx.get(f"{key}_{lang}", -1)
        candidates = [i for i in range(len(pool)) if i != last]
        idx = random.choice(candidates) if candidates else random.randrange(len(pool))
        self._last_pool_idx[f"{key}_{lang}"] = idx
        return pool[idx]

    def build(self, result: ParseResult, lang: str = "pl") -> Optional[List[str]]:
        """
        Returns a list of message lines, or None if the intent
        is not handled here (falls back to legacy ChatHandler).
        """
        handler = getattr(self, f"_resp_{result.intent}", None)
        if handler is None:
            return None
        try:
            out = handler(result, lang)
            return out if isinstance(out, list) else [out]
        except Exception:
            return None

    # ── Hardware — all specs ──────────────────────────────────────────────────

    def _resp_hw_all(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        hw       = user_knowledge.get_all_hardware()
        patterns = user_knowledge.get_all_patterns()

        if not hw:
            return self._live_hw_fallback(lang)

        lines = [_t(lang,
                    f"{self.PREFIX} Twoje podzespoły:",
                    f"{self.PREFIX} Your components:")]

        # ── CPU ───────────────────────────────────────────────────────────────
        if hw.get("cpu_model"):
            cores   = hw.get("cpu_cores",    "?")
            threads = hw.get("cpu_threads",  "")
            boost   = hw.get("cpu_boost_ghz", "?")
            thr_str = f"/{threads}T" if threads and str(threads) != str(cores) else ""
            lines.append("  ◈ CPU")
            lines.append(f"    {hw['cpu_model']}")
            lines.append(f"    {cores}C{thr_str}  ·  boost {boost} GHz")

        # ── GPU ───────────────────────────────────────────────────────────────
        if hw.get("gpu_model"):
            vram_str = f"  ·  {hw['gpu_vram_gb']} GB VRAM" if hw.get("gpu_vram_gb") else ""
            lines.append("  ◈ GPU")
            lines.append(f"    {hw['gpu_model']}{vram_str}")

        # ── RAM ───────────────────────────────────────────────────────────────
        if hw.get("ram_total_gb"):
            spd     = f"  ·  {hw['ram_speed_mhz']} MHz" if hw.get("ram_speed_mhz") else ""
            typ_ram = patterns.get("typical_ram_avg")
            avg_str = f"  ·  avg {typ_ram}%" if typ_ram else ""
            lines.append("  ◈ RAM")
            lines.append(f"    {hw['ram_total_gb']} GB{spd}{avg_str}")

        # ── Storage ───────────────────────────────────────────────────────────
        lines.append("  ◈ " + _t(lang, "Dysk", "Storage"))
        disk_model = hw.get("disk_model")
        if disk_model:
            lines.append(f"    {disk_model}")
        try:
            import psutil
            for p in psutil.disk_partitions(all=False):
                if "remote" in (p.opts or "").lower():
                    continue
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    total_gb = round(u.total / 1_073_741_824, 1)
                    free_gb  = round(u.free  / 1_073_741_824, 1)
                    free_lbl = _t(lang, "wolne", "free")
                    lines.append(f"    {p.device}  {total_gb} GB  /  {free_gb} GB {free_lbl}")
                except Exception:
                    pass
                if len(lines) > 12:
                    break
        except Exception:
            summary = hw.get("storage_summary")
            if summary:
                for part in summary.split(" | "):
                    lines.append(f"    {part.strip()}")

        # ── Motherboard ───────────────────────────────────────────────────────
        if hw.get("motherboard_model"):
            lines.append("  ◈ " + _t(lang, "Płyta główna", "Motherboard"))
            lines.append(f"    {hw['motherboard_model']}")

        # ── OS ────────────────────────────────────────────────────────────────
        if hw.get("os_version"):
            lines.append(f"  ◈ OS  {hw['os_version']}")

        lines.append(_followup("hw", lang))
        return lines

    # ── Hardware — CPU ────────────────────────────────────────────────────────

    def _resp_hw_cpu(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.session_memory  import session_memory
        hw       = user_knowledge.get_all_hardware()
        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()

        model   = hw.get("cpu_model",     _t(lang, "nieznany model", "unknown model"))
        cores_p = hw.get("cpu_cores",     snap.get("cpu_cores_physical", "?"))
        cores_l = hw.get("cpu_threads",   snap.get("cpu_cores_logical",  "?"))
        boost   = hw.get("cpu_boost_ghz", "?")
        cur_mhz = snap.get("cpu_mhz",  "—")
        cur_pct = snap.get("cpu_pct",  "—")
        throttle = ""
        if snap.get("cpu_throttled"):
            throttle = _t(lang, "  ⚠ throttled!", "  ⚠ throttling!")

        # ── Pomysł 1: delta on current usage ─────────────────────────────────
        try:
            cur_f = float(str(cur_pct).replace("%", "") or 0)
        except (ValueError, TypeError):
            cur_f = 0.0
        delta = _delta_label(cur_f, patterns.get("typical_cpu_avg"), lang)
        delta_sfx = f"    {delta}" if delta else ""

        # ── Pomysł 2: record for later cross-response references ──────────────
        session_memory.record_response_data("hw_cpu", {
            "model":       str(model),
            "cores":       cores_p,
            "current_pct": cur_pct,
        })

        if lang == "en":
            return [
                f"{self.PREFIX} Processor:",
                f"  Model:    {model}",
                f"  Cores:    {cores_p} physical  /  {cores_l} logical",
                f"  Boost:    {boost} GHz",
                f"  Now:      {cur_mhz} MHz  |  {cur_pct}% usage{throttle}{delta_sfx}",
                _followup("hw", lang),
            ]
        return [
            f"{self.PREFIX} Procesor:",
            f"  Model:    {model}",
            f"  Rdzenie:  {cores_p} fizyczne  /  {cores_l} logiczne",
            f"  Boost:    {boost} GHz",
            f"  Teraz:    {cur_mhz} MHz  |  {cur_pct}% użycia{throttle}{delta_sfx}",
            _followup("hw", lang),
        ]

    # ── Hardware — GPU ────────────────────────────────────────────────────────

    def _resp_hw_gpu(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        hw    = user_knowledge.get_all_hardware()
        model = hw.get("gpu_model", None)
        vram  = hw.get("gpu_vram_gb", None)

        if not model:
            return [_t(lang,
                       f"{self.PREFIX} Nie mam jeszcze danych o karcie graficznej.",
                       f"{self.PREFIX} No GPU data yet — hardware scan is running.")]

        # ── Pomysł 2: record for cross-response references ───────────────────
        from hck_gpt.memory.session_memory import session_memory
        session_memory.record_response_data("hw_gpu", {
            "model":   str(model),
            "vram_gb": vram,
        })

        vram_str = f"\n  VRAM:  {vram} GB" if vram else ""
        header = _t(lang,
                    f"{self.PREFIX} Karta graficzna:",
                    f"{self.PREFIX} Graphics card:")
        return [header, f"  Model:{vram_str}  {model}", _followup("hw", lang)]

    # ── Hardware — RAM ────────────────────────────────────────────────────────

    def _resp_hw_ram(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        from hck_gpt.context.system_context import system_context
        hw       = user_knowledge.get_all_hardware()
        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()

        total   = hw.get("ram_total_gb", snap.get("ram_total_gb", "?"))
        speed   = hw.get("ram_speed_mhz")
        model   = hw.get("ram_model")       # WMI part number, e.g. "CMK16GX4M2B3200C16"
        pct     = snap.get("ram_pct",    "—")
        used    = snap.get("ram_used_gb", "—")
        free    = snap.get("ram_free_gb", "—")
        typ_avg = patterns.get("typical_ram_avg")  # 7-day average from usage_patterns

        spd_str   = f"  ·  {speed} MHz" if speed else ""
        model_str = f"  ({model})" if model else ""

        # Determine if RAM pressure is elevated
        try:
            pct_f = float(str(pct).replace("%", ""))
        except Exception:
            pct_f = 0.0
        avg_f = float(typ_avg) if typ_avg else 0.0
        high_pressure = pct_f > 75 or avg_f > 70

        # ── Pomysł 2: record for cross-response references ───────────────────
        from hck_gpt.memory.session_memory import session_memory
        session_memory.record_response_data("hw_ram", {
            "total_gb":    total,
            "speed":       speed,
            "model":       model,
            "current_pct": pct,
            "typical_avg": typ_avg,
        })

        if lang == "en":
            lines = [
                f"{self.PREFIX} RAM:",
                f"  Model:    {total} GB{spd_str}{model_str}",
                f"  Now:      {used} GB used  ({pct}%)  /  {free} GB free",
            ]
            if typ_avg:
                lines.append(f"  Avg use:  {typ_avg}%  (7-day typical activity)")
            if high_pressure:
                lines.append("  💡 Reduce background services and apps:")
                lines.append("     [→ Optimization]  or expand Virtual Memory  [→ Virtual Memory]")
            else:
                lines.append("  💬 Manage background apps  [→ Optimization]")
        else:
            lines = [
                f"{self.PREFIX} Pamięć RAM:",
                f"  Model:    {total} GB{spd_str}{model_str}",
                f"  Teraz:    {used} GB użyte  ({pct}%)  /  {free} GB wolne",
            ]
            if typ_avg:
                lines.append(f"  Śr. użycie:  {typ_avg}%  (typowa aktywność — 7 dni)")
            if high_pressure:
                lines.append("  💡 Rozważ zmniejszenie usług i aplikacji w tle:")
                lines.append("     [→ Optimization]  lub dodaj Pamięć Wirtualną  [→ Virtual Memory]")
            else:
                lines.append("  💬 Zarządzaj aplikacjami w tle  [→ Optimization]")
        return lines

    # ── Hardware — Motherboard ────────────────────────────────────────────────

    def _resp_hw_motherboard(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        hw   = user_knowledge.get_all_hardware()
        mobo = hw.get("motherboard_model", None)

        if mobo:
            header = _t(lang, f"{self.PREFIX} Płyta główna:", f"{self.PREFIX} Motherboard:")
            return [f"{header}  {mobo}"]
        if lang == "en":
            return [
                f"{self.PREFIX} No motherboard model found yet.",
                "  Try: Start → System Information → Components → Baseboard",
            ]
        return [
            f"{self.PREFIX} Nie mam jeszcze modelu płyty głównej.",
            "  Spróbuj: Start → Informacje o systemie → Składniki → Karta główna",
        ]

    # ── Hardware — Storage ────────────────────────────────────────────────────

    def _resp_hw_storage(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        hw         = user_knowledge.get_all_hardware()
        disk_model = hw.get("disk_model")   # WMI Win32_DiskDrive model name

        lines = [_t(lang, f"{self.PREFIX} Twój dysk:", f"{self.PREFIX} Your disk:")]

        # Lead with the physical disk model if we have it
        if disk_model:
            lines.append(f"  Model:   {disk_model}")

        # Per-partition capacity + free space (live)
        try:
            import psutil
            partition_count = 0
            for p in psutil.disk_partitions(all=False):
                if "remote" in (p.opts or "").lower():
                    continue
                try:
                    u        = psutil.disk_usage(p.mountpoint)
                    total_gb = round(u.total / 1_073_741_824, 1)
                    free_gb  = round(u.free  / 1_073_741_824, 1)
                    free_lbl = _t(lang, "wolne", "free")
                    warn     = "  ⚠ " + _t(lang, "prawie pełny!", "almost full!") \
                               if u.percent > 85 else ""
                    lines.append(
                        f"  {p.device}  {total_gb} GB"
                        f"  /  {free_gb} GB {free_lbl}  ({u.percent:.0f}%){warn}"
                    )
                    partition_count += 1
                except Exception:
                    pass
                if partition_count >= 5:   # cap
                    break
        except Exception:
            # Fallback: stored psutil summary
            summary = hw.get("storage_summary")
            if summary:
                for part in summary.split(" | "):
                    lines.append(f"  {part.strip()}")

        if len(lines) == 1:
            # Nothing added — scanner hasn't run yet
            lines.append(_t(lang,
                            "  Brak danych — skan sprzętu trwa lub nie powiódł się.",
                            "  No data yet — hardware scan still running."))

        lines.append(_followup("hw", lang))
        return lines

    # ── Health check ──────────────────────────────────────────────────────────

    _HEALTH_INTROS_PL = [
        "{P} Ocena zdrowia systemu:",
        "{P} Sprawdzam kondycję PC...",
        "{P} Diagnostyka systemu:",
        "{P} Oto jak twój PC sobie radzi:",
        "{P} Szybki przegląd stanu maszyny:",
    ]
    _HEALTH_INTROS_EN = [
        "{P} System health check:",
        "{P} Here's how your PC is doing:",
        "{P} Running diagnostics:",
        "{P} Let's see how your machine is holding up:",
        "{P} Quick system check:",
    ]

    def _resp_health_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        from hck_gpt.memory.session_memory  import session_memory

        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()
        issues   = []
        good     = []

        cpu = float(snap.get("cpu_pct", 0) or 0)
        ram = float(snap.get("ram_pct", 0) or 0)

        # ── Pomysł 1: delta labels ────────────────────────────────────────────
        typ_cpu  = patterns.get("typical_cpu_avg")
        typ_ram  = patterns.get("typical_ram_avg")
        cpu_ctx  = f"    {_delta_label(cpu, typ_cpu, lang)}" if typ_cpu else ""
        ram_ctx  = f"    {_delta_label(ram, typ_ram, lang)}" if typ_ram else ""

        if lang == "en":
            if cpu > 90:
                issues.append(f"  ⚠ CPU critical:  {cpu:.0f}%{cpu_ctx}")
            elif cpu > 75:
                issues.append(f"  ! CPU high:      {cpu:.0f}%{cpu_ctx}")
            else:
                good.append(f"  ✓ CPU OK:        {cpu:.0f}%{cpu_ctx}")

            if ram > 90:
                issues.append(f"  ⚠ RAM critical:  {ram:.0f}%{ram_ctx}")
            elif ram > 80:
                issues.append(f"  ! RAM high:      {ram:.0f}%{ram_ctx}")
            else:
                good.append(f"  ✓ RAM OK:        {ram:.0f}%{ram_ctx}")

            if snap.get("cpu_throttled"):
                ratio = snap.get("cpu_throttle_ratio", 0)
                issues.append(f"  ⚠ CPU throttled: running at {ratio*100:.0f}% power")
            else:
                good.append("  ✓ CPU not throttling")

            intro = random.choice(self._HEALTH_INTROS_EN).replace("{P}", self.PREFIX)
            lines = [intro]
            if issues:
                lines.append("Issues found:")
                lines.extend(issues)
            lines.extend(good)
            if not issues:
                lines.append(random.choice([
                    "Everything looks healthy ✓",
                    "Your PC is in good shape ✓",
                    "All good — nothing to worry about ✓",
                    "All looks good ✓",
                ]))

            # ── Pomysł 2: session reference ───────────────────────────────────
            ram_sess = session_memory.get_response_data("hw_ram")
            if ram_sess.get("total_gb") and ram > 70:
                lines.append(
                    f"  (Your {ram_sess['total_gb']} GB RAM was discussed earlier"
                    f" — now at {ram:.0f}%, that's worth watching)"
                )

        else:
            if cpu > 90:
                issues.append(f"  ⚠ CPU krytyczne:  {cpu:.0f}%{cpu_ctx}")
            elif cpu > 75:
                issues.append(f"  ! CPU wysokie:    {cpu:.0f}%{cpu_ctx}")
            else:
                good.append(f"  ✓ CPU OK:          {cpu:.0f}%{cpu_ctx}")

            if ram > 90:
                issues.append(f"  ⚠ RAM krytyczne:  {ram:.0f}%{ram_ctx}")
            elif ram > 80:
                issues.append(f"  ! RAM wysokie:    {ram:.0f}%{ram_ctx}")
            else:
                good.append(f"  ✓ RAM OK:          {ram:.0f}%{ram_ctx}")

            if snap.get("cpu_throttled"):
                ratio = snap.get("cpu_throttle_ratio", 0)
                issues.append(f"  ⚠ CPU throttled:  działa na {ratio*100:.0f}% mocy")
            else:
                good.append("  ✓ CPU nie throttluje")

            intro = random.choice(self._HEALTH_INTROS_PL).replace("{P}", self.PREFIX)
            lines = [intro]
            if issues:
                lines.append("Problemy:")
                lines.extend(issues)
            lines.extend(good)
            if not issues:
                lines.append("Wszystko wygląda dobrze ✓")

            ram_sess = session_memory.get_response_data("hw_ram")
            if ram_sess.get("total_gb") and ram > 70:
                lines.append(
                    f"  (RAM {ram_sess['total_gb']} GB omawiany wcześniej"
                    f" — teraz {ram:.0f}%, warto obserwować)"
                )

        lines.append(_followup("health", lang))
        return lines

    # ── Temperature ───────────────────────────────────────────────────────────

    def _resp_temperature(self, r: ParseResult, lang: str = "pl") -> List[str]:
        # ── 1. Try live hardware sensors (works on Linux / some Windows setups)
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                header = _t(lang, f"{self.PREFIX} Temperatury (live):", f"{self.PREFIX} Temperatures (live):")
                lines = [header]
                for name, entries in temps.items():
                    for e in entries[:3]:
                        label = e.label or name
                        if e.current > 85:
                            status = _t(lang, "⚠ GORĄCO", "⚠ HOT")
                        elif e.current > 70:
                            status = _t(lang, "! ciepło", "! warm")
                        else:
                            status = "OK"
                        lines.append(f"  {label:<20} {e.current:.0f}°C  {status}")
                return lines
        except Exception:
            pass

        # ── 2. Fall back to DB — scheduler records cpu_temp every minute
        try:
            from hck_stats_engine.query_api import query_api
            th = query_api.get_temperature_history(minutes=60)
            if th:
                cpu_cur  = th.get("cpu_current")
                gpu_cur  = th.get("gpu_current")
                cpu_avg  = th.get("cpu_avg")
                gpu_avg  = th.get("gpu_avg")
                cpu_max  = th.get("cpu_max")
                gpu_max  = th.get("gpu_max")
                samples  = th.get("samples", 0)
                est      = th.get("estimated", False)

                def _status(t):
                    if t is None:
                        return "—"
                    if t > 85:
                        return _t(lang, "⚠ GORĄCO", "⚠ HOT")
                    if t > 70:
                        return _t(lang, "! ciepło", "! warm")
                    return "OK"

                note = _t(lang,
                    "  (szacowane — brak czujnika HW; scheduler oblicza z obciążenia)",
                    "  (estimated — no HW sensor; scheduler derives from load)") if est else ""

                header = _t(lang,
                    f"{self.PREFIX} Temperatury (ostatnia godzina, {samples} próbek):",
                    f"{self.PREFIX} Temperatures (last hour, {samples} samples):")
                lines = [header]
                if note:
                    lines.append(note)
                lines.append("")

                if cpu_cur is not None:
                    lines.append(
                        f"  {'CPU teraz' if lang == 'pl' else 'CPU now':<20} "
                        f"{cpu_cur:.0f}°C  {_status(cpu_cur)}")
                if cpu_avg is not None:
                    lines.append(
                        f"  {'CPU śr. 1h' if lang == 'pl' else 'CPU avg 1h':<20} "
                        f"{cpu_avg:.0f}°C")
                if cpu_max is not None:
                    lines.append(
                        f"  {'CPU max 1h' if lang == 'pl' else 'CPU peak 1h':<20} "
                        f"{cpu_max:.0f}°C  {_status(cpu_max)}")

                if gpu_cur is not None:
                    lines.append(
                        f"  {'GPU teraz' if lang == 'pl' else 'GPU now':<20} "
                        f"{gpu_cur:.0f}°C  {_status(gpu_cur)}")
                if gpu_avg is not None:
                    lines.append(
                        f"  {'GPU śr. 1h' if lang == 'pl' else 'GPU avg 1h':<20} "
                        f"{gpu_avg:.0f}°C")
                if gpu_max is not None:
                    lines.append(
                        f"  {'GPU max 1h' if lang == 'pl' else 'GPU peak 1h':<20} "
                        f"{gpu_max:.0f}°C  {_status(gpu_max)}")

                # Long-term averages from daily stats
                try:
                    ts = query_api.get_temperature_summary(days=7)
                    if ts and ts.get("cpu_temp_avg"):
                        lines.append("")
                        lines.append(_t(lang,
                            f"  CPU śr. 7 dni:  {ts['cpu_temp_avg']:.0f}°C  "
                            f"  max: {ts.get('cpu_temp_max', '—')}°C",
                            f"  CPU avg 7 days: {ts['cpu_temp_avg']:.0f}°C  "
                            f"  peak: {ts.get('cpu_temp_max', '—')}°C"))
                        if ts.get("gpu_temp_avg"):
                            lines.append(_t(lang,
                                f"  GPU śr. 7 dni:  {ts['gpu_temp_avg']:.0f}°C  "
                                f"  max: {ts.get('gpu_temp_max', '—')}°C",
                                f"  GPU avg 7 days: {ts['gpu_temp_avg']:.0f}°C  "
                                f"  peak: {ts.get('gpu_temp_max', '—')}°C"))
                except Exception:
                    pass

                return lines
        except Exception:
            pass

        # ── 3. No data at all
        if lang == "en":
            return [
                f"{self.PREFIX} No temperature data yet.",
                "  The scheduler collects CPU temp every minute — check back in a moment.",
                "  For GPU temps, hardware sensor support is needed.",
            ]
        return [
            f"{self.PREFIX} Brak danych o temperaturach.",
            "  Scheduler zapisuje temp. CPU co minutę — sprawdź za chwilę.",
            "  Temperatury GPU wymagają czujnika sprzętowego.",
        ]

    # ── Throttle check ────────────────────────────────────────────────────────

    def _resp_throttle_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        snap = system_context.snapshot()
        mhz      = snap.get("cpu_mhz",     None)
        max_mhz  = snap.get("cpu_max_mhz", None)
        throttled = snap.get("cpu_throttled", False)

        if mhz is None:
            return [_t(lang,
                       f"{self.PREFIX} Brak danych o taktowaniu CPU.",
                       f"{self.PREFIX} No CPU frequency data available.")]

        ratio_str = ""
        if max_mhz:
            ratio = mhz / max_mhz
            ratio_str = _t(lang, f"  ({ratio*100:.0f}% mocy)", f"  ({ratio*100:.0f}% of max)")

        if throttled:
            if lang == "en":
                return [
                    f"{self.PREFIX} ⚠ CPU IS THROTTLING!",
                    f"  Now:    {mhz} MHz{ratio_str}",
                    f"  Max:    {max_mhz} MHz",
                    "  Likely cause: heat, power limit, or power plan.",
                    "  Check temperatures and active power plan.",
                ]
            return [
                f"{self.PREFIX} ⚠ CPU THROTTLUJE!",
                f"  Teraz:  {mhz} MHz{ratio_str}",
                f"  Max:    {max_mhz} MHz",
                "  Możliwe przyczyny: przegrzanie, power limit, plan zasilania.",
                "  Sprawdź temperatury i plan zasilania.",
            ]

        ok_msg = _t(lang,
                    f"{self.PREFIX} CPU nie throttluje.",
                    f"{self.PREFIX} CPU is not throttling.")
        return [ok_msg,
                f"  {_t(lang, 'Teraz', 'Now')}: {mhz} MHz  /  Max: {max_mhz} MHz  {ratio_str}",
                _followup("perf", lang)]

    # ── Performance ───────────────────────────────────────────────────────────

    _PERF_INTROS_PL = [
        "{P} Wydajność teraz:",
        "{P} Aktualne obciążenie systemu:",
        "{P} Sprawdzam co się dzieje:",
        "{P} Oto co robi twój PC w tej chwili:",
    ]
    _PERF_INTROS_EN = [
        "{P} Current performance:",
        "{P} System load right now:",
        "{P} Here's what's happening:",
        "{P} Live snapshot of your system:",
        "{P} Here's what your PC is up to:",
    ]

    def _resp_performance(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()

        cpu = snap.get("cpu_pct",  "—")
        ram = snap.get("ram_pct",  "—")
        mhz = snap.get("cpu_mhz",  "—")

        # ── Pomysł 1: delta labels ────────────────────────────────────────────
        try:
            cpu_f = float(str(cpu).replace("%", "") or 0)
            ram_f = float(str(ram).replace("%", "") or 0)
        except (ValueError, TypeError):
            cpu_f = ram_f = 0.0

        cpu_delta = _delta_label(cpu_f, patterns.get("typical_cpu_avg"), lang)
        ram_delta = _delta_label(ram_f, patterns.get("typical_ram_avg"), lang)
        cpu_sfx   = f"    {cpu_delta}" if cpu_delta else ""
        ram_sfx   = f"    {ram_delta}" if ram_delta else ""

        thr = ""
        if snap.get("cpu_throttled"):
            ratio = snap.get("cpu_throttle_ratio", 0) * 100
            thr = _t(lang,
                     f"  ⚠ CPU throttled ({ratio:.0f}% mocy)",
                     f"  ⚠ CPU throttled ({ratio:.0f}% of max power)")

        pool  = self._PERF_INTROS_EN if lang == "en" else self._PERF_INTROS_PL
        intro = random.choice(pool).replace("{P}", self.PREFIX)
        lines = [intro,
                 f"  CPU:  {cpu}%  @  {mhz} MHz{cpu_sfx}",
                 f"  RAM:  {ram}%{ram_sfx}"]
        if snap.get("gpu_avg_today"):
            gpu_lbl = _t(lang, "GPU avg dzisiaj", "GPU avg today")
            lines.append(f"  {gpu_lbl}:  {snap['gpu_avg_today']}%")
        if thr:
            lines.append(thr)
        lines.append(_followup("perf", lang))
        return lines

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _resp_stats(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        snap    = system_context.snapshot()
        cpu_avg = snap.get("cpu_avg_today", _t(lang, "brak danych", "no data"))
        cpu_max = snap.get("cpu_max_today", "—")
        ram_avg = snap.get("ram_avg_today", _t(lang, "brak danych", "no data"))
        gpu_avg = snap.get("gpu_avg_today", None)

        header = _t(lang, f"{self.PREFIX} Dzisiejsze statystyki:", f"{self.PREFIX} Today's stats:")
        lines = [
            header,
            f"  CPU avg:  {cpu_avg}%   peak: {cpu_max}%",
            f"  RAM avg:  {ram_avg}%",
        ]
        if gpu_avg:
            lines.append(f"  GPU avg:  {gpu_avg}%")

        # Week-over-week trend
        try:
            from hck_stats_engine.query_api import query_api
            this_week = query_api.get_summary_stats(days=7)
            last_week = query_api.get_summary_stats(days=14)
            if this_week and last_week:
                tw_cpu = this_week.get("cpu_avg") or 0
                lw_cpu = last_week.get("cpu_avg") or 0
                if lw_cpu > 0:
                    diff = tw_cpu - lw_cpu
                    sign = "+" if diff >= 0 else ""
                    arrow = "↑" if diff > 3 else ("↓" if diff < -3 else "→")
                    lines.append(_t(lang,
                                    f"  CPU vs poprzedni tydzień: {arrow} {sign}{diff:.0f}% (śr. {lw_cpu:.0f}% → {tw_cpu:.0f}%)",
                                    f"  CPU vs last week: {arrow} {sign}{diff:.0f}% (avg {lw_cpu:.0f}% → {tw_cpu:.0f}%)"))
        except Exception:
            pass

        hint = _t(lang,
                  "  (Pełny raport: zakładka AllMonitor lub 'today report')",
                  "  (Full report: AllMonitor tab or type 'today report')")
        lines.append(hint)
        return lines

    # ── Uptime ────────────────────────────────────────────────────────────────

    def _resp_uptime(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        dur = session_memory.session_duration_str()
        msg = _t(lang,
                 f"{self.PREFIX} Sesja PC Workman trwa: {dur}",
                 f"{self.PREFIX} PC Workman session running for: {dur}")
        return [msg, _followup("perf", lang)]

    # ── Processes ─────────────────────────────────────────────────────────────

    def _resp_processes(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
            # Cap iteration at 128 processes to avoid hangs on loaded systems
            raw = []
            for p in psutil.process_iter(["name", "cpu_percent"]):
                try:
                    raw.append(p)
                    if len(raw) >= 128:
                        break
                except Exception:
                    continue
            procs = sorted(
                raw,
                key=lambda p: p.info.get("cpu_percent", 0) or 0,
                reverse=True
            )[:5]
            header = _t(lang,
                        f"{self.PREFIX} Top procesy CPU teraz:",
                        f"{self.PREFIX} Top CPU processes now:")
            lines = [header]
            for i, p in enumerate(procs, 1):
                name = (p.info.get("name") or "?")[:28]
                pct  = p.info.get("cpu_percent", 0) or 0
                lines.append(f"  {i}. {name:<28}  {pct:.1f}%")
            return lines
        except Exception:
            return [_t(lang,
                       f"{self.PREFIX} Brak danych o procesach. Sprawdź: zakładka Efficiency",
                       f"{self.PREFIX} No process data. Check: Efficiency tab")]

    # ── Optimization ──────────────────────────────────────────────────────────

    def _resp_optimization(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        snap    = system_context.snapshot()
        hw      = user_knowledge.get_all_hardware()
        profile = _hw_profile(hw)

        cpu = float(snap.get("cpu_pct", 0) or 0)
        ram = float(snap.get("ram_pct", 0) or 0)

        # ── Contextual priority tip based on live state ───────────────────────
        if ram > 85 or cpu > 85:
            dominant = "RAM" if ram >= cpu else "CPU"
            val      = ram if ram >= cpu else cpu
            priority = _t(lang,
                f"  🔴 Teraz: {dominant} na {val:.0f}% — zacznij od TURBO BOOST",
                f"  🔴 Right now: {dominant} at {val:.0f}% — start with TURBO BOOST")
        elif ram > 70 or cpu > 70:
            priority = _t(lang,
                f"  🟡 Umiarkowane obciążenie (CPU {cpu:.0f}% / RAM {ram:.0f}%) — warto posprzątać",
                f"  🟡 Moderate load (CPU {cpu:.0f}% / RAM {ram:.0f}%) — a good time to clean up")
        else:
            priority = _t(lang,
                f"  ✓ System wygląda OK (CPU {cpu:.0f}% / RAM {ram:.0f}%) — prewencja zamiast gaszenia pożarów",
                f"  ✓ System looks fine (CPU {cpu:.0f}% / RAM {ram:.0f}%) — prevention rather than firefighting")

        header = _t(lang, f"{self.PREFIX} Optymalizacja systemu:", f"{self.PREFIX} System optimization:")
        lines  = [header, priority, ""]

        # ── Quick action menu ─────────────────────────────────────────────────
        lines.append(_t(lang, "  Szybkie akcje:", "  Quick actions:"))
        lines.append(_t(lang,
            "  ⚡ TURBO BOOST — High Perf + flush RAM + wyczyść TEMP  [→ Optimization]",
            "  ⚡ TURBO BOOST — High Perf + RAM flush + clear TEMP  [→ Optimization]"))
        lines.append(_t(lang,
            "  🚀 Autostart — ogranicz co odpala się z Windows  [→ Startup Manager]",
            "  🚀 Startup — limit what launches with Windows  [→ Startup Manager]"))

        # HW-aware additions
        if profile["ram_low"]:
            lines.append(_t(lang,
                f"  🧠 Pamięć wirtualna — masz {profile['ram_gb']:.0f} GB RAM, pagefile da oddech  [→ Virtual Memory]",
                f"  🧠 Virtual Memory — you have {profile['ram_gb']:.0f} GB RAM, pagefile will help  [→ Virtual Memory]"))
        if profile["is_hdd"]:
            lines.append(_t(lang,
                "  💽 HDD wykryty — wyłącz indeksowanie Windows Search dla szybszego dysku",
                "  💽 HDD detected — disable Windows Search indexing for a faster drive"))

        lines.append("")
        lines.append(_t(lang,
            "  💬 Wpisz 'przyspiesz komputer' po spersonalizowany plan optymalizacji",
            "  💬 Type 'speed up pc' for a personalised optimisation plan"))
        return lines

    # ── Power plan ────────────────────────────────────────────────────────────

    def _resp_power_plan(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import subprocess
            result = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True, text=True, timeout=3
            )
            line = result.stdout.strip()
            if "(" in line:
                name = line[line.rfind("(") + 1:line.rfind(")")]
                label = _t(lang, "Aktywny plan zasilania", "Active power plan")
                return [f"{self.PREFIX} {label}:  {name}"]
        except Exception:
            pass
        return [_t(lang,
                   f"{self.PREFIX} Nie mogę odczytać planu zasilania.",
                   f"{self.PREFIX} Can't read power plan.")]

    # ── Conversational ────────────────────────────────────────────────────────

    _GREET_PL = [
        "{P} Hej! Spytaj o swój sprzęt, temperatury lub wydajność.",
        "{P} Cześć! Jestem tu — o co chcesz zapytać?",
        "{P} Siema! Pisz śmiało — CPU, GPU, RAM, zdrowie, statystyki.",
        "{P} Hej, tu hck_GPT. W czym mogę pomóc?",
        "{P} Gotowy. Co sprawdzamy?",
    ]
    _GREET_EN = [
        "{P} Hey! Ask about your hardware, temps or performance.",
        "{P} Hi there — what would you like to know?",
        "{P} Hey! Fire away — CPU, GPU, RAM, health, stats.",
        "{P} hck_GPT here. What are we looking at?",
        "{P} Ready. What do you need?",
    ]
    # Sarcastic/alert greetings when system is NOT doing well
    _GREET_ALERT_PL = [
        "{P} Hej — RAM już na {ram}%, zanim zaczniesz, może warto to ogarnąć?",
        "{P} Cześć. CPU na {cpu}%. Nie będę udawać że wszystko OK — co chcesz sprawdzić?",
        "{P} Tu hck_GPT. System nie jest w najlepszej formie ({cpu}% CPU / {ram}% RAM). Pytaj.",
    ]
    _GREET_ALERT_EN = [
        "{P} Hey — RAM at {ram}% before we even start. Worth addressing?",
        "{P} Hi. CPU at {cpu}%. Not going to pretend everything is fine — what do you need?",
        "{P} hck_GPT here. System's not great ({cpu}% CPU / {ram}% RAM). Ask away.",
    ]

    def _resp_greeting(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        from hck_gpt.memory.user_knowledge import user_knowledge
        from hck_gpt.context.system_context import system_context
        hw   = user_knowledge.get_hardware("cpu_model")
        snap = system_context.snapshot()
        cpu  = snap.get("cpu_pct", 0) or 0
        ram  = snap.get("ram_pct", 0) or 0

        # Use alert greeting if system is stressed
        if cpu > 80 or ram > 85:
            pool = self._GREET_ALERT_EN if lang == "en" else self._GREET_ALERT_PL
            response = self._pick_fresh("greet_alert", lang, self._GREET_ALERT_PL, self._GREET_ALERT_EN)
            response = response.replace("{P}", self.PREFIX).replace("{cpu}", f"{cpu:.0f}").replace("{ram}", f"{ram:.0f}")
        else:
            response = self._pick_fresh("greet", lang, self._GREET_PL, self._GREET_EN)
            response = response.replace("{P}", self.PREFIX)

        if not session_memory.greeted_this_session:
            session_memory.greeted_this_session = True
            if hw:
                cpu_note = _t(lang, f"  (Widzę: {hw})", f"  (I see: {hw})")
                response += "\n" + cpu_note
        return [response]

    _THANKS_PL = [
        "{P} Nie ma za co. Pisz jak coś.",
        "{P} Spoko. Zawsze tu jestem.",
        "{P} Czystka zaliczona. Co dalej?",
        "{P} Cała przyjemność po mojej stronie. Następne pytanie?",
        "{P} Gotowe. Jeśli coś się zmieni — daj znać.",
    ]
    _THANKS_EN = [
        "{P} No problem. Hit me up anytime.",
        "{P} Done. What's next?",
        "{P} You're welcome. I'm always running.",
        "{P} Anytime — that's the job.",
        "{P} Good. Let me know if anything changes.",
    ]

    def _resp_thanks(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [self._pick_fresh("thanks", lang, self._THANKS_PL, self._THANKS_EN).replace("{P}", self.PREFIX)]

    def _resp_help(self, r: ParseResult, lang: str = "pl") -> List[str]:
        if lang == "en":
            return [
                f"{self.PREFIX} What I can help with:",
                "",
                "  🖥  Hardware",
                "      'what cpu do i have'  /  'specs'  /  'how much ram'",
                "      'what gpu'  /  'what disk do i have'  /  'motherboard'",
                "",
                "  🩺  Diagnostics & Health",
                "      'health check'  /  'temperatures'  /  'is cpu throttling'",
                "      'is my gpu overheating'  /  'disk health'",
                "      'what risks does my pc have'  ← risk ranking",
                "",
                "  📊  Performance & Stats",
                "      'performance'  /  'stats'  /  'top processes'  /  'uptime'",
                "      'what changed in performance'  /  'compare sessions'",
                "      'what changed on my pc since yesterday'  ← broad changes view",
                "",
                "  🔍  Why is it doing that?",
                "      'why is it slow'  /  'why is ram so high'  /  'why is disk at 100'",
                "      'which process is draining my battery right now'  /  'unnecessary programs'",
                "",
                "  ⚡  Optimization",
                "      'speed up pc'  /  'turbo boost'  /  'startup programs'",
                "      'optimization'  /  'power plan'  /  'disk speed'",
                "      'is it safe to disable X from startup'  ← startup safety check",
                "",
                "  🔒  Security",
                "      'virus check'  /  'suspicious processes'  /  'what is svchost'",
                "",
                "  😄  Fun / Personality",
                "      'why does my computer hate me'  /  'which process is the laziest'",
                "      'why does discord run in the background like a stalker'",
                "",
                "  💬  Small talk  /  'about this program'  /  'who made this'",
            ]
        return [
            f"{self.PREFIX} W czym mogę pomóc:",
            "",
            "  🖥  Sprzęt",
            "      'jaki mam procesor'  /  'specyfikacja'  /  'ile ram'",
            "      'jaki gpu'  /  'jaki mam dysk'  /  'płyta główna'",
            "",
            "  🩺  Diagnostyka i zdrowie",
            "      'zdrowie systemu'  /  'jakie temperatury'  /  'czy CPU throttluje'",
            "      'czy GPU się przegrzewa'  /  'zdrowie dysku'",
            "      'co zagraża mojemu PC'  ← ranking ryzyk",
            "",
            "  📊  Wydajność i statystyki",
            "      'wydajność'  /  'stats'  /  'top procesy'  /  'czas sesji'",
            "      'co się zmieniło w wydajności'  /  'porównaj sesje'",
            "      'co się zmieniło od wczoraj'  ← szeroki widok zmian",
            "",
            "  🔍  Dlaczego tak działa?",
            "      'dlaczego laguje'  /  'dlaczego ram wysoki'  /  'dysk na 100 dlaczego'",
            "      'który proces rozładowuje baterię teraz'  /  'niepotrzebne programy'",
            "",
            "  ⚡  Optymalizacja",
            "      'przyspiesz komputer'  /  'turbo boost'  /  'autostart'",
            "      'optymalizacja'  /  'plan zasilania'  /  'jak przyspieszyć dysk'",
            "      'czy mogę wyłączyć X ze startu'  ← sprawdzenie bezpieczeństwa autostartu",
            "",
            "  🔒  Bezpieczeństwo",
            "      'sprawdź wirusy'  /  'podejrzane procesy'  /  'co to svchost'",
            "",
            "  😄  Zabawa / Osobowość",
            "      'dlaczego mój komputer mnie nienawidzi'  /  'który proces jest leniem'",
            "      'dlaczego discord działa w tle jak stalker'",
            "",
            "  💬  Pogadaj  /  'o programie'  /  'kto stworzył'",
        ]

    # ── Small talk (route to Ollama via hybrid engine; rule fallback here) ────

    _SMALLTALK_PL = [
        "{P} Dobrze, dzięki. Twój komputer ma {cpu}% CPU i {ram}% RAM — nieźle jak na pogawędkę.",
        "{P} W porządku. Bardziej martwię się o Twój RAM ({ram}%) niż o small talk.",
        "{P} Pytaj o PC — w tym jestem dobry. Na filozofię masz Google.",
        "{P} Funkcjonuję. CPU {cpu}%, RAM {ram}%. Ty jak?",
        "{P} Monitoruję wszystko po cichu. Jak chcesz wiedzieć co się dzieje — pytaj.",
    ]
    _SMALLTALK_EN = [
        "{P} Fine, thanks. Your PC is at {cpu}% CPU and {ram}% RAM — not bad for small talk.",
        "{P} Doing ok. More concerned about your RAM ({ram}%) than chatting, honestly.",
        "{P} Ask me about your PC — that's my lane. For philosophy, try Google.",
        "{P} Running. CPU {cpu}%, RAM {ram}%. You?",
        "{P} Monitoring everything quietly. Ask if you want to know what's going on.",
    ]

    def _resp_small_talk(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_gpt.context.system_context import system_context
            snap = system_context.snapshot()
            cpu = f"{snap.get('cpu_pct', 0) or 0:.0f}"
            ram = f"{snap.get('ram_pct', 0) or 0:.0f}"
        except Exception:
            cpu, ram = "?", "?"
        resp = self._pick_fresh("smalltalk", lang, self._SMALLTALK_PL, self._SMALLTALK_EN)
        return [resp.replace("{P}", self.PREFIX).replace("{cpu}", cpu).replace("{ram}", ram)]

    # ── About the program ─────────────────────────────────────────────────────

    def _resp_about_program(self, r: ParseResult, lang: str = "pl") -> List[str]:
        if lang == "en":
            return [
                f"{self.PREFIX} About PC Workman HCK v1.7.3:",
                "  A real-time PC monitoring and optimization tool.",
                "  • Live CPU / RAM / GPU tracking with history graphs",
                "  • hck_GPT — AI assistant answering hardware questions",
                "  • Stats engine — daily/weekly usage database (SQLite)",
                "  • Optimization Center — one-click TURBO BOOST, RAM flush",
                "  • Fan control editor, stability tests, hardware sensors",
                "  • Process library — identifies 100+ running programs",
                "  💬 Try: 'specs'  'health'  'temperatures'  'stats'",
            ]
        return [
            f"{self.PREFIX} O programie PC Workman HCK v1.7.3:",
            "  Narzędzie do monitorowania i optymalizacji PC w czasie rzeczywistym.",
            "  • Śledzenie CPU / RAM / GPU na żywo z wykresami historii",
            "  • hck_GPT — asystent AI odpowiadający na pytania o sprzęt",
            "  • Silnik statystyk — baza danych użytkowania (SQLite)",
            "  • Centrum optymalizacji — TURBO BOOST jednym kliknięciem, flush RAM",
            "  • Edytor krzywej wentylatora, testy stabilności, czujniki sprzętu",
            "  • Biblioteka procesów — identyfikuje 100+ działających programów",
            "  💬 Spróbuj: 'specyfikacja'  'zdrowie'  'temperatury'  'stats'",
        ]

    # ── About the author ──────────────────────────────────────────────────────

    def _resp_about_author(self, r: ParseResult, lang: str = "pl") -> List[str]:
        if lang == "en":
            return [
                f"{self.PREFIX} PC Workman HCK was built by HCK Labs.",
                "  An independent one-person development project.",
                "  Focused on giving Windows users real insight into",
                "  what their PC is actually doing — no bloat, no cloud.",
            ]
        return [
            f"{self.PREFIX} PC Workman HCK został stworzony przez HCK Labs.",
            "  Niezależny, jednoosobowy projekt deweloperski.",
            "  Celem było danie użytkownikom Windows prawdziwego wglądu",
            "  w to, co dzieje się z ich komputerem — bez zbędnych rzeczy.",
        ]

    # ── Virus / security check ────────────────────────────────────────────────

    def _resp_virus_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        import time as _time
        try:
            import psutil
            from hck_gpt.process_library import process_library as _lib
        except Exception:
            return [_t(lang,
                       f"{self.PREFIX} Nie mogę sprawdzić procesów.",
                       f"{self.PREFIX} Cannot check processes right now.")]

        _SUSPICIOUS_PATTERNS = {
            "xmrig", "cpuminer", "nicehash", "minerd", "claymore",
            "cgminer", "bfgminer", "ethminer", "gminer", "phoenixminer",
        }

        checked = 0
        unknown = []
        suspicious = []

        try:
            for proc in psutil.process_iter(["name", "pid"]):
                try:
                    name = (proc.info.get("name") or "").lower().strip()
                    if not name or name in ("system idle process", "idle"):
                        continue
                    checked += 1
                    if checked > 120:
                        break

                    # Known suspicious patterns (miners etc.)
                    base = name.replace(".exe", "")
                    if any(pat in base for pat in _SUSPICIOUS_PATTERNS):
                        suspicious.append(name)
                        continue

                    info = _lib.get_process_info(name)
                    if info:
                        if info.get("safety") in ("suspicious", "unsafe"):
                            suspicious.append(f"{name}  [{info.get('name', '')}]")
                    else:
                        # Not in library — unknown but not necessarily bad
                        if len(unknown) < 8 and not name.startswith(("svchost", "conhost")):
                            unknown.append(name)
                except Exception:
                    continue
        except Exception:
            pass

        if suspicious:
            lines = [_t(lang,
                        f"{self.PREFIX} ⚠ UWAGA — znaleziono podejrzane procesy!",
                        f"{self.PREFIX} ⚠ WARNING — suspicious processes detected!")]
            for s in suspicious[:5]:
                lines.append(f"  ⚠ {s}")
            lines.append(_t(lang,
                            "  Sprawdź te procesy w Menedżerze zadań.",
                            "  Check these in Task Manager immediately."))
            lines.append(_followup("security", lang))
            return lines

        header = _t(lang,
                    f"{self.PREFIX} Skanowanie bezpieczeństwa ({checked} procesów):",
                    f"{self.PREFIX} Security scan ({checked} processes):")
        lines = [header,
                 _t(lang, "  ✓ Brak podejrzanych procesów.", "  ✓ No suspicious processes found.")]

        if unknown:
            unk_label = _t(lang, f"  Nieznanych programom:", f"  Unrecognised programs:")
            lines.append(unk_label)
            for u in unknown[:5]:
                lines.append(f"    — {u}")
            lines.append(_t(lang,
                            "  (Nieznane ≠ niebezpieczne — to np. własne aplikacje.)",
                            "  (Unknown ≠ dangerous — could be your own tools.)"))
        lines.append(_followup("security", lang))
        return lines

    # ── Unnecessary / background programs ────────────────────────────────────

    _BACKGROUND_BLOAT = {
        "epicgameslauncher.exe", "battlenet.exe", "ubisoft connect.exe",
        "gog galaxy.exe", "ea app.exe", "rockstarlauncher.exe",
        "nvidiaSharecontainer.exe", "adobeupdateservice.exe",
        "adobearm.exe", "acrobat.exe", "creativeclouduis.exe",
        "ccleaner64.exe", "ccleanermonitor.exe",
        "microsoftedgeupdate.exe", "googleupdater.exe",
        "onedrive.exe", "dropbox.exe", "skype.exe",
        "cortana.exe", "microsoftedgewebview2.exe",
    }

    def _resp_unnecessary_programs(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
        except Exception:
            return [_t(lang,
                       f"{self.PREFIX} Brak dostępu do procesów.",
                       f"{self.PREFIX} Cannot read process list.")]

        running_names: list[str] = []
        try:
            for proc in psutil.process_iter(["name", "memory_info"]):
                try:
                    n = (proc.info.get("name") or "").lower()
                    if n:
                        running_names.append(n)
                except Exception:
                    continue
        except Exception:
            pass

        found_bloat: list[str] = []
        for name in running_names:
            if name in self._BACKGROUND_BLOAT:
                found_bloat.append(name)

        header = _t(lang,
                    f"{self.PREFIX} Programy działające w tle:",
                    f"{self.PREFIX} Background program check:")

        if not found_bloat:
            return [
                header,
                _t(lang,
                   "  ✓ Żadnych znanych zbędnych procesów w tle.",
                   "  ✓ No known unnecessary background apps detected."),
                _t(lang,
                   "  Możesz sprawdzić dalej: zakładka Efficiency → lista procesów.",
                   "  You can dig deeper: Efficiency tab → full process list."),
            ]

        lines = [
            header,
            _t(lang,
               f"  Znaleziono {len(found_bloat)} zbędnych procesów:",
               f"  Found {len(found_bloat)} potentially unnecessary programs:"),
        ]
        for b in found_bloat[:8]:
            lines.append(f"  — {b}")
        lines.append(_t(lang,
                        "  Możesz je wyłączyć ze startu: Start → Menedżer zadań → Autostart.",
                        "  Disable from startup: Start → Task Manager → Startup apps."))
        return lines

    # ── Disk speed / optimization ─────────────────────────────────────────────

    def _resp_disk_speed(self, r: ParseResult, lang: str = "pl") -> List[str]:
        import os, tempfile
        lines = [_t(lang, f"{self.PREFIX} Stan dysków:", f"{self.PREFIX} Disk status:")]

        # Live disk usage
        try:
            import psutil
            for p in psutil.disk_partitions(all=False):
                if "remote" in (p.opts or "").lower():
                    continue
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    free_gb  = round(u.free  / 1_073_741_824, 1)
                    total_gb = round(u.total / 1_073_741_824, 1)
                    used_pct = u.percent
                    status = "⚠ " if used_pct > 85 else ("! " if used_pct > 70 else "  ")
                    lines.append(f"  {status}{p.device}  {used_pct:.0f}% used"
                                 f"  ({free_gb} GB free / {total_gb} GB)")
                except Exception:
                    pass
        except Exception:
            pass

        # TEMP folder
        try:
            td = tempfile.gettempdir()
            temp_mb = sum(
                e.stat().st_size for e in os.scandir(td) if e.is_file(follow_symlinks=False)
            ) // 1_048_576
            if temp_mb > 100:
                lines.append(_t(lang,
                    f"  🗑 Folder TEMP: {temp_mb} MB  →  wyczyść w zakładce Optimization",
                    f"  🗑 TEMP folder: {temp_mb} MB  →  clear in Optimization tab"))
        except Exception:
            pass

        # AppData check
        try:
            appdata = os.environ.get('APPDATA', '')
            if appdata and os.path.exists(appdata):
                app_dirs = [d.name for d in os.scandir(appdata) if d.is_dir()]
                count = len(app_dirs)
                if count > 50:
                    lines.append(_t(lang,
                        f"  📁 AppData: {count} folderów — mogą być resztki starych aplikacji.",
                        f"  📁 AppData: {count} folders — may contain leftovers from old apps."))
                    lines.append(_t(lang,
                        "     Wpisz '%appdata%' w Wyszukaj → przejrzyj i usuń foldery",
                        "     Type '%appdata%' in Windows Search → review and delete old folders"))
        except Exception:
            pass

        lines.append(_t(lang,
            "  💡 Wskazówka: Optymalizacja → Wyczyść TEMP → Uruchom TURBO BOOST",
            "  💡 Tip: Optimization → Clear TEMP → Run TURBO BOOST"))
        return lines

    # ── Speed up PC / FPS ─────────────────────────────────────────────────────

    def _resp_speed_up_pc(self, r: ParseResult, lang: str = "pl") -> List[str]:
        import os, tempfile, subprocess
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        snap    = system_context.snapshot()
        hw      = user_knowledge.get_all_hardware()
        profile = _hw_profile(hw)        # ── Pomysł 5: hardware profile ──

        cpu = float(snap.get("cpu_pct", 0) or 0)
        ram = float(snap.get("ram_pct", 0) or 0)

        header = _t(lang,
                    f"{self.PREFIX} Plan przyspieszenia komputera:",
                    f"{self.PREFIX} PC speed-up plan:")
        recs: list[str] = []

        # ── Pomysł 5: HW-specific issues first ───────────────────────────────
        # Low RAM — flag before anything else, it's the biggest bottleneck
        if profile["ram_low"]:
            recs.append(_t(lang,
                f"  🧠 RAM: {profile['ram_gb']:.0f} GB — mało dla obecnych standardów. Priorytet #1:",
                f"  🧠 RAM: {profile['ram_gb']:.0f} GB — tight for modern workloads. Priority #1:"))
            recs.append(_t(lang,
                "     Zamknij browser gdy nieużywany (~3–4 GB odzysk)",
                "     Close browser when idle (~3–4 GB recovered)"))
            recs.append(_t(lang,
                "     lub dodaj Pamięć Wirtualną  [→ Virtual Memory]",
                "     or add Virtual Memory  [→ Virtual Memory]"))

        # HDD — drastically different optimization path
        if profile["is_hdd"]:
            recs.append(_t(lang,
                f"  💽 Dysk: HDD wykryty — największy hamulec w systemie.",
                f"  💽 Disk: HDD detected — the biggest bottleneck in your system."))
            recs.append(_t(lang,
                "     Wyłącz Windows Search indexing (Usługi → WSearch → Disabled)",
                "     Disable Windows Search indexing (Services → WSearch → Disabled)"))
            recs.append(_t(lang,
                "     Uruchom defragmentację: Start → Defragmentuj dyski",
                "     Run defrag: Start → Defragment and Optimize Drives"))

        # Power plan
        try:
            rp = subprocess.run(["powercfg", "/getactivescheme"],
                                capture_output=True, text=True, timeout=3)
            ln = rp.stdout.strip()
            plan = ln[ln.rfind("(")+1:ln.rfind(")")] if "(" in ln else "Unknown"
            if "High Performance" not in plan and "Ultimate" not in plan:
                recs.append(_t(lang,
                    f"  ⚡ Plan zasilania: {plan}  →  zmień na High Performance",
                    f"  ⚡ Power plan: {plan}  →  switch to High Performance"))
        except Exception:
            pass

        # TEMP size
        try:
            temp_mb = sum(
                e.stat().st_size
                for e in os.scandir(tempfile.gettempdir())
                if e.is_file(follow_symlinks=False)
            ) // 1_048_576
            if temp_mb > 150:
                recs.append(_t(lang,
                    f"  🗑 Folder TEMP: {temp_mb} MB  →  [→ Optimization] → Clear TEMP",
                    f"  🗑 TEMP folder: {temp_mb} MB  →  [→ Optimization] → Clear TEMP"))
        except Exception:
            pass

        # RAM pressure (general, not just low-RAM case)
        if ram > 75 and not profile["ram_low"]:
            recs.append(_t(lang,
                f"  ⚠ RAM na {ram:.0f}%  →  zamknij zbędne karty i włącz Auto RAM Flush",
                f"  ⚠ RAM at {ram:.0f}%  →  close unused tabs and enable Auto RAM Flush"))

        # CPU pressure
        if cpu > 80:
            recs.append(_t(lang,
                f"  ⚠ CPU na {cpu:.0f}%  →  wpisz 'top' żeby znaleźć winowajcę",
                f"  ⚠ CPU at {cpu:.0f}%  →  type 'top' to identify the culprit"))

        # Few cores — process management is key
        if profile["few_cores"] and cpu > 60:
            recs.append(_t(lang,
                f"  ⚠ {profile['cpu_cores']} rdzenie CPU — ogranicz równoległe aplikacje",
                f"  ⚠ {profile['cpu_cores']} CPU cores — limit parallel running apps"))

        # Disk C: space
        try:
            import psutil
            du = psutil.disk_usage("C:\\")
            free_gb = round(du.free / 1_073_741_824, 1)
            if free_gb < 15:
                recs.append(_t(lang,
                    f"  ⚠ Dysk C: tylko {free_gb} GB wolne  →  usuń pliki, wyczyść AppData",
                    f"  ⚠ Drive C: only {free_gb} GB free  →  delete files, clean AppData"))
        except Exception:
            pass

        # AppData
        try:
            appdata = os.environ.get('APPDATA', '')
            if appdata and os.path.exists(appdata):
                count = sum(1 for d in os.scandir(appdata) if d.is_dir())
                if count > 60:
                    recs.append(_t(lang,
                        f"  📁 AppData: {count} folderów (resztki starych aplikacji)",
                        f"  📁 AppData: {count} folders (old app leftovers)"))
                    recs.append(_t(lang,
                        "     → wpisz '%appdata%' w Windows Search i posprzątaj",
                        "     → type '%appdata%' in Windows Search and clean up"))
        except Exception:
            pass

        # Startup programs link
        recs.append(_t(lang,
            "  🚀 Sprawdź programy startowe  [→ Startup Manager]",
            "  🚀 Review startup programs  [→ Startup Manager]"))

        if len(recs) == 1:  # only startup hint, system is clean
            recs.insert(0, _t(lang,
                "  ✓ System wygląda dobrze — nie ma oczywistych usprawnień.",
                "  ✓ System looks clean — no obvious wins found."))

        return [header] + recs

    # ── TURBO Boost ───────────────────────────────────────────────────────────

    def _resp_turbo_boost(self, r: ParseResult, lang: str = "pl") -> List[str]:
        if lang == "en":
            return [
                f"{self.PREFIX} TURBO BOOST — what it does:",
                "  Activates: High Performance power plan + RAM flush + disables non-essential services.",
                "  Result: faster response, lower RAM, more CPU headroom.",
                "  When to use: before gaming, heavy work, or when system feels sluggish.",
                "  💬 Go to the Optimization tab to activate it.",
            ]
        return [
            f"{self.PREFIX} TURBO BOOST — co robi:",
            "  Aktywuje: plan zasilania High Performance + flush RAM + wyłącza zbędne serwisy.",
            "  Efekt: szybsza odpowiedź systemu, mniej zajętego RAM, więcej mocy dla CPU.",
            "  Kiedy używać: przed graniem, ciężką pracą, albo gdy PC chodzi wolno.",
            "  💬 Zakładka Optimization → aktywuj TURBO BOOST jednym kliknięciem.",
        ]

    # ── Why slow / lag ────────────────────────────────────────────────────────

    def _resp_why_slow(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        from hck_gpt.memory.session_memory  import session_memory

        snap     = system_context.snapshot()
        hw       = user_knowledge.get_all_hardware()
        patterns = user_knowledge.get_all_patterns()
        profile  = _hw_profile(hw)

        cpu = float(snap.get("cpu_pct", 0) or 0)
        ram = float(snap.get("ram_pct", 0) or 0)

        # Pull top 3 CPU hogs live
        top_procs: list[str] = []
        try:
            import psutil
            raw = []
            for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
                try:
                    raw.append(p)
                    if len(raw) >= 64:
                        break
                except Exception:
                    continue
            sorted_procs = sorted(raw, key=lambda p: p.info.get("cpu_percent", 0) or 0, reverse=True)
            for p in sorted_procs[:3]:
                name = (p.info.get("name") or "?")[:24]
                pct  = p.info.get("cpu_percent", 0) or 0
                if pct > 0.5:
                    top_procs.append(f"{name} ({pct:.0f}%)")
        except Exception:
            pass

        reasons: list[str] = []

        # CPU reasons — with delta context
        if cpu > 80:
            cpu_delta = _delta_label(cpu, patterns.get("typical_cpu_avg"), lang)
            delta_sfx = f"  {cpu_delta}" if cpu_delta else ""
            reasons.append(_t(lang,
                f"  ⚠ CPU na {cpu:.0f}%{delta_sfx}",
                f"  ⚠ CPU at {cpu:.0f}%{delta_sfx}"))

        # ── Pomysł 5: hardware-aware RAM diagnosis ────────────────────────────
        if ram > 80:
            ram_delta = _delta_label(ram, patterns.get("typical_ram_avg"), lang)
            delta_sfx = f"  {ram_delta}" if ram_delta else ""
            if profile["ram_low"]:
                reasons.append(_t(lang,
                    f"  ⚠ RAM na {ram:.0f}%{delta_sfx} — masz tylko {profile['ram_gb']:.0f} GB (ciasno dla nowoczesnych apek)",
                    f"  ⚠ RAM at {ram:.0f}%{delta_sfx} — you only have {profile['ram_gb']:.0f} GB (tight for modern apps)"))
            else:
                reasons.append(_t(lang,
                    f"  ⚠ RAM na {ram:.0f}%{delta_sfx} — może używać pliku wymiany",
                    f"  ⚠ RAM at {ram:.0f}%{delta_sfx} — may be using pagefile"))

        elif ram > 65 and profile["ram_low"]:
            # Low RAM + moderately elevated — flag it earlier than normal
            reasons.append(_t(lang,
                f"  ! RAM na {ram:.0f}% — przy {profile['ram_gb']:.0f} GB to już odczuwalne",
                f"  ! RAM at {ram:.0f}% — with {profile['ram_gb']:.0f} GB total this is noticeable"))

        if snap.get("cpu_throttled"):
            reasons.append(_t(lang,
                "  ⚠ CPU throttluje — ogranicza mu się moc (przegrzanie lub brak zasilania)",
                "  ⚠ CPU throttling — power is being limited (heat or power supply issue)"))

        # ── Pomysł 5: HDD-specific cause ─────────────────────────────────────
        if profile["is_hdd"]:
            reasons.append(_t(lang,
                "  ! Dysk HDD — typowa przyczyna spowolnień przy dużej aktywności plików",
                "  ! HDD detected — a common cause of slowdowns under heavy file activity"))

        if lang == "en":
            header = f"{self.PREFIX} Why is it slow — live check:"
            lines  = [header]
            if not reasons:
                lines.append(f"  CPU: {cpu:.0f}%  RAM: {ram:.0f}%  — both look OK right now.")
                lines.append("  Possible causes: background updates, antivirus scan, disk activity.")
            else:
                lines.extend(reasons)
            if top_procs:
                lines.append(f"  Top processes: {',  '.join(top_procs)}")
            lines.append("  💬 Type 'top processes' for full list, or 'optimization' to fix  [→ Optimization]")
        else:
            header = f"{self.PREFIX} Dlaczego jest wolno — live sprawdzenie:"
            lines  = [header]
            if not reasons:
                lines.append(f"  CPU: {cpu:.0f}%  RAM: {ram:.0f}%  — teraz wygląda OK.")
                lines.append("  Możliwe: aktualizacje w tle, antywirus, aktywność dysku.")
            else:
                lines.extend(reasons)
            if top_procs:
                lines.append(f"  Winowajcy: {',  '.join(top_procs)}")
            lines.append("  💬 Wpisz 'top procesy' po pełną listę, lub napraw  [→ Optimization]")

        # ── Pomysł 2: session reference — link to previously shown RAM spec ───
        ram_sess = session_memory.get_response_data("hw_ram")
        if ram_sess.get("total_gb") and ram > 70:
            typ = ram_sess.get("typical_avg")
            if typ:
                lines.append(_t(lang,
                    f"  (Wcześniej omawiany RAM: {ram_sess['total_gb']} GB, typowo {typ}% — teraz {ram:.0f}%)",
                    f"  (Earlier your RAM: {ram_sess['total_gb']} GB, typical {typ}% — now at {ram:.0f}%)"))

        # Historical context from stats engine
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge as _uk2
            avg7 = float(patterns.get("typical_cpu_avg") or 0)
            if avg7 > 0 and cpu > avg7 + 15:
                lines.append(_t(lang,
                    f"  ⚠ CPU ({cpu:.0f}%) jest {cpu - avg7:.0f}% powyżej Twojej 7-dniowej normy ({avg7:.0f}%).",
                    f"  ⚠ CPU ({cpu:.0f}%) is {cpu - avg7:.0f}% above your 7-day avg ({avg7:.0f}%)."))
        except Exception:
            pass

        return lines

    # ── Process info ──────────────────────────────────────────────────────────

    # Known process explanations
    _KNOWN_PROCS = {
        "svchost.exe": ("Svchost.exe to kontener systemowy — odpala wiele usług Windows jednocześnie. To normalne że jest ich kilka.",
                        "Svchost.exe is a Windows service host container — runs multiple system services. Multiple instances are normal."),
        "explorer.exe": ("Explorer.exe to powłoka Windows — pasek zadań, Eksplorator plików. NIE wyłączaj, bo zniknie UI.",
                         "Explorer.exe is the Windows shell — taskbar, File Explorer. Don't kill it or your UI will disappear."),
        "csrss.exe":    ("Csrss.exe to krytyczny proces Windows (Client/Server Runtime). Zabicie = błękit ekranu. Zostaw.",
                         "Csrss.exe is a critical Windows process (Client/Server Runtime). Killing it = BSOD. Leave it alone."),
        "lsass.exe":    ("Lsass.exe zarządza logowaniem i bezpieczeństwem. Nietykalny — zabicie restartuje system.",
                         "Lsass.exe manages Windows login and security. Untouchable — killing it forces a reboot."),
        "system":       ("'System' to rdzeń kernela Windows. Zawsze obecny, bezpieczny.",
                         "'System' is the Windows kernel process. Always present, always safe."),
        "dwm.exe":      ("Dwm.exe — Desktop Window Manager, renderuje efekty wizualne Windows. Normalne zużycie GPU.",
                         "Dwm.exe — Desktop Window Manager, renders Windows visual effects. Normal GPU usage."),
        "runtime broker": ("Runtime Broker zarządza uprawnieniami aplikacji UWP (Store). Normalnie niska aktywność.",
                           "Runtime Broker manages UWP app permissions (Store apps). Should be low activity normally."),
        "chrome.exe":   ("Chrome.exe — Google Chrome. Wiele procesów to norma (każda zakładka = osobny proces).",
                         "Chrome.exe — Google Chrome. Multiple processes are normal (each tab = separate process)."),
        "discord.exe":  ("Discord.exe — komunikator Discord. Może zużywać sporo RAM przez overlay i video.",
                         "Discord.exe — Discord app. Can use significant RAM due to overlay and video features."),
    }

    def _resp_process_info(self, r: ParseResult, lang: str = "pl") -> List[str]:
        # Try to extract process name from raw text
        raw = (r.raw_text or "").lower()
        matched_key = None
        matched_val = None
        for proc_name, (pl_desc, en_desc) in self._KNOWN_PROCS.items():
            if proc_name.replace(".exe", "") in raw or proc_name in raw:
                matched_key = proc_name
                matched_val = (pl_desc, en_desc)
                break

        if matched_val:
            desc = matched_val[1] if lang == "en" else matched_val[0]
            return [f"{self.PREFIX} {matched_key}:", f"  {desc}", _followup("process", lang)]

        # Generic fallback — suggest process library
        if lang == "en":
            return [
                f"{self.PREFIX} I don't have specific info on that process.",
                "  Check: Efficiency tab → click on the process for details.",
                "  General rule: if it's Microsoft-signed and low CPU — safe.",
                "  High CPU + unknown name → worth investigating.",
                _followup("process", lang),
            ]
        return [
            f"{self.PREFIX} Nie mam konkretnych danych o tym procesie.",
            "  Sprawdź: zakładka Efficiency → kliknij na proces.",
            "  Ogólna zasada: podpisany przez Microsoft i mało CPU — bezpieczny.",
            "  Dużo CPU + nieznana nazwa → warto sprawdzić.",
            _followup("process", lang),
        ]

    # ── RAM why high ──────────────────────────────────────────────────────────

    def _resp_ram_why_high(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        from hck_gpt.memory.session_memory  import session_memory

        snap    = system_context.snapshot()
        hw      = user_knowledge.get_all_hardware()
        profile = _hw_profile(hw)

        ram  = float(snap.get("ram_pct",     0) or 0)
        used = snap.get("ram_used_gb", "?")
        free = snap.get("ram_free_gb", "?")

        # Top RAM consumers
        top_ram: list[str] = []
        try:
            import psutil
            raw = []
            for p in psutil.process_iter(["name", "memory_percent"]):
                try:
                    raw.append(p)
                    if len(raw) >= 64:
                        break
                except Exception:
                    continue
            sorted_procs = sorted(raw, key=lambda p: p.info.get("memory_percent", 0) or 0, reverse=True)
            for p in sorted_procs[:3]:
                name = (p.info.get("name") or "?")[:24]
                pct  = p.info.get("memory_percent", 0) or 0
                if pct > 0.3:
                    top_ram.append(f"{name} ({pct:.1f}%)")
        except Exception:
            pass

        # ── Pomysł 2: get typical avg from session data or patterns ───────────
        ram_sess  = session_memory.get_response_data("hw_ram")
        typ_avg   = ram_sess.get("typical_avg")
        if typ_avg is None:
            patterns = user_knowledge.get_all_patterns()
            typ_avg  = patterns.get("typical_ram_avg")

        if lang == "en":
            header = (
                f"{self.PREFIX} Why is RAM high — {ram:.0f}%"
                f" ({used} GB used / {free} GB free):"
            )
            lines = [header]

            # ── Pomysł 5: low-RAM context ─────────────────────────────────────
            if profile["ram_low"]:
                lines.append(
                    f"  ⚠ You only have {profile['ram_gb']:.0f} GB total — "
                    f"{ram:.0f}% means only ~{free} GB breathing room."
                )

            if top_ram:
                lines.append(f"  Top consumers: {',  '.join(top_ram)}")

            # ── Pomysł 2: delta vs typical ────────────────────────────────────
            if typ_avg:
                delta_str = _delta_label(ram, typ_avg, "en")
                if delta_str:
                    lines.append(f"  Context: {delta_str}")

            if ram > 90:
                lines.append("  ⚠ Critical — system is likely using pagefile (slow disk swapping).")
                lines.append("  Fix: close unused apps  [→ Optimization]")
                if profile["is_hdd"]:
                    lines.append("  ⚠ HDD detected — pagefile on HDD is very slow. Consider Virtual Memory on faster drive  [→ Virtual Memory]")
            elif ram > 75:
                lines.append("  High but manageable. Browser tabs are usually the main cause.")
                lines.append(f"  Reduce background apps  [→ Optimization]  ·  or add swap  [→ Virtual Memory]")
                if profile["ram_low"]:
                    lines.append(f"  Long-term: {profile['ram_gb']:.0f} GB is limiting — more RAM would help.")
            else:
                lines.append("  Within normal range — Windows pre-loads data into RAM.")
                lines.append("  Free RAM is wasted RAM. Only act if above 85%.")

        else:
            header = (
                f"{self.PREFIX} Dlaczego RAM wysoki — {ram:.0f}%"
                f" ({used} GB zajęte / {free} GB wolne):"
            )
            lines = [header]

            if profile["ram_low"]:
                lines.append(
                    f"  ⚠ Masz tylko {profile['ram_gb']:.0f} GB — "
                    f"{ram:.0f}% to zostaje ci ~{free} GB na resztę."
                )

            if top_ram:
                lines.append(f"  Główni winowajcy: {',  '.join(top_ram)}")

            if typ_avg:
                delta_str = _delta_label(ram, typ_avg, "pl")
                if delta_str:
                    lines.append(f"  Kontekst: {delta_str}")

            if ram > 90:
                lines.append("  ⚠ Krytyczne — system używa prawdopodobnie pliku wymiany (wolno).")
                lines.append("  Napraw: zamknij zbędne programy  [→ Optimization]")
                if profile["is_hdd"]:
                    lines.append("  ⚠ HDD wykryty — plik wymiany na HDD jest bardzo wolny  [→ Virtual Memory]")
            elif ram > 75:
                lines.append("  Wysoki, zarządzalny. Główna przyczyna: karty przeglądarki.")
                lines.append(f"  Zamknij aplikacje w tle  [→ Optimization]  ·  lub dodaj pamięć  [→ Virtual Memory]")
                if profile["ram_low"]:
                    lines.append(f"  Długofalowo: {profile['ram_gb']:.0f} GB to za mało — więcej RAM by pomogło.")
            else:
                lines.append("  To normalny zakres — Windows wstępnie ładuje dane do RAM.")
                lines.append("  Wolny RAM = zmarnowany RAM. Reaguj dopiero powyżej 85%.")

        return lines

    # ── GPU temp why ──────────────────────────────────────────────────────────

    def _resp_gpu_temp_why(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        snap     = system_context.snapshot()
        gpu_temp = snap.get("gpu_temp", None)

        if lang == "en":
            lines = [f"{self.PREFIX} GPU temperature analysis:"]
            if gpu_temp:
                if gpu_temp > 90:
                    lines += [
                        f"  ⚠ {gpu_temp}°C — CRITICAL. GPU is thermal throttling.",
                        "  Causes: full load (gaming/rendering), poor airflow, dusty heatsink.",
                        "  Fix: clean GPU cooler, improve case airflow, lower in-game settings.",
                    ]
                elif gpu_temp > 80:
                    lines += [
                        f"  ! {gpu_temp}°C — high but within spec for most GPUs under load.",
                        "  Modern GPUs are designed for up to 85–95°C under full load.",
                        "  Check airflow if idle temp is also high.",
                    ]
                else:
                    lines += [
                        f"  ✓ {gpu_temp}°C — normal operating temperature.",
                        "  GPUs under load typically run 65–80°C. You're fine.",
                    ]
            else:
                lines += [
                    "  No GPU temperature sensor data available.",
                    "  Under load (gaming): 65–80°C is normal. 85°C+ warrants attention.",
                    "  Check GPU-Z or HWInfo for hardware-level readings.",
                ]
            lines.append("  💬 Type 'temperatures' for full thermal report.")
        else:
            lines = [f"{self.PREFIX} Analiza temperatury GPU:"]
            if gpu_temp:
                if gpu_temp > 90:
                    lines += [
                        f"  ⚠ {gpu_temp}°C — KRYTYCZNA. GPU throttluje termicznie.",
                        "  Przyczyny: pełne obciążenie (gry/render), słaby przepływ powietrza, zakurzony chłodnik.",
                        "  Fix: wyczyść chłodnik GPU, popraw obieg powietrza, obniż ustawienia gry.",
                    ]
                elif gpu_temp > 80:
                    lines += [
                        f"  ! {gpu_temp}°C — wysoka, ale w normie dla większości GPU pod obciążeniem.",
                        "  Nowoczesne GPU są projektowane do 85–95°C pod pełnym ładunkiem.",
                        "  Sprawdź przepływ powietrza jeśli temp na jałowym też jest wysoka.",
                    ]
                else:
                    lines += [
                        f"  ✓ {gpu_temp}°C — normalna temperatura robocza.",
                        "  GPU pod obciążeniem gier: 65–80°C to norma. Wszystko OK.",
                    ]
            else:
                lines += [
                    "  Brak danych z czujnika temperatury GPU.",
                    "  Pod obciążeniem (gry): 65–80°C norma. Powyżej 85°C warto reagować.",
                    "  Sprawdź GPU-Z lub HWInfo dla odczytów sprzętowych.",
                ]
            lines.append("  💬 Wpisz 'temperatury' po pełny raport termiczny.")
        return lines

    # ── Disk health ───────────────────────────────────────────────────────────

    def _resp_disk_health(self, r: ParseResult, lang: str = "pl") -> List[str]:
        lines = [_t(lang, f"{self.PREFIX} Zdrowie dysków:", f"{self.PREFIX} Disk health:")]
        try:
            import psutil
            SAFE_FSTYPES = {"ntfs", "fat32", "exfat", "refs"}
            partitions = [
                p for p in psutil.disk_partitions(all=False)
                if "remote" not in (p.opts or "").lower()
                and p.fstype and p.fstype.lower() in SAFE_FSTYPES
            ]
            for p in partitions[:4]:
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    used_pct = u.percent
                    free_gb  = round(u.free  / 1_073_741_824, 1)
                    total_gb = round(u.total / 1_073_741_824, 1)
                    if used_pct > 90:
                        icon = "⚠"
                        status = _t(lang, "PEŁNY — zwolnij miejsce!", "FULL — free up space!")
                    elif used_pct > 75:
                        icon = "!"
                        status = _t(lang, f"{used_pct:.0f}% zajęte", f"{used_pct:.0f}% used")
                    else:
                        icon = "✓"
                        status = _t(lang, f"{used_pct:.0f}% zajęte", f"{used_pct:.0f}% used")
                    lines.append(f"  {icon} {p.device}  {total_gb} GB  —  {free_gb} GB {_t(lang, 'wolne', 'free')}  ({status})")
                except Exception:
                    pass
        except Exception:
            pass

        # S.M.A.R.T. note
        lines.append(_t(lang,
            "  ℹ S.M.A.R.T. monitoring: sprawdź CrystalDiskInfo dla pełnej diagnozy dysku.",
            "  ℹ S.M.A.R.T. check: use CrystalDiskInfo for full drive health diagnostics."))
        lines.append(_followup("disk", lang))
        return lines

    # ── Startup programs check ────────────────────────────────────────────────

    _HIGH_IMPACT_STARTUP = {
        "chrome", "opera", "operagx", "brave", "firefox", "edge",
        "epicgameslauncher", "steam", "battlenet", "ubisoft",
        "eaapp", "rockstarlauncher", "gog", "spotify",
        "discordptb", "discordcanary",
    }
    _MEDIUM_IMPACT_STARTUP = {
        "discord", "slack", "teams", "zoom", "skype",
        "telegram", "signal", "onedrive", "dropbox",
    }

    def _resp_startup_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        entries: list[tuple[str, str]] = []
        try:
            import winreg
            _REG = [
                (winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
            ]
            seen: set[str] = set()
            for hive, path in _REG:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            name, val, _ = winreg.EnumValue(key, i)
                            slug = name.lower().replace(" ", "").replace("-", "")
                            if slug not in seen:
                                seen.add(slug)
                                entries.append((name, val))
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    continue
        except Exception:
            pass

        if not entries:
            return [_t(lang,
                       f"{self.PREFIX} Nie mogę odczytać wpisów startowych.",
                       f"{self.PREFIX} Can't read startup entries.")]

        high, medium, low = [], [], []
        for name, val in entries:
            exe = val.lower()
            slug = name.lower().replace(" ", "").replace("-", "")
            if any(k in exe or k in slug for k in self._HIGH_IMPACT_STARTUP):
                high.append(name)
            elif any(k in exe or k in slug for k in self._MEDIUM_IMPACT_STARTUP):
                medium.append(name)
            else:
                low.append(name)

        total = len(entries)
        verdict = ""
        if total <= 4:
            verdict = _t(lang, "✓ Bardzo dobry autostart.", "✓ Very clean startup.")
        elif total <= 8:
            verdict = _t(lang, "Umiarkowany autostart — da się zoptymalizować.", "Moderate startup — could be trimmed.")
        else:
            verdict = _t(lang, "⚠ Za dużo elementów startowych — spowolnienie boot.", "⚠ Too many startup items — boot is slower.")

        lines = [_t(lang,
                    f"{self.PREFIX} Programy startowe ({total} wpisów):",
                    f"{self.PREFIX} Startup programs ({total} entries):")]
        lines.append(f"  {verdict}")
        if high:
            lines.append(_t(lang,
                            f"  Wysoki wpływ ({len(high)}): {', '.join(high[:4])}",
                            f"  High impact ({len(high)}): {', '.join(high[:4])}"))
        if medium:
            lines.append(_t(lang,
                            f"  Średni wpływ ({len(medium)}): {', '.join(medium[:4])}",
                            f"  Medium impact ({len(medium)}): {', '.join(medium[:4])}"))
        if low:
            lines.append(_t(lang,
                            f"  Niski wpływ ({len(low)}): {', '.join(low[:3])}{'...' if len(low) > 3 else ''}",
                            f"  Low impact ({len(low)}): {', '.join(low[:3])}{'...' if len(low) > 3 else ''}"))
        lines.append(_t(lang,
                        "  💬 Zarządzaj programami startowymi  [→ Startup Manager]",
                        "  💬 Manage startup programs  [→ Startup Manager]"))
        lines.append(_followup("startup", lang))
        return lines

    # ── Startup safety — is it safe to disable X from startup? ───────────────

    # Per-program safety verdict: True=safe, False=keep, None=depends on usage
    _STARTUP_SAFETY_KB: dict = {
        "chrome":       (True,  "Przeglądarka — nie potrzebuje startować z Windows, otwieraj ręcznie",
                                "Browser — no reason to start with Windows, launch manually"),
        "opera":        (True,  "Przeglądarka — wyłącz ze startu, otwieraj ręcznie",
                                "Browser — safe to disable, open manually"),
        "operagx":      (True,  "Przeglądarka gamingowa — bezpieczne do wyłączenia ze startu",
                                "Gaming browser — safe to disable from startup"),
        "brave":        (True,  "Przeglądarka — nie ma sensu startować z Windows",
                                "Browser — no reason to start with Windows"),
        "firefox":      (True,  "Przeglądarka — wyłącz ze startu",
                                "Browser — safe to disable from startup"),
        "spotify":      (True,  "Odtwarzacz muzyki — wyłącz, odpali się gdy klikniesz ikonę",
                                "Music player — disable, it starts when you click the icon"),
        "discord":      (True,  "Komunikator — bezpieczne do wyłączenia, uruchom ręcznie gdy potrzebny",
                                "Chat app — safe to disable, launch manually when needed"),
        "steam":        (True,  "Platforma gier — wyłącz ze startu, otwieraj gdy grasz",
                                "Gaming platform — disable from startup, open when gaming"),
        "epicgameslauncher": (True, "Launcher gier — nie potrzebuje startować z Windows",
                                    "Game launcher — no need to start with Windows"),
        "battlenet":    (True,  "Launcher Blizzard — wyłącz ze startu",
                                "Blizzard launcher — safe to disable"),
        "ubisoft":      (True,  "Launcher Ubisoft — wyłącz ze startu",
                                "Ubisoft launcher — safe to disable"),
        "skype":        (True,  "Skype — wyłącz ze startu; użytkownicy Discord/Teams nie potrzebują",
                                "Skype — disable from startup; Discord/Teams users don't need it"),
        "telegram":     (True,  "Telegram — wyłącz ze startu, uruchom ręcznie gdy potrzebny",
                                "Telegram — disable from startup, launch manually when needed"),
        "signal":       (True,  "Signal — wyłącz jeśli nie potrzebujesz powiadomień od razu po starcie",
                                "Signal — disable if you don't need instant notifications at boot"),
        "teams":        (None,  "Teams — zostaw jeśli używasz w pracy codziennie; wyłącz jeśli nie",
                                "Teams — keep it if used for work daily; disable otherwise"),
        "zoom":         (None,  "Zoom — zostaw jeśli masz regularne spotkania; inaczej wyłącz",
                                "Zoom — keep for regular meetings; disable otherwise"),
        "slack":        (None,  "Slack — zostaw jeśli używasz na co dzień",
                                "Slack — keep it if you use it daily"),
        "onedrive":     (None,  "OneDrive — wyłącz jeśli nie synchronizujesz aktywnie; zostaw jeśli tak",
                                "OneDrive — disable if not actively syncing; keep if you do"),
        "dropbox":      (None,  "Dropbox — wyłącz jeśli nie synchronizujesz aktywnie plików",
                                "Dropbox — disable if not actively syncing files"),
        "msedge":       (None,  "Edge — wyłączenie bezpieczne, możesz uruchomić ręcznie",
                                "Edge — safe to disable, launch manually when needed"),
        "realtek":      (False, "Sterownik audio Realtek — warto zostawić dla stabilności dźwięku",
                                "Realtek audio driver — worth keeping for audio stability"),
        "nvidia":       (False, "NVIDIA Panel / GeForce Experience — lepiej zostawić dla sterowników",
                                "NVIDIA Control Panel / GeForce Experience — better to keep"),
        "amd":          (False, "Oprogramowanie AMD — warto zostawić dla sterowników GPU/CPU",
                                "AMD software — worth keeping for GPU/CPU drivers"),
        "intel":        (False, "Intel software — powiązany ze sterownikami, lepiej zostaw",
                                "Intel software — driver-related, better to keep"),
        "windowsdefender": (False, "Windows Defender — NIE wyłączaj! To Twoje bezpieczeństwo systemowe",
                                   "Windows Defender — do NOT disable! This is your system security"),
    }

    def _resp_startup_safety(self, r: ParseResult, lang: str = "pl") -> List[str]:
        raw = (r.raw_text or "").lower()

        matched_slug = None
        matched_data = None
        for slug, data in self._STARTUP_SAFETY_KB.items():
            if slug in raw:
                matched_slug = slug
                matched_data = data
                break

        if matched_data:
            safe, reason_pl, reason_en = matched_data
            if safe is True:
                verdict = _t(lang, "✓ Bezpieczne do wyłączenia ze startu:", "✓ Safe to disable from startup:")
            elif safe is False:
                verdict = _t(lang, "⚠ Lepiej zostawić włączone:", "⚠ Better to keep enabled:")
            else:
                verdict = _t(lang, "➤ Zależy od użycia:", "➤ Depends on your usage:")
            reason = reason_en if lang == "en" else reason_pl
            return [
                _t(lang,
                   f"{self.PREFIX} Autostart — {matched_slug}:",
                   f"{self.PREFIX} Startup — {matched_slug}:"),
                f"  {verdict}",
                f"  {reason}",
                _t(lang,
                   "  Zarządzaj tym i innymi wpisami  [→ Startup Manager]",
                   "  Manage this and other startup entries  [→ Startup Manager]"),
                _followup("startup", lang),
            ]

        # No specific program matched — general guide
        if lang == "en":
            return [
                f"{self.PREFIX} Startup program safety guide:",
                "  ✓ Safe to disable:  Chrome, Firefox, Spotify, Discord, Steam, game launchers",
                "  ➤ Depends on use:   OneDrive, Teams, Zoom — disable if not used daily",
                "  ⚠ Keep enabled:     security software, audio/GPU drivers, system services",
                "  Rule: if you can launch it manually when you need it — disable it at boot.",
                "  💬 See all your startup entries  [→ Startup Manager]",
                _followup("startup", lang),
            ]
        return [
            f"{self.PREFIX} Poradnik — co wyłączyć ze startu:",
            "  ✓ Bezpieczne:    Chrome, Firefox, Spotify, Discord, Steam, launchery gier",
            "  ➤ Zależy:        OneDrive, Teams, Zoom — wyłącz jeśli nie używasz codziennie",
            "  ⚠ Zostaw:        antywirus, sterowniki audio/GPU, usługi systemowe",
            "  Zasada: jeśli możesz uruchomić ręcznie — nie potrzebuje startować z Windows.",
            "  💬 Przejrzyj wszystkie wpisy  [→ Startup Manager]",
            _followup("startup", lang),
        ]

    # ── What changed on my PC since yesterday ────────────────────────────────

    def _resp_pc_changes(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Broad 'what changed since yesterday' — goes beyond raw numbers to show:
        new/missing active processes, performance shift summary, power plan,
        startup entry count.
        """
        changes: list[str] = []

        # ── 1. New / gone processes (top 10 today vs yesterday) ───────────────
        try:
            from hck_stats_engine.query_api import query_api
            from datetime import datetime, timedelta
            today_str = datetime.now().strftime("%Y-%m-%d")
            yest_str  = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            t_rows = query_api.get_process_daily_breakdown(today_str, top_n=10) or []
            y_rows = query_api.get_process_daily_breakdown(yest_str,  top_n=10) or []
            t_procs = {row.get("process_name") for row in t_rows} - {None}
            y_procs = {row.get("process_name") for row in y_rows} - {None}
            new_today  = t_procs - y_procs
            gone_today = y_procs - t_procs
            if new_today:
                names = ", ".join(sorted(new_today)[:3])
                changes.append(_t(lang,
                    f"  🆕 Nowe aktywne procesy (nie było wczoraj): {names}",
                    f"  🆕 New active processes (not in yesterday's top): {names}"))
            if gone_today:
                names = ", ".join(sorted(gone_today)[:3])
                changes.append(_t(lang,
                    f"  👻 Nieaktywne dziś (były wczoraj): {names}",
                    f"  👻 No longer active today (were in yesterday's top): {names}"))
        except Exception:
            pass

        # ── 2. Performance delta summary (only if notable) ────────────────────
        try:
            from hck_stats_engine.query_api import query_api as qa
            today = qa.get_daily_summary(days=1)
            yest  = qa.get_daily_summary(days=2)
            if today and yest:
                cpu_t = today.get("cpu_avg") or 0
                cpu_y = yest.get("cpu_avg")  or 0
                ram_t = today.get("ram_avg") or 0
                ram_y = yest.get("ram_avg")  or 0
                cpu_d = cpu_t - cpu_y
                ram_d = ram_t - ram_y
                if abs(cpu_d) > 5 or abs(ram_d) > 5:
                    cpu_arrow = "↑" if cpu_d > 3 else ("↓" if cpu_d < -3 else "→")
                    ram_arrow = "↑" if ram_d > 3 else ("↓" if ram_d < -3 else "→")
                    changes.append(_t(lang,
                        f"  📊 Wydajność: CPU {cpu_arrow} {cpu_t:.0f}% (wczoraj {cpu_y:.0f}%) | RAM {ram_arrow} {ram_t:.0f}% (wczoraj {ram_y:.0f}%)",
                        f"  📊 Performance: CPU {cpu_arrow} {cpu_t:.0f}% (yest {cpu_y:.0f}%) | RAM {ram_arrow} {ram_t:.0f}% (yest {ram_y:.0f}%)"))
        except Exception:
            pass

        # ── 3. Current power plan ─────────────────────────────────────────────
        try:
            import subprocess
            rp = subprocess.run(["powercfg", "/getactivescheme"],
                                capture_output=True, text=True, timeout=3)
            ln = rp.stdout.strip()
            plan = ln[ln.rfind("(")+1:ln.rfind(")")] if "(" in ln else ""
            if plan:
                changes.append(_t(lang,
                    f"  ⚡ Aktywny plan zasilania: {plan}",
                    f"  ⚡ Active power plan: {plan}"))
        except Exception:
            pass

        # ── 4. Startup entry count ────────────────────────────────────────────
        try:
            import winreg
            startup_count = 0
            for hive, path in [
                (winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            winreg.EnumValue(key, i)
                            startup_count += 1
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    pass
            if startup_count > 0:
                if startup_count > 10:
                    note = _t(lang, " ⚠ dużo — warto przejrzeć", " ⚠ high — worth reviewing")
                elif startup_count <= 4:
                    note = _t(lang, " ✓ bardzo czysty", " ✓ very clean")
                else:
                    note = ""
                changes.append(_t(lang,
                    f"  🚀 Programy startowe: {startup_count} wpisów{note}",
                    f"  🚀 Startup programs: {startup_count} entries{note}"))
        except Exception:
            pass

        header = _t(lang,
            f"{self.PREFIX} Co się zmieniło na PC od wczoraj:",
            f"{self.PREFIX} What changed on your PC since yesterday:")
        lines = [header]

        if not changes:
            lines.append(_t(lang,
                "  Za mało danych historycznych — potrzebuję min. 2 dni historii w bazie.",
                "  Not enough history yet — need at least 2 days of data."))
            lines.append(_t(lang,
                "  Sprawdź zmiany ręcznie: zakładka AllMonitor → DayStats.",
                "  Check manually: AllMonitor tab → DayStats."))
        else:
            lines.extend(changes)

        lines.append(_t(lang,
            "  💬 Pełna oś czasu: zakładka AllMonitor.",
            "  💬 Full timeline: AllMonitor tab."))
        lines.append(_followup("session", lang))
        return lines

    # ── System risk assessment ────────────────────────────────────────────────

    def _resp_system_risk(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Ranks current system state by risk level across performance,
        security and stability dimensions. Inspired by: 'which recent system
        changes are creating the highest performance, security, or stability risk?'
        """
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        snap    = system_context.snapshot()
        hw      = user_knowledge.get_all_hardware()
        profile = _hw_profile(hw)

        # risks: list of (level, message) — level 3=high, 2=medium, 1=info
        risks: list[tuple[int, str]] = []

        cpu = float(snap.get("cpu_pct", 0) or 0)
        ram = float(snap.get("ram_pct", 0) or 0)

        # ── Performance ───────────────────────────────────────────────────────
        if cpu > 85:
            risks.append((3, _t(lang,
                f"🔴 CPU {cpu:.0f}% — ryzyko throttlingu i spowolnień (wydajność)",
                f"🔴 CPU {cpu:.0f}% — throttle and slowdown risk (performance)")))
        elif cpu > 70:
            risks.append((2, _t(lang,
                f"🟡 CPU {cpu:.0f}% — podwyższone obciążenie, mały margines",
                f"🟡 CPU {cpu:.0f}% — elevated load, low headroom")))

        if ram > 85:
            risks.append((3, _t(lang,
                f"🔴 RAM {ram:.0f}% — system może używać pagefile (stabilność/wydajność)",
                f"🔴 RAM {ram:.0f}% — system may be swapping to pagefile (stability/performance)")))
        elif ram > 70:
            risks.append((2, _t(lang,
                f"🟡 RAM {ram:.0f}% — mało wolnej pamięci, reaguj przy 85%+",
                f"🟡 RAM {ram:.0f}% — low free memory headroom, act at 85%+")))

        if snap.get("cpu_throttled"):
            risks.append((3, _t(lang,
                "🔴 CPU throttluje — moc ograniczona (przegrzanie / power limit) (stabilność)",
                "🔴 CPU throttling — power is being limited (heat or power limit) (stability)")))

        # ── Disk space ────────────────────────────────────────────────────────
        try:
            import psutil
            for p in psutil.disk_partitions(all=False):
                if "remote" in (p.opts or "").lower():
                    continue
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    if u.percent > 90:
                        free_gb = round(u.free / 1_073_741_824, 1)
                        risks.append((3, _t(lang,
                            f"🔴 Dysk {p.device}: {u.percent:.0f}% pełny ({free_gb} GB wolne) — ryzyko awarii zapisu (stabilność)",
                            f"🔴 Drive {p.device}: {u.percent:.0f}% full ({free_gb} GB free) — write failure risk (stability)")))
                    elif u.percent > 80:
                        risks.append((2, _t(lang,
                            f"🟡 Dysk {p.device}: {u.percent:.0f}% zajęty — zacznij zwalniać miejsce",
                            f"🟡 Drive {p.device}: {u.percent:.0f}% used — start freeing space")))
                except Exception:
                    pass
        except Exception:
            pass

        # ── Startup count ─────────────────────────────────────────────────────
        try:
            import winreg
            startup_count = 0
            for hive, path in [
                (winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            winreg.EnumValue(key, i)
                            startup_count += 1
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    pass
            if startup_count > 12:
                risks.append((2, _t(lang,
                    f"🟡 Autostart: {startup_count} wpisów — zbędne tło + wolniejszy boot (wydajność)",
                    f"🟡 Startup: {startup_count} entries — background bloat + slower boot (performance)")))
            elif startup_count > 8:
                risks.append((1, _t(lang,
                    f"ℹ Autostart: {startup_count} wpisów — warto przejrzeć  [→ Startup Manager]",
                    f"ℹ Startup: {startup_count} entries — worth reviewing  [→ Startup Manager]")))
        except Exception:
            pass

        # ── Hardware profile ──────────────────────────────────────────────────
        if profile["ram_very_low"]:
            risks.append((3, _t(lang,
                f"🔴 RAM: tylko {profile['ram_gb']:.0f} GB — krytycznie mało dla nowoczesnych systemów",
                f"🔴 RAM: only {profile['ram_gb']:.0f} GB — critically low for modern workloads")))
        elif profile["ram_low"] and ram > 60:
            risks.append((2, _t(lang,
                f"🟡 RAM: {profile['ram_gb']:.0f} GB + {ram:.0f}% zajęte — bardzo mały margines",
                f"🟡 RAM: {profile['ram_gb']:.0f} GB + {ram:.0f}% used — very low margin")))
        if profile["is_hdd"]:
            risks.append((1, _t(lang,
                "ℹ HDD wykryty — wolniejszy dysk to systemowe spowolnienie przy każdej operacji na plikach",
                "ℹ HDD detected — slower disk causes system-wide slowdowns during file operations")))

        # ── Security ─────────────────────────────────────────────────────────
        try:
            import psutil
            from hck_gpt.process_library import process_library as _lib
            _SUSPICIOUS_KW = {"xmrig", "cpuminer", "nicehash", "minerd", "cgminer"}
            susp: list[str] = []
            checked = 0
            for proc in psutil.process_iter(["name"]):
                try:
                    nm = (proc.info.get("name") or "").lower()
                    base = nm.replace(".exe", "")
                    if any(kw in base for kw in _SUSPICIOUS_KW):
                        susp.append(nm)
                    else:
                        info = _lib.get_process_info(nm)
                        if info and info.get("safety") in ("suspicious", "unsafe"):
                            susp.append(nm)
                    checked += 1
                    if checked >= 120:
                        break
                except Exception:
                    continue
            if susp:
                names = ", ".join(susp[:3])
                risks.append((3, _t(lang,
                    f"🔴 Bezpieczeństwo: {len(susp)} podejrzanych procesów ({names}) — sprawdź natychmiast",
                    f"🔴 Security: {len(susp)} suspicious process(es) ({names}) — check immediately")))
        except Exception:
            pass

        # ── Sort descending by risk level ─────────────────────────────────────
        risks.sort(key=lambda x: x[0], reverse=True)

        header = _t(lang,
            f"{self.PREFIX} Analiza ryzyka systemu:",
            f"{self.PREFIX} System risk assessment:")
        lines = [header]

        if not risks:
            lines.append(_t(lang,
                "  ✅ Nie znaleziono aktywnych ryzyk. System wygląda zdrowo.",
                "  ✅ No active risks found. System looks healthy."))
        else:
            lines.append(_t(lang,
                f"  Wykryto {len(risks)} czynnik(ów) ryzyka — od najwyższego:",
                f"  Found {len(risks)} risk factor(s) — ranked highest first:"))
            for _, msg in risks[:6]:
                lines.append(f"  {msg}")

        lines.append("")
        lines.append(_t(lang,
            "  💬 Wpisz 'przyspiesz komputer' po plan naprawy  ·  'zdrowie systemu' po pełną diagnozę",
            "  💬 Type 'speed up pc' for a fix plan  ·  'health check' for full diagnostics"))
        lines.append(_followup("health", lang))
        return lines

    # ── Disk usage — why high ─────────────────────────────────────────────────

    def _resp_disk_usage_why(self, r: ParseResult, lang: str = "pl") -> List[str]:
        lines = [_t(lang,
                    f"{self.PREFIX} Analiza aktywności dysku:",
                    f"{self.PREFIX} Disk activity analysis:")]
        try:
            import psutil

            # Overall disk I/O
            io = psutil.disk_io_counters(perdisk=False)
            if io:
                read_mb  = round(io.read_bytes  / 1_048_576)
                write_mb = round(io.write_bytes / 1_048_576)
                lines.append(_t(lang,
                                f"  Odczyt total:  {read_mb} MB   Zapis total: {write_mb} MB",
                                f"  Total read:    {read_mb} MB   Total write: {write_mb} MB"))

            # Top disk I/O processes
            io_procs: list[tuple[str, int]] = []
            for p in psutil.process_iter(["name", "io_counters"]):
                try:
                    ioc = p.info.get("io_counters")
                    if ioc:
                        total_bytes = getattr(ioc, "read_bytes", 0) + getattr(ioc, "write_bytes", 0)
                        if total_bytes > 0:
                            io_procs.append((p.info["name"] or "?", total_bytes))
                except Exception:
                    continue
            io_procs.sort(key=lambda x: x[1], reverse=True)

            if io_procs:
                lines.append(_t(lang, "  Procesy z najwyższym I/O:", "  Processes with highest I/O:"))
                for name, total in io_procs[:5]:
                    mb = round(total / 1_048_576)
                    lines.append(f"    — {name[:30]:<30}  {mb} MB")
            else:
                lines.append(_t(lang,
                                "  Brak danych per-proces — Windows może ograniczać dostęp.",
                                "  No per-process data — Windows may restrict I/O access."))

            # Disk fill level check
            for part in psutil.disk_partitions(all=False):
                if "remote" in (part.opts or "").lower():
                    continue
                try:
                    u = psutil.disk_usage(part.mountpoint)
                    if u.percent > 85:
                        free = round(u.free / 1_073_741_824, 1)
                        lines.append(_t(lang,
                                        f"  ⚠ {part.device} prawie pełny — {u.percent:.0f}% ({free} GB wolne)",
                                        f"  ⚠ {part.device} almost full — {u.percent:.0f}% ({free} GB free)"))
                except Exception:
                    pass

        except Exception:
            lines.append(_t(lang, "  Brak dostępu do danych dysku.", "  No disk data access."))

        lines.append(_t(lang,
                        "  Typowe przyczyny: Windows Update, antywirus, indeksowanie.",
                        "  Common causes: Windows Update, antivirus, search indexing."))
        lines.append(_followup("disk", lang))
        return lines

    # ── Battery / power drain ─────────────────────────────────────────────────

    def _resp_battery_drain(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
            bat = psutil.sensors_battery()
        except Exception:
            bat = None

        lines: list[str] = []

        if bat is None:
            lines.append(_t(lang,
                            f"{self.PREFIX} Brak baterii (PC stacjonarny).",
                            f"{self.PREFIX} No battery detected (desktop PC)."))
            lines.append(_t(lang,
                            "  Top pożeracze prądu = procesy z wysokim CPU:",
                            "  Top power consumers = high CPU processes:"))
        else:
            plugged = bat.power_plugged
            pct = bat.percent
            secs = bat.secsleft
            time_str = ""
            if secs and secs > 0:
                h, m = divmod(secs // 60, 60)
                time_str = f"  ~{h}h {m}min left" if lang == "en" else f"  ~{h}h {m}min zostało"
            status = _t(lang,
                        "ładowanie" if plugged else "na baterii",
                        "charging"  if plugged else "on battery")
            lines.append(_t(lang,
                            f"{self.PREFIX} Bateria: {pct:.0f}%  [{status}]{time_str}",
                            f"{self.PREFIX} Battery: {pct:.0f}%  [{status}]{time_str}"))
            lines.append(_t(lang,
                            "  Procesy najbardziej drenujące baterię (CPU = prąd):",
                            "  Processes draining battery most (CPU = power):"))

        try:
            import psutil
            raw = []
            for p in psutil.process_iter(["name", "cpu_percent"]):
                try:
                    raw.append(p)
                    if len(raw) >= 64:
                        break
                except Exception:
                    continue
            top = sorted(raw, key=lambda p: p.info.get("cpu_percent", 0) or 0, reverse=True)[:5]
            for i, p in enumerate(top, 1):
                nm = (p.info.get("name") or "?")[:28]
                c  = p.info.get("cpu_percent", 0) or 0
                if c > 0.1:
                    lines.append(f"  {i}. {nm:<28}  {c:.1f}% CPU")
        except Exception:
            pass

        lines.append(_t(lang,
                        "  💡 Plan zasilania Balanced = lepsza bateria niż High Performance.",
                        "  💡 Balanced power plan saves more battery than High Performance."))
        lines.append(_followup("process", lang))
        return lines

    # ── Performance change since last session ─────────────────────────────────

    def _resp_perf_change(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_stats_engine.query_api import query_api
            today = query_api.get_daily_summary(days=1)
            yest  = query_api.get_daily_summary(days=2)
        except Exception:
            today = None
            yest  = None

        lines = [_t(lang,
                    f"{self.PREFIX} Co się zmieniło w wydajności:",
                    f"{self.PREFIX} Performance change since last session:")]

        if not today or not yest:
            lines.append(_t(lang,
                            "  Za mało danych — potrzebuję minimum 2 dni historii.",
                            "  Not enough data — need at least 2 days of history."))
            return lines

        cpu_t = today.get("cpu_avg") or 0
        cpu_y = yest.get("cpu_avg")  or 0
        ram_t = today.get("ram_avg") or 0
        ram_y = yest.get("ram_avg")  or 0

        def _delta(val, ref, unit=""):
            d = val - ref
            sign = "+" if d >= 0 else ""
            tag = "⚠ " if abs(d) > 10 else ("↑ " if d > 3 else ("↓ " if d < -3 else "  "))
            return f"{tag}{sign}{d:.0f}{unit}"

        cpu_d = _delta(cpu_t, cpu_y, "%")
        ram_d = _delta(ram_t, ram_y, "%")

        # ── Pomysł 2: record for cross-response references ───────────────────
        from hck_gpt.memory.session_memory import session_memory
        session_memory.record_response_data("perf_change", {
            "cpu_today": cpu_t,
            "cpu_yest":  cpu_y,
            "ram_today": ram_t,
            "ram_yest":  ram_y,
        })

        lines.append(_t(lang,
                        f"  CPU:  dziś {cpu_t:.0f}%  vs  wczoraj {cpu_y:.0f}%   {cpu_d}",
                        f"  CPU:  today {cpu_t:.0f}%  vs  yesterday {cpu_y:.0f}%   {cpu_d}"))
        lines.append(_t(lang,
                        f"  RAM:  dziś {ram_t:.0f}%  vs  wczoraj {ram_y:.0f}%   {ram_d}",
                        f"  RAM:  today {ram_t:.0f}%  vs  yesterday {ram_y:.0f}%   {ram_d}"))

        if today.get("cpu_temp_avg") and yest.get("cpu_temp_avg"):
            ct = today["cpu_temp_avg"]
            cy = yest["cpu_temp_avg"]
            td = _delta(ct, cy, "°C")
            lines.append(_t(lang,
                            f"  Temp: dziś {ct:.0f}°C  vs  wczoraj {cy:.0f}°C   {td}",
                            f"  Temp: today {ct:.0f}°C  vs  yesterday {cy:.0f}°C   {td}"))

        # New heavy processes today (not in yesterday top)
        try:
            from datetime import datetime
            from hck_stats_engine.query_api import query_api as qa
            today_str = datetime.now().strftime("%Y-%m-%d")
            from datetime import timedelta
            yest_str  = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            t_procs = {r.get("process_name") for r in (qa.get_process_daily_breakdown(today_str, top_n=10) or [])}
            y_procs = {r.get("process_name") for r in (qa.get_process_daily_breakdown(yest_str,  top_n=10) or [])}
            new_today = t_procs - y_procs - {None}
            if new_today:
                names = ", ".join(list(new_today)[:3])
                lines.append(_t(lang,
                                f"  Nowe procesy dziś (nie było wczoraj): {names}",
                                f"  New processes today (not in yesterday): {names}"))
        except Exception:
            pass

        lines.append(_t(lang,
                        "  💬 Pełne wykresy: zakładka DayStats lub AllMonitor.",
                        "  💬 Full charts: DayStats or AllMonitor tab."))
        lines.append(_followup("session", lang))
        return lines

    # ── Fun / roast / personality ─────────────────────────────────────────────

    def _resp_fun_roast(self, r: ParseResult, lang: str = "pl") -> List[str]:
        text = (r.raw_text or "").lower()

        # Gather live context for personalization
        ram_pct      = 0
        chrome_count = 0
        discord_on   = False
        svchost_count = 0
        top_ram_name = "unknown"
        top_cpu_name = "unknown"
        startup_total = 0

        try:
            import psutil
            vm = psutil.virtual_memory()
            ram_pct = vm.percent
            names_cpu: list[tuple[str, float]] = []
            names_ram: list[tuple[str, float]] = []
            for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
                try:
                    nm = (p.info.get("name") or "").lower()
                    cp = p.info.get("cpu_percent") or 0
                    mp = p.info.get("memory_percent") or 0
                    if "chrome" in nm:
                        chrome_count += 1
                    if "discord" in nm:
                        discord_on = True
                    if "svchost" in nm:
                        svchost_count += 1
                    names_cpu.append((p.info.get("name") or "?", cp))
                    names_ram.append((p.info.get("name") or "?", mp))
                except Exception:
                    continue
            names_cpu.sort(key=lambda x: x[1], reverse=True)
            names_ram.sort(key=lambda x: x[1], reverse=True)
            if names_cpu:
                top_cpu_name = names_cpu[0][0]
            if names_ram:
                top_ram_name = names_ram[0][0]
        except Exception:
            pass

        try:
            import winreg
            seen: set[str] = set()
            for hive, path in [
                (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            name, _, _ = winreg.EnumValue(key, i)
                            seen.add(name.lower())
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    continue
            startup_total = len(seen)
        except Exception:
            pass

        P = self.PREFIX

        # ── Sub-type detection + witty response ───────────────────────────────

        if any(w in text for w in ["nienawidzi", "hate", "hates"]):
            if lang == "en":
                chrome_str = f" and {chrome_count} Chrome instances" if chrome_count > 2 else ""
                startup_str = f" and {startup_total} startup programs" if startup_total > 5 else ""
                return [
                    f"{P} Because you have RAM at {ram_pct:.0f}%{chrome_str}{startup_str}.",
                    "  It doesn't hate you — it's just exhausted.",
                    f"  The biggest culprit right now: {top_cpu_name}.",
                ]
            chrome_str = f" i {chrome_count} instancji Chrome" if chrome_count > 2 else ""
            startup_str = f" i {startup_total} programów startowych" if startup_total > 5 else ""
            return [
                f"{P} Bo masz RAM na {ram_pct:.0f}%{chrome_str}{startup_str}.",
                "  On Cię nie nienawidzi — po prostu jest wykończony.",
                f"  Największy winowajca teraz: {top_cpu_name}.",
            ]

        if any(w in text for w in ["głupi", "dumb", "stupid"]):
            chrome_str = f"Chrome z {chrome_count} procesami" if chrome_count > 1 else "sporo rzeczy"
            if lang == "en":
                return [
                    f"{P} Not dumb — just incredibly patient.",
                    f"  It's been running {chrome_str} for hours without complaining.",
                    f"  Current RAM: {ram_pct:.0f}%. That's the real test of endurance.",
                ]
            return [
                f"{P} Nie jest głupi — jest niesamowicie cierpliwy.",
                f"  Od godzin dźwiga {chrome_str} i ani słowa skargi.",
                f"  RAM teraz: {ram_pct:.0f}%. To dopiero wytrzymałość.",
            ]

        if any(w in text for w in ["leni", "lazy", "laziest"]):
            # Find the process with lowest CPU but most RAM (the "lazy" one)
            lazy_name = "unknown"
            try:
                import psutil
                candidates = []
                for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
                    try:
                        mp = p.info.get("memory_percent") or 0
                        cp = p.info.get("cpu_percent") or 0
                        nm = p.info.get("name") or ""
                        if mp > 0.5 and cp < 1.0 and nm.lower() not in ("system idle process", ""):
                            candidates.append((nm, mp, cp))
                    except Exception:
                        continue
                if candidates:
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    lazy_name = candidates[0][0]
                    lazy_ram  = candidates[0][1]
            except Exception:
                lazy_ram = 0
            ram_str = f" ({lazy_ram:.1f}% RAM)" if lazy_ram else ""
            if lang == "en":
                return [
                    f"{P} The laziest award goes to: {lazy_name}{ram_str}",
                    "  High RAM, near-zero CPU. It's just sitting there.",
                    "  Typical suspect: browser, Electron app, or communication tool.",
                ]
            return [
                f"{P} Nagroda dla największego lenia: {lazy_name}{ram_str}",
                "  Dużo RAMu, prawie zero CPU. Po prostu siedzi i zajmuje miejsce.",
                "  Typowy podejrzany: przeglądarka, aplikacja Electron lub komunikator.",
            ]

        if any(w in text for w in ["chrome", "chrom"]):
            if lang == "en":
                return [
                    f"{P} Chrome currently has {chrome_count} process{'es' if chrome_count != 1 else ''} running.",
                    "  Each tab = 1 separate process. That's by design (isolation).",
                    "  Downside: Chrome eats RAM like it has an infinite supply.",
                    f"  Top RAM hog right now: {top_ram_name}.",
                ]
            return [
                f"{P} Chrome ma teraz {chrome_count} {'procesów' if chrome_count > 1 else 'proces'} aktywnych.",
                "  Każda zakładka = osobny proces — to jego styl życia (izolacja).",
                "  Minus: Chrome żre RAM jakby go miał za darmo.",
                f"  Największy pożeracz RAM teraz: {top_ram_name}.",
            ]

        if any(w in text for w in ["discord", "stalker"]):
            disc_str = _t(lang,
                          "Discord jest uruchomiony w tle." if discord_on else "Discord nie jest teraz aktywny.",
                          "Discord is running in the background." if discord_on else "Discord is not running right now.")
            if lang == "en":
                return [
                    f"{P} Discord runs in background because it wants to be 'always ready'.",
                    f"  {disc_str}",
                    "  It uses GPU for overlay + RAM for the Electron runtime.",
                    "  Fix: Settings → Windows Settings → disable 'Launch on startup'.",
                ]
            return [
                f"{P} Discord działa w tle bo chce być 'zawsze gotowy'.",
                f"  {disc_str}",
                "  Zjada GPU przez overlay i RAM przez silnik Electron.",
                "  Fix: Ustawienia Discord → Windows → wyłącz 'Uruchamiaj przy starcie'.",
            ]

        if any(w in text for w in ["svchost", "szpieg", "spy"]):
            if lang == "en":
                return [
                    f"{P} svchost.exe — spy? Not exactly. Suspicious? Sometimes.",
                    f"  Right now there are {svchost_count} svchost instances running.",
                    "  Each one hosts a group of Windows services (networking, updates, etc).",
                    "  If one spikes CPU at night — probably Windows Update doing its thing.",
                ]
            return [
                f"{P} svchost.exe — szpieg? Niekoniecznie. Podejrzany? Czasem.",
                f"  Teraz działa {svchost_count} instancji svchost.",
                "  Każda hostuje grupę usług Windows (sieć, aktualizacje itp.).",
                "  Jeśli skacze CPU nocą — to prawdopodobnie Windows Update robi swoje.",
            ]

        if any(w in text for w in ["kac", "hangover", "ładuje się wolno", "wolno ładuje"]):
            if lang == "en":
                return [
                    f"{P} Loading slowly like it has a hangover? Classic symptom.",
                    f"  Startup programs: {startup_total}. That's {startup_total} things fighting for CPU on boot.",
                    f"  Top CPU hog right now: {top_cpu_name}.",
                    "  Cure: disable the heavy hitters  [→ Startup Manager]",
                ]
            return [
                f"{P} Ładuje się wolno jakby miało kaca? Klasyczny objaw.",
                f"  Programów startowych: {startup_total}. To {startup_total} rzeczy walczących o CPU podczas uruchamiania.",
                f"  Największy pożeracz CPU teraz: {top_cpu_name}.",
                "  Lekarstwo: wyłącz ciężkich kandydatów  [→ Startup Manager]",
            ]

        if any(w in text for w in ["timeout", "time-out"]):
            if lang == "en":
                return [
                    f"{P} Your PC could use a timeout, honestly.",
                    f"  RAM is at {ram_pct:.0f}%. Top offender: {top_cpu_name}.",
                    "  Closest thing to a timeout: close everything + restart.",
                    "  Or: Optimization tab → TURBO BOOST for a quick reset.",
                ]
            return [
                f"{P} Twój PC naprawdę mógłby dostać timeout.",
                f"  RAM na {ram_pct:.0f}%. Winowajca: {top_cpu_name}.",
                "  Najbliższe timeout'owi: zamknij wszystko + restart.",
                "  Albo: zakładka Optimization → TURBO BOOST = szybki reset systemu.",
            ]

        if any(w in text for w in ["złodziej", "steal", "steals", "most ram"]):
            if lang == "en":
                return [
                    f"{P} Biggest RAM thief right now: {top_ram_name}.",
                    f"  Total RAM usage: {ram_pct:.0f}%.",
                    "  Type 'ram why high' for a full breakdown.",
                ]
            return [
                f"{P} Największy złodziej RAM teraz: {top_ram_name}.",
                f"  Łączne zużycie RAM: {ram_pct:.0f}%.",
                "  Wpisz 'dlaczego ram wysoki' po pełną analizę.",
            ]

        # ── Default fun response ───────────────────────────────────────────────
        if lang == "en":
            return [
                f"{P} Your PC is doing its best. Probably.",
                f"  RAM: {ram_pct:.0f}%  |  Top process: {top_cpu_name}",
                "  Could be worse. Could also be better.",
                "  Type 'health check' if you want real answers.",
            ]
        return [
            f"{P} Twój PC robi co może. Prawdopodobnie.",
            f"  RAM: {ram_pct:.0f}%  |  Top proces: {top_cpu_name}",
            "  Mogło być gorzej. Ale mogło być i lepiej.",
            "  Wpisz 'health check' jeśli chcesz prawdziwych odpowiedzi.",
        ]

    # ── Session compare ───────────────────────────────────────────────────────

    def _resp_session_compare(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_stats_engine.query_api import query_api
            today = query_api.get_daily_summary(days=1)
            yest  = query_api.get_daily_summary(days=2)
        except Exception:
            today = None
            yest  = None

        if not today and not yest:
            if lang == "en":
                return [
                    f"{self.PREFIX} Not enough history yet for comparison.",
                    "  The stats engine needs at least 2 days of data.",
                    "  Check back tomorrow — I'll have something to compare.",
                ]
            return [
                f"{self.PREFIX} Za mało danych historycznych do porównania.",
                "  Silnik statystyk potrzebuje minimum 2 dni danych.",
                "  Wróć jutro — będę miał co porównać.",
            ]

        lines = [_t(lang,
                    f"{self.PREFIX} Porównanie sesji — wczoraj vs dziś:",
                    f"{self.PREFIX} Session comparison — yesterday vs today:")]

        def _row(label_pl, label_en, val_today, val_yest, unit=""):
            label = label_en if lang == "en" else label_pl
            t = f"{val_today:.0f}{unit}" if val_today is not None else "—"
            y = f"{val_yest:.0f}{unit}" if val_yest is not None else "—"
            diff = ""
            if val_today is not None and val_yest is not None:
                delta = val_today - val_yest
                diff = f"  ({'+' if delta >= 0 else ''}{delta:.0f}{unit})"
            lines.append(f"  {label:<18} dziś: {t:<8} wczoraj: {y}{diff}"
                         if lang == "pl" else
                         f"  {label:<18} today: {t:<8} yest: {y}{diff}")

        if today and yest:
            _row("CPU średnia", "CPU avg",
                 today.get("cpu_avg"), yest.get("cpu_avg"), "%")
            _row("CPU max", "CPU peak",
                 today.get("cpu_max"), yest.get("cpu_max"), "%")
            _row("RAM średnia", "RAM avg",
                 today.get("ram_avg"), yest.get("ram_avg"), "%")
            if today.get("cpu_temp_avg") or yest.get("cpu_temp_avg"):
                _row("CPU temp avg", "CPU temp avg",
                     today.get("cpu_temp_avg"), yest.get("cpu_temp_avg"), "°C")

            # ── Pomysł 2: record for cross-response references ────────────────
            from hck_gpt.memory.session_memory import session_memory
            session_memory.record_response_data("session_compare", {
                "cpu_today": today.get("cpu_avg"),
                "cpu_yest":  yest.get("cpu_avg"),
                "ram_today": today.get("ram_avg"),
                "ram_yest":  yest.get("ram_avg"),
            })

        lines.append(_t(lang,
                        "  💬 Pełne wykresy: zakładka AllMonitor lub DayStats.",
                        "  💬 Full charts: AllMonitor or DayStats tab."))
        lines.append(_followup("session", lang))
        return lines

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _live_hw_fallback(self, lang: str = "pl") -> List[str]:
        """Report basic hw via psutil when DB is empty."""
        try:
            import psutil, platform
            cores_p = psutil.cpu_count(logical=False)
            cores_l = psutil.cpu_count(logical=True)
            freq    = psutil.cpu_freq()
            ram_gb  = round(psutil.virtual_memory().total / 1_073_741_824, 1)
            boost   = round(freq.max / 1000, 1) if freq and freq.max else "?"
            if lang == "en":
                return [
                    f"{self.PREFIX} Hardware (live — CPU model unknown, scan running):",
                    f"  CPU:  {cores_p} cores  /  {cores_l} threads  /  boost {boost} GHz",
                    f"  RAM:  {ram_gb} GB",
                    f"  OS:   Windows {platform.release()}",
                ]
            return [
                f"{self.PREFIX} Sprzęt (live, model CPU nieznany — skanowanie w toku):",
                f"  CPU:  {cores_p} rdzeni  /  {cores_l} wątków  /  boost {boost} GHz",
                f"  RAM:  {ram_gb} GB",
                f"  OS:   Windows {platform.release()}",
            ]
        except Exception:
            return [_t(lang,
                       f"{self.PREFIX} Brak danych — skanowanie sprzętu w toku.",
                       f"{self.PREFIX} No data yet — hardware scan running.")]


    # ── Explain proactive message ─────────────────────────────────────────────

    def _resp_explain_proactive(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Explain the most recently pushed proactive / teaser message.
        Triggered when user asks: 'what does that mean?', 'what 3/7?',
        'explain that', 'co to znaczy?', etc.
        """
        from hck_gpt.memory.session_memory import session_memory
        last = session_memory.get_last_proactive()

        if not last or not last.get("text"):
            return [_t(lang,
                f"{self.PREFIX} Nie mam żadnej ostatniej wiadomości do wyjaśnienia. "
                "Zapytaj np. 'zdrowie systemu' lub 'stats'.",
                f"{self.PREFIX} I don't have a recent message to explain. "
                "Try asking 'health check' or 'stats'.")]

        text = last.get("text", "")
        ctx  = last.get("context", {})
        ptype = ctx.get("type", "")

        lines = [_t(lang,
            f"{self.PREFIX} Wyjaśniam ostatni komunikat:",
            f"{self.PREFIX} Here's what that message meant:")]
        lines.append(f"  » {text}")
        lines.append("")

        if ptype == "teaser":
            proc = ctx.get("process", "?")
            freq = ctx.get("freq",    "?")
            cpu  = ctx.get("cpu",     None)
            if lang == "en":
                lines.append(f"  '{proc}' was active on {freq} out of the last 7 days.")
                lines.append(f"  That makes it one of your regular tools — I track patterns over time.")
                if cpu:
                    lines.append(f"  When it runs, it averages {cpu:.0f}% CPU load.")
            else:
                lines.append(f"  '{proc}' był aktywny przez {freq} z ostatnich 7 dni.")
                lines.append(f"  Oznacza to, że to regularny element Twojego zestawu.")
                if cpu:
                    lines.append(f"  Średnie obciążenie CPU gdy działa: {cpu:.0f}%.")

        elif ptype in ("cpu_high", "cpu_crit"):
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  Your CPU was running at {val}% — that's sustained high load.")
                lines.append(f"  Type 'top processes' to see which app caused it.")
            else:
                lines.append(f"  CPU pracował na {val}% — to utrzymane wysokie obciążenie.")
                lines.append(f"  Wpisz 'top procesy' by znaleźć winowajcę.")

        elif ptype in ("ram_high", "ram_crit"):
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  RAM was at {val}% — memory was getting tight.")
                lines.append(f"  Ask me 'why is RAM high' for a detailed breakdown.")
            else:
                lines.append(f"  RAM był na {val}% — mało wolnej pamięci.")
                lines.append(f"  Zapytaj 'dlaczego ram wysoki' po szczegółową analizę.")

        elif ptype == "throttle":
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  Your CPU was throttled — running at only {val}% of max power.")
                lines.append(f"  This is usually caused by heat. Check 'temperatures'.")
            else:
                lines.append(f"  CPU był dławiony — pracował na zaledwie {val}% mocy maksymalnej.")
                lines.append(f"  Zwykle winne jest przegrzanie. Sprawdź 'temperatury'.")

        elif ptype == "disk_low":
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  Your disk had only {val} GB of free space.")
                lines.append(f"  Clean up TEMP files via the Optimization tab.")
            else:
                lines.append(f"  Na dysku zostało tylko {val} GB wolnego miejsca.")
                lines.append(f"  Wyczyść pliki TEMP przez zakładkę Optimization.")

        elif ptype == "long_session":
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  PC has been running for {val} hours without a restart.")
                lines.append(f"  Memory leaks can accumulate over long sessions — consider restarting tonight.")
            else:
                lines.append(f"  PC działa od {val} godzin bez restartu.")
                lines.append(f"  Przy długich sesjach mogą gromadzić się wycieki pamięci.")

        elif ptype == "gpu_temp_spike":
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  GPU temperature hit {val}°C — that's a sudden heat spike.")
                lines.append(f"  Check cooling, airflow, or lower your GPU load settings.")
            else:
                lines.append(f"  Temperatura GPU osiągnęła {val}°C — ostry skok ciepła.")
                lines.append(f"  Sprawdź chłodzenie, wentylację lub obniż ustawienia GPU.")

        elif ptype in ("all_clear",):
            if lang == "en":
                lines.append(f"  That was a routine status check — everything was healthy at that moment.")
            else:
                lines.append(f"  To był rutynowy przegląd — wszystko działało prawidłowo w tym momencie.")

        elif ptype == "greeting":
            if lang == "en":
                lines.append(f"  That was my greeting — a quick summary of your PC's state when you opened the app.")
            else:
                lines.append(f"  To było powitanie — szybki przegląd stanu PC przy otwarciu aplikacji.")

        else:
            # Generic fallback
            if lang == "en":
                lines.append(f"  That was a proactive system notification. Ask me 'health check' or 'stats' for more.")
            else:
                lines.append(f"  To był proaktywny komunikat o stanie systemu. Zapytaj 'health' lub 'stats' po więcej.")

        lines.append(_followup("health", lang))
        return lines


    # ── Browser cache / slow browser ─────────────────────────────────────────

    def _resp_browser_cache(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        try:
            import psutil
            procs = []
            BROWSERS = {"chrome.exe", "firefox.exe", "msedge.exe",
                        "brave.exe", "opera.exe", "vivaldi.exe"}
            total_mb = 0.0
            counts: dict = {}
            for proc in psutil.process_iter(["name", "memory_info"]):
                try:
                    nm = (proc.info["name"] or "").lower()
                    if nm in BROWSERS:
                        mb = (proc.info["memory_info"].rss / 1_048_576)
                        total_mb += mb
                        counts[nm] = counts.get(nm, 0) + 1
                except Exception:
                    pass
            browser_lines = []
            for bname, cnt in sorted(counts.items(), key=lambda x: -x[1]):
                friendly = bname.replace(".exe", "").capitalize()
                browser_lines.append(f"  {friendly}: {cnt} tab{'s' if cnt != 1 else ''}")
            if not counts:
                if lang == "en":
                    return [f"{P} No browser is currently running.",
                            "  Cache only matters while the browser is open.",
                            _followup("perf", lang)]
                return [f"{P} Żadna przeglądarka nie działa teraz.",
                        "  Cache obciąża tylko przy otwartej przeglądarce.",
                        _followup("perf", lang)]
        except Exception:
            total_mb = 0.0
            browser_lines = []

        # Severity band
        if total_mb > 2000:
            sev_en = f"HIGH — {total_mb:.0f} MB total across all browser processes."
            sev_pl = f"WYSOKI — {total_mb:.0f} MB łącznie dla wszystkich procesów przeglądarki."
            tip_en = "Consider closing unused tabs, disabling heavy extensions."
            tip_pl = "Zamknij nieużywane zakładki, wyłącz ciężkie rozszerzenia."
        elif total_mb > 800:
            sev_en = f"MODERATE — {total_mb:.0f} MB in use."
            sev_pl = f"UMIARKOWANY — {total_mb:.0f} MB w użyciu."
            tip_en = "Cache is normal for this size. Close tabs you don't need."
            tip_pl = "Cache OK przy tym rozmiarze. Zamknij zakładki których nie używasz."
        else:
            sev_en = f"LOW — {total_mb:.0f} MB, nothing to worry about."
            sev_pl = f"NISKI — {total_mb:.0f} MB, bez obaw."
            tip_en = "Browser memory is healthy. Cache isn't slowing you down."
            tip_pl = "Pamięć przeglądarki OK. Cache nie spowalnia komputera."

        if lang == "en":
            lines = [f"{P} Browser memory footprint — {sev_en}"]
            lines += browser_lines
            lines.append(f"  Tip: {tip_en}")
            lines.append("  To clear cache: Ctrl+Shift+Del in any browser.")
        else:
            lines = [f"{P} Pamięć przeglądarki — {sev_pl}"]
            lines += browser_lines
            lines.append(f"  Wskazówka: {tip_pl}")
            lines.append("  Wyczyść cache: Ctrl+Shift+Del w dowolnej przeglądarce.")
        lines.append(_followup("perf", lang))
        return lines

    # ── RAM comparison (session + persistent history) ─────────────────────────

    def _resp_ram_compare(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        try:
            from hck_gpt.data.live_sensors import snapshot as _ls_snap
            ls = _ls_snap()
        except Exception:
            ls = {}

        try:
            import psutil
            vm      = psutil.virtual_memory()
            cur_pct = vm.percent
            cur_mb  = vm.used / 1_048_576
            tot_mb  = vm.total / 1_048_576
        except Exception:
            cur_pct = -1.0
            cur_mb  = tot_mb = 0.0

        # Pull multi-day history from metrics_store
        try:
            from hck_gpt.data.metrics_store import metrics_store as _ms
            days = _ms.daily_summary(days=7)
        except Exception:
            days = []

        # Session extremes from live_sensors historical baselines
        sh       = ls.get("session_hist", {})
        ram_hist = sh.get("ram_pct", [])
        sess_min = ram_hist[0] if len(ram_hist) >= 2 else None
        sess_max = ram_hist[1] if len(ram_hist) >= 2 else None
        hist_avg = ls.get("_hist_ram_avg_7d", None)

        if lang == "en":
            lines = [f"{P} RAM comparison:"]
            if cur_pct >= 0:
                lines.append(f"  Now:      {cur_pct:.0f}%  ({cur_mb:.0f} MB / {tot_mb:.0f} MB)")
            if sess_min is not None:
                lines.append(f"  Session:  Min {sess_min:.0f}%  Max {sess_max:.0f}%")
            if hist_avg is not None:
                delta = cur_pct - hist_avg
                sign  = "+" if delta >= 0 else ""
                lines.append(f"  7-day avg: {hist_avg:.0f}%  →  today is {sign}{delta:.0f}% vs baseline")
            if days:
                lines.append("  Daily breakdown (last 7 days):")
                for d in days[:5]:
                    lines.append(f"    {d['date_str']}  avg {d['ram_avg']:.0f}%  max {d['ram_max']:.0f}%")
            else:
                lines.append("  Multi-day history builds up after a few sessions.")
        else:
            lines = [f"{P} Porównanie RAM:"]
            if cur_pct >= 0:
                lines.append(f"  Teraz:     {cur_pct:.0f}%  ({cur_mb:.0f} MB / {tot_mb:.0f} MB)")
            if sess_min is not None:
                lines.append(f"  Sesja:     Min {sess_min:.0f}%  Max {sess_max:.0f}%")
            if hist_avg is not None:
                delta = cur_pct - hist_avg
                sign  = "+" if delta >= 0 else ""
                lines.append(f"  Śr. 7 dni: {hist_avg:.0f}%  →  dziś {sign}{delta:.0f}% vs bazowy")
            if days:
                lines.append("  Dane dzienne (ostatnie 7 dni):")
                for d in days[:5]:
                    lines.append(f"    {d['date_str']}  śr. {d['ram_avg']:.0f}%  max {d['ram_max']:.0f}%")
            else:
                lines.append("  Historia wielodniowa narośnie po kilku sesjach.")
        lines.append(_followup("perf", lang))
        return lines

    # ── Swap / virtual memory / pagefile analysis ─────────────────────────────

    def _resp_swap_analysis(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        try:
            import psutil
            sw = psutil.swap_memory()
            swap_pct  = sw.percent
            swap_used = sw.used  / 1_073_741_824   # GB
            swap_tot  = sw.total / 1_073_741_824    # GB
            vm        = psutil.virtual_memory()

            # Top processes by virtual_memory_size (includes swap)
            top: list = []
            for proc in psutil.process_iter(["name", "memory_info"]):
                try:
                    mi = proc.info["memory_info"]
                    vms_mb = mi.vms / 1_048_576
                    rss_mb = mi.rss / 1_048_576
                    # Likely on swap if VMS >> RSS
                    swap_est = max(0.0, vms_mb - rss_mb)
                    if swap_est > 50:
                        top.append((proc.info["name"], swap_est))
                except Exception:
                    pass
            top.sort(key=lambda x: -x[1])
            top = top[:5]
        except Exception:
            swap_pct = -1.0
            swap_used = swap_tot = 0.0
            top = []
            vm = None

        if swap_pct < 0:
            msg = _t(lang, "Nie mogę odczytać danych swap.", "Can't read swap data.")
            return [f"{P} {msg}", _followup("perf", lang)]

        if swap_tot < 0.1:
            if lang == "en":
                return [f"{P} No pagefile / swap configured on this system.",
                        "  Windows is managing memory entirely in physical RAM.",
                        _followup("perf", lang)]
            return [f"{P} Brak pliku wymiany / swap na tym systemie.",
                    "  Windows zarządza pamięcią wyłącznie w fizycznym RAM.",
                    _followup("perf", lang)]

        sev_en = "HIGH — swap heavily used, expect slowdowns" if swap_pct > 60 else \
                 "MODERATE" if swap_pct > 25 else "LOW — healthy"
        sev_pl = "WYSOKI — swap mocno zajęty, spodziewaj się spowolnienia" if swap_pct > 60 else \
                 "UMIARKOWANY" if swap_pct > 25 else "NISKI — OK"

        if lang == "en":
            lines = [f"{P} Swap / Pagefile: {swap_pct:.0f}% used  ({swap_used:.1f} GB / {swap_tot:.1f} GB)  → {sev_en}"]
            lines.append(f"  Physical RAM: {vm.percent:.0f}% full  ({vm.used/1e9:.1f} / {vm.total/1e9:.1f} GB)")
            if top:
                lines.append("  Processes with largest virtual footprint (likely swap users):")
                for name, mb in top:
                    lines.append(f"    • {name[:22]:<22}  ~{mb:.0f} MB on swap")
            if swap_pct > 60:
                lines.append("  Fix: Close background apps, add more RAM, or increase pagefile size.")
            else:
                lines.append("  Swap is normal — Windows uses it as a buffer even when RAM is available.")
        else:
            lines = [f"{P} Swap / Plik wymiany: {swap_pct:.0f}% zajęty  ({swap_used:.1f} GB / {swap_tot:.1f} GB)  → {sev_pl}"]
            lines.append(f"  Fizyczny RAM: {vm.percent:.0f}% pełny  ({vm.used/1e9:.1f} / {vm.total/1e9:.1f} GB)")
            if top:
                lines.append("  Procesy z największym wirtualnym śladem (prawdopodobni użytkownicy swap):")
                for name, mb in top:
                    lines.append(f"    • {name[:22]:<22}  ~{mb:.0f} MB na swap")
            if swap_pct > 60:
                lines.append("  Rozwiązanie: zamknij programy w tle, dodaj RAM lub zwiększ rozmiar pliku wymiany.")
            else:
                lines.append("  Swap normalny — Windows używa go jako bufora nawet gdy RAM jest dostępny.")
        lines.append(_followup("perf", lang))
        return lines

    # ── Network usage by process (12th intent) ───────────────────────────────

    def _resp_network_usage(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        net_rows: list = []
        total_sent_mb = total_recv_mb = 0.0
        try:
            import psutil, time as _t

            # Per-process net I/O: delta over 1 s window
            # psutil.net_connections gives connections but not per-process bytes;
            # use net_io_counters per-NIC for total, and process connections for top-N
            before = psutil.net_io_counters()
            _t.sleep(1.0)
            after  = psutil.net_io_counters()
            recv_mb = (after.bytes_recv - before.bytes_recv) / 1_048_576
            sent_mb = (after.bytes_sent - before.bytes_sent) / 1_048_576
            total_sent_mb = sent_mb
            total_recv_mb = recv_mb

            # Identify top processes by open connections count
            conn_count: dict = {}
            try:
                for c in psutil.net_connections(kind="inet"):
                    if c.pid and c.status == "ESTABLISHED":
                        try:
                            pname = psutil.Process(c.pid).name()
                        except Exception:
                            pname = f"PID {c.pid}"
                        conn_count[pname] = conn_count.get(pname, 0) + 1
            except (psutil.AccessDenied, Exception):
                pass

            top_conns = sorted(conn_count.items(), key=lambda x: -x[1])[:6]

        except Exception:
            top_conns = []
            recv_mb = sent_mb = 0.0

        # Live sensors for extra context
        try:
            from hck_gpt.data.live_sensors import snapshot as _ls_snap
            cpu_load = _ls_snap().get("cpu_load", -1.0)
        except Exception:
            cpu_load = -1.0

        if lang == "en":
            lines = [f"{P} Network activity — 1-second snapshot:"]
            lines.append(f"  Download: {total_recv_mb:.2f} MB/s   Upload: {total_sent_mb:.2f} MB/s")
            if top_conns:
                lines.append("  Processes with most active connections:")
                for pname, cnt in top_conns:
                    lines.append(f"    • {pname[:28]:<28}  {cnt} connection{'s' if cnt != 1 else ''}")
            else:
                lines.append("  No established connections detected right now.")
            if total_recv_mb + total_sent_mb > 5:
                lines.append("  Tip: High background traffic? Check Windows Update, cloud sync, or antivirus.")
            elif total_recv_mb + total_sent_mb < 0.1:
                lines.append("  Network is nearly idle.")
            if cpu_load > 60:
                lines.append(f"  Note: CPU is at {cpu_load:.0f}% — network processing may be contributing.")
        else:
            lines = [f"{P} Aktywność sieciowa — pomiar 1-sekundowy:"]
            lines.append(f"  Pobieranie: {total_recv_mb:.2f} MB/s   Wysyłanie: {total_sent_mb:.2f} MB/s")
            if top_conns:
                lines.append("  Procesy z największą liczbą aktywnych połączeń:")
                for pname, cnt in top_conns:
                    lines.append(f"    • {pname[:28]:<28}  {cnt} połączen{'ia' if cnt != 1 else 'ie'}")
            else:
                lines.append("  Brak aktywnych połączeń w tej chwili.")
            if total_recv_mb + total_sent_mb > 5:
                lines.append("  Wskazówka: Wysoki ruch w tle? Sprawdź Windows Update, sync chmury lub antywirusa.")
            elif total_recv_mb + total_sent_mb < 0.1:
                lines.append("  Sieć prawie bezczynna.")
            if cpu_load > 60:
                lines.append(f"  Uwaga: CPU jest na {cpu_load:.0f}% — obsługa sieci może dokładać swoje.")
        lines.append(_followup("perf", lang))
        return lines

    # ── USB / external drive transfer monitoring ──────────────────────────────

    def _resp_usb_transfer(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        try:
            import psutil
            io1 = psutil.disk_io_counters(perdisk=True)
            import time as _t
            _t.sleep(0.5)
            io2 = psutil.disk_io_counters(perdisk=True)

            transfer_info: list = []
            for disk_name in io2:
                a = io1.get(disk_name)
                b = io2.get(disk_name)
                if not a or not b:
                    continue
                r_mb = (b.read_bytes  - a.read_bytes)  / 1_048_576 / 0.5
                w_mb = (b.write_bytes - a.write_bytes) / 1_048_576 / 0.5
                if r_mb + w_mb > 0.5:    # only show active disks
                    transfer_info.append((disk_name, r_mb, w_mb))
            transfer_info.sort(key=lambda x: -(x[1] + x[2]))

            # CPU during transfer window
            cpu_load = psutil.cpu_percent(interval=None)

            # Partitions to map drive letters to disk names
            parts = {p.device.rstrip("\\"): p for p in psutil.disk_partitions()}
        except Exception:
            transfer_info = []
            cpu_load = -1.0
            parts = {}

        # Live sensors for context
        try:
            from hck_gpt.data.live_sensors import snapshot as _ls_snap
            ls = _ls_snap()
            cpu_load = ls.get("cpu_load", cpu_load)
        except Exception:
            pass

        if lang == "en":
            lines = [f"{P} External / USB transfer — live I/O snapshot:"]
            if not transfer_info:
                lines.append("  No active disk I/O detected at the moment.")
                lines.append("  If your transfer just started, ask me again in a few seconds.")
            else:
                for dname, r_mb, w_mb in transfer_info[:4]:
                    arrow = f"R: {r_mb:.1f} MB/s" if r_mb > w_mb else f"W: {w_mb:.1f} MB/s"
                    lines.append(f"  {dname:<12}  {arrow}  (R {r_mb:.1f} + W {w_mb:.1f} MB/s)")
            if cpu_load >= 0:
                cpu_note = "minimal" if cpu_load < 15 else "moderate" if cpu_load < 40 else "high"
                lines.append(f"  CPU during transfer: {cpu_load:.0f}%  — {cpu_note} overhead.")
                if cpu_load < 15:
                    lines.append("  File transfers are very CPU-light on SSDs — storage controller handles it.")
                elif cpu_load > 50:
                    lines.append("  High CPU during transfer can happen with encryption, compression, or virus scanning.")
            lines.append("  Tip: Transfer speed depends on USB version — USB 3.x is ~400 MB/s, USB 2.0 ~40 MB/s.")
        else:
            lines = [f"{P} Transfer zewnętrzny / USB — szybki odczyt I/O:"]
            if not transfer_info:
                lines.append("  Nie wykryto aktywnego transferu w tej chwili.")
                lines.append("  Jeśli transfer właśnie się zaczął, zapytaj ponownie za chwilę.")
            else:
                for dname, r_mb, w_mb in transfer_info[:4]:
                    arrow = f"R: {r_mb:.1f} MB/s" if r_mb > w_mb else f"Z: {w_mb:.1f} MB/s"
                    lines.append(f"  {dname:<12}  {arrow}  (R {r_mb:.1f} + Z {w_mb:.1f} MB/s)")
            if cpu_load >= 0:
                cpu_note = "minimalny" if cpu_load < 15 else "umiarkowany" if cpu_load < 40 else "wysoki"
                lines.append(f"  CPU podczas transferu: {cpu_load:.0f}%  — obciążenie {cpu_note}.")
                if cpu_load < 15:
                    lines.append("  Transfer plików to małe obciążenie CPU dla SSD — kontroler pamięci robi robotę.")
                elif cpu_load > 50:
                    lines.append("  Wysokie CPU podczas transferu może być efektem szyfrowania, kompresji lub antywirusa.")
            lines.append("  Tip: Prędkość zależy od USB — USB 3.x ~400 MB/s, USB 2.0 ~40 MB/s.")
        lines.append(_followup("perf", lang))
        return lines

    # ─────────────────────────────────────────────────────────────────────────
    # MEGA FEATURE: Structured fallback — no AI-slop when data is unavailable
    # ─────────────────────────────────────────────────────────────────────────

    def _no_data(self, intent: str, lang: str, what_missing: str = "") -> List[str]:
        """
        Return a structured 'data unavailable' message instead of hallucinating.
        Called by any handler when critical data is missing.
        """
        generic = _t(lang, "brak danych", "data unavailable")
        detail  = f"  ({what_missing})" if what_missing else ""
        if lang == "en":
            return [
                f"{self.PREFIX} ⚠ Not enough data for a reliable answer.",
                f"  I'd rather tell you honestly than guess.{detail}",
                "  What would help: use PC Workman for a few more days so the stats engine builds history.",
                f"  Alternative: try 'health check' or 'stats' for what I do have.",
            ]
        return [
            f"{self.PREFIX} ⚠ Za mało danych żeby udzielić pewnej odpowiedzi.",
            f"  Wolę powiedzieć szczerze niż zgadywać.{detail}",
            "  Co pomoże: uruchom PC Workman przez kilka dni — silnik statystyk buduje historię.",
            f"  Alternatywa: spróbuj 'zdrowie systemu' lub 'stats' — to mam na pewno.",
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # MEGA FEATURE: Time-Travel helper — compare current to N-day history
    # ─────────────────────────────────────────────────────────────────────────

    # Map from user-facing metric alias → daily_summary column name
    _METRIC_COL_MAP: dict[str, str] = {
        "cpu_temp":  "cpu_temp_avg",
        "gpu_temp":  "gpu_temp_avg",
        "cpu_load":  "cpu_avg",
        "gpu_load":  "gpu_avg",
        "ram_pct":   "ram_avg",
    }

    def _get_historical_comparison(
        self, metric: str, days: int, lang: str
    ) -> Optional[str]:
        """
        Compare current metric value to N-day historical average.
        metric: 'cpu_temp', 'gpu_temp', 'cpu_load', 'ram_pct', 'gpu_load'
        Returns a formatted comparison string or None if data missing.
        """
        try:
            from hck_gpt.data.metrics_store import metrics_store

            # Map metric alias → actual daily_summary column name
            col = self._METRIC_COL_MAP.get(metric, metric)

            summary = metrics_store.daily_summary(days=days)
            if not summary:
                return None

            # Average of historical daily averages (ignore -1 / None entries)
            valid = [
                float(row[col]) for row in summary
                if row.get(col) is not None and float(row.get(col, -1)) > 0
            ]
            if len(valid) < 2:
                return None
            hist_avg = sum(valid) / len(valid)
            hist_max = max(valid)
            hist_min = min(valid)

            # Get current live value
            from hck_gpt.data.live_sensors import snapshot as _ls_snap
            live    = _ls_snap()
            current = live.get(metric)
            if current is None or current <= 0:
                try:
                    import psutil
                    if metric == "cpu_load":
                        current = psutil.cpu_percent(interval=None)
                    elif metric == "ram_pct":
                        current = psutil.virtual_memory().percent
                except Exception:
                    current = None

            if current is None:
                return None

            diff  = float(current) - hist_avg
            arrow = "↑" if diff > 5 else ("↓" if diff < -5 else "→")
            sign  = "+" if diff >= 0 else ""
            unit  = "°C" if "temp" in metric else "%"

            if lang == "en":
                return (
                    f"  Now: {current:.0f}{unit}  vs  {days}-day avg: {hist_avg:.0f}{unit}  "
                    f"{arrow} ({sign}{diff:.0f}{unit})  |  range: {hist_min:.0f}–{hist_max:.0f}{unit}"
                )
            return (
                f"  Teraz: {current:.0f}{unit}  vs  śr. {days} dni: {hist_avg:.0f}{unit}  "
                f"{arrow} ({sign}{diff:.0f}{unit})  |  zakres: {hist_min:.0f}–{hist_max:.0f}{unit}"
            )
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # MEGA FEATURE: Micro-Benchmark trigger
    # ─────────────────────────────────────────────────────────────────────────

    def _trigger_micro_benchmark(self, bench_type: str) -> None:
        """
        Fire-and-forget background micro-test. Results stored in session_memory
        under 'micro_bench' key so the NEXT query can reference real measured data.
        bench_type: 'cpu_single', 'disk_seq', 'ram_bandwidth'
        """
        import threading

        def _run_cpu_single() -> None:
            import time as _t
            start = _t.perf_counter()
            x = 0.0
            for i in range(1_000_000):
                x += (i ** 0.5)
            elapsed = _t.perf_counter() - start
            score = round(1_000_000 / elapsed)
            try:
                from hck_gpt.memory.session_memory import session_memory
                session_memory.record_response_data("micro_bench", {
                    "type": "cpu_single",
                    "score": score,
                    "elapsed_ms": round(elapsed * 1000),
                })
            except Exception:
                pass

        def _run_disk_seq() -> None:
            import os, tempfile, time as _t
            tmp = os.path.join(tempfile.gettempdir(), "_hck_bench_tmp.bin")
            MB  = 32
            data = b"\xAB" * (MB * 1_048_576)
            try:
                start_w = _t.perf_counter()
                with open(tmp, "wb") as f:
                    f.write(data)
                write_mb_s = round(MB / (_t.perf_counter() - start_w))
                start_r = _t.perf_counter()
                with open(tmp, "rb") as f:
                    _ = f.read()
                read_mb_s = round(MB / (_t.perf_counter() - start_r))
            except Exception:
                write_mb_s = read_mb_s = -1
            finally:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
            try:
                from hck_gpt.memory.session_memory import session_memory
                session_memory.record_response_data("micro_bench", {
                    "type":         "disk_seq",
                    "write_mb_s":   write_mb_s,
                    "read_mb_s":    read_mb_s,
                    "test_size_mb": MB,
                })
            except Exception:
                pass

        runners = {
            "cpu_single": _run_cpu_single,
            "disk_seq":   _run_disk_seq,
        }
        fn = runners.get(bench_type)
        if fn:
            threading.Thread(target=fn, daemon=True,
                             name=f"hck_microbench_{bench_type}").start()

    # ─────────────────────────────────────────────────────────────────────────
    # NEW INTENT HANDLERS (community feedback)
    # ─────────────────────────────────────────────────────────────────────────

    # ── Fan noise history ─────────────────────────────────────────────────────

    def _resp_fan_noise_history(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge

        snap = system_context.snapshot()
        hw   = user_knowledge.get_all_hardware()
        cpu  = float(snap.get("cpu_pct",  0) or 0)
        ram  = float(snap.get("ram_pct",  0) or 0)
        temp_now: Optional[float] = None

        # Get current temperatures from snapshot
        temps = snap.get("temperatures", [])
        if temps:
            temp_now = max(t for _, t in temps) if temps else None

        # Historical temperature trend from metrics_store
        hist_temp_cmp = self._get_historical_comparison("cpu_temp", 7, lang)

        lines = [_t(lang,
            f"{self.PREFIX} Analiza głośności wentylatora:",
            f"{self.PREFIX} Fan noise analysis:")]

        # Main cause: temperature and CPU load
        if cpu > 80 or (temp_now and temp_now > 80):
            lines.append(_t(lang,
                f"  🔴 CPU na {cpu:.0f}%{f' / temp {temp_now:.0f}°C' if temp_now else ''} — wentylatory kręcą się szybciej, to normalne.",
                f"  🔴 CPU at {cpu:.0f}%{f' / temp {temp_now:.0f}°C' if temp_now else ''} — fans spinning up, that's expected."))
        elif cpu > 55 or (temp_now and temp_now > 65):
            lines.append(_t(lang,
                f"  🟡 Umiarkowane obciążenie (CPU {cpu:.0f}%{f' / {temp_now:.0f}°C' if temp_now else ''}) — wentylatory mogą być słyszalne.",
                f"  🟡 Moderate load (CPU {cpu:.0f}%{f' / {temp_now:.0f}°C' if temp_now else ''}) — fans may be audible."))
        else:
            lines.append(_t(lang,
                f"  ✓ Niskie obciążenie (CPU {cpu:.0f}%) — jeśli fan hałasuje, może być kurz lub starzejące się łożysko.",
                f"  ✓ Low load (CPU {cpu:.0f}%) — if fan is loud, suspect dust or aging bearing."))

        # Historical comparison (time-travel)
        if hist_temp_cmp:
            lines.append(_t(lang, "  Porównanie historyczne (7 dni):", "  Historical comparison (7 days):"))
            lines.append(hist_temp_cmp)
        else:
            lines.append(_t(lang,
                "  Brak danych historycznych — wentylatory nie mają czujnika RPM przez psutil.",
                "  No historical fan data — fan RPM not exposed via psutil on Windows."))

        # Practical tips
        lines.append("")
        lines.append(_t(lang,
            "  Możliwe przyczyny głośniejszego wentylatora:",
            "  Possible causes of increased fan noise:"))
        lines.append(_t(lang,
            "  • Kurz w chłodniku — wyczyść sprężonym powietrzem (1x rok)",
            "  • Dust in heatsink — clean with compressed air (1x/year)"))
        lines.append(_t(lang,
            "  • Zużyte łożysko wentylatora — charakterystyczny warkot/szum",
            "  • Worn fan bearing — grinding or rattling sound"))
        lines.append(_t(lang,
            "  • Wysokie obciążenie (gry, render) — normalne i tymczasowe",
            "  • High load (gaming, rendering) — normal and temporary"))
        lines.append(_t(lang,
            "  💬 Wpisz 'temperatury' po pełny raport termiczny",
            "  💬 Type 'temperatures' for full thermal report"))
        return lines

    # ── Driver status ─────────────────────────────────────────────────────────

    def _resp_driver_status(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Shows GPU/display/audio driver info with dates via PowerShell/WMI.
        Color-codes by age: <6 months green, 6-18 months yellow, >18 months red.
        """
        import subprocess, datetime

        lines = [_t(lang,
            f"{self.PREFIX} Status sterowników (kluczowe):",
            f"{self.PREFIX} Driver status (key drivers):")]

        # Query via PowerShell — fastest way to get driver dates on Windows
        ps_cmd = (
            "Get-WmiObject Win32_PnPSignedDriver | "
            "Where-Object {$_.DeviceName -match 'Display|VGA|NVIDIA|AMD|Radeon|Intel.*Graphics|"
            "Audio|Sound|High Definition|Ethernet|Wi-Fi|Wireless'} | "
            "Select-Object DeviceName,DriverVersion,DriverDate | "
            "ConvertTo-Json"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=8
            )
            import json as _json
            raw = result.stdout.strip()
            if not raw:
                raise ValueError("empty")
            data = _json.loads(raw)
            if isinstance(data, dict):
                data = [data]

            now = datetime.datetime.now()
            for drv in data[:8]:
                name    = (drv.get("DeviceName")    or "?")[:40]
                version = (drv.get("DriverVersion") or "?")[:20]
                date_raw = drv.get("DriverDate") or ""

                # WMI DriverDate format: "20231005000000.000000-000"
                age_str = "?"
                color   = ""
                try:
                    date_str = date_raw[:8]  # YYYYMMDD
                    dt = datetime.datetime.strptime(date_str, "%Y%m%d")
                    months = (now - dt).days // 30
                    age_str = f"{months}m"
                    if months < 6:
                        color = "✓"
                    elif months < 18:
                        color = "!"
                    else:
                        color = "⚠"
                except Exception:
                    color = " "

                lines.append(f"  {color} {name[:38]}")
                lines.append(f"    ver {version}  ·  {age_str} old")
        except Exception:
            lines.append(_t(lang,
                "  Nie udało się pobrać listy sterowników przez PowerShell.",
                "  Could not retrieve driver list via PowerShell."))
            lines.append(_t(lang,
                "  Sprawdź ręcznie: Start → Menedżer urządzeń",
                "  Check manually: Start → Device Manager"))

        lines.append("")
        lines.append(_t(lang,
            "  ⚠ = starszy niż 18 mies.  !  = 6–18 mies.  ✓ = świeży (<6 mies.)",
            "  ⚠ = older than 18 months  !  = 6–18 months  ✓ = recent (<6 months)"))
        lines.append(_t(lang,
            "  Zaktualizuj sterowniki GPU w: NVIDIA GeForce Experience / AMD Software",
            "  Update GPU drivers in: NVIDIA GeForce Experience / AMD Software"))
        return lines

    # ── Gaming vs work time ───────────────────────────────────────────────────

    def _resp_gaming_vs_work_time(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Categorizes process CPU time from today's stats engine data into
        gaming / productive / background categories.
        """
        lines = [_t(lang,
            f"{self.PREFIX} Podział czasu na PC dziś:",
            f"{self.PREFIX} Time breakdown on PC today:")]

        _GAME_SLUGS = {
            "csgo", "cs2", "valorant", "fortnite", "minecraft", "steam",
            "epicgameslauncher", "battlenet", "gog", "ubisoft",
            "leagueoflegends", "dota2", "rocketleague", "cyberpunk",
            "witcher3", "ac_valhalla", "elden_ring", "apex", "pubg",
            "overwatch", "destiny2", "r5apex", "cod", "warzone",
        }
        _WORK_SLUGS = {
            "chrome", "firefox", "msedge", "brave", "opera",
            "code", "pycharm", "devenv", "rider", "clion", "idea",
            "word", "excel", "powerpnt", "winword", "excel",
            "notepad", "notepad++", "sublime_text", "atom",
            "cmd", "powershell", "windowsterminal", "python",
            "node", "java", "slack", "teams", "zoom", "outlook",
            "filezilla", "putty", "winscp",
        }

        gaming_cpu = 0.0
        work_cpu   = 0.0
        other_cpu  = 0.0
        found_any  = False

        try:
            import psutil
            for proc in psutil.process_iter(["name", "cpu_percent"]):
                try:
                    nm  = (proc.info.get("name") or "").lower().replace(".exe", "").replace("-", "").replace(" ", "")
                    cpu = proc.info.get("cpu_percent") or 0
                    if cpu < 0.1:
                        continue
                    found_any = True
                    if any(g in nm for g in _GAME_SLUGS):
                        gaming_cpu += cpu
                    elif any(w in nm for w in _WORK_SLUGS):
                        work_cpu += cpu
                    else:
                        other_cpu += cpu
                except Exception:
                    continue
        except Exception:
            pass

        if not found_any:
            return self._no_data("gaming_vs_work_time", lang,
                _t(lang, "brak aktywnych procesów", "no active processes"))

        total = gaming_cpu + work_cpu + other_cpu or 1.0
        g_pct = gaming_cpu / total * 100
        w_pct = work_cpu   / total * 100
        o_pct = other_cpu  / total * 100

        lines.append(_t(lang,
            "  (Podział bazuje na aktywnych procesach teraz, nie całym dniu)",
            "  (Split based on currently active processes, not full-day history)"))
        lines.append("")
        lines.append(_t(lang,
            f"  🎮 Gry/Gaming:       {g_pct:.0f}%  CPU share",
            f"  🎮 Gaming:           {g_pct:.0f}%  CPU share"))
        lines.append(_t(lang,
            f"  💼 Praca/Produktywność:  {w_pct:.0f}%  CPU share",
            f"  💼 Productive/Work:  {w_pct:.0f}%  CPU share"))
        lines.append(_t(lang,
            f"  ⚙ System/Inne:       {o_pct:.0f}%  CPU share",
            f"  ⚙ System/Other:     {o_pct:.0f}%  CPU share"))
        lines.append("")

        # Verdict
        if g_pct > 50:
            lines.append(_t(lang, "  → Aktualnie dominuje gaming.", "  → Gaming is currently dominant."))
        elif w_pct > 50:
            lines.append(_t(lang, "  → Aktualnie dominuje produktywność.", "  → Productivity is currently dominant."))
        else:
            lines.append(_t(lang, "  → Mix — nic nie dominuje wyraźnie.", "  → Mixed session — nothing clearly dominant."))

        lines.append(_t(lang,
            "  💬 Pełna historia: zakładka Statistics → Weekly",
            "  💬 Full history: Statistics → Weekly tab"))
        return lines

    # ── Process identity ──────────────────────────────────────────────────────

    def _resp_process_identity(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Checks if a named .exe is part of Windows, a known app, or suspicious.
        Uses the process_library and a Windows system path check.
        """
        import os

        raw = (r.raw_text or "").lower()

        # Extract .exe name from query
        import re as _re
        match = _re.search(r'[\w\-]+\.exe', raw)
        proc_name = match.group(0) if match else None

        # Also try without .exe if user typed e.g. "co to conhost"
        if not proc_name:
            _WIN_PROCS = {
                "svchost", "csrss", "lsass", "winlogon", "services", "smss",
                "conhost", "dwm", "ntoskrnl", "explorer", "taskhostw",
                "msiexec", "werfault", "searchindexer", "spoolsv",
                "audiodg", "runtimebroker", "settingssynchost",
            }
            for wp in _WIN_PROCS:
                if wp in raw:
                    proc_name = wp + ".exe"
                    break

        if not proc_name:
            if lang == "en":
                return [
                    f"{self.PREFIX} Which process do you want me to check?",
                    "  Include the .exe name, e.g.: 'is conhost.exe safe'",
                    "  or: 'what is werfault.exe'",
                ]
            return [
                f"{self.PREFIX} Który proces chcesz sprawdzić?",
                "  Podaj nazwę .exe, np.: 'czy conhost.exe jest bezpieczny'",
                "  lub: 'co to jest werfault.exe'",
            ]

        # Check process library first
        try:
            from hck_gpt.process_library import process_library as _lib
            info = _lib.get_process_info(proc_name)
        except Exception:
            info = None

        # Windows system path check
        is_system = False
        win_paths  = [
            os.environ.get("SystemRoot", "C:\\Windows"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "SysWOW64"),
        ]
        try:
            import psutil
            for proc in psutil.process_iter(["name", "exe"]):
                try:
                    if (proc.info.get("name") or "").lower() == proc_name.lower():
                        exe_path = proc.info.get("exe") or ""
                        for wp in win_paths:
                            if exe_path.lower().startswith(wp.lower()):
                                is_system = True
                                break
                        break
                except Exception:
                    continue
        except Exception:
            pass

        lines = [_t(lang,
            f"{self.PREFIX} Identyfikacja procesu — {proc_name}:",
            f"{self.PREFIX} Process identity — {proc_name}:")]

        if info:
            safety = info.get("safety", "unknown")
            desc_key = "description_pl" if lang == "pl" else "description_en"
            desc = info.get(desc_key) or info.get("description_en") or info.get("name", "?")
            icon = {"safe": "✓", "suspicious": "⚠", "unsafe": "🔴"}.get(safety, "?")
            lines.append(f"  {icon} {desc}")
            if safety == "suspicious":
                lines.append(_t(lang,
                    "  ⚠ Oznaczony jako podejrzany — sprawdź w Menedżerze zadań.",
                    "  ⚠ Flagged as suspicious — check in Task Manager."))
            elif safety == "unsafe":
                lines.append(_t(lang,
                    "  🔴 Oznaczony jako niebezpieczny — zamknij i przeskanuj antywirusem.",
                    "  🔴 Flagged as unsafe — close it and run antivirus scan."))
        elif is_system:
            lines.append(_t(lang,
                f"  ✓ Proces systemowy Windows — uruchomiony z folderu System32.",
                f"  ✓ Windows system process — running from System32 folder."))
            lines.append(_t(lang,
                "  Bezpieczny — nie przerywaj go.",
                "  Safe — do not terminate it."))
        else:
            lines.append(_t(lang,
                "  ? Nie ma go w bibliotece procesów PC Workman.",
                "  ? Not found in PC Workman's process library."))
            lines.append(_t(lang,
                "  Nieznany ≠ niebezpieczny. Sprawdź: google 'co to [nazwa].exe'",
                "  Unknown ≠ dangerous. Check: google 'what is [name].exe'"))
            lines.append(_t(lang,
                "  Podejrzany jeśli: w %TEMP%, brak podpisu, losowa nazwa",
                "  Suspicious if: in %TEMP%, no digital signature, random name"))

        lines.append(_followup("security", lang))
        return lines

    # ── Stale / unused apps ───────────────────────────────────────────────────

    def _resp_stale_apps(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Lists installed programs from registry that have not been seen
        in the process stats for 30+ days (if history available),
        or just shows all installed with last-seen fallback.
        """
        import winreg

        lines = [_t(lang,
            f"{self.PREFIX} Aplikacje prawdopodobnie nieużywane:",
            f"{self.PREFIX} Likely unused applications:")]

        installed: list[str] = []
        reg_paths = [
            (winreg.HKEY_CURRENT_USER,
             r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        seen: set[str] = set()
        try:
            for hive, path in reg_paths:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            sub = winreg.EnumKey(key, i)
                            try:
                                sub_key = winreg.OpenKey(key, sub)
                                name_val, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                                if name_val and name_val.lower() not in seen:
                                    seen.add(name_val.lower())
                                    installed.append(name_val)
                                winreg.CloseKey(sub_key)
                            except Exception:
                                pass
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    continue
        except Exception:
            pass

        if not installed:
            return self._no_data("stale_apps", lang,
                _t(lang, "brak dostępu do rejestru Uninstall", "no access to Uninstall registry"))

        # Filter obvious system/driver entries
        _SKIP = {"microsoft", "windows", "redistributable", "runtime", "update",
                 "directx", ".net", "visual c++", "driver", "intel", "amd", "nvidia",
                 "realtek", "vc_redist", "vcredist"}
        user_apps = [
            a for a in installed
            if not any(s in a.lower() for s in _SKIP)
        ][:20]

        # Try to cross-reference with process history in stats engine
        used_recently: set[str] = set()
        try:
            from hck_stats_engine.query_api import query_api
            from datetime import datetime, timedelta
            cutoff_str = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            today_str  = datetime.now().strftime("%Y-%m-%d")
            rows = query_api.get_process_daily_breakdown(today_str, top_n=50) or []
            for row in rows:
                nm = (row.get("process_name") or "").lower()
                for app in user_apps:
                    if nm[:8] in app.lower():
                        used_recently.add(app)
        except Exception:
            pass

        stale = [a for a in user_apps if a not in used_recently]

        if stale:
            lines.append(_t(lang,
                f"  Znaleziono {len(stale)} aplikacji bez widocznej aktywności w ostatnich 30 dniach:",
                f"  Found {len(stale)} apps with no visible activity in the last 30 days:"))
            for app in stale[:10]:
                lines.append(f"  — {app[:50]}")
            if len(stale) > 10:
                lines.append(_t(lang, f"  ... i {len(stale)-10} więcej", f"  ... and {len(stale)-10} more"))
        else:
            lines.append(_t(lang,
                "  Brak wyraźnie nieużywanych aplikacji w bazie ostatnich 30 dni.",
                "  No clearly unused apps found in last 30 days of process data."))

        lines.append("")
        lines.append(_t(lang,
            "  💡 Odinstaluj przez: Start → Ustawienia → Aplikacje",
            "  💡 Uninstall via: Start → Settings → Apps"))
        return lines

    # ── FPS degradation — time-travel debugging ───────────────────────────────

    def _resp_fps_degradation(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Time-Travel: compares current GPU load + temps to 30-day history.
        Looks for patterns that explain why FPS would degrade over time.
        """
        lines = [_t(lang,
            f"{self.PREFIX} Analiza degradacji FPS (Time-Travel):",
            f"{self.PREFIX} FPS degradation analysis (Time-Travel):")]

        # GPU load trend
        gpu_hist = self._get_historical_comparison("gpu_load", 30, lang)
        # CPU temp trend (thermal throttle is fps killer)
        cpu_temp_hist = self._get_historical_comparison("cpu_temp", 30, lang)
        # GPU temp trend
        gpu_temp_hist = self._get_historical_comparison("gpu_temp", 30, lang)

        if not gpu_hist and not cpu_temp_hist:
            lines.append(_t(lang,
                "  Brak danych historycznych (min. 7 dni wymagane).",
                "  Not enough historical data (need 7+ days of metrics_store data)."))
        else:
            if gpu_hist:
                lines.append(_t(lang, "  GPU load (30 dni):", "  GPU load (30 days):"))
                lines.append(gpu_hist)
            if gpu_temp_hist:
                lines.append(_t(lang, "  GPU temp (30 dni):", "  GPU temp (30 days):"))
                lines.append(gpu_temp_hist)
            if cpu_temp_hist:
                lines.append(_t(lang, "  CPU temp (30 dni):", "  CPU temp (30 days):"))
                lines.append(cpu_temp_hist)

        lines.append("")
        lines.append(_t(lang,
            "  Najczęstsze przyczyny degradacji FPS z czasem:",
            "  Most common causes of FPS degradation over time:"))
        lines.append(_t(lang,
            "  🌡 Kurz → gorzsze chłodzenie → CPU/GPU throttluje → gorsza wydajność",
            "  🌡 Dust buildup → worse cooling → CPU/GPU throttles → lower FPS"))
        lines.append(_t(lang,
            "  💾 Pełny dysk C: < 10 GB wolne → Windows swap spowalnia grę",
            "  💾 Full drive C: < 10 GB free → Windows swap slows the game"))
        lines.append(_t(lang,
            "  🔄 Aktualizacja sterownika GPU — czasem nowe wersje są gorsze dla starszych gier",
            "  🔄 GPU driver update — newer versions sometimes regress older titles"))
        lines.append(_t(lang,
            "  📦 Nowe apki w autostarcie pożerają RAM przy każdym starcie",
            "  📦 New startup apps eating RAM from boot"))

        # Trigger micro benchmark for disk
        self._trigger_micro_benchmark("disk_seq")
        lines.append("")
        lines.append(_t(lang,
            "  🔬 Uruchomiono micro-test dysku w tle — zapytaj 'jak szybki jest mój dysk' za 10s.",
            "  🔬 Disk micro-benchmark running in background — ask 'disk speed' in ~10s for results."))

        lines.append(_followup("perf", lang))
        return lines

    # ── App behavior change ───────────────────────────────────────────────────

    def _resp_app_behavior_change(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Time-Travel: checks if performance shifted since a week ago.
        Helps answer "why did X start acting differently".
        """
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge

        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()

        cpu  = float(snap.get("cpu_pct", 0) or 0)
        ram  = float(snap.get("ram_pct", 0) or 0)

        # 7-day CPU delta
        cpu_hist = self._get_historical_comparison("cpu_load", 7, lang)
        ram_hist = self._get_historical_comparison("ram_pct",  7, lang)

        lines = [_t(lang,
            f"{self.PREFIX} Analiza zmiany zachowania aplikacji:",
            f"{self.PREFIX} App behavior change analysis:")]

        # Check for notable changes
        typ_cpu = float(patterns.get("typical_cpu_avg") or 0)
        if typ_cpu > 0 and cpu > typ_cpu + 15:
            lines.append(_t(lang,
                f"  ⚠ CPU teraz {cpu:.0f}% vs norma {typ_cpu:.0f}% — coś pobiera więcej mocy niż zwykle.",
                f"  ⚠ CPU now {cpu:.0f}% vs typical {typ_cpu:.0f}% — something is consuming more than usual."))

        if cpu_hist:
            lines.append(_t(lang, "  CPU trend (7 dni):", "  CPU trend (7 days):"))
            lines.append(cpu_hist)
        if ram_hist:
            lines.append(_t(lang, "  RAM trend (7 dni):", "  RAM trend (7 days):"))
            lines.append(ram_hist)

        if not cpu_hist and not ram_hist:
            lines.append(_t(lang,
                "  Brak wystarczającej historii metryk — potrzebuję 7+ dni danych.",
                "  Not enough metric history — need 7+ days of data."))

        lines.append("")
        lines.append(_t(lang,
            "  Typowe przyczyny zmiany zachowania aplikacji:",
            "  Typical causes of app behavior change:"))
        lines.append(_t(lang,
            "  • Aktualizacja aplikacji — sprawdź w Ustawienia → Aplikacje",
            "  • App update — check Settings → Apps for recent updates"))
        lines.append(_t(lang,
            "  • Nowa usługa w tle odciągająca CPU/RAM",
            "  • New background service consuming CPU/RAM"))
        lines.append(_t(lang,
            "  • Pełny dysk — < 10 GB wolne spowalnia wszystko",
            "  • Full disk — < 10 GB free slows everything down"))
        lines.append(_t(lang,
            "  • Problem z temperaturą — CPU/GPU throttluje pod obciążeniem",
            "  • Thermal issue — CPU/GPU throttling under load"))
        lines.append(_t(lang,
            "  💬 Sprawdź 'co się zmieniło od wczoraj' po konkretne zmiany procesów",
            "  💬 Try 'what changed since yesterday' for specific process changes"))
        return lines

    # ── Startup slowdown ──────────────────────────────────────────────────────

    def _resp_startup_slowdown(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Enhanced startup analysis — ranks startup entries by likely boot impact,
        measures current startup program count and gives actionable prioritization.
        """
        import winreg

        lines = [_t(lang,
            f"{self.PREFIX} Co zwalnia uruchamianie komputera:",
            f"{self.PREFIX} What slows down your PC startup:")]

        _HIGH_IMPACT = {
            "chrome", "opera", "operagx", "brave", "firefox", "edge",
            "epicgameslauncher", "steam", "battlenet", "ubisoft", "gog",
            "spotify", "discord", "discordptb", "onedrive", "dropbox",
            "teamviewer", "anydesk",
        }
        _MED_IMPACT = {
            "teams", "zoom", "slack", "telegram", "signal", "skype",
            "googledrive", "box", "mega",
        }

        entries: list[tuple[str, str, int]] = []  # (name, exe, impact 3/2/1)
        try:
            reg_paths = [
                (winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]
            seen: set[str] = set()
            for hive, path in reg_paths:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            name, val, _ = winreg.EnumValue(key, i)
                            slug = name.lower().replace(" ", "").replace("-", "")
                            if slug not in seen:
                                seen.add(slug)
                                exe  = val.lower()
                                slug2 = slug + exe
                                impact = 1
                                if any(k in slug2 for k in _HIGH_IMPACT):
                                    impact = 3
                                elif any(k in slug2 for k in _MED_IMPACT):
                                    impact = 2
                                entries.append((name, val[:60], impact))
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    continue
        except Exception:
            pass

        if not entries:
            return self._no_data("startup_slowdown", lang,
                _t(lang, "brak dostępu do rejestru Run", "no registry Run access"))

        # Sort by impact descending
        entries.sort(key=lambda x: x[2], reverse=True)
        total = len(entries)

        verdict = ""
        if total <= 4:
            verdict = _t(lang, "✓ Bardzo czysty autostart.", "✓ Very clean startup.")
        elif total <= 8:
            verdict = _t(lang, "! Umiarkowany — można skrócić czas boot.", "! Moderate — boot time can be reduced.")
        else:
            verdict = _t(lang, "⚠ Dużo wpisów — boot jest wyraźnie wolniejszy.", "⚠ Many entries — boot is noticeably slower.")

        lines.append(f"  {verdict}  ({total} wpisów / {total} entries)")
        lines.append(_t(lang, "  Największy wpływ (sugeruj wyłączyć):", "  Highest impact (suggest disabling):"))

        for name, exe, impact in entries[:6]:
            icon = "🔴" if impact == 3 else ("🟡" if impact == 2 else "  ")
            lines.append(f"  {icon} {name[:40]}")

        lines.append("")
        lines.append(_t(lang,
            "  💬 Zarządzaj wpisami  [→ Startup Manager]",
            "  💬 Manage entries  [→ Startup Manager]"))
        lines.append(_followup("startup", lang))
        return lines

    # ── Temperature comparison (time-travel) ──────────────────────────────────

    def _resp_temp_comparison(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Time-Travel: compares current temps to 7-day and 30-day historical averages.
        Answers "is my PC hotter than usual lately?"
        """
        lines = [_t(lang,
            f"{self.PREFIX} Porównanie temperatur — czy jest goręcej niż zwykle?",
            f"{self.PREFIX} Temperature comparison — running hotter than usual?")]

        cpu_7d  = self._get_historical_comparison("cpu_temp", 7,  lang)
        cpu_30d = self._get_historical_comparison("cpu_temp", 30, lang)
        gpu_7d  = self._get_historical_comparison("gpu_temp", 7,  lang)

        has_data = any([cpu_7d, cpu_30d, gpu_7d])
        if not has_data:
            lines.extend(self._no_data("temp_comparison", lang,
                _t(lang, "brak danych z metrics_store", "no metrics_store temperature history")))
            lines.append(_t(lang,
                "  PC Workman zbiera dane co 5 min — wróć za kilka dni.",
                "  PC Workman collects data every 5 min — check back in a few days."))
            return lines

        if cpu_7d:
            lines.append(_t(lang, "  CPU temp vs 7 dni:", "  CPU temp vs 7 days:"))
            lines.append(cpu_7d)
        if cpu_30d:
            lines.append(_t(lang, "  CPU temp vs 30 dni:", "  CPU temp vs 30 days:"))
            lines.append(cpu_30d)
        if gpu_7d:
            lines.append(_t(lang, "  GPU temp vs 7 dni:", "  GPU temp vs 7 days:"))
            lines.append(gpu_7d)

        lines.append("")
        lines.append(_t(lang,
            "  Jeśli temperatury są wyraźnie wyższe niż zwykle:",
            "  If temperatures are notably higher than normal:"))
        lines.append(_t(lang,
            "  • Wyczyść chłodnik ze kurzu (sprężone powietrze)",
            "  • Clean heatsink of dust (compressed air)"))
        lines.append(_t(lang,
            "  • Sprawdź plan zasilania — High Performance grzeje bardziej",
            "  • Check power plan — High Performance runs hotter"))
        lines.append(_t(lang,
            "  • Sprawdź czy pasta termoprzewodząca nie wymaga wymiany (>3-4 lata)",
            "  • Check if thermal paste needs replacing (>3–4 years old)"))
        lines.append(_t(lang,
            "  💬 Wpisz 'temperatury' po aktualny live raport",
            "  💬 Type 'temperatures' for current live report"))
        return lines

    # ── Crash / freeze context ────────────────────────────────────────────────

    def _resp_crash_context(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Provides context about what was likely happening before the last freeze.
        Uses session_memory events + trends + last known snapshot.
        """
        from hck_gpt.memory.session_memory  import session_memory
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge

        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()

        lines = [_t(lang,
            f"{self.PREFIX} Analiza kontekstu przed ostatnim freezem:",
            f"{self.PREFIX} Context analysis before the last freeze:")]

        # Session events
        recent_evts = session_memory.recent_events(n=20)
        freeze_hint = None
        for evt in reversed(recent_evts):
            if evt.event_type in ("cpu_spike", "high_temp", "throttle", "high_ram"):
                freeze_hint = evt
                break

        if freeze_hint:
            age = freeze_hint.age_minutes()
            lines.append(_t(lang,
                f"  Ostatnie zdarzenie: {freeze_hint.event_type} — {age:.0f} min temu",
                f"  Last event: {freeze_hint.event_type} — {age:.0f} min ago"))
            if freeze_hint.detail:
                lines.append(f"  Szczegóły: {freeze_hint.detail}")
        else:
            lines.append(_t(lang,
                "  Brak nagranych zdarzeń w tej sesji przed pytaniem.",
                "  No events recorded in this session before the query."))

        # CPU/RAM at freeze time (current as approximation)
        cpu = float(snap.get("cpu_pct", 0) or 0)
        ram = float(snap.get("ram_pct", 0) or 0)
        lines.append(_t(lang,
            f"  Stan teraz: CPU {cpu:.0f}%  RAM {ram:.0f}%",
            f"  Current state: CPU {cpu:.0f}%  RAM {ram:.0f}%"))

        # Temperature context
        temps = snap.get("temperatures", [])
        if temps:
            max_temp = max(t for _, t in temps)
            if max_temp > 80:
                lines.append(_t(lang,
                    f"  ⚠ Temperatura teraz: {max_temp:.0f}°C — przegrzanie jest częstą przyczyną freezów.",
                    f"  ⚠ Temperature now: {max_temp:.0f}°C — overheating is a frequent freeze cause."))

        # Historical crash patterns from metrics
        cpu_temp_hist = self._get_historical_comparison("cpu_temp", 7, lang)
        if cpu_temp_hist:
            lines.append(_t(lang, "  CPU temp trend 7 dni:", "  CPU temp trend 7 days:"))
            lines.append(cpu_temp_hist)

        lines.append("")
        lines.append(_t(lang,
            "  Typowe przyczyny freezów/crashów:",
            "  Common causes of freezes/crashes:"))
        lines.append(_t(lang,
            "  🌡 Przegrzanie CPU/GPU — sprawdź temperatury i kurz",
            "  🌡 CPU/GPU overheating — check temps and dust"))
        lines.append(_t(lang,
            "  💾 RAM — uszkodzony moduł lub przeciążony pagefile (niski wolny RAM)",
            "  💾 RAM — faulty module or overloaded pagefile (low free RAM)"))
        lines.append(_t(lang,
            "  ⚡ Zasilanie — PSU zbyt słabe dla obciążenia, szczególnie przy graniu",
            "  ⚡ PSU — underpowered for load, especially during gaming"))
        lines.append(_t(lang,
            "  🔄 Sterowniki GPU — niestabilne wersje czasem powodują crash",
            "  🔄 GPU driver — unstable versions can cause crashes"))
        lines.append(_t(lang,
            "  💬 Sprawdź Windows Event Viewer: Win+R → eventvwr → System Logs",
            "  💬 Check Windows Event Viewer: Win+R → eventvwr → System Logs"))
        return lines

    # ── Game hardware stress ───────────────────────────────────────────────────

    def _resp_game_hardware_stress(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Looks at current running game processes and compares CPU/GPU load.
        Also uses historical metrics if available.
        """
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge

        snap    = system_context.snapshot()
        hw      = user_knowledge.get_all_hardware()

        _KNOWN_GAMES = {
            "csgo", "cs2", "valorant", "fortnite", "minecraft",
            "leagueoflegends", "dota2", "rocketleague", "cyberpunk2077",
            "witcher3", "apex_legends", "r5apex", "cod", "warzone",
            "overwatch", "destiny2", "pubg", "elden_ring", "gta5",
            "ac_valhalla", "halo", "battlefield", "bf2042", "tarkov",
        }

        # Find running game processes
        running_games: list[tuple[str, float, float]] = []
        try:
            import psutil
            for proc in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
                try:
                    nm = (proc.info.get("name") or "").lower().replace(".exe", "").replace(" ", "").replace("-", "")
                    cpu_p = proc.info.get("cpu_percent") or 0
                    ram_p = proc.info.get("memory_percent") or 0
                    if any(g in nm for g in _KNOWN_GAMES):
                        running_games.append((proc.info["name"], cpu_p, ram_p))
                except Exception:
                    continue
        except Exception:
            pass

        lines = [_t(lang,
            f"{self.PREFIX} Analiza obciążenia hardware podczas grania:",
            f"{self.PREFIX} Game hardware stress analysis:")]

        if running_games:
            lines.append(_t(lang,
                "  Aktywne gry teraz:", "  Active games right now:"))
            for name, cpu_p, ram_p in running_games[:4]:
                lines.append(f"  🎮 {name[:30]:<30}  CPU {cpu_p:.1f}%  RAM {ram_p:.1f}%")
        else:
            lines.append(_t(lang,
                "  Żadna gra nie jest teraz aktywna.",
                "  No game currently active."))

        # Overall system load right now
        cpu_now = float(snap.get("cpu_pct", 0) or 0)
        gpu_now_str = ""
        try:
            from hck_gpt.data.live_sensors import snapshot as _ls
            ls = _ls()
            gpu_load = ls.get("gpu_load", -1)
            if gpu_load >= 0:
                gpu_now_str = f"  GPU: {gpu_load:.0f}%"
        except Exception:
            pass

        lines.append(f"  CPU teraz: {cpu_now:.0f}%{gpu_now_str}" if lang == "pl"
                     else f"  CPU now: {cpu_now:.0f}%{gpu_now_str}")

        # Historical GPU load peak (which session pushed it hardest)
        try:
            from hck_gpt.data.metrics_store import metrics_store
            summary = metrics_store.daily_summary(days=14)
            if summary:
                # Find day with max GPU load
                peak_day = max(summary, key=lambda r: r.get("gpu_max") or 0)
                gpu_peak = peak_day.get("gpu_max")
                cpu_peak = peak_day.get("cpu_max")
                if gpu_peak and gpu_peak > 0:
                    lines.append("")
                    lines.append(_t(lang,
                        f"  Historyczny szczyt GPU (14 dni): {gpu_peak:.0f}% obciążenia ({peak_day['date_str']})",
                        f"  Historical GPU peak (14 days): {gpu_peak:.0f}% load ({peak_day['date_str']})"))
                    if cpu_peak:
                        lines.append(_t(lang,
                            f"  Przy tym CPU {cpu_peak:.0f}% — prawdopodobnie ciężka sesja gamingowa.",
                            f"  Alongside CPU {cpu_peak:.0f}% — likely a heavy gaming session."))
        except Exception:
            pass

        # Hardware capacity context
        if hw.get("gpu_model"):
            lines.append("")
            lines.append(_t(lang,
                f"  Twoja karta GPU: {hw['gpu_model']}",
                f"  Your GPU: {hw['gpu_model']}"))
        if hw.get("cpu_model"):
            lines.append(_t(lang,
                f"  Twój CPU: {hw['cpu_model']}",
                f"  Your CPU: {hw['cpu_model']}"))

        lines.append("")
        lines.append(_t(lang,
            "  💬 Wpisz 'temperatury' by sprawdzić czy sprzęt throttluje podczas grania",
            "  💬 Type 'temperatures' to check if hardware throttles during gaming"))
        return lines

    # ── Battery drain rate ─────────────────────────────────────────────────────

    def _resp_battery_drain_rate(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """Enhanced battery response — shows drain rate estimate during gaming vs idle."""
        try:
            import psutil
            bat = psutil.sensors_battery()
        except Exception:
            bat = None

        lines = [_t(lang,
            f"{self.PREFIX} Zużycie baterii:",
            f"{self.PREFIX} Battery drain:")]

        if bat is None:
            lines.append(_t(lang,
                "  Brak baterii (komputer stacjonarny lub brak czujnika).",
                "  No battery (desktop PC or no sensor available)."))
            lines.append(_t(lang,
                "  Pytanie o 'pobór prądu' jest bardziej odpowiednie dla laptopów.",
                "  'Power consumption' question is more relevant for laptops."))
        else:
            pct     = bat.percent
            plugged = bat.power_plugged
            secs    = bat.secsleft
            time_str = ""
            if secs and secs > 0 and not plugged:
                h, m = divmod(secs // 60, 60)
                time_str = (f"  ~{h}h {m}min pozostało" if lang == "pl"
                            else f"  ~{h}h {m}min remaining")
            status = _t(lang,
                "ładowanie" if plugged else "na baterii",
                "charging"  if plugged else "on battery")
            lines.append(f"  {pct:.0f}%  [{status}]{time_str}")

        # Current CPU load as proxy for power draw
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            lines.append("")
            lines.append(_t(lang,
                f"  CPU teraz: {cpu:.0f}%  RAM: {ram:.0f}%  — to główne czynniki poboru prądu",
                f"  CPU now: {cpu:.0f}%  RAM: {ram:.0f}%  — main factors in power draw"))

            if cpu > 70:
                lines.append(_t(lang,
                    "  🔴 Wysokie CPU = wysoki pobór — bateria rozładowuje się szybko",
                    "  🔴 High CPU = high draw — battery draining fast"))
            elif cpu > 40:
                lines.append(_t(lang,
                    "  🟡 Umiarkowane CPU — bateria rozładowuje się w normalnym tempie",
                    "  🟡 Moderate CPU — battery draining at normal pace"))
            else:
                lines.append(_t(lang,
                    "  ✓ Niskie CPU — wolne rozładowywanie baterii",
                    "  ✓ Low CPU — slow battery drain"))
        except Exception:
            pass

        lines.append("")
        lines.append(_t(lang,
            "  Szacowane zużycie baterii:",
            "  Estimated battery usage:"))
        lines.append(_t(lang,
            "  • Gaming:     ~20–35 % / godz  (GPU + CPU pod pełnym ładunkiem)",
            "  • Gaming:     ~20–35% / hour   (GPU + CPU under full load)"))
        lines.append(_t(lang,
            "  • Praca:      ~8–15 % / godz   (przeglądarka, dokumenty)",
            "  • Work:       ~8–15% / hour    (browser, documents)"))
        lines.append(_t(lang,
            "  • Jałowy:     ~3–6 % / godz    (bezczynność, ekran wygaszony)",
            "  • Idle:       ~3–6% / hour     (idle, screen off)"))
        lines.append(_t(lang,
            "  💡 Plan zasilania Balanced = lepsza bateria niż High Performance",
            "  💡 Balanced power plan saves more battery than High Performance"))
        return lines

    # ── Power after restart ────────────────────────────────────────────────────

    def _resp_power_after_restart(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Shows which processes have used the most CPU since session start,
        as a proxy for 'who used the most power since restart'.
        """
        from hck_gpt.memory.session_memory import session_memory

        session_dur = session_memory.session_duration_str()

        lines = [_t(lang,
            f"{self.PREFIX} Zużycie prądu od startu systemu (szacowane przez CPU):",
            f"{self.PREFIX} Power usage since restart (estimated via CPU):")]
        lines.append(_t(lang,
            f"  Czas sesji PC Workman: {session_dur}",
            f"  PC Workman session time: {session_dur}"))
        lines.append("")

        try:
            import psutil
            # cumulative CPU times since boot (more accurate for power history)
            procs_cpu: list[tuple[str, float]] = []
            for proc in psutil.process_iter(["name", "cpu_times"]):
                try:
                    ct = proc.info.get("cpu_times")
                    if ct:
                        total_s = getattr(ct, "user", 0) + getattr(ct, "system", 0)
                        if total_s > 1:
                            procs_cpu.append((proc.info["name"] or "?", total_s))
                except Exception:
                    continue
            procs_cpu.sort(key=lambda x: x[1], reverse=True)

            if procs_cpu:
                lines.append(_t(lang,
                    "  Procesy z największym łącznym czasem CPU od uruchomienia:",
                    "  Processes with most cumulative CPU time since boot:"))
                for name, secs in procs_cpu[:7]:
                    mins = secs / 60
                    lines.append(f"  — {name[:30]:<30}  {mins:.0f} min CPU time")
            else:
                lines.append(_t(lang,
                    "  Brak danych o CPU times — prawdopodobnie brak uprawnień.",
                    "  No CPU times data — likely insufficient permissions."))
        except Exception:
            lines.append(_t(lang,
                "  Nie mogę pobrać danych o procesach.",
                "  Cannot retrieve process data."))

        lines.append("")
        lines.append(_t(lang,
            "  💡 Więcej czasu CPU = więcej prądu zużytego.",
            "  💡 More CPU time = more power consumed."))
        lines.append(_t(lang,
            "  Dla dokładniejszego pomiaru (laptopy): Start → powercfg /batteryreport",
            "  For more precise measurement (laptops): Start → powercfg /batteryreport"))
        lines.append(_followup("process", lang))
        return lines


# ── Singleton ─────────────────────────────────────────────────────────────────
response_builder = ResponseBuilder()
