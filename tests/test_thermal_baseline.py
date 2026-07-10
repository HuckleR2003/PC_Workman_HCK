"""tests.test_thermal_baseline
The learning "heart": per-workload, per-metric Welford baselines.

Regression guard for the starvation bug (fixed 2026-07-05): the engine used to
learn ONLY cpu_temp, filtered on `WHERE cpu_temp > 0`. On any machine without
LibreHardwareMonitor (most users) cpu_temp is -1, so it learned nothing and the
Learning Center sat at 0% forever. It now learns every real signal per bucket
(cpu_temp when a sensor exists, gpu_temp on NVIDIA, cpu_load always).
"""
import os
import random
import sqlite3
import tempfile
import unittest

import core.thermal_baseline as tbm


def _seed_db(path, *, with_cpu_temp):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE deepmonitor_snapshots "
                "(ts REAL, cpu_temp REAL, gpu_temp REAL, cpu_load REAL, gpu_load REAL)")
    random.seed(7)
    for i in range(300):
        gaming = (i % 3 == 0)
        cpu_l = random.uniform(60, 85) if gaming else random.uniform(2, 12)
        gpu_l = random.uniform(70, 99) if gaming else random.uniform(0, 8)
        gpu_t = random.gauss(72, 3)   if gaming else random.gauss(41, 2)
        cpu_t = random.gauss(70, 3)   if gaming else random.gauss(38, 2)
        con.execute("INSERT INTO deepmonitor_snapshots VALUES (?,?,?,?,?)",
                    (1000.0 + i, cpu_t if with_cpu_temp else -1.0, gpu_t, cpu_l, gpu_l))
    con.commit()
    con.close()


class TestNoLHMMachineStillLearns(unittest.TestCase):
    """The critical case: no CPU-temp sensor, but GPU temp + load are real."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        _seed_db(os.path.join(self.d, "db.sqlite"), with_cpu_temp=False)
        tbm._DB_PATH = os.path.join(self.d, "db.sqlite")
        tbm._PREFS_PATH = os.path.join(self.d, "tb.json")
        self.tb = tbm.ThermalBaseline()
        self.tb.rebuild(force=True)

    def test_gpu_and_load_accumulate_without_cpu_temp(self):
        self.assertEqual(self.tb._metric_total("cpu_temp"), 0)
        self.assertGreater(self.tb._metric_total("gpu_temp"), 200)
        self.assertGreater(self.tb._metric_total("cpu_load"), 200)

    def test_primary_metric_falls_back_to_gpu_temp(self):
        self.assertEqual(self.tb.primary_metric(), "gpu_temp")

    def test_overall_pct_is_not_zero(self):
        self.assertGreater(self.tb.overall_training_pct(), 0)

    def test_gaming_bucket_learned_real_gpu_range(self):
        g = self.tb.get_range("gaming", "gpu_temp")
        self.assertTrue(g.is_usable)
        self.assertTrue(66 <= g.mean <= 78, f"mean off: {g.mean}")

    def test_chat_reports_real_gpu_temp(self):
        msg = self.tb.format_for_chat(cpu_temp=-1, cpu_load=30, gpu_load=85,
                                      lang="en", gpu_temp=71)
        self.assertIn("GPU TEMP", msg)
        self.assertIn("71", msg)

    def test_backward_compatible_cpu_temp_call_is_safe(self):
        # old callers that don't pass a metric still work (just empty here)
        self.assertEqual(self.tb.get_range("gaming").n, 0)
        self.assertTrue(self.tb.training_status())  # non-empty


class TestLHMMachineLearnsCpuTemp(unittest.TestCase):
    """With a real CPU-temp sensor, cpu_temp becomes the primary metric."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        _seed_db(os.path.join(self.d, "db.sqlite"), with_cpu_temp=True)
        tbm._DB_PATH = os.path.join(self.d, "db.sqlite")
        tbm._PREFS_PATH = os.path.join(self.d, "tb.json")
        self.tb = tbm.ThermalBaseline()
        self.tb.rebuild(force=True)

    def test_cpu_temp_is_primary_when_available(self):
        self.assertEqual(self.tb.primary_metric(), "cpu_temp")
        self.assertGreater(self.tb._metric_total("cpu_temp"), 200)

    def test_engine_classify_temp_entrypoint(self):
        # was AttributeError-then-swallowed before the fix
        verdict = self.tb.classify_temp(70.0)
        self.assertIn(verdict, ("normal", "elevated", "high", "critical", "unknown"))


if __name__ == "__main__":
    unittest.main()
