import tkinter as tk
import subprocess
import threading
import os
import json
import tempfile
import time
import math

try:
    from utils.fonts import UI as _F, MONO as _M
except Exception:
    _F, _M = "Segoe UI", "Consolas"

BG      = "#080b10"
CARD    = "#0e1118"
SURFACE = "#111520"
BORDER  = "#181d2e"
LINE    = "#141826"
TEXT    = "#c4cfdf"
MUTED   = "#3d4a60"
DIM     = "#1e2838"
AMBER   = "#f59e0b"
EMERALD = "#10b981"
VIOLET  = "#8b5cf6"
BLUE    = "#3b82f6"
RED     = "#ef4444"

_TOTAL = 14

_PREFS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "settings", "user_prefs.json")
)

def _load_prefs():
    try:
        with open(_PREFS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_opt(**kw):
    try:
        p = _load_prefs()
        o = p.get("optimization", {})
        o.update(kw)
        p["optimization"] = o
        with open(_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)
    except Exception:
        pass

_RAM = {
    "active": False, "stop_flag": False,
    "threshold": 75, "consecutive_high": 0,
    "result_lbl": None, "prog_lbl": None,
    "run_cv": None, "run_draw": None,
}

_ACTION_BTNS: dict = {}

def _init():
    o = _load_prefs().get("optimization", {})
    _RAM["active"]    = bool(o.get("ram_auto", False))
    _RAM["threshold"] = int(o.get("ram_threshold", 75))

_init()


def build_optimization_page(self, parent):
    root_frame = tk.Frame(parent, bg=BG)
    root_frame.pack(fill="both", expand=True)

    _build_hero_header(root_frame)

    cv  = tk.Canvas(root_frame, bg=BG, highlightthickness=0)
    sb  = tk.Scrollbar(root_frame, orient="vertical", command=cv.yview,
                       bg=BG, troughcolor=BG, activebackground=BORDER, width=4)
    sf  = tk.Frame(cv, bg=BG)
    sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
    wid = cv.create_window((0, 0), window=sf, anchor="nw")
    cv.configure(yscrollcommand=sb.set)
    cv.bind("<Configure>", lambda e: cv.itemconfig(wid, width=e.width - 2))

    def _mw(ev):
        try:
            if cv.winfo_exists():
                cv.yview_scroll(int(-1 * (ev.delta / 120)), "units")
        except Exception:
            pass
    cv.bind_all("<MouseWheel>", _mw, add="+")

    sb.pack(side="right", fill="y")
    cv.pack(side="left", fill="both", expand=True)

    _build_snapshot_strip(sf)
    _build_body(sf)


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def _hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"

def _sep(parent, color=LINE):
    tk.Frame(parent, bg=color, height=1).pack(fill="x")

def _ico_power(c, s):
    c.create_arc(2, 3, s-2, s-1, start=50, extent=260,
                 style="arc", outline=AMBER, width=2)
    c.create_line(s//2, 1, s//2, s//2+1, fill=AMBER, width=2)

def _ico_globe(c, s):
    c.create_oval(1, 1, s-1, s-1, outline=BLUE, width=1)
    c.create_line(2, s//2, s-2, s//2, fill=BLUE, width=1)
    c.create_line(3, s//3, s-3, s//3, fill=BLUE, width=1)
    c.create_line(3, s*2//3, s-3, s*2//3, fill=BLUE, width=1)

def _ico_trash(c, s):
    c.create_rectangle(2, 4, s-2, s-1, outline=RED, width=1)
    c.create_line(0, 4, s, 4, fill=RED, width=1)
    c.create_rectangle(s//2-2, 1, s//2+2, 4, outline=RED, width=1)
    for lx in [5, s-5]:
        c.create_line(lx, 6, lx, s-2, fill=RED, width=1)

def _ico_arrow(c, s):
    mid = s // 2
    c.create_polygon(mid, 1, s-1, s//2+1, s*3//4, s//2+1,
                     s*3//4, s-1, s//4, s-1, s//4, s//2+1,
                     1, s//2+1, fill=EMERALD, outline="")

def _ico_ram(c, s):
    c.create_rectangle(1, 4, s-1, s-4, outline=VIOLET, width=1)
    for x in [4, 7, 10]:
        if x < s - 2:
            c.create_line(x, 4, x, 1, fill=VIOLET, width=1)
            c.create_line(x, s-4, x, s-1, fill=VIOLET, width=1)

def _icv(parent, fn, bg=CARD, size=13):
    c = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0)
    fn(c, size)
    return c

def _pill_cv(c, active, W, H):
    c.delete("all")
    r = H // 2
    track = EMERALD if active else "#1a2030"
    c.create_arc(0, 0, H, H, start=90, extent=180, fill=track, outline="")
    c.create_arc(W-H, 0, W, H, start=-90, extent=180, fill=track, outline="")
    c.create_rectangle(r, 0, W-r, H, fill=track, outline="")
    m = 2
    tx = W - H + m if active else m
    c.create_oval(tx, m, tx+H-2*m, H-m, fill="#ffffff", outline="")

def _section_label(parent, text):
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x")
    tk.Label(row, text=text, font=(_F, 6, "bold"), bg=BG, fg=MUTED).pack(side="left")
    tk.Frame(row, bg=LINE, height=1).pack(side="left", fill="x", expand=True, padx=8)


def _build_hero_header(parent):
    HH = "#0b0f18"
    h = tk.Frame(parent, bg=HH, height=72)
    h.pack(fill="x")
    h.pack_propagate(False)

    inner = tk.Frame(h, bg=HH)
    inner.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)

    # ── Left: title + subtitle ─────────────────────────────────────
    title_col = tk.Frame(inner, bg=HH)
    title_col.pack(side="left", fill="both", expand=True, padx=(18, 0), pady=10)
    tk.Label(title_col, text="OPTIMIZATION CENTER",
             font=(_F, 13, "bold"), bg=HH, fg=TEXT, anchor="w").pack(anchor="w")
    tk.Label(title_col, text="Automated boost, cleanup & performance maintenance",
             font=(_F, 7), bg=HH, fg=MUTED, anchor="w").pack(anchor="w", pady=(1, 0))

    # ── Right: 1/14 badge ─────────────────────────────────────────
    badge_col = tk.Frame(inner, bg=HH)
    badge_col.pack(side="right", padx=(10, 18), pady=10)

    box = tk.Frame(badge_col, bg="#0a1a14",
                   highlightbackground=EMERALD, highlightthickness=1)
    box.pack()
    num_row = tk.Frame(box, bg="#0a1a14")
    num_row.pack(padx=14, pady=(7, 0))
    tk.Label(num_row, text="1",
             font=(_M, 24, "bold"), bg="#0a1a14", fg=EMERALD).pack(side="left")
    tk.Label(num_row, text=f" /{_TOTAL}",
             font=(_M, 12), bg="#0a1a14", fg=MUTED).pack(side="left", anchor="s", pady=(5, 0))
    tk.Label(box, text="active",
             font=(_F, 6), bg="#0a1a14", fg=MUTED, pady=3).pack()

    # ── Middle: TURBO BOOST button ────────────────────────────────
    turbo_col = tk.Frame(inner, bg=HH)
    turbo_col.pack(side="right", padx=(0, 14), pady=12)

    turbo_cv = tk.Canvas(turbo_col, width=200, height=48,
                         bg=HH, highlightthickness=0, cursor="hand2")
    turbo_cv.pack()

    _phase   = [0.0]
    _running = [False]

    def _draw_turbo(bright=1.0):
        turbo_cv.delete("all")
        W, H_btn = 200, 48
        b = (1.0 + 0.07 * math.sin(_phase[0])) if _running[0] else bright
        for x in range(0, W, 2):
            r, g, bb = _lerp((140, 62, 4), (210, 155, 8), x / max(W-1, 1))
            turbo_cv.create_rectangle(
                x, 0, x+2, H_btn,
                fill=_hex(min(255, int(r*b)), min(255, int(g*b)), min(255, int(bb*b))),
                outline="")
        turbo_cv.create_text(W//2, H_btn//2,
                             text="TURBO  BOOST",
                             font=(_F, 9, "bold"), fill="#000000")

    def _pulse():
        if not _running[0]:
            return
        _phase[0] += 0.12
        _draw_turbo()
        turbo_cv.after(50, _pulse)

    turbo_cv.bind("<Configure>", lambda e: _draw_turbo())
    turbo_cv.bind("<Enter>",     lambda e: _draw_turbo(1.18) if not _running[0] else None)
    turbo_cv.bind("<Leave>",     lambda e: _draw_turbo(1.0)  if not _running[0] else None)
    turbo_cv.after(60, lambda: _draw_turbo())

    _action_order = [
        (_set_high_performance, "power"),
        (_flush_dns,            "dns"),
        (_clear_temp,           "temp"),
        (_boost_priority,       "priority"),
    ]

    def _flash_btn(key, ok):
        entry = _ACTION_BTNS.get(key)
        if not entry:
            return
        btn, base_col = entry
        c2 = EMERALD if ok else RED
        bg2 = "#0a1a10" if ok else "#1a0a0a"
        if btn.winfo_exists():
            btn.config(fg=c2, highlightbackground=c2, bg=bg2)
        btn.after(2500, lambda: btn.config(
            fg=base_col, highlightbackground=base_col, bg=CARD)
            if btn.winfo_exists() else None)

    def _on_turbo(e=None):
        if _running[0]:
            return
        _running[0] = True
        _pulse()
        for _, key in _action_order:
            entry = _ACTION_BTNS.get(key)
            if entry:
                btn, _ = entry
                if btn.winfo_exists():
                    btn.after(0, lambda b=btn: b.config(
                        text="...", fg=MUTED, highlightbackground=BORDER, bg=CARD))
        def _bg():
            for func, key in _action_order:
                ok, _ = func()
                if turbo_cv.winfo_exists():
                    turbo_cv.after(0, lambda k=key, o=ok: _flash_btn(k, o))
            _running[0] = False
            if turbo_cv.winfo_exists():
                turbo_cv.after(0, lambda: _draw_turbo(1.0))
        threading.Thread(target=_bg, daemon=True).start()

    turbo_cv.bind("<Button-1>", _on_turbo)

    # ── Gradient accent line ──────────────────────────────────────
    grad_cv = tk.Canvas(parent, height=3, bg=BG, highlightthickness=0)
    grad_cv.pack(fill="x")

    def _draw_grad(e=None):
        grad_cv.delete("all")
        w = grad_cv.winfo_width() or 900
        half = w // 2
        for x in range(half):
            r, g, b = _lerp((8, 11, 16), (245, 158, 11), x / max(half-1, 1))
            grad_cv.create_line(x, 0, x, 3, fill=_hex(r, g, b))
        for x in range(half, w):
            r, g, b = _lerp((245, 158, 11), (8, 11, 16), (x-half) / max(w-half-1, 1))
            grad_cv.create_line(x, 0, x, 3, fill=_hex(r, g, b))

    grad_cv.bind("<Configure>", _draw_grad)


def _build_snapshot_strip(parent):
    outer = tk.Frame(parent, bg=SURFACE)
    outer.pack(fill="x", padx=12, pady=(10, 0))

    hdr = tk.Frame(outer, bg=SURFACE)
    hdr.pack(fill="x", padx=10, pady=(6, 3))
    tk.Label(hdr, text="SYSTEM  SNAPSHOT",
             font=(_F, 6, "bold"), bg=SURFACE, fg=MUTED).pack(side="left")
    tk.Frame(hdr, bg=LINE, height=1).pack(side="left", fill="x", expand=True, padx=8)

    row = tk.Frame(outer, bg=SURFACE)
    row.pack(fill="x", padx=10, pady=(0, 8))

    cells = {}
    for key, title, color in [
        ("power_plan", "Power Plan",    AMBER),
        ("temp_size",  "TEMP Folder",   RED),
        ("ram_pct",    "RAM",           BLUE),
        ("startup",    "Startup Items", "#6b7280"),
    ]:
        cell = tk.Frame(row, bg="#090d15",
                        highlightbackground=BORDER, highlightthickness=1)
        cell.pack(side="left", fill="both", expand=True, padx=3)
        tk.Frame(cell, bg=color, height=2).pack(fill="x")
        tk.Label(cell, text=title,
                 font=(_F, 5, "bold"), bg="#090d15", fg=MUTED).pack(pady=(5, 0))
        val = tk.Label(cell, text="—",
                       font=(_M, 9, "bold"), bg="#090d15", fg=color)
        val.pack()
        sub = tk.Label(cell, text=" ",
                       font=(_F, 5), bg="#090d15", fg=DIM, pady=3)
        sub.pack()
        cells[key] = (val, sub)

    def _load():
        res = {}
        try:
            r = subprocess.run(["powercfg", "/getactivescheme"],
                               capture_output=True, text=True, timeout=4)
            ln = r.stdout.strip()
            name = ln[ln.rfind("(")+1:ln.rfind(")")] if "(" in ln else "Unknown"
            ok = "High Performance" in name or "Ultimate" in name
            res["power_plan"] = (name[:13], "ok" if ok else "needs fix",
                                 EMERALD if ok else AMBER)
        except Exception:
            res["power_plan"] = ("N/A", "", MUTED)
        try:
            total = sum(e.stat().st_size for e in os.scandir(tempfile.gettempdir())
                        if e.is_file(follow_symlinks=False))
            mb = total / 1048576
            col = RED if mb > 500 else AMBER if mb > 100 else EMERALD
            res["temp_size"] = (f"{mb:.0f} MB",
                                "clear recommended" if mb > 100 else "clean", col)
        except Exception:
            res["temp_size"] = ("N/A", "", MUTED)
        try:
            import psutil
            pct = psutil.virtual_memory().percent
            col = RED if pct >= 85 else AMBER if pct >= 70 else EMERALD
            res["ram_pct"] = (f"{pct:.0f}%", "high" if pct >= 70 else "ok", col)
        except Exception:
            res["ram_pct"] = ("N/A", "", MUTED)
        try:
            import winreg
            count = 0
            for hive, path in [
                (winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]:
                try:
                    k = winreg.OpenKey(hive, path)
                    i = 0
                    while True:
                        try: winreg.EnumValue(k, i); count += 1; i += 1
                        except OSError: break
                    winreg.CloseKey(k)
                except Exception:
                    pass
            col = RED if count > 12 else AMBER if count > 8 else EMERALD
            res["startup"] = (str(count), "items", col)
        except Exception:
            res["startup"] = ("N/A", "", MUTED)
        for key, (vl, sl) in cells.items():
            if key in res:
                txt, sub, col = res[key]
                if vl.winfo_exists():
                    vl.after(0, lambda v=vl, t=txt, c=col: v.config(text=t, fg=c))
                if sl.winfo_exists():
                    sl.after(0, lambda s=sl, t=sub: s.config(text=t))

    threading.Thread(target=_load, daemon=True).start()


def _build_body(parent):
    body = tk.Frame(parent, bg=BG)
    body.pack(fill="both", expand=True, padx=12, pady=(10, 12))

    # LEFT: Quick Actions — narrow, fixed
    left = tk.Frame(body, bg=BG, width=280)
    left.pack(side="left", fill="y", padx=(0, 8))
    left.pack_propagate(False)

    # RIGHT: Features list — expands
    right = tk.Frame(body, bg=BG)
    right.pack(side="left", fill="both", expand=True)

    _build_quick_actions(left)
    _build_features_list(right)


def _build_quick_actions(parent):
    _section_label(parent, "QUICK  ACTIONS")

    wrap = tk.Frame(parent, bg=CARD,
                    highlightbackground=BORDER, highlightthickness=1)
    wrap.pack(fill="x", pady=(4, 0))

    status_lbl = tk.Label(wrap, text=" ",
                          font=(_M, 5), bg=SURFACE, fg=MUTED,
                          pady=3, padx=8, anchor="w")
    status_lbl.pack(fill="x")
    _sep(wrap, BORDER)

    actions = [
        ("power",    _ico_power, "High Performance Plan", AMBER,   _set_high_performance),
        ("dns",      _ico_globe, "Flush DNS Cache",        BLUE,    _flush_dns),
        ("temp",     _ico_trash, "Clear TEMP Files",       RED,     _clear_temp),
        ("priority", _ico_arrow, "Boost App Priority",     EMERALD, _boost_priority),
    ]

    for i, (key, fn, name, color, func) in enumerate(actions):
        if i > 0:
            _sep(wrap, LINE)

        row = tk.Frame(wrap, bg=CARD)
        row.pack(fill="x")

        tk.Frame(row, bg=color, width=2).pack(side="left", fill="y")
        _icv(row, fn, bg=CARD, size=12).pack(side="left", padx=(9, 6), pady=10)
        tk.Label(row, text=name, font=(_F, 7),
                 bg=CARD, fg="#7a8fa8", anchor="w").pack(side="left", fill="x", expand=True)

        btn = tk.Label(row, text="RUN", font=(_M, 6, "bold"),
                       bg=CARD, fg=color, cursor="hand2",
                       padx=9, pady=3,
                       highlightbackground=color, highlightthickness=1)
        btn.pack(side="right", padx=8, pady=6)

        _ACTION_BTNS[key] = (btn, color)

        def _mk(f, b, col):
            def _h(e=None):
                b.config(text="...", fg=MUTED, highlightbackground=BORDER, bg=CARD)
                def _run():
                    ok, msg = f()
                    t2, c2 = ("DONE", EMERALD) if ok else ("FAIL", RED)
                    bg2 = "#0a1a10" if ok else "#1a0a0a"
                    if b.winfo_exists():
                        b.after(0, lambda: b.config(
                            text=t2, fg=c2, highlightbackground=c2, bg=bg2))
                    if status_lbl.winfo_exists():
                        status_lbl.after(0, lambda: status_lbl.config(text=msg))
                    time.sleep(3)
                    if b.winfo_exists():
                        b.after(0, lambda: b.config(
                            text="RUN", fg=col, highlightbackground=col, bg=CARD))
                threading.Thread(target=_run, daemon=True).start()
            return _h

        btn.bind("<Button-1>", _mk(func, btn, color))
        btn.bind("<Enter>", lambda e, b=btn: b.config(fg="#ffffff"))
        btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(fg=c))

    _sep(wrap, LINE)
    tk.Label(wrap, text="All 4 actions run on  TURBO BOOST",
             font=(_F, 6), bg=CARD, fg=DIM, pady=5).pack()


def _build_features_list(parent):
    hdr_row = tk.Frame(parent, bg=BG)
    hdr_row.pack(fill="x")
    tk.Label(hdr_row, text="FEATURES",
             font=(_F, 6, "bold"), bg=BG, fg=MUTED).pack(side="left")
    tk.Frame(hdr_row, bg=LINE, height=1).pack(
        side="left", fill="x", expand=True, padx=8)
    tk.Label(hdr_row, text="1  /  14  active",
             font=(_M, 6), bg=BG, fg=DIM).pack(side="right")

    wrap = tk.Frame(parent, bg=CARD,
                    highlightbackground=BORDER, highlightthickness=1)
    wrap.pack(fill="both", expand=True, pady=(4, 0))

    _build_ram_flush_card(wrap)

    for name, color in [
        ("CPU Thermal Throttle Prevention",  AMBER),
        ("Browser Cache Auto-Cleaner",       BLUE),
        ("Startup Optimizer",                EMERALD),
        ("Background Process Limiter",       VIOLET),
        ("Disk Fragmentation Monitor",       "#6b7280"),
        ("Network Adapter Reset",            BLUE),
        ("Registry Junk Cleaner",            RED),
        ("GPU Driver Health Watchdog",       AMBER),
        ("Log File Rotation",                "#6b7280"),
        ("DNS Auto-Flush (nightly)",         BLUE),
        ("Weekly Performance Report",        EMERALD),
        ("Windows Update Checker",           AMBER),
        ("Firewall Health Monitor",          RED),
    ]:
        _sep(wrap)
        row = tk.Frame(wrap, bg=CARD)
        row.pack(fill="x")
        tk.Frame(row, bg=color, width=2).pack(side="left", fill="y")
        dot = tk.Canvas(row, width=5, height=5, bg=CARD, highlightthickness=0)
        dot.pack(side="left", padx=(8, 5), pady=9)
        dot.create_oval(0, 0, 5, 5, fill=color, outline="", stipple="gray25")
        tk.Label(row, text=name, font=(_F, 7),
                 bg=CARD, fg=DIM, anchor="w").pack(side="left", fill="x", expand=True)
        ph = tk.Canvas(row, width=24, height=12, bg=CARD, highlightthickness=0)
        ph.pack(side="right", padx=(0, 8))
        _pill_cv(ph, False, 24, 12)
        tk.Label(row, text="SOON", font=(_M, 5, "bold"),
                 bg=CARD, fg="#141d28").pack(side="right")


def _build_ram_flush_card(parent):
    card = tk.Frame(parent, bg="#0d1220",
                    highlightbackground="#1a2640", highlightthickness=1)
    card.pack(fill="x", padx=6, pady=6)
    tk.Frame(card, bg=VIOLET, height=2).pack(fill="x")

    inner = tk.Frame(card, bg="#0d1220")
    inner.pack(fill="x", padx=10, pady=6)

    # Top row: icon + title + description
    top = tk.Frame(inner, bg="#0d1220")
    top.pack(fill="x")
    _icv(top, _ico_ram, bg="#0d1220", size=13).pack(side="left", padx=(0, 7))
    t = tk.Frame(top, bg="#0d1220")
    t.pack(side="left", fill="both", expand=True)
    tk.Label(t, text="Auto RAM Flush",
             font=(_F, 8, "bold"), bg="#0d1220", fg=TEXT, anchor="w").pack(anchor="w")
    tk.Label(t, text=f"Triggers when RAM > {_RAM['threshold']}%  for 30s",
             font=(_F, 6), bg="#0d1220", fg=MUTED, anchor="w").pack(anchor="w")

    # Bottom row: status + RUN + AUTO
    ctrl = tk.Frame(inner, bg="#0d1220")
    ctrl.pack(fill="x", pady=(5, 0))

    result_lbl = tk.Label(ctrl, text="",
                          font=(_M, 6), bg="#0d1220", fg=MUTED, anchor="w")
    result_lbl.pack(side="left", fill="x", expand=True)
    prog_lbl = tk.Label(ctrl, text="",
                        font=(_M, 5), bg="#0d1220", fg=DIM)
    _RAM["result_lbl"] = result_lbl
    _RAM["prog_lbl"]   = prog_lbl

    # AUTO toggle
    auto_wrap = tk.Frame(ctrl, bg="#0d1220")
    auto_wrap.pack(side="right", padx=(8, 0))
    a_sub = tk.Label(auto_wrap, text="AUTO",
                     font=(_F, 5, "bold"), bg="#0d1220", fg=MUTED)
    a_sub.pack(side="left", padx=(0, 4))
    a_pill = tk.Canvas(auto_wrap, width=34, height=16,
                       bg="#0d1220", highlightthickness=0, cursor="hand2")
    a_pill.pack(side="left")

    # Gradient RUN button
    run_cv = tk.Canvas(ctrl, width=72, height=28,
                       bg="#0d1220", highlightthickness=0, cursor="hand2")
    run_cv.pack(side="right", padx=(0, 8))
    _RAM["run_cv"] = run_cv

    def _draw_run(state="idle"):
        run_cv.delete("all")
        W, H = 72, 28
        if state == "done":
            run_cv.create_rectangle(0, 0, W, H, fill=EMERALD, outline="")
            run_cv.create_text(W//2, H//2, text="DONE",
                               font=(_F, 7, "bold"), fill="#000000")
        elif state == "running":
            run_cv.create_rectangle(0, 0, W, H, fill="#1a2030", outline="")
            run_cv.create_text(W//2, H//2, text="FLUSH",
                               font=(_F, 7, "bold"), fill=MUTED)
        else:
            for x in range(0, W, 2):
                r, g, b = _lerp((107, 18, 18), (16, 185, 129), x / max(W-1, 1))
                run_cv.create_rectangle(x, 0, x+2, H,
                                        fill=_hex(r, g, b), outline="")
            run_cv.create_text(W//2, H//2, text="FLUSH  RAM",
                               font=(_F, 7, "bold"), fill="#ffffff")

    _RAM["run_draw"] = _draw_run
    run_cv.after(60, lambda: _draw_run("idle"))

    def _on_run(e=None):
        _draw_run("running")
        def _bg():
            ok, msg, before, after = _do_ram_flush()
            freed = after - before
            d = f"Freed {freed} MB  ({before}→{after} MB)" if freed > 0 else msg
            if result_lbl.winfo_exists():
                result_lbl.after(0, lambda: result_lbl.config(text=d))
            if run_cv.winfo_exists():
                run_cv.after(0, lambda: _draw_run("done"))
            time.sleep(3)
            if run_cv.winfo_exists():
                run_cv.after(0, lambda: _draw_run("idle"))
        threading.Thread(target=_bg, daemon=True).start()

    run_cv.bind("<Button-1>", _on_run)

    def _toggle_auto(e=None):
        _RAM["active"] = not _RAM["active"]
        act = _RAM["active"]
        _pill_cv(a_pill, act, 34, 16)
        _save_opt(ram_auto=act, ram_threshold=_RAM["threshold"])
        if act:
            a_sub.config(text="AUTO  ●", fg=EMERALD)
            _RAM["stop_flag"] = False
            _RAM["consecutive_high"] = 0
            threading.Thread(
                target=_ram_monitor_loop,
                args=(result_lbl, prog_lbl, run_cv, _draw_run),
                daemon=True
            ).start()
        else:
            _RAM["stop_flag"] = True
            _RAM["consecutive_high"] = 0
            a_sub.config(text="AUTO", fg=MUTED)
            result_lbl.config(text="")

    a_pill.bind("<Button-1>", _toggle_auto)
    _pill_cv(a_pill, _RAM["active"], 34, 16)
    if _RAM["active"]:
        a_sub.config(text="AUTO  ●", fg=EMERALD)
        _RAM["stop_flag"] = False
        threading.Thread(
            target=_ram_monitor_loop,
            args=(result_lbl, prog_lbl, run_cv, _draw_run),
            daemon=True
        ).start()


def _do_ram_flush():
    import psutil, ctypes
    before = int(psutil.virtual_memory().available / 1048576)
    try:
        cmd = ctypes.c_int(4)
        ctypes.windll.ntdll.NtSetSystemInformation(
            80, ctypes.byref(cmd), ctypes.sizeof(cmd))
    except Exception:
        pass
    try:
        ctypes.windll.kernel32.SetSystemFileCacheSize(
            ctypes.c_size_t(0xFFFFFFFF), ctypes.c_size_t(0xFFFFFFFF), 0)
    except Exception:
        pass
    count = 0
    try:
        for proc in psutil.process_iter(["pid"]):
            pid = proc.pid
            if pid <= 4:
                continue
            try:
                h = ctypes.windll.kernel32.OpenProcess(0x0100 | 0x0400, False, pid)
                if h:
                    ctypes.windll.psapi.EmptyWorkingSet(h)
                    ctypes.windll.kernel32.CloseHandle(h)
                    count += 1
            except Exception:
                pass
    except Exception:
        pass
    time.sleep(0.8)
    after = int(psutil.virtual_memory().available / 1048576)
    freed = after - before
    if freed > 0:
        return True, f"Freed {freed} MB  ({count} procs)", before, after
    elif count > 0:
        return True, f"Flushed {count} procs (limited perms)", before, after
    return False, "No effect — admin rights needed", before, after


def _ram_monitor_loop(result_lbl, prog_lbl, run_cv, draw_run):
    import psutil
    TRIGGER, STEP = 30, 10
    while not _RAM["stop_flag"]:
        try:
            pct = psutil.virtual_memory().percent
            if pct > _RAM["threshold"]:
                _RAM["consecutive_high"] = min(_RAM["consecutive_high"] + STEP, TRIGGER)
                s = _RAM["consecutive_high"]
                if prog_lbl.winfo_exists():
                    prog_lbl.after(0, lambda v=s: prog_lbl.config(
                        text=f"high: {v}s/{TRIGGER}s", fg=AMBER))
                if _RAM["consecutive_high"] >= TRIGGER:
                    _RAM["consecutive_high"] = 0
                    if run_cv.winfo_exists():
                        run_cv.after(0, lambda: draw_run("running"))
                    ok, msg, before, after = _do_ram_flush()
                    freed = after - before
                    d = f"AUTO: freed {freed} MB" if freed > 0 else f"AUTO: {msg}"
                    if result_lbl.winfo_exists():
                        result_lbl.after(0, lambda v=d: result_lbl.config(text=v))
                    if prog_lbl.winfo_exists():
                        prog_lbl.after(0, lambda: prog_lbl.config(text="", fg=DIM))
                    if run_cv.winfo_exists():
                        run_cv.after(0, lambda: draw_run("done"))
                    time.sleep(3)
                    if run_cv.winfo_exists():
                        run_cv.after(0, lambda: draw_run("idle"))
            else:
                if _RAM["consecutive_high"] > 0:
                    _RAM["consecutive_high"] = 0
                    if prog_lbl.winfo_exists():
                        prog_lbl.after(0, lambda: prog_lbl.config(text="", fg=DIM))
        except Exception:
            pass
        time.sleep(STEP)


def _set_high_performance():
    try:
        r = subprocess.run(
            ["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
            capture_output=True, text=True, timeout=5)
        return (True, "High Performance plan activated.") if r.returncode == 0 \
               else (False, f"powercfg: {r.stderr.strip()[:50]}")
    except Exception as ex:
        return False, str(ex)[:50]

def _flush_dns():
    try:
        r = subprocess.run(["ipconfig", "/flushdns"],
                           capture_output=True, text=True, timeout=5)
        return (True, "DNS cache flushed.") if r.returncode == 0 \
               else (False, f"ipconfig: {r.stderr.strip()[:50]}")
    except Exception as ex:
        return False, str(ex)[:50]

def _clear_temp():
    import shutil
    removed = 0
    try:
        for name in os.listdir(tempfile.gettempdir()):
            path = os.path.join(tempfile.gettempdir(), name)
            try:
                if os.path.isfile(path):
                    os.unlink(path); removed += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True); removed += 1
            except Exception:
                pass
        return True, f"Cleared {removed} temp items."
    except Exception as ex:
        return False, str(ex)[:50]

def _boost_priority():
    try:
        import psutil, ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        fg = pid.value
        if fg and fg > 4:
            proc = psutil.Process(fg)
            proc.nice(psutil.HIGH_PRIORITY_CLASS)
            return True, f"Boosted: {proc.name()[:20]} (PID {fg})"
        return False, "No foreground process."
    except Exception as ex:
        return False, str(ex)[:50]
