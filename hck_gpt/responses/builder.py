"""hck_gpt.responses.builder - ResponseBuilder facade.

The former 6.5k-line monolith now composes seven category mixins
(r_hardware, r_thermal, r_gaming, r_system, r_performance, r_insights,
r_assistant); shared helpers/data live in common.py. Dispatch is unchanged:
getattr(self, f"_resp_{intent}") resolves through the MRO.
"""
from hck_gpt.responses.common import (  # shared helpers/data
    List,
    Optional,
    ParseResult,
    _t,
    random,
)
from hck_gpt.responses.r_hardware import HardwareResponses
from hck_gpt.responses.r_upgrade import UpgradeResponses
from hck_gpt.responses.r_thermal import ThermalResponses
from hck_gpt.responses.r_gaming import GamingResponses
from hck_gpt.responses.r_system import SystemResponses
from hck_gpt.responses.r_performance import PerformanceResponses
from hck_gpt.responses.r_insights import InsightsResponses
from hck_gpt.responses.r_assistant import AssistantResponses


class ResponseBuilder(HardwareResponses, UpgradeResponses, ThermalResponses, GamingResponses, SystemResponses, PerformanceResponses, InsightsResponses, AssistantResponses):
    """Builds bilingual responses for every parsed intent (92 handlers)."""

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

    _INTENT_ALIASES: dict = {
        "fan_speed":          "fan_noise_history",   # fan speed queries -> history handler
        "session_digest":     "session_compare",     # session digest -> comparison handler
        "thermal_history":    "temp_comparison",     # thermal history -> temp comparison
        "symptom_freeze":     "crash_context",       # freezing symptoms -> crash context
        "symptom_noisy":      "fan_noise_history",   # noisy PC -> fan noise
        "compare_baseline":   "temp_comparison",     # baseline compare -> temp comparison
        "game_ready":         "game_can_run",        # game readiness -> game_can_run
        "morning_brief":      "stats",               # morning brief -> stats handler
        "gaming_session":     "gaming_vs_work_time", # gaming session -> gaming vs work
        "weekly_trends":      "perf_change",         # weekly trends -> perf change
        "process_deep_dive":  "process_info",        # deep dive -> process info
        "ram_flush":          "optimization",        # flush request -> optimization (actionable)
        "overclock_check":    "temperature",         # overclock -> temps
        "ai_context":         "explain_proactive",   # AI context -> explain proactive
        "thermal_prediction": "temp_comparison",     # prediction -> comparison
        "process_kill":       "process_info",        # kill request -> process info first
    }

    def build(self, result: ParseResult, lang: str = "pl") -> Optional[List[str]]:
        """
        Returns a list of message lines, or None if the intent
        is not handled here (falls back to legacy ChatHandler).
        Applies _INTENT_ALIASES so vocabulary intents without their own handler
        still return a sensible response instead of silent None.
        """
        intent  = self._INTENT_ALIASES.get(result.intent, result.intent)
        handler = getattr(self, f"_resp_{intent}", None)
        if handler is None:
            return None
        try:
            out = handler(result, lang)
            out = out if isinstance(out, list) else [out]
            # Conversation context memory: every answered intent leaves its
            # headline in the session ledger, so "ile to bylo?" / "wroc do
            # tego" can recall ANY earlier answer - not just guided flows.
            # Small-talk/meta intents are skipped (no numbers worth keeping).
            if intent not in self._NO_LEDGER and out:
                try:
                    from hck_gpt.memory.session_memory import session_memory
                    head = str(out[0]).replace(self.PREFIX, "").strip()
                    session_memory.record_response_data(
                        intent, {"headline": head[:140]})
                except Exception:
                    pass
            return out
        except Exception as _e:
            # Log handler errors so they appear in the diagnostic console
            # (not swallowed silently - helps during development)
            print(f"[builder] _resp_{intent} raised: {_e}")
            return None

    # Intents whose answers carry no recallable data - keep the ledger clean.
    _NO_LEDGER = frozenset({
        "greeting", "small_talk", "thanks", "help", "about_program",
        "about_author", "fun_roast", "recall_numbers", "privacy_data",
    })

    @staticmethod
    def _live_cpu_model() -> str:
        """Best-effort live CPU model name for when the hardware scan hasn't
        stored one yet (e.g. first seconds after launch, or WMI unavailable).
        Windows registry gives the clean marketing name; platform is the fallback."""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                name, _ = winreg.QueryValueEx(k, "ProcessorNameString")
                if name:
                    return str(name).strip()
        except Exception:
            pass
        try:
            import platform
            p = platform.processor()
            if p:
                return p.strip()
        except Exception:
            pass
        return ""

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

    _SMALLTALK_PL = [
        "{P} Dobrze, dzięki. Twój komputer ma {cpu}% CPU i {ram}% RAM - nieźle jak na pogawędkę.",
        "{P} W porządku. Bardziej martwię się o Twój RAM ({ram}%) niż o small talk.",
        "{P} Pytaj o PC - w tym jestem dobry. Na filozofię masz Google.",
        "{P} Funkcjonuję. CPU {cpu}%, RAM {ram}%. Ty jak?",
        "{P} Monitoruję wszystko po cichu. Jak chcesz wiedzieć co się dzieje - pytaj.",
        # Extended personality pool
        "{P} CPU {cpu}%, RAM {ram}%. Wszystko w normie. Mam nadzieję że u Ciebie tak samo.",
        "{P} Jestem tu, w tle, cały czas. Twój PC mi nie ucieka - CPU {cpu}%, RAM {ram}%.",
        "{P} Small talk to nie moja specjalność, ale PC? Na tym znam się świetnie. Pytaj.",
        "{P} Działam na CPU {cpu}% i RAM {ram}%. Twój komputer spokojny. Pytaj kiedy chcesz.",
        "{P} Monitoruję, uczę się, nic nie umyka. CPU {cpu}%, RAM {ram}%. Co Cię interesuje?",
        "{P} Cieszę się że piszesz. CPU {cpu}%, RAM {ram}% - wszystko OK. Co sprawdzamy?",
    ]

    _SMALLTALK_EN = [
        "{P} Fine, thanks. Your PC is at {cpu}% CPU and {ram}% RAM - not bad for small talk.",
        "{P} Doing ok. More concerned about your RAM ({ram}%) than chatting, honestly.",
        "{P} Ask me about your PC - that's my lane. For philosophy, try Google.",
        "{P} Running. CPU {cpu}%, RAM {ram}%. You?",
        "{P} Monitoring everything quietly. Ask if you want to know what's going on.",
        # Extended personality pool
        "{P} CPU {cpu}%, RAM {ram}%. All nominal. Hope the same goes for you.",
        "{P} Here in the background, always. PC isn't going anywhere - CPU {cpu}%, RAM {ram}%.",
        "{P} Small talk's not my thing, but PC hardware? That's exactly my thing. Ask away.",
        "{P} Running at CPU {cpu}%, RAM {ram}%. Your machine is calm. What do you want to check?",
        "{P} Still here, still watching. CPU {cpu}%, RAM {ram}% - nothing unusual. What's on your mind?",
        "{P} Good to hear from you. CPU {cpu}%, RAM {ram}% - everything's fine. What shall we look at?",
    ]

    _FAV_SKIP = {
        "system idle process", "system", "registry", "memory compression", "idle",
        "svchost.exe", "svchost", "explorer.exe", "dwm.exe", "csrss.exe",
        "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "smss.exe",
        "runtimebroker.exe", "searchhost.exe", "searchapp.exe", "taskhostw.exe",
        "ctfmon.exe", "fontdrvhost.exe", "sihost.exe", "conhost.exe", "audiodg.exe",
        "shellexperiencehost.exe", "startmenuexperiencehost.exe", "wmiprvse.exe",
        "applicationframehost.exe", "spoolsv.exe", "msmpeng.exe", "wininit",
        "python.exe", "pythonw.exe", "pc workman hck.exe", "pcworkman.exe",
    }

    _FAV_PL = [
        "  Widzę, że {app} to Twój faworyt - dziś też lecimy? 😏",
        "  {app} króluje w Twoich statystykach. Odpalamy znowu?",
        "  Czy dziś znowu lecimy z {app}? 😏",
        "  Stawiam, że dziś też odpalisz {app}. 😉",
    ]

    _FAV_EN = [
        "  {app} is your favourite, I can tell - going again today? 😏",
        "  {app} tops your stats. Firing it up again?",
        "  Fancy {app} again today? 😏",
        "  I'd bet {app} is on the menu today too. 😉",
    ]

    def _favorite_process(self, lang: str = "pl") -> Optional[str]:
        """A warm, engaging one-liner about the user's most-used app, or None."""
        try:
            from hck_stats_engine.query_api import query_api
            procs = query_api.get_top_processes_lifetime(top_n=12) or []
        except Exception:
            return None
        import random
        for p in procs:
            name = (p.get("process_name") or "").strip().lower()
            if not name or name in self._FAV_SKIP:
                continue
            if (p.get("days_active") or 0) < 1:
                continue
            disp = (p.get("display_name") or p.get("process_name") or "").strip()
            if not disp:
                continue
            pool = self._FAV_PL if lang == "pl" else self._FAV_EN
            return random.choice(pool).replace("{app}", disp)
        return None

    @staticmethod
    def _app_version() -> str:
        """Current app version from the ONE source (utils/app_version.py).
        The old file-parse of startup.py returned a stale fallback in frozen
        builds - the .py file is not shipped inside the dist."""
        try:
            from utils.app_version import APP_VERSION
            return APP_VERSION
        except Exception:
            return "unknown"

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

    _KNOWN_PROCS = {
        "svchost.exe": ("Svchost.exe to kontener systemowy - odpala wiele usług Windows jednocześnie. To normalne że jest ich kilka.",
                        "Svchost.exe is a Windows service host container - runs multiple system services. Multiple instances are normal."),
        "explorer.exe": ("Explorer.exe to powłoka Windows - pasek zadań, Eksplorator plików. NIE wyłączaj, bo zniknie UI.",
                         "Explorer.exe is the Windows shell - taskbar, File Explorer. Don't kill it or your UI will disappear."),
        "csrss.exe":    ("Csrss.exe to krytyczny proces Windows (Client/Server Runtime). Zabicie = błękit ekranu. Zostaw.",
                         "Csrss.exe is a critical Windows process (Client/Server Runtime). Killing it = BSOD. Leave it alone."),
        "lsass.exe":    ("Lsass.exe zarządza logowaniem i bezpieczeństwem. Nietykalny - zabicie restartuje system.",
                         "Lsass.exe manages Windows login and security. Untouchable - killing it forces a reboot."),
        "system":       ("'System' to rdzeń kernela Windows. Zawsze obecny, bezpieczny.",
                         "'System' is the Windows kernel process. Always present, always safe."),
        "dwm.exe":      ("Dwm.exe - Desktop Window Manager, renderuje efekty wizualne Windows. Normalne zużycie GPU.",
                         "Dwm.exe - Desktop Window Manager, renders Windows visual effects. Normal GPU usage."),
        "runtime broker": ("Runtime Broker zarządza uprawnieniami aplikacji UWP (Store). Normalnie niska aktywność.",
                           "Runtime Broker manages UWP app permissions (Store apps). Should be low activity normally."),
        "chrome.exe":   ("Chrome.exe - Google Chrome. Wiele procesów to norma (każda zakładka = osobny proces).",
                         "Chrome.exe - Google Chrome. Multiple processes are normal (each tab = separate process)."),
        "discord.exe":  ("Discord.exe - komunikator Discord. Może zużywać sporo RAM przez overlay i video.",
                         "Discord.exe - Discord app. Can use significant RAM due to overlay and video features."),
    }

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

    _STARTUP_SAFETY_KB: dict = {
        "chrome":       (True,  "Przeglądarka - nie potrzebuje startować z Windows, otwieraj ręcznie",
                                "Browser - no reason to start with Windows, launch manually"),
        "opera":        (True,  "Przeglądarka - wyłącz ze startu, otwieraj ręcznie",
                                "Browser - safe to disable, open manually"),
        "operagx":      (True,  "Przeglądarka gamingowa - bezpieczne do wyłączenia ze startu",
                                "Gaming browser - safe to disable from startup"),
        "brave":        (True,  "Przeglądarka - nie ma sensu startować z Windows",
                                "Browser - no reason to start with Windows"),
        "firefox":      (True,  "Przeglądarka - wyłącz ze startu",
                                "Browser - safe to disable from startup"),
        "spotify":      (True,  "Odtwarzacz muzyki - wyłącz, odpali się gdy klikniesz ikonę",
                                "Music player - disable, it starts when you click the icon"),
        "discord":      (True,  "Komunikator - bezpieczne do wyłączenia, uruchom ręcznie gdy potrzebny",
                                "Chat app - safe to disable, launch manually when needed"),
        "steam":        (True,  "Platforma gier - wyłącz ze startu, otwieraj gdy grasz",
                                "Gaming platform - disable from startup, open when gaming"),
        "epicgameslauncher": (True, "Launcher gier - nie potrzebuje startować z Windows",
                                    "Game launcher - no need to start with Windows"),
        "battlenet":    (True,  "Launcher Blizzard - wyłącz ze startu",
                                "Blizzard launcher - safe to disable"),
        "ubisoft":      (True,  "Launcher Ubisoft - wyłącz ze startu",
                                "Ubisoft launcher - safe to disable"),
        "skype":        (True,  "Skype - wyłącz ze startu; użytkownicy Discord/Teams nie potrzebują",
                                "Skype - disable from startup; Discord/Teams users don't need it"),
        "telegram":     (True,  "Telegram - wyłącz ze startu, uruchom ręcznie gdy potrzebny",
                                "Telegram - disable from startup, launch manually when needed"),
        "signal":       (True,  "Signal - wyłącz jeśli nie potrzebujesz powiadomień od razu po starcie",
                                "Signal - disable if you don't need instant notifications at boot"),
        "teams":        (None,  "Teams - zostaw jeśli używasz w pracy codziennie; wyłącz jeśli nie",
                                "Teams - keep it if used for work daily; disable otherwise"),
        "zoom":         (None,  "Zoom - zostaw jeśli masz regularne spotkania; inaczej wyłącz",
                                "Zoom - keep for regular meetings; disable otherwise"),
        "slack":        (None,  "Slack - zostaw jeśli używasz na co dzień",
                                "Slack - keep it if you use it daily"),
        "onedrive":     (None,  "OneDrive - wyłącz jeśli nie synchronizujesz aktywnie; zostaw jeśli tak",
                                "OneDrive - disable if not actively syncing; keep if you do"),
        "dropbox":      (None,  "Dropbox - wyłącz jeśli nie synchronizujesz aktywnie plików",
                                "Dropbox - disable if not actively syncing files"),
        "msedge":       (None,  "Edge - wyłączenie bezpieczne, możesz uruchomić ręcznie",
                                "Edge - safe to disable, launch manually when needed"),
        "realtek":      (False, "Sterownik audio Realtek - warto zostawić dla stabilności dźwięku",
                                "Realtek audio driver - worth keeping for audio stability"),
        "nvidia":       (False, "NVIDIA Panel / GeForce Experience - lepiej zostawić dla sterowników",
                                "NVIDIA Control Panel / GeForce Experience - better to keep"),
        "amd":          (False, "Oprogramowanie AMD - warto zostawić dla sterowników GPU/CPU",
                                "AMD software - worth keeping for GPU/CPU drivers"),
        "intel":        (False, "Intel software - powiązany ze sterownikami, lepiej zostaw",
                                "Intel software - driver-related, better to keep"),
        "windowsdefender": (False, "Windows Defender - NIE wyłączaj! To Twoje bezpieczeństwo systemowe",
                                   "Windows Defender - do NOT disable! This is your system security"),
    }

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
                    f"{self.PREFIX} Hardware (live - CPU model unknown, scan running):",
                    f"  CPU:  {cores_p} cores  /  {cores_l} threads  /  boost {boost} GHz",
                    f"  RAM:  {ram_gb} GB",
                    f"  OS:   Windows {platform.release()}",
                ]
            return [
                f"{self.PREFIX} Sprzęt (live, model CPU nieznany - skanowanie w toku):",
                f"  CPU:  {cores_p} rdzeni  /  {cores_l} wątków  /  boost {boost} GHz",
                f"  RAM:  {ram_gb} GB",
                f"  OS:   Windows {platform.release()}",
            ]
        except Exception:
            return [_t(lang,
                       f"{self.PREFIX} Brak danych - skanowanie sprzętu w toku.",
                       f"{self.PREFIX} No data yet - hardware scan running.")]

    def _no_data(self, intent: str, lang: str, what_missing: str = "") -> List[str]:
        """
        Return a structured 'data unavailable' message instead of hallucinating.
        Called by any handler when critical data is missing.
        """
        detail  = f"  ({what_missing})" if what_missing else ""
        if lang == "en":
            return [
                f"{self.PREFIX} ⚠ Not enough data for a reliable answer.",
                f"  I'd rather tell you honestly than guess.{detail}",
                "  What would help: use PC Workman for a few more days so the stats engine builds history.",
                "  Alternative: try 'health check' or 'stats' for what I do have.",
            ]
        return [
            f"{self.PREFIX} ⚠ Za mało danych żeby udzielić pewnej odpowiedzi.",
            f"  Wolę powiedzieć szczerze niż zgadywać.{detail}",
            "  Co pomoże: uruchom PC Workman przez kilka dni - silnik statystyk buduje historię.",
            "  Alternatywa: spróbuj 'zdrowie systemu' lub 'stats' - to mam na pewno.",
        ]

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

            # Map metric alias -> actual daily_summary column name
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
            arrow = "↑" if diff > 5 else ("↓" if diff < -5 else "->")
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

    _GAME_DB: dict = {
        "cs2":          {"name": "CS2",              "ram_min": 8,  "ram_rec": 16, "vram_min": 2, "disk_gb": 85,  "cpu_note": "i5-6600K / Ryzen 5 1600"},
        "csgo":         {"name": "CS:GO / CS2",      "ram_min": 8,  "ram_rec": 16, "vram_min": 2, "disk_gb": 85,  "cpu_note": "i5-6600K / Ryzen 5 1600"},
        "counter-strike":{"name":"CS2",              "ram_min": 8,  "ram_rec": 16, "vram_min": 2, "disk_gb": 85,  "cpu_note": "i5-6600K / Ryzen 5 1600"},
        "fortnite":     {"name": "Fortnite",         "ram_min": 8,  "ram_rec": 16, "vram_min": 2, "disk_gb": 40,  "cpu_note": "i5-7300U / Ryzen 3 3300U"},
        "cyberpunk":    {"name": "Cyberpunk 2077",   "ram_min": 12, "ram_rec": 16, "vram_min": 8, "disk_gb": 70,  "cpu_note": "i7-6700 / Ryzen 5 1600"},
        "hogwarts":     {"name": "Hogwarts Legacy",  "ram_min": 16, "ram_rec": 16, "vram_min": 8, "disk_gb": 85,  "cpu_note": "i7-8700 / Ryzen 5 3600"},
        "minecraft":    {"name": "Minecraft Java",   "ram_min": 4,  "ram_rec": 8,  "vram_min": 1, "disk_gb": 4,   "cpu_note": "any modern dual-core"},
        "gta":          {"name": "GTA V",            "ram_min": 8,  "ram_rec": 16, "vram_min": 4, "disk_gb": 90,  "cpu_note": "i5-3470 / FX-8350"},
        "gta5":         {"name": "GTA V",            "ram_min": 8,  "ram_rec": 16, "vram_min": 4, "disk_gb": 90,  "cpu_note": "i5-3470 / FX-8350"},
        "valorant":     {"name": "Valorant",         "ram_min": 4,  "ram_rec": 8,  "vram_min": 1, "disk_gb": 22,  "cpu_note": "i3-4150 / Ryzen 3 1200"},
        "elden ring":   {"name": "Elden Ring",       "ram_min": 12, "ram_rec": 16, "vram_min": 4, "disk_gb": 60,  "cpu_note": "i5-8600K / Ryzen 5 3600"},
        "eldenring":    {"name": "Elden Ring",       "ram_min": 12, "ram_rec": 16, "vram_min": 4, "disk_gb": 60,  "cpu_note": "i5-8600K / Ryzen 5 3600"},
        "witcher":      {"name": "The Witcher 3",    "ram_min": 8,  "ram_rec": 16, "vram_min": 4, "disk_gb": 50,  "cpu_note": "i5-2500K / FX-8350"},
        "apex":         {"name": "Apex Legends",     "ram_min": 8,  "ram_rec": 16, "vram_min": 2, "disk_gb": 60,  "cpu_note": "i5-3570T / FX-4170"},
        "warzone":      {"name": "Warzone",          "ram_min": 12, "ram_rec": 16, "vram_min": 4, "disk_gb": 125, "cpu_note": "i5-2500K / Ryzen 5 1600X"},
        "overwatch":    {"name": "Overwatch 2",      "ram_min": 8,  "ram_rec": 16, "vram_min": 4, "disk_gb": 50,  "cpu_note": "i7-4770 / Ryzen 5 1600"},
        "league":       {"name": "League of Legends","ram_min": 4,  "ram_rec": 8,  "vram_min": 1, "disk_gb": 20,  "cpu_note": "any dual-core 2GHz+"},
        "roblox":       {"name": "Roblox",           "ram_min": 4,  "ram_rec": 8,  "vram_min": 1, "disk_gb": 2,   "cpu_note": "any dual-core"},
        "battlefield":  {"name": "Battlefield 2042", "ram_min": 16, "ram_rec": 16, "vram_min": 8, "disk_gb": 100, "cpu_note": "i7-4790 / Ryzen 7 3700X"},
        "stray":        {"name": "Stray",            "ram_min": 8,  "ram_rec": 16, "vram_min": 4, "disk_gb": 10,  "cpu_note": "i7-8700 / Ryzen 5 3600"},
    }

    _GREET_INTROS_PL = [
        "{P} Cześć! Monitoruję Twój PC. CPU {cpu}%, RAM {ram}%. Co sprawdzamy?",
        "{P} Hej! Jestem tu i obserwuję. CPU {cpu}%, RAM {ram}%. Czym mogę pomóc?",
        "{P} Witaj! System spokojny - CPU {cpu}%, RAM {ram}%. Pytaj o co chcesz.",
        "{P} Hejka! Gotowy. CPU {cpu}%, RAM {ram}%. Zacznij od 'specs' lub 'zdrowie'.",
    ]

    _GREET_INTROS_EN = [
        "{P} Hey! Monitoring your PC. CPU {cpu}%, RAM {ram}%. What shall we check?",
        "{P} Hi! Here and watching. CPU {cpu}%, RAM {ram}%. How can I help?",
        "{P} Welcome! System calm - CPU {cpu}%, RAM {ram}%. Ask away.",
        "{P} Hello! Ready. CPU {cpu}%, RAM {ram}%. Start with 'specs' or 'health'.",
    ]

    _GREET_ALERT_PL = [
        "{P} Cześć! System dość zajęty - CPU {cpu}%, RAM {ram}%. Mogę pomóc to rozładować.",
        "{P} Hej! PC pracuje mocno ({cpu}% CPU / {ram}% RAM). Sprawdzamy?",
    ]

    _GREET_ALERT_EN = [
        "{P} Hey! System quite busy - CPU {cpu}%, RAM {ram}%. I can help sort that out.",
        "{P} Hi! PC working hard ({cpu}% CPU / {ram}% RAM). Shall we check it out?",
    ]

    _THANKS_PL = [
        "{P} Spoko! Monitoruję dalej. Wróć jak będziesz potrzebował.",
        "{P} Nie ma za co. Czujki działają, dane lecą. Pytaj kiedy chcesz.",
        "{P} Zawsze do usług. Wpisz 'help' kiedy zapomnisz co potrafię.",
        "{P} Okej! Pilnuję systemu. Daj znać jak coś się zmieni.",
    ]

    _THANKS_EN = [
        "{P} Sure! Still monitoring. Come back whenever.",
        "{P} No problem. Sensors running, data flowing. Ask anytime.",
        "{P} Anytime. Type 'help' if you forget what I can do.",
        "{P} All good! Watching the system. Let me know if anything changes.",
    ]

    @staticmethod
    def _dm_live() -> dict:
        """Fresh live-sensor snapshot ({} on any failure)."""
        try:
            from hck_gpt.data import live_sensors
            return live_sensors.snapshot()
        except Exception:
            return {}

    @staticmethod
    def _dm_val(v, suffix="", nd=0):
        """Format a sensor value, '-' when the sensor reports -1/None."""
        try:
            if v is None or float(v) < 0:
                return "-"
            return f"{float(v):.{nd}f}{suffix}"
        except Exception:
            return "-"

    _GUIDE_TTL = 1800   # 30 min - stale guide state never hijacks a later 'dalej'


# ── Singleton (consumed by chat_handler / hybrid_engine) ──────────────────────
response_builder = ResponseBuilder()
