"""tests.test_fan_honesty
A fan speed on screen is a measurement, or it is not there (2026-11-14).

The fan pages used to draw random.randint() values under "Real-time fan
monitoring", list cooler models typed into the source ("Noctua NH-D15"),
print max_rpm * curve% as if it were an RPM reading, and confirm Apply with
"this is now the active fan plan" although nothing controls a fan.
These tests keep invented numbers from coming back.
"""
import os
import re
import time
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _code_only(src: str) -> str:
    """Executable code only: no comments and no docstrings, so the notes
    that describe the OLD invented data do not trip the guards."""
    import ast
    tree = ast.parse(src)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            node.body = [b for b in body
                         if not (isinstance(b, ast.Expr)
                                 and isinstance(b.value, ast.Constant)
                                 and isinstance(b.value.value, str))] \
                        or [ast.Pass()]
    return ast.unparse(tree)


class TestNoInventedFanData(unittest.TestCase):

    FAN_FILES = (("ui", "pages", "fan_control", "hardware_info.py"),
                 ("ui", "pages", "fan_control", "usage_stats.py"),
                 ("ui", "components", "fan_dashboard.py"))

    def test_fan_pages_do_not_use_random(self):
        for parts in self.FAN_FILES:
            code = _code_only(_read(*parts))
            self.assertNotRegex(code, r"\bimport random\b|\brandom\.",
                                f"{parts[-1]} generates numbers")

    def test_no_cooler_models_typed_into_the_source(self):
        for parts in self.FAN_FILES + (("ui", "components", "yourpc_page.py"),):
            code = _code_only(_read(*parts))
            for brand in ("Noctua", "Arctic P12", "be quiet", "Stock Cooler"):
                self.assertNotIn(brand, code, f"{brand} in {parts[-1]}")

    def test_my_pc_strip_has_no_literal_rpm(self):
        code = _code_only(_read("ui", "components", "yourpc_page.py"))
        self.assertNotRegex(code, r'''text=["'][A-Za-z ]*\d{3,4} RPM["']''',
                            "a hard-coded RPM value is back in My PC")

    def test_dashboard_no_longer_prints_plan_as_rpm(self):
        code = _code_only(_read("ui", "components", "fan_dashboard.py"))
        self.assertNotIn("int(max_rpm * pct / 100))", code)
        self.assertNotIn("Case front", code)
        self.assertNotIn("Case rear", code)

    def test_apply_does_not_claim_control(self):
        src = _read("ui", "components", "fan_dashboard.py")
        self.assertNotIn("This is now the active fan plan", src)
        self.assertIn("fan_control.apply_saved", src)
        self.assertIn("fan_control.plan_note", src)


class TestFanSensors(unittest.TestCase):

    def setUp(self):
        from core import fan_sensors
        self.fs = fan_sensors
        fan_sensors._reset_for_tests()

    def tearDown(self):
        self.fs._reset_for_tests()

    def test_nothing_recorded_means_nothing_measured(self):
        self.assertEqual(self.fs.measured(), [])
        self.assertEqual(self.fs.history(3600), {})
        self.assertEqual(self.fs.source_label(), "")

    def test_a_reading_is_returned_as_given(self):
        self.fs.record([{"name": "CPU Fan", "rpm": 1234}], "lhm")
        self.assertEqual(self.fs.measured(), [{"name": "CPU Fan", "rpm": 1234}])
        self.assertEqual(self.fs.source_label(), "LibreHardwareMonitor")

    def test_a_stale_reading_expires(self):
        self.fs.record([{"name": "CPU Fan", "rpm": 900}], "lhm",
                       now=time.time() - 60)
        self.assertEqual(self.fs.measured(), [],
                         "sensor went away 60 s ago, value still shown")

    def test_sensor_gone_clears_the_reading(self):
        self.fs.record([{"name": "CPU Fan", "rpm": 900}], "lhm")
        self.fs.record([], "")
        self.assertEqual(self.fs.measured(), [])
        self.assertEqual(self.fs.source(), "")

    def test_garbage_is_dropped(self):
        self.fs.record([{"name": "", "rpm": 5}, {"name": "X", "rpm": "abc"},
                        {"name": "Y", "rpm": -3}, {"rpm": 7}, None and {},
                        {"name": "Rear", "rpm": "850.0"}], "ohm")
        self.assertEqual(self.fs.measured(), [{"name": "Rear", "rpm": 850}])

    def test_history_holds_measured_samples_only(self):
        t0 = time.time() - 100
        step = self.fs.SAMPLE_INTERVAL_S
        for i in range(5):
            self.fs.record([{"name": "CPU Fan", "rpm": 1000 + i}], "lhm",
                           now=t0 + i * step)
        self.assertEqual(self.fs.history(3600), {"CPU Fan": [1000, 1001, 1002,
                                                             1003, 1004]})

    def test_history_respects_the_sample_interval(self):
        t0 = time.time() - 50
        for i in range(10):                         # ten ticks within 1 s
            self.fs.record([{"name": "CPU Fan", "rpm": 1000}], "lhm",
                           now=t0 + i * 0.1)
        self.assertEqual(self.fs.history(3600), {},
                         "one sample is not a line and must not be drawn")

    def test_usage_page_uses_the_same_interval(self):
        from ui.pages.fan_control.usage_stats import FansUsageStatsPage as U
        self.assertEqual(U._SAMPLE_INTERVAL_S, self.fs.SAMPLE_INTERVAL_S)


class TestSensorTreeFans(unittest.TestCase):
    """The LHM/OHM data.json walker."""

    TREE = {"Text": "Sensor", "Children": [
        {"Text": "Nuvoton NCT6687D", "Children": [
            {"Text": "Fans", "Children": [
                {"Text": "CPU Fan", "Value": "1187 RPM"},
                {"Text": "System Fan #1", "Value": "842 RPM"},
                {"Text": "Pump Fan", "Value": "0 RPM"}]},
            {"Text": "Controls", "Children": [
                {"Text": "CPU Fan", "Value": "45.0 %"}]},
            {"Text": "Voltages", "Children": [
                {"Text": "+12V", "Value": "12.096 V"}]},
            {"Text": "Temperatures", "Children": [
                {"Text": "System", "Value": "34.0 °C"}]}]}]}

    def test_fans_are_read(self):
        from core.live_collector import _walk_sensor_tree
        acc = {}
        _walk_sensor_tree(self.TREE, acc)
        self.assertEqual(acc["fans"], [{"name": "CPU Fan", "rpm": 1187},
                                       {"name": "System Fan #1", "rpm": 842},
                                       {"name": "Pump Fan", "rpm": 0}])

    def test_a_fan_is_not_mistaken_for_a_temperature(self):
        """'System Fan #1 842 RPM' used to land in temp_sys via the 'system'
        keyword, i.e. a motherboard at 842 degrees."""
        from core.live_collector import _walk_sensor_tree
        acc = {}
        _walk_sensor_tree(self.TREE, acc)
        self.assertEqual(acc["temp_sys"], 34.0)
        self.assertEqual(acc["volt_12v"], 12.096)

    def test_percent_controls_are_not_fans(self):
        from core.live_collector import _walk_sensor_tree
        acc = {}
        _walk_sensor_tree(self.TREE, acc)
        self.assertNotIn(45, [f["rpm"] for f in acc["fans"]])


class TestLocaleKeys(unittest.TestCase):

    def test_new_fan_strings_exist_in_both_languages(self):
        import json
        used = set()
        for parts in (("ui", "pages", "fan_control", "hardware_info.py"),
                      ("ui", "pages", "fan_control", "usage_stats.py"),
                      ("ui", "components", "fan_dashboard.py"),
                      ("ui", "components", "yourpc_page.py")):
            used |= set(re.findall(r'"fan_control\.([a-z_]+)"', _read(*parts)))
        self.assertGreater(len(used), 10)
        for lang in ("en", "pl"):
            with open(os.path.join(_ROOT, "locales", f"{lang}.json"),
                      encoding="utf-8") as f:
                have = json.load(f)["fan_control"]
            self.assertEqual(sorted(used - set(have)), [],
                             f"missing in locales/{lang}.json")


if __name__ == "__main__":
    unittest.main()
