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

    @staticmethod
    def _game_installed(game_name: str) -> bool:
        """Whether a game with this name is in an installed Steam / Epic /
        GOG library folder (folder names, read once)."""
        try:
            import os
            import re
            from core import game_detect
            key = re.sub(r"[^a-z0-9]", "", game_name.lower())
            aliases = {"cs2": "counterstrikeglobaloffensive", "gtav": "grandtheftautov",
                       "witcher3": "thewitcher3"}
            want = {key, aliases.get(key, key)}
            roots = getattr(game_detect, "_LIB_FOLDERS", None)
            if roots is None:
                roots = set()
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                        steam = winreg.QueryValueEx(k, "SteamPath")[0]
                    paths = [os.path.join(steam, "steamapps", "common")]
                    vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
                    if os.path.exists(vdf):
                        txt = open(vdf, encoding="utf-8", errors="replace").read()
                        paths += [os.path.join(p.replace("\\\\", "\\"), "steamapps", "common")
                                  for p in re.findall(r'"path"\s+"([^"]+)"', txt)]
                    for pth in paths:
                        if os.path.isdir(pth):
                            roots |= {re.sub(r"[^a-z0-9]", "", d.lower()) for d in os.listdir(pth)}
                except Exception:
                    pass
                game_detect._LIB_FOLDERS = roots
            return any(w and any(w in r_ for r_ in roots) for w in want)
        except Exception:
            return False

    def _resp_game_can_run(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Checks if the user's PC meets minimum/recommended requirements
        for a specific game detected in the message text.
        Uses live RAM, GPU VRAM (from WMI), and disk data.
        """
        from hck_gpt.memory.user_knowledge import user_knowledge

        msg_lower = (r.raw_text or "").lower()

        # GTA 6 is not on PC yet; "gta 6" used to match "gta" and got the
        # GTA V requirements (2026-11-17)
        import re as _re
        if _re.search(r"gta ?(6|vi)(?![0-9a-z])", msg_lower):
            return [_t(lang,
                f"{self.PREFIX} GTA 6 nie ma jeszcze wersji na PC ani oficjalnych wymagań.",
                f"{self.PREFIX} GTA 6 has no PC version or official requirements yet."),
                _t(lang,
                   "  Gdy Rockstar je poda, porównam je z Twoim sprzętem. Na dziś mogę sprawdzić GTA V.",
                   "  Once Rockstar publishes them I can compare them with your hardware. GTA V I can check today.")]

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
        raw_vram = (hw.get("gpu_vram_gb", "") or hw.get("gpu_vram", "")
                    or hw.get("vram", "") or "")
        try:
            vram_gb = float(str(raw_vram).replace("GB", "").replace("MB", "").strip())
            if "MB" in str(raw_vram):
                vram_gb /= 1024
        except Exception:
            vram_gb = None

        disk_name, disk_free_gb = _roomiest_drive()

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
        gpu_need  = game.get("gpu_high", 0)

        gpu_name = str(hw.get("gpu_model", "") or hw.get("gpu_name", "") or "")
        if not gpu_name:
            try:
                from hck_gpt.data.live_sensors import get as _ls_get
                gpu_name = str(_ls_get("gpu_name", "") or "")
            except Exception:
                gpu_name = ""
        gpu_score = _gpu_score(gpu_name)

        lines = [_t(lang,
            f"{self.PREFIX} Sprawdzam wymagania: {gname}",
            f"{self.PREFIX} Checking requirements: {gname}"),
            _t(lang, f"§STEP {gname} · Twój sprzęt i wymagania", f"§STEP {gname} · your hardware and the requirements")]

        # RAM: Windows reports a few hundred MB less than the modules hold,
        # 8 GB shows as 7.85 GB (third long test, 2026-11-17)
        ram_ok = ram_rec_ok = False
        if ram_gb is not None:
            ram_ok     = ram_gb >= ram_min * 0.9
            ram_rec_ok = ram_gb >= ram_rec * 0.9
            tag = "§OK " if ram_rec_ok else "§WARN "
            lines.append(tag + _t(lang,
                f"RAM: masz {ram_gb:.0f} GB  ·  minimum {ram_min} GB  ·  zalecane {ram_rec} GB",
                f"RAM: {ram_gb:.0f} GB installed  ·  minimum {ram_min} GB  ·  recommended {ram_rec} GB"))
        else:
            lines.append(_t(lang, f"  ? RAM: brak danych  (minimum {ram_min} GB)",
                            f"  ? RAM: no data  (minimum {ram_min} GB)"))

        vram_ok = vram_gb is None or vram_gb >= vram_min
        if vram_gb is not None or gpu_name:
            card = (gpu_name + (f", {vram_gb:.0f} GB VRAM" if vram_gb is not None else "")).strip(", ")
            lines.append(("§OK " if vram_ok else "§WARN ") + _t(lang,
                f"Karta: {card}  ·  minimum {vram_min} GB VRAM",
                f"Graphics: {card}  ·  minimum {vram_min} GB VRAM"))
        else:
            lines.append(_t(lang, f"  ? Karta graficzna: brak danych  (minimum {vram_min} GB VRAM)",
                            f"  ? Graphics card: no data  (minimum {vram_min} GB VRAM)"))

        # Disk: only for a game that is not installed yet, and on the drive
        # with the most room, not just C: (fifth long test: "0.5 TB free"
        # elsewhere, the answer counted the system drive only)
        installed = False
        try:
            installed = bool(self._game_installed(gname))
        except Exception:
            installed = False
        if installed:
            lines.append("§OK " + _t(lang, "Dysk: gra jest już zainstalowana.",
                                     "Disk: the game is already installed."))
        elif disk_free_gb is not None:
            lines.append(("§OK " if disk_free_gb >= disk_gb else "§WARN ") + _t(lang,
                f"Dysk: najwięcej miejsca ma {disk_name}, {disk_free_gb:.0f} GB wolnego  ·  gra zajmie ok. {disk_gb} GB",
                f"Disk: {disk_name} has the most room, {disk_free_gb:.0f} GB free  ·  the game takes about {disk_gb} GB"))
        lines.append(_t(lang, f"  CPU: wymagany {cpu_note}", f"  CPU: required {cpu_note}"))

        # Verdict: the minimum decides whether it starts at all, the card's
        # rough power decides the settings, RAM below the recommendation caps
        # them. Disk space never changes the verdict: it only says where.
        lines.append("")
        if ram_gb is None and vram_gb is None and not gpu_score:
            lines.append(_t(lang, "  ⚠ Za mało danych o sprzęcie: wpisz 'moje specs', żeby je uzupełnić.",
                            "  ⚠ Not enough hardware data: type 'my specs' to fill it in."))
        elif not ((ram_gb is None or ram_ok) and vram_ok):
            lines.append("§WARN " + _t(lang,
                f"Twój sprzęt nie spełnia minimalnych wymagań {gname}: gra może się nie uruchomić albo działać bardzo słabo.",
                f"Your hardware is below the minimum for {gname}: it may not start or will run very poorly."))
        else:
            if gpu_score and gpu_need:
                ratio = gpu_score / gpu_need
                level = 3 if ratio >= 1.6 else 2 if ratio >= 1.0 else 1 if ratio >= 0.6 else 0
            else:
                level = 2 if (ram_rec_ok and vram_gb is not None and vram_gb >= vram_min * 2) else 1
            if ram_gb is not None and not ram_rec_ok and level > 1:
                level = 1 if ram_gb < ram_rec * 0.6 else min(level, 2)
            pl = ["niskich", "średnich", "wysokich", "wysokich i ultra"][level]
            en = ["low", "medium", "high", "high and ultra"][level]
            lines.append(("§OK " if level >= 2 else "§WARN ") + _t(lang,
                f"{gname} pójdzie, w 1080p spodziewaj się {pl} ustawień.",
                f"{gname} will run; at 1080p expect {en} settings."))
            if gpu_score and gpu_need:
                lines.append(_t(lang, "  Ustawienia to szacunek z mocy karty graficznej, nie pomiar w tej grze.",
                                "  The settings are an estimate from the graphics card's power, not a test in this game."))
            if ram_gb is not None and not ram_rec_ok:
                lines.append(_t(lang,
                    f"  RAM poniżej zalecanych {ram_rec} GB: zamknij przeglądarkę i komunikatory przed grą, inaczej możliwe przycięcia.",
                    f"  RAM below the recommended {ram_rec} GB: close the browser and chat apps before playing, or expect stutter."))
        try:
            from hck_gpt.memory.session_memory import session_memory
            session_memory.note_reference("game", gname, "game_can_run")
        except Exception:
            pass
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
        lines += _current_games(lang)
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


_GENRE_NAMES = {
    "fps": ("strzelanka", "shooter"), "moba": ("MOBA", "MOBA"), "action": ("akcja", "action"),
    "rpg": ("RPG", "RPG"), "cozy": ("spokojna", "cozy"), "sim": ("symulator", "simulation"),
    "strategy": ("strategia", "strategy"), "survival": ("survival", "survival"),
    "sandbox": ("sandbox", "sandbox"), "racing": ("wyścigi", "racing"), "sports": ("sport", "sports"),
    "horror": ("horror", "horror"), "party": ("imprezowa / co-op", "party / co-op"),
    "puzzle": ("logiczna / karciana", "puzzle / cards"),
}


def _current_games(lang: str) -> list:
    """'  Gra: PlateUp! (spokojna)' for every game running now."""
    out = []
    try:
        from ui.components.gaming_toast import gaming_watcher
        from core.game_library import resolve
        for exe in sorted(getattr(gaming_watcher, "_active", set())):
            info = resolve(exe, getattr(gaming_watcher, "_paths", {}).get(exe))
            g = _GENRE_NAMES.get(info["genre"])
            kind = f" ({g[1] if lang == 'en' else g[0]})" if g else ""
            out.append(_t(lang, f"  Gra: {info['name']}{kind}", f"  Game: {info['name']}{kind}"))
    except Exception:
        pass
    return out


def _roomiest_drive():
    """(name, free GB) of the local fixed drive with the most free space."""
    try:
        import psutil
        best = (None, None)
        for part in psutil.disk_partitions(all=False):
            opts = (part.opts or "").lower()
            if "cdrom" in opts or "removable" in opts or "remote" in opts or not part.fstype:
                continue
            try:
                free = psutil.disk_usage(part.mountpoint).free / (1024 ** 3)
            except Exception:
                continue
            if best[1] is None or free > best[1]:
                best = (part.mountpoint.rstrip("\\"), free)
        return best
    except Exception:
        return (None, None)


# Rough 1080p power of a graphics card, GTX 1060 = 100. Only for "which
# settings" in the requirements answer, never shown as a number.
_GPU_SCORES = [
    ("RTX 4090", 400), ("RTX 4080", 330), ("RTX 4070 TI", 280), ("RTX 4070", 240), ("RTX 4060 TI", 190), ("RTX 4060", 165),
    ("RTX 5090", 480), ("RTX 5080", 360), ("RTX 5070 TI", 310), ("RTX 5070", 260), ("RTX 5060 TI", 210), ("RTX 5060", 180),
    ("RTX 3090", 300), ("RTX 3080", 270), ("RTX 3070", 210), ("RTX 3060 TI", 185), ("RTX 3060", 155), ("RTX 3050", 115),
    ("RTX 2080", 200), ("RTX 2070", 170), ("RTX 2060", 140), ("GTX 1660", 115), ("GTX 1650", 75),
    ("GTX 1080", 160), ("GTX 1070", 130), ("GTX 1060", 100), ("GTX 1050", 55), ("GTX 970", 85), ("GTX 960", 55),
    ("RX 9070", 300), ("RX 7900", 330), ("RX 7800", 250), ("RX 7700", 220), ("RX 7600", 160),
    ("RX 6950", 290), ("RX 6900", 280), ("RX 6800", 250), ("RX 6750", 205), ("RX 6700", 195),
    ("RX 6650", 160), ("RX 6600", 150), ("RX 6500", 75), ("RX 5700", 145), ("RX 5600", 125), ("RX 5500", 90),
    ("RX 590", 100), ("RX 580", 95), ("RX 570", 85),
    ("ARC B580", 170), ("ARC A770", 160), ("ARC A750", 145), ("ARC A380", 60),
]


def _gpu_score(name: str) -> int:
    n = " ".join((name or "").upper().replace("-", " ").split())
    for key, score in _GPU_SCORES:
        if key in n:
            return score
    return 0
