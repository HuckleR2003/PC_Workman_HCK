"""ui.pages.gaming_home - the GAMING / In-Game page of My PC (2026-11-20).

The tile used to open the overlay configurator straight away. Marcin: a page
that explains first, with a title, a description, "Start configuration" and
the MiniOverlay switch in a red-to-blue banner, then what PC Workman has
learned about gaming on this PC.

    banner     title, one line, [Start configuration] [MiniOverlay: on/off]
    left       gaming learning, the heaviest games and processes (top 3),
               "See more - Process Center"
    right      a thermal verdict from the recorded gaming, and one line
               "CPU: OK  RAM: OK  GPU: OK" (blue / yellow / green); hover
               turns a part red like the Dashboard cards, a click opens
               its history

gaming_summary() is plain Python; the page only draws it. Nothing is shown
that the history does not hold.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk

from utils.fonts import UI as _BODY, HDR as _HDR

BG = "#0a0e14"
PANEL = "#0f141c"
PANEL2 = "#131a24"
LINE = "#1f2937"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
DIM = "#64748b"
HOT = "#7f1d1d"
COMP_COL = {"cpu": "#3b82f6", "ram": "#fbbf24", "gpu": "#10b981"}

_TX = {
    "title": {"pl": "Twoje statystyki w grze", "en": "Your stats in game"},
    "sub": {"pl": "Nakładka pokazuje w grze dokładnie to, co wybierzesz. MiniOverlay to mały monitor, który działa cały czas.",
            "en": "The overlay shows exactly what you pick, in the game. MiniOverlay is a small monitor that runs all the time."},
    "start": {"pl": "Rozpocznij konfigurację", "en": "Start configuration"},
    "mini_on": {"pl": "MiniOverlay: włączony", "en": "MiniOverlay: on"},
    "mini_off": {"pl": "MiniOverlay: wyłączony", "en": "MiniOverlay: off"},
    "learn": {"pl": "NAUKA W GRACH", "en": "LEARNING IN GAMES"},
    "learn_txt": {"pl": "Granie: {n} min z {t} potrzebnych do pełnej normy ({p}%).",
                  "en": "Gaming: {n} of the {t} minutes for a full normal ({p}%)."},
    "learn_none": {"pl": "Jeszcze nie widziałem grania na tym komputerze.",
                   "en": "I have not seen any gaming on this PC yet."},
    "games": {"pl": "NAJCIĘŻSZE GRY", "en": "HEAVIEST GAMES"},
    "game_row": {"pl": "{h} h  ·  GPU śr. {a}%", "en": "{h} h  ·  GPU avg {a}%"},
    "procs": {"pl": "NAJCIĘŻSZE PROCESY, 7 DNI", "en": "HEAVIEST PROCESSES, 7 DAYS"},
    "more": {"pl": "Zobacz więcej  ·  Centrum procesów", "en": "See more  ·  Process Center"},
    "none": {"pl": "Brak zapisów.", "en": "Nothing recorded."},
    "thermal": {"pl": "OCENA TERMICZNA W GRACH", "en": "TEMPERATURES IN GAMES"},
    "t_gpu": {"pl": "GPU w grach: średnio {m}°C, zwykle do {p}°C.", "en": "GPU in games: {m}°C on average, usually up to {p}°C."},
    "t_cpu": {"pl": "CPU w grach: średnio {m}°C, zwykle do {p}°C.", "en": "CPU in games: {m}°C on average, usually up to {p}°C."},
    "t_ok": {"pl": "W normie: chłodzenie radzi sobie z grami.", "en": "Normal: the cooling copes with games."},
    "t_warm": {"pl": "Ciepło: warto sprawdzić kurz i przepływ powietrza.", "en": "Warm: worth checking dust and airflow."},
    "t_hot": {"pl": "Gorąco: karta zbliża się do granicy, sprawdź chłodzenie.", "en": "Hot: the card nears its limit, check the cooling."},
    "t_none": {"pl": "Ocena pojawi się po kilku sesjach gry.", "en": "The verdict appears after a few gaming sessions."},
    "state": {"pl": "STAN PODZESPOŁÓW W GRACH  ·  kliknij, by zobaczyć historię",
              "en": "PARTS WHILE GAMING  ·  click for the history"},
    "ok": {"pl": "OK", "en": "OK"},
    "high": {"pl": "WYSOKO", "en": "HIGH"},
    "tight": {"pl": "CIASNO", "en": "TIGHT"},
    "hot": {"pl": "GORĄCO", "en": "HOT"},
    "na": {"pl": "--", "en": "--"},
}


def _lang() -> str:
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def _tx(key, **kw) -> str:
    s = _TX[key][_lang()]
    return s.format(**kw) if kw else s


def _num(v, d=1):
    s = f"{v:.{d}f}"
    return s.replace(".", ",") if _lang() == "pl" else s


def gaming_summary(now: float | None = None) -> dict:
    """What the history knows about gaming on this PC."""
    now = now or time.time()
    out = {"learn_n": 0, "learn_t": 180, "learn_pct": 0, "games": [], "procs": [],
           "gpu_t": None, "cpu_t": None, "state": {}}
    try:
        from core.thermal_baseline import thermal_baseline as tb, T_TRAINED
        out["learn_t"] = T_TRAINED
        for m in ("gpu_temp", "cpu_load"):
            n = tb.get_range("gaming", m).n
            if n:
                out["learn_n"] = n
                break
        out["learn_pct"] = int(min(100, out["learn_n"] / T_TRAINED * 100))
        for key, metric in (("gpu_t", "gpu_temp"), ("cpu_t", "cpu_temp")):
            r = tb.get_range("gaming", metric)
            if r.n >= 15 and r.mean:
                out[key] = (r.mean, r.p95 or r.mean)
    except Exception:
        pass
    try:
        from hck_stats_engine.db_manager import db_manager
        conn = db_manager.get_connection() if db_manager.is_ready else None
    except Exception:
        conn = None
    if conn is not None:
        try:
            rows = conn.execute(
                "SELECT process_name, SUM(COALESCE(resolved_at, timestamp) - timestamp) s, "
                "AVG(baseline) FROM events WHERE event_type IN ('game_session', 'load_period') "
                "AND metric IN ('game', 'gpu') AND process_name IS NOT NULL AND process_name != '' "
                "GROUP BY lower(process_name) ORDER BY s DESC LIMIT 3").fetchall()
            out["games"] = [(r[0], (r[1] or 0) / 3600, r[2]) for r in rows if (r[1] or 0) >= 300]
        except Exception:
            pass
    try:
        from hck_stats_engine import history as h
        out["procs"] = [(p.get("process") or p["name"], p["value"])
                        for p in h.top_processes("cpu", now - 7 * 86400, now, 3)]
        for comp in ("cpu", "ram", "gpu"):
            st = h.stats(comp, now - 7 * 86400, now)
            out["state"][comp] = st.get("p95") if st.get("has_data") else None
    except Exception:
        pass
    return out


def verdicts(summary: dict) -> dict:
    """comp -> status key (ok / high / tight / hot / na), and the thermal key."""
    st = summary.get("state", {})
    gpu_t = summary.get("gpu_t")
    res = {}
    cpu = st.get("cpu")
    res["cpu"] = "na" if cpu is None else ("ok" if cpu < 85 else "high")
    ram = st.get("ram")
    res["ram"] = "na" if ram is None else ("ok" if ram < 90 else "tight")
    if gpu_t:
        res["gpu"] = "ok" if gpu_t[1] < 80 else "hot"
    else:
        gpu = st.get("gpu")
        res["gpu"] = "na" if gpu is None else "ok"
    if gpu_t:
        res["thermal"] = "t_ok" if gpu_t[1] < 78 else "t_warm" if gpu_t[1] < 85 else "t_hot"
    else:
        res["thermal"] = "t_none"
    return res


class _Box:
    def __init__(self):
        self.data = None


def _work(box):
    try:
        box.data = gaming_summary()
    except Exception:
        box.data = {}


def _mini_on() -> bool:
    try:
        import ui.overlay_mini_monitor as _omm
        i = getattr(_omm, "_overlay_instance", None)
        return bool(i and getattr(i, "running", False))
    except Exception:
        return False


def build_gaming_home(win, parent, on_configure):
    """Draw the page into `parent` (My PC's content frame)."""
    root = tk.Frame(parent, bg=BG)
    root.pack(fill="both", expand=True)
    from ui.components.hero_banner import hero_banner

    def _toggle_mini():
        try:
            import ui.overlay_mini_monitor as _omm
            if _mini_on():
                _omm._overlay_instance.stop()
            else:
                _omm.launch_overlay_in_main_tk(parent.winfo_toplevel(),
                                               monitor=getattr(win, "monitor", None))
        except Exception as exc:
            print(f"[gaming] mini overlay: {exc}")
        root.after(80, _redraw_banner)

    holder = tk.Frame(root, bg=BG)
    holder.pack(fill="x")

    def _redraw_banner():
        try:
            if not holder.winfo_exists():
                return
        except Exception:
            return
        for w in holder.winfo_children():
            w.destroy()
        hero_banner(holder, _tx("title"), _tx("sub"),
                    stops=["#f87171", "#c084fc", "#60a5fa"], height=104,
                    buttons=[(_tx("start"), on_configure, True),
                             (_tx("mini_on") if _mini_on() else _tx("mini_off"), _toggle_mini, False)])
    _redraw_banner()

    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True, padx=14, pady=10)
    left = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
    left.pack(side="left", fill="both", expand=True)
    right = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE, width=360)
    right.pack(side="right", fill="y", padx=(10, 0))
    right.pack_propagate(False)
    tk.Label(left, text="…", bg=PANEL, fg=MUTED).pack(pady=20)

    box = _Box()
    threading.Thread(target=_work, args=(box,), daemon=True, name="gaming-home").start()

    def _wait():
        try:
            if not root.winfo_exists():
                return
        except Exception:
            return
        if box.data is None:
            root.after(120, _wait)
            return
        _fill(win, left, right, box.data)
    _wait()
    return root


def _caption(parent, text):
    tk.Label(parent, text=text, font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED,
             anchor="w").pack(fill="x", padx=14, pady=(12, 4))


def _fill(win, left, right, s):
    for w in left.winfo_children():
        w.destroy()
    _caption(left, _tx("learn"))
    if s.get("learn_n"):
        bar = tk.Frame(left, bg=PANEL2, height=8)
        bar.pack(fill="x", padx=14)
        tk.Frame(bar, bg="#c084fc", height=8).place(relwidth=max(0.02, s["learn_pct"] / 100), relheight=1)
        tk.Label(left, text=_tx("learn_txt", n=s["learn_n"], t=s["learn_t"], p=s["learn_pct"]),
                 font=(_BODY, 9), bg=PANEL, fg=TEXT, anchor="w").pack(fill="x", padx=14, pady=(4, 0))
    else:
        tk.Label(left, text=_tx("learn_none"), font=(_BODY, 9), bg=PANEL, fg=MUTED,
                 anchor="w").pack(fill="x", padx=14)

    cols = tk.Frame(left, bg=PANEL)
    cols.pack(fill="both", expand=True)
    gcol = tk.Frame(cols, bg=PANEL)
    gcol.pack(side="left", fill="both", expand=True)
    pcol = tk.Frame(cols, bg=PANEL)
    pcol.pack(side="left", fill="both", expand=True)
    _caption(gcol, _tx("games"))
    if s.get("games"):
        for name, hours, avg in s["games"]:
            r = tk.Frame(gcol, bg=PANEL)
            r.pack(fill="x", padx=14, pady=2)
            tk.Label(r, text=name, font=(_BODY, 9, "bold"), bg=PANEL, fg=TEXT, anchor="w").pack(fill="x")
            tk.Label(r, text=_tx("game_row", h=_num(hours), a=_num(avg or 0, 0)), font=(_BODY, 8),
                     bg=PANEL, fg=MUTED, anchor="w").pack(fill="x")
    else:
        tk.Label(gcol, text=_tx("none"), font=(_BODY, 8), bg=PANEL, fg=DIM, anchor="w").pack(fill="x", padx=14)
    _caption(pcol, _tx("procs"))
    if s.get("procs"):
        for name, val in s["procs"]:
            r = tk.Frame(pcol, bg=PANEL)
            r.pack(fill="x", padx=14, pady=2)
            a = tk.Label(r, text=name, font=(_BODY, 9), bg=PANEL, fg=TEXT, anchor="w")
            a.pack(side="left")
            b = tk.Label(r, text=f"{_num(val)}%", font=(_BODY, 8), bg=PANEL, fg=MUTED)
            b.pack(side="right")
            try:
                from ui.components import process_ref
                process_ref.bind([r, a, b], name, win)
            except Exception:
                pass
    else:
        tk.Label(pcol, text=_tx("none"), font=(_BODY, 8), bg=PANEL, fg=DIM, anchor="w").pack(fill="x", padx=14)
    more = tk.Label(pcol, text=_tx("more") + "  ›", font=(_BODY, 8, "bold"), bg=PANEL,
                    fg="#a78bfa", cursor="hand2", anchor="w")
    more.pack(fill="x", padx=14, pady=(8, 10))
    more.bind("<Button-1>", lambda e=None: win.open_process_center()
              if hasattr(win, "open_process_center") else None)

    for w in right.winfo_children():
        w.destroy()
    v = verdicts(s)
    _caption(right, _tx("thermal"))
    for key in ("gpu_t", "cpu_t"):
        if s.get(key):
            m, p = s[key]
            tk.Label(right, text=_tx("t_gpu" if key == "gpu_t" else "t_cpu", m=_num(m, 0), p=_num(p, 0)),
                     font=(_BODY, 9), bg=PANEL, fg=TEXT, anchor="w", justify="left",
                     wraplength=320).pack(fill="x", padx=14)
    col = {"t_ok": "#34d399", "t_warm": "#fbbf24", "t_hot": "#f87171", "t_none": MUTED}[v["thermal"]]
    tk.Label(right, text=_tx(v["thermal"]), font=(_BODY, 9, "bold"), bg=PANEL, fg=col,
             anchor="w", justify="left", wraplength=320).pack(fill="x", padx=14, pady=(6, 0))

    _caption(right, _tx("state"))
    line = tk.Frame(right, bg=PANEL)
    line.pack(fill="x", padx=14, pady=(0, 12))
    for comp in ("cpu", "ram", "gpu"):
        status = v[comp]
        c = COMP_COL[comp]
        cell = tk.Label(line, text=f"{comp.upper()}: {_tx(status)}", font=(_HDR, 9, "bold"),
                        bg=PANEL2, fg=c if status in ("ok", "na") else "#f87171",
                        padx=10, pady=6, cursor="hand2")
        cell.pack(side="left", padx=(0, 6))
        cell.bind("<Enter>", lambda e=None, w=cell: w.config(bg=HOT))
        cell.bind("<Leave>", lambda e=None, w=cell: w.config(bg=PANEL2))
        cell.bind("<Button-1>", lambda e=None, k=comp: win.open_activity_memory(k)
                  if hasattr(win, "open_activity_memory") else None)
