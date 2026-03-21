"""tests.test_monitor
Simple sanity test for monitor mock."""
from core.monitor import monitor

def test_monitor_has_read():
    s = monitor.read()
    assert 'cpu_percent' in s
