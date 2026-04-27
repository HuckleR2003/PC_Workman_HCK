# utils/paths.py
"""
Centralne rozwiązanie ścieżek dla trybów: dev, onedir EXE, onefile EXE.

APP_DIR    — katalog z EXE (trwały zapis: logi, DB, prefs, cache)
BUNDLE_DIR — katalog z bundlowanymi zasobami read-only (ikony, JSON, assets)

Dev / onedir:  oba = katalog główny projektu
Onefile EXE:   APP_DIR  = os.path.dirname(sys.executable)   (obok .exe)
               BUNDLE_DIR = sys._MEIPASS                     (temp extraction)
"""

import os
import sys


def _app_dir() -> str:
    """Katalog zawierający uruchomiony plik .exe (lub projekt w trybie dev)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # dev: dwa poziomy wyżej niż utils/paths.py → root projektu
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bundle_dir() -> str:
    """Katalog z zasobami read-only bundlowanymi przez PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


APP_DIR    = _app_dir()
BUNDLE_DIR = _bundle_dir()
