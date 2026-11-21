"""
hck_stats_engine/load_periods.py - stretches of high load (2026-11-16).

The spike detector compares one minute with the 5 minutes before it. A game
that ramps up over a few minutes never crosses that difference: in the long
test 40 minutes of GPU at 95-99 % in BeamNG left no event at all.

A load period is what a person means by "it was working hard then":
    starts  after OPEN_MIN consecutive minutes at or above the threshold
    ends    after CLOSE_MIN consecutive minutes below threshold - HYSTERESIS,
            or when the recording stops (sleep, app closed)
It is stored in the events table (event_type "load_period"):
    timestamp    start          resolved_at  end (updated every minute)
    metric       cpu | gpu      value        peak %
    baseline     average %      process_name what ran (a game first)
    description  "{minutes} min" plus the highest measured temperature
The row is written when the period opens and updated each minute, so a
period that is still running, or cut by a crash, is already in the history.
"""
from __future__ import annotations

import collections
import time

from hck_stats_engine.db_manager import db_manager

# GPU 60 % (2026-11-17, was 80): the same line at which learning counts a
# minute as gaming. The third long test had 1.5 h of a game at GPU 64-75 %
# and no period at all. While a game runs the GPU period stays open whatever
# the load, so a game with a frame cap is still one stretch.
THRESHOLD = {"cpu": 70.0, "gpu": 60.0}
HYSTERESIS = 15.0
OPEN_MIN = 3
CLOSE_MIN = 3
GAP_S = 180          # no minute for this long = recording stopped (sleep)


class _Track:
    def __init__(self):
        self.reset()

    def reset(self):
        self.above = []            # minutes above the threshold before opening
        self.below = 0
        self.row_id = None
        self.start = None
        self.last = None
        self.n = 0
        self.sum = 0.0
        self.peak = 0.0
        self.temp_max = None
        self.procs = collections.Counter()
        self.game = None


class LoadPeriodTracker:
    def __init__(self):
        self._t = {m: _Track() for m in THRESHOLD}

    def on_minute(self, ts, values: dict, temps: dict | None = None,
                  top_process: str | None = None, game: str | None = None):
        """values: {"cpu": avg %, "gpu": avg %} for the minute ending at ts."""
        temps = temps or {}
        for metric, thr in THRESHOLD.items():
            v = values.get(metric)
            if v is None:
                continue
            tr = self._t[metric]
            if tr.last is not None and ts - tr.last > GAP_S:
                self._close(metric)                  # slept / app was closed
            playing = metric == "gpu" and bool(game)
            if tr.row_id is None:
                if v >= thr or playing:
                    tr.above.append((ts, v))
                    if len(tr.above) >= OPEN_MIN:
                        self._open(metric, temps.get(metric), top_process, game)
                else:
                    tr.above = []
                tr.last = ts
                continue
            # an open period
            self._add(tr, ts, v, temps.get(metric), top_process, game)
            if v < thr - HYSTERESIS and not playing:
                tr.below += 1
                if tr.below >= CLOSE_MIN:
                    self._close(metric)
            else:
                tr.below = 0
                self._write(metric)

    @staticmethod
    def _add(tr, ts, v, temp, proc, game):
        tr.n += 1
        tr.sum += v
        tr.peak = max(tr.peak, v)
        tr.last = ts
        if temp is not None and temp > 0:
            tr.temp_max = temp if tr.temp_max is None else max(tr.temp_max, temp)
        if game:
            tr.game = game
        if proc:
            tr.procs[proc] += 1

    def _open(self, metric, temp, proc, game):
        tr = self._t[metric]
        first = tr.above
        tr.above = []
        tr.start = first[0][0] - 60
        for ts, v in first:
            self._add(tr, ts, v, temp, proc, game)
        conn = db_manager.get_connection()
        if not conn:
            return
        try:
            cur = conn.execute(
                "INSERT INTO events (timestamp, event_type, severity, metric, "
                "value, baseline, process_name, description, resolved_at) "
                "VALUES (?, 'load_period', 'info', ?, ?, ?, ?, ?, ?)",
                (tr.start, metric, tr.peak, tr.sum / tr.n, self._who(tr),
                 self._desc(tr), tr.last))
            conn.commit()
            tr.row_id = cur.lastrowid
        except Exception as e:
            print(f"[LoadPeriods] open error: {e}")

    def _write(self, metric):
        tr = self._t[metric]
        if tr.row_id is None or not tr.n:
            return
        conn = db_manager.get_connection()
        if not conn:
            return
        avg = tr.sum / tr.n
        try:
            conn.execute(
                "UPDATE events SET value=?, baseline=?, process_name=?, "
                "description=?, resolved_at=?, severity=? WHERE id=?",
                (round(tr.peak, 1), round(avg, 1), self._who(tr), self._desc(tr),
                 tr.last, "warning" if avg >= 90 else "info", tr.row_id))
            conn.commit()
        except Exception as e:
            print(f"[LoadPeriods] update error: {e}")

    def _close(self, metric):
        self._write(metric)
        self._t[metric].reset()

    def close_all(self):
        for m in self._t:
            if self._t[m].row_id is not None:
                self._close(m)

    @staticmethod
    def _who(tr):
        if tr.game:
            return tr.game
        return tr.procs.most_common(1)[0][0] if tr.procs else None

    @staticmethod
    def _desc(tr):
        minutes = max(1, int(round((tr.last - tr.start) / 60))) if tr.start else tr.n
        out = f"{minutes} min"
        if tr.temp_max is not None:
            out += f", max {tr.temp_max:.0f} C"
        return out


load_period_tracker = LoadPeriodTracker()


def rebuild_from_minutes(days: int = 7) -> int:
    """Rebuild the periods of the last `days` from the minute history when
    none were recorded (2026-11-17). Periods start being recorded with the
    release that brought them, and with the old 80 % GPU line; this fills
    the history that is already there. The busiest process of each hour,
    a game first, names the period. Returns the number of periods written."""
    conn = db_manager.get_connection()
    if not conn:
        return 0
    try:
        if conn.execute("SELECT 1 FROM events WHERE event_type='load_period' "
                        "LIMIT 1").fetchone():
            return 0
        since = time.time() - days * 86400
        rows = conn.execute(
            "SELECT timestamp, cpu_avg, gpu_avg, cpu_temp, gpu_temp FROM minute_stats "
            "WHERE timestamp >= ? ORDER BY timestamp", (since,)).fetchall()
        names = {}
        for r in conn.execute(
                "SELECT timestamp, process_name, cpu_avg FROM process_hourly_stats "
                "WHERE timestamp >= ? ORDER BY cpu_avg DESC", (since - 3600,)):
            names.setdefault(int(r[0]), []).append(r[1])
    except Exception:
        return 0
    try:
        from core.game_detect import is_game, display_name
    except Exception:
        is_game = display_name = None
    hour_game, hour_top = {}, {}
    for h, procs in names.items():
        hour_top[h] = procs[0] if procs else None
        if is_game:
            g = next((p for p in procs if is_game(p)), None)
            hour_game[h] = display_name(g) if g else None
    tr = LoadPeriodTracker()
    for ts, cpu, gpu, ct, gt in rows:
        h = int(ts // 3600 * 3600)
        tr.on_minute(ts, {"cpu": cpu or 0.0, "gpu": gpu or 0.0},
                     {"cpu": ct, "gpu": gt},
                     top_process=hour_top.get(h), game=hour_game.get(h))
    tr.close_all()
    try:
        return conn.execute("SELECT COUNT(*) FROM events WHERE "
                            "event_type='load_period'").fetchone()[0]
    except Exception:
        return 0


def periods(start: float, end: float, metric: str | None = None) -> list:
    """Load periods overlapping [start, end), newest first."""
    conn = db_manager.get_connection()
    if not conn:
        return []
    q = ("SELECT id, timestamp, resolved_at, metric, value, baseline, "
         "process_name, description, severity FROM events "
         "WHERE event_type='load_period' AND timestamp < ? "
         "AND COALESCE(resolved_at, timestamp) >= ?")
    args = [end, start]
    if metric:
        q += " AND metric = ?"
        args.append(metric)
    q += " ORDER BY timestamp DESC"
    try:
        rows = conn.execute(q, args).fetchall()
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


def sleeps(start: float, end: float) -> list:
    """Times the PC slept while PC Workman was running (event_type 'sleep',
    recorded by core.scheduler), overlapping [start, end)."""
    conn = db_manager.get_connection()
    if not conn:
        return []
    try:
        rows = conn.execute(
            "SELECT timestamp, resolved_at FROM events WHERE event_type='sleep' "
            "AND timestamp < ? AND COALESCE(resolved_at, timestamp) >= ? "
            "ORDER BY timestamp", (end, start)).fetchall()
    except Exception:
        return []
    return [{"start": r[0], "end": r[1] or r[0]} for r in rows]
