"""utils.install_kind - which PC Workman is this, and what may it change (2026-11-20).

One place that knows the install kind and what follows from it, so pages
stop guessing ("Right-click → Run as administrator" was shown to Store users,
for whom it may not exist):

  kind()                  "store" (MSIX from the Microsoft Store), "exe" (the
                          PyInstaller build) or "source" (python startup.py)
  is_admin()              the process runs elevated
  registry_virtualized()  writes to HKCU land in the package's private copy
                          of the registry instead of the real one

Why the last one matters: a packaged desktop app (MSIX, runFullTrust) has its
HKCU writes copied into %LOCALAPPDATA%\\Packages\\<family>\\SystemAppData\\
Helium\\User.dat, unless the manifest turns that off
(desktop6:RegistryWriteVirtualization = disabled, with the restricted
capability unvirtualizedResources). Checked on 2026-11-20 with the package
published in the Store: a key written from inside it did not appear in the real
HKCU. So the Store build's Startup Manager "disabled" entries only in its own
copy: PC Workman showed them off, Windows still started them.
"""
from __future__ import annotations

import os
import sys

_MANIFEST_FLAG = "registrywritevirtualization>disabled"


def kind() -> str:
    exe = (sys.executable or "").lower()
    if "\\windowsapps\\" in exe:
        return "store"
    if getattr(sys, "frozen", False):
        return "exe"
    return "source"


def is_store() -> bool:
    return kind() == "store"


def is_admin() -> bool:
    try:
        from utils.admin import is_admin as _a
        return _a()
    except Exception:
        return False


def _own_manifest() -> str | None:
    """AppxManifest.xml of the package this process runs from."""
    d = os.path.dirname(sys.executable or "")
    for _ in range(3):
        p = os.path.join(d, "AppxManifest.xml")
        if os.path.exists(p):
            return p
        d = os.path.dirname(d)
    return None


def registry_virtualized(manifest_path: str | None = None, store: bool | None = None) -> bool:
    """True when this is a Store install whose manifest leaves HKCU write
    virtualization on (every package published before 2026-11-21)."""
    if store is None:
        store = is_store()
    if not store:
        return False
    path = manifest_path or _own_manifest()
    if not path:
        return True              # packaged, manifest unreadable: assume the default
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            txt = f.read().lower().replace(" ", "")
        return _MANIFEST_FLAG not in txt
    except Exception:
        return True


def open_task_manager_startup() -> bool:
    """Task Manager on its Startup apps page (Windows' own switch, which
    works from any install)."""
    try:
        import subprocess
        subprocess.Popen(["taskmgr.exe", "/0", "/startup"])
        return True
    except Exception:
        return False
