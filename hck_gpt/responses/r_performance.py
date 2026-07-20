"""hck_gpt.responses.r_performance - PerformanceResponses mixin (12 intent handlers).
Split out of the builder.py monolith; composed into ResponseBuilder via MRO."""
from hck_gpt.responses.common import (  # shared helpers/data
    List,
    ParseResult,
    _IDLE_PROC_NAMES,
    _delta_label,
    _followup,
    _hw_profile,
    _t,
    random,
)


class PerformanceResponses:
    def _resp_performance(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()

        cpu = snap.get("cpu_pct",  "-")
        ram = snap.get("ram_pct",  "-")
        mhz = snap.get("cpu_mhz",  "-")

        # ── delta labels ────────────────────────────────────────────
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
                f"  🔴 Teraz: {dominant} na {val:.0f}% - zacznij od TURBO BOOST",
                f"  🔴 Right now: {dominant} at {val:.0f}% - start with TURBO BOOST")
        elif ram > 70 or cpu > 70:
            priority = _t(lang,
                f"  🟡 Umiarkowane obciążenie (CPU {cpu:.0f}% / RAM {ram:.0f}%) - warto posprzątać",
                f"  🟡 Moderate load (CPU {cpu:.0f}% / RAM {ram:.0f}%) - a good time to clean up")
        else:
            priority = _t(lang,
                f"  ✓ System wygląda OK (CPU {cpu:.0f}% / RAM {ram:.0f}%) - prewencja zamiast gaszenia pożarów",
                f"  ✓ System looks fine (CPU {cpu:.0f}% / RAM {ram:.0f}%) - prevention rather than firefighting")

        header = _t(lang, f"{self.PREFIX} Optymalizacja systemu:", f"{self.PREFIX} System optimization:")
        lines  = [header, priority, ""]

        # ── Quick action menu ─────────────────────────────────────────────────
        lines.append(_t(lang, "  Szybkie akcje:", "  Quick actions:"))
        lines.append(_t(lang,
            "  ⚡ TURBO BOOST - High Perf + flush RAM + wyczyść TEMP  [-> Optimization]",
            "  ⚡ TURBO BOOST - High Perf + RAM flush + clear TEMP  [-> Optimization]"))
        lines.append(_t(lang,
            "  🚀 Autostart - ogranicz co odpala się z Windows  [-> Startup Manager]",
            "  🚀 Startup - limit what launches with Windows  [-> Startup Manager]"))

        # HW-aware additions
        if profile["ram_low"]:
            lines.append(_t(lang,
                f"  🧠 Pamięć wirtualna - masz {profile['ram_gb']:.0f} GB RAM, pagefile da oddech  [-> Virtual Memory]",
                f"  🧠 Virtual Memory - you have {profile['ram_gb']:.0f} GB RAM, pagefile will help  [-> Virtual Memory]"))
        if profile["is_hdd"]:
            lines.append(_t(lang,
                "  💽 HDD wykryty - wyłącz indeksowanie Windows Search dla szybszego dysku",
                "  💽 HDD detected - disable Windows Search indexing for a faster drive"))

        lines.append("")
        lines.append(_t(lang,
            "  💬 Wpisz 'przyspiesz komputer' po spersonalizowany plan optymalizacji",
            "  💬 Type 'speed up pc' for a personalised optimisation plan"))
        return lines

    def _resp_speed_up_pc(self, r: ParseResult, lang: str = "pl") -> List[str]:
        import os, tempfile, subprocess
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        snap    = system_context.snapshot()
        hw      = user_knowledge.get_all_hardware()
        profile = _hw_profile(hw)        # ── hardware profile ──

        cpu = float(snap.get("cpu_pct", 0) or 0)
        ram = float(snap.get("ram_pct", 0) or 0)

        header = _t(lang,
                    f"{self.PREFIX} Plan przyspieszenia komputera:",
                    f"{self.PREFIX} PC speed-up plan:")
        recs: list[str] = []

        # ── HW-specific issues first ───────────────────────────────
        # Low RAM - flag before anything else, it's the biggest bottleneck
        if profile["ram_low"]:
            recs.append(_t(lang,
                f"  · RAM: {profile['ram_gb']:.0f} GB - realne wąskie gardło przy dzisiejszych obciążeniach. Priorytet 1:",
                f"  · RAM: {profile['ram_gb']:.0f} GB - a real bottleneck under today's workloads. Priority 1:"))
            recs.append(_t(lang,
                "     Zamknij browser gdy nieużywany (~3–4 GB odzysk)",
                "     Close browser when idle (~3–4 GB recovered)"))
            recs.append(_t(lang,
                "     lub dodaj Pamięć Wirtualną  [-> Virtual Memory]",
                "     or add Virtual Memory  [-> Virtual Memory]"))

        # HDD - drastically different optimization path
        if profile["is_hdd"]:
            recs.append(_t(lang,
                "  · Dysk: HDD - najwolniejszy element tego zestawu.",
                "  · Disk: HDD - the slowest link in this build."))
            recs.append(_t(lang,
                "     Wyłącz Windows Search indexing (Usługi -> WSearch -> Disabled)",
                "     Disable Windows Search indexing (Services -> WSearch -> Disabled)"))
            recs.append(_t(lang,
                "     Uruchom defragmentację: Start -> Defragmentuj dyski",
                "     Run defrag: Start -> Defragment and Optimize Drives"))

        # Power plan
        try:
            rp = subprocess.run(["powercfg", "/getactivescheme"],
                                capture_output=True, text=True, errors="replace", timeout=3)
            ln = rp.stdout.strip()
            plan = ln[ln.rfind("(")+1:ln.rfind(")")] if "(" in ln else "Unknown"
            if "High Performance" not in plan and "Ultimate" not in plan:
                recs.append(_t(lang,
                    f"  · Plan zasilania: {plan}  ->  zmień na High Performance",
                    f"  · Power plan: {plan}  ->  switch to High Performance"))
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
                    f"  · Folder TEMP: {temp_mb} MB  ->  [-> Optimization] -> Clear TEMP",
                    f"  · TEMP folder: {temp_mb} MB  ->  [-> Optimization] -> Clear TEMP"))
        except Exception:
            pass

        # RAM pressure (general, not just low-RAM case)
        if ram > 75 and not profile["ram_low"]:
            recs.append(_t(lang,
                f"  ⚠ RAM na {ram:.0f}%  ->  zamknij zbędne karty i włącz Auto RAM Flush",
                f"  ⚠ RAM at {ram:.0f}%  ->  close unused tabs and enable Auto RAM Flush"))

        # CPU pressure
        if cpu > 80:
            recs.append(_t(lang,
                f"  ⚠ CPU na {cpu:.0f}%  ->  wpisz 'top' żeby znaleźć winowajcę",
                f"  ⚠ CPU at {cpu:.0f}%  ->  type 'top' to identify the culprit"))

        # Few cores - process management is key
        if profile["few_cores"] and cpu > 60:
            recs.append(_t(lang,
                f"  ⚠ {profile['cpu_cores']} rdzenie CPU - ogranicz równoległe aplikacje",
                f"  ⚠ {profile['cpu_cores']} CPU cores - limit parallel running apps"))

        # Disk C: space
        try:
            import psutil
            du = psutil.disk_usage("C:\\")
            free_gb = round(du.free / 1_073_741_824, 1)
            if free_gb < 15:
                recs.append(_t(lang,
                    f"  ⚠ Dysk C: tylko {free_gb} GB wolne  ->  usuń pliki, wyczyść AppData",
                    f"  ⚠ Drive C: only {free_gb} GB free  ->  delete files, clean AppData"))
        except Exception:
            pass

        # AppData
        try:
            appdata = os.environ.get('APPDATA', '')
            if appdata and os.path.exists(appdata):
                count = sum(1 for d in os.scandir(appdata) if d.is_dir())
                if count > 60:
                    recs.append(_t(lang,
                        f"  · AppData: {count} folderów (resztki starych aplikacji)",
                        f"  · AppData: {count} folders (old app leftovers)"))
                    recs.append(_t(lang,
                        "     -> wpisz '%appdata%' w Windows Search i posprzątaj",
                        "     -> type '%appdata%' in Windows Search and clean up"))
        except Exception:
            pass

        # Startup programs link
        recs.append(_t(lang,
            "  · Programy startowe do przeglądu  [-> Startup Manager]",
            "  · Review startup programs  [-> Startup Manager]"))

        if len(recs) == 1:  # only startup hint, system is clean
            recs.insert(0, _t(lang,
                "  ✓ System wygląda dobrze - nie ma oczywistych usprawnień.",
                "  ✓ System looks clean - no obvious wins found."))

        recs.append(_t(lang,
            "  Wolisz, żebym Cię poprowadził? Pełny przewodnik krok po kroku "
            "z pomiarem przed/po - napisz: zoptymalizuj komputer.",
            "  Prefer to be guided? Full step-by-step walkthrough with "
            "before/after measurements - type: optimize my pc."))

        return [header] + recs

    def _resp_turbo_boost(self, r: ParseResult, lang: str = "pl") -> List[str]:
        if lang == "en":
            return [
                f"{self.PREFIX} TURBO BOOST - what it does:",
                "  Activates: High Performance power plan + RAM flush + disables non-essential services.",
                "  Result: faster response, lower RAM, more CPU headroom.",
                "  When to use: before gaming, heavy work, or when system feels sluggish.",
                "  💬 Go to the Optimization tab to activate it.",
            ]
        return [
            f"{self.PREFIX} TURBO BOOST - co robi:",
            "  Aktywuje: plan zasilania High Performance + flush RAM + wyłącza zbędne serwisy.",
            "  Efekt: szybsza odpowiedź systemu, mniej zajętego RAM, więcej mocy dla CPU.",
            "  Kiedy używać: przed graniem, ciężką pracą, albo gdy PC chodzi wolno.",
            "  💬 Zakładka Optimization -> aktywuj TURBO BOOST jednym kliknięciem.",
        ]

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
            for p in sorted_procs:
                name_raw = p.info.get("name") or "?"
                if name_raw.lower() in _IDLE_PROC_NAMES:
                    continue   # never blame System Idle Process
                pct = p.info.get("cpu_percent", 0) or 0
                if pct > 0.5:
                    top_procs.append(f"{name_raw[:24]} ({pct:.0f}%)")
                if len(top_procs) >= 3:
                    break
        except Exception:
            pass

        reasons: list[str] = []

        # CPU reasons - with delta context
        if cpu > 80:
            cpu_delta = _delta_label(cpu, patterns.get("typical_cpu_avg"), lang)
            delta_sfx = f"  {cpu_delta}" if cpu_delta else ""
            reasons.append(_t(lang,
                f"  ⚠ CPU na {cpu:.0f}%{delta_sfx}",
                f"  ⚠ CPU at {cpu:.0f}%{delta_sfx}"))

        # ── hardware-aware RAM diagnosis ────────────────────────────
        if ram > 80:
            ram_delta = _delta_label(ram, patterns.get("typical_ram_avg"), lang)
            delta_sfx = f"  {ram_delta}" if ram_delta else ""
            if profile["ram_low"]:
                reasons.append(_t(lang,
                    f"  ⚠ RAM na {ram:.0f}%{delta_sfx} - masz tylko {profile['ram_gb']:.0f} GB (ciasno dla nowoczesnych apek)",
                    f"  ⚠ RAM at {ram:.0f}%{delta_sfx} - you only have {profile['ram_gb']:.0f} GB (tight for modern apps)"))
            else:
                reasons.append(_t(lang,
                    f"  ⚠ RAM na {ram:.0f}%{delta_sfx} - może używać pliku wymiany",
                    f"  ⚠ RAM at {ram:.0f}%{delta_sfx} - may be using pagefile"))

        elif ram > 65 and profile["ram_low"]:
            # Low RAM + moderately elevated - flag it earlier than normal
            reasons.append(_t(lang,
                f"  ! RAM na {ram:.0f}% - przy {profile['ram_gb']:.0f} GB to już odczuwalne",
                f"  ! RAM at {ram:.0f}% - with {profile['ram_gb']:.0f} GB total this is noticeable"))

        if snap.get("cpu_throttled"):
            reasons.append(_t(lang,
                "  ⚠ CPU throttluje - ogranicza mu się moc (przegrzanie lub brak zasilania)",
                "  ⚠ CPU throttling - power is being limited (heat or power supply issue)"))

        # ── HDD-specific cause ─────────────────────────────────────
        if profile["is_hdd"]:
            reasons.append(_t(lang,
                "  ! Dysk HDD - typowa przyczyna spowolnień przy dużej aktywności plików",
                "  ! HDD detected - a common cause of slowdowns under heavy file activity"))

        if lang == "en":
            header = f"{self.PREFIX} Why is it slow - live check:"
            lines  = [header]
            if not reasons:
                lines.append(f"  CPU: {cpu:.0f}%  RAM: {ram:.0f}%  - both look OK right now.")
                lines.append("  Possible causes: background updates, antivirus scan, disk activity.")
            else:
                lines.extend(reasons)
            if top_procs:
                lines.append(f"  Top processes: {',  '.join(top_procs)}")
            lines.append("  💬 Type 'top processes' for full list, or 'optimization' to fix  [-> Optimization]")
        else:
            header = f"{self.PREFIX} Dlaczego jest wolno - live sprawdzenie:"
            lines  = [header]
            if not reasons:
                lines.append(f"  CPU: {cpu:.0f}%  RAM: {ram:.0f}%  - teraz wygląda OK.")
                lines.append("  Możliwe: aktualizacje w tle, antywirus, aktywność dysku.")
            else:
                lines.extend(reasons)
            if top_procs:
                lines.append(f"  Winowajcy: {',  '.join(top_procs)}")
            lines.append("  💬 Wpisz 'top procesy' po pełną listę, lub napraw  [-> Optimization]")

        # ── session reference - link to previously shown RAM spec ───
        ram_sess = session_memory.get_response_data("hw_ram")
        if ram_sess.get("total_gb") and ram > 70:
            typ = ram_sess.get("typical_avg")
            if typ:
                lines.append(_t(lang,
                    f"  (Wcześniej omawiany RAM: {ram_sess['total_gb']} GB, typowo {typ}% - teraz {ram:.0f}%)",
                    f"  (Earlier your RAM: {ram_sess['total_gb']} GB, typical {typ}% - now at {ram:.0f}%)"))

        # Historical context from stats engine
        try:
            avg7 = float(patterns.get("typical_cpu_avg") or 0)
            if avg7 > 0 and cpu > avg7 + 15:
                lines.append(_t(lang,
                    f"  ⚠ CPU ({cpu:.0f}%) jest {cpu - avg7:.0f}% powyżej Twojej 7-dniowej normy ({avg7:.0f}%).",
                    f"  ⚠ CPU ({cpu:.0f}%) is {cpu - avg7:.0f}% above your 7-day avg ({avg7:.0f}%)."))
        except Exception:
            pass

        return lines

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

        # ── get typical avg from session data or patterns ───────────
        ram_sess  = session_memory.get_response_data("hw_ram")
        typ_avg   = ram_sess.get("typical_avg")
        if typ_avg is None:
            patterns = user_knowledge.get_all_patterns()
            typ_avg  = patterns.get("typical_ram_avg")

        if lang == "en":
            header = (
                f"{self.PREFIX} Why is RAM high - {ram:.0f}%"
                f" ({used} GB used / {free} GB free):"
            )
            lines = [header]

            # ── low-RAM context ─────────────────────────────────────
            if profile["ram_low"]:
                lines.append(
                    f"  ⚠ You only have {profile['ram_gb']:.0f} GB total - "
                    f"{ram:.0f}% means only ~{free} GB breathing room."
                )

            if top_ram:
                lines.append(f"  Top consumers: {',  '.join(top_ram)}")

            # ── delta vs typical ────────────────────────────────────
            if typ_avg:
                delta_str = _delta_label(ram, typ_avg, "en")
                if delta_str:
                    lines.append(f"  Context: {delta_str}")

            if ram > 90:
                lines.append("  ⚠ Critical - system is likely using pagefile (slow disk swapping).")
                lines.append("  Fix: close unused apps  [-> Optimization]")
                if profile["is_hdd"]:
                    lines.append("  ⚠ HDD detected - pagefile on HDD is very slow. Consider Virtual Memory on faster drive  [-> Virtual Memory]")
            elif ram > 75:
                lines.append("  High but manageable. Browser tabs are usually the main cause.")
                lines.append("  Reduce background apps  [-> Optimization]  ·  or add swap  [-> Virtual Memory]")
                if profile["ram_low"]:
                    lines.append(f"  Long-term: {profile['ram_gb']:.0f} GB is limiting - more RAM would help.")
            else:
                lines.append("  Within normal range - Windows pre-loads data into RAM.")
                lines.append("  Free RAM is wasted RAM. Only act if above 85%.")

        else:
            header = (
                f"{self.PREFIX} Dlaczego RAM wysoki - {ram:.0f}%"
                f" ({used} GB zajęte / {free} GB wolne):"
            )
            lines = [header]

            if profile["ram_low"]:
                lines.append(
                    f"  ⚠ Masz tylko {profile['ram_gb']:.0f} GB - "
                    f"{ram:.0f}% to zostaje ci ~{free} GB na resztę."
                )

            if top_ram:
                lines.append(f"  Główni winowajcy: {',  '.join(top_ram)}")

            if typ_avg:
                delta_str = _delta_label(ram, typ_avg, "pl")
                if delta_str:
                    lines.append(f"  Kontekst: {delta_str}")

            if ram > 90:
                lines.append("  ⚠ Krytyczne - system używa prawdopodobnie pliku wymiany (wolno).")
                lines.append("  Napraw: zamknij zbędne programy  [-> Optimization]")
                if profile["is_hdd"]:
                    lines.append("  ⚠ HDD wykryty - plik wymiany na HDD jest bardzo wolny  [-> Virtual Memory]")
            elif ram > 75:
                lines.append("  Wysoki, zarządzalny. Główna przyczyna: karty przeglądarki.")
                lines.append("  Zamknij aplikacje w tle  [-> Optimization]  ·  lub dodaj pamięć  [-> Virtual Memory]")
                if profile["ram_low"]:
                    lines.append(f"  Długofalowo: {profile['ram_gb']:.0f} GB to za mało - więcej RAM by pomogło.")
            else:
                lines.append("  To normalny zakres - Windows wstępnie ładuje dane do RAM.")
                lines.append("  Wolny RAM = zmarnowany RAM. Reaguj dopiero powyżej 85%.")

        return lines

    def _resp_browser_cache(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        try:
            import psutil
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
            sev_en = f"HIGH - {total_mb:.0f} MB total across all browser processes."
            sev_pl = f"WYSOKI - {total_mb:.0f} MB łącznie dla wszystkich procesów przeglądarki."
            tip_en = "Consider closing unused tabs, disabling heavy extensions."
            tip_pl = "Zamknij nieużywane zakładki, wyłącz ciężkie rozszerzenia."
        elif total_mb > 800:
            sev_en = f"MODERATE - {total_mb:.0f} MB in use."
            sev_pl = f"UMIARKOWANY - {total_mb:.0f} MB w użyciu."
            tip_en = "Cache is normal for this size. Close tabs you don't need."
            tip_pl = "Cache OK przy tym rozmiarze. Zamknij zakładki których nie używasz."
        else:
            sev_en = f"LOW - {total_mb:.0f} MB, nothing to worry about."
            sev_pl = f"NISKI - {total_mb:.0f} MB, bez obaw."
            tip_en = "Browser memory is healthy. Cache isn't slowing you down."
            tip_pl = "Pamięć przeglądarki OK. Cache nie spowalnia komputera."

        if lang == "en":
            lines = [f"{P} Browser memory footprint - {sev_en}"]
            lines += browser_lines
            lines.append(f"  Tip: {tip_en}")
            lines.append("  To clear cache: Ctrl+Shift+Del in any browser.")
        else:
            lines = [f"{P} Pamięć przeglądarki - {sev_pl}"]
            lines += browser_lines
            lines.append(f"  Wskazówka: {tip_pl}")
            lines.append("  Wyczyść cache: Ctrl+Shift+Del w dowolnej przeglądarce.")
        lines.append(_followup("perf", lang))
        return lines

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
                lines.append(f"  7-day avg: {hist_avg:.0f}%  ->  today is {sign}{delta:.0f}% vs baseline")
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
                lines.append(f"  Śr. 7 dni: {hist_avg:.0f}%  ->  dziś {sign}{delta:.0f}% vs bazowy")
            if days:
                lines.append("  Dane dzienne (ostatnie 7 dni):")
                for d in days[:5]:
                    lines.append(f"    {d['date_str']}  śr. {d['ram_avg']:.0f}%  max {d['ram_max']:.0f}%")
            else:
                lines.append("  Historia wielodniowa narośnie po kilku sesjach.")
        lines.append(_followup("perf", lang))
        return lines

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

        sev_en = "HIGH - swap heavily used, expect slowdowns" if swap_pct > 60 else \
                 "MODERATE" if swap_pct > 25 else "LOW - healthy"
        sev_pl = "WYSOKI - swap mocno zajęty, spodziewaj się spowolnienia" if swap_pct > 60 else \
                 "UMIARKOWANY" if swap_pct > 25 else "NISKI - OK"

        if lang == "en":
            lines = [f"{P} Swap / Pagefile: {swap_pct:.0f}% used  ({swap_used:.1f} GB / {swap_tot:.1f} GB)  -> {sev_en}"]
            lines.append(f"  Physical RAM: {vm.percent:.0f}% full  ({vm.used/1e9:.1f} / {vm.total/1e9:.1f} GB)")
            if top:
                lines.append("  Processes with largest virtual footprint (likely swap users):")
                for name, mb in top:
                    lines.append(f"    • {name[:22]:<22}  ~{mb:.0f} MB on swap")
            if swap_pct > 60:
                lines.append("  Fix: Close background apps, add more RAM, or increase pagefile size.")
            else:
                lines.append("  Swap is normal - Windows uses it as a buffer even when RAM is available.")
        else:
            lines = [f"{P} Swap / Plik wymiany: {swap_pct:.0f}% zajęty  ({swap_used:.1f} GB / {swap_tot:.1f} GB)  -> {sev_pl}"]
            lines.append(f"  Fizyczny RAM: {vm.percent:.0f}% pełny  ({vm.used/1e9:.1f} / {vm.total/1e9:.1f} GB)")
            if top:
                lines.append("  Procesy z największym wirtualnym śladem (prawdopodobni użytkownicy swap):")
                for name, mb in top:
                    lines.append(f"    • {name[:22]:<22}  ~{mb:.0f} MB na swap")
            if swap_pct > 60:
                lines.append("  Rozwiązanie: zamknij programy w tle, dodaj RAM lub zwiększ rozmiar pliku wymiany.")
            else:
                lines.append("  Swap normalny - Windows używa go jako bufora nawet gdy RAM jest dostępny.")
        lines.append(_followup("perf", lang))
        return lines

    def _resp_network_usage(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
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
            lines = [f"{P} Network activity - 1-second snapshot:"]
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
                lines.append(f"  Note: CPU is at {cpu_load:.0f}% - network processing may be contributing.")
        else:
            lines = [f"{P} Aktywność sieciowa - pomiar 1-sekundowy:"]
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
                lines.append(f"  Uwaga: CPU jest na {cpu_load:.0f}% - obsługa sieci może dokładać swoje.")
        lines.append(_followup("perf", lang))
        return lines

    def _resp_top_resource_hog(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Shows top 5 processes by RAM usage and top 5 by disk I/O bytes.
        Straight psutil data - no fabrication.
        """
        msg_lower = (r.raw_text or "").lower()
        want_disk = any(w in msg_lower for w in ("disk", "dysk", "io", "i/o", "storage"))
        want_ram  = any(w in msg_lower for w in ("ram", "pamię", "memory", "mem"))

        # Default: show both unless user was specific
        show_ram  = want_ram  or (not want_disk)
        show_disk = want_disk or (not want_ram)

        lines = [_t(lang,
            f"{self.PREFIX} Największe pochłaniacze zasobów:",
            f"{self.PREFIX} Top resource consumers:")]

        try:
            import psutil

            # ── TOP RAM consumers ──────────────────────────────────────────
            if show_ram:
                procs_ram: list[tuple[str, float]] = []
                for proc in psutil.process_iter(["name", "memory_info"]):
                    try:
                        mi = proc.info.get("memory_info")
                        if mi:
                            mb = (mi.rss or 0) / (1024 ** 2)
                            if mb > 10:
                                procs_ram.append((proc.info["name"] or "?", mb))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                procs_ram.sort(key=lambda x: x[1], reverse=True)
                lines.append("")
                lines.append(_t(lang,
                    "  🧠 TOP 5 - RAM (RSS):",
                    "  🧠 TOP 5 - RAM (RSS):"))
                for name, mb in procs_ram[:5]:
                    gb_str = f"{mb/1024:.2f} GB" if mb > 1024 else f"{mb:.0f} MB"
                    lines.append(f"  - {name[:36]:<36}  {gb_str}")

            # ── TOP Disk I/O consumers ─────────────────────────────────────
            if show_disk:
                procs_io: list[tuple[str, float]] = []
                for proc in psutil.process_iter(["name", "io_counters"]):
                    try:
                        io = proc.info.get("io_counters")
                        if io:
                            total_mb = ((io.read_bytes or 0) + (io.write_bytes or 0)) / (1024 ** 2)
                            if total_mb > 1:
                                procs_io.append((proc.info["name"] or "?", total_mb))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                procs_io.sort(key=lambda x: x[1], reverse=True)
                lines.append("")
                lines.append(_t(lang,
                    "  💾 TOP 5 - I/O dysku (łączne od uruchomienia):",
                    "  💾 TOP 5 - Disk I/O (cumulative since boot):"))
                if procs_io:
                    for name, mb in procs_io[:5]:
                        gb_str = f"{mb/1024:.1f} GB" if mb > 1024 else f"{mb:.0f} MB"
                        lines.append(f"  - {name[:36]:<36}  {gb_str}")
                else:
                    lines.append(_t(lang,
                        "  Brak danych I/O (Windows może wymagać uprawnień admina).",
                        "  No I/O data (Windows may require admin rights for this)."))

        except Exception:
            lines.append(_t(lang,
                "  Nie można pobrać danych procesów.",
                "  Cannot fetch process data."))

        lines.append("")
        lines.append(_t(lang,
            "  💡 Duże I/O nie znaczy problem - to mogą być aktualizacje lub indeksowanie.",
            "  💡 High disk I/O isn't always a problem - it may be updates or indexing."))
        lines.append(_followup("process", lang))
        return lines

    def _resp_ram_flush(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
            vm = psutil.virtual_memory()
            now = f"{vm.percent:.0f}% ({vm.used/(1024**3):.1f}/{vm.total/(1024**3):.0f} GB)"
        except Exception:
            now = "-"
        return [
            _t(lang, f"{self.PREFIX} RAM teraz: {now}",
                     f"{self.PREFIX} RAM right now: {now}"),
            _t(lang,
               "  Auto RAM Flush działa w [-> Optimization]: czeka aż presja "
               "utrzyma się >75% przez 30 s i dopiero wtedy zwalnia cache "
               "(SetSystemFileCacheSize + EmptyWorkingSet).",
               "  Auto RAM Flush lives in [-> Optimization]: it waits for "
               "sustained >75% pressure for 30 s, then releases cache "
               "(SetSystemFileCacheSize + EmptyWorkingSet)."),
            _t(lang, "  Sztuczka to nie flush - to wiedzieć, kiedy NIE flushować.",
                     "  The real trick isn't the flush - it's knowing when NOT to."),
        ]


    def _resp_optimize_guide(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """Master 5-step optimization flow (FlowEngine). The engine owns the
        step state; 'dalej/tak/pomiń/stop' are handled in chat_handler before
        normal routing, so the whole guide never loses its place."""
        import hck_gpt.responses.flows  # noqa: F401  (registers flows once)
        from hck_gpt.engine.flow_engine import flow_engine
        out = flow_engine.start("optimize", self, lang)
        return [f"{self.PREFIX} {out[0]}"] + out[1:] if out else \
            [self.PREFIX + _t(lang, " Przewodnik chwilowo niedostępny.",
                                    " Guide temporarily unavailable.")]
