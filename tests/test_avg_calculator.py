"""tests.test_avg_calculator
"""
from hck_stats_engine.avg_calculator import avg_calc

def test_hourly_to_daily_runs():
    # Should not raise
    _ = avg_calc.hourly_to_daily()
