# ui/pages/startup_manager.py
"""
STARTUP MANAGER
Read, analyze and manage Windows startup programs.
Splits entries into two panels:
  • TOP:    "Optimize at startup" — entries with High/Medium impact
  • BOTTOM: "Disable from startup" — entries safe to turn off
"""

import tkinter as tk
from tkinter import messagebox
import threading
import os
import json

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

try:
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    import sys as _sys
    _APP_DIR = os.path.dirname(_sys.executable) if getattr(_sys, "frozen", False) \
               else os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

_PREFS_PATH = os.path.join(_APP_DIR, "data", "cache", "startup_prefs.json")

# ─── Known heavy hitters ─────────────────────────────────────────────────────
# Maps lowercase exe basename → (impact, recommendation)
# impact: "high" | "medium" | "low"
# recommendation: "disable" | "delay" | "keep"
_KNOWN: dict[str, tuple[str, str]] = {
    "teams.exe":            ("high",   "disable"),
    "discord.exe":          ("medium", "delay"),
    "slack.exe":            ("high",   "disable"),
    "zoom.exe":             ("medium", "delay"),
    "spotify.exe":          ("medium", "delay"),
    "skype.exe":            ("medium", "delay"),
    "onedrive.exe":         ("medium", "delay"),
    "dropbox.exe":          ("medium", "delay"),
    "googledrivesync.exe":  ("medium", "delay"),
    "steam.exe":            ("high",   "disable"),
    "epicgameslauncher.exe":("high",   "disable"),
    "ea_desktop.exe":       ("high",   "disable"),
    "battle.net.exe":       ("high",   "disable"),
    "upc.exe":              ("medium", "disable"),
    "origin.exe":           ("high",   "disable"),
    "adobeupdatedaemon.exe":("medium", "disable"),
    "acrobat.exe":          ("medium", "delay"),
    "ccleaner64.exe":       ("low",    "keep"),
    "malwarebytes.exe":     ("low",    "keep"),
    "curve.exe":            ("medium", "delay"),
    "corsairhid.exe":       ("low",    "keep"),
    "razercentralservice.exe": ("low", "keep"),
    "lghub.exe":            ("low",    "keep"),
    "msiafterburner.exe":   ("low",    "keep"),
    "hwinfo64.exe":         ("low",    "keep"),
}

_IMPACT_COLOR = {
    "high":   RED,
    "medium": AMBER,
    "low":    EMERALD,
}
_IMPACT_LABEL = {
    "high":   "HIGH",
    "medium": "MED",
    "low":    "LOW",
}

_REG_PATHS = [
    (winreg.HKEY_CURRENT_USER if _HAS_WINREG else None,
     r"Software\Microsoft\Windows\CurrentVersion\Run",
     "HKCU"),
    (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
     r"Software\Microsoft\Windows\CurrentVersion\Run",
     "HKLM"),
    (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
     "HKLM32"),
] if _HAS_WINREG else []


# ─── Registry helpers ─────────────────────────────────────────────────────────

def _read_startup_entries() -> list[dict]:
    """Return list of startup entries with metadata."""
    if not _HAS_WINREG:
        return []
    entries = []
    seen_names = set()
    for hive, path, hive_label in _REG_PATHS:
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
        except OSError:
            continue
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                i += 1
            except OSError:
                break
            exe = os.path.basename(value.strip('"').split()[0]).lower() if value else ""
            key_id = f"{hive_label}:{name.lower()}"
            if key_id in seen_names:
                continue
            seen_names.add(key_id)
            impact, rec = _KNOWN.get(exe, ("low", "keep"))
            entries.append({
                "id":         key_id,
                "name":       name,
                "value":      value,
                "exe":        exe,
                "hive":       hive_label,
                "hive_const": hive,
                "reg_path":   path,
                "impact":     impact,
                "rec":        rec,
            })
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
    """Remove a Run key value. Returns True on success."""
    if not _HAS_WINREG:
        return False
    try:
        key = winreg.OpenKey(hive_const, path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


# ─── UI helpers ───────────────────────────────────────────────────────────────

def _scrollable(parent, bg=BG) -> tuple[tk.Frame, tk.Canvas]:
    """Return (inner_frame, canvas). Mousewheel bound."""
    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill="both", expand=True)

    cv = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    sb = tk.Scrollbar(outer, orient="vertical", command=cv.yview,
                      bg=bg, troughcolor=bg, activebackground=BORDER,
                      highlightthickness=0, bd=0, width=6)
    inner = tk.Frame(cv, bg=bg)
    win_id = cv.create_window((0, 0), window=inner, anchor="nw")

    def _on_resize(e):
        cv.itemconfig(win_id, width=e.width)
    cv.bind("<Configure>", _on_resize)

    def _on_frame_size(e):
        cv.configure(scrollregion=cv.bbox("all"))
    inner.bind("<Configure>", _on_frame_size)

    def _on_wheel(e):
        cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
    cv.bind_all("<MouseWheel>", _on_wheel)

    sb.pack(side="right", fill="y")
    cv.pack(side="left", fill="both", expand=True)
    cv.configure(yscrollcommand=sb.set)

    return inner, cv


def _section_header(parent, title: str, count: int = 0, color=BLUE):
    row = tk.Frame(parent, bg=PANEL2)
    row.pack(fill="x", padx=10, pady=(10, 2))

    tk.Label(row, text=title, font=(_F, 9, "bold"),
             bg=PANEL2, fg=TEXT).pack(side="left", padx=(8, 4), pady=5)
    if count:
        badge = tk.Label(row, text=str(count),
                         font=(_F, 7, "bold"),
                         bg=color, fg="#ffffff",
                         padx=5, pady=1)
        badge.pack(side="left")
    tk.Frame(row, bg=BORDER, height=1).pack(side="bottom", fill="x")


def _impact_badge(parent, impact: str) -> tk.Label:
    c = _IMPACT_COLOR.get(impact, MUTED)
    lbl = tk.Label(parent, text=_IMPACT_LABEL.get(impact, "?"),
                   font=(_F, 6, "bold"),
                   bg=c, fg="#000000" if impact == "medium" else "#ffffff",
                   padx=4, pady=1)
    return lbl


def _entry_card(parent, entry: dict, prefs: dict,
                on_disable_cb, on_delay_cb, on_keep_cb):
    """Build one startup entry card."""
    eid    = entry["id"]
    impact = entry["impact"]
    rec    = entry["rec"]
    status = prefs.get(eid, {}).get("status", "active")   # active | disabled | delayed

    card = tk.Frame(parent, bg=PANEL, bd=0,
                    highlightthickness=1,
                    highlightbackground=BORDER)
    card.pack(fill="x", padx=10, pady=2)

    inner = tk.Frame(card, bg=PANEL)
    inner.pack(fill="x", padx=8, pady=5)

    # ── Left: impact badge ──
    left = tk.Frame(inner, bg=PANEL, width=34)
    left.pack(side="left", fill="y")
    left.pack_propagate(False)
    _impact_badge(left, impact).pack(pady=4)

    # ── Centre: name + exe ──
    mid = tk.Frame(inner, bg=PANEL)
    mid.pack(side="left", fill="both", expand=True, padx=6)

    name_txt = entry["name"] if len(entry["name"]) <= 32 else entry["name"][:30] + "…"
    tk.Label(mid, text=name_txt, font=(_F, 9, "bold"),
             bg=PANEL, fg=TEXT, anchor="w").pack(anchor="w")

    exe_txt = entry["exe"] or "unknown"
    hive_txt = f"  [{entry['hive']}]"
    tk.Label(mid, text=exe_txt + hive_txt, font=(_F, 7),
             bg=PANEL, fg=MUTED, anchor="w").pack(anchor="w")

    # Recommendation hint
    _rec_map = {
        "disable": ("● Can be disabled safely", RED),
        "delay":   ("○ Consider delaying", AMBER),
        "keep":    ("✓ Recommended to keep", EMERALD),
    }
    hint_txt, hint_color = _rec_map.get(rec, ("", MUTED))
    tk.Label(mid, text=hint_txt, font=(_F, 7),
             bg=PANEL, fg=hint_color, anchor="w").pack(anchor="w")

    # ── Right: buttons / status ──
    right = tk.Frame(inner, bg=PANEL)
    right.pack(side="right", fill="y", padx=(4, 0))

    if status == "disabled":
        tk.Label(right, text="DISABLED", font=(_F, 7, "bold"),
                 bg=PANEL, fg=MUTED).pack(pady=6)
        restore_btn = tk.Label(right, text="Restore",
                               font=(_F, 7), bg=DIM, fg=BLUE,
                               padx=6, pady=2, cursor="hand2")
        restore_btn.pack()
        restore_btn.bind("<Button-1>", lambda e: on_keep_cb(entry, card))
    elif status == "delayed":
        tk.Label(right, text="DELAYED", font=(_F, 7, "bold"),
                 bg=PANEL, fg=AMBER).pack(pady=4)
        restore_btn = tk.Label(right, text="Restore",
                               font=(_F, 7), bg=DIM, fg=BLUE,
                               padx=6, pady=2, cursor="hand2")
        restore_btn.pack()
        restore_btn.bind("<Button-1>", lambda e: on_keep_cb(entry, card))
    else:
        # Active — show action buttons
        if rec in ("disable",):
            dis_btn = tk.Label(right, text="Disable",
                               font=(_F, 7, "bold"),
                               bg="#3b1a1a", fg=RED,
                               padx=7, pady=3, cursor="hand2")
            dis_btn.pack(pady=(0, 2))
            dis_btn.bind("<Button-1>", lambda e: on_disable_cb(entry, card))

        if rec in ("delay", "disable"):
            del_btn = tk.Label(right, text="Delay",
                               font=(_F, 7),
                               bg=DIM, fg=AMBER,
                               padx=7, pady=3, cursor="hand2")
            del_btn.pack(pady=(0, 2))
            del_btn.bind("<Button-1>", lambda e: on_delay_cb(entry, card))


# ─── Main page builder ────────────────────────────────────────────────────────

def build_startup_manager_page(host, parent: tk.Frame):
    """Entry point called from main_window_expanded."""
    prefs = _load_prefs()

    # ── Page wrapper ──
    page = tk.Frame(parent, bg=BG)
    page.pack(fill="both", expand=True)

    # ── Spinner shown while loading ──
    spinner = tk.Label(page, text="Scanning startup entries…",
                       font=(_F, 10), bg=BG, fg=MUTED)
    spinner.pack(pady=40)

    def _on_entries_ready(entries: list[dict]):
        spinner.destroy()
        _render(page, entries, prefs)

    def _scan():
        entries = _read_startup_entries()
        page.after(0, lambda: _on_entries_ready(entries))

    threading.Thread(target=_scan, daemon=True).start()


def _render(page: tk.Frame, entries: list[dict], prefs: dict):
    """Render two-panel layout once entries are loaded."""

    if not entries:
        tk.Label(page, text="No startup entries found — or winreg unavailable.",
                 font=(_F, 10), bg=BG, fg=MUTED).pack(pady=60)
        return

    # Split into panels
    optimize = [e for e in entries
                if e["impact"] in ("high", "medium") and e["rec"] in ("disable", "delay")
                and prefs.get(e["id"], {}).get("status", "active") == "active"]
    disable  = [e for e in entries
                if e["rec"] == "disable"
                and prefs.get(e["id"], {}).get("status", "active") == "active"]
    all_entries = entries   # shown at bottom always

    # ── Stat bar ──
    stat = tk.Frame(page, bg=NAVY, height=24)
    stat.pack(fill="x")
    stat.pack_propagate(False)
    tk.Label(stat, text=f"  {len(entries)} startup entries found",
             font=(_F, 7, "bold"), bg=NAVY, fg="#93c5fd").pack(side="left", padx=6)
    n_heavy = len([e for e in entries if e["impact"] == "high"])
    tk.Label(stat, text=f"  {n_heavy} HIGH impact",
             font=(_F, 7), bg=NAVY, fg=RED).pack(side="left", padx=4)

    # ── Main scroll area ──
    inner, _ = _scrollable(page)

    # ── Callbacks ──
    def _disable(entry, card):
        ans = messagebox.askyesno(
            "Disable Startup Entry",
            f"Remove '{entry['name']}' from startup?\n\n"
            "The program will no longer start automatically.\n"
            "You can restore it later from this page.",
            icon="warning"
        )
        if not ans:
            return
        ok = _delete_startup_entry(entry["hive_const"], entry["reg_path"], entry["name"])
        if ok:
            prefs.setdefault(entry["id"], {})["status"] = "disabled"
            _save_prefs(prefs)
            card.destroy()
        else:
            messagebox.showerror(
                "Failed",
                "Could not remove registry entry.\n"
                "Try running PC Workman as Administrator."
            )

    def _delay(entry, card):
        # Mark as "delayed" preference only — actual delay mechanism is a note
        prefs.setdefault(entry["id"], {})["status"] = "delayed"
        _save_prefs(prefs)
        card.destroy()
        _note = tk.Frame(inner, bg=DIM)
        _note.pack(fill="x", padx=10, pady=2)
        tk.Label(_note,
                 text=f"✓ '{entry['name']}' marked as delayed (manual action may be needed)",
                 font=(_F, 7), bg=DIM, fg=AMBER, padx=8, pady=4).pack(anchor="w")

    def _keep(entry, card):
        prefs.setdefault(entry["id"], {})["status"] = "active"
        _save_prefs(prefs)
        card.destroy()

    # ─── Panel A: Optimize at startup ────────────────────────────────────────
    _section_header(inner, "⚡ Optimize at startup",
                    count=len(optimize), color=AMBER)

    if optimize:
        for entry in optimize:
            _entry_card(inner, entry, prefs,
                        on_disable_cb=_disable,
                        on_delay_cb=_delay,
                        on_keep_cb=_keep)
    else:
        tk.Label(inner, text="  ✓ No heavy startup programs found.",
                 font=(_F, 8), bg=BG, fg=EMERALD, padx=14, pady=6).pack(anchor="w")

    # ─── Panel B: Disable from startup ───────────────────────────────────────
    _section_header(inner, "🗑 Safe to disable",
                    count=len(disable), color=RED)

    if disable:
        for entry in disable:
            _entry_card(inner, entry, prefs,
                        on_disable_cb=_disable,
                        on_delay_cb=_delay,
                        on_keep_cb=_keep)
    else:
        tk.Label(inner, text="  ✓ Nothing flagged as safe-to-disable.",
                 font=(_F, 8), bg=BG, fg=EMERALD, padx=14, pady=6).pack(anchor="w")

    # ─── Panel C: All entries (reference) ────────────────────────────────────
    _section_header(inner, "📋 All startup entries",
                    count=len(all_entries), color=BLUE)

    for entry in all_entries:
        _entry_card(inner, entry, prefs,
                    on_disable_cb=_disable,
                    on_delay_cb=_delay,
                    on_keep_cb=_keep)

    # ─── Footer note ──────────────────────────────────────────────────────────
    foot = tk.Frame(inner, bg=BG)
    foot.pack(fill="x", padx=10, pady=(14, 8))
    tk.Label(foot,
             text="ℹ  Changes take effect on next reboot.  "
                  "Restore disabled entries from 'All startup entries' above.",
             font=(_F, 7), bg=BG, fg=MUTED, wraplength=700, justify="left").pack(anchor="w")
