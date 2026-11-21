"""ui.pages.profile_page - Your profile (2026-11-20).

My PC's "Your account" did nothing: PC Workman has no accounts and should
not have them. This page is a profile that stays on this PC:
  * this PC: the name you give it, its kind (desktop / laptop), CPU and GPU
  * since the beginning: hours recorded, games, recordings, RAM flushes,
    cleanups, since when it learns
  * milestones, earned from the history (nothing to unlock by clicking)
  * privacy in one place: what is sent (the anonymous hardware snapshot, on
    or off), export of all data, how to delete it

profile_stats() and milestones() are plain Python.
"""
from __future__ import annotations

import os
import threading
import tkinter as tk

from utils.fonts import UI as _BODY, HDR as _HDR

BG = "#0a0e14"
PANEL = "#0f141c"
PANEL2 = "#131a24"
LINE = "#1f2937"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
DIM = "#64748b"
GREEN = "#34d399"
VIOLET = "#a78bfa"

_TX = {
    "title": {"pl": "Twój profil", "en": "Your profile"},
    "sub": {"pl": "Wszystko zostaje na tym komputerze. Bez konta i bez logowania.",
            "en": "Everything stays on this PC. No account, no sign-in."},
    "export": {"pl": "Eksportuj moje dane", "en": "Export my data"},
    "settings": {"pl": "Ustawienia prywatności", "en": "Privacy settings"},
    "pc": {"pl": "TEN KOMPUTER", "en": "THIS PC"},
    "name": {"pl": "Nazwa", "en": "Name"},
    "name_hint": {"pl": "np. Komputer do grania", "en": "e.g. Gaming PC"},
    "save": {"pl": "Zapisz", "en": "Save"},
    "saved": {"pl": "Zapisano.", "en": "Saved."},
    "kind": {"pl": "Rodzaj", "en": "Kind"},
    "desktop": {"pl": "komputer stacjonarny", "en": "desktop"},
    "laptop": {"pl": "laptop", "en": "laptop"},
    "unknown": {"pl": "nie wiem jeszcze", "en": "not known yet"},
    "since": {"pl": "OD POCZĄTKU", "en": "SINCE THE BEGINNING"},
    "hours": {"pl": "godzin z PC Workman", "en": "hours with PC Workman"},
    "games": {"pl": "gier w historii", "en": "games in the history"},
    "game_hours": {"pl": "godzin grania", "en": "hours of gaming"},
    "recordings": {"pl": "nagrań przed/po", "en": "before/after recordings"},
    "flushes": {"pl": "czyszczeń RAM", "en": "RAM flushes"},
    "cleanups": {"pl": "oczyszczeń dysku", "en": "disk cleanups"},
    "learning": {"pl": "Uczę się od {s}.", "en": "Learning since {s}."},
    "miles": {"pl": "KAMIENIE MILOWE", "en": "MILESTONES"},
    "m_week": {"pl": "Tydzień razem", "en": "A week together"},
    "m_100h": {"pl": "100 godzin", "en": "100 hours"},
    "m_norm": {"pl": "Znam Twoją normę", "en": "I know your normal"},
    "m_game": {"pl": "Pierwsza gra", "en": "First game"},
    "m_rec": {"pl": "Pierwsze nagranie", "en": "First recording"},
    "m_clean": {"pl": "Porządki", "en": "Tidy-up"},
    "privacy": {"pl": "PRYWATNOŚĆ", "en": "PRIVACY"},
    "tel_on": {"pl": "Wysyłany jest tylko anonimowy raport o sprzęcie (modele części, ekrany, wersja Windows, czas pracy programu). Nigdy pliki, nazwy ani procesy.",
               "en": "Only an anonymous hardware snapshot is sent (part models, screens, Windows version, how long the app ran). Never files, names or processes."},
    "tel_off": {"pl": "Nic nie jest wysyłane: telemetria jest wyłączona.", "en": "Nothing is sent: telemetry is off."},
    "delete": {"pl": "Usunięcie danych: zamknij PC Workman i usuń folder data obok programu (w wersji ze Sklepu: %LOCALAPPDATA%\\PC_Workman_HCK). Przed tym możesz je wyeksportować.",
               "en": "To delete the data: close PC Workman and delete the data folder next to it (Store version: %LOCALAPPDATA%\\PC_Workman_HCK). Export it first if you like."},
    "exported": {"pl": "✓ Zapisano: {p}", "en": "✓ Saved: {p}"},
}


def _lang():
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def _tx(k, lang, **kw):
    s = _TX[k][lang]
    return s.format(**kw) if kw else s


def _app_settings(app):
    try:
        from utils.prefs_io import load_json
        return load_json(app._app_settings_file(), {}) or {}
    except Exception:
        return {}


def profile_stats() -> dict:
    out = {"hours": 0.0, "games": 0, "game_hours": 0.0, "recordings": 0, "flushes": 0,
           "cleanups": 0, "learn_pct": 0, "learning_days": 0, "since": ""}
    try:
        from core.thermal_baseline import thermal_baseline as tb
        out["hours"] = tb.total_observed_hours()
        out["learn_pct"] = tb.overall_training_pct()
        out["since"] = tb.learning_since_str(_lang())
        started = float((getattr(tb, "_raw", {}) or {}).get("started_ts", 0) or 0)
        if started:
            import time
            out["learning_days"] = int((time.time() - started) / 86400)
    except Exception:
        pass
    try:
        from hck_stats_engine.db_manager import db_manager
        conn = db_manager.get_connection() if db_manager.is_ready else None
        if conn is not None:
            row = conn.execute(
                "SELECT COUNT(DISTINCT lower(process_name)), "
                "SUM(COALESCE(resolved_at, timestamp) - timestamp) FROM events "
                "WHERE event_type IN ('game_session', 'load_period') AND metric IN ('game', 'gpu') "
                "AND process_name IS NOT NULL AND process_name != ''").fetchone()
            if row:
                out["games"] = int(row[0] or 0)
                out["game_hours"] = (row[1] or 0) / 3600
    except Exception:
        pass
    try:
        from utils.paths import APP_DIR
        d = os.path.join(APP_DIR, "data", "observations")
        out["recordings"] = len([f for f in os.listdir(d) if f.endswith(".json")]) if os.path.isdir(d) else 0
    except Exception:
        pass
    try:
        from core.opt_receipts import get_receipts
        out["flushes"] = sum(1 for r in get_receipts() if "ram" in str(r.get("action", "")).lower())
    except Exception:
        pass
    try:
        import json
        from utils.paths import APP_DIR
        p = os.path.join(APP_DIR, "data", "cache", "cleanup_log.json")
        out["cleanups"] = len(json.load(open(p, encoding="utf-8"))) if os.path.isfile(p) else 0
    except Exception:
        pass
    return out


def milestones(st: dict) -> list:
    """[(key, earned)] from the stats; nothing is earned by a click."""
    return [("m_week", st["learning_days"] >= 7 or st["hours"] >= 40),
            ("m_100h", st["hours"] >= 100),
            ("m_norm", st["learn_pct"] >= 80),
            ("m_game", st["games"] >= 1),
            ("m_rec", st["recordings"] >= 1),
            ("m_clean", st["cleanups"] >= 1)]


class _Box:
    def __init__(self):
        self.data = None


def _work(box):
    box.data = profile_stats()


def build_profile_page(app, parent):
    lang = _lang()
    root = tk.Frame(parent, bg=BG)
    root.pack(fill="both", expand=True)
    status = {}

    def _export():
        try:
            from core.data_export import export_zip
            res = export_zip()
            status["lbl"].config(text=_tx("exported", lang, p=res.get("path", "")), fg=GREEN)
        except Exception as e:
            status["lbl"].config(text=str(e), fg="#f87171")

    def _settings():
        try:
            app._show_overlay("settings")
        except Exception:
            pass

    from ui.components.hero_banner import hero_banner, nav_crumbs
    hero_banner(root, _tx("title", lang), _tx("sub", lang), stops=["#8b5cf6", "#ec4899", "#f59e0b"],
                height=96, crumbs=nav_crumbs(app, _tx("title", lang)),
                buttons=[(_tx("export", lang), _export, True), (_tx("settings", lang), _settings, False)])
    status["lbl"] = tk.Label(root, text="", font=(_BODY, 8, "bold"), bg=BG, fg=GREEN, anchor="w")
    status["lbl"].pack(fill="x", padx=16, pady=(6, 0))
    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True, padx=16, pady=(4, 12))
    left = tk.Frame(body, bg=BG)
    left.pack(side="left", fill="both", expand=True)
    right = tk.Frame(body, bg=BG, width=380)
    right.pack(side="right", fill="y", padx=(10, 0))
    right.pack_propagate(False)

    # this PC
    pc = _card(left, _tx("pc", lang))
    st = _app_settings(app)
    row = tk.Frame(pc, bg=PANEL)
    row.pack(fill="x", padx=12, pady=(0, 4))
    tk.Label(row, text=_tx("name", lang), font=(_BODY, 9), bg=PANEL, fg=MUTED, width=10, anchor="w").pack(side="left")
    var = tk.StringVar(value=st.get("pc_nickname", ""))
    ent = tk.Entry(row, textvariable=var, font=(_BODY, 10), bg=PANEL2, fg=TEXT, insertbackground=TEXT,
                   relief="flat", width=28, highlightthickness=1, highlightbackground=LINE,
                   highlightcolor=VIOLET)
    ent.pack(side="left", ipady=3)
    if not var.get():
        ent.insert(0, "")
    msg = tk.Label(row, text="", font=(_BODY, 8), bg=PANEL, fg=GREEN)

    def _save_name(e=None):
        try:
            from utils.prefs_io import update_json
            update_json(app._app_settings_file(), pc_nickname=var.get().strip()[:40])
            msg.config(text=_tx("saved", lang))
        except Exception:
            pass
    sv = tk.Label(row, text=_tx("save", lang), font=(_BODY, 8, "bold"), bg="#2a2244", fg="#ffffff",
                  padx=10, pady=3, cursor="hand2")
    sv.pack(side="left", padx=(8, 0))
    sv.bind("<Button-1>", _save_name)
    ent.bind("<Return>", _save_name)
    msg.pack(side="left", padx=8)
    tk.Label(pc, text=_tx("name_hint", lang), font=(_BODY, 7), bg=PANEL, fg=DIM, anchor="w").pack(fill="x", padx=12 + 90)
    try:
        from core.machine_type import get as _mt
        kind = _mt()
    except Exception:
        kind = None
    _line(pc, _tx("kind", lang), _tx(kind if kind in ("desktop", "laptop") else "unknown", lang))
    try:
        _line(pc, "CPU", app._cpu_marketing_name())
        _line(pc, "GPU", app._gpu_name_nonblocking())
    except Exception:
        pass
    tk.Frame(pc, bg=PANEL, height=8).pack()

    since = _card(left, _tx("since", lang))
    grid = tk.Frame(since, bg=PANEL)
    grid.pack(fill="x", padx=12, pady=(0, 10))
    tk.Label(since, text="…", bg=PANEL, fg=MUTED)
    miles = _card(right, _tx("miles", lang))

    priv = _card(right, _tx("privacy", lang))
    try:
        from core.network import telemetry_enabled, network_allowed
        on = telemetry_enabled() and network_allowed()
    except Exception:
        on = False
    tk.Label(priv, text=_tx("tel_on" if on else "tel_off", lang), font=(_BODY, 8), bg=PANEL, fg=TEXT,
             anchor="w", justify="left", wraplength=350).pack(fill="x", padx=12)
    tk.Label(priv, text=_tx("delete", lang), font=(_BODY, 8), bg=PANEL, fg=MUTED, anchor="w",
             justify="left", wraplength=350).pack(fill="x", padx=12, pady=(6, 10))

    box = _Box()
    threading.Thread(target=_work, args=(box,), daemon=True, name="profile").start()

    def _poll():
        try:
            if not root.winfo_exists():
                return
        except Exception:
            return
        if box.data is None:
            root.after(150, _poll)
            return
        s = box.data
        items = [(f"{s['hours']:.0f}", "hours"), (str(s["games"]), "games"),
                 (f"{s['game_hours']:.0f}", "game_hours"), (str(s["recordings"]), "recordings"),
                 (str(s["flushes"]), "flushes"), (str(s["cleanups"]), "cleanups")]
        for i, (val, key) in enumerate(items):
            cell = tk.Frame(grid, bg=PANEL2)
            cell.grid(row=i // 3, column=i % 3, sticky="nsew", padx=(0, 6), pady=3)
            grid.columnconfigure(i % 3, weight=1)
            tk.Label(cell, text=val, font=(_HDR, 18, "bold"), bg=PANEL2, fg=TEXT, anchor="w").pack(fill="x", padx=10, pady=(6, 0))
            tk.Label(cell, text=_tx(key, lang), font=(_BODY, 8), bg=PANEL2, fg=MUTED, anchor="w").pack(fill="x", padx=10, pady=(0, 6))
        if s.get("since"):
            tk.Label(since, text=_tx("learning", lang, s=s["since"]), font=(_BODY, 8), bg=PANEL, fg=MUTED,
                     anchor="w").pack(fill="x", padx=12, pady=(0, 10))
        for key, earned in milestones(s):
            r = tk.Frame(miles, bg=PANEL)
            r.pack(fill="x", padx=12, pady=1)
            tk.Label(r, text="★" if earned else "☆", font=(_BODY, 11), bg=PANEL,
                     fg="#fbbf24" if earned else DIM).pack(side="left")
            tk.Label(r, text=_tx(key, lang), font=(_BODY, 9, "bold" if earned else "normal"), bg=PANEL,
                     fg=TEXT if earned else DIM).pack(side="left", padx=(6, 0))
        tk.Frame(miles, bg=PANEL, height=8).pack()
    _poll()
    return root


def _card(parent, title):
    f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
    f.pack(fill="x", pady=(0, 8))
    tk.Label(f, text=title, font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED, anchor="w").pack(fill="x", padx=12, pady=(8, 6))
    return f


def _line(parent, cap, val):
    r = tk.Frame(parent, bg=PANEL)
    r.pack(fill="x", padx=12, pady=1)
    tk.Label(r, text=cap, font=(_BODY, 9), bg=PANEL, fg=MUTED, width=10, anchor="w").pack(side="left")
    tk.Label(r, text=val or "-", font=(_BODY, 9), bg=PANEL, fg=TEXT, anchor="w").pack(side="left")
