"""core/observation.py - the observation note: record, change, compare (2026-11-17).

Asked for after the third long test (2026-11-17): "how do I check that it
got better?" The user starts a recording, plays or works or runs the
optimization, stops it, and gets a note: what the PC did during the
recording and, when there is an earlier recording, the two side by side.

    start(label)  sample every second in a background thread: CPU, RAM,
                  GPU load and temperature, the real CPU clock (every 10 s),
                  the busiest process
    stop()        summary {avg, max, p95 for each}; saved as JSON under
                  data/observations/ and as a text note on the Desktop
    status()      {"recording": bool, "seconds", "label"}
    last_two()    the two newest recordings, for a comparison

A recording stops by itself after MAX_SECONDS. Notes go to the Desktop of
the user; with PCW_APP_DIR set (tests, probes) they go to its notes folder.
Nothing here changes the system.
"""
from __future__ import annotations

import json
import os
import threading
import time

MAX_SECONDS = 2 * 3600
_lock = threading.Lock()
_state = {"thread": None, "stop": None, "samples": [], "start": 0.0, "label": "",
          "last_summary": None}


def _obs_dir() -> str:
    try:
        from utils.paths import APP_DIR
        base = APP_DIR
    except Exception:
        base = os.getcwd()
    d = os.path.join(base, "data", "observations")
    os.makedirs(d, exist_ok=True)
    return d


def _notes_dir() -> str:
    """The user's Desktop (OneDrive-moved too); a folder under PCW_APP_DIR
    when the app runs isolated."""
    if os.environ.get("PCW_APP_DIR"):
        d = os.path.join(os.environ["PCW_APP_DIR"], "notes")
        os.makedirs(d, exist_ok=True)
        return d
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
            raw = winreg.QueryValueEx(k, "Desktop")[0]
        d = os.path.expandvars(raw)
        if os.path.isdir(d):
            return d
    except Exception:
        pass
    d = os.path.join(os.path.expanduser("~"), "Desktop")
    return d if os.path.isdir(d) else os.path.expanduser("~")


def status() -> dict:
    with _lock:
        rec = _state["thread"] is not None and _state["thread"].is_alive()
        return {"recording": rec, "label": _state["label"],
                "seconds": int(time.time() - _state["start"]) if rec else 0,
                "samples": len(_state["samples"]) if rec else 0}


def _sample_loop(stop: threading.Event):
    import psutil
    psutil.cpu_percent(None)
    clock_at, clock = 0.0, None
    while not stop.is_set():
        t0 = time.time()
        try:
            cpu = psutil.cpu_percent(None)
            ram = psutil.virtual_memory().percent
        except Exception:
            cpu = ram = None
        gpu = gtemp = None
        try:
            from hck_gpt.data.live_sensors import snapshot
            s = snapshot() or {}
            gpu = s.get("gpu_load") if (s.get("gpu_load") or -1) >= 0 else None
            gtemp = s.get("gpu_temp") if (s.get("gpu_temp") or -1) > 0 else None
        except Exception:
            pass
        if t0 - clock_at >= 10:
            clock_at = t0
            try:
                from core.pc_insight import cpu_clock
                clock = cpu_clock(0.3).get("actual")
            except Exception:
                clock = None
        top = None
        if int(t0) % 5 == 0:
            try:
                best, ncpu = (None, -1.0), psutil.cpu_count() or 1
                for p in psutil.process_iter(["name", "cpu_percent"]):
                    c = (p.info.get("cpu_percent") or 0) / ncpu
                    n = (p.info.get("name") or "").lower()
                    if c > best[1] and n not in ("system idle process", "system", "idle"):
                        best = (p.info.get("name"), c)
                top = best[0]
            except Exception:
                top = None
        with _lock:
            _state["samples"].append({"t": t0, "cpu": cpu, "ram": ram, "gpu": gpu,
                                      "gtemp": gtemp, "clock": clock, "top": top})
            if t0 - _state["start"] > MAX_SECONDS:
                stop.set()
        stop.wait(max(0.0, 1.0 - (time.time() - t0)))


def start(label: str = "") -> bool:
    """Start recording; False when a recording already runs."""
    with _lock:
        if _state["thread"] is not None and _state["thread"].is_alive():
            return False
        stop = threading.Event()
        _state.update(stop=stop, samples=[], start=time.time(), label=label or "")
        th = threading.Thread(target=_sample_loop, args=(stop,), daemon=True,
                              name="ObservationRecorder")
        _state["thread"] = th
    th.start()
    return True


def _stats(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    return {"avg": round(sum(vals) / len(vals), 1), "max": round(vals[-1], 1),
            "p95": round(vals[min(len(vals) - 1, int(len(vals) * 0.95))], 1)}


def summarize(samples: list, started: float, label: str = "") -> dict:
    tops = {}
    for s in samples:
        if s.get("top"):
            tops[s["top"]] = tops.get(s["top"], 0) + 1
    return {
        "label": label, "start": started,
        "end": samples[-1]["t"] if samples else started,
        "seconds": int((samples[-1]["t"] - started) if samples else 0),
        "samples": len(samples),
        "cpu": _stats([s["cpu"] for s in samples]),
        "ram": _stats([s["ram"] for s in samples]),
        "gpu": _stats([s["gpu"] for s in samples]),
        "gpu_temp": _stats([s["gtemp"] for s in samples]),
        "cpu_clock": _stats([s["clock"] for s in samples]),
        "top": sorted(tops, key=lambda k: -tops[k])[:3],
    }


def stop() -> dict | None:
    """Stop, save and write the note. Returns the summary with "note_path"
    and "compare" (against the previous recording), or None."""
    with _lock:
        th, ev = _state["thread"], _state["stop"]
        if th is None:
            return None
    if ev:
        ev.set()
    th.join(timeout=3)
    with _lock:
        samples = list(_state["samples"])
        started, label = _state["start"], _state["label"]
        _state["thread"] = None
    if len(samples) < 3:
        return {"too_short": True, "seconds": len(samples)}
    summ = summarize(samples, started, label)
    prev = last_saved()
    path = os.path.join(_obs_dir(), time.strftime("obs_%Y%m%d_%H%M%S.json",
                                                  time.localtime(started)))
    try:
        from utils.prefs_io import save_json
        save_json(path, summ, indent=1)
    except Exception:
        pass
    summ["compare"] = compare(prev, summ) if prev else None
    summ["note_path"] = write_note(summ, prev)
    with _lock:
        _state["last_summary"] = summ
    return summ


def last_saved() -> dict | None:
    try:
        files = sorted(f for f in os.listdir(_obs_dir()) if f.startswith("obs_"))
        if not files:
            return None
        with open(os.path.join(_obs_dir(), files[-1]), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def compare(a: dict, b: dict) -> dict:
    """b against a: {metric: {"before", "after", "delta"}}, average values,
    plus "verdict": better | same | worse (on CPU, RAM and GPU temp)."""
    out, score = {}, 0
    for m in ("cpu", "ram", "gpu", "gpu_temp", "cpu_clock"):
        x, y = (a or {}).get(m), (b or {}).get(m)
        if x and y:
            d = round(y["avg"] - x["avg"], 1)
            out[m] = {"before": x["avg"], "after": y["avg"], "delta": d}
            if m in ("cpu", "ram", "gpu_temp") and abs(d) >= 3:
                score += -1 if d < 0 else 1
    out["verdict"] = "better" if score < 0 else "worse" if score > 0 else "same"
    return out


_NAMES = {"cpu": ("Procesor", "CPU"), "ram": ("RAM", "RAM"), "gpu": ("GPU", "GPU"),
          "gpu_temp": ("Temperatura GPU", "GPU temperature"),
          "cpu_clock": ("Zegar procesora", "CPU clock")}


def _fmt(m, s, pl=True):
    unit = "°C" if m == "gpu_temp" else " MHz" if m == "cpu_clock" else "%"
    return (f"średnio {s['avg']:.0f}{unit}, szczyt {s['max']:.0f}{unit}, 95% czasu do {s['p95']:.0f}{unit}"
            if pl else
            f"average {s['avg']:.0f}{unit}, peak {s['max']:.0f}{unit}, 95% of the time under {s['p95']:.0f}{unit}")


def note_text(summ: dict, prev: dict | None, lang: str = "pl") -> str:
    pl = lang != "en"
    t0 = time.strftime("%Y-%m-%d %H:%M", time.localtime(summ["start"]))
    mins = summ["seconds"] / 60
    n = summ["samples"]
    dur = (f"{summ['seconds']} s" if summ["seconds"] < 60 else f"{mins:.0f} min")
    word = ("pomiar" if n == 1 else "pomiary" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14
            else "pomiarów")
    lines = ["PC Workman - notatka obserwacyjna" if pl else "PC Workman - observation note",
             "=" * 44,
             (f"Nagranie: {t0}, {dur}, {n} {word}" if pl else
              f"Recording: {t0}, {dur}, {n} readings")]
    if summ.get("label"):
        lines.append(("Opis: " if pl else "Label: ") + summ["label"])
    lines.append("")
    for m in ("cpu", "ram", "gpu", "gpu_temp", "cpu_clock"):
        if summ.get(m):
            lines.append(f"{_NAMES[m][0 if pl else 1]}: {_fmt(m, summ[m], pl)}")
    if summ.get("top"):
        lines.append(("Najczęściej najcięższy proces: " if pl else "Most often the busiest process: ")
                     + ", ".join(summ["top"]))
    if prev:
        c = compare(prev, summ)
        lines += ["", ("Porównanie z poprzednim nagraniem (" if pl else "Compared with the previous recording (")
                  + time.strftime("%Y-%m-%d %H:%M", time.localtime(prev["start"])) + "):"]
        for m in ("cpu", "ram", "gpu", "gpu_temp", "cpu_clock"):
            if m in c:
                unit = "°C" if m == "gpu_temp" else " MHz" if m == "cpu_clock" else " pp"
                lines.append(f"  {_NAMES[m][0 if pl else 1]}: {c[m]['before']:.0f} -> {c[m]['after']:.0f}"
                             f" ({c[m]['delta']:+.0f}{unit})")
        verdict = {"better": ("Werdykt: jest lepiej.", "Verdict: better."),
                   "worse": ("Werdykt: jest gorzej.", "Verdict: worse."),
                   "same": ("Werdykt: bez wyraźnej różnicy.", "Verdict: no clear difference.")}[c["verdict"]]
        lines.append(verdict[0 if pl else 1])
        lines.append("Uwaga: porównanie ma sens przy tej samej czynności (ta sama gra, ten sam test)." if pl else
                     "Note: the comparison makes sense for the same activity (same game, same test).")
    return "\n".join(lines) + "\n"


def write_note(summ: dict, prev: dict | None, lang: str = "pl") -> str:
    name = time.strftime("PC Workman - obserwacja %Y-%m-%d %H-%M.txt", time.localtime(summ["start"]))
    path = os.path.join(_notes_dir(), name)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(note_text(summ, prev, lang))
        return path
    except Exception:
        return ""
