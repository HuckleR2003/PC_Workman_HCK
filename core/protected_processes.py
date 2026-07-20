"""
core/protected_processes.py - the ONE authoritative "never touch" list.

A tester got kicked from League while PC Workman was running and suspected our
optimizer had frozen Riot Vanguard. Suspending, idle-prioritising or trimming
the memory of an anti-cheat process can crash the game or trip the anti-cheat
into thinking the system is being tampered with - a possible ban. So this is a
hard safety rule, not a preference.

Before this module the protection lists were scattered (TURBO had its own,
hibernation had none, RAM Flush had a user list only). Now every mutation
primitive - hibernation_manager.sleep_app, turbo_manager suspension,
optimization RAM-flush EmptyWorkingSet, the overlay kill/suspend - calls
`is_protected()` and refuses. Defense in depth: guarded at the lowest level so
no caller can bypass it.

Covers anti-cheat engines + their kernel/service components. System-critical and
security processes keep their existing guards elsewhere; this list is additive.
"""

# Exact process names (lowercase, with and without .exe where relevant).
PROTECTED_EXES = frozenset({
    # ── Riot Vanguard (Valorant / League of Legends) ──────────────────────────
    "vgc.exe", "vgtray.exe", "vgk.sys", "vanguard.exe",
    "riotclientservices.exe",            # tied to Vanguard's handshake
    # ── EasyAntiCheat (Fortnite, Apex, many UE titles) ────────────────────────
    "easyanticheat.exe", "easyanticheat_eos.exe", "easyanticheat_x64.exe",
    "easyanticheatlauncher.exe", "easyanticheat_setup.exe",
    # ── BattlEye (R6 Siege, PUBG, DayZ, Destiny 2) ────────────────────────────
    "beservice.exe", "beservice_x64.exe", "bedaisy.sys", "belauncher.exe",
    "battleye.exe",
    # ── FACEIT Anti-Cheat (CS2 / competitive) ─────────────────────────────────
    "faceitclient.exe", "faceit.exe", "faceitservice.exe", "faceitac.exe",
    # ── Other major anti-cheats ───────────────────────────────────────────────
    "pnkbstra.exe", "pnkbstrb.exe",       # PunkBuster
    "gameguard.des", "npggnt.des", "gamemon.des",   # nProtect GameGuard
    "xigncode.xem", "xhunter1.sys",        # XIGNCODE3
    "mhyprot2.sys", "mhyprot3.sys",        # miHoYo (Genshin / HSR)
    "acbase.sys",                          # ACE (Riot's older / Tencent)
    "sgware.exe", "wellbia.exe", "wbia.exe",
    "ricochet.exe",                        # Call of Duty
})

# Substring keywords (matched against name AND full exe path, lowercase).
# Kept specific enough to avoid false positives on unrelated processes.
PROTECTED_KEYWORDS = (
    "anticheat", "anti-cheat", "vanguard", "battleye", "easyanti",
    "punkbuster", "gameguard", "faceit", "xigncode", "nprotect",
    "riot vanguard", "\\vgc", "mhyprot",
)

# ── OS-critical processes ─────────────────────────────────────────────────────
# Suspending or idle-prioritising any of these freezes the machine: freeze
# dwm.exe or explorer.exe and you get a white screen and an eternal lag until
# Explorer is force-restarted. This was a real crash: App Hibernation's
# sleep_app only guarded anti-cheat, so a critical process (or PC Workman
# itself) could be frozen. These must never be suspended / killed / memory-
# trimmed by us. (RAM-flush trimming them is benign but we skip them anyway for
# one consistent rule.)
SYSTEM_CRITICAL = frozenset({
    "system", "registry", "idle", "memory compression",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
    "lsass.exe", "svchost.exe", "dwm.exe", "explorer.exe", "fontdrvhost.exe",
    "conhost.exe", "taskhostw.exe", "sihost.exe", "ctfmon.exe", "spoolsv.exe",
    "runtimebroker.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "searchhost.exe", "searchindexer.exe", "searchapp.exe", "audiodg.exe",
    "dllhost.exe", "wudfhost.exe", "lsaiso.exe", "wininet.exe",
    # Windows Security / Defender
    "msmpeng.exe", "mpcmdrun.exe", "nissrv.exe", "securityhealthservice.exe",
    "securityhealthsystray.exe",
})

# PC Workman's own process, by name (the os.getpid() check is the robust guard;
# these cover child/helper processes launched under a different pid).
SELF_NAMES = frozenset({
    "pc workman hck.exe", "pcworkman.exe", "startup.py",
    "python.exe", "pythonw.exe",
})


def is_self(pid: int) -> bool:
    """True if pid is PC Workman's own process - never sleep/kill ourselves."""
    try:
        import os
        return int(pid) == os.getpid()
    except Exception:
        return False


def is_protected(name: str, exe: str = "") -> bool:
    """True if *name*/*exe* must never be suspended, idle-prioritised, memory-
    trimmed or killed by us: an anti-cheat, an OS-critical process, or PC
    Workman itself. This is the single guard every process primitive consults."""
    try:
        nl = (name or "").strip().lower()
        el = (exe or "").strip().lower()
    except Exception:
        return False
    if not nl and not el:
        return False
    base = nl.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
    if nl in PROTECTED_EXES or base in PROTECTED_EXES:
        return True
    if nl in SYSTEM_CRITICAL or base in SYSTEM_CRITICAL:
        return True
    if nl in SELF_NAMES or base in SELF_NAMES:
        return True
    for kw in PROTECTED_KEYWORDS:
        if kw in nl or kw in el:
            return True
    return False
