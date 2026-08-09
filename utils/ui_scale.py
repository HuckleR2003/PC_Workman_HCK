"""
utils/ui_scale.py
Dynamic window scaling based on screen resolution.
Call init(root) once, immediately after tk.Tk() is created.
"""

SCALE = 1.0

_BASE_W = 1160
_BASE_H = 575
_BASE_SIDEBAR = 180


def init(root):
    """Detect screen DPI group, set module-level SCALE and sync Tk's font
    engine to it.

    The font sync is the fix for "text clipped on small screens / 125% laptops":
    window geometry scales with SCALE, but fonts are absolute point sizes that
    Tk converts to pixels with its own 'tk scaling' factor (derived from OS
    DPI). On a 125-150% laptop that factor renders every font ~25-60% larger
    while our pixel layout stays fixed, so text overflows and gets cut (hck_GPT
    banner, panels). Pinning the factor to (96dpi/72) * SCALE makes fonts follow
    the window: identical look at 1080p/100%, proportionally smaller on sub-FHD
    screens, doubled on 4K. One call - every point-sized font in the app obeys.
    """
    global SCALE
    SCALE = _compute_scale(root.winfo_screenwidth(), root.winfo_screenheight())

    try:
        root.tk.call("tk", "scaling", (96.0 / 72.0) * SCALE)
    except Exception:
        pass


def _compute_scale(sw: int, sh: int) -> float:
    """Pure SCALE formula (unit-tested in tests/test_window_scaling.py).

    Sub-FHD change (2026-07): the old branch SHRANK the window on small
    screens (1366x768 got 0.85 -> a 986x489 window swimming in unused
    space with 15% smaller fonts). Small screens need the opposite - fill
    most of the screen. The window now targets ~88% of width and ~85% of
    height, capped at the FHD baseline (1.0) so fonts never exceed their
    designed size, floored at 0.75 for very old panels (1024x768).

    Ultrawide fix (2026-08): the tiers above 1920 read WIDTH ONLY and assumed
    height came along proportionally. It does not on short-wide panels. A
    3840x1080 super-ultrawide picked the 4K tier and got a 1150px-tall window
    on a 1080px screen, so the bottom of the app sat off-screen. Every tier is
    now clamped by the height that actually exists. Nothing changes on 1080p,
    1440p or real 4K: their heights are already larger than the clamp, so the
    tier value passes through untouched.
    """
    if sw >= 3840:       # 4K
        tier = 2.0
    elif sw >= 2560:     # 2K / QHD
        tier = 1.35
    elif sw >= 1920:     # Full HD
        tier = 1.0
    else:
        # smaller laptops: biggest window that still fits comfortably
        fit_w = (sw * 0.88) / _BASE_W
        fit_h = (sh * 0.85) / _BASE_H
        return max(0.75, min(fit_w, fit_h, 1.0))

    # Wide screen, but the window still has to fit the height of it.
    return max(0.75, min(tier, (sh * 0.85) / _BASE_H))


def compact_w() -> int:
    return int(_BASE_W * SCALE)


def compact_h() -> int:
    return int(_BASE_H * SCALE)


def sidebar_width() -> int:
    return int(_BASE_SIDEBAR * SCALE)


def scale(px: int) -> int:
    """Scale any pixel value by SCALE. Returns original value on 1080P (SCALE=1.0)."""
    return int(px * SCALE)


def wide_panel_w() -> int:
    """Process panel width when window is maximized/zoomed."""
    if SCALE >= 2.0:
        return 480   # 4K
    elif SCALE >= 1.35:
        return 360   # 2K
    else:
        return 300   # 1080P


def wide_proc_limit() -> int:
    """How many processes to display in maximize mode."""
    if SCALE >= 2.0:
        return 15    # 4K - plenty of vertical space
    elif SCALE >= 1.35:
        return 12    # 2K
    else:
        return 10    # 1080P


def wide_chart_h() -> int:
    """Chart height in maximize mode - proportional, never comical.
    Roughly 2× compact height (140px), scaled per screen tier."""
    if SCALE >= 2.0:
        return 520   # 4K
    elif SCALE >= 1.35:
        return 340   # 2K
    else:
        return 240   # 1080P


def wide_mid_padx() -> int:
    """Horizontal padding for session-averages section in maximize mode.
    Reduces visible width to ~65% of content area - avoids overstretching.
    On 1080P content area ≈ 1740px → padx 304px each side → middle ≈ 1132px."""
    return scale(304)


def left_col_w() -> int:
    """Width of the left info-column in maximized dashboard (session + hardware + nav)."""
    if SCALE >= 2.0:
        return 480   # 4K
    elif SCALE >= 1.35:
        return 380   # 2K
    else:
        return 320   # 1080P
