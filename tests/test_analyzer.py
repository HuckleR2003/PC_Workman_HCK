"""tests.test_analyzer
Tests for core.analyzer — averaging, spike detection.
Logger is mocked via COMPONENTS so no real data is needed.
"""
import time
import unittest
from unittest.mock import MagicMock
from import_core import COMPONENTS


def _inject_mock_logger(samples):
    """Inject a mock logger into COMPONENTS with the given sample list."""
    mock_logger = MagicMock()
    mock_logger.get_last_seconds.return_value = samples
    COMPONENTS['core.logger'] = mock_logger
    return mock_logger


def _make_samples(cpu_values, base_ts=None):
    """Build a list of snapshot dicts from a list of cpu percent values."""
    if base_ts is None:
        base_ts = time.time() - len(cpu_values)
    return [
        {'timestamp': base_ts + i, 'cpu_percent': v, 'ram_percent': 50.0, 'gpu_percent': 0.0}
        for i, v in enumerate(cpu_values)
    ]


class TestAnalyzerAverages(unittest.TestCase):

    def setUp(self):
        from core.analyzer import Analyzer
        self.analyzer = Analyzer()

    def test_empty_buffer_returns_zeros(self):
        _inject_mock_logger([])
        result = self.analyzer.average_over_seconds(30)
        self.assertEqual(result, {'cpu': 0.0, 'ram': 0.0, 'gpu': 0.0})

    def test_average_cpu_correct(self):
        samples = _make_samples([10.0, 20.0, 30.0])
        _inject_mock_logger(samples)
        result = self.analyzer.average_over_seconds(60)
        self.assertAlmostEqual(result['cpu'], 20.0)

    def test_averages_now_1h_4h_returns_all_keys(self):
        samples = _make_samples([50.0, 60.0])
        _inject_mock_logger(samples)
        result = self.analyzer.averages_now_1h_4h()
        self.assertIn('now', result)
        self.assertIn('1h', result)
        self.assertIn('4h', result)

    def test_average_filters_old_samples(self):
        old_ts = time.time() - 7200
        old_samples = [
            {'timestamp': old_ts, 'cpu_percent': 99.0, 'ram_percent': 99.0, 'gpu_percent': 0.0}
        ]
        recent_samples = _make_samples([10.0, 10.0])
        _inject_mock_logger(old_samples + recent_samples)
        result = self.analyzer.average_over_seconds(30)
        self.assertAlmostEqual(result['cpu'], 10.0)


class TestAnalyzerSpikeDetection(unittest.TestCase):

    def setUp(self):
        from core.analyzer import Analyzer
        self.analyzer = Analyzer()

    def test_spike_detected_when_last_value_jumps(self):
        samples = _make_samples([10.0, 10.0, 10.0, 10.0, 80.0])
        _inject_mock_logger(samples)
        is_spike, diff = self.analyzer.detect_spike_last(seconds=60, threshold_percent=30.0)
        self.assertTrue(is_spike)
        self.assertGreater(diff, 0)

    def test_no_spike_on_stable_values(self):
        samples = _make_samples([20.0, 21.0, 20.5, 20.0, 21.0])
        _inject_mock_logger(samples)
        is_spike, diff = self.analyzer.detect_spike_last(seconds=60, threshold_percent=30.0)
        self.assertFalse(is_spike)

    def test_returns_false_on_single_sample(self):
        samples = _make_samples([50.0])
        _inject_mock_logger(samples)
        is_spike, diff = self.analyzer.detect_spike_last(seconds=60)
        self.assertFalse(is_spike)
        self.assertEqual(diff, 0.0)

    def test_returns_false_on_empty_buffer(self):
        _inject_mock_logger([])
        is_spike, diff = self.analyzer.detect_spike_last(seconds=60)
        self.assertFalse(is_spike)
        self.assertEqual(diff, 0.0)

    def test_spike_threshold_respected(self):
        samples = _make_samples([10.0, 10.0, 15.0])
        _inject_mock_logger(samples)
        is_spike_low, _ = self.analyzer.detect_spike_last(seconds=60, threshold_percent=10.0)
        is_spike_high, _ = self.analyzer.detect_spike_last(seconds=60, threshold_percent=80.0)
        self.assertTrue(is_spike_low)
        self.assertFalse(is_spike_high)


if __name__ == '__main__':
    unittest.main()
