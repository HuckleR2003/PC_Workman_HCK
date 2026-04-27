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
        ],
        "en": [
            "  💬 Try: 'what GPU do I have' / 'how much RAM' / 'health check'",
            "  💬 Type 'specs' to see full hardware summary",
            "  💬 Type 'performance' to check current load",
        ],
    },
    "health": {
        "pl": [
            "  💬 Napisz 'top procesy' by zobaczyć co obciąża CPU",
            "  💬 Wpisz 'temperatury' jeśli coś grzeje za mocno",
            "  💬 Sprawdź 'wydajność' po zmknięciu zbędnych programów",
        ],
        "en": [
            "  💬 Type 'top processes' to see what's using CPU",
            "  💬 Type 'temperatures' if something runs hot",
            "  💬 Check 'performance' after closing unused apps",
        ],
    },
    "perf": {
        "pl": [
            "  💬 Wpisz 'stats' by zobaczyć dzisiejsze średnie",
            "  💬 Zapytaj 'czy CPU throttluje' by sprawdzić dławienie",
        ],
        "en": [
            "  💬 Type 'stats' to see today's averages",
            "  💬 Ask 'is CPU throttling' to check power limits",
        ],
    },
}


def _followup(key: str, lang: str) -> str:
    pool = _FOLLOWUPS.get(key, {})
    lines = pool.get(lang, pool.get("pl", []))
    return random.choice(lines) if lines else ""


# ── Main class ────────────────────────────────────────────────────────────────

class ResponseBuilder:
    """
    Template-based bilingual response generator.
    Enriched with live data from SystemContext and UserKnowledge.
    """

    PREFIX = "hck_GPT:"

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
        hw = user_knowledge.get_all_hardware()

        if not hw:
            return self._live_hw_fallback(lang)

        header = _t(lang, f"{self.PREFIX} Twój komputer:", f"{self.PREFIX} Your PC:")
        lines = [header]

        _add = lambda label_pl, label_en, key: (
            lines.append(f"  {_t(lang, label_pl, label_en):<14} {hw[key]}")
            if hw.get(key) else None
        )

        if hw.get("cpu_model"):
            cores = hw.get("cpu_cores", "?")
            boost = hw.get("cpu_boost_ghz", "?")
            lines.append(f"  {'CPU':<14} {hw['cpu_model']}  "
                         f"({cores}{'C' if lang == 'pl' else ' cores'} / boost {boost} GHz)")
        if hw.get("gpu_model"):
            vram = f"  {hw['gpu_vram_gb']} GB VRAM" if hw.get("gpu_vram_gb") else ""
            lines.append(f"  {'GPU':<14} {hw['gpu_model']}{vram}")
        if hw.get("ram_total_gb"):
            spd = f" @ {hw['ram_speed_mhz']} MHz" if hw.get("ram_speed_mhz") else ""
            lines.append(f"  {'RAM':<14} {hw['ram_total_gb']} GB{spd}")
        _add("Płyta główna", "Motherboard", "motherboard_model")
        _add("Dysk",         "Storage",     "storage_summary")
        _add("OS",           "OS",          "os_version")
        lines.append(_followup("hw", lang))
        return lines

    # ── Hardware — CPU ────────────────────────────────────────────────────────

    def _resp_hw_cpu(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        from hck_gpt.context.system_context import system_context
        hw   = user_knowledge.get_all_hardware()
        snap = system_context.snapshot()

        model   = hw.get("cpu_model",     _t(lang, "nieznany model", "unknown model"))
        cores_p = hw.get("cpu_cores",     snap.get("cpu_cores_physical", "?"))
        cores_l = hw.get("cpu_threads",   snap.get("cpu_cores_logical",  "?"))
        boost   = hw.get("cpu_boost_ghz", "?")
        cur_mhz = snap.get("cpu_mhz",  "—")
        cur_pct = snap.get("cpu_pct",  "—")
        throttle = ""
        if snap.get("cpu_throttled"):
            throttle = _t(lang, "  ⚠ throttled!", "  ⚠ throttling!")

        if lang == "en":
            return [
                f"{self.PREFIX} Processor:",
                f"  Model:    {model}",
                f"  Cores:    {cores_p} physical  /  {cores_l} logical",
                f"  Boost:    {boost} GHz",
                f"  Now:      {cur_mhz} MHz  |  {cur_pct}% usage{throttle}",
                _followup("hw", lang),
            ]
        return [
            f"{self.PREFIX} Procesor:",
            f"  Model:    {model}",
            f"  Rdzenie:  {cores_p} fizyczne  /  {cores_l} logiczne",
            f"  Boost:    {boost} GHz",
            f"  Teraz:    {cur_mhz} MHz  |  {cur_pct}% użycia{throttle}",
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

        vram_str = f"\n  VRAM:  {vram} GB" if vram else ""
        header = _t(lang,
                    f"{self.PREFIX} Karta graficzna:",
                    f"{self.PREFIX} Graphics card:")
        return [header, f"  Model:{vram_str}  {model}", _followup("hw", lang)]

    # ── Hardware — RAM ────────────────────────────────────────────────────────

    def _resp_hw_ram(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        from hck_gpt.context.system_context import system_context
        hw   = user_knowledge.get_all_hardware()
        snap = system_context.snapshot()

        total = hw.get("ram_total_gb", snap.get("ram_total_gb", "?"))
        speed = hw.get("ram_speed_mhz", None)
        pct   = snap.get("ram_pct",     "—")
        used  = snap.get("ram_used_gb", "—")
        free  = snap.get("ram_free_gb", "—")

        spd_str = f"  /  {speed} MHz" if speed else ""
        if lang == "en":
            return [
                f"{self.PREFIX} RAM:",
                f"  Installed:  {total} GB{spd_str}",
                f"  Now:        {used} GB used  ({pct}%)  /  {free} GB free",
            ]
        return [
            f"{self.PREFIX} Pamięć RAM:",
            f"  Zainstalowana: {total} GB{spd_str}",
            f"  Teraz:         {used} GB użyte  ({pct}%)  /  {free} GB wolne",
        ]

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
        hw      = user_knowledge.get_all_hardware()
        summary = hw.get("storage_summary", None)

        header = _t(lang, f"{self.PREFIX} Dyski:", f"{self.PREFIX} Disks:")
        if summary:
            return [header, f"  {summary}"]

        try:
            import psutil
            # Only iterate fixed/local drives — skip network/optical to avoid hangs
            SAFE_FSTYPES = {"ntfs", "fat32", "exfat", "refs", "ext4", "apfs"}
            lines = [_t(lang, f"{self.PREFIX} Dyski (live):", f"{self.PREFIX} Disks (live):")]
            for p in psutil.disk_partitions(all=False):
                # Skip network drives (opts contains 'remote') and optical drives
                if "remote" in (p.opts or "").lower():
                    continue
                if p.fstype and p.fstype.lower() not in SAFE_FSTYPES:
                    # Still try, but with tighter guard
                    pass
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    free_gb  = round(u.free  / 1_073_741_824, 1)
                    total_gb = round(u.total / 1_073_741_824, 1)
                    free_lbl = _t(lang, "wolne", "free")
                    lines.append(
                        f"  {p.device}  {total_gb} GB total  |  {free_gb} GB {free_lbl}"
                    )
                except Exception:
                    pass
                if len(lines) > 6:   # cap at 5 drives shown
                    break
            if len(lines) > 1:
                return lines
        except Exception:
            pass
        return [_t(lang, f"{self.PREFIX} Brak danych o dyskach.", f"{self.PREFIX} No disk data available.")]

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
        snap   = system_context.snapshot()
        issues = []
        good   = []

        cpu = snap.get("cpu_pct", 0) or 0
        ram = snap.get("ram_pct", 0) or 0

        if lang == "en":
            if cpu > 90:
                issues.append(f"  ⚠ CPU critical:  {cpu:.0f}%")
            elif cpu > 75:
                issues.append(f"  ! CPU high:      {cpu:.0f}%")
            else:
                good.append(f"  ✓ CPU OK:        {cpu:.0f}%")

            if ram > 90:
                issues.append(f"  ⚠ RAM critical:  {ram:.0f}%")
            elif ram > 80:
                issues.append(f"  ! RAM high:      {ram:.0f}%")
            else:
                good.append(f"  ✓ RAM OK:        {ram:.0f}%")

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
            lines.append(_followup("health", lang))
            return lines

        # Polish
        if cpu > 90:
            issues.append(f"  ⚠ CPU krytyczne:  {cpu:.0f}%")
        elif cpu > 75:
            issues.append(f"  ! CPU wysokie:    {cpu:.0f}%")
        else:
            good.append(f"  ✓ CPU OK:          {cpu:.0f}%")

        if ram > 90:
            issues.append(f"  ⚠ RAM krytyczne:  {ram:.0f}%")
        elif ram > 80:
            issues.append(f"  ! RAM wysokie:    {ram:.0f}%")
        else:
            good.append(f"  ✓ RAM OK:          {ram:.0f}%")

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
            lines.append(_t(lang, "Wszystko wygląda dobrze ✓", "All looks good ✓"))
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
        return [ok_msg, f"  {_t(lang, 'Teraz', 'Now')}: {mhz} MHz  /  Max: {max_mhz} MHz  {ratio_str}"]

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
        snap = system_context.snapshot()
        cpu = snap.get("cpu_pct",  "—")
        ram = snap.get("ram_pct",  "—")
        mhz = snap.get("cpu_mhz",  "—")

        thr = ""
        if snap.get("cpu_throttled"):
            ratio = snap.get("cpu_throttle_ratio", 0) * 100
            thr = _t(lang,
                     f"  ⚠ CPU throttled ({ratio:.0f}% mocy)",
                     f"  ⚠ CPU throttled ({ratio:.0f}% of max power)")

        pool = self._PERF_INTROS_EN if lang == "en" else self._PERF_INTROS_PL
        intro = random.choice(pool).replace("{P}", self.PREFIX)
        lines = [intro,
                 f"  CPU:  {cpu}%  @  {mhz} MHz",
                 f"  RAM:  {ram}%"]
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
        return [msg]

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
        if lang == "en":
            return [
                f"{self.PREFIX} System optimization:",
                "  Go to the Optimization tab → Service Setup",
                "  or type 'service setup' to launch the wizard.",
            ]
        return [
            f"{self.PREFIX} Optymalizacja systemu:",
            "  Zakładka Optimization → Service Setup",
            "  lub wpisz 'service setup' żeby uruchomić kreatora.",
        ]

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
        "{P} Hej, tu hck_GPT! W czym mogę pomóc?",
    ]
    _GREET_EN = [
        "{P} Hey! Ask about your hardware, temps or performance.",
        "{P} Hi there! I'm here — what would you like to know?",
        "{P} Hey! Feel free — CPU, GPU, RAM, health, stats.",
        "{P} Hello, hck_GPT here! How can I help?",
    ]

    def _resp_greeting(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        from hck_gpt.memory.user_knowledge import user_knowledge
        hw = user_knowledge.get_hardware("cpu_model")

        pool = self._GREET_EN if lang == "en" else self._GREET_PL
        response = random.choice(pool).replace("{P}", self.PREFIX)

        if not session_memory.greeted_this_session:
            session_memory.greeted_this_session = True
            if hw:
                cpu_note = _t(lang, f"  (Widzę: {hw})", f"  (I see: {hw})")
                response += "\n" + cpu_note
        return [response]

    _THANKS_PL = [
        "{P} Nie ma za co! Pisz jak coś.",
        "{P} Spoko! Zawsze tu jestem.",
        "{P} Chętnie pomagam! 😊",
        "{P} Cała przyjemność po mojej stronie!",
    ]
    _THANKS_EN = [
        "{P} You're welcome! Ping me anytime.",
        "{P} No problem! I'm always here.",
        "{P} Happy to help! 😊",
        "{P} Anytime — that's what I'm here for!",
    ]

    def _resp_thanks(self, r: ParseResult, lang: str = "pl") -> List[str]:
        pool = self._THANKS_EN if lang == "en" else self._THANKS_PL
        return [random.choice(pool).replace("{P}", self.PREFIX)]

    def _resp_help(self, r: ParseResult, lang: str = "pl") -> List[str]:
        if lang == "en":
            return [
                f"{self.PREFIX} What I can do:",
                "  Hardware:     'what CPU do I have' / 'specs' / 'how much RAM'",
                "  Health:       'health check' / 'is my PC OK'",
                "  Temperature:  'temperatures' / 'is it running hot'",
                "  Performance:  'performance' / 'is CPU throttling'",
                "  Stats:        'stats' / 'today averages'",
                "  Processes:    'top processes' / 'what's using CPU'",
                "  Optimization: 'service setup' / 'optimization'",
            ]
        return [
            f"{self.PREFIX} Co mogę zrobić:",
            "  Sprzęt:      'jaki mam procesor' / 'specyfikacja' / 'ile ram'",
            "  Zdrowie:     'czy komputer jest zdrowy' / 'diagnostics'",
            "  Temp:        'jakie temperatury' / 'czy się grzeje'",
            "  Wydajność:   'wydajność' / 'czy CPU throttluje'",
            "  Statystyki:  'stats' / 'dzisiejsze średnie'",
            "  Procesy:     'top procesy' / 'co używa CPU'",
            "  Optymalizacja: 'service setup' / 'optimization'",
        ]

    # ── Small talk (route to Ollama via hybrid engine; rule fallback here) ────

    _SMALLTALK_PL = [
        "{P} Nie jestem filozofem, ale mogę opowiedzieć o Twoim PC 😄",
        "{P} Moje specjalizacje to CPU, GPU, RAM i diagnostyka — spróbuj mnie 'specs'!",
        "{P} Skupiam się na Twoim komputerze — zapytaj o cokolwiek związanego z PC.",
        "{P} To ciekawe pytanie! Ale lepiej spytaj o swój sprzęt — tam jestem ekspertem.",
    ]
    _SMALLTALK_EN = [
        "{P} I'm not a philosopher, but I know your PC well 😄",
        "{P} My specialty is CPU, GPU, RAM and diagnostics — try 'specs'!",
        "{P} I focus on your computer — ask me anything PC-related.",
        "{P} Interesting! But I'm more useful talking about your hardware.",
    ]

    def _resp_small_talk(self, r: ParseResult, lang: str = "pl") -> List[str]:
        pool = self._SMALLTALK_EN if lang == "en" else self._SMALLTALK_PL
        return [random.choice(pool).replace("{P}", self.PREFIX)]

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
        snap = system_context.snapshot()
        cpu = snap.get("cpu_pct", 0) or 0
        ram = snap.get("ram_pct", 0) or 0

        header = _t(lang,
                    f"{self.PREFIX} Plan przyspieszenia komputera:",
                    f"{self.PREFIX} PC speed-up plan:")
        recs: list[str] = []

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
                    f"  🗑 Folder TEMP: {temp_mb} MB  →  zakładka Optimization → Clear TEMP",
                    f"  🗑 TEMP folder: {temp_mb} MB  →  Optimization tab → Clear TEMP"))
        except Exception:
            pass

        # RAM pressure
        if ram > 75:
            recs.append(_t(lang,
                f"  ⚠ RAM na {ram:.0f}%  →  zamknij zbędne karty/aplikacje lub włącz Auto RAM Flush",
                f"  ⚠ RAM at {ram:.0f}%  →  close unused tabs/apps or enable Auto RAM Flush"))

        # CPU pressure
        if cpu > 80:
            recs.append(_t(lang,
                f"  ⚠ CPU na {cpu:.0f}%  →  sprawdź 'top' kto obciąża i zamknij zbędne",
                f"  ⚠ CPU at {cpu:.0f}%  →  type 'top' to find and close the culprit"))

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
                        f"  📁 AppData: {count} folderów (dużo starych resztek aplikacji)",
                        f"  📁 AppData: {count} folders (many old app leftovers)"))
                    recs.append(_t(lang,
                        "     → wpisz '%appdata%' w Windows Search i posprzątaj",
                        "     → type '%appdata%' in Windows Search and clean up"))
        except Exception:
            pass

        if not recs:
            recs.append(_t(lang,
                "  ✓ System wygląda dobrze — nie ma oczywistych usprawnień.",
                "  ✓ System looks clean — no obvious wins found."))
            recs.append(_t(lang,
                "  💡 Możesz sprawdzić zakładkę Optimization → TURBO BOOST.",
                "  💡 You can still try the Optimization tab → TURBO BOOST."))

        return [header] + recs

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
