"""ui.components.hero_banner - the gradient header of a page (2026-11-20).

HCK_Labs and the Guide drew their gradient header inside labs_guide_pages.
The new pages (Gaming, Process Center, Optimization Center, Health Report,
Cleanup, Profile) use the same one:

    hero_banner(parent, title, subtitle,
                stops=["#f87171", "#60a5fa"],
                buttons=[(text, command, primary), ...])   # up to two, stacked

The colours fade into the page background towards the bottom, so the band
reads as light from the top-left rather than a flat block.
"""
from __future__ import annotations

import tkinter as tk

from utils.fonts import UI as _UI, HDR as _HDR, LIGHT as _LIGHT

BG = "#0a0e14"
BORDER = "#1f2937"
TEXT = "#f1f5f9"
DIM = "#cbd5e1"

# red to blue, the Gaming page (Marcin's note, 2026-11-20)
STOPS_GAMING = ["#f87171", "#c084fc", "#60a5fa"]


def mix(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


def paint_gradient(cv, width: int, height: int, stops, bg: str = BG,
                   strength: float = 0.56) -> None:
    """Horizontal gradient through `stops`, faded into `bg` downwards."""
    steps = 90
    rows = 24
    for i in range(steps):
        t = i / (steps - 1)
        seg = t * (len(stops) - 1)
        k = min(int(seg), len(stops) - 2)
        col = mix(stops[k], stops[k + 1], seg - k)
        x0 = int(width * i / steps)
        x1 = int(width * (i + 1) / steps) + 1
        for j in range(rows):
            f = strength * (1 - j / rows) ** 1.6 + 0.05
            y0 = int(height * j / rows)
            y1 = int(height * (j + 1) / rows) + 1
            cv.create_rectangle(x0, y0, x1, y1, outline="", fill=mix(bg, col, f))
    cv.create_line(0, height - 1, width, height - 1, fill=BORDER)


def _button(parent, text, cmd, primary):
    bg, fg, hov = (("#f8fafc", "#0b1020", "#e2e8f0") if primary
                   else ("#111827", TEXT, "#1f2937"))
    b = tk.Label(parent, text=text, font=(_HDR, 9, "bold"), bg=bg, fg=fg,
                 padx=16, pady=7, cursor="hand2", width=22)
    b.bind("<Button-1>", lambda e=None: cmd())
    b.bind("<Enter>", lambda e=None: b.config(bg=hov))
    b.bind("<Leave>", lambda e=None: b.config(bg=bg))
    return b


_CRUMB_TX = {
    "my_pc": {"pl": "MÓJ PC", "en": "MY PC"},
    "dashboard": {"pl": "DASHBOARD", "en": "DASHBOARD"},
}


def _lang() -> str:
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def nav_crumbs(win, here: str, siblings=()):
    """The navigation strip of a page banner (Marcin, 2026-11-20): My PC and
    Dashboard always one click away, then where you are, then the pages
    next to it. siblings: [(label, page_id)]. None in the list is a divider."""
    def go(page_id):
        def _go():
            try:
                if page_id == "my_pc":
                    win._handle_sidebar_navigation("my_pc")
                    win.sidebar.set_active_page("my_pc")
                else:
                    win.current_view = None
                    win._switch_to_page(page_id)
            except Exception:
                pass
        return _go
    lang = _lang()
    out = [(_CRUMB_TX["my_pc"][lang], go("my_pc"), False),
           (_CRUMB_TX["dashboard"][lang], go("dashboard"), False),
           None,
           (here, None, True)]
    out += [(lab, go(pid), False) for lab, pid in siblings]
    return out


def hero_banner(parent, title: str, subtitle: str = "", stops=None,
                buttons=(), height: int = 150, bg: str = BG, crumbs=()):
    """Pack a gradient banner into `parent` and return its Canvas.
    crumbs (from nav_crumbs) draws a clickable navigation strip along the
    top of the banner; the title moves down to make room."""
    stops = stops or STOPS_GAMING
    crumbs = list(crumbs)
    if crumbs:
        height += 16
    cv = tk.Canvas(parent, height=height, bg=bg, highlightthickness=0)
    cv.pack(fill="x")
    holder = tk.Frame(cv, bg=bg)
    made = [_button(holder, txt, cmd, prim) for txt, cmd, prim in list(buttons)[:2]]
    for i, b in enumerate(made):
        b.pack(fill="x", pady=(0 if i == 0 else 6, 0))
    # measured once, here: an update_idletasks() inside _draw ran a nested
    # <Configure> redraw, and the outer one then drew its narrow layout on
    # top (buttons over the title on the Process Center, 2026-11-20)
    holder.update_idletasks()
    bw = holder.winfo_reqwidth() if made else 0
    busy = {"on": False}

    def _draw(_e=None):
        if busy["on"]:
            return
        busy["on"] = True
        try:
            _paint()
        finally:
            busy["on"] = False

    def _paint():
        w = cv.winfo_width()
        if w < 50:
            return                      # not laid out yet; <Configure> follows
        cv.delete("all")
        paint_gradient(cv, w, height, stops, bg)
        right = 0
        if made:
            right = bw + 40
            cv.create_window(w - 28, height // 2 + (8 if crumbs else 0), window=holder,
                             anchor="e")
        dy = 0
        if crumbs:
            dy = 16
            x = 34
            for i, c in enumerate(crumbs):
                if c is None:
                    cv.create_text(x, 10, anchor="nw", text="│", font=(_UI, 8), fill=DIM)
                    x += 16
                    continue
                label, cmd, current = c
                if i and crumbs[i - 1] is not None:
                    cv.create_text(x, 10, anchor="nw", text="·", font=(_UI, 8), fill=DIM)
                    x += 14
                tag = f"crumb{i}"
                tid = cv.create_text(x, 10, anchor="nw", text=label, tags=(tag,),
                                     font=(_HDR, 8, "bold") if current else (_UI, 8, "bold"),
                                     fill=TEXT if current else DIM)
                x1 = (cv.bbox(tid) or (x, 0, x + 40, 0))[2]
                if current:
                    cv.create_line(x, 25, x1, 25, fill=TEXT, width=2)
                elif cmd is not None:
                    cv.tag_bind(tag, "<Button-1>", lambda e=None, f=cmd: f())
                    cv.tag_bind(tag, "<Enter>", lambda e=None, t=tid: (
                        cv.itemconfig(t, fill=TEXT), cv.config(cursor="hand2")))
                    cv.tag_bind(tag, "<Leave>", lambda e=None, t=tid: (
                        cv.itemconfig(t, fill=DIM), cv.config(cursor="")))
                x = x1 + 10
        cv.create_text(32, 30 + dy, anchor="nw", text=title, font=(_LIGHT, 24), fill=TEXT,
                       width=max(240, w - right - 64))
        if subtitle:
            cv.create_text(34, 76 + dy, anchor="nw", text=subtitle, font=(_UI, 10), fill=DIM,
                           width=max(240, w - right - 70))

    cv.bind("<Configure>", _draw)
    cv.after(30, _draw)
    return cv
