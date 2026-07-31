"""Pure scoring policy for hck_GPT proactivity.

The background daemon remains ProactiveMonitor. This module only decides
whether a candidate is worth interrupting the user for, which keeps the policy
headless and testable without starting threads or touching Tk.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ProactiveDecision:
    allowed: bool
    score: float
    threshold: float
    reason: str
    urgent: bool = False


class ProactivePolicy:
    MODES = frozenset({"quiet", "balanced", "companion"})
    _THRESHOLDS = {
        "quiet": 0.70,
        "balanced": 0.40,
        "companion": 0.29,
    }
    _URGENT = frozenset({
        "cpu_crit", "cpu_temp_crit", "gpu_temp_crit", "gpu_temp_spike",
        "ram_crit", "multi_disk_low",
    })
    # severity, confidence, actionability, relevance, interruption cost
    _PROFILES: Dict[str, tuple[float, float, float, float, float]] = {
        "cpu_crit": (0.95, 0.90, 0.85, 0.95, 0.15),
        "cpu_high": (0.70, 0.85, 0.75, 0.80, 0.40),
        "ram_high": (0.68, 0.90, 0.80, 0.85, 0.38),
        "throttle": (0.78, 0.75, 0.75, 0.90, 0.30),
        "disk_low": (0.82, 0.98, 0.90, 0.90, 0.28),
        "multi_disk_low": (0.88, 0.98, 0.90, 0.90, 0.25),
        "gpu_temp_spike": (0.92, 0.85, 0.85, 0.95, 0.18),
        "temp_sustained": (0.80, 0.88, 0.80, 0.92, 0.28),
        "cpu_temp_crit": (1.00, 0.92, 0.90, 1.00, 0.10),
        "gpu_temp_crit": (1.00, 0.92, 0.90, 1.00, 0.10),
        "cpu_temp_warn": (0.72, 0.85, 0.75, 0.88, 0.35),
        "gpu_temp_warn": (0.72, 0.85, 0.75, 0.88, 0.35),
        "process_spike": (0.52, 0.70, 0.62, 0.68, 0.48),
        "cpu_freq_severe": (0.78, 0.72, 0.70, 0.85, 0.32),
        "voltage_spike": (0.82, 0.72, 0.58, 0.85, 0.30),
        "voltage_trend": (0.65, 0.72, 0.55, 0.78, 0.38),
        "long_session": (0.30, 1.00, 0.45, 0.55, 0.34),
        "learning_milestone": (0.12, 1.00, 0.25, 0.45, 0.25),
        "voltage_new_normal": (0.12, 0.95, 0.20, 0.45, 0.28),
        "thermal_insight": (0.48, 0.82, 0.58, 0.72, 0.38),
        "idle_tip": (0.10, 0.75, 0.42, 0.48, 0.38),
        "context_idle_tip": (0.15, 0.88, 0.55, 0.70, 0.30),
        "game_checkin": (0.16, 0.85, 0.58, 0.90, 0.30),
        "game_recap": (0.14, 0.92, 0.45, 0.86, 0.28),
        "recovery": (0.20, 0.95, 0.35, 0.82, 0.22),
    }
    _DEFAULT = (0.45, 0.75, 0.55, 0.65, 0.38)

    @classmethod
    def normalize_mode(cls, value: str) -> str:
        return value if value in cls.MODES else "balanced"

    @classmethod
    def decide(cls, event_type: str, mode: str = "balanced",
               enabled: bool = True, urgent: bool = False,
               user_active: bool = False, novelty: float = 1.0,
               relevance: Optional[float] = None) -> ProactiveDecision:
        mode = cls.normalize_mode(mode)
        urgent = bool(urgent or event_type in cls._URGENT)
        threshold = cls._THRESHOLDS[mode]
        if not enabled and not urgent:
            return ProactiveDecision(False, 0.0, threshold, "disabled", urgent)

        severity, confidence, actionability, base_relevance, cost = (
            cls._PROFILES.get(event_type, cls._DEFAULT)
        )
        if relevance is not None:
            base_relevance = max(0.0, min(1.0, relevance))
        novelty = max(0.0, min(1.0, novelty))
        if user_active and not urgent:
            cost = min(1.0, cost + 0.25)
        score = (
            0.28 * severity
            + 0.24 * confidence
            + 0.18 * actionability
            + 0.15 * novelty
            + 0.15 * base_relevance
            - 0.25 * cost
        )
        score = round(max(0.0, min(1.0, score)), 3)
        if urgent:
            return ProactiveDecision(True, score, threshold, "urgent", True)
        allowed = score >= threshold
        return ProactiveDecision(
            allowed, score, threshold,
            "useful_enough" if allowed else "below_threshold", False,
        )


__all__ = ["ProactiveDecision", "ProactivePolicy"]
