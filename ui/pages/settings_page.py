# ui/pages/settings_page.py
"""Settings page - two-column compact layout with AI section highlight."""

import tkinter as tk
import json
import os

from ui.theme import THEME

# Centralized i18n - graceful fallback if utils not on path yet
try:
    from utils.i18n import t as _t, set_lang as _i18n_set_lang, get_lang as _i18n_get_lang
    _HAS_I18N = True
except ImportError:
    _HAS_I18N = False
    def _t(key: str, **kw) -> str: return key      # noqa: E731
    def _i18n_set_lang(code: str) -> None: pass
    def _i18n_get_lang() -> str: return "en"

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# ── Colour palette ─────────────────────────────────────────────────────────────
_BG       = THEME["bg_main"]
_PANEL    = "#10141a"
_BORDER   = "#1c2230"
_TEXT     = THEME["text"]
_MUTED    = "#6b7c93"
_ACCENT   = THEME["accent"]       # neon mint
_ACCENT2  = THEME["accent2"]      # neon blue
_WARN     = "#f59e0b"
_DANGER   = "#ef4444"
_GREEN    = "#10b981"

# hck_GPT / AI section - indigo palette
_AI_BG    = "#0d0f1e"
_AI_PANEL = "#11132a"
_AI_BD    = "#3730a3"
_AI_BAR   = "#818cf8"
_AI_TEXT  = "#c7d2fe"
_AI_MUTED = "#6366f1"

# Notifications section - lighter violet (sibling of AI, less weight)
_NOTIF_BG  = "#0b0c1c"
_NOTIF_BD  = "#4c1d95"
_NOTIF_BAR = "#a78bfa"
_NOTIF_MUT = "#7c3aed"

# ── PC WORKMAN - GENERAL section - bordeaux-violet gaming palette ───────────────
_GEN_BG    = "#0d0010"   # very dark violet-black
_GEN_PANEL = "#0f0016"   # card inner
_GEN_BD    = "#581c87"   # violet border
_GEN_BAR   = "#c026d3"   # fuchsia top bar (3 px)
_GEN_SIDE  = "#9f1239"   # bordeaux left bar in header
_GEN_ACC   = "#e879f9"   # bright fuchsia accent
_GEN_MUTED = "#7c3aed"   # dim violet muted
_GEN_TEXT  = "#fae8ff"   # light lavender text
_GEN_SEP   = "#3b0764"   # dark violet separator
_GEN_BADGE = "#3b0764"   # badge background

try:
    # MSIX/Store-safe: the app dir next to the exe is read-only there
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    _APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_SETTINGS_FILE = os.path.join(_APP_DIR, "settings", "app_settings.json")

# ── Persistence ───────────────────────────────────────────────────────────────

def _load_settings() -> dict:
    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_settings(data: dict) -> None:
    os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
    try:
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ── Layout helpers ────────────────────────────────────────────────────────────

def _section_header(
    parent: tk.Widget,
    title: str,
    accent: str = _MUTED,
    bg: str = _BG,
) -> tk.Frame:
    """3 px coloured left bar + uppercase label."""
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", pady=(14, 5))
    tk.Frame(row, bg=accent, width=3).pack(side="left", fill="y")
    tk.Label(
        row, text=title.upper(),
        font=(_BODY, 7, "bold"),
        bg=bg, fg=accent, anchor="w", padx=8,
    ).pack(side="left", anchor="w")
    return row


def _ai_section_header(parent: tk.Widget) -> tk.Frame:
    """Special header row for the hck_GPT section with AI badge."""
    row = tk.Frame(parent, bg=_BG)
    row.pack(fill="x", pady=(14, 5))
    tk.Frame(row, bg=_AI_BAR, width=3).pack(side="left", fill="y")
    tk.Label(
        row, text=_t("settings.section.hck_gpt"),
        font=(_BODY, 7, "bold"),
        bg=_BG, fg=_AI_BAR, anchor="w", padx=8,
    ).pack(side="left", anchor="w")
    tk.Label(
        row, text=" AI ",
        font=(_BODY, 7, "bold"),
        bg="#4f46e5", fg="#ffffff",
        padx=5, pady=1,
    ).pack(side="left", padx=(2, 0), anchor="w")
    return row


def _gen_section_header(parent: tk.Widget) -> tk.Frame:
    """Gaming bordeaux-violet header for PC WORKMAN - GENERAL section."""
    row = tk.Frame(parent, bg=_BG)
    row.pack(fill="x", pady=(14, 5))

    # Dual left bar: bordeaux + violet
    bars = tk.Frame(row, bg=_BG)
    bars.pack(side="left", fill="y")
    tk.Frame(bars, bg=_GEN_SIDE, width=2).pack(side="left", fill="y")
    tk.Frame(bars, bg=_GEN_MUTED, width=1).pack(side="left", fill="y")

    tk.Label(
        row, text=_t("settings.section.general_badge"),
        font=(_BODY, 7, "bold"),
        bg=_BG, fg=_GEN_ACC, anchor="w", padx=6,
    ).pack(side="left", anchor="w")

    tk.Label(
        row, text=f" {_t('settings.section.general')} ",
        font=(_BODY, 7, "bold"),
        bg=_GEN_BADGE, fg="#c084fc",
        padx=5, pady=1,
    ).pack(side="left", padx=(2, 0), anchor="w")

    tk.Label(
        row, text=" ⚡ ",
        font=(_BODY, 8),
        bg=_GEN_SIDE, fg="#fda4af",
        padx=3, pady=1,
    ).pack(side="left", padx=(4, 0), anchor="w")
    return row


def _card(parent: tk.Widget, pady_top: int = 0, padx: int = 0) -> tk.Frame:
    """Standard settings card with a 1 px border."""
    outer = tk.Frame(parent, bg=_BORDER)
    outer.pack(fill="x", padx=padx, pady=(pady_top, 0))
    inner = tk.Frame(outer, bg=_PANEL)
    inner.pack(fill="x", padx=1, pady=1)
    return inner


def _ai_card(parent: tk.Widget) -> tk.Frame:
    """Indigo-bordered card for the hck_GPT section."""
    outer = tk.Frame(parent, bg=_AI_BD)
    outer.pack(fill="x", pady=(0, 0))
    card = tk.Frame(outer, bg=_AI_BG)
    card.pack(fill="x", padx=1, pady=1)
    tk.Frame(card, bg=_AI_BAR, height=2).pack(fill="x")
    return card


def _gen_card(parent: tk.Widget) -> tk.Frame:
    """Bordeaux-violet gaming card for PC WORKMAN - GENERAL section."""
    outer = tk.Frame(parent, bg=_GEN_BD)
    outer.pack(fill="x", pady=(0, 0))
    card = tk.Frame(outer, bg=_GEN_PANEL)
    card.pack(fill="x", padx=1, pady=1)
    # Thick fuchsia + bordeaux top bar
    bar_row = tk.Frame(card, bg=_GEN_PANEL)
    bar_row.pack(fill="x")
    tk.Frame(bar_row, bg=_GEN_BAR,  height=2).pack(fill="x")
    tk.Frame(bar_row, bg=_GEN_SIDE, height=1).pack(fill="x")
    return card


def _notif_section_header(parent: tk.Widget) -> tk.Frame:
    """Lighter violet header for Notifications (sibling of _ai_section_header)."""
    row = tk.Frame(parent, bg=_BG)
    row.pack(fill="x", pady=(14, 5))
    tk.Frame(row, bg=_NOTIF_BAR, width=3).pack(side="left", fill="y")
    tk.Label(
        row, text=_t("settings.section.notifications"),
        font=(_BODY, 7, "bold"),
        bg=_BG, fg=_NOTIF_BAR, anchor="w", padx=8,
    ).pack(side="left", anchor="w")
    return row


def _notif_card(parent: tk.Widget) -> tk.Frame:
    """Light-violet–bordered card for Notifications section."""
    outer = tk.Frame(parent, bg=_NOTIF_BD)
    outer.pack(fill="x", pady=(0, 0))
    card = tk.Frame(outer, bg=_NOTIF_BG)
    card.pack(fill="x", padx=1, pady=1)
    tk.Frame(card, bg=_NOTIF_BAR, height=1).pack(fill="x")   # thinner bar (1px)
    return card


def _setting_row(
    card: tk.Widget,
    label: str,
    sublabel: str = "",
    right_widget_factory=None,
    separator: bool = True,
    bg: str = _PANEL,
    border: str = _BORDER,
    pady: int = 4,
) -> tk.Frame:
    """One compact row inside a card."""
    row = tk.Frame(card, bg=bg)
    row.pack(fill="x", padx=12, pady=pady)

    left = tk.Frame(row, bg=bg)
    left.pack(side="left", fill="both", expand=True)

    tk.Label(
        left, text=label,
        font=(_BODY, 9), bg=bg, fg=_TEXT, anchor="w",
    ).pack(anchor="w")

    if sublabel:
        tk.Label(
            left, text=sublabel,
            font=(_BODY, 7), bg=bg, fg=_MUTED, anchor="w",
        ).pack(anchor="w")

    if right_widget_factory:
        right_widget_factory(row)

    if separator:
        tk.Frame(card, bg=border, height=1).pack(fill="x", padx=12)

    return row


# ── Toggle - square bordeaux gaming style ────────────────────────────────────

class _ToggleSquare:
    """Square gaming toggle. ON = bordeaux, OFF = dark. Calls on_change(bool)."""
    W, H = 44, 22

    def __init__(self, parent: tk.Widget, initial: bool, on_change=None,
                 bg: str = _PANEL):
        self._on_change = on_change
        self._state     = initial
        self._bg        = bg

        self.canvas = tk.Canvas(
            parent, width=self.W, height=self.H,
            bg=bg, highlightthickness=0, cursor="hand2",
        )
        self.canvas.pack(side="right", padx=(8, 0))
        self.canvas.bind("<Button-1>", self._toggle)
        self._draw()

    def _draw(self):
        c = self.canvas
        c.delete("all")
        if self._state:
            # ON - bordeaux
            c.create_rectangle(0, 0, self.W - 1, self.H - 1,
                                fill="#3b0014", outline="#be123c", width=1)
            c.create_line(4, self.H // 2, self.W - 4, self.H // 2,
                          fill="#500724", width=1)
            c.create_rectangle(self.W - 18, 4, self.W - 5, self.H - 5,
                                fill="#f43f5e", outline="")
        else:
            # OFF - dark neutral
            c.create_rectangle(0, 0, self.W - 1, self.H - 1,
                                fill="#0d1018", outline="#2d3748", width=1)
            c.create_line(4, self.H // 2, self.W - 4, self.H // 2,
                          fill="#1e293b", width=1)
            c.create_rectangle(5, 4, 18, self.H - 5,
                                fill="#374151", outline="")

    def _toggle(self, _=None):
        self._state = not self._state
        self._draw()
        if self._on_change:
            self._on_change(self._state)

    def get(self) -> bool:
        return self._state

    def set(self, value: bool):
        if self._state != value:
            self._state = value
            self._draw()


# backward-compat alias
_TogglePill = _ToggleSquare


# ── Locked toggle - gray, non-interactive, 🔒 centred ─────────────────────────

class _LockedToggle:
    """
    Gray non-interactive toggle.
    Shows a 🔒 emoji centred on the knob - option not yet available.
    """
    W, H = 44, 22

    def __init__(self, parent: tk.Widget, bg: str = _PANEL):
        self.canvas = tk.Canvas(
            parent, width=self.W, height=self.H,
            bg=bg, highlightthickness=0, cursor="arrow",
        )
        self.canvas.pack(side="right", padx=(8, 0))
        self._draw()

    def _draw(self):
        c  = self.canvas
        W, H = self.W, self.H
        # Dark gray frame
        c.create_rectangle(0, 0, W - 1, H - 1,
                            fill="#1a1d24", outline="#374151", width=1)
        # Dim track line
        c.create_line(4, H // 2, W - 4, H // 2, fill="#2d3748", width=1)
        # Centred gray knob
        mid = W // 2
        c.create_rectangle(mid - 7, 4, mid + 7, H - 5,
                            fill="#374151", outline="#4b5563")
        # Lock emoji centred on knob
        c.create_text(mid, H // 2, text="🔒",
                      font=("Segoe UI Emoji", 7), fill="#111318")


# ── Language chip selector ─────────────────────────────────────────────────────

class _LangSelector:
    """Row of pill chips for language selection."""

    def __init__(self, parent: tk.Widget, current: str,
                 options: list, on_change=None, bg: str = _PANEL):
        self._on_change = on_change
        self._current = current
        self._chips: dict = {}

        frame = tk.Frame(parent, bg=bg)
        frame.pack(side="right", padx=(8, 0))

        for code, label, available in options:
            chip = tk.Label(
                frame, text=label,
                font=(_BODY, 9, "bold"),
                padx=12, pady=3,
                cursor="hand2" if available else "arrow",
                relief="flat",
            )
            chip.pack(side="left", padx=3)
            self._chips[code] = chip
            if available:
                chip.bind("<Button-1>", lambda e, c=code: self._select(c))

        self._refresh()

    def _refresh(self):
        for code, chip in self._chips.items():
            if code == self._current:
                chip.config(bg=_ACCENT, fg="#000000")
            else:
                chip.config(bg=_BORDER, fg=_MUTED)

    def _select(self, code: str):
        self._current = code
        self._refresh()
        if self._on_change:
            self._on_change(code)

    def get(self) -> str:
        return self._current


# ── Alert sensitivity chips ───────────────────────────────────────────────────

class _SensitivityChips:
    """Low / Normal / High chips for alert sensitivity."""
    OPTIONS = [("low", "Low"), ("normal", "Normal"), ("high", "High")]
    _COLORS  = {"low": "#3b82f6", "normal": "#f59e0b", "high": "#ef4444"}

    def __init__(self, parent: tk.Widget, current: str, on_change=None,
                 bg: str = _PANEL, options=None):
        self._on_change = on_change
        self._current   = current
        self._chips: dict = {}

        frame = tk.Frame(parent, bg=bg)
        frame.pack(side="right", padx=(8, 0))

        for val, lbl in (options if options is not None else self.OPTIONS):
            chip = tk.Label(
                frame, text=lbl,
                font=(_BODY, 8, "bold"),
                padx=9, pady=2, cursor="hand2", relief="flat",
            )
            chip.pack(side="left", padx=2)
            self._chips[val] = chip
            chip.bind("<Button-1>", lambda e, v=val: self._select(v))

        self._refresh()

    def _refresh(self):
        for val, chip in self._chips.items():
            if val == self._current:
                col = self._COLORS.get(val, _ACCENT)
                chip.config(bg=col, fg="#ffffff")
            else:
                chip.config(bg=_BORDER, fg=_MUTED)

    def _select(self, val: str):
        self._current = val
        self._refresh()
        if self._on_change:
            self._on_change(val)

    def get(self) -> str:
        return self._current


# ── Turbo threshold chips ─────────────────────────────────────────────────────

class _ThresholdChips:
    """3/5/10 MIN chips for TURBO idle threshold."""
    OPTIONS = [(180, "3 min"), (300, "5 min"), (600, "10 min")]

    def __init__(self, parent: tk.Widget, current: int, on_change=None):
        self._on_change = on_change
        self._current = current
        self._chips: dict = {}

        frame = tk.Frame(parent, bg=_PANEL)
        frame.pack(side="right", padx=(8, 0))

        for val, lbl in self.OPTIONS:
            chip = tk.Label(
                frame, text=lbl,
                font=(_BODY, 9, "bold"),
                padx=10, pady=3, cursor="hand2", relief="flat",
            )
            chip.pack(side="left", padx=3)
            self._chips[val] = chip
            chip.bind("<Button-1>", lambda e, v=val: self._select(v))

        self._refresh()

    def _refresh(self):
        for val, chip in self._chips.items():
            if val == self._current:
                chip.config(bg="#7c3aed", fg="#ffffff")
            else:
                chip.config(bg=_BORDER, fg=_MUTED)

    def _select(self, val: int):
        self._current = val
        self._refresh()
        if self._on_change:
            self._on_change(val)

    def get(self) -> int:
        return self._current


# ── Main settings page ────────────────────────────────────────────────────────

class SettingsPage:
    """
    Two-column compact settings page built inside a scrollable tk.Frame.
    Attach via:  page.frame  -> place/pack in parent.
    show_header=False when used inside an overlay that already has a title.
    app=None  - pass the main window to enable live sidebar auto-hide wiring.
    """

    def __init__(self, parent: tk.Widget, show_header: bool = True, app=None):
        self._settings    = _load_settings()
        self._show_header = show_header
        self._app         = app          # main window reference (optional)

        outer = tk.Frame(parent, bg=_BG)
        self.frame = outer

        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(outer, bg=_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(
            outer, orient="vertical", command=canvas.yview,
            bg=_BG, troughcolor="#0d1018", activebackground=_BORDER, width=6,
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._scroll_frame = tk.Frame(canvas, bg=_BG)
        self._win_id = canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")

        def _on_content(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas(e):
            canvas.itemconfig(self._win_id, width=e.width)
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_mousewheel(e):
            try:
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                pass

        self._scroll_frame.bind("<Configure>", _on_content)
        canvas.bind("<Configure>", _on_canvas)

        def _on_map(e=None):
            outer.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            if canvas.winfo_width() > 1:
                canvas.itemconfig(self._win_id, width=canvas.winfo_width())

        outer.bind("<Map>", lambda e: outer.after(20, _on_map))
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._build(self._scroll_frame)

    # ── Language-change rebuild ───────────────────────────────────────────────

    def _rebuild(self) -> None:
        """Destroy all settings content and rebuild in the new language."""
        try:
            if not self._scroll_frame.winfo_exists():
                return
        except Exception:
            return
        # Destroy all child widgets inside the scroll frame
        for child in self._scroll_frame.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass
        # Reload settings (language may have changed)
        self._settings = _load_settings()
        # Rebuild content
        self._build(self._scroll_frame)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self, parent: tk.Widget):
        # ── Page header ───────────────────────────────────────────────────────
        if self._show_header:
            header = tk.Frame(parent, bg="#0a0d13")
            header.pack(fill="x")
            tk.Label(
                header, text=_t("settings.page_title"),
                font=(_BODY, 15, "bold"),
                bg="#0a0d13", fg=_TEXT, anchor="w", padx=18, pady=10,
            ).pack(side="left")
            tk.Label(
                header, text=_t("settings.page_subtitle"),
                font=(_BODY, 8), bg="#0a0d13", fg=_MUTED, anchor="e", padx=16,
            ).pack(side="right", pady=10)
        else:
            tk.Frame(parent, bg=_BG, height=6).pack()

        tk.Frame(parent, bg=_BORDER, height=1).pack(fill="x")

        # ── Two-column body ───────────────────────────────────────────────────
        body = tk.Frame(parent, bg=_BG)
        body.pack(fill="x")
        # Left column takes ~58 %, right (hck_GPT + Notifications) ~42 % - ~20 % narrower
        body.columnconfigure(0, weight=7)
        body.columnconfigure(1, weight=5)

        left = tk.Frame(body, bg=_BG)
        left.grid(row=0, column=0, sticky="new", padx=(10, 5), pady=8)

        right = tk.Frame(body, bg=_BG)
        right.grid(row=0, column=1, sticky="new", padx=(8, 10), pady=8)

        # Left column: Language · PC WORKMAN GENERAL · TURBO
        self._build_language(left)
        self._build_pc_general(left)
        self._build_turbo(left)

        # Right column: hck_GPT (highlighted) · Notifications
        self._build_hck_gpt(right)
        self._build_notifications(right)

        # ── Footer: Data & Privacy | About - side by side ────────────────────
        footer = tk.Frame(parent, bg=_BG)
        footer.pack(fill="x", padx=12, pady=(0, 8))
        footer.columnconfigure(0, weight=1, uniform="foot")
        footer.columnconfigure(1, weight=1, uniform="foot")

        dp_col = tk.Frame(footer, bg=_BG)
        dp_col.grid(row=0, column=0, sticky="new", padx=(0, 4))

        ab_col = tk.Frame(footer, bg=_BG)
        ab_col.grid(row=0, column=1, sticky="new", padx=(4, 0))

        self._build_data_privacy(dp_col)
        self._build_about(ab_col)

        tk.Frame(parent, bg=_BG, height=20).pack()

    # ── Language ──────────────────────────────────────────────────────────────

    # ── Palette constants reused from _build_hck_gpt Ollama row ─────────────────
    _LANG_OUTER  = "#2e1065"   # vivid dark violet border
    _LANG_BG     = "#0f0a28"   # deep purple-black card bg
    _LANG_BAR1   = "#4f46e5"   # indigo top bar
    _LANG_BAR2   = "#7c3aed"   # violet second bar
    _LANG_TITLE  = "#a5b4fc"   # periwinkle title text
    _LANG_NOTICE = "#6366f1"   # notice muted

    def _build_language(self, parent: tk.Widget):
        # Section header - keep accent2 (neon blue) to match its identity
        _section_header(parent, _t("settings.section.language"), accent=_ACCENT2)

        # Prefer the live i18n state (may differ from saved JSON if changed this session)
        current_lang = _i18n_get_lang() if _HAS_I18N else self._settings.get("language", "en")

        def _on_lang_change(code):
            self._settings["language"] = code
            _save_settings(self._settings)
            _i18n_set_lang(code)   # update centralized i18n (fires nav rebuild etc.)
            # Rebuild this settings page after a short delay so i18n is settled
            try:
                self._scroll_frame.after(60, self._rebuild)
            except Exception:
                pass

        # ── Styled card matching "Switch CORE AI to Ollama" ───────────────────
        outer = tk.Frame(parent, bg=self._LANG_OUTER)
        outer.pack(fill="x")

        card = tk.Frame(outer, bg=self._LANG_BG)
        card.pack(fill="x", padx=1, pady=1)

        # Dual top bars: indigo + violet
        tk.Frame(card, bg=self._LANG_BAR1, height=1).pack(fill="x")
        tk.Frame(card, bg=self._LANG_BAR2, height=1).pack(fill="x")

        row = tk.Frame(card, bg=self._LANG_BG)
        row.pack(fill="x", padx=12, pady=(7, 7))

        # Left: single-line label only (no sublabel)
        tk.Label(
            row, text=_t("settings.language.label"),
            font=(_BODY, 9, "bold"),
            bg=self._LANG_BG, fg=self._LANG_TITLE, anchor="w",
        ).pack(side="left", fill="x", expand=True)

        # Right: language chip selector (bg matches card)
        self._lang_sel = _LangSelector(
            row, current_lang,
            [("en", "EN", True), ("pl", "PL", True)],
            on_change=_on_lang_change,
            bg=self._LANG_BG,
        )

        # Subtle notice at bottom
        note_row = tk.Frame(card, bg=self._LANG_BG)
        note_row.pack(fill="x", padx=12, pady=(0, 6))
        tk.Frame(note_row, bg="#2e1065", height=1).pack(fill="x", pady=(0, 4))
        tk.Label(
            note_row,
            text=_t("settings.language.notice"),
            font=(_BODY, 7),
            bg=self._LANG_BG, fg=self._LANG_NOTICE,
            anchor="w",
        ).pack(anchor="w")

    # ── PC WORKMAN - GENERAL (replaces Appearance) ────────────────────────────

    def _build_pc_general(self, parent: tk.Widget):
        _gen_section_header(parent)
        card = _gen_card(parent)

        BG = _GEN_PANEL
        BD = _GEN_SEP

        # ── 1. Anonymous telemetry (ON by default this release) - INFO + TURN ──
        _net_box = {}

        def _kick_send():
            """Fire one telemetry send right now (off-thread) so enabling it gives
            instant confirmation instead of waiting for the next app start."""
            import threading as _th

            def _go():
                try:
                    from core.telemetry import send as _s
                    _s("")
                except Exception:
                    pass

            _th.Thread(target=_go, daemon=True, name="telemetry-now").start()

        def _on_quick_toggle(v):
            from core import network as _net
            _net.set_network(v, v)   # ON = allowed + telemetry · OFF = full offline
            if v:
                _kick_send()

        def _make_info_btn(parent, compact=False):
            """INFO chip that opens the 'what PC Workman collects' presentation.
            Available PERMANENTLY - before AND after the first TURN."""
            info = tk.Label(parent, text=("ⓘ INFO" if compact else "INFO"),
                            font=(_BODY, 8, "bold"), bg="#241a3a", fg="#c4b5fd",
                            padx=(10 if compact else 16), pady=(4 if compact else 6),
                            cursor="hand2")
            info.bind("<Button-1>", lambda e: _net_dialog())
            info.bind("<Enter>", lambda e: info.config(bg="#2f2150"))
            info.bind("<Leave>", lambda e: info.config(bg="#241a3a"))
            return info

        def _render_net_widget():
            box = _net_box.get("c")
            try:
                if not box or not box.winfo_exists():
                    return
            except Exception:
                return
            for w in box.winfo_children():
                w.destroy()
            from core import network as _net
            if _net.telemetry_touched():
                # After the first TURN: ON/OFF toggle PLUS a permanent INFO button,
                # so the resource/data dialog is always one click away.
                _ToggleSquare(box, _net.telemetry_enabled(), _on_quick_toggle, bg=BG)
                _make_info_btn(box, compact=True).pack(side="right", padx=(0, 8))
            else:
                # Before the first TURN: a prominent INFO button only.
                _make_info_btn(box, compact=False).pack(side="right")

        def _net_dialog():
            from core import network as _net
            try:
                from utils.i18n import get_lang
                _pl = get_lang() == "pl"
            except Exception:
                _pl = False

            def L(en, plt):
                return plt if _pl else en

            import json as _json
            try:
                from core import telemetry
                payload_txt = _json.dumps(telemetry.build_payload(""), indent=2,
                                          ensure_ascii=False)
            except Exception:
                payload_txt = "{}"

            dlg = tk.Toplevel(card)
            dlg.title(L("Anonymous telemetry", "Anonimowa telemetria"))
            dlg.configure(bg="#0a0e14")
            dlg.resizable(False, False)
            try:
                dlg.transient(card.winfo_toplevel())
                dlg.grab_set()
            except Exception:
                pass

            wrap = tk.Frame(dlg, bg="#0a0e14", padx=20, pady=16)
            wrap.pack(fill="both", expand=True)
            tk.Label(wrap, text="📊 " + L("Anonymous telemetry", "Anonimowa telemetria"),
                     font=(_HDR, 14), bg="#0a0e14", fg="#f3e8ff",
                     anchor="w").pack(fill="x")
            tk.Label(wrap, text=L(
                "PC Workman shares an anonymous snapshot that helps improve the app. "
                "Turn it here anytime, OFF means zero "
                "network traffic.",
                "PC Workman wysyła anonimowy zrzut, który pomaga ulepszać program." \
                "Włączysz tutaj w każdej chwili, a WYŁ oznacza "
                "zero ruchu sieciowego."),
                font=(_BODY, 9), bg="#0a0e14", fg="#9ca3af", anchor="w",
                justify="left", wraplength=470).pack(fill="x", pady=(8, 12))

            for en, plt in [
                ("Anonymous - a random ID, never your name, machine or IP.",
                 "Anonimowo - losowy identyfikator, nigdy nazwa, maszyna ani IP."),
                ("Minimal - hardware models, OS and session time only. No files, no "
                 "process names, no content.",
                 "Minimalnie - tylko modele sprzętu, OS i czas sesji. Żadnych plików, "
                 "nazw procesów ani treści."),
                ("Verifiable - the exact data is shown below, the code is open-source, "
                 "and OFF means zero traffic (check with a firewall).",
                 "Sprawdzalnie - dokładne dane masz niżej, kod jest open-source, a WYŁ "
                 "= zero ruchu (sprawdź firewallem)."),
                ("Reversible - turn it off anytime.",
                 "Odwracalnie - wyłączysz w każdej chwili."),
            ]:
                rf = tk.Frame(wrap, bg="#0a0e14")
                rf.pack(fill="x", pady=1)
                tk.Label(rf, text="✓", font=(_BODY, 9, "bold"), bg="#0a0e14",
                         fg="#22c55e").pack(side="left", anchor="n", padx=(0, 6))
                tk.Label(rf, text=L(en, plt), font=(_BODY, 8), bg="#0a0e14",
                         fg="#cbd5e1", anchor="w", justify="left",
                         wraplength=440).pack(side="left", fill="x")

            tk.Label(wrap, text=L("Exactly what is sent:",
                     "Dokładnie to, co jest wysyłane:"),
                     font=(_BODY, 8, "bold"), bg="#0a0e14", fg="#6b7280",
                     anchor="w").pack(fill="x", pady=(12, 4))
            box = tk.Text(wrap, height=11, width=58, font=(_MONO, 8), bg="#06080d",
                          fg="#86efac", bd=0, padx=8, pady=6, wrap="none")
            box.insert("1.0", payload_txt)
            box.config(state="disabled")
            box.pack(fill="x")

            btns = tk.Frame(wrap, bg="#0a0e14")
            btns.pack(fill="x", pady=(14, 0))
            close = tk.Label(btns, text=L("Close", "Zamknij"),
                             font=(_BODY, 9, "bold"), bg="#1a1f2e", fg="#9ca3af",
                             padx=16, pady=8, cursor="hand2")
            close.pack(side="left")
            close.bind("<Button-1>", lambda e: dlg.destroy())

            turn = tk.Label(btns, font=(_BODY, 10, "bold"), padx=22, pady=8,
                            cursor="hand2")
            turn.pack(side="right")

            def _paint_turn():
                if not _net.telemetry_touched():
                    turn.config(text="TURN", bg="#7c3aed", fg="#ffffff")
                elif _net.telemetry_enabled():
                    turn.config(text="ON", bg="#166534", fg="#86efac")
                else:
                    turn.config(text="OFF", bg="#3a1010", fg="#fca5a5")

            def _do_turn(_=None):
                new = not _net.telemetry_enabled()
                _net.set_network(new, new)
                _net.set_touched()
                _paint_turn()
                _render_net_widget()
                if new:
                    _kick_send()

            turn.bind("<Button-1>", _do_turn)
            _paint_turn()

            dlg.update_idletasks()
            try:
                top = card.winfo_toplevel()
                x = top.winfo_rootx() + (top.winfo_width() - dlg.winfo_width()) // 2
                y = top.winfo_rooty() + (top.winfo_height() - dlg.winfo_height()) // 2
                dlg.geometry(f"+{max(x, 0)}+{max(y, 0)}")
            except Exception:
                pass
            dlg.wait_window()

        def _build_net_widget(r):
            c = tk.Frame(r, bg=BG)
            c.pack(side="right")
            _net_box["c"] = c
            _render_net_widget()
            return c

        _setting_row(
            card,
            _t("settings.general.internet_label"),
            _t("settings.general.internet_desc"),
            right_widget_factory=_build_net_widget,
            separator=True,
            bg=BG, border=BD,
        )

        # ── 2. Restart Turbo Settings (RESET button) ──────────────────────────
        def _build_reset_btn(row):
            btn = tk.Label(
                row, text=_t("settings.general.reset_btn"),
                font=(_MONO, 8, "bold"),
                bg="#3b0014", fg="#f43f5e",
                padx=10, pady=5, cursor="hand2",
                relief="flat",
                highlightthickness=1,
                highlightbackground="#be123c",
            )
            btn.pack(side="right", padx=(8, 0))

            def _do_reset():
                for k in ("turbo_idle_seconds", "turbo_auto_power_plan",
                          "turbo_restore_on_exit"):
                    self._settings.pop(k, None)
                _save_settings(self._settings)
                btn.config(text=_t("settings.general.reset_done"), fg="#10b981",
                           highlightbackground="#10b981")
                btn.after(2200, lambda: btn.config(
                    text=_t("settings.general.reset_btn"), fg="#f43f5e",
                    highlightbackground="#be123c",
                ))

            btn.bind("<Button-1>", lambda e: _do_reset())
            btn.bind("<Enter>",    lambda e: btn.config(bg="#5c001e"))
            btn.bind("<Leave>",    lambda e: btn.config(bg="#3b0014"))

        _setting_row(
            card,
            _t("settings.general.reset_label"),
            _t("settings.general.reset_desc"),
            right_widget_factory=_build_reset_btn,
            separator=True,
            bg=BG, border=BD,
        )

        # ── 3. Launch at Windows startup ──────────────────────────────────────
        at_startup = self._settings.get("launch_at_startup", False)

        def _on_startup(v):
            self._settings["launch_at_startup"] = v
            _save_settings(self._settings)
            try:
                import winreg, sys
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                                     winreg.KEY_ALL_ACCESS)
                if v:
                    exe    = sys.executable
                    script = os.path.abspath(sys.argv[0])
                    winreg.SetValueEx(reg, "PC_Workman_HCK", 0, winreg.REG_SZ,
                                      f'"{exe}" "{script}"')
                else:
                    try:
                        winreg.DeleteValue(reg, "PC_Workman_HCK")
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(reg)
            except Exception as exc:
                print(f"[Settings] Startup registry error: {exc}")

        _setting_row(
            card,
            _t("settings.general.startup_label"),
            _t("settings.general.startup_desc"),
            right_widget_factory=lambda r: _ToggleSquare(r, at_startup, _on_startup, bg=BG),
            separator=True,
            bg=BG, border=BD,
        )

        # ── 3a. Run as administrator (asks via UAC at next launch) ────────────
        as_admin = self._settings.get("run_as_admin", False)

        def _on_admin(v):
            self._settings["run_as_admin"] = v
            _save_settings(self._settings)

        _setting_row(
            card,
            _t("settings.general.admin_label", default="Uruchamiaj jako administrator"),
            _t("settings.general.admin_desc",
               default="Przy starcie poproś o podniesienie uprawnień (UAC). "
                       "Potrzebne dla wpisów HKLM, niektórych usług i planów zasilania. "
                       "Nie dotyczy instalacji z Microsoft Store."),
            right_widget_factory=lambda r: _ToggleSquare(r, as_admin, _on_admin, bg=BG),
            separator=True,
            bg=BG, border=BD,
        )

        # ── 3b. Create desktop shortcut ───────────────────────────────────────
        # Store/MSIX installs live in WindowsApps where users can't right-click
        # -> "create shortcut", so we do it for them. Works for the ZIP .exe and
        # dev runs too. MSIX needs the AUMID link (shell:AppsFolder\PFN!AppId).
        def _create_desktop_shortcut() -> bool:
            import sys, subprocess
            # Real Desktop path (handles OneDrive-redirected desktops)
            desktop = ""
            try:
                import winreg as _wr
                k = _wr.OpenKey(_wr.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion"
                                r"\Explorer\User Shell Folders")
                desktop = os.path.expandvars(_wr.QueryValueEx(k, "Desktop")[0])
                _wr.CloseKey(k)
            except Exception:
                pass
            if not desktop or not os.path.isdir(desktop):
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")

            lnk = os.path.join(desktop, "PC Workman.lnk")
            exe = sys.executable
            if "windowsapps" in exe.lower():
                # Microsoft Store install - launch via the app's AUMID
                target = os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                                      "explorer.exe")
                args = (r"shell:AppsFolder\MarcinHCKFirmuga.PCWorkman"
                        r"_4hekbcs2ddfbc!PCWorkmanHCK")
            elif getattr(sys, "frozen", False):
                target, args = exe, ""                      # portable .exe
            else:
                target = exe                                # dev: python + script
                args = f'"{os.path.abspath(sys.argv[0])}"'

            def _q(s):   # single-quote for PowerShell ('' escapes ')
                return s.replace("'", "''")

            ps = (f"$w=New-Object -ComObject WScript.Shell;"
                  f"$s=$w.CreateShortcut('{_q(lnk)}');"
                  f"$s.TargetPath='{_q(target)}';"
                  + (f"$s.Arguments='{_q(args)}';" if args else "")
                  + f"$s.IconLocation='{_q(exe)},0';$s.Save()")
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                    capture_output=True, timeout=20,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                return r.returncode == 0 and os.path.isfile(lnk)
            except Exception:
                return False

        def _build_shortcut_btn(row):
            btn = tk.Label(
                row, text=_t("settings.general.shortcut_btn", default="Utwórz"),
                font=(_MONO, 8, "bold"),
                bg="#001a2e", fg="#38bdf8",
                padx=10, pady=5, cursor="hand2",
                relief="flat", highlightthickness=1,
                highlightbackground="#0369a1",
            )
            btn.pack(side="right", padx=(8, 0))

            def _do(_=None):
                ok = _create_desktop_shortcut()
                if ok:
                    btn.config(text=_t("settings.general.shortcut_done",
                                       default="✓ Skrót na pulpicie"),
                               fg="#10b981", highlightbackground="#10b981")
                else:
                    btn.config(text=_t("settings.general.shortcut_fail",
                                       default="Nie udało się"),
                               fg="#f43f5e", highlightbackground="#be123c")
                btn.after(2600, lambda: btn.config(
                    text=_t("settings.general.shortcut_btn", default="Utwórz"),
                    fg="#38bdf8", highlightbackground="#0369a1"))

            btn.bind("<Button-1>", _do)
            return btn

        _setting_row(
            card,
            _t("settings.general.shortcut_label", default="Skrót na pulpicie"),
            _t("settings.general.shortcut_desc",
               default="Utwórz klasyczny skrót do PC Workmana na pulpicie "
                       "(działa też dla instalacji z Microsoft Store)."),
            right_widget_factory=_build_shortcut_btn,
            separator=True,
            bg=BG, border=BD,
        )

        # ── 4. Auto-hide sidebar ──────────────────────────────────────────────
        auto_hide = self._settings.get("sidebar_auto_hide", False)

        def _on_auto_hide(v):
            self._settings["sidebar_auto_hide"] = v
            _save_settings(self._settings)
            # Wire live to sidebar if app reference is available
            sidebar = getattr(self._app, "sidebar", None)
            if sidebar and hasattr(sidebar, "set_auto_hide"):
                sidebar.set_auto_hide(v)

        _setting_row(
            card,
            _t("settings.general.autohide_label"),
            _t("settings.general.autohide_desc"),
            right_widget_factory=lambda r: _ToggleSquare(r, auto_hide, _on_auto_hide, bg=BG),
            separator=True,
            bg=BG, border=BD,
        )

        # ── 5. Temperature unit ───────────────────────────────────────────────
        temp_unit = self._settings.get("temp_unit", "C")

        def _on_temp_unit(code):
            self._settings["temp_unit"] = code
            _save_settings(self._settings)

        def _temp_right(row):
            _LangSelector(row, temp_unit,
                          [("C", "°C", True), ("F", "°F", True)],
                          on_change=_on_temp_unit)

        _setting_row(
            card,
            _t("settings.general.temp_unit_label"),
            _t("settings.general.temp_unit_desc"),
            right_widget_factory=_temp_right,
            separator=True,
            bg=BG, border=BD,
        )

        # ── 6. Debug Control Center (bordeaux special row) ────────────────────
        debug_outer = tk.Frame(card, bg="#1a0008")   # bordeaux-tinted outer strip
        debug_outer.pack(fill="x")

        # Left bordeaux accent bar
        tk.Frame(debug_outer, bg="#be123c", width=3).pack(side="left", fill="y")

        debug_inner = tk.Frame(debug_outer, bg="#140006")
        debug_inner.pack(fill="both", expand=True)

        debug_row = tk.Frame(debug_inner, bg="#140006")
        debug_row.pack(fill="x", padx=12, pady=6)

        left_d = tk.Frame(debug_row, bg="#140006")
        left_d.pack(side="left", fill="both", expand=True)

        tk.Label(
            left_d, text=_t("settings.general.debug_label"),
            font=(_BODY, 9, "bold"),
            bg="#140006", fg="#fca5a5", anchor="w",
        ).pack(anchor="w")
        tk.Label(
            left_d, text=_t("settings.general.debug_desc"),
            font=(_BODY, 7),
            bg="#140006", fg="#a84a5e", anchor="w",
        ).pack(anchor="w")

        btn_dbg = tk.Label(
            debug_row, text=_t("settings.general.debug_btn"),
            font=(_BODY, 8, "bold"),
            bg="#3b0000", fg="#ef4444",
            padx=10, pady=5, cursor="hand2",
            relief="flat",
            highlightthickness=1, highlightbackground="#7f1d1d",
        )
        btn_dbg.pack(side="right")
        btn_dbg.bind("<Button-1>", lambda e: self._show_debug_password(
            btn_dbg.winfo_toplevel()))
        btn_dbg.bind("<Enter>", lambda e: btn_dbg.config(bg="#5c0000"))
        btn_dbg.bind("<Leave>", lambda e: btn_dbg.config(bg="#3b0000"))

    # ── TURBO ─────────────────────────────────────────────────────────────────

    def _build_turbo(self, parent: tk.Widget):
        _section_header(parent, _t("settings.section.turbo"), accent=_WARN)
        card = _card(parent)

        idle_s = self._settings.get("turbo_idle_seconds", 300)

        def _on_threshold(val):
            self._settings["turbo_idle_seconds"] = val
            _save_settings(self._settings)
            try:
                from core.turbo_manager import turbo_processes
                turbo_processes._idle_seconds = val
            except Exception:
                pass

        _setting_row(card, _t("settings.turbo.threshold_label"),
                     _t("settings.turbo.threshold_desc"),
                     right_widget_factory=lambda r: _ThresholdChips(r, idle_s, _on_threshold))

        auto_pp = self._settings.get("turbo_auto_power_plan", True)

        def _on_auto_pp(v):
            self._settings["turbo_auto_power_plan"] = v
            _save_settings(self._settings)

        _setting_row(card, _t("settings.turbo.power_plan_label"),
                     _t("settings.turbo.power_plan_desc"),
                     right_widget_factory=lambda r: _TogglePill(r, auto_pp, _on_auto_pp))

        restore_svcs = self._settings.get("turbo_restore_on_exit", True)

        def _on_restore(v):
            self._settings["turbo_restore_on_exit"] = v
            _save_settings(self._settings)

        _setting_row(card, _t("settings.turbo.restore_label"),
                     _t("settings.turbo.restore_desc"),
                     right_widget_factory=lambda r: _TogglePill(r, restore_svcs, _on_restore),
                     separator=False)

    # ── hck_GPT (AI section, indigo theme) ───────────────────────────────────

    def _build_hck_gpt(self, parent: tk.Widget):
        _ai_section_header(parent)
        card = _ai_card(parent)

        # ── Special: Switch CORE AI to Ollama (locked, featured row) ─────────
        ollama_outer = tk.Frame(card, bg="#2e1065")   # vivid violet accent border
        ollama_outer.pack(fill="x", padx=1, pady=(0, 0))

        ollama_card = tk.Frame(ollama_outer, bg="#0f0a28")
        ollama_card.pack(fill="x", padx=1, pady=1)

        # Dual top bar: indigo + fuchsia
        tk.Frame(ollama_card, bg="#4f46e5", height=1).pack(fill="x")
        tk.Frame(ollama_card, bg="#7c3aed", height=1).pack(fill="x")

        ollama_row = tk.Frame(ollama_card, bg="#0f0a28")
        ollama_row.pack(fill="x", padx=12, pady=(8, 8))

        left_o = tk.Frame(ollama_row, bg="#0f0a28")
        left_o.pack(side="left", fill="both", expand=True)

        # Title + badge
        title_row = tk.Frame(left_o, bg="#0f0a28")
        title_row.pack(anchor="w")

        tk.Label(
            title_row, text=_t("settings.hck_gpt.ollama_label"),
            font=(_BODY, 9, "bold"),
            bg="#0f0a28", fg="#a5b4fc", anchor="w",
        ).pack(side="left")

        tk.Label(
            title_row, text=f" {_t('settings.hck_gpt.ollama_badge_local')} ",
            font=(_BODY, 7, "bold"),
            bg="#1e40af", fg="#bfdbfe",
            padx=5, pady=1,
        ).pack(side="left", padx=(7, 0))

        tk.Label(
            title_row, text=f" 🔒 {_t('settings.hck_gpt.ollama_badge_locked')} ",
            font=(_BODY, 7, "bold"),
            bg="#1f2937", fg="#8593a8",
            padx=5, pady=1,
        ).pack(side="left", padx=(4, 0))

        tk.Label(
            left_o,
            text=_t("settings.hck_gpt.ollama_desc"),
            font=(_BODY, 7),
            bg="#0f0a28", fg="#6366f1",
            anchor="w", justify="left",
            wraplength=220,
        ).pack(anchor="w", pady=(4, 0))

        _LockedToggle(ollama_row, bg="#0f0a28")

        # Thin separator after Ollama row
        tk.Frame(card, bg=_AI_BD, height=1).pack(fill="x", padx=10, pady=(4, 0))

        # ── Regular AI rows ───────────────────────────────────────────────────
        def _ai_row(lbl, sub, key, default, last=False):
            val = self._settings.get(key, default)

            def _on_change(v):
                self._settings[key] = v
                _save_settings(self._settings)

            _setting_row(
                card, lbl, sub,
                right_widget_factory=lambda r: _ToggleSquare(r, val, _on_change, bg=_AI_BG),
                separator=not last,
                bg=_AI_BG, border=_AI_BD,
            )

        _ai_row(
            _t("settings.hck_gpt.proactive_label"),
            _t("settings.hck_gpt.proactive_desc"),
            "gpt_proactive_alerts", True,
        )
        _ai_row(
            _t("settings.hck_gpt.morning_label"),
            _t("settings.hck_gpt.morning_desc"),
            "gpt_morning_brief", True,
        )
        _ai_row(
            _t("settings.hck_gpt.spike_label"),
            _t("settings.hck_gpt.spike_desc"),
            "gpt_process_spike", True,
        )
        _ai_row(
            _t("settings.hck_gpt.digest_label"),
            _t("settings.hck_gpt.digest_desc"),
            "gpt_digest", True,
            last=True,
        )

    # ── Notifications ─────────────────────────────────────────────────────────

    def _build_notifications(self, parent: tk.Widget):
        _notif_section_header(parent)
        card = _notif_card(parent)

        sens_val = self._settings.get("alert_sensitivity", "normal")

        def _on_sens(v):
            self._settings["alert_sensitivity"] = v
            _save_settings(self._settings)

        _setting_row(
            card, _t("settings.notifications.sensitivity_label"),
            _t("settings.notifications.sensitivity_desc"),
            right_widget_factory=lambda r: _SensitivityChips(
                r, sens_val, _on_sens, bg=_NOTIF_BG,
                options=[
                    ("low",    _t("settings.notifications.sens_low")),
                    ("normal", _t("settings.notifications.sens_normal")),
                    ("high",   _t("settings.notifications.sens_high")),
                ],
            ),
            separator=True,
            bg=_NOTIF_BG, border=_NOTIF_BD,
        )

        rows = [
            ("toast_temp_spike",     _t("settings.notifications.temp_spike_label"),  _t("settings.notifications.temp_spike_desc"), True),
            ("toast_ram_pressure",   _t("settings.notifications.ram_label"),         _t("settings.notifications.ram_desc"),        True),
            ("toast_weekly_recap",   _t("settings.notifications.weekly_label"),      _t("settings.notifications.weekly_desc"),     True),
            ("toast_new_process",    _t("settings.notifications.new_proc_label"),    _t("settings.notifications.new_proc_desc"),   False),
            ("toast_gaming_recap",   _t("settings.notifications.gaming_label"),      _t("settings.notifications.gaming_desc"),     True),
            ("gaming_launch_toast",  _t("settings.notifications.gaming_launch_label", default="Gaming launch reminders"),
                                     _t("settings.notifications.gaming_launch_desc",  default='Subtle 2s tip when a game starts - "Good luck!", custom messages per game'),
                                     True),
        ]

        for i, (key, label, sub, default) in enumerate(rows):
            val     = self._settings.get(key, default)
            is_last = (i == len(rows) - 1)

            def _make_handler(k):
                def handler(v):
                    self._settings[k] = v
                    _save_settings(self._settings)
                return handler

            def _make_right(v, cb, bg=_NOTIF_BG):
                def factory(row):
                    _ToggleSquare(row, v, on_change=cb, bg=bg)
                return factory

            _setting_row(card, label, sub,
                         right_widget_factory=_make_right(val, _make_handler(key)),
                         separator=not is_last,
                         bg=_NOTIF_BG, border=_NOTIF_BD)

    # ── Data & Privacy ────────────────────────────────────────────────────────

    def _build_data_privacy(self, parent: tk.Widget):
        _section_header(parent, _t("settings.section.data_privacy"), accent="#f87171")
        card = _card(parent)

        _setting_row(card, _t("settings.data_privacy.retention_label"),
                     _t("settings.data_privacy.retention_desc"),
                     separator=True)

        def _export_right(row):
            btn = tk.Label(
                row, text=_t("settings.data_privacy.export_btn"),
                font=(_BODY, 8, "bold"),
                bg=_ACCENT2, fg="#ffffff",
                padx=10, pady=3, cursor="hand2", relief="flat",
            )
            btn.pack(side="right", padx=(8, 0))
            btn.bind("<Button-1>", lambda e: self._export_data())

        _setting_row(card, _t("settings.data_privacy.export_label"),
                     _t("settings.data_privacy.export_desc"),
                     right_widget_factory=_export_right)

        def _reset_right(row):
            btn = tk.Label(
                row, text=_t("settings.data_privacy.reset_btn"),
                font=(_BODY, 8, "bold"),
                bg=_DANGER, fg="#ffffff",
                padx=10, pady=3, cursor="hand2", relief="flat",
            )
            btn.pack(side="right", padx=(8, 0))
            btn.bind("<Button-1>", lambda e: self._confirm_reset(row.winfo_toplevel()))

        _setting_row(card, _t("settings.data_privacy.reset_label"),
                     _t("settings.data_privacy.reset_desc"),
                     right_widget_factory=_reset_right, separator=False)

    # ── About ─────────────────────────────────────────────────────────────────

    def _build_about(self, parent: tk.Widget):
        _section_header(parent, _t("settings.section.about"), accent=_MUTED)
        card = _card(parent)

        _setting_row(card, _t("settings.about.app_label"), _t("settings.about.app_desc"))
        _setting_row(card, _t("settings.about.author_label"), _t("settings.about.author_desc"))

        def _gh_right(row):
            lbl = tk.Label(
                row, text=_t("settings.about.github_btn"),
                font=(_BODY, 8, "bold"),
                bg=_PANEL, fg=_ACCENT2,
                padx=0, cursor="hand2",
            )
            lbl.pack(side="right", padx=(8, 0))
            lbl.bind("<Button-1>", lambda e: self._open_github())

        _setting_row(card, _t("settings.about.source_label"),
                     _t("settings.about.source_desc"),
                     right_widget_factory=_gh_right, separator=False)

    # ── Debug password dialog ─────────────────────────────────────────────────

    def _show_debug_password(self, root: tk.Misc) -> None:
        """Debug Control Center - always denies access."""
        try:
            top = root.winfo_toplevel()
        except Exception:
            top = root

        dlg = tk.Toplevel(top)
        dlg.title(_t("settings.general.debug_dialog_title"))
        dlg.configure(bg="#0a0005")
        dlg.resizable(False, False)
        dlg.grab_set()

        W, H = 360, 220
        rx = top.winfo_rootx() + max(0, (top.winfo_width()  - W) // 2)
        ry = top.winfo_rooty() + max(0, (top.winfo_height() - H) // 2)
        dlg.geometry(f"{W}x{H}+{rx}+{ry}")

        # Header
        hdr = tk.Frame(dlg, bg="#1a0008")
        hdr.pack(fill="x")
        tk.Frame(hdr, bg="#be123c", height=2).pack(fill="x")
        tk.Label(
            hdr, text=f"🔐  {_t('settings.general.debug_dialog_title')}",
            font=(_BODY, 11, "bold"),
            bg="#1a0008", fg="#fca5a5",
            padx=20, pady=10,
        ).pack(anchor="w")

        body = tk.Frame(dlg, bg="#0a0005")
        body.pack(fill="both", expand=True, padx=20, pady=(10, 4))

        tk.Label(
            body, text=_t("settings.general.debug_dialog_prompt"),
            font=(_BODY, 9), bg="#0a0005", fg="#9ca3af",
        ).pack(anchor="w")

        entry = tk.Entry(
            body,
            font=(_MONO, 11),
            bg="#111827", fg="#f87171",
            insertbackground="#f87171",
            relief="flat",
            highlightthickness=1, highlightbackground="#450a0a",
            show="•", width=30,
        )
        entry.pack(anchor="w", pady=(4, 8), ipady=4)
        entry.focus_set()

        status_var = tk.StringVar(value="")
        status_lbl = tk.Label(
            body, textvariable=status_var,
            font=(_BODY, 8),
            bg="#0a0005", fg="#ef4444",
        )
        status_lbl.pack(anchor="w")

        def _try_unlock(_e=None):
            status_var.set(_t("settings.general.debug_denied"))
            entry.config(highlightbackground="#ef4444")
            entry.delete(0, "end")

        entry.bind("<Return>", _try_unlock)

        btn_row = tk.Frame(dlg, bg="#0a0005")
        btn_row.pack(side="bottom", fill="x", padx=20, pady=12)

        cancel = tk.Label(
            btn_row, text=_t("settings.general.debug_cancel"),
            font=(_BODY, 9, "bold"),
            bg="#1f2937", fg="#9ca3af",
            padx=14, pady=5, cursor="hand2",
        )
        cancel.pack(side="right", padx=(6, 0))
        cancel.bind("<Button-1>", lambda e: dlg.destroy())
        cancel.bind("<Enter>",    lambda e: cancel.config(bg="#374151"))
        cancel.bind("<Leave>",    lambda e: cancel.config(bg="#1f2937"))

        unlock = tk.Label(
            btn_row, text=_t("settings.general.debug_unlock"),
            font=(_BODY, 9, "bold"),
            bg="#450a0a", fg="#ef4444",
            padx=14, pady=5, cursor="hand2",
        )
        unlock.pack(side="right")
        unlock.bind("<Button-1>", _try_unlock)
        unlock.bind("<Enter>",    lambda e: unlock.config(bg="#5c0000"))
        unlock.bind("<Leave>",    lambda e: unlock.config(bg="#450a0a"))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _export_data(self):
        import tkinter.filedialog as fd
        import shutil

        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "logs",
        )
        dest = fd.askdirectory(title="Export logs to folder…")
        if dest:
            try:
                for fname in ("raw_usage.csv", "minute_avg.csv"):
                    src = os.path.join(data_dir, fname)
                    if os.path.exists(src):
                        shutil.copy2(src, dest)
            except Exception as exc:
                print(f"[Settings] Export error: {exc}")

    def _confirm_reset(self, root: tk.Tk):
        dlg = tk.Toplevel(root)
        dlg.title(_t("settings.data_privacy.confirm_title"))
        dlg.configure(bg="#0a0d13")
        dlg.resizable(False, False)
        dlg.grab_set()

        w, h = 360, 160
        dlg.geometry(f"{w}x{h}+{root.winfo_rootx() + 60}+{root.winfo_rooty() + 80}")

        tk.Label(dlg, text=_t("settings.data_privacy.confirm_question"),
                 font=(_BODY, 13, "bold"), bg="#0a0d13", fg=_TEXT,
                 padx=24, pady=18).pack(anchor="w")
        tk.Label(dlg, text=_t("settings.data_privacy.confirm_body"),
                 font=(_BODY, 9), bg="#0a0d13", fg=_MUTED,
                 wraplength=310, padx=24).pack(anchor="w")

        btn_row = tk.Frame(dlg, bg="#0a0d13")
        btn_row.pack(side="bottom", fill="x", padx=24, pady=16)

        tk.Label(btn_row, text=_t("common.cancel"), font=(_BODY, 10, "bold"),
                 bg=_BORDER, fg=_TEXT, padx=16, pady=6,
                 cursor="hand2").pack(side="right", padx=4)
        btn_row.winfo_children()[-1].bind("<Button-1>", lambda e: dlg.destroy())

        def _do_reset():
            self._reset_data()
            dlg.destroy()

        tk.Label(btn_row, text=_t("settings.data_privacy.reset_btn"), font=(_BODY, 10, "bold"),
                 bg=_DANGER, fg="#ffffff", padx=16, pady=6,
                 cursor="hand2").pack(side="right", padx=4)
        btn_row.winfo_children()[-1].bind("<Button-1>", lambda e: _do_reset())

    def _reset_data(self):
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        to_clear = [
            os.path.join(base, "data", "logs", "raw_usage.csv"),
            os.path.join(base, "data", "logs", "minute_avg.csv"),
            os.path.join(base, "data", "process_info", "process_statistics.json"),
        ]
        for path in to_clear:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        print("[Settings] Data reset complete.")

    def _open_github(self):
        import webbrowser
        webbrowser.open("https://github.com/HuckleR2003/PC_Workman_HCK")
