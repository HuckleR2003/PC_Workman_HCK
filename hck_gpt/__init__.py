# hck_gpt/__init__.py
"""
hck_GPT - AI Assistant for PC Workman
Provides system optimization and intelligent suggestions
"""

from .chat_handler import ChatHandler
from .service_setup_wizard import ServiceSetupWizard
from .services_manager import ServicesManager
from .panel import HCKGPTPanel

__version__ = "1.0.0"
__all__ = ["ChatHandler", "ServiceSetupWizard", "ServicesManager", "HCKGPTPanel"]
