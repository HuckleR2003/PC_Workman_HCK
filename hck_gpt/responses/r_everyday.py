"""hck_gpt.responses.r_everyday - everyday questions (2026-11-16).

Added after the first long test, where 28 of 71 questions ended in "I did not
understand": where is the overlay, is everything fine, do I have the latest
version, where is the website, what can I delete, where do I update drivers,
has the program learned, are you an AI, Ollama, and plain reactions.
Every answer is built from what this PC recorded; nothing is guessed.
"""
import os
import time

from hck_gpt.responses.common import List, ParseResult, _t

SITE = "pcworkman.dev"


class EverydayResponses:

    # ── where is the in-game overlay ─────────────────────────────────────────
    def _resp_overlay_where(self, r: ParseResult, lang: str = "pl") -> List[str]:
        raw = (r.raw_text or "").lower()
        if any(k in raw for k in ("nie dzia", "nie widac", "nie widać", "nie pokazuje",
                                  "nie wyswietla", "nie wyświetla", "not work", "doesn",
                                  "not show")):
            # "nakladka nie dziala w grze" got only where it is (2026-11-17)
            return [
                _t(lang, f"{self.PREFIX} Gdy nakładki nie widać w grze, sprawdź po kolei:",
                   f"{self.PREFIX} When the overlay does not show in game, check in order:"),
                _t(lang, "  1. Czy jest włączona: My PC → kafelek GAMING / In-Game.",
                   "  1. Is it on: My PC → GAMING / In-Game tile."),
                _t(lang, "  2. Tryb gry: „Pełny ekran w oknie” (borderless). Wyłączny pełny ekran "
                         "zasłania nakładki innych programów.",
                   "  2. The game's display mode: borderless / windowed fullscreen. Exclusive "
                   "fullscreen hides other programs' overlays."),
                _t(lang, "  3. Gra uruchomiona jako administrator: wtedy PC Workman też musi być "
                         "uruchomiony jako administrator.",
                   "  3. A game run as administrator needs PC Workman run as administrator too."),
                "  [-> In-Game Overlay]",
            ]
        return [
            _t(lang,
               f"{self.PREFIX} In-Game Overlay jest w My PC, na kafelku GAMING / In-Game.",
               f"{self.PREFIX} The In-Game Overlay is in My PC, on the GAMING / In-Game tile."),
            _t(lang,
               "  Wybierasz tam, co widać w grze (FPS, CPU, GPU, temperatury) i mini monitor.",
               "  There you pick what shows in game (FPS, CPU, GPU, temperatures) and the mini monitor."),
            "  [-> In-Game Overlay]",
        ]

    # ── is everything fine ────────────────────────────────────────────────────
    def _resp_pc_status(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        now = time.time()
        live = {}
        try:
            import psutil
            live["cpu"] = psutil.cpu_percent(interval=0.2)
            live["ram"] = psutil.virtual_memory().percent
        except Exception:
            pass
        try:
            from hck_gpt.data.live_sensors import snapshot
            snap = snapshot() or {}
            g = snap.get("gpu_load", -1)
            if g is not None and g >= 0:
                live["gpu"] = float(g)
            if snap.get("gpu_ok") and (snap.get("gpu_temp") or -1) > 0:
                live["gpu_temp"] = float(snap["gpu_temp"])
            if snap.get("cpu_temp_src") == "sensor" and (snap.get("cpu_temp") or -1) > 0:
                live["cpu_temp"] = float(snap["cpu_temp"])
        except Exception:
            pass

        issues, notes = [], []
        recorded_h = 0.0
        try:
            from hck_stats_engine import history
            for comp in ("cpu", "ram", "gpu"):
                st = history.stats(comp, now - 7 * 86400, now)
                if not st.get("has_data"):
                    continue
                recorded_h = st["recorded_hours"]
                cur = live.get(comp)
                if cur is None or st["recorded_hours"] < 3:
                    continue
                if cur > st["p95"] + 10 and cur > 60:
                    issues.append(_t(lang,
                        f"{comp.upper()} {cur:.0f}% - wyżej niż zwykle (95% czasu do {st['p95']:.0f}%)",
                        f"{comp.upper()} {cur:.0f}% - higher than usual (95% of the time under {st['p95']:.0f}%)"))
        except Exception:
            pass
        gt = live.get("gpu_temp")
        if gt is not None and gt >= 85:
            issues.append(_t(lang, f"GPU ma {gt:.0f}°C - gorąco", f"GPU is at {gt:.0f}°C - hot"))
        ct = live.get("cpu_temp")
        if ct is not None and ct >= 90:
            issues.append(_t(lang, f"CPU ma {ct:.0f}°C - gorąco", f"CPU is at {ct:.0f}°C - hot"))
        try:
            import psutil
            sysd = os.environ.get("SystemDrive", "C:") + "\\"
            du = psutil.disk_usage(sysd)
            if du.free / du.total < 0.08:
                issues.append(_t(lang,
                    f"na dysku {sysd[:2]} zostało {du.free / 1024**3:.0f} GB",
                    f"{sysd[:2]} has {du.free / 1024**3:.0f} GB left"))
        except Exception:
            pass

        # today's high-load periods
        try:
            from hck_stats_engine.load_periods import periods
            import datetime
            midnight = datetime.datetime.combine(datetime.date.today(),
                                                 datetime.time()).timestamp()
            today = periods(midnight, now)
            if today:
                longest = max(today, key=lambda p: p["minutes"])
                who = longest.get("process_name") or "-"
                notes.append(_t(lang,
                    f"Dziś {len(today)}× wysokie obciążenie, najdłużej {longest['minutes']} min "
                    f"({longest['metric'].upper()}, {who}) - przy grze to normalne.",
                    f"Today {len(today)} high-load period(s), the longest {longest['minutes']} min "
                    f"({longest['metric'].upper()}, {who}) - normal while gaming."))
        except Exception:
            pass

        cur_line = "  " + "  ·  ".join(
            f"{k.upper()} {live[k]:.0f}%" for k in ("cpu", "ram", "gpu") if k in live)
        if gt is not None:
            cur_line += f"  ·  GPU {gt:.0f}°C"

        if issues:
            out = [_t(lang, f"{P} ⚠ Prawie wszystko gra, ale jest {len(issues)} rzecz(y) do uwagi:",
                            f"{P} ⚠ Mostly fine, with {len(issues)} thing(s) to look at:")]
            out += [f"  • {i}" for i in issues]
            out.append(cur_line)
        else:
            out = [_t(lang, f"{P} ✓ Wszystko gra.", f"{P} ✓ Everything looks fine."),
                   cur_line + _t(lang, "  - w normie tego komputera" if recorded_h >= 3 else "",
                                       "  - within this PC's normal" if recorded_h >= 3 else "")]
        out += [f"  {n}" for n in notes]

        try:
            from core.thermal_baseline import thermal_baseline as tb
            pct = tb.overall_training_pct()
            if pct < 60:
                out.append(_t(lang,
                    f"  Uczę się tego komputera ({pct}%). Im dłużej działam, tym pewniejsza ocena. [-> Learning Center]",
                    f"  I am still learning this PC ({pct}%). The longer I run, the surer the verdict. [-> Learning Center]"))
        except Exception:
            pass
        return out

    # ── latest version ────────────────────────────────────────────────────────
    def _resp_version_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        try:
            from utils.app_version import APP_VERSION, RELEASE_DATE
        except Exception:
            return [_t(lang, f"{P} Nie mogę odczytać wersji. [-> {SITE}]",
                             f"{P} I cannot read the version. [-> {SITE}]")]
        import datetime
        rel = datetime.date.fromisoformat(RELEASE_DATE)
        days = (datetime.date.today() - rel).days
        date_txt = rel.strftime("%d.%m.%Y")
        if days < 21:
            verdict = _t(lang, f"Wersja {APP_VERSION} z {date_txt} - powinna być jak najbardziej aktualna.",
                               f"Version {APP_VERSION} from {date_txt} - it should be current.")
        elif days < 45:
            verdict = _t(lang, f"Wersja {APP_VERSION} ma ponad 3 tygodnie - pewnie czeka nowa, z prostą aktualizacją.",
                               f"Version {APP_VERSION} is over 3 weeks old - a newer one is probably out, easy to update.")
        elif days < 100:
            verdict = _t(lang, f"Wersja {APP_VERSION} ma około {days // 30} miesięcy - powinny być nowe wersje.",
                               f"Version {APP_VERSION} is about {days // 30} months old - there should be newer versions.")
        else:
            verdict = _t(lang, f"Ten build ma już {days // 30} miesięcy, czas go zaktualizować :)",
                               f"This build is {days // 30} months old, time to update :)")
        return [
            f"{P} {verdict}",
            _t(lang,
               "  Dla bezpieczeństwa sam nie łączę się z internetem, żeby to sprawdzić.",
               "  For safety I do not go online to check this myself."),
            _t(lang,
               f"  Najnowszą pobierzesz ze strony (przycisk na środku albo w nagłówku): [-> {SITE}]",
               f"  Get the newest from the website (button in the middle or in the header): [-> {SITE}]"),
            _t(lang,
               "  Z Microsoft Store aktualizacje przychodzą same; HCK_Labs → Sprawdź aktualizację otwiera stronę w Sklepie.",
               "  Microsoft Store installs update on their own; HCK_Labs → Check for updates opens the Store page."),
        ]

    # ── website ───────────────────────────────────────────────────────────────
    def _resp_website(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Strona PC Workman to {SITE}:",
                     f"{self.PREFIX} PC Workman's website is {SITE}:"),
            _t(lang,
               "  pobieranie (na środku i w nagłówku), poradniki i historia projektu.",
               "  downloads (middle and header), guides and the story of the project."),
            f"  [-> {SITE}]",
        ]

    # ── what can I delete ─────────────────────────────────────────────────────
    @staticmethod
    def _folder_size(path: str, budget_s: float = 1.2) -> float:
        """Bytes in a folder, stopping after budget_s seconds (a lower bound)."""
        total, end = 0, time.time() + budget_s
        try:
            for root, _dirs, files in os.walk(path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
                if time.time() > end:
                    break
        except Exception:
            pass
        return total

    def _resp_free_space(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        out = [_t(lang, f"{P} Gdzie odzyskać miejsce:", f"{P} Where to get space back:")]
        try:
            import psutil
            for part in psutil.disk_partitions():
                try:
                    du = psutil.disk_usage(part.mountpoint)
                except Exception:
                    continue
                if du.percent >= 85:
                    out.append(_t(lang,
                        f"  ⚠ {part.device[:2]} zajęty w {du.percent:.0f}% (wolne {du.free / 1024**3:.0f} GB)",
                        f"  ⚠ {part.device[:2]} is {du.percent:.0f}% full ({du.free / 1024**3:.0f} GB free)"))
        except Exception:
            pass
        temp = os.environ.get("TEMP", "")
        if temp:
            gb = self._folder_size(temp) / 1024 ** 3
            if gb >= 0.2:
                out.append(_t(lang,
                    f"  • Pliki tymczasowe: co najmniej {gb:.1f} GB ({temp}) - bezpieczne do usunięcia.",
                    f"  • Temporary files: at least {gb:.1f} GB ({temp}) - safe to delete."))
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.isdir(dl):
            gb = self._folder_size(dl) / 1024 ** 3
            if gb >= 1:
                out.append(_t(lang,
                    f"  • Pobrane: co najmniej {gb:.1f} GB - instalatory zwykle można usunąć.",
                    f"  • Downloads: at least {gb:.1f} GB - installers can usually go."))
        out.extend(self._last_cleanup_scan(lang))
        out.append(_t(lang,
            "  • Oczyszczanie w PC Workman pokaże, ile zajmuje każda kategoria, i usunie to, co zaznaczysz: [-> Cleanup]",
            "  • Cleanup in PC Workman shows what each category holds and removes what you choose: [-> Cleanup]"))
        out.append(_t(lang,
            "  Programy, których dawno nie używasz: zapytaj 'co mogę odinstalować'.",
            "  Programs you have not used in a while: ask 'what can I uninstall'."))
        return out

    _CLEANUP_NAMES = {
        "user_temp": ("pliki tymczasowe", "temporary files"),
        "windows_temp": ("pliki tymczasowe Windows", "Windows temporary files"),
        "thumb_cache": ("miniatury", "thumbnails"),
        "error_reports": ("raporty błędów", "error reports"),
        "system_reports": ("raporty systemowe", "system reports"),
        "shader_cache": ("pamięć shaderów", "shader cache"),
        "update_cache": ("pobrane aktualizacje", "downloaded updates"),
        "delivery_opt": ("optymalizacja dostarczania", "Delivery Optimization"),
        "big_downloads": ("duże pliki w Pobranych", "big files in Downloads"),
        "recycle_bin": ("Kosz", "Recycle Bin"),
        "br_operagx": ("Opera GX", "Opera GX"),
    }

    def _last_cleanup_scan(self, lang: str = "pl", max_age_s: float = 7 * 86400) -> List[str]:
        """The Cleanup page's last scan (data/cache/cleanup_scan.json), when
        it is under a week old: what it found and the three biggest items."""
        try:
            import time as _time
            from core.cleanup import last_scan, fmt_size
            s = last_scan()
            if not s or _time.time() - float(s.get("ts", 0)) > max_age_s:
                return []
            items = [(k, v) for k, v in (s.get("items") or {}).items()
                     if v.get("size") and not v.get("blocked")]
            if not items:
                return []
            items.sort(key=lambda kv: -kv[1]["size"])
            i = 1 if lang == "en" else 0

            def nm(k):
                if k in self._CLEANUP_NAMES:
                    return self._CLEANUP_NAMES[k][i]
                # br_chrome -> Chrome, app_discord -> Discord
                return k.split("_", 1)[-1].capitalize()
            top = ", ".join(f"{nm(k)} {fmt_size(v['size'], lang)}" for k, v in items[:3])
            day = _time.strftime("%d.%m", _time.localtime(s["ts"]))
            return [_t(lang,
                f"  • Ostatni skan Oczyszczania ({day}): do odzyskania {fmt_size(s.get('total', 0), lang)}. Najwięcej: {top}.",
                f"  • The last Cleanup scan ({day}): {fmt_size(s.get('total', 0), lang)} to free. Biggest: {top}.")]
        except Exception:
            return []

    # ── where to update drivers ───────────────────────────────────────────────
    def _resp_driver_update_where(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        gpu = ""
        try:
            from hck_gpt.data.live_sensors import get as _ls_get
            gpu = str(_ls_get("gpu_name", "") or "")
        except Exception:
            pass
        if not gpu:
            try:
                from hck_gpt.memory.user_knowledge import user_knowledge
                gpu = str((user_knowledge.get_all_hardware() or {}).get("gpu_model") or "")
            except Exception:
                gpu = ""
        g = gpu.upper()
        if "NVIDIA" in g or "GEFORCE" in g or "RTX" in g or "GTX" in g:
            gpu_line = _t(lang, "  • Karta graficzna (NVIDIA): aplikacja NVIDIA App albo nvidia.com/drivers.",
                                "  • Graphics (NVIDIA): the NVIDIA App or nvidia.com/drivers.")
        elif "AMD" in g or "RADEON" in g:
            gpu_line = _t(lang, "  • Karta graficzna (AMD): AMD Software: Adrenalin Edition.",
                                "  • Graphics (AMD): AMD Software: Adrenalin Edition.")
        elif "INTEL" in g or "ARC" in g:
            gpu_line = _t(lang, "  • Karta graficzna (Intel): Intel Driver & Support Assistant.",
                                "  • Graphics (Intel): Intel Driver & Support Assistant.")
        else:
            gpu_line = _t(lang, "  • Karta graficzna: aplikacja producenta karty.",
                                "  • Graphics: the card maker's app.")
        return [
            _t(lang, f"{P} Gdzie zaktualizować sterowniki:", f"{P} Where to update drivers:"),
            gpu_line,
            _t(lang, "  • Chipset, sieć, audio: strona producenta płyty głównej (dział Support).",
                     "  • Chipset, network, audio: the motherboard maker's support page."),
            _t(lang, "  • Reszta: Windows Update → Opcje zaawansowane → Aktualizacje opcjonalne.",
                     "  • The rest: Windows Update → Advanced options → Optional updates."),
            _t(lang, "  Które sterowniki są stare, widać w Setup & Drivers: [-> Setup & Drivers]",
                     "  Which drivers are old is shown in Setup & Drivers: [-> Setup & Drivers]"),
        ]

    # ── are you an AI ─────────────────────────────────────────────────────────
    def _resp_about_assistant(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        online = False
        try:
            from hck_gpt.engine.hybrid_engine import hybrid_engine
            online = bool(hybrid_engine.ollama_online)
        except Exception:
            pass
        out = [
            _t(lang, f"{P} Jestem hck_GPT, asystent wbudowany w PC Workman. Nie jestem ChatGPT.",
                     f"{P} I am hck_GPT, the assistant built into PC Workman. I am not ChatGPT."),
            _t(lang, "  Działam na Twoim komputerze: rozpoznaję pytanie (słownik i mały model",
                     "  I run on your PC: I recognise the question (a vocabulary and a small"),
            _t(lang, "  uczony na pytaniach) i odpowiadam z danych, które PC Workman tu zebrał.",
                     "  trained model) and answer from the data PC Workman collected here."),
        ]
        out.append(_t(lang,
            "  Lokalne AI (Ollama) jest włączone - z niego korzystam przy luźniejszych pytaniach." if online else
            "  Jeśli zainstalujesz Ollamę, przy luźniejszych pytaniach użyję lokalnego modelu.",
            "  Local AI (Ollama) is on - I use it for open-ended questions." if online else
            "  If you install Ollama, I will use a local model for open-ended questions."))
        return out

    # ── Ollama ────────────────────────────────────────────────────────────────
    def _resp_ollama_info(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        online, model = False, ""
        try:
            from hck_gpt.engine.hybrid_engine import hybrid_engine
            online = bool(hybrid_engine.refresh_availability())
            model = getattr(hybrid_engine, "model", "") or ""
        except Exception:
            pass
        if online:
            return [_t(lang, f"{P} Ollama działa - używam modelu {model or '(domyślny)'}.",
                             f"{P} Ollama is running - I use the {model or '(default)'} model."),
                    _t(lang, "  Konkretne pytania o sprzęt dalej obsługuję z danych PC Workman,",
                             "  Concrete hardware questions still come from PC Workman's data,"),
                    _t(lang, "  Ollama odpowiada na luźniejsze pytania. Nic nie wychodzi poza komputer.",
                             "  Ollama answers the open-ended ones. Nothing leaves the PC.")]
        return [_t(lang, f"{P} Ollamy teraz nie widzę (127.0.0.1:11434).",
                         f"{P} I do not see Ollama right now (127.0.0.1:11434)."),
                _t(lang, "  Żeby ją włączyć: zainstaluj ze strony ollama.com i pobierz model,",
                         "  To turn it on: install it from ollama.com and pull a model,"),
                _t(lang, "  np. 'ollama pull llama3.2'. Wykryję ją sam w ciągu kilku minut.",
                         "  e.g. 'ollama pull llama3.2'. I will find it myself within minutes."),
                _t(lang, "  Bez niej wszystko działa - odpowiadam z danych PC Workman.",
                         "  Everything works without it - I answer from PC Workman's data.")]

    # ── reactions ─────────────────────────────────────────────────────────────
    def _resp_reaction(self, r: ParseResult, lang: str = "pl") -> List[str]:
        text = (r.raw_text or "").lower()
        if "co powiesz" in text:
            return [_t(lang,
                f"{self.PREFIX} Mogę powiedzieć, jak dziś pracował komputer - zapytaj 'wszystko działa?'.",
                f"{self.PREFIX} I can tell you how the PC did today - ask 'is everything fine?'.")]
        if "co to bylo" in text or "co to było" in text:
            return [_t(lang,
                f"{self.PREFIX} Jeśli coś było niejasne, zapytaj inaczej albo napisz 'co potrafisz'.",
                f"{self.PREFIX} If something was unclear, ask another way or type 'what can you do'.")]
        return [_t(lang, f"{self.PREFIX} 🙂 Pytaj śmiało dalej.",
                         f"{self.PREFIX} 🙂 Ask away.")]
