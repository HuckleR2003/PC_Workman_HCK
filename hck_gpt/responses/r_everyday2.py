"""hck_gpt.responses.r_everyday2 - questions from the second long test and
the 122-question sweep (2026-11-17).

Two kinds:
  * the history PC Workman records, asked in plain words: when was the PC
    busiest, did it sleep, what did I play and for how long, how long has it
    been on today, today against yesterday. hck_GPT reads the same tables as
    Activity Memory, so the chat and the page never disagree;
  * everyday problems that ended in "I did not understand": virtual memory,
    which apps can I close, which services to turn off, the monitor stuck at
    60 Hz, crackling sound, dust, backup, turning Windows Update off,
    changing the language, PC Workman's own footprint, XMP, Wi-Fi drops,
    "nothing works".
Numbers come from this PC; what PC Workman cannot see is said plainly.
"""
from __future__ import annotations

import datetime as _dt
import time

from hck_gpt.responses.common import List, ParseResult, _t

_DAY = 86400.0


def _hm(ts: float, lang: str) -> str:
    d = _dt.datetime.fromtimestamp(ts)
    today = _dt.date.today()
    if d.date() == today:
        day = _t(lang, "dziś", "today")
    elif d.date() == today - _dt.timedelta(days=1):
        day = _t(lang, "wczoraj", "yesterday")
    else:
        day = d.strftime("%d.%m")
    return f"{day} {d:%H:%M}"


def _dur(minutes: float, lang: str) -> str:
    m = int(round(minutes))
    if m < 60:
        return f"{m} min"
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min" if m else f"{h} h"


def _midnight(days_ago: int = 0) -> float:
    d = _dt.datetime.combine(_dt.date.today() - _dt.timedelta(days=days_ago), _dt.time())
    return d.timestamp()


def _offer_activity(lang: str) -> str:
    return _t(lang, "  Cała historia z wykresami: [-> Activity Memory]",
              "  The full history with charts: [-> Activity Memory]")


class MoreEverydayResponses:

    # ── history: the busiest moment ──────────────────────────────────────────
    def _resp_history_peak(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_stats_engine import history
        now = time.time()
        raw = (r.raw_text or "").lower()
        span = 7 * _DAY if any(k in raw for k in ("tydzie", "week", "7 dni")) else _DAY
        label = _t(lang, "ostatnich 7 dni" if span > _DAY else "ostatnich 24 godzin",
                   "the last 7 days" if span > _DAY else "the last 24 hours")
        lines = [_t(lang, f"{self.PREFIX} Najcięższe momenty z {label}:",
                    f"{self.PREFIX} The busiest moments of {label}:")]
        found = False
        for comp, name in (("cpu", "CPU"), ("gpu", "GPU"), ("ram", "RAM")):
            try:
                st = history.stats(comp, now - span, now)
            except Exception:
                st = {}
            if not st.get("has_data"):
                continue
            found = True
            who = ""
            if comp != "gpu":
                try:
                    top = history.top_processes(comp, st["max_ts"] - 1800, st["max_ts"] + 1800, n=1)
                    if top:
                        who = _t(lang, f", najwięcej brał {top[0]['name']}",
                                 f", {top[0]['name']} used the most")
                except Exception:
                    who = ""
            lines.append(_t(lang,
                f"  {name}: {st['max']:.0f}% {_hm(st['max_ts'], lang)}{who} "
                f"(średnio {st['avg']:.0f}%)",
                f"  {name}: {st['max']:.0f}% {_hm(st['max_ts'], lang)}{who} "
                f"(average {st['avg']:.0f}%)"))
        try:
            from hck_stats_engine.load_periods import periods
            ps = periods(now - span, now)
        except Exception:
            ps = []
        if ps:
            longest = max(ps, key=lambda p: p["minutes"])
            game = longest.get("process_name") or ""
            lines.append(_t(lang,
                f"  Najdłuższy okres obciążenia: {_dur(longest['minutes'], lang)} od "
                f"{_hm(longest['timestamp'], lang)}" + (f" ({game})" if game else "") + ".",
                f"  Longest busy stretch: {_dur(longest['minutes'], lang)} from "
                f"{_hm(longest['timestamp'], lang)}" + (f" ({game})" if game else "") + "."))
        if not found:
            return [_t(lang,
                f"{self.PREFIX} Nie mam jeszcze historii z tego okresu. Zbieram ją co minutę, "
                f"wróć za godzinę.",
                f"{self.PREFIX} No history for that period yet. I record every minute, "
                f"ask again in an hour.")]
        lines.append(_offer_activity(lang))
        return lines

    # ── history: did the PC sleep ────────────────────────────────────────────
    def _resp_history_sleep(self, r: ParseResult, lang: str = "pl") -> List[str]:
        now = time.time()
        try:
            from hck_stats_engine.load_periods import sleeps
            ss = sleeps(now - 2 * _DAY, now)
        except Exception:
            ss = []
        if not ss:
            return [_t(lang,
                f"{self.PREFIX} W ostatnich 48 godzinach nie zapisałem uśpienia, gdy PC Workman działał.",
                f"{self.PREFIX} I recorded no sleep in the last 48 hours while PC Workman was running."),
                _t(lang,
                   "  Przerwy, gdy program był wyłączony, widać w historii jako puste miejsca.",
                   "  Gaps while the app was closed show in the history as blank stretches."),
                _offer_activity(lang)]
        lines = [_t(lang, f"{self.PREFIX} Tak, komputer spał {len(ss)} raz(y) w ostatnich 48 godzinach:",
                    f"{self.PREFIX} Yes, the PC slept {len(ss)} time(s) in the last 48 hours:")]
        for s in ss[-5:]:
            mins = (s["end"] - s["start"]) / 60
            lines.append(_t(lang,
                f"  · {_hm(s['start'], lang)} → {_hm(s['end'], lang)} ({_dur(mins, lang)})",
                f"  · {_hm(s['start'], lang)} → {_hm(s['end'], lang)} ({_dur(mins, lang)})"))
        lines.append(_offer_activity(lang))
        return lines

    # ── history: what did I play ─────────────────────────────────────────────
    def _game_minutes(self, start: float, end: float) -> list:
        """[(game, minutes)] from the per-process history, games only."""
        from hck_stats_engine import history
        from core.game_detect import is_game, display_name
        out = {}
        try:
            for p in history.top_processes("cpu", start, end, n=80,
                                           recorded_seconds=max(1.0, end - start)):
                exe = p.get("process") or p.get("name") or ""
                if is_game(exe):
                    # beamng.drive.exe and beamng.drive.x64.exe are one game
                    key = display_name(exe) or exe
                    key = key[:1].upper() + key[1:]
                    out[key] = out.get(key, 0.0) + float(p.get("active_hours") or 0) * 60
        except Exception:
            return []
        return sorted(((k, v) for k, v in out.items() if v >= 1), key=lambda kv: -kv[1])

    def _resp_history_games(self, r: ParseResult, lang: str = "pl") -> List[str]:
        raw = (r.raw_text or "").lower()
        now = time.time()
        today_only = any(k in raw for k in ("dzis", "dziś", "dzisiaj", "today"))
        start = _midnight(0) if today_only else now - 7 * _DAY
        label = _t(lang, "dziś" if today_only else "przez ostatnie 7 dni",
                   "today" if today_only else "over the last 7 days")
        games = self._game_minutes(start, now)
        if not games:
            return [_t(lang,
                f"{self.PREFIX} Nie widzę grania {label} w historii.",
                f"{self.PREFIX} I see no gaming {label} in the history."),
                _t(lang,
                   "  Gry rozpoznaję po nazwie i po folderze (Steam, Epic, GOG, Xbox, Riot…).",
                   "  I recognise games by name and folder (Steam, Epic, GOG, Xbox, Riot…)."),
                _offer_activity(lang)]
        total = sum(m for _, m in games)
        lines = [_t(lang, f"{self.PREFIX} Granie {label}: razem {_dur(total, lang)}.",
                    f"{self.PREFIX} Gaming {label}: {_dur(total, lang)} in total.")]
        for g, m in games[:5]:
            lines.append(f"  · {g}: {_dur(m, lang)}")
        lines.append(_t(lang,
            "  Czas liczę z minut, w których gra działała i PC Workman nagrywał.",
            "  Time counts the minutes the game ran while PC Workman was recording."))
        lines.append(_offer_activity(lang))
        return lines

    # ── history: how long has it been on today ───────────────────────────────
    def _resp_history_today(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_stats_engine import history
        now = time.time()
        lines = []
        try:
            import psutil
            boot = psutil.boot_time()
            lines.append(_t(lang,
                f"{self.PREFIX} Windows działa od {_hm(boot, lang)} ({_dur((now - boot) / 60, lang)}, "
                f"razem z uśpieniami).",
                f"{self.PREFIX} Windows has been up since {_hm(boot, lang)} ({_dur((now - boot) / 60, lang)}, "
                f"sleep included)."))
        except Exception:
            lines.append(_t(lang, f"{self.PREFIX} Dzisiejszy dzień komputera:",
                            f"{self.PREFIX} Today on this PC:"))
        try:
            st = history.stats("cpu", _midnight(0), now)
        except Exception:
            st = {}
        if st.get("has_data"):
            lines.append(_t(lang,
                f"  Dziś nagrałem {_dur(st['recorded_hours'] * 60, lang)} pracy: CPU średnio "
                f"{st['avg']:.0f}%, najwyżej {st['max']:.0f}% o {_hm(st['max_ts'], lang)[-5:]}.",
                f"  Recorded today: {_dur(st['recorded_hours'] * 60, lang)}: CPU average "
                f"{st['avg']:.0f}%, peak {st['max']:.0f}% at {_hm(st['max_ts'], lang)[-5:]}."))
        games = self._game_minutes(_midnight(0), now)
        if games:
            lines.append(_t(lang,
                f"  Z tego granie: {_dur(sum(m for _, m in games), lang)} ({games[0][0]} najdłużej).",
                f"  Gaming: {_dur(sum(m for _, m in games), lang)} ({games[0][0]} the longest)."))
        lines.append(_offer_activity(lang))
        return lines

    # ── history: today vs yesterday ──────────────────────────────────────────
    def _resp_history_compare_days(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_stats_engine import history
        now = time.time()
        t0, y0 = _midnight(0), _midnight(1)
        lines = [_t(lang, f"{self.PREFIX} Dziś a wczoraj:", f"{self.PREFIX} Today vs yesterday:")]
        any_data = False
        for comp, name in (("cpu", "CPU"), ("gpu", "GPU"), ("ram", "RAM")):
            try:
                a = history.stats(comp, t0, now)
                b = history.stats(comp, y0, t0)
            except Exception:
                continue
            if not (a.get("has_data") and b.get("has_data")):
                continue
            any_data = True
            d = a["avg"] - b["avg"]
            word = (_t(lang, "podobnie", "about the same") if abs(d) < 3 else
                    _t(lang, f"{d:+.0f} pp", f"{d:+.0f} pp"))
            lines.append(_t(lang,
                f"  {name}: dziś średnio {a['avg']:.0f}% (szczyt {a['max']:.0f}%), wczoraj "
                f"{b['avg']:.0f}% (szczyt {b['max']:.0f}%) - {word}",
                f"  {name}: today average {a['avg']:.0f}% (peak {a['max']:.0f}%), yesterday "
                f"{b['avg']:.0f}% (peak {b['max']:.0f}%) - {word}"))
        if not any_data:
            return [_t(lang,
                f"{self.PREFIX} Do porównania potrzebuję zapisu z obu dni; wczoraj albo dziś go brakuje.",
                f"{self.PREFIX} I need a record from both days to compare; one of them is missing.")]
        lines.append(_offer_activity(lang))
        return lines

    # ── virtual memory ───────────────────────────────────────────────────────
    def _resp_virtual_memory(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pagefile import describe, info
        d = info()
        raw = (r.raw_text or "").lower()
        how = any(k in raw for k in ("jak", "gdzie", "zwiększ", "zwieksz", "ustaw", "dodaj",
                                     "how", "where", "increase", "set", "add"))
        lines = [f"{self.PREFIX} " + describe(lang, d) + "."]
        lines.append(_t(lang,
            "  Pamięć wirtualna to miejsce na dysku, do którego Windows odkłada to, co nie "
            "mieści się w RAM. Ratuje przed zamykaniem programów, ale jest wolniejsza niż RAM.",
            "  Virtual memory is disk space where Windows puts what does not fit in RAM. It "
            "keeps apps from closing, but it is slower than RAM."))
        if d.get("mode") == "none":
            lines.append(_t(lang,
                "  ⚠ Bez niej przy pełnym RAM programy mogą się zamykać. Włącz ją:",
                "  ⚠ Without it, apps can close when RAM is full. Turn it on:"))
        if how or d.get("mode") == "none":
            lines += [
                "",
                _t(lang, "  1. Otwórz ustawienia przyciskiem niżej (zakładka Zaawansowane).",
                         "  1. Open the settings with the link below (Advanced tab)."),
                _t(lang, "  2. Wydajność → Ustawienia… → zakładka Zaawansowane.",
                         "  2. Performance → Settings… → Advanced tab."),
                _t(lang, "  3. Pamięć wirtualna → Zmień… → najlepiej „Automatycznie zarządzaj”.",
                         "  3. Virtual memory → Change… → best: \"Automatically manage\"."),
            ]
        lines.append("  [-> Virtual Memory]")
        return lines

    # ── which apps can I close ───────────────────────────────────────────────
    _KEEP = {"svchost", "explorer", "dwm", "csrss", "lsass", "services", "wininit",
             "winlogon", "smss", "msmpeng", "searchindexer", "searchhost", "startmenuexperiencehost",
             "shellexperiencehost", "runtimebroker", "audiodg", "fontdrvhost", "sihost",
             "ctfmon", "taskhostw", "textinputhost", "nvdisplay.container", "spoolsv",
             "pc workman hck", "pc_workman_hck", "python", "pythonw", "conhost",
             "securityhealthservice", "wudfhost", "lsaiso", "dllhost", "applicationframehost",
             "systemsettings", "widgets", "phoneexperiencehost", "crossdeviceservice"}

    def _resp_closable_apps(self, r: ParseResult, lang: str = "pl") -> List[str]:
        top, comp = self._ram_by_app(25)
        apps = [(n, mb) for n, mb in top if n.lower() not in self._KEEP and mb >= 150][:5]
        if not apps:
            return [_t(lang,
                f"{self.PREFIX} Nie widzę teraz dużych programów do zamknięcia: zostały głównie "
                f"procesy Windows.",
                f"{self.PREFIX} I see no big apps worth closing right now: mostly Windows "
                f"processes are left.")]
        lines = [_t(lang,
            f"{self.PREFIX} Możesz zamknąć, jeśli teraz ich nie używasz (od największych):",
            f"{self.PREFIX} You can close these if you are not using them (largest first):")]
        for n, mb in apps:
            lines.append(f"  · {n}  {self._mb_text(mb)}")
        lines.append(_t(lang,
            "  Procesy Windows (svchost, explorer, dwm) i antywirus zostaw. Zamykaj normalnie, "
            "nie przez Menedżer zadań, żeby nic nie stracić.",
            "  Leave Windows processes (svchost, explorer, dwm) and the antivirus. Close apps "
            "normally, not through Task Manager, so nothing is lost."))
        lines.append(_t(lang,
            "  Zamiast zamykać, PC Workman może je usypiać: App Hibernation  [-> Optimization]",
            "  Instead of closing, PC Workman can put them to sleep: App Hibernation  [-> Optimization]"))
        return lines

    # ── which services to turn off ───────────────────────────────────────────
    def _resp_services_advice(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_gpt.responses.flows import _running_unneeded
            running = _running_unneeded()
        except Exception:
            running = None
        lines = [_t(lang, f"{self.PREFIX} Usługi Windows:", f"{self.PREFIX} Windows services:")]
        if running:
            lines.append(_t(lang,
                f"  Działa {len(running)} usług, których większość komputerów nie potrzebuje: "
                f"{', '.join(running)}.",
                f"  {len(running)} services run that most PCs do not need: {', '.join(running)}."))
        elif running is not None:
            lines.append(_t(lang, "  ✓ Żadna z typowo zbędnych usług nie działa.",
                            "  ✓ None of the usually unneeded services is running."))
        lines.append(_t(lang,
            "  Bezpieczniej niż wyłączać na stałe: profil w Services Manager, a TURBO zatrzyma "
            "je tylko na czas grania i przywróci.",
            "  Safer than disabling for good: a profile in Services Manager; TURBO stops them "
            "only while you play and restores them."))
        lines.append(_t(lang,
            "  Nie ruszaj: Windows Update, Windows Defender, Audio, sieci i sterowników.",
            "  Leave alone: Windows Update, Windows Defender, audio, network and driver services."))
        lines.append("  [-> Services Manager]")
        return lines

    # ── monitor refresh rate ─────────────────────────────────────────────────
    @staticmethod
    def _displays() -> list:
        """[(device name, Hz, width, height)] of the active displays."""
        out = []
        try:
            import ctypes
            from ctypes import wintypes

            class DEVMODE(ctypes.Structure):
                _fields_ = [("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
                            ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD),
                            ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
                            ("dmPositionX", wintypes.LONG), ("dmPositionY", wintypes.LONG),
                            ("dmDisplayOrientation", wintypes.DWORD),
                            ("dmDisplayFixedOutput", wintypes.DWORD),
                            ("dmColor", wintypes.SHORT), ("dmDuplex", wintypes.SHORT),
                            ("dmYResolution", wintypes.SHORT), ("dmTTOption", wintypes.SHORT),
                            ("dmCollate", wintypes.SHORT), ("dmFormName", wintypes.WCHAR * 32),
                            ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD),
                            ("dmPelsWidth", wintypes.DWORD), ("dmPelsHeight", wintypes.DWORD),
                            ("dmDisplayFlags", wintypes.DWORD), ("dmDisplayFrequency", wintypes.DWORD),
                            ("dmICMMethod", wintypes.DWORD), ("dmICMIntent", wintypes.DWORD),
                            ("dmMediaType", wintypes.DWORD), ("dmDitherType", wintypes.DWORD),
                            ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
                            ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD)]

            class DISPLAY_DEVICE(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("DeviceName", wintypes.WCHAR * 32),
                            ("DeviceString", wintypes.WCHAR * 128), ("StateFlags", wintypes.DWORD),
                            ("DeviceID", wintypes.WCHAR * 128), ("DeviceKey", wintypes.WCHAR * 128)]

            user32 = ctypes.windll.user32
            i = 0
            while i < 16:
                dd = DISPLAY_DEVICE()
                dd.cb = ctypes.sizeof(dd)
                if not user32.EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
                    break
                i += 1
                if not dd.StateFlags & 0x1:          # attached to the desktop
                    continue
                dm = DEVMODE()
                dm.dmSize = ctypes.sizeof(dm)
                if user32.EnumDisplaySettingsW(dd.DeviceName, -1, ctypes.byref(dm)):
                    out.append((dd.DeviceName.replace("\\\\.\\", ""), int(dm.dmDisplayFrequency),
                                int(dm.dmPelsWidth), int(dm.dmPelsHeight)))
        except Exception:
            return []
        return out

    def _resp_refresh_rate(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ds = self._displays()
        lines = [_t(lang, f"{self.PREFIX} Odświeżanie ekranu teraz:",
                    f"{self.PREFIX} Screen refresh rate right now:")]
        for name, hz, w, h in ds:
            lines.append(f"  · {name}: {w}×{h}, {hz} Hz")
        if not ds:
            lines.append(_t(lang, "  Nie mogę odczytać ustawień ekranu.",
                            "  I cannot read the display settings."))
        lines += [
            "",
            _t(lang, "  Monitor 144 Hz na 60 Hz to zwykle jedno z trzech:",
                     "  A 144 Hz monitor stuck at 60 Hz is usually one of three:"),
            _t(lang, "  1. Ustawienia → System → Ekran → Ekran zaawansowany → Częstotliwość odświeżania.",
                     "  1. Settings → System → Display → Advanced display → Refresh rate."),
            _t(lang, "  2. Kabel: DisplayPort albo HDMI 2.0+; stary HDMI często daje tylko 60 Hz.",
                     "  2. Cable: DisplayPort or HDMI 2.0+; an old HDMI cable often caps at 60 Hz."),
            _t(lang, "  3. Kabel w karcie graficznej, nie w gnieździe płyty głównej.",
                     "  3. Cable in the graphics card, not in the motherboard's port."),
        ]
        return lines

    # ── crackling sound ──────────────────────────────────────────────────────
    def _resp_audio_crackle(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Trzeszczący dźwięk ma zwykle jedną z tych przyczyn:",
               f"{self.PREFIX} Crackling sound usually comes from one of these:"),
            _t(lang, "  1. Sterownik audio: zaktualizuj go ze strony producenta płyty (Realtek).",
               "  1. The audio driver: update it from the motherboard maker's site (Realtek)."),
            _t(lang, "  2. Plan zasilania oszczędzający energię: przełącz na Zrównoważony albo Wysoka wydajność.",
               "  2. A power-saving power plan: switch to Balanced or High performance."),
            _t(lang, "  3. Przeciążony procesor w tle: sprawdź 'co zjada procesor'.",
               "  3. A busy CPU in the background: ask 'what is using my cpu'."),
            _t(lang, "  4. Słuchawki USB / Bluetooth: inny port USB albo wyłączenie „Ulepszeń dźwięku” "
                     "w ustawieniach urządzenia.",
               "  4. USB / Bluetooth headphones: another USB port, or turn off \"Audio enhancements\" "
               "in the device settings."),
            _t(lang, "  Sterowniki z datami: [-> Setup & Drivers]",
               "  Drivers with dates: [-> Setup & Drivers]"),
        ]

    # ── dust and paste ───────────────────────────────────────────────────────
    def _resp_dust_cleaning(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Czyszczenie z kurzu, bezpiecznie:",
               f"{self.PREFIX} Dust cleaning, safely:"),
            _t(lang, "  1. Wyłącz komputer i odłącz zasilanie; poczekaj minutę.",
               "  1. Shut down and unplug; wait a minute."),
            _t(lang, "  2. Sprężone powietrze krótkimi seriami. Wentylatory przytrzymaj palcem, żeby się nie kręciły.",
               "  2. Compressed air in short bursts. Hold the fans so they do not spin."),
            _t(lang, "  3. Filtry przeciwkurzowe przemyj wodą i wysusz.",
               "  3. Rinse dust filters with water and let them dry."),
            _t(lang, "  Raz na 6-12 miesięcy wystarcza. Pastę na procesorze wymienia się rzadko: "
                     "gdy temperatury wyraźnie wzrosły przy tym samym obciążeniu.",
               "  Every 6-12 months is enough. CPU paste rarely needs replacing: only when "
               "temperatures clearly rose under the same load."),
            _t(lang, "  Po czyszczeniu porównam temperatury z tym, czego się nauczyłem: zapytaj 'temperatury'.",
               "  After cleaning I can compare temperatures with what I learned: ask 'temperatures'."),
        ]

    # ── backup ───────────────────────────────────────────────────────────────
    def _resp_backup_where(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} PC Workman nie robi kopii zapasowych, ale Windows ma to wbudowane:",
               f"{self.PREFIX} PC Workman does not make backups, but Windows has it built in:"),
            _t(lang, "  · Pliki: Ustawienia → Konta → Kopia zapasowa systemu Windows (OneDrive).",
               "  · Files: Settings → Accounts → Windows backup (OneDrive)."),
            _t(lang, "  · Na dysk zewnętrzny: Panel sterowania → Historia plików.",
               "  · To an external drive: Control Panel → File History."),
            _t(lang, "  Zasada 3-2-1: trzy kopie, na dwóch nośnikach, jedna poza domem.",
               "  The 3-2-1 rule: three copies, on two media, one away from home."),
        ]

    # ── turn off Windows Update? ─────────────────────────────────────────────
    def _resp_windows_update_off(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Nie wyłączaj Windows Update na stałe: to łatki bezpieczeństwa.",
               f"{self.PREFIX} Do not turn Windows Update off for good: it brings security fixes."),
            _t(lang, "  Jeśli przeszkadza w graniu albo pracy, wstrzymaj go: Ustawienia → Windows Update → "
                     "Wstrzymaj aktualizacje (do 5 tygodni), i ustaw Godziny aktywne.",
               "  If it gets in the way, pause it: Settings → Windows Update → Pause updates "
               "(up to 5 weeks), and set Active hours."),
            _t(lang, "  Pobieranie w tle mogę zatrzymać na czas grania profilem TURBO.  [-> Services Manager]",
               "  TURBO can hold background downloads while you play.  [-> Services Manager]"),
        ]

    # ── change the language ──────────────────────────────────────────────────
    def _resp_language_change(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Język czatu zmienisz przyciskiem Languages nad rozmową.",
               f"{self.PREFIX} Change the chat language with the Languages button above the chat."),
            _t(lang, "  Język całego programu jest w Ustawieniach.  [-> Settings]",
               "  The language of the whole app is in Settings.  [-> Settings]"),
        ]

    # ── PC Workman's own footprint ───────────────────────────────────────────
    def _resp_self_usage(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import os
            import psutil
            me = psutil.Process(os.getpid())
            mb = me.memory_info().rss / 1024 ** 2
            me.cpu_percent(None)
            time.sleep(0.5)
            cpu = me.cpu_percent(None) / (psutil.cpu_count() or 1)
            total = psutil.virtual_memory().total / 1024 ** 2
        except Exception:
            return [_t(lang, f"{self.PREFIX} Nie mogę teraz zmierzyć samego siebie.",
                       f"{self.PREFIX} I cannot measure myself right now.")]
        return [
            _t(lang, f"{self.PREFIX} PC Workman teraz: CPU {cpu:.1f}%, RAM {mb:.0f} MB "
                     f"({mb / total * 100:.1f}% pamięci).",
               f"{self.PREFIX} PC Workman right now: CPU {cpu:.1f}%, RAM {mb:.0f} MB "
               f"({mb / total * 100:.1f}% of memory)."),
            _t(lang, "  Pomiary robię w tle, a ciężkie skany tylko na prośbę. Jeśli liczby u Ciebie "
                     "są wyraźnie wyższe, daj znać przez formularz na stronie: [-> pcworkman.dev]",
               "  Measuring runs in the background; heavy scans only when asked. If your numbers "
               "are clearly higher, tell me through the form on the site: [-> pcworkman.dev]"),
        ]

    # ── XMP / RAM speed ──────────────────────────────────────────────────────
    def _resp_xmp_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            hw = user_knowledge.get_all_hardware() or {}
        except Exception:
            hw = {}
        spd = int(hw.get("ram_speed_mhz") or 0)
        rtype = str(hw.get("ram_type") or "").upper()
        if not spd:
            return [_t(lang, f"{self.PREFIX} Nie znam jeszcze prędkości RAM; zapytaj za chwilę.",
                       f"{self.PREFIX} I do not know the RAM speed yet; ask again shortly.")]
        base = {2133: "DDR4", 2400: "DDR4", 4800: "DDR5"}
        lines = [_t(lang, f"{self.PREFIX} RAM pracuje teraz na {spd} MHz.",
                    f"{self.PREFIX} RAM runs at {spd} MHz right now.")]
        if spd in base and (not rtype or base[spd] in rtype):
            lines.append(_t(lang,
                f"  To bazowa prędkość {base[spd]}, więc XMP / EXPO jest najpewniej wyłączony. "
                f"Jeśli na naklejce kości jest więcej (np. 3200 MHz), tracisz wydajność w grach.",
                f"  That is the base {base[spd]} speed, so XMP / EXPO is most likely off. If the "
                f"sticker says more (e.g. 3200 MHz), you are leaving game performance behind."))
            lines.append(_t(lang,
                "  Włączysz go w BIOS-ie: profil XMP 1 (MSI: A-XMP / XMP, ASUS: D.O.C.P., Gigabyte: XMP). "
                "Po zmianie warto sprawdzić stabilność.",
                "  Turn it on in the BIOS: XMP profile 1 (MSI: A-XMP / XMP, ASUS: D.O.C.P., Gigabyte: XMP). "
                "Check stability afterwards."))
        else:
            lines.append(_t(lang,
                "  To więcej niż prędkość bazowa, więc XMP / EXPO wygląda na włączony.",
                "  That is above the base speed, so XMP / EXPO looks on."))
        return lines

    # _resp_network_drop: the network guide answers it now, tested first (r_network.py, 2026-11-20)

    # ── "nothing works" ──────────────────────────────────────────────────────
    def _resp_vague_problem(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Pomogę. Napisz w paru słowach, co dokładnie się dzieje, na przykład:",
               f"{self.PREFIX} I will help. Tell me in a few words what happens, for example:"),
            _t(lang, "  „gra się przycina”, „komputer się zawiesza”, „wentylatory głośno chodzą”, "
                     "„nie działa nakładka w grze”.",
               "  \"the game stutters\", \"the PC freezes\", \"the fans are loud\", "
               "\"the in-game overlay does not show\"."),
            _t(lang, "  Albo kliknij „Wszystko działa?”, a sprawdzę komputer od razu.",
               "  Or click \"Is everything OK?\" and I check the PC right away."),
        ]

    # ── what slows games on THIS PC, checked now ─────────────────────────────
    def _fps_checklist(self, lang: str) -> List[str]:
        """Short list of real findings for FPS drops / stutter: RAM size and
        what holds it, RAM speed (XMP), graphics driver age, power plan, a
        busy background process. Only what is actually off is listed."""
        out = []
        try:
            import psutil
            vm = psutil.virtual_memory()
            gb = vm.total / 1024 ** 3
            if gb < 12:
                top, _ = self._ram_by_app(3)
                br = next(((n, mb) for n, mb in top
                           if any(n.lower().startswith(k) for k in self._BROWSERS)), None)
                extra = (_t(lang, f"; {br[0]} trzyma teraz {self._mb_text(br[1])}",
                            f"; {br[0]} holds {self._mb_text(br[1])} now") if br else "")
                out.append(_t(lang,
                    f"  ⚠ RAM {gb:.0f} GB, zajęte {vm.percent:.0f}%: do gier to mało{extra}.",
                    f"  ⚠ RAM {gb:.0f} GB, {vm.percent:.0f}% used: little for games{extra}."))
        except Exception:
            pass
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            spd = int((user_knowledge.get_all_hardware() or {}).get("ram_speed_mhz") or 0)
            if spd in (2133, 2400, 4800):
                out.append(_t(lang,
                    f"  ⚠ RAM na {spd} MHz: XMP najpewniej wyłączony, w grach to kilka-kilkanaście % FPS ('xmp').",
                    f"  ⚠ RAM at {spd} MHz: XMP is most likely off, worth several % FPS in games ('xmp')."))
        except Exception:
            pass
        try:
            from core.component_check import _class_drivers, _GPU_CLASS, _age_months
            g = next((d for d in _class_drivers(_GPU_CLASS) if d["date"]
                      and "basic display" not in d["name"].lower()), None)
            if g and _age_months(g["date"]) >= 12:
                out.append(_t(lang,
                    f"  ⚠ Sterownik grafiki z {g['date']:%m.%Y}: nowszy często poprawia płynność.",
                    f"  ⚠ Graphics driver from {g['date']:%Y-%m}: a newer one often helps smoothness."))
        except Exception:
            pass
        try:
            hog = self._cpu_by_app(1)
            if hog and hog[0][1] >= 8:
                out.append(_t(lang,
                    f"  ⚠ W tle {hog[0][0]} bierze {hog[0][1]:.0f}% procesora.",
                    f"  ⚠ {hog[0][0]} takes {hog[0][1]:.0f}% of the CPU in the background."))
        except Exception:
            pass
        if not out:
            out.append(_t(lang, "  ✓ RAM, sterownik grafiki i procesy w tle wyglądają dobrze.",
                          "  ✓ RAM, graphics driver and background processes look fine."))
        return out

    # ── restarts and blue screens, from the Windows event log ────────────────
    @staticmethod
    def _crash_events(limit: int = 12) -> list:
        """[(datetime, id)] of Kernel-Power 41 (restart without a clean
        shutdown), 6008 (unexpected shutdown) and 1001 (BugCheck = blue
        screen), newest first. wevtutil answers in well under a second."""
        import subprocess
        try:
            out = subprocess.run(
                ["wevtutil", "qe", "System",
                 "/q:*[System[(EventID=41 or EventID=1001 or EventID=6008)]]",
                 f"/c:{limit}", "/rd:true", "/f:text"],
                capture_output=True, timeout=6,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            text = out.decode("utf-8", errors="replace")
        except Exception:
            return []
        events, date = [], None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("Date:"):
                try:
                    raw = line.split(":", 1)[1].strip()[:19]
                    utc = _dt.datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S")
                    date = utc.replace(tzinfo=_dt.timezone.utc).astimezone().replace(tzinfo=None)
                except Exception:
                    date = None
            elif line.startswith("Event ID:") and date is not None:
                try:
                    events.append((date, int(line.split(":", 1)[1].strip())))
                except ValueError:
                    pass
                date = None
        return events

    def _resp_restart_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ev = self._crash_events()
        month_ago = _dt.datetime.now() - _dt.timedelta(days=30)
        recent = [e for e in ev if e[0] >= month_ago]
        bsod = [e for e in recent if e[1] == 1001]
        power = [e for e in recent if e[1] == 41]
        lines = []
        if not recent:
            lines.append(_t(lang,
                f"{self.PREFIX} W dzienniku Windows z ostatnich 30 dni nie ma nagłych restartów "
                f"ani niebieskich ekranów.",
                f"{self.PREFIX} The Windows log has no sudden restarts or blue screens in the "
                f"last 30 days."))
        else:
            lines.append(_t(lang,
                f"{self.PREFIX} Dziennik Windows, ostatnie 30 dni: {len(power)} restart(ów) bez "
                f"czystego zamknięcia, {len(bsod)} niebieski(ch) ekran(ów).",
                f"{self.PREFIX} Windows log, last 30 days: {len(power)} restart(s) without a "
                f"clean shutdown, {len(bsod)} blue screen(s)."))
            shown = sorted({e[0].strftime("%d.%m %H:%M") for e in recent if e[1] in (41, 1001)},
                           reverse=True)[:4]
            if shown:
                lines.append(_t(lang, "  Kiedy: ", "  When: ") + ", ".join(shown))
            lines.append("")
            if bsod:
                lines.append(_t(lang,
                    "  Niebieski ekran to zwykle sterownik albo niestabilny RAM (XMP, podkręcanie). "
                    "Najpierw sterownik grafiki, potem test pamięci.",
                    "  A blue screen is usually a driver or unstable RAM (XMP, overclock). "
                    "Graphics driver first, then a memory test."))
            if power and not bsod:
                lines.append(_t(lang,
                    "  Restart bez niebieskiego ekranu najczęściej oznacza zasilanie: zasilacz "
                    "pod obciążeniem (granie), listwa, albo przegrzanie.",
                    "  A restart with no blue screen most often points to power: the PSU under "
                    "load (gaming), the power strip, or overheating."))
            lines.append(_t(lang, "  Sterowniki z datami: 'sterowniki'.  Temperatury: 'temperatury'.",
                            "  Drivers with dates: 'drivers'.  Temperatures: 'temperatures'."))
        try:
            from hck_gpt.guide_links import take_offer
            extra = take_offer("power_after_restart", lang)
            if extra:
                lines += extra
        except Exception:
            pass
        return lines

    # ── where is a page ──────────────────────────────────────────────────────
    _PAGES = (
        (("optymaliz", "optimiz", "turbo"), "Optimization",
         ("Optymalizacja", "Optimization")),
        (("autostart", "startup"), "Startup Manager", ("Autostart", "Startup")),
        (("usług", "uslug", "services"), "Services Manager", ("Usługi", "Services")),
        (("wentylator", "fan"), "Fan Control", ("Kontrola wentylatorów", "Fan Control")),
        (("ustawie", "settings"), "Settings", ("Ustawienia", "Settings")),
        (("histori", "pamięć aktyw", "pamiec aktyw", "activity"), "Activity Memory",
         ("Pamięć aktywności", "Activity Memory")),
        (("sterownik", "driver"), "Setup & Drivers", ("Konfiguracja i sterowniki", "Setup & Drivers")),
        (("overclock", "podkręc", "podkrec"), "Overclock", ("Overclock", "Overclock")),
    )

    def _resp_where_page(self, r: ParseResult, lang: str = "pl") -> List[str]:
        raw = (r.raw_text or "").lower()
        for keys, nav, names in self._PAGES:
            if any(k in raw for k in keys):
                name = names[0] if lang != "en" else names[1]
                out = [_t(lang, f"{self.PREFIX} {name} jest w menu po lewej. Przeniosę Cię:",
                          f"{self.PREFIX} {name} is in the menu on the left. Take me there:"),
                       f"  [-> {nav}]"]
                if nav == "Optimization":
                    out.append("§OFFER optimize")
                return out
        return [_t(lang, f"{self.PREFIX} Wszystkie strony są w menu po lewej. Której szukasz?",
                   f"{self.PREFIX} All pages are in the menu on the left. Which one are you after?")]
