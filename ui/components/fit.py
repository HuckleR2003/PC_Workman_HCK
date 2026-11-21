# ui/components/fit.py
"""
Text that fits (2026-11-15).

Why buttons and labels were cut off all over the app ("FLUSH RA", "OPE",
"Disab", a sidebar item ending in "Learı"): Tk's pack() hands out space in
the order widgets are packed. A long text packed first takes everything it
asks for, and the button packed after it gets what is left, sometimes 13 px
for a 38 px word. Tk does not shrink the long text and does not warn.

Two rules, and one helper for the second:

  1. Pack what must stay whole FIRST (buttons, pills, toggles, arrows), then
     the text that may give way.
  2. Text that may give way wraps to the width it really has, instead of
     being cut mid-letter: wrap_to_width(label).

tests/test_text_fits.py builds the real window and fails when a button or a
label gets less room than its text needs.
"""
import tkinter as tk

# px: changes smaller than this never re-wrap a label or re-show a widget
_SLACK = 6


def fixed_width_natural_height(frame: tk.Frame, width: int) -> None:
    """Give *frame* a fixed width but the height its content needs.

    `Frame(width=96)` + `pack_propagate(False)` fixes the width and, as a
    side effect, makes the frame ask for NO height: it becomes as tall as its
    neighbours happen to be, and its last line of text is sliced through when
    they are shorter. Call this after the frame's children are packed. The
    height is measured from the content, so it is right at any font size and
    any Windows display scaling.
    """
    try:
        frame.pack_propagate(True)
        frame.update_idletasks()
        height = frame.winfo_reqheight()
        frame.pack_propagate(False)
        frame.configure(width=width, height=height)
    except tk.TclError:
        pass


def show_only_if_fits(optional: tk.Widget, container: tk.Misc, required,
                      margin: int = 12, **pack_kwargs) -> None:
    """Show *optional* only while *container* has room for it next to the
    *required* widgets; otherwise take it away whole.

    For text that is nice to have (a tagline, a caption, a technical key
    that is also in the tooltip). A decoration that is half visible reads as
    a bug; one that is absent reads as nothing. *pack_kwargs* is how the
    widget is packed when it is shown (default: side="left").
    """
    if not pack_kwargs:
        pack_kwargs = {"side": "left"}

    def _apply(event=None):
        try:
            room = event.width if event is not None else container.winfo_width()
            need = (sum(w.winfo_reqwidth() for w in required)
                    + optional.winfo_reqwidth() + margin)
            shown = bool(optional.winfo_manager())
            # Hysteresis: hide at the limit, show again only with room to
            # spare, so one pixel of difference cannot flip it back and forth.
            if need > room and shown:
                optional.pack_forget()
            elif need + _SLACK <= room and not shown:
                optional.pack(**pack_kwargs)
        except tk.TclError:
            pass                                    # widget is gone

    container.bind("<Configure>", _apply, add="+")


def wrap_to_width(label: tk.Label, container: tk.Misc = None,
                  pad: int = 0, min_width: int = 40) -> None:
    """Keep *label* wrapped to the width of *container* (default: its parent).

    The wrap length follows every resize, so the text is never clipped at the
    right edge: it flows onto another line when the window gets narrower and
    back onto one line when there is room again.
    """
    host = container if container is not None else label.master

    def _apply(event=None):
        try:
            width = (event.width if event is not None
                     else host.winfo_width()) - pad
            if width < min_width:
                return
            # Re-wrap only on a real change: re-wrapping alters the label's
            # requested size, which can resize the host by a pixel or two and
            # come straight back here.
            try:
                current = int(str(label.cget("wraplength")))
            except (ValueError, tk.TclError):
                current = 0
            if abs(current - width) >= _SLACK:
                label.configure(wraplength=width)
        except tk.TclError:
            pass                                    # widget is gone

    host.bind("<Configure>", _apply, add="+")
    try:
        label.configure(justify="left")
    except tk.TclError:
        pass
