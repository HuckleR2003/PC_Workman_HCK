"""tests._isolate - keep window tests away from the real settings (2026-11-15).

The main window now remembers its size, position and chart range in
settings/app_settings.json. A test that builds the real window would write
there on every <Configure>, i.e. into the developer's own settings. Every
test that builds ExpandedMainWindow calls isolate_window_state() first.
"""
import os
import tempfile

_DIR = tempfile.mkdtemp(prefix="pcw_test_appsettings_")


def isolate_window_state():
    import ui.windows.main_window_expanded as mwe
    path = os.path.join(_DIR, "app_settings.json")
    mwe.ExpandedMainWindow._app_settings_file = staticmethod(lambda: path)
    return path
