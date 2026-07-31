"""Headless game-session evidence tracker.

It never polls processes and never starts a thread. GamingToastWatcher remains
the one game start/end detector, while ProactiveMonitor owns this tracker and
feeds it honest live samples. FPS is accepted only when explicitly sourced from
RTSS.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GameSession:
    exe: str
    label: str
    started_at: float
    baseline: Dict[str, Any] = field(default_factory=dict)
    samples: List[Dict[str, float]] = field(default_factory=list)
    checkin_sent: bool = False
    last_sample_at: float = 0.0


class GameSessionTracker:
    MAX_SAMPLES = 120
    SAMPLE_GAP_S = 40
    CHECKIN_AFTER_S = 600

    def __init__(self) -> None:
        self._active: Dict[str, GameSession] = {}

    @staticmethod
    def _clean_metrics(metrics: Optional[Dict[str, Any]]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for key in ("cpu_pct", "ram_pct", "gpu_pct", "cpu_temp", "gpu_temp"):
            try:
                value = float((metrics or {}).get(key))
            except (TypeError, ValueError):
                continue
            if value >= 0:
                out[key] = round(value, 1)
        fps_source = str((metrics or {}).get("fps_source") or "").lower()
        if fps_source == "rtss":
            try:
                fps = float((metrics or {}).get("fps"))
                if 0 < fps < 10000:
                    out["fps"] = round(fps, 1)
            except (TypeError, ValueError):
                pass
        return out

    def start(self, exe: str, label: str = "",
              metrics: Optional[Dict[str, Any]] = None,
              now: Optional[float] = None) -> GameSession:
        key = (exe or "").strip().lower()
        ts = time.time() if now is None else float(now)
        session = GameSession(
            exe=key,
            label=(label or key).strip(),
            started_at=ts,
            baseline=self._clean_metrics(metrics),
        )
        self._active[key] = session
        return session

    def sample(self, exe: str, metrics: Dict[str, Any],
               now: Optional[float] = None) -> bool:
        key = (exe or "").strip().lower()
        session = self._active.get(key)
        if session is None:
            return False
        ts = time.time() if now is None else float(now)
        if session.last_sample_at and ts - session.last_sample_at < self.SAMPLE_GAP_S:
            return False
        clean = self._clean_metrics(metrics)
        if not clean:
            return False
        clean["captured_at"] = ts
        session.samples.append(clean)
        if len(session.samples) > self.MAX_SAMPLES:
            del session.samples[:-self.MAX_SAMPLES]
        session.last_sample_at = ts
        return True

    def active_executables(self) -> List[str]:
        return list(self._active)

    def should_check_in(self, exe: str, mode: str,
                        now: Optional[float] = None) -> bool:
        session = self._active.get((exe or "").strip().lower())
        if session is None or mode != "companion" or session.checkin_sent:
            return False
        ts = time.time() if now is None else float(now)
        return (ts - session.started_at >= self.CHECKIN_AFTER_S
                and len(session.samples) >= 2)

    def mark_checkin(self, exe: str) -> None:
        session = self._active.get((exe or "").strip().lower())
        if session is not None:
            session.checkin_sent = True

    @staticmethod
    def _averages(session: GameSession) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for key in ("cpu_pct", "ram_pct", "gpu_pct", "cpu_temp", "gpu_temp", "fps"):
            values = [row[key] for row in session.samples if key in row]
            if values:
                out[key] = round(sum(values) / len(values), 1)
        return out

    def end(self, exe: str, now: Optional[float] = None) -> Dict[str, Any]:
        key = (exe or "").strip().lower()
        session = self._active.pop(key, None)
        if session is None:
            return {}
        ts = time.time() if now is None else float(now)
        summary: Dict[str, Any] = {
            "exe": session.exe,
            "label": session.label,
            "duration_s": max(0, int(ts - session.started_at)),
            "sample_count": len(session.samples),
            "averages": self._averages(session),
            "baseline": dict(session.baseline),
            "checkin_sent": session.checkin_sent,
        }
        # Absence of RTSS means absence of an FPS claim, not "0 FPS".
        if "fps" not in summary["averages"]:
            summary["fps_available"] = False
        else:
            summary["fps_available"] = True
            summary["fps_source"] = "rtss"
        return summary


__all__ = ["GameSession", "GameSessionTracker"]
