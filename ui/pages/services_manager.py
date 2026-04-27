# ui/pages/services_manager.py
"""
SERVICES MANAGER
Full Windows services browser with TURBO integration.

Categories:
  • Essential          — system-critical, locked (cannot be stopped)
  • Recommended        — useful, leave running
  • Potentially Unneeded — context-dependent
  • Likely Unneeded    — safe to stop / set Manual

TURBO Mode section lets users pick services to auto-stop when TURBO
activates and auto-restore when it deactivates.
"""

import tkinter as tk
from tkinter import messagebox
import threading
import subprocess
import os
import json
import ctypes

try:
    import winreg
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False

try:
    from utils.fonts import UI as _F, MONO as _M
except Exception:
    _F, _M = "Inter", "Consolas"

# ─── Palette ──────────────────────────────────────────────────────────────────
BG      = "#0a0e14"
PANEL   = "#0e1118"
PANEL2  = "#111520"
BORDER  = "#1a2035"
LINE    = "#141826"
TEXT    = "#c4cfdf"
MUTED   = "#3d4a60"
DIM     = "#1e2838"
AMBER   = "#f59e0b"
EMERALD = "#10b981"
BLUE    = "#3b82f6"
RED     = "#ef4444"
VIOLET  = "#8b5cf6"
NAVY    = "#1e3a5f"
DARKRED = "#7f1d1d"

try:
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    import sys as _sys
    _APP_DIR = os.path.dirname(_sys.executable) if getattr(_sys, "frozen", False) \
               else os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

_TURBO_PREFS = os.path.join(_APP_DIR, "settings", "turbo_services.json")
_SVC_LOG     = os.path.join(_APP_DIR, "data", "logs", "service_changes.log")

# ─── Service catalogue ────────────────────────────────────────────────────────
# (service_name, display_name, category, description)
# category: "essential" | "recommended" | "optional" | "unnecessary"
_CATALOGUE: list[tuple[str, str, str, str]] = [
    # ── Essential ──────────────────────────────────────────────────────────
    ("wuauserv",       "Windows Update",               "essential",    "Keeps Windows up to date"),
    ("Windefend",      "Windows Defender Antivirus",   "essential",    "Real-time malware protection"),
    ("MpsSvc",         "Windows Firewall",             "essential",    "Network packet filtering"),
    ("EventLog",       "Windows Event Log",            "essential",    "System event recording"),
    ("RpcSs",          "Remote Procedure Call (RPC)",  "essential",    "Core IPC mechanism"),
    ("lsass",          "Local Security Authority",     "essential",    "Authentication & tokens"),
    ("CryptSvc",       "Cryptographic Services",       "essential",    "Certificate management"),
    ("DcomLaunch",     "DCOM Server Process Launcher", "essential",    "COM object activation"),
    ("LanmanServer",   "Server (SMB)",                 "essential",    "File/printer sharing"),
    ("Netlogon",       "Net Logon",                    "essential",    "Domain authentication"),
    # ── Recommended ────────────────────────────────────────────────────────
    ("AudioSrv",       "Windows Audio",                "recommended",  "Sound subsystem"),
    ("Audiosrv",       "Windows Audio Endpoint",       "recommended",  "Audio device management"),
    ("BFE",            "Base Filtering Engine",        "recommended",  "Firewall policy base"),
    ("BITS",           "Background Intelligent Transfer","recommended","OS update downloads"),
    ("DPS",            "Diagnostic Policy Service",    "recommended",  "Problem detection"),
    ("Schedule",       "Task Scheduler",               "recommended",  "Automated task runner"),
    ("Themes",         "Themes",                       "recommended",  "Visual theme engine"),
    ("TabletInputService","Touch Keyboard & Handwriting","recommended","Tablet input"),
    ("WSearch",        "Windows Search",               "recommended",  "File indexing"),
    ("SysMain",        "Superfetch / SysMain",         "recommended",  "Memory prefetch"),
    # ── Optional / context-dependent ───────────────────────────────────────
    ("wsearch",        "Windows Search (duplicate)",   "optional",     "Duplicate search entry"),
    ("WerSvc",         "Windows Error Reporting",      "optional",     "Crash report uploads"),
    ("RemoteRegistry", "Remote Registry",              "optional",     "Remote reg access — disable if unused"),
    ("TrkWks",         "Distributed Link Tracking",    "optional",     "File link maintenance"),
    ("SSDPSRV",        "SSDP Discovery",               "optional",     "UPnP device discovery"),
    ("upnphost",       "UPnP Device Host",             "optional",     "UPnP service hosting"),
    ("lmhosts",        "TCP/IP NetBIOS Helper",        "optional",     "Legacy NetBIOS — disable on modern LAN"),
    ("MapsBroker",     "Downloaded Maps Manager",      "optional",     "Offline maps cache"),
    ("RetailDemo",     "Retail Demo Service",          "optional",     "Store demo mode"),
    ("WbioSrvc",       "Windows Biometric Service",    "optional",     "Fingerprint/face ID"),
    # ── Likely unnecessary ─────────────────────────────────────────────────
    ("DiagTrack",      "Connected User Experiences / Telemetry", "unnecessary",
                                                               "Sends usage data to Microsoft"),
    ("dmwappushservice","Device Management WAP Push",  "unnecessary",  "Telemetry relay"),
    ("XblGameSave",    "Xbox Game Save",               "unnecessary",  "Xbox cloud saves"),
    ("XblAuthManager", "Xbox Live Auth Manager",       "unnecessary",  "Xbox Live auth"),
    ("XboxNetApiSvc",  "Xbox Live Networking",         "unnecessary",  "Xbox Live networking"),
    ("WMPNetworkSvc",  "Windows Media Player Sharing", "unnecessary",  "Shares WMP library"),
    ("Fax",            "Fax",                          "unnecessary",  "Fax machine support"),
    ("TermService",    "Remote Desktop Services",      "unnecessary",  "RDP — disable if unused"),
    ("SessionEnv",     "Remote Desktop Config",        "unnecessary",  "RDP configuration"),
    ("UmRdpService",   "Remote Desktop Device Redir.", "unnecessary",  "RDP redirectors"),
    ("PrintNotify",    "Printer Extensions and Notifications","unnecessary","Printer UI popups"),
    ("spooler",        "Print Spooler",                "unnecessary",  "Printing — disable if no printer"),
    ("SharedAccess",   "Internet Connection Sharing",  "unnecessary",  "ICS hotspot relay"),
    ("iphlpsvc",       "IP Helper",                    "unnecessary",  "IPv6 tunnels — rarely needed"),
]

_CAT_COLOR = {
    "essential":   RED,
    "recommended": EMERALD,
    "optional":    AMBER,
    "unnecessary": VIOLET,
}
_CAT_LABEL = {
    "essential":   "ESSENTIAL",
    "recommended": "RECOMMENDED",
    "optional":    "OPTIONAL",
    "unnecessary": "UNNEEDED",
}
_CAT_SECTIONS = ["essential", "recommended", "optional", "unnecessary"]
_CAT_TITLE = {
    "essential":   "🔒 Essential — do not stop",
    "recommended": "✅ Recommended",
    "optional":    "⚠  Optional (context-dependent)",
    "unnecessary": "🗑  Likely unnecessary",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _sc_run(args: list[str]) -> tuple[bool, str]:
    """Run sc.exe command. Returns (success, output)."""
    try:
        result = subprocess.run(
            ["sc"] + args,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def _query_service_status(name: str) -> str:
    """Return 'running' | 'stopped' | 'unknown'."""
    ok, out = _sc_run(["query", name])
    if not ok:
        return "unknown"
    if "RUNNING" in out.upper():
        return "running"
    if "STOPPED" in out.upper():
        return "stopped"
    if "PAUSED" in out.upper():
        return "paused"
    return "unknown"


def _query_start_type(name: str) -> str:
    """Return 'auto' | 'manual' | 'disabled' | 'unknown'."""
    ok, out = _sc_run(["qc", name])
    if not ok:
        return "unknown"
    for line in out.splitlines():
        if "START_TYPE" in line.upper():
            if "AUTO" in line.upper():
                return "auto"
            if "DEMAND" in line.upper():
                return "manual"
            if "DISABLED" in line.upper():
                return "disabled"
    return "unknown"


def _get_statuses_batch(names: list[str]) -> dict[str, str]:
    """Query all services in one sc query run. Faster than individual calls."""
    try:
        result = subprocess.run(
            ["sc", "query", "type=", "all", "state=", "all"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=20
        )
        lines = result.stdout.splitlines()
    except Exception:
        return {n: "unknown" for n in names}

    statuses: dict[str, str] = {}
    current = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("SERVICE_NAME:"):
            current = stripped.split(":", 1)[1].strip().lower()
        elif stripped.startswith("STATE") and current is not None:
            if "RUNNING" in stripped.upper():
                statuses[current] = "running"
            elif "STOPPED" in stripped.upper():
                statuses[current] = "stopped"
            elif "PAUSED" in stripped.upper():
                statuses[current] = "paused"
            else:
                statuses[current] = "unknown"

    return {n: statuses.get(n.lower(), "unknown") for n in names}


def _log_change(svc_name: str, action: str, success: bool):
    os.makedirs(os.path.dirname(_SVC_LOG), exist_ok=True)
    try:
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "OK" if success else "FAILED"
        with open(_SVC_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {action.upper()} {svc_name} — {status}\n")
    except Exception:
        pass


def _load_turbo_prefs() -> dict:
    try:
        with open(_TURBO_PREFS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"turbo_stop": []}


def _save_turbo_prefs(data: dict):
    os.makedirs(os.path.dirname(_TURBO_PREFS), exist_ok=True)
    try:
        with open(_TURBO_PREFS, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ─── UI helpers ───────────────────────────────────────────────────────────────

def _scrollable(parent, bg=BG) -> tuple[tk.Frame, tk.Canvas]:
    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill="both", expand=True)

    cv = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    sb = tk.Scrollbar(outer, orient="vertical", command=cv.yview,
                      bg=bg, troughcolor=bg,
                      highlightthickness=0, bd=0, width=6)
    inner = tk.Frame(cv, bg=bg)
    win_id = cv.create_window((0, 0), window=inner, anchor="nw")

    def _on_resize(e):
        cv.itemconfig(win_id, width=e.width)
    cv.bind("<Configure>", _on_resize)
    inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))

    def _wheel(e):
        cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
    cv.bind_all("<MouseWheel>", _wheel)

    sb.pack(side="right", fill="y")
    cv.pack(side="left", fill="both", expand=True)
    cv.configure(yscrollcommand=sb.set)
    return inner, cv


def _cat_header(parent, cat: str, count: int):
    color = _CAT_COLOR[cat]
    title = _CAT_TITLE[cat]
    row = tk.Frame(parent, bg=PANEL2)
    row.pack(fill="x", padx=10, pady=(12, 2))
    tk.Label(row, text=title, font=(_F, 9, "bold"),
             bg=PANEL2, fg=TEXT).pack(side="left", padx=(8, 6), pady=6)
    if count:
        tk.Label(row, text=str(count), font=(_F, 7, "bold"),
                 bg=color, fg="#ffffff", padx=4, pady=1).pack(side="left")
    tk.Frame(row, bg=BORDER, height=1).pack(side="bottom", fill="x")


def _status_dot(status: str) -> tuple[str, str]:
    """Return (dot_char, color) for a service status."""
    if status == "running":
        return "●", EMERALD
    if status == "stopped":
        return "○", MUTED
    if status == "paused":
        return "◐", AMBER
    return "?", MUTED


def _build_service_row(parent, entry: dict,
                       statuses: dict[str, str],
                       turbo_set: set[str],
                       on_action,
                       locked: bool,
                       show_turbo_check: bool):
    """Build one service row."""
    name  = entry["name"]
    dname = entry["display"]
    cat   = entry["cat"]
    desc  = entry["desc"]

    status = statuses.get(name, "unknown")
    dot, dot_color = _status_dot(status)

    card = tk.Frame(parent, bg=PANEL, bd=0,
                    highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="x", padx=10, pady=1)

    inner = tk.Frame(card, bg=PANEL)
    inner.pack(fill="x", padx=8, pady=4)

    # Status dot
    tk.Label(inner, text=dot, font=(_F, 11),
             bg=PANEL, fg=dot_color, width=2).pack(side="left")

    # Centre text block
    mid = tk.Frame(inner, bg=PANEL)
    mid.pack(side="left", fill="both", expand=True, padx=6)

    name_row = tk.Frame(mid, bg=PANEL)
    name_row.pack(anchor="w")
    tk.Label(name_row, text=dname, font=(_F, 9, "bold"),
             bg=PANEL, fg=TEXT).pack(side="left")
    # Category badge
    c_col = _CAT_COLOR.get(cat, MUTED)
    c_lbl = _CAT_LABEL.get(cat, cat.upper())
    tk.Label(name_row, text=f" [{c_lbl}]", font=(_F, 7),
             bg=PANEL, fg=c_col).pack(side="left", padx=(4, 0))

    tk.Label(mid, text=f"  {name}  —  {desc}",
             font=(_F, 7), bg=PANEL, fg=MUTED).pack(anchor="w")

    # Right: TURBO checkbox + action buttons
    right = tk.Frame(inner, bg=PANEL)
    right.pack(side="right")

    if show_turbo_check and cat in ("optional", "unnecessary"):
        var = tk.BooleanVar(value=name in turbo_set)
        chk = tk.Checkbutton(
            right, text="TURBO", font=(_F, 7),
            variable=var, bg=PANEL, fg=AMBER,
            activebackground=PANEL, activeforeground=AMBER,
            selectcolor=DIM,
            command=lambda n=name, v=var: _turbo_toggle(n, v.get(), turbo_set)
        )
        chk.pack(side="left", padx=(0, 6))

    if locked:
        tk.Label(right, text="🔒", font=(_F, 9),
                 bg=PANEL, fg=MUTED).pack(side="left", padx=4)
    else:
        if status == "running":
            stop_btn = tk.Label(right, text="Stop", font=(_F, 7),
                                bg=DARKRED, fg=RED,
                                padx=7, pady=3, cursor="hand2")
            stop_btn.pack(side="left", padx=2)
            stop_btn.bind("<Button-1>",
                          lambda e, n=name, c=card: on_action(n, "stop", c))
        else:
            start_btn = tk.Label(right, text="Start", font=(_F, 7),
                                 bg="#0d2b1d", fg=EMERALD,
                                 padx=7, pady=3, cursor="hand2")
            start_btn.pack(side="left", padx=2)
            start_btn.bind("<Button-1>",
                           lambda e, n=name, c=card: on_action(n, "start", c))

        restart_btn = tk.Label(right, text="↺", font=(_F, 9),
                               bg=DIM, fg=BLUE,
                               padx=6, pady=3, cursor="hand2")
        restart_btn.pack(side="left", padx=2)
        restart_btn.bind("<Button-1>",
                         lambda e, n=name, c=card: on_action(n, "restart", c))


def _turbo_toggle(svc_name: str, enabled: bool, turbo_set: set[str]):
    if enabled:
        turbo_set.add(svc_name)
    else:
        turbo_set.discard(svc_name)
    data = _load_turbo_prefs()
    data["turbo_stop"] = list(turbo_set)
    _save_turbo_prefs(data)


# ─── Main page builder ────────────────────────────────────────────────────────

def build_services_manager_page(host, parent: tk.Frame):
    """Entry point called from main_window_expanded."""
    is_admin = _is_admin()

    page = tk.Frame(parent, bg=BG)
    page.pack(fill="both", expand=True)

    # ── Admin warning ──
    if not is_admin:
        warn = tk.Frame(page, bg="#2d1a00", height=26)
        warn.pack(fill="x")
        warn.pack_propagate(False)
        tk.Label(warn,
                 text="⚠  Not running as Administrator — Stop/Start actions may fail.",
                 font=(_F, 7, "bold"), bg="#2d1a00", fg=AMBER,
                 padx=10).pack(side="left", fill="y")

    # ── Stat bar ──
    stat = tk.Frame(page, bg=NAVY, height=24)
    stat.pack(fill="x")
    stat.pack_propagate(False)
    stat_lbl = tk.Label(stat, text="  Scanning services…",
                        font=(_F, 7, "bold"), bg=NAVY, fg="#93c5fd")
    stat_lbl.pack(side="left", padx=6)

    # ── Spinner ──
    spinner = tk.Label(page, text="Loading Windows services…",
                       font=(_F, 10), bg=BG, fg=MUTED)
    spinner.pack(pady=40)

    def _on_data_ready(statuses: dict[str, str]):
        spinner.destroy()
        _render(page, stat_lbl, statuses, is_admin)

    def _scan():
        names = [e[0] for e in _CATALOGUE]
        statuses = _get_statuses_batch(names)
        page.after(0, lambda: _on_data_ready(statuses))

    threading.Thread(target=_scan, daemon=True).start()


def _render(page: tk.Frame, stat_lbl: tk.Label,
            statuses: dict[str, str], is_admin: bool):
    """Render service list once status query completes."""
    turbo_data = _load_turbo_prefs()
    turbo_set = set(turbo_data.get("turbo_stop", []))

    # ── Build structured entry list ──
    entries_by_cat: dict[str, list[dict]] = {c: [] for c in _CAT_SECTIONS}
    for name, display, cat, desc in _CATALOGUE:
        # Deduplicate by name
        if any(e["name"] == name for e in entries_by_cat[cat]):
            continue
        entries_by_cat[cat].append({
            "name": name, "display": display, "cat": cat, "desc": desc
        })

    # Stat bar update
    running = sum(1 for s in statuses.values() if s == "running")
    total   = len(_CATALOGUE)
    stat_lbl.config(text=f"  {total} services catalogued  ·  {running} running  "
                         f"·  TURBO: {len(turbo_set)} queued")

    # ── Action handler ──
    def _action(svc_name: str, action: str, card: tk.Frame):
        if not is_admin:
            messagebox.showwarning(
                "Admin required",
                "PC Workman needs to be run as Administrator to control services."
            )
            return
        verb_map = {"stop": "stop", "start": "start", "restart": "restart"}
        ans = messagebox.askyesno(
            "Confirm",
            f"Are you sure you want to {action} service '{svc_name}'?"
        )
        if not ans:
            return
        if action == "restart":
            ok1, _ = _sc_run(["stop", svc_name])
            import time; time.sleep(1)
            ok2, _ = _sc_run(["start", svc_name])
            ok = ok2
        else:
            ok, _ = _sc_run([verb_map[action], svc_name])
        _log_change(svc_name, action, ok)
        if ok:
            new_status = "running" if action in ("start", "restart") else "stopped"
            statuses[svc_name] = new_status
            # Rebuild card in-place
            card.destroy()
            # Rebuild is complex; inform user to refresh
            info = tk.Frame(card.master if card.master.winfo_exists() else page, bg=DIM)
            info.pack(fill="x", padx=10, pady=1)
            tk.Label(info,
                     text=f"  ✓ {svc_name} {action}ed — refresh page to see updated status",
                     font=(_F, 7), bg=DIM, fg=EMERALD, padx=6, pady=3).pack(anchor="w")
        else:
            messagebox.showerror(
                "Failed",
                f"Could not {action} '{svc_name}'.\n"
                "Check the service log at data/logs/service_changes.log"
            )

    # ── Scrollable content ──
    inner, _ = _scrollable(page)

    for cat in _CAT_SECTIONS:
        elist = entries_by_cat[cat]
        if not elist:
            continue
        _cat_header(inner, cat, len(elist))
        locked = (cat == "essential")
        for entry in elist:
            _build_service_row(
                inner, entry, statuses, turbo_set,
                on_action=_action,
                locked=locked,
                show_turbo_check=True
            )

    # ─── TURBO Mode section ───────────────────────────────────────────────────
    turbo_frame = tk.Frame(inner, bg=PANEL2,
                           highlightthickness=1, highlightbackground="#2a3d5f")
    turbo_frame.pack(fill="x", padx=10, pady=(16, 4))

    turbo_hdr = tk.Frame(turbo_frame, bg="#0d1f38")
    turbo_hdr.pack(fill="x")
    tk.Label(turbo_hdr, text="⚡  TURBO Mode Integration",
             font=(_F, 9, "bold"), bg="#0d1f38", fg=AMBER,
             padx=10, pady=7).pack(side="left")
    tk.Label(turbo_hdr,
             text="Services checked above will auto-stop when TURBO activates",
             font=(_F, 7), bg="#0d1f38", fg=MUTED,
             padx=6).pack(side="left")

    turbo_body = tk.Frame(turbo_frame, bg=PANEL2)
    turbo_body.pack(fill="x", padx=10, pady=6)

    if turbo_set:
        for svc in sorted(turbo_set):
            row = tk.Frame(turbo_body, bg=PANEL2)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"  ⚡ {svc}",
                     font=(_F, 8), bg=PANEL2, fg=AMBER).pack(side="left")
            remove_btn = tk.Label(row, text="✕",
                                  font=(_F, 7), bg=PANEL2, fg=MUTED,
                                  cursor="hand2")
            remove_btn.pack(side="right", padx=6)

            def _remove(s=svc, r=row):
                turbo_set.discard(s)
                data = _load_turbo_prefs()
                data["turbo_stop"] = list(turbo_set)
                _save_turbo_prefs(data)
                r.destroy()

            remove_btn.bind("<Button-1>", lambda e, fn=_remove: fn())
    else:
        tk.Label(turbo_body,
                 text="No services queued for TURBO.\n"
                      "Use the checkboxes in Optional/Unneeded rows above to add them.",
                 font=(_F, 8), bg=PANEL2, fg=MUTED,
                 justify="left", padx=6, pady=6).pack(anchor="w")

    # ─── Log link ─────────────────────────────────────────────────────────────
    foot = tk.Frame(inner, bg=BG)
    foot.pack(fill="x", padx=10, pady=(10, 8))
    tk.Label(foot,
             text=f"ℹ  Changes logged to:  {_SVC_LOG}",
             font=(_F, 7), bg=BG, fg=MUTED).pack(anchor="w")
