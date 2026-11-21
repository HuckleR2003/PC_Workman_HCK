"""core.recommendations - what to do with a process, in one place (2026-11-20).

Advice on processes lived in four places that did not know about each
other: the Startup Manager's tables, hck_GPT's "background bloat" list, the
TURBO service list and the protected-process guard. The Process Center needs
one answer per process, and the other pages should give the same one.

    recommend("teams.exe") -> {
        "action": "startup_off",     # keep | startup_off | delay | close_ok | protected
        "impact": "high",            # low | medium | high (at boot / in the background)
        "why":    "Heavy at boot. Open it when you have a meeting.",
        "source": "startup",         # which table answered
    }

"Protected" always wins: an anti-cheat, an OS-critical process or PC
Workman itself is never offered for switching off.
"""
from __future__ import annotations

# ── Startup tables (from ui/pages/startup_manager.py) ─────────────────────
# Known files: exe -> (impact at boot, recommendation, why)
STARTUP_KNOWN: dict[str, tuple[str, str, str]] = {
    "teams.exe":              ("high",   "disable", "High RAM & CPU at boot. Open when you need a meeting."),
    "discord.exe":            ("medium", "delay",   "Chat app - launch on demand. Saves seconds at boot."),
    "slack.exe":              ("high",   "disable", "Heavy memory footprint. Open manually at work start."),
    "zoom.exe":               ("medium", "delay",   "Video client. Only needed when joining a call."),
    "spotify.exe":            ("medium", "delay",   "Music player. Start when you actually want to listen."),
    "skype.exe":              ("medium", "delay",   "Legacy VoIP - start manually if still used."),
    "onedrive.exe":           ("medium", "delay",   "Cloud sync runs fine when delayed or started on-demand."),
    "dropbox.exe":            ("medium", "delay",   "Cloud sync - can start delayed after login."),
    "googledrivesync.exe":    ("medium", "delay",   "Google Drive sync - delayed start works fine."),
    "steam.exe":              ("high",   "disable", "Game launcher. No reason to start with Windows."),
    "epicgameslauncher.exe":  ("high",   "disable", "Epic Games - opens fine on demand."),
    "ea_desktop.exe":         ("high",   "disable", "EA Desktop - large, start manually when gaming."),
    "battle.net.exe":         ("high",   "disable", "Battle.net - open when you want to play."),
    "upc.exe":                ("medium", "disable", "Ubisoft Connect - can start on demand."),
    "origin.exe":             ("high",   "disable", "EA Origin - large process, open when gaming."),
    "adobeupdatedaemon.exe":  ("medium", "disable", "Adobe updater - update manually from the app."),
    "acrobat.exe":            ("medium", "delay",   "PDF viewer - only needed when opening PDF files."),
    "ccleaner64.exe":         ("low",    "keep",    "Lightweight cleaner - fine to keep in startup."),
    "malwarebytes.exe":       ("low",    "keep",    "Security tool - recommended to keep running."),
    "msiafterburner.exe":     ("low",    "keep",    "GPU OC utility - keep if actively using fan curves."),
    "hwinfo64.exe":           ("low",    "keep",    "Hardware monitor - lightweight, keep if using sensors."),
    "corsairhid.exe":         ("low",    "keep",    "Corsair iCUE - needed for RGB and macros."),
    "razercentralservice.exe":("low",    "keep",    "Razer Synapse - needed for G keys and lighting."),
    "lghub.exe":              ("low",    "keep",    "Logitech G HUB - needed for G-series devices."),
    "curve.exe":              ("medium", "delay",   "NZXT CAM - can delay startup without issues."),
    # Screenshot / recording
    "sharex.exe":             ("low",    "keep",    "ShareX screenshot & recording - lightweight, safe to keep."),
    "lightshot.exe":          ("low",    "keep",    "Lightshot screenshot tool - very lightweight."),
    "obs64.exe":              ("medium", "delay",   "OBS Studio - start manually when streaming/recording."),
    "obs32.exe":              ("medium", "delay",   "OBS Studio (32-bit) - start manually when needed."),
    # Remote / streaming
    "parsec.exe":             ("low",    "keep",    "Parsec remote desktop - keep if used regularly."),
    "rustdesk.exe":           ("medium", "delay",   "RustDesk remote desktop - start on demand."),
    "anydesk.exe":            ("medium", "delay",   "AnyDesk remote access - start manually when needed."),
    # Password managers
    "bitwarden.exe":          ("low",    "keep",    "Bitwarden password manager - keep for autofill."),
    "keepassxc.exe":          ("low",    "keep",    "KeePassXC password manager - keep for autofill."),
    # Cloud / sync
    "nextcloud.exe":          ("medium", "delay",   "Nextcloud desktop sync - delayed start is fine."),
    "megasync.exe":           ("medium", "delay",   "MEGA cloud sync - can start delayed."),
    # Dev / heavy tools
    "docker desktop.exe":     ("high",   "disable", "Docker Desktop - heavy, start manually when developing."),
}


# Entries whose file is not in _KNOWN were all "low / keep" (2026-11-16): on
# the test PC 24 of 24 entries, among them Teams, Driver Booster and Edge's
# auto-launch, so the optimization guide said "clean". Rules by name, first
# match wins; (fragment, impact, recommendation, why).
STARTUP_NAME_RULES: list[tuple[str, str, str, str]] = [
    ("securityhealth",          "low",    "keep",    "Windows Security - keep it."),
    ("vanguard",                "low",    "keep",    "Riot anti-cheat - Valorant / LoL need it at boot."),
    ("anticheat",               "low",    "keep",    "Anti-cheat - games need it."),
    ("pc_workman",              "low",    "keep",    "PC Workman itself."),
    ("teams",                   "high",   "disable", "Heavy at boot. Open it when you have a meeting."),
    ("driverbooster",           "medium", "disable", "Driver updater. Windows Update and the card maker's app do this."),
    ("driver booster",          "medium", "disable", "Driver updater. Windows Update and the card maker's app do this."),
    ("edgeautolaunch",          "medium", "disable", "Edge preloads itself at login even if you use another browser."),
    ("browser assistant",       "low",    "disable", "Browser helper, not needed at boot."),
    ("opera gx stable",         "medium", "delay",   "The browser opens itself at login. Start it when you need it."),
    ("opera stable",            "medium", "delay",   "The browser opens itself at login. Start it when you need it."),
    ("linkedin",                "low",    "disable", "LinkedIn app, not needed at boot."),
    ("yourphone",               "low",    "disable", "Phone Link - only if you connect a phone."),
    ("crossdevice",             "low",    "disable", "Cross-device sync - only if you use a phone with Windows."),
    ("gamingapp",               "medium", "disable", "Xbox app - unless you use Game Pass every day."),
    ("spotify",                 "medium", "disable", "Starts music at login. Open it when you listen."),
    ("steam",                   "medium", "delay",   "Launcher. Start it when you play."),
    ("epicgames",               "medium", "delay",   "Launcher. Start it when you play."),
    ("ea desktop",              "medium", "delay",   "Launcher. Start it when you play."),
    ("ubisoft",                 "medium", "delay",   "Launcher. Start it when you play."),
    ("gpu tweak",               "medium", "keep",    "Keep only if you use its overclock or fan profile."),
    ("msicenter",               "medium", "keep",    "Needed for MSI fan / lighting profiles."),
    ("autoupdate",              "low",    "keep",    "Updater task, runs briefly."),
    ("nvnodelauncher",          "low",    "keep",    "NVIDIA helper, light."),
    ("nvprofileupdater",        "low",    "keep",    "NVIDIA helper, light."),
    ("onedrive",                "medium", "keep",    "Keep if you sync files with OneDrive."),
    ("cortana",                 "low",    "disable", "Not needed."),
]


# Programs that sit in the background without being asked to and can be
# closed or kept out of startup (was hck_GPT's _BACKGROUND_BLOAT).
BACKGROUND_OPTIONAL = frozenset({
    "epicgameslauncher.exe", "battlenet.exe", "battle.net.exe", "ubisoft connect.exe",
    "upc.exe", "gog galaxy.exe", "galaxyclient.exe", "ea app.exe", "eadesktop.exe",
    "rockstarlauncher.exe", "nvidiasharecontainer.exe", "adobeupdateservice.exe",
    "adobearm.exe", "creativeclouduis.exe", "ccleaner64.exe", "ccleanermonitor.exe",
    "microsoftedgeupdate.exe", "googleupdater.exe", "skype.exe", "cortana.exe",
})

_ACTION_FROM_REC = {"disable": "startup_off", "delay": "delay", "keep": "keep"}


def _startup_advice(exe: str, name: str = ""):
    hit = STARTUP_KNOWN.get(exe)
    if hit:
        return hit
    # The name rules were written for startup entries ("Steam", "Teams").
    # For a running process the rule must name the program itself, not a
    # helper that starts with the same word: steamwebhelper.exe got "delay
    # start" from the "steam" rule (2026-11-20). msteams.exe still matches
    # "teams" (two letters of prefix).
    stem = exe[:-4] if exe.endswith(".exe") else exe
    stem = stem.replace(" ", "")
    for frag, impact, rec, why in STARTUP_NAME_RULES:
        f = frag.replace(" ", "")
        if stem == f or (stem.endswith(f) and len(stem) - len(f) <= 2):
            return impact, rec, why
    return None


def recommend(process_name: str, display_name: str = "") -> dict:
    exe = (process_name or "").strip().lower()
    out = {"action": "keep", "impact": "low", "why": "", "source": ""}
    if not exe:
        return out
    try:
        from core.protected_processes import is_protected
        if is_protected(exe):
            out.update(action="protected", source="protected",
                       why="Windows, an anti-cheat or PC Workman itself: never switched off.")
            return out
    except Exception:
        pass
    adv = _startup_advice(exe, display_name)
    if adv:
        impact, rec, why = adv
        out.update(action=_ACTION_FROM_REC.get(rec, "keep"), impact=impact,
                   why=why, source="startup")
        return out
    if exe in BACKGROUND_OPTIONAL:
        out.update(action="close_ok", impact="medium", source="background",
                   why="Runs in the background without being needed; it can be closed and kept out of startup.")
        return out
    return out


def worth_switching_off(process_name: str, display_name: str = "") -> bool:
    """True when the advice is to take it out of startup, delay it or close it."""
    return recommend(process_name, display_name)["action"] in ("startup_off", "delay", "close_ok")
