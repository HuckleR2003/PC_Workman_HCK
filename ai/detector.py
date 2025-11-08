"""ai.detector
Simple process classifier (mock). In production use signatures or ML models.
"""
from import_core import register_component

class Detector:
    def __init__(self):
        register_component('ai.detector', self)
        self.suspicious_keywords = ['miner', 'crypto', 'coin', 'xmr']

    def is_suspicious(self, proc_name):
        name = proc_name.lower()
        for k in self.suspicious_keywords:
            if k in name:
                return True
        return False

detector = Detector()
