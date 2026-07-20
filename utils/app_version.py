# utils/app_version.py
"""
THE one version source for the whole project.

Bump the number below and everything follows: startup banner + single-instance
window lookup, both window titles, HCK_Labs badge and "What's new", Guide page,
hck_GPT about, telemetry payloads, and the PyInstaller dist folder name
(PCWorkman.spec reads this file by regex at build time).

Rules (guarded by tests/test_version.py):
  - this module imports NOTHING - safe at line 1 of startup.py and in frozen
    builds (reading startup.py as a FILE broke in dist: the .py is not there,
    so pre-1.8.4 fallbacks silently reported "1.8.0")
  - no other source file may hardcode an app version literal
  - MAIN_WINDOW_TITLE is shared by main_window_expanded (sets it) and
    startup's FindWindowW (searches it) - before 1.8.4 the two strings were
    hardcoded separately, drifted (v1.8.1 vs v1.8.2) and second-instance
    focus quietly stopped working
"""

APP_VERSION = "1.8.4"

# Exact main-window title. startup.py's single-instance path looks this
# string up via FindWindowW, so the two must be THE SAME object - never
# rebuild it by hand. (Double space is intentional, kept from 1.8.x.)
MAIN_WINDOW_TITLE = f"PC Workman HCK  v{APP_VERSION}"


def version_tuple():
    """(1, 8, 4) - for numeric comparisons (update checks etc.)."""
    return tuple(int(p) for p in APP_VERSION.split("."))
