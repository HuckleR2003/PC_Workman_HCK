# utils/paths.py
"""
Centralne rozwiązanie ścieżek dla trybów: dev, onedir EXE, onefile EXE, MSIX.

APP_DIR    - katalog TRWAŁEGO ZAPISU (logi, DB, prefs, cache, settings)
BUNDLE_DIR - katalog z bundlowanymi zasobami read-only (ikony, JSON, assets)

Dev / onedir:  oba = katalog główny projektu
Onefile EXE:   APP_DIR  = os.path.dirname(sys.executable)   (obok .exe)
               BUNDLE_DIR = sys._MEIPASS                     (temp extraction)
MSIX (Store):  exe mieszka w C:\\Program Files\\WindowsApps\\... które jest
               READ-ONLY - każdy zapis tam pada. APP_DIR przenosi się wtedy do
               %LOCALAPPDATA%\\PC_Workman_HCK (ta sama lokalizacja, której już
               używa user_knowledge.db). Dodatkowo robimy realny test zapisu,
               więc każda inna nie-zapisywalna lokalizacja też się przeniesie.
"""

import os
import sys

_FALLBACK_DIRNAME = "PC_Workman_HCK"


def _writable(path: str) -> bool:
    """True if we can actually create+delete a file inside *path*."""
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write_probe")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def _local_appdata_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local")
    path = os.path.join(base, _FALLBACK_DIRNAME)
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


def _app_dir() -> str:
    """Katalog trwałego zapisu (patrz nagłówek modułu)."""
    # PCW_APP_DIR: a separate folder for settings and data (2026-11-15). The
    # test suite sets it so a test can never write the real settings, and a
    # tester can run a second, clean profile next to the normal one.
    override = os.environ.get("PCW_APP_DIR")
    if override:
        try:
            os.makedirs(override, exist_ok=True)
            return override
        except Exception:
            pass
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        # Microsoft Store / MSIX: install dir is read-only -> LOCALAPPDATA
        if "windowsapps" in exe_dir.lower() or not _writable(exe_dir):
            return _local_appdata_dir()
        return exe_dir
    # dev: dwa poziomy wyżej niż utils/paths.py -> root projektu
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bundle_dir() -> str:
    """Katalog z zasobami read-only bundlowanymi przez PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


APP_DIR    = _app_dir()
BUNDLE_DIR = _bundle_dir()


def log_dir() -> str:
    """
    Folder for errors.log and freeze_dump.txt.

    PCW_LOG_DIR overrides it. The test suite sets that to a temp folder:
    tests build the real window without a mainloop, which the freeze watchdog
    reads as a stall, and until 2026-11-14 every test run appended fake
    freezes and thread errors to the logs of real use.
    Read at call time, so the override works even after this module is imported.
    """
    return os.environ.get("PCW_LOG_DIR") or os.path.join(APP_DIR, "data", "logs")
