"""core.process_center - the data behind the Process Center (2026-11-20).

Processes were shown in eight places (Dashboard TOP 5, My PC, Activity
Memory, hck_GPT, Startup, Services...) and nowhere together. This module
gathers everything known about each one, so the page only draws:

    ProcessSampler().refresh() -> list of rows, one per process NAME:
        name, display, instances, cpu (% of the whole CPU), ram_mb,
        windowed (has a visible window), cpu_7d, ram_7d (recorded averages),
        days_7, streak, first_seen (how it lives on this PC),
        safety (trusted | check | unknown), category, game,
        action, impact, why (core.recommendations)

    counts(rows) -> {"now", "background", "to_consider", "avg_7d", "max_7d"}
    series(seconds) -> [(ts, process count)] for the chart

The CPU of a process is measured between two refreshes (psutil needs two
readings), so the first refresh reports 0 % and the page refreshes again.
"""
from __future__ import annotations

import datetime as _dt
import threading
import time

_SAFETY = {"safe": "trusted", "caution": "check", "suspicious": "check"}


def _visible_window_pids() -> set:
    """PIDs that own a visible top-level window (Windows only)."""
    pids: set = set()
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        proto = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _cb(hwnd, _lp):
            if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                pids.add(pid.value)
            return True
        user32.EnumWindows(proto(_cb), 0)
    except Exception:
        pass
    return pids


def _conn():
    try:
        from hck_stats_engine.db_manager import db_manager
        return db_manager.get_connection() if db_manager.is_ready else None
    except Exception:
        return None


def history_by_name(days: int = 7, today: _dt.date | None = None) -> dict:
    """name -> {"cpu_7d", "ram_7d", "days_7", "streak", "first_seen"} for
    every process in the recorded history, from one pass over the tables."""
    out: dict = {}
    conn = _conn()
    if conn is None:
        return out
    today = today or _dt.date.today()
    since_ts = _dt.datetime.combine(today - _dt.timedelta(days=days - 1), _dt.time()).timestamp()
    try:
        # The history samples every INSTANCE once a second: Claude's 12
        # processes give 12 samples a second at ~30 MB each. Summed over the
        # instances and divided by the seconds the program was there
        # (at most 3600 an hour) it is the whole program's average while it
        # runs, comparable with "now" (which sums the instances too).
        for name, cpu, ram in conn.execute(
                "SELECT lower(process_name), "
                "SUM(cpu_avg * sample_count) / NULLIF(SUM(MIN(sample_count, 3600)), 0), "
                "SUM(ram_avg_mb * sample_count) / NULLIF(SUM(MIN(sample_count, 3600)), 0) "
                "FROM process_hourly_stats WHERE timestamp >= ? GROUP BY lower(process_name)",
                (since_ts,)):
            out.setdefault(name, {})["cpu_7d"] = cpu
            out[name]["ram_7d"] = ram
        days_by: dict = {}
        for name, d in conn.execute(
                "SELECT DISTINCT lower(process_name), date_str FROM process_daily_stats"):
            days_by.setdefault(name, set()).add(d)
        start = _dt.datetime.combine(today, _dt.time()).timestamp()
        for (name,) in conn.execute(
                "SELECT DISTINCT lower(process_name) FROM process_hourly_stats WHERE timestamp >= ?",
                (start,)):
            days_by.setdefault(name, set()).add(today.isoformat())
    except Exception:
        return out
    from core.process_history import summarize
    for name, ds in days_by.items():
        info = summarize(ds, today)
        out.setdefault(name, {}).update(
            days_7=info["days_7"], streak=info["streak"], first_seen=info["first_seen"])
    return out


class ProcessSampler:
    """Live processes grouped by name, joined with what is known about them."""

    HISTORY_TTL = 120          # the recorded averages change slowly

    def __init__(self):
        self._procs: dict = {}         # pid -> psutil.Process (keeps cpu deltas)
        self._lock = threading.Lock()
        self._hist: dict = {}
        self._hist_ts = 0.0
        self._lib = None

    def _library(self):
        if self._lib is None:
            try:
                from hck_gpt.process_library import process_library
                self._lib = process_library
            except Exception:
                self._lib = False
        return self._lib or None

    def _history(self) -> dict:
        if time.time() - self._hist_ts > self.HISTORY_TTL:
            self._hist = history_by_name()
            self._hist_ts = time.time()
        return self._hist

    def refresh(self) -> list:
        import psutil
        ncpu = psutil.cpu_count() or 1
        windowed = _visible_window_pids()
        groups: dict = {}
        with self._lock:
            alive = set()
            for p in psutil.process_iter(["pid", "name", "memory_info"]):
                pid = p.info["pid"]
                name = (p.info.get("name") or "").strip()
                if not name or pid in (0, 4):
                    continue
                alive.add(pid)
                proc = self._procs.get(pid)
                if proc is None:
                    proc = self._procs[pid] = p
                try:
                    cpu = proc.cpu_percent(None) / ncpu
                except Exception:
                    cpu = 0.0
                mem = p.info.get("memory_info")
                g = groups.setdefault(name.lower(), {
                    "name": name.lower(), "instances": 0, "cpu": 0.0, "ram_mb": 0.0,
                    "windowed": False, "pids": []})
                g["instances"] += 1
                g["cpu"] += cpu
                g["ram_mb"] += (mem.rss / 1048576) if mem else 0.0
                g["windowed"] = g["windowed"] or pid in windowed
                g["pids"].append(pid)
            for pid in list(self._procs):
                if pid not in alive:
                    del self._procs[pid]
        hist = self._history()
        lib = self._library()
        try:
            from core.recommendations import recommend
        except Exception:
            recommend = None
        try:
            from core.game_detect import is_game
        except Exception:
            is_game = None
        rows = []
        for name, g in groups.items():
            info = lib.get_process_info(name) if lib else None
            h = hist.get(name, {})
            rec = recommend(name) if recommend else {"action": "keep", "impact": "low", "why": ""}
            g.update(
                display=(info or {}).get("name") or name,
                cpu=round(g["cpu"], 1), ram_mb=round(g["ram_mb"]),
                cpu_7d=h.get("cpu_7d"), ram_7d=h.get("ram_7d"),
                days_7=h.get("days_7", 0), streak=h.get("streak", 0),
                first_seen=h.get("first_seen"),
                safety=_SAFETY.get((info or {}).get("safety"), "unknown"),
                category=(info or {}).get("category") or "",
                game=bool(is_game and is_game(name)),
                action=rec["action"], impact=rec["impact"], why=rec["why"])
            rows.append(g)
        return rows


def counts(rows: list) -> dict:
    """The four tiles: processes now, in the background, worth switching
    off, and the recorded average / peak over 7 days (None before data)."""
    now = sum(r["instances"] for r in rows)
    background = sum(r["instances"] for r in rows if not r["windowed"])
    consider = sum(1 for r in rows if r["action"] in ("startup_off", "delay", "close_ok"))
    avg = mx = None
    conn = _conn()
    if conn is not None:
        try:
            row = conn.execute(
                "SELECT AVG(proc_avg), MAX(proc_max) FROM hourly_stats "
                "WHERE timestamp >= ? AND proc_avg IS NOT NULL",
                (time.time() - 7 * 86400,)).fetchone()
            if row and row[0] is not None:
                avg, mx = round(row[0]), row[1]
            else:
                row = conn.execute(
                    "SELECT AVG(proc_count), MAX(proc_count) FROM minute_stats "
                    "WHERE timestamp >= ? AND proc_count IS NOT NULL",
                    (time.time() - 7 * 86400,)).fetchone()
                if row and row[0] is not None:
                    avg, mx = round(row[0]), row[1]
        except Exception:
            pass
    return {"now": now, "background": background, "to_consider": consider,
            "avg_7d": avg, "max_7d": mx}


def series(seconds: float, now: float | None = None) -> list:
    """[(timestamp, process count)] for the last `seconds`: minutes up to a
    day, hourly averages beyond."""
    now = now or time.time()
    conn = _conn()
    if conn is None:
        return []
    try:
        if seconds <= 86400:
            rows = conn.execute(
                "SELECT timestamp, proc_count FROM minute_stats WHERE timestamp >= ? "
                "AND proc_count IS NOT NULL ORDER BY timestamp", (now - seconds,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT timestamp, proc_avg FROM hourly_stats WHERE timestamp >= ? "
                "AND proc_avg IS NOT NULL ORDER BY timestamp", (now - seconds,)).fetchall()
    except Exception:
        return []
    return [(r[0], r[1]) for r in rows]


SORT_KEYS = {
    "name":   lambda r: r["display"].lower(),
    "cpu":    lambda r: r["cpu"],
    "ram":    lambda r: r["ram_mb"],
    "cpu_7d": lambda r: r["cpu_7d"] or 0.0,
    "ram_7d": lambda r: r["ram_7d"] or 0.0,
    "steady": lambda r: (r["streak"], r["days_7"]),
    "safety": lambda r: {"check": 0, "unknown": 1, "trusted": 2}[r["safety"]],
    "action": lambda r: {"startup_off": 0, "close_ok": 1, "delay": 2, "keep": 3,
                         "protected": 4}.get(r["action"], 5),
}


def sort_rows(rows: list, key: str, descending: bool = True) -> list:
    fn = SORT_KEYS.get(key, SORT_KEYS["ram"])
    return sorted(rows, key=fn, reverse=descending)


def filter_rows(rows: list, kind: str = "all", query: str = "") -> list:
    q = (query or "").strip().lower()
    out = []
    for r in rows:
        if q and q not in r["name"] and q not in r["display"].lower():
            continue
        if kind == "background" and r["windowed"]:
            continue
        if kind == "steady" and r["streak"] < 7:
            continue
        if kind == "consider" and r["action"] not in ("startup_off", "delay", "close_ok"):
            continue
        if kind == "games" and not r["game"]:
            continue
        out.append(r)
    return out
