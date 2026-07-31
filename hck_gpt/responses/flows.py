# hck_gpt/responses/flows.py
"""
Flow definitions for the FlowEngine (guided multi-step assistants).

Wave 1 ships THE master flow: "optimize my pc" - measure, startup, services,
RAM action (confirmed), verify-with-numbers. Steps are DATA + small callables;
they reuse existing engines (auto_optimizer, startup entries, live psutil)
and never duplicate handler logic.
"""
from __future__ import annotations

from hck_gpt.engine.flow_engine import Flow, FlowStep, flow_engine
from hck_gpt.responses.common import _t


# ── helpers ───────────────────────────────────────────────────────────────────
def _measure() -> dict:
    import psutil
    m = {"ram_pct": -1.0, "cpu_pct": -1.0, "procs": -1}
    try:
        m["ram_pct"] = float(psutil.virtual_memory().percent)
        m["cpu_pct"] = float(psutil.cpu_percent(interval=None))
        m["procs"]   = len(psutil.pids())
    except Exception:
        pass
    return m


def _startup_flagged() -> tuple:
    """(flagged, total) high/medium-impact autostart candidates, (-1,-1) on fail."""
    try:
        from ui.pages.startup_manager import _read_startup_entries
        ents = _read_startup_entries()
        flagged = len([e for e in ents
                       if e.get("rec") in ("disable", "delay")
                       and e.get("impact") in ("high", "medium")])
        return flagged, len(ents)
    except Exception:
        return -1, -1


# ── master flow: optimize ─────────────────────────────────────────────────────
def _s0_measure(rb, state, lang):
    m = _measure()
    state["before"] = m
    head = _t(lang,
              "🚀 Przewodnik optymalizacji - 5 kroków, konkretne liczby, "
              "zero zgadywania.",
              "🚀 Optimization guide - 5 steps, real numbers, no guessing.")
    if m["ram_pct"] >= 0:
        now = _t(lang,
                 f"KROK 1/5 · Pomiar startowy: RAM {m['ram_pct']:.0f}%  ·  "
                 f"CPU {m['cpu_pct']:.0f}%  ·  {m['procs']} procesów. "
                 f"Te liczby wrócą na końcu - zobaczysz różnicę.",
                 f"STEP 1/5 · Baseline: RAM {m['ram_pct']:.0f}%  ·  "
                 f"CPU {m['cpu_pct']:.0f}%  ·  {m['procs']} processes. "
                 f"We'll re-measure at the end - you'll SEE the difference.")
    else:
        now = _t(lang, "KROK 1/5 · Pomiar niedostępny - lecimy dalej.",
                       "STEP 1/5 · Baseline unavailable - moving on.")
    nxt = _t(lang, "➡ Napisz 'dalej'.", "➡ Type 'next'.")
    return [head, now, nxt]


def _s1_startup(rb, state, lang):
    flagged, total = _startup_flagged()
    if flagged > 0:
        body = _t(lang,
                  f"KROK 2/5 · Autostart: {total} wpisów, w tym {flagged} o "
                  f"wysokim/średnim wpływie do bezpiecznego wyłączenia. "
                  f"To najtańsze przyspieszenie startu systemu. "
                  f"[-> Startup Manager]",
                  f"STEP 2/5 · Startup: {total} entries, {flagged} of them "
                  f"high/medium impact and safe to disable - the cheapest "
                  f"boot speedup there is. [-> Startup Manager]")
    elif flagged == 0:
        body = _t(lang,
                  f"KROK 2/5 · Autostart: {total} wpisów i czysto - nic nie "
                  f"marnuje Twojego startu. Rzadki widok, brawo.",
                  f"STEP 2/5 · Startup: {total} entries and clean - nothing "
                  f"wasting your boot. Rare sight, well done.")
    else:
        body = _t(lang,
                  "KROK 2/5 · Autostart: nie mogę teraz odczytać wpisów - "
                  "zajrzyj do [-> Startup Manager] ręcznie.",
                  "STEP 2/5 · Startup: can't read entries right now - "
                  "check [-> Startup Manager] manually.")
    return [body, _t(lang, "➡ 'dalej', gdy gotowe.", "➡ 'next' when ready.")]


def _s2_services(rb, state, lang):
    body = _t(lang,
              "KROK 3/5 · Usługi: zamiast wyłączać na ślepo, ustaw profil "
              "(Gaming / Economy / Manager) - TURBO zatrzyma je tylko wtedy, "
              "gdy potrzebujesz mocy, i przywróci po wszystkim. "
              "[-> Services Manager]",
              "STEP 3/5 · Services: instead of blind disabling, set a profile "
              "(Gaming / Economy / Manager) - TURBO stops them only when you "
              "need the power and restores them after. [-> Services Manager]")
    return [body, _t(lang, "➡ 'dalej'.", "➡ 'next'.")]


def _s3_ram_say(rb, state, lang):
    m = _measure()
    state["pre_flush"] = m
    if m["ram_pct"] >= 75:
        tone = _t(lang, f"RAM {m['ram_pct']:.0f}% - jest co zwalniać.",
                        f"RAM {m['ram_pct']:.0f}% - there's real pressure.")
    elif m["ram_pct"] >= 0:
        tone = _t(lang,
                  f"RAM {m['ram_pct']:.0f}% - nie jest źle, ale flush "
                  f"potrafi oddać kilkaset MB.",
                  f"RAM {m['ram_pct']:.0f}% - not bad, but a flush can "
                  f"still hand back a few hundred MB.")
    else:
        tone = ""
    ask = _t(lang,
             "KROK 4/5 · Akcja: mogę TERAZ zwolnić pamięć (RAM Flush - "
             "bezpieczny, omija anti-cheaty i procesy krytyczne). "
             "Napisz 'tak' aby wykonać, 'pomiń' aby przejść dalej.",
             "STEP 4/5 · Action: I can free memory NOW (RAM Flush - safe, "
             "skips anti-cheat and OS-critical processes). "
             "Type 'yes' to run it, 'skip' to move on.")
    return [x for x in (tone, ask) if x]


def _s3_ram_act(rb, state, lang):
    from core.auto_optimizer import auto_optimizer
    ok, msg, before, after = auto_optimizer.flush_now()
    state["flush"] = {"ok": ok, "freed_mb": max(0, after - before)}
    return ["🧹 " + msg]


def _s4_verify(rb, state, lang):
    m = _measure()
    b = state.get("before") or {}
    lines = []
    if m["ram_pct"] >= 0 and b.get("ram_pct", -1) >= 0:
        d_ram = m["ram_pct"] - b["ram_pct"]   # after minus before (drop = minus)
        freed = (state.get("flush") or {}).get("freed_mb", 0)
        extra = _t(lang, f" (flush oddał ~{freed} MB)",
                         f" (flush returned ~{freed} MB)") if freed else ""
        lines.append(_t(lang,
            f"KROK 5/5 · Weryfikacja: RAM {b['ram_pct']:.0f}% -> "
            f"{m['ram_pct']:.0f}% ({d_ram:+.0f} pp){extra}  ·  "
            f"procesy {b.get('procs', '?')} -> {m['procs']}.",
            f"STEP 5/5 · Verify: RAM {b['ram_pct']:.0f}% -> "
            f"{m['ram_pct']:.0f}% ({d_ram:+.0f} pp){extra}  ·  "
            f"processes {b.get('procs', '?')} -> {m['procs']}."))
    else:
        lines.append(_t(lang, "KROK 5/5 · Weryfikacja niedostępna.",
                              "STEP 5/5 · Verification unavailable."))
    lines.append(_t(lang,
        "Trwałe efekty zrobisz w [-> Startup Manager] i profilach usług - "
        "a ja dalej uczę się Twojego 'normalnie', więc każda kolejna rada "
        "będzie celniejsza. To tyle - bez magii, same liczby. 🖤",
        "For lasting gains use [-> Startup Manager] and service profiles - "
        "and I keep learning your 'normal', so every next tip gets sharper. "
        "That's it - no magic, just numbers. 🖤"))
    # verify-after-action ledger: later "ile to było?" can recall this
    try:
        from hck_gpt.memory.session_memory import session_memory
        session_memory.record_response_data("optimize_guide", {
            "ram_before": b.get("ram_pct"), "ram_after": m["ram_pct"],
            "freed_mb": (state.get("flush") or {}).get("freed_mb", 0),
            "procs_before": b.get("procs"), "procs_after": m["procs"],
        })
    except Exception:
        pass
    return lines


flow_engine.register(Flow("optimize", [
    FlowStep(_s0_measure),
    FlowStep(_s1_startup),
    FlowStep(_s2_services),
    FlowStep(_s3_ram_say, act=_s3_ram_act),
    FlowStep(_s4_verify),
]))


# ── cooling diagnosis ───────────────────────────────────────────────────────
def _thermal_measure() -> dict:
    out = {
        "cpu_temp": -1.0, "cpu_temp_src": "none", "gpu_temp": -1.0,
        "cpu_load": -1.0, "gpu_load": -1.0, "ram_pct": -1.0,
        "top_name": "", "top_cpu": -1.0, "top_ram_mb": -1.0,
    }
    try:
        from hck_gpt.data.live_sensors import snapshot
        live = snapshot() or {}
        for key in ("cpu_temp", "gpu_temp", "cpu_load", "gpu_load"):
            try:
                out[key] = float(live.get(key, -1) or -1)
            except (TypeError, ValueError):
                pass
        out["cpu_temp_src"] = live.get("cpu_temp_src") or "none"
    except Exception:
        pass
    try:
        import psutil
        out["ram_pct"] = float(psutil.virtual_memory().percent)
        if out["cpu_load"] < 0:
            out["cpu_load"] = float(psutil.cpu_percent(interval=None))
        candidates = []
        for proc in psutil.process_iter(
                ["name", "cpu_percent", "memory_info"]):
            try:
                name = (proc.info.get("name") or "").strip()
                if not name or name.lower() in (
                        "system idle process", "idle"):
                    continue
                cpu = float(proc.info.get("cpu_percent") or 0)
                mem = proc.info.get("memory_info")
                ram_mb = (float(mem.rss) / 1_048_576) if mem else 0.0
                candidates.append((cpu, ram_mb, name))
            except Exception:
                continue
        if candidates:
            cpu, ram_mb, name = max(candidates)
            out.update(top_name=name, top_cpu=cpu, top_ram_mb=ram_mb)
    except Exception:
        pass
    return out


def _temp_text(value: float, lang: str) -> str:
    if value >= 0:
        return f"{value:.0f}°C"
    return "brak odczytu" if lang == "pl" else "no reading"


def _cool_s0(rb, state, lang):
    m = _thermal_measure()
    state["before"] = m
    cpu = _temp_text(m["cpu_temp"], lang)
    gpu = _temp_text(m["gpu_temp"], lang)
    if m["cpu_temp_src"] == "est" and m["cpu_temp"] >= 0:
        cpu = f"~{m['cpu_temp']:.0f}°C"
    lines = [_t(
        lang,
        "Diagnoza chłodzenia, 4 krótkie kroki. Najpierw oddzielam "
        "prawdziwy czujnik od oszacowania.",
        "Cooling diagnosis in 4 short steps. First I separate a real "
        "sensor from an estimate.",
    )]
    lines.append(_t(
        lang,
        f"KROK 1/4 · CPU {cpu} przy {m['cpu_load']:.0f}% obciążenia · "
        f"GPU {gpu} przy {m['gpu_load']:.0f}% · RAM {m['ram_pct']:.0f}%.",
        f"STEP 1/4 · CPU {cpu} at {m['cpu_load']:.0f}% load · "
        f"GPU {gpu} at {m['gpu_load']:.0f}% · RAM {m['ram_pct']:.0f}%.",
    ))
    if m["cpu_temp_src"] == "est":
        lines.append(_t(
            lang,
            "  CPU jest tylko oszacowaniem, więc nie wydaję na tej podstawie "
            "werdyktu o przegrzewaniu ani throttlingu.",
            "  CPU is estimated only, so I will not call overheating or "
            "throttling from that number.",
        ))
    elif m["cpu_temp"] < 0:
        lines.append(_t(
            lang,
            "  Brak czujnika CPU. Mogę nadal sprawdzić obciążenie i procesy, "
            "ale temperaturę trzeba potwierdzić czujnikiem.",
            "  No CPU sensor is available. I can still inspect load and "
            "processes, but temperature needs a sensor reading.",
        ))
    lines.append(_t(lang, "Napisz „dalej”.", "Type “next”."))
    return lines


def _cool_s1(rb, state, lang):
    m = _thermal_measure()
    state["mid"] = m
    lines = [_t(
        lang,
        "KROK 2/4 · Czy ciepło pochodzi z obciążenia, czy z chłodzenia:",
        "STEP 2/4 · Is the heat coming from workload or cooling:",
    )]
    real_cpu = m["cpu_temp_src"] == "sensor" and m["cpu_temp"] >= 0
    if real_cpu and m["cpu_temp"] >= 80 and m["cpu_load"] < 35:
        lines.append(_t(
            lang,
            f"  CPU ma {m['cpu_temp']:.0f}°C przy tylko "
            f"{m['cpu_load']:.0f}% obciążenia. To nie wygląda jak sam ciężki "
            "program. Najpierw sprawdź wentylator, kurz i montaż coolera.",
            f"  CPU is at {m['cpu_temp']:.0f}°C with only "
            f"{m['cpu_load']:.0f}% load. A heavy app alone does not explain "
            "that. Check the fan, dust and cooler mount first.",
        ))
    elif real_cpu and m["cpu_temp"] >= 85:
        lines.append(_t(
            lang,
            f"  CPU ma {m['cpu_temp']:.0f}°C przy "
            f"{m['cpu_load']:.0f}% obciążenia. Sprawdź, czy temperatura "
            "spada po zamknięciu pracy, zanim ruszysz chłodzenie.",
            f"  CPU is at {m['cpu_temp']:.0f}°C with "
            f"{m['cpu_load']:.0f}% load. Check whether it falls after the "
            "workload ends before changing the cooling.",
        ))
    elif m["gpu_temp"] >= 85:
        lines.append(_t(
            lang,
            f"  GPU jest teraz cieplejszym tropem: {m['gpu_temp']:.0f}°C "
            f"przy {m['gpu_load']:.0f}% obciążenia.",
            f"  GPU is the hotter lead right now: {m['gpu_temp']:.0f}°C "
            f"at {m['gpu_load']:.0f}% load.",
        ))
    else:
        lines.append(_t(
            lang,
            "  Nie widzę teraz twardego dowodu na stan alarmowy. Sprawdzamy "
            "źródło obciążenia i profilaktykę, nie gasimy pożaru na ślepo.",
            "  I do not see hard evidence of an emergency right now. We will "
            "check workload and prevention instead of treating a blind alarm.",
        ))
    if m["top_name"]:
        lines.append(_t(
            lang,
            f"  Najaktywniejszy proces: {m['top_name']} · "
            f"{m['top_cpu']:.1f}% CPU · {m['top_ram_mb']:.0f} MB RAM.",
            f"  Most active process: {m['top_name']} · "
            f"{m['top_cpu']:.1f}% CPU · {m['top_ram_mb']:.0f} MB RAM.",
        ))
    lines.append(_t(
        lang,
        "  Pełny podgląd: [-> Monitoring]. Napisz „dalej”.",
        "  Full view: [-> Monitoring]. Type “next”.",
    ))
    return lines


def _cool_s2(rb, state, lang):
    laptop = False
    try:
        import psutil
        laptop = psutil.sensors_battery() is not None
    except Exception:
        pass
    lines = [_t(
        lang,
        "KROK 3/4 · Zmieniaj po jednej rzeczy, inaczej nie dowiesz się, "
        "co naprawdę pomogło:",
        "STEP 3/4 · Change one thing at a time, otherwise you will not know "
        "what actually helped:",
    )]
    if laptop:
        lines.append(_t(
            lang,
            "  1. Postaw laptop na twardej powierzchni i odsłoń wloty. "
            "Podnieś tył o 1-2 cm, bez zasłaniania wentylacji.",
            "  1. Put the laptop on a hard surface and expose the intakes. "
            "Raise the rear 1-2 cm without blocking ventilation.",
        ))
    else:
        lines.append(_t(
            lang,
            "  1. Wyłącz komputer i sprawdź kurz w filtrach, radiatorze CPU "
            "oraz wlotach obudowy. Nie rozpędzaj wentylatorów sprężonym powietrzem.",
            "  1. Shut the PC down and check dust in filters, the CPU heatsink "
            "and case intakes. Do not overspin fans with compressed air.",
        ))
    lines.append(_t(
        lang,
        "  2. Sprawdź obroty i krzywą w [-> Fan Control]. Nie ustawiaj "
        "100% na stałe: szukamy temperatury pod obciążeniem przy rozsądnym hałasie.",
        "  2. Check RPM and the curve in [-> Fan Control]. Do not lock it "
        "to 100%: the goal is load temperature at reasonable noise.",
    ))
    lines.append(_t(
        lang,
        "  3. Pastę lub docisk coolera ruszaj dopiero, gdy temperatura jest "
        "wysoka przy niskim obciążeniu albo po czyszczeniu nie ma poprawy.",
        "  3. Touch thermal paste or cooler mounting only when temperature "
        "is high at low load or cleaning makes no difference.",
    ))
    lines.append(_t(lang, "Napisz „dalej”, a zmierzę ponownie.",
                          "Type “next” and I will measure again."))
    return lines


def _cool_s3(rb, state, lang):
    before = state.get("before") or {}
    now = _thermal_measure()
    lines = [_t(lang, "KROK 4/4 · Pomiar kontrolny:",
                      "STEP 4/4 · Verification:")]
    if (before.get("cpu_temp_src") == "sensor"
            and now["cpu_temp_src"] == "sensor"
            and before.get("cpu_temp", -1) >= 0
            and now["cpu_temp"] >= 0):
        delta = now["cpu_temp"] - float(before["cpu_temp"])
        lines.append(_t(
            lang,
            f"  CPU {before['cpu_temp']:.0f}°C -> {now['cpu_temp']:.0f}°C "
            f"({delta:+.0f}°C), obciążenie teraz {now['cpu_load']:.0f}%.",
            f"  CPU {before['cpu_temp']:.0f}°C -> {now['cpu_temp']:.0f}°C "
            f"({delta:+.0f}°C), load now {now['cpu_load']:.0f}%.",
        ))
        lines.append(_t(
            lang,
            "  Porównuj temperatury tylko przy podobnym obciążeniu. Inaczej "
            "różnica nie mówi nic o skuteczności chłodzenia.",
            "  Compare temperatures only at similar load. Otherwise the "
            "difference says nothing about cooling effectiveness.",
        ))
    else:
        lines.append(_t(
            lang,
            "  Nie mam dwóch prawdziwych odczytów CPU, więc nie wymyślam "
            "różnicy. Sprawdź czujnik w [-> Monitoring].",
            "  I do not have two real CPU readings, so I will not invent a "
            "delta. Check the sensor in [-> Monitoring].",
        ))
    lines.append(_t(
        lang,
        "  Po kilku dniach zapytaj „trend temperatury”, aby porównać historię, "
        "a nie pojedynczą chwilę.",
        "  After a few days ask for “temperature trend” to compare history, "
        "not one moment.",
    ))
    return lines


flow_engine.register(Flow("cooling", [
    FlowStep(_cool_s0),
    FlowStep(_cool_s1),
    FlowStep(_cool_s2),
    FlowStep(_cool_s3),
]))


# ── Windows desktop/shell recovery ──────────────────────────────────────────
def _desktop_state() -> dict:
    out = {"explorer": False, "dwm": False, "top_name": "", "top_cpu": 0.0}
    try:
        import psutil
        seen = []
        for proc in psutil.process_iter(["name", "cpu_percent"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name == "explorer.exe":
                    out["explorer"] = True
                elif name == "dwm.exe":
                    out["dwm"] = True
                if name not in ("system idle process", "idle"):
                    seen.append((float(proc.info.get("cpu_percent") or 0), name))
            except Exception:
                continue
        if seen:
            out["top_cpu"], out["top_name"] = max(seen)
    except Exception:
        pass
    return out


def _desktop_symptom(raw: str) -> str:
    low = (raw or "").lower()
    if any(x in low for x in ("czarn", "black screen", "black desktop")):
        return "black"
    if any(x in low for x in ("pasek", "taskbar", "start menu")):
        return "taskbar"
    if any(x in low for x in ("ikon", "icons")):
        return "icons"
    if any(x in low for x in ("miga", "flicker", "mruga")):
        return "flicker"
    return "shell"


def _desk_s0(rb, state, lang):
    snap = _desktop_state()
    state["desktop_before"] = snap
    symptom = _desktop_symptom(state.get("raw_text", ""))
    state["symptom"] = symptom
    labels_pl = {
        "black": "czarny ekran lub pulpit", "taskbar": "pasek zadań",
        "icons": "ikony pulpitu", "flicker": "miganie obrazu",
        "shell": "pulpit lub powłoka Windows",
    }
    labels_en = {
        "black": "black screen or desktop", "taskbar": "taskbar",
        "icons": "desktop icons", "flicker": "screen flicker",
        "shell": "Windows desktop or shell",
    }
    label = labels_pl[symptom] if lang == "pl" else labels_en[symptom]
    return [
        _t(
            lang,
            f"Naprawa pulpitu, 4 bezpieczne kroki. Rozpoznany trop: {label}.",
            f"Desktop recovery in 4 safe steps. Detected lead: {label}.",
        ),
        _t(
            lang,
            f"KROK 1/4 · explorer.exe: "
            f"{'działa' if snap['explorer'] else 'nie widzę procesu'} · "
            f"dwm.exe: {'działa' if snap['dwm'] else 'nie widzę procesu'}.",
            f"STEP 1/4 · explorer.exe: "
            f"{'running' if snap['explorer'] else 'not detected'} · "
            f"dwm.exe: {'running' if snap['dwm'] else 'not detected'}.",
        ),
        _t(
            lang,
            "  Niczego nie kończę automatycznie. Najpierw odzyskamy powłokę "
            "bez ryzyka utraty niezapisanej pracy. Napisz „dalej”.",
            "  I will not end anything automatically. First we will recover "
            "the shell without risking unsaved work. Type “next”.",
        ),
    ]


def _desk_s1(rb, state, lang):
    explorer = (state.get("desktop_before") or {}).get("explorer")
    if explorer:
        action_pl = (
            "Ctrl+Shift+Esc -> Procesy -> Eksplorator Windows -> Uruchom ponownie. "
            "To odświeża pulpit i pasek, ale nie zamyka otwartych dokumentów."
        )
        action_en = (
            "Ctrl+Shift+Esc -> Processes -> Windows Explorer -> Restart. "
            "This refreshes the desktop and taskbar without closing open documents."
        )
    else:
        action_pl = (
            "Ctrl+Shift+Esc -> Uruchom nowe zadanie -> wpisz explorer.exe -> OK. "
            "To uruchomi brakującą powłokę Windows."
        )
        action_en = (
            "Ctrl+Shift+Esc -> Run new task -> enter explorer.exe -> OK. "
            "This starts the missing Windows shell."
        )
    return [
        _t(lang, "KROK 2/4 · Najmniej ryzykowna naprawa:",
                 "STEP 2/4 · Lowest-risk repair:"),
        "  " + _t(lang, action_pl, action_en),
        _t(lang, "  Gdy sprawdzisz efekt, napisz „dalej”.",
                 "  After checking the result, type “next”."),
    ]


def _desk_s2(rb, state, lang):
    symptom = state.get("symptom")
    lines = [_t(lang, "KROK 3/4 · Jeśli problem został:",
                      "STEP 3/4 · If the problem remains:")]
    if symptom in ("black", "flicker"):
        lines.append(_t(
            lang,
            "  Naciśnij Win+Ctrl+Shift+B. Windows zresetuje sterownik obrazu; "
            "ekran może mignąć i wydać dźwięk.",
            "  Press Win+Ctrl+Shift+B. Windows will reset the display driver; "
            "the screen may blink and beep.",
        ))
    elif symptom == "icons":
        lines.append(_t(
            lang,
            "  Kliknij pulpit prawym przyciskiem -> Widok -> Pokaż ikony "
            "pulpitu. Sprawdź też, czy nie włączył się drugi pulpit wirtualny.",
            "  Right-click the desktop -> View -> Show desktop icons. Also "
            "check whether you switched to another virtual desktop.",
        ))
    elif symptom == "taskbar":
        lines.append(_t(
            lang,
            "  Naciśnij Win+R i wpisz ms-settings:taskbar. Jeśli Ustawienia "
            "się otworzą, sprawdź automatyczne ukrywanie paska.",
            "  Press Win+R and enter ms-settings:taskbar. If Settings opens, "
            "check automatic taskbar hiding.",
        ))
    else:
        lines.append(_t(
            lang,
            "  Win+Ctrl+Shift+B bezpiecznie odświeży sterownik obrazu. Jeśli "
            "problem dotyczy tylko ikon, sprawdź Pulpit -> Widok -> Pokaż ikony.",
            "  Win+Ctrl+Shift+B safely refreshes the display driver. If only "
            "icons are missing, check Desktop -> View -> Show desktop icons.",
        ))
    lines.append(_t(
        lang,
        "  Nie wyłączaj dwm.exe ani explorer.exe na siłę. Napisz „dalej”.",
        "  Do not force-close dwm.exe or explorer.exe. Type “next”.",
    ))
    return lines


def _desk_s3(rb, state, lang):
    return [
        _t(lang, "KROK 4/4 · Gdy problem wraca po restarcie:",
                 "STEP 4/4 · If the problem returns after a reboot:"),
        _t(
            lang,
            "  1. Win+R -> perfmon /rel. Sprawdź awarię Explorer, sterownika "
            "GPU lub aktualizację dokładnie w chwili problemu.",
            "  1. Win+R -> perfmon /rel. Check for an Explorer, GPU driver or "
            "update failure at the exact time of the problem.",
        ),
        _t(
            lang,
            "  2. Sprawdź sterownik obrazu i temperatury w [-> Components] "
            "oraz [-> Monitoring].",
            "  2. Check the display driver and temperatures in [-> Components] "
            "and [-> Monitoring].",
        ),
        _t(
            lang,
            "  3. Dopiero przy podejrzeniu uszkodzonych plików systemu uruchom "
            "Terminal jako administrator i użyj kolejno: DISM /Online "
            "/Cleanup-Image /RestoreHealth, potem sfc /scannow. hck_GPT niczego "
            "tu nie uruchamia sam.",
            "  3. Only when system-file corruption is plausible, open Terminal "
            "as administrator and run: DISM /Online /Cleanup-Image "
            "/RestoreHealth, then sfc /scannow. hck_GPT runs neither command "
            "on its own.",
        ),
    ]


flow_engine.register(Flow("desktop_repair", [
    FlowStep(_desk_s0),
    FlowStep(_desk_s1),
    FlowStep(_desk_s2),
    FlowStep(_desk_s3),
]))


# ── evidence-first upgrade planning ─────────────────────────────────────────
def _upgrade_snapshot() -> dict:
    out = {"platform": {}, "summary": {}, "temps": {}}
    try:
        from core.hardware_compat import current_platform
        out["platform"] = current_platform() or {}
    except Exception:
        pass
    try:
        from hck_stats_engine.query_api import query_api
        out["summary"] = query_api.get_summary_stats(days=14) or {}
        out["temps"] = query_api.get_temperature_summary(days=14) or {}
    except Exception:
        pass
    return out


def _upgrade_bottleneck(data: dict) -> str:
    s = data.get("summary") or {}
    cpu_avg = float(s.get("cpu_avg") or 0)
    cpu_max = float(s.get("cpu_max") or 0)
    gpu_avg = float(s.get("gpu_avg") or 0)
    gpu_max = float(s.get("gpu_max") or 0)
    ram_avg = float(s.get("ram_avg") or 0)
    ram_max = float(s.get("ram_max") or 0)
    if ram_avg >= 80 or ram_max >= 97:
        return "ram"
    if (cpu_avg >= 70 or cpu_max >= 99) and gpu_avg < 55:
        return "cpu"
    if (gpu_avg >= 70 or gpu_max >= 99) and cpu_avg < 60:
        return "gpu"
    if cpu_avg > 0:
        return "balanced"
    return "unknown"


def _up_s0(rb, state, lang):
    data = _upgrade_snapshot()
    state["upgrade"] = data
    plat = data["platform"]
    try:
        from core.hardware_compat import platform_label
        label = platform_label(plat)
    except Exception:
        label = "platform not identified"
    cpu = plat.get("cpu_name") or _t(lang, "niezidentyfikowany CPU",
                                          "unidentified CPU")
    gpu = plat.get("gpu_name") or _t(lang, "brak rozpoznanej karty",
                                          "no identified GPU")
    return [
        _t(
            lang,
            "Plan modernizacji, 4 kroki. Najpierw fakty, potem zakup.",
            "Upgrade plan in 4 steps. Evidence first, shopping second.",
        ),
        _t(lang, f"KROK 1/4 · Platforma: {label}.",
                 f"STEP 1/4 · Platform: {label}."),
        f"  CPU: {cpu}",
        f"  GPU: {gpu}",
        _t(
            lang,
            "  Jeżeli model płyty lub zasilacza nie jest znany, zaznaczę to "
            "zamiast zgadywać. Napisz „dalej”.",
            "  If the board or PSU model is unknown, I will say so instead "
            "of guessing. Type “next”.",
        ),
    ]


def _up_s1(rb, state, lang):
    data = state.get("upgrade") or {}
    s = data.get("summary") or {}
    bottleneck = _upgrade_bottleneck(data)
    state["bottleneck"] = bottleneck
    days = int(s.get("days_with_data") or 0)
    lines = [_t(lang, "KROK 2/4 · Dowody z realnego użycia:",
                      "STEP 2/4 · Evidence from real use:")]
    if not days or float(s.get("cpu_avg") or 0) <= 0:
        lines.append(_t(
            lang,
            "  Historia jest jeszcze za krótka. Nie wybieram części na "
            "podstawie samej nazwy sprzętu. Zbieraj dane przez 1-2 dni.",
            "  History is still too short. I will not choose a part from "
            "hardware names alone. Collect 1-2 days of use first.",
        ))
    else:
        lines.append(_t(
            lang,
            f"  {days} dni · CPU śr. {float(s.get('cpu_avg') or 0):.0f}% "
            f"(max {float(s.get('cpu_max') or 0):.0f}%) · GPU śr. "
            f"{float(s.get('gpu_avg') or 0):.0f}% · RAM śr. "
            f"{float(s.get('ram_avg') or 0):.0f}% "
            f"(max {float(s.get('ram_max') or 0):.0f}%).",
            f"  {days} days · CPU avg {float(s.get('cpu_avg') or 0):.0f}% "
            f"(max {float(s.get('cpu_max') or 0):.0f}%) · GPU avg "
            f"{float(s.get('gpu_avg') or 0):.0f}% · RAM avg "
            f"{float(s.get('ram_avg') or 0):.0f}% "
            f"(max {float(s.get('ram_max') or 0):.0f}%).",
        ))
        verdicts = {
            "cpu": ("Najmocniejszy trop: CPU.", "Strongest lead: CPU."),
            "gpu": ("Najmocniejszy trop: GPU.", "Strongest lead: GPU."),
            "ram": ("Najmocniejszy trop: RAM.", "Strongest lead: RAM."),
            "balanced": (
                "Brak jednego oczywistego wąskiego gardła.",
                "There is no single obvious bottleneck.",
            ),
        }
        pl, en = verdicts.get(bottleneck, (
            "Za mało danych na werdykt.", "Not enough data for a verdict."))
        lines.append("  " + _t(lang, pl, en))
    lines.append(_t(lang, "Napisz „dalej”.", "Type “next”."))
    return lines


def _up_s2(rb, state, lang):
    plat = ((state.get("upgrade") or {}).get("platform") or {})
    sock = plat.get("socket")
    chip = plat.get("chipset")
    ram = plat.get("ram_actual") or plat.get("ram_type")
    board = plat.get("board")
    lines = [_t(lang, "KROK 3/4 · Zgodność przed zakupem:",
                      "STEP 3/4 · Compatibility before buying:")]
    if sock:
        lines.append(_t(
            lang,
            f"  Rozpoznane: socket {sock}"
            f"{f', chipset {chip}' if chip else ''}"
            f"{f', pamięć {ram}' if ram else ''}.",
            f"  Detected: {sock} socket"
            f"{f', {chip} chipset' if chip else ''}"
            f"{f', {ram} memory' if ram else ''}.",
        ))
    else:
        lines.append(_t(
            lang,
            "  Socket nie został rozpoznany. Najpierw otwórz [-> Components] "
            "i pozwól zakończyć skan.",
            "  Socket was not identified. Open [-> Components] first and let "
            "the scan finish.",
        ))
    if board:
        lines.append(_t(lang, f"  Płyta: {board}.",
                              f"  Board: {board}."))
    lines.append(_t(
        lang,
        "  CPU: socket + lista wsparcia BIOS producenta. RAM: generacja DDR, "
        "pojemność, liczba modułów i profil XMP/EXPO. GPU: moc i złącza PSU "
        "oraz długość/grubość karty w obudowie.",
        "  CPU: socket plus the vendor BIOS support list. RAM: DDR generation, "
        "capacity, module count and XMP/EXPO profile. GPU: PSU wattage and "
        "connectors plus card length/thickness in the case.",
    ))
    lines.append(_t(
        lang,
        "  Bez dokładnego modelu zasilacza i obudowy nie potwierdzę fizycznego "
        "montażu karty. To celowa granica bezpieczeństwa. Napisz „dalej”.",
        "  Without exact PSU and case models I cannot confirm a GPU's physical "
        "fit. That is an intentional safety boundary. Type “next”.",
    ))
    return lines


def _up_s3(rb, state, lang):
    bottleneck = state.get("bottleneck", "unknown")
    plans = {
        "cpu": (
            "1. Sprawdź konkretny CPU. 2. Potwierdź BIOS i chłodzenie. "
            "3. Kupuj płytę/RAM tylko, jeśli wymusza je zmiana platformy.",
            "1. Check a concrete CPU. 2. Confirm BIOS and cooling. "
            "3. Buy a board/RAM only if the platform change requires them.",
        ),
        "gpu": (
            "1. Ustal rozdzielczość i gry/programy. 2. Sprawdź PSU oraz miejsce "
            "w obudowie. 3. Porównaj realny skok, nie sam numer modelu.",
            "1. Define resolution and games/apps. 2. Check PSU and case space. "
            "3. Compare a real uplift, not the model number alone.",
        ),
        "ram": (
            "1. Sprawdź wolne sloty i obecne moduły. 2. Dobierz tę samą "
            "generację DDR. 3. Najpewniejszy jest dopasowany zestaw, nie "
            "mieszanka przypadkowych kości.",
            "1. Check free slots and current modules. 2. Match the DDR "
            "generation. 3. A matched kit is safer than mixed random sticks.",
        ),
        "balanced": (
            "Nie kupuj części bez konkretnego celu. Najpierw wskaż grę, "
            "program, rozdzielczość i objaw, który ma zniknąć.",
            "Do not buy a part without a concrete target. First name the game, "
            "app, resolution and symptom the upgrade must fix.",
        ),
        "unknown": (
            "Najpierw zbierz historię i dokończ skan sprzętu. Dziś bezpieczny "
            "wynik brzmi: za mało dowodów na zakup.",
            "Collect history and finish the hardware scan first. Today the "
            "safe result is: not enough evidence to buy.",
        ),
    }
    pl, en = plans.get(bottleneck, plans["unknown"])
    return [
        _t(lang, "KROK 4/4 · Kolejność decyzji:",
                 "STEP 4/4 · Decision order:"),
        "  " + _t(lang, pl, en),
        _t(
            lang,
            "  Wpisz konkretny model, np. „czy RTX 4070 będzie pasować”, albo "
            "użyj [-> Upgrade Readiness].",
            "  Name a concrete model, for example “will an RTX 4070 fit”, or "
            "use [-> Upgrade Readiness].",
        ),
    ]


flow_engine.register(Flow("upgrade_plan", [
    FlowStep(_up_s0),
    FlowStep(_up_s1),
    FlowStep(_up_s2),
    FlowStep(_up_s3),
]))
