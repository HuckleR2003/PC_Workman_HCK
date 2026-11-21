"""ui.pages.process_center - the Process Information Center (2026-11-20).

Every process on this PC in one place: what it is, what it costs now and
over 7 days, whether it runs every day, whether it is trusted, and what to
do with it. The data comes from core.process_center; this file only draws.

Layout, top to bottom:
    gradient banner          title, one line, Startup / Services buttons
    four tiles               now | 7-day average | in the background | worth switching off
    process count chart      1H / 24H / 7D / 30D, from the minute and hour history
    filters + search
    table | card             sortable table (click a heading; again to reverse),
                             the selected process's card on the right

Refreshes every 3 s in a background thread (one refresh costs ~0.5 s:
the process list, the window list and, every 2 minutes, the history).
"""
from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import ttk

from utils.fonts import UI as _BODY, HDR as _HDR, MONO as _MONO

BG = "#0a0e14"
PANEL = "#0f141c"
PANEL2 = "#131a24"
LINE = "#1f2937"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
DIM = "#64748b"
LIME = "#a3e635"
VIOLET = "#a78bfa"
BLUE = "#60a5fa"
AMBER = "#fbbf24"
RED = "#f87171"
GREEN = "#34d399"

REFRESH_MS = 3000
RANGES = [("1H", 3600), ("24H", 86400), ("7D", 7 * 86400), ("30D", 30 * 86400)]


def _pl() -> bool:
    try:
        from utils.i18n import get_lang
        return get_lang() != "en"
    except Exception:
        return True


def L(pl: str, en: str) -> str:
    return pl if _pl() else en


def _fmt_mb(mb) -> str:
    if mb is None:
        return "-"
    return f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.0f} MB"


def _steady_text(r) -> str:
    if r["streak"] >= 7:
        return L(f"codziennie, {r['streak']} dni", f"daily, {r['streak']} days")
    if r["days_7"]:
        return L(f"{r['days_7']} z 7 dni", f"{r['days_7']} of 7 days")
    return L("nowy", "new")


def _safety_text(s) -> str:
    return {"trusted": L("zaufany", "trusted"), "check": L("do sprawdzenia", "check"),
            "unknown": L("nieznany", "unknown")}[s]


def _action_text(a) -> str:
    return {"startup_off": L("wyłącz z autostartu", "off at startup"),
            "delay": L("opóźnij start", "delay start"),
            "close_ok": L("można zamknąć", "can be closed"),
            "protected": L("chroniony", "protected"),
            "keep": L("zostaw", "keep")}.get(a, a)


COLUMNS = [
    # id, heading, width, sort key, anchor
    ("name",   {"pl": "Proces", "en": "Process"}, 150, "name", "w"),
    ("cpu",    {"pl": "CPU teraz", "en": "CPU now"}, 64, "cpu", "e"),
    ("ram",    {"pl": "RAM teraz", "en": "RAM now"}, 70, "ram", "e"),
    ("cpu_7d", {"pl": "CPU 7 dni", "en": "CPU 7 d"}, 64, "cpu_7d", "e"),
    ("ram_7d", {"pl": "RAM 7 dni", "en": "RAM 7 d"}, 70, "ram_7d", "e"),
    ("steady", {"pl": "Stały?", "en": "Steady?"}, 92, "steady", "w"),
    ("safety", {"pl": "Bezpieczny?", "en": "Safe?"}, 88, "safety", "w"),
    ("action", {"pl": "Rekomendacja", "en": "Advice"}, 128, "action", "w"),
]

FILTERS = [("all", {"pl": "Wszystkie", "en": "All"}),
           ("background", {"pl": "W tle", "en": "Background"}),
           ("steady", {"pl": "Stałe", "en": "Steady"}),
           ("consider", {"pl": "Do rozważenia", "en": "Worth a look"}),
           ("games", {"pl": "Gry", "en": "Games"})]


def _h(d) -> str:
    return d["pl"] if _pl() else d["en"]


class _Shared:
    """What the background threads touch: plain data, never a Tk object.
    A thread that held the page (and so its widgets) could drop the last
    reference after the page closed, and Tk then crashed with
    "Tcl_AsyncDelete: async handler deleted by the wrong thread"."""

    def __init__(self, sampler):
        self.sampler = sampler
        self.pending = None
        self.busy = False
        self.series = None


def _refresh_worker(sh: _Shared) -> None:
    try:
        from core.process_center import counts
        rows = sh.sampler.refresh()
        sh.pending = (rows, counts(rows))
    except Exception as e:
        print(f"[ProcessCenter] refresh: {e}")
        sh.pending = None
    sh.busy = False


def _series_worker(sh: _Shared, span: float) -> None:
    try:
        from core.process_center import series
        sh.series = series(span)
    except Exception:
        sh.series = []


class ProcessCenterPage:

    def __init__(self, app, parent, focus: str | None = None):
        self.app = app
        self.focus = (focus or "").lower() or None
        self.sort_key, self.sort_desc = "ram", True
        self.kind, self.query = "all", ""
        self.range = "24H"
        self.rows: list = []
        self.selected: str | None = self.focus
        from core.process_center import ProcessSampler
        self._sh = _Shared(ProcessSampler())

        self.root = tk.Frame(parent, bg=BG)
        self.root.pack(fill="both", expand=True)
        self._build_banner()
        self._build_tiles()
        self._build_chart()
        self._build_filters()
        self._build_body()
        self._load_chart()
        self._refresh()

    # ── building ─────────────────────────────────────────────────────────
    def _nav(self, page):
        try:
            self.app.current_view = None
            self.app._switch_to_page(page)
        except Exception:
            pass

    def _build_banner(self):
        from ui.components.hero_banner import hero_banner, nav_crumbs
        crumbs = nav_crumbs(self.app, L("Centrum procesów", "Process Center"),
                            [(L("Autostart", "Startup"), "startup_manager"),
                             (L("Usługi", "Services"), "services_manager")])
        hero_banner(self.root,
                    L("Centrum informacji o procesach", "Process Information Center"),
                    L("Co działa na tym komputerze, od kiedy, ile kosztuje i co z tym zrobić.",
                      "What runs on this PC, since when, what it costs and what to do about it."),
                    stops=["#65a30d", "#7c3aed", "#2563eb"], height=96,
                    buttons=[(L("Menedżer autostartu", "Startup Manager"),
                              lambda: self._nav("startup_manager"), True),
                             (L("Usługi Windows", "Windows services"),
                              lambda: self._nav("services_manager"), False)],
                    crumbs=crumbs)

    def _build_tiles(self):
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", padx=16, pady=(8, 0))
        self.tiles = {}
        spec = [("now", L("PROCESY TERAZ", "PROCESSES NOW"), TEXT),
                ("avg", L("ŚREDNIO, 7 DNI", "AVERAGE, 7 DAYS"), BLUE),
                ("bg", L("W TLE (BEZ OKNA)", "IN THE BACKGROUND"), VIOLET),
                ("consider", L("DO ROZWAŻENIA", "WORTH A LOOK"), AMBER)]
        for i, (key, cap, col) in enumerate(spec):
            t = tk.Frame(row, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            t.pack(side="left", fill="x", expand=True, padx=(0 if i == 0 else 8, 0))
            tk.Label(t, text=cap, font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED,
                     anchor="w").pack(fill="x", padx=12, pady=(6, 0))
            v = tk.Label(t, text="…", font=(_HDR, 15, "bold"), bg=PANEL, fg=col, anchor="w")
            v.pack(fill="x", padx=12)
            sub = tk.Label(t, text="", font=(_BODY, 7), bg=PANEL, fg=DIM, anchor="w")
            sub.pack(fill="x", padx=12, pady=(0, 6))
            self.tiles[key] = (v, sub)
        # "worth a look" filters the table
        v, sub = self.tiles["consider"]
        for w in (v, sub, v.master):
            w.config(cursor="hand2")
            w.bind("<Button-1>", lambda e=None: self._set_kind("consider"))

    def _build_chart(self):
        box = tk.Frame(self.root, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="x", padx=16, pady=(8, 0))
        top = tk.Frame(box, bg=PANEL)
        top.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(top, text=L("LICZBA PROCESÓW W CZASIE", "NUMBER OF PROCESSES OVER TIME"),
                 font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED).pack(side="left")
        self.range_btns = {}
        for lab, _ in reversed(RANGES):
            b = tk.Label(top, text=lab, font=(_BODY, 7, "bold"), padx=7, pady=1, cursor="hand2")
            b.pack(side="right", padx=(4, 0))
            b.bind("<Button-1>", lambda e=None, l=lab: self._set_range(l))
            self.range_btns[lab] = b
        self._paint_range()
        self.chart = tk.Canvas(box, height=62, bg=PANEL, highlightthickness=0)
        self.chart.pack(fill="x", padx=10, pady=(4, 8))
        self.chart.bind("<Configure>", lambda e=None: self._draw_chart())
        self._series = []

    def _build_filters(self):
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=16, pady=(8, 4))
        self.filter_btns = {}
        for key, lab in FILTERS:
            b = tk.Label(bar, text=_h(lab), font=(_BODY, 8, "bold"), padx=10, pady=3,
                         cursor="hand2")
            b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e=None, k=key: self._set_kind(k))
            self.filter_btns[key] = b
        self._paint_filters()
        self.search = tk.Entry(bar, font=(_BODY, 9), bg=PANEL2, fg=TEXT, insertbackground=TEXT,
                               relief="flat", width=26, highlightthickness=1,
                               highlightbackground=LINE, highlightcolor=VIOLET)
        self.search.pack(side="right", ipady=3)
        tk.Label(bar, text=L("Szukaj", "Search"), font=(_BODY, 8), bg=BG,
                 fg=MUTED).pack(side="right", padx=(0, 6))
        self.search.bind("<KeyRelease>", lambda e=None: self._on_search())

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.card = tk.Frame(body, bg=PANEL, width=300, highlightthickness=1,
                             highlightbackground=LINE)
        self.card.pack(side="right", fill="y", padx=(10, 0))
        self.card.pack_propagate(False)
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("PC.Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                     rowheight=22, borderwidth=0, font=(_BODY, 8))
        st.configure("PC.Treeview.Heading", background=PANEL2, foreground=MUTED,
                     borderwidth=0, relief="flat", font=(_BODY, 7, "bold"))
        st.map("PC.Treeview", background=[("selected", "#2a2244")],
               foreground=[("selected", "#ffffff")])
        st.map("PC.Treeview.Heading", background=[("active", "#1c2433")])

        self.tree = ttk.Treeview(left, columns=[c[0] for c in COLUMNS], show="headings",
                                 style="PC.Treeview", selectmode="browse")
        for cid, lab, w, key, anchor in COLUMNS:
            self.tree.heading(cid, text=_h(lab), anchor=anchor,
                              command=lambda k=key: self._sort_by(k))
            self.tree.column(cid, width=w, minwidth=50, anchor=anchor,
                             stretch=(cid == "name"))
        self.tree.tag_configure("odd", background=PANEL2)
        self.tree.tag_configure("check", foreground=AMBER)
        self.tree.tag_configure("consider", foreground="#fde68a")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e=None: self._on_select())
        self._headings()
        self._draw_card(None)

    # ── state changes ────────────────────────────────────────────────────
    def _paint_range(self):
        for lab, b in self.range_btns.items():
            on = lab == self.range
            b.config(bg="#2a2244" if on else PANEL2, fg="#ffffff" if on else MUTED)

    def _paint_filters(self):
        for key, b in self.filter_btns.items():
            on = key == self.kind
            b.config(bg="#2a2244" if on else PANEL, fg="#ffffff" if on else MUTED)

    def _set_range(self, lab):
        self.range = lab
        self._paint_range()
        self._load_chart()

    def _set_kind(self, kind):
        self.kind = "all" if kind == self.kind and kind != "all" else kind
        self._paint_filters()
        self._fill_table()

    def _on_search(self):
        self.query = self.search.get()
        self._fill_table()

    def _sort_by(self, key):
        if key == self.sort_key:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_key, self.sort_desc = key, key != "name"
        self._headings()
        self._fill_table()

    def _headings(self):
        for cid, lab, w, key, anchor in COLUMNS:
            arrow = (" ▼" if self.sort_desc else " ▲") if key == self.sort_key else ""
            self.tree.heading(cid, text=_h(lab) + arrow)

    def _on_select(self):
        sel = self.tree.selection()
        if sel:
            self.selected = sel[0]
            self._draw_card(self._row(self.selected))

    def _history_row(self, name):
        """A row for a process that is not running: what the history knows."""
        from core.process_center import history_by_name
        h = history_by_name().get(name, {})
        try:
            from core.recommendations import recommend
            rec = recommend(name)
        except Exception:
            rec = {"action": "keep", "impact": "low", "why": ""}
        info = None
        try:
            from hck_gpt.process_library import process_library
            info = process_library.get_process_info(name)
        except Exception:
            pass
        from core.process_center import _SAFETY
        return {"name": name, "display": (info or {}).get("name") or name, "instances": 0,
                "cpu": 0.0, "ram_mb": 0, "windowed": False, "pids": [],
                "cpu_7d": h.get("cpu_7d"), "ram_7d": h.get("ram_7d"),
                "days_7": h.get("days_7", 0), "streak": h.get("streak", 0),
                "first_seen": h.get("first_seen"),
                "safety": _SAFETY.get((info or {}).get("safety"), "unknown"),
                "category": (info or {}).get("category") or "", "game": False,
                "action": rec["action"], "impact": rec["impact"], "why": rec["why"],
                "not_running": True}

    def _row(self, name):
        for r in self.rows:
            if r["name"] == name:
                return r
        return None

    # ── refresh loop ─────────────────────────────────────────────────────
    def _alive(self) -> bool:
        try:
            return bool(self.root.winfo_exists())
        except Exception:
            return False

    def _refresh(self):
        if not self._alive():
            return
        sh = self._sh
        if not sh.busy:
            sh.busy = True
            threading.Thread(target=_refresh_worker, args=(sh,), daemon=True,
                             name="process-center").start()
        self.root.after(150, self._apply)

    def _apply(self):
        if not self._alive():
            return
        sh = self._sh
        if sh.pending is None and sh.busy:
            self.root.after(150, self._apply)
            return
        pending, sh.pending = sh.pending, None
        if pending:
            self.rows, c = pending
            self._fill_tiles(c)
            self._fill_table()
            row = self._row(self.selected) if self.selected else None
            if row is not None:
                self._draw_card(row, keep_extra=True)
        self.root.after(REFRESH_MS, self._refresh)

    # ── filling ──────────────────────────────────────────────────────────
    def _fill_tiles(self, c):
        v, sub = self.tiles["now"]
        v.config(text=str(c["now"]))
        sub.config(text=L(f"{len(self.rows)} różnych programów", f"{len(self.rows)} different programs"))
        v, sub = self.tiles["avg"]
        if c["avg_7d"] is None:
            v.config(text="-")
            sub.config(text=L("zbieram dane, wróć za godzinę", "collecting, back in an hour"))
        else:
            v.config(text=str(c["avg_7d"]))
            sub.config(text=L(f"najwięcej {c['max_7d']}", f"peak {c['max_7d']}"))
        v, sub = self.tiles["bg"]
        v.config(text=str(c["background"]))
        share = c["background"] / max(c["now"], 1) * 100
        sub.config(text=L(f"{share:.0f}% wszystkich; to normalne w Windows",
                          f"{share:.0f}% of all; normal on Windows"))
        v, sub = self.tiles["consider"]
        v.config(text=str(c["to_consider"]))
        sub.config(text=L("kliknij, by je pokazać", "click to show them"))

    def _fill_table(self):
        from core.process_center import filter_rows, sort_rows
        rows = sort_rows(filter_rows(self.rows, self.kind, self.query),
                         self.sort_key, self.sort_desc)
        tree = self.tree
        y = tree.yview()[0]
        tree.delete(*tree.get_children())
        for i, r in enumerate(rows):
            name = r["display"] + (f"  ×{r['instances']}" if r["instances"] > 1 else "")
            vals = (name, f"{r['cpu']:.1f}%", _fmt_mb(r["ram_mb"]),
                    "-" if r["cpu_7d"] is None else f"{r['cpu_7d']:.1f}%",
                    _fmt_mb(r["ram_7d"]), _steady_text(r), _safety_text(r["safety"]),
                    _action_text(r["action"]))
            tags = ["odd"] if i % 2 else []
            if r["safety"] == "check":
                tags.append("check")
            elif r["action"] in ("startup_off", "delay", "close_ok"):
                tags.append("consider")
            tree.insert("", "end", iid=r["name"], values=vals, tags=tags)
        if self.selected and tree.exists(self.selected):
            tree.selection_set(self.selected)
            if self.focus == self.selected:
                tree.see(self.selected)
                self.focus = None
        elif self.focus and self.rows and getattr(self, "_card_for", None) != self.focus:
            # opened on a process that is not running now (from the history)
            self._draw_card(self._history_row(self.focus))
        tree.yview_moveto(y)

    # ── chart ────────────────────────────────────────────────────────────
    def _load_chart(self):
        sh = self._sh
        sh.series = None
        threading.Thread(target=_series_worker, args=(sh, dict(RANGES)[self.range]),
                         daemon=True, name="process-center-chart").start()
        self._wait_chart()

    def _wait_chart(self):
        if not self._alive():
            return
        if self._sh.series is None:
            self.root.after(120, self._wait_chart)
            return
        self._series = self._sh.series
        self._draw_chart()

    def _draw_chart(self):
        cv = self.chart
        try:
            cv.delete("all")
            W, H = max(cv.winfo_width(), 200), int(cv.cget("height"))
        except Exception:
            return
        pts = self._series
        if len(pts) < 2:
            cv.create_text(W / 2, H / 2, fill=DIM, font=(_BODY, 8), text=L(
                "PC Workman zaczął zapisywać liczbę procesów w tej wersji. Wykres wypełni się w ciągu godziny.",
                "PC Workman started recording the number of processes in this version. The chart fills within an hour."))
            return
        lo = min(v for _, v in pts)
        hi = max(v for _, v in pts)
        pad = max((hi - lo) * 0.15, 5)
        lo, hi = max(0, lo - pad), hi + pad
        t0, t1 = pts[0][0], pts[-1][0]
        PL, PR, PT, PB = 34, 6, 6, 14

        def X(t):
            return PL + (t - t0) / max(t1 - t0, 1) * (W - PL - PR)

        def Y(v):
            return PT + (1 - (v - lo) / max(hi - lo, 1)) * (H - PT - PB)
        for frac in (0, 0.5, 1):
            v = lo + (hi - lo) * frac
            cv.create_line(PL, Y(v), W - PR, Y(v), fill=LINE)
            cv.create_text(PL - 4, Y(v), text=f"{v:.0f}", anchor="e", fill=DIM, font=(_MONO, 7))
        coords = []
        for t, v in pts:
            coords += [X(t), Y(v)]
        poly = [PL, H - PB] + coords + [X(t1), H - PB]
        cv.create_polygon(poly, fill="#1e1638", outline="")
        cv.create_line(coords, fill=VIOLET, width=2, smooth=True)
        from datetime import datetime
        fmt = "%H:%M" if t1 - t0 <= 86400 else "%d.%m"
        cv.create_text(PL, H - 2, text=datetime.fromtimestamp(t0).strftime(fmt),
                       anchor="sw", fill=DIM, font=(_MONO, 7))
        cv.create_text(W - PR, H - 2, text=datetime.fromtimestamp(t1).strftime(fmt),
                       anchor="se", fill=DIM, font=(_MONO, 7))

    # ── the card ─────────────────────────────────────────────────────────
    def _draw_card(self, r, keep_extra=False):
        card = self.card
        if keep_extra and r is not None and getattr(self, "_card_for", None) == r["name"]:
            self._card_live(r)
            return
        for w in card.winfo_children():
            w.destroy()
        self._card_for = r["name"] if r else None
        if r is None:
            tk.Label(card, text=L("Wybierz proces z tabeli,\nby zobaczyć jego kartę.",
                                  "Pick a process in the table\nto see its card."),
                     font=(_BODY, 9), bg=PANEL, fg=MUTED, justify="center").pack(expand=True)
            return
        pad = {"padx": 14}
        tk.Frame(card, bg=VIOLET, height=3).pack(fill="x")
        # the buttons first: packed before the text, they keep their place
        # when the window is short and the text gets clipped instead
        btns = tk.Frame(card, bg=PANEL)
        btns.pack(side="bottom", fill="x", pady=(6, 10), **pad)

        def button(text, cmd, primary=False):
            bg, fg = ("#2a2244", "#ffffff") if primary else (PANEL2, TEXT)
            b = tk.Label(btns, text=text, font=(_BODY, 8, "bold"), bg=bg, fg=fg, pady=6, cursor="hand2")
            b.pack(fill="x", pady=(4, 0))
            b.bind("<Button-1>", lambda e=None: cmd())
        button(L("Zapytaj hck_GPT", "Ask hck_GPT"), lambda: self._ask(r), primary=True)
        if r["action"] in ("startup_off", "delay"):
            button(L("Otwórz Autostart", "Open Startup Manager"), lambda: self._nav("startup_manager"))
        button(L("Otwórz lokalizację pliku", "Open file location"), lambda: self._open_location(r))
        tk.Label(card, text=r["display"], font=(_HDR, 13, "bold"), bg=PANEL, fg=TEXT,
                 anchor="w", wraplength=270, justify="left").pack(fill="x", pady=(10, 0), **pad)
        tk.Label(card, text=r["name"] + (f"   ·   {r['instances']} " + L("procesów", "processes")
                                         if r["instances"] > 1 else ""),
                 font=(_MONO, 7), bg=PANEL, fg=DIM, anchor="w").pack(fill="x", **pad)
        if r.get("not_running"):
            tk.Label(card, text=L("Teraz nie działa. Poniżej to, co zapisała historia.",
                                  "Not running now. Below is what the history recorded."),
                     font=(_BODY, 7, "bold"), bg=PANEL, fg=AMBER, anchor="w",
                     wraplength=270, justify="left").pack(fill="x", pady=(4, 0), **pad)
        info = None
        try:
            from hck_gpt.process_library import process_library
            info = process_library.get_process_info(r["name"])
        except Exception:
            pass
        desc = (info or {}).get("description") or L("Nie ma go jeszcze w bazie procesów.",
                                                     "Not in the process library yet.")
        tk.Label(card, text=desc, font=(_BODY, 8), bg=PANEL, fg=TEXT, anchor="w",
                 justify="left", wraplength=270).pack(fill="x", pady=(8, 0), **pad)
        if (info or {}).get("vendor"):
            tk.Label(card, text=info["vendor"], font=(_BODY, 7), bg=PANEL, fg=MUTED,
                     anchor="w").pack(fill="x", **pad)

        grid = tk.Frame(card, bg=PANEL)
        grid.pack(fill="x", pady=(10, 0), **pad)
        self._card_vals = {}
        for i, (key, cap) in enumerate([("cpu", L("CPU teraz", "CPU now")),
                                        ("ram", L("RAM teraz", "RAM now")),
                                        ("cpu_7d", L("CPU, 7 dni", "CPU, 7 days")),
                                        ("ram_7d", L("RAM, 7 dni", "RAM, 7 days"))]):
            f = tk.Frame(grid, bg=PANEL2)
            f.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, 6) if i % 2 == 0 else 0, pady=3)
            grid.columnconfigure(i % 2, weight=1)
            tk.Label(f, text=cap, font=(_BODY, 7), bg=PANEL2, fg=MUTED, anchor="w").pack(fill="x", padx=8, pady=(4, 0))
            v = tk.Label(f, text="", font=(_HDR, 11, "bold"), bg=PANEL2, fg=TEXT, anchor="w")
            v.pack(fill="x", padx=8, pady=(0, 4))
            self._card_vals[key] = v

        def line(cap, val, col=TEXT):
            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x", pady=(6, 0), **pad)
            tk.Label(row, text=cap, font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED, anchor="w").pack(fill="x")
            tk.Label(row, text=val, font=(_BODY, 8), bg=PANEL, fg=col, anchor="w",
                     justify="left", wraplength=270).pack(fill="x")
        from core.process_history import describe
        line(L("NA TYM KOMPUTERZE", "ON THIS PC"),
             describe({"days_7": r["days_7"], "streak": r["streak"], "first_seen": r["first_seen"]},
                      "pl" if _pl() else "en"))
        col = {"trusted": GREEN, "check": AMBER}.get(r["safety"], MUTED)
        line(L("BEZPIECZEŃSTWO", "SAFETY"), _safety_text(r["safety"]).capitalize(), col)
        line(L("REKOMENDACJA", "ADVICE"),
             _action_text(r["action"]).capitalize() + (f". {r['why']}" if r["why"] else ""),
             AMBER if r["action"] in ("startup_off", "delay", "close_ok") else TEXT)

        self._card_live(r)

    def _card_live(self, r):
        vals = getattr(self, "_card_vals", {})
        try:
            vals["cpu"].config(text=f"{r['cpu']:.1f}%")
            vals["ram"].config(text=_fmt_mb(r["ram_mb"]))
            vals["cpu_7d"].config(text="-" if r["cpu_7d"] is None else f"{r['cpu_7d']:.1f}%")
            vals["ram_7d"].config(text=_fmt_mb(r["ram_7d"]))
        except Exception:
            pass

    def _ask(self, r):
        panel = getattr(self.app, "gpt_panel", None)
        if panel is not None and hasattr(panel, "ask"):
            panel.ask(L(f"czym jest {r['name']}", f"what is {r['name']}"))

    def _open_location(self, r):
        try:
            import psutil
            for pid in r.get("pids", []):
                try:
                    exe = psutil.Process(pid).exe()
                except Exception:
                    continue
                if exe and os.path.exists(exe):
                    import subprocess
                    subprocess.Popen(["explorer", "/select,", exe])
                    return
        except Exception:
            pass


def build_process_center_page(app, parent, focus: str | None = None) -> ProcessCenterPage:
    return ProcessCenterPage(app, parent, focus=focus)
