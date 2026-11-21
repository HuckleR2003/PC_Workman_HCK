"""core.process_history - how a process lives on this PC (2026-11-20).

One question many places ask: is this process here every day, since when,
on how many of the last 7 days? The answer comes from the recorded history
(process_daily_stats for finished days, process_hourly_stats for today), not
from the process library, which only knows what a process is in general.

    presence("opera.exe") -> {
        "days_7":     6,              # days of the last 7 it ran on
        "streak":     12,             # consecutive days up to today/yesterday
        "first_seen": "2026-07-29",   # first recorded day, or None
        "today":      True,
    }
"""
from __future__ import annotations

import datetime as _dt
import time


def _conn():
    from hck_stats_engine.db_manager import db_manager
    if not db_manager.is_ready:
        return None
    return db_manager.get_connection()


def _days(name: str, conn) -> set:
    rows = conn.execute(
        "SELECT DISTINCT date_str FROM process_daily_stats WHERE lower(process_name) = ?",
        (name,)).fetchall()
    days = {r[0] for r in rows if r and r[0]}
    start = _dt.datetime.combine(_dt.date.today(), _dt.time()).timestamp()
    if conn.execute("SELECT 1 FROM process_hourly_stats WHERE lower(process_name) = ? "
                    "AND timestamp >= ? LIMIT 1", (name, start)).fetchone():
        days.add(_dt.date.today().isoformat())
    return days


def presence(process_name: str, today: _dt.date | None = None) -> dict:
    out = {"days_7": 0, "streak": 0, "first_seen": None, "today": False}
    name = (process_name or "").strip().lower()
    if not name:
        return out
    try:
        conn = _conn()
        if conn is None:
            return out
        days = _days(name, conn)
    except Exception:
        return out
    return summarize(days, today)


def summarize(days: set, today: _dt.date | None = None) -> dict:
    """The numbers from a set of ISO dates (kept apart for tests)."""
    today = today or _dt.date.today()
    out = {"days_7": 0, "streak": 0, "first_seen": None, "today": False}
    if not days:
        return out
    parsed = set()
    for d in days:
        try:
            parsed.add(_dt.date.fromisoformat(d))
        except Exception:
            continue
    if not parsed:
        return out
    out["first_seen"] = min(parsed).isoformat()
    out["today"] = today in parsed
    out["days_7"] = sum(1 for k in range(7) if today - _dt.timedelta(days=k) in parsed)
    # a streak may end yesterday: today is not over (or not recorded yet)
    day = today if today in parsed else today - _dt.timedelta(days=1)
    streak = 0
    while day in parsed:
        streak += 1
        day -= _dt.timedelta(days=1)
    out["streak"] = streak
    return out


def describe(info: dict, lang: str = "pl") -> str:
    """One line for a card: 'codziennie od 12 dni' / '3 z ostatnich 7 dni'."""
    if not info or not info.get("first_seen"):
        return ("Jeszcze nie ma go w historii." if lang != "en"
                else "Not in the history yet.")
    s, d7 = info.get("streak", 0), info.get("days_7", 0)
    if s >= 7:
        return f"Codziennie od {s} dni." if lang != "en" else f"Every day for {s} days."
    if d7:
        return (f"{d7} z ostatnich 7 dni." if lang != "en"
                else f"{d7} of the last 7 days.")
    return (f"Ostatnio widziany dawniej; pierwszy raz {info['first_seen']}." if lang != "en"
            else f"Not seen lately; first seen {info['first_seen']}.")
