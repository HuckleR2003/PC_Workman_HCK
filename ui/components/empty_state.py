# ui/components/empty_state.py
"""
One empty state for the whole app (2026-11-14).

When a page has nothing real to show, it says what is missing and what makes
it appear. It never fills the space with "--", "N/A" or invented numbers.
Born with the fan pages, which used to draw random RPM values; meant to be
reused wherever data depends on something the user may not have.

    from ui.components.empty_state import build_empty_state
    build_empty_state(parent, title="No fan speed sensor",
                      body="Windows does not report ...",
                      note="Until then this page stays empty.")
"""
from utils.fonts import UI as _FONT_UI, HDR as _FONT_HDR, HEAVY as _FONT_HEAVY, LIGHT as _FONT_LIGHT  # noqa: F401
import tkinter as tk

try:
    from utils.fonts import UI as _UIF
except ImportError:
    _UIF = _FONT_UI
_HDR = _FONT_HDR

_PANEL = "#111827"
_TITLE = "#e5e7eb"
_BODY_FG = "#9ca3af"
_NOTE_FG = "#6b7280"


def build_empty_state(parent, title: str, body: str = "", note: str = "",
                      accent: str = "#f59e0b", bg: str = "#0a0e14",
                      wrap: int = 560) -> tk.Frame:
    """A centred panel: accent bar, title, explanation, quiet footnote.
    Returns the outer frame; `frame.extra` is a frame under the text where
    the caller may add its own rows (for example what IS measured)."""
    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill="both", expand=True, padx=20, pady=16)

    panel = tk.Frame(outer, bg=_PANEL)
    panel.pack(fill="x", anchor="n")
    tk.Frame(panel, bg=accent, width=3).pack(side="left", fill="y")

    inner = tk.Frame(panel, bg=_PANEL)
    inner.pack(side="left", fill="both", expand=True, padx=18, pady=16)

    tk.Label(inner, text=title, font=(_HDR, 13), bg=_PANEL, fg=_TITLE,
             anchor="w").pack(fill="x")
    labels = []
    if body:
        lb = tk.Label(inner, text=body, font=(_UIF, 10), bg=_PANEL,
                      fg=_BODY_FG, anchor="w", justify="left", wraplength=wrap)
        lb.pack(fill="x", pady=(6, 0))
        labels.append(lb)
    if note:
        ln = tk.Label(inner, text=note, font=(_UIF, 9), bg=_PANEL,
                      fg=_NOTE_FG, anchor="w", justify="left", wraplength=wrap)
        ln.pack(fill="x", pady=(8, 0))
        labels.append(ln)

    extra = tk.Frame(inner, bg=_PANEL)
    extra.pack(fill="x", pady=(12, 0))
    outer.extra = extra
    outer.panel_bg = _PANEL

    # Text follows the panel width, so nothing is cut off in a narrow window
    # and nothing is squeezed into a column in a wide one.
    def _rewrap(event):
        w = max(event.width - 12, 200)
        for lab in labels:
            try:
                lab.configure(wraplength=w)
            except Exception:
                pass
    inner.bind("<Configure>", _rewrap, add="+")
    return outer
