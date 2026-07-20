"""hck_gpt.responses.r_thermal - ThermalResponses mixin (9 intent handlers).
Split out of the builder.py monolith; composed into ResponseBuilder via MRO."""
from hck_gpt.responses.common import (  # shared helpers/data
    List,
    Optional,
    ParseResult,
    _followup,
    _t,
)


class ThermalResponses:

    # ── Fan Dashboard consult (the chart's hck_GPT [AI] button) ──────────────
    def _resp_fan_consult(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """Friendly pre-fan-tuning check: temps NOW + learned history verdict
        + a gentle (never aggressive) tuning suggestion + the learned
        hck_GPT - AI profile as the one-click alternative."""
        P = self.PREFIX
        cpu_t = gpu_t = None
        try:
            from hck_gpt.data.live_sensors import snapshot as _ls
            s = _ls()
            v = s.get("cpu_temp"); cpu_t = float(v) if v and v > 0 else None
            v = s.get("gpu_temp"); gpu_t = float(v) if v and v > 0 else None
        except Exception:
            pass
        now_bits = []
        if cpu_t: now_bits.append(f"CPU {cpu_t:.0f}°C")
        if gpu_t: now_bits.append(f"GPU {gpu_t:.0f}°C")
        now_txt = "  ·  ".join(now_bits) if now_bits else \
            _t(lang, "brak odczytu czujników", "no sensor reading")

        # History verdict from the learned baseline (honest when untrained)
        hist_pl = hist_en = ""
        try:
            from core.thermal_baseline import thermal_baseline as _tb
            pm = _tb.primary_metric()
            if "temp" in pm:
                st = _tb.training_status(pm)
                gi = st.get("gaming", {}) or st.get("medium", {})
                if int(gi.get("n", 0)) >= 20:
                    p5, p95 = gi.get("p5", 0), gi.get("p95", 0)
                    lbl = _tb.metric_label(pm)
                    hist_pl = (f"  Historycznie {lbl} pod obciążeniem trzyma "
                               f"{p5:.0f}-{p95:.0f}°C - bez śladów przegrzewania.")
                    hist_en = (f"  Historically {lbl} under load sits at "
                               f"{p5:.0f}-{p95:.0f}°C - no overheating pattern.")
        except Exception:
            pass

        ref = max((v for v in (cpu_t, gpu_t) if v is not None), default=None)
        if ref is None:
            v_pl = v_en = ""
        elif ref < 55:
            v_pl, v_en = " Chłodno i spokojnie.", " Cool and calm."
        elif ref < 70:
            v_pl, v_en = " Ciepło, ale w normie.", " Warm, but normal."
        elif ref < 82:
            v_pl, v_en = (" Gorąco - krzywa w górę to dobry pomysł.",
                          " Hot - lifting the curve is a good idea.")
        else:
            v_pl, v_en = (" Bardzo gorąco - zacznij od sprawdzenia przepływu powietrza!",
                          " Very hot - check the airflow first!")
        lines = [_t(lang,
                    f"{P} Hej! Zerknąłem na czujniki: {now_txt}.{v_pl}",
                    f"{P} Hey! Sensor check: {now_txt}.{v_en}")]
        if hist_pl:
            lines.append(_t(lang, hist_pl, hist_en))
        else:
            lines.append(_t(lang,
                "  Historii jeszcze się uczę - po kilku dniach powiem, co jest normą TEJ maszyny.",
                "  Still learning your history - a few more days and I'll know THIS machine's normal."))
        lines.append(_t(lang,
            "  Konfiguruj śmiało. Delikatna zabawa: podnieś środkowe punkty krzywej o 5-10%,",
            "  Tune away. Gentle play: lift the middle curve points by 5-10%,"))
        lines.append(_t(lang,
            "  posłuchaj minutę i dopiero wtedy idź wyżej - bez skoków na 100%.",
            "  listen for a minute, then go higher - no jumps straight to 100%."))
        lines.append(_t(lang,
            "  Albo wybierz profil 'hck_GPT - AI' - krzywą uszytą z Twoich wyuczonych temperatur.",
            "  Or pick the 'hck_GPT - AI' profile - a curve shaped from your learned temperatures."))
        lines.append(_t(lang,
            "  Chcesz, żebym przełączył go teraz? Napisz: 'ustaw profil AI wentylatorów'.",
            "  Want me to switch it now? Say: 'apply the AI fan profile'."))
        return lines

    def _resp_fan_apply_ai(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """Actually switch the Fan Dashboard to the learned profile - the
        dashboard registers itself as ui.fan_dashboard when built."""
        P = self.PREFIX
        try:
            from import_core import COMPONENTS
            dash = COMPONENTS.get("ui.fan_dashboard")
        except Exception:
            dash = None
        if dash is not None and getattr(dash, "apply_ai_profile", None):
            ok = False
            try:
                ok = bool(dash.apply_ai_profile())
            except Exception:
                ok = False
            if ok:
                return [_t(lang,
                    f"{P} Zrobione ✓ Profil 'hck_GPT - AI' aktywny - krzywa z Twoich wyuczonych temperatur.",
                    f"{P} Done ✓ 'hck_GPT - AI' profile active - the curve shaped from your learned temps."),
                    _t(lang,
                    "  Kolano krzywej siedzi tuż nad Twoją normą pod obciążeniem: cicho w normie, pewnie powyżej.",
                    "  The knee sits just above your load-time normal: quiet inside it, firm above it.")]
        return [_t(lang,
            f"{P} Otwórz najpierw Fan Dashboard (Fan Control), a potem poproś ponownie -",
            f"{P} Open the Fan Dashboard first (Fan Control), then ask again -"),
            _t(lang,
            "  profil przełączam na żywo na otwartej stronie.",
            "  I switch the profile live on the open page.")]

    def _resp_temperature(self, r: ParseResult, lang: str = "pl") -> List[str]:
        # Leads with the learned, workload-aware verdict (thermal_baseline) so
        # the answer is "82C is +14% above your gaming norm", not a fixed 85C cutoff.
        from hck_gpt.context.system_context import system_context
        snap     = system_context.snapshot()
        cpu_load = float(snap.get("cpu_pct",  0) or 0)
        cpu_temp = float(snap.get("cpu_temp", 0) or 0)
        gpu_temp = float(snap.get("gpu_temp", 0) or 0)
        gpu_load = 0.0
        try:
            from hck_gpt.data.live_sensors import snapshot as _ls
            ls = _ls()
            if (ls.get("gpu_load", -1) or -1) >= 0:
                gpu_load = float(ls["gpu_load"])
            if cpu_temp <= 0 and (ls.get("cpu_temp", -1) or -1) > 0:
                cpu_temp = float(ls["cpu_temp"])
            if gpu_temp <= 0 and (ls.get("gpu_temp", -1) or -1) > 0:
                gpu_temp = float(ls["gpu_temp"])
        except Exception:
            pass

        lines: List[str] = []
        try:
            from core.thermal_baseline import thermal_baseline
            thermal_baseline.maybe_rebuild()
            block = thermal_baseline.format_for_chat(cpu_temp, cpu_load, gpu_load, lang, gpu_temp=gpu_temp).split("\n")
            block[0] = f"{self.PREFIX} {block[0].lstrip()}"
            lines.extend(block)
        except Exception:
            pass

        if gpu_temp > 0:
            g_state = "✓" if gpu_temp <= 83 else "⚠"
            lines.append(_t(lang,
                f"  {g_state} GPU teraz: {gpu_temp:.0f}°C",
                f"  {g_state} GPU now: {gpu_temp:.0f}°C"))

        try:
            from hck_stats_engine.query_api import query_api
            ts = query_api.get_temperature_summary(days=7)
            if ts and ts.get("cpu_temp_avg"):
                lines.append(_t(lang,
                    f"  Śr. 7 dni: CPU {ts['cpu_temp_avg']:.0f}°C (max {ts.get('cpu_temp_max', '-')}°C)",
                    f"  7-day avg: CPU {ts['cpu_temp_avg']:.0f}°C (peak {ts.get('cpu_temp_max', '-')}°C)"))
        except Exception:
            pass

        if not lines:
            return [_t(lang,
                f"{self.PREFIX} Brak danych o temperaturach - scheduler zbiera co minutę, sprawdź za chwilę.",
                f"{self.PREFIX} No temperature data yet - the scheduler samples every minute, check back shortly.")]

        lines.append(_followup("health", lang))
        return lines

    def _resp_voltage_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        # Real voltage answer backed by the learned SPC analyzer (was aliased to temperature).
        try:
            from core.voltage_analyzer import voltage_analyzer
            voltage_analyzer.maybe_rebuild()
            block = voltage_analyzer.format_for_chat(lang).split("\n")
        except Exception:
            return [_t(lang,
                f"{self.PREFIX} Nie mogę teraz odczytać napięć.",
                f"{self.PREFIX} Cannot read voltages right now.")]
        block[0] = f"{self.PREFIX} {block[0].lstrip()}"
        return block

    def _resp_gpu_temp_why(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context
        snap     = system_context.snapshot()
        gpu_temp = snap.get("gpu_temp", None)

        if lang == "en":
            lines = [f"{self.PREFIX} GPU temperature analysis:"]
            if gpu_temp:
                if gpu_temp > 90:
                    lines += [
                        f"  ⚠ {gpu_temp}°C - CRITICAL. GPU is thermal throttling.",
                        "  Causes: full load (gaming/rendering), poor airflow, dusty heatsink.",
                        "  Fix: clean GPU cooler, improve case airflow, lower in-game settings.",
                    ]
                elif gpu_temp > 80:
                    lines += [
                        f"  ! {gpu_temp}°C - high but within spec for most GPUs under load.",
                        "  Modern GPUs are designed for up to 85–95°C under full load.",
                        "  Check airflow if idle temp is also high.",
                    ]
                else:
                    lines += [
                        f"  ✓ {gpu_temp}°C - normal operating temperature.",
                        "  GPUs under load typically run 65–80°C. You're fine.",
                    ]
            else:
                lines += [
                    "  No GPU temperature sensor data available.",
                    "  Under load (gaming): 65–80°C is normal. 85°C+ warrants attention.",
                    "  Check GPU-Z or HWInfo for hardware-level readings.",
                ]
            lines.append("  💬 Type 'temperatures' for full thermal report.")
        else:
            lines = [f"{self.PREFIX} Analiza temperatury GPU:"]
            if gpu_temp:
                if gpu_temp > 90:
                    lines += [
                        f"  ⚠ {gpu_temp}°C - KRYTYCZNA. GPU throttluje termicznie.",
                        "  Przyczyny: pełne obciążenie (gry/render), słaby przepływ powietrza, zakurzony chłodnik.",
                        "  Fix: wyczyść chłodnik GPU, popraw obieg powietrza, obniż ustawienia gry.",
                    ]
                elif gpu_temp > 80:
                    lines += [
                        f"  ! {gpu_temp}°C - wysoka, ale w normie dla większości GPU pod obciążeniem.",
                        "  Nowoczesne GPU są projektowane do 85–95°C pod pełnym ładunkiem.",
                        "  Sprawdź przepływ powietrza jeśli temp na jałowym też jest wysoka.",
                    ]
                else:
                    lines += [
                        f"  ✓ {gpu_temp}°C - normalna temperatura robocza.",
                        "  GPU pod obciążeniem gier: 65–80°C to norma. Wszystko OK.",
                    ]
            else:
                lines += [
                    "  Brak danych z czujnika temperatury GPU.",
                    "  Pod obciążeniem (gry): 65–80°C norma. Powyżej 85°C warto reagować.",
                    "  Sprawdź GPU-Z lub HWInfo dla odczytów sprzętowych.",
                ]
            lines.append("  💬 Wpisz 'temperatury' po pełny raport termiczny.")
        return lines

    def _resp_fan_noise_history(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.context.system_context import system_context

        snap = system_context.snapshot()
        cpu  = float(snap.get("cpu_pct",  0) or 0)
        temp_now: Optional[float] = None

        # Get current temperatures from snapshot
        temps = snap.get("temperatures", [])
        if temps:
            temp_now = max(t for _, t in temps) if temps else None

        # Historical temperature trend from metrics_store
        hist_temp_cmp = self._get_historical_comparison("cpu_temp", 7, lang)

        lines = [_t(lang,
            f"{self.PREFIX} Analiza głośności wentylatora:",
            f"{self.PREFIX} Fan noise analysis:")]

        # Main cause: temperature and CPU load
        if cpu > 80 or (temp_now and temp_now > 80):
            lines.append(_t(lang,
                f"  🔴 CPU na {cpu:.0f}%{f' / temp {temp_now:.0f}°C' if temp_now else ''} - wentylatory kręcą się szybciej, to normalne.",
                f"  🔴 CPU at {cpu:.0f}%{f' / temp {temp_now:.0f}°C' if temp_now else ''} - fans spinning up, that's expected."))
        elif cpu > 55 or (temp_now and temp_now > 65):
            lines.append(_t(lang,
                f"  🟡 Umiarkowane obciążenie (CPU {cpu:.0f}%{f' / {temp_now:.0f}°C' if temp_now else ''}) - wentylatory mogą być słyszalne.",
                f"  🟡 Moderate load (CPU {cpu:.0f}%{f' / {temp_now:.0f}°C' if temp_now else ''}) - fans may be audible."))
        else:
            lines.append(_t(lang,
                f"  ✓ Niskie obciążenie (CPU {cpu:.0f}%) - jeśli fan hałasuje, może być kurz lub starzejące się łożysko.",
                f"  ✓ Low load (CPU {cpu:.0f}%) - if fan is loud, suspect dust or aging bearing."))

        # Historical comparison (time-travel)
        if hist_temp_cmp:
            lines.append(_t(lang, "  Porównanie historyczne (7 dni):", "  Historical comparison (7 days):"))
            lines.append(hist_temp_cmp)
        else:
            lines.append(_t(lang,
                "  Brak danych historycznych - wentylatory nie mają czujnika RPM przez psutil.",
                "  No historical fan data - fan RPM not exposed via psutil on Windows."))

        # Practical tips
        lines.append("")
        lines.append(_t(lang,
            "  Możliwe przyczyny głośniejszego wentylatora:",
            "  Possible causes of increased fan noise:"))
        lines.append(_t(lang,
            "  • Kurz w chłodniku - wyczyść sprężonym powietrzem (1x rok)",
            "  • Dust in heatsink - clean with compressed air (1x/year)"))
        lines.append(_t(lang,
            "  • Zużyte łożysko wentylatora - charakterystyczny warkot/szum",
            "  • Worn fan bearing - grinding or rattling sound"))
        lines.append(_t(lang,
            "  • Wysokie obciążenie (gry, render) - normalne i tymczasowe",
            "  • High load (gaming, rendering) - normal and temporary"))
        lines.append(_t(lang,
            "  💬 Wpisz 'temperatury' po pełny raport termiczny",
            "  💬 Type 'temperatures' for full thermal report"))
        return lines

    def _resp_temp_comparison(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """
        Time-Travel: compares current temps to 7-day and 30-day historical averages.
        Answers "is my PC hotter than usual lately?"
        """
        cpu_7d  = self._get_historical_comparison("cpu_temp", 7,  lang)
        cpu_30d = self._get_historical_comparison("cpu_temp", 30, lang)
        gpu_7d  = self._get_historical_comparison("gpu_temp", 7,  lang)

        has_data = any([cpu_7d, cpu_30d, gpu_7d])
        if not has_data:
            # _no_data already carries the hck_GPT: prefix - don't prepend a
            # second prefixed header (was producing a double "hck_GPT:" line).
            lines = self._no_data("temp_comparison", lang,
                _t(lang, "brak danych z metrics_store", "no metrics_store temperature history"))
            lines.append(_t(lang,
                "  PC Workman zbiera dane co 5 min - wróć za kilka dni.",
                "  PC Workman collects data every 5 min - check back in a few days."))
            return lines

        lines = [_t(lang,
            f"{self.PREFIX} Porównanie temperatur - czy jest goręcej niż zwykle?",
            f"{self.PREFIX} Temperature comparison - running hotter than usual?")]

        if cpu_7d:
            lines.append(_t(lang, "  CPU temp vs 7 dni:", "  CPU temp vs 7 days:"))
            lines.append(cpu_7d)
        if cpu_30d:
            lines.append(_t(lang, "  CPU temp vs 30 dni:", "  CPU temp vs 30 days:"))
            lines.append(cpu_30d)
        if gpu_7d:
            lines.append(_t(lang, "  GPU temp vs 7 dni:", "  GPU temp vs 7 days:"))
            lines.append(gpu_7d)

        lines.append("")
        lines.append(_t(lang,
            "  Jeśli temperatury są wyraźnie wyższe niż zwykle:",
            "  If temperatures are notably higher than normal:"))
        lines.append(_t(lang,
            "  • Wyczyść chłodnik ze kurzu (sprężone powietrze)",
            "  • Clean heatsink of dust (compressed air)"))
        lines.append(_t(lang,
            "  • Sprawdź plan zasilania - High Performance grzeje bardziej",
            "  • Check power plan - High Performance runs hotter"))
        lines.append(_t(lang,
            "  • Sprawdź czy pasta termoprzewodząca nie wymaga wymiany (>3-4 lata)",
            "  • Check if thermal paste needs replacing (>3–4 years old)"))
        lines.append(_t(lang,
            "  💬 Wpisz 'temperatury' po aktualny live raport",
            "  💬 Type 'temperatures' for current live report"))
        return lines

    def _resp_fan_speed(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from core.hardware_sensors import get_hardware_sensors
            fans = [s for s in get_hardware_sensors().get_flat_sensor_list()
                    if "rpm" in str(s.get("unit", "")).lower()
                    or "fan" in str(s.get("type", "")).lower()]
        except Exception:
            fans = []
        if not fans:
            return [_t(lang,
                f"{self.PREFIX} Nie widzę odczytów wentylatorów. Do RPM potrzebny jest "
                "LibreHardwareMonitor (uruchomiony w tle) - psutil ich nie podaje.",
                f"{self.PREFIX} No fan readings available. RPM needs LibreHardwareMonitor "
                "running in the background - psutil doesn't expose them."),
                _t(lang, "  Sprawdź też: 'temperatura' · 'najgorętszy podzespół'",
                         "  Also try: 'temperature' · 'hottest component'")]
        lines = [_t(lang, f"{self.PREFIX} Wentylatory teraz:",
                          f"{self.PREFIX} Fans right now:")]
        for s in fans[:6]:
            lines.append(f"  {str(s.get('sensor_name','?'))[:30]:<30} {s.get('value','-')}")
        return lines

    def _resp_thermal_history(self, r: ParseResult, lang: str = "pl") -> List[str]:
        try:
            from hck_gpt.data.metrics_store import metrics_store
            rows = metrics_store.get_history(hours=12)
        except Exception:
            rows = []
        cpu = [x["cpu_temp"] for x in rows if (x.get("cpu_temp") or -1) >= 0]
        gpu = [x["gpu_temp"] for x in rows if (x.get("gpu_temp") or -1) >= 0]
        if not cpu and not gpu:
            return [_t(lang,
                f"{self.PREFIX} Za mało zapisanych temperatur (DeepMonitor zbiera migawki "
                "co 5 min - daj mi trochę czasu po starcie).",
                f"{self.PREFIX} Not enough recorded temperatures yet (DeepMonitor snapshots "
                "every 5 min - give me a little time after startup).")]
        lines = [_t(lang, f"{self.PREFIX} Temperatury z ostatnich 12 h "
                          f"({len(rows)} migawek DeepMonitor):",
                          f"{self.PREFIX} Temperatures over the last 12 h "
                          f"({len(rows)} DeepMonitor snapshots):")]
        if cpu:
            lines.append(f"  CPU   min {min(cpu):.0f}°C · avg {sum(cpu)/len(cpu):.0f}°C · max {max(cpu):.0f}°C")
        if gpu:
            lines.append(f"  GPU   min {min(gpu):.0f}°C · avg {sum(gpu)/len(gpu):.0f}°C · max {max(gpu):.0f}°C")
        try:
            from core.thermal_baseline import thermal_baseline
            ls = self._dm_live()
            verdict = thermal_baseline.format_for_chat(
                ls.get("cpu_temp", -1), ls.get("cpu_load", -1),
                ls.get("gpu_load", -1), lang,
                gpu_temp=ls.get("gpu_temp", -1)).split("\n")[0]
            lines += ["", verdict]
        except Exception:
            pass
        return lines

    def _resp_thermal_prediction(self, r: ParseResult, lang: str = "pl") -> List[str]:
        ls = self._dm_live()
        try:
            from core.thermal_baseline import thermal_baseline
            bucket = thermal_baseline.classify(ls.get("cpu_load", -1) or 0,
                                               ls.get("gpu_load", 0) or 0)
            rng = thermal_baseline.bucket_range(bucket) if hasattr(thermal_baseline, "bucket_range") else None
        except Exception:
            bucket, rng = None, None
        cur = self._dm_val(ls.get("cpu_temp"), "°C")
        if not bucket:
            return [_t(lang,
                f"{self.PREFIX} Jeszcze uczę się Twoich temperatur - wróć po kilku "
                "sesjach, wtedy przewidzę zakres dla każdego obciążenia.",
                f"{self.PREFIX} Still learning your temperatures - come back after a "
                "few sessions and I'll predict the range for each workload.")]
        head = _t(lang,
            f"{self.PREFIX} Przy obecnym obciążeniu ({bucket}) Twoje CPU zwykle trzyma:",
            f"{self.PREFIX} At your current workload ({bucket}) your CPU usually holds:")
        lines = [head]
        if rng:
            lines.append(f"  {rng[0]:.0f}–{rng[1]:.0f}°C  ·  " +
                         _t(lang, f"teraz: {cur}", f"now: {cur}"))
        else:
            try:
                from core.thermal_baseline import thermal_baseline as _tb
                lines += _tb.format_for_chat(ls.get("cpu_temp", -1),
                                             ls.get("cpu_load", -1),
                                             ls.get("gpu_load", -1), lang,
                                             gpu_temp=ls.get("gpu_temp", -1)).split("\n")
            except Exception:
                lines.append(_t(lang, f"  teraz: {cur}", f"  now: {cur}"))
        lines.append(_t(lang,
            "  Nauczone na Twoich danych (Welford) - nie z tabelki producenta.",
            "  Learned from your own data (Welford) - not a vendor spec sheet."))
        return lines

    def _resp_cooling_advice(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'How do I cool my PC' - advice ranked by what is ACTUALLY hot here."""
        ls = self._dm_live()
        ct, gt = ls.get("cpu_temp", -1), ls.get("gpu_temp", -1)
        lines = [_t(lang, f"{self.PREFIX} Plan chłodzenia pod TWOJE odczyty "
                          f"(CPU {self._dm_val(ct,'°C')} · GPU {self._dm_val(gt,'°C')}):",
                          f"{self.PREFIX} Cooling plan based on YOUR readings "
                          f"(CPU {self._dm_val(ct,'°C')} · GPU {self._dm_val(gt,'°C')}):")]
        tips = []
        if ct >= 80:
            tips.append(_t(lang,
                "1. CPU grzeje najmocniej - kurz z radiatora i sprawdź pastę "
                "(po 3+ latach potrafi dać -10°C).",
                "1. CPU is the hot one - dust the heatsink and check the paste "
                "(3+ year old paste can cost you 10°C)."))
        if gt >= 75:
            tips.append(_t(lang,
                f"{len(tips)+1}. GPU wysoko - zrób miejsce na przepływ powietrza, "
                "rozważ krzywą wentylatorów.",
                f"{len(tips)+1}. GPU running high - clear airflow around the card, "
                "consider a fan curve."))
        if not tips:
            try:
                from core.thermal_baseline import thermal_baseline
                verdict = thermal_baseline.classify_temp(ct) if ct >= 0 else "normal"
            except Exception:
                verdict = "normal"
            if verdict in ("normal", "elevated"):
                tips.append(_t(lang,
                    "1. Dobra wiadomość: temperatury są w Twojej normie - "
                    "nie ma pożaru do gaszenia. Profilaktycznie:",
                    "1. Good news: temps are within your normal - nothing on "
                    "fire. Preventively:"))
        tips.append(_t(lang,
            f"{len(tips)+1}. Zmniejsz obciążenie tła: 'top procesy' pokaże "
            "żarłoków, App Hibernation uśpi nieaktywne [-> Optimization].",
            f"{len(tips)+1}. Cut background load: 'top processes' finds the "
            "hogs, App Hibernation freezes idle ones [-> Optimization]."))
        tips.append(_t(lang,
            f"{len(tips)+1}. Laptop? Podnieś tył o 2 cm - najtańszy upgrade "
            "chłodzenia świata.",
            f"{len(tips)+1}. Laptop? Raise the back 2 cm - the cheapest "
            "cooling upgrade in existence."))
        lines += [f"  {t}" for t in tips]
        lines.append(_t(lang,
            "  Kontrola za tydzień: napisz 'trend tygodnia' - zobaczysz, czy pomogło.",
            "  Check back in a week: type 'weekly trends' to see if it helped."))
        return lines

