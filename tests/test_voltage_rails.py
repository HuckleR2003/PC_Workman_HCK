"""tests.test_voltage_rails
Voltage learning for CPU / GPU / MB (2026-07-17).

The SPC engine used to know only the board rails (12V / 5V / 3.3V). This
guards the full new-rail pipeline: LHM tree parsing (unit-aware - "CPU Core"
exists under Temperatures AND Voltages), the live_sensors keys, the
deepmonitor_snapshots migration for existing installs, and the analyzer's
dynamic rail map.
"""
import os
import sqlite3
import tempfile
import time
import unittest

from core.live_collector import _walk_sensor_tree
from core.voltage_analyzer import RAILS


def _n(text, value, children=None):
    return {"Text": text, "Value": value, "Children": children or []}


class TestSensorTreeParsing(unittest.TestCase):

    def test_unit_separates_core_voltage_from_core_temperature(self):
        """'CPU Core' appears twice in a real LHM tree - only the V one may
        land in volt_vcore, never the °C one."""
        tree = _n("Computer", "", [
            _n("Temperatures", "", [
                _n("CPU Core", "46.0 °C"),
                _n("GPU Core", "51.0 °C"),
            ]),
            _n("Voltages", "", [
                _n("CPU Core", "1.224 V"),
                _n("GPU Core", "0.881 V"),
                _n("+12V", "12.096 V"),
                _n("+5V", "5.040 V"),
                _n("+3.3V", "3.312 V"),
            ]),
        ])
        acc: dict = {}
        _walk_sensor_tree(tree, acc)
        self.assertEqual(acc["volt_vcore"], 1.224)
        self.assertEqual(acc["volt_gpu"], 0.881)
        self.assertEqual(acc["volt_12v"], 12.096)
        self.assertEqual(acc["volt_5v"], 5.040)
        self.assertEqual(acc["volt_33v"], 3.312)

    def test_vcore_spelling_variant(self):
        acc: dict = {}
        _walk_sensor_tree(_n("Vcore", "1.104 V"), acc)
        self.assertEqual(acc["volt_vcore"], 1.104)

    def test_board_temps_still_parse(self):
        acc: dict = {}
        _walk_sensor_tree(_n("root", "", [
            _n("VRM", "58.0 °C"), _n("System", "39.0 °C")]), acc)
        self.assertEqual(acc["temp_vrm"], 58.0)
        self.assertEqual(acc["temp_sys"], 39.0)


class TestRailsMap(unittest.TestCase):

    def test_five_rails_cover_cpu_gpu_mb(self):
        self.assertEqual(
            set(RAILS),
            {"mb_volt_12v", "mb_volt_5v", "mb_volt_33v",
             "mb_volt_vcore", "mb_volt_gpu"})
        self.assertEqual(RAILS["mb_volt_vcore"]["label"], "VCore")
        self.assertEqual(RAILS["mb_volt_gpu"]["label"], "GPU")

    def test_live_sensors_defaults_carry_new_keys(self):
        from hck_gpt.data.live_sensors import LIVE, mb_summary
        self.assertIn("mb_volt_vcore", LIVE)
        self.assertIn("mb_volt_gpu", LIVE)
        s = mb_summary()
        self.assertIn("mb_volt_vcore", s)
        self.assertIn("mb_volt_gpu", s)


class TestSnapshotMigration(unittest.TestCase):
    """Existing installs have the 18-column table - _ensure_table must add
    the two new rail columns without touching the data."""

    _OLD_SCHEMA = """
    CREATE TABLE deepmonitor_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL, date_str TEXT NOT NULL,
        cpu_load REAL, cpu_temp REAL, cpu_mhz REAL, cpu_power REAL,
        gpu_temp REAL, gpu_load REAL, gpu_vram_pct REAL, gpu_power REAL,
        ram_pct REAL, ram_used_gb REAL, swap_pct REAL,
        mb_temp_sys REAL, mb_temp_vrm REAL,
        mb_volt_12v REAL, mb_volt_5v REAL, mb_volt_33v REAL,
        disk_json TEXT, mb_source TEXT DEFAULT ''
    );
    """

    def test_old_table_gains_new_columns_and_keeps_rows(self):
        from hck_gpt.data.metrics_store import MetricsStore
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "hck_stats.db")
            con = sqlite3.connect(db)
            con.executescript(self._OLD_SCHEMA)
            con.execute(
                "INSERT INTO deepmonitor_snapshots (ts, date_str, mb_volt_12v)"
                " VALUES (1.0, '2026-07-17', 12.05)")
            con.commit()
            con.close()

            ms = MetricsStore()
            ms._db_path = db
            self.assertTrue(ms._ensure_table())

            con = sqlite3.connect(db)
            cols = {r[1] for r in con.execute(
                "PRAGMA table_info(deepmonitor_snapshots)")}
            self.assertIn("mb_volt_vcore", cols)
            self.assertIn("mb_volt_gpu", cols)
            kept = con.execute(
                "SELECT mb_volt_12v FROM deepmonitor_snapshots").fetchone()[0]
            self.assertEqual(kept, 12.05)
            # migration is idempotent
            self.assertTrue(ms._ensure_table())
            con.close()


class TestAnalyzerQuery(unittest.TestCase):

    def test_query_history_returns_new_rails(self):
        import core.voltage_analyzer as va_mod
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "hck_stats.db")
            con = sqlite3.connect(db)
            con.execute(
                "CREATE TABLE deepmonitor_snapshots ("
                "ts REAL, mb_volt_12v REAL, mb_volt_5v REAL, "
                "mb_volt_33v REAL, mb_volt_vcore REAL, mb_volt_gpu REAL, "
                "gpu_load REAL)")
            now = time.time()
            for i in range(5):
                con.execute(
                    "INSERT INTO deepmonitor_snapshots VALUES (?,?,?,?,?,?,?)",
                    (now - i * 60, 12.05, 5.02, 3.31, 1.20 + i * 0.001,
                     0.88, 25.0))
            con.commit()
            con.close()

            orig = va_mod._DB_PATH
            va_mod._DB_PATH = db
            try:
                rows = va_mod.voltage_analyzer._query_history(hours=1)
            finally:
                va_mod._DB_PATH = orig
            self.assertEqual(len(rows), 5)
            self.assertIn("mb_volt_vcore", rows[0])
            self.assertIn("mb_volt_gpu", rows[0])
            self.assertAlmostEqual(rows[-1]["mb_volt_vcore"], 1.20, places=2)


if __name__ == "__main__":
    unittest.main()
