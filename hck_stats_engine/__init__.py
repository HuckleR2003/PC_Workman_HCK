# hck_stats_engine package
"""
HCK Stats Engine v2 - Long-term statistics collection and storage
SQLite-based pipeline: minute → hour → day → week → month
"""

from hck_stats_engine.db_manager import db_manager
from hck_stats_engine.aggregator import aggregator
from hck_stats_engine.process_aggregator import process_aggregator
from hck_stats_engine.query_api import query_api
from hck_stats_engine.events import event_detector

# Link process aggregator to main aggregator
aggregator.set_process_aggregator(process_aggregator)

__all__ = [
    'db_manager',
    'aggregator',
    'process_aggregator',
    'query_api',
    'event_detector',
]