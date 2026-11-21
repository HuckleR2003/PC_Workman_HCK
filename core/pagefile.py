"""Virtual memory (page file) on this Windows machine, read without
PowerShell so the chat can show it at once (2026-11-17).

    info() -> {
        "mode":    "auto" | "system" | "custom" | "none" | "unknown",
        "size_gb": float | None,    # page files as they are now, all drives
        "drives":  [{"drive": "C:", "kind": "custom", "min_mb": 3072, "max_mb": 4096}, ...],
    }

mode:
    auto    "Automatically manage paging file size for all drives" is on
    system  a page file on each listed drive, size managed by Windows
    custom  at least one drive has a size set by hand
    none    no page file at all
The size comes from psutil.swap_memory(), which on Windows is the sum of
the page files (psutil 7: 24.1 GB here = 3.5 GB on C: + 19 GB on D:).
"""
from __future__ import annotations

_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"


def _parse(entries) -> tuple:
    drives = []
    for raw in entries or []:
        parts = (raw or "").strip().split()
        if not parts:
            continue
        path = parts[0]
        if path.startswith("?:"):
            return "auto", []
        drive = path[:2].upper()
        try:
            lo = int(parts[1]) if len(parts) > 1 else 0
            hi = int(parts[2]) if len(parts) > 2 else 0
        except ValueError:
            lo = hi = 0
        kind = "system" if lo == 0 and hi == 0 else "custom"
        drives.append({"drive": drive, "kind": kind, "min_mb": lo, "max_mb": hi})
    if not drives:
        return "none", []
    mode = "custom" if any(d["kind"] == "custom" for d in drives) else "system"
    return mode, drives


def info() -> dict:
    out = {"mode": "unknown", "size_gb": None, "drives": []}
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _KEY) as k:
            vals, _ = winreg.QueryValueEx(k, "PagingFiles")
        if isinstance(vals, str):
            vals = [vals]
        out["mode"], out["drives"] = _parse(vals)
    except Exception:
        pass
    try:
        import psutil
        total = psutil.swap_memory().total
        out["size_gb"] = round(total / 1024 ** 3, 1)
        if out["mode"] == "unknown" and total <= 0:
            out["mode"] = "none"
    except Exception:
        pass
    return out


def describe(lang: str = "pl", data: dict = None) -> str:
    """One line for the chat: is there virtual memory, how much, who sets it."""
    d = data if data is not None else info()
    mode, size = d.get("mode"), d.get("size_gb")
    size_txt = f"{size:.1f} GB" if size else ""
    drives = ", ".join(x["drive"] for x in d.get("drives") or [])
    pl = lang != "en"
    if mode == "none" or (mode != "unknown" and not size):
        return ("Pamięć wirtualna: wyłączona (brak pliku stronicowania)" if pl else
                "Virtual memory: off (no page file)")
    if mode == "auto":
        return (f"Pamięć wirtualna: jest, {size_txt}, rozmiarem zarządza Windows" if pl else
                f"Virtual memory: on, {size_txt}, size managed by Windows")
    if mode == "system":
        return (f"Pamięć wirtualna: jest, {size_txt} ({drives}), rozmiarem zarządza Windows" if pl else
                f"Virtual memory: on, {size_txt} ({drives}), size managed by Windows")
    if mode == "custom":
        return (f"Pamięć wirtualna: jest, {size_txt} ({drives}), rozmiar ustawiony ręcznie" if pl else
                f"Virtual memory: on, {size_txt} ({drives}), size set by hand")
    if size:
        return (f"Pamięć wirtualna: {size_txt}" if pl else f"Virtual memory: {size_txt}")
    return ("Pamięć wirtualna: nie mogę jej odczytać" if pl else
            "Virtual memory: cannot read it")
