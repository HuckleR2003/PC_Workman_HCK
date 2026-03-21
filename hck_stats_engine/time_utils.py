"""hck_stats_engine.time_utils
Time helpers for aggregation."""
from import_core import register_component
from datetime import datetime

class TimeUtils:
    def __init__(self):
        register_component('hck_stats_engine.time_utils', self)

    def now_iso(self):
        return datetime.utcnow().isoformat()

time_utils = TimeUtils()
