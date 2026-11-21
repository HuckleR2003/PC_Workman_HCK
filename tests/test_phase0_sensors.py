"""tests.test_phase0_sensors - phase 0 of the big update (2026-11-20).

LibreHardwareMonitor on a Polish Windows writes "43,5 °C"; float() refused
the comma, so every temperature and voltage with a fraction was dropped and
the CPU temperature was never measured on Windows. The trees below are
copied from the author's PC (MSI PRO B760M-E, i5-12400F, RTX 3050).
"""
import unittest
from unittest import mock


def _node(text, value, kind, sid):
    return {"Text": text, "Value": value, "Type": kind, "SensorId": sid, "Children": []}


def _group(text, *children):
    return {"Text": text, "Value": "", "Children": list(children)}


INTEL_PL = _group("Sensor", _group("DESKTOP", _group(
    "MSI PRO B760M-E DDR4 (MS-7D48)", _group(
        "Nuvoton NCT6687D",
        _group("Voltages",
               _node("+12V", "12,120 V", "Voltage", "/lpc/nct6687d/0/voltage/0"),
               _node("+5V", "5,040 V", "Voltage", "/lpc/nct6687d/0/voltage/1"),
               _node("Vcore", "1,086 V", "Voltage", "/lpc/nct6687d/0/voltage/2"),
               _node("CPU System Agent", "0,902 V", "Voltage", "/lpc/nct6687d/0/voltage/6"),
               _node("AVCC3", "3,336 V", "Voltage", "/lpc/nct6687d/0/voltage/8")),
        _group("Temperatures",
               _node("CPU", "43,5 °C", "Temperature", "/lpc/nct6687d/0/temperature/0"),
               _node("System", "36,5 °C", "Temperature", "/lpc/nct6687d/0/temperature/1"),
               _node("VRM MOS", "38,0 °C", "Temperature", "/lpc/nct6687d/0/temperature/2")),
        _group("Fans", _node("CPU Fan", "372 RPM", "Fan", "/lpc/nct6687d/0/fan/0")))),
    _group("12th Gen Intel Core i5-12400F",
           _group("Voltages",
                  _node("CPU Core", "1,085 V", "Voltage", "/intelcpu/0/voltage/0"),
                  _node("CPU Core #6", "1,080 V", "Voltage", "/intelcpu/0/voltage/6")),
           _group("Temperatures",
                  _node("Core Max", "43,0 °C", "Temperature", "/intelcpu/0/temperature/0"),
                  _node("CPU Package", "42,0 °C", "Temperature", "/intelcpu/0/temperature/8"),
                  _node("CPU Core #1 Distance to TjMax", "57,0 °C", "Temperature",
                        "/intelcpu/0/temperature/9"))),
    _group("NVIDIA GeForce RTX 3050",
           _group("Voltages", _node("GPU Core Voltage", "0,650 V", "Voltage", "/gpu-nvidia/0/voltage/0")),
           _group("Temperatures", _node("GPU Core", "48,0 °C", "Temperature", "/gpu-nvidia/0/temperature/0")))))

AMD = _group("Sensor", _group("AMD Ryzen 5 5600X", _group(
    "Temperatures",
    _node("Core (Tctl/Tdie)", "61.3 °C", "Temperature", "/amdcpu/0/temperature/2"),
    _node("CCD1 (Tdie)", "58.0 °C", "Temperature", "/amdcpu/0/temperature/3"))))


class TestLhmNumbers(unittest.TestCase):

    def test_comma_and_dot_and_spaces(self):
        from core.live_collector import _lhm_number
        self.assertEqual(_lhm_number("43,5 °C"), 43.5)
        self.assertEqual(_lhm_number("12.120 V"), 12.12)
        self.assertEqual(_lhm_number("1 200 RPM"), 1200.0)
        self.assertEqual(_lhm_number("1 200 RPM"), 1200.0)
        self.assertIsNone(_lhm_number(""))
        self.assertIsNone(_lhm_number(None))

    def test_polish_intel_tree(self):
        from core.live_collector import _walk_sensor_tree
        acc = {}
        _walk_sensor_tree(INTEL_PL, acc)
        self.assertEqual(acc["cpu_temp"], 42.0, "CPU Package wins over Core Max")
        self.assertEqual(acc["volt_12v"], 12.12)
        self.assertEqual(acc["volt_5v"], 5.04)
        self.assertEqual(acc["volt_33v"], 3.336)
        self.assertEqual(acc["volt_gpu"], 0.65)
        self.assertEqual(acc["temp_sys"], 36.5)
        self.assertEqual(acc["temp_vrm"], 38.0)
        self.assertIn(acc["volt_vcore"], (1.086, 1.085),
                      "a per-core voltage (#6) never overwrites Vcore")
        self.assertEqual(acc["fans"], [{"name": "CPU Fan", "rpm": 372}])

    def test_a_voltage_is_never_a_temperature(self):
        """'CPU System Agent' (0,902 V) used to land in temp_sys."""
        from core.live_collector import _walk_sensor_tree
        acc = {}
        _walk_sensor_tree(_group("x", _node("CPU System Agent", "0,902 V", "Voltage", "/lpc/x/voltage/6")), acc)
        self.assertNotIn("temp_sys", acc)

    def test_amd_tctl(self):
        from core.live_collector import _walk_sensor_tree
        acc = {}
        _walk_sensor_tree(AMD, acc)
        self.assertEqual(acc["cpu_temp"], 61.3)

    def test_windows_cpu_temperature_comes_from_lhm(self):
        import core.hardware_sensors as hs
        with mock.patch.object(hs, "_lhm_cpu_temp", return_value=44.0), \
                mock.patch.object(hs.psutil, "sensors_temperatures", create=True, return_value={}):
            cpu = hs.get_hardware_sensors()._get_cpu_sensors()
        temps = {k: v for k, v in cpu["sensors"].items() if v.get("type") == "temperature"}
        self.assertIn("Package Temperature", temps)
        self.assertEqual(temps["Package Temperature"]["raw"], 44.0)
        self.assertFalse(any("estimat" in k.lower() for k in temps))

    def test_without_lhm_it_stays_an_estimate(self):
        import core.hardware_sensors as hs
        with mock.patch.object(hs, "_lhm_cpu_temp", return_value=-1.0), \
                mock.patch.object(hs.psutil, "sensors_temperatures", create=True, return_value={}):
            cpu = hs.get_hardware_sensors()._get_cpu_sensors()
        self.assertTrue(any("estimat" in k.lower() for k in cpu["sensors"]))


class TestLhmAnswerIsHonest(unittest.TestCase):

    def _answer(self, mb):
        from hck_gpt.responses.builder import response_builder
        from hck_gpt.intents.parser import ParseResult
        with mock.patch("core.live_collector.fetch_mb_sensors", return_value=mb):
            return "\n".join(response_builder.build(
                ParseResult("lhm_help", 1.0, raw_text="librehardwaremonitor"), "pl"))

    def test_server_answers_but_nothing_is_read(self):
        out = self._answer({"answered": 8085, "source": "lhm", "cpu_temp": -1.0,
                            "volt_12v": -1.0, "volt_vcore": -1.0, "volt_5v": -1.0})
        self.assertNotIn("§OK", out)
        self.assertIn("§WARN", out)
        self.assertIn("administrator", out)

    def test_readings_arrive(self):
        out = self._answer({"answered": 8085, "source": "lhm", "cpu_temp": 43.0,
                            "volt_12v": 12.12, "volt_vcore": 1.08, "volt_5v": 5.04})
        self.assertIn("§OK", out)
        self.assertIn("43°C", out)


class TestStabilityIntegrity(unittest.TestCase):

    def test_a_module_counts_without_its_py_file(self):
        from ui.pages import stability_tests as st
        with mock.patch.object(st.os.path, "isfile", return_value=False):
            ok, size = st.module_status("core/monitor.py")
        self.assertTrue(ok, "in the exe and MSIX the module is bundled, not a file")
        self.assertIsNone(size)
        self.assertFalse(st.module_status("core/does_not_exist.py")[0])


class TestMinecraftJava(unittest.TestCase):

    def test_javaw_is_not_a_game_by_name(self):
        from core.game_detect import is_game, is_minecraft_java
        self.assertFalse(is_game("javaw.exe"))
        self.assertFalse(is_minecraft_java(None))

    def test_javaw_with_minecraft_on_the_command_line(self):
        from core import game_detect
        fake = mock.Mock()
        fake.cmdline.return_value = ["javaw.exe", "-cp", "x", "net.minecraft.client.main.Main"]
        with mock.patch("psutil.Process", return_value=fake):
            self.assertTrue(game_detect.is_game("javaw.exe", pid=1234))
        fake.cmdline.return_value = ["javaw.exe", "-jar", "idea.jar"]
        with mock.patch("psutil.Process", return_value=fake):
            self.assertFalse(game_detect.is_game("javaw.exe", pid=1234))


if __name__ == "__main__":
    unittest.main()
