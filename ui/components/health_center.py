"""ui.components.health_center - My PC → Health, the health centre
(2026-11-20).

A score 0-100 from core.health_score (the event log, drives, temperatures
in games, memory, the graphics driver, startup) as a ring, and one bar per
part with its reason. A click on a bar opens the place where that part is
looked after. Computed once, in a background thread (the event log and the
drives take a few seconds); bars grow when the result arrives.
"""
from __future__ import annotations

import threading
import tkinter as tk

from utils.fonts import UI as _BODY, HDR as _HDR

BG = "#0b0f16"
PANEL = "#0f141c"
PANEL2 = "#131a24"
LINE = "#1f2937"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
HOVER = "#1b2333"


def _col(s):
    return "#34d399" if s >= 80 else "#fbbf24" if s >= 55 else "#f87171"


_TX = {
    "title": {"pl": "Centrum zdrowia", "en": "Health centre"},
    "checking": {"pl": "Sprawdzam dziennik Windows, dyski i historię…",
                 "en": "Checking the Windows log, the drives and the history…"},
    "none": {"pl": "Za mało danych na wynik: wróć za godzinę.", "en": "Not enough data for a score yet: back in an hour."},
    "word": {"pl": "zdrowie", "en": "health"},
    "parts": {
        "stability": {"pl": "Stabilność", "en": "Stability"},
        "drives": {"pl": "Dyski", "en": "Drives"},
        "temps": {"pl": "Temperatury w grach", "en": "Temperatures in games"},
        "memory": {"pl": "Pamięć", "en": "Memory"},
        "drivers": {"pl": "Sterownik grafiki", "en": "Graphics driver"},
        "startup": {"pl": "Autostart", "en": "Startup"},
    },
    "why": {
        "hw_errors": {"pl": "błędy sprzętu albo niebieskie ekrany w 30 dni", "en": "hardware errors or blue screens in 30 days"},
        "disk_errors": {"pl": "błędy dysku w dzienniku Windows", "en": "disk errors in the Windows log"},
        "restarts": {"pl": "restarty bez czystego zamknięcia", "en": "restarts without a clean shutdown"},
        "no_errors": {"pl": "bez błędów i nagłych restartów w 30 dni", "en": "no errors or sudden restarts in 30 days"},
        "disk_health": {"pl": "dysk zgłasza zły stan: zrób kopię", "en": "a drive reports a bad state: back up"},
        "c_full": {"pl": "mało miejsca na C:", "en": "little room on C:"},
        "system_hdd": {"pl": "Windows na dysku talerzowym", "en": "Windows on a hard disk"},
        "drives_ok": {"pl": "stan dobry, miejsca wystarczy", "en": "healthy, enough room"},
        "gpu_temp": {"pl": "GPU w grach do {v:.0f}°C", "en": "GPU up to {v:.0f}°C in games"},
        "ram_small": {"pl": "RAM zwykle prawie pełny", "en": "RAM usually almost full"},
        "ram_ok": {"pl": "RAM wystarcza", "en": "RAM is enough"},
        "xmp_off": {"pl": "RAM bez XMP", "en": "RAM without XMP"},
        "no_pagefile": {"pl": "pamięć wirtualna wyłączona", "en": "virtual memory off"},
        "gpu_driver": {"pl": "ma {v} mies.", "en": "{v} months old"},
        "startup_heavy": {"pl": "{v} programów spowalnia start", "en": "{v} programs slow the boot"},
        "startup_ok": {"pl": "start bez zbędnych programów", "en": "no needless programs at boot"},
    },
}


def _lang():
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def part_text(p, lang):
    name = _TX["parts"][p["key"]][lang]
    why = _TX["why"].get(p["why"], {}).get(lang, "")
    if "{v" in why:
        why = why.format(v=p.get("value", 0))
    return name, why


class _Box:
    def __init__(self):
        self.data = None


def _work(box):
    try:
        from core.health_score import collect, score
        box.data = score(collect())
    except Exception:
        box.data = {"total": None, "parts": []}


def build_health_center(parent, win=None) -> tk.Frame:
    lang = _lang()
    root = tk.Frame(parent, bg=BG)
    root.pack(fill="x", padx=8, pady=(6, 4))
    head = tk.Frame(root, bg=BG)
    head.pack(fill="x")
    tk.Frame(head, bg="#34d399", width=3, height=18).pack(side="left", padx=(0, 8))
    tk.Label(head, text=_TX["title"][lang], font=(_HDR, 12, "bold"), bg=BG, fg=TEXT).pack(side="left")
    body = tk.Frame(root, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
    body.pack(fill="x", pady=(6, 0))
    ring = tk.Canvas(body, width=130, height=130, bg=PANEL, highlightthickness=0)
    ring.pack(side="left", padx=14, pady=10)
    bars = tk.Frame(body, bg=PANEL)
    bars.pack(side="left", fill="both", expand=True, padx=(0, 14), pady=10)
    tk.Label(bars, text=_TX["checking"][lang], font=(_BODY, 9), bg=PANEL, fg=MUTED).pack(anchor="w")
    _ring(ring, None, lang)

    box = _Box()
    threading.Thread(target=_work, args=(box,), daemon=True, name="health-center").start()

    def _poll():
        try:
            if not root.winfo_exists():
                return
        except Exception:
            return
        if box.data is None:
            root.after(150, _poll)
            return
        _ring(ring, box.data.get("total"), lang)
        _bars(bars, box.data.get("parts") or [], lang, win)
    _poll()
    return root


def _ring(cv, total, lang):
    cv.delete("all")
    cv.create_oval(12, 12, 118, 118, outline=PANEL2, width=10)
    if total is not None:
        c = _col(total)
        if total >= 100:
            cv.create_oval(12, 12, 118, 118, outline=c, width=10)
        elif total > 0:
            cv.create_arc(12, 12, 118, 118, start=90, extent=-3.6 * total, style="arc",
                          outline=c, width=10)
    cv.create_text(65, 58, text="--" if total is None else str(total), font=(_HDR, 24, "bold"), fill=TEXT)
    cv.create_text(65, 84, text=_TX["word"][lang], font=(_BODY, 8), fill=MUTED)


def _go(win, page):
    if win is None:
        return
    try:
        if page == "stability":
            from ui.components.yourpc_page import _open_stability_tests
            _open_stability_tests(win)
        elif page == "activity_hardware":
            win.open_activity_memory("hardware")
        elif page == "process_center":
            win.open_process_center()
        else:
            win.current_view = None
            win._switch_to_page(page)
    except Exception:
        pass


def _bars(frame, parts, lang, win):
    for w in frame.winfo_children():
        w.destroy()
    if not parts:
        tk.Label(frame, text=_TX["none"][lang], font=(_BODY, 9), bg=PANEL, fg=MUTED).pack(anchor="w")
        return
    for p in parts:
        name, why = part_text(p, lang)
        row = tk.Frame(frame, bg=PANEL, cursor="hand2")
        row.pack(fill="x", pady=2)
        top = tk.Frame(row, bg=PANEL)
        top.pack(fill="x")
        a = tk.Label(top, text=name, font=(_BODY, 9, "bold"), bg=PANEL, fg=TEXT, anchor="w")
        a.pack(side="left")
        b = tk.Label(top, text=why, font=(_BODY, 8), bg=PANEL, fg=MUTED, anchor="w")
        b.pack(side="left", padx=(8, 0))
        c = tk.Label(top, text=f"{p['score']}  ›", font=(_HDR, 9, "bold"), bg=PANEL, fg=_col(p["score"]))
        c.pack(side="right")
        track = tk.Frame(row, bg=PANEL2, height=6)
        track.pack(fill="x", pady=(2, 0))
        tk.Frame(track, bg=_col(p["score"]), height=6).place(relwidth=max(0.02, p["score"] / 100), relheight=1)
        widgets = [row, top, a, b, c]

        def _hover(on, ws=widgets):
            for w in ws:
                try:
                    w.config(bg=HOVER if on else PANEL)
                except Exception:
                    pass
        for w in widgets + [track]:
            w.bind("<Enter>", lambda e=None, h=_hover: h(True))
            w.bind("<Leave>", lambda e=None, h=_hover: h(False))
            w.bind("<Button-1>", lambda e=None, g=p["go"]: _go(win, g))
