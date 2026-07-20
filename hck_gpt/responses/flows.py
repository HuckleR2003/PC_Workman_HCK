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
