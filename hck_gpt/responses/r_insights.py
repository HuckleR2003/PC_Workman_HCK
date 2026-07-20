"""hck_gpt.responses.r_insights - InsightsResponses mixin (15 intent handlers).
Split out of the builder.py monolith; composed into ResponseBuilder via MRO."""
from hck_gpt.responses.common import (  # shared helpers/data
    List,
    ParseResult,
    _followup,
    _t,
)


class InsightsResponses:
    def _resp_stats(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        snap    = system_context.snapshot()
        cpu_avg = snap.get("cpu_avg_today", _t(lang, "brak danych", "no data"))
        cpu_max = snap.get("cpu_max_today", "-")
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
                    arrow = "↑" if diff > 3 else ("↓" if diff < -3 else "->")
                    lines.append(_t(lang,
                                    f"  CPU vs poprzedni tydzień: {arrow} {sign}{diff:.0f}% (śr. {lw_cpu:.0f}% -> {tw_cpu:.0f}%)",
                                    f"  CPU vs last week: {arrow} {sign}{diff:.0f}% (avg {lw_cpu:.0f}% -> {tw_cpu:.0f}%)"))
        except Exception:
            pass

        hint = _t(lang,
                  "  (Pełny raport: zakładka AllMonitor lub 'today report')",
                  "  (Full report: AllMonitor tab or type 'today report')")
        lines.append(hint)
        return lines

    def _resp_uptime(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        dur = session_memory.session_duration_str()
        msg = _t(lang,
                 f"{self.PREFIX} Sesja PC Workman trwa: {dur}",
                 f"{self.PREFIX} PC Workman session running for: {dur}")
        return [msg, _followup("perf", lang)]

    def _resp_pc_changes(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Broad 'what changed since yesterday' - goes beyond raw numbers to show:
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
                    cpu_arrow = "↑" if cpu_d > 3 else ("↓" if cpu_d < -3 else "->")
                    ram_arrow = "↑" if ram_d > 3 else ("↓" if ram_d < -3 else "->")
                    changes.append(_t(lang,
                        f"  📊 Wydajność: CPU {cpu_arrow} {cpu_t:.0f}% (wczoraj {cpu_y:.0f}%) | RAM {ram_arrow} {ram_t:.0f}% (wczoraj {ram_y:.0f}%)",
                        f"  📊 Performance: CPU {cpu_arrow} {cpu_t:.0f}% (yest {cpu_y:.0f}%) | RAM {ram_arrow} {ram_t:.0f}% (yest {ram_y:.0f}%)"))
        except Exception:
            pass

        # ── 3. Current power plan ─────────────────────────────────────────────
        try:
            import subprocess
            rp = subprocess.run(["powercfg", "/getactivescheme"],
                                capture_output=True, text=True, errors="replace", timeout=3)
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
                    note = _t(lang, " ⚠ dużo - warto przejrzeć", " ⚠ high - worth reviewing")
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
                "  Za mało danych historycznych - potrzebuję min. 2 dni historii w bazie.",
                "  Not enough history yet - need at least 2 days of data."))
            lines.append(_t(lang,
                "  Sprawdź zmiany ręcznie: zakładka AllMonitor -> DayStats.",
                "  Check manually: AllMonitor tab -> DayStats."))
        else:
            lines.extend(changes)

        lines.append(_t(lang,
            "  💬 Pełna oś czasu: zakładka AllMonitor.",
            "  💬 Full timeline: AllMonitor tab."))
        lines.append(_followup("session", lang))
        return lines

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
                            "  Za mało danych - potrzebuję minimum 2 dni historii.",
                            "  Not enough data - need at least 2 days of history."))
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

        # ── record for cross-response references ───────────────────
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
                    "  Check back tomorrow - I'll have something to compare.",
                ]
            return [
                f"{self.PREFIX} Za mało danych historycznych do porównania.",
                "  Silnik statystyk potrzebuje minimum 2 dni danych.",
                "  Wróć jutro - będę miał co porównać.",
            ]

        lines = [_t(lang,
                    f"{self.PREFIX} Porównanie sesji - wczoraj vs dziś:",
                    f"{self.PREFIX} Session comparison - yesterday vs today:")]

        def _row(label_pl, label_en, val_today, val_yest, unit=""):
            label = label_en if lang == "en" else label_pl
            t = f"{val_today:.0f}{unit}" if val_today is not None else "-"
            y = f"{val_yest:.0f}{unit}" if val_yest is not None else "-"
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

            # ── record for cross-response references ────────────────
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
                lines.append("  That makes it one of your regular tools - I track patterns over time.")
                if cpu:
                    lines.append(f"  When it runs, it averages {cpu:.0f}% CPU load.")
            else:
                lines.append(f"  '{proc}' był aktywny przez {freq} z ostatnich 7 dni.")
                lines.append("  Oznacza to, że to regularny element Twojego zestawu.")
                if cpu:
                    lines.append(f"  Średnie obciążenie CPU gdy działa: {cpu:.0f}%.")

        elif ptype in ("cpu_high", "cpu_crit"):
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  Your CPU was running at {val}% - that's sustained high load.")
                lines.append("  Type 'top processes' to see which app caused it.")
            else:
                lines.append(f"  CPU pracował na {val}% - to utrzymane wysokie obciążenie.")
                lines.append("  Wpisz 'top procesy' by znaleźć winowajcę.")

        elif ptype in ("ram_high", "ram_crit"):
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  RAM was at {val}% - memory was getting tight.")
                lines.append("  Ask me 'why is RAM high' for a detailed breakdown.")
            else:
                lines.append(f"  RAM był na {val}% - mało wolnej pamięci.")
                lines.append("  Zapytaj 'dlaczego ram wysoki' po szczegółową analizę.")

        elif ptype == "throttle":
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  Your CPU was throttled - running at only {val}% of max power.")
                lines.append("  This is usually caused by heat. Check 'temperatures'.")
            else:
                lines.append(f"  CPU był dławiony - pracował na zaledwie {val}% mocy maksymalnej.")
                lines.append("  Zwykle winne jest przegrzanie. Sprawdź 'temperatury'.")

        elif ptype == "disk_low":
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  Your disk had only {val} GB of free space.")
                lines.append("  Clean up TEMP files via the Optimization tab.")
            else:
                lines.append(f"  Na dysku zostało tylko {val} GB wolnego miejsca.")
                lines.append("  Wyczyść pliki TEMP przez zakładkę Optimization.")

        elif ptype == "long_session":
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  PC has been running for {val} hours without a restart.")
                lines.append("  Memory leaks can accumulate over long sessions - consider restarting tonight.")
            else:
                lines.append(f"  PC działa od {val} godzin bez restartu.")
                lines.append("  Przy długich sesjach mogą gromadzić się wycieki pamięci.")

        elif ptype == "gpu_temp_spike":
            val = ctx.get("val", "?")
            if lang == "en":
                lines.append(f"  GPU temperature hit {val}°C - that's a sudden heat spike.")
                lines.append("  Check cooling, airflow, or lower your GPU load settings.")
            else:
                lines.append(f"  Temperatura GPU osiągnęła {val}°C - ostry skok ciepła.")
                lines.append("  Sprawdź chłodzenie, wentylację lub obniż ustawienia GPU.")

        elif ptype in ("all_clear",):
            if lang == "en":
                lines.append("  That was a routine status check - everything was healthy at that moment.")
            else:
                lines.append("  To był rutynowy przegląd - wszystko działało prawidłowo w tym momencie.")

        elif ptype == "greeting":
            if lang == "en":
                lines.append("  That was my greeting - a quick summary of your PC's state when you opened the app.")
            else:
                lines.append("  To było powitanie - szybki przegląd stanu PC przy otwarciu aplikacji.")

        else:
            # Generic fallback
            if lang == "en":
                lines.append("  That was a proactive system notification. Ask me 'health check' or 'stats' for more.")
            else:
                lines.append("  To był proaktywny komunikat o stanie systemu. Zapytaj 'health' lub 'stats' po więcej.")

        lines.append(_followup("health", lang))
        return lines

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
                f"  ⚠ CPU teraz {cpu:.0f}% vs norma {typ_cpu:.0f}% - coś pobiera więcej mocy niż zwykle.",
                f"  ⚠ CPU now {cpu:.0f}% vs typical {typ_cpu:.0f}% - something is consuming more than usual."))

        if cpu_hist:
            lines.append(_t(lang, "  CPU trend (7 dni):", "  CPU trend (7 days):"))
            lines.append(cpu_hist)
        if ram_hist:
            lines.append(_t(lang, "  RAM trend (7 dni):", "  RAM trend (7 days):"))
            lines.append(ram_hist)

        if not cpu_hist and not ram_hist:
            lines.append(_t(lang,
                "  Brak wystarczającej historii metryk - potrzebuję 7+ dni danych.",
                "  Not enough metric history - need 7+ days of data."))

        lines.append("")
        lines.append(_t(lang,
            "  Typowe przyczyny zmiany zachowania aplikacji:",
            "  Typical causes of app behavior change:"))
        lines.append(_t(lang,
            "  • Aktualizacja aplikacji - sprawdź w Ustawienia -> Aplikacje",
            "  • App update - check Settings -> Apps for recent updates"))
        lines.append(_t(lang,
            "  • Nowa usługa w tle odciągająca CPU/RAM",
            "  • New background service consuming CPU/RAM"))
        lines.append(_t(lang,
            "  • Pełny dysk - < 10 GB wolne spowalnia wszystko",
            "  • Full disk - < 10 GB free slows everything down"))
        lines.append(_t(lang,
            "  • Problem z temperaturą - CPU/GPU throttluje pod obciążeniem",
            "  • Thermal issue - CPU/GPU throttling under load"))
        lines.append(_t(lang,
            "  💬 Sprawdź 'co się zmieniło od wczoraj' po konkretne zmiany procesów",
            "  💬 Try 'what changed since yesterday' for specific process changes"))
        return lines

    def _resp_crash_context(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Provides context about what was likely happening before the last freeze.
        Uses session_memory events + trends + last known snapshot.
        """
        from hck_gpt.memory.session_memory  import session_memory
        from hck_gpt.context.system_context import system_context

        snap     = system_context.snapshot()

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
                f"  Ostatnie zdarzenie: {freeze_hint.event_type} - {age:.0f} min temu",
                f"  Last event: {freeze_hint.event_type} - {age:.0f} min ago"))
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
                    f"  ⚠ Temperatura teraz: {max_temp:.0f}°C - przegrzanie jest częstą przyczyną freezów.",
                    f"  ⚠ Temperature now: {max_temp:.0f}°C - overheating is a frequent freeze cause."))

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
            "  🌡 Przegrzanie CPU/GPU - sprawdź temperatury i kurz",
            "  🌡 CPU/GPU overheating - check temps and dust"))
        lines.append(_t(lang,
            "  💾 RAM - uszkodzony moduł lub przeciążony pagefile (niski wolny RAM)",
            "  💾 RAM - faulty module or overloaded pagefile (low free RAM)"))
        lines.append(_t(lang,
            "  ⚡ Zasilanie - PSU zbyt słabe dla obciążenia, szczególnie przy graniu",
            "  ⚡ PSU - underpowered for load, especially during gaming"))
        lines.append(_t(lang,
            "  🔄 Sterowniki GPU - niestabilne wersje czasem powodują crash",
            "  🔄 GPU driver - unstable versions can cause crashes"))
        lines.append(_t(lang,
            "  💬 Sprawdź Windows Event Viewer: Win+R -> eventvwr -> System Logs",
            "  💬 Check Windows Event Viewer: Win+R -> eventvwr -> System Logs"))
        return lines

    def _resp_health_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Comprehensive health overview: live metrics, temps, throttle, disk.
        Gives an overall verdict with actionable follow-ups.
        """
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()

        cpu  = float(snap.get("cpu_pct",  0) or 0)
        ram  = float(snap.get("ram_pct",  0) or 0)
        cpu_t = snap.get("cpu_temp")
        gpu_t = snap.get("gpu_temp")
        disk_free = snap.get("disk_free_gb", 0) or 0
        throttled = snap.get("cpu_throttled", False)

        # Score-based health verdict
        score = 100
        issues: List[str] = []

        if cpu > 90:
            score -= 25; issues.append(_t(lang, "CPU krytycznie wysoki", "CPU critically high"))
        elif cpu > 75:
            score -= 12; issues.append(_t(lang, "CPU podwyższony", "CPU elevated"))

        if ram > 90:
            score -= 25; issues.append(_t(lang, "RAM krytycznie zajęty", "RAM critically full"))
        elif ram > 80:
            score -= 12; issues.append(_t(lang, "RAM wysoki", "RAM high"))

        if cpu_t and cpu_t > 88:
            score -= 20; issues.append(_t(lang, f"CPU przegrzany ({cpu_t:.0f}°C)", f"CPU overheating ({cpu_t:.0f}°C)"))
        elif cpu_t and cpu_t > 78:
            score -= 8;  issues.append(_t(lang, f"CPU ciepły ({cpu_t:.0f}°C)", f"CPU warm ({cpu_t:.0f}°C)"))

        if gpu_t and gpu_t > 90:
            score -= 15; issues.append(_t(lang, f"GPU przegrzany ({gpu_t:.0f}°C)", f"GPU overheating ({gpu_t:.0f}°C)"))
        elif gpu_t and gpu_t > 80:
            score -= 8;  issues.append(_t(lang, f"GPU ciepły ({gpu_t:.0f}°C)", f"GPU warm ({gpu_t:.0f}°C)"))

        if throttled:
            score -= 15; issues.append(_t(lang, "CPU throttluje", "CPU throttling"))

        if disk_free < 5:
            score -= 20; issues.append(_t(lang, f"Dysk prawie pełny ({disk_free:.0f} GB wolne)", f"Disk nearly full ({disk_free:.0f} GB free)"))
        elif disk_free < 15:
            score -= 8;  issues.append(_t(lang, f"Mało miejsca na dysku ({disk_free:.0f} GB)", f"Low disk space ({disk_free:.0f} GB free)"))

        score = max(0, score)

        # Verdict
        if score >= 90:
            verdict = _t(lang, "DOSKONAŁY", "EXCELLENT")
            verdict_sym = "✓"
        elif score >= 75:
            verdict = _t(lang, "DOBRY", "GOOD")
            verdict_sym = "✓"
        elif score >= 55:
            verdict = _t(lang, "PRZECIĘTNY", "FAIR")
            verdict_sym = "!"
        else:
            verdict = _t(lang, "KRYTYCZNY", "CRITICAL")
            verdict_sym = "⚠"

        lines = [_t(lang,
            f"{self.PREFIX} Stan zdrowia systemu  [{verdict_sym} {verdict}  {score}/100]",
            f"{self.PREFIX} System health  [{verdict_sym} {verdict}  {score}/100]")]
        lines.append("")

        # Live metrics row
        temp_str = ""
        if cpu_t:
            temp_str += f"  {cpu_t:.0f}°C CPU"
        if gpu_t:
            temp_str += f"  {gpu_t:.0f}°C GPU"
        lines.append(f"  CPU {cpu:.0f}%   RAM {ram:.0f}%{temp_str}")
        if snap.get("cpu_mhz") and snap.get("cpu_max_mhz"):
            ratio = snap["cpu_mhz"] / snap["cpu_max_mhz"] * 100
            if ratio < 75:
                lines.append(_t(lang,
                    f"  Taktowanie: {snap['cpu_mhz']} MHz  ({ratio:.0f}% mocy)",
                    f"  Freq: {snap['cpu_mhz']} MHz  ({ratio:.0f}% of max)"))

        # Issues
        if issues:
            lines.append("")
            lines.append(_t(lang, "  Znalezione problemy:", "  Issues detected:"))
            for iss in issues:
                lines.append(f"  • {iss}")

        # Typical vs now comparison
        typ_cpu = float(patterns.get("typical_cpu_avg") or 0)
        if typ_cpu > 0 and abs(cpu - typ_cpu) > 10:
            delta = cpu - typ_cpu
            sign = "+" if delta > 0 else ""
            lines.append(_t(lang,
                f"  CPU teraz {sign}{delta:.0f}% vs Twoja norma ({typ_cpu:.0f}%)",
                f"  CPU now {sign}{delta:.0f}% vs your typical ({typ_cpu:.0f}%)"))

        # Tips
        lines.append("")
        if score < 75:
            lines.append(_t(lang,
                "  💬 Rekomendowane: 'optymalizacja' · 'top procesy' · 'temperatura'",
                "  💬 Recommended: 'optimization' · 'top processes' · 'temperature'"))
        else:
            lines.append(_t(lang,
                "  💬 Sprawdź: 'stats' · 'temperatura' · 'specs'",
                "  💬 Check: 'stats' · 'temperature' · 'specs'"))

        return lines

    def _resp_morning_brief(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_gpt.data.metrics_store import metrics_store
            ext = metrics_store.last_session_extremes()
        except Exception:
            ext = {}
        ls = self._dm_live()
        lines = [_t(lang, f"{self.PREFIX} Dzień dobry! Szybki brief:",
                          f"{self.PREFIX} Good morning! Quick brief:")]
        y = (ext or {}).get("yesterday") or {}
        if y:
            lines.append(_t(lang,
                f"  Wczoraj: CPU max {self._dm_val(y.get('cpu_max'),'%')} · "
                f"temp max {self._dm_val(y.get('cpu_temp_max'),'°C')} · "
                f"RAM max {self._dm_val(y.get('ram_max'),'%')}",
                f"  Yesterday: CPU max {self._dm_val(y.get('cpu_max'),'%')} · "
                f"temp max {self._dm_val(y.get('cpu_temp_max'),'°C')} · "
                f"RAM max {self._dm_val(y.get('ram_max'),'%')}"))
        lines.append(_t(lang,
            f"  Teraz: CPU {self._dm_val(ls.get('cpu_load'),'%')} · "
            f"{self._dm_val(ls.get('cpu_temp'),'°C')} · "
            f"GPU {self._dm_val(ls.get('gpu_temp'),'°C')}",
            f"  Now: CPU {self._dm_val(ls.get('cpu_load'),'%')} · "
            f"{self._dm_val(ls.get('cpu_temp'),'°C')} · "
            f"GPU {self._dm_val(ls.get('gpu_temp'),'°C')}"))
        try:
            from core.voltage_analyzer import voltage_analyzer
            score = voltage_analyzer.overall_health_score()
            lines.append(_t(lang, f"  Zasilanie: {score}/100 wg Twojej normy",
                                  f"  Power health: {score}/100 vs your baseline"))
        except Exception:
            pass
        lines.append(_t(lang, "  Miłego dnia - pilnuję wszystkiego w tle. ✅",
                              "  Have a good one - I'm watching everything. ✅"))
        return lines

    def _resp_session_digest(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        hist = ls.get("session_hist") or {}
        try:
            from hck_gpt.memory.session_memory import session_memory
            dur = session_memory.session_duration_str()
        except Exception:
            dur = "-"
        lines = [_t(lang, f"{self.PREFIX} Podsumowanie tej sesji ({dur}):",
                          f"{self.PREFIX} This session's digest ({dur}):")]
        label = {"cpu_load": "CPU %", "cpu_temp": "CPU °C",
                 "gpu_load": "GPU %", "gpu_temp": "GPU °C",
                 "cpu_power": "CPU W", "gpu_power": "GPU W"}
        shown = 0
        for k, lab in label.items():
            mm = hist.get(k)
            if mm and mm[0] >= 0:
                lines.append(f"  {lab:<7} min {mm[0]:.0f} · max {mm[1]:.0f}")
                shown += 1
        if not shown:
            lines.append(_t(lang, "  Sesja dopiero się rozkręca - spytaj za parę minut.",
                                  "  Session just warming up - ask again in a few minutes."))
        return lines

    def _resp_weekly_trends(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_gpt.data.metrics_store import metrics_store
            days = metrics_store.daily_summary(days=7)
        except Exception:
            days = []
        if len(days) < 2:
            return [_t(lang,
                f"{self.PREFIX} Potrzebuję co najmniej 2 dni danych na trend tygodnia "
                "(DeepMonitor zapisuje historię lokalnie).",
                f"{self.PREFIX} I need at least 2 days of data for a weekly trend "
                "(DeepMonitor stores history locally).")]
        lines = [_t(lang, f"{self.PREFIX} Trend z {len(days)} dni (avg / max):",
                          f"{self.PREFIX} Trend across {len(days)} days (avg / max):")]
        for d in days[:7]:
            lines.append(
                f"  {d.get('date_str','?')}  CPU {self._dm_val(d.get('cpu_avg'),'%')}/"
                f"{self._dm_val(d.get('cpu_max'),'%')}  ·  "
                f"temp {self._dm_val(d.get('cpu_temp_max'),'°C')}  ·  "
                f"RAM {self._dm_val(d.get('ram_max'),'%')}")
        newest, oldest = days[0], days[-1]
        try:
            dt = (newest.get("cpu_temp_max") or 0) - (oldest.get("cpu_temp_max") or 0)
            if abs(dt) >= 3:
                arrow = "↑" if dt > 0 else "↓"
                lines += ["", _t(lang,
                    f"  {arrow} Max temperatura CPU {'wzrosła' if dt>0 else 'spadła'} o {abs(dt):.0f}°C w tym okresie.",
                    f"  {arrow} Max CPU temperature went {'up' if dt>0 else 'down'} {abs(dt):.0f}°C over this period.")]
        except Exception:
            pass
        return lines

    def _resp_compare_baseline(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        try:
            from core.thermal_baseline import thermal_baseline
            thermal_baseline.maybe_rebuild()
            block = thermal_baseline.format_for_chat(
                ls.get("cpu_temp", -1), ls.get("cpu_load", -1),
                ls.get("gpu_load", -1), lang,
                gpu_temp=ls.get("gpu_temp", -1)).split("\n")
        except Exception:
            block = []
        head = _t(lang, f"{self.PREFIX} Teraz vs Twoja nauczona norma:",
                        f"{self.PREFIX} Now vs your learned baseline:")
        if not block:
            return [head, _t(lang,
                "  Baza jeszcze się uczy - każda godzina pracy poprawia dokładność.",
                "  Baseline still learning - every hour of use improves accuracy.")]
        return [head] + [f"  {b}" for b in block if b.strip()]

    def _resp_symptom_freeze(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        finds = []
        try:
            import psutil
            vm, sw = psutil.virtual_memory(), psutil.swap_memory()
            if vm.percent >= 88:
                finds.append(_t(lang, f"RAM {vm.percent:.0f}% - system dusi się pamięcią",
                                      f"RAM {vm.percent:.0f}% - memory pressure"))
            if sw.percent >= 60:
                finds.append(_t(lang, f"SWAP {sw.percent:.0f}% - dysk ratuje RAM (lagi)",
                                      f"SWAP {sw.percent:.0f}% - disk backing RAM (stutter)"))
        except Exception:
            pass
        ct = ls.get("cpu_temp", -1)
        if ct >= 92:
            finds.append(_t(lang, f"CPU {ct:.0f}°C - throttling bardzo prawdopodobny",
                                  f"CPU {ct:.0f}°C - throttling very likely"))
        head = _t(lang, f"{self.PREFIX} Zawiesza się? Sprawdziłem typowych winnych:",
                        f"{self.PREFIX} Freezing? I checked the usual suspects:")
        if not finds:
            return [head,
                _t(lang, "  ✅ RAM, SWAP i temperatury wyglądają zdrowo TERAZ.",
                         "  ✅ RAM, SWAP and temps look healthy RIGHT NOW."),
                _t(lang, "  Jeśli zwiesza się przy starcie gry → 'gotowy do gry'. "
                         "Historia: 'temperatury dzisiaj'.",
                         "  If it freezes at game launch → 'game ready'. "
                         "History: 'temps today'.")]
        return [head] + [f"  ⚠ {f}" for f in finds] + [
            _t(lang, "  Szybka pomoc: [-> Optimization] (RAM Flush / Hibernation).",
                     "  Quick help: [-> Optimization] (RAM Flush / Hibernation).")]

    def _resp_symptom_noisy(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        ct, gt = ls.get("cpu_temp", -1), ls.get("gpu_temp", -1)
        cause_pl, cause_en = "nie widzę gorącego podzespołu - możliwy kurz/łożysko wentylatora", \
                             "no hot component visible - possibly dust or a fan bearing"
        if gt >= 75:
            cause_pl = f"GPU {gt:.0f}°C - to jego wentylatory słyszysz"
            cause_en = f"GPU {gt:.0f}°C - that's its fans you hear"
        elif ct >= 80:
            cause_pl = f"CPU {ct:.0f}°C - chłodzenie procesora pracuje na wysokich obrotach"
            cause_en = f"CPU {ct:.0f}°C - the CPU cooler is spinning hard"
        return [
            _t(lang, f"{self.PREFIX} Głośno? Najpewniej: {cause_pl}.",
                     f"{self.PREFIX} Noisy? Most likely: {cause_en}."),
            _t(lang, f"  CPU {self._dm_val(ct,'°C')} · GPU {self._dm_val(gt,'°C')} · "
                     "RPM: napisz 'wentylatory' (wymaga LHM).",
                     f"  CPU {self._dm_val(ct,'°C')} · GPU {self._dm_val(gt,'°C')} · "
                     "RPM: type 'fans' (needs LHM)."),
            _t(lang, "  Utrzymuje się przy bezczynności? 'top procesy' znajdzie winnego.",
                     "  Persists at idle? 'top processes' finds the culprit."),
        ]

