"""hck_gpt.responses.r_meta - questions about hck_GPT, the program and the
user's data (fourth long test, 2026-11-17: 34 of 73 questions ended in
"I did not understand", most of them in these groups).

    learning_eta     how much longer does it learn
    lhm_help         LibreHardwareMonitor: what, where, how it connects
    project_status   is PC Workman still being developed, where is a new version
    whats_new        anything new / anything to watch out for
    presence         "halo", "jesteś?", "rozumiesz?"
    meta_feedback    "nie rozpoznajesz pytań"
    compliment       "fajny ziomek jesteś"
    error_help       "mam błąd", "coś nie działa?"
    data_export      move the data to a new Windows (and data_export_run)
    data_reset       delete the data / the learning
"""
from __future__ import annotations

import time

from hck_gpt.responses.common import List, ParseResult, _t


class MetaResponses:

    def _resp_learning_eta(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from core.thermal_baseline import thermal_baseline as tb, T_TRAINED, T_CALIBRATED
        except Exception:
            return self._resp_ai_context(r, lang)
        pct = tb.overall_training_pct()
        bd = tb.training_breakdown()
        lines = [_t(lang, f"{self.PREFIX} Twoje typowe obciążenia znam w {pct}%. Każda minuta pracy komputera to jedna próbka.",
                    f"{self.PREFIX} I know your typical workloads {pct}%. Every minute the PC runs is one sample.")]
        names = {"idle": ("bezczynność", "idle"), "light": ("lekka praca", "light work"),
                 "medium": ("średnie obciążenie", "medium load"), "heavy": ("ciężkie obciążenie", "heavy load"),
                 "gaming": ("granie", "gaming")}
        total = max(bd["total"], 1)
        for b, n in bd["typical"].items():
            nm = names.get(b, (b, b))[0 if lang != "en" else 1]
            if n >= T_TRAINED:
                left = max(0, T_CALIBRATED - n)
                lines.append(_t(lang, f"  ✓ {nm}: {n} min, nauczone; pełna kalibracja za ok. {left // 60} h tej pracy." if left else f"  ✓ {nm}: {n} min, w pełni skalibrowane.",
                                f"  ✓ {nm}: {n} min, learned; full calibration in about {left // 60} h of this work." if left else f"  ✓ {nm}: {n} min, fully calibrated."))
            else:
                lines.append(_t(lang, f"  · {nm}: {n} min, do nauczenia jeszcze ok. {T_TRAINED - n} min.",
                                f"  · {nm}: {n} min, about {T_TRAINED - n} min to go."))
        if bd["rare"]:
            share = sum(bd["rare"].values()) / total * 100
            rare_pl = ", ".join(f"{names.get(b, (b, b))[0]} {n} min" for b, n in bd["rare"].items())
            rare_en = ", ".join(f"{names.get(b, (b, b))[1]} {n} min" for b, n in bd["rare"].items())
            lines.append(_t(lang,
                f"  Rzadkie u Ciebie ({share:.0f}% czasu): {rare_pl}. Uczę się ich przy okazji, nie wliczam do procentu.",
                f"  Rare on this PC ({share:.0f}% of the time): {rare_en}. I learn them along the way; they are not in the percentage."))
        try:
            cpu_n = tb._metric_total("cpu_temp")
            if bd["metric"] != "cpu_temp":
                lines.append(_t(lang,
                    f"  Temperatura CPU: {cpu_n} próbek z czujnika." + ("" if cpu_n else " Mierzę ją tylko z LibreHardwareMonitor ('co to librehardwaremonitor')."),
                    f"  CPU temperature: {cpu_n} samples from the sensor." + ("" if cpu_n else " I measure it only with LibreHardwareMonitor ('what is librehardwaremonitor').")))
        except Exception:
            pass
        lines.append(_t(lang, "  Nie przestaję się uczyć: norma przesuwa się razem z tym, jak używasz komputera.",
                        "  I never stop learning: the normal moves with how you use the PC."))
        lines.append("  [-> Learning Center]")
        return lines

    def _resp_lhm_help(self, r: ParseResult, lang: str = "pl") -> List[str]:
        # "I see it" only when values actually arrive (2026-11-20: the server
        # answered, only fan speeds got through, and the chat said "OK")
        connected, answered, cpu_t = "", None, -1.0
        try:
            from core.live_collector import fetch_mb_sensors
            mb = fetch_mb_sensors()
            answered = mb.get("answered")
            cpu_t = float(mb.get("cpu_temp", -1.0) or -1.0)
            volts = [mb.get(k, -1.0) for k in ("volt_12v", "volt_vcore", "volt_5v")]
            if cpu_t > 0 or any(v and v > 0 for v in volts):
                connected = "LibreHardwareMonitor" if mb.get("source") == "lhm" else "OpenHardwareMonitor"
        except Exception:
            connected = ""
        lines = [_t(lang,
            f"{self.PREFIX} LibreHardwareMonitor to darmowy program, który odczytuje czujniki: temperaturę CPU, napięcia i obroty wentylatorów. Windows sam ich nie podaje.",
            f"{self.PREFIX} LibreHardwareMonitor is a free program that reads the sensors: CPU temperature, voltages and fan speeds. Windows does not report them itself.")]
        if connected:
            extra_pl = f" Temperatura CPU teraz: {cpu_t:.0f}°C." if cpu_t > 0 else ""
            extra_en = f" CPU temperature now: {cpu_t:.0f}°C." if cpu_t > 0 else ""
            lines.append(_t(lang, f"§OK Już go widzę ({connected}): dane trafiają do PC Workman." + extra_pl,
                            f"§OK I already see it ({connected}): its data reaches PC Workman." + extra_en))
        elif answered:
            lines.append(_t(lang,
                f"§WARN Serwer na porcie {answered} odpowiada, ale nie przychodzą z niego temperatury ani napięcia. "
                "Uruchom LibreHardwareMonitor jako administrator, bez tego nie widzi czujników.",
                f"§WARN The server on port {answered} answers, but no temperatures or voltages come from it. "
                "Run LibreHardwareMonitor as administrator; without it, it cannot see the sensors."))
        # "czy konieczny jest serio?" (fifth long test, 2026-11-17)
        lines.append(_t(lang,
            "  Czy jest konieczny? Nie. Bez niego działa wszystko poza temperaturą CPU, napięciami i obrotami wentylatorów: "
            "obciążenie, GPU, historia, nauka i czat. Instalujesz go tylko wtedy, gdy chcesz widzieć te trzy rzeczy.",
            "  Do you need it? No. Without it everything works except the CPU temperature, voltages and fan speeds: "
            "load, GPU, history, learning and the chat. Install it only if you want to see those three."))
        lines.append(_t(lang,
            "  Jest otwartoźródłowy i darmowy; pobieraj go tylko z oficjalnej strony na GitHubie (przycisk „Zobacz sam”).",
            "  It is open source and free; only download it from the official GitHub page (the \"See for yourself\" button)."))
        lines += [
            _t(lang, "  1. Pobierz z GitHub: LibreHardwareMonitor → Releases → plik .zip. Rozpakuj gdziekolwiek (np. C:\\Programy\\LHM), nie wymaga instalacji.",
               "  1. Download from GitHub: LibreHardwareMonitor → Releases → the .zip. Unpack anywhere (e.g. C:\\Tools\\LHM); no installation."),
            _t(lang, "  2. Uruchom LibreHardwareMonitor.exe jako administrator (prawy klik).",
               "  2. Run LibreHardwareMonitor.exe as administrator (right-click)."),
            _t(lang, "  3. Options → Remote Web Server → Run (port 8085). Z tego serwera PC Workman czyta czujniki.",
               "  3. Options → Remote Web Server → Run (port 8085). PC Workman reads the sensors from it."),
            _t(lang, "  4. Options → Run On Windows Startup, żeby działał zawsze. Po chwili temperatura CPU i napięcia pojawią się w PC Workman.",
               "  4. Options → Run On Windows Startup, so it is always on. CPU temperature and voltages then appear in PC Workman."),
            "§OFFER lhm",
        ]
        return lines

    def _resp_project_status(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from utils.app_version import APP_VERSION as VERSION, RELEASE_DATE
        except Exception:
            VERSION, RELEASE_DATE = "?", ""
        return [
            _t(lang, f"{self.PREFIX} Tak, PC Workman jest rozwijany. Masz wersję {VERSION}" + (f" z {RELEASE_DATE}" if RELEASE_DATE else "") + ".",
               f"{self.PREFIX} Yes, PC Workman is in active development. You have version {VERSION}" + (f" from {RELEASE_DATE}" if RELEASE_DATE else "") + "."),
            _t(lang, "  Marcin pracuje nad nim po pracy; każdą wersję testuje godzinami na własnym komputerze, a zgłoszenia czyta sam.",
               "  Marcin works on it after his job; every version is tested for hours on his own PC, and he reads the reports himself."),
            _t(lang, "  Nowe wersje, lista zmian i historia projektu: [-> pcworkman.dev]",
               "  New versions, the change list and the project's story: [-> pcworkman.dev]"),
            _t(lang, "  Robi też grę Scaling Laws, o tym również na stronie.", "  He also makes the game Scaling Laws, on the site as well."),
        ]

    def _resp_whats_new(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'coś nowego?', 'znalazłeś coś?', 'na co zwrócić uwagę?'"""
        from core.pc_insight import findings
        lines = [_t(lang, f"{self.PREFIX} Co zauważyłem:", f"{self.PREFIX} What I noticed:")]
        try:
            rc = self._resp_recent_changes(r, lang)
            lines += [l for l in rc[1:] if l.strip()][:3]
        except Exception:
            pass
        try:
            from hck_stats_engine.load_periods import periods
            ps = periods(time.time() - 86400, time.time())
            if ps:
                p = ps[0]
                lines.append(_t(lang, f"  · Ostatni okres dużego obciążenia: {p['minutes']} min" + (f" ({p['process_name']})" if p.get("process_name") else "") + ".",
                                f"  · The last busy stretch: {p['minutes']} min" + (f" ({p['process_name']})" if p.get("process_name") else "") + "."))
        except Exception:
            pass
        fs = [f for f in findings(deep=False) if f["sev"] >= 1][:3]
        if fs:
            lines.append(_t(lang, "  Na co zwrócić uwagę:", "  Worth your attention:"))
            for f in fs:
                lines.append("  ⚠ " + self._finding_text(f, lang))
        else:
            lines.append(_t(lang, "  ✓ Nic, na co trzeba by zwrócić uwagę.", "  ✓ Nothing that needs attention."))
        try:
            from core.thermal_baseline import thermal_baseline as tb
            lines.append(_t(lang, f"  · Nauka: {tb.overall_training_pct()}%.", f"  · Learning: {tb.overall_training_pct()}%."))
        except Exception:
            pass
        return lines

    def _resp_presence(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
            cpu, ram = psutil.cpu_percent(interval=0.3), psutil.virtual_memory().percent
            tail = _t(lang, f" Komputer: CPU {cpu:.0f}%, RAM {ram:.0f}%.", f" The PC: CPU {cpu:.0f}%, RAM {ram:.0f}%.")
        except Exception:
            tail = ""
        return [_t(lang, f"{self.PREFIX} Jestem, słucham." + tail + " Pytaj o cokolwiek dotyczącego komputera.",
                   f"{self.PREFIX} I am here, listening." + tail + " Ask anything about the PC.")]

    def _resp_meta_feedback(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Przepraszam, nie każde pytanie jeszcze rozpoznaję. Uczę się z prawdziwych rozmów, więc każde nietrafione pytanie trafia na listę poprawek.",
               f"{self.PREFIX} Sorry, I do not recognise every question yet. I learn from real conversations, so each miss goes on the list of fixes."),
            _t(lang, "  Najlepiej działam, gdy pytanie dotyczy komputera, na przykład: „co spowalnia komputer”, „czy mam wąskie gardło”, „w co grałem”.",
               "  I work best with questions about the PC, for example: \"what slows my pc\", \"do I have a bottleneck\", \"what did I play\"."),
            _t(lang, "  Pytanie, którego nie zrozumiałem, możesz wysłać autorowi: [-> pcworkman.dev]",
               "  You can send the author a question I did not understand: [-> pcworkman.dev]"),
        ]

    def _resp_compliment(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [_t(lang, f"{self.PREFIX} Dzięki! Robię, co mogę, a Twój komputer daje mi dużo materiału do nauki. 🙂",
                   f"{self.PREFIX} Thanks! I do my best, and your PC gives me plenty to learn from. 🙂")]

    def _resp_error_help(self, r: ParseResult, lang: str = "pl") -> List[str]:
        lines = [_t(lang, f"{self.PREFIX} Pomogę. Przepisz treść błędu albo powiedz, gdzie wyskakuje (gra, program, start Windows, niebieski ekran).",
                    f"{self.PREFIX} I will help. Type the error message, or say where it shows up (a game, a program, Windows start, a blue screen).")]
        try:
            from core.pc_insight import hardware_errors
            e = hardware_errors(days=7)
            if e.get("ok"):
                n = e["whea"] + e["bsod"] + e["disk"] + e["ntfs"] + e["restart"]
                lines.append(_t(lang, f"  W dzienniku Windows z 7 dni: {n} zdarzeń sprzętowych (błędy, niebieskie ekrany, nagłe restarty)." if n else
                                "  W dzienniku Windows z 7 dni nie ma błędów sprzętu ani nagłych restartów.",
                                f"  The Windows log of 7 days has {n} hardware events (errors, blue screens, sudden restarts)." if n else
                                "  The Windows log of 7 days has no hardware errors or sudden restarts."))
        except Exception:
            pass
        lines.append(_t(lang, "  Jeśli to błąd PC Workman: data\\logs\\startup.log ma szczegóły, które warto dołączyć do zgłoszenia.",
                        "  If it is a PC Workman error: data\\logs\\startup.log has the details worth attaching to a report."))
        return lines

    def _resp_data_export(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Tak. Mogę spakować wszystko, czego się nauczyłem, do jednego pliku ZIP na pulpicie:",
               f"{self.PREFIX} Yes. I can pack everything I learned into one ZIP on the Desktop:"),
            _t(lang, "  historię (baza statystyk), naukę, ustawienia, nagrania obserwacji i to, co wiem o sprzęcie.",
               "  the history (statistics database), learning, settings, observation recordings and what I know about the hardware."),
            _t(lang, "  Na nowym Windows: rozpakuj PC Workman, przed pierwszym uruchomieniem wgraj foldery z ZIP-a (instrukcja jest w środku).",
               "  On the new Windows: unpack PC Workman and, before the first start, copy the folders from the ZIP (instructions inside)."),
            "§OFFER export",
        ]

    def _resp_data_export_run(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.data_export import export_zip
        res = export_zip()
        if res.get("error"):
            return [_t(lang, f"{self.PREFIX} Nie udało się utworzyć pliku: {res['error']}",
                       f"{self.PREFIX} Could not create the file: {res['error']}")]
        return [_t(lang, f"{self.PREFIX} ✓ Gotowe: {res['files']} plików, {res['mb']} MB.",
                   f"{self.PREFIX} ✓ Done: {res['files']} files, {res['mb']} MB."),
                f"  {res['path']}",
                _t(lang, "  W środku jest README_IMPORT.txt z krokami dla nowego systemu.",
                   "  README_IMPORT.txt inside has the steps for the new system.")]

    def _resp_data_reset(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Da się, w dwóch zakresach:", f"{self.PREFIX} Yes, in two scopes:"),
            _t(lang, "  · Wiedza hck_GPT (profil sprzętu, fakty, rozmowy): wpisz 'reset', zapytam o potwierdzenie.",
               "  · hck_GPT's knowledge (hardware profile, facts, chats): type 'reset', I will ask to confirm."),
            _t(lang, "  · Historia i nauka: zamknij PC Workman i usuń data\\logs\\hck_stats.db oraz data\\cache\\thermal_baseline.json. Program zacznie od zera.",
               "  · History and learning: close PC Workman and delete data\\logs\\hck_stats.db and data\\cache\\thermal_baseline.json. It starts from zero."),
            _t(lang, "  Przed usunięciem możesz zrobić kopię: 'zrób export'.", "  Before deleting you can make a copy: 'export data'."),
        ]
