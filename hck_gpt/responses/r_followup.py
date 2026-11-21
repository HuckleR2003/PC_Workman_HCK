"""hck_gpt.responses.r_followup - conversations of several turns (2026-11-17).

The third long test asked for conversations like:

    "Mam wrażenie, że komputer wolno działa."  -> what slows it, names a process
    "A co najbardziej go obciąża?"             -> the heaviest, remembered as "it"
    "A czy mogę to wyłączyć?"                  -> about that process
    "Jak to zrobić?"                           -> steps for that action
    "Czy to pomoże?"                           -> measured effect of that action

    "Chcę pograć w CS2, ale mam lagi" / "Czy komputer sobie z tym radzi?" /
    "Co zamknąć przed grą?" / "A co jeśli dalej będzie zacinać?" /
    "Jak sprawdzić, że jest poprawa?"          -> the observation note

Each handler reads what the previous turns left in session memory: the
last intent, the last process, the last game.
"""
from __future__ import annotations

from hck_gpt.responses.common import List, ParseResult, _t


def _last_intent() -> str:
    try:
        from hck_gpt.memory.session_memory import session_memory
        # handlers run before their own turn is stored: the last entry is
        # the previous answer
        for t in reversed(list(session_memory._turn_context)):
            it = str(t.get("intent") or "")
            if it and it not in ("how_to", "will_it_help", "unknown", "reaction", "thanks"):
                return it
    except Exception:
        pass
    return ""


def _ref(kind: str) -> str:
    try:
        from hck_gpt.memory.session_memory import session_memory
        return session_memory.last_reference(kind) or ""
    except Exception:
        return ""


class FollowupResponses:

    _CLOSE_INTENTS = {"process_kill", "closable_apps", "background_load", "slowdown_cause",
                      "top_resource_hog", "processes", "why_slow", "ram_why_high",
                      "process_anomaly", "slower_lately"}

    # ── "Jak to zrobić?" ─────────────────────────────────────────────────────
    def _resp_how_to(self, r: ParseResult, lang: str = "pl") -> List[str]:
        last = _last_intent()
        proc = _ref("process")
        P = self.PREFIX
        if last in self._CLOSE_INTENTS or (proc and last in ("", "process_info", "process_identity")):
            name = proc or _t(lang, "ten program", "that program")
            return [
                _t(lang, f"{P} Zamykanie {name}, bezpiecznie:", f"{P} Closing {name}, safely:"),
                _t(lang, "  1. Zamknij go normalnie: krzyżyk w oknie albo prawy klik na ikonie przy zegarze → Zakończ.",
                   "  1. Close it normally: the X in its window, or right-click its icon by the clock → Exit."),
                _t(lang, "  2. Jeśli nie odpowiada: Ctrl+Shift+Esc → Menedżer zadań → zaznacz go → Zakończ zadanie.",
                   "  2. If it does not respond: Ctrl+Shift+Esc → Task Manager → select it → End task."),
                _t(lang, "  3. Żeby nie wracał przy każdym starcie, wyłącz go w autostarcie:  [-> Startup Manager]",
                   "  3. To stop it coming back at every start, turn it off in startup:  [-> Startup Manager]"),
                _t(lang, "  Zamiast zamykać, PC Workman może go uśpić: App Hibernation  [-> Optimization]",
                   "  Instead of closing it, PC Workman can put it to sleep: App Hibernation  [-> Optimization]"),
            ]
        if last in ("startup_check", "startup_slowdown", "startup_safety"):
            return [_t(lang, f"{P} Autostart, krok po kroku:", f"{P} Startup, step by step:"),
                    _t(lang, "  1. Otwórz Startup Manager (link niżej).", "  1. Open Startup Manager (link below)."),
                    _t(lang, "  2. Przy programie z oceną „wyłącz” kliknij przełącznik.", "  2. Click the switch next to a program marked \"disable\"."),
                    _t(lang, "  3. Wyłączone wracają jednym kliknięciem w zakładce Disabled; nic się nie odinstalowuje.",
                       "  3. Disabled ones come back with one click in the Disabled tab; nothing is uninstalled."),
                    "  [-> Startup Manager]"]
        if last in ("xmp_check",):
            return [_t(lang, f"{P} Włączenie XMP w BIOS-ie:", f"{P} Turning on XMP in the BIOS:"),
                    _t(lang, "  1. Uruchom ponownie i wciskaj Del (MSI, ASUS, Gigabyte) zaraz po starcie.",
                       "  1. Restart and keep pressing Del (MSI, ASUS, Gigabyte) right after power-on."),
                    _t(lang, "  2. MSI: na górze ekranu przełącznik A-XMP / XMP, wybierz Profile 1. ASUS: D.O.C.P., Gigabyte: XMP.",
                       "  2. MSI: the A-XMP / XMP switch at the top, pick Profile 1. ASUS: D.O.C.P., Gigabyte: XMP."),
                    _t(lang, "  3. F10, zapisz i uruchom ponownie. Potem zapytaj mnie 'czy xmp jest włączony'.",
                       "  3. F10 to save and restart. Then ask me 'is xmp on'."),
                    _t(lang, "  Jeśli po tym komputer się zawiesza albo nie startuje, wróć do ustawień domyślnych (Clear CMOS / F6 w BIOS-ie).",
                       "  If the PC then hangs or will not start, go back to defaults (Clear CMOS / F6 in the BIOS).")]
        if last in ("virtual_memory",):
            return [_t(lang, f"{P} Pamięć wirtualna:", f"{P} Virtual memory:"),
                    _t(lang, "  1. Otwórz ustawienia (link niżej), zakładka Zaawansowane.", "  1. Open the settings (link below), Advanced tab."),
                    _t(lang, "  2. Wydajność → Ustawienia… → zakładka Zaawansowane → Pamięć wirtualna → Zmień…",
                       "  2. Performance → Settings… → Advanced tab → Virtual memory → Change…"),
                    _t(lang, "  3. Zaznacz „Automatycznie zarządzaj…”, OK, uruchom ponownie.", "  3. Tick \"Automatically manage…\", OK, restart."),
                    "  [-> Virtual Memory]"]
        if last in ("services_advice", "unnecessary_programs"):
            return [_t(lang, f"{P} Usługi bezpiecznie: w Services Manager wybierz profil (Gaming / Economy), a TURBO wyłączy zbędne tylko na czas grania i przywróci je po wszystkim.",
                       f"{P} Services safely: pick a profile in Services Manager (Gaming / Economy); TURBO turns the unneeded ones off only while you play and restores them."),
                    "  [-> Services Manager]"]
        if last in ("ram_enough", "bottleneck", "upgrade_feasibility", "ram_compat", "new_pc_advice"):
            return [_t(lang, f"{P} Dokładanie RAM:", f"{P} Adding RAM:"),
                    _t(lang, "  1. Sprawdź wolne gniazda i typ pamięci: 'czy mogę dołożyć RAM'.", "  1. Check free slots and memory type: 'can I add RAM'."),
                    _t(lang, "  2. Kup kość tego samego typu i prędkości co obecna (najlepiej zestaw 2 sztuk).",
                       "  2. Buy a module of the same type and speed as the current one (ideally a kit of two)."),
                    _t(lang, "  3. Wyłącz komputer, odłącz zasilanie, włóż kość aż zatrzaski kliknął.",
                       "  3. Shut down, unplug, push the module in until the latches click."),
                    "  [-> Upgrade Readiness]"]
        if last in ("driver_status", "driver_update_where", "gpu_driver"):
            return self._resp_driver_update_where(r, lang)
        if last in ("power_plan",):
            return [_t(lang, f"{P} Win+R → powercfg.cpl → zaznacz Wysoka wydajność. Na czas grania zrobi to za Ciebie TURBO.",
                       f"{P} Win+R → powercfg.cpl → select High performance. TURBO does it for you while gaming."),
                    "  [-> Optimization]"]
        return [_t(lang, f"{P} Powiedz, co chcesz zrobić (np. 'jak wyłączyć program z autostartu'), a podam kroki.",
                   f"{P} Tell me what you want to do (e.g. 'how to remove a program from startup') and I will give the steps.")]

    # ── "Czy to pomoże?" ─────────────────────────────────────────────────────
    def _process_footprint(self, name: str):
        """(MB, CPU %) of every instance of a running program, measured."""
        import time
        try:
            import psutil
            base = name.lower().rsplit(".exe", 1)[0]
            procs = [p for p in psutil.process_iter(["name", "memory_info"])
                     if (p.info.get("name") or "").lower().rsplit(".exe", 1)[0] == base]
            if not procs:
                return None
            for p in procs:
                try:
                    p.cpu_percent(None)
                except Exception:
                    pass
            time.sleep(0.4)
            mb = cpu = 0.0
            for p in procs:
                try:
                    mi = p.info.get("memory_info")
                    mb += (mi.rss / 1024 ** 2) if mi else 0
                    cpu += p.cpu_percent(None)
                except Exception:
                    continue
            return mb, cpu / (psutil.cpu_count() or 1)
        except Exception:
            return None

    def _resp_will_it_help(self, r: ParseResult, lang: str = "pl") -> List[str]:
        last = _last_intent()
        proc = _ref("process")
        P = self.PREFIX
        if proc and (last in self._CLOSE_INTENTS or last in ("how_to", "")):
            fp = self._process_footprint(proc)
            if fp:
                mb, cpu = fp
                try:
                    import psutil
                    vm = psutil.virtual_memory()
                    now = vm.percent
                    after = max(0.0, (vm.used - mb * 1024 ** 2) / vm.total * 100)
                except Exception:
                    now = after = None
                lines = [_t(lang, f"{P} Zmierzyłem {proc}: trzyma {self._mb_text(mb)} RAM i bierze {cpu:.0f}% procesora.",
                            f"{P} I measured {proc}: it holds {self._mb_text(mb)} of RAM and uses {cpu:.0f}% of the CPU.")]
                if now is not None:
                    lines.append(_t(lang, f"  Po zamknięciu RAM spadnie z {now:.0f}% do ok. {after:.0f}%.",
                                    f"  After closing it, RAM drops from {now:.0f}% to about {after:.0f}%."))
                big = mb >= 500 or cpu >= 10
                lines.append(("§OK " if big else "  ") + _t(lang,
                    "Tak, to odczuwalna różnica." if big else "Niewielka różnica: ten program nie jest głównym problemem.",
                    "Yes, a noticeable difference." if big else "A small difference: this program is not the main problem."))
                lines.append(_t(lang, "  Pewność da nagranie przed i po: 'zacznij nagrywanie'.",
                                "  A before-and-after recording settles it: 'start recording'."))
                return lines
        if last == "xmp_check":
            return [_t(lang, f"{P} Tak, w grach zależnych od procesora XMP daje zwykle kilka do kilkunastu procent FPS i płynniejsze minimalne klatki.",
                       f"{P} Yes, in CPU-bound games XMP usually gives a few to a dozen percent more FPS and smoother lows.")]
        if last in ("startup_check", "startup_slowdown"):
            return [_t(lang, f"{P} Skróci uruchamianie Windows i zwolni trochę RAM od startu. Szybsza praca po starcie zależy bardziej od tego, co otwierasz.",
                       f"{P} It shortens the Windows start and frees some RAM from boot. Speed after boot depends more on what you open.")]
        if last in ("ram_enough", "bottleneck", "new_pc_advice"):
            return [_t(lang, f"{P} Tak: przy 16 GB pamięć przestanie dochodzić do 90%, Windows nie będzie odkładał danych na dysk i zniknie większość przycięć.",
                       f"{P} Yes: with 16 GB memory stops reaching 90%, Windows stops moving data to disk and most stutters go away.")]
        return [_t(lang, f"{P} Najpewniej sprawdzisz to nagraniem: 'zacznij nagrywanie' przed zmianą, potem po zmianie. Porównam oba.",
                   f"{P} The surest check is a recording: 'start recording' before the change and again after it. I will compare them.")]

    # ── "A co jeśli dalej będzie zacinać?" ───────────────────────────────────
    def _resp_still_lagging(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        game = _ref("game")
        lines = [_t(lang, f"{P} Jeśli dalej zacina" + (f" w {game}" if game else "") + ", kolejne kroki od najprostszych:",
                    f"{P} If it still stutters" + (f" in {game}" if game else "") + ", next steps from the simplest:")]
        try:
            lines += self._fps_checklist(lang)
        except Exception:
            pass
        lines += [
            _t(lang, "  · W grze: limit FPS na poziomie odświeżania monitora i tryb „pełny ekran”.",
               "  · In the game: an FPS cap at the monitor's refresh rate and fullscreen mode."),
            _t(lang, "  · Sterownik grafiki: czysta instalacja najnowszego (NVIDIA App / AMD Software).",
               "  · Graphics driver: a clean install of the latest (NVIDIA App / AMD Software)."),
            _t(lang, "  · Nagraj grę przed i po zmianie: 'zacznij nagrywanie', a porównam, co pomogło.",
               "  · Record the game before and after a change: 'start recording', and I will compare what helped."),
            "§OFFER record",
        ]
        try:
            from hck_gpt.guide_links import offer_lines
            extra = offer_lines("fps_degradation", lang)
            if extra:
                lines += extra
        except Exception:
            pass
        return lines

    # ── game follow-up: "czy komputer sobie z tym radzi?" ────────────────────
    def _resp_game_followup(self, r: ParseResult, lang: str = "pl") -> List[str]:
        game = _ref("game")
        if game:
            from hck_gpt.intents.parser import ParseResult as _PR
            return self._resp_game_can_run(_PR("game_can_run", 0.9, raw_text=f"czy pojdzie {game}"), lang)
        return self._resp_part_verdict(_PR_like(r, "czy karta graficzna daje rade"), lang)

    # ── "Chcę pograć w CS2, ale mam lagi" ────────────────────────────────────
    def _game_in(self, raw: str) -> str:
        try:
            from hck_gpt.memory.session_memory import session_memory
            folded = session_memory._fold_text(raw)
            for g in session_memory._KNOWN_GAMES:
                if session_memory._fold_text(g) in folded:
                    session_memory.note_reference("game", g, "game_lag")
                    return g
        except Exception:
            pass
        return ""

    def _resp_game_lag(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """A game named together with lag: whether the PC meets its needs,
        what is off on this PC, and how to measure a change. It got the
        part-compatibility checker before (third long test)."""
        game = self._game_in(r.raw_text or "") or _ref("game")
        P = self.PREFIX
        shown = (game.upper() if len(game) <= 4 else game.title()) if game else ""
        lines = [_t(lang, f"{P} Lagi w {shown}: sprawdzam sprzęt i to, co zwykle je powoduje." if game else
                    f"{P} Lagi w grze: sprawdzam to, co zwykle je powoduje.",
                    f"{P} Lag in {shown}: checking the hardware and the usual causes." if game else
                    f"{P} Lag in a game: checking the usual causes.")]
        if game:
            try:
                from hck_gpt.intents.parser import ParseResult as _PR
                req = self._resp_game_can_run(_PR("game_can_run", 0.9, raw_text=game), lang)
                verdict = [l for l in req if l.strip()[:1] in ("✓", "✗", "!")]
                lines += verdict[:4]
            except Exception:
                pass
        lines.append(_t(lang, "  Na tym komputerze:", "  On this PC:"))
        try:
            lines += self._fps_checklist(lang)
        except Exception:
            pass
        lines.append(_t(lang, "  Przed grą zamknij to, co zbędne: 'co zamknąć przed grą'. Zmianę zmierzysz nagraniem: 'zacznij nagrywanie'.",
                        "  Before playing close what is not needed: 'what to close before gaming'. Measure the change with a recording: 'start recording'."))
        lines.append("§OFFER record")
        return lines

    # ── what changed lately ──────────────────────────────────────────────────
    def _resp_recent_changes(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pc_insight import usage_norms, process_anomalies
        lines = [_t(lang, f"{self.PREFIX} Co się ostatnio zmieniło:", f"{self.PREFIX} What changed lately:")]
        moved = False
        for comp, n in usage_norms().items():
            rv = n.get("recent") or {}
            if rv.get("notable"):
                moved = True
                lines.append(_t(lang, f"  ⚠ {comp.upper()}: ostatnie 2 dni {rv['recent_avg']:.0f}%, wcześniej {rv['usual_avg']:.0f}%.",
                                f"  ⚠ {comp.upper()}: last 2 days {rv['recent_avg']:.0f}%, before {rv['usual_avg']:.0f}%."))
        for a in process_anomalies()[:3]:
            moved = True
            lines.append("  ⚠ " + self._finding_text({"code": "process_up", "data": a}, lang))
        if not moved:
            lines.append(_t(lang, "  Obciążenie trzyma się normy, żaden program nie bierze więcej niż zwykle.",
                            "  Load stays within normal, no program uses more than usual."))
        try:
            pc = self._resp_pc_changes(r, lang)
            lines += [l for l in pc[1:3] if l.strip()]
        except Exception:
            pass
        return lines

    # ── observation note ─────────────────────────────────────────────────────
    def _resp_observe_howto(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Nagraj to. Notatka obserwacyjna zapisuje, co komputer robi, i porównuje z poprzednim nagraniem:",
               f"{self.PREFIX} Record it. The observation note records what the PC does and compares it with the previous recording:"),
            _t(lang, "  1. Przed zmianą: 'zacznij nagrywanie', zagraj albo popracuj kilka minut, 'zakończ nagrywanie'.",
               "  1. Before the change: 'start recording', play or work a few minutes, 'stop recording'."),
            _t(lang, "  2. Zrób zmianę (optymalizacja, zamknięcie programów, XMP).", "  2. Make the change (optimization, closing programs, XMP)."),
            _t(lang, "  3. Po zmianie to samo jeszcze raz: ta sama gra, podobny czas.", "  3. After it, the same again: the same game, a similar time."),
            _t(lang, "  Notatkę z porównaniem i werdyktem zapiszę na pulpicie.", "  I save the note with the comparison and a verdict on the Desktop."),
            "§OFFER record",
        ]

    def _resp_observe_start(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core import observation
        st = observation.status()
        if st["recording"]:
            return [_t(lang, f"{self.PREFIX} Już nagrywam ({st['seconds'] // 60} min {st['seconds'] % 60} s). Zakończ: 'zakończ nagrywanie'.",
                       f"{self.PREFIX} Already recording ({st['seconds'] // 60} min {st['seconds'] % 60} s). Stop: 'stop recording'.")]
        observation.start(label=(r.raw_text or "")[:80])
        prev = observation.last_saved()
        return [_t(lang, f"{self.PREFIX} ⏺ Nagrywam co sekundę: CPU, RAM, GPU, temperaturę GPU, zegar procesora i najcięższy proces.",
                   f"{self.PREFIX} ⏺ Recording every second: CPU, RAM, GPU, GPU temperature, CPU clock and the busiest process."),
                _t(lang, "  Rób to, co chcesz zmierzyć (gra, praca), potem 'zakończ nagrywanie'. Najdłużej 2 godziny.",
                   "  Do what you want to measure (a game, work), then 'stop recording'. Two hours at most."),
                _t(lang, "  Porównam z poprzednim nagraniem." if prev else "  To pierwsze nagranie: następne porównam z nim.",
                   "  I will compare it with the previous recording." if prev else "  This is the first recording: I will compare the next one with it.")]

    def _resp_observe_stop(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core import observation
        s = observation.stop()
        if s is None:
            return [_t(lang, f"{self.PREFIX} Nic nie nagrywam. Start: 'zacznij nagrywanie'.",
                       f"{self.PREFIX} Nothing is recording. Start: 'start recording'.")]
        if s.get("too_short"):
            return [_t(lang, f"{self.PREFIX} Nagranie było za krótkie ({s['seconds']} s), nie zapisałem go.",
                       f"{self.PREFIX} The recording was too short ({s['seconds']} s), not saved.")]
        text = observation.note_text(s, None, lang).splitlines()
        lines = [_t(lang, f"{self.PREFIX} ⏹ Nagranie zakończone.", f"{self.PREFIX} ⏹ Recording stopped.")]
        lines += ["  " + l for l in text[2:] if l.strip()]
        c = s.get("compare")
        if c:
            lines.append("")
            lines.append(_t(lang, "  Wobec poprzedniego nagrania:", "  Against the previous recording:"))
            for m, nm in (("cpu", "CPU"), ("ram", "RAM"), ("gpu", "GPU"), ("gpu_temp", _t(lang, "Temp. GPU", "GPU temp"))):
                if m in c:
                    unit = "°C" if m == "gpu_temp" else " pp"
                    lines.append(f"    {nm}: {c[m]['before']:.0f} → {c[m]['after']:.0f} ({c[m]['delta']:+.0f}{unit})")
            v = c["verdict"]
            lines.append(("§OK " if v == "better" else "§WARN " if v == "worse" else "  ") + _t(lang,
                {"better": "Jest lepiej.", "worse": "Jest gorzej.", "same": "Bez wyraźnej różnicy."}[v],
                {"better": "It is better.", "worse": "It is worse.", "same": "No clear difference."}[v]))
        if s.get("note_path"):
            lines.append(_t(lang, f"  Notatka zapisana: {s['note_path']}", f"  Note saved: {s['note_path']}"))
        return lines


def _PR_like(r, text):
    from hck_gpt.intents.parser import ParseResult as _PR
    return _PR("part_verdict", 0.9, raw_text=text)
