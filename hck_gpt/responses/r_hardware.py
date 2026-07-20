"""hck_gpt.responses.r_hardware - HardwareResponses mixin (25 intent handlers).
Split out of the builder.py monolith; composed into ResponseBuilder via MRO."""
from hck_gpt.responses.common import (  # shared helpers/data
    List,
    ParseResult,
    _delta_label,
    _followup,
    _t,
)


class HardwareResponses:
    def _resp_hw_all(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        hw       = user_knowledge.get_all_hardware()
        patterns = user_knowledge.get_all_patterns()

        if not hw:
            return self._live_hw_fallback(lang)

        lines = [_t(lang,
                    f"{self.PREFIX} Twoje podzespoły:",
                    f"{self.PREFIX} Your components:")]

        # ── CPU ───────────────────────────────────────────────────────────────
        if hw.get("cpu_model"):
            cores   = hw.get("cpu_cores",    "?")
            threads = hw.get("cpu_threads",  "")
            boost   = hw.get("cpu_boost_ghz", "?")
            thr_str = f"/{threads}T" if threads and str(threads) != str(cores) else ""
            lines.append("  ◈ CPU")
            lines.append(f"    {hw['cpu_model']}")
            lines.append(f"    {cores}C{thr_str}  ·  boost {boost} GHz")

        # ── GPU ───────────────────────────────────────────────────────────────
        if hw.get("gpu_model"):
            vram_str = f"  ·  {hw['gpu_vram_gb']} GB VRAM" if hw.get("gpu_vram_gb") else ""
            lines.append("  ◈ GPU")
            lines.append(f"    {hw['gpu_model']}{vram_str}")

        # ── RAM ───────────────────────────────────────────────────────────────
        if hw.get("ram_total_gb"):
            spd     = f"  ·  {hw['ram_speed_mhz']} MHz" if hw.get("ram_speed_mhz") else ""
            typ_ram = patterns.get("typical_ram_avg")
            avg_str = f"  ·  avg {typ_ram}%" if typ_ram else ""
            lines.append("  ◈ RAM")
            lines.append(f"    {hw['ram_total_gb']} GB{spd}{avg_str}")

        # ── Storage ───────────────────────────────────────────────────────────
        lines.append("  ◈ " + _t(lang, "Dysk", "Storage"))
        disk_model = hw.get("disk_model")
        if disk_model:
            lines.append(f"    {disk_model}")
        try:
            import psutil
            for p in psutil.disk_partitions(all=False):
                if "remote" in (p.opts or "").lower():
                    continue
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    total_gb = round(u.total / 1_073_741_824, 1)
                    free_gb  = round(u.free  / 1_073_741_824, 1)
                    free_lbl = _t(lang, "wolne", "free")
                    lines.append(f"    {p.device}  {total_gb} GB  /  {free_gb} GB {free_lbl}")
                except Exception:
                    pass
                if len(lines) > 12:
                    break
        except Exception:
            summary = hw.get("storage_summary")
            if summary:
                for part in summary.split(" | "):
                    lines.append(f"    {part.strip()}")

        # ── Motherboard ───────────────────────────────────────────────────────
        if hw.get("motherboard_model"):
            lines.append("  ◈ " + _t(lang, "Płyta główna", "Motherboard"))
            lines.append(f"    {hw['motherboard_model']}")

        # ── OS ────────────────────────────────────────────────────────────────
        if hw.get("os_version"):
            lines.append(f"  ◈ OS  {hw['os_version']}")

        lines.append(_followup("hw", lang))
        return lines

    def _resp_hw_cpu(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        from hck_gpt.context.system_context import system_context
        from hck_gpt.memory.session_memory  import session_memory
        hw       = user_knowledge.get_all_hardware()
        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()

        model   = (hw.get("cpu_model") or self._live_cpu_model()
                   or _t(lang, "nieznany model", "unknown model"))
        cores_p = hw.get("cpu_cores",     snap.get("cpu_cores_physical", "?"))
        cores_l = hw.get("cpu_threads",   snap.get("cpu_cores_logical",  "?"))
        boost   = hw.get("cpu_boost_ghz", "?")
        cur_mhz = snap.get("cpu_mhz",  "-")
        cur_pct = snap.get("cpu_pct",  "-")
        throttle = ""
        if snap.get("cpu_throttled"):
            throttle = _t(lang, "  ⚠ throttled!", "  ⚠ throttling!")

        # ── delta on current usage ─────────────────────────────────
        try:
            cur_f = float(str(cur_pct).replace("%", "") or 0)
        except (ValueError, TypeError):
            cur_f = 0.0
        delta = _delta_label(cur_f, patterns.get("typical_cpu_avg"), lang)
        delta_sfx = f"    {delta}" if delta else ""

        # ── record for later cross-response references ──────────────
        session_memory.record_response_data("hw_cpu", {
            "model":       str(model),
            "cores":       cores_p,
            "current_pct": cur_pct,
        })

        if lang == "en":
            return [
                f"{self.PREFIX} Processor:",
                f"  Model:    {model}",
                f"  Cores:    {cores_p} physical  /  {cores_l} logical",
                f"  Boost:    {boost} GHz",
                f"  Now:      {cur_mhz} MHz  |  {cur_pct}% usage{throttle}{delta_sfx}",
                _followup("hw", lang),
            ]
        return [
            f"{self.PREFIX} Procesor:",
            f"  Model:    {model}",
            f"  Rdzenie:  {cores_p} fizyczne  /  {cores_l} logiczne",
            f"  Boost:    {boost} GHz",
            f"  Teraz:    {cur_mhz} MHz  |  {cur_pct}% użycia{throttle}{delta_sfx}",
            _followup("hw", lang),
        ]

    def _resp_hw_gpu(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        hw    = user_knowledge.get_all_hardware()
        model = hw.get("gpu_model", None)
        vram  = hw.get("gpu_vram_gb", None)

        if not model:
            return [_t(lang,
                       f"{self.PREFIX} Nie mam jeszcze danych o karcie graficznej.",
                       f"{self.PREFIX} No GPU data yet - hardware scan is running.")]

        # ── record for cross-response references ───────────────────
        from hck_gpt.memory.session_memory import session_memory
        session_memory.record_response_data("hw_gpu", {
            "model":   str(model),
            "vram_gb": vram,
        })

        vram_str = f"\n  VRAM:  {vram} GB" if vram else ""
        header = _t(lang,
                    f"{self.PREFIX} Karta graficzna:",
                    f"{self.PREFIX} Graphics card:")
        return [header, f"  Model:{vram_str}  {model}", _followup("hw", lang)]

    def _resp_hw_ram(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        from hck_gpt.context.system_context import system_context
        hw       = user_knowledge.get_all_hardware()
        snap     = system_context.snapshot()
        patterns = user_knowledge.get_all_patterns()

        total   = hw.get("ram_total_gb", snap.get("ram_total_gb", "?"))
        speed   = hw.get("ram_speed_mhz")
        model   = hw.get("ram_model")       # WMI part number, e.g. "CMK16GX4M2B3200C16"
        pct     = snap.get("ram_pct",    "-")
        used    = snap.get("ram_used_gb", "-")
        free    = snap.get("ram_free_gb", "-")
        typ_avg = patterns.get("typical_ram_avg")  # 7-day average from usage_patterns

        spd_str   = f"  ·  {speed} MHz" if speed else ""
        model_str = f"  ({model})" if model else ""

        # Determine if RAM pressure is elevated
        try:
            pct_f = float(str(pct).replace("%", ""))
        except Exception:
            pct_f = 0.0
        avg_f = float(typ_avg) if typ_avg else 0.0
        high_pressure = pct_f > 75 or avg_f > 70

        # ── record for cross-response references ───────────────────
        from hck_gpt.memory.session_memory import session_memory
        session_memory.record_response_data("hw_ram", {
            "total_gb":    total,
            "speed":       speed,
            "model":       model,
            "current_pct": pct,
            "typical_avg": typ_avg,
        })

        if lang == "en":
            lines = [
                f"{self.PREFIX} RAM:",
                f"  Model:    {total} GB{spd_str}{model_str}",
                f"  Now:      {used} GB used  ({pct}%)  /  {free} GB free",
            ]
            if typ_avg:
                lines.append(f"  Avg use:  {typ_avg}%  (7-day typical activity)")
            if high_pressure:
                lines.append("  💡 Reduce background services and apps:")
                lines.append("     [-> Optimization]  or expand Virtual Memory  [-> Virtual Memory]")
            else:
                lines.append("  💬 Manage background apps  [-> Optimization]")
        else:
            lines = [
                f"{self.PREFIX} Pamięć RAM:",
                f"  Model:    {total} GB{spd_str}{model_str}",
                f"  Teraz:    {used} GB użyte  ({pct}%)  /  {free} GB wolne",
            ]
            if typ_avg:
                lines.append(f"  Śr. użycie:  {typ_avg}%  (typowa aktywność - 7 dni)")
            if high_pressure:
                lines.append("  💡 Rozważ zmniejszenie usług i aplikacji w tle:")
                lines.append("     [-> Optimization]  lub dodaj Pamięć Wirtualną  [-> Virtual Memory]")
            else:
                lines.append("  💬 Zarządzaj aplikacjami w tle  [-> Optimization]")
        return lines

    def _resp_hw_motherboard(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        hw   = user_knowledge.get_all_hardware()
        mobo = hw.get("motherboard_model", None)

        if mobo:
            header = _t(lang, f"{self.PREFIX} Płyta główna:", f"{self.PREFIX} Motherboard:")
            return [f"{header}  {mobo}"]
        if lang == "en":
            return [
                f"{self.PREFIX} No motherboard model found yet.",
                "  Try: Start -> System Information -> Components -> Baseboard",
            ]
        return [
            f"{self.PREFIX} Nie mam jeszcze modelu płyty głównej.",
            "  Spróbuj: Start -> Informacje o systemie -> Składniki -> Karta główna",
        ]

    def _resp_hw_storage(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.memory.user_knowledge import user_knowledge
        hw         = user_knowledge.get_all_hardware()
        disk_model = hw.get("disk_model")   # WMI Win32_DiskDrive model name

        lines = [_t(lang, f"{self.PREFIX} Twój dysk:", f"{self.PREFIX} Your disk:")]

        # Lead with the physical disk model if we have it
        if disk_model:
            lines.append(f"  Model:   {disk_model}")

        # Per-partition capacity + free space (live)
        try:
            import psutil
            partition_count = 0
            for p in psutil.disk_partitions(all=False):
                if "remote" in (p.opts or "").lower():
                    continue
                try:
                    u        = psutil.disk_usage(p.mountpoint)
                    total_gb = round(u.total / 1_073_741_824, 1)
                    free_gb  = round(u.free  / 1_073_741_824, 1)
                    free_lbl = _t(lang, "wolne", "free")
                    warn     = "  ⚠ " + _t(lang, "prawie pełny!", "almost full!") \
                               if u.percent > 85 else ""
                    lines.append(
                        f"  {p.device}  {total_gb} GB"
                        f"  /  {free_gb} GB {free_lbl}  ({u.percent:.0f}%){warn}"
                    )
                    partition_count += 1
                except Exception:
                    pass
                if partition_count >= 5:   # cap
                    break
        except Exception:
            # Fallback: stored psutil summary
            summary = hw.get("storage_summary")
            if summary:
                for part in summary.split(" | "):
                    lines.append(f"  {part.strip()}")

        if len(lines) == 1:
            # Nothing added - scanner hasn't run yet
            lines.append(_t(lang,
                            "  Brak danych - skan sprzętu trwa lub nie powiódł się.",
                            "  No data yet - hardware scan still running."))

        lines.append(_followup("hw", lang))
        return lines

    def _resp_throttle_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        snap = system_context.snapshot()
        mhz      = snap.get("cpu_mhz",     None)
        max_mhz  = snap.get("cpu_max_mhz", None)
        throttled = snap.get("cpu_throttled", False)

        if mhz is None:
            return [_t(lang,
                       f"{self.PREFIX} Brak danych o taktowaniu CPU.",
                       f"{self.PREFIX} No CPU frequency data available.")]

        ratio_str = ""
        if max_mhz:
            ratio = mhz / max_mhz
            ratio_str = _t(lang, f"  ({ratio*100:.0f}% mocy)", f"  ({ratio*100:.0f}% of max)")

        if throttled:
            if lang == "en":
                return [
                    f"{self.PREFIX} ⚠ CPU IS THROTTLING!",
                    f"  Now:    {mhz} MHz{ratio_str}",
                    f"  Max:    {max_mhz} MHz",
                    "  Likely cause: heat, power limit, or power plan.",
                    "  Check temperatures and active power plan.",
                ]
            return [
                f"{self.PREFIX} ⚠ CPU THROTTLUJE!",
                f"  Teraz:  {mhz} MHz{ratio_str}",
                f"  Max:    {max_mhz} MHz",
                "  Możliwe przyczyny: przegrzanie, power limit, plan zasilania.",
                "  Sprawdź temperatury i plan zasilania.",
            ]

        ok_msg = _t(lang,
                    f"{self.PREFIX} CPU nie throttluje.",
                    f"{self.PREFIX} CPU is not throttling.")
        return [ok_msg,
                f"  {_t(lang, 'Teraz', 'Now')}: {mhz} MHz  /  Max: {max_mhz} MHz  {ratio_str}",
                _followup("perf", lang)]

    def _resp_power_plan(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import subprocess
            result = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True, text=True, errors="replace", timeout=3
            )
            line = result.stdout.strip()
            if "(" in line:
                name = line[line.rfind("(") + 1:line.rfind(")")]
                label = _t(lang, "Aktywny plan zasilania", "Active power plan")
                return [f"{self.PREFIX} {label}:  {name}"]
        except Exception:
            pass
        return [_t(lang,
                   f"{self.PREFIX} Nie mogę odczytać planu zasilania.",
                   f"{self.PREFIX} Can't read power plan.")]

    def _resp_upgrade_advice(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """Detects the real bottleneck from the user's own load/temperature history
        (CPU vs GPU headroom, RAM pressure, cooling) - no generic guessing."""
        P = self.PREFIX
        try:
            from hck_gpt.context.system_context import system_context
            snap = system_context.snapshot()
        except Exception:
            snap = {}
        try:
            from hck_stats_engine.query_api import query_api
            summ  = query_api.get_summary_stats(days=14) or {}
            temps = query_api.get_temperature_summary(days=14) or {}
        except Exception:
            summ, temps = {}, {}
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            hw = user_knowledge.get_all_hardware() or {}
        except Exception:
            hw = {}

        # Not enough history yet -> set expectations, don't bluff
        if not summ or float(summ.get("cpu_avg") or 0) <= 0:
            return [
                _t(lang, f"{P} Jeszcze zbieram dane o Twoim obciążeniu.",
                         f"{P} I'm still learning how you load this PC."),
                _t(lang, "  Daj mi popracować dzień-dwa w tle, a powiem konkretnie,",
                         "  Give me a day or two in the background and I'll tell you"),
                _t(lang, "  który podzespół jest wąskim gardłem - bez zgadywania. 📊",
                         "  exactly which part is the bottleneck - no guessing. 📊"),
            ]

        cpu_avg = float(summ.get("cpu_avg") or 0)
        cpu_max = float(summ.get("cpu_max") or 0)
        gpu_avg = float(summ.get("gpu_avg") or 0)
        gpu_max = float(summ.get("gpu_max") or 0)
        ram_avg = float(summ.get("ram_avg") or 0)
        ram_max = float(summ.get("ram_max") or 0)
        days    = int(summ.get("days_with_data") or 1)
        ct_avg  = temps.get("cpu_temp_avg")
        ct_max  = temps.get("cpu_temp_max")
        throttled = bool(snap.get("cpu_throttled"))

        has_gpu   = (gpu_avg > 0 or gpu_max > 0)
        cpu_model = hw.get("cpu_model") or "CPU"
        gpu_model = hw.get("gpu_model") or "GPU"
        ram_gb    = hw.get("ram_total_gb")

        cpu_loaded   = cpu_avg >= 70 or cpu_max >= 99
        cpu_heavy    = cpu_avg >= 80
        cpu_headroom = cpu_avg < 50
        gpu_loaded   = has_gpu and (gpu_avg >= 70 or gpu_max >= 99)
        gpu_headroom = has_gpu and gpu_avg < 55
        ram_pressure = ram_avg >= 80 or ram_max >= 97
        cpu_hot      = bool((ct_avg and ct_avg > 75) or (ct_max and ct_max > 92) or throttled)

        d_lbl = _t(lang, "dni", "days")
        lines = [_t(lang,
            f"{P} Co warto wymienić? Patrzę na Twoje {days} {d_lbl} użytkowania:",
            f"{P} What's worth upgrading? Reading your last {days} {d_lbl} of use:")]
        ev = (f"  CPU śr. {cpu_avg:.0f}% (szczyt {cpu_max:.0f}%)" if lang == "pl"
              else f"  CPU avg {cpu_avg:.0f}% (peak {cpu_max:.0f}%)")
        if has_gpu:
            ev += _t(lang, f"  ·  GPU śr. {gpu_avg:.0f}%", f"  ·  GPU avg {gpu_avg:.0f}%")
        ev += _t(lang, f"  ·  RAM śr. {ram_avg:.0f}%", f"  ·  RAM avg {ram_avg:.0f}%")
        if ct_avg:
            ev += f"  ·  CPU {ct_avg:.0f}°C"
        lines.append(ev)
        lines.append("")

        if cpu_loaded and gpu_headroom:
            lines.append(_t(lang,
                f"  ▸ Procesor jest wąskim gardłem. {cpu_model} często pracuje na maksa,",
                f"  ▸ Your CPU is the bottleneck. {cpu_model} runs near its limit,"))
            lines.append(_t(lang,
                f"    a {gpu_model} ma sporo wolnej mocy ({gpu_avg:.0f}%). Mocniejszy CPU",
                f"    while {gpu_model} sits with spare power ({gpu_avg:.0f}%). A stronger CPU"))
            lines.append(_t(lang,
                "    dałby tu największy skok wydajności.",
                "    would give you the biggest jump here."))
        elif gpu_loaded and cpu_headroom:
            lines.append(_t(lang,
                f"  ▸ Karta graficzna jest wąskim gardłem. {gpu_model} pracuje na maksa",
                f"  ▸ Your GPU is the bottleneck. {gpu_model} runs flat out"))
            lines.append(_t(lang,
                f"    (śr. {gpu_avg:.0f}%), a CPU ma zapas ({cpu_avg:.0f}%). Nowsza karta",
                f"    (avg {gpu_avg:.0f}%) while the CPU has headroom ({cpu_avg:.0f}%). A newer GPU"))
            lines.append(_t(lang,
                "    da najwięcej, zwłaszcza w grach i renderowaniu.",
                "    helps most, especially in games and rendering."))
        elif ram_pressure:
            cur    = f" (masz {ram_gb:.0f} GB)" if ram_gb else ""
            cur_en = f" (you have {ram_gb:.0f} GB)" if ram_gb else ""
            lines.append(_t(lang,
                f"  ▸ RAM się dusi - średnio {ram_avg:.0f}%, szczyty {ram_max:.0f}%{cur}.",
                f"  ▸ RAM is under pressure - avg {ram_avg:.0f}%, peaks {ram_max:.0f}%{cur_en}."))
            lines.append(_t(lang,
                "    Dołożenie pamięci to najtańszy i najpewniejszy zysk płynności.",
                "    Adding memory is the cheapest, surest win for smoothness."))
        elif cpu_loaded and gpu_loaded:
            lines.append(_t(lang,
                "  ▸ I CPU, i GPU pracują mocno - ładnie zbalansowany zestaw.",
                "  ▸ Both CPU and GPU work hard - a nicely balanced rig."))
            lines.append(_t(lang,
                "    Wymiana opłaca się dopiero, gdy konkretna gra/program zwalnia.",
                "    An upgrade only pays off once a specific game/app feels slow."))
        else:
            extra    = f", GPU {gpu_avg:.0f}%" if has_gpu else ""
            lines.append(_t(lang,
                "  ▸ Nie widzę potrzeby wymiany. Wszystko ma zapas mocy -",
                "  ▸ No upgrade needed. Everything has headroom -"))
            lines.append(_t(lang,
                f"    CPU {cpu_avg:.0f}%, RAM {ram_avg:.0f}%{extra}. Sprzęt nadąża za Tobą.",
                f"    CPU {cpu_avg:.0f}%, RAM {ram_avg:.0f}%{extra}. The hardware keeps up with you."))

        if cpu_hot and not cpu_heavy:
            t_show = ct_max or ct_avg
            lines.append("")
            if t_show:
                lines.append(_t(lang,
                    f"  🌡 Uwaga: CPU bywa gorący ({t_show:.0f}°C) przy umiarkowanym obciążeniu -",
                    f"  🌡 Note: CPU runs hot ({t_show:.0f}°C) at moderate load -"))
            else:
                lines.append(_t(lang,
                    "  🌡 Uwaga: CPU throttluje przy umiarkowanym obciążeniu -",
                    "  🌡 Note: CPU throttles at moderate load -"))
            lines.append(_t(lang,
                "    zanim wymienisz, sprawdź chłodzenie/pastę. To dużo tańsze.",
                "    before replacing it, check cooling/paste. Far cheaper."))

        lines.append("")
        lines.append(_t(lang,
            "  💬 Chcesz pełny obraz? Napisz 'zdrowie' albo 'temperatura'.",
            "  💬 Want the full picture? Try 'health' or 'temperature'."))
        return lines

    def _resp_disk_speed(self, r: ParseResult, lang: str = "pl") -> List[str]:
        import os, tempfile
        lines = [_t(lang, f"{self.PREFIX} Stan dysków:", f"{self.PREFIX} Disk status:")]

        # Live disk usage
        try:
            import psutil
            for p in psutil.disk_partitions(all=False):
                if "remote" in (p.opts or "").lower():
                    continue
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    free_gb  = round(u.free  / 1_073_741_824, 1)
                    total_gb = round(u.total / 1_073_741_824, 1)
                    used_pct = u.percent
                    status = "⚠ " if used_pct > 85 else ("! " if used_pct > 70 else "  ")
                    lines.append(f"  {status}{p.device}  {used_pct:.0f}% used"
                                 f"  ({free_gb} GB free / {total_gb} GB)")
                except Exception:
                    pass
        except Exception:
            pass

        # TEMP folder
        try:
            td = tempfile.gettempdir()
            temp_mb = sum(
                e.stat().st_size for e in os.scandir(td) if e.is_file(follow_symlinks=False)
            ) // 1_048_576
            if temp_mb > 100:
                lines.append(_t(lang,
                    f"  🗑 Folder TEMP: {temp_mb} MB  ->  wyczyść w zakładce Optimization",
                    f"  🗑 TEMP folder: {temp_mb} MB  ->  clear in Optimization tab"))
        except Exception:
            pass

        # AppData check
        try:
            appdata = os.environ.get('APPDATA', '')
            if appdata and os.path.exists(appdata):
                app_dirs = [d.name for d in os.scandir(appdata) if d.is_dir()]
                count = len(app_dirs)
                if count > 50:
                    lines.append(_t(lang,
                        f"  📁 AppData: {count} folderów - mogą być resztki starych aplikacji.",
                        f"  📁 AppData: {count} folders - may contain leftovers from old apps."))
                    lines.append(_t(lang,
                        "     Wpisz '%appdata%' w Wyszukaj -> przejrzyj i usuń foldery",
                        "     Type '%appdata%' in Windows Search -> review and delete old folders"))
        except Exception:
            pass

        lines.append(_t(lang,
            "  💡 Wskazówka: Optymalizacja -> Wyczyść TEMP -> Uruchom TURBO BOOST",
            "  💡 Tip: Optimization -> Clear TEMP -> Run TURBO BOOST"))
        return lines

    def _resp_disk_health(self, r: ParseResult, lang: str = "pl") -> List[str]:
        lines = [_t(lang, f"{self.PREFIX} Zdrowie dysków:", f"{self.PREFIX} Disk health:")]
        try:
            import psutil
            SAFE_FSTYPES = {"ntfs", "fat32", "exfat", "refs"}
            partitions = [
                p for p in psutil.disk_partitions(all=False)
                if "remote" not in (p.opts or "").lower()
                and p.fstype and p.fstype.lower() in SAFE_FSTYPES
            ]
            for p in partitions[:4]:
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    used_pct = u.percent
                    free_gb  = round(u.free  / 1_073_741_824, 1)
                    total_gb = round(u.total / 1_073_741_824, 1)
                    if used_pct > 90:
                        icon = "⚠"
                        status = _t(lang, "PEŁNY - zwolnij miejsce!", "FULL - free up space!")
                    elif used_pct > 75:
                        icon = "!"
                        status = _t(lang, f"{used_pct:.0f}% zajęte", f"{used_pct:.0f}% used")
                    else:
                        icon = "✓"
                        status = _t(lang, f"{used_pct:.0f}% zajęte", f"{used_pct:.0f}% used")
                    lines.append(f"  {icon} {p.device}  {total_gb} GB  -  {free_gb} GB {_t(lang, 'wolne', 'free')}  ({status})")
                except Exception:
                    pass
        except Exception:
            pass

        # S.M.A.R.T. note
        lines.append(_t(lang,
            "  ℹ S.M.A.R.T. monitoring: sprawdź CrystalDiskInfo dla pełnej diagnozy dysku.",
            "  ℹ S.M.A.R.T. check: use CrystalDiskInfo for full drive health diagnostics."))
        lines.append(_followup("disk", lang))
        return lines

    def _resp_disk_usage_why(self, r: ParseResult, lang: str = "pl") -> List[str]:
        lines = [_t(lang,
                    f"{self.PREFIX} Analiza aktywności dysku:",
                    f"{self.PREFIX} Disk activity analysis:")]
        try:
            import psutil

            # Overall disk I/O
            io = psutil.disk_io_counters(perdisk=False)
            if io:
                read_mb  = round(io.read_bytes  / 1_048_576)
                write_mb = round(io.write_bytes / 1_048_576)
                lines.append(_t(lang,
                                f"  Odczyt total:  {read_mb} MB   Zapis total: {write_mb} MB",
                                f"  Total read:    {read_mb} MB   Total write: {write_mb} MB"))

            # Top disk I/O processes
            io_procs: list[tuple[str, int]] = []
            for p in psutil.process_iter(["name", "io_counters"]):
                try:
                    ioc = p.info.get("io_counters")
                    if ioc:
                        total_bytes = getattr(ioc, "read_bytes", 0) + getattr(ioc, "write_bytes", 0)
                        if total_bytes > 0:
                            io_procs.append((p.info["name"] or "?", total_bytes))
                except Exception:
                    continue
            io_procs.sort(key=lambda x: x[1], reverse=True)

            if io_procs:
                lines.append(_t(lang, "  Procesy z najwyższym I/O:", "  Processes with highest I/O:"))
                for name, total in io_procs[:5]:
                    mb = round(total / 1_048_576)
                    lines.append(f"    - {name[:30]:<30}  {mb} MB")
            else:
                lines.append(_t(lang,
                                "  Brak danych per-proces - Windows może ograniczać dostęp.",
                                "  No per-process data - Windows may restrict I/O access."))

            # Disk fill level check
            for part in psutil.disk_partitions(all=False):
                if "remote" in (part.opts or "").lower():
                    continue
                try:
                    u = psutil.disk_usage(part.mountpoint)
                    if u.percent > 85:
                        free = round(u.free / 1_073_741_824, 1)
                        lines.append(_t(lang,
                                        f"  ⚠ {part.device} prawie pełny - {u.percent:.0f}% ({free} GB wolne)",
                                        f"  ⚠ {part.device} almost full - {u.percent:.0f}% ({free} GB free)"))
                except Exception:
                    pass

        except Exception:
            lines.append(_t(lang, "  Brak dostępu do danych dysku.", "  No disk data access."))

        lines.append(_t(lang,
                        "  Typowe przyczyny: Windows Update, antywirus, indeksowanie.",
                        "  Common causes: Windows Update, antivirus, search indexing."))
        lines.append(_followup("disk", lang))
        return lines

    def _resp_battery_drain(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            import psutil
            bat = psutil.sensors_battery()
        except Exception:
            bat = None

        lines: list[str] = []

        if bat is None:
            lines.append(_t(lang,
                            f"{self.PREFIX} Brak baterii (PC stacjonarny).",
                            f"{self.PREFIX} No battery detected (desktop PC)."))
            lines.append(_t(lang,
                            "  Top pożeracze prądu = procesy z wysokim CPU:",
                            "  Top power consumers = high CPU processes:"))
        else:
            plugged = bat.power_plugged
            pct = bat.percent
            secs = bat.secsleft
            time_str = ""
            if secs and secs > 0:
                h, m = divmod(secs // 60, 60)
                time_str = f"  ~{h}h {m}min left" if lang == "en" else f"  ~{h}h {m}min zostało"
            status = _t(lang,
                        "ładowanie" if plugged else "na baterii",
                        "charging"  if plugged else "on battery")
            lines.append(_t(lang,
                            f"{self.PREFIX} Bateria: {pct:.0f}%  [{status}]{time_str}",
                            f"{self.PREFIX} Battery: {pct:.0f}%  [{status}]{time_str}"))
            lines.append(_t(lang,
                            "  Procesy najbardziej drenujące baterię (CPU = prąd):",
                            "  Processes draining battery most (CPU = power):"))

        try:
            import psutil
            raw = []
            for p in psutil.process_iter(["name", "cpu_percent"]):
                try:
                    raw.append(p)
                    if len(raw) >= 64:
                        break
                except Exception:
                    continue
            top = sorted(raw, key=lambda p: p.info.get("cpu_percent", 0) or 0, reverse=True)[:5]
            for i, p in enumerate(top, 1):
                nm = (p.info.get("name") or "?")[:28]
                c  = p.info.get("cpu_percent", 0) or 0
                if c > 0.1:
                    lines.append(f"  {i}. {nm:<28}  {c:.1f}% CPU")
        except Exception:
            pass

        lines.append(_t(lang,
                        "  💡 Plan zasilania Balanced = lepsza bateria niż High Performance.",
                        "  💡 Balanced power plan saves more battery than High Performance."))
        lines.append(_followup("process", lang))
        return lines

    def _resp_usb_transfer(self, r: ParseResult, lang: str = "pl") -> List[str]:
        P = self.PREFIX
        try:
            import psutil
            io1 = psutil.disk_io_counters(perdisk=True)
            import time as _t
            _t.sleep(0.5)
            io2 = psutil.disk_io_counters(perdisk=True)

            transfer_info: list = []
            for disk_name in io2:
                a = io1.get(disk_name)
                b = io2.get(disk_name)
                if not a or not b:
                    continue
                r_mb = (b.read_bytes  - a.read_bytes)  / 1_048_576 / 0.5
                w_mb = (b.write_bytes - a.write_bytes) / 1_048_576 / 0.5
                if r_mb + w_mb > 0.5:    # only show active disks
                    transfer_info.append((disk_name, r_mb, w_mb))
            transfer_info.sort(key=lambda x: -(x[1] + x[2]))

            # CPU during transfer window
            cpu_load = psutil.cpu_percent(interval=None)

        except Exception:
            transfer_info = []
            cpu_load = -1.0

        # Live sensors for context
        try:
            from hck_gpt.data.live_sensors import snapshot as _ls_snap
            ls = _ls_snap()
            cpu_load = ls.get("cpu_load", cpu_load)
        except Exception:
            pass

        if lang == "en":
            lines = [f"{P} External / USB transfer - live I/O snapshot:"]
            if not transfer_info:
                lines.append("  No active disk I/O detected at the moment.")
                lines.append("  If your transfer just started, ask me again in a few seconds.")
            else:
                for dname, r_mb, w_mb in transfer_info[:4]:
                    arrow = f"R: {r_mb:.1f} MB/s" if r_mb > w_mb else f"W: {w_mb:.1f} MB/s"
                    lines.append(f"  {dname:<12}  {arrow}  (R {r_mb:.1f} + W {w_mb:.1f} MB/s)")
            if cpu_load >= 0:
                cpu_note = "minimal" if cpu_load < 15 else "moderate" if cpu_load < 40 else "high"
                lines.append(f"  CPU during transfer: {cpu_load:.0f}%  - {cpu_note} overhead.")
                if cpu_load < 15:
                    lines.append("  File transfers are very CPU-light on SSDs - storage controller handles it.")
                elif cpu_load > 50:
                    lines.append("  High CPU during transfer can happen with encryption, compression, or virus scanning.")
            lines.append("  Tip: Transfer speed depends on USB version - USB 3.x is ~400 MB/s, USB 2.0 ~40 MB/s.")
        else:
            lines = [f"{P} Transfer zewnętrzny / USB - szybki odczyt I/O:"]
            if not transfer_info:
                lines.append("  Nie wykryto aktywnego transferu w tej chwili.")
                lines.append("  Jeśli transfer właśnie się zaczął, zapytaj ponownie za chwilę.")
            else:
                for dname, r_mb, w_mb in transfer_info[:4]:
                    arrow = f"R: {r_mb:.1f} MB/s" if r_mb > w_mb else f"Z: {w_mb:.1f} MB/s"
                    lines.append(f"  {dname:<12}  {arrow}  (R {r_mb:.1f} + Z {w_mb:.1f} MB/s)")
            if cpu_load >= 0:
                cpu_note = "minimalny" if cpu_load < 15 else "umiarkowany" if cpu_load < 40 else "wysoki"
                lines.append(f"  CPU podczas transferu: {cpu_load:.0f}%  - obciążenie {cpu_note}.")
                if cpu_load < 15:
                    lines.append("  Transfer plików to małe obciążenie CPU dla SSD - kontroler pamięci robi robotę.")
                elif cpu_load > 50:
                    lines.append("  Wysokie CPU podczas transferu może być efektem szyfrowania, kompresji lub antywirusa.")
            lines.append("  Tip: Prędkość zależy od USB - USB 3.x ~400 MB/s, USB 2.0 ~40 MB/s.")
        lines.append(_followup("perf", lang))
        return lines

    def _resp_battery_drain_rate(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """Enhanced battery response - shows drain rate estimate during gaming vs idle."""
        try:
            import psutil
            bat = psutil.sensors_battery()
        except Exception:
            bat = None

        lines = [_t(lang,
            f"{self.PREFIX} Zużycie baterii:",
            f"{self.PREFIX} Battery drain:")]

        if bat is None:
            lines.append(_t(lang,
                "  Brak baterii (komputer stacjonarny lub brak czujnika).",
                "  No battery (desktop PC or no sensor available)."))
            lines.append(_t(lang,
                "  Pytanie o 'pobór prądu' jest bardziej odpowiednie dla laptopów.",
                "  'Power consumption' question is more relevant for laptops."))
        else:
            pct     = bat.percent
            plugged = bat.power_plugged
            secs    = bat.secsleft
            time_str = ""
            if secs and secs > 0 and not plugged:
                h, m = divmod(secs // 60, 60)
                time_str = (f"  ~{h}h {m}min pozostało" if lang == "pl"
                            else f"  ~{h}h {m}min remaining")
            status = _t(lang,
                "ładowanie" if plugged else "na baterii",
                "charging"  if plugged else "on battery")
            lines.append(f"  {pct:.0f}%  [{status}]{time_str}")

        # Current CPU load as proxy for power draw
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            lines.append("")
            lines.append(_t(lang,
                f"  CPU teraz: {cpu:.0f}%  RAM: {ram:.0f}%  - to główne czynniki poboru prądu",
                f"  CPU now: {cpu:.0f}%  RAM: {ram:.0f}%  - main factors in power draw"))

            if cpu > 70:
                lines.append(_t(lang,
                    "  🔴 Wysokie CPU = wysoki pobór - bateria rozładowuje się szybko",
                    "  🔴 High CPU = high draw - battery draining fast"))
            elif cpu > 40:
                lines.append(_t(lang,
                    "  🟡 Umiarkowane CPU - bateria rozładowuje się w normalnym tempie",
                    "  🟡 Moderate CPU - battery draining at normal pace"))
            else:
                lines.append(_t(lang,
                    "  ✓ Niskie CPU - wolne rozładowywanie baterii",
                    "  ✓ Low CPU - slow battery drain"))
        except Exception:
            pass

        lines.append("")
        lines.append(_t(lang,
            "  Szacowane zużycie baterii:",
            "  Estimated battery usage:"))
        lines.append(_t(lang,
            "  • Gaming:     ~20–35 % / godz  (GPU + CPU pod pełnym ładunkiem)",
            "  • Gaming:     ~20–35% / hour   (GPU + CPU under full load)"))
        lines.append(_t(lang,
            "  • Praca:      ~8–15 % / godz   (przeglądarka, dokumenty)",
            "  • Work:       ~8–15% / hour    (browser, documents)"))
        lines.append(_t(lang,
            "  • Jałowy:     ~3–6 % / godz    (bezczynność, ekran wygaszony)",
            "  • Idle:       ~3–6% / hour     (idle, screen off)"))
        lines.append(_t(lang,
            "  💡 Plan zasilania Balanced = lepsza bateria niż High Performance",
            "  💡 Balanced power plan saves more battery than High Performance"))
        return lines

    def _resp_power_after_restart(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Shows which processes have used the most CPU since session start,
        as a proxy for 'who used the most power since restart'.
        """
        from hck_gpt.memory.session_memory import session_memory

        session_dur = session_memory.session_duration_str()

        lines = [_t(lang,
            f"{self.PREFIX} Zużycie prądu od startu systemu (szacowane przez CPU):",
            f"{self.PREFIX} Power usage since restart (estimated via CPU):")]
        lines.append(_t(lang,
            f"  Czas sesji PC Workman: {session_dur}",
            f"  PC Workman session time: {session_dur}"))
        lines.append("")

        try:
            import psutil
            # cumulative CPU times since boot (more accurate for power history)
            procs_cpu: list[tuple[str, float]] = []
            for proc in psutil.process_iter(["name", "cpu_times"]):
                try:
                    ct = proc.info.get("cpu_times")
                    if ct:
                        total_s = getattr(ct, "user", 0) + getattr(ct, "system", 0)
                        if total_s > 1:
                            procs_cpu.append((proc.info["name"] or "?", total_s))
                except Exception:
                    continue
            procs_cpu.sort(key=lambda x: x[1], reverse=True)

            if procs_cpu:
                lines.append(_t(lang,
                    "  Procesy z największym łącznym czasem CPU od uruchomienia:",
                    "  Processes with most cumulative CPU time since boot:"))
                for name, secs in procs_cpu[:7]:
                    mins = secs / 60
                    lines.append(f"  - {name[:30]:<30}  {mins:.0f} min CPU time")
            else:
                lines.append(_t(lang,
                    "  Brak danych o CPU times - prawdopodobnie brak uprawnień.",
                    "  No CPU times data - likely insufficient permissions."))
        except Exception:
            lines.append(_t(lang,
                "  Nie mogę pobrać danych o procesach.",
                "  Cannot retrieve process data."))

        lines.append("")
        lines.append(_t(lang,
            "  💡 Więcej czasu CPU = więcej prądu zużytego.",
            "  💡 More CPU time = more power consumed."))
        lines.append(_t(lang,
            "  Dla dokładniejszego pomiaru (laptopy): Start -> powercfg /batteryreport",
            "  For more precise measurement (laptops): Start -> powercfg /batteryreport"))
        lines.append(_followup("process", lang))
        return lines

    def _resp_gaming_ram_usage(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Shows RAM usage specifically during gaming sessions:
        - Current RAM if a game is running
        - Session peak RAM (from session_memory)
        - 7-day average RAM during high-GPU-load periods (metrics_store)
        """
        from hck_gpt.memory.session_memory import session_memory

        lines = [_t(lang,
            f"{self.PREFIX} Zużycie RAM podczas grania:",
            f"{self.PREFIX} RAM usage during gaming:")]

        # Current RAM snapshot
        try:
            import psutil
            vm = psutil.virtual_memory()
            ram_used  = vm.used  / (1024 ** 3)
            ram_total = vm.total / (1024 ** 3)
            ram_pct   = vm.percent

            # Check if a game process is currently running
            game_slugs = {
                "cs2", "csgo", "valorant", "fortnite", "minecraft",
                "epicgameslauncher", "steam", "leagueoflegends",
                "dota2", "rocketleague", "cyberpunk2077", "witcher3",
                "eldenring", "r5apex", "cod", "warzone2", "overwatch",
                "destiny2", "battlefield", "hogwartslauncher",
            }
            game_running = []
            game_ram_mb  = 0
            for proc in psutil.process_iter(["name", "memory_info"]):
                try:
                    pname = (proc.info.get("name") or "").lower().replace(".exe", "").replace("_", "").replace("-", "").replace(" ", "")
                    if any(slug in pname for slug in game_slugs):
                        mem = proc.info.get("memory_info")
                        if mem:
                            mb = (mem.rss or 0) / (1024 ** 2)
                            game_running.append((proc.info["name"], mb))
                            game_ram_mb += mb
                except Exception:
                    continue

            if game_running:
                lines.append(_t(lang,
                    f"  🎮 Aktywna gra wykryta - RAM teraz: {ram_used:.1f} GB / {ram_total:.0f} GB ({ram_pct:.0f}%)",
                    f"  🎮 Active game detected - RAM now: {ram_used:.1f} GB / {ram_total:.0f} GB ({ram_pct:.0f}%)"))
                lines.append(_t(lang,
                    f"  Gra zajmuje RAM: ~{game_ram_mb:.0f} MB",
                    f"  Game RAM footprint: ~{game_ram_mb:.0f} MB"))
                for gname, gmb in sorted(game_running, key=lambda x: x[1], reverse=True)[:3]:
                    lines.append(f"    - {gname[:32]:<32}  {gmb:.0f} MB")
            else:
                lines.append(_t(lang,
                    f"  RAM teraz (bez aktywnej gry): {ram_used:.1f} GB / {ram_total:.0f} GB ({ram_pct:.0f}%)",
                    f"  RAM now (no active game): {ram_used:.1f} GB / {ram_total:.0f} GB ({ram_pct:.0f}%)"))
        except Exception:
            lines.append(_t(lang,
                "  Nie mogę odczytać aktualnego RAM.",
                "  Cannot read current RAM."))

        # Historical: session peak from session_memory
        try:
            peak_ram = max(session_memory._ram_trend) if session_memory._ram_trend else None
            if peak_ram:
                lines.append("")
                lines.append(_t(lang,
                    f"  Szczyt RAM tej sesji: {peak_ram:.0f}%",
                    f"  RAM peak this session: {peak_ram:.0f}%"))
        except Exception:
            pass

        # 7-day history - average RAM on gaming days vs non-gaming days
        lines.append("")
        hist = self._get_historical_comparison("ram_pct", 7, lang)
        if hist:
            lines.append(_t(lang,
                "  Historyczne porównanie RAM (7 dni):",
                "  Historical RAM comparison (7 days):"))
            lines.append(hist)
        else:
            lines.append(_t(lang,
                "  Brak 7-dniowej historii RAM - zbiera się z czasem.",
                "  No 7-day RAM history yet - accumulates over time."))

        lines.append("")
        lines.append(_t(lang,
            "  💡 Typowe gry: 4–8 GB RAM. Nowe tytuły AAA mogą wymagać 12–16 GB.",
            "  💡 Typical games: 4–8 GB RAM. New AAA titles may require 12–16 GB."))
        lines.append(_followup("perf", lang))
        return lines

    def _resp_daily_ram_usage(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Shows typical daily RAM usage from 7-day metrics_store history.
        Compares to current usage and installed capacity.
        """
        lines = [_t(lang,
            f"{self.PREFIX} Typowe dzienne zużycie RAM:",
            f"{self.PREFIX} Your typical daily RAM usage:")]

        # Current live value
        try:
            import psutil
            vm = psutil.virtual_memory()
            ram_used_gb  = vm.used  / (1024 ** 3)
            ram_total_gb = vm.total / (1024 ** 3)
            ram_pct      = vm.percent
            lines.append(_t(lang,
                f"  Teraz: {ram_used_gb:.1f} GB / {ram_total_gb:.0f} GB ({ram_pct:.0f}%)",
                f"  Right now: {ram_used_gb:.1f} GB / {ram_total_gb:.0f} GB ({ram_pct:.0f}%)"))
        except Exception:
            ram_total_gb = 0
            lines.append(_t(lang, "  RAM: brak danych na żywo.", "  RAM: no live data."))

        # 7-day history from metrics_store
        try:
            from hck_gpt.data.metrics_store import metrics_store
            summary = metrics_store.daily_summary(days=7)
            if summary:
                valid_avg  = [float(r["ram_avg"]) for r in summary if r.get("ram_avg") and float(r["ram_avg"]) > 0]
                valid_max  = [float(r["ram_max"]) for r in summary if r.get("ram_max") and float(r["ram_max"]) > 0]

                if valid_avg:
                    avg7 = sum(valid_avg) / len(valid_avg)
                    max7 = max(valid_max) if valid_max else None
                    min7 = min(valid_avg)

                    lines.append("")
                    lines.append(_t(lang,
                        f"  Średnia (7 dni):    {avg7:.0f}%",
                        f"  Average (7 days):   {avg7:.0f}%"))
                    if max7:
                        lines.append(_t(lang,
                            f"  Szczyt (7 dni):     {max7:.0f}%",
                            f"  Peak (7 days):      {max7:.0f}%"))
                    lines.append(_t(lang,
                        f"  Minimum (7 dni):    {min7:.0f}%",
                        f"  Minimum (7 days):   {min7:.0f}%"))

                    if ram_total_gb > 0:
                        avg_gb = (avg7 / 100) * ram_total_gb
                        max_gb = (max7 / 100) * ram_total_gb if max7 else None
                        lines.append("")
                        lines.append(_t(lang,
                            f"  W GB: średnio ~{avg_gb:.1f} GB{f'  /  szczyt ~{max_gb:.1f} GB' if max_gb else ''} z {ram_total_gb:.0f} GB",
                            f"  In GB: average ~{avg_gb:.1f} GB{f'  /  peak ~{max_gb:.1f} GB' if max_gb else ''} of {ram_total_gb:.0f} GB"))

                    # Verdict
                    lines.append("")
                    if avg7 > 85:
                        lines.append(_t(lang,
                            "  ⚠ Bardzo wysokie - regularnie brakuje RAM. Rozważ upgrade lub zamknięcie procesów w tle.",
                            "  ⚠ Very high - regularly running low on RAM. Consider upgrading or closing background apps."))
                    elif avg7 > 70:
                        lines.append(_t(lang,
                            "  ! Wysokie - masz mało rezerwy. Przy graniu lub renderze możesz odczuć spowolnienia.",
                            "  ! High - limited headroom. You may notice slowdowns during gaming or rendering."))
                    elif avg7 > 50:
                        lines.append(_t(lang,
                            "  ✓ Umiarkowane - normalne przy aktywnym użytkowaniu.",
                            "  ✓ Moderate - normal for active desktop usage."))
                    else:
                        lines.append(_t(lang,
                            "  ✓ Niskie - masz spory zapas RAM. System oddycha swobodnie.",
                            "  ✓ Low - plenty of RAM headroom. System is comfortable."))
                else:
                    lines.append(_t(lang,
                        "  Brak wystarczającej historii - uruchom PC Workman przez kilka dni.",
                        "  Not enough history yet - run PC Workman for a few days."))
            else:
                lines.append(_t(lang,
                    "  Brak danych historycznych (metrics_store pusty).",
                    "  No historical data (metrics_store is empty)."))
        except Exception:
            lines.append(_t(lang,
                "  Nie można pobrać historii RAM.",
                "  Cannot load RAM history."))

        lines.append(_followup("hw", lang))
        return lines

    def _resp_battery_estimate(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Estimates remaining battery life based on current % and activity type.
        Detects activity from message text (gaming / work / video / idle).
        """
        msg_lower = (r.raw_text or "").lower()

        lines = [_t(lang,
            f"{self.PREFIX} Szacowany czas pracy na baterii:",
            f"{self.PREFIX} Estimated battery life remaining:")]

        # Read current battery state
        try:
            import psutil
            batt = psutil.sensors_battery()
            if batt is None:
                lines.append(_t(lang,
                    "  ⚠ Bateria nie wykryta - to może być komputer stacjonarny lub psutil nie widzi baterii.",
                    "  ⚠ No battery detected - this may be a desktop PC or psutil cannot read battery state."))
                return lines

            pct        = batt.percent
            plugged    = batt.power_plugged
            secsleft   = batt.secsleft  # can be psutil.POWER_TIME_UNLIMITED or -1

            if plugged:
                lines.append(_t(lang,
                    f"  🔌 Podłączono ładowarkę - bateria: {pct:.0f}%",
                    f"  🔌 Charger connected - battery at {pct:.0f}%"))
                lines.append(_t(lang,
                    "  Szacowanie czasu nie ma sensu gdy jesteś podłączony do prądu.",
                    "  Runtime estimate is irrelevant while you're plugged in."))
                return lines

            lines.append(_t(lang,
                f"  Bateria: {pct:.0f}%  (nie podłączono)",
                f"  Battery: {pct:.0f}%  (on battery)"))

            # If OS provides remaining time, use it
            if secsleft and secsleft > 0:
                hours   = secsleft // 3600
                minutes = (secsleft % 3600) // 60
                lines.append(_t(lang,
                    f"  System szacuje: ~{hours}h {minutes}m przy obecnym zużyciu",
                    f"  OS estimate: ~{hours}h {minutes}m at current consumption"))
        except Exception:
            lines.append(_t(lang,
                "  Nie można odczytać stanu baterii (psutil).",
                "  Cannot read battery state (psutil)."))
            return lines

        # Activity detection from message
        is_gaming = any(w in msg_lower for w in ("gra", "gaming", "fortnite", "cs", "minecraft"))
        is_video  = any(w in msg_lower for w in ("film", "video", "youtube", "oglądani", "watch"))
        is_work   = any(w in msg_lower for w in ("praca", "projekt", "pisani", "word", "excel", "piszę", "write", "work", "office"))
        is_idle   = any(w in msg_lower for w in ("bezczynny", "idle", "nic", "spać", "sleep"))

        # Drain rate lookup (% per hour, typical for laptops)
        if is_gaming:
            drain_lo, drain_hi = 22, 35
            activity_pl = "granie"
            activity_en = "gaming"
        elif is_video:
            drain_lo, drain_hi = 12, 18
            activity_pl = "oglądanie wideo"
            activity_en = "watching video"
        elif is_work:
            drain_lo, drain_hi = 8, 15
            activity_pl = "praca biurowa / pisanie"
            activity_en = "office / writing work"
        elif is_idle:
            drain_lo, drain_hi = 3, 6
            activity_pl = "bezczynność"
            activity_en = "idle"
        else:
            # Generic - mixed use
            drain_lo, drain_hi = 8, 18
            activity_pl = "typowe użytkowanie"
            activity_en = "typical mixed use"

        try:
            pct_now = psutil.sensors_battery().percent  # type: ignore[union-attr]
        except Exception:
            pct_now = 50  # fallback

        hrs_lo = pct_now / drain_hi
        hrs_hi = pct_now / drain_lo
        mins_lo = int((hrs_lo % 1) * 60)
        mins_hi = int((hrs_hi % 1) * 60)

        lines.append("")
        lines.append(_t(lang,
            f"  Aktywność: {activity_pl}",
            f"  Activity: {activity_en}"))
        lines.append(_t(lang,
            f"  Typowe zużycie: {drain_lo}–{drain_hi}% / godz",
            f"  Typical drain: {drain_lo}–{drain_hi}% / hour"))
        lines.append(_t(lang,
            f"  Szacowany czas: ~{int(hrs_lo)}h {mins_lo}m  -  {int(hrs_hi)}h {mins_hi}m",
            f"  Estimated remaining: ~{int(hrs_lo)}h {mins_lo}m  -  {int(hrs_hi)}h {mins_hi}m"))

        lines.append("")
        lines.append(_t(lang,
            "  💡 Oszczędność: zmniejsz jasność, wyłącz Wi-Fi gdy niepotrzebne, plan Balanced.",
            "  💡 Save battery: lower brightness, disable Wi-Fi when idle, use Balanced plan."))
        lines.append(_followup("perf", lang))
        return lines

    def _resp_upgrade_feasibility(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Checks whether the machine can have RAM or storage added.
        Uses WMI to read RAM slot count and populated slots.
        Falls back to graceful hardware info if WMI unavailable.
        """
        import subprocess

        lines = [_t(lang,
            f"{self.PREFIX} Możliwości rozbudowy sprzętu:",
            f"{self.PREFIX} Upgrade feasibility check:")]

        # ── RAM slots via WMI ──────────────────────────────────────────────
        lines.append("")
        lines.append(_t(lang, "  ── RAM ──", "  ── RAM ──"))
        try:
            ps_ram = (
                "Get-WmiObject Win32_PhysicalMemoryArray | "
                "Select-Object MemoryDevices,MaxCapacity | "
                "ConvertTo-Json"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_ram],
                capture_output=True, text=True, errors="replace", timeout=7,
            )
            import json as _json
            raw = res.stdout.strip()
            if raw:
                data = _json.loads(raw)
                if isinstance(data, dict):
                    data = [data]
                for slot_info in data:
                    total_slots = slot_info.get("MemoryDevices", "?")
                    max_cap_kb  = slot_info.get("MaxCapacity", 0) or 0
                    max_cap_gb  = int(max_cap_kb) // (1024 * 1024) if max_cap_kb else 0

                    # Count populated slots
                    ps_sticks = (
                        "Get-WmiObject Win32_PhysicalMemory | "
                        "Select-Object Capacity,Speed,MemoryType | "
                        "ConvertTo-Json"
                    )
                    res2 = subprocess.run(
                        ["powershell", "-NoProfile", "-Command", ps_sticks],
                        capture_output=True, text=True, errors="replace", timeout=7,
                    )
                    sticks = []
                    try:
                        raw2 = res2.stdout.strip()
                        if raw2:
                            sticks_data = _json.loads(raw2)
                            if isinstance(sticks_data, dict):
                                sticks_data = [sticks_data]
                            sticks = sticks_data
                    except Exception:
                        pass

                    populated = len(sticks)
                    free_slots = int(total_slots) - populated if isinstance(total_slots, int) else "?"
                    installed_gb = sum(
                        int(s.get("Capacity", 0) or 0) // (1024 ** 3) for s in sticks
                    )

                    lines.append(_t(lang,
                        f"  Sloty RAM: {total_slots} total  /  {populated} zajęte  /  {free_slots} wolne",
                        f"  RAM slots: {total_slots} total  /  {populated} used  /  {free_slots} free"))
                    lines.append(_t(lang,
                        f"  Zainstalowane: {installed_gb} GB  |  Maks obsługiwane: {max_cap_gb if max_cap_gb else '?'} GB",
                        f"  Installed: {installed_gb} GB  |  Max supported: {max_cap_gb if max_cap_gb else '?'} GB"))

                    if free_slots and free_slots != "?" and int(str(free_slots)) > 0:
                        lines.append(_t(lang,
                            f"  ✓ Masz {free_slots} wolny slot(ów) - można dołożyć RAM.",
                            f"  ✓ {free_slots} free slot(s) available - RAM upgrade is possible."))
                    else:
                        lines.append(_t(lang,
                            "  ! Wszystkie sloty zajęte - upgrade wymaga wymiany kości, nie dołożenia.",
                            "  ! All slots occupied - upgrade requires replacing sticks, not adding."))

                    if max_cap_gb and installed_gb and max_cap_gb > installed_gb:
                        diff = max_cap_gb - installed_gb
                        lines.append(_t(lang,
                            f"  Możesz dodać do {diff} GB więcej RAM (maks płyty: {max_cap_gb} GB).",
                            f"  You can add up to {diff} GB more RAM (board max: {max_cap_gb} GB)."))
            else:
                raise ValueError("empty")
        except Exception:
            lines.append(_t(lang,
                "  Nie udało się odczytać danych przez WMI - sprawdź Menedżer urządzeń.",
                "  WMI query failed - check Device Manager manually."))
            # Fallback: show current RAM from psutil
            try:
                import psutil
                vm = psutil.virtual_memory()
                lines.append(_t(lang,
                    f"  Aktualnie zainstalowane: {vm.total / (1024**3):.0f} GB RAM",
                    f"  Currently installed: {vm.total / (1024**3):.0f} GB RAM"))
            except Exception:
                pass

        # ── Storage upgrade hint ───────────────────────────────────────────
        lines.append("")
        lines.append(_t(lang, "  ── Dysk / Storage ──", "  ── Disk / Storage ──"))
        try:
            import psutil
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    total_gb = usage.total / (1024 ** 3)
                    free_gb  = usage.free  / (1024 ** 3)
                    lines.append(f"  {p.device}  {total_gb:.0f} GB total  /  {free_gb:.0f} GB free  ({p.fstype})")
                except Exception:
                    continue
        except Exception:
            lines.append(_t(lang,
                "  Nie można odczytać dysków.",
                "  Cannot read disk info."))

        lines.append("")
        lines.append(_t(lang,
            "  💡 Większość laptopów ma 1–2 sloty M.2/SATA. Sprawdź model w specyfikacji producenta.",
            "  💡 Most laptops have 1–2 M.2/SATA slots. Check manufacturer specs for your model."))
        lines.append(_t(lang,
            "  Wpisz 'specs' by zobaczyć pełny profil sprzętu.",
            "  Type 'specs' to see your full hardware profile."))
        return lines

    def _resp_overclock_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        mhz, boost = ls.get("cpu_mhz", -1), ls.get("cpu_boost", -1)
        lines = [_t(lang, f"{self.PREFIX} Zegary i zasilanie:",
                          f"{self.PREFIX} Clocks & power:")]
        lines.append(
            f"  CPU {self._dm_val(mhz,' MHz')}"
            + (f"  (boost {self._dm_val(boost,' MHz')})" if boost and boost > 0 else ""))
        if ls.get("gpu_clk_gr", -1) >= 0:
            lines.append(f"  GPU {self._dm_val(ls.get('gpu_clk_gr'),' MHz')} core · "
                         f"{self._dm_val(ls.get('gpu_clk_mem'),' MHz')} mem")
        v12 = ls.get("mb_volt_12v", -1)
        if v12 and v12 > 0:
            state = "OK" if 11.4 <= v12 <= 12.6 else "⚠"
            lines.append(f"  12V rail: {v12:.2f} V {state}")
        try:
            if mhz > 0 and boost > 0:
                over = mhz > boost * 1.03
                lines.append(_t(lang,
                    "  Wygląda na OC ponad profil boost." if over else
                    "  Zegary w granicach profilu - brak śladów OC.",
                    "  Looks overclocked beyond the boost profile." if over else
                    "  Clocks within profile - no OC signs."))
        except Exception:
            pass
        return lines

    def _resp_sensor_report(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        hist = ls.get("session_hist") or {}
        def mm(k):
            v = hist.get(k)
            return f" (min {v[0]:.0f} / max {v[1]:.0f})" if v and v[0] >= 0 else ""
        lines = [_t(lang, f"{self.PREFIX} Raport czujników (DeepMonitor, na żywo):",
                          f"{self.PREFIX} Sensor report (DeepMonitor, live):")]
        lines.append(f"  CPU  {self._dm_val(ls.get('cpu_load'),'%')} · "
                     f"{self._dm_val(ls.get('cpu_temp'),'°C')}{mm('cpu_temp')} · "
                     f"{self._dm_val(ls.get('cpu_mhz'),' MHz')} · "
                     f"{self._dm_val(ls.get('cpu_power'),' W')}")
        lines.append(f"  GPU  {self._dm_val(ls.get('gpu_load'),'%')} · "
                     f"{self._dm_val(ls.get('gpu_temp'),'°C')}{mm('gpu_temp')} · "
                     f"VRAM {self._dm_val(ls.get('gpu_vram_pct'),'%')} · "
                     f"{self._dm_val(ls.get('gpu_power'),' W')}")
        mbs, mbv = ls.get("mb_temp_sys", -1), ls.get("mb_temp_vrm", -1)
        if mbs >= 0 or mbv >= 0:
            lines.append(f"  MB   sys {self._dm_val(mbs,'°C')} · VRM {self._dm_val(mbv,'°C')}")
        v12, v5, v33 = ls.get("mb_volt_12v", -1), ls.get("mb_volt_5v", -1), ls.get("mb_volt_33v", -1)
        if any(v and v > 0 for v in (v12, v5, v33)):
            lines.append(f"  PWR  12V {self._dm_val(v12,' V',2)} · "
                         f"5V {self._dm_val(v5,' V',2)} · 3.3V {self._dm_val(v33,' V',2)}")
        if not ls.get("mb_source"):
            lines.append(_t(lang,
                "  (płyta/napięcia wymagają LibreHardwareMonitor w tle)",
                "  (motherboard/voltages need LibreHardwareMonitor running)"))
        return lines

    def _resp_hottest_component(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        cands = [(_t(lang, "CPU", "CPU"), ls.get("cpu_temp", -1)),
                 (_t(lang, "GPU", "GPU"), ls.get("gpu_temp", -1)),
                 (_t(lang, "Płyta (sys)", "Motherboard (sys)"), ls.get("mb_temp_sys", -1)),
                 ("VRM", ls.get("mb_temp_vrm", -1))]
        cands = [(n, t) for n, t in cands if t is not None and t >= 0]
        if not cands:
            return [_t(lang, f"{self.PREFIX} Brak odczytów temperatur - uruchom "
                             "LibreHardwareMonitor dla pełnych danych.",
                             f"{self.PREFIX} No temperature readings - run "
                             "LibreHardwareMonitor for full data.")]
        name, temp = max(cands, key=lambda x: x[1])
        try:
            from core.thermal_baseline import thermal_baseline
            verdict = thermal_baseline.classify_temp(temp)
        except Exception:
            verdict = ""
        vmap = {"normal": _t(lang, "w Twojej normie", "within your normal"),
                "elevated": _t(lang, "podwyższona, ale bez dramatu", "elevated, not dramatic"),
                "high": _t(lang, "wysoka - obserwuj", "high - keep an eye on it"),
                "critical": _t(lang, "KRYTYCZNA dla Twojej normy", "CRITICAL vs your normal")}
        lines = [_t(lang, f"{self.PREFIX} Najgorętszy teraz: {name} - {temp:.0f}°C",
                          f"{self.PREFIX} Hottest right now: {name} - {temp:.0f}°C")]
        if verdict in vmap:
            lines.append(f"  {vmap[verdict]}")
        others = " · ".join(f"{n} {t:.0f}°C" for n, t in cands if n != name)
        if others:
            lines.append(f"  {others}")
        return lines

    def _resp_cpu_clock(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        mhz, boost = ls.get("cpu_mhz", -1), ls.get("cpu_boost", -1)
        if mhz < 0:
            try:
                import psutil
                f = psutil.cpu_freq()
                mhz = f.current if f else -1
            except Exception:
                pass
        lines = [_t(lang, f"{self.PREFIX} Zegar CPU: {self._dm_val(mhz,' MHz')}",
                          f"{self.PREFIX} CPU clock: {self._dm_val(mhz,' MHz')}")]
        if boost and boost > 0 and mhz and mhz > 0:
            pct = mhz / boost * 100
            lines.append(_t(lang, f"  {pct:.0f}% profilu boost ({boost:.0f} MHz)",
                                  f"  {pct:.0f}% of boost profile ({boost:.0f} MHz)"))
            if pct < 55:
                lines.append(_t(lang,
                    "  Nisko przy pracy? Sprawdź plan zasilania: 'power plan'.",
                    "  Low under load? Check the power plan: 'power plan'."))
        return lines

    def _resp_vram_usage(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        pct, mb = ls.get("gpu_vram_pct", -1), ls.get("gpu_vram_mb", -1)
        if pct < 0 and mb < 0:
            return [_t(lang,
                f"{self.PREFIX} Brak danych VRAM - pełne odczyty daje karta NVIDIA "
                "(nvidia-smi) lub LHM.",
                f"{self.PREFIX} No VRAM data - full readings come from NVIDIA "
                "(nvidia-smi) or LHM.")]
        name = ls.get("gpu_name") or "GPU"
        lines = [_t(lang,
            f"{self.PREFIX} VRAM ({name}): {self._dm_val(mb,' MB')} "
            f"= {self._dm_val(pct,'%')}",
            f"{self.PREFIX} VRAM ({name}): {self._dm_val(mb,' MB')} "
            f"= {self._dm_val(pct,'%')}")]
        if pct >= 90:
            lines.append(_t(lang,
                "  ⚠ Prawie pełny - w grach to częsty powód stutteru. Zmniejsz "
                "tekstury o jeden poziom.",
                "  ⚠ Nearly full - a common stutter cause in games. Drop textures "
                "one notch."))
        elif pct >= 0:
            lines.append(_t(lang, "  Zapas jest - VRAM nie jest wąskim gardłem.",
                                  "  Headroom available - VRAM isn't the bottleneck."))
        return lines

