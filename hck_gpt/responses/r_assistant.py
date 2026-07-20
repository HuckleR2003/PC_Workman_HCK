"""hck_gpt.responses.r_assistant - AssistantResponses mixin (10 intent handlers).
Split out of the builder.py monolith; composed into ResponseBuilder via MRO."""
from hck_gpt.responses.common import (  # shared helpers/data
    List,
    ParseResult,
    _t,
    random,
)


class AssistantResponses:
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
                "      'what risks does my pc have'  <- risk ranking",
                "",
                "  📊  Performance & Stats",
                "      'performance'  /  'stats'  /  'top processes'  /  'uptime'",
                "      'what changed in performance'  /  'compare sessions'",
                "      'what changed on my pc since yesterday'  <- broad changes view",
                "",
                "  🔍  Why is it doing that?",
                "      'why is it slow'  /  'why is ram so high'  /  'why is disk at 100'",
                "      'which process is draining my battery right now'  /  'unnecessary programs'",
                "",
                "  ⚡  Optimization",
                "      'speed up pc'  /  'turbo boost'  /  'startup programs'",
                "      'optimization'  /  'power plan'  /  'disk speed'",
                "      'is it safe to disable X from startup'  <- startup safety check",
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
            "      'co zagraża mojemu PC'  <- ranking ryzyk",
            "",
            "  📊  Wydajność i statystyki",
            "      'wydajność'  /  'stats'  /  'top procesy'  /  'czas sesji'",
            "      'co się zmieniło w wydajności'  /  'porównaj sesje'",
            "      'co się zmieniło od wczoraj'  <- szeroki widok zmian",
            "",
            "  🔍  Dlaczego tak działa?",
            "      'dlaczego laguje'  /  'dlaczego ram wysoki'  /  'dysk na 100 dlaczego'",
            "      'który proces rozładowuje baterię teraz'  /  'niepotrzebne programy'",
            "",
            "  ⚡  Optymalizacja",
            "      'przyspiesz komputer'  /  'turbo boost'  /  'autostart'",
            "      'optymalizacja'  /  'plan zasilania'  /  'jak przyspieszyć dysk'",
            "      'czy mogę wyłączyć X ze startu'  <- sprawdzenie bezpieczeństwa autostartu",
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

    def _resp_small_talk(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_gpt.context.system_context import system_context
            snap = system_context.snapshot()
            cpu = f"{snap.get('cpu_pct', 0) or 0:.0f}"
            ram = f"{snap.get('ram_pct', 0) or 0:.0f}"
        except Exception:
            cpu, ram = "?", "?"
        resp = self._pick_fresh("smalltalk", lang, self._SMALLTALK_PL, self._SMALLTALK_EN)
        out = [resp.replace("{P}", self.PREFIX).replace("{cpu}", cpu).replace("{ram}", ram)]

        if random.random() < 0.6:
            fav = self._favorite_process(lang)
            if fav:
                out.append(fav)
        return out

    def _resp_about_program(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ver = self._app_version()
        if lang == "en":
            return [
                f"{self.PREFIX} About PC Workman HCK v{ver}:",
                "  A real-time PC monitor + optimizer - runs fully on your machine,",
                "  nothing in the cloud.",
                "  • Live CPU / RAM / GPU tracking with history graphs",
                "  • hck_GPT - AI assistant (bilingual PL/EN, learns your patterns, Ollama-ready)",
                "  • Stats engine - daily/weekly usage history (local SQLite)",
                "  • Optimization Center - one-click TURBO BOOST, RAM flush",
                "  • Fan control editor, stability tests, hardware sensors",
                "  • DeepMonitor + 2.5D MAP OF COMPONENTS - live hardware view",
                "  • Process library - identifies 370+ running programs & games",
                "",
                "  Your data stays local - want proof it runs clean?  [-> Stability Tests]",
                "  💬 Try: 'specs'  'health'  'temperatures'  'what do you collect'",
            ]
        return [
            f"{self.PREFIX} O programie PC Workman HCK v{ver}:",
            "  Monitor i optymalizator PC w czasie rzeczywistym - działa w całości",
            "  na Twoim komputerze, nic nie idzie do chmury.",
            "  • Śledzenie CPU / RAM / GPU na żywo z wykresami historii",
            "  • hck_GPT - asystent AI (PL/EN, uczy się Twoich wzorców, gotowy na Ollama)",
            "  • Silnik statystyk - lokalna historia użytkowania (SQLite)",
            "  • Centrum optymalizacji - TURBO BOOST jednym kliknięciem, flush RAM",
            "  • Edytor krzywej wentylatora, testy stabilności, czujniki sprzętu",
            "  • DeepMonitor + MAPA PODZESPOŁÓW 2.5D - podgląd sprzętu na żywo",
            "  • Biblioteka procesów - identyfikuje 370+ programów i gier",
            "",
            "  Twoje dane zostają u Ciebie - chcesz dowód, że działa czysto?  [-> Stability Tests]",
            "  💬 Spróbuj: 'specyfikacja'  'zdrowie'  'temperatury'  'jakie dane zbierasz'",
        ]

    def _resp_about_author(self, r: ParseResult, lang: str = "pl") -> List[str]:
        if lang == "en":
            return [
                f"{self.PREFIX} PC Workman HCK was built by HCK Labs.",
                "  An independent one-person development project.",
                "  Focused on giving Windows users real insight into",
                "  what their PC is actually doing - no bloat, no cloud.",
            ]
        return [
            f"{self.PREFIX} PC Workman HCK został stworzony przez HCK Labs.",
            "  Niezależny, jednoosobowy projekt deweloperski.",
            "  Celem było danie użytkownikom Windows prawdziwego wglądu",
            "  w to, co dzieje się z ich komputerem - bez zbędnych rzeczy.",
        ]

    def _resp_privacy_data(self, r: ParseResult, lang: str = "pl") -> List[str]:
        if lang == "en":
            return [
                f"{self.PREFIX} Relax - I'm not spying on you. 🛡️",
                "  PC Workman runs locally, on your machine:",
                "  • I only remember hardware stats - CPU/RAM/GPU load, temperatures,",
                "    uptime - in a local SQLite database on your own disk.",
                "  • I never read your files, keystrokes, browser or anything personal.",
                "  • I never send your data anywhere without consent - every bit of",
                "    internet access is yours to control in Settings.",
                "  • Nothing is hidden: it all lives in plain files you can open.",
                "",
                "  Want to see for yourself how clean it runs?  [-> Stability Tests]",
            ]
        return [
            f"{self.PREFIX} Spokojnie - nie szpieguję Cię. 🛡️",
            "  PC Workman działa lokalnie, na Twoim komputerze:",
            "  • Zapamiętuję tylko statystyki sprzętu - obciążenie CPU/RAM/GPU,",
            "    temperatury, czas pracy - w lokalnej bazie SQLite na Twoim dysku.",
            "  • Nigdy nie czytam plików, klawiatury, przeglądarki ani niczego osobistego.",
            "  • Nigdy nie wysyłam Twoich danych bez zgody - każdy dostęp do",
            "    internetu w całości kontrolujesz w Ustawieniach.",
            "  • Nic nie jest ukryte: wszystko leży w zwykłych plikach, które otworzysz.",
            "",
            "  Chcesz sam zobaczyć, jak czysto działa?  [-> Stability Tests]",
        ]

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
                    "  It doesn't hate you - it's just exhausted.",
                    f"  The biggest culprit right now: {top_cpu_name}.",
                ]
            chrome_str = f" i {chrome_count} instancji Chrome" if chrome_count > 2 else ""
            startup_str = f" i {startup_total} programów startowych" if startup_total > 5 else ""
            return [
                f"{P} Bo masz RAM na {ram_pct:.0f}%{chrome_str}{startup_str}.",
                "  On Cię nie nienawidzi - po prostu jest wykończony.",
                f"  Największy winowajca teraz: {top_cpu_name}.",
            ]

        if any(w in text for w in ["głupi", "dumb", "stupid"]):
            chrome_str = f"Chrome z {chrome_count} procesami" if chrome_count > 1 else "sporo rzeczy"
            if lang == "en":
                return [
                    f"{P} Not dumb - just incredibly patient.",
                    f"  It's been running {chrome_str} for hours without complaining.",
                    f"  Current RAM: {ram_pct:.0f}%. That's the real test of endurance.",
                ]
            return [
                f"{P} Nie jest głupi - jest niesamowicie cierpliwy.",
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
                "  Każda zakładka = osobny proces - to jego styl życia (izolacja).",
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
                    "  Fix: Settings -> Windows Settings -> disable 'Launch on startup'.",
                ]
            return [
                f"{P} Discord działa w tle bo chce być 'zawsze gotowy'.",
                f"  {disc_str}",
                "  Zjada GPU przez overlay i RAM przez silnik Electron.",
                "  Fix: Ustawienia Discord -> Windows -> wyłącz 'Uruchamiaj przy starcie'.",
            ]

        if any(w in text for w in ["svchost", "szpieg", "spy"]):
            if lang == "en":
                return [
                    f"{P} svchost.exe - spy? Not exactly. Suspicious? Sometimes.",
                    f"  Right now there are {svchost_count} svchost instances running.",
                    "  Each one hosts a group of Windows services (networking, updates, etc).",
                    "  If one spikes CPU at night - probably Windows Update doing its thing.",
                ]
            return [
                f"{P} svchost.exe - szpieg? Niekoniecznie. Podejrzany? Czasem.",
                f"  Teraz działa {svchost_count} instancji svchost.",
                "  Każda hostuje grupę usług Windows (sieć, aktualizacje itp.).",
                "  Jeśli skacze CPU nocą - to prawdopodobnie Windows Update robi swoje.",
            ]

        if any(w in text for w in ["kac", "hangover", "ładuje się wolno", "wolno ładuje"]):
            if lang == "en":
                return [
                    f"{P} Loading slowly like it has a hangover? Classic symptom.",
                    f"  Startup programs: {startup_total}. That's {startup_total} things fighting for CPU on boot.",
                    f"  Top CPU hog right now: {top_cpu_name}.",
                    "  Cure: disable the heavy hitters  [-> Startup Manager]",
                ]
            return [
                f"{P} Ładuje się wolno jakby miało kaca? Klasyczny objaw.",
                f"  Programów startowych: {startup_total}. To {startup_total} rzeczy walczących o CPU podczas uruchamiania.",
                f"  Największy pożeracz CPU teraz: {top_cpu_name}.",
                "  Lekarstwo: wyłącz ciężkich kandydatów  [-> Startup Manager]",
            ]

        if any(w in text for w in ["timeout", "time-out"]):
            if lang == "en":
                return [
                    f"{P} Your PC could use a timeout, honestly.",
                    f"  RAM is at {ram_pct:.0f}%. Top offender: {top_cpu_name}.",
                    "  Closest thing to a timeout: close everything + restart.",
                    "  Or: Optimization tab -> TURBO BOOST for a quick reset.",
                ]
            return [
                f"{P} Twój PC naprawdę mógłby dostać timeout.",
                f"  RAM na {ram_pct:.0f}%. Winowajca: {top_cpu_name}.",
                "  Najbliższe timeout'owi: zamknij wszystko + restart.",
                "  Albo: zakładka Optimization -> TURBO BOOST = szybki reset systemu.",
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

    def _resp_greeting(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_gpt.context.system_context import system_context
            snap = system_context.snapshot()
            cpu_raw = float(snap.get("cpu_pct", 0) or 0)
            ram_raw = float(snap.get("ram_pct", 0) or 0)
            cpu = f"{cpu_raw:.0f}"
            ram = f"{ram_raw:.0f}"
        except Exception:
            cpu, ram, cpu_raw, ram_raw = "?", "?", 0.0, 0.0

        # Stress-aware greeting (same logic as first version)
        if cpu_raw > 80 or ram_raw > 85:
            resp = self._pick_fresh("greet_alert", lang, self._GREET_ALERT_PL, self._GREET_ALERT_EN)
        else:
            resp = self._pick_fresh("greeting", lang, self._GREET_INTROS_PL, self._GREET_INTROS_EN)

        resp = resp.replace("{P}", self.PREFIX).replace("{cpu}", cpu).replace("{ram}", ram)

        lines = [resp]
        # Engaging personal hook: the user's favourite app ("fancy CS2 again today?")
        fav = self._favorite_process(lang)
        if fav:
            lines.append(fav)
        else:
            # First greeting of the session with no fav hook -> note the CPU we see
            try:
                from hck_gpt.memory.session_memory import session_memory
                from hck_gpt.memory.user_knowledge import user_knowledge
                if not getattr(session_memory, "greeted_this_session", False):
                    session_memory.greeted_this_session = True
                    hw = user_knowledge.get_hardware("cpu_model")
                    if hw:
                        lines.append(_t(lang, f"  (Widzę: {hw})", f"  (I see: {hw})"))
            except Exception:
                pass
        return lines

    def _resp_thanks(self, r: ParseResult, lang: str = "pl") -> List[str]:
        resp = self._pick_fresh("thanks", lang, self._THANKS_PL, self._THANKS_EN)
        return [resp.replace("{P}", self.PREFIX)]

    def _resp_ai_context(self, r: ParseResult, lang: str = "pl") -> List[str]:
        lines = [_t(lang,
            f"{self.PREFIX} Czego nauczyłem się o TWOIM komputerze (wszystko lokalnie):",
            f"{self.PREFIX} What I've learned about YOUR machine (all local):")]
        _bpl = {"idle": "bezczynność", "light": "lekki", "medium": "średni",
                "heavy": "intensywny", "gaming": "gaming"}
        try:
            from core.thermal_baseline import thermal_baseline as tb
            pm     = tb.primary_metric()
            plabel = tb.metric_label(pm, lang)
            unit   = tb.metric_unit(pm)
            since  = tb.learning_since_str(lang)
            hrs    = tb.total_observed_hours()
            pct    = tb.overall_training_pct()
            lines.append(_t(lang,
                f"  ⏱ Uczę się od {since} · {hrs:.0f}h obserwacji · {pct}% skalibrowane",
                f"  ⏱ Learning for {since} · {hrs:.0f}h observed · {pct}% calibrated"))
            status  = tb.training_status(pm)
            learned = [(b, status[b]) for b in ("idle", "light", "medium", "heavy", "gaming")
                       if status.get(b, {}).get("n", 0) >= 20]
            if learned:
                lines.append(_t(lang, f"  Nauczone zakresy ({plabel}):",
                                      f"  Learned ranges ({plabel}):"))
                for b, info in learned:
                    bn = _bpl.get(b, b) if lang == "pl" else b
                    lines.append(f"    {bn:<11} {info['p5']:.0f}–{info['p95']:.0f}{unit}")
            else:
                lines.append(_t(lang,
                    "  Zbieram dane - zakresy pojawią się przy 20+ próbkach na tryb.",
                    "  Gathering data - ranges appear at 20+ samples per workload."))
            if "cpu_temp" not in tb.available_metrics():
                lines.append(_t(lang,
                    "  (temp. CPU: uruchom LibreHardwareMonitor, by ją odblokować)",
                    "  (CPU temp: run LibreHardwareMonitor to unlock it)"))
        except Exception:
            pass
        try:
            from core.voltage_analyzer import voltage_analyzer
            rails = len(voltage_analyzer.get_rail_stats() or {})
            if rails:
                lines.append(_t(lang,
                    f"  · {rails} szyn zasilania z medianą/MAD i regułami Nelsona",
                    f"  · {rails} voltage rails watched with median/MAD + Nelson rules"))
        except Exception:
            pass
        try:
            from hck_gpt.data.metrics_store import metrics_store
            n = len(metrics_store.get_history(hours=24 * 30))
            if n:
                lines.append(_t(lang,
                    f"  · {n} zapisanych migawek DeepMonitor (do 6 miesięcy wstecz)",
                    f"  · {n} stored DeepMonitor snapshots (up to 6 months of history)"))
        except Exception:
            pass
        lines.append(_t(lang,
            "  Zero chmury - pełny obraz w Learning Center (Monitoring & Alerts).",
            "  Zero cloud - the full picture is in the Learning Center (Monitoring & Alerts)."))
        return lines

    def _resp_tuneup_guide(self, r: ParseResult, lang: str = "pl") -> List[str]:
        import time as _tm
        raw = (getattr(r, "raw_text", "") or "").lower()
        fresh_words = ("podrasuj", "podrasować", "przewodnik", "krok po kroku",
                       "tune up", "guide", "step by step", "plan optymalizacji",
                       "poprowadź", "wyciśnij", "squeeze", "zacznij")
        step = getattr(self, "_guide_step", None)
        ts   = getattr(self, "_guide_ts", 0)
        expired = (_tm.time() - ts) > self._GUIDE_TTL
        if step is None or expired or any(w in raw for w in fresh_words):
            step = 0
        else:
            step += 1
        self._guide_step = step
        self._guide_ts   = _tm.time()

        nxt = _t(lang, "➡ Napisz 'dalej', gdy będziesz gotowy.",
                       "➡ Type 'next' when you're ready.")

        if step == 0:
            # Live mini-diagnosis to open with real numbers
            flagged = total = -1
            try:
                from ui.pages.startup_manager import _read_startup_entries
                ents = _read_startup_entries()
                total = len(ents)
                flagged = len([e for e in ents
                               if e.get("rec") in ("disable", "delay")
                               and e.get("impact") in ("high", "medium")])
            except Exception:
                pass
            try:
                import psutil
                ram = f"{psutil.virtual_memory().percent:.0f}%"
            except Exception:
                ram = "-"
            head = _t(lang,
                f"{self.PREFIX} Tuning krok po kroku - prowadzę Cię przez 4 kroki, "
                "każdy na TWOICH danych:",
                f"{self.PREFIX} Step-by-step tune-up - I'll walk you through 4 steps, "
                "each based on YOUR data:")
            diag = _t(lang,
                f"  Szybka diagnoza: RAM {ram}"
                + (f" · autostart: {total} wpisów, {flagged} wartych wyłączenia" if total >= 0 else ""),
                f"  Quick diagnosis: RAM {ram}"
                + (f" · startup: {total} entries, {flagged} worth disabling" if total >= 0 else ""))
            plan = _t(lang,
                "  1️⃣ Autostart → 2️⃣ Usługi → 3️⃣ Funkcje auto (RAM Flush, plan "
                "zasilania, hibernacja) → 4️⃣ Weryfikacja",
                "  1️⃣ Startup → 2️⃣ Services → 3️⃣ Auto features (RAM Flush, power "
                "plan, hibernation) → 4️⃣ Verify")
            return [head, diag, plan, nxt]

        if step == 1:
            flagged_names = []
            try:
                from ui.pages.startup_manager import _read_startup_entries
                ents = _read_startup_entries()
                flagged_names = [e["name"] for e in ents
                                 if e.get("rec") in ("disable", "delay")
                                 and e.get("impact") in ("high", "medium")][:4]
            except Exception:
                pass
            lines = [_t(lang, f"{self.PREFIX} KROK 1/4 - Autostart 🚀",
                              f"{self.PREFIX} STEP 1/4 - Startup 🚀")]
            if flagged_names:
                lines.append(_t(lang,
                    "  U Ciebie warte wyłączenia: " + ", ".join(flagged_names),
                    "  Worth disabling on your machine: " + ", ".join(flagged_names)))
            lines.append(_t(lang,
                "  Otwórz [-> Startup Manager], klikaj wpisy (zbiorą się na dole) "
                "i Zatwierdź. Wszystko odwracalne w zakładce Disabled.",
                "  Open [-> Startup Manager], click entries (they queue at the "
                "bottom) and confirm. Fully reversible in the Disabled tab."))
            return lines + [nxt]

        if step == 2:
            return [
                _t(lang, f"{self.PREFIX} KROK 2/4 - Usługi Windows ⚙",
                         f"{self.PREFIX} STEP 2/4 - Windows services ⚙"),
                _t(lang,
                   "  W [-> Services Manager] sekcja 'Unneeded' u góry to "
                   "najbezpieczniejsze wyłączenia. Klikasz Wyłącz → Zatwierdź. "
                   "Chipy G/E/M przypną usługę do trybu Gaming/Economy.",
                   "  In [-> Services Manager] the 'Unneeded' tier at the top is "
                   "the safest to stop. Click Disable → Confirm. G/E/M chips pin "
                   "a service to Gaming/Economy modes."),
                _t(lang,
                   "  Zasada: Essential ma kłódkę - tego nie ruszamy nigdy.",
                   "  Rule: Essential is locked - we never touch those."),
                nxt,
            ]

        if step == 3:
            try:
                import psutil
                ram = psutil.virtual_memory().percent
                ram_note = _t(lang,
                    f"  RAM teraz {ram:.0f}% - " +
                    ("Flush będzie miał co robić." if ram >= 70 else
                     "spokojnie, ale Flush przyda się przy grach."),
                    f"  RAM now {ram:.0f}% - " +
                    ("Flush will have work to do." if ram >= 70 else
                     "calm now, but Flush earns its keep in games."))
            except Exception:
                ram_note = ""
            lines = [
                _t(lang, f"{self.PREFIX} KROK 3/4 - Automaty, które pilnują za Ciebie 🤖",
                         f"{self.PREFIX} STEP 3/4 - Automations that watch for you 🤖"),
                _t(lang,
                   "  W [-> Optimization] włącz: Auto RAM Flush (>75% przez 30 s), "
                   "Turbo Power Plan (auto przy grze) i App Hibernation "
                   "(zamraża nieaktywne po 15-30 min).",
                   "  In [-> Optimization] enable: Auto RAM Flush (>75% for 30 s), "
                   "Turbo Power Plan (auto on game launch) and App Hibernation "
                   "(freezes idle apps after 15-30 min)."),
            ]
            if ram_note:
                lines.append(ram_note)
            return lines + [nxt]

        # step >= 4 - finale + reset
        self._guide_step = None
        return [
            _t(lang, f"{self.PREFIX} KROK 4/4 - Weryfikacja ✅",
                     f"{self.PREFIX} STEP 4/4 - Verify ✅"),
            _t(lang,
               "  Restart i sprawdzamy: 'health check' (ogólna forma), "
               "'raport czujników' (parametry), a za kilka dni 'trend tygodnia' "
               "- zobaczysz różnicę w danych, nie w obietnicach.",
               "  Restart, then check: 'health check' (overall shape), "
               "'sensor report' (parameters), and in a few days 'weekly trends' "
               "- you'll see the difference in data, not promises."),
            _t(lang,
               "  Tuning zakończony. Gdyby coś się pogorszyło - wszystko jest "
               "odwracalne (Disabled tab / przełączniki funkcji). 🖤",
               "  Tune-up complete. If anything gets worse - everything is "
               "reversible (Disabled tab / feature toggles). 🖤"),
        ]


    def _resp_recall_numbers(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """Response ledger recall: repeat the key numbers from recent answers
        ('ile to było?', 'what was that number'). Session-only by design."""
        from hck_gpt.memory.session_memory import session_memory
        recent = session_memory.last_recorded(3)
        if not recent:
            return [self.PREFIX + _t(lang,
                " Nie mam jeszcze zapisanych liczb z tej sesji - zapytaj "
                "najpierw o coś konkretnego (RAM, temperatury, przewodnik).",
                " No numbers recorded this session yet - ask me something "
                "concrete first (RAM, temps, the optimize guide).")]
        lines = [self.PREFIX + _t(lang, " Ostatnie zapisane wyniki:",
                                        " Recent recorded results:")]
        for intent, data in recent:
            vals = ", ".join(f"{k}={v}" for k, v in data.items()
                             if k != "recorded_at" and v is not None)
            if vals:
                lines.append(f"  · {intent}: {vals}")
        lines.append(_t(lang,
            "  (pamiętam je tylko w tej sesji - tak ma być)",
            "  (session-only memory - by design)"))
        return lines
