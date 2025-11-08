"""tests.test_analyzer
"""
from core.analyzer import analyzer

def test_detect_spike_returns_tuple():
    ok, diff = analyzer.detect_spike([10,12,30], threshold_percent=50)
    assert isinstance(ok, bool)
