# ui/pages/first_setup_drivers.py
"""
FIRST SETUP & DRIVERS
Real-time driver health, system readiness score, startup manager, setup checklist.
Data sourced from Windows registry — no admin rights required for reads.
"""

import tkinter as tk
import threading
import time
import os
import json
import subprocess
from datetime import datetime, date

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    psutil = None
    _HAS_PSUTIL = False

try:
    import winreg
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False

# ─── Palette ──────────────────────────────────────────────────────────────────
BG     = "#0a0e14"
PANEL  = "#111827"
PANEL2 = "#0d1117"
BORDER = "#1f2937"
TEXT   = "#e5e7eb"
MUTED  = "#6b7280"
BLUE   = "#3b82f6"
GREEN  = "#10b981"
AMBER  = "#f59e0b"
RED    = "#ef4444"
PURPLE = "#8b5cf6"

CHECKLIST_PATH = os.path.join("data", "cache", "setup_checklist.json")

# ─── Checklist definition ─────────────────────────────────────────────────────
_CHECKLIST = [
    ("windows_update",  "Windows Update checked"),
    ("antivirus",       "Antivirus active"),
    ("gpu_driver",      "GPU driver verified"),
    ("startup",         "Startup programs reviewed"),
    ("privacy",         "Privacy settings tuned"),
    ("disk_smart",      "Disk health checked"),
]

# ─── Skip keywords for virtual/software adapters ─────────────────────────────
_SKIP = ("virtual", "software", "tunnel", "loopback", "wan miniport",
         "microsoft kernel", "ndis", "teredo", "isatap", "6to4", "tap-")


# ─── Utilities ────────────────────────────────────────────────────────────────
def _driver_age_days(date_str):
    if not date_str:
        return None
    try:
        s = date_str.replace("/", "-")
        parts = s.split("-")
        if len(parts) == 3:
            if len(parts[2]) == 4:          # MM-DD-YYYY (Windows registry)
                d = date(int(parts[2]), int(parts[0]), int(parts[1]))
            else:                            # YYYY-MM-DD (ISO)
                d = date(int(parts[0]), int(parts[1]), int(parts[2]))
            return max(0, (date.today() - d).days)
        if len(date_str) == 8 and date_str.isdigit():  # YYYYMMDD
            d = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:]))
            return max(0, (date.today() - d).days)
    except Exception:
        pass
    return None


def _age_info(days):
    """(status_text, fg, badge_bg, bar_color, card_border)"""
    if days is None:
        return "UNKNOWN",    MUTED,  "#1f2937", "#374151", BORDER
    if days < 180:
        return "CURRENT",    GREEN,  "#064e3b", GREEN,     "#065f46"
    if days < 365:
        return "6+ MONTHS",  AMBER,  "#451a03", AMBER,     "#78350f"
    mo = days // 30
    return f"{mo}mo OLD",    RED,    "#450a0a", RED,       "#7f1d1d"


def _score_color(score):
    return GREEN if score >= 80 else AMBER if score >= 55 else RED


def _score_grade(score):
    if score >= 85: return "EXCELLENT"
    if score >= 70: return "GOOD"
    if score >= 50: return "FAIR"
    return "NEEDS WORK"


def _fmt_date(date_str):
    """MM-DD-YYYY → 'Jan 2025'."""
    try:
        parts = date_str.replace("/", "-").split("-")
        if len(parts) == 3 and len(parts[2]) == 4:
            mon = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return f"{mon[int(parts[0])]} {parts[2]}"
    except Exception:
        pass
    return date_str[:10] if date_str else ""


def _lighten(hex_color, amount=22):
    try:
        r = min(255, int(hex_color[1:3], 16) + amount)
        g = min(255, int(hex_color[3:5], 16) + amount)
        b = min(255, int(hex_color[5:7], 16) + amount)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


# ─── Registry helpers ─────────────────────────────────────────────────────────
def _read_class_driver(guid):
    """Return first real driver dict from Windows device class GUID."""
    if not _HAS_WINREG:
        return None
    key_path = fr"SYSTEM\CurrentControlSet\Control\Class\{guid}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as cls:
            n = winreg.QueryInfoKey(cls)[0]
            for i in range(min(n, 24)):
                try:
                    sn = winreg.EnumKey(cls, i)
                    if not sn[:4].isdigit():
                        continue
                    with winreg.OpenKey(cls, sn) as dev:
                        try:
                            desc = winreg.QueryValueEx(dev, "DriverDesc")[0]
                        except OSError:
                            continue
                        if any(kw in desc.lower() for kw in _SKIP):
                            continue
                        ver, drv_date = "", ""
                        try:
                            ver = winreg.QueryValueEx(dev, "DriverVersion")[0]
                        except OSError:
                            pass
                        try:
                            drv_date = winreg.QueryValueEx(dev, "DriverDate")[0]
                        except OSError:
                            pass
                        return {"name": desc, "version": ver, "date": drv_date}
                except OSError:
                    continue
    except Exception:
        pass
    return None


def _get_windows_info():
    info = {"product": "Windows", "version_tag": "", "build": "", "install_ts": 0}
    if not _HAS_WINREG:
        return info
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
            def _v(n, d=""):
                try: return winreg.QueryValueEx(k, n)[0]
                except OSError: return d
            info["product"]     = _v("ProductName")
            info["version_tag"] = _v("DisplayVersion")
            info["build"]       = _v("CurrentBuildNumber")
            info["install_ts"]  = int(_v("InstallDate", 0) or 0)
    except Exception:
        pass
    return info


def _get_startup_programs():
    programs = []
    if not _HAS_WINREG:
        return programs
    paths = [
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",             "User"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",             "System"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "System"),
    ]
    seen = set()
    for hive, path, src in paths:
        try:
            with winreg.OpenKey(hive, path) as k:
                for i in range(min(winreg.QueryInfoKey(k)[1], 20)):
                    try:
                        name, val, _ = winreg.EnumValue(k, i)
                        if name in seen:
                            continue
                        seen.add(name)
                        exe = os.path.basename(val.strip().strip('"').split('"')[0])
                        programs.append({"name": name, "source": src, "exe": exe})
                    except OSError:
                        pass
        except OSError:
            pass
    return programs[:10]


def _compute_score(drivers, startup_count):
    score = 100
    for d in drivers:
        days = _driver_age_days(d.get("date", "") if d else "")
        if days is None:
            score -= 6
        elif days >= 365:
            score -= 20
        elif days >= 180:
            score -= 9
    if startup_count > 12:
        score -= 15
    elif startup_count > 8:
        score -= 8
    elif startup_count > 5:
        score -= 3
    return max(10, min(100, score))


# ─── Checklist persistence ────────────────────────────────────────────────────
def _load_checklist():
    try:
        if os.path.exists(CHECKLIST_PATH):
            with open(CHECKLIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_checklist(state):
    try:
        os.makedirs(os.path.dirname(CHECKLIST_PATH), exist_ok=True)
        with open(CHECKLIST_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass


# ─── Page entry point ─────────────────────────────────────────────────────────
def build_first_setup_page(win_self, parent):
    main = tk.Frame(parent, bg=BG)
    main.pack(fill="both", expand=True)

    # Scrollable canvas — width bound to canvas so content always fills
    wrap  = tk.Canvas(main, bg=BG, highlightthickness=0)
    vsb   = tk.Scrollbar(main, orient="vertical", command=wrap.yview,
                         bg="#000000", troughcolor=BG, width=8, bd=0)
    sf    = tk.Frame(wrap, bg=BG)
    sf.bind("<Configure>", lambda e: wrap.configure(scrollregion=wrap.bbox("all")))
    win_id = wrap.create_window((0, 0), window=sf, anchor="nw")
    wrap.configure(yscrollcommand=vsb.set)
    wrap.bind("<Configure>", lambda e: wrap.itemconfig(win_id, width=e.width - 2))

    def _wheel(ev):
        try:
            if wrap.winfo_exists():
                wrap.yview_scroll(int(-1 * (ev.delta / 120)), "units")
        except Exception:
            pass
    wrap.bind_all("<MouseWheel>", _wheel, add="+")

    wrap.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    refs = {}
    _build_header(sf, refs)
    _build_hero(sf, refs)
    _build_driver_section(sf, refs)
    _build_bottom_row(sf, refs)
    _build_checklist(sf)

    _start_pulse(refs)

    def _do_scan():
        gpu   = _read_class_driver("{4d36e968-e325-11ce-bfc1-08002be10318}")
        audio = _read_class_driver("{4d36e96c-e325-11ce-bfc1-08002be10318}")
        net   = _read_class_driver("{4d36e972-e325-11ce-bfc1-08002be10318}")
        usb   = _read_class_driver("{36fc9e60-c465-11cf-8056-444553540000}")

        all_drivers = [
            gpu   or {"name": "Display adapter not detected",  "version": "", "date": ""},
            audio or {"name": "Audio device not detected",     "version": "", "date": ""},
            net   or {"name": "Network adapter not detected",  "version": "", "date": ""},
            usb   or {"name": "USB controller not detected",   "version": "", "date": ""},
        ]
        win_info = _get_windows_info()
        startup  = _get_startup_programs()
        score    = _compute_score(all_drivers, len(startup))

        uptime_str = last_boot_str = ""
        if _HAS_PSUTIL:
            try:
                boot = psutil.boot_time()
                secs = time.time() - boot
                d = int(secs // 86400)
                h = int((secs % 86400) // 3600)
                m = int((secs % 3600) // 60)
                uptime_str    = f"{d}d {h}h" if d > 0 else f"{h}h {m}min"
                last_boot_str = datetime.fromtimestamp(boot).strftime("%a %H:%M")
            except Exception:
                pass

        try:
            sf.after(0, lambda: _apply(refs, all_drivers, win_info, startup,
                                       score, uptime_str, last_boot_str))
        except Exception:
            pass

    def _trigger_scan():
        refs["scanning"] = True
        _start_pulse(refs)
        for card in refs.get("cards", []):
            _reset_card(card)
        try:
            refs["scan_msg"].config(text="  Re-scanning…")
            refs["scan_dot"].config(fg=AMBER)
            refs["header_dot"].config(text="● Scanning…", fg=AMBER)
        except Exception:
            pass
        threading.Thread(target=_do_scan, daemon=True).start()

    refs["rescan_cmd"] = _trigger_scan
    threading.Thread(target=_do_scan, daemon=True).start()

    return main


# ─── Scan pulse animation ─────────────────────────────────────────────────────
def _start_pulse(refs):
    refs["scanning"] = True
    refs["_pulse_tick"] = 0

    def _pulse():
        if not refs.get("scanning", False):
            return
        dot = refs.get("scan_dot")
        if dot is None:
            return
        try:
            if not dot.winfo_exists():
                return
        except Exception:
            return
        refs["_pulse_tick"] = (refs.get("_pulse_tick", 0) + 1) % 6
        colors = [AMBER, "#fcd34d", "#fef08a", "#fcd34d", AMBER, MUTED]
        try:
            dot.config(fg=colors[refs["_pulse_tick"]])
            dot.after(300, _pulse)
        except Exception:
            pass

    _pulse()


# ─── Header ───────────────────────────────────────────────────────────────────
def _build_header(parent, refs):
    hdr = tk.Frame(parent, bg="#0b1220", height=46)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)

    inner = tk.Frame(hdr, bg="#0b1220")
    inner.pack(fill="both", expand=True, padx=14)

    left = tk.Frame(inner, bg="#0b1220")
    left.pack(side="left", fill="y")
    tk.Label(left, text="⚙", font=("Segoe UI", 14), bg="#0b1220",
             fg=BLUE).pack(side="left", pady=10)
    tk.Label(left, text="  FIRST SETUP & DRIVERS",
             font=("Consolas", 10, "bold"), bg="#0b1220", fg=TEXT).pack(side="left")
    tk.Label(left, text="   ·   system readiness  ·  driver health  ·  startup control",
             font=("Consolas", 7), bg="#0b1220", fg=MUTED).pack(side="left")

    right = tk.Frame(inner, bg="#0b1220")
    right.pack(side="right", fill="y")

    dot = tk.Label(right, text="● Scanning…", font=("Consolas", 7),
                   bg="#0b1220", fg=AMBER)
    dot.pack(side="right", padx=(8, 0), pady=14)
    refs["header_dot"] = dot

    def _make_btn(label, bg_, cmd):
        b = tk.Label(right, text=label, font=("Consolas", 8, "bold"),
                     bg=bg_, fg="#ffffff", padx=10, pady=6, cursor="hand2")
        b.pack(side="right", padx=(5, 0), pady=8)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e, w=b, c=bg_: w.config(bg=_lighten(c)))
        b.bind("<Leave>", lambda e, w=b, c=bg_: w.config(bg=c))

    def _rescan():
        cmd = refs.get("rescan_cmd")
        if cmd:
            cmd()

    def _win_update():
        try: os.startfile("ms-settings:windowsupdate")
        except Exception: pass

    def _dev_mgr():
        try: subprocess.Popen(["devmgmt.msc"], shell=True)
        except Exception: pass

    _make_btn("↺  Re-Scan",        "#374151", _rescan)
    _make_btn("⊞  Device Manager", "#0c4a6e", _dev_mgr)
    _make_btn("↑  Windows Update", "#1d4ed8", _win_update)


# ─── Hero: score gauge + system info ─────────────────────────────────────────
def _build_hero(parent, refs):
    sec = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                   highlightbackground=BORDER)
    sec.pack(fill="x", padx=15, pady=(10, 5))

    row = tk.Frame(sec, bg=PANEL)
    row.pack(fill="x", padx=14, pady=10)

    # Gauge
    gf = tk.Frame(row, bg=PANEL, width=116)
    gf.pack(side="left", fill="y")
    gf.pack_propagate(False)

    gc = tk.Canvas(gf, width=108, height=92, bg=PANEL, highlightthickness=0)
    gc.pack(padx=4, pady=4)
    _draw_arc(gc, None)
    refs["gauge"] = gc

    grade_lbl = tk.Label(gf, text="SCANNING", font=("Consolas", 8, "bold"),
                         bg=PANEL, fg=MUTED)
    grade_lbl.pack()
    refs["grade_lbl"] = grade_lbl

    tk.Frame(row, bg=BORDER, width=1).pack(side="left", fill="y", padx=(10, 14), pady=6)

    # Info block
    info = tk.Frame(row, bg=PANEL)
    info.pack(side="left", fill="both", expand=True)

    line1 = tk.Frame(info, bg=PANEL)
    line1.pack(fill="x")
    win_lbl = tk.Label(line1, text="Scanning system…",
                       font=("Segoe UI Semibold", 11), bg=PANEL, fg=TEXT)
    win_lbl.pack(side="left")
    build_badge = tk.Label(line1, text="", font=("Consolas", 7, "bold"),
                           bg="#1e3a5f", fg="#93c5fd", padx=7, pady=2)
    build_badge.pack(side="left", padx=(8, 0))
    refs["win_lbl"]     = win_lbl
    refs["build_badge"] = build_badge

    stats = tk.Frame(info, bg=PANEL)
    stats.pack(fill="x", pady=(6, 0))
    for col, (lbl, key) in enumerate([
        ("UPTIME",    "lbl_uptime"),
        ("LAST BOOT", "lbl_boot"),
        ("BUILD",     "lbl_build"),
        ("DRIVERS",   "lbl_drv_ok"),
    ]):
        f = tk.Frame(stats, bg=PANEL)
        f.grid(row=0, column=col, sticky="w", padx=(0, 28))
        tk.Label(f, text=lbl, font=("Consolas", 6), bg=PANEL, fg=MUTED).pack(anchor="w")
        v = tk.Label(f, text="—", font=("Consolas", 8, "bold"), bg=PANEL, fg=TEXT)
        v.pack(anchor="w")
        refs[key] = v

    bar_f = tk.Frame(info, bg=PANEL)
    bar_f.pack(fill="x", pady=(8, 0))
    scan_dot = tk.Label(bar_f, text="●", font=("Consolas", 9), bg=PANEL, fg=AMBER)
    scan_dot.pack(side="left")
    scan_msg = tk.Label(bar_f, text="  Scanning registry for driver information…",
                        font=("Consolas", 7), bg=PANEL, fg=MUTED)
    scan_msg.pack(side="left")
    refs["scan_dot"] = scan_dot
    refs["scan_msg"] = scan_msg


# ─── Driver cards ─────────────────────────────────────────────────────────────
def _build_driver_section(parent, refs):
    sec = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                   highlightbackground=BORDER)
    sec.pack(fill="x", padx=15, pady=(0, 5))

    hdr = tk.Frame(sec, bg="#091628")
    hdr.pack(fill="x")
    tk.Label(hdr, text="  DRIVER HEALTH", font=("Consolas", 9, "bold"),
             bg="#091628", fg=BLUE, pady=5).pack(side="left")
    summ = tk.Label(hdr, text="scanning…", font=("Consolas", 7),
                    bg="#091628", fg=MUTED)
    summ.pack(side="right", padx=12)
    refs["drv_summary"] = summ

    body = tk.Frame(sec, bg=PANEL)
    body.pack(fill="x", padx=10, pady=(6, 8))

    CATS = [
        ("GPU",       "Display / Graphics",  "▣", BLUE),
        ("AUDIO",     "Sound Device",        "◈", PURPLE),
        ("NETWORK",   "Network Adapter",     "◎", GREEN),
        ("USB / IN",  "Controllers",         "⬡", "#ec4899"),
    ]
    cards = []
    for cat, sub, icon, color in CATS:
        c = _make_driver_card(body, cat, sub, icon, color)
        c["frame"].pack(fill="x", pady=2)
        cards.append(c)
    refs["cards"] = cards


def _make_driver_card(parent, category, subcategory, icon, accent):
    outer = tk.Frame(parent, bg=PANEL2, highlightthickness=1,
                     highlightbackground=BORDER)
    row = tk.Frame(outer, bg=PANEL2)
    row.pack(fill="x")

    ab = tk.Frame(row, bg="#374151", width=4)
    ab.pack(side="left", fill="y")

    cf = tk.Frame(row, bg=PANEL2, width=84)
    cf.pack(side="left", fill="y")
    cf.pack_propagate(False)
    tk.Label(cf, text=icon, font=("Segoe UI", 10), bg=PANEL2, fg=accent
             ).pack(pady=(7, 0))
    tk.Label(cf, text=category, font=("Consolas", 7, "bold"), bg=PANEL2, fg=accent
             ).pack()
    tk.Label(cf, text=subcategory, font=("Consolas", 5), bg=PANEL2, fg=MUTED
             ).pack(pady=(0, 7))

    tk.Frame(row, bg=BORDER, width=1).pack(side="left", fill="y", pady=4)

    inf = tk.Frame(row, bg=PANEL2)
    inf.pack(side="left", fill="both", expand=True, padx=(10, 0))

    name_lbl = tk.Label(inf, text="Scanning…",
                        font=("Segoe UI Semibold", 9), bg=PANEL2, fg=TEXT, anchor="w")
    name_lbl.pack(anchor="w", pady=(8, 2))

    meta = tk.Frame(inf, bg=PANEL2)
    meta.pack(anchor="w")
    ver_lbl  = tk.Label(meta, text="", font=("Consolas", 7), bg=PANEL2, fg=MUTED)
    ver_lbl.pack(side="left")
    date_lbl = tk.Label(meta, text="", font=("Consolas", 7), bg=PANEL2, fg=MUTED)
    date_lbl.pack(side="left", padx=(12, 0))

    # Age freshness bar
    age_bar_bg = tk.Frame(inf, bg="#1f2937", height=3)
    age_bar_bg.pack(fill="x", pady=(3, 7))
    age_bar_bg.pack_propagate(False)
    age_bar_fill = tk.Frame(age_bar_bg, bg="#374151", height=3)
    age_bar_fill.place(x=0, y=0, relwidth=0.0, relheight=1.0)

    rf = tk.Frame(row, bg=PANEL2, width=120)
    rf.pack(side="right", fill="y", padx=10)
    rf.pack_propagate(False)

    badge = tk.Label(rf, text="SCANNING", font=("Consolas", 7, "bold"),
                     bg="#1f2937", fg=MUTED, padx=8, pady=3)
    badge.pack(pady=(10, 4))

    def _open_dm(e=None):
        try: subprocess.Popen(["devmgmt.msc"], shell=True)
        except Exception: pass

    action = tk.Label(rf, text="⟶ Device Manager",
                      font=("Consolas", 6), bg=PANEL2, fg="#4b5563",
                      cursor="hand2")
    action.pack()
    action.bind("<Button-1>", _open_dm)
    action.bind("<Enter>", lambda e: action.config(fg=BLUE))
    action.bind("<Leave>", lambda e: action.config(fg="#4b5563"))

    return {
        "frame": outer, "bar": ab,
        "name": name_lbl, "ver": ver_lbl, "date": date_lbl,
        "badge": badge, "age_fill": age_bar_fill,
    }


def _reset_card(card):
    try:
        card["frame"].config(highlightbackground=BORDER)
        card["bar"].config(bg="#374151")
        card["name"].config(text="Scanning…", fg=TEXT)
        card["ver"].config(text="")
        card["date"].config(text="")
        card["badge"].config(text="SCANNING", bg="#1f2937", fg=MUTED)
        card["age_fill"].place(relwidth=0.0)
    except Exception:
        pass


# ─── Bottom row: Quick Actions + Startup Programs ────────────────────────────
def _build_bottom_row(parent, refs):
    wrap = tk.Frame(parent, bg=BG)
    wrap.pack(fill="x", padx=15, pady=(0, 5))

    # Quick Actions
    left = tk.Frame(wrap, bg=PANEL, highlightthickness=1,
                    highlightbackground=BORDER)
    left.pack(side="left", fill="both", expand=True, padx=(0, 5))

    hdr_l = tk.Frame(left, bg="#1a0d2e")
    hdr_l.pack(fill="x")
    tk.Label(hdr_l, text="  QUICK ACTIONS", font=("Consolas", 9, "bold"),
             bg="#1a0d2e", fg=PURPLE, pady=4).pack(side="left")

    ACTIONS = [
        ("↺  Windows Update",  "#1d4ed8", "startfile", "ms-settings:windowsupdate"),
        ("⊞  Device Manager",  "#0c4a6e", "shell",     "devmgmt.msc"),
        ("⚙  Services",        "#1e3a5f", "shell",     "services.msc"),
        ("✦  Task Scheduler",  "#1c1917", "shell",     "taskschd.msc"),
        ("⬡  System Info",     "#1a2e1a", "shell",     "msinfo32"),
        ("⚙  MSConfig",        "#1f1d3a", "shell",     "msconfig"),
    ]

    grid = tk.Frame(left, bg=PANEL)
    grid.pack(fill="both", expand=True, padx=8, pady=6)

    for idx, (label, bg_, mode, target) in enumerate(ACTIONS):
        r, c = divmod(idx, 2)

        def _run(m=mode, t=target):
            try:
                os.startfile(t) if m == "startfile" else subprocess.Popen([t], shell=True)
            except Exception:
                pass

        btn = tk.Label(grid, text=label, font=("Consolas", 8, "bold"),
                       bg=bg_, fg=TEXT, anchor="w", padx=10, pady=7, cursor="hand2")
        btn.grid(row=r, column=c, padx=3, pady=2, sticky="ew")
        grid.columnconfigure(c, weight=1)
        btn.bind("<Button-1>", lambda e, f=_run: f())
        btn.bind("<Enter>", lambda e, b=btn, o=bg_: b.config(bg=_lighten(o)))
        btn.bind("<Leave>", lambda e, b=btn, o=bg_: b.config(bg=o))

    foot_l = tk.Frame(left, bg=PANEL)
    foot_l.pack(fill="x", padx=8, pady=(0, 6))
    tk.Label(foot_l, text="⟶ More tools in Optimization tab",
             font=("Consolas", 7), bg=PANEL, fg="#4b5563").pack(side="right")

    # Startup Programs
    right = tk.Frame(wrap, bg=PANEL, highlightthickness=1,
                     highlightbackground=BORDER)
    right.pack(side="right", fill="both", expand=True)

    hdr_r = tk.Frame(right, bg="#0d1a12")
    hdr_r.pack(fill="x")
    tk.Label(hdr_r, text="  STARTUP PROGRAMS", font=("Consolas", 9, "bold"),
             bg="#0d1a12", fg=GREEN, pady=4).pack(side="left")
    cnt_lbl = tk.Label(hdr_r, text="scanning…", font=("Consolas", 7),
                       bg="#0d1a12", fg=MUTED)
    cnt_lbl.pack(side="right", padx=10)
    refs["startup_cnt"] = cnt_lbl

    su_body = tk.Frame(right, bg=PANEL)
    su_body.pack(fill="both", expand=True, padx=8, pady=(4, 0))

    rows = []
    for _ in range(10):
        rf = tk.Frame(su_body, bg=PANEL2, highlightthickness=1,
                      highlightbackground=BORDER)
        rf.pack(fill="x", pady=1)
        dot = tk.Label(rf, text="●", font=("Consolas", 8), bg=PANEL2, fg="#374151")
        dot.pack(side="left", padx=(6, 4), pady=3)
        n_l = tk.Label(rf, text="—", font=("Consolas", 8), bg=PANEL2,
                       fg=MUTED, anchor="w")
        n_l.pack(side="left", fill="x", expand=True)
        src = tk.Label(rf, text="", font=("Consolas", 6), bg=PANEL2, fg="#374151")
        src.pack(side="right", padx=(0, 8))
        rf.pack_forget()
        rows.append({"frame": rf, "dot": dot, "name": n_l, "src": src})
    refs["startup_rows"] = rows

    foot_r = tk.Frame(right, bg=PANEL)
    foot_r.pack(fill="x", padx=8, pady=4)

    def _open_startup():
        try: os.startfile("ms-settings:startupapps")
        except Exception: pass

    lnk2 = tk.Label(foot_r, text="⟶ Open Startup Settings",
                    font=("Consolas", 7), bg=PANEL, fg="#4b5563", cursor="hand2")
    lnk2.pack(side="right")
    lnk2.bind("<Button-1>", lambda e: _open_startup())
    lnk2.bind("<Enter>", lambda e: lnk2.config(fg=GREEN))
    lnk2.bind("<Leave>", lambda e: lnk2.config(fg="#4b5563"))


# ─── Setup Checklist ──────────────────────────────────────────────────────────
def _build_checklist(parent):
    sec = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                   highlightbackground=BORDER)
    sec.pack(fill="x", padx=15, pady=(0, 14))

    hdr = tk.Frame(sec, bg="#1a1200")
    hdr.pack(fill="x")
    tk.Label(hdr, text="  SETUP CHECKLIST", font=("Consolas", 9, "bold"),
             bg="#1a1200", fg=AMBER, pady=5).pack(side="left")
    tk.Label(hdr, text="  Click any item to mark as done — saved automatically",
             font=("Consolas", 7), bg="#1a1200", fg=MUTED).pack(side="left")

    state = _load_checklist()
    done_count = sum(1 for k, _ in _CHECKLIST if state.get(k, False))

    # Progress bar
    prog_f = tk.Frame(sec, bg=PANEL)
    prog_f.pack(fill="x", padx=10, pady=(6, 2))
    prog_bar_bg = tk.Frame(prog_f, bg="#1f2937", height=4)
    prog_bar_bg.pack(fill="x")
    prog_bar_bg.pack_propagate(False)
    fill_w = done_count / len(_CHECKLIST)
    prog_fill = tk.Frame(prog_bar_bg,
                         bg=GREEN if fill_w == 1.0 else AMBER, height=4)
    prog_fill.place(x=0, y=0, relwidth=fill_w, relheight=1.0)

    grid = tk.Frame(sec, bg=PANEL)
    grid.pack(fill="x", padx=10, pady=(4, 10))

    for idx, (key, label) in enumerate(_CHECKLIST):
        r, c = divmod(idx, 2)
        done = bool(state.get(key, False))

        item = tk.Frame(grid, bg=PANEL2, highlightthickness=1,
                        highlightbackground="#065f46" if done else BORDER)
        item.grid(row=r, column=c, padx=4, pady=3, sticky="ew")
        grid.columnconfigure(c, weight=1)

        ck = tk.Label(item, text="✓" if done else "○",
                      font=("Consolas", 11, "bold"), bg=PANEL2,
                      fg=GREEN if done else "#374151")
        ck.pack(side="left", padx=(8, 6), pady=6)

        txt = tk.Label(item, text=label, font=("Consolas", 8), bg=PANEL2,
                       fg=TEXT if done else MUTED, anchor="w")
        txt.pack(side="left", fill="x", expand=True, pady=6)

        def _toggle(e, k=key, fr=item, cl=ck, tl=txt, pb=prog_fill):
            s = _load_checklist()
            s[k] = not s.get(k, False)
            _save_checklist(s)
            now = s[k]
            cl.config(text="✓" if now else "○", fg=GREEN if now else "#374151")
            tl.config(fg=TEXT if now else MUTED)
            fr.config(highlightbackground="#065f46" if now else BORDER)
            dc = sum(1 for ky, _ in _CHECKLIST if s.get(ky, False))
            fw = dc / len(_CHECKLIST)
            try:
                pb.place(relwidth=fw)
                pb.config(bg=GREEN if fw == 1.0 else AMBER)
            except Exception:
                pass

        for w in (item, ck, txt):
            w.bind("<Button-1>", _toggle)
            w.config(cursor="hand2")


# ─── Apply scan results ───────────────────────────────────────────────────────
def _apply(refs, drivers, win_info, startup, score, uptime_str, last_boot_str):
    refs["scanning"] = False
    try:
        gc = refs.get("gauge")
        if gc and gc.winfo_exists():
            _draw_arc(gc, score)
        sc = _score_color(score)
        refs.get("grade_lbl",   tk.Label()).config(text=_score_grade(score), fg=sc)

        product = win_info.get("product", "Windows")
        vtag    = win_info.get("version_tag", "")
        build   = win_info.get("build", "")
        refs.get("win_lbl",     tk.Label()).config(text=product)
        refs.get("build_badge", tk.Label()).config(
            text=f" {vtag} " if vtag else f" Build {build} ")
        refs.get("lbl_uptime",  tk.Label()).config(text=uptime_str or "N/A",    fg=TEXT)
        refs.get("lbl_boot",    tk.Label()).config(text=last_boot_str or "N/A", fg=TEXT)
        refs.get("lbl_build",   tk.Label()).config(text=build or "N/A",         fg=TEXT)

        current = sum(
            1 for d in drivers
            if _driver_age_days(d.get("date", "")) is not None
            and _driver_age_days(d.get("date", "")) < 180
        )
        dv_col = GREEN if current == len(drivers) else AMBER if current > 0 else RED
        refs.get("lbl_drv_ok",  tk.Label()).config(
            text=f"{current}/{len(drivers)} current", fg=dv_col)
        refs.get("drv_summary", tk.Label()).config(
            text=f"{current} of {len(drivers)} drivers up-to-date", fg=dv_col)

        refs.get("scan_dot",    tk.Label()).config(fg=GREEN)
        refs.get("scan_msg",    tk.Label()).config(
            text=f"  Scan complete  ·  score {score}/100")
        refs.get("header_dot",  tk.Label()).config(
            text=f"● Ready  {score}/100", fg=_score_color(score))

        for card, d in zip(refs.get("cards", []), drivers):
            _fill_card(card, d)

        cnt   = len(startup)
        c_col = RED if cnt > 12 else AMBER if cnt > 7 else GREEN
        refs.get("startup_cnt", tk.Label()).config(
            text=f"{cnt} items detected", fg=c_col)
        for i, row in enumerate(refs.get("startup_rows", [])):
            if i < cnt:
                s = startup[i]
                row["frame"].pack(fill="x", pady=1)
                row["dot"].config(fg=GREEN if s["source"] == "User" else AMBER)
                row["name"].config(text=s["name"][:30], fg=TEXT)
                row["src"].config(text=s["source"], fg=MUTED)
            else:
                row["frame"].pack_forget()

    except Exception:
        import traceback
        traceback.print_exc()


def _fill_card(card, data):
    name     = data.get("name", "Unknown")
    version  = data.get("version", "")
    date_str = data.get("date", "")
    days     = _driver_age_days(date_str)
    status, txt_col, badge_bg, bar_col, brd_col = _age_info(days)
    age_ratio = max(0.0, 1.0 - days / 730) if days is not None else 0.0

    try:
        card["frame"].config(highlightbackground=brd_col)
        card["bar"].config(bg=bar_col)
        card["name"].config(text=name[:50])
        card["ver"].config(text=f"v{version}" if version else "version unknown")
        card["date"].config(text=_fmt_date(date_str))
        card["badge"].config(text=f"  {status}  ", bg=badge_bg, fg=txt_col)
        card["age_fill"].place(relwidth=age_ratio)
        card["age_fill"].config(bg=bar_col)
    except Exception:
        pass


# ─── Arc gauge ────────────────────────────────────────────────────────────────
def _draw_arc(canvas, score):
    canvas.delete("all")
    W, H = 108, 92
    cx, cy, r = W // 2, H // 2 + 4, 35

    # Outer glow ring
    canvas.create_arc(cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4,
                      start=225, extent=-270, style="arc",
                      outline="#1a2035", width=10)
    # Track
    canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                      start=225, extent=-270,
                      style="arc", outline="#1f2937", width=7)

    if score is not None:
        col    = _score_color(score)
        extent = -int(270 * score / 100)
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=225, extent=extent,
                          style="arc", outline=col, width=7)
        canvas.create_text(cx, cy - 3, text=str(score),
                           font=("Consolas", 18, "bold"), fill=col, anchor="center")
        canvas.create_text(cx, cy + 17, text="/100",
                           font=("Consolas", 7), fill=MUTED, anchor="center")
    else:
        canvas.create_text(cx, cy, text="—",
                           font=("Consolas", 18, "bold"), fill=MUTED, anchor="center")
