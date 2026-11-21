"""
hck_stats_engine/history.py - Activity history of one component (2026-11-16).

The data behind the CPU / RAM / GPU history pages and behind hck_GPT's
"your CPU has been running higher than usual" note. Read-only: it never
writes the database.

Where the numbers come from (retention in constants.py):
    minute_stats   7 days     one row per minute the app was running
    hourly_stats   90 days    rolled up from minutes
    daily_stats    forever    rolled up from hours
For any range the finest table that still covers it is used, and the most
recent stretch the coarser table does not have yet (today, this hour) is
filled in from the finer one, so the right edge of a chart is always "now".

Temperatures: rows written before 2026-11-16 stored `35 + cpu * 0.5` as the CPU
temperature when there was no sensor. Those values are recognised by that
exact relation and left out; only measured temperatures are shown.
"""
from __future__ import annotations

import time

from hck_stats_engine.constants import (
    SECONDS_PER_HOUR, SECONDS_PER_DAY, RETENTION_MINUTES, RETENTION_HOURLY)

COMPONENTS = ("cpu", "ram", "gpu")
TEMP_FIELD = {"cpu": "cpu_temp", "gpu": "gpu_temp", "ram": None}

# label -> seconds (None = everything recorded)
RANGES = {
    "1H":  SECONDS_PER_HOUR,
    "24H": SECONDS_PER_DAY,
    "7D":  7 * SECONDS_PER_DAY,
    "30D": 30 * SECONDS_PER_DAY,
    "90D": 90 * SECONDS_PER_DAY,
    "1Y":  365 * SECONDS_PER_DAY,
    "ALL": None,
}
HIGH_LOAD = {"cpu": 80.0, "ram": 85.0, "gpu": 85.0}


def _conn():
    try:
        from hck_stats_engine.db_manager import db_manager
        if not db_manager.is_ready:
            return None
        return db_manager.get_connection()
    except Exception:
        return None


def _is_fake_cpu_temp(temp, cpu_avg) -> bool:
    """The pre-2026-11-16 placeholder: temp == 35 + cpu_avg * 0.5 (rounded)."""
    try:
        return abs(float(temp) - (35.0 + float(cpu_avg) * 0.5)) < 0.6
    except (TypeError, ValueError):
        return False


def _table_rows(conn, table, comp, start, end):
    temp_col = {"minute_stats": "cpu_temp, gpu_temp"}.get(
        table, "cpu_temp_avg AS cpu_temp, gpu_temp_avg AS gpu_temp")
    rows = conn.execute(f"""
        SELECT timestamp, {comp}_avg AS avg, {comp}_min AS mn, {comp}_max AS mx,
               cpu_avg, {temp_col}, sample_count
        FROM {table}
        WHERE timestamp >= ? AND timestamp < ?
        ORDER BY timestamp ASC
    """, (start, end)).fetchall()
    out = []
    tf = TEMP_FIELD[comp]
    for r in rows:
        temp = r[tf] if tf else None
        if comp == "cpu" and temp is not None and _is_fake_cpu_temp(temp, r["cpu_avg"]):
            temp = None
        out.append({"ts": float(r["timestamp"]), "avg": r["avg"], "min": r["mn"],
                    "max": r["mx"], "temp": temp,
                    "samples": int(r["sample_count"] or 0)})
    return out


def resolution_for(span: float) -> str:
    """Which table a span is drawn from."""
    if span <= 2 * SECONDS_PER_DAY:
        return "minute"
    if span <= 92 * SECONDS_PER_DAY:
        return "hour"
    return "day"


def series(comp: str, start: float, end: float, max_points: int = 600) -> dict:
    """Points of one component over [start, end).
    Returns {"points": [...], "resolution": "minute"|"hour"|"day"}."""
    assert comp in COMPONENTS
    conn = _conn()
    res = resolution_for(end - start)
    if conn is None:
        return {"points": [], "resolution": res}
    now = time.time()
    try:
        if res == "minute":
            pts = _table_rows(conn, "minute_stats", comp, start, end)
        elif res == "hour":
            pts = _table_rows(conn, "hourly_stats", comp, start, end)
            last = pts[-1]["ts"] + SECONDS_PER_HOUR if pts else start
            if end > now - RETENTION_MINUTES:
                pts += _rollup(_table_rows(conn, "minute_stats", comp,
                                           max(last, start), end), SECONDS_PER_HOUR)
        else:
            pts = _table_rows(conn, "daily_stats", comp, start, end)
            last = pts[-1]["ts"] + SECONDS_PER_DAY if pts else start
            tail = []
            if end > now - RETENTION_HOURLY:
                tail = _table_rows(conn, "hourly_stats", comp, max(last, start), end)
            tail_last = tail[-1]["ts"] + SECONDS_PER_HOUR if tail else max(last, start)
            if end > now - RETENTION_MINUTES:
                tail += _table_rows(conn, "minute_stats", comp, tail_last, end)
            pts += _rollup(tail, SECONDS_PER_DAY)
    except Exception as e:
        print(f"[History] series error: {e}")
        pts = []
    return {"points": _downsample(pts, max_points), "resolution": res}


def _rollup(points, bucket):
    """Combine finer points into buckets (sample-weighted average)."""
    groups: dict = {}
    for p in points:
        key = int(p["ts"] // bucket) * bucket
        groups.setdefault(key, []).append(p)
    out = []
    for key in sorted(groups):
        g = groups[key]
        w = sum(max(p["samples"], 1) for p in g)
        temps = [p["temp"] for p in g if p["temp"] is not None]
        out.append({
            "ts": float(key),
            "avg": sum(p["avg"] * max(p["samples"], 1) for p in g) / w,
            "min": min(p["min"] for p in g),
            "max": max(p["max"] for p in g),
            "temp": (sum(temps) / len(temps)) if temps else None,
            "samples": sum(p["samples"] for p in g),
        })
    return out


def _downsample(points, max_points):
    """Keep the shape: every bucket keeps the point with its highest max, so a
    spike never disappears when a long range is squeezed into the chart."""
    if len(points) <= max_points or max_points <= 0:
        return points
    step = len(points) / max_points
    out, i = [], 0.0
    while int(i) < len(points):
        chunk = points[int(i):max(int(i + step), int(i) + 1)]
        out.append(max(chunk, key=lambda p: p["max"]))
        i += step
    return out


def stats(comp: str, start: float, end: float) -> dict:
    """Summary of one component over [start, end)."""
    pts = series(comp, start, end, max_points=10 ** 9)["points"]
    if not pts:
        return {"has_data": False}
    w = sum(max(p["samples"], 1) for p in pts)
    avg = sum(p["avg"] * max(p["samples"], 1) for p in pts) / w
    peak = max(pts, key=lambda p: p["max"])
    low = min(pts, key=lambda p: p["min"])
    avgs = sorted(p["avg"] for p in pts)
    p95 = avgs[min(int(len(avgs) * 0.95), len(avgs) - 1)]
    high = HIGH_LOAD[comp]
    high_secs = sum(p["samples"] for p in pts if p["avg"] >= high)
    temps = [p["temp"] for p in pts if p["temp"] is not None]
    hot = max((p for p in pts if p["temp"] is not None),
              key=lambda p: p["temp"], default=None)
    return {
        "has_data": True,
        "avg": round(avg, 1),
        "min": round(low["min"], 1),
        "max": round(peak["max"], 1),
        "max_ts": peak["ts"],
        "p95": round(p95, 1),
        "high_load_threshold": high,
        "high_load_minutes": int(round(high_secs / 60)),
        "recorded_hours": round(sum(p["samples"] for p in pts) / 3600, 1),
        "temp_avg": round(sum(temps) / len(temps), 1) if temps else None,
        "temp_max": round(hot["temp"], 1) if hot else None,
        "temp_max_ts": hot["ts"] if hot else None,
        "first_ts": pts[0]["ts"],
        "last_ts": pts[-1]["ts"],
    }


def compare_previous(comp: str, start: float, end: float) -> dict:
    """This period against the one just before it, same length."""
    cur = stats(comp, start, end)
    prev = stats(comp, start - (end - start), start)
    if not (cur.get("has_data") and prev.get("has_data")):
        return {"has_data": False}
    return {"has_data": True, "avg": cur["avg"], "prev_avg": prev["avg"],
            "delta": round(cur["avg"] - prev["avg"], 1)}


def top_processes(comp: str, start: float, end: float, n: int = 5,
                  recorded_seconds: float | None = None) -> list:
    """Heaviest processes in the range. GPU use is not recorded per
    process, so GPU returns [].

    `value` with recorded_seconds given: what the process (all its
    instances together) used on average over the whole recorded time -
    % of CPU, or MB of memory. That is also the ranking, so the number and
    the order agree. Without it: the plain per-instance average."""
    if comp == "gpu":
        return []
    conn = _conn()
    if conn is None:
        return []
    key = "cpu_avg" if comp == "cpu" else "ram_avg_mb"
    peak_col = "cpu_max" if comp == "cpu" else "ram_max_mb"
    # active_seconds adds up every instance of a process (a browser with 12
    # processes "ran" 12 hours in one hour), so the time shown is capped at
    # what the app actually recorded in that hour / day.
    # Hourly rows where they still exist, daily rows for older stretches.
    # Split at the hourly cut-off (a 90-day range starting a second before
    # it used to read only the daily table and come back empty).
    cutoff = time.time() - RETENTION_HOURLY
    parts = []
    if end > cutoff:
        parts.append(("process_hourly_stats", "active_seconds",
                      "LEFT JOIN hourly_stats s ON s.timestamp = p.timestamp",
                      "COALESCE(s.sample_count, 3600)", max(start, cutoff), end))
    if start < cutoff:
        parts.append(("process_daily_stats", "total_active_seconds",
                      "LEFT JOIN daily_stats s ON s.date_str = p.date_str",
                      "COALESCE(s.uptime_minutes * 60, 86400)",
                      start, min(end, cutoff)))
    acc: dict = {}
    try:
        for table, secs, join, cap, a, b in parts:
            for r in conn.execute(f"""
                SELECT p.process_name AS process_name,
                       MAX(p.display_name) AS display_name,
                       SUM(p.{key} * MAX(p.{secs}, 1)) AS weighted,
                       SUM(MAX(p.{secs}, 1)) AS weight,
                       MAX(p.{peak_col}) AS peak,
                       SUM(MIN(p.{secs}, {cap})) AS active
                FROM {table} p {join}
                WHERE p.timestamp >= ? AND p.timestamp < ?
                GROUP BY p.process_name
            """, (a, b)):
                e = acc.setdefault(r["process_name"], {
                    "name": r["display_name"] or r["process_name"],
                    "weighted": 0.0, "weight": 0.0, "peak": 0.0, "active": 0.0})
                e["weighted"] += r["weighted"] or 0
                e["weight"] += r["weight"] or 0
                e["peak"] = max(e["peak"], r["peak"] or 0)
                e["active"] += r["active"] or 0
    except Exception as e:
        print(f"[History] top processes error: {e}")
        return []
    def value(e):
        if recorded_seconds and recorded_seconds > 0:
            return round(e["weighted"] / recorded_seconds, 1)
        return round(e["weighted"] / e["weight"], 1) if e["weight"] else 0.0
    out = [{"name": e["name"], "process": p,
            "value": value(e),
            "peak": round(e["peak"], 1),
            "active_hours": round(min(e["active"], recorded_seconds or e["active"]) / 3600, 1),
            "_load": e["weighted"]} for p, e in acc.items()]
    # Ranked by total contribution (average x time running), not by average:
    # a tool that ran 20 seconds at 8 % is not "the heaviest process".
    out.sort(key=lambda x: x["_load"], reverse=True)
    for x in out:
        x.pop("_load")
    return out[:n]


def events(comp: str, start: float, end: float, limit: int = 8) -> list:
    conn = _conn()
    if conn is None:
        return []
    try:
        rows = conn.execute("""
            SELECT timestamp, event_type, severity, value, baseline, description
            FROM events
            WHERE metric = ? AND timestamp >= ? AND timestamp < ?
              AND event_type != 'load_period'
            ORDER BY timestamp DESC LIMIT ?
        """, (comp, start, end, limit)).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def available_since() -> float | None:
    """Oldest timestamp with component data, any table."""
    conn = _conn()
    if conn is None:
        return None
    oldest = None
    for t in ("daily_stats", "hourly_stats", "minute_stats"):
        try:
            v = conn.execute(f"SELECT MIN(timestamp) FROM {t}").fetchone()[0]
            if v is not None and (oldest is None or v < oldest):
                oldest = float(v)
        except Exception:
            pass
    return oldest


def recent_vs_usual(comp: str, recent_days: int = 2, usual_days: int = 14,
                    now: float | None = None) -> dict:
    """For hck_GPT: the last `recent_days` against the `usual_days` before
    them. `notable` is True only with enough data on both sides and a
    difference a person would notice."""
    now = time.time() if now is None else now
    r_start = now - recent_days * SECONDS_PER_DAY
    u_start = r_start - usual_days * SECONDS_PER_DAY
    recent = stats(comp, r_start, now)
    usual = stats(comp, u_start, r_start)
    if not (recent.get("has_data") and usual.get("has_data")):
        return {"notable": False, "reason": "not enough history"}
    if recent["recorded_hours"] < 2 or usual["recorded_hours"] < 6:
        return {"notable": False, "reason": "not enough hours recorded"}
    delta = recent["avg"] - usual["avg"]
    ratio = recent["avg"] / usual["avg"] if usual["avg"] > 0.5 else None
    # notable: at least 10 points higher AND at least 1.5x, or 15 points
    notable = (delta >= 15) or (delta >= 10 and ratio is not None and ratio >= 1.5)
    return {"notable": bool(notable), "recent_avg": recent["avg"],
            "usual_avg": usual["avg"], "delta": round(delta, 1),
            "recent_days": recent_days, "usual_days": usual_days}
