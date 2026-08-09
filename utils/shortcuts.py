# utils/shortcuts.py
"""
THE one place that creates desktop shortcuts.

Two kinds:
  create_shortcut()        - normal launch
  create_admin_shortcut()  - same target, but the .lnk carries the
                             "Run as administrator" bit

Why a module and not another copy inside the Settings page: the AUMID used for
Store installs was wrong in the old inline version (it pointed at an
Application Id that does not exist in the published manifest), so the Store
shortcut opened nothing. One definition means one place to get it right.

The elevation bit is not something WScript.Shell can set. It lives in the
LinkFlags field of the .lnk binary format, byte 21, bit 0x20. We create the
shortcut normally and then flip that bit. This is the same thing the Windows
"Advanced..." checkbox does.
"""
from __future__ import annotations

import os
import subprocess
import sys

# Must match Applications/Application/@Id in AppxManifest.xml. The published
# 1.8.2 package uses "App"; changing it would break every pinned tile and
# shortcut of existing users, so it stays.
_AUMID = r"MarcinHCKFirmuga.PCWorkman_4hekbcs2ddfbc!App"

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def is_store_install() -> bool:
    """True when running from the MSIX/WindowsApps location."""
    return "windowsapps" in (sys.executable or "").lower()


def desktop_dir() -> str:
    """Real Desktop path, honouring a OneDrive-redirected desktop."""
    try:
        import winreg as _wr
        k = _wr.OpenKey(_wr.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion"
                        r"\Explorer\User Shell Folders")
        d = os.path.expandvars(_wr.QueryValueEx(k, "Desktop")[0])
        _wr.CloseKey(k)
        if d and os.path.isdir(d):
            return d
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def _target_and_args():
    """(target, arguments, icon_source) for the current install kind."""
    exe = sys.executable
    if is_store_install():
        # WindowsApps is virtualised: launch through the shell's AppsFolder.
        explorer = os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                                "explorer.exe")
        return explorer, "shell:AppsFolder\\" + _AUMID, exe
    if getattr(sys, "frozen", False):
        return exe, "", exe
    return exe, f'"{os.path.abspath(sys.argv[0])}"', exe


def _make_lnk(path: str, target: str, args: str, icon: str) -> bool:
    def q(s):
        return (s or "").replace("'", "''")
    ps = (f"$w=New-Object -ComObject WScript.Shell;"
          f"$s=$w.CreateShortcut('{q(path)}');"
          f"$s.TargetPath='{q(target)}';"
          + (f"$s.Arguments='{q(args)}';" if args else "")
          + f"$s.IconLocation='{q(icon)},0';$s.Save()")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, timeout=20, creationflags=_NO_WINDOW)
        return r.returncode == 0 and os.path.isfile(path)
    except Exception:
        return False


def _set_run_as_admin(path: str) -> bool:
    """
    Flip the RunAsUser bit in the .lnk header.

    Byte 21 of a Shell Link holds the upper byte of LinkFlags; 0x20 there is
    RunAsUser, which is what the Properties > Advanced > "Run as administrator"
    checkbox writes. Nothing else in the file changes.
    """
    try:
        with open(path, "r+b") as f:
            f.seek(21)
            b = f.read(1)
            if not b:
                return False
            f.seek(21)
            f.write(bytes([b[0] | 0x20]))
        return True
    except Exception:
        return False


def create_shortcut(name: str = "PC Workman") -> bool:
    """Normal desktop shortcut. Returns True when the .lnk exists afterwards."""
    target, args, icon = _target_and_args()
    return _make_lnk(os.path.join(desktop_dir(), f"{name}.lnk"),
                     target, args, icon)


def create_admin_shortcut(name: str = "PC Workman (Administrator)"):
    """
    Desktop shortcut that asks for elevation on launch.

    Returns (ok, note). On a Store install this is refused rather than faked:
    the package launches through the shell's AppsFolder, and Windows does not
    elevate a packaged app that way. Saying so is more useful than creating a
    shortcut that quietly behaves like the normal one.
    """
    if is_store_install():
        return False, "store"
    target, args, icon = _target_and_args()
    path = os.path.join(desktop_dir(), f"{name}.lnk")
    if not _make_lnk(path, target, args, icon):
        return False, "create_failed"
    if not _set_run_as_admin(path):
        return False, "flag_failed"
    return True, "ok"
