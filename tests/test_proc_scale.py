"""tests.test_proc_scale
Per-process CPU must be on the WHOLE-MACHINE scale (2026-07-18).

psutil's per-process cpu_percent is scaled to one core; undivided, a single
busy thread on a 12-thread CPU showed "100%" next to a machine total of 8%,
and the proactive 30% spike alert fired for nothing. Both consumers must
divide by the logical core count - these source ratchets keep it that way.
"""
import io
import unittest


def _src(path):
    return io.open(path, encoding="utf-8").read()


class TestProcessCpuScale(unittest.TestCase):

    def test_monitor_normalizes_per_core(self):
        src = _src("core/monitor.py")
        self.assertIn("cpu_count(logical=True)", src)
        self.assertIn("/ n_cores", src)

    def test_proactive_spike_normalizes_per_core(self):
        src = _src("hck_gpt/memory/proactive_monitor.py")
        self.assertIn("cpu_count(logical=True)", src)
        self.assertIn("/ _nc", src)

    def test_scale_math(self):
        """One fully busy thread on a 12-thread CPU = ~8.3% of the machine,
        NOT 100% - and must stay under the 30% spike threshold."""
        from hck_gpt.memory.proactive_monitor import PROC_SPIKE_PCT
        one_thread_raw = 100.0
        n = 12
        normalized = one_thread_raw / n
        self.assertLess(normalized, PROC_SPIKE_PCT)
        self.assertAlmostEqual(normalized, 8.33, places=1)


if __name__ == "__main__":
    unittest.main()
