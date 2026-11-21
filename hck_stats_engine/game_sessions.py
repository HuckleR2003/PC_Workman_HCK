"""hck_stats_engine/game_sessions.py - every game played, light or heavy
(2026-11-20).

Load periods (load_periods.py) open at GPU 60 % / CPU 70 % for 3 minutes.
Stardew Valley, PlateUp or Democracy never get there, so they left no trace
in the history, and the charts could not mark them. Each game the watcher
sees is now written to the events table, whatever the load:

    event_type   'game_session'     metric       'game'
    timestamp    start              resolved_at  end (moved forward every
                                                 minute while it runs, so a
                                                 crash still leaves the row)
    process_name the game's name    description  "{minutes} min"
    value        GPU peak %         baseline     GPU average %

Fed by GamingToastWatcher (the one process poller) through
register_game_observer: start, end, and "tick" for games still running.
Processes of one game (beamng.drive.exe + beamng.drive.x64.exe) are one
session.
"""
from __future__ import annotations

import threading
import time

from hck_stats_engine.db_manager import db_manager

TOUCH_EVERY_S = 60


class GameSessionRecorder:

    def __init__(self):
        self._lock = threading.Lock()
        self._open: dict = {}        # family -> {"id", "start", "touched", "exe"}

    # ── observer ─────────────────────────────────────────────────────────
    def on_game_event(self, event: str, exe: str, label: str = "",
                      now: float | None = None) -> None:
        if not exe or event not in ("start", "end", "tick"):
            return
        from core.game_detect import game_family, display_name
        now = time.time() if now is None else now
        fam = game_family(exe)
        with self._lock:
            sess = self._open.get(fam)
            if event == "start":
                if sess is None:
                    self._open[fam] = self._insert(display_name(exe), now, exe)
                return
            if sess is None:
                return
            if event == "tick":
                if now - sess["touched"] >= TOUCH_EVERY_S:
                    self._touch(sess, now)
                return
            # end: only the process that opened the session closes it
            if exe.strip().lower() != sess["exe"]:
                return
            self._close(sess, now)
            del self._open[fam]

    # ── database ─────────────────────────────────────────────────────────
    def _insert(self, name: str, now: float, exe: str) -> dict:
        sess = {"id": None, "start": now, "touched": now, "exe": exe.strip().lower()}
        conn = db_manager.get_connection()
        if conn is None:
            return sess
        try:
            cur = conn.execute(
                "INSERT INTO events (timestamp, event_type, severity, metric, value, "
                "baseline, process_name, description, resolved_at) "
                "VALUES (?, 'game_session', 'info', 'game', NULL, NULL, ?, '', ?)",
                (now, name, now))
            conn.commit()
            sess["id"] = cur.lastrowid
        except Exception as e:
            print(f"[GameSessions] insert failed: {e}")
        return sess

    def _touch(self, sess: dict, now: float) -> None:
        sess["touched"] = now
        if sess["id"] is None:
            return
        conn = db_manager.get_connection()
        if conn is None:
            return
        try:
            conn.execute("UPDATE events SET resolved_at = ?, description = ? WHERE id = ?",
                         (now, f"{max(1, int(round((now - sess['start']) / 60)))} min", sess["id"]))
            conn.commit()
        except Exception:
            pass

    def _close(self, sess: dict, now: float) -> None:
        if sess["id"] is None:
            return
        conn = db_manager.get_connection()
        if conn is None:
            return
        peak = avg = None
        try:
            row = conn.execute(
                "SELECT MAX(gpu_max), AVG(gpu_avg) FROM minute_stats "
                "WHERE timestamp >= ? AND timestamp <= ?", (sess["start"], now)).fetchone()
            if row:
                peak, avg = row[0], row[1]
        except Exception:
            pass
        try:
            conn.execute(
                "UPDATE events SET resolved_at = ?, description = ?, value = ?, baseline = ? "
                "WHERE id = ?",
                (now, f"{max(1, int(round((now - sess['start']) / 60)))} min",
                 round(peak, 1) if peak is not None else None,
                 round(avg, 1) if avg is not None else None, sess["id"]))
            conn.commit()
        except Exception as e:
            print(f"[GameSessions] close failed: {e}")


def sessions(start: float, end: float) -> list:
    """Game sessions overlapping [start, end), newest first, in the shape of
    load_periods.periods(): timestamp, end, process_name, minutes, peak, avg."""
    conn = db_manager.get_connection()
    if not conn:
        return []
    try:
        rows = conn.execute(
            "SELECT id, timestamp, resolved_at, value, baseline, process_name, description "
            "FROM events WHERE event_type = 'game_session' AND timestamp < ? "
            "AND COALESCE(resolved_at, timestamp) >= ? ORDER BY timestamp DESC",
            (end, start)).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        d = dict(r)
        d["end"] = d.pop("resolved_at") or d["timestamp"]
        d["peak"] = d.pop("value")
        d["avg"] = d.pop("baseline")
        d["minutes"] = max(1, int(round((d["end"] - d["timestamp"]) / 60)))
        out.append(d)
    return out


game_session_recorder = GameSessionRecorder()
