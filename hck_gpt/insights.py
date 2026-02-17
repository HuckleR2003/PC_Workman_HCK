# hck_gpt/insights.py
"""
InsightsEngine — Local intelligence for hck_GPT.
Reads Stats Engine v2 data (SQLite) and generates contextual messages,
habit tracking, anomaly reports, and personality-driven teasers.
No external AI — all rule-based logic.
"""

import time
import traceback
from datetime import datetime, timedelta


class InsightsEngine:
    """Gathers stats data and generates contextual, personalized messages."""

    def __init__(self):
        self._query_api = None
        self._event_detector = None
        self._process_aggregator = None
        self._classifier = None
        self._loaded = False

        # Caches
        self._last_greeting_time = 0
        self._last_greeting_text = None
        self._last_insight_time = 0
        self._last_insight_text = None

    # ================================================================
    # LAZY LOADING
    # ================================================================
    def _ensure_loaded(self):
        """Lazy-load stats engine singletons (safe if unavailable)."""
        if self._loaded:
            return
        self._loaded = True
        try:
            from hck_stats_engine.query_api import query_api
            self._query_api = query_api
        except Exception:
            pass
        try:
            from hck_stats_engine.events import event_detector
            self._event_detector = event_detector
        except Exception:
            pass
        try:
            from hck_stats_engine.process_aggregator import process_aggregator
            self._process_aggregator = process_aggregator
        except Exception:
            pass
        try:
            from core.process_classifier import classifier
            self._classifier = classifier
        except Exception:
            pass

    # ================================================================
    # GREETING
    # ================================================================
    def get_greeting(self):
        """Personalized greeting based on time, day, and recent stats.
        Returns list of strings (chat messages).
        Cached for 30 minutes.
        """
        now = time.time()
        if self._last_greeting_text and (now - self._last_greeting_time) < 1800:
            return self._last_greeting_text

        self._ensure_loaded()
        lines = []

        # Time of day
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

        # Weekend?
        weekday = datetime.now().weekday()
        if weekday >= 5:
            time_greet += f" Relaxing {day_name}?"

        lines.append(f"hck_GPT: {time_greet}")

        # Yesterday's summary
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_procs = self._get_daily_breakdown(yesterday, top_n=3)
        summary = self._get_summary(days=1)

        if summary and summary.get("cpu_avg"):
            cpu_avg = summary["cpu_avg"]
            qualifier = "light" if cpu_avg < 30 else "moderate" if cpu_avg < 60 else "heavy"
            line = f"hck_GPT: Yesterday was a {qualifier} day — CPU averaged {cpu_avg:.0f}%"

            # Top culprit
            if yesterday_procs:
                top = yesterday_procs[0]
                name = top.get("display_name", top.get("process_name", "?"))
                line += f", {name} was the main culprit."
            else:
                line += "."
            lines.append(line)

        # Teaser
        teaser = self._build_teaser()
        if teaser:
            lines.append(f"hck_GPT: {teaser}")

        if not lines:
            lines.append("hck_GPT: Welcome back! I'm monitoring your system.")

        self._last_greeting_time = now
        self._last_greeting_text = lines
        return lines

    # ================================================================
    # CURRENT INSIGHT (periodic)
    # ================================================================
    def get_current_insight(self):
        """One contextual message about what's happening right now.
        Returns a single string or None if nothing notable.
        Rate-limited to once per 30 seconds.
        """
        now = time.time()
        if (now - self._last_insight_time) < 30:
            return None

        self._ensure_loaded()
        self._last_insight_time = now

        # Priority 1: Recent spike events (last 5 min)
        spike_msg = self._check_recent_spikes(minutes=5)
        if spike_msg:
            return spike_msg

        # Priority 2: Heavy process running right now
        live_msg = self._check_live_processes()
        if live_msg:
            return live_msg

        # Priority 3: General status
        return None  # Nothing notable — stay quiet

    def _check_recent_spikes(self, minutes=5):
        """Check for spike events in the last N minutes."""
        if not self._query_api:
            return None
        try:
            now = time.time()
            events = self._query_api.get_events(
                start_ts=now - (minutes * 60),
                end_ts=now,
                event_type="spike",
                limit=3
            )
            if not events:
                return None

            e = events[0]
            severity = e.get("severity", "info")
            metric = e.get("metric", "?")
            value = e.get("value", 0)
            baseline = e.get("baseline", 0)

            metric_label = {
                "cpu": "CPU", "ram": "RAM", "gpu": "GPU",
                "cpu_temp": "CPU temp", "gpu_temp": "GPU temp"
            }.get(metric, metric.upper())

            icon = "🔴" if severity == "critical" else "⚠️" if severity == "warning" else "ℹ️"

            if baseline:
                delta = value - baseline
                return (f"hck_GPT: {icon} {metric_label} spike — "
                        f"{value:.0f}% (+{delta:.0f} above baseline {baseline:.0f}%)")
            else:
                return f"hck_GPT: {icon} {metric_label} spike detected — {value:.0f}%"
        except Exception:
            return None

    def _check_live_processes(self):
        """Check what's running right now from in-memory process accumulator."""
        if not self._process_aggregator:
            return None
        try:
            top = self._process_aggregator.get_current_hour_top(5)
            if not top:
                return None

            classified = self._classify_processes(top)

            # Game running?
            if classified["games"]:
                g = classified["games"][0]
                name = g.get("display_name", g["name"])
                cpu = g.get("cpu_avg", 0)
                return (f"hck_GPT: {name} is running — "
                        f"CPU {cpu:.0f}%. Game on.")

            # Heavy browser?
            if classified["browsers"]:
                b = classified["browsers"][0]
                name = b.get("display_name", b["name"])
                ram = b.get("ram_avg_mb", 0)
                if ram > 500:
                    return (f"hck_GPT: {name} is using {ram:.0f}MB RAM. "
                            f"Classic browser appetite.")

            # Heavy dev tool?
            if classified["dev_tools"]:
                d = classified["dev_tools"][0]
                name = d.get("display_name", d["name"])
                cpu = d.get("cpu_avg", 0)
                if cpu > 15:
                    return f"hck_GPT: {name} is working hard — CPU {cpu:.0f}%."

            return None
        except Exception:
            return None

    # ================================================================
    # HABIT SUMMARY
    # ================================================================
    def get_habit_summary(self):
        """Detailed summary of user habits. Returns list of chat messages."""
        self._ensure_loaded()
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 hck_GPT — Your Usage Profile",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]

        # Today's top processes
        today = datetime.now().strftime("%Y-%m-%d")
        today_procs = self._get_daily_breakdown(today, top_n=10)

        if today_procs:
            classified = self._classify_processes(today_procs)

            lines.append("Today's top apps:")
            for i, proc in enumerate(today_procs[:5], 1):
                name = proc.get("display_name", proc.get("process_name", "?"))
                cpu = proc.get("cpu_avg", 0)
                secs = proc.get("total_active_seconds", proc.get("active_seconds", 0))
                time_str = self._format_duration(secs)
                lines.append(f"  {i}. {name} — CPU {cpu:.1f}%, active {time_str}")

            lines.append("")

            # Browser summary
            if classified["browsers"]:
                b = classified["browsers"][0]
                name = b.get("display_name", b["name"])
                ram = b.get("ram_avg_mb", 0)
                lines.append(f"🌐 Browser: {name} ({ram:.0f}MB avg RAM)")

            # Game summary
            if classified["games"]:
                g = classified["games"][0]
                name = g.get("display_name", g["name"])
                cpu = g.get("cpu_avg", 0)
                lines.append(f"🎮 Game: {name} (CPU {cpu:.1f}%)")

            # Dev tools
            if classified["dev_tools"]:
                d = classified["dev_tools"][0]
                name = d.get("display_name", d["name"])
                lines.append(f"💻 Dev: {name}")
        else:
            lines.append("Not enough data yet — keep the app running!")
            lines.append("Process stats accumulate over hours.")

        # Weekly trend
        lines.append("")
        this_week = self._get_summary(days=7)
        last_week = self._get_summary(days=14)

        if this_week and last_week and this_week.get("cpu_avg") and last_week.get("cpu_avg"):
            diff = this_week["cpu_avg"] - last_week["cpu_avg"]
            if abs(diff) > 3:
                direction = "heavier" if diff > 0 else "lighter"
                lines.append(f"📈 Weekly trend: {direction} usage than last week "
                             f"(CPU avg {this_week['cpu_avg']:.0f}% vs {last_week['cpu_avg']:.0f}%)")

        lines.extend(["", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"])
        return lines

    # ================================================================
    # ANOMALY REPORT
    # ================================================================
    def get_anomaly_report(self):
        """Recent anomalies summary. Returns list of chat messages."""
        self._ensure_loaded()
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🔍 hck_GPT — Anomaly Report (24h)",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]

        if not self._query_api:
            lines.append("Stats engine not available.")
            return lines

        try:
            now = time.time()
            events = self._query_api.get_events(
                start_ts=now - 86400,
                end_ts=now,
                limit=20
            )

            if not events:
                lines.append("No anomalies in the last 24 hours.")
                lines.append("Your system has been stable. ✅")
                lines.extend(["", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"])
                return lines

            # Count by severity
            counts = {"critical": 0, "warning": 0, "info": 0}
            for e in events:
                sev = e.get("severity", "info")
                if sev in counts:
                    counts[sev] += 1

            total = sum(counts.values())
            parts = []
            if counts["critical"]:
                parts.append(f"{counts['critical']} critical")
            if counts["warning"]:
                parts.append(f"{counts['warning']} warning")
            if counts["info"]:
                parts.append(f"{counts['info']} info")

            lines.append(f"Total events: {total} ({', '.join(parts)})")
            lines.append("")

            # Show latest 5 events
            lines.append("Recent events:")
            for e in events[:5]:
                ts = e.get("timestamp", 0)
                time_str = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "??:??"
                severity = e.get("severity", "?")
                desc = e.get("description", "Unknown event")

                icon = "🔴" if severity == "critical" else "⚠️" if severity == "warning" else "ℹ️"
                lines.append(f"  {icon} [{time_str}] {desc}")

        except Exception as ex:
            lines.append(f"Error reading events: {ex}")

        lines.extend(["", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"])
        return lines

    # ================================================================
    # TEASER (personality-driven)
    # ================================================================
    def _build_teaser(self):
        """Build a personality-driven teaser based on 7-day recurring patterns.
        Returns a single string or None.
        """
        patterns = self._detect_recurring_patterns(days=7)
        if not patterns:
            return None

        # Find the most frequent recurring app
        top = patterns[0]
        name = top["display_name"]
        category = top.get("category", "")
        freq = top["frequency"]

        if category == "Gaming":
            return f"Ready for another round of {name}? Your GPU is warmed up. 🎮"
        elif category == "Browser":
            return f"{name} again? Your RAM knows the drill. 🌐"
        elif category == "Development":
            return f"Back to {name}? Let's see what you build today. 💻"
        elif category == "Communication":
            return f"{name} calling — you use it almost every day."
        elif category == "Media":
            return f"{name} time? You've been on it {freq} of the last 7 days."
        elif freq >= 5:
            return f"{name} — {freq}/7 days. It's basically part of your system now."

        return None

    def get_teaser(self):
        """Public teaser method. Returns list of messages."""
        self._ensure_loaded()
        teaser = self._build_teaser()
        if teaser:
            return [f"hck_GPT: {teaser}"]
        return ["hck_GPT: Not enough usage data to detect your habits yet."]

    # ================================================================
    # BANNER STATUS (compact one-liner)
    # ================================================================
    def get_banner_status(self):
        """Short status string for the panel banner.
        Returns string like 'CPU 12% | RAM 45% | All quiet'
        """
        self._ensure_loaded()

        parts = []

        # Live process info
        if self._process_aggregator:
            try:
                top = self._process_aggregator.get_current_hour_top(1)
                if top:
                    classified = self._classify_processes(top)
                    if classified["games"]:
                        g = classified["games"][0]
                        name = g.get("display_name", g["name"])
                        parts.append(f"{name} running")
            except Exception:
                pass

        # Active alerts
        if self._event_detector:
            try:
                alerts = self._event_detector.get_active_alerts_count()
                total = alerts.get("total", 0)
                if total > 0:
                    crit = alerts.get("critical", 0)
                    if crit > 0:
                        parts.append(f"{crit} critical alert{'s' if crit > 1 else ''}")
                    else:
                        parts.append(f"{total} alert{'s' if total > 1 else ''}")
            except Exception:
                pass

        if not parts:
            parts.append("System monitored")

        return " | ".join(parts)

    # ================================================================
    # HELPERS
    # ================================================================
    def _get_daily_breakdown(self, date_str, top_n=10):
        """Get process breakdown for a day via query_api."""
        if not self._query_api:
            return []
        try:
            return self._query_api.get_process_daily_breakdown(date_str, top_n)
        except Exception:
            return []

    def _get_summary(self, days=7):
        """Get summary stats via query_api."""
        if not self._query_api:
            return {}
        try:
            return self._query_api.get_summary_stats(days)
        except Exception:
            return {}

    def _classify_processes(self, processes_list):
        """Group processes into games, browsers, dev_tools, other."""
        result = {"games": [], "browsers": [], "dev_tools": [], "other": []}

        for proc in processes_list:
            name = proc.get("process_name", proc.get("name", ""))
            category = proc.get("category", "")
            proc_type = proc.get("process_type", "")

            # Use classifier if category not already set
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

    def _detect_recurring_patterns(self, days=7):
        """Find processes that appear frequently over the last N days.
        Returns sorted list of {name, display_name, category, frequency, avg_cpu, avg_ram}.
        """
        if not self._query_api:
            return []

        try:
            # Collect per-day breakdowns
            process_days = {}  # {process_name: {days_seen, total_cpu, total_ram, display_name, category}}

            for offset in range(days):
                date = (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
                procs = self._get_daily_breakdown(date, top_n=20)

                for p in procs:
                    name = p.get("process_name", "")
                    if not name:
                        continue
                    # Skip system processes
                    ptype = p.get("process_type", "")
                    if ptype == "system":
                        continue

                    cpu = p.get("cpu_avg", 0)
                    ram = p.get("ram_avg_mb", 0)

                    # Minimum threshold: >5% CPU or >100MB RAM
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

            # Filter: must appear on at least 50% of days (min 3 days for 7-day window)
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

            # Sort by frequency desc, then by avg_cpu desc
            results.sort(key=lambda x: (x["frequency"], x["avg_cpu"]), reverse=True)
            return results

        except Exception:
            traceback.print_exc()
            return []

    def _format_duration(self, seconds):
        """Format seconds into human-readable duration."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}min"
        else:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h}h {m}min" if m else f"{h}h"


# Singleton
insights_engine = InsightsEngine()
