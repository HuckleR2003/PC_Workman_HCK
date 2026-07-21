# hck_gpt/__init__.py
"""
hck_GPT v2.1.0
AI diagnostic assistant embedded inside PC Workman HCK.

Architecture:
  engine/      - Hybrid routing: rule engine + Ollama LLM fallback
  intents/     - Intent parser, vocabulary (84 intents), language detection PL/EN
  responses/   - Bilingual response builder with live hardware data
  memory/      - Session memory, proactive monitor, user knowledge (SQLite)
  context/     - System context builder, hardware scanner (WMI + psutil)
  data/        - Live sensors bridge, DeepMonitor metrics store
"""

from .chat_handler import ChatHandler
from .panel import HCKGPTPanel
from .insights import InsightsEngine

__version__ = "2.1.0"
__author__  = "Marcin Firmuga / HCK_Labs"
__all__ = ["ChatHandler", "HCKGPTPanel", "InsightsEngine", "__version__"]
