"""
ui/pages/activity_memory.py - Activity Memory: the full history of one
component (CPU, RAM or GPU), from the last hour back to the first day the
app ran (2026-11-16).

Opened by clicking a hardware card on the dashboard, from a hck_GPT note
("[-> CPU History]") and by switching component in its own header.

What is on the page, top to bottom:
    header       component name, hardware model, CPU / RAM / GPU switch
    toolbar      range chips 1H .. ALL, previous / next period, back to now
    overview     the whole recorded history as one strip of days; click or
                 drag it to jump months back
    timeline     average line with the min-max band and, for CPU and GPU,
                 the measured temperature; drag to move in time, scroll to
                 zoom, double-click to open that moment closer
    stat tiles   average, lowest, peak and when, 95 % line, time under high
                 load, how much of the period was recorded, temperature,
                 change against the period before
    bottom       heaviest processes of the period, recorded load spikes

Time on the x axis is real time: hours the PC was off stay empty instead of
being squeezed out, so the chart never suggests activity that did not
happen. All queries run on a worker thread (hck_stats_engine.history).
"""
from __future__ import annotations

from utils.fonts import UI as _FONT_UI, HDR as _FONT_HDR, HEAVY as _FONT_HEAVY, LIGHT as _FONT_LIGHT  # noqa: F401
import bisect
import math
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta

from utils.i18n import t, get_lang

try:
    from utils.fonts import UI as _BODY, MONO as _MONO
except ImportError:
    _BODY, _MONO = _FONT_UI, "Consolas"
_HDR = _FONT_HDR
_BLACK = _FONT_HEAVY

try:
    import utils.ui_scale as _uis
    _sc = _uis.scale
except Exception:
    def _sc(px):
        return px

BG = "#0a0e14"
PANEL = "#0f141c"
PANEL_HI = "#141b26"
LINE = "#1a2230"
GRID = "#131a26"
TEXT = "#c4cfdf"
MUTED = "#6b7a90"
DIM = "#6c7a91"
WINE = "#8b1e3f"          # the bordeaux accent of this page family
WINE_SOFT = "#2a0f19"
TEMP_COL = "#f97316"
UP_COL = "#ef4444"
DOWN_COL = "#10b981"

ACCENT = {"cpu": "#3b82f6", "ram": "#fbbf24", "gpu": "#10b981", "hardware": "#a78bfa"}
# "hardware" = CPU, RAM and GPU on one time axis (2026-11-20)
HW_COMPS = ("cpu", "ram", "gpu")
ZOOM_ORDER = ["1H", "24H", "7D", "30D", "90D", "1Y", "ALL"]
# The mouse wheel goes in smaller steps than the buttons (2026-11-20: 1H to
# 24H in one notch lost the place you were looking at); these spans exist
# only for the wheel and are not remembered as the page's range.
WHEEL_ORDER = ["1H", "3H", "6H", "12H", "24H", "3D", "7D", "14D", "30D", "90D", "1Y", "ALL"]
WHEEL_SPANS = {"3H": 3 * 3600, "6H": 6 * 3600, "12H": 12 * 3600,
               "3D": 3 * 86400, "14D": 14 * 86400}
STEP = {"minute": 60, "hour": 3600, "day": 86400}
SETTING_KEY = "activity_range"


# ── formatting ────────────────────────────────────────────────────────────────

def _num(v, d=1):
    if v is None:
        return "--"
    s = f"{v:.{d}f}"
    return s.replace(".", ",") if get_lang() == "pl" else s


def _months():
    names = t("activity.months").split()
    return names if len(names) == 12 else [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _day(dt: datetime, year=False) -> str:
    s = f"{dt.day} {_months()[dt.month - 1]}"
    return f"{s} {dt.year}" if year else s


def fmt_moment(ts: float, resolution: str) -> str:
    """When a point happened, as precise as its resolution."""
    dt = datetime.fromtimestamp(ts)
    if resolution == "minute":
        return f"{_day(dt)}, {dt:%H:%M}"
    if resolution == "hour":
        end = dt + timedelta(hours=1)
        return f"{_day(dt)}, {dt:%H:00}-{end:%H:00}"
    return _day(dt, year=True)


def fmt_period(start: float, end: float) -> str:
    a, b = datetime.fromtimestamp(start), datetime.fromtimestamp(end)
    if end - start <= 2 * 86400:
        if a.date() == b.date():
            return f"{_day(a)}  {a:%H:%M} - {b:%H:%M}"
        return f"{_day(a)} {a:%H:%M}  -  {_day(b)} {b:%H:%M}"
    return f"{_day(a, year=a.year != b.year)}  -  {_day(b, year=True)}"


def fmt_minutes(m) -> str:
    m = int(round(m or 0))
    if m < 60:
        return t("activity.dur_min", n=m)
    h, mm = divmod(m, 60)
    if h < 48:
        return t("activity.dur_h_min", h=h, m=mm) if mm else t("activity.dur_h", h=h)
    d, hh = divmod(h, 24)
    return t("activity.dur_d_h", d=d, h=hh)


def fmt_short(m) -> str:
    """Duration that fits a stat tile: 45 min / 19,6 h / 12,5 d."""
    m = m or 0
    if m < 60:
        return t("activity.dur_min", n=int(round(m)))
    if m < 48 * 60:
        return t("activity.dur_h", h=_num(m / 60))
    return t("activity.dur_d", d=_num(m / 1440))


def _blend(c1: str, c2: str, k: float) -> str:
    """k of c1 over c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(x * k + y * (1 - k)):02x}" for x, y in zip(a, b))


# ── x-axis ticks ──────────────────────────────────────────────────────────────

_TICK_STEPS = [
    ("s", 300), ("s", 900), ("s", 1800), ("s", 3600), ("s", 3 * 3600),
    ("s", 6 * 3600), ("s", 12 * 3600), ("d", 1), ("d", 2), ("d", 7),
    ("d", 14), ("m", 1), ("m", 2), ("m", 3), ("m", 6), ("y", 1)]


def _approx(kind, n):
    return {"s": n, "d": n * 86400, "m": n * 30.4 * 86400, "y": n * 365 * 86400}[kind]


def time_ticks(start: float, end: float, max_ticks: int):
    """[(ts, label)] aligned to local clock/calendar boundaries."""
    span = max(end - start, 1)
    kind, n = _TICK_STEPS[-1]
    for k, v in _TICK_STEPS:
        if span / _approx(k, v) <= max(max_ticks, 2):
            kind, n = k, v
            break
    out = []
    a = datetime.fromtimestamp(start)
    if kind == "s":
        midnight = datetime(a.year, a.month, a.day)
        base = midnight.timestamp()
        k = math.ceil((start - base) / n)
        ts = base + k * n
        while ts <= end and len(out) < 60:
            dt = datetime.fromtimestamp(ts)
            lab = _day(dt) if (dt.hour == 0 and dt.minute == 0) else f"{dt:%H:%M}"
            out.append((ts, lab))
            ts += n
    elif kind == "d":
        d = datetime(a.year, a.month, a.day)
        if d.timestamp() < start:
            d += timedelta(days=1)
        while d.timestamp() <= end and len(out) < 60:
            out.append((d.timestamp(), _day(d)))
            d += timedelta(days=n)
    else:
        step_m = n if kind == "m" else 12
        y, m = a.year, a.month
        d = datetime(y, m, 1)
        if d.timestamp() < start:
            m += 1
        while True:
            y2, m2 = y + (m - 1) // 12, (m - 1) % 12 + 1
            d = datetime(y2, m2, 1)
            if d.timestamp() > end or len(out) >= 60:
                break
            if (m2 - 1) % step_m == 0 or step_m == 1:
                lab = _months()[m2 - 1]
                if m2 == 1 or not out:
                    lab = f"{lab} {y2}"
                out.append((d.timestamp(), lab))
            m += 1
    return out


def segments(points, resolution):
    """Split points where the PC was not recording (gap > 1.5 steps)."""
    step = STEP[resolution]
    segs, cur = [], []
    for p in points:
        if cur and p["ts"] - cur[-1]["ts"] > step * 1.5:
            segs.append(cur)
            cur = []
        cur.append(p)
    if cur:
        segs.append(cur)
    return segs


# ── timeline chart ────────────────────────────────────────────────────────────

class TimelineChart:
    """Real-time x axis, average line, min-max band, optional temperature."""

    def __init__(self, parent, accent, on_pan, on_zoom, on_drill, title=""):
        self.accent = accent
        self.title = title
        self.band = _blend(accent, PANEL, 0.22)
        self.on_pan, self.on_zoom, self.on_drill = on_pan, on_zoom, on_drill
        self.cv = tk.Canvas(parent, bg=PANEL, highlightthickness=0,
                            cursor="crosshair")
        self.cv.pack(fill="both", expand=True)
        self.points, self.events = [], []
        self.start = time.time() - 86400
        self.end = time.time()
        self.resolution = "minute"
        self.show_temp = False
        self.loading = True
        self.shift = 0.0
        self.hover_x = None
        self._drag_x0 = None
        self._centers = []
        cv = self.cv
        cv.bind("<Configure>", lambda e=None: self.draw())
        cv.bind("<Motion>", self._motion)
        cv.bind("<Leave>", lambda e=None: self._set_hover(None))
        cv.bind("<ButtonPress-1>", self._press)
        cv.bind("<B1-Motion>", self._drag)
        cv.bind("<ButtonRelease-1>", self._release)
        cv.bind("<Double-Button-1>", self._double)
        cv.bind("<MouseWheel>", self._wheel)

    # data
    def set_data(self, points, start, end, resolution, events=(), show_temp=False,
                 periods=(), sleeps=(), sessions=()):
        self.points = points
        self.sessions = list(sessions)
        self.sleeps = list(sleeps)
        self.start, self.end = start, end
        self.resolution = resolution
        self.events = list(events)
        self.periods = list(periods)
        self.show_temp = show_temp
        self.loading = False
        self.shift = 0.0
        half = STEP[resolution] / 2
        self._centers = [p["ts"] + half for p in points]
        self.draw()

    def set_loading(self):
        self.loading = True
        self.draw()

    # geometry
    def _geom(self):
        W = max(self.cv.winfo_width(), 50)
        H = max(self.cv.winfo_height(), 50)
        PL, PT, PB = 48, 16, 30
        PR = 48 if self._has_temp() else 18
        if getattr(self, "fixed_pr", None):
            PR = self.fixed_pr          # charts that share one time axis
        return W, H, PL, PR, PT, PB

    def _has_temp(self):
        return self.show_temp and any(p.get("temp") is not None for p in self.points)

    def _view(self):
        return self.start + self.shift, self.end + self.shift

    def _x(self, ts, PL, cw):
        a, b = self._view()
        return PL + (ts - a) / max(b - a, 1) * cw

    def _ts_at(self, x):
        W, H, PL, PR, PT, PB = self._geom()
        cw = W - PL - PR
        a, b = self._view()
        return a + (x - PL) / max(cw, 1) * (b - a)

    # drawing
    def draw(self):
        cv = self.cv
        try:
            if not cv.winfo_exists():
                return
        except Exception:
            return
        cv.delete("all")
        W, H, PL, PR, PT, PB = self._geom()
        cw, ch = W - PL - PR, H - PT - PB
        if self.title:
            cv.create_text(PL, 2, anchor="nw", text=self.title,
                           font=(_HDR, 8), fill=self.accent)

        def vy(v):
            return PT + ch * (1 - max(0.0, min(100.0, v)) / 100.0)

        for v in (0, 25, 50, 75, 100):
            y = vy(v)
            cv.create_line(PL, y, W - PR, y, fill=GRID if v else LINE,
                           dash=() if v in (0, 100) else (2, 4))
            cv.create_text(PL - 8, y, text=f"{v}%", anchor="e",
                           font=(_MONO, 8), fill=DIM)

        a, b = self._view()
        for ts, lab in time_ticks(a, b, max(2, int(cw / 96))):
            x = self._x(ts, PL, cw)
            if PL <= x <= W - PR:
                cv.create_line(x, PT, x, PT + ch, fill=GRID, dash=(1, 5))
                cv.create_line(x, PT + ch, x, PT + ch + 4, fill=LINE)
                cv.create_text(x, PT + ch + 15, text=lab, font=(_BODY, 8),
                               fill=MUTED)

        # "now" edge
        now = time.time()
        if a < now <= b + 1:
            x = self._x(now, PL, cw)
            cv.create_line(x, PT, x, PT + ch, fill=_blend(WINE, PANEL, 0.7),
                           dash=(3, 3))
            cv.create_text(x - 4, PT + 2, text=t("activity.now"), anchor="ne",
                           font=(_BODY, 7, "bold"), fill=_blend(WINE, TEXT, 0.6))

        if self.loading and not self.points:
            cv.create_text(PL + cw / 2, PT + ch / 2, text=t("activity.loading"),
                           font=(_BODY, 10), fill=MUTED)
            return
        if not self.points:
            cv.create_text(PL + cw / 2, PT + ch / 2 - 10,
                           text=t("activity.no_records"),
                           font=(_HDR, 11), fill=MUTED)
            cv.create_text(PL + cw / 2, PT + ch / 2 + 12,
                           text=t("activity.no_records_hint"),
                           font=(_BODY, 8), fill=DIM, width=max(cw - 40, 100))
            return

        # game sessions: the same band about 40 % more transparent, so a
        # light game (Stardew, PlateUp) shows up next to the heavy stretches
        sess_bg = _blend(WINE, PANEL, 0.13)
        for ses in getattr(self, "sessions", []):
            x0 = max(PL, self._x(ses["timestamp"], PL, cw))
            x1 = min(W - PR, self._x(ses["end"], PL, cw))
            if x1 - x0 < 1:
                if PL <= x0 <= W - PR:
                    x1 = x0 + 2
                else:
                    continue
            cv.create_rectangle(x0, PT, x1, PT + ch, fill=sess_bg, outline="")
            cv.create_line(x0, PT + ch - 1, x1, PT + ch - 1, fill=_blend(WINE, PANEL, 0.6), width=2)
            who = ses.get("process_name") or ""
            if who and x1 - x0 > 70:
                cv.create_text(x0 + 5, PT + ch - 6, text=who, anchor="sw",
                               font=(_BODY, 7), fill=_blend(WINE, TEXT, 0.35))

        # load periods: a bordeaux band behind the data, the game on top
        band_bg = _blend(WINE, PANEL, 0.22)
        for per in getattr(self, "periods", []):
            x0 = max(PL, self._x(per["timestamp"], PL, cw))
            x1 = min(W - PR, self._x(per["end"], PL, cw))
            if x1 - x0 < 1:
                if PL <= x0 <= W - PR:
                    x1 = x0 + 2
                else:
                    continue
            cv.create_rectangle(x0, PT, x1, PT + ch, fill=band_bg, outline="")
            cv.create_line(x0, PT, x1, PT, fill=WINE, width=3)
            who = per.get("process_name") or ""
            if who and x1 - x0 > 70:
                cv.create_text(x0 + 5, PT + 6, text=who, anchor="nw",
                               font=(_BODY, 7, "bold"), fill=_blend(WINE, TEXT, 0.45))

        half = STEP[self.resolution] / 2
        x = lambda ts: self._x(ts + half, PL, cw)  # noqa: E731
        segs = segments(self.points, self.resolution)
        for seg in segs:
            if len(seg) == 1:
                p = seg[0]
                px = x(p["ts"])
                cv.create_line(px, vy(p["min"]), px, vy(p["max"]),
                               fill=self.band, width=4)
                cv.create_oval(px - 2.5, vy(p["avg"]) - 2.5, px + 2.5,
                               vy(p["avg"]) + 2.5, fill=self.accent, outline="")
                continue
            top = [c for p in seg for c in (x(p["ts"]), vy(p["max"]))]
            bot = [c for p in reversed(seg) for c in (x(p["ts"]), vy(p["min"]))]
            cv.create_polygon(top + bot, fill=self.band, outline="")
            line = [c for p in seg for c in (x(p["ts"]), vy(p["avg"]))]
            cv.create_line(line, fill=self.accent, width=2)

        if self._has_temp():
            tlo, thi = self._temp_scale()

            def ty(v):
                return PT + ch * (1 - (v - tlo) / max(thi - tlo, 1))
            for seg in segs:
                pts = [c for p in seg if p.get("temp") is not None
                       for c in (x(p["ts"]), ty(p["temp"]))]
                if len(pts) >= 4:
                    cv.create_line(pts, fill=TEMP_COL, width=1, dash=(4, 2))
            for v in (tlo, (tlo + thi) / 2, thi):
                cv.create_text(W - PR + 8, ty(v), text=f"{v:.0f}°", anchor="w",
                               font=(_MONO, 8), fill=_blend(TEMP_COL, PANEL, 0.6))

        for ev in self.events:
            ex = self._x(ev["timestamp"], PL, cw)
            if PL <= ex <= W - PR:
                cv.create_polygon(ex - 4, PT - 1, ex + 4, PT - 1, ex, PT + 6,
                                  fill=UP_COL, outline="")

        if self.hover_x is not None and self._drag_x0 is None:
            self._draw_hover(cv, W, H, PL, PR, PT, ch, cw, vy, x)

    def _temp_scale(self):
        temps = [p["temp"] for p in self.points if p.get("temp") is not None]
        lo = math.floor((min(temps) - 5) / 10) * 10
        hi = math.ceil((max(temps) + 5) / 10) * 10
        return lo, max(hi, lo + 20)

    def _nearest(self, ts):
        if not self._centers:
            return None
        i = bisect.bisect_left(self._centers, ts)
        cand = [j for j in (i - 1, i) if 0 <= j < len(self._centers)]
        j = min(cand, key=lambda k: abs(self._centers[k] - ts))
        if abs(self._centers[j] - ts) > STEP[self.resolution] * 1.5:
            return None
        return j

    def _draw_hover(self, cv, W, H, PL, PR, PT, ch, cw, vy, x):
        hx = self.hover_x
        if not (PL <= hx <= W - PR):
            return
        j = self._nearest(self._ts_at(hx))
        if j is None:
            cv.create_line(hx, PT, hx, PT + ch, fill=DIM, dash=(2, 3))
            ts_h = self._ts_at(hx)
            slept = next((sl for sl in getattr(self, "sleeps", [])
                          if sl["start"] <= ts_h <= sl["end"]), None)
            lines = [(MUTED, fmt_moment(ts_h, self.resolution)),
                     (DIM, t("activity.tip_slept",
                             v=fmt_minutes((slept["end"] - slept["start"]) / 60))
                      if slept else t("activity.tip_off"))]
        else:
            p = self.points[j]
            px = x(p["ts"])
            cv.create_line(px, PT, px, PT + ch, fill=_blend(WINE, PANEL, 0.8))
            cv.create_oval(px - 4, vy(p["avg"]) - 4, px + 4, vy(p["avg"]) + 4,
                           fill=self.accent, outline="#ffffff")
            lines = [(TEXT, fmt_moment(p["ts"], self.resolution)),
                     (self.accent, f"{t('activity.avg')}  {_num(p['avg'])}%"),
                     (MUTED, f"{t('activity.range_minmax')}  {_num(p['min'], 0)}-{_num(p['max'], 0)}%")]
            if p.get("temp") is not None:
                lines.append((TEMP_COL, f"{t('activity.temp')}  {_num(p['temp'], 0)} °C"))
            lines.append((DIM, t("activity.tip_recorded", v=fmt_minutes(p["samples"] / 60))))
            for per in getattr(self, "periods", []):
                if per["timestamp"] <= p["ts"] + STEP[self.resolution] and p["ts"] <= per["end"]:
                    lines.append((_blend(WINE, TEXT, 0.35), t(
                        "activity.tip_period", m=per["minutes"],
                        who=per.get("process_name") or "-")))
                    break
            hx = px
        tw = max(len(s) for _, s in lines) * 7 + 20
        th = len(lines) * 17 + 12
        tx = hx + 14 if hx + 14 + tw < W - PR else hx - 14 - tw
        ty = PT + 8
        cv.create_rectangle(tx, ty, tx + tw, ty + th, fill="#0b0f16",
                            outline=_blend(WINE, PANEL, 0.75))
        cv.create_rectangle(tx, ty, tx + 3, ty + th, fill=WINE, outline="")
        for i, (col, s) in enumerate(lines):
            cv.create_text(tx + 12, ty + 14 + i * 17, text=s, anchor="w",
                           fill=col, font=(_BODY, 9, "bold") if i == 0 else (_BODY, 9))

    # interaction
    def _set_hover(self, x):
        self.hover_x = x
        self.draw()

    def _motion(self, e=None):
        if e is not None:
            self._set_hover(e.x)

    def _press(self, e=None):
        self._drag_x0 = e.x if e is not None else None

    def _drag(self, e=None):
        if self._drag_x0 is None or e is None:
            return
        W, H, PL, PR, PT, PB = self._geom()
        span = self.end - self.start
        self.shift = -(e.x - self._drag_x0) / max(W - PL - PR, 1) * span
        self.cv.config(cursor="fleur")
        self.draw()

    def _release(self, e=None):
        shift, self._drag_x0 = self.shift, None
        self.cv.config(cursor="crosshair")
        span = self.end - self.start
        if abs(shift) > span * 0.01:
            self.on_pan(shift)
        else:
            self.shift = 0.0
            self.draw()

    def _double(self, e=None):
        if e is not None:
            self.on_drill(self._ts_at(e.x))

    def _wheel(self, e=None):
        if e is not None:
            self.on_zoom(self._ts_at(e.x), -1 if e.delta > 0 else 1)
        return "break"


# ── overview strip: the whole history ────────────────────────────────────────

class OverviewStrip:
    def __init__(self, parent, accent, on_jump):
        self.accent = accent
        self.on_jump = on_jump
        self.cv = tk.Canvas(parent, bg=BG, height=_sc(34), highlightthickness=0,
                            cursor="hand2")
        self.cv.pack(fill="x")
        self.days, self.first, self.win = [], None, (0, 0)
        self.cv.bind("<Configure>", lambda e=None: self.draw())
        self.cv.bind("<Button-1>", self._jump)
        self.cv.bind("<B1-Motion>", self._jump)

    def set_data(self, days, first, win):
        self.days, self.first, self.win = days, first, win
        self.draw()

    def _span(self):
        now = time.time()
        first = self.first if self.first else now - 30 * 86400
        first = min(first, self.win[0])
        return first, now

    def draw(self):
        cv = self.cv
        cv.delete("all")
        W, H = max(cv.winfo_width(), 50), max(cv.winfo_height(), 20)
        PL, PR, top, bot = 48, 18, 4, H - 12
        cw = W - PL - PR
        a, b = self._span()

        def x(ts):
            return PL + (ts - a) / max(b - a, 1) * cw
        cv.create_rectangle(PL, top, W - PR, bot, fill=PANEL, outline=LINE)
        cv.create_text(PL - 8, (top + bot) / 2, text=t("activity.all_short"),
                       anchor="e", font=(_BODY, 7, "bold"), fill=DIM)
        bw = max(cw / max((b - a) / 86400, 1), 1)
        dim = _blend(self.accent, PANEL, 0.45)
        for p in self.days:
            px = x(p["ts"])
            h = (bot - top - 2) * max(0.04, p["avg"] / 100)
            cv.create_rectangle(px, bot - 1 - h, px + max(bw - 1, 1), bot - 1,
                                fill=dim, outline="")
        x0, x1 = x(self.win[0]), x(self.win[1])
        if x1 - x0 < 4:
            mid = (x0 + x1) / 2
            x0, x1 = mid - 2, mid + 2
        cv.create_rectangle(x0, top, x1, bot, outline=WINE, width=2)
        cv.create_text(PL, H - 5, text=_day(datetime.fromtimestamp(a), year=True),
                       anchor="w", font=(_BODY, 7), fill=DIM)
        cv.create_text(W - PR, H - 5, text=t("activity.now"), anchor="e",
                       font=(_BODY, 7), fill=DIM)

    def _jump(self, e=None):
        if e is None:
            return
        W = max(self.cv.winfo_width(), 50)
        PL, PR = 48, 18
        a, b = self._span()
        frac = min(max((e.x - PL) / max(W - PL - PR, 1), 0), 1)
        self.on_jump(a + frac * (b - a))


# ── page ──────────────────────────────────────────────────────────────────────

def _saved_range(app) -> str:
    try:
        from utils.prefs_io import load_json
        v = (load_json(app._app_settings_file(), {}) or {}).get(SETTING_KEY)
        return v if v in ZOOM_ORDER else "24H"
    except Exception:
        return "24H"


def _remember_range(app, label: str) -> None:
    try:
        from utils.prefs_io import update_json
        update_json(app._app_settings_file(), **{SETTING_KEY: label})
    except Exception:
        pass


def _hardware_name(app, comp: str) -> str:
    try:
        if comp == "cpu":
            return app._cpu_marketing_name()
        if comp == "gpu":
            return app._gpu_name_nonblocking()
        import psutil
        return t("activity.ram_total", gb=_num(psutil.virtual_memory().total / 1024 ** 3))
    except Exception:
        return ""


class ActivityMemoryPage:
    def __init__(self, app, parent, comp: str):
        from hck_stats_engine import history
        self.h = history
        self.app, self.parent, self.comp = app, parent, comp
        self.hw = comp == "hardware"
        self.accent = ACCENT[comp]
        st = getattr(app, "_activity_state", None) or {}
        self.span_label = st.get("span") or _saved_range(app)
        self.end = st.get("end")          # None = follow "now"
        self.show_temp = st.get("temp", True)
        self._gen = 0
        self._result = None
        self._overview_loaded = False
        self._first_ts = None
        self._chips = {}

        self.root = tk.Frame(parent, bg=BG)
        self.root.pack(fill="both", expand=True)
        self._build_header()
        self._build_toolbar()
        # bottom-up packing: fixed parts first, the chart takes what is left
        self._build_bottom()
        self._build_tiles()
        self.overview = OverviewStrip(self._wrap(pady=(6, 0), side="bottom"),
                                      self.accent, self._jump_to)
        chart_box = self._wrap(pady=(8, 0), side="top", expand=True)
        if self.hw:
            # three charts, one time axis: pan and zoom move all of them
            self.charts = {}
            for c in HW_COMPS:
                f = tk.Frame(chart_box, bg=BG)
                f.pack(fill="both", expand=True, pady=(0, 4))
                self.charts[c] = TimelineChart(f, ACCENT[c], self._pan, self._zoom,
                                               self._drill, title=c.upper())
                # a small asked-for height, so "expand" shares the room in
                # three equal parts (Tk's default canvas height let CPU take
                # it all and pushed GPU off the page)
                self.charts[c].cv.config(height=40)
                self.charts[c].fixed_pr = 48     # same x axis on all three
                f.pack_propagate(False)
                f.config(height=40)
            self.chart = self.charts["cpu"]
        else:
            self.chart = TimelineChart(chart_box, self.accent, self._pan,
                                       self._zoom, self._drill)
        self.load()

    # layout helpers
    def _wrap(self, pady=(0, 0), side="top", expand=False):
        f = tk.Frame(self.root, bg=BG)
        f.pack(side=side, fill="both" if expand else "x", expand=expand,
               padx=16, pady=pady)
        return f

    def _build_header(self):
        cv = tk.Canvas(self.root, bg=BG, height=_sc(60), highlightthickness=0)
        cv.pack(fill="x")
        name = _hardware_name(self.app, self.comp)
        accent = self.accent

        def draw(e=None):
            cv.delete("all")
            W, H = cv.winfo_width(), cv.winfo_height()
            if W < 20:
                return
            for y in range(H):
                k = y / H
                cv.create_line(0, y, W, y, fill=_blend("#1a0a11", BG, 1 - k * 0.9))
            cv.create_line(0, H - 1, W, H - 1, fill=_blend(WINE, BG, 0.5))
            cv.create_rectangle(0, 0, 4, H, fill=WINE, outline="")
            tid = cv.create_text(20, H / 2 - 2, text=self.comp.upper(), anchor="w",
                                 font=(_BLACK, 22), fill=accent)
            bx = (cv.bbox(tid) or (0, 0, 80, 0))[2] + 14
            cv.create_line(bx, H / 2 - 18, bx, H / 2 + 14, fill=_blend(WINE, BG, 0.7))
            cv.create_text(bx + 14, H / 2 - 9, text=t("activity.title"), anchor="w",
                           font=(_HDR, 13), fill=TEXT)
            cv.create_text(bx + 14, H / 2 + 12,
                           text=(t("activity.hw_subtitle") if self.hw
                                 else name or t("activity.subtitle")),
                           anchor="w", font=(_BODY, 8), fill=MUTED)
            cv.create_text(W - 16, H - 10, text=f"‹ {t('nav.back_dashboard')}",
                           anchor="e", font=(_BODY, 8), fill=DIM, tags="back")
            # component switch
            x = W - 16
            for c in reversed(("cpu", "ram", "gpu", "hardware")):
                lab = c.upper()
                w = 86 if c == "hardware" else 46
                x0 = x - w
                on = c == self.comp
                cv.create_rectangle(x0, 9, x, 31, outline=WINE if on else LINE,
                                    fill=WINE_SOFT if on else BG, tags=("sw", f"sw_{c}"))
                cv.create_text((x0 + x) / 2, 20, text=lab,
                               font=(_HDR, 9), fill=ACCENT[c] if on else MUTED,
                               tags=("sw", f"sw_{c}"))
                cv.tag_bind(f"sw_{c}", "<Button-1>",
                            lambda e=None, c=c: self._switch_comp(c))
                x = x0 - 6

        cv.bind("<Configure>", draw)
        cv.tag_bind("back", "<Button-1>", lambda e=None: self._back())
        cv.tag_bind("back", "<Enter>", lambda e=None: cv.itemconfig("back", fill=TEXT))
        cv.tag_bind("back", "<Leave>", lambda e=None: cv.itemconfig("back", fill=DIM))
        cv.tag_bind("sw", "<Enter>", lambda e=None: cv.config(cursor="hand2"))
        cv.tag_bind("sw", "<Leave>", lambda e=None: cv.config(cursor=""))

    def _chip(self, parent, text, cmd, key=None):
        lb = tk.Label(parent, text=text, font=(_HDR, 9), bg=PANEL, fg=MUTED,
                      padx=10, pady=3, cursor="hand2")
        lb.pack(side="left", padx=(0, 4))
        lb.bind("<Button-1>", lambda e=None: cmd())
        lb.bind("<Enter>", lambda e=None: lb.config(bg=WINE_SOFT)
                if lb.cget("fg") != TEXT else None)
        lb.bind("<Leave>", lambda e=None: lb.config(bg=PANEL)
                if lb.cget("fg") != TEXT else None)
        if key:
            self._chips[key] = lb
        return lb

    def _build_toolbar(self):
        bar = self._wrap(pady=(10, 0))
        # right side first: it must never be pushed off by the chips
        right = tk.Frame(bar, bg=BG)
        right.pack(side="right")
        if self.comp in ("cpu", "gpu", "hardware"):
            self._temp_chip = self._chip(right, t("activity.temp_toggle"),
                                         self._toggle_temp)
        else:
            self._temp_chip = None
        self._chip(right, f"{t('activity.back_now')}  ⟶", self._to_now)
        for lab in ZOOM_ORDER:
            self._chip(bar, t(f"activity.r_{lab.lower()}"),
                       lambda lab=lab: self._set_span(lab), key=lab)
        nav = tk.Frame(bar, bg=BG)
        nav.pack(side="left", padx=(10, 0))
        self._chip(nav, "◀", lambda: self._step(-1))
        self.period_lbl = tk.Label(nav, text="", font=(_BODY, 9), bg=BG, fg=TEXT)
        self.period_lbl.pack(side="left", padx=8)
        self._next_chip = self._chip(nav, "▶", lambda: self._step(1))
        self._paint_chips()

        hint = self._wrap(pady=(4, 0))
        self.res_lbl = tk.Label(hint, text="", font=(_BODY, 7), bg=BG, fg=DIM,
                                anchor="w")
        self.res_lbl.pack(side="left")
        tk.Label(hint, text=t("activity.hint"), font=(_BODY, 7), bg=BG, fg=DIM,
                 anchor="e").pack(side="right")

    def _paint_chips(self):
        for lab, lb in self._chips.items():
            on = lab == self.span_label
            lb.config(bg=WINE if on else PANEL, fg=TEXT if on else MUTED)
        if self._temp_chip is not None:
            self._temp_chip.config(fg=TEMP_COL if self.show_temp else MUTED)

    def _build_tiles(self):
        self.tiles_box = self._wrap(pady=(8, 0), side="bottom")
        self.tiles = {}
        if self.hw:
            keys = ["cpu", "ram", "gpu", "cpu_t", "gpu_t", "recorded"]
        else:
            keys = ["avg", "min", "max", "p95", "high", "recorded"]
            if self.comp != "ram":
                keys.append("temp")
            keys.append("prev")
        for i, k in enumerate(keys):
            f = tk.Frame(self.tiles_box, bg=PANEL, highlightthickness=1,
                         highlightbackground=LINE)
            f.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            self.tiles_box.grid_columnconfigure(i, weight=1, uniform="tile")
            cap = tk.Label(f, text="", font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED,
                           anchor="w")
            cap.pack(fill="x", padx=10, pady=(5, 0))
            val = tk.Label(f, text="--", font=(_HDR, 13), bg=PANEL, fg=TEXT,
                           anchor="w")
            val.pack(fill="x", padx=10)
            sub = tk.Label(f, text="", font=(_BODY, 7), bg=PANEL, fg=DIM, anchor="w")
            sub.pack(fill="x", padx=10, pady=(0, 5))
            self.tiles[k] = (cap, val, sub)

    def _build_bottom(self):
        box = self._wrap(pady=(8, 10), side="bottom")
        box.grid_columnconfigure(0, weight=3, uniform="b")
        box.grid_columnconfigure(1, weight=2, uniform="b")
        self.proc_box = tk.Frame(box, bg=PANEL, height=_sc(112),
                                 highlightthickness=1, highlightbackground=LINE)
        self.proc_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.proc_box.pack_propagate(False)
        self.ev_box = tk.Frame(box, bg=PANEL, height=_sc(112),
                               highlightthickness=1, highlightbackground=LINE)
        self.ev_box.grid(row=0, column=1, sticky="nsew")
        self.ev_box.pack_propagate(False)

    # navigation inside the page
    def _span_s(self, label=None):
        label = label or self.span_label
        s = self.h.RANGES[label] if label in self.h.RANGES else WHEEL_SPANS.get(label, 86400)
        if s is None:
            first = self._first_ts or (time.time() - 30 * 86400)
            s = max(time.time() - first, 86400)
        return s

    def _window(self):
        span = self._span_s()
        end = time.time() if self.end is None else self.end
        return end - span, end

    def _set_end(self, end):
        now = time.time()
        if end is None or end >= now - 30:
            self.end = None
        else:
            # the window never starts before the first record (it allowed
            # three quarters of empty chart, easy to get lost in)
            first = self._first_ts or (now - 365 * 86400)
            self.end = max(end, first + self._span_s())
            if self.end >= now - 30:
                self.end = None
        self.load()

    def _set_span(self, label, center=None):
        if label == self.span_label and center is None:
            return
        self.span_label = label
        if label in ZOOM_ORDER:
            _remember_range(self.app, label)
        if label == "ALL":
            self.end = None
        elif center is not None:
            self.end = center + self._span_s() / 2
        self._paint_chips()
        self._set_end(self.end)

    def _step(self, direction):
        a, b = self._window()
        self._set_end(b + direction * (b - a))

    def _to_now(self):
        self._set_end(None)

    def _pan(self, shift):
        a, b = self._window()
        self._set_end(b + shift)

    def _zoom(self, ts, direction):
        cur = self.span_label if self.span_label in WHEEL_ORDER else "24H"
        i = WHEEL_ORDER.index(cur) + direction
        if i >= len(WHEEL_ORDER) - 1 and direction > 0:
            # zooming out past "everything" resets the view: the whole
            # history, nothing off to the side (Marcin, 2026-11-20)
            self.span_label = "ALL"
            _remember_range(self.app, "ALL")
            self.end = None
            self._paint_chips()
            self.load()
            return
        if 0 <= i < len(WHEEL_ORDER):
            self._set_span(WHEEL_ORDER[i], center=ts)

    def _drill(self, ts):
        self._zoom(ts, -1)

    def _jump_to(self, ts):
        self._set_end(ts + self._span_s() / 2)

    def _toggle_temp(self):
        self.show_temp = not self.show_temp
        self._paint_chips()
        self._save_state()
        if self._result:
            self._apply(self._result)

    def _switch_comp(self, comp):
        if comp == self.comp:
            return
        self._save_state()
        self.app._switch_to_page(f"activity_{comp}")

    def _back(self):
        self.app._activity_state = None
        self.app._switch_to_page("dashboard")
        try:
            self.app.sidebar.set_active_page("dashboard")
        except Exception:
            pass

    def _save_state(self):
        self.app._activity_state = {"span": self.span_label, "end": self.end,
                                    "temp": self.show_temp}

    # data
    def load(self):
        self._gen += 1
        gen = self._gen
        self._save_state()
        start, end = self._window()
        self.period_lbl.config(text=fmt_period(start, end))
        self._next_chip.config(fg=DIM if self.end is None else MUTED)
        for _c in (self.charts.values() if self.hw and hasattr(self, "charts")
                   else ([self.chart] if hasattr(self, "chart") else [])):
            _c.set_loading()
        want_overview = not self._overview_loaded
        comp, h = self.comp, self.h
        if self.hw:
            self._load_hw(gen, start, end, want_overview)
            return

        def work():
            out = {"gen": gen, "start": start, "end": end}
            try:
                if want_overview:
                    first = h.available_since()
                    out["first"] = first
                    if first:
                        out["days"] = h.series(comp, first, time.time(),
                                               max_points=100000)["points"]
                        if h.resolution_for(time.time() - first) != "day":
                            out["days"] = h._rollup(out["days"], 86400)
                s = h.series(comp, start, end, max_points=900)
                out["series"] = s
                out["stats"] = h.stats(comp, start, end)
                out["prev"] = (h.compare_previous(comp, start, end)
                               if self.span_label != "ALL" else {"has_data": False})
                rec = out["stats"].get("recorded_hours")
                out["procs"] = h.top_processes(
                    comp, start, end, 6,
                    recorded_seconds=rec * 3600 if rec else None)
                out["events"] = h.events(comp, start, end, 6)
                if comp in ("cpu", "gpu"):
                    from hck_stats_engine.load_periods import periods as _periods
                    out["periods"] = _periods(start, end, comp)
                    # games under the load threshold too (2026-11-20)
                    from hck_stats_engine.game_sessions import sessions as _sessions
                    out["sessions"] = _sessions(start, end)
                from hck_stats_engine.load_periods import sleeps as _sleeps
                out["sleeps"] = _sleeps(start, end)
            except Exception as e:
                out["error"] = str(e)
            self._result_pending = out

        self._result_pending = None
        threading.Thread(target=work, daemon=True, name="activity-load").start()
        self._poll(gen)

    def _load_hw(self, gen, start, end, want_overview):
        h = self.h

        def work():
            out = {"gen": gen, "start": start, "end": end, "hw": {}}
            try:
                if want_overview:
                    first = h.available_since()
                    out["first"] = first
                    if first:
                        out["days"] = h.series("cpu", first, time.time(),
                                               max_points=100000)["points"]
                        if h.resolution_for(time.time() - first) != "day":
                            out["days"] = h._rollup(out["days"], 86400)
                for c in HW_COMPS:
                    out["hw"][c] = {"series": h.series(c, start, end, max_points=900),
                                    "stats": h.stats(c, start, end)}
                st = out["hw"]["cpu"]["stats"]
                out["stats"] = st
                rec = st.get("recorded_hours")
                out["procs"] = h.top_processes("cpu", start, end, 6,
                                               recorded_seconds=rec * 3600 if rec else None)
                from hck_stats_engine.load_periods import periods as _periods, sleeps as _sleeps
                out["periods_by"] = {c: _periods(start, end, c) for c in ("cpu", "gpu")}
                out["periods"] = out["periods_by"]["cpu"] + out["periods_by"]["gpu"]
                from hck_stats_engine.game_sessions import sessions as _sessions
                out["sessions"] = _sessions(start, end)
                out["sleeps"] = _sleeps(start, end)
                out["series"] = out["hw"]["cpu"]["series"]
            except Exception as e:
                out["error"] = str(e)
            self._result_pending = out

        self._result_pending = None
        threading.Thread(target=work, daemon=True, name="activity-load-hw").start()
        self._poll(gen)

    def _poll(self, gen):
        try:
            if not self.root.winfo_exists() or gen != self._gen:
                return
        except Exception:
            return
        r = self._result_pending
        if r is None or r.get("gen") != gen:
            self.root.after(40, lambda: self._poll(gen))
            return
        if "first" in r:
            self._first_ts = r.get("first")
            self._days = r.get("days") or []
            self._overview_loaded = True
            # "All" was measured before the first record was known
            if (self.span_label == "ALL" and self._first_ts
                    and abs(r["start"] - self._window()[0]) > 3600):
                self.load()
                return
        self._result = r
        self._apply(r)

    def _apply(self, r):
        if self.hw:
            self._apply_hw(r)
            return
        s = r.get("series") or {"points": [], "resolution": "minute"}
        self.chart.set_data(s["points"], r["start"], r["end"], s["resolution"],
                            r.get("events") or [], show_temp=self.show_temp,
                            periods=r.get("periods") or [],
                            sessions=r.get("sessions") or [],
                            sleeps=r.get("sleeps") or [])
        self.overview.set_data(getattr(self, "_days", []), self._first_ts,
                               (r["start"], r["end"]))
        self.res_lbl.config(text=t(f"activity.res_{s['resolution']}"))
        self._fill_tiles(r.get("stats") or {}, r.get("prev") or {}, r)
        self._fill_procs(r.get("procs") or [])
        self._fill_events(r.get("events") or [], r.get("periods") or [])

    def _apply_hw(self, r):
        hw = r.get("hw") or {}
        empty = {"points": [], "resolution": "minute"}
        for c, chart in self.charts.items():
            s = (hw.get(c) or {}).get("series") or empty
            chart.set_data(s["points"], r["start"], r["end"], s["resolution"], [],
                           show_temp=self.show_temp and c != "ram",
                           periods=(r.get("periods_by") or {}).get(c, []),
                           sessions=(r.get("sessions") or []) if c != "ram" else [],
                           sleeps=r.get("sleeps") or [])
        s = (hw.get("cpu") or {}).get("series") or empty
        self.overview.set_data(getattr(self, "_days", []), self._first_ts,
                               (r["start"], r["end"]))
        self.res_lbl.config(text=t(f"activity.res_{s['resolution']}"))
        res = s["resolution"]
        for c in HW_COMPS:
            st = (hw.get(c) or {}).get("stats") or {}
            cap = c.upper() + "  " + t("activity.avg")
            if st.get("has_data"):
                self._tile(c, cap, _num(st["avg"], 1) + "%",
                           t("activity.max").lower() + " " + _num(st["max"], 0) + "%  ·  "
                           + fmt_moment(st["max_ts"], res), ACCENT[c])
            else:
                self._tile(c, cap, "--", t("activity.recorded_none"), DIM)
        for c in ("cpu", "gpu"):
            st = (hw.get(c) or {}).get("stats") or {}
            cap = c.upper() + "  " + t("activity.temp")
            if st.get("has_data") and st.get("temp_avg") is not None:
                self._tile(c + "_t", cap, _num(st["temp_avg"], 0) + " °C",
                           t("activity.temp_sub", v=_num(st["temp_max"], 0)), TEMP_COL)
            else:
                self._tile(c + "_t", cap, "--", "", DIM)
        st = r.get("stats") or {}
        if st.get("has_data"):
            span_h = max((r["end"] - r["start"]) / 3600, 0.01)
            cov = min(100, st["recorded_hours"] / span_h * 100)
            pct = "<1" if 0 < cov < 1 else _num(cov, 0)
            self._tile("recorded", t("activity.recorded"), fmt_short(st["recorded_hours"] * 60),
                       t("activity.recorded_sub", pct=pct))
        else:
            self._tile("recorded", t("activity.recorded"), "--", t("activity.recorded_none"))
        self._fill_procs(r.get("procs") or [])
        self._fill_events([], r.get("periods") or [])

    def _tile(self, key, cap, val, sub="", col=TEXT):
        if key not in self.tiles:
            return
        c, v, s = self.tiles[key]
        c.config(text=cap.upper())
        v.config(text=val, fg=col)
        s.config(text=sub)

    def _fill_tiles(self, st, prev, r):
        has = st.get("has_data")
        res = (r.get("series") or {}).get("resolution", "minute")
        g = (lambda k: st.get(k)) if has else (lambda k: None)
        pc = lambda v, d=0: f"{_num(v, d)}%" if v is not None else "--"  # noqa: E731
        self._tile("avg", t("activity.avg"), pc(g("avg"), 1), t("activity.avg_sub"),
                   self.accent if has else DIM)
        self._tile("min", t("activity.min"), pc(g("min")), t("activity.min_sub"))
        self._tile("max", t("activity.max"), pc(g("max")),
                   fmt_moment(st["max_ts"], res) if has else "")
        self._tile("p95", t("activity.p95"), pc(g("p95")), t("activity.p95_sub"))
        thr = self.h.HIGH_LOAD[self.comp]
        self._tile("high", t("activity.high", thr=int(thr)),
                   fmt_short(g("high_load_minutes")) if has else "--",
                   t("activity.high_sub"))
        if has:
            span_h = max((r["end"] - r["start"]) / 3600, 0.01)
            cov = min(100, st["recorded_hours"] / span_h * 100)
            pct = "<1" if 0 < cov < 1 else _num(cov, 0)
            self._tile("recorded", t("activity.recorded"),
                       fmt_short(st["recorded_hours"] * 60),
                       t("activity.recorded_sub", pct=pct))
        else:
            self._tile("recorded", t("activity.recorded"), "--",
                       t("activity.recorded_none"))
        if self.comp != "ram":
            if has and st.get("temp_avg") is not None:
                self._tile("temp", t("activity.temp"), f"{_num(st['temp_avg'], 0)} °C",
                           t("activity.temp_sub", v=_num(st["temp_max"], 0)), TEMP_COL)
            else:
                self._tile("temp", t("activity.temp"), "--", t("activity.temp_none"), DIM)
        if prev.get("has_data"):
            d = prev["delta"]
            col = UP_COL if d >= 3 else DOWN_COL if d <= -3 else TEXT
            arrow = "▲" if d > 0 else "▼" if d < 0 else "="
            self._tile("prev", t("activity.prev"), f"{arrow} {_num(abs(d))} {t('activity.pts')}",
                       t("activity.prev_sub", v=_num(prev["prev_avg"])), col)
        else:
            self._tile("prev", t("activity.prev"), "--", t("activity.prev_none"), DIM)

    @staticmethod
    def _rows_fit(box):
        """How many rows fit under the box title (no half rows). The row
        height is measured from the font, not assumed."""
        import tkinter.font as tkfont
        h = box.winfo_height()
        if h <= 1:
            h = int(box.cget("height"))
        row = tkfont.Font(font=(_BODY, 8)).metrics("linespace") + 6
        title = tkfont.Font(font=(_BODY, 7, "bold")).metrics("linespace") + 14
        return max(1, (h - title) // row)

    def _clear(self, box):
        for w in box.winfo_children():
            w.destroy()

    def _box_title(self, box, text):
        tk.Label(box, text=text.upper(), font=(_BODY, 7, "bold"), bg=PANEL,
                 fg=MUTED, anchor="w").pack(fill="x", padx=10, pady=(7, 4))

    def _fill_procs(self, procs):
        box = self.proc_box
        self._clear(box)
        self._box_title(box, t("activity.procs_" + ("cpu" if self.hw else self.comp)))
        if self.comp == "gpu":
            tk.Label(box, text=t("activity.procs_gpu_none"), font=(_BODY, 8),
                     bg=PANEL, fg=DIM, anchor="w", justify="left",
                     wraplength=_sc(420)).pack(fill="x", padx=10)
            return
        if not procs:
            tk.Label(box, text=t("activity.procs_none"), font=(_BODY, 8),
                     bg=PANEL, fg=DIM, anchor="w").pack(fill="x", padx=10)
            return
        procs = procs[:self._rows_fit(box)]
        top = max(p["value"] for p in procs) or 1
        unit = "%" if self.comp in ("cpu", "hardware") else " MB"
        for p in procs:
            row = tk.Frame(box, bg=PANEL)
            row.pack(fill="x", padx=10, pady=1)
            tk.Label(row, text=t("activity.proc_hours", v=_num(p["active_hours"])),
                     font=(_BODY, 7), bg=PANEL, fg=DIM, width=9,
                     anchor="e").pack(side="right")
            tk.Label(row, text=f"{_num(p['value'], 0 if self.comp == 'ram' else 1)}{unit}",
                     font=(_MONO, 8), bg=PANEL, fg=self.accent, width=9,
                     anchor="e").pack(side="right")
            name = p["name"] if len(p["name"]) <= 26 else p["name"][:25] + "…"
            name_lbl = tk.Label(row, text=name, font=(_BODY, 8), bg=PANEL, fg=TEXT,
                                width=22, anchor="w")
            name_lbl.pack(side="left")
            bar = tk.Frame(row, bg=GRID, height=5)
            bar.pack(side="left", fill="x", expand=True, padx=(6, 6))
            tk.Frame(bar, bg=_blend(self.accent, PANEL, 0.7), height=5).place(
                x=0, y=0, relheight=1, relwidth=max(0.02, p["value"] / top))
            # hover: what the process is and how it lives here (2026-11-20)
            try:
                from ui.components import process_ref
                process_ref.bind([row] + list(row.winfo_children()),
                                 p.get("process") or p["name"], self.app)
            except Exception:
                pass

    def _show_period(self, per):
        """Zoom to the smallest range that shows the whole period."""
        length = max(per["end"] - per["timestamp"], 60)
        for lab in ZOOM_ORDER:
            span = self.h.RANGES[lab]
            if span is None or span >= length * 1.4:
                self._set_span(lab, center=(per["timestamp"] + per["end"]) / 2)
                return

    def _fill_events(self, events, periods=()):
        box = self.ev_box
        self._clear(box)
        self._box_title(box, t("activity.events"))
        if not events and not periods:
            tk.Label(box, text=t("activity.events_none"), font=(_BODY, 8),
                     bg=PANEL, fg=DIM, anchor="w", justify="left",
                     wraplength=_sc(300)).pack(fill="x", padx=10)
            return
        room = self._rows_fit(box)
        for per in list(periods)[:room]:
            row = tk.Frame(box, bg=PANEL)
            row.pack(fill="x", padx=10, pady=1)
            tk.Label(row, text="▮", font=(_BODY, 8), bg=PANEL, fg=WINE).pack(side="left")
            a = datetime.fromtimestamp(per["timestamp"])
            b = datetime.fromtimestamp(per["end"])
            when = (f"{_day(a)} {a:%H:%M}-{b:%H:%M}" if a.date() == b.date()
                    else f"{_day(a)} {a:%H:%M}")
            tk.Label(row, text=when, font=(_BODY, 8), bg=PANEL, fg=MUTED,
                     anchor="w").pack(side="left", padx=(4, 8))
            tk.Label(row, text=t("activity.period_row", m=per["minutes"],
                                 avg=_num(per["avg"], 0),
                                 who=per.get("process_name") or "-"),
                     font=(_BODY, 8), bg=PANEL, fg=TEXT, anchor="w").pack(side="left")
            for w in (row, *row.winfo_children()):
                w.bind("<Button-1>", lambda e=None, pr=per: self._show_period(pr))
                w.config(cursor="hand2")
        room -= min(len(periods), room)
        for ev in events[:max(0, room)]:
            row = tk.Frame(box, bg=PANEL)
            row.pack(fill="x", padx=10, pady=1)
            tk.Label(row, text="▲", font=(_BODY, 7), bg=PANEL, fg=UP_COL).pack(side="left")
            tk.Label(row, text=fmt_moment(ev["timestamp"], "minute"), font=(_BODY, 8),
                     bg=PANEL, fg=MUTED, width=14, anchor="w").pack(side="left", padx=(4, 0))
            val = ev.get("value")
            base = ev.get("baseline")
            txt = t("activity.event_spike", v=_num(val, 0)) if val is not None else ""
            if base is not None:
                txt += "  " + t("activity.event_base", v=_num(base, 0))
            tk.Label(row, text=txt, font=(_BODY, 8), bg=PANEL, fg=TEXT,
                     anchor="w").pack(side="left", fill="x")
            # the whole row opens one hour around the spike
            for w in (row, *row.winfo_children()):
                w.bind("<Button-1>", lambda e=None, ts=ev["timestamp"]:
                       self._set_span("1H", center=ts))
                w.config(cursor="hand2")


def build_activity_memory_page(app, parent, comp: str) -> ActivityMemoryPage:
    return ActivityMemoryPage(app, parent, comp if comp in ACCENT else "cpu")
