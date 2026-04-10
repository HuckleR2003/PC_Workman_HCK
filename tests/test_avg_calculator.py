"""tests.test_avg_calculator
Tests for hck_stats_engine.avg_calculator — CSV-based daily aggregation.
"""
import os
import csv
import tempfile
import unittest
from unittest.mock import patch


class TestAvgCalculator(unittest.TestCase):

    def setUp(self):
        from hck_stats_engine.avg_calculator import AvgCalculator
        self.calc = AvgCalculator()

    def test_returns_empty_list_when_file_missing(self):
        with patch('hck_stats_engine.avg_calculator.HOURLY', '/nonexistent/path/hourly.csv'):
            result = self.calc.hourly_to_daily()
        self.assertEqual(result, [])

    def test_aggregates_single_day_correctly(self):
        rows = [
            {'iso_time': '2026-01-01T10:00:00', 'cpu_percent': '20.0'},
            {'iso_time': '2026-01-01T11:00:00', 'cpu_percent': '40.0'},
            {'iso_time': '2026-01-01T12:00:00', 'cpu_percent': '60.0'},
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['iso_time', 'cpu_percent'])
            writer.writeheader()
            writer.writerows(rows)
            tmp_path = f.name

        try:
            with patch('hck_stats_engine.avg_calculator.HOURLY', tmp_path):
                result = self.calc.hourly_to_daily()
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['date'], '2026-01-01')
            self.assertAlmostEqual(result[0]['cpu_avg'], 40.0)
        finally:
            os.unlink(tmp_path)

    def test_aggregates_multiple_days_separately(self):
        rows = [
            {'iso_time': '2026-01-01T10:00:00', 'cpu_percent': '10.0'},
            {'iso_time': '2026-01-01T11:00:00', 'cpu_percent': '20.0'},
            {'iso_time': '2026-01-02T10:00:00', 'cpu_percent': '80.0'},
            {'iso_time': '2026-01-02T11:00:00', 'cpu_percent': '60.0'},
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['iso_time', 'cpu_percent'])
            writer.writeheader()
            writer.writerows(rows)
            tmp_path = f.name

        try:
            with patch('hck_stats_engine.avg_calculator.HOURLY', tmp_path):
                result = self.calc.hourly_to_daily()
            self.assertEqual(len(result), 2)
            dates = {r['date']: r['cpu_avg'] for r in result}
            self.assertAlmostEqual(dates['2026-01-01'], 15.0)
            self.assertAlmostEqual(dates['2026-01-02'], 70.0)
        finally:
            os.unlink(tmp_path)

    def test_result_contains_date_and_cpu_avg_keys(self):
        rows = [{'iso_time': '2026-03-15T09:00:00', 'cpu_percent': '55.0'}]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['iso_time', 'cpu_percent'])
            writer.writeheader()
            writer.writerows(rows)
            tmp_path = f.name

        try:
            with patch('hck_stats_engine.avg_calculator.HOURLY', tmp_path):
                result = self.calc.hourly_to_daily()
            self.assertIn('date', result[0])
            self.assertIn('cpu_avg', result[0])
        finally:
            os.unlink(tmp_path)


if __name__ == '__main__':
    unittest.main()
