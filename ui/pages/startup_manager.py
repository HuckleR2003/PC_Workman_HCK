"""
Startup Manager - PC Workman HCK
Redesigned UX:
  · Split layout: Needs attention (left 50%) + All entries 2-col grid (right 50%)
  · Subtle "click to queue" banner below tab bar
  · Click any active entry -> adds to disable queue
  · Bottom confirmation drawer (black-bordeau, hck_GPT style)
  · Critical process detection + warning in drawer
  · "Disabled" tab -> full-width view
"""
from utils.fonts import UI as _FONT_UI, HDR as _FONT_HDR, HEAVY as _FONT_HEAVY, LIGHT as _FONT_LIGHT  # noqa: F401
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
    _UIF, _MONOF = _FONT_UI, "Consolas"
_HDR  = _FONT_HDR
_F    = _UIF
_M    = _MONOF
_BODY = _UIF
_MONO = _MONOF

try:
    from utils.i18n import t as _t
except Exception:                                   # pragma: no cover
    def _t(key, default=None, **kw):
        return default if default is not None else key

# ── Palette ───────────────────────────────────────────────────────────────────
BG         = "#090c12"
SURFACE    = "#0d1117"
HOVER      = "#101a22"
HOVER_Q    = "#120d1a"      # queue-item hover (purplish tint)
BORDER     = "#14202e"
SEP        = "#141d28"
TEXT       = "#cdd8e8"
SUB        = "#8693a6"   # readable secondary (was #66788f)
MUTED      = "#93a1b5"   # readable muted (was #344256 - barely visible on dark)
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

# Source badge colors: HKCU / HKLM / startup folder
_SRC_COLOR = {
    "HKCU":         "#2a4a6a",
    "HKLM":         "#3a2a6a",
    "HKLM32":       "#3a2a6a",
    "STARTUP_USER": "#1a3a2a",
    "STARTUP_SYS":  "#1a3a2a",
    "TASK":         "#5a3a1a",
    "UWP":          "#1a3a5a",
}
# Human labels - users kept asking what "HKCU / HKLM / Task" means
# Looked up through t() at draw time, so they follow the interface language.
# (They were Polish literals, shown as-is with the interface set to English.)
_SRC_ICON = {
    "HKCU": "👤", "HKLM": "🖥", "HKLM32": "🖥", "STARTUP_USER": "📁",
    "STARTUP_SYS": "📁", "TASK": "⏰", "UWP": "⊞",
}
_SRC_LABEL_EN = {
    "HKCU":         "Your account",
    "HKLM":         "All users",
    "HKLM32":       "All users (32)",
    "STARTUP_USER": "Startup folder",
    "STARTUP_SYS":  "Startup folder (all)",
    "TASK":         "Scheduler",
    "UWP":          "Store",
}
_SRC_HINT_EN = {
    "HKCU":         "Registry entry - starts only for your account (HKCU\\...\\Run)",
    "HKLM":         "Registry entry - starts for all users (HKLM\\...\\Run)",
    "HKLM32":       "32-bit registry entry - for all users (WOW6432Node)",
    "STARTUP_USER": "Shortcut in your account's Startup folder",
    "STARTUP_SYS":  "Shortcut in the Startup folder of all users",
    "TASK":         "Windows Task Scheduler task (logon/boot)",
    "UWP":          "Microsoft Store app with a startup task",
}


def _src_label(hive: str, fallback: str = None) -> str:
    """Badge text for where a startup entry comes from."""
    if hive not in _SRC_LABEL_EN:
        return hive if fallback is None else fallback
    return (_SRC_ICON[hive] + " "
            + _t("startup_manager.src_" + hive.lower(), _SRC_LABEL_EN[hive]))


def _src_hint(hive: str):
    if hive not in _SRC_HINT_EN:
        return None
    return _t("startup_manager.hint_" + hive.lower(), _SRC_HINT_EN[hive])


def _who_label(who: str) -> str:
    """'UŻYTKOWNIK' is the value stored in prefs (kept for old files); what
    is shown follows the interface language."""
    return _t("common.user_tag", "USER") if who == "UŻYTKOWNIK" else who

# Exe fragments that warrant a critical warning before disabling
_CRITICAL_FRAGS = frozenset({
    "realtek", "audio", "sound", "nahimic", "conexant", "hdaudio",
    "nvidia", "amd", "displaylink",
    "windowsdefender", "defender", "malwarebytes", "avast", "avg",
    "eset", "kaspersky", "bitdefender", "mbam",
})

# The tables moved to core/recommendations.py (2026-11-20): the Process
# Center, hck_GPT and this page give the same advice from one place.
from core.recommendations import STARTUP_KNOWN as _KNOWN, STARTUP_NAME_RULES as _NAME_RULES


def _known_or_guess(exe: str, name: str = ""):
    """(impact, rec, why) from the file table, else from the name rules."""
    hit = _KNOWN.get(exe)
    if hit:
        return hit
    key = f"{(name or '').lower()} {(exe or '').lower()}"
    for frag, impact, rec, why in _NAME_RULES:
        if frag in key:
            return impact, rec, why
    return ("low", "keep", "")

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


def _extract_exe(value: str) -> str:
    """
    Safely extract lowercase exe basename from a registry Run value.
    Handles:
      "C:\\path with spaces\\app.exe" -silent   (quoted path + args)
      C:\\path\\app.exe                          (unquoted, no args)
      "C:\\path\\app.exe"                        (quoted, no args)
      C:\\path with spaces\\app.exe              (unquoted, spaces in path)
    """
    if not value:
        return ""
    v = value.strip()
    if v.startswith('"'):
        # Quoted path - everything between first and second quote
        end = v.find('"', 1)
        path = v[1:end] if end > 1 else v[1:]
    else:
        # Unquoted - find .exe boundary (handles paths with spaces)
        v_lower = v.lower()
        exe_idx = v_lower.find('.exe')
        if exe_idx >= 0:
            path = v[:exe_idx + 4]
        else:
            # No .exe found - fall back to first token
            path = v.split()[0] if v else ""
    return os.path.basename(path).lower()


def _read_startup_entries() -> list[dict]:
    if not _HAS_WINREG:
        return []
    entries, seen = [], set()

    # ── Registry Run keys ─────────────────────────────────────────────────────
    for hive, path, hive_label in _REG_PATHS:
        sa_state = _read_startup_approved(hive_label)   # Task-Manager on/off flags
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
            exe = _extract_exe(value)
            kid = f"{hive_label}:{name.lower()}"
            if kid in seen: continue
            seen.add(kid)
            impact, rec, desc = _known_or_guess(exe, name)
            entries.append({"id": kid, "name": name, "value": value, "exe": exe,
                            "hive": hive_label, "hive_const": hive, "reg_path": path,
                            "impact": impact, "rec": rec, "desc": desc,
                            # real Windows state: False if disabled via StartupApproved
                            # (by us OR by Task Manager) - was invisible before
                            "_enabled": sa_state.get(name.lower(), True)})
        winreg.CloseKey(key)

    # ── Startup folders (.lnk shortcuts) ──────────────────────────────────────
    _startup_dirs = []
    _appdata = os.environ.get("APPDATA", "")
    if _appdata:
        _startup_dirs.append((
            os.path.join(_appdata, "Microsoft", "Windows",
                         "Start Menu", "Programs", "Startup"),
            "STARTUP_USER"
        ))
    _allusers = os.environ.get("ALLUSERSPROFILE", os.environ.get("ProgramData", ""))
    if _allusers:
        _startup_dirs.append((
            os.path.join(_allusers, "Microsoft", "Windows",
                         "Start Menu", "Programs", "Startup"),
            "STARTUP_SYS"
        ))

    for folder_path, hive_label in _startup_dirs:
        if not os.path.isdir(folder_path):
            continue
        try:
            for fname in os.listdir(folder_path):
                if not fname.lower().endswith(".lnk"):
                    continue
                full_path = os.path.join(folder_path, fname)
                name = fname[:-4]  # strip .lnk

                # Try win32com to resolve target exe; fall back to name-based guess
                exe = ""
                target_value = full_path
                try:
                    import win32com.client as _wc
                    _shell = _wc.Dispatch("WScript.Shell")
                    _sc    = _shell.CreateShortcut(full_path)
                    target_value = _sc.TargetPath or full_path
                    exe = os.path.basename(_sc.TargetPath).lower() if _sc.TargetPath else ""
                except Exception:
                    exe = (name.lower().replace(" ", "") + ".exe")

                kid = f"{hive_label}:{name.lower()}"
                if kid in seen:
                    continue
                seen.add(kid)

                impact, rec, desc = _known_or_guess(exe, name)
                entries.append({
                    "id":         kid,
                    "name":       name,
                    "value":      target_value,
                    "exe":        exe,
                    "hive":       hive_label,
                    "hive_const": None,     # not registry-based
                    "reg_path":   folder_path,
                    "impact":     impact,
                    "rec":        rec,
                    "desc":       desc,
                    "_folder":    True,     # startup folder item (not registry)
                })
        except Exception:
            pass

    # ── Sources 2 & 3: scheduled tasks + UWP/Store startup ────────────────────
    for extra in _read_scheduled_tasks() + _read_uwp_startup():
        if extra["id"] not in seen:
            seen.add(extra["id"])
            entries.append(extra)

    return entries


def _load_prefs() -> dict:
    from utils.prefs_io import load_json
    return load_json(_PREFS_PATH, {})


def _save_prefs(data: dict):
    from utils.prefs_io import save_json
    save_json(_PREFS_PATH, data)


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


# ── StartupApproved - the Task-Manager way of disabling a Run entry ────────────
# Deleting a Run value doesn't stick: apps like OneDrive or Advanced SystemCare
# simply re-create it on their next launch. Task Manager instead writes a flag in
# ...\Explorer\StartupApproved\Run - Windows then SKIPS the Run entry at logon
# even if the app re-adds it. We disable the same way, so it finally sticks.
# Binary format: 12 bytes; first byte even (0x02) = enabled, odd (0x03) = disabled.

_SA_MAP = {
    "HKCU":   (winreg.HKEY_CURRENT_USER  if _HAS_WINREG else None,
               r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"),
    "HKLM":   (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
               r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"),
    "HKLM32": (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
               r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32"),
} if _HAS_WINREG else {}


def _read_startup_approved(hive_label: str) -> dict:
    """Return {value_name_lower: enabled_bool} from StartupApproved for a hive."""
    out = {}
    info = _SA_MAP.get(hive_label)
    if not info or not _HAS_WINREG:
        return out
    try:
        key = winreg.OpenKey(info[0], info[1], 0, winreg.KEY_READ)
    except OSError:
        return out
    i = 0
    while True:
        try:
            name, data, _t = winreg.EnumValue(key, i); i += 1
        except OSError:
            break
        try:
            out[name.lower()] = not (data and data[0] % 2 == 1)   # odd = disabled
        except Exception:
            pass
    winreg.CloseKey(key)
    return out


def _set_startup_approved(hive_label: str, name: str, enable: bool) -> bool:
    """Write the Task-Manager style enable/disable flag for a Run entry."""
    info = _SA_MAP.get(hive_label)
    if not info or not _HAS_WINREG:
        return False
    data = bytes([2 if enable else 3] + [0] * 11)
    try:
        key = winreg.CreateKeyEx(info[0], info[1], 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, data)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


# ── Source 2: Task Scheduler (GPU Tweak, MSI helpers, ShareX, vendor tools) ────
# Many modern apps register startup via a logon/boot scheduled task instead of a
# Run key, so they were invisible to the old Run-only scan. We read third-party
# logon/boot tasks and let the user enable/disable them (reversible) via schtasks.

_CREATE_NO_WINDOW = 0x08000000


def _read_scheduled_tasks() -> list[dict]:
    # Use Get-ScheduledTask (not schtasks CSV) because its CIM trigger class
    # names and State enum are language-neutral - schtasks column headers are
    # localized and would break enumeration on non-English Windows.
    if os.name != "nt":
        return []
    import subprocess, json as _json
    ps = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "Get-ScheduledTask | Where-Object { "
        "($_.Triggers | ForEach-Object { $_.CimClass.CimClassName }) "
        "-match 'LogonTrigger|BootTrigger' -and $_.TaskPath -notlike '\\Microsoft\\*' "
        "} | ForEach-Object { [PSCustomObject]@{ Name=$_.TaskName; Path=$_.TaskPath; "
        "State=[string]$_.State; Exe=($_.Actions | Select-Object -First 1 "
        "-ExpandProperty Execute) } } | ConvertTo-Json -Compress"
    )
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, timeout=30, creationflags=_CREATE_NO_WINDOW)
        out = r.stdout.decode("utf-8", "replace").strip()
        if not out:
            return []
        data = _json.loads(out)
        if isinstance(data, dict):
            data = [data]
    except Exception:
        return []
    entries = []
    for d in data:
        try:
            name = (d.get("Name") or "").strip()
            if not name:
                continue
            full = (d.get("Path") or "") + name      # full task path for schtasks /change
            enabled = (d.get("State") or "").strip().lower() != "disabled"
            exe_path = (d.get("Exe") or "").strip().strip('"')
            exe = os.path.basename(exe_path).lower() if exe_path else ""
            impact, rec, desc = _known_or_guess(exe, name)
            entries.append({
                "id": f"TASK:{full.lower()}", "name": name, "value": exe_path,
                "exe": exe, "hive": "TASK", "hive_const": None, "reg_path": full,
                "impact": impact, "rec": rec, "desc": desc,
                "_task": True, "_enabled": enabled,
            })
        except Exception:
            continue
    return entries


def _set_task_enabled(task_path: str, enable: bool) -> bool:
    """Enable/disable a scheduled task (reversible 'disable from startup')."""
    if os.name != "nt":
        return False
    import subprocess
    try:
        r = subprocess.run(
            ["schtasks", "/change", "/tn", task_path,
             "/enable" if enable else "/disable"],
            capture_output=True, timeout=15, creationflags=_CREATE_NO_WINDOW)
        return r.returncode == 0
    except Exception:
        return False


# ── Source 3: UWP / Microsoft Store packaged-app startup tasks ─────────────────
# Store apps (ShareX, LinkedIn, MSI Center...) register a StartupTask whose state
# lives in the registry. Task Manager toggles the same 'State' DWORD.
#   ...\AppModel\SystemAppData\<PackageFamilyName>\<TaskId>\State
#   State: 2/4 = enabled, 0/1/3 = disabled (StartupTaskState enum)

_UWP_BASE = (r"Software\Classes\Local Settings\Software\Microsoft\Windows"
             r"\CurrentVersion\AppModel\SystemAppData")


def _read_uwp_startup() -> list[dict]:
    if not _HAS_WINREG:
        return []
    entries = []
    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _UWP_BASE)
    except OSError:
        return entries
    i = 0
    while True:
        try:
            pfn = winreg.EnumKey(root, i); i += 1
        except OSError:
            break
        try:
            pkg = winreg.OpenKey(root, pfn)
        except OSError:
            continue
        j = 0
        while True:
            try:
                task_id = winreg.EnumKey(pkg, j); j += 1
            except OSError:
                break
            sub_path = f"{_UWP_BASE}\\{pfn}\\{task_id}"
            try:
                tk = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_path)
                state, _ = winreg.QueryValueEx(tk, "State")
                winreg.CloseKey(tk)
            except OSError:
                continue   # no State -> not a startup task
            enabled = int(state) in (2, 4)
            disp = pfn.split("_")[0].split(".")[-1] or pfn
            _imp, _rec, _why = _known_or_guess("", f"{disp} {pfn}")
            entries.append({
                "id": f"UWP:{pfn.lower()}:{task_id.lower()}", "name": disp,
                "value": pfn, "exe": "", "hive": "UWP", "hive_const": None,
                "reg_path": sub_path, "impact": _imp, "rec": _rec, "desc": _why,
                "_uwp": True, "_enabled": enabled,
            })
        winreg.CloseKey(pkg)
    winreg.CloseKey(root)
    return entries


def _set_uwp_enabled(reg_path: str, enable: bool) -> bool:
    """Toggle a UWP startup task's State DWORD (2 = enabled, 1 = disabled-by-user)."""
    if not _HAS_WINREG:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0,
                             winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "State", 0, winreg.REG_DWORD, 2 if enable else 1)
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
    cv.bind("<Configure>", lambda e=None: cv.itemconfig(wid, width=e.width))
    inner.bind("<Configure>", lambda e=None: cv.configure(scrollregion=cv.bbox("all")))

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
                 running_set: set = None,
                 show_on_badge: bool = False):
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

    # "ACTIVE NOW" badge - green - if exe is currently running
    if not is_dis and running_set is not None:
        exe_l = (entry.get("exe") or "").lower()
        if exe_l and exe_l in running_set:
            tk.Label(line1, text="● ACTIVE NOW",
                     font=(_F, 7, "bold"),
                     bg="#052e16", fg="#22c55e",
                     padx=4, pady=1).pack(side="left", padx=(4, 0))

    if not is_dis:
        tag = tk.Label(line1, text=_IL.get(impact, "?"),
                       font=(_F, 7, "bold"),
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

    # "ON" badge - subtle green - shown in the all-active panel
    if show_on_badge and not is_dis and not in_q:
        tk.Label(line1, text="ON",
                 font=(_F, 7, "bold"),
                 bg="#052e16", fg="#22c55e",
                 padx=4, pady=1).pack(side="right", padx=(0, 4))

    # Source badge - where this entry comes from (👤 / 🖥 / ⏰ / ⊞ / 📁)
    if show_on_badge and not is_dis:
        hive = entry.get("hive", "")
        src_col = _SRC_COLOR.get(hive, "#1a2530")
        src_txt = _src_label(hive, hive[:6])
        if src_txt:
            src_badge = tk.Label(line1, text=src_txt,
                                 font=(_F, 7), bg=src_col, fg="#6a8aaa",
                                 padx=3, pady=1)
            src_badge.pack(side="right", padx=(0, 3))
            hint = _src_hint(hive)
            if hint:
                _Tooltip(src_badge, hint)

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


# ── Panel builders ────────────────────────────────────────────────────────────
# (The old inline drawer lived here - replaced by the shared OperatorDrawer,
#  the single confirm mechanism used across Startup and Services Manager.)

def _build_needs_attention_panel(parent: tk.Frame, flagged: list[dict],
                                  prefs: dict, on_queue, queued_ids: set):
    """Startup Menu panel - flagged entries (single column, compact rows)."""
    # Header
    hdr = tk.Frame(parent, bg=BG)
    hdr.pack(fill="x", padx=10, pady=(8, 4))
    from ui.components.page_titles import text as _ptx
    tk.Label(hdr, text=_ptx("sm_menu_head"), font=(_F, 8, "bold"),
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
                 text=_t("startup_manager.clean_note",
                         "A program that quietly added itself\n"
                         "to Windows startup would show up here."),
                 font=(_F, 8), bg=BG, fg="#6f86a3",
                 justify="left", anchor="w").pack(anchor="w")
        return

    inner, cv = _scrollable_frame(parent, bg=BG)

    for e in flagged:
        _compact_row(inner, e, prefs, on_queue, queued_ids, two_col=False)

    tk.Frame(inner, bg=BG, height=6).pack()


def _build_all_active_panel(parent: tk.Frame, active: list[dict],
                             prefs: dict, on_queue, queued_ids: set):
    """Right panel - ALL active startup entries with ON badge + source indicator.
    Shows everything that starts with Windows (registry + startup folders).
    Subtly styled - secondary info, all clickable to queue for disable.
    """
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
    tk.Label(hdr, text=_t("startup_manager.active_at_boot", "Active at startup"),
             font=(_F, 8, "bold"), bg=BG, fg=TEXT).pack(side="left")
    tk.Label(hdr, text=f"  {len(active)}", font=(_F, 8),
             bg=BG, fg=SUB).pack(side="left")
    tk.Label(hdr, text=_t("startup_manager.click_to_disable", "click to disable"),
             font=(_F, 7), bg=BG, fg=MUTED).pack(side="right")

    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=10)

    if not active:
        tk.Label(parent,
                 text=_t("startup_manager.no_active", "No active startup entries."),
                 font=(_F, 9), bg=BG, fg=SUB).pack(pady=30)
        return

    inner, cv = _scrollable_frame(parent, bg=BG)

    for e in active:
        if e.get("_task") or e.get("_uwp"):
            # Scheduled task / Store app - same click-to-queue as registry rows
            _actionable_row(inner, e, on_queue, queued_ids, running_set=_running)
        elif e.get("_folder"):
            # Startup folder shortcut - managed via Explorer (read-only)
            _folder_row(inner, e, prefs, running_set=_running)
        else:
            row_w, sep_w = _compact_row(
                inner, e, prefs, on_queue, queued_ids,
                two_col=False,
                running_set=_running,
                show_on_badge=True,
            )
            _bind_scroll(row_w, cv)
            _bind_scroll(sep_w, cv)

    tk.Frame(inner, bg=BG, height=6).pack()


def _folder_row(parent: tk.Frame, entry: dict, prefs: dict, running_set: set = None):
    """Read-only row for startup folder (.lnk) items - shown but not queue-able."""
    name  = entry["name"]
    exe   = entry["exe"] or "-"
    hive  = entry.get("hive", "")

    row = tk.Frame(parent, bg=SURFACE, cursor="arrow")
    row.pack(fill="x", padx=0, pady=0)

    # Thin grey accent bar (not clickable = no color)
    tk.Frame(row, bg="#1a3a2a", width=2).pack(side="left", fill="y")

    body = tk.Frame(row, bg=SURFACE)
    body.pack(side="left", fill="both", expand=True, padx=(7, 4), pady=(4, 3))

    line1 = tk.Frame(body, bg=SURFACE)
    line1.pack(fill="x")

    tk.Label(line1, text=name[:28], font=(_F, 9, "bold"),
             bg=SURFACE, fg=TEXT, anchor="w").pack(side="left")

    # ACTIVE NOW if running
    if running_set is not None:
        if exe.lower() in running_set:
            tk.Label(line1, text="● ACTIVE NOW", font=(_F, 7, "bold"),
                     bg="#052e16", fg="#22c55e", padx=4, pady=1
                     ).pack(side="left", padx=(4, 0))

    # ON badge (green, subtle)
    tk.Label(line1, text="ON", font=(_F, 7, "bold"),
             bg="#052e16", fg="#22c55e", padx=4, pady=1
             ).pack(side="right", padx=(0, 4))

    # Source badge (📁)
    src_lbl = _src_label(hive, "📁")
    tk.Label(line1, text=src_lbl, font=(_F, 7),
             bg=_SRC_COLOR.get(hive, "#1a3a2a"), fg="#5a8a6a",
             padx=3, pady=1).pack(side="right", padx=(0, 3))

    tk.Label(body, text=exe[:32], font=(_F, 7),
             bg=SURFACE, fg=MUTED, anchor="w").pack(anchor="w")

    # Tooltip explaining it's a startup folder item
    _Tooltip(row, f"Startup folder shortcut - managed via Windows Explorer.\n"
                  f"Location: {entry.get('reg_path','')}")

    tk.Frame(parent, bg=SEP, height=1).pack(fill="x")


def _actionable_row(parent: tk.Frame, entry: dict, on_queue, queued_ids: set,
                    running_set: set = None):
    """Row for a scheduled task / UWP startup item. Click-to-queue, exactly like
    registry rows - ONE confirm mechanism (the bottom operator drawer) for all."""
    name    = entry["name"]
    exe     = entry.get("exe") or "-"
    hive    = entry.get("hive", "")
    enabled = entry.get("_enabled", True)
    in_q    = entry["id"] in queued_ids
    accent  = "#5a3a1a" if entry.get("_task") else "#1d3a5a"
    row_bg  = QUEUED_BG if in_q else SURFACE

    row = tk.Frame(parent, bg=row_bg, cursor="hand2")
    row.pack(fill="x")
    bar = tk.Frame(row, bg=BORDEAU if in_q else accent, width=2)
    bar.pack(side="left", fill="y")
    bar.pack_propagate(False)

    body = tk.Frame(row, bg=row_bg)
    body.pack(side="left", fill="both", expand=True, padx=(7, 4), pady=(4, 3))
    line1 = tk.Frame(body, bg=row_bg)
    line1.pack(fill="x")

    name_l = tk.Label(line1, text=name[:30] + ("…" if len(name) > 30 else ""),
                      font=(_F, 9, "bold"), bg=row_bg,
                      fg=BORDEAU_LIGHT if in_q else (TEXT if enabled else MUTED),
                      anchor="w")
    name_l.pack(side="left")
    if running_set is not None and exe.lower() in running_set:
        tk.Label(line1, text="● ACTIVE NOW", font=(_F, 7, "bold"),
                 bg="#052e16", fg="#22c55e", padx=4, pady=1).pack(side="left", padx=(4, 0))

    if in_q:
        tk.Label(line1, text="✓ " + _t("startup_manager.queued", "queued"), font=(_F, 7, "bold"),
                 bg=row_bg, fg=BORDEAU_LIGHT, padx=4).pack(side="right", padx=(0, 4))

    tk.Label(line1, text="ON" if enabled else "OFF", font=(_F, 7, "bold"),
             bg="#052e16" if enabled else row_bg, fg="#22c55e" if enabled else MUTED,
             padx=4, pady=1).pack(side="right", padx=(0, 4))
    tk.Label(line1, text=_src_label(hive, hive), font=(_F, 7),
             bg=_SRC_COLOR.get(hive, "#1a2530"), fg="#8aa0bc",
             padx=3, pady=1).pack(side="right", padx=(0, 3))

    exe_l = tk.Label(body, text=exe[:34], font=(_F, 7), bg=row_bg, fg=MUTED,
                     anchor="w")
    exe_l.pack(anchor="w")

    kind = (_t("startup_manager.kind_task", "Scheduled task (⏰)")
            if entry.get("_task")
            else _t("startup_manager.kind_uwp", "Microsoft Store app (⊞)"))
    _Tooltip(row, _t("startup_manager.row_tip",
                     "{kind} - click to add it to the disable list.\n"
                     "Fully reversible in the Disabled tab.", kind=kind)
                  + f"\n{entry.get('reg_path','')}")

    def _click(e, _entry=entry):
        on_queue(_entry)
    for w in (row, body, line1, name_l, exe_l):
        w.bind("<Button-1>", _click)
    tk.Frame(parent, bg=SEP, height=1).pack(fill="x")


def _build_disabled_panel(parent: tk.Frame, disabled: list[dict],
                           prefs: dict, on_restore_done):
    """Full-width view for Disabled tab."""
    hdr = tk.Frame(parent, bg=BG)
    hdr.pack(fill="x", padx=16, pady=(10, 6))
    from ui.components.page_titles import text as _ptx
    tk.Label(hdr, text=_ptx("sm_disabled_head"), font=(_F, 8, "bold"),
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

        # "Kto: UŻYTKOWNIK · data" - show if saved
        pdata   = prefs.get(eid, {})
        dis_by  = pdata.get("disabled_by", "")
        dis_at  = pdata.get("disabled_at", "")
        if dis_by:
            who_str = _t("startup_manager.who", "By: {who}", who=_who_label(dis_by))
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
                if _store_blocked(entry):
                    from utils.install_kind import open_task_manager_startup
                    if messagebox.askyesno(_sx("store_title"),
                                           _sx("store_skip", names=f"  • {entry['name']}")):
                        open_task_manager_startup()
                    return
                # Scheduled task / UWP: re-enable directly (no registry value to write)
                if entry.get("_task") or entry.get("_uwp"):
                    ok = (_set_task_enabled(entry["reg_path"], True) if entry.get("_task")
                          else _set_uwp_enabled(entry["reg_path"], True))
                    if not ok:
                        import tkinter.messagebox as _mb
                        _mb.showerror(
                            _t("startup_manager.restore_fail_title",
                               "Could not restore"),
                            _t("startup_manager.restore_fail_enable",
                               "Cannot enable '{name}'.\n"
                               "It may need Administrator rights.",
                               name=entry['name']))
                        return
                    r.destroy()
                    on_restore_done()
                    return
                # Registry entry: reverse whichever mechanism disabled it.
                pdata  = prefs.get(entry["id"], {})
                method = pdata.get("method", "deleted")
                sa_off = not entry.get("_enabled", True)   # StartupApproved says OFF
                hc  = entry.get("hive_const")
                rp  = entry.get("reg_path", "")
                val = entry.get("value", "")
                ok  = True
                if sa_off or method == "startupapproved":
                    # Flip the Task-Manager flag back to enabled (works even for
                    # entries disabled in Task Manager itself, not by us)
                    ok = _set_startup_approved(entry.get("hive", ""), entry["name"], True)
                elif hc and rp and val:
                    # Old delete method - write the Run value back
                    ok = _restore_startup_entry(hc, rp, entry["name"], val)
                if not ok:
                    import tkinter.messagebox as _mb
                    _mb.showerror(
                        _t("startup_manager.restore_fail_title",
                           "Could not restore"),
                        _t("startup_manager.restore_fail_registry",
                           "Cannot restore '{name}'.\n"
                           "Run PC Workman as Administrator.",
                           name=entry['name'])
                    )
                    return
                # Remove from prefs entirely - entry will appear as active next scan
                prefs.pop(entry["id"], None)
                _save_prefs(prefs)
                r.destroy()
                on_restore_done()
            return _do

        rb = tk.Label(right, text="Restore", font=(_F, 8),
                      fg=SUB, bg=SURFACE, cursor="hand2", padx=6, pady=2)
        rb.pack(anchor="e", pady=(3, 0))
        rb.bind("<Button-1>", lambda e=None, fn=_make_restore(): fn())
        rb.bind("<Enter>",    lambda e=None, w=rb: w.config(fg=TEXT))
        rb.bind("<Leave>",    lambda e=None, w=rb: w.config(fg=SUB))

        tk.Frame(inner, bg=SEP, height=1).pack(fill="x", padx=17)

    tk.Frame(inner, bg=BG, height=6).pack()


# ── Main entry point ──────────────────────────────────────────────────────────

from utils.admin import is_admin as _is_admin  # single source of truth

# What this install may change (utils/install_kind.py, 2026-11-20)
_SX = {
    "store_banner": {"pl": "  ⚠  Wersja ze Sklepu: Windows zapisuje zmiany autostartu w prywatnej kopii rejestru tej aplikacji, więc wyłączenie tutaj by nie zadziałało. Zrób to w Menedżerze zadań.",
                     "en": "  ⚠  Store version: Windows writes startup changes to this app's private copy of the registry, so disabling here would not work. Use Task Manager instead."},
    "store_btn": {"pl": "Otwórz Menedżer zadań", "en": "Open Task Manager"},
    "admin_banner": {"pl": "  ⚠  Bez uprawnień administratora: wpisów dla wszystkich użytkowników (HKLM) nie zmienię. Uruchom PC Workman jako administrator.",
                     "en": "  ⚠  Not running as administrator: entries for all users (HKLM) cannot be changed. Run PC Workman as administrator."},
    "store_title": {"pl": "Wersja ze Sklepu", "en": "Store version"},
    "scanning": {"pl": "Sprawdzam, co startuje z Windows…", "en": "Scanning startup entries…"},
    "store_skip": {"pl": "Tych wpisów nie wyłączę z wersji ze Sklepu (Windows zapisałby zmianę tylko w prywatnej kopii rejestru tej aplikacji):\n\n{names}\n\nOtworzyć Menedżer zadań na stronie Aplikacje autostartu?",
                   "en": "I cannot disable these from the Store version (Windows would only change this app's private copy of the registry):\n\n{names}\n\nOpen Task Manager on its Startup apps page?"},
}


def _sx(k, **kw):
    try:
        from utils.i18n import get_lang
        lang = "en" if get_lang() == "en" else "pl"
    except Exception:
        lang = "pl"
    s = _SX[k][lang]
    return s.format(**kw) if kw else s


def _store_blocked(entry) -> bool:
    """A registry or startup-folder entry on a Store install whose HKCU
    writes are virtualized: the change would not reach Windows. Scheduled
    tasks go through the Task Scheduler service and do work."""
    if entry.get("_task"):
        return False
    try:
        from utils.install_kind import registry_virtualized
        return registry_virtualized()
    except Exception:
        return False

def build_startup_manager_page(host, parent: tk.Frame):
    prefs = _load_prefs()

    page = tk.Frame(parent, bg=BG)
    page.pack(fill="both", expand=True)

    spin = tk.Label(page, text=_sx("scanning"),
                    font=(_F, 10), bg=BG, fg=SUB)
    spin.pack(pady=60)

    def _on_ready(entries):
        try:
            if not page.winfo_exists():
                return                      # user left the page meanwhile
        except Exception:
            return
        spin.destroy()
        _render(page, entries, prefs, host=host)

    # The worker only fills a plain dict; the window polls it. 2026-11-20:
    # page.after() called FROM the worker raised whenever the Tk main loop was
    # not the one pumping (the error was swallowed, the list never showed),
    # and a worker holding a Tk widget is what crashed with Tcl_AsyncDelete
    # on other pages this month.
    box = {"entries": None}

    def _scan(b=box):
        # Registry + scheduled tasks (PowerShell) are read HERE, on the
        # worker, so the window does not freeze while PowerShell starts.
        try:
            b["entries"] = _read_startup_entries()
        except Exception:
            b["entries"] = []

    def _poll():
        try:
            if not page.winfo_exists():
                return
        except Exception:
            return
        if box["entries"] is None:
            page.after(150, _poll)
            return
        _on_ready(box["entries"])

    threading.Thread(target=_scan, daemon=True, name="startup-scan").start()
    page.after(150, _poll)


def _render(page: tk.Frame, entries: list[dict], prefs: dict, host=None):
    if not entries:
        tk.Label(page, text="No startup entries found - or winreg unavailable.",
                 font=(_F, 10), bg=BG, fg=SUB).pack(pady=60)
        return

    # Derived lists
    def _get_derived():
        def _is_on(e):
            # Task / UWP entries carry their real on/off state from the system;
            # registry entries combine the StartupApproved flag (real Windows state,
            # set by us or Task Manager) with the app's prefs (old delete method).
            if e.get("_task") or e.get("_uwp"):
                return e.get("_enabled", True)
            if not e.get("_enabled", True):
                return False
            return prefs.get(e["id"], {}).get("status", "active") == "active"

        active  = [e for e in entries if _is_on(e)]
        flagged = [e for e in active  if e["rec"] in ("disable", "delay") and e["impact"] in ("high", "medium")]

        # Disabled = registry entries marked disabled, system tasks/UWP turned off,
        #            plus entries deleted from the registry (stored only in prefs).
        disabled_from_registry = [e for e in entries if not _is_on(e)]
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

    # Queue state - the OperatorDrawer owns the queue; this set only mirrors it
    # so rows can paint their "queued" tint.
    queued_ids: set = set()

    # ── Page layout (grid: 0=header, 1=content, 2=drawer) ────────────────────
    page.grid_rowconfigure(0, weight=0)
    page.grid_rowconfigure(1, weight=1)
    page.grid_rowconfigure(2, weight=0)
    page.grid_columnconfigure(0, weight=1)

    # ── Row 0: Header block ───────────────────────────────────────────────────
    header_block = tk.Frame(page, bg=BG)
    header_block.grid(row=0, column=0, sticky="ew")

    # Admin / Store notice - inside header_block so it survives _full_refresh
    try:
        from utils.install_kind import registry_virtualized as _virt
        _store_virt = _virt()
    except Exception:
        _store_virt = False
    if _store_virt or not _is_admin():
        _adm = tk.Frame(header_block, bg="#1a0f00")
        _adm.pack(fill="x")
        if _store_virt:
            from utils.install_kind import open_task_manager_startup as _otm
            _b = tk.Label(_adm, text=_sx("store_btn"), font=(_F, 8, "bold"), bg="#3a2a00",
                          fg="#ffffff", padx=10, pady=3, cursor="hand2")
            _b.pack(side="right", padx=8, pady=4)
            _b.bind("<Button-1>", lambda e=None: _otm())
        tk.Label(_adm, text=_sx("store_banner" if _store_virt else "admin_banner"),
                 font=(_F, 7, "bold"), bg="#1a0f00", fg=AMBER, anchor="w", justify="left",
                 wraplength=900, padx=8, pady=5).pack(side="left", fill="x", expand=True)

    # Compact title row - no subtitle, minimal vertical padding
    title_row = tk.Frame(header_block, bg=BG)
    title_row.pack(fill="x", padx=16, pady=(6, 0))

    title_col = tk.Frame(title_row, bg=BG)
    title_col.pack(side="left", fill="y")
    from ui.components.page_titles import text as _ptx
    tk.Label(title_col, text=_ptx("startup_manager"),
             font=(_F, 13, "bold"), bg=BG, fg=TEXT).pack(anchor="w")

    # Back navigation link (far right, before chips so it sits at the edge)
    _nav_cb = getattr(host, "_switch_to_page", None) if host else None
    if _nav_cb:
        _back_sm = tk.Label(title_row, text="‹ Dashboard",
                            font=(_F, 7), bg=BG, fg="#6f86a3",
                            cursor="hand2", padx=8)
        _back_sm.pack(side="right", fill="y")
        _back_sm.bind("<Button-1>", lambda e=None: _nav_cb("dashboard"))
        _back_sm.bind("<Enter>", lambda e=None: _back_sm.config(fg="#8b5cf6"))
        _back_sm.bind("<Leave>", lambda e=None: _back_sm.config(fg="#6f86a3"))

    chips_row = tk.Frame(title_row, bg=BG)
    chips_row.pack(side="right", fill="y")

    def _chip(parent, label, val, color):
        f = tk.Frame(parent, bg="#0f1720", padx=7, pady=2)
        f.pack(side="left", padx=2)
        tk.Label(f, text=label, font=(_F, 7, "bold"), bg="#0f1720", fg=color).pack(side="left")
        tk.Label(f, text=str(val), font=(_F, 7), bg="#0f1720", fg=SUB).pack(side="left", padx=(2, 0))

    _chip(chips_row, _ptx("sm_total"),   len(entries), TEXT)
    _chip(chips_row, _ptx("sm_high"),    n_high,        RED)
    _chip(chips_row, _ptx("sm_flagged"), len(flagged),  AMBER)

    tk.Frame(header_block, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(6, 0))

    # ── Tab bar - only 2 tabs: Startup Menu + Disabled ───────────────────────
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
            _tab_btns["split"].config(text=f"{_ptx('sm_tab_menu')}  {len(active_now)}")
        if "disabled" in _tab_btns:
            _tab_btns["disabled"].config(text=f"{_ptx('sm_tab_disabled')}  {len(disabled_now)}")
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
                page.after_idle(_full_refresh)   # UI thread (a click)
            _build_disabled_panel(cf, disabled_now, prefs, _after_restore)

    def _full_refresh():
        """Re-read registry + prefs and rebuild entire view."""
        new_entries = _read_startup_entries()
        # Rebuild from scratch on the same page frame
        for w in page.winfo_children():
            try: w.destroy()
            except Exception: pass
        # Re-run render with fresh entries (host propagated from outer _render scope)
        _render(page, new_entries, prefs, host=host)

    # Two tabs only: Startup Menu + Disabled
    for key, lbl, col in [
        ("split",    f"{_ptx('sm_tab_menu')}  {len(active)}",  TEXT),
        ("disabled", f"{_ptx('sm_tab_disabled')}  {len(disabled)}",    SUB),
    ]:
        b = tk.Label(tab_bar, text=lbl, font=(_F, 9),
                     bg=BG, fg=col, padx=12, pady=5, cursor="hand2")
        b.pack(side="left", padx=(0, 3))
        b.bind("<Button-1>", lambda e=None, _v=key: _switch_view(_v))
        _tab_btns[key] = b

    # ── Banner ────────────────────────────────────────────────────────────────
    banner = tk.Frame(header_block, bg=BANNER_BG)
    banner.pack(fill="x", padx=0, pady=(4, 0))
    tk.Label(banner,
             text="  " + _t("startup_manager.banner",
                            "Click an entry to add it to the disable list   ·   "
                            "👤 your account  ·  🖥 all users  ·  "
                            "⏰ Task Scheduler  ·  ⊞ Store app"),
             font=(_F, 8), bg=BANNER_BG, fg="#5a7a96",
             anchor="w", pady=4).pack(fill="x", padx=16)

    # ── Row 2: shared operator drawer (ONE confirm mechanism for everything) ──
    from ui.components.operator_drawer import OperatorDrawer

    def _disable_entry(e) -> bool:
        """Disable one queued entry, dispatching on its source type."""
        if e.get("_task"):
            return _set_task_enabled(e["reg_path"], False)
        if e.get("_uwp"):
            return _set_uwp_enabled(e["reg_path"], False)
        # Registry Run entry - StartupApproved flag first (Task-Manager style:
        # survives the app re-creating its Run key, e.g. OneDrive / ASC).
        if _set_startup_approved(e.get("hive", ""), e["name"], False):
            method = "startupapproved"
        elif _delete_startup_entry(e["hive_const"], e["reg_path"], e["name"]):
            method = "deleted"                      # legacy fallback
        else:
            return False
        from datetime import datetime as _dt
        prefs.setdefault(e["id"], {}).update({
            "status":      "disabled",
            "method":      method,
            "name":        e["name"],
            "value":       e.get("value", ""),
            "exe":         e.get("exe", ""),
            "hive":        e.get("hive", "HKCU"),
            "impact":      e.get("impact", "low"),
            "desc":        e.get("desc", ""),
            "disabled_by": "UŻYTKOWNIK",
            "disabled_at": _dt.now().strftime("%Y-%m-%d %H:%M"),
        })
        return True

    def _apply_queue(items: list):
        if not items:
            return
        # Store build: registry entries would change only the app's private
        # copy of the registry; send the user to Task Manager instead
        blocked = [it for it in items if _store_blocked(it.get("payload") or {})]
        if blocked:
            if messagebox.askyesno(_sx("store_title"), _sx(
                    "store_skip", names="\n".join(f"  • {it['label']}" for it in blocked[:8]))):
                from utils.install_kind import open_task_manager_startup
                open_task_manager_startup()
            items = [it for it in items if it not in blocked]
            if not items:
                return
        names_str = "\n".join(f"  • {it['label']}" for it in items[:8])
        has_crit  = any(it.get("warn") for it in items)
        extra     = ("\n\n" + _t("startup_manager.crit_warn",
                                 "⚠ One of these looks like a driver or a "
                                 "system tool.\nDisable it only if you are sure.")
                     if has_crit else "")
        msg = (_t("startup_manager.confirm_msg",
                  "Disable startup entries: {n}?", n=len(items))
               + f"\n\n{names_str}{extra}\n\n"
               + _t("startup_manager.confirm_after",
                    "Changes take effect after the next restart."))
        if not messagebox.askyesno(
                _t("startup_manager.confirm_title", "Confirm disable"),
                msg, icon="warning"):
            return

        failed = []
        for it in items:
            if not _disable_entry(it["payload"]):
                failed.append(it["label"])

        _save_prefs(prefs)
        queued_ids.clear()
        drawer.clear()

        if failed:
            messagebox.showerror(
                _t("startup_manager.partial_title", "Some operations failed"),
                _t("startup_manager.partial_msg", "Could not disable:") + "\n"
                + "\n".join(f"  • {n}" for n in failed) + "\n\n"
                + _t("startup_manager.run_admin",
                     "Run PC Workman as Administrator.")
            )
        _full_refresh()

    def _sync_rows():
        # Keep row tint in sync with the drawer queue (Wróć clears everything)
        queued_ids.clear()
        queued_ids.update(it["id"] for it in drawer.items())
        _switch_view(_view.get())

    drawer = OperatorDrawer(page, grid_row=2,
                            on_confirm=_apply_queue, on_change=_sync_rows)

    def _on_queue(entry: dict):
        drawer.toggle({
            "id":      entry["id"],
            "label":   entry["name"],
            "warn":    _is_critical(entry.get("exe", "")),
            "payload": entry,
        })

    # ── Split view builder ────────────────────────────────────────────────────

    def _draw_split(cf: tk.Frame):
        """Split: LEFT = Startup Menu (flagged, needs action),
                  RIGHT = All active entries with ON badge."""
        cf.grid_rowconfigure(0, weight=1)
        cf.grid_columnconfigure(0, weight=2)   # Startup Menu - narrower
        cf.grid_columnconfigure(1, weight=0)   # divider
        cf.grid_columnconfigure(2, weight=3)   # All active - wider

        left_panel = tk.Frame(cf, bg=BG)
        left_panel.grid(row=0, column=0, sticky="nsew")

        tk.Frame(cf, bg=PANEL_DIV, width=1).grid(row=0, column=1, sticky="ns")

        right_panel = tk.Frame(cf, bg=BG)
        right_panel.grid(row=0, column=2, sticky="nsew")

        active_now, fl, _ = _get_derived()
        _build_needs_attention_panel(left_panel, fl, prefs, _on_queue, queued_ids)
        _build_all_active_panel(right_panel, active_now, prefs, _on_queue, queued_ids)

    # ── Initial content render ────────────────────────────────────────────────
    cf_init = tk.Frame(page, bg=BG)
    cf_init.grid(row=1, column=0, sticky="nsew")
    _content_ref[0] = cf_init
    _refresh_tabs()
    _draw_split(cf_init)
