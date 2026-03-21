# hck_gpt/service_setup_wizard.py
"""
Service Setup Wizard
Interactive wizard for optimizing Windows services
"""

from .services_manager import ServicesManager

class ServiceSetupWizard:
    """Interactive wizard for service optimization"""

    def __init__(self):
        self.services_manager = ServicesManager()
        self.state = "idle"  # idle, intro, questions, confirmation, done
        self.current_question = 0
        self.user_responses = {}

        # Questions to ask user
        self.questions = [
            {
                "id": "printer",
                "question": "Do you have a Printer connected to your PC?",
                "hint": "(Yes/No)",
                "service_category": "printer"
            },
            {
                "id": "bluetooth",
                "question": "Do you use Bluetooth devices?",
                "hint": "(Yes/No)",
                "service_category": "bluetooth"
            },
            {
                "id": "remote",
                "question": "Do you use Remote Desktop or PC sharing?",
                "hint": "(Yes/No)",
                "service_category": "remote"
            },
            {
                "id": "fax",
                "question": "Do you use Fax services?",
                "hint": "(Yes/No)",
                "service_category": "fax"
            },
            {
                "id": "tablet",
                "question": "Do you have a drawing tablet or use pen input?",
                "hint": "(Yes/No)",
                "service_category": "tablet"
            },
            {
                "id": "xbox",
                "question": "Do you use Xbox gaming features?",
                "hint": "(Yes/No)",
                "service_category": "xbox"
            },
            {
                "id": "telemetry",
                "question": "Do you want to keep Windows telemetry enabled?",
                "hint": "(Yes/No - No recommended for privacy)",
                "service_category": "telemetry"
            }
        ]

    def start(self):
        """Start the wizard"""
        self.state = "intro"
        self.current_question = 0
        self.user_responses = {}
        return self.get_intro_message()

    def get_intro_message(self):
        """Get the introduction message"""
        return [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 Service Setup - Welcome!",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "Do you want to quick setup to disable",
            "useless services for your PC?",
            "",
            "E.g. Print Spooler, Bluetooth, Remote Desktop",
            "and more services that take system resources.",
            "",
            "This can improve your PC performance",
            "and reduce memory usage.",
            "",
            "Type 'Yes' to start or 'No' to cancel",
        ]

    def process_input(self, user_input):
        """
        Process user input and return response

        Args:
            user_input: User's text input

        Returns:
            list: Response messages to display
        """
        user_input = user_input.strip().lower()

        if self.state == "intro":
            return self._handle_intro_response(user_input)
        elif self.state == "questions":
            return self._handle_question_response(user_input)
        elif self.state == "confirmation":
            return self._handle_confirmation_response(user_input)
        else:
            return ["Error: Invalid wizard state"]

    def _handle_intro_response(self, user_input):
        """Handle response to intro message"""
        positive_words = ["yes", "y", "yeah", "ok", "sure", "tak", "t"]
        negative_words = ["no", "n", "nope", "nie"]

        if any(word in user_input for word in positive_words):
            self.state = "questions"
            return self._get_current_question()
        elif any(word in user_input for word in negative_words):
            self.state = "idle"
            return [
                "Setup cancelled.",
                "Type 'service setup' anytime to start again."
            ]
        else:
            return [
                "Please answer Yes or No",
                "Type 'Yes' to start or 'No' to cancel"
            ]

    def _handle_question_response(self, user_input):
        """Handle response to a question"""
        positive_words = ["yes", "y", "yeah", "ok", "sure", "tak", "t"]
        negative_words = ["no", "n", "nope", "nie"]

        # Determine user's answer
        uses_service = None
        if any(word in user_input for word in positive_words):
            uses_service = True
        elif any(word in user_input for word in negative_words):
            uses_service = False

        if uses_service is None:
            return [
                "Please answer Yes or No",
                self.questions[self.current_question]["question"],
                self.questions[self.current_question]["hint"]
            ]

        # Save response
        question = self.questions[self.current_question]
        self.user_responses[question["id"]] = {
            "uses_service": uses_service,
            "category": question["service_category"]
        }

        # Move to next question or confirmation
        self.current_question += 1

        if self.current_question >= len(self.questions):
            self.state = "confirmation"
            return self._get_confirmation_message()
        else:
            return self._get_current_question()

    def _handle_confirmation_response(self, user_input):
        """Handle confirmation response"""
        positive_words = ["yes", "y", "yeah", "ok", "confirm", "apply", "tak", "t"]
        negative_words = ["no", "n", "nope", "cancel", "nie"]

        if any(word in user_input for word in positive_words):
            return self._apply_optimization()
        elif any(word in user_input for word in negative_words):
            self.state = "idle"
            return [
                "Setup cancelled. No changes were made.",
                "Type 'service setup' to start again."
            ]
        else:
            return [
                "Please confirm:",
                "Type 'Yes' to apply or 'No' to cancel"
            ]

    def _get_current_question(self):
        """Get the current question message"""
        question = self.questions[self.current_question]
        progress = f"[{self.current_question + 1}/{len(self.questions)}]"

        return [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🔧 Service Setup {progress}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            question["question"],
            question["hint"]
        ]

    def _get_confirmation_message(self):
        """Get the confirmation message with summary"""
        messages = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "✅ Service Setup - Summary",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "Based on your answers, these services",
            "will be DISABLED to optimize your PC:",
            ""
        ]

        # List services that will be disabled
        to_disable = []
        for q_id, response in self.user_responses.items():
            if not response["uses_service"]:  # User doesn't use it
                category = response["category"]
                service_info = self.services_manager.SERVICES.get(category)
                if service_info:
                    to_disable.append(f"  • {service_info['display']}")

        if to_disable:
            messages.extend(to_disable)
        else:
            messages.append("  (None - you use all services)")

        messages.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "These services will remain ENABLED:",
            ""
        ])

        # List services that will remain enabled
        to_keep = []
        for q_id, response in self.user_responses.items():
            if response["uses_service"]:  # User uses it
                category = response["category"]
                service_info = self.services_manager.SERVICES.get(category)
                if service_info:
                    to_keep.append(f"  • {service_info['display']}")

        if to_keep:
            messages.extend(to_keep)
        else:
            messages.append("  (None)")

        messages.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "⚠️  Note: You can restore services anytime",
            "    by typing 'restore services'",
            "",
            "Type 'Yes' to apply or 'No' to cancel"
        ])

        return messages

    def _apply_optimization(self):
        """Apply the service optimization based on user responses"""
        messages = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "⚙️  Applying optimizations...",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]

        success_count = 0
        fail_count = 0

        # Apply optimizations
        for q_id, response in self.user_responses.items():
            category = response["category"]
            should_disable = not response["uses_service"]

            if should_disable:
                success, results = self.services_manager.apply_optimization(
                    category, should_disable=True
                )

                service_info = self.services_manager.SERVICES.get(category)
                if success:
                    messages.append(f"✅ Disabled: {service_info['display']}")
                    success_count += 1
                else:
                    messages.append(f"❌ Failed: {service_info['display']}")
                    fail_count += 1

        messages.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"✨ Optimization Complete!",
            f"   {success_count} services optimized",
        ])

        if fail_count > 0:
            messages.append(f"   {fail_count} services failed (may need admin)")

        messages.extend([
            "",
            "Your PC should now use less resources!",
            "Configuration saved to: data/services_config.json",
            "",
            "Type 'restore services' to undo changes",
            "Type 'service status' to see current state"
        ])

        self.state = "done"
        return messages

    def is_active(self):
        """Check if wizard is currently active"""
        return self.state in ["intro", "questions", "confirmation"]

    def reset(self):
        """Reset wizard to initial state"""
        self.state = "idle"
        self.current_question = 0
        self.user_responses = {}
