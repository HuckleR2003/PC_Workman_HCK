"""ui.components.nav_history - where the user came from (2026-11-20).

Pages had no way back: Optimization went "back" to the Dashboard whatever
the user came from, Stability Tests, Startup, Services and Setup had none.
The main window records every place it shows (a page, an overlay, the tab
of My PC) and the sidebar offers "← Wróć: <the previous place>".

A location is a tuple (kind, id, tab): kind "page" or "overlay", id the page
id the window uses, tab the My PC tab or None. Pure Python, no Tk.
"""
from __future__ import annotations

from typing import Optional, Tuple

Location = Tuple[str, str, Optional[str]]

LIMIT = 20

# Names of the places, as the sidebar shows them
_NAMES = {
    "dashboard":         {"pl": "Dashboard", "en": "Dashboard"},
    "your_pc":           {"pl": "Mój PC", "en": "My PC"},
    "monitoring_alerts": {"pl": "Monitoring", "en": "Monitoring"},
    "optimization":      {"pl": "Centrum optymalizacji", "en": "Optimization Center"},
    "startup_manager":   {"pl": "Autostart", "en": "Startup Manager"},
    "services_manager":  {"pl": "Usługi", "en": "Services Manager"},
    "first_setup":       {"pl": "Konfiguracja i sterowniki", "en": "Setup & Drivers"},
    "overclock":         {"pl": "Overclock", "en": "Overclock"},
    "fan_control":       {"pl": "Fan Dashboard", "en": "Fan Dashboard"},
    "fans_hw_usage":     {"pl": "Sprzęt i użycie", "en": "Hardware & Usage"},
    "upgrade_readiness": {"pl": "Upgrade Readiness", "en": "Upgrade Readiness"},
    "settings":          {"pl": "Ustawienia", "en": "Settings"},
    "hck_labs":          {"pl": "HCK_Labs", "en": "HCK_Labs"},
    "guide":             {"pl": "Przewodnik", "en": "Guide"},
    "statistics":        {"pl": "Statystyki", "en": "Statistics"},
    "sensors":           {"pl": "Czujniki", "en": "Sensors"},
    "live_graphs":       {"pl": "DeepMonitor", "en": "DeepMonitor"},
    "process_center":    {"pl": "Centrum procesów", "en": "Process Center"},
    "cleanup":           {"pl": "Oczyszczanie", "en": "Cleanup"},
    "health_report":     {"pl": "Raport zdrowia", "en": "Health report"},
    "profile":           {"pl": "Twój profil", "en": "Your profile"},
    "activity_cpu":      {"pl": "Historia CPU", "en": "CPU history"},
    "activity_ram":      {"pl": "Historia RAM", "en": "RAM history"},
    "activity_gpu":      {"pl": "Historia GPU", "en": "GPU history"},
    "activity_hardware": {"pl": "Historia sprzętu", "en": "Hardware history"},
}


def label(loc: Optional[Location], lang: str = "pl") -> str:
    if not loc:
        return ""
    lang = "en" if lang == "en" else "pl"
    name = _NAMES.get(loc[1])
    if name:
        return name[lang]
    return str(loc[1]).replace("_", " ").title()


class NavHistory:

    def __init__(self, limit: int = LIMIT):
        self._stack: list = []
        self._limit = limit

    def push(self, loc: Optional[Location]) -> None:
        if not loc or not loc[1]:
            return
        if self._stack and self._stack[-1] == loc:
            return
        self._stack.append(loc)
        if len(self._stack) > self._limit:
            del self._stack[0]

    def peek(self) -> Optional[Location]:
        return self._stack[-1] if self._stack else None

    def pop(self) -> Optional[Location]:
        return self._stack.pop() if self._stack else None

    def clear(self) -> None:
        self._stack.clear()

    def __len__(self) -> int:
        return len(self._stack)
