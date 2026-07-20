"""hck_gpt.responses.r_gaming - GamingResponses mixin (6 intent handlers).
Split out of the builder.py monolith; composed into ResponseBuilder via MRO."""
from hck_gpt.responses.common import (  # shared helpers/data
    List,
    Optional,
    ParseResult,
    _followup,
    _t,
)


class GamingResponses:
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
            lines.append(_t(lang, "  -> Aktualnie dominuje gaming.", "  -> Gaming is currently dominant."))
        elif w_pct > 50:
            lines.append(_t(lang, "  -> Aktualnie dominuje produktywność.", "  -> Productivity is currently dominant."))
        else:
            lines.append(_t(lang, "  -> Mix - nic nie dominuje wyraźnie.", "  -> Mixed session - nothing clearly dominant."))

        lines.append(_t(lang,
            "  💬 Pełna historia: zakładka Statistics -> Weekly",
            "  💬 Full history: Statistics -> Weekly tab"))
        return lines

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
            "  🌡 Kurz -> gorzsze chłodzenie -> CPU/GPU throttluje -> gorsza wydajność",
            "  🌡 Dust buildup -> worse cooling -> CPU/GPU throttles -> lower FPS"))
        lines.append(_t(lang,
            "  💾 Pełny dysk C: < 10 GB wolne -> Windows swap spowalnia grę",
            "  💾 Full drive C: < 10 GB free -> Windows swap slows the game"))
        lines.append(_t(lang,
            "  🔄 Aktualizacja sterownika GPU - czasem nowe wersje są gorsze dla starszych gier",
            "  🔄 GPU driver update - newer versions sometimes regress older titles"))
        lines.append(_t(lang,
            "  📦 Nowe apki w autostarcie pożerają RAM przy każdym starcie",
            "  📦 New startup apps eating RAM from boot"))

        # Trigger micro benchmark for disk
        self._trigger_micro_benchmark("disk_seq")
        lines.append("")
        lines.append(_t(lang,
            "  🔬 Uruchomiono micro-test dysku w tle - zapytaj 'jak szybki jest mój dysk' za 10s.",
            "  🔬 Disk micro-benchmark running in background - ask 'disk speed' in ~10s for results."))

        lines.append(_followup("perf", lang))
        return lines

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
                            f"  Przy tym CPU {cpu_peak:.0f}% - prawdopodobnie ciężka sesja gamingowa.",
                            f"  Alongside CPU {cpu_peak:.0f}% - likely a heavy gaming session."))
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

    def _resp_game_can_run(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Checks if the user's PC meets minimum/recommended requirements
        for a specific game detected in the message text.
        Uses live RAM, GPU VRAM (from WMI), and disk data.
        """
        from hck_gpt.memory.user_knowledge import user_knowledge

        msg_lower = (r.raw_text or "").lower()

        # Find which game the user is asking about
        game = None
        for key, data in self._GAME_DB.items():
            if key in msg_lower:
                game = data
                break

        hw = user_knowledge.get_all_hardware()

        # Get actual RAM (GB installed)
        ram_gb: Optional[float] = None
        try:
            import psutil
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        except Exception:
            pass
        if not ram_gb:
            raw_ram = hw.get("ram_total", "") or ""
            try:
                ram_gb = float(str(raw_ram).replace("GB", "").strip())
            except Exception:
                ram_gb = None

        # Get GPU VRAM (GB) from user_knowledge
        vram_gb: Optional[float] = None
        raw_vram = hw.get("gpu_vram", "") or hw.get("vram", "") or ""
        try:
            vram_gb = float(str(raw_vram).replace("GB", "").replace("MB", "").strip())
            if "MB" in str(raw_vram):
                vram_gb /= 1024
        except Exception:
            vram_gb = None

        # Get free disk space
        disk_free_gb: Optional[float] = None
        try:
            import psutil
            disk_free_gb = psutil.disk_usage("C:\\").free / (1024 ** 3)
        except Exception:
            pass

        if game is None:
            # Unknown game - give generic guidance
            lines = [_t(lang,
                f"{self.PREFIX} Nie rozpoznałem nazwy gry w pytaniu.",
                f"{self.PREFIX} I didn't recognise a game name in your question.")]
            lines.append(_t(lang,
                "  Zapytaj np.: 'czy dam radę uruchomić Cyberpunk 2077' / 'czy zagram w Fortnite'",
                "  Try: 'can my pc run Cyberpunk 2077' / 'can I play Fortnite'"))
            lines.append(_t(lang,
                "  Obsługiwane gry: CS2, Fortnite, Cyberpunk, Hogwarts Legacy, Minecraft,",
                "  Supported games: CS2, Fortnite, Cyberpunk, Hogwarts Legacy, Minecraft,"))
            lines.append(_t(lang,
                "    GTA V, Valorant, Elden Ring, Witcher 3, Apex, Warzone, Overwatch 2",
                "    GTA V, Valorant, Elden Ring, Witcher 3, Apex, Warzone, Overwatch 2"))
            return lines

        gname     = game["name"]
        ram_min   = game["ram_min"]
        ram_rec   = game["ram_rec"]
        vram_min  = game["vram_min"]
        disk_gb   = game["disk_gb"]
        cpu_note  = game["cpu_note"]

        lines = [_t(lang,
            f"{self.PREFIX} Sprawdzam wymagania: {gname}",
            f"{self.PREFIX} Checking requirements: {gname}")]

        # RAM check
        ram_ok = ram_rec_ok = False
        if ram_gb is not None:
            ram_ok     = ram_gb >= ram_min
            ram_rec_ok = ram_gb >= ram_rec
            if ram_rec_ok:
                ram_icon = "✓"
            elif ram_ok:
                ram_icon = "!"
            else:
                ram_icon = "✗"
            lines.append(_t(lang,
                f"  {ram_icon} RAM: {ram_gb:.0f} GB masz  /  min {ram_min} GB  /  rec {ram_rec} GB",
                f"  {ram_icon} RAM: {ram_gb:.0f} GB installed  /  min {ram_min} GB  /  rec {ram_rec} GB"))
        else:
            lines.append(_t(lang,
                f"  ? RAM: brak danych  (wymagane min {ram_min} GB)",
                f"  ? RAM: no data available  (required min {ram_min} GB)"))

        # VRAM check
        if vram_gb is not None:
            vram_ok = vram_gb >= vram_min
            vram_icon = "✓" if vram_ok else "✗"
            lines.append(_t(lang,
                f"  {vram_icon} VRAM GPU: {vram_gb:.0f} GB masz  /  min {vram_min} GB",
                f"  {vram_icon} VRAM GPU: {vram_gb:.0f} GB installed  /  min {vram_min} GB"))
        else:
            lines.append(_t(lang,
                f"  ? VRAM GPU: brak danych  (wymagane min {vram_min} GB)",
                f"  ? VRAM GPU: no data  (required min {vram_min} GB)"))

        # Disk check
        if disk_free_gb is not None:
            disk_ok = disk_free_gb >= disk_gb
            disk_icon = "✓" if disk_ok else "✗"
            lines.append(_t(lang,
                f"  {disk_icon} Dysk wolne: {disk_free_gb:.0f} GB  /  wymagane ~{disk_gb} GB",
                f"  {disk_icon} Disk free: {disk_free_gb:.0f} GB  /  required ~{disk_gb} GB"))
        else:
            lines.append(_t(lang,
                f"  ? Dysk: brak danych  (wymagane ~{disk_gb} GB wolnego)",
                f"  ? Disk: no data  (need ~{disk_gb} GB free)"))

        lines.append(_t(lang,
            f"  CPU: wymagany {cpu_note}",
            f"  CPU: required {cpu_note}"))

        # Verdict
        lines.append("")
        can_run    = (ram_gb is None or ram_ok) and (vram_gb is None or vram_gb >= vram_min)
        can_ultra  = (ram_gb is None or ram_rec_ok) and (vram_gb is None or vram_gb >= vram_min * 2)
        no_data    = ram_gb is None and vram_gb is None

        if no_data:
            lines.append(_t(lang,
                "  ⚠ Za mało danych sprzętowych - sprawdź 'moje specs' aby je wypełnić.",
                "  ⚠ Not enough hardware data - type 'my specs' to populate it."))
        elif not can_run:
            lines.append(_t(lang,
                f"  ✗ Twój sprzęt NIE SPEŁNIA minimalnych wymagań {gname}.",
                f"  ✗ Your hardware does NOT meet minimum requirements for {gname}."))
            lines.append(_t(lang,
                "  Gra może nie uruchomić się lub działać bardzo źle.",
                "  The game may not launch or will run very poorly."))
        elif can_ultra:
            lines.append(_t(lang,
                f"  ✓ {gname} pójdzie płynnie - masz zapas na wyższe ustawienia.",
                f"  ✓ {gname} will run smoothly - you have headroom for higher settings."))
        else:
            lines.append(_t(lang,
                f"  ! {gname} uruchomi się, ale spodziewaj się niskich/średnich ustawień.",
                f"  ! {gname} will launch but expect low to medium settings."))
            lines.append(_t(lang,
                "  Na ultra może być za wolno - spróbuj najpierw ustawień Medium.",
                "  Ultra settings will likely struggle - start with Medium."))

        lines.append(_followup("hw", lang))
        return lines

    def _resp_game_ready(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        checks = []
        def _chk(ok, pl, en):
            checks.append(("✅" if ok else "⚠️") + " " + _t(lang, pl, en))
        ct, gt = ls.get("cpu_temp", -1), ls.get("gpu_temp", -1)
        _chk(ct < 0 or ct < 75, f"CPU {self._dm_val(ct,'°C')} - chłodne na start",
                                f"CPU {self._dm_val(ct,'°C')} - cool to start")
        _chk(gt < 0 or gt < 70, f"GPU {self._dm_val(gt,'°C')} - gotowe",
                                f"GPU {self._dm_val(gt,'°C')} - ready")
        try:
            import psutil
            ram = psutil.virtual_memory().percent
            _chk(ram < 80, f"RAM {ram:.0f}% - jest zapas",
                           f"RAM {ram:.0f}% - headroom available")
        except Exception:
            pass
        vram = ls.get("gpu_vram_pct", -1)
        if vram >= 0:
            _chk(vram < 70, f"VRAM {vram:.0f}%", f"VRAM {vram:.0f}%")
        bad = sum(1 for c in checks if c.startswith("⚠"))
        head = _t(lang,
            f"{self.PREFIX} Gotowość do grania: " + ("PEŁNA 🎮" if bad == 0 else f"{bad} rzecz(y) do sprawdzenia"),
            f"{self.PREFIX} Game readiness: " + ("ALL CLEAR 🎮" if bad == 0 else f"{bad} thing(s) to check"))
        return [head] + [f"  {c}" for c in checks]

    def _resp_gaming_session(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        try:
            from core.thermal_baseline import thermal_baseline
            bucket = thermal_baseline.classify(ls.get("cpu_load", 0) or 0,
                                               ls.get("gpu_load", 0) or 0)
        except Exception:
            bucket = "?"
        hist = ls.get("session_hist") or {}
        gmax = (hist.get("gpu_temp") or [-1, -1])[1]
        lines = [_t(lang, f"{self.PREFIX} Sesja gamingowa - stan:",
                          f"{self.PREFIX} Gaming session - status:")]
        lines.append(_t(lang,
            f"  Tryb obciążenia: {bucket} · GPU {self._dm_val(ls.get('gpu_load'),'%')} "
            f"@ {self._dm_val(ls.get('gpu_temp'),'°C')} · clock {self._dm_val(ls.get('gpu_clk_gr'),' MHz')}",
            f"  Workload bucket: {bucket} · GPU {self._dm_val(ls.get('gpu_load'),'%')} "
            f"@ {self._dm_val(ls.get('gpu_temp'),'°C')} · clock {self._dm_val(ls.get('gpu_clk_gr'),' MHz')}"))
        if gmax and gmax >= 0:
            lines.append(_t(lang, f"  Szczyt GPU w tej sesji: {gmax:.0f}°C",
                                  f"  GPU peak this session: {gmax:.0f}°C"))
        lines.append(_t(lang,
            "  Nakładka In-Game: My PC → GAMING (FPS przez RTSS).",
            "  In-Game overlay: My PC → GAMING (FPS via RTSS)."))
        return lines

