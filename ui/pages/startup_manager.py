"""
Startup Manager - PC Workman HCK 1.7.3
Redesigned UX:
  · Split layout: Needs attention (left 50%) + All entries 2-col grid (right 50%)
  · Subtle "click to queue" banner below tab bar
  · Click any active entry -> adds to disable queue
  · Bottom confirmation drawer (black-bordeau, hck_GPT style)
  · Critical process detection + warning in drawer
  · "Disabled" tab -> full-width view
"""
import tkinter as tk
from tkinter import messagebox
import threading, os, json

try:
    import winreg; _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False

try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except Exception:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_F    = _UIF
_M    = _MONOF
_BODY = _UIF
_MONO = _MONOF

# ── Palette ───────────────────────────────────────────────────────────────────
BG         = "#090c12"
SURFACE    = "#0d1117"
HOVER      = "#101a22"
HOVER_Q    = "#120d1a"      # queue-item hover (purplish tint)
BORDER     = "#14202e"
SEP        = "#141d28"
TEXT       = "#cdd8e8"
SUB        = "#66788f"
MUTED      = "#344256"
ACCENT     = "#7c3aed"
AMBER      = "#d97706"
GREEN      = "#16a34a"
RED        = "#dc2626"
CHIP_A     = "#1c1040"

# Redesign-specific
BORDEAU       = "#5a0e20"       # dark red-bordeau border
BORDEAU_MID   = "#3d0a16"       # medium bordeau for backgrounds
BORDEAU_LIGHT = "#c07090"       # lighter bordeau text / accents
DRAWER_BG     = "#060408"       # near-black + subtle purple tint
BANNER_BG     = "#0c1219"       # very subtle banner background
TAB_ACTIVE_BG = "#0f1d2d"       # active tab highlight (soft dark-blue)
TAB_ACTIVE_FG = "#8cb4d2"       # active tab text
PANEL_DIV     = "#111a26"       # divider between left/right panels
QUEUED_BG     = "#0d0915"       # queued-entry tint in list

_IC = {"high": RED,   "medium": AMBER, "low": GREEN}
_IL = {"high": "H",   "medium": "M",   "low": "L"}
_IB = {"high": "#1c0808", "medium": "#1c1008", "low": "#081c0e"}
_IF = {"high": "#fca5a5", "medium": "#fcd34d", "low": "#86efac"}

# Exe fragments that warrant a critical warning before disabling
_CRITICAL_FRAGS = frozenset({
    "realtek", "audio", "sound", "nahimic", "conexant", "hdaudio",
    "nvidia", "amd", "displaylink",
    "windowsdefender", "defender", "malwarebytes", "avast", "avg",
    "eset", "kaspersky", "bitdefender", "mbam",
})

_KNOWN: dict[str, tuple[str, str, str]] = {
    "teams.exe":              ("high",   "disable", "High RAM & CPU at boot. Open when you need a meeting."),
    "discord.exe":            ("medium", "delay",   "Chat app - launch on demand. Saves seconds at boot."),
    "slack.exe":              ("high",   "disable", "Heavy memory footprint. Open manually at work start."),
    "zoom.exe":               ("medium", "delay",   "Video client. Only needed when joining a call."),
    "spotify.exe":            ("medium", "delay",   "Music player. Start when you actually want to listen."),
    "skype.exe":              ("medium", "delay",   "Legacy VoIP - start manually if still used."),
    "onedrive.exe":           ("medium", "delay",   "Cloud sync runs fine when delayed or started on-demand."),
    "dropbox.exe":            ("medium", "delay",   "Cloud sync - can start delayed after login."),
    "googledrivesync.exe":    ("medium", "delay",   "Google Drive sync - delayed start works fine."),
    "steam.exe":              ("high",   "disable", "Game launcher. No reason to start with Windows."),
    "epicgameslauncher.exe":  ("high",   "disable", "Epic Games - opens fine on demand."),
    "ea_desktop.exe":         ("high",   "disable", "EA Desktop - large, start manually when gaming."),
    "battle.net.exe":         ("high",   "disable", "Battle.net - open when you want to play."),
    "upc.exe":                ("medium", "disable", "Ubisoft Connect - can start on demand."),
    "origin.exe":             ("high",   "disable", "EA Origin - large process, open when gaming."),
    "adobeupdatedaemon.exe":  ("medium", "disable", "Adobe updater - update manually from the app."),
    "acrobat.exe":            ("medium", "delay",   "PDF viewer - only needed when opening PDF files."),
    "ccleaner64.exe":         ("low",    "keep",    "Lightweight cleaner - fine to keep in startup."),
    "malwarebytes.exe":       ("low",    "keep",    "Security tool - recommended to keep running."),
    "msiafterburner.exe":     ("low",    "keep",    "GPU OC utility - keep if actively using fan curves."),
    "hwinfo64.exe":           ("low",    "keep",    "Hardware monitor - lightweight, keep if using sensors."),
    "corsairhid.exe":         ("low",    "keep",    "Corsair iCUE - needed for RGB and macros."),
    "razercentralservice.exe":("low",    "keep",    "Razer Synapse - needed for G keys and lighting."),
    "lghub.exe":              ("low",    "keep",    "Logitech G HUB - needed for G-series devices."),
    "curve.exe":              ("medium", "delay",   "NZXT CAM - can delay startup without issues."),
}

# ── Registry helpers ──────────────────────────────────────────────────────────

_REG_PATHS = [
    (winreg.HKEY_CURRENT_USER  if _HAS_WINREG else None,
     r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
    (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
     r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
    (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM32"),
] if _HAS_WINREG else []

try:
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    import sys as _sys
    _APP_DIR = os.path.dirname(_sys.executable) if getattr(_sys, "frozen", False) \
               else os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

_PREFS_PATH = os.path.join(_APP_DIR, "data", "cache", "startup_prefs.json")


def _read_startup_entries() -> list[dict]:
    if not _HAS_WINREG:
        return []
    entries, seen = [], set()
    for hive, path, hive_label in _REG_PATHS:
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
        except OSError:
            continue
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i); i += 1
            except OSError:
                break
            exe = os.path.basename(value.strip('"').split()[0]).lower() if value else ""
            kid = f"{hive_label}:{name.lower()}"
            if kid in seen: continue
            seen.add(kid)
            impact, rec, desc = _KNOWN.get(exe, ("low", "keep", ""))
            entries.append({"id": kid, "name": name, "value": value, "exe": exe,
                            "hive": hive_label, "hive_const": hive, "reg_path": path,
                            "impact": impact, "rec": rec, "desc": desc})
        winreg.CloseKey(key)
    return entries


def _load_prefs() -> dict:
    try:
        with open(_PREFS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_prefs(data: dict):
    os.makedirs(os.path.dirname(_PREFS_PATH), exist_ok=True)
    try:
        with open(_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _delete_startup_entry(hive_const, path: str, name: str) -> bool:
    if not _HAS_WINREG: return False
    try:
        key = winreg.OpenKey(hive_const, path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def _restore_startup_entry(hive_const, path: str, name: str, value: str) -> bool:
    """Write the entry back to the registry (re-enable startup)."""
    if not _HAS_WINREG: return False
    try:
        key = winreg.OpenKey(hive_const, path, 0,
                             winreg.KEY_SET_VALUE | winreg.KEY_CREATE_SUB_KEY)
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


# Map hive label -> (hive_const, reg_path) for restore
_HIVE_MAP = {
    "HKCU":   (winreg.HKEY_CURRENT_USER  if _HAS_WINREG else None,
               r"Software\Microsoft\Windows\CurrentVersion\Run"),
    "HKLM":   (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
               r"Software\Microsoft\Windows\CurrentVersion\Run"),
    "HKLM32": (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
               r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
} if _HAS_WINREG else {}


def _is_critical(exe: str) -> bool:
    exe_lower = (exe or "").lower()
    return any(frag in exe_lower for frag in _CRITICAL_FRAGS)


# ── Widget helpers ────────────────────────────────────────────────────────────

class _Tooltip:
    def __init__(self, widget, text: str, delay: int = 650):
        self._w, self._text, self._delay = widget, text, delay
        self._job = self._tw = None
        widget.bind("<Enter>",       self._sched,  add="+")
        widget.bind("<Leave>",       self._cancel, add="+")
        widget.bind("<ButtonPress>", self._cancel, add="+")

    def _sched(self, _=None):
        self._cancel()
        self._job = self._w.after(self._delay, self._show)

    def _cancel(self, _=None):
        if self._job: self._w.after_cancel(self._job); self._job = None
        if self._tw:  self._tw.destroy();               self._tw  = None

    def _show(self):
        x = self._w.winfo_rootx() + 8
        y = self._w.winfo_rooty() + self._w.winfo_height() + 4
        self._tw = tw = tk.Toplevel(self._w)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self._text, font=(_F, 9), bg="#1a2540", fg=TEXT,
                 padx=10, pady=6, wraplength=280, justify="left").pack()


def _scrollable_frame(parent, bg=BG):
    """Returns (inner_frame, canvas) - inner_frame is where you pack content."""
    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill="both", expand=True)
    cv = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    sb = tk.Scrollbar(outer, orient="vertical", command=cv.yview,
                      bg=bg, troughcolor=bg, highlightthickness=0, bd=0, width=4)
    inner = tk.Frame(cv, bg=bg)
    wid = cv.create_window((0, 0), window=inner, anchor="nw")
    cv.bind("<Configure>", lambda e: cv.itemconfig(wid, width=e.width))
    inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))

    def _scroll(e):
        try: cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception: pass

    cv.bind("<MouseWheel>", _scroll)
    inner.bind("<MouseWheel>", _scroll)
    sb.pack(side="right", fill="y")
    cv.pack(side="left", fill="both", expand=True)
    cv.configure(yscrollcommand=sb.set)
    return inner, cv


def _bind_scroll(widget, canvas):
    def _scroll(e):
        try: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception: pass
    widget.bind("<MouseWheel>", _scroll, add="+")


# ── Compact entry row (click-to-queue) ───────────────────────────────────────

def _compact_row(parent, entry: dict, prefs: dict,
                 on_queue, queued_ids: set,
                 two_col: bool = False,
                 running_set: set = None):
    """
    Compact clickable entry row.
    Click -> adds entry to disable queue (shows bottom drawer).
    two_col=True: slightly narrower layout for 2-column grid.
    running_set: set of lowercase exe names currently running (for ACTIVE NOW badge).
    """
    eid    = entry["id"]
    impact = entry["impact"]
    status = prefs.get(eid, {}).get("status", "active")
    name   = entry["name"]
    exe    = entry["exe"] or "-"
    desc   = entry.get("desc", "")
    is_dis = (status != "active")
    in_q   = (eid in queued_ids)

    base_bg = QUEUED_BG if in_q else SURFACE
    hov_bg  = HOVER_Q   if in_q else HOVER

    row = tk.Frame(parent, bg=base_bg, bd=0,
                   cursor="arrow" if is_dis else "hand2")
    row.pack(fill="x", padx=0, pady=0)

    # Left accent bar
    accent_col = ACCENT if in_q else (_IC.get(impact, MUTED) if not is_dis else MUTED)
    accent = tk.Frame(row, bg=accent_col, width=2)
    accent.pack(side="left", fill="y")
    accent.pack_propagate(False)

    body = tk.Frame(row, bg=base_bg)
    body.pack(side="left", fill="both", expand=True,
              padx=(7, 4), pady=(4, 3))

    # Line 1: name + impact badge
    line1 = tk.Frame(body, bg=base_bg)
    line1.pack(fill="x")

    max_name = 22 if two_col else 30
    name_lbl = tk.Label(line1,
                        text=name[:max_name] + ("…" if len(name) > max_name else ""),
                        font=(_F, 9, "bold"), bg=base_bg, fg=MUTED if is_dis else TEXT,
                        anchor="w")
    name_lbl.pack(side="left")

    # "ACTIVE NOW" badge — green — if exe is currently running
    if not is_dis and running_set is not None:
        exe_l = (entry.get("exe") or "").lower()
        if exe_l and exe_l in running_set:
            tk.Label(line1, text="● ACTIVE NOW",
                     font=(_F, 6, "bold"),
                     bg="#052e16", fg="#22c55e",
                     padx=4, pady=1).pack(side="left", padx=(4, 0))

    if not is_dis:
        tag = tk.Label(line1, text=_IL.get(impact, "?"),
                       font=(_F, 6, "bold"),
                       bg=_IB.get(impact, "#111"),
                       fg=_IF.get(impact, SUB),
                       padx=4, pady=1)
        tag.pack(side="left", padx=(5, 0))
    else:
        tk.Label(line1, text="OFF", font=(_F, 7),
                 bg=base_bg, fg=MUTED).pack(side="left", padx=(6, 0))

    if in_q:
        tk.Label(line1, text="✓", font=(_F, 8, "bold"),
                 bg=base_bg, fg=ACCENT).pack(side="right", padx=(0, 4))

    # Line 2: exe
    exe_lbl = tk.Label(body,
                       text=(exe[:26] if two_col else exe[:34]),
                       font=(_F, 7), bg=base_bg, fg=MUTED, anchor="w")
    exe_lbl.pack(anchor="w")

    # Separator line below row
    sep = tk.Frame(parent, bg=SEP, height=1)
    sep.pack(fill="x")

    if desc and not is_dis:
        _Tooltip(name_lbl, desc)
        _Tooltip(row,      desc)

    # All interactive widgets
    all_w = [row, body, line1, name_lbl, exe_lbl, accent]
    try: all_w.append(tag)
    except Exception: pass

    # Hover
    def _h_on(e):
        for w in all_w:
            try: w.config(bg=hov_bg)
            except Exception: pass

    def _h_off(e):
        for w in all_w:
            try: w.config(bg=base_bg)
            except Exception: pass

    for w in all_w:
        w.bind("<Enter>", _h_on,  add="+")
        w.bind("<Leave>", _h_off, add="+")

    # Click handler - only for active (non-disabled) entries
    if not is_dis:
        def _click(e, _entry=entry):
            on_queue(_entry)
        for w in all_w:
            w.bind("<Button-1>", _click, add="+")

    return row, sep


# ── Drawer helpers ────────────────────────────────────────────────────────────

DRAWER_H = 100   # drawer height in pixels when visible


def _build_drawer_content(drawer: tk.Frame, queue: list[dict],
                          on_confirm, on_back):
    """Rebuild drawer content from queue list."""
    for w in drawer.winfo_children():
        w.destroy()

    # Top bordeau line
    tk.Frame(drawer, bg=BORDEAU, height=1).pack(fill="x")

    body = tk.Frame(drawer, bg=DRAWER_BG)
    body.pack(fill="both", expand=True, padx=0, pady=0)

    # ── Left: queue list ──────────────────────────────────────────────────────
    left = tk.Frame(body, bg=DRAWER_BG)
    left.pack(side="left", fill="both", expand=True, padx=(14, 6), pady=8)

    has_critical = any(_is_critical(e["exe"]) for e in queue)

    for e in queue:
        crit = _is_critical(e["exe"])
        col  = AMBER if crit else "#c8d8e8"
        icon = "⚠ " if crit else "- "
        tk.Label(left,
                 text=f"{icon}WYŁĄCZ z Startup:  {e['name'][:32]}",
                 font=(_F, 8), bg=DRAWER_BG, fg=col,
                 anchor="w").pack(anchor="w")

    if has_critical:
        tk.Label(left,
                 text="⚠  Uwaga: wykryto sterownik lub narzędzie systemowe - wyłącz z ostrożnością.",
                 font=(_F, 7), bg=DRAWER_BG, fg=AMBER,
                 anchor="w").pack(anchor="w", pady=(5, 0))

    # ── Vertical bordeau separator ────────────────────────────────────────────
    tk.Frame(body, bg=BORDEAU, width=1).pack(side="left", fill="y", pady=8)

    # ── Right: action buttons ─────────────────────────────────────────────────
    right = tk.Frame(body, bg=DRAWER_BG)
    right.pack(side="left", padx=16, pady=0, fill="y")

    # centre buttons vertically
    spacer_top = tk.Frame(right, bg=DRAWER_BG)
    spacer_top.pack(fill="y", expand=True)

    confirm = tk.Label(right, text="Zatwierdź",
                       font=(_F, 9, "bold"), fg=BORDEAU_LIGHT, bg=BORDEAU_MID,
                       padx=14, pady=5, cursor="hand2")
    confirm.pack()
    confirm.bind("<Button-1>", lambda e: on_confirm())
    confirm.bind("<Enter>",    lambda e: confirm.config(fg=TEXT))
    confirm.bind("<Leave>",    lambda e: confirm.config(fg=BORDEAU_LIGHT))

    tk.Frame(right, bg=BORDEAU, height=1).pack(fill="x", pady=5)

    back = tk.Label(right, text="Wróć",
                    font=(_F, 9), fg=SUB, bg=DRAWER_BG,
                    padx=14, pady=3, cursor="hand2")
    back.pack()
    back.bind("<Button-1>", lambda e: on_back())
    back.bind("<Enter>",    lambda e: back.config(fg=TEXT))
    back.bind("<Leave>",    lambda e: back.config(fg=SUB))

    spacer_bot = tk.Frame(right, bg=DRAWER_BG)
    spacer_bot.pack(fill="y", expand=True)


# ── Panel builders ────────────────────────────────────────────────────────────

def _build_needs_attention_panel(parent: tk.Frame, flagged: list[dict],
                                  prefs: dict, on_queue, queued_ids: set):
    """Startup Menu panel — flagged entries (single column, compact rows)."""
    # Header
    hdr = tk.Frame(parent, bg=BG)
    hdr.pack(fill="x", padx=10, pady=(8, 4))
    tk.Label(hdr, text="Startup Menu", font=(_F, 8, "bold"),
             bg=BG, fg=AMBER).pack(side="left")
    tk.Label(hdr, text=f"  {len(flagged)}", font=(_F, 8),
             bg=BG, fg=SUB).pack(side="left")

    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=10)

    if not flagged:
        _EmptyAttention = tk.Frame(parent, bg=BG)
        _EmptyAttention.pack(fill="x", padx=14, pady=20)
        tk.Label(_EmptyAttention,
                 text="✓  Startup looks clean.",
                 font=(_F, 11, "bold"), bg=BG, fg=GREEN,
                 anchor="w").pack(anchor="w", pady=(0, 10))
        tk.Label(_EmptyAttention,
                 text="To tutaj nie przegapisz potencjalnej złośliwej\n"
                      "aplikacji, która potajemnie chciała wejść\n"
                      "w działanie systemu przy starcie.",
                 font=(_F, 8), bg=BG, fg="#2a4a5f",
                 justify="left", anchor="w").pack(anchor="w")
        return

    inner, cv = _scrollable_frame(parent, bg=BG)

    for e in flagged:
        _compact_row(inner, e, prefs, on_queue, queued_ids, two_col=False)

    tk.Frame(inner, bg=BG, height=6).pack()


def _build_all_entries_panel(parent: tk.Frame, entries: list[dict],
                              prefs: dict, on_queue, queued_ids: set,
                              two_col: bool = True):
    """Left panel - All entries. two_col=False for wider single-column layout."""
    # Build running exe set for ACTIVE NOW badge
    _running: set = set()
    try:
        import psutil as _ps
        for _p in _ps.process_iter(["name"]):
            try: _running.add(_p.info["name"].lower())
            except Exception: pass
    except Exception: pass

    # Header
    hdr = tk.Frame(parent, bg=BG)
    hdr.pack(fill="x", padx=10, pady=(8, 4))
    tk.Label(hdr, text="All entries", font=(_F, 8, "bold"),
             bg=BG, fg=TAB_ACTIVE_FG).pack(side="left")
    tk.Label(hdr, text=f"  {len(entries)}", font=(_F, 8),
             bg=BG, fg=SUB).pack(side="left")

    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=10)

    inner, cv = _scrollable_frame(parent, bg=BG)

    if two_col:
        grid = tk.Frame(inner, bg=BG)
        grid.pack(fill="x", padx=4, pady=2)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        for i, e in enumerate(entries):
            col     = i % 2
            row_num = i // 2
            cell = tk.Frame(grid, bg=BG)
            cell.grid(row=row_num, column=col, sticky="ew", padx=2, pady=1)
            cell.grid_columnconfigure(0, weight=1)
            _bind_scroll(cell, cv)
            row_w, sep_w = _compact_row(cell, e, prefs, on_queue, queued_ids, two_col=True)
            _bind_scroll(row_w, cv)
            _bind_scroll(sep_w, cv)
    else:
        # Single-column layout with ACTIVE NOW badge
        for e in entries:
            row_w, sep_w = _compact_row(inner, e, prefs, on_queue, queued_ids,
                                        two_col=False,
                                        running_set=_running)
            _bind_scroll(row_w, cv)
            _bind_scroll(sep_w, cv)

    tk.Frame(inner, bg=BG, height=6).pack()


def _build_disabled_panel(parent: tk.Frame, disabled: list[dict],
                           prefs: dict, on_restore_done):
    """Full-width view for Disabled tab."""
    hdr = tk.Frame(parent, bg=BG)
    hdr.pack(fill="x", padx=16, pady=(10, 6))
    tk.Label(hdr, text="Disabled entries", font=(_F, 8, "bold"),
             bg=BG, fg=SUB).pack(side="left")
    tk.Label(hdr, text=f"  {len(disabled)}", font=(_F, 8),
             bg=BG, fg=MUTED).pack(side="left")
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=16)

    if not disabled:
        tk.Label(parent, text="No disabled entries yet.",
                 font=(_F, 10), bg=BG, fg=SUB).pack(pady=40)
        return

    inner, _ = _scrollable_frame(parent, bg=BG)

    for e in disabled:
        eid  = e["id"]
        name = e["name"]
        exe  = e["exe"] or "-"

        row = tk.Frame(inner, bg=SURFACE)
        row.pack(fill="x", padx=14, pady=1)

        accent = tk.Frame(row, bg=MUTED, width=2)
        accent.pack(side="left", fill="y")
        accent.pack_propagate(False)

        body = tk.Frame(row, bg=SURFACE)
        body.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=(4, 3))

        tk.Label(body, text=name[:40], font=(_F, 9, "bold"),
                 bg=SURFACE, fg=MUTED, anchor="w").pack(anchor="w")
        tk.Label(body, text=exe, font=(_F, 7), bg=SURFACE, fg=MUTED, anchor="w").pack(anchor="w")

        # "Kto: UŻYTKOWNIK · data" — show if saved
        pdata   = prefs.get(eid, {})
        dis_by  = pdata.get("disabled_by", "")
        dis_at  = pdata.get("disabled_at", "")
        if dis_by:
            who_str = f"Kto: {dis_by}"
            if dis_at:
                who_str += f"  ·  {dis_at}"
            tk.Label(body, text=who_str,
                     font=(_F, 7), bg=SURFACE, fg="#16a34a", anchor="w").pack(anchor="w")

        right = tk.Frame(row, bg=SURFACE)
        right.pack(side="right", padx=10, pady=4)

        tk.Label(right, text="DISABLED", font=(_F, 7, "bold"),
                 bg=SURFACE, fg=MUTED).pack(anchor="e")

        def _make_restore(entry=e, r=row):
            def _do():
                # Write entry back to registry so Windows actually starts it again
                hc  = entry.get("hive_const")
                rp  = entry.get("reg_path", "")
                val = entry.get("value", "")
                if hc and rp and val:
                    ok = _restore_startup_entry(hc, rp, entry["name"], val)
                    if not ok:
                        import tkinter.messagebox as _mb
                        _mb.showerror(
                            "Nie udało się przywrócić",
                            f"Nie można wpisać '{entry['name']}' z powrotem do rejestru.\n"
                            "Uruchom PC Workman jako Administrator."
                        )
                        return
                # Remove from prefs entirely — entry will appear as active next scan
                prefs.pop(entry["id"], None)
                _save_prefs(prefs)
                r.destroy()
                on_restore_done()
            return _do

        rb = tk.Label(right, text="Restore", font=(_F, 8),
                      fg=SUB, bg=SURFACE, cursor="hand2", padx=6, pady=2)
        rb.pack(anchor="e", pady=(3, 0))
        rb.bind("<Button-1>", lambda e, fn=_make_restore(): fn())
        rb.bind("<Enter>",    lambda e, w=rb: w.config(fg=TEXT))
        rb.bind("<Leave>",    lambda e, w=rb: w.config(fg=SUB))

        tk.Frame(inner, bg=SEP, height=1).pack(fill="x", padx=17)

    tk.Frame(inner, bg=BG, height=6).pack()


# ── Main entry point ──────────────────────────────────────────────────────────

def _is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def build_startup_manager_page(host, parent: tk.Frame):
    prefs = _load_prefs()

    page = tk.Frame(parent, bg=BG)
    page.pack(fill="both", expand=True)

    spin = tk.Label(page, text="Scanning startup entries…",
                    font=(_F, 10), bg=BG, fg=SUB)
    spin.pack(pady=60)

    def _on_ready(entries):
        spin.destroy()
        _render(page, entries, prefs)

    threading.Thread(
        target=lambda: page.after(0, lambda: _on_ready(_read_startup_entries())),
        daemon=True
    ).start()


def _render(page: tk.Frame, entries: list[dict], prefs: dict):
    if not entries:
        tk.Label(page, text="No startup entries found - or winreg unavailable.",
                 font=(_F, 10), bg=BG, fg=SUB).pack(pady=60)
        return

    # Derived lists
    def _get_derived():
        active  = [e for e in entries if prefs.get(e["id"], {}).get("status", "active") == "active"]
        flagged = [e for e in active  if e["rec"] in ("disable", "delay") and e["impact"] in ("high", "medium")]

        # Disabled = entries that are in registry but marked disabled
        #          + entries that were deleted from registry (stored only in prefs)
        disabled_from_registry = [e for e in entries
                                   if prefs.get(e["id"], {}).get("status", "active") != "active"]
        registry_ids = {e["id"] for e in entries}
        disabled_offline = []
        for eid, pdata in prefs.items():
            if pdata.get("status") == "disabled" and eid not in registry_ids:
                # Reconstruct ghost entry from saved prefs data
                hive_label = pdata.get("hive", "HKCU")
                hive_info  = _HIVE_MAP.get(hive_label, (None, ""))
                impact, rec, desc_kb = _KNOWN.get(pdata.get("exe", ""), ("low", "keep", ""))
                disabled_offline.append({
                    "id":         eid,
                    "name":       pdata.get("name", eid),
                    "value":      pdata.get("value", ""),
                    "exe":        pdata.get("exe", ""),
                    "hive":       hive_label,
                    "hive_const": hive_info[0],
                    "reg_path":   hive_info[1],
                    "impact":     pdata.get("impact", impact),
                    "rec":        rec,
                    "desc":       pdata.get("desc", desc_kb),
                    "_ghost":     True,   # not in registry
                })
        disabled = disabled_from_registry + disabled_offline
        return active, flagged, disabled

    active, flagged, disabled = _get_derived()
    n_high = len([e for e in entries if e["impact"] == "high"])

    # Queue state (shared mutable)
    queue:      list[dict] = []
    queued_ids: set        = set()

    # ── Page layout (grid: 0=header, 1=content, 2=drawer) ────────────────────
    page.grid_rowconfigure(0, weight=0)
    page.grid_rowconfigure(1, weight=1)
    page.grid_rowconfigure(2, weight=0)
    page.grid_columnconfigure(0, weight=1)

    # ── Row 0: Header block ───────────────────────────────────────────────────
    header_block = tk.Frame(page, bg=BG)
    header_block.grid(row=0, column=0, sticky="ew")

    # Admin notice — inside header_block so it survives _full_refresh
    if not _is_admin():
        _adm = tk.Frame(header_block, bg="#1a0f00", height=28)
        _adm.pack(fill="x")
        _adm.pack_propagate(False)
        tk.Label(_adm,
                 text="  ⚠  Not running as Administrator — HKLM startup entries cannot be modified.  "
                      "Right-click PC Workman → Run as administrator for full control.",
                 font=(_F, 7, "bold"), bg="#1a0f00", fg=AMBER,
                 padx=8).pack(side="left", fill="y")

    # Compact title row — no subtitle, minimal vertical padding
    title_row = tk.Frame(header_block, bg=BG)
    title_row.pack(fill="x", padx=16, pady=(6, 0))

    title_col = tk.Frame(title_row, bg=BG)
    title_col.pack(side="left", fill="y")
    tk.Label(title_col, text="Startup Manager",
             font=(_F, 13, "bold"), bg=BG, fg=TEXT).pack(anchor="w")

    chips_row = tk.Frame(title_row, bg=BG)
    chips_row.pack(side="right", fill="y")

    def _chip(parent, label, val, color):
        f = tk.Frame(parent, bg="#0f1720", padx=7, pady=2)
        f.pack(side="left", padx=2)
        tk.Label(f, text=label, font=(_F, 7, "bold"), bg="#0f1720", fg=color).pack(side="left")
        tk.Label(f, text=str(val), font=(_F, 7), bg="#0f1720", fg=SUB).pack(side="left", padx=(2, 0))

    _chip(chips_row, "Total",       len(entries), TEXT)
    _chip(chips_row, "High impact", n_high,        RED)
    _chip(chips_row, "Flagged",     len(flagged),  AMBER)

    tk.Frame(header_block, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(6, 0))

    # ── Tab bar — only 2 tabs: Startup Menu + Disabled ───────────────────────
    tab_bar = tk.Frame(header_block, bg=BG)
    tab_bar.pack(fill="x", padx=12, pady=(4, 0))

    _view = tk.StringVar(value="split")
    _content_ref  = [None]
    _tab_btns: dict[str, tk.Label] = {}

    def _refresh_tabs():
        v = _view.get()
        for key, btn in _tab_btns.items():
            if key == "split" and v == "split":
                btn.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=(_F, 9, "bold"))
            elif key == "disabled" and v == "disabled":
                btn.config(bg=TAB_ACTIVE_BG, fg=TAB_ACTIVE_FG, font=(_F, 9, "bold"))
            else:
                btn.config(bg=BG, fg=SUB, font=(_F, 9))

    def _switch_view(v: str):
        _view.set(v)
        active_now, flagged_now, disabled_now = _get_derived()
        if "split" in _tab_btns:
            _tab_btns["split"].config(text=f"Startup Menu  {len(active_now)}")
        if "disabled" in _tab_btns:
            _tab_btns["disabled"].config(text=f"Disabled  {len(disabled_now)}")
        _refresh_tabs()
        if _content_ref[0]:
            _content_ref[0].destroy()
        cf = tk.Frame(page, bg=BG)
        cf.grid(row=1, column=0, sticky="nsew")
        _content_ref[0] = cf
        if v == "split":
            _draw_split(cf)
        else:
            # Pass a callback that does a full refresh after restore
            def _after_restore():
                # Re-scan registry to pick up restored entries immediately
                page.after(0, lambda: _full_refresh())
            _build_disabled_panel(cf, disabled_now, prefs, _after_restore)

    def _full_refresh():
        """Re-read registry + prefs and rebuild entire view."""
        new_entries = _read_startup_entries()
        # Rebuild from scratch on the same page frame
        for w in page.winfo_children():
            try: w.destroy()
            except Exception: pass
        # Re-run render with fresh entries
        _render(page, new_entries, prefs)

    # Two tabs only: Startup Menu + Disabled
    for key, lbl, col in [
        ("split",    f"Startup Menu  {len(active)}",  TEXT),
        ("disabled", f"Disabled  {len(disabled)}",    SUB),
    ]:
        b = tk.Label(tab_bar, text=lbl, font=(_F, 9),
                     bg=BG, fg=col, padx=12, pady=5, cursor="hand2")
        b.pack(side="left", padx=(0, 3))
        b.bind("<Button-1>", lambda e, _v=key: _switch_view(_v))
        _tab_btns[key] = b

    # ── Banner ────────────────────────────────────────────────────────────────
    banner = tk.Frame(header_block, bg=BANNER_BG)
    banner.pack(fill="x", padx=0, pady=(4, 0))
    tk.Label(banner, text="  Click a process to disable on Startup",
             font=(_F, 8), bg=BANNER_BG, fg="#5a7a96",
             anchor="w", pady=4).pack(fill="x", padx=16)

    # ── Row 2: Confirmation drawer (initially 0 height) ───────────────────────
    drawer_outer = tk.Frame(page, bg=DRAWER_BG, height=0)
    drawer_outer.grid(row=2, column=0, sticky="ew")
    drawer_outer.grid_propagate(False)

    # ── Queue management ──────────────────────────────────────────────────────

    def _show_drawer():
        drawer_outer.config(height=DRAWER_H)
        _build_drawer_content(drawer_outer, queue, _on_confirm, _on_back)

    def _hide_drawer():
        drawer_outer.config(height=0)
        for w in drawer_outer.winfo_children():
            w.destroy()

    def _on_queue(entry: dict):
        eid = entry["id"]
        if eid in queued_ids:
            # Toggle off
            queued_ids.discard(eid)
            queue[:] = [e for e in queue if e["id"] != eid]
        else:
            queued_ids.add(eid)
            queue.append(entry)

        if queue:
            _show_drawer()
        else:
            _hide_drawer()

        # Refresh current content to update visual state
        _switch_view(_view.get())

    def _on_confirm():
        if not queue:
            _hide_drawer()
            return

        # Build confirmation message
        names_str = "\n".join(f"  • {e['name']}" for e in queue[:8])
        has_crit  = any(_is_critical(e["exe"]) for e in queue)
        extra     = "\n\n⚠ Jeden z procesów wygląda jak sterownik/narzędzie systemowe.\nWyłącz tylko jeśli jesteś pewien." if has_crit else ""
        msg = (f"Wyłączyć ze startu {len(queue)} {'wpis' if len(queue)==1 else 'wpisów'}?\n\n"
               f"{names_str}{extra}\n\nZmiany wejdą w życie po ponownym uruchomieniu.")

        ans = messagebox.askyesno("Potwierdź wyłączenie", msg, icon="warning")
        if not ans:
            return

        failed = []
        for e in list(queue):
            ok = _delete_startup_entry(e["hive_const"], e["reg_path"], e["name"])
            if ok:
                # Save full entry data so we can show it in Disabled tab
                # and restore it to registry later even if it's no longer there
                from datetime import datetime as _dt
                prefs.setdefault(e["id"], {}).update({
                    "status":      "disabled",
                    "name":        e["name"],
                    "value":       e.get("value", ""),
                    "exe":         e.get("exe", ""),
                    "hive":        e.get("hive", "HKCU"),
                    "impact":      e.get("impact", "low"),
                    "desc":        e.get("desc", ""),
                    "disabled_by": "UŻYTKOWNIK",
                    "disabled_at": _dt.now().strftime("%Y-%m-%d %H:%M"),
                })
            else:
                failed.append(e["name"])

        _save_prefs(prefs)
        queue.clear()
        queued_ids.clear()
        _hide_drawer()

        if failed:
            messagebox.showerror(
                "Część operacji nie powiodła się",
                "Nie udało się usunąć:\n" + "\n".join(f"  • {n}" for n in failed) +
                "\n\nUruchom PC Workman jako Administrator."
            )

        _switch_view(_view.get())

    def _on_back():
        queue.clear()
        queued_ids.clear()
        _hide_drawer()
        _switch_view(_view.get())

    # ── Split view builder ────────────────────────────────────────────────────

    def _draw_split(cf: tk.Frame):
        """Full-width Startup Menu — flagged entries only, single column."""
        _, fl, _ = _get_derived()
        _build_needs_attention_panel(cf, fl, prefs, _on_queue, queued_ids)

    # ── Initial content render ────────────────────────────────────────────────
    cf_init = tk.Frame(page, bg=BG)
    cf_init.grid(row=1, column=0, sticky="nsew")
    _content_ref[0] = cf_init
    _refresh_tabs()
    _draw_split(cf_init)
