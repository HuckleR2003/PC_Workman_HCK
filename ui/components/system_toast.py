# ui/components/system_toast.py
"""
SystemToast - modern slide-in notification toasts.

Public API
----------
show_startup_toast(root, name, exe, hive, on_manage, lang='en')
    -> Called when a new Windows autostart entry is detected.

show_app_install_toast(root, display_name, exe_path, lang='en')
    -> Called when a newly installed application is detected.

Both functions are safe to call from the main tkinter thread.
Toasts stack automatically (each new one appears above the previous).
They slide in from the bottom-right, show a countdown progress bar,
and auto-dismiss after AUTO_DISMISS_S seconds.
"""
from __future__ import annotations

import os
import tkinter as tk
from typing import Callable, Optional

# PIL for extracting exe icon (optional)
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# Centralized i18n - falls back gracefully if module missing
try:
    from utils.i18n import t as _t_i18n
    def _t(key: str, **kwargs) -> str:
        return _t_i18n(f"toast.{key}", **kwargs)
except ImportError:
    # Fallback strings (English only) when i18n module is unavailable
    _FALLBACK: dict[str, str] = {
        "startup_title":   "New Startup Entry Detected",
        "startup_body":    "A program was added to Windows autostart.",
        "startup_hive":    "Registry: {hive} Run",
        "startup_manage":  "Open Startup Manager",
        "startup_dismiss": "Dismiss",
        "app_title":       "New Application Installed",
        "app_body":        "A new program was added to your system.",
        "app_ok":          "OK",
    }
    def _t(key: str, **kwargs) -> str:
        s = _FALLBACK.get(key, key)
        return s.format(**kwargs) if kwargs else s

# ── Font system ───────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# ── Global layout ─────────────────────────────────────────────────────────────

TOAST_W        = 360
AUTO_DISMISS_S = 9       # seconds before auto-close
_STACK_PAD     = 12      # vertical gap between stacked toasts
_EDGE_PAD      = 18      # distance from screen edge

# Active toasts list for stacking
_active_toasts: list["_Toast"] = []

# ── Palette ───────────────────────────────────────────────────────────────────

_BG        = "#0b0f16"
_BORDER    = "#1c2534"
_TEXT      = "#e2e8f0"
_MUTED     = "#64748b"
_BODY      = "#94a3b8"

# Startup toast - bordeaux/red
_ST_ACCENT = "#be123c"
_ST_ICON   = "#3b0014"
_ST_GLOW   = "#500724"

# App-install toast - green/teal
_AI_ACCENT = "#10b981"
_AI_ICON   = "#052e16"
_AI_GLOW   = "#065f46"



# ── Icon helpers ──────────────────────────────────────────────────────────────

def _letter_icon(letter: str, bg: str, fg: str, size: int = 40) -> Optional[object]:
    """Create a square PIL image with a centered letter - fallback app icon."""
    if not _HAS_PIL:
        return None
    try:
        img  = Image.new("RGBA", (size, size), bg)
        draw = ImageDraw.Draw(img)
        # Try a bold font; fall back to default
        try:
            fnt = ImageFont.truetype("segoeuib.ttf", size // 2)
        except Exception:
            fnt = ImageFont.load_default()
        text = (letter or "?")[0].upper()
        bbox = draw.textbbox((0, 0), text, font=fnt)
        tw   = bbox[2] - bbox[0]
        th   = bbox[3] - bbox[1]
        draw.text(((size - tw) // 2, (size - th) // 2 - 2), text, fill=fg, font=fnt)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def _exe_icon(exe_path: str, size: int = 40) -> Optional[object]:
    """Extract the first icon from an exe and return a PIL PhotoImage, or None."""
    if not _HAS_PIL or not exe_path or not os.path.isfile(exe_path):
        return None
    try:
        # Try win32ui / win32gui (pywin32)
        import win32ui, win32gui, win32con
        large, small = win32gui.ExtractIconEx(exe_path, 0)
        if not large:
            if small:
                win32gui.DestroyIcon(small[0])
            return None
        icon_handle = large[0]
        hdc    = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hdc_bmp= win32ui.CreateDCFromHandle(hdc.GetHandleOutput())
        hdc_bmp= hdc.CreateCompatibleDC()
        bmp    = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(hdc, size, size)
        hdc_bmp.SelectObject(bmp)
        hdc_bmp.FillSolidRect((0, 0, size, size), 0x000000)
        win32gui.DrawIconEx(hdc_bmp.GetHandleOutput(), 0, 0, icon_handle, size, size, 0, None, 0x0003)
        bmp_info = bmp.GetInfo()
        bmp_str  = bmp.GetBitmapBits(True)
        img = Image.frombuffer("RGBA", (bmp_info["bmWidth"], bmp_info["bmHeight"]),
                               bmp_str, "raw", "BGRA", 0, 1)
        img = img.resize((size, size), Image.LANCZOS)
        for h in (list(large) + list(small)):
            try:
                win32gui.DestroyIcon(h)
            except Exception:
                pass
        hdc_bmp.DeleteDC()
        hdc.DeleteDC()
        win32gui.ReleaseDC(0, win32gui.GetDC(0))
        win32ui.DeleteObject(bmp.GetHandle())
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


# ── Base Toast class ──────────────────────────────────────────────────────────

class _Toast:
    """
    Internal Toplevel-based toast.
    Do not instantiate directly - use show_startup_toast / show_app_install_toast.
    """

    _SLIDE_FRAMES = 14
    _SLIDE_DELAY  = 16   # ms

    def __init__(
        self,
        root:       tk.Misc,
        accent:     str,
        icon_frame_bg: str,
        icon_widget_fn: Callable[[tk.Widget], None],  # fn(parent) -> places icon widget
        title:      str,
        body:       str,
        sub:        str,
        btn_primary_text: str,
        btn_primary_cb:   Callable,
        btn_dismiss_text: str,
    ) -> None:
        self._root       = root
        self._accent     = accent
        self._dismissed  = False
        self._after_ids: list = []

        # ── Create Toplevel ───────────────────────────────────────────────────
        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.wm_attributes("-topmost", True)
        self._win.configure(bg=_BORDER)
        self._win.withdraw()   # hidden until positioned

        # ── Build content ─────────────────────────────────────────────────────
        self._build(icon_frame_bg, icon_widget_fn, title, body, sub,
                    btn_primary_text, btn_primary_cb, btn_dismiss_text)

        # ── Size & position ───────────────────────────────────────────────────
        self._win.update_idletasks()
        self._h = self._win.winfo_reqheight()
        self._sw = root.winfo_screenwidth()
        self._sh = root.winfo_screenheight()
        self._tx = self._sw - TOAST_W - _EDGE_PAD
        self._ty_target = self._sh - _EDGE_PAD - self._h - self._stack_offset()
        self._ty_start  = self._sh + 10   # off-screen start

        self._win.geometry(f"{TOAST_W}x{self._h}+{self._tx}+{self._ty_start}")
        self._win.deiconify()

        # Register in global stack
        _active_toasts.append(self)

        # Slide in
        self._slide_in(0)

        # Auto-dismiss countdown
        self._progress_step()

    # ── Stack offset ──────────────────────────────────────────────────────────

    def _stack_offset(self) -> int:
        """How many px above the bottom edge (accounting for other toasts)."""
        offset = 0
        for t in _active_toasts:
            if t is self:
                continue
            try:
                offset += t._h + _STACK_PAD
            except AttributeError:
                pass
        return offset

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(
        self,
        icon_bg:         str,
        icon_fn:         Callable,
        title:           str,
        body:            str,
        sub:             str,
        btn_primary_txt: str,
        btn_primary_cb:  Callable,
        btn_dismiss_txt: str,
    ) -> None:
        win = self._win

        # Outer 1-px border via bg colour of Toplevel
        inner = tk.Frame(win, bg=_BG)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Accent top bar
        tk.Frame(inner, bg=self._accent, height=3).pack(fill="x")

        # Main body row
        body_row = tk.Frame(inner, bg=_BG)
        body_row.pack(fill="x", padx=14, pady=(10, 6))

        # ── Icon cell ─────────────────────────────────────────────────────────
        icon_cell = tk.Frame(body_row, bg=icon_bg, width=46, height=46)
        icon_cell.pack(side="left", anchor="n")
        icon_cell.pack_propagate(False)
        icon_fn(icon_cell)

        # ── Text block ────────────────────────────────────────────────────────
        txt = tk.Frame(body_row, bg=_BG)
        txt.pack(side="left", fill="both", expand=True, padx=(12, 0))

        tk.Label(
            txt, text=title,
            font=(_BODY, 10, "bold"),
            bg=_BG, fg=_TEXT, anchor="w",
            wraplength=TOAST_W - 90,
        ).pack(anchor="w")

        tk.Label(
            txt, text=body,
            font=(_BODY, 8),
            bg=_BG, fg=_BODY, anchor="w",
            wraplength=TOAST_W - 90,
        ).pack(anchor="w", pady=(2, 0))

        if sub:
            tk.Label(
                txt, text=sub,
                font=(_BODY, 7),
                bg=_BG, fg=_MUTED, anchor="w",
                wraplength=TOAST_W - 90,
            ).pack(anchor="w", pady=(1, 0))

        # ── Divider ───────────────────────────────────────────────────────────
        tk.Frame(inner, bg=_BORDER, height=1).pack(fill="x", padx=14)

        # ── Button row ────────────────────────────────────────────────────────
        btn_row = tk.Frame(inner, bg=_BG)
        btn_row.pack(fill="x", padx=14, pady=(7, 10))

        # Primary button
        pri = tk.Label(
            btn_row, text=btn_primary_txt,
            font=(_BODY, 8, "bold"),
            bg=self._accent, fg="#ffffff",
            padx=14, pady=5, cursor="hand2",
        )
        pri.pack(side="left")
        pri.bind("<Button-1>", lambda _: (btn_primary_cb(), self.dismiss()))
        pri.bind("<Enter>",    lambda _: pri.config(bg=self._darken(self._accent)))
        pri.bind("<Leave>",    lambda _: pri.config(bg=self._accent))

        # Dismiss button
        dis = tk.Label(
            btn_row, text=btn_dismiss_txt,
            font=(_BODY, 8),
            bg="#1c2534", fg=_MUTED,
            padx=14, pady=5, cursor="hand2",
        )
        dis.pack(side="left", padx=(8, 0))
        dis.bind("<Button-1>", lambda _: self.dismiss())
        dis.bind("<Enter>",    lambda _: dis.config(fg=_TEXT, bg="#273040"))
        dis.bind("<Leave>",    lambda _: dis.config(fg=_MUTED, bg="#1c2534"))

        # Progress bar container (bottom, fills over AUTO_DISMISS_S)
        prog_outer = tk.Frame(inner, bg=_BORDER, height=3)
        prog_outer.pack(fill="x")
        prog_outer.pack_propagate(False)
        self._prog_bar = tk.Frame(prog_outer, bg=self._accent, height=3)
        self._prog_bar.place(x=0, y=0, relwidth=1.0, height=3)

        self._prog_start = None   # set on first step
        self._prog_outer = prog_outer

    # ── Progress countdown ────────────────────────────────────────────────────

    def _progress_step(self, step: int = 0) -> None:
        import time
        total_steps = AUTO_DISMISS_S * 20   # 20 fps
        if self._dismissed:
            return
        if step == 0:
            self._prog_start = time.time()
        elapsed  = time.time() - (self._prog_start or 0)
        fraction = max(0.0, 1.0 - elapsed / AUTO_DISMISS_S)
        try:
            self._prog_bar.place_configure(relwidth=fraction)
        except Exception:
            return
        if fraction > 0:
            aid = self._root.after(50, lambda: self._progress_step(step + 1))
            self._after_ids.append(aid)
        else:
            self.dismiss()

    # ── Slide animation ───────────────────────────────────────────────────────

    def _ease_out(self, t: float) -> float:
        return 1.0 - (1.0 - t) ** 3

    def _slide_in(self, step: int) -> None:
        if self._dismissed:
            return
        t     = self._ease_out(step / self._SLIDE_FRAMES)
        cur_y = int(self._ty_start + (self._ty_target - self._ty_start) * t)
        try:
            self._win.geometry(f"{TOAST_W}x{self._h}+{self._tx}+{cur_y}")
        except Exception:
            return
        if step < self._SLIDE_FRAMES:
            aid = self._root.after(
                self._SLIDE_DELAY,
                lambda: self._slide_in(step + 1),
            )
            self._after_ids.append(aid)

    def _slide_out(self, step: int, on_done: Callable) -> None:
        t     = step / self._SLIDE_FRAMES
        cur_y = int(self._ty_target + (self._sh + 20 - self._ty_target) * t)
        try:
            self._win.geometry(f"{TOAST_W}x{self._h}+{self._tx}+{cur_y}")
        except Exception:
            on_done()
            return
        if step < self._SLIDE_FRAMES:
            self._root.after(
                self._SLIDE_DELAY,
                lambda: self._slide_out(step + 1, on_done),
            )
        else:
            on_done()

    # ── Dismiss ───────────────────────────────────────────────────────────────

    def dismiss(self) -> None:
        if self._dismissed:
            return
        self._dismissed = True
        # Cancel pending afters
        for aid in self._after_ids:
            try:
                self._root.after_cancel(aid)
            except Exception:
                pass
        self._after_ids.clear()

        def _destroy():
            try:
                if self in _active_toasts:
                    _active_toasts.remove(self)
                self._win.destroy()
                _restack()
            except Exception:
                pass

        self._slide_out(0, _destroy)

    # ── Util ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _darken(hex_col: str) -> str:
        """Return a slightly darkened version of a hex colour."""
        try:
            r = int(hex_col[1:3], 16)
            g = int(hex_col[3:5], 16)
            b = int(hex_col[5:7], 16)
            r = max(0, r - 30)
            g = max(0, g - 30)
            b = max(0, b - 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_col


# ── Stack re-positioning ──────────────────────────────────────────────────────

def _restack() -> None:
    """Smoothly reposition all surviving toasts after one is dismissed."""
    sh = None
    offset = 0
    for t in list(_active_toasts):
        try:
            if sh is None:
                sh = t._sh
            ty = sh - _EDGE_PAD - t._h - offset
            t._ty_target = ty
            t._win.geometry(f"{TOAST_W}x{t._h}+{t._tx}+{ty}")
            offset += t._h + _STACK_PAD
        except Exception:
            pass


# ── Public API ────────────────────────────────────────────────────────────────

def show_startup_toast(
    root:       tk.Misc,
    name:       str,
    exe:        str,
    hive:       str,
    on_manage:  Callable,
    lang:       str = "en",   # kept for API compatibility; active i18n lang is used
) -> None:
    """
    Show a bordeaux notification about a new Windows autostart entry.

    Parameters
    ----------
    root       : tk.Tk / any tkinter widget (for scheduling)
    name       : Registry value name (display name)
    exe        : Exe filename (e.g. "steam.exe")
    hive       : Hive label ("HKCU" / "HKLM")
    on_manage  : Callable to open the Startup Manager page
    lang       : deprecated - use utils.i18n.set_lang() instead
    """
    title = _t("startup_title")
    body  = _t("startup_body")
    sub   = f"{_t('startup_hive', hive=hive)}  ·  {name}"
    if exe:
        sub += f"  ({exe})"

    def _place_icon(parent: tk.Widget) -> None:
        # Startup icon - red flash symbol
        lbl = tk.Label(
            parent, text="⚡",
            font=("Segoe UI Emoji", 18),
            bg=_ST_ICON, fg="#f43f5e",
        )
        lbl.place(relx=0.5, rely=0.5, anchor="center")

    _Toast(
        root            = root,
        accent          = _ST_ACCENT,
        icon_frame_bg   = _ST_ICON,
        icon_widget_fn  = _place_icon,
        title           = title,
        body            = body,
        sub             = sub,
        btn_primary_text= _t("startup_manage"),
        btn_primary_cb  = on_manage,
        btn_dismiss_text= _t("startup_dismiss"),
    )


def show_app_install_toast(
    root:         tk.Misc,
    display_name: str,
    exe_path:     str,
    lang:         str = "en",   # kept for API compatibility; active i18n lang is used
) -> None:
    """
    Show a green notification about a newly installed application.

    Parameters
    ----------
    root         : tk.Tk / any tkinter widget
    display_name : Application display name (from registry)
    exe_path     : Path to the app's exe (used for icon extraction)
    lang         : deprecated - use utils.i18n.set_lang() instead
    """
    title = _t("app_title")
    body  = _t("app_body")
    sub   = display_name

    # Try to extract icon; generate letter avatar as fallback
    letter  = (display_name or "?")[0].upper()
    icon_ph = None
    if exe_path:
        icon_ph = _exe_icon(exe_path, size=38)
    if icon_ph is None:
        icon_ph = _letter_icon(letter, _AI_ICON, _AI_ACCENT, size=38)

    # Keep a reference to avoid GC
    _icon_refs: list = []
    if icon_ph:
        _icon_refs.append(icon_ph)

    def _place_icon(parent: tk.Widget) -> None:
        if icon_ph:
            lbl = tk.Label(parent, image=icon_ph, bg=_AI_ICON)
            lbl.image = icon_ph   # keep ref on widget too
            lbl.place(relx=0.5, rely=0.5, anchor="center")
        else:
            # Plain letter fallback (no PIL)
            lbl = tk.Label(
                parent, text=letter,
                font=(_BODY, 18, "bold"),
                bg=_AI_ICON, fg=_AI_ACCENT,
            )
            lbl.place(relx=0.5, rely=0.5, anchor="center")

    _Toast(
        root            = root,
        accent          = _AI_ACCENT,
        icon_frame_bg   = _AI_ICON,
        icon_widget_fn  = _place_icon,
        title           = title,
        body            = body,
        sub             = sub,
        btn_primary_text= _t("app_ok"),
        btn_primary_cb  = lambda: None,
        btn_dismiss_text= _t("startup_dismiss"),
    )
