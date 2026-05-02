# ui/guide/live_guide.py
"""
Live Guide — interactive step-by-step tour of the PC_Workman dashboard.

Uses a transparent Toplevel overlay (Windows -transparentcolor trick) to:
  • Dim the whole content area with a dark semi-transparent layer
  • Cut a glowing "spotlight" hole around the widget being explained
  • Show a floating info card with step title, description, step dots,
    a DALEJ (Next) button and a close (✕) button

Three steps:
  1. Main real-time chart + LIVE/1H/4H/… filter buttons
  2. Left nav (My PC, Monitoring, …) + Right nav (FAN Dashboard, …)
  3. Hardware cards (CPU/RAM/GPU) + Session Averages bars

Requirements on the host object (MainWindowExpanded):
  • self.content_area       – parent container for the whole dashboard
  • self.realtime_canvas    – the main chart canvas
  • self.filter_buttons     – dict {name: Label} for filter buttons
  • self.guide_left_nav     – left_nav Frame (stored in _build_middle_section)
  • self.guide_right_nav    – right_nav Frame
  • self.guide_middle_center– center Frame (session bars + hw cards)
"""

from __future__ import annotations
import tkinter as tk
from typing import Optional, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# Colour constants
# ──────────────────────────────────────────────────────────────────────────────

_ACCENT   = "#8b5cf6"   # violet — spotlight border & progress dots
_CARD_BG  = "#0d1117"
_CARD_BD  = "#1e293b"
_DIM_BG   = "#030610"   # near-black dim layer
_SPOT_COL = "#ffffff"   # transparent key (Windows -transparentcolor)
_TEXT     = "#e2e8f0"
_MUTED    = "#64748b"
_BTN_BG   = "#8b5cf6"
_BTN_FG   = "#ffffff"


# ──────────────────────────────────────────────────────────────────────────────
# Step definitions
# ──────────────────────────────────────────────────────────────────────────────

_STEPS = [
    {
        "step":       1,
        "badge":      "📊",
        "title":      "Wykres Czasu Rzeczywistego",
        "body":       (
            "Tutaj widzisz całe użycie podzespołów w jednym miejscu —\n"
            "CPU (niebieski), GPU (zielony) i RAM (żółty) aktualizowane\n"
            "na żywo co kilka sekund.\n\n"
            "Przyciski filtrów pozwalają przełączać widok:\n"
            "  LIVE — bieżące dane na żywo\n"
            "  1H / 4H / 1D — historia z ostatniej godziny / 4h / doby\n"
            "  1W / 1M — tygodniowe i miesięczne trendy z bazy danych"
        ),
        "target_key": "chart",
        "card_side":  "bottom",
    },
    {
        "step":       2,
        "badge":      "🧭",
        "title":      "Nawigacja po panelach",
        "body":       (
            "Lewy panel — sekcje systemowe:\n"
            "  💻 My PC         — Twój sprzęt i dane osobiste\n"
            "  📡 Monitoring    — czujniki, temperatury, alerty\n"
            "  📊 AllMonitor    — pełne dane min / max / avg\n"
            "  ⚡ Optimization  — przyspieszanie i porządki\n\n"
            "Prawy panel — narzędzia zaawansowane:\n"
            "  🌀 FAN Dashboard — zarządzanie wentylatorami\n"
            "  🚀 HCK_Labs      — eksperymenty i beta-funkcje\n"
            "  📖 Guide         — właśnie tu jesteś!"
        ),
        "target_key": "nav",
        "card_side":  "right",
    },
    {
        "step":       3,
        "badge":      "🖥️",
        "title":      "Twoje PC — dane na żywo",
        "body":       (
            "Temperatury i status sprzętu — CPU, RAM, GPU.\n"
            "Mini-wykresy temperatur odświeżają się co kilka sekund;\n"
            "kolor wskaźnika mówi od razu czy wszystko jest OK.\n\n"
            "Poniżej: Średnie użycia zasobów z całej bieżącej sesji.\n"
            "Paski CPU / GPU / RAM rosną razem z Twoją pracą —\n"
            "dzięki temu widzisz jak komputer pracował od startu aplikacji."
        ),
        "target_key": "hw",
        "card_side":  "top",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# LiveGuide class
# ──────────────────────────────────────────────────────────────────────────────

class LiveGuide:
    """Interactive spotlight guide for the PC_Workman dashboard."""

    CARD_W   = 370
    SPOT_PAD = 12    # px padding around spotlight target

    def __init__(self, app) -> None:
        """
        Parameters
        ----------
        app :
            MainWindowExpanded instance — must expose .root, .content_area,
            .realtime_canvas, .filter_buttons, .guide_left_nav,
            .guide_right_nav, .guide_middle_center
        """
        self._app     = app
        self._root    = app.root
        self._step    = 0
        self._running = False

        self._overlay : Optional[tk.Toplevel] = None
        self._canvas  : Optional[tk.Canvas]   = None
        self._card    : Optional[tk.Frame]     = None

        # cached overlay dimensions (set in _reposition)
        self._ow = 0
        self._oh = 0

    # ── public ────────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._step    = 0
        self._create_overlay()
        self._render_step()

    def close(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._overlay:
            try:
                self._overlay.destroy()
            except Exception:
                pass
        self._overlay = None
        self._canvas  = None
        self._card    = None

    # ── overlay construction ──────────────────────────────────────────────────

    def _create_overlay(self) -> None:
        ov = tk.Toplevel(self._root)
        ov.overrideredirect(True)
        ov.wm_attributes("-topmost", True)
        # 82 % opaque dim layer; white pixels → fully transparent (spotlight)
        ov.wm_attributes("-alpha", 0.82)
        ov.wm_attributes("-transparentcolor", _SPOT_COL)
        ov.configure(bg=_DIM_BG)

        self._overlay = ov
        self._reposition()

        cv = tk.Canvas(ov, bg=_DIM_BG, highlightthickness=0)
        cv.place(x=0, y=0, relwidth=1, relheight=1)
        self._canvas = cv

        # ESC / background click → close
        ov.bind("<Escape>", lambda _e: self.close())
        cv.bind("<Button-1>", self._on_bg_click)

    def _reposition(self) -> None:
        ca = self._app.content_area
        self._root.update_idletasks()
        x = ca.winfo_rootx()
        y = ca.winfo_rooty()
        w = ca.winfo_width()
        h = ca.winfo_height()
        if w < 100 or h < 100:
            w, h = 980, 560
        self._ow, self._oh = w, h
        if self._overlay:
            self._overlay.geometry(f"{w}x{h}+{x}+{y}")

    # ── step rendering ────────────────────────────────────────────────────────

    def _render_step(self) -> None:
        if self._step >= len(_STEPS):
            self.close()
            return

        step_data = _STEPS[self._step]

        # Sync size in case the window was resized
        self._reposition()

        bounds = self._get_spotlight(step_data["target_key"])

        # ── draw dim + spotlight on canvas ────────────────────────────────────
        cv = self._canvas
        cv.delete("all")
        w, h = self._ow, self._oh

        if bounds:
            sx1, sy1, sx2, sy2 = bounds
            # Four dim panels around the spotlight (leaving spotlight bare)
            cv.create_rectangle(0,   0,   w,   sy1, fill=_DIM_BG, outline="")
            cv.create_rectangle(0,   sy2, w,   h,   fill=_DIM_BG, outline="")
            cv.create_rectangle(0,   sy1, sx1, sy2, fill=_DIM_BG, outline="")
            cv.create_rectangle(sx2, sy1, w,   sy2, fill=_DIM_BG, outline="")
            # Glowing dashed border around spotlight
            cv.create_rectangle(sx1, sy1, sx2, sy2,
                                fill="", outline=_ACCENT, width=2, dash=(6, 3))
            # White "hole" — becomes fully transparent via -transparentcolor
            cv.create_rectangle(sx1+3, sy1+3, sx2-3, sy2-3,
                                fill=_SPOT_COL, outline="")
        else:
            # Fallback: dim everything
            cv.create_rectangle(0, 0, w, h, fill=_DIM_BG, outline="")

        # ── destroy old card ──────────────────────────────────────────────────
        if self._card:
            try:
                self._card.destroy()
            except Exception:
                pass
            self._card = None

        # ── animate card in with a fade-slide ────────────────────────────────
        self._build_card(step_data, bounds)

    # ── spotlight bounds ──────────────────────────────────────────────────────

    def _get_spotlight(self, key: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Return (x1, y1, x2, y2) relative to the overlay for *key*.
        Returns None if widgets are not yet available / not visible.
        """
        app  = self._app
        ca   = app.content_area
        self._root.update_idletasks()
        ox = ca.winfo_rootx()
        oy = ca.winfo_rooty()
        P  = self.SPOT_PAD

        def _clamp(x1, y1, x2, y2):
            return (max(0, x1), max(0, y1),
                    min(self._ow, x2), min(self._oh, y2))

        try:
            if key == "chart":
                # realtime_canvas top → filter_buttons bottom
                c   = app.realtime_canvas
                fbs = list(app.filter_buttons.values())
                x1  = c.winfo_rootx() - ox - P
                y1  = c.winfo_rooty() - oy - P
                x2  = max(fb.winfo_rootx() + fb.winfo_width() for fb in fbs) - ox + P
                y2  = max(fb.winfo_rooty() + fb.winfo_height() for fb in fbs) - oy + P
                return _clamp(x1, y1, x2, y2)

            elif key == "nav":
                # left_nav leftmost → right_nav rightmost, same top/bottom
                ln  = app.guide_left_nav
                rn  = app.guide_right_nav
                x1  = ln.winfo_rootx() - ox - P
                y1  = min(ln.winfo_rooty(), rn.winfo_rooty()) - oy - P
                x2  = rn.winfo_rootx() + rn.winfo_width()  - ox + P
                y2  = max(ln.winfo_rooty() + ln.winfo_height(),
                          rn.winfo_rooty() + rn.winfo_height()) - oy + P
                return _clamp(x1, y1, x2, y2)

            elif key == "hw":
                # middle center frame (session bars + hardware cards)
                mc  = app.guide_middle_center
                x1  = mc.winfo_rootx() - ox - P
                y1  = mc.winfo_rooty() - oy - P
                x2  = mc.winfo_rootx() + mc.winfo_width()  - ox + P
                y2  = mc.winfo_rooty() + mc.winfo_height() - oy + P
                return _clamp(x1, y1, x2, y2)

        except Exception:
            pass
        return None

    # ── info card ─────────────────────────────────────────────────────────────

    def _build_card(self, step_data: dict,
                    bounds: Optional[Tuple[int, int, int, int]]) -> None:
        CW  = self.CARD_W
        PAD = 16
        GAP = 18     # distance between spotlight edge and card

        # ── position card ─────────────────────────────────────────────────────
        if bounds:
            sx1, sy1, sx2, sy2 = bounds
            side = step_data.get("card_side", "bottom")

            if side == "bottom":
                cx = max(PAD, min(sx1, self._ow - CW - PAD))
                cy = sy2 + GAP
                if cy + 260 > self._oh:   # not enough room below → flip above
                    cy = max(PAD, sy1 - 260 - GAP)
            elif side == "top":
                cx = max(PAD, min(sx1, self._ow - CW - PAD))
                cy = sy1 - 260 - GAP
                if cy < PAD:              # not enough room above → flip below
                    cy = sy2 + GAP
            elif side == "right":
                # Place to the right of the spotlight, vertically centred
                cx = sx2 + GAP
                cy = max(PAD, (sy1 + sy2) // 2 - 130)
                if cx + CW > self._ow - PAD:
                    cx = max(PAD, sx1 - CW - GAP)
            else:  # center
                cx = (self._ow - CW) // 2
                cy = max(PAD, (sy1 + sy2) // 2 - 130)
        else:
            cx = (self._ow - CW) // 2
            cy = (self._oh - 260) // 2

        cy = max(PAD, min(cy, self._oh - 260 - PAD))

        # ── card frame ────────────────────────────────────────────────────────
        card = tk.Frame(
            self._overlay,
            bg=_CARD_BG, bd=0,
            highlightthickness=1,
            highlightbackground=_ACCENT
        )
        card.place(x=cx, y=cy, width=CW)
        self._card = card

        # accent top bar
        tk.Frame(card, bg=_ACCENT, height=2).pack(fill="x")

        inner = tk.Frame(card, bg=_CARD_BG)
        inner.pack(fill="both", expand=True, padx=PAD, pady=(10, PAD))

        # ── header row: badge + title + step indicator ────────────────────────
        hdr = tk.Frame(inner, bg=_CARD_BG)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text=step_data["badge"],
            font=("Segoe UI", 20),
            bg=_CARD_BG, fg=_TEXT
        ).pack(side="left", padx=(0, 10))

        title_col = tk.Frame(hdr, bg=_CARD_BG)
        title_col.pack(side="left", fill="both", expand=True)

        tk.Label(
            title_col, text=step_data["title"],
            font=("Segoe UI Semibold", 11, "bold"),
            bg=_CARD_BG, fg=_TEXT, anchor="w"
        ).pack(anchor="w")

        tk.Label(
            title_col,
            text=f"Krok {step_data['step']} z {len(_STEPS)}",
            font=("Segoe UI", 8),
            bg=_CARD_BG, fg=_MUTED, anchor="w"
        ).pack(anchor="w")

        # ── separator ─────────────────────────────────────────────────────────
        tk.Frame(inner, bg=_CARD_BD, height=1).pack(fill="x", pady=(8, 8))

        # ── body text ─────────────────────────────────────────────────────────
        tk.Label(
            inner, text=step_data["body"],
            font=("Segoe UI", 9),
            bg=_CARD_BG, fg="#94a3b8",
            wraplength=CW - PAD * 2 - 8,
            justify="left", anchor="nw"
        ).pack(anchor="w")

        # ── bottom row: step dots + close + DALEJ ────────────────────────────
        btn_row = tk.Frame(inner, bg=_CARD_BG)
        btn_row.pack(fill="x", pady=(14, 0))

        # step dots
        dots = tk.Frame(btn_row, bg=_CARD_BG)
        dots.pack(side="left")
        for i in range(len(_STEPS)):
            col = _ACCENT if i == self._step else "#1e293b"
            tk.Label(dots, text="●", font=("Segoe UI", 9),
                     bg=_CARD_BG, fg=col).pack(side="left", padx=1)

        # close (✕)
        x_btn = tk.Label(
            btn_row, text="✕",
            font=("Segoe UI", 11),
            bg=_CARD_BG, fg=_MUTED,
            cursor="hand2", padx=4
        )
        x_btn.pack(side="right", padx=(6, 0))
        x_btn.bind("<Button-1>", lambda _e: self.close())
        x_btn.bind("<Enter>",  lambda _e: x_btn.config(fg="#ef4444"))
        x_btn.bind("<Leave>",  lambda _e: x_btn.config(fg=_MUTED))

        # DALEJ / Zakończ
        is_last  = (self._step == len(_STEPS) - 1)
        btn_text = "✓  Zakończ" if is_last else "Dalej  →"
        btn_bg   = "#10b981"   if is_last else _BTN_BG

        dalej = tk.Label(
            btn_row, text=btn_text,
            font=("Segoe UI Semibold", 9, "bold"),
            bg=btn_bg, fg=_BTN_FG,
            cursor="hand2", padx=14, pady=6
        )
        dalej.pack(side="right")
        dalej.bind("<Button-1>", lambda _e: self._advance())
        hover_bg = "#059669" if is_last else "#7c3aed"
        dalej.bind("<Enter>", lambda _e: dalej.config(bg=hover_bg))
        dalej.bind("<Leave>", lambda _e: dalej.config(bg=btn_bg))

    # ── navigation ────────────────────────────────────────────────────────────

    def _advance(self) -> None:
        self._step += 1
        self._render_step()

    def _on_bg_click(self, _event) -> None:
        self.close()
