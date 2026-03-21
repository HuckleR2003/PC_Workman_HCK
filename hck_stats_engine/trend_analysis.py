"""hck_stats_engine.trend_analysis
Basic trend helpers."""
from import_core import register_component

class TrendAnalysis:
    def __init__(self):
        register_component('hck_stats_engine.trend_analysis', self)

    def simple_trend(self, series):
        # return slope-like indicator
        if len(series) < 2:
            return 0
        return (series[-1] - series[0]) / len(series)

trend_analysis = TrendAnalysis()
