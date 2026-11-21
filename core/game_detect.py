"""
core/game_detect.py - is this process a game? (2026-11-16)

The app had several hand-made game lists (gaming toast, session memory,
hck_GPT). None had BeamNG.drive, so during a 40-minute session at 97 % GPU
hck_GPT asked "Spotted BeamNG.drive using significant CPU. Expected?".

A process counts as a game when
  1. its name is on one of the app's known-game lists, or
  2. its executable lives in a game library folder (Steam, Epic, GOG, Xbox,
     Riot, Ubisoft, EA, Battle.net), which covers almost any store game
     without adding it by hand.
Results are cached per process name; the path is read once per name.
"""
from __future__ import annotations

import threading

_LIBRARY_MARKERS = (
    "\\steamapps\\common\\",
    "\\epic games\\",
    "\\gog galaxy\\games\\",
    "\\gog games\\",
    "\\xboxgames\\",
    "\\windowsapps\\",          # only together with a known name, see below
    "\\riot games\\",
    "\\ubisoft game launcher\\games\\",
    "\\ea games\\",
    "\\origin games\\",
    "\\battle.net\\",
    "\\blizzard\\",
    "\\rockstar games\\",
)
# launchers and helpers that live in those folders but are not games
_NOT_GAMES = {
    "steam.exe", "steamwebhelper.exe", "steamservice.exe", "epicgameslauncher.exe",
    "epicwebhelper.exe", "galaxyclient.exe", "riotclientservices.exe",
    "riotclientux.exe", "upc.exe", "ubisoftconnect.exe", "eadesktop.exe",
    "battle.net.exe", "agent.exe", "crashreportclient.exe", "unitycrashhandler64.exe",
    "easyanticheat.exe", "beservice.exe", "vc_redist.x64.exe",
}

# inside a game folder but not the game: runtimes, installers, crash tools
_HELPER_DIRS = {"jre", "java", "redist", "_commonredist", "directx", "vcredist",
                "support", "tools", "crashreporter", "installer", "prerequisites"}
_HELPER_WORDS = ("java", "redist", "setup", "crash", "helper", "uninst", "update",
                 "launcher", "console", "server", "7z", "dxsetup", "qtwebengine",
                 "sendrpt", "support", "uploader", "viewer", "jab", "jacc", "jfr",
                 "jrun", "jweb", "keytool", "kinit", "klist", "ktab", "rmiregistry",
                 "launchpad", "unitycrash", "vc_")

_cache: dict = {}
_lock = threading.Lock()


def _known_names() -> set:
    names = set()
    try:
        # data/games.json (2026-11-20), without the generic names
        from core.game_library import known_exes
        names |= known_exes(strict=True)
    except Exception:
        pass
    return names


_KNOWN = None
_LIBRARY = None


def _library_exe_names() -> set:
    """Names of the .exe files inside the installed game libraries (Steam
    libraries from libraryfolders.vdf, Epic, GOG, Xbox), read once.

    2026-11-17: the history keeps process names, not paths, so "w co
    najwięcej grałem?" could not tell that beamng.drive.x64.exe is a game.
    A game that is installed is recognised by name from now on."""
    import os
    import re
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            steam = winreg.QueryValueEx(k, "SteamPath")[0]
        roots.append(os.path.join(steam, "steamapps", "common"))
        vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf):
            txt = open(vdf, encoding="utf-8", errors="replace").read()
            for p in re.findall(r'"path"\s+"([^"]+)"', txt):
                roots.append(os.path.join(p.replace("\\\\", "\\"), "steamapps", "common"))
    except Exception:
        pass
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        roots += [os.path.join(base, "Epic Games"), os.path.join(base, "GOG Galaxy", "Games")]
    roots.append(r"C:\XboxGames")
    names, seen = set(), 0
    for root in dict.fromkeys(roots):
        if not os.path.isdir(root):
            continue
        # Unreal games keep the real exe deeper, in <game>\<Name>\Binaries\Win64
        # (2026-11-17: AutomationGame-Win64-Shipping.exe was missed)
        import glob
        for pattern in ("*/Binaries/Win64/*.exe", "*/*/Binaries/Win64/*.exe"):
            for f in glob.glob(os.path.join(root, pattern)):
                fl = os.path.basename(f).lower()
                if not any(h in fl for h in _HELPER_WORDS):
                    names.add(fl)
        base_depth = root.rstrip("\\/").count(os.sep)
        for dirpath, dirs, files in os.walk(root):
            if dirpath.count(os.sep) - base_depth >= 3:
                dirs[:] = []
            # bundled runtimes and installers are not the game
            dirs[:] = [d for d in dirs if d.lower() not in _HELPER_DIRS]
            for f in files:
                fl = f.lower()
                if fl.endswith(".exe") and not any(h in fl for h in _HELPER_WORDS):
                    names.add(fl)
            seen += len(files)
            if seen > 60000:
                return names - _NOT_GAMES
    return names - _NOT_GAMES


_JAVA_NAMES = ("javaw.exe", "java.exe", "javaw", "java")


def is_minecraft_java(pid: int | None) -> bool:
    """Minecraft Java Edition runs as javaw.exe, which is also every other
    Java program. Its command line names it (net.minecraft / .minecraft)."""
    if not pid:
        return False
    try:
        import psutil
        cmd = " ".join(psutil.Process(pid).cmdline()).lower()
    except Exception:
        return False
    return "net.minecraft" in cmd or ".minecraft" in cmd or "minecraft-launcher" in cmd


def is_game(name: str, pid: int | None = None, exe_path: str | None = None) -> bool:
    n = (name or "").lower().strip()
    if not n or n in _NOT_GAMES:
        return False
    if n in _JAVA_NAMES:
        # decided per process, never cached by name (2026-11-20)
        return is_minecraft_java(pid)
    with _lock:
        if n in _cache:
            return _cache[n]
    global _KNOWN, _LIBRARY
    if _KNOWN is None:
        _KNOWN = _known_names()
    result = n in _KNOWN
    # an Unreal Engine release build: "<Game>-Win64-Shipping.exe" is a game
    # wherever it is installed (2026-11-17: AutomationGame-Win64-Shipping
    # was reported as "jumped onto the top list, not normally here")
    if not result and any(s in n for s in ("-win64-shipping", "-wingdk-shipping",
                                            "-wingdk-test", "-win64-test")):
        result = True
    if not result and pid is None and exe_path is None:
        # a name from the history, without a path: the installed libraries
        if _LIBRARY is None:
            try:
                _LIBRARY = _library_exe_names()
            except Exception:
                _LIBRARY = set()
        result = n in _LIBRARY or (n + ".exe") in _LIBRARY
    if not result:
        path = exe_path
        if path is None and pid:
            try:
                import psutil
                path = psutil.Process(pid).exe()
            except Exception:
                path = None
        if path:
            low = path.lower()
            result = any(m in low for m in _LIBRARY_MARKERS if m != "\\windowsapps\\")
    with _lock:
        # a negative answer without a path is not final: try again later
        if result or exe_path is not None or pid:
            _cache[n] = result
    return result


def game_family(exe: str) -> str:
    """beamng.drive.exe and beamng.drive.x64.exe are one game (2026-11-17:
    two check-ins and two recaps for one session). Used by the session
    recorder and hck_GPT's proactive monitor alike."""
    import re as _re
    n = (exe or "").strip().lower()
    if n.endswith(".exe"):
        n = n[:-4]
    prev = None
    while prev != n:
        prev = n
        n = _re.sub(r"[._-](x64|x86|win64|win32|shipping|dx11|dx12|vulkan|launcher)$", "", n)
    return n


def display_name(name: str) -> str:
    """'BeamNG.drive.x64.exe' -> 'BeamNG.drive'; a game the library knows
    gets its proper name ('cs2.exe' -> 'Counter-Strike 2')."""
    try:
        from core.game_library import display_name as _lib_name
        proper = _lib_name(name)
        if proper:
            return proper
    except Exception:
        pass
    base = (name or "").rsplit(".exe", 1)[0]
    for suffix in (".x64", "-win64-shipping", "_x64", "64"):
        if base.lower().endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base or name
