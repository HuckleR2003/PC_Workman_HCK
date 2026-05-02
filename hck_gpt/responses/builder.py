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
        EN: '→ normal (avg 42%)'  /  '↑ +23% vs typical (42%)'
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
        return (f"→ normal (avg {typ:.0f}%)" if lang == "en"
                else f"→ norma (śr. {typ:.0f}%)")
    elif delta > 0:
        return (f"↑ +{delta:.0f}% vs typical ({typ:.0f}%)" if lang == "en"
                else f"↑ +{delta:.0f}% vs typowe ({typ:.0f}%)")
    else:
        return (f"↓ {delta:.0f}% vs typical ({typ:.0f}%)" if lang == "en"
                else f"↓ {delta:.0f}% vs typowe ({typ:.0f}%)")


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
    ]
    _HEALTH_INTROS_EN = [
        "{P} System health check:",
        "{P} Checking your PC health...",
        "{P} Running diagnostics...",
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
                lines.append("Issues:")
                lines.extend(issues)
            lines.extend(good)
            if not issues:
                lines.append("All looks good ✓")

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
    ]
    _PERF_INTROS_EN = [
        "{P} Current performance:",
        "{P} System load right now:",
        "{P} Here's what's happening:",
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
                "",
                "  📊  Performance & Stats",
                "      'performance'  /  'stats'  /  'top processes'  /  'uptime'",
                "      'what changed in performance'  /  'compare sessions'",
                "",
                "  🔍  Why is it doing that?",
                "      'why is it slow'  /  'why is ram so high'  /  'why is disk at 100'",
                "      'what drains battery'  /  'unnecessary programs'",
                "",
                "  ⚡  Optimization",
                "      'speed up pc'  /  'turbo boost'  /  'startup programs'",
                "      'optimization'  /  'power plan'  /  'disk speed'",
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
            "",
            "  📊  Wydajność i statystyki",
            "      'wydajność'  /  'stats'  /  'top procesy'  /  'czas sesji'",
            "      'co się zmieniło w wydajności'  /  'porównaj sesje'",
            "",
            "  🔍  Dlaczego tak działa?",
            "      'dlaczego laguje'  /  'dlaczego ram wysoki'  /  'dysk na 100 dlaczego'",
            "      'co rozładowuje baterię'  /  'niepotrzebne programy'",
            "",
            "  ⚡  Optymalizacja",
            "      'przyspiesz komputer'  /  'turbo boost'  /  'autostart'",
            "      'optymalizacja'  /  'plan zasilania'  /  'jak przyspieszyć dysk'",
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
                f"{self.PREFIX} About PC Workman HCK v1.7.2:",
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
            f"{self.PREFIX} O programie PC Workman HCK v1.7.2:",
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


# ── Singleton ─────────────────────────────────────────────────────────────────
response_builder = ResponseBuilder()
