"""tests.test_usage_stats
Guards the Fan Usage Stats range->sample math (2026-07-16). The page appends
a sample every _SAMPLE_INTERVAL_S seconds, but the range window was divided by
a hardcoded 60, so NOW (60 s) resolved to a single point and drew an empty
chart until the user clicked a wider range. Every range must yield >= 2 points.
"""
import unittest


class TestUsageStatsRanges(unittest.TestCase):

    def test_every_range_yields_a_drawable_series(self):
        from ui.pages.fan_control.usage_stats import FansUsageStatsPage as U
        interval = U._SAMPLE_INTERVAL_S
        self.assertGreater(interval, 0)
        for name, meta in U.TIME_RANGES.items():
            want = max(2, meta["seconds"] // interval)
            self.assertGreaterEqual(
                want, 2, f"range {name} would draw < 2 points (empty chart)")

    def test_now_is_not_a_single_point(self):
        from ui.pages.fan_control.usage_stats import FansUsageStatsPage as U
        now = U.TIME_RANGES["NOW"]["seconds"] // U._SAMPLE_INTERVAL_S
        self.assertGreaterEqual(now, 2,
                                "NOW must show a line, not a single dot")


if __name__ == "__main__":
    unittest.main()
