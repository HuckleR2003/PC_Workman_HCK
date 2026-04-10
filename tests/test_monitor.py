"""tests.test_monitor
Tests for core.monitor — snapshot collection, process listing, background thread.
psutil is mocked so tests run without live system data.
"""
import time
import threading
import unittest
from unittest.mock import patch, MagicMock


def _make_mock_process(pid, name, cpu, rss_bytes):
    p = MagicMock()
    p.info = {
        'pid': pid,
        'name': name,
        'cpu_percent': cpu,
        'memory_info': MagicMock(rss=rss_bytes),
    }
    return p


class TestMonitorSnapshot(unittest.TestCase):

    def _get_monitor(self):
        from core.monitor import Monitor
        return Monitor()

    @patch('psutil.process_iter')
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_snapshot_has_required_keys(self, mock_cpu, mock_ram, mock_procs):
        mock_cpu.return_value = 42.0
        mock_ram.return_value = MagicMock(percent=55.0)
        mock_procs.return_value = []

        m = self._get_monitor()
        snap = m.read_snapshot()

        for key in ('timestamp', 'cpu_percent', 'ram_percent', 'gpu_percent', 'processes'):
            self.assertIn(key, snap)

    @patch('psutil.process_iter')
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_snapshot_values_are_numeric(self, mock_cpu, mock_ram, mock_procs):
        mock_cpu.return_value = 75.5
        mock_ram.return_value = MagicMock(percent=60.0)
        mock_procs.return_value = []

        m = self._get_monitor()
        snap = m.read_snapshot()

        self.assertIsInstance(snap['cpu_percent'], float)
        self.assertIsInstance(snap['ram_percent'], float)
        self.assertIsInstance(snap['gpu_percent'], float)
        self.assertIsInstance(snap['timestamp'], float)
        self.assertEqual(snap['cpu_percent'], 75.5)
        self.assertEqual(snap['ram_percent'], 60.0)

    @patch('psutil.process_iter')
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_snapshot_processes_parsed_correctly(self, mock_cpu, mock_ram, mock_procs):
        mock_cpu.return_value = 10.0
        mock_ram.return_value = MagicMock(percent=30.0)
        mock_procs.return_value = [
            _make_mock_process(1, 'chrome.exe', 12.5, 200 * 1024 * 1024),
            _make_mock_process(2, 'python.exe', 5.0, 50 * 1024 * 1024),
        ]

        m = self._get_monitor()
        snap = m.read_snapshot()
        procs = snap['processes']

        self.assertEqual(len(procs), 2)
        self.assertEqual(procs[0]['name'], 'chrome.exe')
        self.assertAlmostEqual(procs[0]['ram_MB'], 200.0, places=0)
        self.assertEqual(procs[1]['cpu_percent'], 5.0)

    @patch('psutil.process_iter')
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_top_processes_sorted_by_cpu(self, mock_cpu, mock_ram, mock_procs):
        mock_cpu.return_value = 20.0
        mock_ram.return_value = MagicMock(percent=40.0)
        mock_procs.return_value = [
            _make_mock_process(1, 'low.exe',  2.0, 10 * 1024 * 1024),
            _make_mock_process(2, 'high.exe', 80.0, 10 * 1024 * 1024),
            _make_mock_process(3, 'mid.exe',  35.0, 10 * 1024 * 1024),
        ]

        m = self._get_monitor()
        top = m.top_processes(n=3, by='cpu')

        self.assertEqual(top[0]['name'], 'high.exe')
        self.assertEqual(top[1]['name'], 'mid.exe')
        self.assertEqual(top[2]['name'], 'low.exe')

    @patch('psutil.process_iter')
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_top_processes_sorted_by_ram(self, mock_cpu, mock_ram, mock_procs):
        mock_cpu.return_value = 5.0
        mock_ram.return_value = MagicMock(percent=50.0)
        mock_procs.return_value = [
            _make_mock_process(1, 'small.exe', 1.0,  50 * 1024 * 1024),
            _make_mock_process(2, 'big.exe',   1.0, 500 * 1024 * 1024),
        ]

        m = self._get_monitor()
        top = m.top_processes(n=2, by='ram')

        self.assertEqual(top[0]['name'], 'big.exe')

    @patch('psutil.process_iter')
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_top_processes_respects_n_limit(self, mock_cpu, mock_ram, mock_procs):
        mock_cpu.return_value = 10.0
        mock_ram.return_value = MagicMock(percent=30.0)
        mock_procs.return_value = [
            _make_mock_process(i, f'proc{i}.exe', float(i), 10 * 1024 * 1024)
            for i in range(10)
        ]

        m = self._get_monitor()
        self.assertEqual(len(m.top_processes(n=3)), 3)
        self.assertEqual(len(m.top_processes(n=6)), 6)

    @patch('psutil.process_iter')
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_cached_snapshot_returned_on_second_call(self, mock_cpu, mock_ram, mock_procs):
        mock_cpu.return_value = 10.0
        mock_ram.return_value = MagicMock(percent=20.0)
        mock_procs.return_value = []

        m = self._get_monitor()
        snap1 = m.read_snapshot()
        # Inject a cached snapshot manually
        m._cached_snapshot = snap1
        snap2 = m.read_snapshot()

        self.assertIs(snap1, snap2)

    @patch('psutil.process_iter')
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    def test_background_collection_sets_cache(self, mock_cpu, mock_ram, mock_procs):
        mock_cpu.return_value = 33.0
        mock_ram.return_value = MagicMock(percent=44.0)
        mock_procs.return_value = []

        m = self._get_monitor()
        m.start_background_collection(interval=0.05)
        time.sleep(0.15)
        m.stop_background_collection()

        self.assertIsNotNone(m._cached_snapshot)
        self.assertEqual(m._cached_snapshot['cpu_percent'], 33.0)


if __name__ == '__main__':
    unittest.main()
