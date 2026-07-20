"""hck_gpt.responses.r_system - SystemResponses mixin (13 intent handlers).
Split out of the builder.py monolith; composed into ResponseBuilder via MRO."""
from hck_gpt.responses.common import (  # shared helpers/data
    List,
    ParseResult,
    _IDLE_PROC_NAMES,
    _followup,
    _hw_profile,
    _t,
)


class SystemResponses:
    def _resp_processes(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
            # Cap iteration at 128 processes to avoid hangs on loaded systems
            raw = []
            for p in psutil.process_iter(["name", "cpu_percent"]):
                try:
                    raw.append(p)
                    if len(raw) >= 128:
                        break
                except Exception:
                    continue
            procs = [
                p for p in sorted(
                    raw,
                    key=lambda p: p.info.get("cpu_percent", 0) or 0,
                    reverse=True,
                )
                if (p.info.get("name") or "").lower() not in _IDLE_PROC_NAMES
            ][:5]
            header = _t(lang,
                        f"{self.PREFIX} Top procesy CPU teraz:",
                        f"{self.PREFIX} Top CPU processes now:")
            lines = [header]
            for i, p in enumerate(procs, 1):
                name = (p.info.get("name") or "?")[:28]
                pct  = p.info.get("cpu_percent", 0) or 0
                lines.append(f"  {i}. {name:<28}  {pct:.1f}%")
            return lines
        except Exception:
            return [_t(lang,
                       f"{self.PREFIX} Brak danych o procesach. Sprawdź: zakładka Efficiency",
                       f"{self.PREFIX} No process data. Check: Efficiency tab")]

    def _resp_virus_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        # Powered by the Process Suspect Guard engine: author (Authenticode)
        # verification + typosquat/homoglyph detection + masquerade checks.
        try:
            from core.process_guard import process_guard as _guard
        except Exception:
            return [_t(lang,
                       f"{self.PREFIX} Nie mogę teraz uruchomić skanera.",
                       f"{self.PREFIX} Cannot run the security scanner right now.")]

        summary = _guard.scan_summary(deep=True)
        counts  = summary["counts"]
        threats = summary["threats"]

        if threats:
            lines = [_t(lang,
                f"{self.PREFIX} ⚠ Process Suspect Guard - wykryto zagrożenia!",
                f"{self.PREFIX} ⚠ Process Suspect Guard - threats detected!")]
            for f in threats[:6]:
                lines.append(f"  {f.name}  (risk {f.score}/100)")
                for rl in f.reason_lines(lang)[:2]:
                    lines.append(f"     {rl}")
                if f.publisher:
                    lines.append(_t(lang, f"     Autor: {f.publisher}",
                                          f"     Author: {f.publisher}"))
            lines.append(_t(lang,
                "  → Optimization → ANTIVIRUS: zawieś / zakończ / dodaj do zaufanych.",
                "  → Optimization → ANTIVIRUS: suspend / kill / trust."))
            lines.append(_followup("security", lang))
            return lines

        lines = [_t(lang,
            f"{self.PREFIX} ✓ Skan bezpieczeństwa - brak zagrożeń.",
            f"{self.PREFIX} ✓ Security scan - no threats found.")]
        lines.append(_t(lang,
            "  Zweryfikowałem autorów (podpisy), nazwy i lokalizacje procesów.",
            "  Verified process authors (signatures), names and locations."))
        n_caution = counts.get("caution", 0)
        if n_caution:
            lines.append(_t(lang,
                f"  {n_caution} proces(y) warte uwagi (nie groźne) - szczegóły w ANTIVIRUS.",
                f"  {n_caution} process(es) worth a look (not dangerous) - see ANTIVIRUS."))
        lines.append(_followup("security", lang))
        return lines

    def _resp_unnecessary_programs(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
        except Exception:
            return [_t(lang,
                       f"{self.PREFIX} Brak dostępu do procesów.",
                       f"{self.PREFIX} Cannot read process list.")]

        running_names: list[str] = []
        try:
            for proc in psutil.process_iter(["name", "memory_info"]):
                try:
                    n = (proc.info.get("name") or "").lower()
                    if n:
                        running_names.append(n)
                except Exception:
                    continue
        except Exception:
            pass

        found_bloat: list[str] = []
        for name in running_names:
            if name in self._BACKGROUND_BLOAT:
                found_bloat.append(name)

        header = _t(lang,
                    f"{self.PREFIX} Programy działające w tle:",
                    f"{self.PREFIX} Background program check:")

        if not found_bloat:
            return [
                header,
                _t(lang,
                   "  ✓ Żadnych znanych zbędnych procesów w tle.",
                   "  ✓ No known unnecessary background apps detected."),
                _t(lang,
                   "  Możesz sprawdzić dalej: zakładka Efficiency -> lista procesów.",
                   "  You can dig deeper: Efficiency tab -> full process list."),
            ]

        lines = [
            header,
            _t(lang,
               f"  Znaleziono {len(found_bloat)} zbędnych procesów:",
               f"  Found {len(found_bloat)} potentially unnecessary programs:"),
        ]
        for b in found_bloat[:8]:
            lines.append(f"  - {b}")
        lines.append(_t(lang,
                        "  Możesz je wyłączyć ze startu: Start -> Menedżer zadań -> Autostart.",
                        "  Disable from startup: Start -> Task Manager -> Startup apps."))
        return lines

    def _resp_process_info(self, r: ParseResult, lang: str = "pl") -> List[str]:
        # Try to extract process name from raw text
        raw = (r.raw_text or "").lower()
        matched_key = None
        matched_val = None
        for proc_name, (pl_desc, en_desc) in self._KNOWN_PROCS.items():
            if proc_name.replace(".exe", "") in raw or proc_name in raw:
                matched_key = proc_name
                matched_val = (pl_desc, en_desc)
                break

        if matched_val:
            desc = matched_val[1] if lang == "en" else matched_val[0]
            return [f"{self.PREFIX} {matched_key}:", f"  {desc}", _followup("process", lang)]

        # Generic fallback - suggest process library
        if lang == "en":
            return [
                f"{self.PREFIX} I don't have specific info on that process.",
                "  Check: Efficiency tab -> click on the process for details.",
                "  General rule: if it's Microsoft-signed and low CPU - safe.",
                "  High CPU + unknown name -> worth investigating.",
                _followup("process", lang),
            ]
        return [
            f"{self.PREFIX} Nie mam konkretnych danych o tym procesie.",
            "  Sprawdź: zakładka Efficiency -> kliknij na proces.",
            "  Ogólna zasada: podpisany przez Microsoft i mało CPU - bezpieczny.",
            "  Dużo CPU + nieznana nazwa -> warto sprawdzić.",
            _followup("process", lang),
        ]

    def _resp_startup_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        entries: list[tuple[str, str]] = []
        try:
            import winreg
            _REG = [
                (winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
            ]
            seen: set[str] = set()
            for hive, path in _REG:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            name, val, _ = winreg.EnumValue(key, i)
                            slug = name.lower().replace(" ", "").replace("-", "")
                            if slug not in seen:
                                seen.add(slug)
                                entries.append((name, val))
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    continue
        except Exception:
            pass

        if not entries:
            return [_t(lang,
                       f"{self.PREFIX} Nie mogę odczytać wpisów startowych.",
                       f"{self.PREFIX} Can't read startup entries.")]

        high, medium, low = [], [], []
        for name, val in entries:
            exe = val.lower()
            slug = name.lower().replace(" ", "").replace("-", "")
            if any(k in exe or k in slug for k in self._HIGH_IMPACT_STARTUP):
                high.append(name)
            elif any(k in exe or k in slug for k in self._MEDIUM_IMPACT_STARTUP):
                medium.append(name)
            else:
                low.append(name)

        total = len(entries)
        verdict = ""
        if total <= 4:
            verdict = _t(lang, "✓ Bardzo dobry autostart.", "✓ Very clean startup.")
        elif total <= 8:
            verdict = _t(lang, "Umiarkowany autostart - da się zoptymalizować.", "Moderate startup - could be trimmed.")
        else:
            verdict = _t(lang, "⚠ Za dużo elementów startowych - spowolnienie boot.", "⚠ Too many startup items - boot is slower.")

        lines = [_t(lang,
                    f"{self.PREFIX} Programy startowe ({total} wpisów):",
                    f"{self.PREFIX} Startup programs ({total} entries):")]
        lines.append(f"  {verdict}")
        if high:
            lines.append(_t(lang,
                            f"  Wysoki wpływ ({len(high)}): {', '.join(high[:4])}",
                            f"  High impact ({len(high)}): {', '.join(high[:4])}"))
        if medium:
            lines.append(_t(lang,
                            f"  Średni wpływ ({len(medium)}): {', '.join(medium[:4])}",
                            f"  Medium impact ({len(medium)}): {', '.join(medium[:4])}"))
        if low:
            lines.append(_t(lang,
                            f"  Niski wpływ ({len(low)}): {', '.join(low[:3])}{'...' if len(low) > 3 else ''}",
                            f"  Low impact ({len(low)}): {', '.join(low[:3])}{'...' if len(low) > 3 else ''}"))
        lines.append("")
        lines.append(_t(lang,
                        "  💬 Przejdź do Menadżera  [-> Startup Manager]   ·   lub napisz, co wyłączyć",
                        "  💬 Open the Manager  [-> Startup Manager]   ·   or tell me what to disable"))
        lines.append(_t(lang,
                        "  Wszystko, co wyłączysz, bezpiecznie włączysz z powrotem w zakładce Disabled.",
                        "  Anything you disable can be safely switched back on in the Disabled tab."))
        return lines

    def _resp_startup_safety(self, r: ParseResult, lang: str = "pl") -> List[str]:
        raw = (r.raw_text or "").lower()

        matched_slug = None
        matched_data = None
        for slug, data in self._STARTUP_SAFETY_KB.items():
            if slug in raw:
                matched_slug = slug
                matched_data = data
                break

        if matched_data:
            safe, reason_pl, reason_en = matched_data
            if safe is True:
                verdict = _t(lang, "✓ Bezpieczne do wyłączenia ze startu:", "✓ Safe to disable from startup:")
            elif safe is False:
                verdict = _t(lang, "⚠ Lepiej zostawić włączone:", "⚠ Better to keep enabled:")
            else:
                verdict = _t(lang, "➤ Zależy od użycia:", "➤ Depends on your usage:")
            reason = reason_en if lang == "en" else reason_pl
            return [
                _t(lang,
                   f"{self.PREFIX} Autostart - {matched_slug}:",
                   f"{self.PREFIX} Startup - {matched_slug}:"),
                f"  {verdict}",
                f"  {reason}",
                _t(lang,
                   "  Zarządzaj tym i innymi wpisami  [-> Startup Manager]",
                   "  Manage this and other startup entries  [-> Startup Manager]"),
                _followup("startup", lang),
            ]

        # No specific program matched - general guide
        if lang == "en":
            return [
                f"{self.PREFIX} Startup program safety guide:",
                "  ✓ Safe to disable:  Chrome, Firefox, Spotify, Discord, Steam, game launchers",
                "  ➤ Depends on use:   OneDrive, Teams, Zoom - disable if not used daily",
                "  ⚠ Keep enabled:     security software, audio/GPU drivers, system services",
                "  Rule: if you can launch it manually when you need it - disable it at boot.",
                "  💬 See all your startup entries  [-> Startup Manager]",
                _followup("startup", lang),
            ]
        return [
            f"{self.PREFIX} Poradnik - co wyłączyć ze startu:",
            "  ✓ Bezpieczne:    Chrome, Firefox, Spotify, Discord, Steam, launchery gier",
            "  ➤ Zależy:        OneDrive, Teams, Zoom - wyłącz jeśli nie używasz codziennie",
            "  ⚠ Zostaw:        antywirus, sterowniki audio/GPU, usługi systemowe",
            "  Zasada: jeśli możesz uruchomić ręcznie - nie potrzebuje startować z Windows.",
            "  💬 Przejrzyj wszystkie wpisy  [-> Startup Manager]",
            _followup("startup", lang),
        ]

    def _resp_system_risk(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Ranks current system state by risk level across performance,
        security and stability dimensions. Inspired by: 'which recent system
        changes are creating the highest performance, security, or stability risk?'
        """
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.user_knowledge  import user_knowledge
        snap    = system_context.snapshot()
        hw      = user_knowledge.get_all_hardware()
        profile = _hw_profile(hw)

        # risks: list of (level, message) - level 3=high, 2=medium, 1=info
        risks: list[tuple[int, str]] = []

        cpu = float(snap.get("cpu_pct", 0) or 0)
        ram = float(snap.get("ram_pct", 0) or 0)

        # ── Performance ───────────────────────────────────────────────────────
        if cpu > 85:
            risks.append((3, _t(lang,
                f"🔴 CPU {cpu:.0f}% - ryzyko throttlingu i spowolnień (wydajność)",
                f"🔴 CPU {cpu:.0f}% - throttle and slowdown risk (performance)")))
        elif cpu > 70:
            risks.append((2, _t(lang,
                f"🟡 CPU {cpu:.0f}% - podwyższone obciążenie, mały margines",
                f"🟡 CPU {cpu:.0f}% - elevated load, low headroom")))

        if ram > 85:
            risks.append((3, _t(lang,
                f"🔴 RAM {ram:.0f}% - system może używać pagefile (stabilność/wydajność)",
                f"🔴 RAM {ram:.0f}% - system may be swapping to pagefile (stability/performance)")))
        elif ram > 70:
            risks.append((2, _t(lang,
                f"🟡 RAM {ram:.0f}% - mało wolnej pamięci, reaguj przy 85%+",
                f"🟡 RAM {ram:.0f}% - low free memory headroom, act at 85%+")))

        if snap.get("cpu_throttled"):
            risks.append((3, _t(lang,
                "🔴 CPU throttluje - moc ograniczona (przegrzanie / power limit) (stabilność)",
                "🔴 CPU throttling - power is being limited (heat or power limit) (stability)")))

        # ── Disk space ────────────────────────────────────────────────────────
        try:
            import psutil
            for p in psutil.disk_partitions(all=False):
                if "remote" in (p.opts or "").lower():
                    continue
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    if u.percent > 90:
                        free_gb = round(u.free / 1_073_741_824, 1)
                        risks.append((3, _t(lang,
                            f"🔴 Dysk {p.device}: {u.percent:.0f}% pełny ({free_gb} GB wolne) - ryzyko awarii zapisu (stabilność)",
                            f"🔴 Drive {p.device}: {u.percent:.0f}% full ({free_gb} GB free) - write failure risk (stability)")))
                    elif u.percent > 80:
                        risks.append((2, _t(lang,
                            f"🟡 Dysk {p.device}: {u.percent:.0f}% zajęty - zacznij zwalniać miejsce",
                            f"🟡 Drive {p.device}: {u.percent:.0f}% used - start freeing space")))
                except Exception:
                    pass
        except Exception:
            pass

        # ── Startup count ─────────────────────────────────────────────────────
        try:
            import winreg
            startup_count = 0
            for hive, path in [
                (winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            winreg.EnumValue(key, i)
                            startup_count += 1
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    pass
            if startup_count > 12:
                risks.append((2, _t(lang,
                    f"🟡 Autostart: {startup_count} wpisów - zbędne tło + wolniejszy boot (wydajność)",
                    f"🟡 Startup: {startup_count} entries - background bloat + slower boot (performance)")))
            elif startup_count > 8:
                risks.append((1, _t(lang,
                    f"ℹ Autostart: {startup_count} wpisów - warto przejrzeć  [-> Startup Manager]",
                    f"ℹ Startup: {startup_count} entries - worth reviewing  [-> Startup Manager]")))
        except Exception:
            pass

        # ── Hardware profile ──────────────────────────────────────────────────
        if profile["ram_very_low"]:
            risks.append((3, _t(lang,
                f"🔴 RAM: tylko {profile['ram_gb']:.0f} GB - krytycznie mało dla nowoczesnych systemów",
                f"🔴 RAM: only {profile['ram_gb']:.0f} GB - critically low for modern workloads")))
        elif profile["ram_low"] and ram > 60:
            risks.append((2, _t(lang,
                f"🟡 RAM: {profile['ram_gb']:.0f} GB + {ram:.0f}% zajęte - bardzo mały margines",
                f"🟡 RAM: {profile['ram_gb']:.0f} GB + {ram:.0f}% used - very low margin")))
        if profile["is_hdd"]:
            risks.append((1, _t(lang,
                "ℹ HDD wykryty - wolniejszy dysk to systemowe spowolnienie przy każdej operacji na plikach",
                "ℹ HDD detected - slower disk causes system-wide slowdowns during file operations")))

        # ── Security ─────────────────────────────────────────────────────────
        try:
            import psutil
            from hck_gpt.process_library import process_library as _lib
            _SUSPICIOUS_KW = {"xmrig", "cpuminer", "nicehash", "minerd", "cgminer"}
            susp: list[str] = []
            checked = 0
            for proc in psutil.process_iter(["name"]):
                try:
                    nm = (proc.info.get("name") or "").lower()
                    base = nm.replace(".exe", "")
                    if any(kw in base for kw in _SUSPICIOUS_KW):
                        susp.append(nm)
                    else:
                        info = _lib.get_process_info(nm)
                        if info and info.get("safety") in ("suspicious", "unsafe"):
                            susp.append(nm)
                    checked += 1
                    if checked >= 120:
                        break
                except Exception:
                    continue
            if susp:
                names = ", ".join(susp[:3])
                risks.append((3, _t(lang,
                    f"🔴 Bezpieczeństwo: {len(susp)} podejrzanych procesów ({names}) - sprawdź natychmiast",
                    f"🔴 Security: {len(susp)} suspicious process(es) ({names}) - check immediately")))
        except Exception:
            pass

        # ── Sort descending by risk level ─────────────────────────────────────
        risks.sort(key=lambda x: x[0], reverse=True)

        header = _t(lang,
            f"{self.PREFIX} Analiza ryzyka systemu:",
            f"{self.PREFIX} System risk assessment:")
        lines = [header]

        if not risks:
            lines.append(_t(lang,
                "  ✅ Nie znaleziono aktywnych ryzyk. System wygląda zdrowo.",
                "  ✅ No active risks found. System looks healthy."))
        else:
            lines.append(_t(lang,
                f"  Wykryto {len(risks)} czynnik(ów) ryzyka - od najwyższego:",
                f"  Found {len(risks)} risk factor(s) - ranked highest first:"))
            for _, msg in risks[:6]:
                lines.append(f"  {msg}")

        lines.append("")
        lines.append(_t(lang,
            "  💬 Wpisz 'przyspiesz komputer' po plan naprawy  ·  'zdrowie systemu' po pełną diagnozę",
            "  💬 Type 'speed up pc' for a fix plan  ·  'health check' for full diagnostics"))
        lines.append(_followup("health", lang))
        return lines

    def _resp_driver_status(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Shows GPU/display/audio driver info with dates via PowerShell/WMI.
        Color-codes by age: <6 months green, 6-18 months yellow, >18 months red.
        """
        import subprocess, datetime

        lines = [_t(lang,
            f"{self.PREFIX} Status sterowników (kluczowe):",
            f"{self.PREFIX} Driver status (key drivers):")]

        # Query via PowerShell - fastest way to get driver dates on Windows
        ps_cmd = (
            "Get-WmiObject Win32_PnPSignedDriver | "
            "Where-Object {$_.DeviceName -match 'Display|VGA|NVIDIA|AMD|Radeon|Intel.*Graphics|"
            "Audio|Sound|High Definition|Ethernet|Wi-Fi|Wireless'} | "
            "Select-Object DeviceName,DriverVersion,DriverDate | "
            "ConvertTo-Json"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, errors="replace", timeout=8
            )
            import json as _json
            raw = result.stdout.strip()
            if not raw:
                raise ValueError("empty")
            data = _json.loads(raw)
            if isinstance(data, dict):
                data = [data]

            now = datetime.datetime.now()
            for drv in data[:8]:
                name    = (drv.get("DeviceName")    or "?")[:40]
                version = (drv.get("DriverVersion") or "?")[:20]
                date_raw = drv.get("DriverDate") or ""

                # WMI DriverDate format: "20231005000000.000000-000"
                age_str = "?"
                color   = ""
                try:
                    date_str = date_raw[:8]  # YYYYMMDD
                    dt = datetime.datetime.strptime(date_str, "%Y%m%d")
                    months = (now - dt).days // 30
                    age_str = f"{months}m"
                    if months < 6:
                        color = "✓"
                    elif months < 18:
                        color = "!"
                    else:
                        color = "⚠"
                except Exception:
                    color = " "

                lines.append(f"  {color} {name[:38]}")
                lines.append(f"    ver {version}  ·  {age_str} old")
        except Exception:
            lines.append(_t(lang,
                "  Nie udało się pobrać listy sterowników przez PowerShell.",
                "  Could not retrieve driver list via PowerShell."))
            lines.append(_t(lang,
                "  Sprawdź ręcznie: Start -> Menedżer urządzeń",
                "  Check manually: Start -> Device Manager"))

        lines.append("")
        lines.append(_t(lang,
            "  ⚠ = starszy niż 18 mies.  !  = 6–18 mies.  ✓ = świeży (<6 mies.)",
            "  ⚠ = older than 18 months  !  = 6–18 months  ✓ = recent (<6 months)"))
        lines.append(_t(lang,
            "  Zaktualizuj sterowniki GPU w: NVIDIA GeForce Experience / AMD Software",
            "  Update GPU drivers in: NVIDIA GeForce Experience / AMD Software"))
        return lines

    def _resp_process_identity(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Checks if a named .exe is part of Windows, a known app, or suspicious.
        Uses the process_library and a Windows system path check.
        """

        raw = (r.raw_text or "").lower()

        # Extract .exe name from query
        import re as _re
        match = _re.search(r'[\w\-]+\.exe', raw)
        proc_name = match.group(0) if match else None

        # Also try without .exe if user typed e.g. "co to conhost"
        if not proc_name:
            _WIN_PROCS = {
                "svchost", "csrss", "lsass", "winlogon", "services", "smss",
                "conhost", "dwm", "ntoskrnl", "explorer", "taskhostw",
                "msiexec", "werfault", "searchindexer", "spoolsv",
                "audiodg", "runtimebroker", "settingssynchost",
            }
            for wp in _WIN_PROCS:
                if wp in raw:
                    proc_name = wp + ".exe"
                    break

        if not proc_name:
            if lang == "en":
                return [
                    f"{self.PREFIX} Which process do you want me to check?",
                    "  Include the .exe name, e.g.: 'is conhost.exe safe'",
                    "  or: 'what is werfault.exe'",
                ]
            return [
                f"{self.PREFIX} Który proces chcesz sprawdzić?",
                "  Podaj nazwę .exe, np.: 'czy conhost.exe jest bezpieczny'",
                "  lub: 'co to jest werfault.exe'",
            ]

        # ── Process Suspect Guard: author (signature) + typosquat + masquerade ──
        exe = ""
        pid = None
        try:
            import psutil
            for proc in psutil.process_iter(["name", "exe", "pid"]):
                try:
                    if (proc.info.get("name") or "").lower() == proc_name.lower():
                        exe = proc.info.get("exe") or ""
                        pid = proc.info.get("pid")
                        break
                except Exception:
                    continue
        except Exception:
            pass

        try:
            from core.process_guard import process_guard as _guard
            f = _guard.analyze(proc_name, exe=exe, pid=pid, deep=bool(exe))
        except Exception:
            f = None

        if f is None:
            return [_t(lang,
                f"{self.PREFIX} Nie mogę teraz sprawdzić {proc_name}.",
                f"{self.PREFIX} Cannot check {proc_name} right now.")]

        _icon = {"trusted": "✓", "unknown": "❓", "caution": "ℹ",
                 "suspicious": "⚠", "danger": "🔴"}.get(f.verdict, "❓")
        _label = {
            "trusted":    _t(lang, "Zaufany - wszystko się zgadza.",
                                    "Trusted - everything checks out."),
            "unknown":    _t(lang, "Nieznany - brak danych, ale i brak sygnałów zagrożenia.",
                                    "Unknown - no data, but no threat signals either."),
            "caution":    _t(lang, "Wart uwagi.", "Worth watching."),
            "suspicious": _t(lang, "Podejrzany - sprawdź uważnie.",
                                    "Suspicious - review carefully."),
            "danger":     _t(lang, "Niebezpieczny - reaguj.",
                                    "Dangerous - take action."),
        }.get(f.verdict, "")

        lines = [_t(lang,
            f"{self.PREFIX} Identyfikacja procesu - {proc_name}:",
            f"{self.PREFIX} Process identity - {proc_name}:")]
        lines.append(f"  {_icon} {_label}  (risk {f.score}/100)")
        for rl in f.reason_lines(lang):
            lines.append(f"  {rl}")
        if exe:
            lines.append(_t(lang, f"  Lokalizacja: {exe}", f"  Location: {exe}"))
        else:
            lines.append(_t(lang,
                "  (Proces nie jest teraz uruchomiony - sprawdzenie po samej nazwie.)",
                "  (Process not running right now - name-only check.)"))
        lines.append(_followup("security", lang))
        return lines

    def _resp_stale_apps(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Lists installed programs from registry that have not been seen
        in the process stats for 30+ days (if history available),
        or just shows all installed with last-seen fallback.
        """
        import winreg

        lines = [_t(lang,
            f"{self.PREFIX} Aplikacje prawdopodobnie nieużywane:",
            f"{self.PREFIX} Likely unused applications:")]

        installed: list[str] = []
        reg_paths = [
            (winreg.HKEY_CURRENT_USER,
             r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        seen: set[str] = set()
        try:
            for hive, path in reg_paths:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            sub = winreg.EnumKey(key, i)
                            try:
                                sub_key = winreg.OpenKey(key, sub)
                                name_val, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                                if name_val and name_val.lower() not in seen:
                                    seen.add(name_val.lower())
                                    installed.append(name_val)
                                winreg.CloseKey(sub_key)
                            except Exception:
                                pass
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    continue
        except Exception:
            pass

        if not installed:
            return self._no_data("stale_apps", lang,
                _t(lang, "brak dostępu do rejestru Uninstall", "no access to Uninstall registry"))

        # Filter obvious system/driver entries
        _SKIP = {"microsoft", "windows", "redistributable", "runtime", "update",
                 "directx", ".net", "visual c++", "driver", "intel", "amd", "nvidia",
                 "realtek", "vc_redist", "vcredist"}
        user_apps = [
            a for a in installed
            if not any(s in a.lower() for s in _SKIP)
        ][:20]

        # Try to cross-reference with process history in stats engine
        used_recently: set[str] = set()
        try:
            from hck_stats_engine.query_api import query_api
            from datetime import datetime
            today_str  = datetime.now().strftime("%Y-%m-%d")
            rows = query_api.get_process_daily_breakdown(today_str, top_n=50) or []
            for row in rows:
                nm = (row.get("process_name") or "").lower()
                for app in user_apps:
                    if nm[:8] in app.lower():
                        used_recently.add(app)
        except Exception:
            pass

        stale = [a for a in user_apps if a not in used_recently]

        if stale:
            lines.append(_t(lang,
                f"  Znaleziono {len(stale)} aplikacji bez widocznej aktywności w ostatnich 30 dniach:",
                f"  Found {len(stale)} apps with no visible activity in the last 30 days:"))
            for app in stale[:10]:
                lines.append(f"  - {app[:50]}")
            if len(stale) > 10:
                lines.append(_t(lang, f"  ... i {len(stale)-10} więcej", f"  ... and {len(stale)-10} more"))
        else:
            lines.append(_t(lang,
                "  Brak wyraźnie nieużywanych aplikacji w bazie ostatnich 30 dni.",
                "  No clearly unused apps found in last 30 days of process data."))

        lines.append("")
        lines.append(_t(lang,
            "  💡 Odinstaluj przez: Start -> Ustawienia -> Aplikacje",
            "  💡 Uninstall via: Start -> Settings -> Apps"))
        return lines

    def _resp_startup_slowdown(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Enhanced startup analysis - ranks startup entries by likely boot impact,
        measures current startup program count and gives actionable prioritization.
        """
        import winreg

        lines = [_t(lang,
            f"{self.PREFIX} Co zwalnia uruchamianie komputera:",
            f"{self.PREFIX} What slows down your PC startup:")]

        _HIGH_IMPACT = {
            "chrome", "opera", "operagx", "brave", "firefox", "edge",
            "epicgameslauncher", "steam", "battlenet", "ubisoft", "gog",
            "spotify", "discord", "discordptb", "onedrive", "dropbox",
            "teamviewer", "anydesk",
        }
        _MED_IMPACT = {
            "teams", "zoom", "slack", "telegram", "signal", "skype",
            "googledrive", "box", "mega",
        }

        entries: list[tuple[str, str, int]] = []  # (name, exe, impact 3/2/1)
        try:
            reg_paths = [
                (winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]
            seen: set[str] = set()
            for hive, path in reg_paths:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            name, val, _ = winreg.EnumValue(key, i)
                            slug = name.lower().replace(" ", "").replace("-", "")
                            if slug not in seen:
                                seen.add(slug)
                                exe  = val.lower()
                                slug2 = slug + exe
                                impact = 1
                                if any(k in slug2 for k in _HIGH_IMPACT):
                                    impact = 3
                                elif any(k in slug2 for k in _MED_IMPACT):
                                    impact = 2
                                entries.append((name, val[:60], impact))
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    continue
        except Exception:
            pass

        if not entries:
            return self._no_data("startup_slowdown", lang,
                _t(lang, "brak dostępu do rejestru Run", "no registry Run access"))

        # Sort by impact descending
        entries.sort(key=lambda x: x[2], reverse=True)
        total = len(entries)

        verdict = ""
        if total <= 4:
            verdict = _t(lang, "✓ Bardzo czysty autostart.", "✓ Very clean startup.")
        elif total <= 8:
            verdict = _t(lang, "! Umiarkowany - można skrócić czas boot.", "! Moderate - boot time can be reduced.")
        else:
            verdict = _t(lang, "⚠ Dużo wpisów - boot jest wyraźnie wolniejszy.", "⚠ Many entries - boot is noticeably slower.")

        lines.append(f"  {verdict}  ({total} wpisów / {total} entries)")
        lines.append(_t(lang, "  Największy wpływ (sugeruj wyłączyć):", "  Highest impact (suggest disabling):"))

        for name, exe, impact in entries[:6]:
            icon = "🔴" if impact == 3 else ("🟡" if impact == 2 else "  ")
            lines.append(f"  {icon} {name[:40]}")

        lines.append("")
        lines.append(_t(lang,
            "  💬 Zarządzaj wpisami  [-> Startup Manager]",
            "  💬 Manage entries  [-> Startup Manager]"))
        lines.append(_followup("startup", lang))
        return lines

    def _resp_process_deep_dive(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
            target = None
            ent = getattr(r, "entities", None) or {}
            wanted = str(ent.get("process", "") or "").lower()
            procs = []
            for p in psutil.process_iter(["name", "cpu_percent", "memory_info",
                                          "num_threads", "create_time"]):
                try:
                    procs.append(p)
                except Exception:
                    continue
            if wanted:
                target = next((p for p in procs
                               if wanted in (p.info.get("name") or "").lower()), None)
            if target is None:
                live = [p for p in procs
                        if (p.info.get("name") or "").lower() not in _IDLE_PROC_NAMES]
                target = max(live, key=lambda p: p.info.get("cpu_percent") or 0,
                             default=None)
            if target is None:
                raise RuntimeError
            import time as _tm
            nm  = target.info.get("name") or "?"
            cpu = target.info.get("cpu_percent") or 0
            ram = (target.info.get("memory_info").rss / (1024**2)
                   if target.info.get("memory_info") else 0)
            thr = target.info.get("num_threads") or 0
            up  = (_tm.time() - (target.info.get("create_time") or _tm.time())) / 60
            lines = [_t(lang, f"{self.PREFIX} Pod lupą: {nm}",
                              f"{self.PREFIX} Deep dive: {nm}")]
            lines.append(f"  CPU {cpu:.1f}% · RAM {ram:.0f} MB · "
                         + _t(lang, f"wątki {thr} · działa {up:.0f} min",
                                    f"threads {thr} · running {up:.0f} min"))
            try:
                from hck_gpt.process_library import process_library
                info = process_library.get(nm.lower())
                if info and info.get("description"):
                    lines.append(f"  ℹ {info['description'][:90]}")
            except Exception:
                pass
            lines.append(_t(lang, "  Tożsamość: napisz 'czy to wirus " + nm + "'",
                                  "  Identity: type 'is " + nm + " a virus'"))
            return lines
        except Exception:
            return [_t(lang,
                f"{self.PREFIX} Nie złapałem procesu do analizy - spróbuj 'top procesy'.",
                f"{self.PREFIX} Couldn't grab a process to analyse - try 'top processes'.")]

    def _resp_process_kill(self, r: ParseResult, lang: str = "pl") -> List[str]:
        # Safety by design: chat never kills anything - it points to the tools.
        lines = [_t(lang,
            f"{self.PREFIX} Nie zabijam procesów z czatu - jedno złe kill potrafi "
            "wywalić system. Bezpieczniejsze opcje:",
            f"{self.PREFIX} I don't kill processes from chat - one bad kill can "
            "take the system down. Safer options:")]
        lines.append(_t(lang,
            "  · App Hibernation usypia zamiast zabijać [-> Optimization]",
            "  · App Hibernation suspends instead of killing [-> Optimization]"))
        lines.append(_t(lang,
            "  · 'top procesy' pokaże co naprawdę zjada zasoby",
            "  · 'top processes' shows what actually eats resources"))
        try:
            import psutil
            top = max((p for p in psutil.process_iter(["name", "cpu_percent"])
                       if (p.info.get("name") or "").lower() not in _IDLE_PROC_NAMES),
                      key=lambda p: p.info.get("cpu_percent") or 0, default=None)
            if top is not None:
                lines.append(_t(lang,
                    f"  Największy teraz: {top.info.get('name')} "
                    f"({top.info.get('cpu_percent') or 0:.0f}% CPU)",
                    f"  Biggest right now: {top.info.get('name')} "
                    f"({top.info.get('cpu_percent') or 0:.0f}% CPU)"))
        except Exception:
            pass
        return lines

