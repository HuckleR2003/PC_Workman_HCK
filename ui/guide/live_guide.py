# ui/guide/live_guide.py
"""
Live Guide - compact spotlight tour (5 steps).

Key design decisions:
  • Overlay alpha = 0.97  -> only 3 % of the app bleeds through
  • Info card is a SEPARATE tk.Toplevel (100 % opaque background, no bleed)
  • Card uses absolute screen coords (self._ox + cx, self._oy + cy)
  • Step 5 extends overlay to full root window -> spotlights the sidebar
  • Steps 1-3, 5 use bordeaux-red style; step 4 (hck_GPT) stays violet

Steps:
  1. chart        - real-time chart + filter bar
  2. nav          - dual navigation panels
  3. hw           - hardware status cards
  4. hckgpt       - hck_GPT AI banner (collapsed strip only)
  5. sidebar      - entire left sidebar (full-root overlay)
                    + secondary tooltip beside the Settings item
"""
from __future__ import annotations
import tkinter as tk
from typing import Optional, Tuple


# ── Font system ───────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# ── Palette ────────────────────────────────────────────────────────────────────

_DIM_BG   = "#030610"   # near-black dim
_SPOT_COL = "#ffffff"   # Windows -transparentcolor key
_CARD_BG  = "#0a0f1a"   # card solid background
_DIVIDER  = "#1e293b"
_TEXT     = "#e2e8f0"
_MUTED    = "#475569"
_BODY_TXT = "#94a3b8"

# Glow layers - bordeaux red (steps 1-3, 5)
_GLOW_RED_A = "#150003"
_GLOW_RED_B = "#2d0008"
_GLOW_RED_C = "#5b0012"

# Glow layers - violet/purple (step 4 - hck_GPT)
_GLOW_VIO_A = "#0e0520"
_GLOW_VIO_B = "#1c0b3d"
_GLOW_VIO_C = "#361270"

_BNR_BG   = "#170900"
_BNR_LINE = "#92400e"
_BNR_AMB  = "#f59e0b"
_BNR_GOLD = "#fbbf24"
_BNR_TXT  = "#fef3c7"

# Secondary tooltip (Settings item beside sidebar)
_TIP_BG   = "#0e0006"
_TIP_BORD = "#3b0014"
_TIP_BAR  = "#f43f5e"


# ── Per-accent glow layers ────────────────────────────────────────────────────

def _glow_layers(accent: str):
    """Return glow rectangle layers (pad, colour) for the given accent."""
    if accent == "#8b5cf6":
        return (
            (18, _GLOW_VIO_A),
            (11, _GLOW_VIO_B),
            (5,  _GLOW_VIO_C),
            (2,  accent),
        )
    return (
        (18, _GLOW_RED_A),
        (11, _GLOW_RED_B),
        (5,  _GLOW_RED_C),
        (2,  accent),
    )


# ── Step definitions ───────────────────────────────────────────────────────────

_STEPS = [
    {
        "step":       1,
        "accent":     "#be123c",
        "title":      "Real-Time Chart",
        "body":       "CPU · GPU · RAM live. Range: LIVE · 1H · 4H · 1D.",
        "target_key": "chart",
    },
    {
        "step":       2,
        "accent":     "#be123c",
        "title":      "Navigation - Two Panels",
        "body":       "Left: system sections.  Right: advanced tools.",
        "target_key": "nav",
    },
    {
        "step":       3,
        "accent":     "#be123c",
        "title":      "Live PC Status",
        "body":       "CPU / RAM / GPU with temperature and status. Session averages below.",
        "target_key": "hw",
    },
    {
        "step":       4,
        "accent":     "#8b5cf6",          # violet - hck_GPT identity colour
        "title":      "hck_GPT - AI Assistant",
        "body":       "Ask about PC status, processes or optimization. Always at hand.",
        "target_key": "hckgpt",
    },
    {
        "step":       5,
        "accent":     "#be123c",
        "title":      "Sidebar - Navigation",
        "body":       "Sections, settings and modes. Click ⚙ Settings to personalize.",
        "target_key": "sidebar",
    },
]

_HOVER = {
    "#be123c": "#9f1239",
    "#8b5cf6": "#7c3aed",
    "#10b981": "#059669",
}

CARD_W = 355
CARD_H = 148   # positioning estimate only; Toplevel auto-sizes to content


# ── Easing ─────────────────────────────────────────────────────────────────────

def _ease_out(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def _ease_in_out(t: float) -> float:
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


# ── LiveGuide ──────────────────────────────────────────────────────────────────

class LiveGuide:
    """Compact spotlight tour for the PC_Workman dashboard."""

    SPOT_PAD = 14

    def __init__(self, app) -> None:
        self._app     = app
        self._root    = app.root
        self._step    = 0
        self._running = False
        self._finale  = False

        self._overlay:  Optional[tk.Toplevel] = None
        self._canvas:   Optional[tk.Canvas]   = None
        self._card:     Optional[tk.Toplevel]  = None   # separate Toplevel -> solid bg
        self._tooltip:  Optional[tk.Toplevel]  = None
        self._banner:   Optional[tk.Toplevel]  = None

        # Overlay origin in screen coordinates (set by _reposition)
        self._ox: int = 0
        self._oy: int = 0
        self._ow: int = 0
        self._oh: int = 0

    # ── public ────────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running or self._finale:
            return
        self._running = True
        self._step    = 0
        self._create_overlay()
        self._animate_overlay_in()

    def close(self) -> None:
        self._running = False
        self._finale  = False
        self._destroy_card()
        self._destroy_tooltip()
        for w in (self._overlay, self._banner):
            if w:
                try:
                    w.destroy()
                except Exception:
                    pass
        self._overlay = None
        self._canvas  = None
        self._banner  = None

    # ── overlay ───────────────────────────────────────────────────────────────

    def _create_overlay(self) -> None:
        ov = tk.Toplevel(self._root)
        ov.overrideredirect(True)
        ov.wm_attributes("-topmost",          True)
        ov.wm_attributes("-alpha",            0.0)
        ov.wm_attributes("-transparentcolor", _SPOT_COL)
        ov.configure(bg=_DIM_BG)
        self._overlay = ov
        self._reposition()

        cv = tk.Canvas(ov, bg=_DIM_BG, highlightthickness=0)
        cv.place(x=0, y=0, relwidth=1, relheight=1)
        self._canvas = cv

        ov.bind("<Escape>",   lambda _e: self.close())
        cv.bind("<Button-1>", self._on_bg_click)

    def _reposition(self, use_root: bool = False) -> None:
        """Position overlay over content_area (default) or the full root window."""
        self._root.update_idletasks()
        if use_root:
            w = self._root.winfo_width()
            h = self._root.winfo_height()
            x = self._root.winfo_rootx()
            y = self._root.winfo_rooty()
        else:
            ca = self._app.content_area
            w  = ca.winfo_width()
            h  = ca.winfo_height()
            x  = ca.winfo_rootx()
            y  = ca.winfo_rooty()
        if w < 100 or h < 100:
            w, h = 980, 560
        self._ox, self._oy = x, y
        self._ow, self._oh = w, h
        if self._overlay:
            self._overlay.geometry(f"{w}x{h}+{x}+{y}")

    # ── overlay fade-in ───────────────────────────────────────────────────────

    def _animate_overlay_in(self, step: int = 0) -> None:
        _FRAMES  = 10
        _TARGET  = 0.97   # 97 % opaque -> only 3 % app bleed
        _DELAY   = 18
        if not self._running or not self._overlay:
            return
        alpha = _ease_out(step / _FRAMES) * _TARGET
        try:
            self._overlay.wm_attributes("-alpha", alpha)
        except Exception:
            return
        if step < _FRAMES:
            self._root.after(_DELAY, lambda: self._animate_overlay_in(step + 1))
        else:
            self._render_step()

    # ── step rendering ────────────────────────────────────────────────────────

    def _render_step(self) -> None:
        if not self._running:
            return
        if self._step >= len(_STEPS):
            self._start_finale()
            return

        sd = _STEPS[self._step]

        # Step 5 (sidebar): extend overlay to full root window
        use_root = sd["target_key"] == "sidebar"
        self._reposition(use_root=use_root)

        bounds = self._get_spotlight(sd["target_key"])
        self._draw_spotlight(bounds, sd["accent"])

        self._destroy_card()
        self._destroy_tooltip()
        self._build_card(sd, bounds)

        if sd["target_key"] == "sidebar":
            self._build_settings_tooltip()

    # ── spotlight drawing ─────────────────────────────────────────────────────

    def _draw_spotlight(
        self,
        bounds: Optional[Tuple[int, int, int, int]],
        accent: str = "#be123c",
    ) -> None:
        cv = self._canvas
        w, h = self._ow, self._oh
        cv.delete("all")
        if bounds:
            sx1, sy1, sx2, sy2 = bounds
            cv.create_rectangle(0, 0, w, h, fill=_DIM_BG, outline="")
            for pad, col in _glow_layers(accent):
                cv.create_rectangle(
                    sx1 - pad, sy1 - pad,
                    sx2 + pad, sy2 + pad,
                    fill=col, outline="",
                )
            cv.create_rectangle(sx1, sy1, sx2, sy2, fill=_SPOT_COL, outline="")
        else:
            cv.create_rectangle(0, 0, w, h, fill=_DIM_BG, outline="")

    # ── card positioning ──────────────────────────────────────────────────────

    def _safe_card_pos(
        self,
        bounds: Optional[Tuple[int, int, int, int]],
        CW: int,
        CH: int,
        PAD: int = 16,
        GAP: int = 20,
    ) -> Tuple[int, int]:
        """Return (cx, cy) in overlay-local coords; never overlaps the spotlight."""
        ow, oh = self._ow, self._oh
        if not bounds:
            return max(PAD, (ow - CW) // 2), max(PAD, oh - CH - PAD - 20)

        sx1, sy1, sx2, sy2 = bounds

        # 1. Above spotlight
        if sy1 - GAP - CH >= PAD:
            return max(PAD, min((ow - CW) // 2, ow - CW - PAD)), sy1 - GAP - CH

        # 2. Below spotlight
        if sy2 + GAP + CH <= oh:
            cy = min(sy2 + GAP, oh - CH - PAD)
            return max(PAD, min((ow - CW) // 2, ow - CW - PAD)), max(PAD, cy)

        # 3. Right of spotlight
        if sx2 + GAP + CW <= ow - PAD:
            return sx2 + GAP, max(PAD, min((sy1 + sy2) // 2 - CH // 2, oh - CH - PAD))

        # 4. Left of spotlight
        if sx1 - GAP - CW >= PAD:
            return sx1 - GAP - CW, max(PAD, min((sy1 + sy2) // 2 - CH // 2, oh - CH - PAD))

        # 5. Top-centre (always in dim area)
        return max(PAD, (ow - CW) // 2), PAD + 12

    # ── card builder (separate Toplevel = 100 % opaque) ──────────────────────

    def _build_card(
        self,
        sd:     dict,
        bounds: Optional[Tuple[int, int, int, int]],
    ) -> None:
        CW     = CARD_W
        CH     = CARD_H
        accent = sd.get("accent", "#be123c")

        cx, cy = self._safe_card_pos(bounds, CW, CH)

        # Absolute screen position
        abs_x = self._ox + cx
        abs_y = self._oy + cy

        card = tk.Toplevel(self._root)
        card.overrideredirect(True)
        card.wm_attributes("-topmost", True)
        card.configure(bg=accent)               # accent bg -> border effect
        # Place off-screen initially while we build content
        card.geometry(f"{CW}x1+{abs_x}+{abs_y + 16}")

        # ── inner frame (card background) ────────────────────────────────────
        # padx=2 -> 2 px left/right border; pady=(6,2) -> 6 px top bar, 2 px bottom
        wrap = tk.Frame(card, bg=_CARD_BG, padx=0, pady=0)
        wrap.pack(fill="both", expand=True, padx=2, pady=(6, 2))

        inner = tk.Frame(wrap, bg=_CARD_BG)
        inner.pack(fill="both", expand=True, padx=14, pady=(11, 12))

        # ── header: title + step counter ─────────────────────────────────────
        hdr = tk.Frame(inner, bg=_CARD_BG)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text=sd["title"],
            font=(_BODY, 11, "bold"),
            bg=_CARD_BG, fg=_TEXT, anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctr = tk.Frame(hdr, bg=_CARD_BG)
        ctr.pack(side="right", anchor="ne")
        tk.Label(
            ctr, text=f"{sd['step']:02d}",
            font=(_MONO, 15, "bold"),
            bg=_CARD_BG, fg=accent,
        ).pack(anchor="e")
        tk.Label(
            ctr, text=f"/ {len(_STEPS):02d}",
            font=(_MONO, 8),
            bg=_CARD_BG, fg=_MUTED,
        ).pack(anchor="e")

        # ── divider ───────────────────────────────────────────────────────────
        tk.Frame(inner, bg=_DIVIDER, height=1).pack(fill="x", pady=(7, 8))

        # ── body text ─────────────────────────────────────────────────────────
        tk.Label(
            inner, text=sd["body"],
            font=(_BODY, 9),
            bg=_CARD_BG, fg=_BODY_TXT,
            anchor="w", justify="left",
            wraplength=CW - 36,
        ).pack(anchor="w", fill="x")

        # ── footer: dots · ✕ · Next / Done ───────────────────────────────────
        footer = tk.Frame(inner, bg=_CARD_BG)
        footer.pack(fill="x", pady=(10, 0))

        dots = tk.Frame(footer, bg=_CARD_BG)
        dots.pack(side="left")
        for i in range(len(_STEPS)):
            col = accent if i == self._step else "#1e293b"
            tk.Label(dots, text="●", font=(_BODY, 7),
                     bg=_CARD_BG, fg=col).pack(side="left", padx=2)

        x_btn = tk.Label(footer, text="✕", font=(_BODY, 10),
                         bg=_CARD_BG, fg=_MUTED, cursor="hand2", padx=4)
        x_btn.pack(side="right", padx=(6, 0))
        x_btn.bind("<Button-1>", lambda _e: self.close())
        x_btn.bind("<Enter>",    lambda _e: x_btn.config(fg="#ef4444"))
        x_btn.bind("<Leave>",    lambda _e: x_btn.config(fg=_MUTED))

        is_last  = self._step == len(_STEPS) - 1
        btn_text = "✓  Done"   if is_last else "Next  ->"
        btn_bg   = "#10b981"   if is_last else accent
        hover_bg = "#059669"   if is_last else _HOVER.get(accent, "#6d28d9")

        dalej = tk.Label(footer, text=btn_text,
                         font=(_BODY, 9, "bold"),
                         bg=btn_bg, fg="#ffffff",
                         cursor="hand2", padx=14, pady=6)
        dalej.pack(side="right")
        dalej.bind("<Button-1>", lambda _e: self._advance())
        dalej.bind("<Enter>",    lambda _e: dalej.config(bg=hover_bg))
        dalej.bind("<Leave>",    lambda _e: dalej.config(bg=btn_bg))

        # Size the card after content is built
        card.update_idletasks()
        actual_h = max(CH, card.winfo_reqheight())
        card.geometry(f"{CW}x{actual_h}+{abs_x}+{abs_y + 16}")
        self._card = card

        # Slide in from 16 px below
        self._animate_card_slide(card, abs_x, abs_y + 16, abs_y, actual_h, CW)

    # ── secondary tooltip - Settings item ────────────────────────────────────

    def _build_settings_tooltip(self) -> None:
        """
        Small bordeaux tooltip next to the Settings item in the sidebar.
        Shows 'Settings' in a red box + short description.
        """
        try:
            btn = self._app.sidebar.item_widgets["settings"]["btn"]
            self._root.update_idletasks()
            bx = btn.winfo_rootx() + btn.winfo_width() + 8
            by = btn.winfo_rooty() + btn.winfo_height() // 2 - 38
        except Exception:
            return

        TW, TH = 248, 76
        tip = tk.Toplevel(self._root)
        tip.overrideredirect(True)
        tip.wm_attributes("-topmost", True)
        tip.geometry(f"{TW}x{TH}+{bx}+{by}")
        tip.configure(bg=_TIP_BORD)
        self._tooltip = tip

        # Left accent bar
        tk.Frame(tip, bg=_TIP_BAR, width=3).pack(side="left", fill="y")

        body = tk.Frame(tip, bg=_TIP_BG)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        # "Settings" in red box (highlighted)
        tk.Label(
            body, text="  ⚙  Settings  ",
            font=(_BODY, 9, "bold"),
            bg="#be123c", fg="#ffffff",
        ).pack(anchor="w")

        tk.Label(
            body,
            text="Change language, and program preferences.",
            font=(_BODY, 8),
            bg=_TIP_BG, fg="#94a3b8",
            anchor="w", justify="left",
            wraplength=TW - 28,
        ).pack(anchor="w", pady=(5, 0))

    def _destroy_tooltip(self) -> None:
        if self._tooltip:
            try:
                self._tooltip.destroy()
            except Exception:
                pass
            self._tooltip = None

    # ── card slide-in (Toplevel geometry) ────────────────────────────────────

    def _animate_card_slide(
        self,
        card_win:  tk.Toplevel,
        abs_x:     int,
        start_y:   int,
        target_y:  int,
        height:    int,
        width:     int,
        step:      int = 0,
    ) -> None:
        _FRAMES, _DELAY = 10, 18
        if card_win is not self._card:
            return
        cur_y = int(start_y + (target_y - start_y) * _ease_out(step / _FRAMES))
        try:
            card_win.geometry(f"{width}x{height}+{abs_x}+{cur_y}")
        except Exception:
            return
        if step < _FRAMES:
            self._root.after(
                _DELAY,
                lambda: self._animate_card_slide(
                    card_win, abs_x, start_y, target_y, height, width, step + 1
                ),
            )

    def _destroy_card(self) -> None:
        if self._card:
            try:
                self._card.destroy()
            except Exception:
                pass
            self._card = None

    # ── navigation ────────────────────────────────────────────────────────────

    def _close_spotlight(self) -> None:
        if self._canvas:
            self._canvas.delete("all")
            self._canvas.create_rectangle(
                0, 0, self._ow, self._oh, fill=_DIM_BG, outline=""
            )

    def _advance(self) -> None:
        self._destroy_card()
        self._destroy_tooltip()
        self._close_spotlight()
        self._step += 1
        if self._running:
            self._root.after(280, self._render_step)

    def _on_bg_click(self, _event) -> None:
        self.close()

    # ── spotlight bounds ──────────────────────────────────────────────────────

    def _get_spotlight(
        self, key: str
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Return (x1, y1, x2, y2) relative to overlay origin (self._ox, self._oy).
        """
        app = self._app
        self._root.update_idletasks()
        ox = self._ox
        oy = self._oy
        P  = self.SPOT_PAD

        def _cl(x1, y1, x2, y2):
            return (
                max(0, x1), max(0, y1),
                min(self._ow, x2), min(self._oh, y2),
            )

        try:
            if key == "chart":
                c   = app.realtime_canvas
                fbs = list(app.filter_buttons.values())
                x1  = c.winfo_rootx() - ox - P
                y1  = c.winfo_rooty() - oy - P
                x2  = max(fb.winfo_rootx() + fb.winfo_width()  for fb in fbs) - ox + P
                y2  = max(fb.winfo_rooty() + fb.winfo_height() for fb in fbs) - oy + P
                return _cl(x1, y1, x2, y2)

            elif key == "nav":
                ln = app.guide_left_nav
                rn = app.guide_right_nav
                x1 = ln.winfo_rootx() - ox - P
                y1 = min(ln.winfo_rooty(), rn.winfo_rooty()) - oy - P
                x2 = rn.winfo_rootx() + rn.winfo_width()  - ox + P
                y2 = max(
                    ln.winfo_rooty() + ln.winfo_height(),
                    rn.winfo_rooty() + rn.winfo_height(),
                ) - oy + P
                return _cl(x1, y1, x2, y2)

            elif key == "hw":
                mc = app.guide_middle_center
                x1 = mc.winfo_rootx() - ox - P
                y1 = mc.winfo_rooty() - oy - P
                x2 = mc.winfo_rootx() + mc.winfo_width()  - ox + P
                y2 = mc.winfo_rooty() + mc.winfo_height() - oy + P
                return _cl(x1, y1, x2, y2)

            elif key == "hckgpt":
                panel = getattr(app, "gpt_panel", None)
                if panel:
                    frame = getattr(panel, "frame", None)
                    if frame:
                        collapsed_h = getattr(panel, "collapsed_h", 34)
                        x1 = frame.winfo_rootx() - ox - P
                        y1 = frame.winfo_rooty() - oy - P
                        x2 = frame.winfo_rootx() + frame.winfo_width() - ox + P
                        y2 = frame.winfo_rooty() + collapsed_h - oy + P
                        if x2 > x1 + 20 and y2 > y1 + 4 and y1 < self._oh:
                            return _cl(x1, y1, x2, y2)
                return None

            elif key == "sidebar":
                # Overlay covers full root - spotlight the sidebar frame
                sb = getattr(app, "sidebar", None)
                if sb:
                    # SidebarNav wraps its content in .frame; fall back to sb if plain widget
                    sf = getattr(sb, "frame", sb)
                    x1 = sf.winfo_rootx() - ox - P
                    y1 = sf.winfo_rooty() - oy - P
                    x2 = sf.winfo_rootx() + sf.winfo_width()  - ox + P
                    y2 = sf.winfo_rooty() + sf.winfo_height() - oy + P
                    return _cl(x1, y1, x2, y2)
                return None

        except Exception:
            pass

        return None

    # ── finale ────────────────────────────────────────────────────────────────

    def _start_finale(self) -> None:
        self._running = False
        self._finale  = True
        self._destroy_card()
        if self._canvas:
            self._canvas.delete("all")
            self._canvas.create_rectangle(
                0, 0, self._ow, self._oh, fill=_DIM_BG, outline=""
            )
        self._animate_finale()

    def _animate_finale(self, step: int = 0) -> None:
        _FRAMES, _INTERVAL, _START = 22, 100, 0.97
        if not self._finale or not self._overlay:
            return
        alpha = _START * (1.0 - _ease_in_out(step / _FRAMES))
        try:
            self._overlay.wm_attributes("-alpha", max(0.0, alpha))
        except Exception:
            return
        if step < _FRAMES:
            self._root.after(_INTERVAL, lambda: self._animate_finale(step + 1))
        else:
            self._finale = False
            try:
                self._overlay.destroy()
            except Exception:
                pass
            self._overlay = None
            self._canvas  = None
            self._show_finale_banner()

    # ── finale banner ─────────────────────────────────────────────────────────

    def _show_finale_banner(self) -> None:
        ca = self._app.content_area
        self._root.update_idletasks()
        bx = ca.winfo_rootx()
        by = ca.winfo_rooty()
        bw = ca.winfo_width()
        bh = ca.winfo_height()
        BNR_H = 60

        bnr = tk.Toplevel(self._root)
        bnr.overrideredirect(True)
        bnr.wm_attributes("-topmost", True)
        bnr.configure(bg=_BNR_BG)
        bnr.geometry(f"{bw}x{BNR_H}+{bx}+{by + bh}")
        self._banner = bnr

        tk.Frame(bnr, bg=_BNR_LINE, height=2).pack(fill="x")

        body = tk.Frame(bnr, bg=_BNR_BG)
        body.pack(fill="both", expand=True, padx=20)

        left = tk.Frame(body, bg=_BNR_BG)
        left.pack(side="left", fill="y", pady=8)

        tk.Label(left, text="✦", font=(_BODY, 13),
                 bg=_BNR_BG, fg=_BNR_AMB).pack(side="left", padx=(0, 12))

        txt_col = tk.Frame(left, bg=_BNR_BG)
        txt_col.pack(side="left")
        tk.Label(txt_col, text="Was that enough?",
                 font=("Segoe UI Semibold", 10, "bold"),
                 bg=_BNR_BG, fg=_BNR_TXT, anchor="w").pack(anchor="w")
        tk.Label(txt_col, text="You can expand any section or close the guide.",
                 font=(_BODY, 8), bg=_BNR_BG, fg=_BNR_AMB, anchor="w").pack(anchor="w")

        right = tk.Frame(body, bg=_BNR_BG)
        right.pack(side="right", fill="y", pady=12)

        close_btn = tk.Label(right, text="Got it  ✓",
                             font=("Segoe UI Semibold", 9, "bold"),
                             bg="#2a1400", fg=_BNR_AMB,
                             padx=16, pady=5, cursor="hand2",
                             highlightthickness=1, highlightbackground=_BNR_LINE)
        close_btn.pack(side="left", padx=(0, 10))
        close_btn.bind("<Button-1>", lambda _: self._close_banner())
        close_btn.bind("<Enter>",    lambda _: close_btn.config(bg="#3d1e00"))
        close_btn.bind("<Leave>",    lambda _: close_btn.config(bg="#2a1400"))

        more_btn = tk.Label(right, text="Show more  ->",
                            font=("Segoe UI Semibold", 9, "bold"),
                            bg=_BNR_AMB, fg="#1a0700", padx=16, pady=5, cursor="hand2")
        more_btn.pack(side="left")
        more_btn.bind("<Button-1>", lambda _: self._on_expand())
        more_btn.bind("<Enter>",    lambda _: more_btn.config(bg=_BNR_GOLD))
        more_btn.bind("<Leave>",    lambda _: more_btn.config(bg=_BNR_AMB))

        target_y = by + bh - BNR_H
        self._animate_banner_slide(bnr, bx, by + bh, target_y, bw, BNR_H)

    def _animate_banner_slide(
        self, bnr, bx, start_y, target_y, bw, bnr_h, step=0
    ) -> None:
        _FRAMES, _DELAY = 10, 28
        if step > _FRAMES:
            return
        cur_y = int(start_y + (target_y - start_y) * _ease_out(step / _FRAMES))
        try:
            bnr.geometry(f"{bw}x{bnr_h}+{bx}+{cur_y}")
        except Exception:
            return
        if step < _FRAMES:
            self._root.after(
                _DELAY,
                lambda: self._animate_banner_slide(
                    bnr, bx, start_y, target_y, bw, bnr_h, step + 1
                ),
            )

    def _close_banner(self) -> None:
        if self._banner:
            try:
                self._banner.destroy()
            except Exception:
                pass
            self._banner = None

    def _on_expand(self) -> None:
        self._close_banner()
        cb = getattr(self._app, "guide_expand_callback", None)
        if callable(cb):
            cb()
