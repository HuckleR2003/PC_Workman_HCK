"""hck_gpt.responses.r_insight - answers that draw conclusions (2026-11-17).

Built from the 63-question library of the third long test (2026-11-17):
51 of 193 phrasings ended in "I did not understand" and about 40 got an
answer to another question. Each handler here reads core.pc_insight (the
shared conclusions) and says three things: what was checked, the verdict,
and what to do. Nothing is guessed; what Windows does not show is said.

Groups:
  state of the PC     pc_checkup, stability_check, usage_vs_normal,
                      process_anomaly, background_load, slowdown_cause
  parts and limits    bottleneck, part_verdict, cpu_boost, gpu_utilization,
                      vram_check, disk_speed_check, ssd_health, gaming_temps,
                      board_cpu_upgrade, ram_enough, pc_age, new_pc_advice
  trust               files_access, data_stored, what_remembered,
                      virus_capability, defender_enough, svchost_safety,
                      signed_trust, impostor_check
  personality         pc_tired, idle_activity, watching, likes_job,
                      predict_slowdown
"""
from __future__ import annotations

import time

from hck_gpt.responses.common import List, ParseResult, _t


def _pl_count(n: int, one: str, few: str, many: str) -> str:
    """Polish plural: 1 restart, 2-4 restarty, 5+ restartów."""
    if n == 1:
        return f"{n} {one}"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f"{n} {few}"
    return f"{n} {many}"


def _sevmark(sev: int) -> str:
    return {2: "§WARN ", 1: "  ⚠ ", 0: "  ✓ "}.get(sev, "  · ")


class InsightResponses:

    # ── how a finding reads ──────────────────────────────────────────────────
    def _finding_text(self, f: dict, lang: str) -> str:
        c, d = f["code"], f.get("data") or {}
        pl = lang != "en"
        if c == "ram_small":
            return _t(lang, f"RAM {d['gb']:.0f} GB jest zwykle zajęty w {d['avg']:.0f}%: mało zapasu, to najczęstsza przyczyna spowolnień tutaj.",
                      f"RAM {d['gb']:.0f} GB is usually {d['avg']:.0f}% full: the most common cause of slowdowns here.")
        if c == "ram_ok":
            return _t(lang, f"RAM {d['gb']:.0f} GB, średnio {d['avg']:.0f}%: wystarcza.",
                      f"RAM {d['gb']:.0f} GB, {d['avg']:.0f}% on average: enough.")
        if c == "xmp_off":
            return _t(lang, f"RAM chodzi na {d['mhz']} MHz, czyli bez XMP: tracisz trochę wydajności ('xmp').",
                      f"RAM runs at {d['mhz']} MHz, without XMP: some performance is left behind ('xmp').")
        if c == "c_full":
            return _t(lang, f"Na dysku C: zostało tylko {d['free_gb']:.0f} GB: Windows zwalnia przy mało miejsca.",
                      f"Only {d['free_gb']:.0f} GB left on C:: Windows slows down when space runs out.")
        if c == "no_pagefile":
            return _t(lang, "Pamięć wirtualna jest wyłączona: przy pełnym RAM programy mogą się zamykać.",
                      "Virtual memory is off: apps can close when RAM fills up.")
        if c == "gpu_driver":
            m = d["months"]
            return (_t(lang, f"Sterownik grafiki ma {m} mies.: warto zaktualizować.",
                       f"The graphics driver is {m} months old: worth updating.") if m >= 12 else
                    _t(lang, f"Sterownik grafiki ma {m} mies.: w porządku.",
                       f"The graphics driver is {m} months old: fine."))
        if c == "gpu_hot":
            return _t(lang, f"GPU w grach dochodzi do {d['gpu_temp_max']:.0f}°C: sprawdź przepływ powietrza.",
                      f"The GPU reaches {d['gpu_temp_max']:.0f}°C in games: check the airflow.")
        if c == "cpu_limited":
            return _t(lang, f"Procesor jest teraz przyhamowany do {d['limit_pct']:.0f}% (temperatura albo limit mocy).",
                      f"The processor is held to {d['limit_pct']:.0f}% right now (heat or power limit).")
        if c == "hw_errors":
            return _t(lang, f"Dziennik Windows: {d['whea']} błędów sprzętu (WHEA) i {d['bsod']} niebieskich ekranów w 30 dni.",
                      f"Windows log: {d['whea']} hardware errors (WHEA) and {d['bsod']} blue screens in 30 days.")
        if c == "disk_errors":
            return _t(lang, f"Dziennik Windows: {d['disk'] + d['ntfs']} błędów dysku w 30 dni: zrób kopię ważnych plików.",
                      f"Windows log: {d['disk'] + d['ntfs']} disk errors in 30 days: back up what matters.")
        if c == "restarts":
            return _t(lang, f"{_pl_count(d['restart'], 'restart', 'restarty', 'restartów')} bez czystego zamknięcia w 30 dni (zasilanie, zawieszenia).",
                      f"{d['restart']} restarts without a clean shutdown in 30 days (power, hangs).")
        if c == "no_errors":
            return _t(lang, "Dziennik Windows: bez błędów sprzętu i nagłych restartów w 30 dni.",
                      "Windows log: no hardware errors or sudden restarts in 30 days.")
        if c == "disk_health":
            return _t(lang, f"Dysk {d['name']} zgłasza stan: {d['health']}. Zrób kopię zapasową.",
                      f"Drive {d['name']} reports: {d['health']}. Back up now.")
        if c == "system_hdd":
            return _t(lang, "Windows jest na dysku talerzowym (HDD): SSD da największą różnicę w szybkości.",
                      "Windows is on a hard disk (HDD): an SSD makes the biggest speed difference.")
        if c == "process_up":
            unit = "%" if d["comp"] == "cpu" else " MB"
            return _t(lang, f"{d['name']} bierze ostatnio {d['now']:.0f}{unit} {d['comp'].upper()}, zwykle {d['usual']:.0f}{unit}.",
                      f"{d['name']} lately uses {d['now']:.0f}{unit} {d['comp'].upper()}, usually {d['usual']:.0f}{unit}.")
        if c == "usage_up":
            return _t(lang, f"{d['comp'].upper()} ostatnie 2 dni średnio {d['recent_avg']:.0f}%, wcześniej {d['usual_avg']:.0f}%.",
                      f"{d['comp'].upper()} averaged {d['recent_avg']:.0f}% over 2 days, {d['usual_avg']:.0f}% before.")
        if c == "startup_heavy":
            return _t(lang, f"{_pl_count(d['n'], 'ciężki program', 'ciężkie programy', 'ciężkich programów')} w autostarcie wydłuża uruchamianie.",
                      f"{d['n']} heavy startup programs slow down the boot.")
        return c if pl else c

    # ── state of the PC ──────────────────────────────────────────────────────
    def _resp_pc_checkup(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'co tam u komputera', 'czy muszę coś naprawić', 'czy mam się czym martwić'."""
        from core.pc_insight import findings
        fs = findings()
        bad = [f for f in fs if f["sev"] == 2]
        warn = [f for f in fs if f["sev"] == 1]
        ok = [f for f in fs if f["sev"] == 0]
        try:
            import psutil
            cpu, ram = psutil.cpu_percent(interval=0.3), psutil.virtual_memory().percent
        except Exception:
            cpu = ram = 0
        if bad:
            head = _t(lang, f"{self.PREFIX} Jest coś do naprawienia ({len(bad)}), reszta poniżej.",
                      f"{self.PREFIX} There is something to fix ({len(bad)}), the rest below.")
        elif warn:
            head = _t(lang, f"{self.PREFIX} Nic pilnego. Działa, ale {len(warn)} rzeczy warto poprawić:",
                      f"{self.PREFIX} Nothing urgent. It works, but {len(warn)} things are worth improving:")
        else:
            head = _t(lang, f"{self.PREFIX} Nie ma się czym martwić: sprawdziłem i wszystko jest w porządku.",
                      f"{self.PREFIX} Nothing to worry about: I checked and everything is fine.")
        lines = [head, _t(lang, f"  Teraz: CPU {cpu:.0f}% · RAM {ram:.0f}%.", f"  Now: CPU {cpu:.0f}% · RAM {ram:.0f}%."), ""]
        for f in bad + warn:
            t = self._finding_text(f, lang)
            lines.append(("§WARN " + t) if f["sev"] == 2 else ("  ⚠ " + t))
        for f in ok[:3]:
            lines.append("  ✓ " + self._finding_text(f, lang))
        if bad or warn:
            lines.append("§OFFER optimize")
        return lines

    def _resp_stability_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'czy komputer jest stabilny', 'czy mam błędy sprzętu'."""
        from core.pc_insight import hardware_errors, disks
        e = hardware_errors()
        ds = disks()
        if not e.get("ok"):
            return [_t(lang, f"{self.PREFIX} Nie mogę teraz odczytać dziennika Windows.",
                       f"{self.PREFIX} I cannot read the Windows log right now.")]
        serious = e["whea"] + e["bsod"] + e["disk"] + e["ntfs"]
        if serious == 0 and e["restart"] == 0:
            head = _t(lang, f"{self.PREFIX} Stabilny. W 30 dniach: zero błędów sprzętu, niebieskich ekranów i nagłych restartów.",
                      f"{self.PREFIX} Stable. In 30 days: no hardware errors, blue screens or sudden restarts.")
        elif serious == 0:
            head = _t(lang, f"{self.PREFIX} Sprzęt nie zgłasza błędów, ale były {e['restart']} restarty bez czystego zamknięcia (30 dni).",
                      f"{self.PREFIX} The hardware reports no errors, but there were {e['restart']} restarts without a clean shutdown (30 days).")
        else:
            head = _t(lang, f"{self.PREFIX} Są sygnały niestabilności w 30 dniach:",
                      f"{self.PREFIX} There are signs of instability in 30 days:")
        lines = [head]
        lines.append(_t(lang,
            f"  Błędy sprzętu (WHEA): {e['whea']} · niebieskie ekrany: {e['bsod']} · błędy dysku: {e['disk'] + e['ntfs']} · nagłe restarty: {e['restart']}",
            f"  Hardware errors (WHEA): {e['whea']} · blue screens: {e['bsod']} · disk errors: {e['disk'] + e['ntfs']} · sudden restarts: {e['restart']}"))
        if e.get("last"):
            lines.append(_t(lang, f"  Ostatnie zdarzenie: {e['last']:%d.%m %H:%M}.", f"  Last event: {e['last']:%Y-%m-%d %H:%M}."))
        for d in ds:
            lines.append(f"  {'✓' if d['health'].lower() == 'healthy' else '⚠'} {d['name']}: {d['health'] or '?'}")
        if e["restart"] and not e["bsod"]:
            lines.append(_t(lang, "  Restart bez niebieskiego ekranu to zwykle zasilanie albo zawieszenie przy grze.",
                            "  A restart without a blue screen is usually power or a hang during a game."))
        if e["whea"] or e["bsod"]:
            lines.append(_t(lang, "  Przy błędach WHEA najpierw wyłącz podkręcanie i XMP, potem test pamięci.",
                            "  With WHEA errors, first turn off overclocking and XMP, then test the memory."))
        return lines

    def _resp_usage_vs_normal(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'czy średnie CPU jest normalne', 'czy działa gorzej niż zwykle',
        'co jest normalnym zużyciem RAM', 'czy wydajność pogarsza się z czasem'."""
        from core.pc_insight import usage_norms
        raw = (r.raw_text or "").lower()
        norms = usage_norms()
        if not norms:
            return [_t(lang, f"{self.PREFIX} Normę poznam po kilku godzinach pracy. Zbieram dane co minutę.",
                       f"{self.PREFIX} I learn the normal level after a few hours. I record every minute.")]
        focus = [c for c in ("ram", "cpu", "gpu") if c in raw or {"ram": "pamię", "cpu": "procesor", "gpu": "grafik"}[c] in raw]
        comps = focus or ["cpu", "ram", "gpu"]
        try:
            import psutil
            live = {"cpu": psutil.cpu_percent(interval=0.3), "ram": psutil.virtual_memory().percent}
        except Exception:
            live = {}
        lines = [_t(lang, f"{self.PREFIX} Twoja norma (ostatnie 14 dni) i jak jest teraz:",
                    f"{self.PREFIX} Your normal (last 14 days) and how it is now:")]
        worse = False
        for c in comps:
            n = norms.get(c)
            if not n:
                continue
            now = live.get(c)
            now_txt = (_t(lang, f", teraz {now:.0f}%", f", now {now:.0f}%") if now is not None else "")
            lines.append(_t(lang,
                f"  {c.upper()}: zwykle {n['avg']:.0f}%, przez 95% czasu do {n['p95']:.0f}%{now_txt}.",
                f"  {c.upper()}: usually {n['avg']:.0f}%, 95% of the time under {n['p95']:.0f}%{now_txt}."))
            rv = n.get("recent") or {}
            if rv.get("notable"):
                worse = True
                lines.append(_t(lang,
                    f"    ⚠ Ostatnie 2 dni wyżej: {rv['recent_avg']:.0f}% wobec {rv['usual_avg']:.0f}%.",
                    f"    ⚠ The last 2 days are higher: {rv['recent_avg']:.0f}% against {rv['usual_avg']:.0f}%."))
            elif now is not None and now > n["p95"] + 5:
                lines.append(_t(lang, "    Teraz ponad normą, ale to chwila, nie trend.",
                                "    Above normal right now, but a moment, not a trend."))
        hours = max(n["hours"] for n in norms.values())
        if not worse:
            lines.append(_t(lang,
                "  Nic nie wskazuje, że jest gorzej niż zwykle." if hours >= 24 else
                f"  Na razie {hours:.0f} h historii; trend porównam pewniej po kilku dniach.",
                "  Nothing suggests it is worse than usual." if hours >= 24 else
                f"  {hours:.0f} h of history so far; a trend gets reliable after a few days."))
        lines.append("  [-> Activity Memory]")
        return lines

    def _resp_process_anomaly(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pc_insight import process_anomalies
        an = process_anomalies()
        if not an:
            return [_t(lang, f"{self.PREFIX} Żaden program nie bierze wyraźnie więcej niż zwykle (ostatnia doba wobec 6 dni wcześniej).",
                       f"{self.PREFIX} No program uses clearly more than usual (the last day against the 6 days before)."),
                    _t(lang, "  Co bierze najwięcej teraz: 'co zjada procesor'.", "  What uses the most now: 'what uses my cpu'.")]
        lines = [_t(lang, f"{self.PREFIX} Te programy biorą ostatnio więcej niż zwykle:",
                    f"{self.PREFIX} These programs use more than usual lately:")]
        for a in an:
            lines.append("  ⚠ " + self._finding_text({"code": "process_up", "data": a}, lang))
        try:
            from hck_gpt.memory.session_memory import session_memory
            session_memory.note_reference("process", an[0]["name"], "process_anomaly")
        except Exception:
            pass
        return lines

    def _resp_background_load(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'czy coś niepotrzebnie działa w tle', 'czy mam za dużo programów'."""
        try:
            import psutil
            n_proc = len(psutil.pids())
            ram = psutil.virtual_memory().percent
        except Exception:
            n_proc, ram = 0, 0
        top, _ = self._ram_by_app(25)
        apps = [(n, mb) for n, mb in top if n.lower() not in self._KEEP and mb >= 150]
        try:
            from hck_gpt.responses.flows import _running_unneeded, _startup_flagged
            svc = _running_unneeded() or []
            flagged, total = _startup_flagged()
        except Exception:
            svc, flagged, total = [], [], 0
        lines = [_t(lang, f"{self.PREFIX} W tle: {n_proc} procesów, RAM {ram:.0f}%.",
                    f"{self.PREFIX} In the background: {n_proc} processes, RAM {ram:.0f}%.")]
        lines.append(_t(lang, "  Kilkaset procesów to normalne w Windows: liczy się, ile biorą, nie ile ich jest.",
                        "  A few hundred processes is normal on Windows: what counts is what they take, not how many."))
        if apps:
            lines.append(_t(lang, "  Programy, które trzymają najwięcej: ", "  Programs holding the most: ")
                         + ", ".join(f"{n} {self._mb_text(mb)}" for n, mb in apps[:4]))
            try:
                from hck_gpt.memory.session_memory import session_memory
                session_memory.note_reference("process", apps[0][0] + ".exe", "background_load")
            except Exception:
                pass
        if svc:
            lines.append(_t(lang, f"  ⚠ Zbędne usługi, które działają: {', '.join(svc)}.",
                            f"  ⚠ Unneeded services that are running: {', '.join(svc)}."))
        else:
            lines.append(_t(lang, "  ✓ Żadna z typowo zbędnych usług nie działa.", "  ✓ None of the usually unneeded services runs."))
        if flagged:
            lines.append(_t(lang, f"  ⚠ {len(flagged)} z {total} programów startuje z Windows bez potrzeby.",
                            f"  ⚠ {len(flagged)} of {total} programs start with Windows for no need."))
        lines.append(_t(lang, "  Co bezpiecznie zamknąć: 'co mogę zamknąć'.", "  What is safe to close: 'what can I close'."))
        lines.append("§OFFER optimize")
        return lines

    # ── parts and limits ─────────────────────────────────────────────────────
    _PART_PL = {"ram": "pamięć RAM", "gpu": "karta graficzna", "cpu": "procesor", "disk": "dysk"}

    def _resp_bottleneck(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'który podzespół jest najsłabszy', 'co wymienić najpierw',
        'czy mam wąskie gardło', 'co ogranicza wydajność'."""
        from core.pc_insight import weakest_part, gaming_profile, cpu_clock
        w = weakest_part()
        part, why, d = w["part"], w["why"], w["data"]
        name = self._PART_PL.get(part, part) if lang != "en" else {"ram": "RAM", "gpu": "graphics card", "cpu": "processor", "disk": "drive"}.get(part, part)
        lines = []
        if why == "small_and_full":
            lines.append(_t(lang, f"{self.PREFIX} Najsłabsze ogniwo: {name}. Masz {d['gb']:.0f} GB, a zwykle zajęte jest {d['avg']:.0f}% (szczyty {d['p95']:.0f}%).",
                            f"{self.PREFIX} The weakest link: {name}. You have {d['gb']:.0f} GB and {d['avg']:.0f}% is usually in use (peaks {d['p95']:.0f}%)."))
            lines.append(_t(lang, "  Gdy RAM się kończy, Windows odkłada dane na dysk i wszystko zwalnia. Dołożenie do 16 GB da największą różnicę za najmniej pieniędzy.",
                            "  When RAM runs out, Windows moves data to disk and everything slows down. Going to 16 GB makes the biggest difference for the least money."))
        elif why == "hdd":
            lines.append(_t(lang, f"{self.PREFIX} Najsłabsze ogniwo: Windows na dysku talerzowym (HDD). SSD skróci start i ładowanie kilka razy.",
                            f"{self.PREFIX} The weakest link: Windows on a hard disk (HDD). An SSD cuts boot and loading several times."))
        elif why == "cpu_in_games":
            lines.append(_t(lang, f"{self.PREFIX} W grach procesor dochodzi do granic (średnio {d['cpu_avg']:.0f}%), a grafika ma zapas ({d['gpu_avg']:.0f}%): procesor ogranicza.",
                            f"{self.PREFIX} In games the processor hits its limit (average {d['cpu_avg']:.0f}%) while the GPU has room ({d['gpu_avg']:.0f}%): the CPU limits."))
        elif why == "gpu_in_games":
            lines.append(_t(lang, f"{self.PREFIX} W grach pracuje na maksa karta graficzna (średnio {d['gpu_avg']:.0f}%). To normalne: przy grze to ona powinna być granicą.",
                            f"{self.PREFIX} In games the graphics card runs at the top (average {d['gpu_avg']:.0f}%). That is normal: in a game it should be the limit."))
            lines.append(_t(lang, "  Więcej FPS da mocniejsza karta albo niższe ustawienia grafiki.",
                            "  More FPS needs a stronger card or lower graphics settings."))
        elif why == "cpu_busy":
            lines.append(_t(lang, f"{self.PREFIX} Procesor pracuje dużo przez cały dzień (średnio {d['avg']:.0f}%): on jest pierwszy do wymiany.",
                            f"{self.PREFIX} The processor works hard all day (average {d['avg']:.0f}%): it goes first."))
        elif why == "ram_tight":
            lines.append(_t(lang, f"{self.PREFIX} Najbliżej granicy jest RAM: {d['gb']:.0f} GB, średnio {d['avg']:.0f}%. Reszta ma zapas.",
                            f"{self.PREFIX} RAM is closest to its limit: {d['gb']:.0f} GB, {d['avg']:.0f}% on average. The rest has room."))
        elif why == "no_data":
            lines.append(_t(lang, f"{self.PREFIX} Za mało historii, żeby wskazać wąskie gardło: potrzebuję co najmniej 2 godzin pracy komputera. Zbieram dane co minutę.",
                            f"{self.PREFIX} Not enough history to name a bottleneck: I need at least 2 hours of use. I record every minute."))
        else:
            lines.append(_t(lang, f"{self.PREFIX} Wyraźnego wąskiego gardła nie widzę: żaden podzespół nie siedzi stale na granicy.",
                            f"{self.PREFIX} I see no clear bottleneck: no part sits at its limit all the time."))
        gp = gaming_profile()
        if gp.get("minutes", 0) >= 15 and why not in ("cpu_in_games", "gpu_in_games"):
            lines.append(_t(lang,
                f"  W grach ({gp['minutes']} min w historii): GPU średnio {gp['gpu_avg']:.0f}%, CPU {gp['cpu_avg']:.0f}%.",
                f"  In games ({gp['minutes']} min recorded): GPU average {gp['gpu_avg']:.0f}%, CPU {gp['cpu_avg']:.0f}%."))
        clk = cpu_clock(0.4)
        if clk.get("limit_pct") is not None and clk["limit_pct"] < 95:
            lines.append(_t(lang, f"  ⚠ Procesor jest teraz przyhamowany do {clk['limit_pct']:.0f}% (temperatura albo limit mocy).",
                            f"  ⚠ The processor is held to {clk['limit_pct']:.0f}% right now (heat or power limit)."))
        lines.append(_t(lang, "  Co pasuje do Twojej płyty: [-> Upgrade Readiness]", "  What fits your board: [-> Upgrade Readiness]"))
        return lines

    def _resp_ram_enough(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pc_insight import _hist
        try:
            import psutil
            gb = psutil.virtual_memory().total / 1024 ** 3
        except Exception:
            gb = 0
        st = _hist("ram", 7)
        if not st.get("has_data"):
            return [_t(lang, f"{self.PREFIX} Masz {gb:.0f} GB RAM. Ocenię, czy wystarcza, po kilku godzinach historii.",
                       f"{self.PREFIX} You have {gb:.0f} GB of RAM. I can judge it after a few hours of history.")]
        if st["avg"] >= 80 or st["p95"] >= 92:
            verdict = _t(lang, "Nie wystarcza: pamięć jest stale prawie pełna, Windows dokłada pracy dyskowi.",
                         "Not enough: memory is nearly full most of the time, Windows leans on the disk.")
        elif st["avg"] >= 65:
            verdict = _t(lang, "Na styk: wystarcza, ale bez zapasu na przeglądarkę i grę naraz.",
                         "Just enough: it works, with no room for a browser and a game together.")
        else:
            verdict = _t(lang, "Wystarcza z zapasem.", "Enough, with room to spare.")
        lines = [_t(lang, f"{self.PREFIX} {gb:.0f} GB RAM, zwykle zajęte {st['avg']:.0f}%, szczyty {st['p95']:.0f}%. {verdict}",
                    f"{self.PREFIX} {gb:.0f} GB of RAM, usually {st['avg']:.0f}% used, peaks {st['p95']:.0f}%. {verdict}")]
        if gb < 16 and st["avg"] >= 65:
            lines.append(_t(lang, "  Dziś do grania i przeglądarki rozsądne minimum to 16 GB.  Wolne gniazda: 'czy mogę dołożyć RAM'.",
                            "  For gaming and a browser today, 16 GB is a sensible minimum.  Free slots: 'can I add RAM'."))
        return lines

    def _resp_part_verdict(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'czy mój procesor jest jeszcze dobry', 'czy karta graficzna daje radę'."""
        from core.pc_insight import cpu_profile, pc_age, gaming_profile, _hist
        raw = (r.raw_text or "").lower()
        gpu_q = any(k in raw for k in ("graficzn", "grafika", "gpu", "karta", "karte", "kartę"))
        year = time.localtime().tm_year
        if gpu_q:
            age = pc_age()
            name, y = age["gpu_name"] or "GPU", age["parts"]["gpu"]
            gp = gaming_profile()
            lines = [_t(lang, f"{self.PREFIX} {name}" + (f" (z {y} r.)" if y else "") + ":",
                        f"{self.PREFIX} {name}" + (f" (from {y})" if y else "") + ":")]
            if gp.get("minutes", 0) >= 15:
                lines.append(_t(lang, f"  W grach średnio {gp['gpu_avg']:.0f}%, szczyty {gp['gpu_p95']:.0f}%, do {gp.get('gpu_temp_max') or 0:.0f}°C.",
                                f"  In games {gp['gpu_avg']:.0f}% on average, peaks {gp['gpu_p95']:.0f}%, up to {gp.get('gpu_temp_max') or 0:.0f}°C."))
                lines.append(_t(lang, "  Daje radę w tym, w co grasz: ma jeszcze zapas." if gp["gpu_p95"] < 95 else
                                "  W tym, w co grasz, pracuje na maksa: przy nowszych grach trzeba obniżać ustawienia.",
                                "  It handles what you play: there is still room." if gp["gpu_p95"] < 95 else
                                "  In what you play it runs at the top: newer games will need lower settings."))
            else:
                lines.append(_t(lang, "  Nie mam jeszcze nagranego grania, więc oceniam po klasie karty.",
                                "  No gaming recorded yet, so I judge by the card's class."))
            lines.append(_t(lang, "  Konkretna gra: 'czy pociągnę Cyberpunka'.", "  A specific game: 'can I run Cyberpunk'."))
            return lines
        prof = cpu_profile()
        st = _hist("cpu", 7)
        lines = [_t(lang, f"{self.PREFIX} {prof['name'] or 'CPU'}" + (f" (z {prof['year']} r.)" if prof["year"] else "") + ":",
                    f"{self.PREFIX} {prof['name'] or 'CPU'}" + (f" (from {prof['year']})" if prof["year"] else "") + ":")]
        if prof["cores"]:
            lines.append(_t(lang, f"  {prof['cores']} rdzeni, do {prof['boost'] / 1000:.1f} GHz.", f"  {prof['cores']} cores, up to {prof['boost'] / 1000:.1f} GHz."))
        if st.get("has_data"):
            lines.append(_t(lang, f"  Na co dzień średnio {st['avg']:.0f}%, czas powyżej 80%: {st['high_load_minutes']} min w 7 dni.",
                            f"  Day to day {st['avg']:.0f}% on average, time above 80%: {st['high_load_minutes']} min in 7 days."))
            good = st["avg"] < 50
            lines.append(_t(lang, "  Jest dobry: ma zapas na to, co robisz." if good else "  Pracuje ciężko: przy wymianie byłby pierwszy w kolejce.",
                            "  It is good: it has room for what you do." if good else "  It works hard: it would be first in line for an upgrade."))
        if prof["year"] and year - prof["year"] <= 5:
            lines.append(_t(lang, f"  Ma {year - prof['year']} lata: wciąż obsługuje nowe gry i Windows 11.",
                            f"  It is {year - prof['year']} years old: still fine for new games and Windows 11."))
        return lines

    def _resp_cpu_boost(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'czy procesor osiąga max taktowanie', 'czy CPU jest na limicie mocy',
        'czy osiąga temperaturę throttlingu', 'czy zwalnia pod obciążeniem'."""
        from core.pc_insight import cpu_clock, cpu_profile
        clk = cpu_clock(0.8)
        prof = cpu_profile()
        if not clk.get("actual"):
            return [_t(lang, f"{self.PREFIX} Windows nie udostępnia teraz liczników procesora.",
                       f"{self.PREFIX} Windows does not expose the processor counters right now."),
                    "  [-> Overclock]"]
        act, util, lim = clk["actual"], clk.get("util_pct") or 0, clk.get("limit_pct")
        boost = prof["boost"] or 0
        lines = [_t(lang, f"{self.PREFIX} Procesor teraz: {act:,.0f} MHz przy obciążeniu {util:.0f}%".replace(",", " ")
                    + (f" (bazowe {clk['base']:.0f}, boost do {boost} MHz)." if boost else "."),
                    f"{self.PREFIX} Processor now: {act:,.0f} MHz at {util:.0f}% load"
                    + (f" (base {clk['base']:.0f}, boost up to {boost} MHz)." if boost else "."))]
        if lim is not None and lim < 95:
            lines.append(_t(lang, f"§WARN Coś go hamuje: wydajność ograniczona do {lim:.0f}%. Najczęściej temperatura albo limit mocy (plan zasilania, BIOS).",
                            f"§WARN Something holds it back: performance limited to {lim:.0f}%. Usually heat or a power limit (power plan, BIOS)."))
        else:
            lines.append(_t(lang, "§OK Nic go nie hamuje: limit wydajności 100%, czyli bez throttlingu i bez limitu mocy.",
                            "§OK Nothing holds it back: performance limit 100%, so no throttling and no power limit."))
        if boost and act >= boost * 0.9:
            lines.append(_t(lang, "  Dochodzi do pełnego boosta.", "  It reaches full boost."))
        elif boost and util < 30:
            lines.append(_t(lang, "  Teraz ma mało pracy, więc zegar jest niższy: to normalne. Pełny boost widać pod obciążeniem.",
                            "  It has little to do now, so the clock is lower: normal. Full boost shows under load."))
        lines.append(_t(lang, "  Temperatury CPU Windows nie podaje bez dodatkowego programu; limit wydajności powyżej i tak pokazuje, czy jest za gorąco.",
                        "  Windows gives no CPU temperature without an extra tool; the performance limit above still shows whether it runs too hot."))
        lines.append("  [-> Overclock]")
        return lines

    def _resp_gpu_utilization(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pc_insight import gaming_profile
        gp = gaming_profile()
        if not gp.get("minutes"):
            return [_t(lang, f"{self.PREFIX} Nie mam jeszcze nagranego grania (GPU powyżej 60%). Zagraj chwilę i zapytaj ponownie.",
                       f"{self.PREFIX} No gaming recorded yet (GPU above 60%). Play for a while and ask again.")]
        lines = [_t(lang, f"{self.PREFIX} W grach ({gp['minutes']} min w ostatnich 7 dniach): GPU średnio {gp['gpu_avg']:.0f}%, szczyty {gp['gpu_p95']:.0f}%; CPU średnio {gp['cpu_avg']:.0f}%.",
                    f"{self.PREFIX} In games ({gp['minutes']} min in the last 7 days): GPU {gp['gpu_avg']:.0f}% on average, peaks {gp['gpu_p95']:.0f}%; CPU {gp['cpu_avg']:.0f}% on average.")]
        if gp["limited_by"] == "gpu":
            lines.append(_t(lang, "§OK Tak, karta jest wykorzystana w pełni. Tak ma być w grach.",
                            "§OK Yes, the card is fully used. That is how it should be in games."))
        elif gp["limited_by"] == "cpu":
            lines.append(_t(lang, "§WARN Nie w pełni: procesor nie nadąża jej karmić (CPU blisko 100%).",
                            "§WARN Not fully: the processor cannot keep it fed (CPU near 100%)."))
        else:
            lines.append(_t(lang, "  Nie zawsze w pełni. Gdy ani CPU, ani GPU nie są na maksa, zwykle działa limit FPS albo V-Sync, albo gra obciąża jeden rdzeń procesora.",
                            "  Not always fully. When neither CPU nor GPU is maxed, a frame cap or V-Sync is usually on, or the game loads one CPU core."))
        return lines

    def _resp_vram_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pc_insight import vram_peak
        v = vram_peak()
        tot = v.get("total_gb")
        lines = [_t(lang, f"{self.PREFIX} VRAM karty: {tot:.0f} GB." if tot else f"{self.PREFIX} VRAM karty: nie znam pojemności.",
                    f"{self.PREFIX} Card VRAM: {tot:.0f} GB." if tot else f"{self.PREFIX} Card VRAM: capacity unknown.")]
        if v.get("peak_pct") is not None:
            lines.append(_t(lang, f"  Najwyżej w ostatnich 7 dniach: {v['peak_pct']:.0f}%" + (f" (~{tot * v['peak_pct'] / 100:.1f} GB)." if tot else "."),
                            f"  Highest in the last 7 days: {v['peak_pct']:.0f}%" + (f" (~{tot * v['peak_pct'] / 100:.1f} GB)." if tot else ".")))
            if v["peak_pct"] >= 90:
                lines.append(_t(lang, "§WARN Dochodzi do pełna: w takich grach obniż tekstury o jeden poziom, to usuwa przycięcia.",
                                "§WARN It fills up: in those games drop textures one level, that removes stutter."))
            else:
                lines.append(_t(lang, "§OK Wystarcza w tym, w co grasz.", "§OK Enough for what you play."))
        if tot and tot <= 6:
            lines.append(_t(lang, "  Przy nowych grach w 1440p 8 GB to dziś minimum.", "  For new games at 1440p, 8 GB is today's minimum."))
        return lines

    def _resp_disk_speed_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'czy mam szybki dysk', 'czy dysk ogranicza ładowanie gier'."""
        from core.pc_insight import disks, system_disk, disk_speed_class
        ds = disks()
        sd = system_disk()
        cls = disk_speed_class(sd)
        label = {"nvme": _t(lang, "NVMe (najszybszy typ, ~3000+ MB/s)", "NVMe (the fastest kind, ~3000+ MB/s)"),
                 "sata_ssd": _t(lang, "SSD SATA (~550 MB/s)", "SATA SSD (~550 MB/s)"),
                 "hdd": _t(lang, "HDD talerzowy (~150 MB/s)", "hard disk HDD (~150 MB/s)"),
                 "unknown": "?"}
        if not ds:
            return [_t(lang, f"{self.PREFIX} Nie mogę teraz odczytać dysków.", f"{self.PREFIX} I cannot read the drives right now.")]
        lines = [_t(lang, f"{self.PREFIX} Windows jest na: {sd.get('name', '?')}, {label[cls]}.",
                    f"{self.PREFIX} Windows runs from: {sd.get('name', '?')}, {label[cls]}.")]
        for d in ds:
            if d is sd:
                continue
            lines.append(f"  · {d['name']}: {label[disk_speed_class(d)]}, {d['size_gb']} GB")
        if cls == "nvme":
            lines.append(_t(lang, "§OK Szybki. Dysk nie ogranicza ładowania gier, o ile gry są na nim albo na innym SSD.",
                            "§OK Fast. The drive does not limit game loading, as long as games are on it or another SSD."))
        elif cls == "sata_ssd":
            lines.append(_t(lang, "§OK Wystarczająco szybki do gier; NVMe skróci ładowanie tylko o kilka sekund.",
                            "§OK Fast enough for games; NVMe would cut loading by only a few seconds."))
        elif cls == "hdd":
            lines.append(_t(lang, "§WARN Wolny: ładowanie gier i start Windows trwają przez niego kilka razy dłużej. SSD to najtańsze przyspieszenie.",
                            "§WARN Slow: game loading and boot take several times longer. An SSD is the cheapest speed-up."))
        if any(disk_speed_class(d) == "hdd" for d in ds if d is not sd):
            lines.append(_t(lang, "  Gry trzymaj na SSD, nie na dysku HDD.", "  Keep games on an SSD, not the HDD."))
        return lines

    def _resp_ssd_health(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pc_insight import disks, hardware_errors
        ds = disks()
        e = hardware_errors()
        lines = [_t(lang, f"{self.PREFIX} Stan dysków według Windows:", f"{self.PREFIX} Drive health according to Windows:")]
        for d in ds:
            ok = d["health"].lower() == "healthy"
            lines.append(f"  {'✓' if ok else '⚠'} {d['name']} ({d['bus']} {d['media']}, {d['size_gb']} GB): {d['health'] or '?'}")
        if e.get("ok"):
            n = e["disk"] + e["ntfs"]
            lines.append(_t(lang, f"  Błędy dysku w dzienniku (30 dni): {n}.", f"  Disk errors in the log (30 days): {n}."))
        lines.append(_t(lang, "  Zużycie komórek (SMART) Windows pokazuje tylko programom uruchomionym jako administrator.",
                        "  Cell wear (SMART) is shown by Windows only to programs run as administrator."))
        return lines

    def _resp_gaming_temps(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pc_insight import gaming_profile, cpu_clock
        gp = gaming_profile()
        if not gp.get("minutes"):
            return [_t(lang, f"{self.PREFIX} Nie mam jeszcze nagranego grania. Zagraj chwilę, a powiem, jak wyglądają temperatury.",
                       f"{self.PREFIX} No gaming recorded yet. Play for a while and I will tell you how temperatures look.")]
        t = gp.get("gpu_temp_max")
        lines = [_t(lang, f"{self.PREFIX} W grach (ostatnie 7 dni): GPU najwyżej {t:.0f}°C." if t else f"{self.PREFIX} GPU nie podało temperatury w grach.",
                    f"{self.PREFIX} In games (last 7 days): GPU at most {t:.0f}°C." if t else f"{self.PREFIX} The GPU reported no temperature in games.")]
        if t:
            lines.append(("§OK " if t < 80 else "§WARN ") + (
                _t(lang, "Bezpiecznie: karty graficzne pracują normalnie do ~83°C." if t < 80 else
                   "Gorąco: powyżej 83°C karta zwalnia. Sprawdź kurz i przepływ powietrza.",
                   "Safe: graphics cards run normally up to ~83°C." if t < 80 else
                   "Hot: above 83°C the card slows down. Check dust and airflow.")))
        clk = cpu_clock(0.4)
        if clk.get("limit_pct") is not None:
            lines.append(_t(lang, "  CPU: Windows nie podaje temperatury, ale nie widzę, żeby ciepło go hamowało." if clk["limit_pct"] >= 95 else
                            "  CPU: coś go teraz hamuje (temperatura albo limit mocy): 'czy cpu ma limit mocy'.",
                            "  CPU: Windows gives no temperature, but I see no heat holding it back." if clk["limit_pct"] >= 95 else
                            "  CPU: something holds it back right now (heat or power): 'is my cpu power limited'."))
        return lines

    _SOCKETS = {
        "lga1700": ("Intel 12., 13. i 14. generacji (do i9-14900K)", "Intel 12th, 13th and 14th gen (up to i9-14900K)"),
        "lga1200": ("Intel 10. i 11. generacji", "Intel 10th and 11th gen"),
        "lga1151": ("Intel 6.-9. generacji (zależnie od chipsetu)", "Intel 6th-9th gen (depends on chipset)"),
        "am4": ("AMD Ryzen 1000-5000 (do 5800X3D / 5950X)", "AMD Ryzen 1000-5000 (up to 5800X3D / 5950X)"),
        "am5": ("AMD Ryzen 7000-9000", "AMD Ryzen 7000-9000"),
        "lga1851": ("Intel Core Ultra 200S", "Intel Core Ultra 200S"),
    }

    def _resp_board_cpu_upgrade(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from core.hardware_compat import current_platform
            plat = current_platform() or {}
        except Exception:
            plat = {}
        board = str(plat.get("board") or "").strip()
        sock = str(plat.get("socket") or "")
        chip = str(plat.get("chipset") or "")
        lines = [_t(lang, f"{self.PREFIX} Twoja płyta" + (f" {board}" if board else "")
                    + (f": chipset {chip}" if chip else "") + (f", gniazdo {sock}" if sock else "") + ".",
                    f"{self.PREFIX} Your board" + (f" {board}" if board else "")
                    + (f": chipset {chip}" if chip else "") + (f", socket {sock}" if sock else "") + ".")]
        fits = self._SOCKETS.get(sock.lower().replace(" ", ""))
        if fits:
            lines.append(_t(lang, f"  Pasują do niej procesory: {fits[0]}.", f"  Processors that fit: {fits[1]}."))
        if sock.upper() == "LGA1700":
            try:
                from core.component_check import _bios
                b = _bios()
                if b.get("date") and b["date"].year <= 2022:
                    lines.append(_t(lang, f"  ⚠ BIOS z {b['date']:%m.%Y}: przed włożeniem procesora 14. generacji zaktualizuj BIOS.",
                                    f"  ⚠ BIOS from {b['date']:%Y-%m}: update it before fitting a 14th-gen processor."))
            except Exception:
                pass
        lines.append(_t(lang, "  Konkretny model sprawdzę: 'czy i5-13600K będzie pasować'.  [-> Upgrade Readiness]",
                        "  I can check a specific model: 'will an i5-13600K fit'.  [-> Upgrade Readiness]"))
        return lines

    def _resp_pc_age(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pc_insight import pc_age
        a = pc_age()
        if a["age"] is None:
            return [_t(lang, f"{self.PREFIX} Nie umiem określić wieku podzespołów po ich nazwach.",
                       f"{self.PREFIX} I cannot tell the age of the parts from their names.")]
        p = a["parts"]
        lines = [_t(lang, f"{self.PREFIX} Najstarsza część ma około {a['age']} lat.",
                    f"{self.PREFIX} The oldest part is about {a['age']} years old.")]
        if p["cpu"]:
            lines.append(_t(lang, f"  Procesor: {a['cpu_name']}, z {p['cpu']} r.", f"  Processor: {a['cpu_name']}, from {p['cpu']}."))
        if p["gpu"]:
            lines.append(_t(lang, f"  Karta: {a['gpu_name']}, z {p['gpu']} r.", f"  Graphics: {a['gpu_name']}, from {p['gpu']}."))
        if a["age"] <= 4:
            lines.append(_t(lang, "  Nie jest stary. To sprzęt, który obsługuje Windows 11 i obecne gry; o tym, jak działa, decyduje bardziej RAM i porządek w tle niż wiek.",
                            "  It is not old. This hardware runs Windows 11 and current games; how it performs depends more on RAM and the background than on age."))
        elif a["age"] <= 7:
            lines.append(_t(lang, "  Średni wiek: do pracy i większości gier w porządku, najnowsze gry na niższych ustawieniach.",
                            "  Middle-aged: fine for work and most games, the newest games on lower settings."))
        else:
            lines.append(_t(lang, "  Stary: przy nowych grach i programach będzie odstawał. Wymiana jednej części może nie wystarczyć.",
                            "  Old: it will lag behind with new games and software. Replacing one part may not be enough."))
        return lines

    def _resp_new_pc_advice(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from core.pc_insight import pc_age, weakest_part
        a, w = pc_age(), weakest_part()
        lines = []
        if a["age"] is not None and a["age"] <= 6 and w["part"] in ("ram", "disk", ""):
            lines.append(_t(lang, f"{self.PREFIX} Nie kupowałbym nowego. Ten komputer ma ok. {a['age']} lata, a jego słabość da się poprawić tanio:",
                            f"{self.PREFIX} I would not buy a new one. This PC is about {a['age']} years old and its weak spot is cheap to fix:"))
            if w["part"] == "ram":
                lines.append(_t(lang, "  · dołóż RAM do 16 GB (największa różnica za najmniej pieniędzy);",
                                "  · add RAM up to 16 GB (the biggest difference for the least money);"))
            if w["part"] == "disk":
                lines.append(_t(lang, "  · przenieś Windows na SSD;", "  · move Windows to an SSD;"))
            lines.append(_t(lang, "  · uporządkuj autostart i tło (przewodnik optymalizacji).",
                            "  · tidy the startup and background (the optimization guide)."))
            lines.append("§OFFER optimize")
        else:
            lines.append(_t(lang, f"{self.PREFIX} Zależy, czego brakuje. Najsłabsze ogniwo to: {self._PART_PL.get(w['part'], 'brak wyraźnego')}.",
                            f"{self.PREFIX} It depends on what is missing. The weakest link: {w['part'] or 'none clear'}."))
            lines.append(_t(lang, "  Jeśli trzeba by wymienić procesor, płytę i RAM naraz, nowy komputer zwykle wychodzi rozsądniej.",
                            "  If the processor, board and RAM would all need replacing, a new PC usually makes more sense."))
        lines.append(_t(lang, "  Szczegóły: 'co wymienić najpierw'.", "  Details: 'what should I upgrade first'."))
        return lines

    # ── trust and privacy ────────────────────────────────────────────────────
    def _resp_files_access(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Nie czytam Twoich plików, dokumentów, zdjęć ani przeglądarki.",
               f"{self.PREFIX} I do not read your files, documents, photos or browser."),
            _t(lang, "  Widzę to, co widzi Menedżer zadań: nazwy uruchomionych programów, ich obciążenie i pamięć, temperatury i stan dysków.",
               "  I see what Task Manager sees: names of running programs, their load and memory, temperatures and drive health."),
            _t(lang, "  Rozmiar folderów sprawdzam tylko, gdy zapytasz o miejsce na dysku, i nie zaglądam do ich treści.",
               "  Folder sizes are checked only when you ask about disk space, without opening their contents."),
        ]

    def _resp_data_stored(self, r: ParseResult, lang: str = "pl") -> List[str]:
        out = [
            _t(lang, f"{self.PREFIX} Zapisuję lokalnie, w folderze programu (data\\):",
               f"{self.PREFIX} I store locally, in the program folder (data\\):"),
            _t(lang, "  · historię obciążenia CPU, RAM, GPU i temperatur (baza hck_stats.db);",
               "  · the history of CPU, RAM, GPU load and temperatures (hck_stats.db);"),
            _t(lang, "  · czego się nauczyłem o normie tego komputera;", "  · what I learned about this PC's normal levels;"),
            _t(lang, "  · rozmowy ze mną i moje wiadomości (hck_gpt_chat.jsonl), żeby autor mógł poprawiać błędy, gdy mu je wyślesz.",
               "  · our chats and my messages (hck_gpt_chat.jsonl), so the author can fix mistakes if you send them."),
        ]
        out += self._telemetry_lines(lang) if hasattr(self, "_telemetry_lines") else []
        return out

    def _resp_what_remembered(self, r: ParseResult, lang: str = "pl") -> List[str]:
        lines = [_t(lang, f"{self.PREFIX} Co o Tobie i tym komputerze pamiętam:",
                    f"{self.PREFIX} What I remember about you and this PC:")]
        try:
            from core.machine_type import get
            kind = get()
            if kind:
                lines.append(_t(lang, f"  · To {'laptop' if kind == 'laptop' else 'komputer stacjonarny'}.",
                                f"  · It is a {'laptop' if kind == 'laptop' else 'desktop'}."))
        except Exception:
            pass
        try:
            from core.thermal_baseline import thermal_baseline as tb
            lines.append(_t(lang, f"  · Normę uczę się od {tb.learning_since_str('pl')}: {tb.overall_training_pct()}% nauczone.",
                            f"  · I have been learning for {tb.learning_since_str('en')}: {tb.overall_training_pct()}% learned."))
        except Exception:
            pass
        try:
            from core.pc_insight import usage_norms
            n = usage_norms().get("ram")
            if n:
                lines.append(_t(lang, f"  · RAM zwykle {n['avg']:.0f}%, szczyty {n['p95']:.0f}%.",
                                f"  · RAM usually {n['avg']:.0f}%, peaks {n['p95']:.0f}%."))
        except Exception:
            pass
        try:
            games = self._game_minutes(time.time() - 7 * 86400, time.time())
            if games:
                lines.append(_t(lang, "  · Grasz w: " + ", ".join(g for g, _ in games[:3]) + ".",
                                "  · You play: " + ", ".join(g for g, _ in games[:3]) + "."))
        except Exception:
            pass
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            hw = user_knowledge.get_all_hardware() or {}
            parts = [str(hw.get(k)) for k in ("cpu_model", "gpu_model") if hw.get(k)]
            if parts:
                lines.append(_t(lang, "  · Sprzęt: " + ", ".join(parts) + ".", "  · Hardware: " + ", ".join(parts) + "."))
        except Exception:
            pass
        lines.append(_t(lang, "  Nie znam Twojego imienia, plików ani historii przeglądarki. Pełny zapis nauki: [-> Learning Center]",
                        "  I do not know your name, files or browser history. The full learning record: [-> Learning Center]"))
        return lines

    def _resp_virus_capability(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Nie jestem antywirusem i nie zastąpię go. Co potrafię:",
               f"{self.PREFIX} I am not an antivirus and do not replace one. What I can do:"),
            _t(lang, "  · sprawdzić, czy procesy mają podpis znanego wydawcy;", "  · check whether processes are signed by a known publisher;"),
            _t(lang, "  · wyłapać program z nazwą systemową w złym folderze (np. svchost.exe poza System32);",
               "  · catch a program with a system name in the wrong folder (e.g. svchost.exe outside System32);"),
            _t(lang, "  · pokazać, co startuje z Windows i co nagle bierze dużo zasobów.",
               "  · show what starts with Windows and what suddenly takes a lot of resources."),
            _t(lang, "  Sprawdzenie teraz: 'skan bezpieczeństwa'. Do pełnego skanu: Windows Defender (Zabezpieczenia Windows).",
               "  Check now: 'security scan'. For a full scan: Windows Defender (Windows Security)."),
        ]

    def _resp_defender_enough(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Dla większości osób tak: Windows Defender jest wbudowany, aktualizuje się sam i dobrze wypada w niezależnych testach.",
               f"{self.PREFIX} For most people, yes: Windows Defender is built in, updates itself and scores well in independent tests."),
            _t(lang, "  Ważniejsze od drugiego antywirusa: aktualny Windows, programy tylko z oficjalnych stron i kopia zapasowa ważnych plików.",
               "  More important than a second antivirus: an up-to-date Windows, software only from official sites and a backup of what matters."),
            _t(lang, "  Dwa antywirusy naraz spowalniają komputer i potrafią się gryźć.",
               "  Two antiviruses at once slow the PC and can conflict."),
        ]

    def _resp_svchost_safety(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """Checks every running svchost.exe: the real one lives in System32."""
        good = bad = 0
        bad_paths = []
        try:
            import os
            import psutil
            sysdir = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32").lower()
            wow = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "SysWOW64").lower()
            for p in psutil.process_iter(["name", "exe"]):
                if (p.info.get("name") or "").lower() != "svchost.exe":
                    continue
                exe = (p.info.get("exe") or "").lower()
                if not exe:
                    good += 1          # protected system instance, path hidden
                elif os.path.dirname(exe) in (sysdir, wow):
                    good += 1
                else:
                    bad += 1
                    bad_paths.append(exe)
        except Exception:
            pass
        lines = [_t(lang, f"{self.PREFIX} Sprawdziłem wszystkie svchost.exe, które teraz działają: {good + bad}.",
                    f"{self.PREFIX} I checked every svchost.exe running now: {good + bad}.")]
        if bad:
            lines.append(_t(lang, f"§WARN {bad} z nich nie jest w System32: " + ", ".join(bad_paths[:2]) + ". To podejrzane: przeskanuj Defenderem.",
                            f"§WARN {bad} of them are not in System32: " + ", ".join(bad_paths[:2]) + ". Suspicious: scan with Defender."))
        else:
            lines.append(_t(lang, "§OK Wszystkie są z folderu Windows (System32). Wiele kopii svchost to normalne: każda prowadzi inne usługi.",
                            "§OK All of them come from the Windows folder (System32). Many svchost copies are normal: each runs different services."))
        lines.append(_t(lang, "  Prawdziwy svchost.exe jest tylko w C:\\Windows\\System32. Ta sama nazwa gdzie indziej to klasyczne podszycie.",
                        "  The real svchost.exe lives only in C:\\Windows\\System32. The same name elsewhere is a classic impostor."))
        return lines

    def _resp_signed_trust(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Podpis cyfrowy mówi, kto wydał program i że nikt go potem nie zmienił. To dobry znak, ale nie gwarancja.",
               f"{self.PREFIX} A digital signature says who published the program and that nobody changed it after. A good sign, not a guarantee."),
            _t(lang, "  Ufaj podpisom znanych wydawców (Microsoft, NVIDIA, Valve…). Nieznana firma z podpisem nadal może rozsyłać śmieci.",
               "  Trust signatures from known publishers (Microsoft, NVIDIA, Valve…). An unknown company with a signature can still ship junk."),
            _t(lang, "  Brak podpisu nie znaczy wirus: wiele małych programów (także PC Workman) go nie ma. Liczy się, skąd program pobrałeś.",
               "  No signature does not mean a virus: many small programs (PC Workman too) have none. What counts is where you got it."),
        ]

    def _resp_impostor_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """System process names running from the wrong folder."""
        names = {"svchost.exe", "lsass.exe", "csrss.exe", "winlogon.exe", "services.exe",
                 "smss.exe", "explorer.exe", "dwm.exe", "taskhostw.exe", "conhost.exe", "rundll32.exe"}
        found = []
        checked = 0
        try:
            import os
            import psutil
            root = os.environ.get("SystemRoot", r"C:\Windows").lower()
            for p in psutil.process_iter(["name", "exe"]):
                n = (p.info.get("name") or "").lower()
                if n not in names:
                    continue
                checked += 1
                exe = (p.info.get("exe") or "").lower()
                if exe and not exe.startswith(root):
                    found.append(exe)
        except Exception:
            pass
        lines = [_t(lang, f"{self.PREFIX} Tak. Szukam programów z nazwą procesu Windows uruchomionych spoza folderu Windows. Sprawdziłem teraz {checked}.",
                    f"{self.PREFIX} Yes. I look for programs with a Windows process name running from outside the Windows folder. Checked {checked} now.")]
        if found:
            lines.append(_t(lang, "§WARN Podejrzane: " + ", ".join(found[:3]) + ". Przeskanuj Defenderem.",
                            "§WARN Suspicious: " + ", ".join(found[:3]) + ". Scan with Defender."))
        else:
            lines.append(_t(lang, "§OK Żaden się nie podszywa.", "§OK None is an impostor."))
        lines.append(_t(lang, "  Pełniejsze sprawdzenie z podpisami: 'skan bezpieczeństwa'.", "  A fuller check with signatures: 'security scan'."))
        return lines

    # ── personality ──────────────────────────────────────────────────────────
    def _resp_pc_tired(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
            up_h = (time.time() - psutil.boot_time()) / 3600
            ram = psutil.virtual_memory().percent
        except Exception:
            up_h, ram = 0, 0
        lines = [_t(lang, f"{self.PREFIX} Komputery się nie męczą, ale Windows po długim działaniu bywa zaśmiecony: ten chodzi od {up_h:.0f} h (z uśpieniami), RAM {ram:.0f}%.",
                    f"{self.PREFIX} Computers do not get tired, but Windows can get cluttered after a long run: this one has been up {up_h:.0f} h (sleep included), RAM {ram:.0f}%.")]
        if up_h > 72:
            lines.append(_t(lang, "  Ponowne uruchomienie raz na kilka dni czyści pamięć i kończy zawieszone procesy. Szybkie uruchamianie i uśpienie tego nie robią.",
                            "  A restart every few days clears memory and ends stuck processes. Fast startup and sleep do not."))
        else:
            lines.append(_t(lang, "  Jest wypoczęty. Jeśli coś zwalnia, to nie zmęczenie: zapytaj 'co spowalnia komputer'.",
                            "  It is well rested. If something slows it down, it is not fatigue: ask 'what slows my pc'."))
        return lines

    def _resp_idle_activity(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [
            _t(lang, f"{self.PREFIX} Gdy nic nie robisz, pracuję cicho w tle:",
               f"{self.PREFIX} When you do nothing, I work quietly in the background:"),
            _t(lang, "  · co minutę zapisuję CPU, RAM, GPU i temperatury;", "  · every minute I record CPU, RAM, GPU and temperatures;"),
            _t(lang, "  · uczę się, co jest normalne dla tego komputera przy różnej pracy;",
               "  · I learn what is normal for this PC under different loads;"),
            _t(lang, "  · zapisuję okresy dużego obciążenia, gry i uśpienia do Pamięci aktywności;",
               "  · I record busy stretches, games and sleep into Activity Memory;"),
            _t(lang, "  · odzywam się sam tylko wtedy, gdy coś wyjdzie ponad normę, z limitem wiadomości.",
               "  · I speak up on my own only when something goes beyond normal, within a message limit."),
        ]

    def _resp_watching(self, r: ParseResult, lang: str = "pl") -> List[str]:
        lines = [_t(lang, f"{self.PREFIX} Tak, pilnuję: obciążenia, pamięci, temperatur GPU, dysków i nowych ciężkich procesów.",
                    f"{self.PREFIX} Yes, I watch: load, memory, GPU temperatures, drives and new heavy processes.")]
        try:
            from core.thermal_baseline import thermal_baseline as tb
            lines.append(_t(lang, f"  Znam już {tb.overall_training_pct()}% normy tego komputera, więc alarmuję przy odchyleniach od niej, nie przy sztywnych progach.",
                            f"  I know {tb.overall_training_pct()}% of this PC's normal, so I alert on departures from it, not fixed thresholds."))
        except Exception:
            pass
        lines.append(_t(lang, "  Nie zmieniam niczego sam: wszystko, co robi zmiany, robisz Ty albo potwierdzasz.",
                        "  I change nothing on my own: anything that makes changes is yours to do or confirm."))
        return lines

    def _resp_likes_job(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return [_t(lang,
            f"{self.PREFIX} Jestem programem, więc nie czuję, ale gdybym mógł wybrać: tak. Komputer, który znam od środka, to dobra robota. "
            f"Najbardziej lubię moment, gdy po optymalizacji liczby spadają.",
            f"{self.PREFIX} I am a program, so I do not feel, but if I could choose: yes. A computer I know from the inside is good work. "
            f"My favourite moment is when the numbers drop after an optimization.")]

    def _resp_predict_slowdown(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'czy potrafisz przewidzieć, kiedy komputer zacznie zwalniać'."""
        from core.pc_insight import usage_norms, _hist
        n = usage_norms()
        lines = [_t(lang, f"{self.PREFIX} Przewiduję z tego, co nagrałem, nie zgaduję:",
                    f"{self.PREFIX} I predict from what I recorded, I do not guess:")]
        ram = n.get("ram")
        if ram:
            lines.append(_t(lang, f"  · RAM zwykle {ram['avg']:.0f}%, szczyty {ram['p95']:.0f}%. "
                                  + ("Zwolni, gdy do przeglądarki dołożysz grę albo duży program: wtedy przekroczy 90%." if ram["p95"] >= 85 else
                                     "Zapas jest, spowolnień z braku pamięci nie przewiduję."),
                            f"  · RAM usually {ram['avg']:.0f}%, peaks {ram['p95']:.0f}%. "
                                  + ("It will slow down once a game or a big program joins the browser: then it crosses 90%." if ram["p95"] >= 85 else
                                     "There is room, I do not expect memory slowdowns.")))
        hours = self._busy_hours()
        if hours:
            lines.append(_t(lang, f"  · Najciężej jest zwykle około {hours}.", f"  · It is usually busiest around {hours}."))
        try:
            import psutil
            free = psutil.disk_usage("C:\\").free / 1024 ** 3
            lines.append(_t(lang, f"  · Dysk C: {free:.0f} GB wolne" + (": poniżej 15 GB Windows zacznie zwalniać." if free < 40 else "."),
                            f"  · Drive C: {free:.0f} GB free" + (": below 15 GB Windows will slow down." if free < 40 else ".")))
        except Exception:
            pass
        rv = [c for c, x in n.items() if (x.get("recent") or {}).get("notable")]
        lines.append(_t(lang, "  · Trend: " + ("rośnie obciążenie " + ", ".join(c.upper() for c in rv) + "." if rv else "na razie stabilnie."),
                        "  · Trend: " + ("load is rising on " + ", ".join(c.upper() for c in rv) + "." if rv else "stable so far.")))
        lines.append(_t(lang, "  Gdy coś zacznie odbiegać od normy, odezwę się sam.", "  When something drifts from normal, I will speak up."))
        return lines

    @staticmethod
    def _busy_hours() -> str:
        try:
            from hck_stats_engine.db_manager import db_manager
            conn = db_manager.get_connection()
            rows = conn.execute("SELECT timestamp, cpu_avg, gpu_avg FROM hourly_stats WHERE timestamp >= ?",
                                (time.time() - 14 * 86400,)).fetchall()
        except Exception:
            return ""
        acc = {}
        for ts, c, g in rows:
            h = time.localtime(ts).tm_hour
            acc.setdefault(h, []).append(max(c or 0, g or 0))
        if len(acc) < 4:
            return ""
        h = max(acc, key=lambda k: sum(acc[k]) / len(acc[k]))
        return f"{h:02d}:00-{(h + 1) % 24:02d}:00"

    def _resp_slower_lately(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'mam wrażenie, że ostatnio działa wolniej': the recorded days
        side by side, programs above their own normal, and what is always
        there."""
        from core.pc_insight import process_anomalies, findings
        lines = [_t(lang, f"{self.PREFIX} Sprawdziłem, co się zmieniło, na nagranej historii:",
                    f"{self.PREFIX} I checked what changed, on the recorded history:")]
        try:
            comp = self._resp_history_compare_days(r, lang)
            lines += [l for l in comp[1:] if "[->" not in l]
        except Exception:
            pass
        an = process_anomalies()
        for a in an[:3]:
            lines.append("  ⚠ " + self._finding_text({"code": "process_up", "data": a}, lang))
        lasting = [f for f in findings(deep=False) if f["sev"] >= 1 and f["code"] != "process_up"]
        if lasting:
            lines.append("")
            lines.append(_t(lang, "  Co spowalnia na stałe:", "  What slows it down all the time:"))
            for f in lasting[:3]:
                lines.append("  ⚠ " + self._finding_text(f, lang))
        if not an and not lasting:
            lines.append(_t(lang, "  W danych nie widzę pogorszenia. Jeśli czujesz różnicę, powiedz kiedy: w grze, przy starcie czy w przeglądarce.",
                            "  The data shows no decline. If you feel a difference, tell me when: in a game, at startup or in the browser."))
        lines.append("§OFFER optimize")
        return lines

    def _resp_slowdown_cause(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'co najbardziej spowalnia mojego PC': now + what is always there."""
        from core.pc_insight import findings
        lines = [_t(lang, f"{self.PREFIX} Co spowalnia ten komputer:", f"{self.PREFIX} What slows this PC down:")]
        hog = self._cpu_by_app(3)
        top, _ = self._ram_by_app(3)
        if hog:
            lines.append(_t(lang, "  Teraz procesor: ", "  Processor now: ") + ", ".join(f"{n} {p:.0f}%" for n, p in hog))
        if top:
            lines.append(_t(lang, "  Teraz pamięć: ", "  Memory now: ") + ", ".join(f"{n} {self._mb_text(mb)}" for n, mb in top))
            try:
                from hck_gpt.memory.session_memory import session_memory
                session_memory.note_reference("process", top[0][0] + ".exe", "slowdown_cause")
            except Exception:
                pass
        lasting = [f for f in findings(deep=False) if f["sev"] >= 1]
        if lasting:
            lines.append("")
            lines.append(_t(lang, "  Na stałe:", "  All the time:"))
            for f in lasting[:4]:
                lines.append("  ⚠ " + self._finding_text(f, lang))
        lines.append("§OFFER optimize")
        return lines
