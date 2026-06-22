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
    """Detect screen DPI group and set module-level SCALE."""
    global SCALE
    sw = root.winfo_screenwidth()
    if sw >= 3840:       # 4K
        SCALE = 2.0
    elif sw >= 2560:     # 2K / QHD
        SCALE = 1.35
    elif sw >= 1920:     # Full HD
        SCALE = 1.0
    else:                # smaller laptops
        SCALE = max(0.85, sw / 1920)


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
        return 15    # 4K — plenty of vertical space
    elif SCALE >= 1.35:
        return 12    # 2K
    else:
        return 10    # 1080P


def wide_chart_h() -> int:
    """Chart height in maximize mode — proportional, never comical.
    Roughly 2× compact height (140px), scaled per screen tier."""
    if SCALE >= 2.0:
        return 520   # 4K
    elif SCALE >= 1.35:
        return 340   # 2K
    else:
        return 240   # 1080P


def wide_mid_padx() -> int:
    """Horizontal padding for session-averages section in maximize mode.
    Reduces visible width to ~65% of content area — avoids overstretching.
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
