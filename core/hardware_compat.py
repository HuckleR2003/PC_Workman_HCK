# core/hardware_compat.py
"""
Upgrade Readiness engine - "will this part work in my machine?", fully offline.

Data lives in core/hardware_compat_db.py (sockets, chipset support tables,
CPUs, GPUs). This module adds the logic:

  identify_cpu / identify_gpu / identify_part - free text -> library record
  current_platform  - the user's real machine (via core.hardware_detector)
  check_cpu_upgrade - socket + per-chipset generation verdict, BIOS notes,
                      RAM carry-over, cooler mounting, iGPU/F-series warning
  check_gpu_upgrade - perf class delta, VRAM delta, PSU recommendation,
                      CPU bottleneck hint, connector/PCIe caveats
  check_ram_upgrade - DDR generation + speed vs platform (XMP/EXPO notes)
  check_upgrade     - dispatcher (text in, verdict dict out)

Every check accepts an optional `platform` dict so tests and "what-if" UI can
inject a synthetic machine (see make_platform). Verdict dicts carry structured
facts plus ready English sentences; hck_GPT composes Polish from the facts.

ARCHITECTURE.md rule: this is the ONE compatibility engine. The Upgrade
Readiness page and every hck_GPT upgrade answer call into here.
"""
from __future__ import annotations

import re
import time
from typing import Optional

from core.hardware_compat_db import (
    DB_VERSION, SOCKETS, CHIPSETS, CPUS, GPUS,
    cpu_record, gpu_record, db_counts,
)

# ── Free-text identification ─────────────────────────────────────────────────
_CPU_NOISE = re.compile(
    r"\(r\)|\(tm\)|\bintel\b|\bamd\b|\bcore\b|\bprocessor\b|\bcpu\b"
    r"|@.*$|\bwith\b.*$|\b\d+-core\b|\b\d+-thread\b")

def _fold_cpu(text: str) -> str:
    s = (text or "").lower()
    s = _CPU_NOISE.sub(" ", s)
    s = s.replace("-", " ")
    return re.sub(r"\s+", " ", s).strip()


_RX_INTEL = re.compile(r"\bi([3579])\s?(\d{4,5})([a-z]{0,2})\b")
_RX_ULTRA = re.compile(r"\bultra\s?([579])\s?(\d{3})([a-z]{0,2})\b")
_RX_RYZEN = re.compile(r"\bryzen\s?([3579])\s?(\d{4})([a-z0-9]{0,3})\b")
_RX_FX    = re.compile(r"\bfx\s?(\d{4})\b")
_RX_PENT  = re.compile(r"\bpentium\s?(?:gold\s?)?g(\d{4})\b")
_RX_XEON  = re.compile(r"\bxeon\s?e3\s?(\d{4})\s?(v\d)\b")


def identify_cpu(text: str) -> Optional[dict]:
    """Match any spelling of a CPU name to its library record.
    'Intel(R) Core(TM) i5-11400F @ 2.60GHz', 'i5 11400f', 'Ryzen75800X3D-ish
    spacing variants all resolve. Returns None when not in the library."""
    s = _fold_cpu(text)
    if not s:
        return None
    m = _RX_INTEL.search(s)
    if m:
        return cpu_record(f"i{m.group(1)}-{m.group(2)}{m.group(3)}")
    m = _RX_ULTRA.search(s)
    if m:
        return cpu_record(f"ultra {m.group(1)} {m.group(2)}{m.group(3)}")
    m = _RX_RYZEN.search(s)
    if m:
        return cpu_record(f"ryzen {m.group(1)} {m.group(2)}{m.group(3)}")
    m = _RX_FX.search(s)
    if m:
        return cpu_record(f"fx-{m.group(1)}")
    m = _RX_PENT.search(s)
    if m:
        return cpu_record(f"pentium g{m.group(1)}")
    m = _RX_XEON.search(s)
    if m:
        return cpu_record(f"xeon e3-{m.group(1)} {m.group(2)}")
    return None


_RX_NV  = re.compile(r"\b(rtx|gtx)\s?(\d{3,4})\s?(ti\s?super|ti|super)?\b")
_RX_RX  = re.compile(r"\brx\s?(\d{3,4})\s?(xtx|xt|gre)?\b")
_RX_ARC = re.compile(r"\barc\s?([ab])\s?(\d{3})\b")


def identify_gpu(text: str) -> Optional[dict]:
    """Match any spelling of a GPU name to its library record."""
    s = re.sub(r"\s+", " ", (text or "").lower().replace("-", " ")).strip()
    if not s:
        return None
    m = _RX_NV.search(s)
    if m:
        suffix = re.sub(r"\s+", " ", m.group(3) or "").strip()
        if suffix == "tisuper":
            suffix = "ti super"
        key = f"{m.group(1)} {m.group(2)}" + (f" {suffix}" if suffix else "")
        return gpu_record(key)
    m = _RX_RX.search(s)
    if m:
        key = f"rx {m.group(1)}" + (f" {m.group(2)}" if m.group(2) else "")
        return gpu_record(key)
    m = _RX_ARC.search(s)
    if m:
        return gpu_record(f"arc {m.group(1)}{m.group(2)}")
    return None


_RX_DDR   = re.compile(r"\bddr\s?([2345])\b")
_RX_SPEED = re.compile(r"\b([2-9]\d{3})\s?(?:mhz|mt/?s)?\b")


def identify_part(text: str):
    """Classify free text: ('cpu', rec) | ('gpu', rec) | ('ram', {...}) |
    (None, None). RAM matches only when DDR-gen or an explicit speed+context
    word is present, so CPU/GPU numbers don't get eaten."""
    cpu = identify_cpu(text)
    if cpu:
        return "cpu", cpu
    gpu = identify_gpu(text)
    if gpu:
        return "gpu", gpu
    low = (text or "").lower()
    m = _RX_DDR.search(low)
    if m or ("ram" in low or "pami" in low or "memory" in low):
        ddr = f"DDR{m.group(1)}" if m else ""
        ms = _RX_SPEED.search(low)
        speed = int(ms.group(1)) if ms else 0
        gb = 0
        mg = re.search(r"\b(\d{1,3})\s?gb\b", low)
        if mg:
            gb = int(mg.group(1))
        if ddr or speed or gb:
            return "ram", {"kind": "ram", "ddr": ddr, "speed": speed, "gb": gb}
    return None, None


# ── Current machine ──────────────────────────────────────────────────────────
_PLAT_CACHE: dict = {"t": 0.0, "v": None}
_RX_CHIP = re.compile(r"\b([ABHXZ]\d{2,3}[A-Z]?|760G|970|990X|990FX)\b")


def chipset_from_board(board: str) -> Optional[str]:
    """Extract a known chipset from a motherboard name.
    'MAG B550M MORTAR (MS-7C94)' -> 'B550', 'ROG STRIX Z97-A' -> 'Z97'."""
    for cand in _RX_CHIP.findall((board or "").upper()):
        if cand in CHIPSETS:
            return cand
        trimmed = cand[:-1]                       # B550M -> B550
        if trimmed in CHIPSETS:
            return trimmed
    return None


def _detector_data() -> dict:
    try:
        from import_core import COMPONENTS
        det = COMPONENTS.get("core.hardware_detector")
        if det is None:
            from core.hardware_detector import get_hardware_detector
            det = get_hardware_detector()
        return det.ensure_data() or {}
    except Exception:
        return {}


def make_platform(cpu: str = "", board: str = "", gpu: str = "",
                  ram_speed: int = 0) -> dict:
    """Build a synthetic platform (tests / what-if mode)."""
    cpu_rec = identify_cpu(cpu) if cpu else None
    chipset = chipset_from_board(board) if board else None
    socket = cpu_rec["socket"] if cpu_rec else (
        CHIPSETS[chipset]["socket"] if chipset else None)
    # Dual-gen sockets (LGA1700 takes DDR4 OR DDR5, board decides): resolve
    # which one is actually installed from the module speed when we can.
    ram_actual = None
    if socket:
        gens = SOCKETS[socket]["ram"]
        if len(gens) == 1:
            ram_actual = gens[0]
        elif ram_speed:
            ram_actual = "DDR5" if ram_speed >= 4400 else "DDR4"
    return {"cpu_name": cpu, "cpu": cpu_rec, "socket": socket,
            "chipset": chipset, "gpu_name": gpu,
            "gpu": identify_gpu(gpu) if gpu else None,
            "ram_speed": ram_speed, "ram_actual": ram_actual,
            "ram_type": "/".join(SOCKETS[socket]["ram"]) if socket else None}


def current_platform(force: bool = False) -> dict:
    """The user's real machine, cached 60 s. Same shape as make_platform."""
    now = time.time()
    if not force and _PLAT_CACHE["v"] and now - _PLAT_CACHE["t"] < 60:
        return _PLAT_CACHE["v"]
    d = _detector_data()
    cpu_name = (d.get("cpu") or {}).get("name", "") or ""
    gpu_name = (d.get("gpu") or {}).get("name", "") or ""
    mb = d.get("motherboard") or {}
    board = " ".join(filter(None, [str(mb.get("product", "") or ""),
                                   str(mb.get("version", "") or "")]))
    ram = d.get("ram") or {}
    plat = make_platform(cpu=cpu_name, board=board, gpu=gpu_name,
                         ram_speed=int(ram.get("speed_mhz") or 0))
    plat["cpu_name"] = cpu_name          # keep raw names even when unmatched
    plat["gpu_name"] = gpu_name
    plat["board"] = board
    _PLAT_CACHE.update(t=now, v=plat)
    return plat


def platform_label(plat: Optional[dict] = None) -> str:
    """'LGA1200 - B560 - DDR4' style one-liner for the UI header."""
    p = plat or current_platform()
    bits = [b for b in [p.get("socket"), p.get("chipset"), p.get("ram_type")]
            if b]
    return " - ".join(bits) if bits else "platform not identified"


# ── CPU upgrade check ────────────────────────────────────────────────────────
def _chipset_support(chipset: Optional[str], gen: int) -> str:
    """'native' | 'bios' | 'maybe' | 'no' | 'unlisted' | 'unknown_chipset'."""
    if not chipset or chipset not in CHIPSETS:
        return "unknown_chipset"
    info = CHIPSETS[chipset]
    if gen in info["native"]:
        return "native"
    if gen in info["bios"]:
        return "bios"
    if gen in info["maybe"]:
        return "maybe"
    if gen in info["no"]:
        return "no"
    return "unlisted"


def _cpu_class(rec: dict) -> float:
    """Coarse CPU performance class on the GPU perf scale (bottleneck hint)."""
    base = {"intel": {4: 10, 6: 13, 7: 15, 8: 22, 9: 25, 10: 29, 11: 33,
                      12: 47, 13: 55, 14: 57, 15: 58},
            "amd": {0: 6, 1: 16, 2: 20, 3: 30, 5: 40, 7: 52, 8: 50, 9: 60}}
    b = base.get(rec["vendor"], {}).get(rec["gen"], 20)
    b += min(rec["threads"], 32) / 3.2
    if "x3d" in rec["key"]:
        b += 8
    return b


def check_cpu_upgrade(target: str, platform: Optional[dict] = None) -> dict:
    """Verdict for swapping the CPU to *target* on the current board."""
    plat = platform or current_platform()
    tgt = identify_cpu(target)
    out = {"kind": "cpu", "target_text": target, "target": tgt,
           "current": plat, "ok": False, "verdict": "", "headline": "",
           "reasons": [], "notes": [], "socket_ok": False,
           "chipset_support": "", "ram_change": None, "cooler_ok": True}

    if tgt is None:
        out["verdict"] = "unknown_part"
        out["headline"] = "Not in the offline library yet"
        out["reasons"].append(
            "That CPU is not in my offline library. It covers Intel 4th-gen "
            "through Core Ultra 200S and AMD FX through Ryzen 9000 "
            f"(desktop, {db_counts()['cpus']} models).")
        return out

    cur_sock = plat.get("socket")
    if not cur_sock:
        out["verdict"] = "unknown_current"
        out["headline"] = "Current platform not identified"
        out["reasons"].append(
            "I could not determine your socket/board. Open My PC > Components "
            "so the hardware scan runs, then ask again.")
        return out

    tgt_sock = tgt["socket"]
    chipset = plat.get("chipset")
    out["socket_ok"] = (tgt_sock == cur_sock)

    # -- different socket -----------------------------------------------------
    if not out["socket_ok"]:
        both_1151 = {tgt_sock, cur_sock} == {"LGA1151", "LGA1151-2"}
        out["verdict"] = "needs_new_board"
        if both_1151:
            out["headline"] = "Same-looking socket, incompatible platform"
            out["reasons"].append(
                f"{tgt['label']} uses the Coffee Lake side of LGA1151 - the "
                "pins match but 100/200-series and 300-series boards are "
                "electrically incompatible. A new motherboard is required.")
        else:
            out["headline"] = "Different socket - new motherboard required"
            out["reasons"].append(
                f"{tgt['label']} is {tgt_sock}, your board is {cur_sock}. "
                "It physically will not fit - plan a motherboard swap.")
        # The sticks the user actually owns decide what carries over, not
        # everything the socket could take (LGA1700 DDR5 build -> AM4 board:
        # nothing carries even though LGA1700 also "supports" DDR4).
        cur_ram = ([plat["ram_actual"]] if plat.get("ram_actual")
                   else SOCKETS[cur_sock]["ram"])
        tgt_ram = SOCKETS[tgt_sock]["ram"]
        shared = sorted(set(cur_ram) & set(tgt_ram))
        if shared:
            out["ram_change"] = None
            out["ram_carry"] = shared[0]
            out["notes"].append(
                f"Your {shared[0]} RAM can carry over to the new board.")
        else:
            out["ram_change"] = ("/".join(cur_ram), "/".join(tgt_ram))
            out["reasons"].append(
                f"It also changes memory: {'/'.join(cur_ram)} -> "
                f"{'/'.join(tgt_ram)}, so budget for new RAM too.")
        out["cooler_ok"] = (SOCKETS[cur_sock]["mount"]
                            == SOCKETS[tgt_sock]["mount"])
        out["notes"].append(
            "Cooler mounting carries over." if out["cooler_ok"] else
            f"Your cooler needs a mounting kit for {SOCKETS[tgt_sock]['mount']} "
            "(or a new cooler).")
        return out

    # -- same socket: consult the chipset table -------------------------------
    sup = _chipset_support(chipset, tgt["gen"])
    out["chipset_support"] = sup
    if sup == "native":
        out["ok"] = True
        out["verdict"] = "compatible"
        out["headline"] = "Drops straight in"
        out["reasons"].append(
            f"Same socket ({tgt_sock}) and your {chipset} runs "
            f"{tgt['label']} natively - swap and boot.")
    elif sup == "bios":
        out["ok"] = True
        out["verdict"] = "bios_update"
        out["headline"] = "Fits after a BIOS update"
        out["reasons"].append(
            f"Same socket ({tgt_sock}), but {chipset} boards need a BIOS "
            f"update for this generation. Flash the latest BIOS with the "
            "current CPU still installed, then swap.")
    elif sup == "maybe":
        out["verdict"] = "vendor_dependent"
        out["headline"] = "Board-vendor dependent"
        out["reasons"].append(
            f"Some {chipset} boards received BIOS support for this "
            "generation and some never did. Check your exact model's CPU "
            "support list before buying.")
    elif sup == "no":
        out["verdict"] = "chipset_blocked"
        out["headline"] = "Same socket, blocked by chipset"
        out["reasons"].append(
            f"The socket matches, but {chipset} boards do not support "
            f"{tgt['label']} at all - no BIOS unlocks it. You would need a "
            "board whose chipset lists this generation.")
    elif sup == "unlisted":
        out["ok"] = True
        out["verdict"] = "check_support_list"
        out["headline"] = "Likely fine - verify the support list"
        out["reasons"].append(
            f"Socket matches, but this pairing is outside {chipset}'s "
            "official list in my library. Check your board vendor's CPU "
            "support page to be sure.")
    else:  # unknown_chipset
        out["ok"] = True
        out["verdict"] = "check_support_list"
        out["headline"] = "Socket matches - verify the support list"
        out["reasons"].append(
            f"Same socket ({tgt_sock}). I could not read your exact chipset, "
            "so confirm the CPU on your board vendor's support list.")

    # -- extras ---------------------------------------------------------------
    cur_cpu = plat.get("cpu")
    if tgt["tdp"] >= 125 and (not cur_cpu or cur_cpu["tdp"] <= 65):
        out["notes"].append(
            f"{tgt['tdp']} W part - make sure your cooler and board VRM are "
            "up to it (a tower cooler, not the stock puck).")
    if not tgt["igpu"] and not plat.get("gpu"):
        gpu_name = (plat.get("gpu_name") or "").strip()
        if not gpu_name or "graphics" in gpu_name.lower():
            out["notes"].append(
                "This is an F-series style chip with no integrated graphics - "
                "it needs a dedicated GPU to show an image.")
    if cur_cpu and cur_cpu["key"] == tgt["key"]:
        out["notes"].append("That is the CPU you already have.")
    return out


# ── GPU upgrade check ────────────────────────────────────────────────────────
def check_gpu_upgrade(target: str, platform: Optional[dict] = None) -> dict:
    """Verdict for swapping/adding a GPU. PCIe is backward compatible, so the
    interesting facts are power, the performance delta, and CPU pairing."""
    plat = platform or current_platform()
    tgt = identify_gpu(target)
    out = {"kind": "gpu", "target_text": target, "target": tgt,
           "current": plat, "ok": False, "verdict": "", "headline": "",
           "reasons": [], "notes": [], "perf_delta_pct": None,
           "vram_delta_gb": None, "rec_psu": None, "bottleneck": False}

    if tgt is None:
        out["verdict"] = "unknown_part"
        out["headline"] = "Not in the offline library yet"
        out["reasons"].append(
            "That GPU is not in my offline library (GTX 700 through RTX 50, "
            f"RX 500 through RX 9000, Arc - {db_counts()['gpus']} models).")
        return out

    out["ok"] = True
    out["verdict"] = "compatible"
    out["headline"] = "Fits any PCIe x16 slot"
    out["rec_psu"] = tgt["rec_psu"]
    out["reasons"].append(
        f"{tgt['label']} uses a standard PCIe x16 slot - electrically "
        "compatible with every platform in my library.")
    out["reasons"].append(
        f"Power: the card draws up to {tgt['tdp']} W; recommended system "
        f"PSU is {tgt['rec_psu']} W.")

    cur = plat.get("gpu")
    if cur:
        if cur["key"] == tgt["key"]:
            out["notes"].append("That is the GPU you already have.")
        else:
            delta = round((tgt["perf"] - cur["perf"]) / cur["perf"] * 100)
            out["perf_delta_pct"] = delta
            out["vram_delta_gb"] = tgt["vram_gb"] - cur["vram_gb"]
            if delta >= 25:
                out["reasons"].append(
                    f"Versus your {cur['label']}: roughly a {delta:+d}% "
                    "class jump - a real upgrade.")
            elif delta > -10:
                out["reasons"].append(
                    f"Versus your {cur['label']}: about {delta:+d}% - closer "
                    "to a sidegrade than an upgrade.")
            else:
                out["verdict"] = "downgrade"
                out["headline"] = "Compatible, but a downgrade"
                out["reasons"].append(
                    f"Versus your {cur['label']}: about {delta:+d}% - that "
                    "is a step down in class.")
            if out["vram_delta_gb"] and out["vram_delta_gb"] != 0:
                sign = "+" if out["vram_delta_gb"] > 0 else ""
                out["notes"].append(
                    f"VRAM: {cur['vram_gb']} GB -> {tgt['vram_gb']} GB "
                    f"({sign}{out['vram_delta_gb']} GB).")
            watt_delta = tgt["tdp"] - cur["tdp"]
            if watt_delta >= 75:
                out["notes"].append(
                    f"It draws {watt_delta} W more than your current card - "
                    "check your PSU's wattage and connectors.")
    else:
        out["notes"].append(
            "I do not see a dedicated GPU in this machine, so this would be "
            "an addition, not a swap - just confirm the PSU wattage above.")

    cur_cpu = plat.get("cpu")
    if cur_cpu:
        gap = tgt["perf"] - _cpu_class(cur_cpu)
        if gap > 35:
            out["bottleneck"] = True
            out["notes"].append(
                f"Pairing note: {cur_cpu['label']} will hold this card back "
                "in CPU-heavy games at 1440p and below. It works, but a CPU "
                "upgrade would unlock more of it.")
    if tgt.get("note"):
        out["notes"].append(tgt["note"])
    return out


# ── RAM upgrade check ────────────────────────────────────────────────────────
def check_ram_upgrade(target: str = "", platform: Optional[dict] = None) -> dict:
    """Verdict for a RAM purchase: DDR generation vs the platform, plus
    speed guidance (official max vs XMP/EXPO sweet spots)."""
    plat = platform or current_platform()
    _, ram = identify_part(target if target else "ram")
    want = ram or {"kind": "ram", "ddr": "", "speed": 0, "gb": 0}
    out = {"kind": "ram", "target_text": target, "target": want,
           "current": plat, "ok": False, "verdict": "", "headline": "",
           "reasons": [], "notes": []}

    sock = plat.get("socket")
    if not sock:
        out["verdict"] = "unknown_current"
        out["headline"] = "Current platform not identified"
        out["reasons"].append(
            "I could not determine your platform. Open My PC > Components "
            "so the hardware scan runs, then ask again.")
        return out

    supported = SOCKETS[sock]["ram"]
    ram_max = SOCKETS[sock]["ram_max"]
    if not want["ddr"]:
        out["ok"] = True
        out["verdict"] = "info"
        out["headline"] = f"Your platform takes {'/'.join(supported)}"
        out["reasons"].append(
            f"{sock} boards use {'/'.join(supported)} "
            f"(official max {', '.join(f'{k}-{v}' for k, v in ram_max.items())}).")
    elif want["ddr"] in supported:
        out["ok"] = True
        out["verdict"] = "compatible"
        out["headline"] = f"{want['ddr']} is the right type"
        out["reasons"].append(
            f"{want['ddr']} matches your {sock} platform.")
    else:
        out["verdict"] = "incompatible"
        out["headline"] = "Wrong memory generation"
        out["reasons"].append(
            f"{sock} takes {'/'.join(supported)}, not {want['ddr']} - the "
            "notch physically will not line up.")
        return out

    ddr = want["ddr"] or supported[0]
    if want["speed"] and ddr in ram_max:
        official = ram_max[ddr]
        if want["speed"] <= official:
            out["notes"].append(
                f"{want['speed']} MT/s is within the official "
                f"{ddr}-{official} spec - plug and play.")
        else:
            out["notes"].append(
                f"{want['speed']} MT/s is above the official {ddr}-{official} "
                "spec - it runs via an XMP/EXPO profile, which most boards "
                "handle fine.")
            if plat.get("chipset") in ("H410", "B460", "H470"):
                out["notes"].append(
                    f"Caveat: {plat['chipset']} locks memory to official "
                    "speeds - the kit will downclock to spec.")
    if sock == "AM4":
        out["notes"].append("Sweet spot on AM4: DDR4-3600 CL16.")
    elif sock == "AM5":
        out["notes"].append("Sweet spot on AM5: DDR5-6000 CL30 (EXPO).")
    elif sock == "LGA1700" and ddr == "DDR5":
        out["notes"].append("Sweet spot on LGA1700: DDR5-6000 or so.")
    return out


# ── Dispatcher ───────────────────────────────────────────────────────────────
def check_upgrade(text: str, platform: Optional[dict] = None) -> dict:
    """Free text in ('i5 11400f', 'rtx 4070', 'ddr5 6000'), verdict out."""
    kind, _rec = identify_part(text)
    if kind == "cpu":
        return check_cpu_upgrade(text, platform)
    if kind == "gpu":
        return check_gpu_upgrade(text, platform)
    if kind == "ram":
        return check_ram_upgrade(text, platform)
    return {"kind": None, "target_text": text, "target": None, "ok": False,
            "verdict": "unknown_part",
            "headline": "Could not recognise that part",
            "reasons": [
                "Tell me a CPU (e.g. 'i5 11400F', 'Ryzen 7 5800X3D'), a GPU "
                "(e.g. 'RTX 4070', 'RX 7800 XT') or RAM (e.g. 'DDR5 6000')."],
            "notes": [], "current": platform or current_platform()}


def suggest_upgrades(platform: Optional[dict] = None,
                     limit: int = 3) -> dict:
    """Contextual picks for this platform: same-socket CPUs that are a real
    step up (and actually run on the user's chipset), GPUs one to three
    classes above the current card, and the matching RAM sweet spot.
    Feeds the Upgrade Readiness quick-pick chips and hck_GPT suggestions."""
    plat = platform or current_platform()
    out = {"cpu": [], "gpu": [], "ram": []}
    sock, chip = plat.get("socket"), plat.get("chipset")
    cur_cpu, cur_gpu = plat.get("cpu"), plat.get("gpu")

    if sock:
        cands = []
        for key in CPUS:
            rec = cpu_record(key)
            if rec["socket"] != sock:
                continue
            if _chipset_support(chip, rec["gen"]) not in (
                    "native", "bios", "unknown_chipset"):
                continue
            if cur_cpu and rec["threads"] <= cur_cpu["threads"]:
                continue
            cands.append(rec)
        cands.sort(key=lambda r: (r["threads"], r["gen"], r["cores"]),
                   reverse=True)
        seen, picks = set(), []
        for r in cands:                      # one pick per thread count
            if r["threads"] in seen:
                continue
            seen.add(r["threads"])
            picks.append(r)
        out["cpu"] = picks[:limit]

    if cur_gpu:
        pool = [gpu_record(k) for k in GPUS]
        pool = [r for r in pool
                if 1.4 * cur_gpu["perf"] <= r["perf"] <= 3.5 * cur_gpu["perf"]]
        pool.sort(key=lambda r: r["perf"])
        if pool:
            idxs = sorted({0, len(pool) // 2, len(pool) - 1})
            out["gpu"] = [pool[i] for i in idxs][:limit]
    if not out["gpu"]:
        out["gpu"] = [gpu_record(k) for k in ("rtx 4060", "rx 7600",
                                              "rtx 4070")][:limit]

    ram_t = plat.get("ram_type") or ""
    if "DDR5" in ram_t:
        out["ram"] = ["DDR5 6000"]
    elif "DDR4" in ram_t:
        out["ram"] = ["DDR4 3600"]
    elif "DDR3" in ram_t:
        out["ram"] = ["DDR3 1600"]
    return out


def db_stats() -> dict:
    """Coverage numbers for the UI footer / diagnostics."""
    stats = db_counts()
    stats["version"] = DB_VERSION
    return stats
