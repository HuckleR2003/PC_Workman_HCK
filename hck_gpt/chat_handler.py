# hck_gpt/chat_handler.py
"""
Chat Handler
Main logic for hck_GPT chat interactions and command processing.
Routes user messages to service wizard, insights engine, or default response.
"""

from .service_setup_wizard import ServiceSetupWizard
from .services_manager import ServicesManager

try:
    from .insights import InsightsEngine
    HAS_INSIGHTS = True
except ImportError:
    HAS_INSIGHTS = False


class ChatHandler:
    """Handles chat messages and commands for hck_GPT"""

    def __init__(self):
        self.wizard = ServiceSetupWizard()
        self.services_manager = ServicesManager()
        self.conversation_history = []
        self.insights = InsightsEngine() if HAS_INSIGHTS else None

    def process_message(self, user_message):
        """
        Process user message and return response

        Args:
            user_message: String message from user

        Returns:
            list: Response messages to display
        """
        user_message = user_message.strip()

        # If wizard is active, route to wizard
        if self.wizard.is_active():
            return self.wizard.process_input(user_message)

        # Process commands
        message_lower = user_message.lower()

        # Service Setup command
        if any(cmd in message_lower for cmd in ["service setup", "service's setup", "setup services"]):
            return self.wizard.start()

        # Restore services command
        elif any(cmd in message_lower for cmd in ["restore services", "enable services", "restore all"]):
            return self._restore_services()

        # Service status command
        elif any(cmd in message_lower for cmd in ["service status", "services status", "show services"]):
            return self._show_service_status()

        # --- Insights commands ---

        # Stats / habits
        elif any(cmd in message_lower for cmd in [
            "stats", "habits", "top apps", "usage", "co uzywam",
            "statystyki", "nawyki"
        ]):
            return self._insights_habits()

        # Anomalies / alerts
        elif any(cmd in message_lower for cmd in [
            "alerts", "anomalies", "spikes", "anomalie", "alerty"
        ]):
            return self._insights_anomalies()

        # Current insight
        elif any(cmd in message_lower for cmd in [
            "insights", "what's up", "whats up", "co nowego",
            "status", "co sie dzieje"
        ]):
            return self._insights_current()

        # Teaser
        elif any(cmd in message_lower for cmd in [
            "teaser", "predict", "guess", "co dzis"
        ]):
            return self._insights_teaser()

        # Health check
        elif any(cmd in message_lower for cmd in [
            "health", "zdrowie", "check", "diagnostics", "stan"
        ]):
            return self._insights_health()

        # Summary
        elif "summary" in message_lower or "podsumowanie" in message_lower:
            return self._insights_habits()

        # Today report (text version)
        elif any(cmd in message_lower for cmd in [
            "report", "raport", "today"
        ]):
            return self._insights_report_text()

        # Help command
        elif any(cmd in message_lower for cmd in ["help", "commands", "?", "pomoc"]):
            return self._show_help()

        # Default response — show insight instead of "AI not connected"
        else:
            return self._default_response(user_message)

    # ================================================================
    # INSIGHTS COMMANDS
    # ================================================================

    def _insights_habits(self):
        if self.insights:
            return self.insights.get_habit_summary()
        return ["hck_GPT: Insights engine not available."]

    def _insights_anomalies(self):
        if self.insights:
            return self.insights.get_anomaly_report()
        return ["hck_GPT: Insights engine not available."]

    def _insights_current(self):
        if self.insights:
            msg = self.insights.get_current_insight()
            if msg:
                return [msg]
            return ["hck_GPT: All quiet right now. No anomalies, no heavy loads."]
        return ["hck_GPT: Insights engine not available."]

    def _insights_teaser(self):
        if self.insights:
            return self.insights.get_teaser()
        return ["hck_GPT: Insights engine not available."]

    def _insights_health(self):
        if self.insights:
            return self.insights.get_health_check()
        return ["hck_GPT: Insights engine not available."]

    def _insights_report_text(self):
        """Text-based quick report (points to the visual report button)."""
        lines = []
        if self.insights:
            lines = self.insights.get_health_check()
        else:
            lines = ["hck_GPT: Insights engine not available."]
        lines.append("")
        lines.append("💡 Click the ✨ Today Report! ✨ button above for the full visual report.")
        return lines

    # ================================================================
    # SERVICE COMMANDS
    # ================================================================

    def _restore_services(self):
        """Restore all previously disabled services"""
        messages = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🔄 Restoring Services...",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]

        summary = self.services_manager.get_disabled_services_summary()

        if summary["count"] == 0:
            messages.extend([
                "No services to restore.",
                "All services are currently enabled.",
                "",
                "Type 'service setup' to optimize your PC"
            ])
            return messages

        messages.append(f"Restoring {summary['count']} services...")
        messages.append("")

        results = self.services_manager.restore_all_services()

        success_count = sum(1 for r in results if r[1])
        fail_count = len(results) - success_count

        for service, success, msg in results:
            if success:
                messages.append(f"✅ Restored: {service}")
            else:
                messages.append(f"❌ Failed: {service}")

        messages.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"✨ Restore Complete!",
            f"   {success_count} services restored"
        ])

        if fail_count > 0:
            messages.append(f"   {fail_count} services failed (may need admin)")

        return messages

    def _show_service_status(self):
        """Show current service optimization status"""
        messages = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 Service Status",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]

        summary = self.services_manager.get_disabled_services_summary()

        messages.append(f"Disabled Services: {summary['count']}")
        messages.append(f"Last Modified: {summary['timestamp']}")
        messages.append("")

        if summary["count"] > 0:
            messages.append("Currently disabled:")
            for service in summary["services"]:
                display_name = service
                for category, info in self.services_manager.SERVICES.items():
                    if service in info["services"]:
                        display_name = f"{service} ({info['display']})"
                        break
                messages.append(f"  • {display_name}")
        else:
            messages.append("No services are currently disabled")

        messages.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "Commands:",
            "  • 'restore services' - Re-enable all",
            "  • 'service setup' - Run optimization again"
        ])

        return messages

    def _show_help(self):
        """Show available commands"""
        return [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🤖 hck_GPT — Available Commands",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "Intelligence:",
            "  • stats / habits — Your usage profile & top apps",
            "  • health — Quick system health check",
            "  • alerts — Anomaly report (spikes, temps)",
            "  • insights — What's happening right now",
            "  • teaser — Personality-driven prediction",
            "  • report — Text summary (or use ✨ button)",
            "",
            "Service Optimization:",
            "  • service setup — Start service optimization wizard",
            "  • service status — Show current service state",
            "  • restore services — Re-enable all disabled services",
            "",
            "General:",
            "  • help — Show this message",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

    def _default_response(self, user_message):
        """Smart default: show current insight + hint commands."""
        lines = [f"> {user_message}", ""]

        # Try to show something useful
        if self.insights:
            msg = self.insights.get_current_insight()
            if msg:
                lines.append(msg)
                lines.append("")

        lines.extend([
            "hck_GPT: I don't have full AI yet, but I'm learning!",
            "Try: 'stats', 'alerts', 'insights', 'teaser', or 'help'"
        ])
        return lines

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

    def reset(self):
        """Reset handler to initial state"""
        self.wizard.reset()
        self.conversation_history = []
