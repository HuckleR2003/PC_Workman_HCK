# hck_gpt/insights.py
"""
InsightsEngine — Local intelligence for hck_GPT.
Reads Stats Engine v2 data (SQLite) and generates contextual messages,
habit tracking, anomaly reports, and personality-driven teasers.
No external AI — all rule-based logic.
"""

import time
import random
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

        # Session tracking
        self._session_start = time.time()

        # Caches
        self._last_greeting_time = 0
        self._last_greeting_text = None
        self._last_insight_time = 0
        self._last_insight_msg = None  # Dedup: don't repeat same insight

        # Teaser templates (variety)
        self._teaser_templates = {
            "Gaming": [
                "Ready for another round of {name}? Your GPU is warmed up. 🎮",
                "{name} again? Let's see if your CPU can keep up today. 🎮",
                "Your PC is expecting {name} — it's been {freq}/7 days. 🎮",
                "{name} incoming? Average CPU hit: {cpu:.0f}%. Game on. 🎮",
            ],
            "Browser": [
                "{name} again? Your RAM knows the drill. 🌐",
                "Round {freq} of {name} this week. Classic. 🌐",
                "{name} — your RAM's favorite customer. ~{ram:.0f}MB daily. 🌐",
                "Tabs are calling! {name} has been active {freq}/7 days. 🌐",
            ],
            "Development": [
                "Back to {name}? Let's see what you build today. 💻",
                "{name} — {freq}/7 days. Productivity mode activated. 💻",
                "Time to code? {name} is your daily driver. 💻",
            ],
            "Communication": [
                "{name} calling — you use it almost every day. 💬",
                "{name} — {freq}/7 days. Staying connected. 💬",
            ],
            "Media": [
                "{name} time? {freq}/7 days and counting. 🎵",
                "{name} — part of your daily routine now. 🎵",
            ],
            "_default": [
                "{name} — {freq}/7 days. It's basically part of your system now.",
                "You've been using {name} regularly. CPU avg: {cpu:.0f}%.",
            ],
        }

    # ================================================================
    # SESSION
    # ================================================================
    def get_session_uptime(self):
        """Returns current session uptime in seconds."""
        return time.time() - self._session_start

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

        # Session uptime context
        session_h = self.get_session_uptime() / 3600
        if session_h > 4:
            lines.append(f"hck_GPT: You've been running for {session_h:.1f}h this session. Stay hydrated!")

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
        Rate-limited to once per 30 seconds. Won't repeat same message.
        """
        now = time.time()
        if (now - self._last_insight_time) < 30:
            return None

        self._ensure_loaded()
        self._last_insight_time = now

        # Priority 1: Recent spike events (last 5 min)
        spike_msg = self._check_recent_spikes(minutes=5)
        if spike_msg and spike_msg != self._last_insight_msg:
            self._last_insight_msg = spike_msg
            return spike_msg

        # Priority 2: Heavy process running right now
        live_msg = self._check_live_processes()
        if live_msg and live_msg != self._last_insight_msg:
            self._last_insight_msg = live_msg
            return live_msg

        # Priority 3: Session milestone
        session_msg = self._check_session_milestone()
        if session_msg and session_msg != self._last_insight_msg:
            self._last_insight_msg = session_msg
            return session_msg

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
            top = self._process_aggregator.get_current_hour_top(10)
            if not top:
                return None

            # Filter out system/idle processes and cap CPU at 100%
            filtered = []
            for proc in top:
                name = proc.get("name", "").lower()
                # Skip system idle process and other OS noise
                if self._is_system_noise(name):
                    continue
                # Cap CPU at 100% (psutil can report per-core values)
                if proc.get("cpu_avg", 0) > 100:
                    proc["cpu_avg"] = min(proc["cpu_avg"], 100.0)
                if proc.get("cpu_max", 0) > 100:
                    proc["cpu_max"] = min(proc["cpu_max"], 100.0)
                filtered.append(proc)

            if not filtered:
                return None

            classified = self._classify_processes(filtered)

            # Game running?
            if classified["games"]:
                g = classified["games"][0]
                name = g.get("display_name", g["name"])
                cpu = g.get("cpu_avg", 0)
                ram = g.get("ram_avg_mb", 0)
                msgs = [
                    f"hck_GPT: {name} is running — CPU {cpu:.0f}%. Game on.",
                    f"hck_GPT: {name} active — CPU {cpu:.0f}%, RAM {ram:.0f}MB.",
                    f"hck_GPT: Gaming detected: {name} @ CPU {cpu:.0f}%.",
                ]
                return random.choice(msgs)

            # Heavy browser?
            if classified["browsers"]:
                b = classified["browsers"][0]
                name = b.get("display_name", b["name"])
                ram = b.get("ram_avg_mb", 0)
                if ram > 500:
                    msgs = [
                        f"hck_GPT: {name} is using {ram:.0f}MB RAM. Classic browser appetite.",
                        f"hck_GPT: {name} — {ram:.0f}MB RAM. Tabs adding up?",
                    ]
                    return random.choice(msgs)

            # Heavy dev tool?
            if classified["dev_tools"]:
                d = classified["dev_tools"][0]
                name = d.get("display_name", d["name"])
                cpu = d.get("cpu_avg", 0)
                if cpu > 15:
                    return f"hck_GPT: {name} is working hard — CPU {cpu:.0f}%."

            # Heavy unknown app (>30% CPU) — only non-system processes
            for proc in filtered[:3]:
                cpu = proc.get("cpu_avg", 0)
                ptype = proc.get("process_type", "")
                if cpu > 30 and ptype != "system":
                    name = proc.get("display_name", proc.get("name", "?"))
                    return f"hck_GPT: {name} is pushing CPU to {cpu:.0f}%."

            return None
        except Exception:
            return None

    @staticmethod
    def _is_system_noise(name):
        """Check if a process name is system noise that should be ignored."""
        noise = {
            "system idle process", "idle", "system",
            "registry", "memory compression", "secure system",
            "system interrupts", "ntoskrnl", "wininit",
            "csrss", "smss", "lsass", "services",
        }
        name_lower = name.lower().strip()
        if name_lower in noise:
            return True
        # Also catch partial matches for idle-like processes
        if "idle" in name_lower:
            return True
        return False

    def _check_session_milestone(self):
        """Session duration milestones."""
        hours = self.get_session_uptime() / 3600

        # Only trigger at specific milestones (with 2 min window)
        milestones = {
            1: "1 hour in! Your system is running smooth.",
            2: "2 hours of monitoring. Everything logged.",
            4: "4 hours! That's a solid session.",
            8: "8 hours of uptime — marathon session!",
            12: "12 hours. Your PC is a trooper.",
        }

        for milestone_h, msg in milestones.items():
            if milestone_h <= hours < milestone_h + (2 / 60):  # 2 min window
                return f"hck_GPT: ⏱ {msg}"

        return None

    # ================================================================
    # HEALTH CHECK (quick status)
    # ================================================================
    def get_health_check(self):
        """Quick system health check. Returns list of chat messages."""
        self._ensure_loaded()
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🩺 hck_GPT — Quick Health Check",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]

        # Session info
        session_str = self._format_duration(self.get_session_uptime())
        lines.append(f"⏱ Session uptime: {session_str}")

        # Current load from live accumulator
        if self._process_aggregator:
            try:
                top = self._process_aggregator.get_current_hour_top(10)
                # Filter system noise
                top = [p for p in top if not self._is_system_noise(p.get("name", ""))]
                for p in top:
                    if p.get("cpu_avg", 0) > 100:
                        p["cpu_avg"] = 100.0
                if top:
                    top3 = top[:3]
                    total_cpu = sum(min(p.get("cpu_avg", 0), 100) for p in top3)
                    total_ram = sum(p.get("ram_avg_mb", 0) for p in top3)
                    lines.append(f"💪 Top 3 load: CPU ~{total_cpu:.0f}%, RAM ~{total_ram:.0f}MB")

                    heaviest = top3[0]
                    h_name = heaviest.get("display_name", heaviest.get("name", "?"))
                    lines.append(f"   Heaviest: {h_name} ({heaviest.get('cpu_avg', 0):.1f}% CPU)")
            except Exception:
                pass

        # Today's summary
        summary = self._get_summary(days=1)
        if summary and summary.get("cpu_avg"):
            lines.append("")
            lines.append(f"📊 Today avg: CPU {summary['cpu_avg']:.0f}% | "
                         f"RAM {summary.get('ram_avg', 0):.0f}% | "
                         f"GPU {summary.get('gpu_avg', 0):.0f}%")

            cpu_max = summary.get("cpu_max", 0)
            if cpu_max > 85:
                lines.append(f"   ⚠️ Peak CPU: {cpu_max:.0f}% — that's high!")
            elif cpu_max > 0:
                lines.append(f"   Peak CPU: {cpu_max:.0f}%")

        # Alerts
        if self._event_detector:
            try:
                alerts = self._event_detector.get_active_alerts_count()
                total = alerts.get("total", 0)
                if total == 0:
                    lines.append("")
                    lines.append("✅ No active alerts — system is healthy")
                else:
                    crit = alerts.get("critical", 0)
                    warn = alerts.get("warning", 0)
                    lines.append("")
                    parts = []
                    if crit:
                        parts.append(f"🔴 {crit} critical")
                    if warn:
                        parts.append(f"⚠️ {warn} warnings")
                    lines.append(f"Active alerts: {', '.join(parts)}")
            except Exception:
                pass

        # Data collection status
        if self._query_api:
            try:
                date_range = self._query_api.get_available_date_range()
                if date_range:
                    days = date_range.get("total_days", 0)
                    lines.append("")
                    lines.append(f"📅 Data collected: {days} day{'s' if days != 1 else ''} "
                                 f"(since {date_range.get('earliest_date', '?')})")
                else:
                    lines.append("")
                    lines.append("📅 Data collection: just started — give it time")
            except Exception:
                pass

        lines.extend(["", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"])
        return lines

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
            else:
                lines.append(f"📈 Weekly: stable usage (CPU avg ~{this_week['cpu_avg']:.0f}%)")

        # Recurring patterns
        patterns = self._detect_recurring_patterns(days=7)
        if patterns:
            lines.append("")
            lines.append("🔄 Your regulars (last 7 days):")
            for p in patterns[:3]:
                lines.append(f"   {p['display_name']} — {p['frequency']}/7 days, "
                             f"CPU ~{p['avg_cpu']:.0f}%")

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
                # Truncate long descriptions
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                lines.append(f"  {icon} [{time_str}] {desc}")

            # Summary insight
            if counts["critical"] > 2:
                lines.append("")
                lines.append("⚠️ Multiple critical events — check your cooling and load.")
            elif total > 10:
                lines.append("")
                lines.append("📊 High event count — your system was under pressure.")

        except Exception as ex:
            lines.append(f"Error reading events: {ex}")

        lines.extend(["", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"])
        return lines

    # ================================================================
    # TEASER (personality-driven, with variety)
    # ================================================================
    def _build_teaser(self):
        """Build a personality-driven teaser based on 7-day recurring patterns.
        Returns a single string or None. Uses template variety.
        """
        patterns = self._detect_recurring_patterns(days=7)
        if not patterns:
            return None

        top = patterns[0]
        name = top["display_name"]
        category = top.get("category", "")
        freq = top["frequency"]
        cpu = top.get("avg_cpu", 0)
        ram = top.get("avg_ram", 0)

        # Pick template category
        templates = self._teaser_templates.get(category,
                    self._teaser_templates["_default"])

        template = random.choice(templates)
        try:
            return template.format(name=name, freq=freq, cpu=cpu, ram=ram)
        except (KeyError, ValueError):
            return f"{name} — you use it {freq}/7 days."

    def get_teaser(self):
        """Public teaser method. Returns list of messages."""
        self._ensure_loaded()
        teaser = self._build_teaser()
        if teaser:
            return [f"hck_GPT: {teaser}"]
        return ["hck_GPT: Not enough usage data to detect your habits yet.",
                "hck_GPT: Keep the app running — I learn from your usage patterns."]

    # ================================================================
    # BANNER STATUS (compact one-liner)
    # ================================================================
    def get_banner_status(self):
        """Short status string for the panel banner.
        Returns string like 'Battlefield running | 2 alerts' or 'System monitored'
        """
        self._ensure_loaded()

        parts = []

        # Live process info
        if self._process_aggregator:
            try:
                top = self._process_aggregator.get_current_hour_top(5)
                top = [p for p in top if not self._is_system_noise(p.get("name", ""))]
                if top:
                    classified = self._classify_processes(top[:1])
                    if classified["games"]:
                        g = classified["games"][0]
                        name = g.get("display_name", g["name"])
                        parts.append(f"{name} running")
                    elif classified["browsers"]:
                        b = classified["browsers"][0]
                        ram = b.get("ram_avg_mb", 0)
                        if ram > 300:
                            name = b.get("display_name", b["name"])
                            parts.append(f"{name} {ram:.0f}MB")
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
                        parts.append(f"{crit} critical")
                    else:
                        parts.append(f"{total} alert{'s' if total > 1 else ''}")
            except Exception:
                pass

        if not parts:
            # Fallback: show session uptime
            uptime = self._format_duration(self.get_session_uptime())
            parts.append(f"Session: {uptime}")

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
            process_days = {}

            for offset in range(days):
                date = (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
                procs = self._get_daily_breakdown(date, top_n=20)

                for p in procs:
                    name = p.get("process_name", "")
                    if not name:
                        continue
                    ptype = p.get("process_type", "")
                    if ptype == "system":
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
