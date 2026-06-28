import tkinter as tk
from tkinter import messagebox
import threading, subprocess, os, json, ctypes

# Single source of truth for mode -> service stop-lists (synced with Features).
try:
    from core.turbo_manager import turbo_services, RECOMMENDED
    _HAS_TURBO = True
except Exception:
    turbo_services, RECOMMENDED = None, []
    _HAS_TURBO = False

# Shared "operator" drawer — the single confirm/queue mechanism (also used by
# Startup Manager). One component, no duplicated drawers.
from ui.components.operator_drawer import OperatorDrawer

try:
    from utils.i18n import t as _t
except Exception:
    def _t(key, default=None, **kw):
        return default if default is not None else key

# User-facing modes shown as per-service chips (match the Features mode buttons).
_MODES = [
    ("gaming",  "G", "#c62828"),
    ("economy", "E", "#10b981"),
    ("manager", "M", "#cbd5e1"),
]

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
SUB     = "#8693a6"   # readable secondary (was #66788f)
MUTED   = "#93a1b5"   # readable muted (was #344256 — barely visible on dark)
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

_SVC_LOG     = os.path.join(_APP_DIR, "data", "logs", "service_changes.log")


def _is_admin() -> bool:
    try: return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except: return False


def _sc_run(args: list[str]) -> tuple[bool, str]:
    try:
        r = subprocess.run(["sc"] + args, capture_output=True, text=True,
                           errors="replace",
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
        return r.returncode == 0, r.stdout.strip()
    except Exception as e: return False, str(e)


def _get_start_type(name: str) -> str:
    """Return start type for a single service via 'sc qc': auto/manual/disabled/unknown."""
    try:
        r = subprocess.run(["sc", "qc", name],
                           capture_output=True, text=True, errors="replace",
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
                           capture_output=True, text=True, errors="replace",
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


_QUICK_PATH = os.path.join(_APP_DIR, "settings", "quick_setup.json")


def _load_quick() -> dict:
    """Saved Quick-setup answers: {recommendation_label: 'yes'|'no'}."""
    try:
        with open(_QUICK_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_quick(data: dict):
    os.makedirs(os.path.dirname(_QUICK_PATH), exist_ok=True)
    try:
        with open(_QUICK_PATH, "w", encoding="utf-8") as f:
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

    # Scope the wheel to THIS scroll area only (hover in -> grab, hover out ->
    # release). A global bind_all leaks the wheel across page switches; the
    # bounds-check on Leave ignores NotifyInferior crossings into child rows.
    def _enter(_e):
        cv.bind_all("<MouseWheel>", _mw)

    def _leave(_e):
        try:
            sx, sy = outer.winfo_pointerxy()
            rx, ry = outer.winfo_rootx(), outer.winfo_rooty()
            if not (rx <= sx <= rx + outer.winfo_width()
                    and ry <= sy <= ry + outer.winfo_height()):
                cv.unbind_all("<MouseWheel>")
        except Exception:
            pass

    outer.bind("<Enter>", _enter, add="+")
    outer.bind("<Leave>", _leave, add="+")
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


def _mode_chip(parent, svc: str, mkey: str, letter: str, color: str,
               active: bool, on_toggle):
    """Small G / E / M chip: lit when `svc` is in that mode's stop-list. Click toggles."""
    st = {"on": active}
    chip = tk.Label(parent, text=letter, font=(_F, 7, "bold"), width=2,
                    cursor="hand2", padx=1, pady=1,
                    highlightthickness=1)

    def _paint():
        chip.config(bg=color if st["on"] else "#0e141d",
                    fg="#08080a" if st["on"] else MUTED,
                    highlightbackground=color if st["on"] else BORDER)

    def _click(_=None):
        st["on"] = not st["on"]
        _paint()
        on_toggle(svc, mkey, st["on"])

    chip.bind("<Button-1>", _click)
    _paint()
    _Tooltip(chip, f"{mkey.capitalize()} mode: {'stops' if active else 'add to stop'} "
                   f"'{svc}' when this mode runs.")
    return chip


def _section_header(parent, cat: str, count: int, collapsed_var: tk.BooleanVar, toggle_fn):
    meta = _CAT_META[cat]
    color = meta["color"]

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


def _service_row(parent, entry: dict, statuses: dict, mode_sets: dict,
                 locked: bool, is_admin: bool,
                 on_mode_toggle, queue_toggle, is_queued,
                 svc_prefs: dict = None, row_apis: dict = None):
    """One configurator row. A single Wyłącz/Włącz control queues the change into
    the shared operator drawer (no per-row confirm dialogs). G/E/M chips stay
    inline. Repaints itself in place after a batch is applied."""
    name  = entry["name"]
    dname = entry["display"]
    desc  = entry["desc"]

    row = tk.Frame(parent, bg=SURFACE)
    row.pack(fill="x", padx=8, pady=1)
    sep = tk.Frame(parent, bg=SEP, height=1)
    sep.pack(fill="x", padx=8)

    state = {"sync": (lambda: None)}

    def _build():
        status = statuses.get(name, "unknown")

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

        # "changed by user" badge if this service was previously actioned by user
        if svc_prefs:
            hist = svc_prefs.get(name, {})
            if hist.get("changed_by") == "UŻYTKOWNIK" and hist.get("last_action"):
                ts  = hist.get("last_change", "")
                act = hist.get("last_action", "").upper()
                badge_txt = f"UŻYTKOWNIK: {act}" + (f"  ·  {ts}" if ts else "")
                tk.Label(body, text=badge_txt, font=(_F, 7), bg=SURFACE,
                         fg="#16a34a", anchor="w").pack(anchor="w")

        all_labels = [body, name_row, name_lbl, svc_key, desc_lbl]
        _Tooltip(name_lbl, f"{dname}\n\n{desc}\n\nService key: {name}")

        right = tk.Frame(row, bg=SURFACE)
        right.pack(side="right", padx=(0, 12), pady=8)
        all_labels.append(right)

        pill = _pill_status(right, status, SURFACE)
        pill.pack(side="left", padx=(0, 10))
        all_labels.append(pill)

        sync = (lambda: None)

        if status == "disabled":
            # Disabled at system level — nothing to queue.
            dis_lbl = tk.Label(right, text="DISABLED", font=(_M, 7, "bold"),
                               bg=SURFACE, fg="#4b5563")
            dis_lbl.pack(side="left", padx=(0, 8))
            _Tooltip(dis_lbl, "This service is disabled at the system level.\n"
                              "Start it first before enabling here.")
            all_labels.append(dis_lbl)
        elif locked:
            # Essential — never queued for stopping.
            lock = tk.Label(right, text="⛒", font=(_F, 10), bg=SURFACE, fg=LOCK)
            lock.pack(side="left", padx=4)
            _Tooltip(lock, "Essential service - cannot be stopped safely.")
            all_labels.append(lock)
        else:
            running  = (status == "running")
            base_txt = "Wyłącz" if running else "Włącz"
            base_fg  = RED if running else GREEN

            tg = tk.Label(right, font=(_F, 9, "bold"), bg=SURFACE,
                          cursor="hand2", padx=12, pady=3)

            def _style():
                if is_queued(name):
                    tg.config(text=f"✓ {base_txt}", fg="#08080a", bg=base_fg)
                else:
                    tg.config(text=base_txt, fg=base_fg, bg=SURFACE)

            tg.bind("<Button-1>", lambda e, en=entry: queue_toggle(en))
            tg.bind("<Enter>", lambda e: (tg.config(fg=TEXT) if not is_queued(name) else None))
            tg.bind("<Leave>", lambda e: _style())
            tg.pack(side="left", padx=2)
            _Tooltip(tg, f"Dodaj „{base_txt} {dname}” do operatora zmian (na dole).")
            _style()
            sync = _style

            # Mode chips — pick which TURBO / Features modes stop this service.
            mc = tk.Frame(right, bg=SURFACE)
            mc.pack(side="left", padx=(8, 0))
            all_labels.append(mc)
            for mkey, letter, color in _MODES:
                ch = _mode_chip(mc, name, mkey, letter, color,
                                name in mode_sets.get(mkey, set()), on_mode_toggle)
                ch.pack(side="left", padx=1)

        _hover_row(row, all_labels)
        return sync

    def _paint():
        for w in row.winfo_children():
            try: w.destroy()
            except Exception: pass
        state["sync"] = _build()

    _paint()
    if row_apis is not None:
        row_apis[name] = {"refresh": _paint, "sync": (lambda: state["sync"]())}


def _quick_card(strip, item, answers, on_answer, after_answer):
    """One Quick-setup tile. Persists its TAK/NIE answer and shows a corner ZMIEŃ
    to flip it later — the layout never shifts (header reserves the corner slot)."""
    label = item["label"]
    card = tk.Frame(strip, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER)
    card.pack(side="left", padx=(0, 6), pady=2)
    inner = tk.Frame(card, bg=SURFACE)
    inner.pack(padx=8, pady=6, fill="both")

    head = tk.Frame(inner, bg=SURFACE)
    head.pack(fill="x")
    tk.Label(head, text=label, font=(_F, 8, "bold"), bg=SURFACE, fg=TEXT).pack(side="left")
    change = tk.Label(head, text="", font=(_F, 7, "bold"), bg=SURFACE, fg=SUB, cursor="hand2")
    change.pack(side="right")
    change.bind("<Enter>", lambda e: change.config(fg=TEXT) if change.cget("text") else None)
    change.bind("<Leave>", lambda e: change.config(fg=SUB)  if change.cget("text") else None)

    tk.Label(inner, text=(item.get("q_pl") or item.get("q_en") or ""),
             font=(_F, 7), bg=SURFACE, fg=SUB, wraplength=150,
             justify="left").pack(anchor="w", pady=(1, 4))

    content = tk.Frame(inner, bg=SURFACE)
    content.pack(anchor="w", fill="x")

    def _buttons():
        for w in content.winfo_children():
            w.destroy()
        change.config(text="")
        change.unbind("<Button-1>")
        _btn(content, "Nie używam", "#f87171", SURFACE, "#fca5a5",
             lambda: _answer(False), 7).pack(side="left", padx=(0, 4))
        _btn(content, "Używam", "#34d399", SURFACE, "#6ee7b7",
             lambda: _answer(True), 7).pack(side="left")

    def _state(used):
        for w in content.winfo_children():
            w.destroy()
        if used:
            tk.Label(content, text="TAK", font=(_F, 8, "bold"),
                     bg=SURFACE, fg=GREEN).pack(side="left")
            tk.Label(content, text=" — zostawiam", font=(_F, 7),
                     bg=SURFACE, fg=MUTED).pack(side="left")
        else:
            tk.Label(content, text="NIE", font=(_F, 8, "bold"),
                     bg=SURFACE, fg=RED).pack(side="left")
            tk.Label(content, text=" — dodano do MANAGER", font=(_F, 7),
                     bg=SURFACE, fg=GREEN).pack(side="left")
        change.config(text="ZMIEŃ", fg=SUB)
        change.bind("<Button-1>", lambda e: _buttons())

    def _answer(used):
        answers[label] = "yes" if used else "no"
        _save_quick(answers)
        on_answer(item, used)
        _state(used)
        after_answer()

    prev = answers.get(label)
    _state(prev == "yes") if prev in ("yes", "no") else _buttons()


def _recommended_strip(parent, on_answer):
    """Guided Quick-setup row. Remembers answers across launches; once every card is
    answered it collapses to a thin full-width 'QUICK SETUP CONFIGURED' banner."""
    if not RECOMMENDED:
        return
    answers = _load_quick()

    wrap = tk.Frame(parent, bg=BG)
    wrap.pack(fill="x", padx=20, pady=(2, 4))
    cards_holder = tk.Frame(wrap, bg=BG)
    banner       = tk.Frame(wrap, bg=BG)

    def _all_answered():
        return all(it["label"] in answers for it in RECOMMENDED)

    def _show_cards():
        banner.pack_forget()
        cards_holder.pack(fill="x")

    def _show_banner():
        cards_holder.pack_forget()
        for w in banner.winfo_children():
            w.destroy()
        bar = tk.Frame(banner, bg="#0c1a12", height=22)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="✓  QUICK SETUP CONFIGURED", font=(_F, 8, "bold"),
                 bg="#0c1a12", fg=GREEN).pack(side="left", padx=12)
        chg = tk.Label(bar, text="CHANGE", font=(_F, 7, "bold"), bg="#0c1a12",
                       fg=SUB, cursor="hand2", padx=10)
        chg.pack(side="left")
        chg.bind("<Button-1>", lambda e: _show_cards())
        chg.bind("<Enter>", lambda e: chg.config(fg=TEXT))
        chg.bind("<Leave>", lambda e: chg.config(fg=SUB))
        banner.pack(fill="x")

    cv = tk.Canvas(cards_holder, bg=BG, highlightthickness=0, height=92)
    cv.pack(fill="x")
    strip = tk.Frame(cv, bg=BG)
    cv.create_window((0, 0), window=strip, anchor="nw")
    strip.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
    cv.bind("<Shift-MouseWheel>",
            lambda e: cv.xview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _maybe_collapse():
        if _all_answered():
            _show_banner()

    for item in RECOMMENDED:
        _quick_card(strip, item, answers, on_answer, _maybe_collapse)

    _show_banner() if _all_answered() else _show_cards()


def _modes_panel(parent, mode_sets: dict, get_active, set_active):
    """Bottom bar: clickable per-mode chips that set the active profile (synced with
    the Features modes), plus a 'Current profile' label that flashes Saving/Saved!."""
    panel = tk.Frame(parent, bg=TURBO_BG, highlightthickness=1, highlightbackground=TURBO_BD)
    panel.pack(fill="x", side="bottom")
    row = tk.Frame(panel, bg=TURBO_BG)
    row.pack(fill="x", padx=14, pady=6)
    tk.Label(row, text="MODES", font=(_F, 8, "bold"),
             bg=TURBO_BG, fg=TEXT).pack(side="left", padx=(0, 12))

    active = {"key": get_active()}
    chips  = {}

    cur_lbl = tk.Label(row, text="", font=(_F, 8, "bold"), bg=TURBO_BG, fg=VIOLET)
    cur_lbl.pack(side="right")

    def _cur_text():
        return f"Current profile: {active['key'].upper()}"

    def _paint():
        for mkey, (fr, cl) in chips.items():
            on = (mkey == active["key"])
            fr.config(highlightbackground="#8b5cf6" if on else TURBO_BD)
            cl.config(fg=TEXT if on else SUB)

    for mkey, letter, color in _MODES:
        fr = tk.Frame(row, bg=TURBO_BG, cursor="hand2",
                      highlightthickness=1, highlightbackground=TURBO_BD)
        fr.pack(side="left", padx=(0, 10))
        ll = tk.Label(fr, text=letter, font=(_F, 8, "bold"),
                      bg=color, fg="#08080a", width=2)
        ll.pack(side="left")
        cl = tk.Label(fr, text=f" {mkey.capitalize()}: {len(mode_sets[mkey])} ",
                      font=(_F, 8), bg=TURBO_BG, fg=SUB)
        cl.pack(side="left")
        chips[mkey] = (fr, cl)

        def _click(_=None, k=mkey):
            active["key"] = k
            set_active(k)
            _paint()
            cur_lbl.config(text=_cur_text(), fg=VIOLET)
        for w in (fr, ll, cl):
            w.bind("<Button-1>", _click)

    cur_lbl.config(text=_cur_text())
    _paint()

    class _Ctl:
        def refresh(self):
            for mkey, (fr, cl) in chips.items():
                cl.config(text=f" {mkey.capitalize()}: {len(mode_sets[mkey])} ")

        def flash(self):
            if not cur_lbl.winfo_exists():
                return
            cur_lbl.config(text="Saving…", fg=AMBER)
            def _saved():
                if cur_lbl.winfo_exists():
                    cur_lbl.config(text="Saved!", fg=GREEN)
            def _restore():
                if cur_lbl.winfo_exists():
                    cur_lbl.config(text=_cur_text(), fg=VIOLET)
            panel.after(500,  _saved)
            panel.after(1500, _restore)

    return _Ctl()


def _stat_text(total, running):
    return f"  {total} services catalogued   ·   {running} running"


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
    mode_sets = ({m: set(turbo_services.get_profile_services(m)) for m, _, _ in _MODES}
                 if _HAS_TURBO else {m: set() for m, _, _ in _MODES})

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

    stat_lbl = tk.Label(right_col, text=_stat_text(total, running),
                        font=(_F, 8), bg=BG, fg=MUTED)
    stat_lbl.pack(side="right")

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

    def on_mode_toggle(svc_name: str, mkey: str, enabled: bool):
        if _HAS_TURBO:
            turbo_services.set_membership(mkey, svc_name, enabled)
        (mode_sets[mkey].add if enabled else mode_sets[mkey].discard)(svc_name)
        modes.refresh()
        modes.flash()

    def on_answer(item, used: bool):
        # "Używam" -> keep running (remove from MANAGER); "Nie używam" -> add to MANAGER
        for svc in item.get("services", []):
            if _HAS_TURBO:
                turbo_services.set_membership("manager", svc, not used)
            (mode_sets["manager"].discard if used else mode_sets["manager"].add)(svc)
        modes.refresh()
        modes.flash()

    _recommended_strip(page, on_answer)

    content_wrap = tk.Frame(page, bg=BG)
    content_wrap.pack(fill="both", expand=True)

    inner, cv = _scrollable(content_wrap)

    section_bodies: dict[str, tk.Frame] = {}
    collapsed_vars: dict[str, tk.BooleanVar] = {}

    svc_prefs = _load_svc_prefs()

    # ── Operator-drawer queue model ─────────────────────────────────────────
    # Each row's Wyłącz/Włącz adds a change here; the drawer applies them as a
    # single batch on Zatwierdź. No per-row confirm dialogs.
    row_apis: dict[str, dict] = {}
    drawer_holder = {"d": None}            # set once the drawer is built (below)

    def is_queued(svc_name: str) -> bool:
        d = drawer_holder["d"]
        return bool(d and d.is_queued(svc_name))

    def queue_toggle(entry: dict):
        d = drawer_holder["d"]
        if not d:
            return
        n       = entry["name"]
        running = (statuses.get(n) == "running")
        action  = "stop" if running else "start"
        d.toggle({
            "id":      n,
            "label":   f"{entry['display']}  ·  {action.upper()}",
            "warn":    entry.get("cat") in ("recommended", "essential"),
            "payload": {"name": n, "action": action},
        })

    def _sync_queue_buttons():
        # Re-style every row's toggle to match the current queue.
        for api in row_apis.values():
            try: api["sync"]()
            except Exception: pass

    def _apply_changes(items: list):
        if not is_admin:
            messagebox.showwarning("Admin required",
                "PC Workman must run as Administrator to control services.")
            return
        lines = "\n".join(
            f"   •  {it['payload']['action'].upper()}   {it['label'].split('  ·')[0]}"
            for it in items)
        if not messagebox.askyesno("Potwierdź zmiany",
                f"Zatwierdzić {len(items)} zmian(y)?\n\n{lines}"):
            return

        payloads = [dict(it["payload"]) for it in items]

        def _do():
            from datetime import datetime as _dt
            for p in payloads:
                n, action = p["name"], p["action"]
                ok, _ = _sc_run([action, n])
                _log_change(n, action, ok)
                if ok:
                    statuses[n] = "running" if action == "start" else "stopped"
                    ts = _dt.now().strftime("%Y-%m-%d %H:%M")
                    svc_prefs.setdefault(n, {}).update({
                        "last_action": action,
                        "last_change": ts,
                        "changed_by":  "UŻYTKOWNIK",
                    })
            _save_svc_prefs(svc_prefs)
            page.after(0, _after)

        def _after():
            for p in payloads:
                api = row_apis.get(p["name"])
                if api:
                    try: api["refresh"]()
                    except Exception: pass
            d = drawer_holder["d"]
            if d:
                d.clear()

        threading.Thread(target=_do, daemon=True).start()

    # ── 2×2 grid: row1 = UNNEEDED | OPTIONAL, row2 = RECOMMENDED | ESSENTIAL ──
    #    (configurator order: safest-to-disable at the top, never-touch at the bottom)
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
    col_map.update(_make_col_pair(inner, "unnecessary", "optional"))
    tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=8)
    col_map.update(_make_col_pair(inner, "recommended", "essential"))

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
            _service_row(body, entry, statuses, mode_sets,
                         locked=locked, is_admin=is_admin,
                         on_mode_toggle=on_mode_toggle,
                         queue_toggle=queue_toggle, is_queued=is_queued,
                         svc_prefs=svc_prefs, row_apis=row_apis)

        if overflow:
            # Overflow frame — hidden by default, shown by expand banner
            overflow_frame = tk.Frame(body, bg=BG)
            _exp_open = [False]

            def _build_overflow(of=overflow_frame, ol=overflow, lkd=locked):
                for oe in ol:
                    _service_row(of, oe, statuses, mode_sets,
                                 locked=lkd, is_admin=is_admin,
                                 on_mode_toggle=on_mode_toggle,
                                 queue_toggle=queue_toggle, is_queued=is_queued,
                                 svc_prefs=svc_prefs, row_apis=row_apis)

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
                                  bld=_build_overflow,
                                  bar=expand_bar):   # capture THIS tier's bar (late-binding fix)
                eo[0] = not eo[0]
                if eo[0]:
                    if not eb[0]:
                        bld()
                        eb[0] = True
                    ef.pack(fill="x", after=bar)
                    el.config(text="∧  Zwiń  ∧")
                else:
                    ef.pack_forget()
                    el.config(text=f"∨  Rozwiń więcej ({len(ol)})  ∨")
                inner.event_generate("<Configure>")

            expand_bar.bind("<Button-1>", _toggle_overflow)
            expand_lbl.bind("<Button-1>", _toggle_overflow)
            expand_bar.bind("<Enter>", lambda e, w=expand_lbl: w.config(fg=TEXT))
            expand_bar.bind("<Leave>", lambda e, w=expand_lbl: w.config(fg=MUTED))

    tk.Frame(inner, bg=BG, height=10).pack()

    # ── Shared operator drawer — always visible at the very bottom ───────────
    drawer = OperatorDrawer(
        page, pack_side="bottom",
        on_confirm=_apply_changes,
        on_change=_sync_queue_buttons,
        title=_t("operator.title", default="Zmiany do zatwierdzenia"),
    )
    drawer_holder["d"] = drawer

    active_get = turbo_services.get_active_profile if _HAS_TURBO else (lambda: "gaming")
    active_set = turbo_services.set_active_profile if _HAS_TURBO else (lambda k: None)
    modes = _modes_panel(page, mode_sets, active_get, active_set)

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
