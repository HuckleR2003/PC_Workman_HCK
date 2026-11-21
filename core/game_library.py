"""core.game_library - which game is this, its genre and what to say (2026-11-20).

data/games.json holds about 230 games: their .exe names, a genre, the Steam
appid and one to three launch messages in Polish and English. Before this the
list lived inside the toast (42 games), and a game outside it got one line
for everything ("Dobrej zabawy!").

How a game is recognised, in order:
  1. by its .exe name (or the name of its family: beamng.drive.x64 = beamng.drive);
  2. when it runs from a Steam library: the folder it runs from leads to its
     appmanifest_<appid>.acf, which gives the appid (then the genre from the
     library) and the game's real name. So a wrong or new .exe name still
     finds the right game, and an unknown Steam game gets its real name.

What it says, in order:
  1. the first time a game is seen on this PC: a "first time" line;
  2. the game's own messages;
  3. a message from its genre's pool;
  4. the default line.
The games already greeted are kept in data/cache/games_seen.json (names only).
"""
from __future__ import annotations

import json
import os
import random
import re
import threading
from typing import Dict, Optional, Tuple

_lock = threading.Lock()
_DB: Optional[Dict] = None
_BY_EXE: Dict[str, Dict] = {}
_BY_APPID: Dict[int, Dict] = {}
_BY_FAMILY: Dict[str, Dict] = {}
_MANIFEST_CACHE: Dict[str, Optional[Tuple[int, str]]] = {}


def _db_path() -> Optional[str]:
    try:
        from utils.paths import BUNDLE_DIR, APP_DIR
        bases = (BUNDLE_DIR, APP_DIR)
    except Exception:
        bases = ()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for base in (*bases, here):
        p = os.path.join(base, "data", "games.json")
        if os.path.exists(p):
            return p
    return None


def _family(exe: str) -> str:
    try:
        from core.game_detect import game_family
        return game_family(exe)
    except Exception:
        return (exe or "").lower().rsplit(".exe", 1)[0]


def load(path: Optional[str] = None) -> Dict:
    global _DB
    with _lock:
        if _DB is not None and path is None:
            return _DB
        p = path or _db_path()
        try:
            with open(p, encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            db = {"genres": {}, "first": {}, "games": []}
        _BY_EXE.clear()
        _BY_APPID.clear()
        _BY_FAMILY.clear()
        for g in db.get("games", []):
            for e in g.get("exe", []):
                _BY_EXE[e.lower()] = g
                _BY_FAMILY.setdefault(_family(e), g)
            if g.get("appid"):
                _BY_APPID[int(g["appid"])] = g
        _DB = db
        return db


def known_exes(strict: bool = True) -> set:
    """Every .exe in the library. strict leaves out the names any program
    could have ("generic": discovery.exe, fm.exe, human.exe...): those count
    as a game only when they run from a game library folder."""
    db = load()
    if not strict:
        return set(_BY_EXE)
    generic = {e.lower() for g in db.get("games", []) for e in g.get("generic", [])}
    return set(_BY_EXE) - generic


def by_exe(exe: str) -> Optional[Dict]:
    load()
    n = (exe or "").lower().strip()
    return _BY_EXE.get(n) or _BY_FAMILY.get(_family(n))


def steam_manifest(exe_path: str) -> Optional[Tuple[int, str]]:
    """(appid, name) of the Steam game an .exe belongs to, from the
    appmanifest next to its library folder; None outside Steam."""
    if not exe_path:
        return None
    low = exe_path.replace("/", "\\")
    m = re.search(r"^(.*\\steamapps)\\common\\([^\\]+)", low, re.I)
    if not m:
        return None
    lib, installdir = m.group(1), m.group(2)
    key = (lib + "|" + installdir).lower()
    if key in _MANIFEST_CACHE:
        return _MANIFEST_CACHE[key]
    found = None
    try:
        for f in os.listdir(lib):
            if not (f.startswith("appmanifest_") and f.endswith(".acf")):
                continue
            with open(os.path.join(lib, f), encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
            inst = re.search(r'"installdir"\s+"([^"]+)"', txt)
            if inst and inst.group(1).lower() == installdir.lower():
                aid = re.search(r'"appid"\s+"(\d+)"', txt)
                nm = re.search(r'"name"\s+"([^"]+)"', txt)
                found = (int(aid.group(1)) if aid else 0, nm.group(1) if nm else installdir)
                break
    except Exception:
        found = None
    _MANIFEST_CACHE[key] = found
    return found


def resolve(exe: str, exe_path: Optional[str] = None) -> Dict:
    """{"name", "genre", "game": the library entry or None, "appid"}."""
    g = by_exe(exe)
    appid, name = None, None
    if exe_path:
        man = steam_manifest(exe_path)
        if man:
            appid, name = man
            if g is None and appid:
                g = _BY_APPID.get(appid)
    if g is not None:
        return {"name": g["name"], "genre": g.get("genre", "default"), "game": g,
                "appid": g.get("appid") or appid}
    try:
        from core.game_detect import display_name
        fallback = display_name(exe)
    except Exception:
        fallback = (exe or "").rsplit(".exe", 1)[0]
    return {"name": name or fallback, "genre": "default", "game": None, "appid": appid}


def display_name(exe: str) -> Optional[str]:
    """The game's proper name when the library knows it, else None."""
    g = by_exe(exe)
    return g["name"] if g else None


def accent(genre: str) -> str:
    return (load().get("genres", {}).get(genre) or {}).get("accent", "#3b82f6")


# ── first time on this PC ────────────────────────────────────────────────
def _seen_path() -> str:
    from utils.paths import APP_DIR
    return os.path.join(APP_DIR, "data", "cache", "games_seen.json")


def _seen() -> set:
    try:
        from utils.prefs_io import load_json
        return set(load_json(_seen_path(), {}).get("games", []))
    except Exception:
        return set()


def is_first_time(exe: str) -> bool:
    return _family(exe) not in _seen()


def mark_seen(exe: str) -> None:
    try:
        from utils.prefs_io import edit_json
        fam = _family(exe)

        def _add(d):
            games = set(d.get("games", []))
            games.add(fam)
            d["games"] = sorted(games)
        edit_json(_seen_path(), _add)
    except Exception:
        pass


def message(exe: str, lang: str = "pl", exe_path: Optional[str] = None,
            first: Optional[bool] = None, rng=random) -> Tuple[str, Optional[str], str]:
    """(title, subtitle, accent colour) for a game that just started."""
    lang = "en" if lang == "en" else "pl"
    db = load()
    info = resolve(exe, exe_path)
    genre = info["genre"]
    name = info["name"]
    if first is None:
        first = is_first_time(exe)
    pool = None
    if first:
        pool = (db.get("first") or {}).get(lang)
    if not pool and info["game"] is not None:
        pool = (info["game"].get("msg") or {}).get(lang)
    if not pool:
        pool = (db.get("genres", {}).get(genre) or {}).get(lang)
    if not pool:
        pool = (db.get("genres", {}).get("default") or {}).get(lang) or [["Dobrej zabawy!" if lang == "pl" else "Good luck, have fun!", None]]
    title, sub = rng.choice(pool)
    if sub:
        sub = sub.replace("{name}", name)
    return title.replace("{name}", name), sub, accent(genre)
