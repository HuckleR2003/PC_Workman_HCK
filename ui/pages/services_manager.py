import tkinter as tk
from tkinter import messagebox
import threading, subprocess, os, json, ctypes, time

try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except Exception:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_F    = _UIF
_M    = _MONOF
_BODY = _UIF
_MONO = _MONOF

BG      = "#090c12"
SURFACE = "#0d1117"
HOVER   = "#101620"
BORDER  = "#14202e"
SEP     = "#141d28"
TEXT    = "#cdd8e8"
SUB     = "#66788f"
MUTED   = "#344256"
ACCENT  = "#7c3aed"
AMBER   = "#d97706"
GREEN   = "#16a34a"
RED     = "#dc2626"
VIOLET  = "#7c3aed"
LOCK    = "#991b1b"
TURBO_BG = "#0d1020"
TURBO_BD = "#1e2a4a"

_CAT_META = {
    "essential":   {"label": "ESSENTIAL",   "color": "#dc2626", "bg": "#1a0808",
                    "icon": "⛒",  "desc": "System-critical - cannot be stopped"},
    "recommended": {"label": "RECOMMENDED", "color": "#16a34a", "bg": "#071610",
                    "icon": "✓",  "desc": "Useful services - leave running"},
    "optional":    {"label": "OPTIONAL",    "color": "#d97706", "bg": "#161006",
                    "icon": "◈",  "desc": "Context-dependent - review before stopping"},
    "unnecessary": {"label": "UNNEEDED",    "color": "#7c3aed", "bg": "#120d1c",
                    "icon": "✕",  "desc": "Safe to disable on most systems"},
}
_CAT_ORDER = ["essential", "recommended", "optional", "unnecessary"]

_CATALOGUE: list[tuple[str, str, str, str]] = [
    ("wuauserv",        "Windows Update",                  "essential",   "Keeps Windows patched and secure"),
    ("Windefend",       "Windows Defender Antivirus",      "essential",   "Real-time malware protection"),
    ("MpsSvc",          "Windows Firewall",                "essential",   "Network packet filtering"),
    ("EventLog",        "Windows Event Log",               "essential",   "System event recording for diagnostics"),
    ("RpcSs",           "Remote Procedure Call (RPC)",     "essential",   "Core IPC mechanism - many apps depend on it"),
    ("CryptSvc",        "Cryptographic Services",          "essential",   "Certificate and code signature validation"),
    ("DcomLaunch",      "DCOM Server Process Launcher",    "essential",   "COM object activation - core Windows"),
    ("LanmanServer",    "Server (SMB)",                    "essential",   "File and printer sharing over network"),
    ("LanmanWorkstation","Workstation (SMB client)",       "essential",   "Connects to network shares"),
    ("Netlogon",        "Net Logon",                       "essential",   "Domain authentication service"),
    ("AudioSrv",        "Windows Audio",                   "recommended", "Core sound subsystem"),
    ("AudioEndpointBuilder","Windows Audio Endpoint",      "recommended", "Audio device management"),
    ("BFE",             "Base Filtering Engine",           "recommended", "Firewall policy base layer"),
    ("BITS",            "Background Intelligent Transfer", "recommended", "Windows Update download manager"),
    ("DPS",             "Diagnostic Policy Service",       "recommended", "Problem detection and reporting"),
    ("Schedule",        "Task Scheduler",                  "recommended", "Runs scheduled tasks and maintenance"),
    ("Themes",          "Themes",                          "recommended", "Windows visual theme engine"),
    ("WSearch",         "Windows Search",                  "recommended", "File indexing for fast search"),
    ("SysMain",         "SysMain / Superfetch",            "recommended", "Memory prefetch - improves app launch times"),
    ("WerSvc",          "Windows Error Reporting",         "optional",    "Uploads crash data to Microsoft"),
    ("RemoteRegistry",  "Remote Registry",                 "optional",    "Remote registry access - disable if unused"),
    ("TrkWks",          "Distributed Link Tracking",       "optional",    "Maintains file shortcut links - rarely critical"),
    ("SSDPSRV",         "SSDP Discovery",                  "optional",    "UPnP device discovery on local network"),
    ("upnphost",        "UPnP Device Host",                "optional",    "Hosts UPnP services - disable if no smart devices"),
    ("lmhosts",         "TCP/IP NetBIOS Helper",           "optional",    "Legacy NetBIOS resolution - rarely needed today"),
    ("MapsBroker",      "Downloaded Maps Manager",         "optional",    "Offline maps cache - disable if not used"),
    ("RetailDemo",      "Retail Demo Service",             "optional",    "Store demo mode - safe to disable"),
    ("WbioSrvc",        "Windows Biometric Service",       "optional",    "Fingerprint and face unlock support"),
    ("TabletInputService","Touch Keyboard & Handwriting",  "optional",    "Tablet input - disable on desktop PCs"),
    ("DiagTrack",       "Connected User Experiences / Telemetry", "unnecessary", "Sends Windows usage data to Microsoft"),
    ("dmwappushservice","Device Management WAP Push",      "unnecessary", "Telemetry relay - can be disabled"),
    ("XblGameSave",     "Xbox Game Save",                  "unnecessary", "Xbox cloud save sync - disable if no Xbox"),
    ("XblAuthManager",  "Xbox Live Auth Manager",          "unnecessary", "Xbox Live authentication"),
    ("XboxNetApiSvc",   "Xbox Live Networking",            "unnecessary", "Xbox Live network service"),
    ("WMPNetworkSvc",   "Windows Media Player Sharing",    "unnecessary", "Shares WMP library over network"),
    ("Fax",             "Fax",                             "unnecessary", "Fax machine support - disable if no fax"),
    ("TermService",     "Remote Desktop Services",         "unnecessary", "RDP server - disable if not used remotely"),
    ("SessionEnv",      "Remote Desktop Configuration",    "unnecessary", "RDP session configuration"),
    ("UmRdpService",    "Remote Desktop Device Redirector","unnecessary", "RDP device redirection"),
    ("PrintNotify",     "Printer Extensions",              "unnecessary", "Printer popup notifications"),
    ("spooler",         "Print Spooler",                   "unnecessary", "Printing - disable if no printer connected"),
    ("SharedAccess",    "Internet Connection Sharing",     "unnecessary", "ICS hotspot - disable if not sharing internet"),
    ("iphlpsvc",        "IP Helper",                       "unnecessary", "IPv6 transition tunnels - rarely needed"),
]

try:
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    import sys as _sys
    _APP_DIR = os.path.dirname(_sys.executable) if getattr(_sys, "frozen", False) \
               else os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

_TURBO_PREFS = os.path.join(_APP_DIR, "settings", "turbo_services.json")
_SVC_LOG     = os.path.join(_APP_DIR, "data", "logs", "service_changes.log")


def _is_admin() -> bool:
    try: return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except: return False


def _sc_run(args: list[str]) -> tuple[bool, str]:
    try:
        r = subprocess.run(["sc"] + args, capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
        return r.returncode == 0, r.stdout.strip()
    except Exception as e: return False, str(e)


def _get_start_type(name: str) -> str:
    """Return start type for a single service via 'sc qc': auto/manual/disabled/unknown."""
    try:
        r = subprocess.run(["sc", "qc", name],
                           capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=8)
        for line in r.stdout.splitlines():
            s = line.strip().upper()
            if "START_TYPE" in s or "START TYPE" in s:
                if "DISABLED" in s:   return "disabled"
                if "AUTO"     in s:   return "auto"
                if "DEMAND"   in s:   return "manual"
                if "BOOT"     in s or "SYSTEM" in s: return "auto"
    except Exception:
        pass
    return "unknown"


def _get_statuses_batch(names: list[str]) -> dict[str, str]:
    """Returns dict: service_name_lower -> 'running'|'stopped'|'paused'|'disabled'|'unknown'"""
    try:
        r = subprocess.run(["sc", "query", "type=", "all", "state=", "all"],
                           capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)
        lines = r.stdout.splitlines()
    except Exception: return {n: "unknown" for n in names}
    statuses: dict[str, str] = {}
    current = None
    for line in lines:
        s = line.strip()
        if s.startswith("SERVICE_NAME:"):
            current = s.split(":", 1)[1].strip().lower()
        elif s.startswith("STATE") and current is not None:
            up = s.upper()
            if "RUNNING" in up:   statuses[current] = "running"
            elif "STOPPED" in up: statuses[current] = "stopped"
            elif "PAUSED"  in up: statuses[current] = "paused"
            else:                 statuses[current] = "unknown"
    # For services not seen in query (may be disabled at system level), check sc qc
    result = {}
    for n in names:
        st = statuses.get(n.lower(), None)
        if st is None:
            # Service not returned by sc query — likely disabled at StartType level
            st = _get_start_type(n)
        result[n] = st
    return result


_SVC_PREFS_PATH = os.path.join(_APP_DIR, "data", "cache", "service_prefs.json")


def _load_svc_prefs() -> dict:
    try:
        with open(_SVC_PREFS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_svc_prefs(data: dict):
    os.makedirs(os.path.dirname(_SVC_PREFS_PATH), exist_ok=True)
    try:
        with open(_SVC_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _log_change(svc: str, action: str, ok: bool):
    os.makedirs(os.path.dirname(_SVC_LOG), exist_ok=True)
    try:
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        who = "UŻYTKOWNIK"
        with open(_SVC_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {action.upper()} {svc} - {'OK' if ok else 'FAILED'} - przez: {who}\n")
    except Exception: pass


def _load_turbo() -> dict:
    try:
        with open(_TURBO_PREFS, encoding="utf-8") as f: return json.load(f)
    except Exception: return {"turbo_stop": []}


def _save_turbo(data: dict):
    os.makedirs(os.path.dirname(_TURBO_PREFS), exist_ok=True)
    try:
        with open(_TURBO_PREFS, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
    except Exception: pass


class _Tooltip:
    def __init__(self, widget, text: str, delay: int = 700):
        self._w = widget; self._text = text; self._delay = delay
        self._job = None; self._tw = None
        widget.bind("<Enter>", self._sched, add="+")
        widget.bind("<Leave>", self._cancel, add="+")
        widget.bind("<ButtonPress>", self._cancel, add="+")

    def _sched(self, _=None):
        self._cancel()
        self._job = self._w.after(self._delay, self._show)

    def _cancel(self, _=None):
        if self._job: self._w.after_cancel(self._job); self._job = None
        if self._tw:  self._tw.destroy();               self._tw = None

    def _show(self):
        x = self._w.winfo_rootx() + 8
        y = self._w.winfo_rooty() + self._w.winfo_height() + 6
        self._tw = tw = tk.Toplevel(self._w)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self._text, font=(_F, 9), bg="#1a2540", fg=TEXT,
                 padx=12, pady=7, wraplength=320, justify="left").pack()


def _hover_row(row: tk.Frame, children: list):
    def _on(e):
        try: row.config(bg=HOVER)
        except: pass
        for w in children:
            try: w.config(bg=HOVER)
            except: pass
    def _off(e):
        sx, sy = row.winfo_pointerxy()
        rx, ry = row.winfo_rootx(), row.winfo_rooty()
        if not (rx <= sx <= rx + row.winfo_width() and ry <= sy <= ry + row.winfo_height()):
            try: row.config(bg=SURFACE)
            except: pass
            for w in children:
                try: w.config(bg=SURFACE)
                except: pass
    for w in [row, *children]:
        w.bind("<Enter>", _on, add="+")
        w.bind("<Leave>", _off, add="+")


def _scrollable(parent, bg=BG):
    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill="both", expand=True)
    cv = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    sb = tk.Scrollbar(outer, orient="vertical", command=cv.yview,
                      bg=bg, troughcolor=bg, highlightthickness=0, bd=0, width=5)
    inner = tk.Frame(cv, bg=bg)
    wid = cv.create_window((0, 0), window=inner, anchor="nw")
    cv.bind("<Configure>", lambda e: cv.itemconfig(wid, width=e.width))
    inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
    def _mw(e):
        try:
            if cv.winfo_exists():
                cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception:
            pass
    cv.bind_all("<MouseWheel>", _mw)
    sb.pack(side="right", fill="y")
    cv.pack(side="left", fill="both", expand=True)
    cv.configure(yscrollcommand=sb.set)
    return inner, cv


def _pill_status(parent, status: str, bg: str) -> tk.Label:
    cfg = {
        "running": (GREEN,  "#0a1f10", "● Running"),
        "stopped": (MUTED,  "#111520", "○ Stopped"),
        "paused":  (AMBER,  "#1c1000", "◐ Paused"),
        "unknown": (MUTED,  "#111520", "? Unknown"),
    }
    fg, pbg, txt = cfg.get(status, cfg["unknown"])
    return tk.Label(parent, text=txt, font=(_F, 8), bg=pbg, fg=fg, padx=7, pady=2)


def _btn(parent, text: str, fg: str, bg: str, hover_fg: str, command, font_size: int = 8):
    b = tk.Label(parent, text=text, font=(_F, font_size), fg=fg, bg=bg,
                 padx=9, pady=3, cursor="hand2")
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>", lambda e: b.config(fg=hover_fg))
    b.bind("<Leave>", lambda e: b.config(fg=fg))
    return b


def _section_header(parent, cat: str, count: int, collapsed_var: tk.BooleanVar, toggle_fn):
    meta = _CAT_META[cat]
    color = meta["color"]
    bg_strip = meta["bg"]

    hdr = tk.Frame(parent, bg=BG)
    hdr.pack(fill="x", padx=10, pady=(12, 0))
    hdr.bind("<Button-1>", lambda e: toggle_fn())

    left = tk.Frame(hdr, bg=BG)
    left.pack(side="left", fill="y")

    icon_lbl = tk.Label(left, text=meta["icon"], font=(_F, 10, "bold"),
                        bg=BG, fg=color, cursor="hand2")
    icon_lbl.pack(side="left", padx=(0, 8))
    icon_lbl.bind("<Button-1>", lambda e: toggle_fn())

    name_lbl = tk.Label(left, text=meta["label"], font=(_F, 9, "bold"),
                        bg=BG, fg=color, cursor="hand2")
    name_lbl.pack(side="left")
    name_lbl.bind("<Button-1>", lambda e: toggle_fn())

    desc_lbl = tk.Label(left, text=f"  -  {meta['desc']}",
                        font=(_F, 8), bg=BG, fg=MUTED, cursor="hand2")
    desc_lbl.pack(side="left")
    desc_lbl.bind("<Button-1>", lambda e: toggle_fn())

    right = tk.Frame(hdr, bg=BG)
    right.pack(side="right")
    count_lbl = tk.Label(right, text=str(count), font=(_F, 8, "bold"),
                         bg=meta["bg"], fg=color, padx=8, pady=2)
    count_lbl.pack(side="left")

    caret_lbl = tk.Label(right, text="▾", font=(_F, 9),
                         bg=BG, fg=MUTED, cursor="hand2", padx=8)
    caret_lbl.pack(side="left")
    caret_lbl.bind("<Button-1>", lambda e: toggle_fn())

    tk.Frame(hdr, bg=color, height=1).pack(side="bottom", fill="x")

    def _update_caret():
        caret_lbl.config(text="▸" if collapsed_var.get() else "▾")

    collapsed_var.trace_add("write", lambda *_: _update_caret())

    return hdr


def _service_row(parent, entry: dict, statuses: dict, turbo_set: set,
                 locked: bool, show_turbo: bool, is_admin: bool,
                 on_action, on_turbo_toggle, svc_prefs: dict = None):
    name   = entry["name"]
    dname  = entry["display"]
    cat    = entry["cat"]
    desc   = entry["desc"]
    status = statuses.get(name, "unknown")
    meta   = _CAT_META.get(cat, _CAT_META["optional"])

    row = tk.Frame(parent, bg=SURFACE)
    row.pack(fill="x", padx=8, pady=1)

    body = tk.Frame(row, bg=SURFACE)
    body.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=7)

    name_row = tk.Frame(body, bg=SURFACE)
    name_row.pack(fill="x")

    name_lbl = tk.Label(name_row, text=dname, font=(_F, 10, "bold"),
                        bg=SURFACE, fg=TEXT)
    name_lbl.pack(side="left")

    svc_key = tk.Label(name_row, text=f"  {name}", font=(_M, 8),
                       bg=SURFACE, fg=MUTED)
    svc_key.pack(side="left")

    desc_lbl = tk.Label(body, text=desc, font=(_F, 8), bg=SURFACE, fg=SUB,
                        anchor="w", wraplength=220, justify="left")
    desc_lbl.pack(anchor="w", pady=(2, 0))

    # Show "changed by user" badge if this service was previously actioned by user
    if svc_prefs:
        hist = svc_prefs.get(name, {})
        if hist.get("changed_by") == "UŻYTKOWNIK" and hist.get("last_action"):
            ts  = hist.get("last_change", "")
            act = hist.get("last_action", "").upper()
            badge_txt = f"UŻYTKOWNIK: {act}"
            if ts:
                badge_txt += f"  ·  {ts}"
            tk.Label(body, text=badge_txt,
                     font=(_F, 7), bg=SURFACE, fg="#16a34a",
                     anchor="w").pack(anchor="w")

    all_labels = [body, name_row, name_lbl, svc_key, desc_lbl]

    _Tooltip(name_lbl, f"{dname}\n\n{desc}\n\nService key: {name}")

    right = tk.Frame(row, bg=SURFACE)
    right.pack(side="right", padx=(0, 12), pady=8)
    all_labels.append(right)

    pill = _pill_status(right, status, SURFACE)
    pill.pack(side="left", padx=(0, 10))
    all_labels.append(pill)

    # ── Disabled-at-system-level indicator ───────────────────────────────────
    if status == "disabled":
        dis_lbl = tk.Label(right, text="DISABLED",
                           font=(_M, 7, "bold"), bg=SURFACE, fg="#4b5563")
        dis_lbl.pack(side="left", padx=(0, 8))
        _Tooltip(dis_lbl, "This service is disabled at the system level.\n"
                           "Start it first before enabling here.")
        all_labels.append(dis_lbl)
        # No Stop/Start buttons for system-disabled services
        return row

    if locked:
        lock = tk.Label(right, text="⛒", font=(_F, 10), bg=SURFACE, fg=LOCK)
        lock.pack(side="left", padx=4)
        _Tooltip(lock, "Essential service - cannot be stopped safely.")
        all_labels.append(lock)
    else:
        is_running = (status == "running")

        # Stop — always visible; active (red) when running, muted when stopped
        sb = _btn(right, "Stop",
                  fg=RED if is_running else "#2d3748",
                  bg=SURFACE,
                  hover_fg="#ff6666" if is_running else "#4a5568",
                  command=lambda n=name, r=row: on_action(n, "stop", r))
        sb.pack(side="left", padx=2)
        _Tooltip(sb, f"Stop the {dname} service." if is_running else f"{dname} is already stopped.")
        all_labels.append(sb)

        # Start — always visible; active (green) when stopped, muted when running
        stb = _btn(right, "Start",
                   fg=GREEN if not is_running else "#1a3a1a",
                   bg=SURFACE,
                   hover_fg="#4ade80" if not is_running else "#2a4a2a",
                   command=lambda n=name, r=row: on_action(n, "start", r))
        stb.pack(side="left", padx=2)
        _Tooltip(stb, f"Start the {dname} service." if not is_running else f"{dname} is already running.")
        all_labels.append(stb)

        rb = _btn(right, "↺", fg=SUB, bg=SURFACE, hover_fg=TEXT, font_size=11,
                  command=lambda n=name, r=row: on_action(n, "restart", r))
        rb.pack(side="left", padx=2)
        _Tooltip(rb, f"Restart {dname}.")
        all_labels.append(rb)

        if show_turbo and cat in ("optional", "unnecessary"):
            in_turbo = name in turbo_set
            tv = tk.BooleanVar(value=in_turbo)

            def _make_turbo_lbl(var, n):
                lbl_color = AMBER if var.get() else MUTED
                tlbl = tk.Label(right, text="⚡", font=(_F, 10),
                                bg=SURFACE, fg=lbl_color, cursor="hand2")
                def _toggle():
                    var.set(not var.get())
                    tlbl.config(fg=AMBER if var.get() else MUTED)
                    on_turbo_toggle(n, var.get())
                tlbl.bind("<Button-1>", lambda e: _toggle())
                _Tooltip(tlbl, "Toggle TURBO: this service will auto-stop when TURBO Boost activates.")
                return tlbl

            tlbl = _make_turbo_lbl(tv, name)
            tlbl.pack(side="left", padx=(6, 0))
            all_labels.append(tlbl)

    sep = tk.Frame(parent, bg=SEP, height=1)
    sep.pack(fill="x", padx=8)

    _hover_row(row, all_labels)


def _turbo_panel(parent, turbo_set: set, stat_lbl: tk.Label):
    panel = tk.Frame(parent, bg=TURBO_BG, highlightthickness=1,
                     highlightbackground=TURBO_BD)
    panel.pack(fill="x", side="bottom")

    hdr = tk.Frame(panel, bg=TURBO_BG)
    hdr.pack(fill="x", padx=14, pady=(6, 2))

    tk.Label(hdr, text="⚡ TURBO", font=(_F, 8, "bold"),
             bg=TURBO_BG, fg=AMBER).pack(side="left")
    tk.Label(hdr, text="  - services queued to stop on TURBO activate:",
             font=(_F, 7), bg=TURBO_BG, fg=MUTED).pack(side="left")

    chips_frame = [None]

    def _refresh_chips():
        if chips_frame[0]: chips_frame[0].destroy()
        cf = tk.Frame(panel, bg=TURBO_BG)
        cf.pack(fill="x", padx=14, pady=(0, 10))
        chips_frame[0] = cf

        if not turbo_set:
            tk.Label(cf, text="No services queued.  Use ⚡ buttons in Optional / Unneeded rows above.",
                     font=(_F, 8), bg=TURBO_BG, fg=MUTED).pack(anchor="w")
        else:
            for svc in sorted(turbo_set):
                chip = tk.Frame(cf, bg="#141c30", padx=6, pady=3)
                chip.pack(side="left", padx=(0, 6), pady=2)
                tk.Label(chip, text=svc, font=(_M, 8), bg="#141c30", fg=AMBER).pack(side="left")

                def _remove(s=svc):
                    turbo_set.discard(s)
                    data = _load_turbo()
                    data["turbo_stop"] = list(turbo_set)
                    _save_turbo(data)
                    _refresh_chips()
                    stat_lbl.config(text=_stat_text(stat_lbl._total, stat_lbl._running, turbo_set))

                x = tk.Label(chip, text=" ✕", font=(_F, 8), bg="#141c30", fg=MUTED, cursor="hand2")
                x.pack(side="left")
                x.bind("<Button-1>", lambda e, fn=_remove: fn())
                x.bind("<Enter>", lambda e, w=x: w.config(fg=RED))
                x.bind("<Leave>", lambda e, w=x: w.config(fg=MUTED))

    _refresh_chips()
    return _refresh_chips


def _stat_text(total, running, turbo_set):
    return f"  {total} services catalogued   ·   {running} running   ·   {len(turbo_set)} in TURBO"


def build_services_manager_page(host, parent: tk.Frame):
    is_admin = _is_admin()
    page = tk.Frame(parent, bg=BG)
    page.pack(fill="both", expand=True)

    if not is_admin:
        warn = tk.Frame(page, bg="#1a0f00", height=28)
        warn.pack(fill="x")
        warn.pack_propagate(False)
        tk.Label(warn, text="  ⚠  Not running as Administrator - Stop / Start actions may fail.",
                 font=(_F, 8, "bold"), bg="#1a0f00", fg=AMBER,
                 padx=10).pack(side="left", fill="y")

    names = [e[0] for e in _CATALOGUE]
    spin  = tk.Label(page, text="Loading Windows services…",
                     font=(_F, 10), bg=BG, fg=SUB)
    spin.pack(pady=60)

    def _on_ready(statuses):
        spin.destroy()
        _render(page, statuses, is_admin)

    threading.Thread(target=lambda: page.after(0, lambda: _on_ready(_get_statuses_batch(names))),
                     daemon=True).start()


def _render(page: tk.Frame, statuses: dict, is_admin: bool):
    turbo_data = _load_turbo()
    turbo_set  = set(turbo_data.get("turbo_stop", []))

    entries_by_cat: dict[str, list[dict]] = {c: [] for c in _CAT_ORDER}
    seen = set()
    for name, display, cat, desc in _CATALOGUE:
        if name in seen: continue
        seen.add(name)
        entries_by_cat[cat].append({"name": name, "display": display, "cat": cat, "desc": desc})

    running = sum(1 for s in statuses.values() if s == "running")
    total   = len(seen)

    # Compact header — no subtitle
    header = tk.Frame(page, bg=BG)
    header.pack(fill="x", padx=16, pady=(6, 0))

    left_col = tk.Frame(header, bg=BG)
    left_col.pack(side="left")
    tk.Label(left_col, text="Services Manager", font=(_F, 13, "bold"),
             bg=BG, fg=TEXT).pack(anchor="w")

    right_col = tk.Frame(header, bg=BG)
    right_col.pack(side="right", fill="y")

    if is_admin:
        tk.Label(right_col, text="Administrator ✓", font=(_F, 8, "bold"),
                 bg="#071610", fg=GREEN, padx=8, pady=3).pack(side="right", padx=(6, 0))
    else:
        tk.Label(right_col, text="Limited mode", font=(_F, 8, "bold"),
                 bg="#1a0f00", fg=AMBER, padx=8, pady=3).pack(side="right", padx=(6, 0))

    stat_lbl = tk.Label(right_col, text=_stat_text(total, running, turbo_set),
                        font=(_F, 8), bg=BG, fg=MUTED)
    stat_lbl.pack(side="right")
    stat_lbl._total   = total
    stat_lbl._running = running

    tk.Frame(page, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(14, 0))

    search_row = tk.Frame(page, bg=BG)
    search_row.pack(fill="x", padx=20, pady=10)

    search_var = tk.StringVar()
    search_entry = tk.Entry(search_row, textvariable=search_var,
                            font=(_F, 9), bg=SURFACE, fg=TEXT,
                            insertbackground=TEXT, relief="flat",
                            highlightthickness=1, highlightbackground=BORDER,
                            highlightcolor=ACCENT)
    search_entry.pack(fill="x", ipady=6, padx=(0, 0))

    placeholder = "Search services…"
    search_entry.insert(0, placeholder)
    search_entry.config(fg=SUB)
    search_entry.bind("<FocusIn>",  lambda e: (search_entry.delete(0, "end"), search_entry.config(fg=TEXT))
                                    if search_entry.get() == placeholder else None)
    search_entry.bind("<FocusOut>", lambda e: (search_entry.insert(0, placeholder), search_entry.config(fg=SUB))
                                    if not search_entry.get() else None)

    content_wrap = tk.Frame(page, bg=BG)
    content_wrap.pack(fill="both", expand=True)

    inner, cv = _scrollable(content_wrap)

    section_bodies: dict[str, tk.Frame] = {}
    collapsed_vars: dict[str, tk.BooleanVar] = {}

    def on_turbo_toggle(svc_name: str, enabled: bool):
        if enabled: turbo_set.add(svc_name)
        else:       turbo_set.discard(svc_name)
        data = _load_turbo()
        data["turbo_stop"] = list(turbo_set)
        _save_turbo(data)
        stat_lbl.config(text=_stat_text(total, running, turbo_set))
        refresh_turbo()

    svc_prefs = _load_svc_prefs()

    def on_action(svc_name: str, action: str, row: tk.Frame):
        nonlocal svc_prefs
        if not is_admin:
            messagebox.showwarning("Admin required",
                "PC Workman must run as Administrator to control services.")
            return
        confirm = messagebox.askyesno("Confirm action",
            f"Are you sure you want to {action}  \"{svc_name}\"?")
        if not confirm: return

        def _do():
            nonlocal svc_prefs
            if action == "restart":
                _sc_run(["stop", svc_name])
                time.sleep(1.2)
                ok, _ = _sc_run(["start", svc_name])
            else:
                ok, _ = _sc_run([action, svc_name])
            _log_change(svc_name, action, ok)
            new_status = "running" if action in ("start", "restart") else "stopped"
            if ok:
                statuses[svc_name] = new_status
                # Track who did what and when
                from datetime import datetime as _dt
                ts = _dt.now().strftime("%Y-%m-%d %H:%M")
                svc_prefs.setdefault(svc_name, {}).update({
                    "last_action":  action,
                    "last_change":  ts,
                    "changed_by":   "UŻYTKOWNIK",
                })
                _save_svc_prefs(svc_prefs)
            page.after(0, lambda: _handle_action_result(svc_name, action, ok, row, new_status))

        threading.Thread(target=_do, daemon=True).start()

    def _handle_action_result(svc_name, action, ok, row, new_status):
        if ok:
            from datetime import datetime as _dt
            ts = _dt.now().strftime("%H:%M")
            # Rebuild the row in place — don't destroy so user can stop/start again
            for w in row.winfo_children():
                try: w.destroy()
                except Exception: pass

            entry_info = next(
                (e for e in entries_by_cat.get(statuses.get(svc_name + "_cat", "optional"), [])
                 if e["name"] == svc_name),
                {"name": svc_name, "display": svc_name, "cat": "optional",
                 "desc": f"Last action: {action} at {ts}"}
            )
            # Find the correct entry across all categories
            for cat_entries in entries_by_cat.values():
                for e in cat_entries:
                    if e["name"] == svc_name:
                        entry_info = e
                        break

            # Show brief confirmation banner at top of row
            confirm_f = tk.Frame(row, bg="#0a160a")
            confirm_f.pack(fill="x")
            tk.Frame(confirm_f, bg=GREEN, width=3).pack(side="left", fill="y")
            tk.Label(confirm_f,
                     text=f"✓  {action.upper()}  ·  UŻYTKOWNIK  ·  {ts}",
                     font=(_F, 7), bg="#0a160a", fg="#22c55e",
                     pady=3, padx=6).pack(side="left")

            # Re-render service info with updated buttons
            locked = (entry_info.get("cat") == "essential")
            _service_row(row, entry_info, statuses, turbo_set,
                         locked=locked, show_turbo=True,
                         is_admin=is_admin,
                         on_action=on_action,
                         on_turbo_toggle=on_turbo_toggle,
                         svc_prefs=svc_prefs)
        else:
            messagebox.showerror("Action failed",
                f"Could not {action} '{svc_name}'.\n"
                "Check data/logs/service_changes.log for details.")

    # ── 2×2 grid: row1 = ESSENTIAL | RECOMMENDED, row2 = OPTIONAL | UNNEEDED ──
    def _make_col_pair(parent_frame, left_cat, right_cat):
        row = tk.Frame(parent_frame, bg=BG)
        row.pack(fill="x")

        left_col  = tk.Frame(row, bg=BG)
        left_col.pack(side="left", fill="both", expand=True)

        tk.Frame(row, bg=BORDER, width=1).pack(side="left", fill="y")

        right_col = tk.Frame(row, bg=BG)
        right_col.pack(side="left", fill="both", expand=True)

        return {left_cat: left_col, right_cat: right_col}

    col_map: dict[str, tk.Frame] = {}
    col_map.update(_make_col_pair(inner, "essential",   "recommended"))
    tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=8)
    col_map.update(_make_col_pair(inner, "optional",    "unnecessary"))

    _PREVIEW_COUNT = 3   # services shown before "expand more" banner

    for cat in _CAT_ORDER:
        elist = entries_by_cat.get(cat, [])
        if not elist: continue

        container = col_map[cat]

        cvar = tk.BooleanVar(value=False)
        collapsed_vars[cat] = cvar

        body = tk.Frame(container, bg=BG)

        def _toggle(c=cat, b=body, cv=cvar):
            cv.set(not cv.get())
            if cv.get():
                b.pack_forget()
            else:
                b.pack(fill="x")
            inner.event_generate("<Configure>")

        _section_header(container, cat, len(elist), cvar, _toggle)

        body.pack(fill="x")
        section_bodies[cat] = body

        locked = (cat == "essential")
        preview  = elist[:_PREVIEW_COUNT]
        overflow = elist[_PREVIEW_COUNT:]

        for entry in preview:
            _service_row(body, entry, statuses, turbo_set,
                         locked=locked, show_turbo=True,
                         is_admin=is_admin,
                         on_action=on_action,
                         on_turbo_toggle=on_turbo_toggle,
                         svc_prefs=svc_prefs)

        if overflow:
            # Overflow frame — hidden by default, shown by expand banner
            overflow_frame = tk.Frame(body, bg=BG)
            _exp_open = [False]

            def _build_overflow(of=overflow_frame, ol=overflow, lkd=locked):
                for oe in ol:
                    _service_row(of, oe, statuses, turbo_set,
                                 locked=lkd, show_turbo=True,
                                 is_admin=is_admin,
                                 on_action=on_action,
                                 on_turbo_toggle=on_turbo_toggle,
                                 svc_prefs=svc_prefs)

            _overflow_built = [False]

            expand_bar = tk.Frame(body, bg="#0b1018", cursor="hand2")
            expand_bar.pack(fill="x", padx=8, pady=0)
            expand_lbl = tk.Label(expand_bar,
                                   text=f"∨  Rozwiń więcej ({len(overflow)})  ∨",
                                   font=(_F, 7), bg="#0b1018", fg=MUTED,
                                   pady=2, cursor="hand2")
            expand_lbl.pack()

            def _toggle_overflow(e=None,
                                  ef=overflow_frame,
                                  el=expand_lbl,
                                  eo=_exp_open,
                                  eb=_overflow_built,
                                  ol=overflow,
                                  bld=_build_overflow):
                eo[0] = not eo[0]
                if eo[0]:
                    if not eb[0]:
                        bld()
                        eb[0] = True
                    ef.pack(fill="x", after=expand_bar)
                    el.config(text="∧  Collapse  ∧")
                else:
                    ef.pack_forget()
                    el.config(text=f"∨  Rozwiń więcej ({len(ol)})  ∨")
                inner.event_generate("<Configure>")

            expand_bar.bind("<Button-1>", _toggle_overflow)
            expand_lbl.bind("<Button-1>", _toggle_overflow)
            expand_bar.bind("<Enter>", lambda e, w=expand_lbl: w.config(fg=TEXT))
            expand_bar.bind("<Leave>", lambda e, w=expand_lbl: w.config(fg=MUTED))

    tk.Frame(inner, bg=BG, height=10).pack()

    refresh_turbo = _turbo_panel(page, turbo_set, stat_lbl)

    def _apply_search(*_):
        q = search_var.get().lower().strip()
        if q == placeholder.lower() or not q:
            for cat in _CAT_ORDER:
                b = section_bodies.get(cat)
                if b: b.pack(fill="x")
            return
        for cat in _CAT_ORDER:
            b = section_bodies.get(cat)
            if not b: continue
            any_visible = False
            for child in b.winfo_children():
                if not isinstance(child, tk.Frame): continue
                match = q in child.winfo_name().lower()
                for w in child.winfo_children():
                    try:
                        if q in (w.cget("text") or "").lower():
                            match = True; break
                    except: pass
                if match: child.pack(fill="x"); any_visible = True
                else:     child.pack_forget()
            if any_visible: b.pack(fill="x")
            else:            b.pack_forget()
        inner.event_generate("<Configure>")

    search_var.trace_add("write", _apply_search)
