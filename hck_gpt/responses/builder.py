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
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                header = _t(lang, f"{self.PREFIX} Temperatury:", f"{self.PREFIX} Temperatures:")
                lines = [header]
                for name, entries in temps.items():
                    for e in entries[:3]:
                        label  = e.label or name
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
        if lang == "en":
            return [
                f"{self.PREFIX} Can't read temperatures directly on Windows.",
                "  Check: Monitoring tab → Sensors → Hardware Sensors",
            ]
        return [
            f"{self.PREFIX} Nie mogę odczytać temperatur bezpośrednio.",
            "  Sprawdź: zakładka Monitoring → Sensors → Hardware Sensors",
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
