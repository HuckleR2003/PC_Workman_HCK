"""utils/win_active.py - foreground window PID (2026-07 dedup).

Three identical `_foreground_pid()` copies (app_activity_tracker, fps_monitor,
turbo_manager) all did GetForegroundWindow + GetWindowThreadProcessId. Unified
into one guarded helper - returns 0 on any failure, never raises (safe on
non-Windows and when no window is focused)."""


def foreground_pid() -> int:
    """PID of the window currently in focus (usually the active app or game),
    or 0 when unavailable."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return 0
        pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0
