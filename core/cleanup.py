"""core.cleanup - what can be cleaned, and cleaning it safely (2026-11-20).

The rules are in this module, not only on the page:
  * only known folders, listed below; nothing outside them is ever touched;
  * a scan first; nothing is deleted without the user choosing it on the
    page (a preview of the files is one click away);
  * temporary files and caches are deleted for good, like Windows' own Disk
    Cleanup does: Windows and the programs rebuild them, and moving 9 GB of
    temp files to the Recycle Bin would free nothing until it is emptied.
    Big files from Downloads (the user's own) go to the Recycle Bin. The page
    names the amount and asks before anything happens;
  * files younger than MIN_AGE_S, or in use, are skipped;
  * a browser's or a program's cache only while it is closed;
  * a "*" in a folder only stands for profile folders (Default, Profile 1);
  * big files in Downloads are never chosen automatically;
  * no registry.

    scan() -> [Category]        category: key, path(s), files, size, note
    clean(categories) -> {"freed", "files", "skipped", "per": {key: bytes}}
"""
from __future__ import annotations

import os
import time

MIN_AGE_S = 24 * 3600
BIG_FILE = 100 * 1024 ** 2
OLD_DOWNLOAD_S = 90 * 86400
PREVIEW = 30


def _env(name, default=""):
    return os.environ.get(name, default)


def _local():
    return _env("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))


GROUPS = ("windows", "browsers", "apps", "files")


def _items():
    """Every place Cleanup knows, as (key, group, [folders], options).

    A folder may hold one "*" (profiles: Chrome's Default, Profile 1, ...).
    Options:
      exe       programs that must be closed, or the item is skipped
      admin     needs PC Workman run as administrator
      pattern   only files matching it (fnmatch), e.g. thumbcache_*.db
      top_only  only the folder itself, not below it
      min_age   seconds a file must be untouched (default MIN_AGE_S)
      manual    never selected by default (the user's own files)
      recycle   to the Recycle Bin instead of deleted for good
    Nothing outside these folders is ever touched.
    """
    l = _local()
    a = _env("APPDATA", os.path.expanduser(r"~\AppData\Roaming"))
    win = _env("WINDIR", r"C:\Windows")
    pd = _env("PROGRAMDATA", r"C:\ProgramData")
    j = os.path.join

    def chromium(base):
        return [j(base, "*", "Cache"), j(base, "*", "Code Cache"), j(base, "*", "GPUCache")]

    return [
        # Windows
        ("user_temp", "windows", [_env("TEMP", j(l, "Temp"))], {}),
        ("windows_temp", "windows", [j(win, "Temp")], {"admin": True}),
        ("thumb_cache", "windows", [j(l, r"Microsoft\Windows\Explorer")],
         {"pattern": "thumbcache_*.db", "top_only": True, "min_age": 0}),
        ("error_reports", "windows", [j(l, r"Microsoft\Windows\WER"), j(l, "CrashDumps")], {}),
        ("system_reports", "windows", [j(pd, r"Microsoft\Windows\WER\ReportArchive"),
                                       j(pd, r"Microsoft\Windows\WER\ReportQueue"),
                                       j(win, "Minidump")], {"admin": True}),
        ("shader_cache", "windows", [j(l, r"NVIDIA\DXCache"), j(l, r"NVIDIA\GLCache"),
                                     j(l, "D3DSCache"), j(l, r"AMD\DxCache"),
                                     j(l, r"AMD\GLCache")], {}),
        ("update_cache", "windows", [j(win, r"SoftwareDistribution\Download")], {"admin": True}),
        ("delivery_opt", "windows", [j(win, r"ServiceProfiles\NetworkService\AppData\Local"
                                            r"\Microsoft\Windows\DeliveryOptimization\Cache")],
         {"admin": True}),
        # Browsers: only the page cache, never passwords, history or cookies
        ("br_chrome", "browsers", chromium(j(l, r"Google\Chrome\User Data")), {"exe": ["chrome.exe"]}),
        ("br_edge", "browsers", chromium(j(l, r"Microsoft\Edge\User Data")), {"exe": ["msedge.exe"]}),
        ("br_brave", "browsers", chromium(j(l, r"BraveSoftware\Brave-Browser\User Data")),
         {"exe": ["brave.exe"]}),
        ("br_opera", "browsers", [j(a, r"Opera Software\Opera Stable\Cache"),
                                  j(l, r"Opera Software\Opera Stable\Cache"),
                                  j(a, r"Opera Software\Opera Stable\Code Cache"),
                                  j(a, r"Opera Software\Opera Stable\GPUCache")], {"exe": ["opera.exe"]}),
        ("br_operagx", "browsers", [j(l, r"Opera Software\Opera GX Stable\Cache"),
                                    j(a, r"Opera Software\Opera GX Stable\Cache"),
                                    j(a, r"Opera Software\Opera GX Stable\Code Cache"),
                                    j(a, r"Opera Software\Opera GX Stable\GPUCache")], {"exe": ["opera.exe"]}),
        ("br_firefox", "browsers", [j(l, r"Mozilla\Firefox\Profiles\*\cache2")], {"exe": ["firefox.exe"]}),
        # Apps
        ("app_discord", "apps", [j(a, r"discord\Cache"), j(a, r"discord\Code Cache"),
                                 j(a, r"discord\GPUCache")], {"exe": ["discord.exe"]}),
        ("app_steam", "apps", [j(l, r"Steam\htmlcache")], {"exe": ["steam.exe", "steamwebhelper.exe"]}),
        ("app_spotify", "apps", [j(l, r"Spotify\Data"), j(l, r"Spotify\Browser\Cache")],
         {"exe": ["spotify.exe"]}),
        # Your files
        ("big_downloads", "files", [j(os.path.expanduser("~"), "Downloads")],
         {"big_only": True, "manual": True, "top_only": True, "recycle": True}),
    ]


def _expand(folders):
    """Folders with a "*" become every match; missing folders are dropped."""
    import glob
    out = []
    for f in folders or []:
        if not f:
            continue
        for p in (glob.glob(f) if "*" in f else [f]):
            if os.path.isdir(p) and not os.path.islink(p) and p not in out:
                out.append(p)
    return out


def categories_spec():
    """(key, [folders], options), group and programs inside the options."""
    return [(key, folders, {**opts, "group": group}) for key, group, folders, opts in _items()]


class Category:
    def __init__(self, key, folders, opts):
        self.key = key
        self.group = opts.get("group", "windows")
        self.folders = _expand(folders)
        self.opts = opts
        self.files = []          # (path, size)
        self.size = 0
        self.note = ""
        self.blocked = False     # e.g. browser running, no admin rights
        self.selected = not opts.get("manual", False)

    def preview(self, n=PREVIEW):
        return sorted(self.files, key=lambda f: -f[1])[:n]


def _running(names) -> set:
    try:
        import psutil
        want = {n.lower() for n in names}
        return {(p.info.get("name") or "").lower() for p in psutil.process_iter(["name"])} & want
    except Exception:
        return set()


def _walk(folder, now, opts, cap=200000):
    import fnmatch
    out = []
    pattern = (opts.get("pattern") or "").lower()
    min_age = opts.get("min_age", MIN_AGE_S)
    try:
        if opts.get("top_only"):
            entries = ((folder, [], os.listdir(folder)),)
        else:
            entries = os.walk(folder)
        for root, _dirs, names in entries:
            for n in names:
                p = os.path.join(root, n)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if not os.path.isfile(p):
                    continue
                if pattern and not fnmatch.fnmatch(n.lower(), pattern):
                    continue
                if opts.get("big_only"):
                    if st.st_size < BIG_FILE or now - st.st_mtime < OLD_DOWNLOAD_S:
                        continue
                elif now - st.st_mtime < min_age:
                    continue
                out.append((p, st.st_size))
                if len(out) >= cap:
                    return out
    except OSError:
        pass
    return out


def scan(now: float | None = None, spec=None) -> list:
    now = now or time.time()
    spec = spec or categories_spec()
    running = _running({e for _k, _f, o in spec for e in o.get("exe", [])})
    admin = is_admin()
    cats = []
    for key, folders, opts in spec:
        c = Category(key, folders, opts)
        open_now = sorted(e for e in opts.get("exe", []) if e.lower() in running)
        if open_now:
            # a program writes to its cache while it runs: skip it whole
            c.blocked = True
            c.note = "running:" + ", ".join(open_now)
        elif opts.get("admin") and not admin:
            # os.access() on Windows only reads the read-only flag; these
            # folders need administrator rights to delete anything
            c.blocked = True
            c.note = "admin"
        if not c.blocked:
            for f in c.folders:
                c.files += _walk(f, now, opts)
        c.size = sum(s for _p, s in c.files)
        if c.blocked:
            c.selected = False
        cats.append(c)
    try:
        cats.append(_recycle_bin())
    except Exception:
        pass
    _remember_scan(cats)
    return cats


def summary(cats) -> dict:
    """What a scan found, for hck_GPT and the tips (no file names)."""
    return {"ts": time.time(),
            "total": sum(c.size for c in cats if not c.blocked),
            "items": {c.key: {"size": c.size, "files": len(c.files), "group": c.group,
                              "blocked": c.note if c.blocked else ""} for c in cats}}


def _scan_path():
    from utils.paths import APP_DIR
    return os.path.join(APP_DIR, "data", "cache", "cleanup_scan.json")


def _remember_scan(cats) -> None:
    try:
        from utils.prefs_io import save_json
        save_json(_scan_path(), summary(cats), indent=0)
    except Exception:
        pass


def last_scan():
    try:
        import json
        from utils.prefs_io import load_json
        return load_json(_scan_path(), None) or None
    except Exception:
        return None


def flush_dns() -> bool:
    """ipconfig /flushdns, only when the user clicks it. Harmless: Windows
    asks the DNS server again on the next visit."""
    try:
        import subprocess
        r = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=15,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode == 0
    except Exception:
        return False


def is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _recycle_bin():
    """The Recycle Bin's size (SHQueryRecycleBinW). Emptying it is permanent,
    so it is never selected by default."""
    import ctypes
    from ctypes import wintypes

    class _Info(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("i64Size", ctypes.c_longlong),
                    ("i64NumItems", ctypes.c_longlong)]
    info = _Info()
    info.cbSize = ctypes.sizeof(_Info)
    c = Category("recycle_bin", [], {"manual": True, "permanent": True, "group": "files"})
    if ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info)) == 0:
        c.size = int(info.i64Size)
        c.files = [("(Recycle Bin)", c.size)] if c.size else []
    c.selected = False
    return c


def to_recycle_bin(paths, undo: bool = True) -> int:
    """Move files to the Recycle Bin. Returns how many are gone afterwards.
    undo=False deletes for good (only the tests use it, on their own files,
    so checking the shell call never fills the user's Recycle Bin)."""
    paths = [p for p in paths if p and os.path.isfile(p)]
    if not paths:
        return 0
    if not undo:
        # for good: one call per file, a file in use is simply skipped
        done = 0
        for p in paths:
            try:
                os.remove(p)
                done += 1
            except OSError:
                pass
        return done
    import ctypes
    from ctypes import wintypes

    class _Op(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                    ("fFlags", ctypes.c_uint16), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]
    FO_DELETE = 3
    FOF = 0x0010 | 0x0004 | 0x0400            # no confirmation, silent, no error UI
    if undo:
        FOF |= 0x0040                          # allow undo = the Recycle Bin
    done = 0
    for i in range(0, len(paths), 200):       # the shell takes a double-NUL list
        chunk = paths[i:i + 200]
        op = _Op(None, FO_DELETE, "\0".join(chunk) + "\0\0", None, FOF, False, None, None)
        if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0:
            done += sum(1 for p in chunk if not os.path.exists(p))
    return done


def empty_recycle_bin() -> bool:
    import ctypes
    SHERB = 0x1 | 0x2 | 0x4          # no confirmation, no progress, no sound
    return ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, SHERB) in (0, -2147418113)


def clean(categories) -> dict:
    """Clean the chosen categories. The caller (the page, after the user
    confirmed) decides which; blocked ones are left alone."""
    out = {"freed": 0, "files": 0, "skipped": 0, "per": {}}
    for c in categories:
        if not c.selected or c.blocked:
            continue
        if c.opts.get("permanent"):
            if c.key == "recycle_bin" and c.size and empty_recycle_bin():
                out["per"][c.key] = c.size
                out["freed"] += c.size
            continue
        before = {p: s for p, s in c.files}
        moved = to_recycle_bin(list(before), undo=bool(c.opts.get("recycle")))
        gone = sum(s for p, s in before.items() if not os.path.exists(p))
        out["per"][c.key] = gone
        out["freed"] += gone
        out["files"] += moved
        out["skipped"] += len(before) - moved
    _log(out)
    return out


def _log(result) -> None:
    """The last cleanups, for the page's receipt (data/cache/cleanup_log.json)."""
    try:
        import json
        from utils.paths import APP_DIR
        p = os.path.join(APP_DIR, "data", "cache", "cleanup_log.json")
        from utils.prefs_io import load_json, save_json
        items = load_json(p, [])
        if not isinstance(items, list):
            items = []
        items.append({"ts": time.time(), **result})
        save_json(p, items[-20:], indent=0)
    except Exception:
        pass


def last_cleanup():
    try:
        import json
        from utils.paths import APP_DIR
        p = os.path.join(APP_DIR, "data", "cache", "cleanup_log.json")
        with open(p, encoding="utf-8") as f:
            items = json.load(f)
        return items[-1] if items else None
    except Exception:
        return None


def fmt_size(n: float, lang: str = "pl") -> str:
    for unit, div in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if n >= div:
            s = f"{n / div:.1f}"
            return (s.replace(".", ",") if lang == "pl" else s) + " " + unit
    return f"{int(n)} B"
