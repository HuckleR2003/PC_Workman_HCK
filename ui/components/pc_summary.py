"""ui.components.pc_summary - PC Workman on this PC, in one card (2026-11-20).

It replaces the "SESJA: 4h 47m" bar of My PC (the time since Windows
started, which says nothing about PC Workman). Marcin: "in the learning
ring, the number of hours PC Workman has been working, and something nice
for the user".

    ring      fills with the learning progress; in the middle the hours
              PC Workman has recorded on this PC
    facts     a few lines from the history, one at a time, every 6 s:
              the game played longest, the quietest day of the week,
              what the RAM flushes gave, since when it learns

compute_facts() is plain Python (tests call it); the card only draws it.
Facts that have no data behind them are left out, never invented.
"""
from __future__ import annotations

import threading
import tkinter as tk

from utils.fonts import UI as _BODY, HDR as _HDR

BG = "#0d1220"
EDGE = "#1e2a44"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
RING_BG = "#1e2440"
OK_C = "#34d399"
WARN_C = "#fbbf24"
VIOLET = "#a78bfa"

ROTATE_MS = 6000

_TX = {
    "title": {"pl": "PC Workman na tym komputerze", "en": "PC Workman on this PC"},
    "hours_word": {"pl": "h pracy", "en": "h on duty"},
    "learned": {"pl": "Typowe obciążenia znam w {p}%.", "en": "I know your typical workloads {p}%."},
    "game": {"pl": "Najdłużej grałeś w {g}: {h} h.", "en": "Your longest-played game: {g}, {h} h."},
    "quiet": {"pl": "Najspokojniejszy dzień tygodnia: {d}.", "en": "The quietest day of the week: {d}."},
    "busy": {"pl": "Najbardziej pracowity dzień: {d}.", "en": "The busiest day of the week: {d}."},
    "flush": {"pl": "Ostatnie {n} czyszczenia RAM obniżyły zajętość średnio o {pp} pp.",
              "en": "The last {n} RAM flushes lowered the use by {pp} points on average."},
    "since": {"pl": "Uczę się od {s}.", "en": "Learning since {s}."},
    "none": {"pl": "Zbieram pierwsze dane. Za godzinę będzie tu więcej.",
             "en": "Collecting the first data. More here in an hour."},
}
_DAYS = {"pl": ["niedziela", "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota"],
         "en": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]}


def _lang() -> str:
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def _num(v, d=1, lang="pl"):
    s = f"{v:.{d}f}"
    return s.replace(".", ",") if lang == "pl" else s


def compute_facts(lang: str | None = None) -> dict:
    """{"pct", "hours", "facts": [str, ...]} from what is recorded."""
    lang = lang or _lang()
    tx = lambda k, **kw: _TX[k][lang].format(**kw)  # noqa: E731
    out = {"pct": 0, "hours": 0.0, "facts": []}
    try:
        from core.thermal_baseline import thermal_baseline as tb
        out["pct"] = int(tb.overall_training_pct())
        out["hours"] = float(tb.total_observed_hours())
        out["facts"].append(tx("learned", p=out["pct"]))
        since = tb.learning_since_str(lang)
        if since:
            out["facts"].append(tx("since", s=since))
    except Exception:
        pass
    try:
        from hck_stats_engine.db_manager import db_manager
        conn = db_manager.get_connection() if db_manager.is_ready else None
    except Exception:
        conn = None
    if conn is not None:
        try:
            row = conn.execute(
                "SELECT process_name, SUM(COALESCE(resolved_at, timestamp) - timestamp) s "
                "FROM events WHERE event_type IN ('game_session', 'load_period') "
                "AND metric IN ('game', 'gpu') AND process_name IS NOT NULL AND process_name != '' "
                "GROUP BY lower(process_name) ORDER BY s DESC LIMIT 1").fetchone()
            if row and row[1] and row[1] >= 1800:
                out["facts"].insert(1, tx("game", g=row[0], h=_num(row[1] / 3600, 1, lang)))
        except Exception:
            pass
        try:
            rows = conn.execute(
                "SELECT strftime('%w', timestamp, 'unixepoch', 'localtime') d, AVG(cpu_avg), COUNT(*) "
                "FROM hourly_stats GROUP BY d").fetchall()
            rows = [r for r in rows if r[2] >= 3]
            if len(rows) >= 4:
                quiet = min(rows, key=lambda r: r[1])
                busy = max(rows, key=lambda r: r[1])
                out["facts"].append(tx("quiet", d=_DAYS[lang][int(quiet[0])]))
                if busy[0] != quiet[0]:
                    out["facts"].append(tx("busy", d=_DAYS[lang][int(busy[0])]))
        except Exception:
            pass
    try:
        from core.opt_receipts import get_receipts
        drops = [r["before"]["ram_pct"] - r["after"]["ram_pct"] for r in get_receipts()
                 if "ram" in str(r.get("action", "")).lower() and r.get("after")
                 and r.get("before")]
        if len(drops) >= 2:
            out["facts"].append(tx("flush", n=len(drops), pp=_num(sum(drops) / len(drops), 0, lang)))
    except Exception:
        pass
    if not out["facts"]:
        out["facts"].append(tx("none"))
    return out


class _Box:
    """What the worker thread hands over: plain data, no Tk object."""
    def __init__(self):
        self.data = None


def _work(box: _Box, lang: str) -> None:
    try:
        box.data = compute_facts(lang)
    except Exception:
        box.data = {"pct": 0, "hours": 0.0, "facts": []}


def build_summary_card(parent, on_click=None) -> tk.Frame:
    """The card; on_click (optional) opens the Learning Center."""
    lang = _lang()
    card = tk.Frame(parent, bg=BG, highlightthickness=1, highlightbackground=EDGE)
    card.pack(fill="x", pady=(4, 0))
    ring = tk.Canvas(card, width=96, height=96, bg=BG, highlightthickness=0)
    ring.pack(side="left", padx=(10, 8), pady=8)
    col = tk.Frame(card, bg=BG)
    col.pack(side="left", fill="both", expand=True, pady=10, padx=(0, 10))
    tk.Label(col, text=_TX["title"][lang], font=(_HDR, 9, "bold"), bg=BG, fg=TEXT,
             anchor="w").pack(fill="x")
    fact = tk.Label(col, text="", font=(_BODY, 9), bg=BG, fg=MUTED, anchor="w",
                    justify="left", wraplength=320)
    fact.pack(fill="x", pady=(6, 0))
    dots = tk.Frame(col, bg=BG)
    dots.pack(anchor="w", pady=(6, 0))
    state = {"i": 0, "facts": []}

    def _ring(pct, hours):
        ring.delete("all")
        ring.create_oval(8, 8, 88, 88, outline=RING_BG, width=8)
        c = OK_C if pct >= 80 else WARN_C if pct >= 40 else VIOLET
        if pct >= 100:
            # a 360-degree arc is drawn as nothing by Tk: a full ring is an oval
            ring.create_oval(8, 8, 88, 88, outline=c, width=8)
        elif pct > 0:
            ring.create_arc(8, 8, 88, 88, start=90, extent=-3.6 * pct,
                            style="arc", outline=c, width=8)
        h = f"{hours:.0f}" if hours >= 10 else _num(hours, 1, lang)
        ring.create_text(48, 43, text=h, font=(_HDR, 17, "bold"), fill=TEXT)
        ring.create_text(48, 63, text=_TX["hours_word"][lang], font=(_BODY, 7), fill=MUTED)

    def _show(i):
        facts = state["facts"]
        if not facts:
            return
        state["i"] = i % len(facts)
        fact.config(text=facts[state["i"]])
        for w in dots.winfo_children():
            w.destroy()
        for k in range(len(facts)):
            tk.Frame(dots, bg=TEXT if k == state["i"] else RING_BG, width=6, height=6
                     ).pack(side="left", padx=(0, 4))

    def _rotate():
        try:
            if not card.winfo_exists():
                return
        except Exception:
            return
        _show(state["i"] + 1)
        card.after(ROTATE_MS, _rotate)

    box = _Box()
    threading.Thread(target=_work, args=(box, lang), daemon=True, name="pc-summary").start()

    def _wait():
        try:
            if not card.winfo_exists():
                return
        except Exception:
            return
        if box.data is None:
            card.after(120, _wait)
            return
        _ring(box.data["pct"], box.data["hours"])
        state["facts"] = box.data["facts"]
        _show(0)
        card.after(ROTATE_MS, _rotate)
    _ring(0, 0.0)
    _wait()

    if on_click is not None:
        for w in (card, ring, col, fact):
            w.config(cursor="hand2")
            w.bind("<Button-1>", lambda e=None: on_click())
    return card
