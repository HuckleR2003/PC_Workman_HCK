"""ai.ai_logic
Rule-based logic to create suggestions based on analyzer results.
"""
from import_core import register_component
import math

class AiLogic:
    def __init__(self):
        register_component('ai.ai_logic', self)

    def suggestion_for_snapshot(self, snapshot):
        cpu = snapshot.get('cpu_percent', 0)
        ram = snapshot.get('ram_percent', 0)
        if cpu > 85:
            return 'High CPU usage — consider closing heavy apps or throttling.'
        if ram > 90:
            return 'RAM critical — consider reboot or closing memory-heavy apps.'
        return 'System nominal.'

ai_logic = AiLogic()
