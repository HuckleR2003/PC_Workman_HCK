# core/hardware_compat_db.py
"""
Offline hardware library for Upgrade Readiness.

Pure data, no logic - the engine lives in core/hardware_compat.py and this
module is its ONE data source (ARCHITECTURE.md rule: extend this file, never
start a second library). Numbers come from public vendor spec sheets
(Intel ARK, AMD product pages, board-partner CPU support lists), rounded.

Layout:
  SOCKETS   - platform facts (vendor, memory generations, official max speed,
              cooler mount group)
  CHIPSETS  - per-chipset CPU-generation support: native / bios (needs a BIOS
              update) / maybe (board-vendor dependent) / no (blocked even
              though the socket matches - the classic traps)
  CPUS      - (socket, gen, cores, threads, tdp_w, igpu)
  GPUS      - (vram_gb, tdp_w, recommended_psu_w, perf_index, year)
  GPU_NOTES - free-text caveats per GPU key

Generation key ("gen") is the CHIPSET-SUPPORT generation, not marketing:
  Intel : 4=Haswell 6=Skylake 7=Kaby 8=Coffee 9=Coffee-R 10=Comet
          11=Rocket 12=Alder 13=Raptor 14=Raptor-R 15=Arrow (Core Ultra 200S)
  AMD   : 0=FX 1=Zen(+2000G APU) 2=Zen+(+3000G APU) 3=Zen2(+4000G APU)
          5=Zen3 7=Zen4 8=Zen4 APU (8000G) 9=Zen5
GPU perf_index is a coarse relative class (1440p raster, RTX 5090 = 100).
It exists to say "big jump / sidegrade / downgrade", never as a benchmark.
"""

DB_VERSION = "2026.07"

# ── Sockets ──────────────────────────────────────────────────────────────────
SOCKETS = {
    "LGA1150":   {"vendor": "intel", "ram": ["DDR3"], "ram_max": {"DDR3": 1600},
                  "mount": "LGA115x/1200"},
    "LGA1151":   {"vendor": "intel", "ram": ["DDR4"], "ram_max": {"DDR4": 2400},
                  "mount": "LGA115x/1200"},
    "LGA1151-2": {"vendor": "intel", "ram": ["DDR4"], "ram_max": {"DDR4": 2666},
                  "mount": "LGA115x/1200"},
    "LGA1200":   {"vendor": "intel", "ram": ["DDR4"], "ram_max": {"DDR4": 3200},
                  "mount": "LGA115x/1200"},
    "LGA1700":   {"vendor": "intel", "ram": ["DDR4", "DDR5"],
                  "ram_max": {"DDR4": 3200, "DDR5": 5600}, "mount": "LGA1700"},
    "LGA1851":   {"vendor": "intel", "ram": ["DDR5"], "ram_max": {"DDR5": 6400},
                  "mount": "LGA1700"},
    "AM3+":      {"vendor": "amd", "ram": ["DDR3"], "ram_max": {"DDR3": 1866},
                  "mount": "AM2-AM3+"},
    "AM4":       {"vendor": "amd", "ram": ["DDR4"], "ram_max": {"DDR4": 3200},
                  "mount": "AM4/AM5"},
    "AM5":       {"vendor": "amd", "ram": ["DDR5"], "ram_max": {"DDR5": 5600},
                  "mount": "AM4/AM5"},
}

# ── Chipsets: which CPU generations each board family really runs ────────────
def _cs(socket, native, bios=(), maybe=(), no=()):
    return {"socket": socket, "native": list(native), "bios": list(bios),
            "maybe": list(maybe), "no": list(no)}

CHIPSETS = {
    # Intel 8/9-series (LGA1150, Haswell)
    "H81":  _cs("LGA1150", [4]), "B85": _cs("LGA1150", [4]),
    "H87":  _cs("LGA1150", [4]), "Z87": _cs("LGA1150", [4]),
    "H97":  _cs("LGA1150", [4]), "Z97": _cs("LGA1150", [4]),
    # Intel 100/200-series (LGA1151, Skylake/Kaby)
    "H110": _cs("LGA1151", [6], bios=[7]), "B150": _cs("LGA1151", [6], bios=[7]),
    "H170": _cs("LGA1151", [6], bios=[7]), "Z170": _cs("LGA1151", [6], bios=[7]),
    "B250": _cs("LGA1151", [6, 7]), "H270": _cs("LGA1151", [6, 7]),
    "Z270": _cs("LGA1151", [6, 7]),
    # Intel 300-series (LGA1151-2, Coffee Lake) - NOT cross-compatible with 100/200
    "H310": _cs("LGA1151-2", [8], bios=[9]), "B360": _cs("LGA1151-2", [8], bios=[9]),
    "H370": _cs("LGA1151-2", [8], bios=[9]), "Z370": _cs("LGA1151-2", [8], bios=[9]),
    "B365": _cs("LGA1151-2", [8, 9]), "Z390": _cs("LGA1151-2", [8, 9]),
    # Intel 400-series (LGA1200) - H410/B460 can NOT run 11th gen (the trap)
    "H410": _cs("LGA1200", [10], no=[11]), "B460": _cs("LGA1200", [10], no=[11]),
    "H470": _cs("LGA1200", [10], bios=[11]), "Z490": _cs("LGA1200", [10], bios=[11]),
    # Intel 500-series (LGA1200)
    "H510": _cs("LGA1200", [10, 11]), "B560": _cs("LGA1200", [10, 11]),
    "H570": _cs("LGA1200", [10, 11]), "Z590": _cs("LGA1200", [10, 11]),
    # Intel 600-series (LGA1700) - 13th/14th after BIOS update
    "H610": _cs("LGA1700", [12], bios=[13, 14]), "B660": _cs("LGA1700", [12], bios=[13, 14]),
    "H670": _cs("LGA1700", [12], bios=[13, 14]), "Z690": _cs("LGA1700", [12], bios=[13, 14]),
    # Intel 700-series (LGA1700) - 14th gen safe after BIOS update on early boards
    "B760": _cs("LGA1700", [12, 13], bios=[14]), "H770": _cs("LGA1700", [12, 13], bios=[14]),
    "Z790": _cs("LGA1700", [12, 13], bios=[14]),
    # Intel 800-series (LGA1851, Core Ultra 200S)
    "H810": _cs("LGA1851", [15]), "B860": _cs("LGA1851", [15]),
    "Z890": _cs("LGA1851", [15]),
    # AMD AM3+ (FX)
    "760G": _cs("AM3+", [0]), "970": _cs("AM3+", [0]),
    "990X": _cs("AM3+", [0]), "990FX": _cs("AM3+", [0]),
    # AMD AM4 300-series - Zen3 came back via 2022 AGESA; A320 vendor-dependent
    "A320": _cs("AM4", [1, 2], bios=[3], maybe=[5]),
    "B350": _cs("AM4", [1, 2], bios=[3, 5]),
    "X370": _cs("AM4", [1, 2], bios=[3, 5]),
    # AMD AM4 400-series - Ryzen 5000 needs a BIOS update
    "B450": _cs("AM4", [1, 2, 3], bios=[5]),
    "X470": _cs("AM4", [1, 2, 3], bios=[5]),
    # AMD AM4 500-series - Zen/Zen+ (incl. 3000G APUs) are NOT supported
    "A520": _cs("AM4", [3, 5], no=[1, 2]),
    "B550": _cs("AM4", [3, 5], no=[1, 2]),
    "X570": _cs("AM4", [2, 3], bios=[5], no=[1]),
    # AMD AM5 600-series - Ryzen 9000 after BIOS update
    "A620":  _cs("AM5", [7, 8], bios=[9]), "B650": _cs("AM5", [7, 8], bios=[9]),
    "B650E": _cs("AM5", [7, 8], bios=[9]), "X670": _cs("AM5", [7, 8], bios=[9]),
    "X670E": _cs("AM5", [7, 8], bios=[9]),
    # AMD AM5 800-series
    "B840": _cs("AM5", [7, 8, 9]), "B850": _cs("AM5", [7, 8, 9]),
    "X870": _cs("AM5", [7, 8, 9]), "X870E": _cs("AM5", [7, 8, 9]),
}

# ── CPUs: key -> (socket, gen, cores, threads, tdp_w, igpu) ──────────────────
CPUS = {
    # Intel LGA1150 (4th gen, Haswell)
    "i3-4130": ("LGA1150", 4, 2, 4, 54, True),
    "i3-4160": ("LGA1150", 4, 2, 4, 54, True),
    "i5-4460": ("LGA1150", 4, 4, 4, 84, True),
    "i5-4570": ("LGA1150", 4, 4, 4, 84, True),
    "i5-4590": ("LGA1150", 4, 4, 4, 84, True),
    "i5-4690k": ("LGA1150", 4, 4, 4, 88, True),
    "i7-4770": ("LGA1150", 4, 4, 8, 84, True),
    "i7-4770k": ("LGA1150", 4, 4, 8, 84, True),
    "i7-4790": ("LGA1150", 4, 4, 8, 84, True),
    "i7-4790k": ("LGA1150", 4, 4, 8, 88, True),
    "xeon e3-1231 v3": ("LGA1150", 4, 4, 8, 80, False),
    # Intel LGA1151 (6th gen, Skylake)
    "i3-6100": ("LGA1151", 6, 2, 4, 51, True),
    "i5-6400": ("LGA1151", 6, 4, 4, 65, True),
    "i5-6500": ("LGA1151", 6, 4, 4, 65, True),
    "i5-6600k": ("LGA1151", 6, 4, 4, 91, True),
    "i7-6700": ("LGA1151", 6, 4, 8, 65, True),
    "i7-6700k": ("LGA1151", 6, 4, 8, 91, True),
    # Intel LGA1151 (7th gen, Kaby Lake)
    "pentium g4560": ("LGA1151", 7, 2, 4, 54, True),
    "i3-7100": ("LGA1151", 7, 2, 4, 51, True),
    "i5-7400": ("LGA1151", 7, 4, 4, 65, True),
    "i5-7500": ("LGA1151", 7, 4, 4, 65, True),
    "i5-7600k": ("LGA1151", 7, 4, 4, 91, True),
    "i7-7700": ("LGA1151", 7, 4, 8, 65, True),
    "i7-7700k": ("LGA1151", 7, 4, 8, 91, True),
    # Intel LGA1151-2 (8th gen, Coffee Lake)
    "pentium g5400": ("LGA1151-2", 8, 2, 4, 58, True),
    "i3-8100": ("LGA1151-2", 8, 4, 4, 65, True),
    "i3-8350k": ("LGA1151-2", 8, 4, 4, 91, True),
    "i5-8400": ("LGA1151-2", 8, 6, 6, 65, True),
    "i5-8500": ("LGA1151-2", 8, 6, 6, 65, True),
    "i5-8600k": ("LGA1151-2", 8, 6, 6, 95, True),
    "i7-8700": ("LGA1151-2", 8, 6, 12, 65, True),
    "i7-8700k": ("LGA1151-2", 8, 6, 12, 95, True),
    # Intel LGA1151-2 (9th gen, Coffee Lake Refresh)
    "i3-9100f": ("LGA1151-2", 9, 4, 4, 65, False),
    "i5-9400": ("LGA1151-2", 9, 6, 6, 65, True),
    "i5-9400f": ("LGA1151-2", 9, 6, 6, 65, False),
    "i5-9600k": ("LGA1151-2", 9, 6, 6, 95, True),
    "i7-9700": ("LGA1151-2", 9, 8, 8, 65, True),
    "i7-9700f": ("LGA1151-2", 9, 8, 8, 65, False),
    "i7-9700k": ("LGA1151-2", 9, 8, 8, 95, True),
    "i9-9900k": ("LGA1151-2", 9, 8, 16, 95, True),
    "i9-9900kf": ("LGA1151-2", 9, 8, 16, 95, False),
    # Intel LGA1200 (10th gen, Comet Lake)
    "pentium g6400": ("LGA1200", 10, 2, 4, 58, True),
    "i3-10100": ("LGA1200", 10, 4, 8, 65, True),
    "i3-10100f": ("LGA1200", 10, 4, 8, 65, False),
    "i3-10105f": ("LGA1200", 10, 4, 8, 65, False),
    "i5-10400": ("LGA1200", 10, 6, 12, 65, True),
    "i5-10400f": ("LGA1200", 10, 6, 12, 65, False),
    "i5-10500": ("LGA1200", 10, 6, 12, 65, True),
    "i5-10600k": ("LGA1200", 10, 6, 12, 125, True),
    "i5-10600kf": ("LGA1200", 10, 6, 12, 125, False),
    "i7-10700": ("LGA1200", 10, 8, 16, 65, True),
    "i7-10700f": ("LGA1200", 10, 8, 16, 65, False),
    "i7-10700k": ("LGA1200", 10, 8, 16, 125, True),
    "i7-10700kf": ("LGA1200", 10, 8, 16, 125, False),
    "i9-10850k": ("LGA1200", 10, 10, 20, 125, True),
    "i9-10900k": ("LGA1200", 10, 10, 20, 125, True),
    "i9-10900kf": ("LGA1200", 10, 10, 20, 125, False),
    # Intel LGA1200 (11th gen, Rocket Lake)
    "i5-11400": ("LGA1200", 11, 6, 12, 65, True),
    "i5-11400f": ("LGA1200", 11, 6, 12, 65, False),
    "i5-11500": ("LGA1200", 11, 6, 12, 65, True),
    "i5-11600k": ("LGA1200", 11, 6, 12, 125, True),
    "i5-11600kf": ("LGA1200", 11, 6, 12, 125, False),
    "i7-11700": ("LGA1200", 11, 8, 16, 65, True),
    "i7-11700f": ("LGA1200", 11, 8, 16, 65, False),
    "i7-11700k": ("LGA1200", 11, 8, 16, 125, True),
    "i7-11700kf": ("LGA1200", 11, 8, 16, 125, False),
    "i9-11900k": ("LGA1200", 11, 8, 16, 125, True),
    "i9-11900kf": ("LGA1200", 11, 8, 16, 125, False),
    # Intel LGA1700 (12th gen, Alder Lake)
    "i3-12100": ("LGA1700", 12, 4, 8, 60, True),
    "i3-12100f": ("LGA1700", 12, 4, 8, 58, False),
    "i5-12400": ("LGA1700", 12, 6, 12, 65, True),
    "i5-12400f": ("LGA1700", 12, 6, 12, 65, False),
    "i5-12500": ("LGA1700", 12, 6, 12, 65, True),
    "i5-12600k": ("LGA1700", 12, 10, 16, 125, True),
    "i5-12600kf": ("LGA1700", 12, 10, 16, 125, False),
    "i7-12700": ("LGA1700", 12, 12, 20, 65, True),
    "i7-12700f": ("LGA1700", 12, 12, 20, 65, False),
    "i7-12700k": ("LGA1700", 12, 12, 20, 125, True),
    "i7-12700kf": ("LGA1700", 12, 12, 20, 125, False),
    "i9-12900k": ("LGA1700", 12, 16, 24, 125, True),
    "i9-12900kf": ("LGA1700", 12, 16, 24, 125, False),
    "i9-12900ks": ("LGA1700", 12, 16, 24, 150, True),
    # Intel LGA1700 (13th gen, Raptor Lake)
    "i3-13100": ("LGA1700", 13, 4, 8, 60, True),
    "i3-13100f": ("LGA1700", 13, 4, 8, 58, False),
    "i5-13400": ("LGA1700", 13, 10, 16, 65, True),
    "i5-13400f": ("LGA1700", 13, 10, 16, 65, False),
    "i5-13500": ("LGA1700", 13, 14, 20, 65, True),
    "i5-13600k": ("LGA1700", 13, 14, 20, 125, True),
    "i5-13600kf": ("LGA1700", 13, 14, 20, 125, False),
    "i7-13700": ("LGA1700", 13, 16, 24, 65, True),
    "i7-13700f": ("LGA1700", 13, 16, 24, 65, False),
    "i7-13700k": ("LGA1700", 13, 16, 24, 125, True),
    "i7-13700kf": ("LGA1700", 13, 16, 24, 125, False),
    "i9-13900k": ("LGA1700", 13, 24, 32, 125, True),
    "i9-13900kf": ("LGA1700", 13, 24, 32, 125, False),
    "i9-13900ks": ("LGA1700", 13, 24, 32, 150, True),
    # Intel LGA1700 (14th gen, Raptor Lake Refresh)
    "i3-14100": ("LGA1700", 14, 4, 8, 60, True),
    "i3-14100f": ("LGA1700", 14, 4, 8, 58, False),
    "i5-14400": ("LGA1700", 14, 10, 16, 65, True),
    "i5-14400f": ("LGA1700", 14, 10, 16, 65, False),
    "i5-14500": ("LGA1700", 14, 14, 20, 65, True),
    "i5-14600k": ("LGA1700", 14, 14, 20, 125, True),
    "i5-14600kf": ("LGA1700", 14, 14, 20, 125, False),
    "i7-14700": ("LGA1700", 14, 20, 28, 65, True),
    "i7-14700f": ("LGA1700", 14, 20, 28, 65, False),
    "i7-14700k": ("LGA1700", 14, 20, 28, 125, True),
    "i7-14700kf": ("LGA1700", 14, 20, 28, 125, False),
    "i9-14900k": ("LGA1700", 14, 24, 32, 125, True),
    "i9-14900kf": ("LGA1700", 14, 24, 32, 125, False),
    "i9-14900ks": ("LGA1700", 14, 24, 32, 150, True),
    # Intel LGA1851 (Core Ultra 200S, Arrow Lake - no hyperthreading)
    "ultra 5 225": ("LGA1851", 15, 10, 10, 65, True),
    "ultra 5 245k": ("LGA1851", 15, 14, 14, 125, True),
    "ultra 5 245kf": ("LGA1851", 15, 14, 14, 125, False),
    "ultra 7 265k": ("LGA1851", 15, 20, 20, 125, True),
    "ultra 7 265kf": ("LGA1851", 15, 20, 20, 125, False),
    "ultra 9 285k": ("LGA1851", 15, 24, 24, 125, True),
    # AMD AM3+ (FX)
    "fx-6300": ("AM3+", 0, 6, 6, 95, False),
    "fx-8320": ("AM3+", 0, 8, 8, 125, False),
    "fx-8350": ("AM3+", 0, 8, 8, 125, False),
    # AMD AM4 - Zen (1000 + 2000G APUs)
    "ryzen 3 1200": ("AM4", 1, 4, 4, 65, False),
    "ryzen 5 1400": ("AM4", 1, 4, 8, 65, False),
    "ryzen 5 1600": ("AM4", 1, 6, 12, 65, False),
    "ryzen 5 1600x": ("AM4", 1, 6, 12, 95, False),
    "ryzen 7 1700": ("AM4", 1, 8, 16, 65, False),
    "ryzen 7 1700x": ("AM4", 1, 8, 16, 95, False),
    "ryzen 7 1800x": ("AM4", 1, 8, 16, 95, False),
    "ryzen 3 2200g": ("AM4", 1, 4, 4, 65, True),
    "ryzen 5 2400g": ("AM4", 1, 4, 8, 65, True),
    # AMD AM4 - Zen+ (2000 + 3000G APUs)
    "ryzen 5 2600": ("AM4", 2, 6, 12, 65, False),
    "ryzen 5 2600x": ("AM4", 2, 6, 12, 95, False),
    "ryzen 7 2700": ("AM4", 2, 8, 16, 65, False),
    "ryzen 7 2700x": ("AM4", 2, 8, 16, 105, False),
    "ryzen 3 3200g": ("AM4", 2, 4, 4, 65, True),
    "ryzen 5 3400g": ("AM4", 2, 4, 8, 65, True),
    # AMD AM4 - Zen 2 (3000 + 4000G APUs)
    "ryzen 3 3100": ("AM4", 3, 4, 8, 65, False),
    "ryzen 3 3300x": ("AM4", 3, 4, 8, 65, False),
    "ryzen 5 3600": ("AM4", 3, 6, 12, 65, False),
    "ryzen 5 3600x": ("AM4", 3, 6, 12, 95, False),
    "ryzen 7 3700x": ("AM4", 3, 8, 16, 65, False),
    "ryzen 7 3800x": ("AM4", 3, 8, 16, 105, False),
    "ryzen 9 3900x": ("AM4", 3, 12, 24, 105, False),
    "ryzen 9 3950x": ("AM4", 3, 16, 32, 105, False),
    "ryzen 5 4600g": ("AM4", 3, 6, 12, 65, True),
    # AMD AM4 - Zen 3 (5000)
    "ryzen 5 5500": ("AM4", 5, 6, 12, 65, False),
    "ryzen 5 5600": ("AM4", 5, 6, 12, 65, False),
    "ryzen 5 5600x": ("AM4", 5, 6, 12, 65, False),
    "ryzen 5 5600g": ("AM4", 5, 6, 12, 65, True),
    "ryzen 7 5700g": ("AM4", 5, 8, 16, 65, True),
    "ryzen 7 5700x": ("AM4", 5, 8, 16, 65, False),
    "ryzen 7 5700x3d": ("AM4", 5, 8, 16, 105, False),
    "ryzen 7 5800x": ("AM4", 5, 8, 16, 105, False),
    "ryzen 7 5800x3d": ("AM4", 5, 8, 16, 105, False),
    "ryzen 9 5900x": ("AM4", 5, 12, 24, 105, False),
    "ryzen 9 5950x": ("AM4", 5, 16, 32, 105, False),
    # AMD AM5 - Zen 4 (7000)
    "ryzen 5 7500f": ("AM5", 7, 6, 12, 65, False),
    "ryzen 5 7600": ("AM5", 7, 6, 12, 65, True),
    "ryzen 5 7600x": ("AM5", 7, 6, 12, 105, True),
    "ryzen 7 7700": ("AM5", 7, 8, 16, 65, True),
    "ryzen 7 7700x": ("AM5", 7, 8, 16, 105, True),
    "ryzen 7 7800x3d": ("AM5", 7, 8, 16, 120, True),
    "ryzen 9 7900": ("AM5", 7, 12, 24, 65, True),
    "ryzen 9 7900x": ("AM5", 7, 12, 24, 170, True),
    "ryzen 9 7900x3d": ("AM5", 7, 12, 24, 120, True),
    "ryzen 9 7950x": ("AM5", 7, 16, 32, 170, True),
    "ryzen 9 7950x3d": ("AM5", 7, 16, 32, 120, True),
    # AMD AM5 - Zen 4 APU (8000G)
    "ryzen 5 8600g": ("AM5", 8, 6, 12, 65, True),
    "ryzen 7 8700g": ("AM5", 8, 8, 16, 65, True),
    # AMD AM5 - Zen 5 (9000)
    "ryzen 5 9600x": ("AM5", 9, 6, 12, 65, True),
    "ryzen 7 9700x": ("AM5", 9, 8, 16, 65, True),
    "ryzen 7 9800x3d": ("AM5", 9, 8, 16, 120, True),
    "ryzen 9 9900x": ("AM5", 9, 12, 24, 120, True),
    "ryzen 9 9900x3d": ("AM5", 9, 12, 24, 120, True),
    "ryzen 9 9950x": ("AM5", 9, 16, 32, 170, True),
    "ryzen 9 9950x3d": ("AM5", 9, 16, 32, 170, True),
    # ── Additions (2026-07): budget/mainstream people actually search ──
    "ryzen 3 4100": ("AM4", 3, 4, 8, 65, False),
    "ryzen 5 4500": ("AM4", 3, 6, 12, 65, False),
    "ryzen 5 5500gt": ("AM4", 5, 6, 12, 65, True),
    "ryzen 5 5600gt": ("AM4", 5, 6, 12, 65, True),
    "ryzen 5 8400f": ("AM5", 8, 6, 12, 65, False),
    "ryzen 5 8500g": ("AM5", 8, 6, 12, 65, True),
    "ryzen 5 9600": ("AM5", 9, 6, 12, 65, True),
    "ryzen 7 9700": ("AM5", 9, 8, 16, 65, True),
    "i5-11600": ("LGA1200", 11, 6, 12, 65, True),
    "i5-12600": ("LGA1700", 12, 6, 12, 65, True),
    "i9-12900": ("LGA1700", 12, 16, 24, 65, True),
    "i9-13900": ("LGA1700", 13, 24, 32, 65, True),
    "i9-14900": ("LGA1700", 14, 24, 32, 65, True),
    "ultra 5 235": ("LGA1851", 15, 14, 14, 65, True),
}

# ── GPUs: key -> (vram_gb, tdp_w, recommended_psu_w, perf_index, year) ───────
GPUS = {
    # NVIDIA GTX
    "gtx 750 ti": (2, 60, 300, 2, 2014),
    "gtx 960": (2, 120, 400, 4, 2015),
    "gtx 970": (4, 145, 500, 6, 2014),
    "gtx 980": (4, 165, 500, 7, 2014),
    "gtx 980 ti": (6, 250, 600, 9, 2015),
    "gtx 1050 ti": (4, 75, 300, 4, 2016),
    "gtx 1060": (6, 120, 400, 8, 2016),
    "gtx 1070": (8, 150, 500, 12, 2016),
    "gtx 1070 ti": (8, 180, 500, 13, 2017),
    "gtx 1080": (8, 180, 500, 15, 2016),
    "gtx 1080 ti": (11, 250, 600, 19, 2017),
    "gtx 1650": (4, 75, 300, 6, 2019),
    "gtx 1650 super": (4, 100, 350, 8, 2019),
    "gtx 1660": (6, 120, 450, 10, 2019),
    "gtx 1660 super": (6, 125, 450, 11, 2019),
    "gtx 1660 ti": (6, 120, 450, 11, 2019),
    # NVIDIA RTX 20
    "rtx 2060": (6, 160, 500, 16, 2019),
    "rtx 2060 super": (8, 175, 550, 18, 2019),
    "rtx 2070": (8, 175, 550, 19, 2018),
    "rtx 2070 super": (8, 215, 650, 22, 2019),
    "rtx 2080": (8, 215, 650, 24, 2018),
    "rtx 2080 super": (8, 250, 650, 25, 2019),
    "rtx 2080 ti": (11, 250, 650, 30, 2018),
    # NVIDIA RTX 30
    "rtx 3050": (8, 130, 550, 13, 2022),
    "rtx 3060": (12, 170, 550, 20, 2021),
    "rtx 3060 ti": (8, 200, 600, 27, 2020),
    "rtx 3070": (8, 220, 650, 31, 2020),
    "rtx 3070 ti": (8, 290, 750, 33, 2021),
    "rtx 3080": (10, 320, 750, 39, 2020),
    "rtx 3080 ti": (12, 350, 750, 42, 2021),
    "rtx 3090": (24, 350, 750, 43, 2020),
    "rtx 3090 ti": (24, 450, 850, 46, 2022),
    # NVIDIA RTX 40
    "rtx 4060": (8, 115, 550, 26, 2023),
    "rtx 4060 ti": (8, 160, 550, 32, 2023),
    "rtx 4070": (12, 200, 650, 44, 2023),
    "rtx 4070 super": (12, 220, 650, 49, 2024),
    "rtx 4070 ti": (12, 285, 700, 54, 2023),
    "rtx 4070 ti super": (16, 285, 700, 57, 2024),
    "rtx 4080": (16, 320, 750, 65, 2022),
    "rtx 4080 super": (16, 320, 750, 66, 2024),
    "rtx 4090": (24, 450, 850, 82, 2022),
    # NVIDIA RTX 50
    "rtx 5060": (8, 145, 550, 30, 2025),
    "rtx 5060 ti": (16, 180, 600, 36, 2025),
    "rtx 5070": (12, 250, 650, 51, 2025),
    "rtx 5070 ti": (16, 300, 750, 63, 2025),
    "rtx 5080": (16, 360, 850, 74, 2025),
    "rtx 5090": (32, 575, 1000, 100, 2025),
    # AMD Radeon
    "rx 570": (4, 150, 450, 5, 2017),
    "rx 580": (8, 185, 500, 6, 2017),
    "rx 590": (8, 225, 550, 7, 2018),
    "rx 5500 xt": (8, 130, 450, 9, 2019),
    "rx 5600 xt": (6, 150, 550, 14, 2020),
    "rx 5700": (8, 180, 600, 16, 2019),
    "rx 5700 xt": (8, 225, 600, 18, 2019),
    "rx 6500 xt": (4, 107, 400, 10, 2022),
    "rx 6600": (8, 132, 450, 20, 2021),
    "rx 6600 xt": (8, 160, 500, 23, 2021),
    "rx 6650 xt": (8, 176, 500, 24, 2022),
    "rx 6700 xt": (12, 230, 650, 30, 2021),
    "rx 6750 xt": (12, 250, 650, 31, 2022),
    "rx 6800": (16, 250, 650, 36, 2020),
    "rx 6800 xt": (16, 300, 750, 40, 2020),
    "rx 6900 xt": (16, 300, 850, 42, 2020),
    "rx 6950 xt": (16, 335, 850, 45, 2022),
    "rx 7600": (8, 165, 550, 26, 2023),
    "rx 7600 xt": (16, 190, 600, 28, 2024),
    "rx 7700 xt": (12, 245, 700, 38, 2023),
    "rx 7800 xt": (16, 263, 700, 47, 2023),
    "rx 7900 gre": (16, 260, 700, 52, 2024),
    "rx 7900 xt": (20, 315, 750, 60, 2022),
    "rx 7900 xtx": (24, 355, 800, 68, 2022),
    "rx 9060 xt": (16, 160, 550, 33, 2025),
    "rx 9070": (16, 220, 650, 56, 2025),
    "rx 9070 xt": (16, 304, 750, 64, 2025),
    # Intel Arc
    "arc a380": (6, 75, 400, 6, 2022),
    "arc a750": (8, 225, 600, 18, 2022),
    "arc a770": (16, 225, 600, 20, 2022),
    "arc b570": (10, 150, 500, 20, 2024),
    "arc b580": (12, 190, 600, 24, 2024),
    # ── Additions (2026-07): common budget + newer cards (all reachable) ──
    "arc a580": (8, 175, 550, 17, 2023),
    "gtx 1050": (2, 75, 300, 3, 2016),
    "gtx 1630": (4, 75, 300, 4, 2022),
    "rx 6400": (4, 53, 400, 8, 2022),
    "rx 9060": (8, 150, 500, 30, 2025),
}

GPU_NOTES = {
    "gtx 1060": "Data is for the 6 GB model (the 3 GB one is cut down).",
    "rx 6500 xt": "Runs at PCIe x4 - loses noticeable performance on PCIe 3.0 boards.",
    "rtx 4080": "Uses the 16-pin 12VHPWR connector (adapter in the box, native ATX 3.x cable recommended).",
    "rtx 4080 super": "Uses the 16-pin 12VHPWR connector (adapter in the box, native ATX 3.x cable recommended).",
    "rtx 4090": "Uses the 16-pin 12VHPWR connector - a modern ATX 3.x PSU is strongly recommended.",
    "rtx 5080": "Uses the 12V-2x6 connector - a modern ATX 3.x PSU is strongly recommended.",
    "rtx 5090": "Uses the 12V-2x6 connector and draws 575 W alone - ATX 3.1 PSU required in practice.",
}


# ── Record accessors (the engine reads through these) ────────────────────────
def _fmt_model(token: str) -> str:
    """'i5-11400f' -> 'i5-11400F', 'ryzen 7 5800x3d' -> 'Ryzen 7 5800X3D',
    'rx 7900 xtx' -> 'RX 7900 XTX', 'gtx 1660 super' -> 'GTX 1660 SUPER'."""
    up_words = {"rx", "gtx", "rtx", "xt", "xtx", "gre", "super"}
    out = []
    for w in token.split():
        if w in up_words:
            out.append(w.upper())
        elif w == "arc":
            out.append("Arc")
        elif w.startswith("fx-"):              # fx-8350 -> FX-8350
            out.append("FX-" + w[3:])
        elif w == "ti":
            out.append("Ti")
        elif w[:1] == "i" and "-" in w:            # i5-11400f
            head, _, tail = w.partition("-")
            out.append(head + "-" + tail.upper())
        elif w[:1].isdigit():                      # 5800x3d, 245k, 1231
            out.append(w.upper())
        elif w[:1] == "g" and w[1:2].isdigit():    # g4560
            out.append(w.upper())
        elif w[:1] == "e" and "-" in w:            # e3-1231
            out.append(w.upper())
        elif w[:1] in ("a", "b") and w[1:2].isdigit():   # arc a750/b580
            out.append(w.upper())
        elif w.startswith("v") and w[1:2].isdigit():     # v3
            out.append(w)
        else:
            out.append(w.capitalize())
    return " ".join(out)


def cpu_record(key: str):
    """Full dict for a CPU key, or None."""
    row = CPUS.get(key)
    if not row:
        return None
    socket, gen, cores, threads, tdp, igpu = row
    vendor = SOCKETS[socket]["vendor"]
    prefix = "Intel " if vendor == "intel" else "AMD "
    if key.startswith("i") or key.startswith("ultra"):
        prefix = "Intel Core "
    return {"key": key, "kind": "cpu", "socket": socket, "gen": gen,
            "cores": cores, "threads": threads, "tdp": tdp, "igpu": igpu,
            "vendor": vendor, "label": prefix + _fmt_model(key)}


def gpu_record(key: str):
    """Full dict for a GPU key, or None."""
    row = GPUS.get(key)
    if not row:
        return None
    vram, tdp, psu, perf, year = row
    if key.startswith("rx"):
        label = "AMD Radeon " + _fmt_model(key)
    elif key.startswith("arc"):
        label = "Intel " + _fmt_model(key)
    else:
        label = "NVIDIA GeForce " + _fmt_model(key)
    return {"key": key, "kind": "gpu", "vram_gb": vram, "tdp": tdp,
            "rec_psu": psu, "perf": perf, "year": year,
            "note": GPU_NOTES.get(key, ""), "label": label}


def db_counts():
    return {"cpus": len(CPUS), "gpus": len(GPUS), "chipsets": len(CHIPSETS),
            "sockets": len(SOCKETS),
            "total": len(CPUS) + len(GPUS) + len(CHIPSETS) + len(SOCKETS)}
