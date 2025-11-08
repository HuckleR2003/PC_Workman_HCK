"""ai.hck_gpt
Small rule-based assistant for humorous messages and insights.
"""
from import_core import register_component
import random

class HckGPT:
    def __init__(self):
        self.name = 'hck-gpt'
        register_component('ai.hck_gpt', self)

    def generate_startup_message(self, top_process=None):
        examples = [
            "Hej! Dzis znów katujemy CPU Battlefieldem?","Ready to push your CPU to the limit!","Watch out — background miner detected? (just kidding)"]
        if top_process:
            return f"Hej! Widzę, że {top_process} zabiera najwiecej zasobów."                   f" {random.choice(examples)}"
        return random.choice(examples)

assistant = HckGPT()
