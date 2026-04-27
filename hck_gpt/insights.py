# hck_gpt/insights.py
import time
import random
import traceback
from datetime import datetime, timedelta

_PATTERN_TTL = 300   # 5 min — 7-day scan is expensive
_SUMMARY_TTL  = 120  # 2 min
_BANNER_TTL   = 30   # 30 s


class InsightsEngine:

    def __init__(self) -> None:
        self._query_api = None
        self._event_detector = None
        self._process_aggregator = None
        self._classifier = None
        self._loaded = False

        self._session_start = time.time()

        self._last_greeting_time: float = 0
        self._last_greeting_text: list[str] | None = None
        self._last_insight_time: float = 0
        self._last_insight_msg: str | None = None

        # Caches
        self._pattern_cache: list | None = None
        self._pattern_cache_ts: float = 0
        self._summary_cache: dict[int, tuple[float, dict]] = {}
        self._banner_cache: str = ""
        self._banner_cache_ts: float = 0

        self._teaser_templates: dict[str, list[str]] = {
            "Gaming": [
                "Ready for another round of {name}? Your GPU is warmed up.",
                "{name} again? Let's see if your CPU can keep up today.",
                "Your PC is expecting {name} — it's been {freq}/7 days.",
                "{name} incoming? Average CPU hit: {cpu:.0f}%. Game on.",
            ],
            "Browser": [
                "{name} again? Your RAM knows the drill.",
                "Round {freq} of {name} this week. Classic.",
                "{name} — your RAM's favourite customer. ~{ram:.0f}MB daily.",
                "Tabs are calling! {name} has been active {freq}/7 days.",
            ],
            "Development": [
                "Back to {name}? Let's see what you build today.",
                "{name} — {freq}/7 days. Productivity mode activated.",
                "Time to code? {name} is your daily driver.",
            ],
            "Communication": [
                "{name} calling — you use it almost every day.",
                "{name} — {freq}/7 days. Staying connected.",
            ],
            "Media": [
                "{name} time? {freq}/7 days and counting.",
                "{name} — part of your daily routine now.",
            ],
            "_default": [
                "{name} — {freq}/7 days. It's basically part of your system now.",
                "You've been using {name} regularly. CPU avg: {cpu:.0f}%.",
            ],
        }

    def get_session_uptime(self) -> float:
        return time.time() - self._session_start

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        for mod, attr in [
            ("hck_stats_engine.query_api",       "query_api"),
            ("hck_stats_engine.events",           "event_detector"),
            ("hck_stats_engine.process_aggregator", "process_aggregator"),
        ]:
            try:
                obj = __import__(mod, fromlist=[attr])
                setattr(self, f"_{attr}", getattr(obj, attr))
            except Exception:
                pass
        try:
            from core.process_classifier import classifier
            self._classifier = classifier
        except Exception:
            pass

    # ── Greeting ──────────────────────────────────────────────────────

    def get_greeting(self) -> list[str]:
        """Cached for 30 min. Returns list of chat lines."""
        now = time.time()
        if self._last_greeting_text and (now - self._last_greeting_time) < 1800:
            return self._last_greeting_text

        self._ensure_loaded()
        lines: list[str] = []

        hour = datetime.now().hour
        day_name = datetime.now().strftime("%A")
        if hour < 6:
            time_greet = "Late night session!"
        elif hour < 12:
            time_greet = "Good morning!"
        elif hour < 18:
            time_greet = "Good afternoon!"
        else:
            time_greet = "Good evening!"

        if datetime.now().weekday() >= 5:
            time_greet += f" Relaxing {day_name}?"

        lines.append(f"hck_GPT: {time_greet}")

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_procs = self._get_daily_breakdown(yesterday, top_n=3)
        summary = self._get_summary(days=1)

        if summary and summary.get("cpu_avg"):
            cpu_avg = summary["cpu_avg"]
            qualifier = "light" if cpu_avg < 30 else "moderate" if cpu_avg < 60 else "heavy"
            line = f"hck_GPT: Yesterday was a {qualifier} day — CPU averaged {cpu_avg:.0f}%"
            if yesterday_procs:
                top = yesterday_procs[0]
                name = top.get("display_name", top.get("process_name", "?"))
                line += f", {name} was the main culprit."
            else:
                line += "."
            lines.append(line)

        teaser = self._build_teaser()
        if teaser:
            lines.append(f"hck_GPT: {teaser}")

        session_h = self.get_session_uptime() / 3600
        if session_h > 4:
            lines.append(f"hck_GPT: You've been running for {session_h:.1f}h. Stay hydrated!")

        if not lines:
            lines.append("hck_GPT: Welcome back! I'm monitoring your system.")

        self._last_greeting_time = now
        self._last_greeting_text = lines
        return lines

    # ── Current insight (periodic) ────────────────────────────────────

    def get_current_insight(self) -> str | None:
        """Single contextual message. Rate-limited to once per 30s. No repeats."""
        now = time.time()
        if (now - self._last_insight_time) < 30:
            return None

        self._ensure_loaded()
        self._last_insight_time = now

        # Priority 1: recent spikes
        msg = self._check_recent_spikes(minutes=5)
        if msg and msg != self._last_insight_msg:
            self._last_insight_msg = msg
            return msg

        # Priority 2: heavy process live
        msg = self._check_live_processes()
        if msg and msg != self._last_insight_msg:
            self._last_insight_msg = msg
            return msg

        # Priority 3: session milestone
        msg = self._check_session_milestone()
        if msg and msg != self._last_insight_msg:
            self._last_insight_msg = msg
            return msg

        return None

    def _check_recent_spikes(self, minutes: int = 5) -> str | None:
        if not self._query_api:
            return None
        try:
            now = time.time()
            events = self._query_api.get_events(
                start_ts=now - (minutes * 60), end_ts=now,
                event_type="spike", limit=3
            )
            if not events:
                return None
            e = events[0]
            severity = e.get("severity", "info")
            metric = e.get("metric", "?")
            value = e.get("value", 0)
            baseline = e.get("baseline", 0)
            label = {"cpu": "CPU", "ram": "RAM", "gpu": "GPU",
                     "cpu_temp": "CPU temp", "gpu_temp": "GPU temp"}.get(metric, metric.upper())
            icon = "!" if severity == "critical" else "^"
            if baseline:
                return (f"hck_GPT: [{icon}] {label} spike — "
                        f"{value:.0f}% (+{value - baseline:.0f} above {baseline:.0f}%)")
            return f"hck_GPT: [{icon}] {label} spike detected — {value:.0f}%"
        except Exception:
            return None

    @staticmethod
    def _ensure_exe(name: str) -> str:
        return name if name.lower().endswith(".exe") else name + ".exe"

    def _check_live_processes(self) -> str | None:
        if not self._process_aggregator:
            return None
        try:
            top = self._process_aggregator.get_current_hour_top(10)
            filtered = []
            for proc in top:
                name = proc.get("name", "").lower()
                if self._is_system_noise(name):
                    continue
                proc["cpu_avg"] = min(proc.get("cpu_avg", 0), 100.0)
                proc["cpu_max"] = min(proc.get("cpu_max", 0), 100.0)
                filtered.append(proc)

            if not filtered:
                return None

            classified = self._classify_processes(filtered)

            if classified["games"]:
                g = classified["games"][0]
                pname = self._ensure_exe(g.get("name", ""))
                cpu = g.get("cpu_avg", 0)
                ram = g.get("ram_avg_mb", 0)
                return random.choice([
                    f"hck_GPT: {pname} is running — CPU {cpu:.0f}%. Game on.",
                    f"hck_GPT: {pname} active — CPU {cpu:.0f}%, RAM {ram:.0f}MB.",
                    f"hck_GPT: Gaming detected: {pname} @ CPU {cpu:.0f}%.",
                ])

            if classified["browsers"]:
                b = classified["browsers"][0]
                pname = self._ensure_exe(b.get("name", ""))
                ram = b.get("ram_avg_mb", 0)
                if ram > 400:
                    return random.choice([
                        f"hck_GPT: {pname} is eating RAM — {ram:.0f}MB. Consider closing tabs.",
                        f"hck_GPT: {pname} memory: {ram:.0f}MB. Tab management recommended.",
                    ])

            if classified["dev_tools"]:
                d = classified["dev_tools"][0]
                name = d.get("display_name", d["name"])
                cpu = d.get("cpu_avg", 0)
                if cpu > 15:
                    return f"hck_GPT: {name} is working hard — CPU {cpu:.0f}%."

            if filtered:
                heavy = filtered[0]
                pname = self._ensure_exe(heavy.get("name", ""))
                cpu = heavy.get("cpu_avg", 0)
                if cpu > 30:
                    return f"hck_GPT: {pname} is using {cpu:.0f}% CPU — that's heavy."

            return None
        except Exception:
            return None

    @staticmethod
    def _is_system_noise(name: str) -> bool:
        noise = {
            "system idle process", "idle", "system", "registry",
            "memory compression", "secure system", "system interrupts",
            "ntoskrnl", "wininit", "csrss", "smss", "lsass", "services",
        }
        n = name.lower().strip()
        return n in noise or "idle" in n

    def _check_session_milestone(self) -> str | None:
        hours = self.get_session_uptime() / 3600
        milestones = {
            1: "1 hour in! Your system is running smooth.",
            2: "2 hours of monitoring. Everything logged.",
            4: "4 hours! That's a solid session.",
            8: "8 hours of uptime — marathon session!",
            12: "12 hours. Your PC is a trooper.",
        }
        for h, msg in milestones.items():
            if h <= hours < h + (2 / 60):
                return f"hck_GPT: {msg}"
        return None

    # ── Health check ──────────────────────────────────────────────────

    def get_health_check(self) -> list[str]:
        self._ensure_loaded()
        lines = ["━" * 28, "hck_GPT — Quick Health Check", "━" * 28, ""]

        session_str = self._format_duration(self.get_session_uptime())
        lines.append(f"Session uptime: {session_str}")

        if self._process_aggregator:
            try:
                top = [p for p in self._process_aggregator.get_current_hour_top(10)
                       if not self._is_system_noise(p.get("name", ""))]
                for p in top:
                    p["cpu_avg"] = min(p.get("cpu_avg", 0), 100.0)
                if top:
                    top3 = top[:3]
                    total_cpu = sum(min(p.get("cpu_avg", 0), 100) for p in top3)
                    total_ram = sum(p.get("ram_avg_mb", 0) for p in top3)
                    lines.append(f"Top 3 load: CPU ~{total_cpu:.0f}%, RAM ~{total_ram:.0f}MB")
                    h = top3[0]
                    lines.append(f"   Heaviest: {h.get('display_name', h.get('name', '?'))} "
                                 f"({h.get('cpu_avg', 0):.1f}% CPU)")
            except Exception:
                pass

        summary = self._get_summary(days=1)
        if summary and summary.get("cpu_avg"):
            lines += ["",
                      f"Today avg: CPU {summary['cpu_avg']:.0f}% | "
                      f"RAM {summary.get('ram_avg', 0):.0f}% | "
                      f"GPU {summary.get('gpu_avg', 0):.0f}%"]
            cpu_max = summary.get("cpu_max", 0)
            if cpu_max > 85:
                lines.append(f"   Peak CPU: {cpu_max:.0f}% — that's high!")
            elif cpu_max > 0:
                lines.append(f"   Peak CPU: {cpu_max:.0f}%")

        if self._event_detector:
            try:
                alerts = self._event_detector.get_active_alerts_count()
                total = alerts.get("total", 0)
                lines.append("")
                if total == 0:
                    lines.append("No active alerts — system is healthy")
                else:
                    parts = []
                    if alerts.get("critical"):
                        parts.append(f"{alerts['critical']} critical")
                    if alerts.get("warning"):
                        parts.append(f"{alerts['warning']} warnings")
                    lines.append(f"Active alerts: {', '.join(parts)}")
            except Exception:
                pass

        if self._query_api:
            try:
                dr = self._query_api.get_available_date_range()
                lines.append("")
                if dr:
                    days = dr.get("total_days", 0)
                    lines.append(f"Data collected: {days} day{'s' if days != 1 else ''} "
                                 f"(since {dr.get('earliest_date', '?')})")
                else:
                    lines.append("Data collection: just started — give it time")
            except Exception:
                pass

        lines += ["", "━" * 28]
        return lines

    # ── Habit summary ─────────────────────────────────────────────────

    def get_habit_summary(self) -> list[str]:
        self._ensure_loaded()
        lines = ["━" * 28, "hck_GPT — Your Usage Profile", "━" * 28, ""]

        today = datetime.now().strftime("%Y-%m-%d")
        today_procs = self._get_daily_breakdown(today, top_n=10)

        if today_procs:
            classified = self._classify_processes(today_procs)
            lines.append("Today's top apps:")
            for i, proc in enumerate(today_procs[:5], 1):
                name = proc.get("display_name", proc.get("process_name", "?"))
                cpu = proc.get("cpu_avg", 0)
                secs = proc.get("total_active_seconds", proc.get("active_seconds", 0))
                lines.append(f"  {i}. {name} — CPU {cpu:.1f}%, active {self._format_duration(secs)}")

            lines.append("")
            if classified["browsers"]:
                b = classified["browsers"][0]
                lines.append(f"Browser: {b.get('display_name', b['name'])} "
                             f"({b.get('ram_avg_mb', 0):.0f}MB avg RAM)")
            if classified["games"]:
                g = classified["games"][0]
                lines.append(f"Game: {g.get('display_name', g['name'])} "
                             f"(CPU {g.get('cpu_avg', 0):.1f}%)")
            if classified["dev_tools"]:
                d = classified["dev_tools"][0]
                lines.append(f"Dev: {d.get('display_name', d['name'])}")
        else:
            lines += ["Not enough data yet — keep the app running!",
                      "Process stats accumulate over hours."]

        this_week = self._get_summary(days=7)
        last_week = self._get_summary(days=14)
        lines.append("")
        if (this_week and last_week
                and this_week.get("cpu_avg") and last_week.get("cpu_avg")):
            diff = this_week["cpu_avg"] - last_week["cpu_avg"]
            if abs(diff) > 3:
                direction = "heavier" if diff > 0 else "lighter"
                lines.append(f"Weekly trend: {direction} usage than last week "
                             f"(CPU {this_week['cpu_avg']:.0f}% vs {last_week['cpu_avg']:.0f}%)")
            else:
                lines.append(f"Weekly: stable usage (CPU avg ~{this_week['cpu_avg']:.0f}%)")

        patterns = self._detect_recurring_patterns(days=7)
        if patterns:
            lines += ["", "Your regulars (last 7 days):"]
            for p in patterns[:3]:
                lines.append(f"   {p['display_name']} — {p['frequency']}/7 days, "
                             f"CPU ~{p['avg_cpu']:.0f}%")

        lines += ["", "━" * 28]
        return lines

    # ── Anomaly report ────────────────────────────────────────────────

    def get_anomaly_report(self) -> list[str]:
        self._ensure_loaded()
        lines = ["━" * 28, "hck_GPT — Anomaly Report (24h)", "━" * 28, ""]

        if not self._query_api:
            lines.append("Stats engine not available.")
            return lines

        try:
            now = time.time()
            events = self._query_api.get_events(
                start_ts=now - 86400, end_ts=now, limit=20
            )

            if not events:
                lines += ["No anomalies in the last 24 hours.",
                          "Your system has been stable.",
                          "", "━" * 28]
                return lines

            counts: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
            for e in events:
                sev = e.get("severity", "info")
                if sev in counts:
                    counts[sev] += 1

            total = sum(counts.values())
            parts = [f"{v} {k}" for k, v in counts.items() if v]
            lines += [f"Total events: {total} ({', '.join(parts)})", "", "Recent events:"]

            for e in events[:5]:
                ts = e.get("timestamp", 0)
                t = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "??:??"
                sev = e.get("severity", "?")
                desc = e.get("description", "Unknown event")[:57]
                icon = "!" if sev == "critical" else "^" if sev == "warning" else "i"
                lines.append(f"  [{icon}] [{t}] {desc}")

            if counts["critical"] > 2:
                lines += ["", "Multiple critical events — check your cooling and load."]
            elif total > 10:
                lines += ["", "High event count — your system was under pressure."]

        except Exception as ex:
            lines.append(f"Error reading events: {ex}")

        lines += ["", "━" * 28]
        return lines

    # ── Teaser ────────────────────────────────────────────────────────

    def _build_teaser(self) -> str | None:
        patterns = self._detect_recurring_patterns(days=7)
        if not patterns:
            return None
        top = patterns[0]
        name = top["display_name"]
        freq = top["frequency"]
        cpu = top.get("avg_cpu", 0)
        ram = top.get("avg_ram", 0)
        category = top.get("category", "")
        templates = self._teaser_templates.get(category, self._teaser_templates["_default"])
        try:
            return random.choice(templates).format(name=name, freq=freq, cpu=cpu, ram=ram)
        except (KeyError, ValueError):
            return f"{name} — you use it {freq}/7 days."

    def get_teaser(self) -> list[str]:
        self._ensure_loaded()
        teaser = self._build_teaser()
        if teaser:
            return [f"hck_GPT: {teaser}"]
        return [
            "hck_GPT: Not enough usage data to detect your habits yet.",
            "hck_GPT: Keep the app running — I learn from your patterns.",
        ]

    # ── Banner status (cached 30s) ─────────────────────────────────────

    def get_banner_status(self) -> str:
        now = time.time()
        if self._banner_cache and (now - self._banner_cache_ts) < _BANNER_TTL:
            return self._banner_cache

        self._ensure_loaded()
        parts: list[str] = []

        if self._process_aggregator:
            try:
                top = [p for p in self._process_aggregator.get_current_hour_top(5)
                       if not self._is_system_noise(p.get("name", ""))]
                if top:
                    classified = self._classify_processes(top[:1])
                    if classified["games"]:
                        parts.append(f"{classified['games'][0].get('display_name', '?')} running")
                    elif classified["browsers"]:
                        b = classified["browsers"][0]
                        if b.get("ram_avg_mb", 0) > 300:
                            parts.append(f"{b.get('display_name', '?')} {b['ram_avg_mb']:.0f}MB")
            except Exception:
                pass

        if self._event_detector:
            try:
                alerts = self._event_detector.get_active_alerts_count()
                total = alerts.get("total", 0)
                if total > 0:
                    crit = alerts.get("critical", 0)
                    parts.append(f"{crit} critical" if crit else
                                 f"{total} alert{'s' if total > 1 else ''}")
            except Exception:
                pass

        if not parts:
            parts.append(f"Session: {self._format_duration(self.get_session_uptime())}")

        result = " | ".join(parts)
        self._banner_cache = result
        self._banner_cache_ts = now
        return result

    # ── Helpers ───────────────────────────────────────────────────────

    def _get_daily_breakdown(self, date_str: str, top_n: int = 10) -> list:
        if not self._query_api:
            return []
        try:
            return self._query_api.get_process_daily_breakdown(date_str, top_n)
        except Exception:
            return []

    def _get_summary(self, days: int = 7) -> dict:
        """Cached per days-value, TTL 2 min."""
        now = time.time()
        cached = self._summary_cache.get(days)
        if cached and (now - cached[0]) < _SUMMARY_TTL:
            return cached[1]
        if not self._query_api:
            return {}
        try:
            result = self._query_api.get_summary_stats(days)
        except Exception:
            result = {}
        self._summary_cache[days] = (now, result)
        return result

    def _classify_processes(self, processes: list) -> dict[str, list]:
        result: dict[str, list] = {"games": [], "browsers": [], "dev_tools": [], "other": []}
        for proc in processes:
            name = proc.get("process_name", proc.get("name", ""))
            category = proc.get("category", "")
            proc_type = proc.get("process_type", "")
            if not category and self._classifier:
                try:
                    info = self._classifier.classify_process(name)
                    category = info.get("category", "")
                    proc_type = info.get("type", "")
                    if not proc.get("display_name"):
                        proc["display_name"] = info.get("display_name", name)
                except Exception:
                    pass
            if category == "Gaming" or proc_type == "gaming":
                result["games"].append(proc)
            elif category == "Browser" or proc_type == "browser":
                result["browsers"].append(proc)
            elif category == "Development":
                result["dev_tools"].append(proc)
            else:
                result["other"].append(proc)
        return result

    def _detect_recurring_patterns(self, days: int = 7) -> list:
        """5-min cache — SQLite scan across N days is expensive."""
        now = time.time()
        if self._pattern_cache is not None and (now - self._pattern_cache_ts) < _PATTERN_TTL:
            return self._pattern_cache

        if not self._query_api:
            return []

        try:
            process_days: dict[str, dict] = {}
            for offset in range(days):
                date = (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
                for p in self._get_daily_breakdown(date, top_n=20):
                    name = p.get("process_name", "")
                    if not name or p.get("process_type") == "system":
                        continue
                    cpu = p.get("cpu_avg", 0)
                    ram = p.get("ram_avg_mb", 0)
                    if cpu < 5 and ram < 100:
                        continue
                    if name not in process_days:
                        process_days[name] = {
                            "days_seen": set(),
                            "total_cpu": 0,
                            "total_ram": 0,
                            "display_name": p.get("display_name", name),
                            "category": p.get("category", ""),
                        }
                    process_days[name]["days_seen"].add(date)
                    process_days[name]["total_cpu"] += cpu
                    process_days[name]["total_ram"] += ram

            min_days = max(3, days // 2)
            results = []
            for name, data in process_days.items():
                freq = len(data["days_seen"])
                if freq < min_days:
                    continue
                results.append({
                    "name": name,
                    "display_name": data["display_name"],
                    "category": data["category"],
                    "frequency": freq,
                    "avg_cpu": round(data["total_cpu"] / freq, 1),
                    "avg_ram": round(data["total_ram"] / freq, 1),
                })
            results.sort(key=lambda x: (x["frequency"], x["avg_cpu"]), reverse=True)

            self._pattern_cache = results
            self._pattern_cache_ts = now
            return results

        except Exception:
            traceback.print_exc()
            return []

    def _format_duration(self, seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}s"
        if seconds < 3600:
            return f"{int(seconds // 60)}min"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}min" if m else f"{h}h"


# Singleton
insights_engine = InsightsEngine()
