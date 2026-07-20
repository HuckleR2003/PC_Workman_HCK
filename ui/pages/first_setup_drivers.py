# ui/pages/first_setup_drivers.py
"""
FIRST SETUP & DRIVERS
Real-time driver health, system readiness score, startup manager, setup checklist.
Data sourced from Windows registry - no admin rights required for reads.
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

# ─── Font system ──────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

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

try:
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    import sys as _sys
    _APP_DIR = os.path.dirname(_sys.executable) if getattr(_sys, "frozen", False) \
               else os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

CHECKLIST_PATH = os.path.join(_APP_DIR, "data", "cache", "setup_checklist.json")

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
    if days < 730:
        mo = days // 30
        return f"{mo}mo OLD", AMBER, "#451a03", AMBER,    "#78350f"
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
    """MM-DD-YYYY -> 'Jan 2025'."""
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
    results = _read_all_class_drivers(guid)
    return results[0] if results else None


def _read_all_class_drivers(guid, max_entries=32):
    """Return ALL real driver dicts from Windows device class GUID."""
    if not _HAS_WINREG:
        return []
    key_path = fr"SYSTEM\CurrentControlSet\Control\Class\{guid}"
    results = []
    seen_names = set()
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as cls:
            n = winreg.QueryInfoKey(cls)[0]
            for i in range(min(n, 64)):
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
                        if desc in seen_names:
                            continue
                        seen_names.add(desc)
                        ver, drv_date = "", ""
                        try:
                            ver = winreg.QueryValueEx(dev, "DriverVersion")[0]
                        except OSError:
                            pass
                        try:
                            drv_date = winreg.QueryValueEx(dev, "DriverDate")[0]
                        except OSError:
                            pass
                        results.append({"name": desc, "version": ver, "date": drv_date})
                        if len(results) >= max_entries:
                            break
                except OSError:
                    continue
    except Exception:
        pass
    return results


# Category metadata: (guid, short_name, wmi_class, accent_color)
_CAT_META = [
    ("{4d36e968-e325-11ce-bfc1-08002be10318}", "GPU",     "Win32_VideoController", BLUE),
    ("{4d36e96c-e325-11ce-bfc1-08002be10318}", "AUDIO",   "Win32_SoundDevice",     PURPLE),
    ("{4d36e972-e325-11ce-bfc1-08002be10318}", "NETWORK", "Win32_NetworkAdapter",  GREEN),
    ("{36fc9e60-c465-11cf-8056-444553540000}", "USB",     "Win32_USBController",   "#ec4899"),
]

GHOST_BG   = "#150508"
GHOST_BD   = "#7f1d1d"
GHOST_MARK = "#ef4444"


def _get_pnp_connected_names(class_guid: str) -> set:
    """
    Return lowercase device descriptions that are CURRENTLY CONNECTED
    using pnputil /connected filter.

    pnputil /enum-devices /class {guid} /connected
    lists only devices whose hardware is physically present.
    Phantom drivers (card removed, driver still installed) are excluded.

    Falls back to empty set on failure - caller uses count-based heuristic.
    """
    try:
        result = subprocess.run(
            ["pnputil", "/enum-devices", "/class", class_guid, "/connected"],
            capture_output=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        names = set()
        for line in result.stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key_lower = key.strip().lower()
            if "device description" in key_lower:
                n = val.strip()
                if n:
                    names.add(n.lower())
        return names
    except Exception:
        return set()


def _enum_pnp_class(class_guid: str) -> list:
    """
    Use pnputil to enumerate all devices in a class.
    Returns list of dicts with instance_id, description, driver_name.
    Windows 10+ only.
    """
    try:
        result = subprocess.run(
            ["pnputil", "/enum-devices", "/class", class_guid],
            capture_output=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        devices, current = [], {}
        for line in result.stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                if current.get("instance_id"):
                    devices.append(current)
                    current = {}
                continue
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if "instance id" in key:
                if current.get("instance_id"):
                    devices.append(current)
                current = {"instance_id": val}
            elif "device description" in key:
                current["description"] = val
            elif "driver name" in key:
                current["driver_name"] = val
            elif "status" in key:
                current["status"] = val
        if current.get("instance_id"):
            devices.append(current)
        return devices
    except Exception:
        return []


def _check_ghost(dev_name: str, connected_names: set, all_devs_count: int) -> bool:
    """
    Ghost = driver installed in registry but hardware NOT physically present.

    connected_names comes from pnputil /connected - only hardware currently
    plugged in. If GT 1030 was replaced and its driver was never cleanly
    uninstalled, it appears in the registry but NOT in connected_names.

    - connected_names empty: pnputil unavailable, fall back to count >= 2.
    - connected_names has results: authoritative - not found = phantom ghost.
    """
    name_lower = dev_name.lower()

    if not connected_names:
        return all_devs_count >= 2

    for conn in connected_names:
        if name_lower in conn or conn in name_lower:
            return False

    return True


def _remove_pnp_device(instance_id: str) -> tuple:
    """Remove a PnP device via pnputil. Requires admin."""
    try:
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            return False, "Requires Administrator rights."
    except Exception:
        return False, "Cannot verify admin rights."
    try:
        result = subprocess.run(
            ["pnputil", "/remove-device", instance_id, "/subtree"],
            capture_output=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            return True, "Device removed. Restart may be required."
        out = result.stdout.decode("utf-8", errors="replace").strip()[:120]
        return False, out or "pnputil returned error."
    except Exception as ex:
        return False, str(ex)[:80]


def _open_ghost_dialog(root, dev: dict, pnp_entry: dict, category: str,
                       confirmed_unused: bool):
    """Toplevel info + optional uninstall for a ghost/unused driver."""
    from tkinter import messagebox as _mb
    win = tk.Toplevel(root)
    win.title("Ghost Driver - Check Info")
    win.configure(bg="#0a0e14")
    win.resizable(False, False)
    win.geometry("460x320")
    try:
        win.grab_set()
    except Exception:
        pass

    _W = "#0a0e14"
    _P = "#111827"
    _B = "#1f2937"

    tk.Frame(win, bg=GHOST_MARK, height=3).pack(fill="x")

    hdr = tk.Frame(win, bg="#150508")
    hdr.pack(fill="x", pady=(0, 0))
    tk.Label(hdr, text=f"  ⚠  {category} - Ghost Driver Detected",
             font=(_HDR, 10), bg="#150508", fg=GHOST_MARK, pady=8).pack(side="left")

    body = tk.Frame(win, bg=_W)
    body.pack(fill="both", expand=True, padx=16, pady=12)

    name = dev.get("name", "Unknown")
    ver  = dev.get("version", "")
    date = _fmt_date(dev.get("date", ""))
    days = _driver_age_days(dev.get("date", ""))

    tk.Label(body, text=name, font=(_HDR, 10), bg=_W, fg=TEXT,
             wraplength=420, justify="left").pack(anchor="w")

    meta = tk.Frame(body, bg=_W)
    meta.pack(anchor="w", pady=(2, 8))
    if ver:
        tk.Label(meta, text=f"v{ver}", font=(_MONO, 7), bg=_W, fg=MUTED).pack(side="left")
    if date:
        tk.Label(meta, text=f"  ·  {date}", font=(_MONO, 7), bg=_W, fg=MUTED).pack(side="left")
    if days:
        mo = days // 30
        col = RED if days >= 730 else AMBER
        tk.Label(meta, text=f"  ·  {mo} months old", font=(_MONO, 7, "bold"),
                 bg=_W, fg=col).pack(side="left")

    tk.Frame(body, bg=_B, height=1).pack(fill="x", pady=(0, 8))

    certainty = "100% Unused driver." if confirmed_unused else "Likely unused driver."
    tk.Label(body, text=f"{'🔴' if confirmed_unused else '⚠'}  {certainty}",
             font=(_HDR, 9), bg=_W, fg=RED if confirmed_unused else AMBER).pack(anchor="w")

    tk.Label(body,
             text=(
                 "This driver is installed on your computer but is not currently\n"
                 "used by any active hardware component. It was most likely left\n"
                 "over after replacing or removing the old hardware."
             ),
             font=(_BODY, 8), bg=_W, fg="#8a9db8", justify="left").pack(anchor="w", pady=(4, 0))

    inst_id = pnp_entry.get("instance_id", "") if pnp_entry else ""

    foot = tk.Frame(win, bg="#0d1117")
    foot.pack(fill="x", padx=16, pady=(0, 12))

    status_lbl = tk.Label(foot, text="", font=(_MONO, 7), bg="#0d1117", fg=MUTED)
    status_lbl.pack(anchor="w", pady=(0, 4))

    btn_row = tk.Frame(foot, bg="#0d1117")
    btn_row.pack(fill="x")

    def _do_dm(e=None):
        try: subprocess.Popen(["devmgmt.msc"], shell=True)
        except Exception: pass

    dm_btn = tk.Label(btn_row, text="Open Device Manager",
                      font=(_MONO, 8), bg="#0d1117", fg="#8593a8",
                      cursor="hand2", padx=10, pady=5,
                      highlightbackground="#1f2937", highlightthickness=1)
    dm_btn.pack(side="left", padx=(0, 6))
    dm_btn.bind("<Button-1>", _do_dm)
    dm_btn.bind("<Enter>", lambda e: dm_btn.config(fg=BLUE))
    dm_btn.bind("<Leave>", lambda e: dm_btn.config(fg="#8593a8"))

    if inst_id:
        def _do_remove(e=None):
            if not _mb.askyesno(
                "Remove Driver",
                f"Remove '{name}' from Windows?\n\n"
                "This uninstalls the driver package. A system restart may be needed.\n"
                "Make sure this hardware is no longer in your PC.",
                parent=win
            ):
                return
            status_lbl.config(text="Removing…", fg=AMBER)
            win.update()
            ok, msg = _remove_pnp_device(inst_id)
            status_lbl.config(text=msg, fg=GREEN if ok else RED)

        rm_btn = tk.Label(btn_row, text="🗑 Remove Driver",
                          font=(_MONO, 8, "bold"), bg="#1a0508", fg=GHOST_MARK,
                          cursor="hand2", padx=10, pady=5,
                          highlightbackground=GHOST_BD, highlightthickness=1)
        rm_btn.pack(side="left")
        rm_btn.bind("<Button-1>", _do_remove)
        rm_btn.bind("<Enter>", lambda e: rm_btn.config(fg="#ffffff"))
        rm_btn.bind("<Leave>", lambda e: rm_btn.config(fg=GHOST_MARK))

    close_btn = tk.Label(btn_row, text="Close", font=(_MONO, 8),
                         bg="#0d1117", fg=MUTED, cursor="hand2",
                         padx=10, pady=5,
                         highlightbackground="#1f2937", highlightthickness=1)
    close_btn.pack(side="right")
    close_btn.bind("<Button-1>", lambda e: win.destroy())


def _build_ext_device_row(parent, dev: dict, pnp_entry: dict, category: str,
                           accent: str, root_ref) -> tk.Frame:
    """Single driver row for SEE EVERYTHING / SEE OUTDATED views."""
    days = _driver_age_days(dev.get("date", ""))
    status_txt, _, _, bar_col, _ = _age_info(days)

    is_ghost        = dev.get("_ghost", False)
    confirmed_unused = dev.get("_confirmed_unused", False)

    row_bg = GHOST_BG if is_ghost else "#0c0d16"
    row_bd = GHOST_BD if is_ghost else "#141828"

    outer = tk.Frame(parent, bg=row_bg, highlightthickness=1, highlightbackground=row_bd)
    outer.pack(fill="x", pady=1)

    tk.Frame(outer, bg=GHOST_MARK if is_ghost else accent, width=3).pack(side="left", fill="y")

    ico = tk.Label(outer, text="⚠" if is_ghost else "●",
                   font=(_MONO, 8, "bold" if is_ghost else "normal"),
                   bg=row_bg, fg=GHOST_MARK if is_ghost else accent, padx=5)
    ico.pack(side="left", pady=5)

    info = tk.Frame(outer, bg=row_bg)
    info.pack(side="left", fill="x", expand=True, pady=3)

    name_col = RED if is_ghost else TEXT
    tk.Label(info, text=dev.get("name", "Unknown")[:48],
             font=(_BODY, 7), bg=row_bg, fg=name_col, anchor="w").pack(anchor="w")

    meta = tk.Frame(info, bg=row_bg)
    meta.pack(anchor="w")
    if dev.get("version"):
        tk.Label(meta, text=f"v{dev['version']}", font=(_MONO, 6),
                 bg=row_bg, fg=MUTED).pack(side="left")
    if dev.get("date"):
        tk.Label(meta, text=_fmt_date(dev["date"]),
                 font=(_MONO, 6), bg=row_bg, fg=MUTED).pack(side="left", padx=(8, 0))

    right = tk.Frame(outer, bg=row_bg)
    right.pack(side="right", padx=6, pady=3)

    badge_fg = RED if days and days >= 730 else (AMBER if days and days >= 365 else bar_col)
    tk.Label(right, text=f" {status_txt} ",
             font=(_MONO, 5, "bold"), bg="#0d1522", fg=badge_fg,
             padx=4, pady=2).pack()

    if is_ghost:
        lbl_txt = "100% UNUSED" if confirmed_unused else "⚠ ISSUE"
        issue_btn = tk.Label(right, text=lbl_txt,
                             font=(_MONO, 5, "bold"), bg="#1a0508", fg=GHOST_MARK,
                             cursor="hand2", padx=5, pady=2,
                             highlightbackground=GHOST_BD, highlightthickness=1)
        issue_btn.pack(pady=(3, 0))

        def _on_issue(e=None, d=dev, pe=pnp_entry, cat=category, cu=confirmed_unused):
            try:
                _open_ghost_dialog(outer.winfo_toplevel(), d, pe, cat, cu)
            except Exception:
                pass

        issue_btn.bind("<Button-1>", _on_issue)
        issue_btn.bind("<Enter>", lambda e: issue_btn.config(fg="#ffffff"))
        issue_btn.bind("<Leave>", lambda e: issue_btn.config(fg=GHOST_MARK))

    return outer


def _build_see_everything_view(parent, all_lists: list, ghost_sets: list,
                                pnp_lists: list) -> tk.Frame:
    """Extended view - all devices across all categories."""
    wrap = tk.Frame(parent, bg=PANEL2)
    wrap.pack(fill="x", padx=10, pady=(4, 8))

    for idx, (guid, cat_name, wmi_cls, accent) in enumerate(_CAT_META):
        devs      = all_lists[idx] if idx < len(all_lists) else []
        ghosts    = ghost_sets[idx] if idx < len(ghost_sets) else set()
        pnp_devs  = pnp_lists[idx] if idx < len(pnp_lists) else []

        if not devs:
            continue

        # Category header
        cat_hdr = tk.Frame(wrap, bg="#0a0c14")
        cat_hdr.pack(fill="x", pady=(6 if idx else 0, 2))
        tk.Frame(cat_hdr, bg=accent, width=3).pack(side="left", fill="y")
        tk.Label(cat_hdr, text=f"  {cat_name}  ·  {len(devs)} device{'s' if len(devs)!=1 else ''}",
                 font=(_MONO, 7, "bold"), bg="#0a0c14", fg=accent, pady=3).pack(side="left")

        for dev in devs:
            pnp_match = next(
                (p for p in pnp_devs
                 if dev.get("name", "").lower() in p.get("description", "").lower()
                 or p.get("description", "").lower() in dev.get("name", "").lower()),
                None
            )
            is_g = dev.get("name", "").lower() in ghosts
            d2   = dict(dev)
            d2["_ghost"]            = is_g
            d2["_confirmed_unused"] = is_g and bool(pnp_match)
            _build_ext_device_row(wrap, d2, pnp_match, cat_name, accent, parent)

    return wrap


def _build_see_outdated_view(parent, all_lists: list, ghost_sets: list,
                              pnp_lists: list) -> tk.Frame:
    """Extended view - only drivers >= 730 days (24 months), oldest first."""
    wrap = tk.Frame(parent, bg=PANEL2)
    wrap.pack(fill="x", padx=10, pady=(4, 8))

    aged: list = []
    for idx, (guid, cat_name, wmi_cls, accent) in enumerate(_CAT_META):
        devs   = all_lists[idx] if idx < len(all_lists) else []
        ghosts = ghost_sets[idx] if idx < len(ghost_sets) else set()
        pnp_ds = pnp_lists[idx] if idx < len(pnp_lists) else []
        for dev in devs:
            days = _driver_age_days(dev.get("date", ""))
            if days is not None and days >= 730:
                pnp_match = next(
                    (p for p in pnp_ds
                     if dev.get("name", "").lower() in p.get("description", "").lower()),
                    None
                )
                aged.append((days, dev, pnp_match, cat_name, accent,
                             dev.get("name", "").lower() in ghosts))

    aged.sort(key=lambda x: x[0], reverse=True)

    if not aged:
        tk.Label(wrap,
                 text="  No drivers older than 24 months detected.",
                 font=(_BODY, 8), bg=PANEL2, fg=MUTED, pady=12).pack(fill="x")
        return wrap

    for days, dev, pnp_match, cat_name, accent, is_g in aged:
        d2 = dict(dev)
        d2["_ghost"]            = is_g
        d2["_confirmed_unused"] = is_g and bool(pnp_match)

        row_bg = GHOST_BG if is_g else PANEL2
        row_bd = GHOST_BD if is_g else "#141828"
        outer  = tk.Frame(wrap, bg=row_bg, highlightthickness=1,
                          highlightbackground=row_bd)
        outer.pack(fill="x", pady=1)

        tk.Frame(outer, bg=RED if days >= 730 else AMBER, width=3).pack(side="left", fill="y")

        lbl_frame = tk.Frame(outer, bg=row_bg)
        lbl_frame.pack(side="left", fill="x", expand=True, padx=(6, 0), pady=3)

        cat_badge = tk.Label(lbl_frame, text=cat_name,
                             font=(_MONO, 5, "bold"), bg="#111520", fg=accent, padx=4)
        cat_badge.pack(side="left", padx=(0, 6))
        tk.Label(lbl_frame, text=dev.get("name", "Unknown")[:46],
                 font=(_BODY, 7), bg=row_bg, fg=RED if is_g else TEXT,
                 anchor="w").pack(side="left")

        mo = days // 30
        right = tk.Frame(outer, bg=row_bg)
        right.pack(side="right", padx=8, pady=3)
        tk.Label(right, text=f"{mo}mo OLD",
                 font=(_MONO, 6, "bold"), bg="#0d1522",
                 fg=RED if days >= 730 else AMBER, padx=5, pady=2).pack()

        if is_g:
            lbl_t = "100% UNUSED" if d2["_confirmed_unused"] else "⚠ GHOST"
            issue = tk.Label(right, text=lbl_t,
                             font=(_MONO, 5, "bold"), bg="#1a0508", fg=GHOST_MARK,
                             cursor="hand2", padx=5, pady=2,
                             highlightbackground=GHOST_BD, highlightthickness=1)
            issue.pack(pady=(2, 0))

            def _on_issue(e=None, d=d2, pe=pnp_match, cat=cat_name,
                          cu=d2["_confirmed_unused"]):
                try:
                    _open_ghost_dialog(outer.winfo_toplevel(), d, pe, cat, cu)
                except Exception:
                    pass

            issue.bind("<Button-1>", _on_issue)
            issue.bind("<Enter>", lambda e: issue.config(fg="#ffffff"))
            issue.bind("<Leave>", lambda e: issue.config(fg=GHOST_MARK))

    return wrap


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
            raw_product         = _v("ProductName")
            info["version_tag"] = _v("DisplayVersion")
            info["build"]       = _v("CurrentBuildNumber")
            # Windows 11 reports build 22000+; ProductName may still say "Windows 10"
            try:
                build_int = int(info["build"])
            except (ValueError, TypeError):
                build_int = 0
            if build_int >= 22000 and "10" in raw_product:
                info["product"] = raw_product.replace("Windows 10", "Windows 11")
            else:
                info["product"] = raw_product
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

    # Scrollable canvas - width bound to canvas so content always fills
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
    # No add="+": overwrite the previous page's global wheel handler instead
    # of stacking a dead one per page visit.
    wrap.bind_all("<MouseWheel>", _wheel)

    wrap.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    refs = {}
    _build_header(sf, refs)

    # Upgrade Readiness entry (2026-07): this page lists the machine's parts
    # and drivers, so the compatibility check is one click away.
    _ur = tk.Frame(sf, bg=BG)
    _ur.pack(fill="x", padx=16)
    _lnk = tk.Label(_ur, text="UPGRADE READINESS ->", font=(_MONO, 7, "bold"),
                    bg=BG, fg="#10b981", cursor="hand2")
    _lnk.pack(side="right")
    _lnk.bind("<Enter>", lambda e: _lnk.config(fg="#34d399"))
    _lnk.bind("<Leave>", lambda e: _lnk.config(fg="#10b981"))
    _lnk.bind("<Button-1>", lambda e: win_self.open_upgrade_readiness("cpu"))
    _build_hero(sf, refs)
    _build_driver_section(sf, refs)
    _build_bottom_row(sf, refs)
    _build_checklist(sf)

    _start_pulse(refs)

    def _do_scan():
        # ── Registry: all devices per class ──────────────────────────────────
        raw_lists = []
        for guid, cat, wmi_cls, _ in _CAT_META:
            raw_lists.append(_read_all_class_drivers(guid))

        _FALLBACK_NAMES = [
            "Display adapter not detected", "Audio device not detected",
            "Network adapter not detected", "USB controller not detected",
        ]
        all_lists = [
            lst or [{"name": _FALLBACK_NAMES[i], "version": "", "date": ""}]
            for i, lst in enumerate(raw_lists)
        ]
        all_drivers_primary = [lst[0] for lst in all_lists]

        # ── pnputil /connected: which devices are physically present ─────────
        # Win32_VideoController (WMI) returns phantom cards too - unreliable.
        # pnputil /connected filters to hardware that is currently plugged in.
        ghost_sets = []
        for idx, (guid, cat, wmi_cls, _) in enumerate(_CAT_META):
            connected = _get_pnp_connected_names(guid)
            devs      = all_lists[idx]
            ghosts    = {
                d["name"].lower()
                for d in devs
                if _check_ghost(d["name"], connected, len(devs))
            }
            ghost_sets.append(ghosts)

        # ── PnP: instance IDs for uninstall support ───────────────────────────
        pnp_lists = []
        for guid, cat, wmi_cls, _ in _CAT_META:
            pnp_lists.append(_enum_pnp_class(guid))

        # ── Count outdated drivers (>= 730 days) ─────────────────────────────
        outdated_count = sum(
            1
            for lst in all_lists
            for d in lst
            if (_driver_age_days(d.get("date", "")) or 0) >= 730
        )

        win_info = _get_windows_info()
        startup  = _get_startup_programs()
        score    = _compute_score(all_drivers_primary, len(startup))

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

        scan_data = {
            "all_lists":  all_lists,
            "ghost_sets": ghost_sets,
            "pnp_lists":  pnp_lists,
        }

        try:
            sf.after(0, lambda: _apply(refs, all_drivers_primary, all_lists,
                                       win_info, startup, score,
                                       uptime_str, last_boot_str,
                                       scan_data, outdated_count))
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
    tk.Label(left, text="⚙", font=(_BODY, 14), bg="#0b1220",
             fg=BLUE).pack(side="left", pady=10)
    tk.Label(left, text="  FIRST SETUP & DRIVERS",
             font=(_MONO, 10, "bold"), bg="#0b1220", fg=TEXT).pack(side="left")
    tk.Label(left, text="   ·   system readiness  ·  driver health  ·  startup control",
             font=(_MONO, 7), bg="#0b1220", fg=MUTED).pack(side="left")

    right = tk.Frame(inner, bg="#0b1220")
    right.pack(side="right", fill="y")

    dot = tk.Label(right, text="● Scanning…", font=(_MONO, 7),
                   bg="#0b1220", fg=AMBER)
    dot.pack(side="right", padx=(8, 0), pady=14)
    refs["header_dot"] = dot

    def _make_btn(label, bg_, cmd):
        b = tk.Label(right, text=label, font=(_MONO, 8, "bold"),
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

    grade_lbl = tk.Label(gf, text="SCANNING", font=(_MONO, 8, "bold"),
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
                       font=(_HDR, 11), bg=PANEL, fg=TEXT)
    win_lbl.pack(side="left")
    build_badge = tk.Label(line1, text="", font=(_MONO, 7, "bold"),
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
        tk.Label(f, text=lbl, font=(_MONO, 6), bg=PANEL, fg=MUTED).pack(anchor="w")
        v = tk.Label(f, text="-", font=(_MONO, 8, "bold"), bg=PANEL, fg=TEXT)
        v.pack(anchor="w")
        refs[key] = v

    bar_f = tk.Frame(info, bg=PANEL)
    bar_f.pack(fill="x", pady=(8, 0))
    scan_dot = tk.Label(bar_f, text="●", font=(_MONO, 9), bg=PANEL, fg=AMBER)
    scan_dot.pack(side="left")
    scan_msg = tk.Label(bar_f, text="  Scanning registry for driver information…",
                        font=(_MONO, 7), bg=PANEL, fg=MUTED)
    scan_msg.pack(side="left")
    refs["scan_dot"] = scan_dot
    refs["scan_msg"] = scan_msg


# ─── Driver cards ─────────────────────────────────────────────────────────────
def _build_driver_section(parent, refs):
    sec = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                   highlightbackground=BORDER)
    sec.pack(fill="x", padx=15, pady=(0, 5))

    # ── Header with mode-switch buttons ──────────────────────────────────────
    hdr = tk.Frame(sec, bg="#091628")
    hdr.pack(fill="x")
    tk.Label(hdr, text="  DRIVER HEALTH", font=(_MONO, 9, "bold"),
             bg="#091628", fg=BLUE, pady=5).pack(side="left")

    btn_area = tk.Frame(hdr, bg="#091628")
    btn_area.pack(side="right", padx=6, pady=4)

    summ = tk.Label(hdr, text="scanning…", font=(_MONO, 7),
                    bg="#091628", fg=MUTED)
    summ.pack(side="right", padx=12)
    refs["drv_summary"] = summ

    # ── Normal 4-card body ────────────────────────────────────────────────────
    body = tk.Frame(sec, bg=PANEL)
    body.pack(fill="x", padx=10, pady=(6, 8))
    refs["cards_body"] = body
    refs["ext_sec"]    = sec   # needed to attach ext_frame to same container

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

    # ── Mode state ────────────────────────────────────────────────────────────
    refs["drv_mode"]     = {"v": "normal"}
    refs["drv_ext_view"] = None   # holds current extended view frame

    # ── Mode switch helpers ───────────────────────────────────────────────────
    def _make_mode_btn(parent_f, label, bg_n, fg_n, key):
        b = tk.Label(parent_f, text=label, font=(_MONO, 6, "bold"),
                     bg=bg_n, fg=fg_n, cursor="hand2",
                     padx=8, pady=3,
                     highlightbackground=BORDER, highlightthickness=1)
        b.pack(side="left", padx=(0, 4))
        refs[f"drv_btn_{key}"] = b
        return b

    def _switch_mode(mode: str):
        refs["drv_mode"]["v"] = mode
        # Destroy previous ext view
        old = refs.get("drv_ext_view")
        if old:
            try: old.destroy()
            except Exception: pass
            refs["drv_ext_view"] = None

        if mode == "normal":
            body.pack(fill="x", padx=10, pady=(6, 8))
            # Restore mode buttons
            for w in btn_area.winfo_children():
                w.destroy()
            _wire_mode_buttons()
        else:
            body.pack_forget()
            for w in btn_area.winfo_children():
                w.destroy()
            # BACK button
            back_btn = tk.Label(btn_area, text="← BACK",
                                font=(_MONO, 6, "bold"),
                                bg="#0d1520", fg=BLUE, cursor="hand2",
                                padx=8, pady=3,
                                highlightbackground=BORDER, highlightthickness=1)
            back_btn.pack(side="left")
            back_btn.bind("<Button-1>", lambda e: _switch_mode("normal"))
            back_btn.bind("<Enter>",    lambda e: back_btn.config(fg="#ffffff"))
            back_btn.bind("<Leave>",    lambda e: back_btn.config(fg=BLUE))

            # Build view from cached scan data (if available)
            cached = refs.get("drv_scan_data")
            if cached:
                _build_ext_view(mode, cached)

    def _build_ext_view(mode: str, data: dict):
        al  = data["all_lists"]
        gs  = data["ghost_sets"]
        pnp = data["pnp_lists"]
        old = refs.get("drv_ext_view")
        if old:
            try: old.destroy()
            except Exception: pass
        if mode == "everything":
            frame = _build_see_everything_view(sec, al, gs, pnp)
        else:
            frame = _build_see_outdated_view(sec, al, gs, pnp)
        refs["drv_ext_view"] = frame

    refs["_build_ext_view"] = _build_ext_view
    refs["_switch_mode"]    = _switch_mode

    def _wire_mode_buttons():
        see_all_btn = _make_mode_btn(btn_area, "SEE EVERYTHING",
                                     "#0d1520", BLUE, "see_all")
        see_all_btn.bind("<Button-1>", lambda e: _switch_mode("everything"))
        see_all_btn.bind("<Enter>",    lambda e: see_all_btn.config(fg="#ffffff"))
        see_all_btn.bind("<Leave>",    lambda e: see_all_btn.config(fg=BLUE))

        out_count = refs.get("drv_outdated_count", 0)
        lbl = f"SEE OUTDATED  {out_count}" if out_count else "SEE OUTDATED"
        see_out_btn = _make_mode_btn(btn_area, lbl, "#1a0a0a", RED, "see_out")
        see_out_btn.bind("<Button-1>", lambda e: _switch_mode("outdated"))
        see_out_btn.bind("<Enter>",    lambda e: see_out_btn.config(fg="#ffffff"))
        see_out_btn.bind("<Leave>",    lambda e: see_out_btn.config(fg=RED))
        refs["drv_btn_see_out"] = see_out_btn

    _wire_mode_buttons()


def _make_driver_card(parent, category, subcategory, icon, accent):
    outer = tk.Frame(parent, bg=PANEL2, highlightthickness=1,
                     highlightbackground=BORDER)
    row = tk.Frame(outer, bg=PANEL2)
    row.pack(fill="x")

    ab = tk.Frame(row, bg="#374151", width=4)
    ab.pack(side="left", fill="y")

    # Category column - wider + larger fonts for readability
    cf = tk.Frame(row, bg=PANEL2, width=96)
    cf.pack(side="left", fill="y")
    cf.pack_propagate(False)
    tk.Label(cf, text=icon, font=(_BODY, 11), bg=PANEL2, fg=accent
             ).pack(pady=(7, 0))
    tk.Label(cf, text=category, font=(_MONO, 8, "bold"), bg=PANEL2, fg=accent
             ).pack()
    tk.Label(cf, text=subcategory, font=(_MONO, 7), bg=PANEL2, fg="#8a9db8"
             ).pack(pady=(0, 7))

    tk.Frame(row, bg=BORDER, width=1).pack(side="left", fill="y", pady=4)

    inf = tk.Frame(row, bg=PANEL2)
    inf.pack(side="left", fill="both", expand=True, padx=(10, 0))

    name_lbl = tk.Label(inf, text="Scanning…",
                        font=(_HDR, 10), bg=PANEL2, fg=TEXT, anchor="w")
    name_lbl.pack(anchor="w", pady=(8, 2))

    meta = tk.Frame(inf, bg=PANEL2)
    meta.pack(anchor="w")
    ver_lbl  = tk.Label(meta, text="", font=(_MONO, 8), bg=PANEL2, fg=MUTED)
    ver_lbl.pack(side="left")
    date_lbl = tk.Label(meta, text="", font=(_MONO, 8), bg=PANEL2, fg=MUTED)
    date_lbl.pack(side="left", padx=(12, 0))

    # Age freshness bar
    age_bar_bg = tk.Frame(inf, bg="#1f2937", height=3)
    age_bar_bg.pack(fill="x", pady=(3, 7))
    age_bar_bg.pack_propagate(False)
    age_bar_fill = tk.Frame(age_bar_bg, bg="#374151", height=3)
    age_bar_fill.place(x=0, y=0, relwidth=0.0, relheight=1.0)

    rf = tk.Frame(row, bg=PANEL2, width=136)
    rf.pack(side="right", fill="y", padx=10)
    rf.pack_propagate(False)

    badge = tk.Label(rf, text="SCANNING", font=(_MONO, 8, "bold"),
                     bg="#1f2937", fg=MUTED, padx=8, pady=3)
    badge.pack(pady=(10, 2))

    def _open_dm(e=None):
        try: subprocess.Popen(["devmgmt.msc"], shell=True)
        except Exception: pass

    action = tk.Label(rf, text="⟶ Device Manager",
                      font=(_MONO, 7), bg=PANEL2, fg="#8593a8",
                      cursor="hand2")
    action.pack()
    action.bind("<Button-1>", _open_dm)
    action.bind("<Enter>", lambda e: action.config(fg=BLUE))
    action.bind("<Leave>", lambda e: action.config(fg="#8593a8"))

    # Expand toggle button - shown only after scan with extra devices
    expand_btn = tk.Label(rf, text="", font=(_MONO, 7),
                          bg=PANEL2, fg="#6b7280", cursor="hand2")
    expand_btn.pack(pady=(4, 0))

    # Expand panel - shows all detected devices in this class
    _EXP_BG = "#0a0e17"
    expand_panel = tk.Frame(outer, bg=_EXP_BG)
    _exp_state = {"open": False}

    def _toggle_expand(e=None):
        if _exp_state["open"]:
            expand_panel.pack_forget()
            # Restore collapsed label - update arrow, keep count
            lbl = expand_btn.cget("text")
            expand_btn.config(
                text=lbl.replace("▲ zwiń", "▼ pokaż wszystkie"),
                fg="#8a9db8",
            )
        else:
            expand_panel.pack(fill="x", padx=(4, 4), pady=(0, 4))
            lbl = expand_btn.cget("text")
            expand_btn.config(
                text=lbl.replace("▼ pokaż wszystkie", "▲ zwiń"),
                fg=accent,
            )
        _exp_state["open"] = not _exp_state["open"]

    expand_btn.bind("<Button-1>", _toggle_expand)
    expand_btn.bind("<Enter>", lambda e: expand_btn.config(fg=accent))
    expand_btn.bind("<Leave>", lambda e: expand_btn.config(
        fg=accent if _exp_state["open"] else "#4b5563"))

    # Ghost badge - hidden by default, shown by _fill_card when ghosts detected
    ghost_badge = tk.Label(rf, text="",
                           font=(_MONO, 7, "bold"),
                           bg=GHOST_BG, fg=GHOST_MARK,
                           padx=7, pady=3)
    # NOT packed here - _fill_card shows/hides it

    return {
        "frame": outer, "bar": ab,
        "name": name_lbl, "ver": ver_lbl, "date": date_lbl,
        "badge": badge, "age_fill": age_bar_fill,
        "expand_btn": expand_btn, "expand_panel": expand_panel,
        "accent": accent, "ghost_badge": ghost_badge,
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
    tk.Label(hdr_l, text="  QUICK ACTIONS", font=(_MONO, 9, "bold"),
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

        btn = tk.Label(grid, text=label, font=(_MONO, 8, "bold"),
                       bg=bg_, fg=TEXT, anchor="w", padx=10, pady=7, cursor="hand2")
        btn.grid(row=r, column=c, padx=3, pady=2, sticky="ew")
        grid.columnconfigure(c, weight=1)
        btn.bind("<Button-1>", lambda e, f=_run: f())
        btn.bind("<Enter>", lambda e, b=btn, o=bg_: b.config(bg=_lighten(o)))
        btn.bind("<Leave>", lambda e, b=btn, o=bg_: b.config(bg=o))

    foot_l = tk.Frame(left, bg=PANEL)
    foot_l.pack(fill="x", padx=8, pady=(0, 6))
    tk.Label(foot_l, text="⟶ More tools in Optimization tab",
             font=(_MONO, 7), bg=PANEL, fg="#8593a8").pack(side="right")

    # Startup Programs
    right = tk.Frame(wrap, bg=PANEL, highlightthickness=1,
                     highlightbackground=BORDER)
    right.pack(side="right", fill="both", expand=True)

    hdr_r = tk.Frame(right, bg="#0d1a12")
    hdr_r.pack(fill="x")
    tk.Label(hdr_r, text="  STARTUP PROGRAMS", font=(_MONO, 9, "bold"),
             bg="#0d1a12", fg=GREEN, pady=4).pack(side="left")
    cnt_lbl = tk.Label(hdr_r, text="scanning…", font=(_MONO, 7),
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
        dot = tk.Label(rf, text="●", font=(_MONO, 8), bg=PANEL2, fg="#74839a")
        dot.pack(side="left", padx=(6, 4), pady=3)
        n_l = tk.Label(rf, text="-", font=(_MONO, 8), bg=PANEL2,
                       fg=MUTED, anchor="w")
        n_l.pack(side="left", fill="x", expand=True)
        src = tk.Label(rf, text="", font=(_MONO, 6), bg=PANEL2, fg="#74839a")
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
                    font=(_MONO, 7), bg=PANEL, fg="#8593a8", cursor="hand2")
    lnk2.pack(side="right")
    lnk2.bind("<Button-1>", lambda e: _open_startup())
    lnk2.bind("<Enter>", lambda e: lnk2.config(fg=GREEN))
    lnk2.bind("<Leave>", lambda e: lnk2.config(fg="#8593a8"))


# ─── Setup Checklist ──────────────────────────────────────────────────────────
def _build_checklist(parent):
    sec = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                   highlightbackground=BORDER)
    sec.pack(fill="x", padx=15, pady=(0, 14))

    hdr = tk.Frame(sec, bg="#1a1200")
    hdr.pack(fill="x")
    tk.Label(hdr, text="  SETUP CHECKLIST", font=(_MONO, 9, "bold"),
             bg="#1a1200", fg=AMBER, pady=5).pack(side="left")
    tk.Label(hdr, text="  Click any item to mark as done - saved automatically",
             font=(_MONO, 7), bg="#1a1200", fg=MUTED).pack(side="left")

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
                      font=(_MONO, 11, "bold"), bg=PANEL2,
                      fg=GREEN if done else "#374151")
        ck.pack(side="left", padx=(8, 6), pady=6)

        txt = tk.Label(item, text=label, font=(_MONO, 8), bg=PANEL2,
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
def _apply(refs, drivers, all_driver_lists, win_info, startup, score,
           uptime_str, last_boot_str, scan_data=None, outdated_count=0):
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

        ghost_sets = scan_data.get("ghost_sets", []) if scan_data else []
        for i, (card, d, all_devs) in enumerate(
                zip(refs.get("cards", []), drivers, all_driver_lists)):
            gh = ghost_sets[i] if i < len(ghost_sets) else set()
            _fill_card(card, d, ghost_names=gh)
            _fill_expand_panel(card, all_devs, ghost_names=gh)

        # ── Store scan data for extended views ────────────────────────────────
        if scan_data:
            refs["drv_scan_data"]      = scan_data
            refs["drv_outdated_count"] = outdated_count

            # Update SEE OUTDATED button label
            try:
                ob = refs.get("drv_btn_see_out")
                if ob and ob.winfo_exists():
                    lbl = f"SEE OUTDATED  {outdated_count}" if outdated_count else "SEE OUTDATED"
                    ob.config(text=lbl, fg=RED if outdated_count else MUTED)
            except Exception:
                pass

            # If currently in extended mode, rebuild the view with real data
            mode = refs.get("drv_mode", {}).get("v", "normal")
            if mode in ("everything", "outdated"):
                builder = refs.get("_build_ext_view")
                if builder:
                    try:
                        builder(mode, scan_data)
                    except Exception:
                        pass

        cnt   = len(startup)
        c_col = RED if cnt > 12 else AMBER if cnt > 7 else GREEN
        refs.get("startup_cnt", tk.Label()).config(
            text=f"{cnt} items detected", fg=c_col)
        # Build set of running exe names once (lowercase) for O(1) lookup
        _running_exes: set = set()
        if _HAS_PSUTIL:
            try:
                for _p in psutil.process_iter(["name"]):
                    try:
                        _running_exes.add(_p.info["name"].lower())
                    except Exception:
                        pass
            except Exception:
                pass

        for i, row in enumerate(refs.get("startup_rows", [])):
            if i < cnt:
                s = startup[i]
                row["frame"].pack(fill="x", pady=1)
                # Dot = is the exe actually running right now?
                exe_lower = s.get("exe", "").lower()
                if exe_lower and exe_lower in _running_exes:
                    dot_color = GREEN   # running now
                    src_text  = f"{s['source']} · running"
                else:
                    dot_color = MUTED   # registered but not running
                    src_text  = s["source"]
                row["dot"].config(fg=dot_color)
                row["name"].config(text=s["name"][:30], fg=TEXT)
                row["src"].config(text=src_text, fg=MUTED)
            else:
                row["frame"].pack_forget()

    except Exception:
        import traceback
        traceback.print_exc()


def _fill_card(card, data, ghost_names: set = None):
    name     = data.get("name", "Unknown")
    version  = data.get("version", "")
    date_str = data.get("date", "")
    days     = _driver_age_days(date_str)
    status, txt_col, badge_bg, bar_col, brd_col = _age_info(days)
    age_ratio = max(0.0, 1.0 - days / 730) if days is not None else 0.0
    ghost_count = len(ghost_names) if ghost_names else 0

    try:
        # Ghost cards: bordeaux border + red accent bar + ghost badge in primary slot
        if ghost_count > 0:
            card["frame"].config(highlightbackground=GHOST_BD, bg=GHOST_BG)
            card["bar"].config(bg=GHOST_MARK)
            n = "ghost" if ghost_count == 1 else "ghosts"
            # Override the main status badge - most visible right-side slot
            card["badge"].config(
                text=f"  ⚠ {ghost_count} {n}  ",
                bg=GHOST_BG, fg=GHOST_MARK,
                highlightbackground=GHOST_BD, highlightthickness=1,
            )
        else:
            card["frame"].config(highlightbackground=brd_col, bg=PANEL2)
            card["bar"].config(bg=bar_col)
            card["badge"].config(
                text=f"  {status}  ", bg=badge_bg, fg=txt_col,
                highlightthickness=0,
            )

        card["name"].config(text=name[:50])
        card["ver"].config(text=f"v{version}" if version else "version unknown")
        card["date"].config(text=_fmt_date(date_str))
        card["age_fill"].place(relwidth=age_ratio)
        card["age_fill"].config(bg=bar_col)
    except Exception:
        pass

    # Secondary ghost badge - age info below the main badge
    try:
        gb = card.get("ghost_badge")
        if gb:
            if ghost_count > 0:
                # Show driver age as secondary indicator
                age_txt = f"  {status}  " if status != "UNKNOWN" else "  AGE UNKNOWN  "
                gb.config(text=age_txt,
                          bg="#1a0508", fg="#f87171",
                          highlightbackground=GHOST_BD, highlightthickness=1)
                gb.pack(pady=(0, 4))
            else:
                gb.pack_forget()
    except Exception:
        pass


def _fill_expand_panel(card, all_devs: list, ghost_names: set = None):
    """Populate the expand panel with all detected devices for this class."""
    try:
        ep = card.get("expand_panel")
        eb = card.get("expand_btn")
        accent = card.get("accent", BLUE)
        if ep is None or eb is None:
            return

        # Clear existing children
        for w in ep.winfo_children():
            w.destroy()

        extra = all_devs[1:]  # skip primary (already shown in card header)
        if not extra:
            eb.config(text="")
            return

        ghost_count_in_list = sum(
            1 for d in all_devs
            if d.get("name", "").lower() in (ghost_names or set())
        )

        # Update expand button - show count + ghost warning if applicable
        btn_lbl = f"▼ pokaż wszystkie ({len(all_devs)})"
        btn_fg  = "#8a9db8"
        if ghost_count_in_list:
            btn_lbl = f"▼ pokaż wszystkie ({len(all_devs)})  ⚠ GHOST"
            btn_fg  = GHOST_MARK
        eb.config(text=btn_lbl, fg=btn_fg)

        # Build header row inside expand panel
        _EXP_BG = "#0a0e17"
        hdr = tk.Frame(ep, bg=_EXP_BG)
        hdr.pack(fill="x", padx=6, pady=(4, 2))
        hdr_txt = f"WSZYSTKIE URZĄDZENIA  ({len(all_devs)})"
        hdr_fg  = GHOST_MARK if ghost_count_in_list else TEXT
        tk.Label(hdr, text=hdr_txt,
                 font=(_MONO, 7, "bold"), bg=_EXP_BG, fg=hdr_fg).pack(side="left")
        tk.Frame(hdr, bg="#1a2535", height=1).pack(
            side="left", fill="x", expand=True, padx=(6, 0))

        for dev in all_devs:
            name     = dev.get("name", "Unknown")
            ver      = dev.get("version", "")
            date_str = dev.get("date", "")
            days     = _driver_age_days(date_str)
            status, txt_col, _, bar_col, _ = _age_info(days)
            is_ghost = name.lower() in (ghost_names or set())

            # Ghost or old driver overrides
            if is_ghost:
                row_bg = GHOST_BG
                row_bd = GHOST_BD
                bar_col = GHOST_MARK
                txt_col = GHOST_MARK
            elif days is not None and days >= 730:
                row_bg = _EXP_BG
                row_bd = "#111e2e"
                txt_col = RED
                bar_col = RED
            else:
                row_bg = _EXP_BG
                row_bd = "#111e2e"

            row = tk.Frame(ep, bg=row_bg, highlightthickness=1,
                           highlightbackground=row_bd)
            row.pack(fill="x", padx=6, pady=1)

            # Thin age-color accent on left
            tk.Frame(row, bg=bar_col, width=3).pack(side="left", fill="y")

            info = tk.Frame(row, bg=row_bg)
            info.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=3)

            name_fg = GHOST_MARK if is_ghost else TEXT
            name_lbl = tk.Label(info, text=name[:52],
                                font=(_BODY, 7), bg=row_bg, fg=name_fg, anchor="w")
            name_lbl.pack(anchor="w")

            meta = tk.Frame(info, bg=row_bg)
            meta.pack(anchor="w")
            if ver:
                tk.Label(meta, text=f"v{ver}", font=(_MONO, 6),
                         bg=row_bg, fg=MUTED).pack(side="left")
            if date_str:
                tk.Label(meta, text=_fmt_date(date_str),
                         font=(_MONO, 6), bg=row_bg, fg=MUTED).pack(
                         side="left", padx=(8, 0))

            badge_txt = "⚠ GHOST" if is_ghost else f" {status} "
            badge_bg  = GHOST_BG  if is_ghost else "#0d1522"
            badge = tk.Label(row, text=badge_txt, font=(_MONO, 6, "bold"),
                             bg=badge_bg, fg=txt_col, padx=4, pady=2)
            badge.pack(side="right", padx=(0, 6), pady=3)

        tk.Frame(ep, bg="#0a0e17", height=4).pack(fill="x")

    except Exception:
        pass


# Arc gauge
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
                           font=(_MONO, 18, "bold"), fill=col, anchor="center")
        canvas.create_text(cx, cy + 17, text="/100",
                           font=(_MONO, 7), fill=MUTED, anchor="center")
    else:
        canvas.create_text(cx, cy, text="-",
                           font=(_MONO, 18, "bold"), fill=MUTED, anchor="center")
