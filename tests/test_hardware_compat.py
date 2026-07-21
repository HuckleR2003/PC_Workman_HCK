"""tests.test_hardware_compat
Upgrade Readiness: offline library integrity + compatibility verdicts.

The engine must know the real-world traps, not just string-match sockets:
  - B460 shares LGA1200 with 11th gen but cannot run it (hard block)
  - LGA1151 v1 (Z270) and v2 (Z390) look identical and are incompatible
  - B550 never supported Ryzen 1000/2000
  - B450 + 5800X3D works, but only after a BIOS flash
"""
import unittest

from core import hardware_compat as hc
from core.hardware_compat_db import SOCKETS, CHIPSETS, CPUS, GPUS


class TestLibraryIntegrity(unittest.TestCase):
    """The data file is big; these guards keep every future row honest."""

    def test_scale(self):
        s = hc.db_stats()
        self.assertGreaterEqual(s["cpus"], 150)
        self.assertGreaterEqual(s["gpus"], 70)
        self.assertGreaterEqual(s["chipsets"], 50)
        self.assertGreaterEqual(s["total"], 280)

    def test_every_cpu_socket_exists(self):
        for key, row in CPUS.items():
            self.assertIn(row[0], SOCKETS, f"{key}: unknown socket {row[0]}")

    def test_every_chipset_socket_exists(self):
        for key, info in CHIPSETS.items():
            self.assertIn(info["socket"], SOCKETS, f"{key}")

    def test_cpu_rows_sane(self):
        for key, (sock, gen, cores, threads, tdp, igpu) in CPUS.items():
            self.assertGreaterEqual(threads, cores, key)
            self.assertTrue(2 <= cores <= 32, key)
            self.assertTrue(35 <= tdp <= 230, key)
            self.assertIsInstance(igpu, bool, key)
            # F/KF suffix chips must not claim integrated graphics
            if key.endswith(("f", "kf")) and key.startswith("i"):
                self.assertFalse(igpu, f"{key} is an F part but igpu=True")

    def test_gpu_rows_sane(self):
        for key, (vram, tdp, psu, perf, year) in GPUS.items():
            self.assertTrue(2 <= vram <= 32, key)
            self.assertTrue(50 <= tdp <= 600, key)
            self.assertGreater(psu, tdp, f"{key}: PSU rec below card TDP")
            self.assertTrue(1 <= perf <= 100, key)
            self.assertTrue(2013 <= year <= 2026, key)

    def test_perf_ordering_within_families(self):
        """A Ti/Super/XT must never rank below its base card."""
        for key in GPUS:
            for suffix in (" ti", " super", " xt"):
                base = key[: -len(suffix)] if key.endswith(suffix) else None
                if base and base in GPUS:
                    self.assertGreaterEqual(
                        GPUS[key][3], GPUS[base][3],
                        f"{key} ranks below {base}")

    def test_chipset_gen_lists_consistent(self):
        """A generation cannot be both supported and blocked."""
        for key, info in CHIPSETS.items():
            allowed = set(info["native"]) | set(info["bios"]) | set(info["maybe"])
            self.assertFalse(allowed & set(info["no"]), key)


class TestIdentification(unittest.TestCase):

    def test_cpu_spelling_variants(self):
        for text in ("Intel(R) Core(TM) i5-11400F @ 2.60GHz",
                     "i5 11400f", "I5-11400F", "core i5 11400F"):
            rec = hc.identify_cpu(text)
            self.assertIsNotNone(rec, text)
            self.assertEqual(rec["key"], "i5-11400f", text)
        rec = hc.identify_cpu("AMD Ryzen 7 5800X3D 8-Core Processor")
        self.assertEqual(rec["key"], "ryzen 7 5800x3d")
        rec = hc.identify_cpu("Intel(R) Core(TM) Ultra 7 265K")
        self.assertEqual(rec["key"], "ultra 7 265k")
        rec = hc.identify_cpu("Pentium Gold G4560")
        self.assertEqual(rec["key"], "pentium g4560")
        rec = hc.identify_cpu("FX-8350")
        self.assertEqual(rec["key"], "fx-8350")

    def test_cpu_unknown_is_none(self):
        self.assertIsNone(hc.identify_cpu("i7-9750H laptop"))
        self.assertIsNone(hc.identify_cpu("Apple M3 Pro"))
        self.assertIsNone(hc.identify_cpu(""))

    def test_gpu_spelling_variants(self):
        cases = {
            "NVIDIA GeForce RTX 4070 Ti SUPER": "rtx 4070 ti super",
            "rtx4090": "rtx 4090",
            "GTX 1660 Super": "gtx 1660 super",
            "AMD Radeon RX 7900 XTX": "rx 7900 xtx",
            "rx6600": "rx 6600",
            "Intel Arc B580": "arc b580",
        }
        for text, key in cases.items():
            rec = hc.identify_gpu(text)
            self.assertIsNotNone(rec, text)
            self.assertEqual(rec["key"], key, text)

    def test_igpu_strings_do_not_match(self):
        self.assertIsNone(hc.identify_gpu("Intel(R) UHD Graphics 730"))
        self.assertIsNone(hc.identify_gpu("AMD Radeon(TM) Graphics"))

    def test_part_dispatcher(self):
        self.assertEqual(hc.identify_part("nowy i5 11400f")[0], "cpu")
        self.assertEqual(hc.identify_part("rtx 4070 super")[0], "gpu")
        kind, ram = hc.identify_part("ddr4 3600 32gb")
        self.assertEqual(kind, "ram")
        self.assertEqual(ram["ddr"], "DDR4")
        self.assertEqual(ram["speed"], 3600)
        self.assertEqual(ram["gb"], 32)
        self.assertEqual(hc.identify_part("hello world")[0], None)

    def test_chipset_from_board(self):
        cases = {
            "MAG B550M MORTAR (MS-7C94)": "B550",
            "PRIME B460M-A": "B460",
            "ROG STRIX Z390-E GAMING": "Z390",
            "Z97-A": "Z97",
            "B650E-E GAMING WIFI": "B650E",
            "ProArt X870E-CREATOR": "X870E",
            "H81M-K": "H81",
            "TUF GAMING B560M-PLUS": "B560",
        }
        for board, chip in cases.items():
            self.assertEqual(hc.chipset_from_board(board), chip, board)
        self.assertIsNone(hc.chipset_from_board("Surface Book"))


class TestCpuVerdicts(unittest.TestCase):
    """The traps. Platforms are injected so no detector is needed."""

    def test_native_fit(self):
        plat = hc.make_platform(cpu="i5-10400F", board="B560M PRO")
        v = hc.check_cpu_upgrade("i5 11400f", plat)
        self.assertEqual(v["verdict"], "compatible")
        self.assertTrue(v["ok"])

    def test_b460_blocks_11th_gen(self):
        plat = hc.make_platform(cpu="i5-10400F", board="PRIME B460M-A")
        v = hc.check_cpu_upgrade("i5 11400f", plat)
        self.assertEqual(v["verdict"], "chipset_blocked")
        self.assertTrue(v["socket_ok"])          # socket matches, chipset says no
        self.assertFalse(v["ok"])

    def test_z490_needs_bios_for_11th(self):
        plat = hc.make_platform(cpu="i5-10600K", board="Z490 AORUS ELITE")
        v = hc.check_cpu_upgrade("i9-11900k", plat)
        self.assertEqual(v["verdict"], "bios_update")
        self.assertTrue(v["ok"])

    def test_lga1151_cross_generation_trap(self):
        plat = hc.make_platform(cpu="i7-7700K", board="Z270 GAMING PRO")
        v = hc.check_cpu_upgrade("i7 8700k", plat)
        self.assertEqual(v["verdict"], "needs_new_board")
        self.assertIn("LGA1151", v["reasons"][0])

    def test_b450_bios_flash_for_5800x3d(self):
        plat = hc.make_platform(cpu="Ryzen 5 2600", board="B450 TOMAHAWK MAX")
        v = hc.check_cpu_upgrade("ryzen 7 5800x3d", plat)
        self.assertEqual(v["verdict"], "bios_update")

    def test_b550_blocks_zen_plus(self):
        plat = hc.make_platform(cpu="Ryzen 5 3600", board="B550 TOMAHAWK")
        v = hc.check_cpu_upgrade("ryzen 5 2600", plat)
        self.assertEqual(v["verdict"], "chipset_blocked")

    def test_a320_vendor_dependent_for_zen3(self):
        plat = hc.make_platform(cpu="Ryzen 3 1200", board="PRIME A320M-K")
        v = hc.check_cpu_upgrade("ryzen 5 5600", plat)
        self.assertEqual(v["verdict"], "vendor_dependent")

    def test_cross_socket_keeps_ddr4(self):
        """LGA1200 -> AM4: new board, but DDR4 carries over."""
        plat = hc.make_platform(cpu="i5-11400F", board="B560M PRO")
        v = hc.check_cpu_upgrade("ryzen 7 5800x3d", plat)
        self.assertEqual(v["verdict"], "needs_new_board")
        self.assertIsNone(v["ram_change"])
        self.assertTrue(any("carry over" in n for n in v["notes"]))

    def test_cross_socket_ddr4_to_ddr5(self):
        plat = hc.make_platform(cpu="Ryzen 5 5600X", board="B550-F GAMING")
        v = hc.check_cpu_upgrade("ryzen 7 7800x3d", plat)
        self.assertEqual(v["verdict"], "needs_new_board")
        self.assertEqual(v["ram_change"], ("DDR4", "DDR5"))
        self.assertTrue(v["cooler_ok"])          # AM4/AM5 share mounting

    def test_ram_actual_decides_carry_over(self):
        """LGA1700 is dual-gen (DDR4/DDR5). What carries over to another
        board depends on the sticks the user OWNS (resolved via speed)."""
        # DDR5 build (6000 MT/s) -> AM4 board: nothing carries over
        plat = hc.make_platform(cpu="i7-13700K", board="Z790 HERO",
                                ram_speed=6000)
        self.assertEqual(plat["ram_actual"], "DDR5")
        v = hc.check_cpu_upgrade("ryzen 7 5800x3d", plat)
        self.assertEqual(v["ram_change"], ("DDR5", "DDR4"))
        # DDR4 build (3200 MT/s) -> AM4 board: DDR4 carries
        plat = hc.make_platform(cpu="i5-12400F", board="B660M PRO",
                                ram_speed=3200)
        self.assertEqual(plat["ram_actual"], "DDR4")
        v = hc.check_cpu_upgrade("ryzen 7 5800x3d", plat)
        self.assertIsNone(v["ram_change"])
        self.assertEqual(v["ram_carry"], "DDR4")

    def test_lga1200_to_lga1700_cooler_kit(self):
        plat = hc.make_platform(cpu="i5-11400F", board="B560M PRO")
        v = hc.check_cpu_upgrade("i5 13600k", plat)
        self.assertEqual(v["verdict"], "needs_new_board")
        self.assertFalse(v["cooler_ok"])

    def test_unknown_cpu_and_unknown_platform(self):
        v = hc.check_cpu_upgrade("i9-9980HK",
                                 hc.make_platform(cpu="i5-11400F", board="B560"))
        self.assertEqual(v["verdict"], "unknown_part")
        v = hc.check_cpu_upgrade("i5 12400f", hc.make_platform())
        self.assertEqual(v["verdict"], "unknown_current")


class TestGpuVerdicts(unittest.TestCase):

    def test_upgrade_jump(self):
        plat = hc.make_platform(cpu="i5-11400F", board="B560M PRO",
                                gpu="GTX 1660 SUPER")
        v = hc.check_gpu_upgrade("rtx 4070", plat)
        self.assertEqual(v["verdict"], "compatible")
        self.assertGreater(v["perf_delta_pct"], 100)
        self.assertEqual(v["rec_psu"], 650)

    def test_downgrade_detected(self):
        plat = hc.make_platform(cpu="i7-13700K", board="Z790 HERO",
                                gpu="RTX 4080")
        v = hc.check_gpu_upgrade("rtx 4060", plat)
        self.assertEqual(v["verdict"], "downgrade")
        self.assertLess(v["perf_delta_pct"], -50)

    def test_bottleneck_hint_on_old_cpu(self):
        plat = hc.make_platform(cpu="i5-4590", board="B85M-G",
                                gpu="GTX 970")
        v = hc.check_gpu_upgrade("rtx 4080", plat)
        self.assertTrue(v["bottleneck"])

    def test_no_bottleneck_on_matched_pair(self):
        plat = hc.make_platform(cpu="Ryzen 7 7800X3D", board="B650 AORUS",
                                gpu="RTX 3070")
        v = hc.check_gpu_upgrade("rtx 4070 super", plat)
        self.assertFalse(v["bottleneck"])

    def test_gpu_note_surfaces(self):
        plat = hc.make_platform(cpu="Ryzen 5 5600", board="B550M")
        v = hc.check_gpu_upgrade("rx 6500 xt", plat)
        self.assertTrue(any("PCIe" in n for n in v["notes"]))


class TestRamVerdicts(unittest.TestCase):

    def test_ddr5_on_am4_rejected(self):
        plat = hc.make_platform(cpu="Ryzen 5 5600X", board="B550 TOMAHAWK")
        v = hc.check_ram_upgrade("ddr5 6000", plat)
        self.assertEqual(v["verdict"], "incompatible")

    def test_ddr4_3600_on_am4_with_sweet_spot(self):
        plat = hc.make_platform(cpu="Ryzen 5 5600X", board="B550 TOMAHAWK")
        v = hc.check_ram_upgrade("ddr4 3600", plat)
        self.assertEqual(v["verdict"], "compatible")
        self.assertTrue(any("3600" in n for n in v["notes"]))

    def test_b460_speed_lock_caveat(self):
        plat = hc.make_platform(cpu="i5-10400F", board="PRIME B460M-A")
        v = hc.check_ram_upgrade("ddr4 3600", plat)
        self.assertEqual(v["verdict"], "compatible")
        self.assertTrue(any("downclock" in n for n in v["notes"]))

    def test_bare_question_gives_platform_info(self):
        plat = hc.make_platform(cpu="Ryzen 7 7800X3D", board="B650 AORUS")
        v = hc.check_ram_upgrade("", plat)
        self.assertEqual(v["verdict"], "info")
        self.assertIn("DDR5", v["headline"])


class TestAutocomplete(unittest.TestCase):
    """Live part search for the Upgrade Readiness box (2026-07)."""

    def test_partial_queries_return_matches(self):
        for q, needle in [("i5", "i5-"), ("rtx 40", "RTX 40"),
                          ("5800", "5800"), ("rx 7", "RX 7"),
                          ("ryzen 9", "Ryzen 9")]:
            res = hc.search_parts(q, limit=8)
            self.assertTrue(res, f"no matches for {q!r}")
            self.assertTrue(any(needle.lower() in r["label"].lower()
                                for r in res), f"{q!r} -> {res}")

    def test_empty_query_returns_nothing(self):
        self.assertEqual(hc.search_parts(""), [])
        self.assertEqual(hc.search_parts("   "), [])

    def test_results_carry_kind_and_meta(self):
        res = hc.search_parts("rtx 4070", limit=3)
        self.assertTrue(res)
        for r in res:
            self.assertIn(r["kind"], ("cpu", "gpu"))
            self.assertTrue(r["label"] and r["meta"])

    def test_gibberish_returns_nothing(self):
        self.assertEqual(hc.search_parts("zzzqqq123"), [])

    def test_all_parts_covers_full_library(self):
        s = hc.db_stats()
        self.assertEqual(len(hc.all_parts()), s["cpus"] + s["gpus"])


class TestDispatcher(unittest.TestCase):

    def test_routes_by_part_kind(self):
        plat = hc.make_platform(cpu="i5-11400F", board="B560M PRO",
                                gpu="GTX 1660 SUPER")
        self.assertEqual(hc.check_upgrade("i5 12400f", plat)["kind"], "cpu")
        self.assertEqual(hc.check_upgrade("rx 7800 xt", plat)["kind"], "gpu")
        self.assertEqual(hc.check_upgrade("ddr4 3200", plat)["kind"], "ram")
        v = hc.check_upgrade("czajnik elektryczny", plat)
        self.assertEqual(v["verdict"], "unknown_part")

    def test_suggest_upgrades_respects_platform(self):
        """Quick-pick chips: only same-socket CPUs the chipset can run, GPUs
        above the current class, RAM matching the platform's DDR gen."""
        plat = hc.make_platform(cpu="i5-11400F", board="B560M PRO",
                                gpu="GTX 1660 SUPER")
        sug = hc.suggest_upgrades(plat)
        self.assertTrue(sug["cpu"], "no CPU picks for LGA1200")
        for rec in sug["cpu"]:
            self.assertEqual(rec["socket"], "LGA1200", rec["key"])
            self.assertGreater(rec["threads"], 12, rec["key"])
        gpu_perfs = [r["perf"] for r in sug["gpu"]]
        self.assertEqual(gpu_perfs, sorted(gpu_perfs))
        cur_perf = hc.identify_gpu("gtx 1660 super")["perf"]
        for p in gpu_perfs:
            self.assertGreater(p, cur_perf)
        self.assertEqual(sug["ram"], ["DDR4 3600"])

    def test_suggest_upgrades_skips_blocked_chipset(self):
        """B460 owner must NOT be offered 11th-gen chips."""
        plat = hc.make_platform(cpu="i5-10400F", board="PRIME B460M-A")
        sug = hc.suggest_upgrades(plat)
        for rec in sug["cpu"]:
            self.assertNotEqual(rec["gen"], 11, rec["key"])

    def test_labels_are_pretty(self):
        self.assertEqual(hc.identify_cpu("i5 11400f")["label"],
                         "Intel Core i5-11400F")
        self.assertEqual(hc.identify_cpu("ryzen 7 5800x3d")["label"],
                         "AMD Ryzen 7 5800X3D")
        self.assertEqual(hc.identify_gpu("rtx 4070 ti super")["label"],
                         "NVIDIA GeForce RTX 4070 Ti SUPER")
        self.assertEqual(hc.identify_gpu("rx 7900 xtx")["label"],
                         "AMD Radeon RX 7900 XTX")
        self.assertEqual(hc.identify_cpu("FX 8350")["label"], "AMD FX-8350")
        self.assertEqual(hc.identify_gpu("arc b580")["label"],
                         "Intel Arc B580")


class TestSearchRobustness(unittest.TestCase):
    """The page search box feeds check_upgrade with whatever the user types.
    It must NEVER raise - always a dict with a verdict and a headline."""

    GARBAGE = [
        "", "   ", "x" * 500, "czajnik elektryczny", "!!!@#$%^&*",
        "i5", "rtx", "ddr", "i5-99999", "rtx 99999", "ryzen 15 99999x",
        "I5 12400F   ", "RtX4070", "gtx1660super",
        "procesor amd najlepszy", "karta do gier 4k", "ram 32gb",
        "\U0001F525\U0001F525", "i5 11400f; DROP TABLE",
        "ddr5-6000mhz cl30", "core   ultra   7   265k", "FX 8350!!!",
        "arc  b580", "ddr3 vs ddr5",
    ]

    def test_no_input_can_crash_the_checker(self):
        plat = hc.make_platform(cpu="i5-12400F", board="B660M",
                                gpu="RTX 3050", ram_speed=3200)
        for g in self.GARBAGE:
            v = hc.check_upgrade(g, plat)
            self.assertIsInstance(v, dict, repr(g))
            self.assertIn("verdict", v, repr(g))
            self.assertIn("headline", v, repr(g))

    def test_spacing_and_case_still_resolve(self):
        plat = hc.make_platform(cpu="i5-12400F", board="B660M")
        for text, label in [
            ("I5 12400F   ", "Intel Core i5-12400F"),
            ("RtX4070", "NVIDIA GeForce RTX 4070"),
            ("gtx1660super", "NVIDIA GeForce GTX 1660 SUPER"),
            ("core   ultra   7   265k", "Intel Core Ultra 7 265K"),
        ]:
            v = hc.check_upgrade(text, plat)
            self.assertIsNotNone(v.get("target"), text)
            self.assertEqual(v["target"]["label"], label, text)

    def test_ddr3_platform_rejects_ddr5_and_back(self):
        """The user's own example: DDR3-era board vs a DDR5 kit, red both ways."""
        old = hc.make_platform(cpu="i5-4590", board="B85M-G", ram_speed=1600)
        v = hc.check_ram_upgrade("ddr5 6000", old)
        self.assertEqual(v["verdict"], "incompatible")
        new = hc.make_platform(cpu="i7-13700K", board="Z790 HERO",
                               ram_speed=6000)
        v = hc.check_ram_upgrade("ddr3 1600", new)
        self.assertEqual(v["verdict"], "incompatible")

    def test_every_verdict_has_a_badge_and_color(self):
        """UI contract: any verdict the engine can emit maps to a colour AND
        a status badge on the card - no grey mystery states."""
        from ui.pages.upgrade_readiness import _VERDICT_COLOR, _VERDICT_BADGE
        engine_verdicts = {
            "compatible", "info", "bios_update", "vendor_dependent",
            "check_support_list", "downgrade", "chipset_blocked",
            "needs_new_board", "incompatible", "unknown_part",
            "unknown_current",
        }
        for verdict in engine_verdicts:
            self.assertIn(verdict, _VERDICT_COLOR)
            self.assertIn(verdict, _VERDICT_BADGE)


if __name__ == "__main__":
    unittest.main()
