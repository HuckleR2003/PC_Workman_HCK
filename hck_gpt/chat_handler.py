# hck_gpt/chat_handler.py
"""
Chat Handler
Main logic for hck_GPT chat interactions and command processing
"""

from .service_setup_wizard import ServiceSetupWizard
from .services_manager import ServicesManager

class ChatHandler:
    """Handles chat messages and commands for hck_GPT"""

    def __init__(self):
        self.wizard = ServiceSetupWizard()
        self.services_manager = ServicesManager()
        self.conversation_history = []

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

        # Help command
        elif any(cmd in message_lower for cmd in ["help", "commands", "?"]):
            return self._show_help()

        # Default response (AI not connected)
        else:
            return self._default_response(user_message)

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
                # Try to find the display name
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
            "🤖 hck_GPT - Available Commands",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "Service Optimization:",
            "  • service setup - Start service optimization wizard",
            "  • service status - Show current service state",
            "  • restore services - Re-enable all disabled services",
            "",
            "General:",
            "  • help - Show this help message",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "More features coming soon!",
            "Full AI integration in development 🚀"
        ]

    def _default_response(self, user_message):
        """Default response when AI is not connected"""
        return [
            f"> {user_message}",
            "",
            "hck_GPT: AI is not connected yet.",
            "Available commands:",
            "  • Type 'service setup' for PC optimization",
            "  • Type 'help' for all commands"
        ]

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

    def reset(self):
        """Reset handler to initial state"""
        self.wizard.reset()
        self.conversation_history = []
