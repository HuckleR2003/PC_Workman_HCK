"""ui.components.page_titles - page headers in the interface language (2026-11-21).

The test build showed the older pages with English headers under a Polish
interface ("Startup Manager", "SERVICES MANAGER", "FAN DASHBOARD",
"FIRST SETUP & DRIVERS"...), next to the new pages with Polish banners. The
names follow the sidebar: Menedżer Autostartu, Menedżer Usług, Kontrola
wentylatorów, Konfiguracja i sterowniki. OVERCLOCK and Upgrade Readiness
stay feature names in both languages, as in the sidebar and hck_GPT.

    title(key) -> (title, subtitle)      text(key) -> one string
"""
from __future__ import annotations

_TITLES = {
    "startup_manager":  {"pl": ("Menedżer Autostartu", "Co startuje razem z Windows"),
                         "en": ("Startup Manager", "What starts with Windows")},
    "services_manager": {"pl": ("MENEDŻER USŁUG", "Usługi Windows i profile TURBO"),
                         "en": ("SERVICES MANAGER", "Windows services & TURBO profiles")},
    "services_inner":   {"pl": ("Menedżer Usług", ""), "en": ("Services Manager", "")},
    "fan_control":      {"pl": ("KONTROLA WENTYLATORÓW", "Centrum chłodzenia i profile"),
                         "en": ("FAN DASHBOARD", "Cooling control center & profiles")},
    "fan_overlay":      {"pl": ("KONTROLA WENTYLATORÓW", "Profile chłodzenia i krzywe temperatur"),
                         "en": ("FAN CONTROL", "Cooling profiles & temperature curves")},
    "fans_hw_usage":    {"pl": ("WENTYLATORY: SPRZĘT I UŻYCIE", "Czujniki, wentylatory i ich praca w czasie"),
                         "en": ("FANS - HARDWARE & USAGE", "Sensors, fan monitoring & intensity over time")},
    "fans_hardware":    {"pl": ("WENTYLATORY: SPRZĘT", "Wentylatory na żywo"),
                         "en": ("FANS - HARDWARE", "Real-time fan monitoring")},
    "fans_usage_stats": {"pl": ("STATYSTYKI WENTYLATORÓW", "Praca wentylatorów w czasie"),
                         "en": ("FAN STATISTICS", "Fan intensity over time")},
    "overclock":        {"pl": ("OVERCLOCK", "Headroom Lab: co ogranicza Twoje zegary"),
                         "en": ("OVERCLOCK", "Headroom Lab - what limits your clocks")},
    "upgrade_readiness": {"pl": ("UPGRADE READINESS", "Czy ta część pasuje do tego komputera? Sprawdzenie offline"),
                          "en": ("UPGRADE READINESS", "Will that part fit this PC? Offline compatibility check")},
    "first_setup":      {"pl": ("KONFIGURACJA I STEROWNIKI", "gotowość systemu  ·  stan sterowników  ·  autostart"),
                         "en": ("FIRST SETUP & DRIVERS", "system readiness  ·  driver health  ·  startup control")},
    "sensors":          {"pl": ("MONITORING", "Temperatury · Napięcia · Alerty"),
                         "en": ("MONITORING", "Temperatures · Voltages · Alerts")},
    "optimization":     {"pl": ("OPTYMALIZACJA", "Funkcje, automatyzacja i zasilanie"),
                         "en": ("OPTIMIZATION", "Features, automation & power management")},
    "statistics":       {"pl": ("STATYSTYKI", "Trendy użycia i historia sesji"),
                         "en": ("STATISTICS", "Usage trends & session history")},
    "your_pc_sub":      {"pl": ("", "Przegląd · Wydajność · Zdrowie"),
                         "en": ("", "Overview · Performance · Health")},
    "live_graphs_sub":  {"pl": ("", "Dane na żywo i przegląd sprzętu"),
                         "en": ("", "Live data & hardware overview")},
    # small pieces of the Startup Manager and Services Manager headers
    "sm_total":         {"pl": ("Razem", ""), "en": ("Total", "")},
    "sm_high":          {"pl": ("Duży wpływ", ""), "en": ("High impact", "")},
    "sm_flagged":       {"pl": ("Do sprawdzenia", ""), "en": ("Flagged", "")},
    "sm_tab_menu":      {"pl": ("Do wyłączenia", ""), "en": ("Startup Menu", "")},
    "sm_tab_disabled":  {"pl": ("Wyłączone", ""), "en": ("Disabled", "")},
    "sm_menu_head":     {"pl": ("Do wyłączenia", ""), "en": ("Startup Menu", "")},
    "sm_disabled_head": {"pl": ("Wyłączone wpisy", ""), "en": ("Disabled entries", "")},
    "svc_admin":        {"pl": ("Administrator ✓", ""), "en": ("Administrator ✓", "")},
    "svc_count":        {"pl": ("{total} usług w katalogu   ·   {running} działa", ""),
                         "en": ("{total} services catalogued   ·   {running} running", "")},
    "svc_not_admin":    {"pl": ("Bez uprawnień administratora: zatrzymywanie i uruchamianie usług może się nie udać.", ""),
                         "en": ("Not running as Administrator - Stop / Start actions may fail.", "")},
    "svc_search":       {"pl": ("Szukaj usług…", ""), "en": ("Search services…", "")},
    "svc_limited":      {"pl": ("Tryb ograniczony", ""), "en": ("Limited mode", "")},
    "fs_scanning":      {"pl": ("● Skanuję…", ""), "en": ("● Scanning…", "")},
    "fs_ready":         {"pl": ("● Gotowość", ""), "en": ("● Ready", "")},
    "fs_rescan":        {"pl": ("↺  Skanuj ponownie", ""), "en": ("↺  Re-Scan", "")},
    "fs_devmgr":        {"pl": ("⊞  Menedżer urządzeń", ""), "en": ("⊞  Device Manager", "")},
}


def _lang() -> str:
    try:
        from utils.i18n import get_lang
        return "en" if str(get_lang()).lower().startswith("en") else "pl"
    except Exception:
        return "pl"


def title(key: str) -> tuple:
    """(title, subtitle) in the interface language."""
    entry = _TITLES.get(key)
    if not entry:
        return key.upper().replace("_", " "), ""
    return entry[_lang()]


def text(key: str) -> str:
    return title(key)[0]
