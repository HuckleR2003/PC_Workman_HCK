"""
ui/components/operator_drawer.py

The single shared "operator" drawer for queue + confirm actions.
Used by Startup Manager and Services Manager (and any future bulk operation) -
ONE component, no duplicated drawers.

How a page uses it
-------------------
    drawer = OperatorDrawer(
        page, grid_row=2,
        title="Zmiany do zatwierdzenia",
        on_confirm=_apply_changes,      # gets list[item]; does the real work
        on_change=_refresh_rows,        # optional: re-paint the page's rows
    )

    # in a row's click handler:
    drawer.toggle({"id": uid, "label": "OneDrive", "warn": False, "payload": entry})

    # query state for painting a row:
    drawer.is_queued(uid)

    # _apply_changes(items) does the work, then calls drawer.clear()

Visuals: bordeaux / hck_GPT style, queued items in a 2-column grid (~4 left +
4 right) that grows DOWNWARD as more are selected; right side = Zatwierdź / Wróć.
Always visible - empty state is a thin prompt bar, so it's a persistent operator.
"""
import math
import tkinter as tk

try:
    from utils.fonts import UI as _UIF
except Exception:
    _UIF = "Segoe UI"

try:
    from utils.i18n import t as _t
except Exception:
    def _t(key, default=None, **kw):
        return default if default is not None else key

# ── Palette (matches the original Startup drawer) ──────────────────────────────
_BG        = "#060408"     # near-black + subtle purple tint
_BORDEAU   = "#5a0e20"
_BORD_MID  = "#3d0a16"
_BORD_L    = "#c07090"
_TEXT      = "#cdd8e8"
_SUB       = "#8693a6"
_AMBER     = "#d97706"
_ITEM      = "#c8d8e8"

# ── Geometry ───────────────────────────────────────────────────────────────────
_EMPTY_H      = 30   # thin prompt bar when nothing is queued
_BANNER_H     = 44   # compact banner: Wróć · SZCZEGÓŁY (wide centre) · Zatwierdź
_MIN_EXPANDED = 170  # floor for the expanded detail panel
_MAX_EXPANDED = 460  # ceiling so the panel never eats the whole page


class OperatorDrawer:
    def __init__(self, parent, grid_row=None, *, on_confirm, on_change=None,
                 pack_side=None, title=None, empty_hint=None,
                 confirm_text=None, back_text=None):
        """Mount the drawer into *parent*.

        Geometry - pass exactly one:
            grid_row=N      -> placed with .grid(row=N, column=0, sticky="ew")
            pack_side="bottom" (or "top") -> placed with .pack(side=…, fill="x")
        Default (both None) -> .pack(side="bottom", fill="x").
        """
        self._on_confirm  = on_confirm
        self._on_change   = on_change
        self._title       = title        or _t("operator.title",   default="Zmiany do zatwierdzenia")
        self._empty_hint  = empty_hint   or _t("operator.empty",   default="Zaznacz elementy, aby dodać je do zatwierdzenia")
        self._confirm_txt = confirm_text or _t("operator.confirm", default="Zatwierdź")
        self._back_txt    = back_text    or _t("operator.back",    default="Wróć")
        self._details_txt = _t("operator.details", default="SZCZEGÓŁY")

        self._queue: list[dict] = []
        self._ids:   set        = set()
        self._expanded          = False   # SZCZEGÓŁY closed by default (save vertical space)

        self.outer = tk.Frame(parent, bg=_BG, height=_EMPTY_H)
        if grid_row is not None:
            self.outer.grid(row=grid_row, column=0, sticky="ew")
        else:
            self.outer.pack(side=(pack_side or "bottom"), fill="x")
        # Children use pack(); both propagations off so config(height=…) is honoured.
        self.outer.pack_propagate(False)
        self.outer.grid_propagate(False)
        self._render()

    # ── public API ─────────────────────────────────────────────────────────────
    def is_queued(self, item_id) -> bool:
        return item_id in self._ids

    def toggle(self, item: dict) -> None:
        """Add the item to the queue, or remove it if already queued."""
        iid = item["id"]
        if iid in self._ids:
            self._ids.discard(iid)
            self._queue[:] = [q for q in self._queue if q["id"] != iid]
        else:
            self._ids.add(iid)
            self._queue.append(item)
        self._render()
        if self._on_change:
            self._on_change()

    def items(self) -> list[dict]:
        return list(self._queue)

    def clear(self) -> None:
        self._queue.clear()
        self._ids.clear()
        self._render()
        if self._on_change:
            self._on_change()

    # ── rendering ────────────────────────────────────────────────────────────────
    def _toggle_details(self) -> None:
        self._expanded = not self._expanded
        self._render()

    def _hover(self, w, on_fg, off_fg):
        w.bind("<Enter>", lambda e: w.config(fg=on_fg))
        w.bind("<Leave>", lambda e: w.config(fg=off_fg))

    def _render(self) -> None:
        for w in self.outer.winfo_children():
            w.destroy()

        n = len(self._queue)

        # Empty state - thin, always-visible prompt bar
        if n == 0:
            self._expanded = False
            self.outer.config(height=_EMPTY_H)
            tk.Frame(self.outer, bg="#160a12", height=1).pack(fill="x")
            tk.Label(self.outer, text=self._empty_hint, font=(_UIF, 8),
                     bg=_BG, fg=_SUB, anchor="w", padx=14).pack(fill="x", pady=4)
            return

        # Height: compact banner, plus a ~40%-of-window detail panel when expanded.
        self.outer.config(height=(self._expanded_height() if self._expanded else _BANNER_H))

        tk.Frame(self.outer, bg=_BORDEAU, height=1).pack(fill="x")

        # ── Compact banner: Wróć (left) ·  SZCZEGÓŁY = wide centre  · Zatwierdź (right)
        banner = tk.Frame(self.outer, bg=_BG, height=_BANNER_H)
        banner.pack(fill="x")
        banner.grid_propagate(False)   # children use grid → keep the fixed banner height
        banner.columnconfigure(0, weight=0)   # Wróć
        banner.columnconfigure(1, weight=1)   # spacer
        banner.columnconfigure(2, weight=0)   # SZCZEGÓŁY (centred, wide)
        banner.columnconfigure(3, weight=1)   # spacer
        banner.columnconfigure(4, weight=0)   # Zatwierdź

        back = tk.Label(banner, text="‹ " + self._back_txt, font=(_UIF, 9), fg=_SUB,
                        bg=_BG, padx=14, pady=4, cursor="hand2")
        back.grid(row=0, column=0, sticky="w")
        back.bind("<Button-1>", lambda e: self.clear())
        self._hover(back, _TEXT, _SUB)

        # Wide, prominent centre button: title + count, toggles the detail panel.
        caret   = " ▴" if self._expanded else " ▾"
        det_fg  = _TEXT if self._expanded else _BORD_L
        det_bg  = _BORDEAU if self._expanded else _BORD_MID
        details = tk.Label(banner,
                           text=f"  {self._details_txt}   ·   {self._title} ({n}){caret}  ",
                           font=(_UIF, 9, "bold"), fg=det_fg, bg=det_bg,
                           padx=22, pady=6, cursor="hand2")
        details.grid(row=0, column=2)
        details.bind("<Button-1>", lambda e: self._toggle_details())
        details.bind("<Enter>", lambda e: details.config(fg=_TEXT, bg=_BORDEAU))
        details.bind("<Leave>", lambda e: details.config(fg=det_fg, bg=det_bg))

        confirm = tk.Label(banner, text=self._confirm_txt + " ›", font=(_UIF, 9, "bold"),
                           fg=_BORD_L, bg=_BORD_MID, padx=16, pady=4, cursor="hand2")
        confirm.grid(row=0, column=4, sticky="e", padx=(0, 12))
        confirm.bind("<Button-1>", lambda e: self._confirm())
        self._hover(confirm, _TEXT, _BORD_L)

        # ── Expandable detail panel (revealed by SZCZEGÓŁY, like the GPT panel) ──
        if not self._expanded:
            return

        tk.Frame(self.outer, bg=_BORD_MID, height=1).pack(fill="x")
        body = tk.Frame(self.outer, bg=_BG)
        body.pack(fill="both", expand=True)
        grid = tk.Frame(body, bg=_BG)
        grid.pack(fill="x", anchor="n", padx=16, pady=10)
        grid.columnconfigure(0, weight=1, uniform="q")
        grid.columnconfigure(1, weight=1, uniform="q")

        any_warn = False
        for idx, it in enumerate(self._queue):
            warn = bool(it.get("warn"))
            any_warn = any_warn or warn
            label = str(it.get("label", ""))
            if len(label) > 44:
                label = label[:43] + "…"
            tk.Label(grid, text=("⚠ " if warn else "• ") + label, font=(_UIF, 9),
                     bg=_BG, fg=(_AMBER if warn else _ITEM), anchor="w"
                     ).grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 14), pady=2)

        if any_warn:
            row_warn = math.ceil(len(self._queue) / 2) + 1
            tk.Label(grid,
                     text=_t("operator.warn_critical",
                             default="⚠  Wykryto element systemowy - zatwierdzaj z ostrożnością."),
                     font=(_UIF, 8), bg=_BG, fg=_AMBER, anchor="w"
                     ).grid(row=row_warn, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _expanded_height(self) -> int:
        """~40% of the current window height, clamped to a sane range."""
        try:
            avail = self.outer.winfo_toplevel().winfo_height()
        except Exception:
            avail = 0
        if avail < 120:                 # window not realised yet - sensible default
            avail = 540
        return max(_MIN_EXPANDED, min(int(avail * 0.40), _MAX_EXPANDED))

    def _confirm(self) -> None:
        if not self._queue:
            return
        # The page does the real work (and decides when to clear()).
        self._on_confirm(list(self._queue))
