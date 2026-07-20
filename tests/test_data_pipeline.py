"""tests.test_data_pipeline
Guards the hardware-data pipeline invariants (2026-07-16 audit).

The pipeline: core.live_collector is the SINGLE producer of live sensor keys
on the hck_gpt.data.live_sensors bus; UI pages are consumers. Violations of
this rule caused two shipped bugs: dead temps when pages were closed (1.8.1)
and estimated CPU temps racing past the honesty flag into history/learning
whenever My PC was open (found+fixed 2026-07-16).
"""
import glob
import os
import re
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# Live metric keys owned exclusively by core/live_collector.py
_COLLECTOR_OWNED = (
    '"cpu_load"', '"cpu_temp"', '"cpu_temp_src"', '"gpu_temp"', '"gpu_load"',
    '"gpu_vram_mb"', '"gpu_vram_pct"', '"gpu_power"', '"gpu_clk_gr"',
    '"gpu_clk_mem"', '"gpu_ok"', '"mb_volt_12v"', '"mb_volt_5v"',
    '"mb_volt_33v"', '"mb_temp_sys"', '"mb_temp_vrm"', '"disks"',
)


class TestSingleProducerRule(unittest.TestCase):
    """UI pages must never push collector-owned live keys onto the bus."""

    def test_no_ui_page_produces_live_metrics(self):
        offenders = []
        for path in glob.glob(os.path.join(_ROOT, "ui", "**", "*.py"),
                              recursive=True):
            src = _read(path)
            for m in re.finditer(r"_ls\.update\(|live_sensors\.update\(", src):
                window = src[m.start():m.start() + 2000]
                for key in _COLLECTOR_OWNED:
                    if key + ":" in window.replace(" ", "")[:1600] or \
                       key + " " in window[:1600] or key + ":" in window[:1600]:
                        offenders.append(
                            f"{os.path.relpath(path, _ROOT)}: pushes {key}")
        self.assertEqual(offenders, [],
                         "UI modules producing collector-owned live keys "
                         "(consumer-only rule): " + "; ".join(offenders))

    def test_only_collector_spawns_nvidia_smi(self):
        offenders = []
        for path in glob.glob(os.path.join(_ROOT, "**", "*.py"),
                              recursive=True):
            rel = os.path.relpath(path, _ROOT).replace("\\", "/")
            if ("__pycache__" in rel or rel.startswith(("build/", "dist/",
                                                        "tests/"))):
                continue
            if rel == "core/live_collector.py":
                continue
            if re.search(r'\[\s*"nvidia-smi"', _read(path)):
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         f"nvidia-smi subprocess outside live_collector "
                         f"(use fetch_gpu_smi, it is cached): {offenders}")


class TestHonestyFlagInvariant(unittest.TestCase):
    """cpu_temp must never be written to the bus without cpu_temp_src."""

    def test_collector_writes_flag_with_temp(self):
        src = _read(os.path.join(_ROOT, "core", "live_collector.py"))
        self.assertIn('patch["cpu_temp"]', src)
        self.assertIn('patch["cpu_temp_src"]', src)

    def test_no_other_module_writes_cpu_temp_key(self):
        offenders = []
        for path in glob.glob(os.path.join(_ROOT, "ui", "**", "*.py"),
                              recursive=True) + \
                    glob.glob(os.path.join(_ROOT, "hck_gpt", "**", "*.py"),
                              recursive=True):
            if "__pycache__" in path:
                continue
            src = _read(path)
            for m in re.finditer(r"_ls\.update\(|live_sensors\.update\(", src):
                if '"cpu_temp":' in src[m.start():m.start() + 1600]:
                    offenders.append(os.path.relpath(path, _ROOT))
        self.assertEqual(offenders, [],
                         f"cpu_temp pushed outside the collector "
                         f"(honesty-flag bypass): {offenders}")


class TestOneHardwareIdentity(unittest.TestCase):
    """hck_GPT's scanner must source identity from core.hardware_detector."""

    def test_scanner_does_not_import_dead_wmi_package(self):
        # `import wmi` was never installed/bundled - the scan silently failed
        # on every machine. The scanner now reads the working detector.
        src = _read(os.path.join(_ROOT, "hck_gpt", "context",
                                 "hardware_scanner.py"))
        self.assertNotRegex(src, r"(?m)^\s*import wmi$",
                            "hardware_scanner must not import the never-"
                            "installed `wmi` package")
        self.assertIn("hardware_detector", src,
                      "hardware_scanner should source core.hardware_detector")

    def test_startup_warms_identity_cache(self):
        src = _read(os.path.join(_ROOT, "startup.py"))
        self.assertIn("splash-warmup", src,
                      "splash-time warm-up thread missing from startup")
        self.assertIn("warm_metrics_cache", src,
                      "services/startup metric warm-up missing from startup")


if __name__ == "__main__":
    unittest.main()
