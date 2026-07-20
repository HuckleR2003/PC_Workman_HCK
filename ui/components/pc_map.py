"""
PC Map  --  2.5D Isometric Hardware Visualization
Pillow-rendered, live-updating isometric view of all detected PC components.
Desktop PC and Laptop modes.
"""
from __future__ import annotations

import math
import threading
import time
import tkinter as tk
from typing import Dict, List, Optional, Tuple, Any

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# PIL
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# psutil
try:
    import psutil as _psutil
    _HAS_PSUTIL = True
except ImportError:
    _psutil = None
    _HAS_PSUTIL = False


# ─────────────────────────────────────────────────────────────────────────────
#  ISOMETRIC PROJECTION  (x -> lower-right, y -> lower-left, z -> up)
# ─────────────────────────────────────────────────────────────────────────────
_TW   = 64    # iso tile width  (pixels per x/y unit, at 1x)
_TH   = 22    # iso tile height (y-step per x/y unit, at 1x)
_TZ   = 16    # z step per unit (at 1x)
_SSAA = 2     # super-sampling: draw at 2x, scale down

# Canvas output size
_CW = 680
_CH = 540

# Draw-space origin of 3D (0,0,0) - PC tower centered in canvas
# _OY raised by 40 px so the floor stays visible without scrolling
_OX = int((_CW // 2 - 18) * _SSAA)   # 644
_OY = int((_CH - 115)      * _SSAA)  # 850  (was 930)


def _iso(x: float, y: float, z: float,
         ox: float = _OX, oy: float = _OY) -> Tuple[float, float]:
    s = _SSAA
    sx = ox + (x - y) * (_TW * s / 2.0)
    sy = oy + (x + y) * (_TH * s / 2.0) - z * (_TZ * s)
    return sx, sy


def _face(x: float, y: float, z: float,
          w: float, d: float, h: float,
          face: str,
          ox: float = _OX, oy: float = _OY) -> List[Tuple[float, float]]:
    p = _iso
    if face == "top":
        return [p(x,   y,   z+h, ox, oy), p(x+w, y,   z+h, ox, oy),
                p(x+w, y+d, z+h, ox, oy), p(x,   y+d, z+h, ox, oy)]
    elif face == "front":   # y=y face  (left diagonal)
        return [p(x,   y, z,   ox, oy), p(x,   y, z+h, ox, oy),
                p(x+w, y, z+h, ox, oy), p(x+w, y, z,   ox, oy)]
    elif face == "side":    # x=x+w face (right diagonal)
        return [p(x+w, y,   z,   ox, oy), p(x+w, y,   z+h, ox, oy),
                p(x+w, y+d, z+h, ox, oy), p(x+w, y+d, z,   ox, oy)]
    return []


def _shade(rgb: Tuple, f: float) -> Tuple:
    return (min(255, max(0, int(rgb[0]*f))),
            min(255, max(0, int(rgb[1]*f))),
            min(255, max(0, int(rgb[2]*f))))


def _lerp(a: Tuple, b: Tuple, t: float) -> Tuple:
    return (int(a[0]+(b[0]-a[0])*t), int(a[1]+(b[1]-a[1])*t), int(a[2]+(b[2]-a[2])*t))


def _heat(base: Tuple, heat: float) -> Tuple:
    """Shift base color: cool -> warm amber -> hot red based on heat 0..1."""
    if heat <= 0.45:
        return base
    elif heat <= 0.72:
        t = (heat - 0.45) / 0.27
        return _lerp(base, (210, 120, 20), t)
    else:
        t = min(1.0, (heat - 0.72) / 0.28)
        return _lerp((210, 120, 20), (220, 30, 30), t)


def _pulse(base: Tuple, warn: Tuple, phase: float) -> Tuple:
    t = (math.sin(phase) + 1.0) / 2.0
    return _lerp(base, warn, t * 0.65)


def _poly(draw: "ImageDraw.ImageDraw", pts, fill, outline=None, width=1):
    """Draw a filled polygon with flat tuples."""
    flat = [(int(p[0]), int(p[1])) for p in pts]
    draw.polygon(flat, fill=fill)
    if outline:
        draw.line(flat + [flat[0]], fill=outline, width=width)


# ── Component colors ───────────────────────────────────────────────────────────
_C = {
    "bg":      (8,  11, 18),
    "floor":   (14, 18, 28),
    "grid":    (24, 32, 48),
    "case":    (26, 30, 40),
    "case_hi": (38, 44, 58),
    "case_lo": (18, 21, 30),
    "mobo":    (18, 65, 44),
    "mobo_hi": (22, 85, 55),
    "cpu":     (16, 172, 150),
    "cpu_hi":  (22, 210, 185),
    "hsink":   (145, 155, 168),
    "hsink_hi":(180, 195, 210),
    "gpu":     (108, 58, 188),
    "gpu_hi":  (135, 75, 220),
    "ram":     (195, 140, 22),
    "ram_hi":  (230, 175, 35),
    "ssd":     (30, 150, 68),
    "ssd_hi":  (40, 185, 85),
    "hdd":     (60, 85, 115),
    "hdd_hi":  (75, 108, 145),
    "psu":     (55, 68, 88),
    "psu_hi":  (70, 88, 112),
    "fan":     (32, 42, 58),
    "fan_hi":  (45, 58, 80),
    "wire_b":  (30, 120, 220),
    "wire_y":  (220, 175, 25),
    "wire_r":  (200, 40,  40),
    "led_g":   (20, 230, 100),
    "led_b":   (30, 160, 255),
}


# ─────────────────────────────────────────────────────────────────────────────
#  LIVE DATA GATHERING
# ─────────────────────────────────────────────────────────────────────────────
def _gather_live() -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "cpu_pct":  0.0, "cpu_temp": 0.0, "cpu_freq": 0.0,
        "gpu_pct":  0.0, "gpu_temp": 0.0, "gpu_vram_pct": 0.0,
        "ram_pct":  0.0, "ram_used": 0.0, "ram_total": 0.0,
        "disk_pct": 0.0, "disk_free": 0.0,
        "cpu_name": "CPU", "gpu_name": "GPU",
        "ram_slots": 2,
    }
    if _HAS_PSUTIL and _psutil:
        try:
            d["cpu_pct"]  = _psutil.cpu_percent(interval=None)
            freq = _psutil.cpu_freq()
            d["cpu_freq"] = round(freq.current / 1000.0, 2) if freq else 0.0
            vm = _psutil.virtual_memory()
            d["ram_pct"]   = vm.percent
            d["ram_used"]  = round(vm.used  / 1e9, 1)
            d["ram_total"] = round(vm.total / 1e9, 1)
        except Exception:
            pass
        try:
            du = _psutil.disk_usage("C:\\")
            d["disk_pct"]  = du.percent
            d["disk_free"] = round(du.free / 1e9, 1)
        except Exception:
            pass
    try:
        from core.hardware_sensors import get_cpu_temp, get_gpu_temp
        t = get_cpu_temp()
        if t:
            d["cpu_temp"] = float(t)
        g = get_gpu_temp()
        if g:
            d["gpu_temp"] = float(g)
    except Exception:
        pass
    try:
        from core.hardware_detector import get_hardware_detector
        det = get_hardware_detector()
        if det.is_ready:
            hw = det.get_data()
            cpu = hw.get("cpu", {})
            gpu = hw.get("gpu", {})
            ram = hw.get("ram", {})
            if cpu.get("name"):
                d["cpu_name"] = cpu["name"].split("@")[0].strip()[:32]
            if gpu.get("name"):
                d["gpu_name"] = gpu["name"][:32]
            slots = ram.get("modules", [])
            d["ram_slots"] = max(1, min(4, len(slots))) if slots else 2
    except Exception:
        pass
    return d


# ─────────────────────────────────────────────────────────────────────────────
#  ISOMETRIC BOX DRAWING
# ─────────────────────────────────────────────────────────────────────────────
class _Box:
    """Drawable isometric box with hit-testing support."""
    __slots__ = ("x","y","z","w","d","h","col","name",
                 "outline","outline_w","top_f","front_f","side_f")

    def __init__(self, x, y, z, w, d, h, col, name="",
                 outline=None, ow=2,
                 top_f=1.0, front_f=0.76, side_f=0.55):
        self.x, self.y, self.z = x, y, z
        self.w, self.d, self.h = w, d, h
        self.col = col
        self.name = name
        self.outline = outline
        self.outline_w = ow
        self.top_f   = top_f
        self.front_f = front_f
        self.side_f  = side_f

    def draw(self, draw, ox=_OX, oy=_OY):
        x,y,z,w,d,h = self.x,self.y,self.z,self.w,self.d,self.h
        c = self.col
        out = self.outline
        ow  = self.outline_w * _SSAA

        # Draw back-most edges first (side, then front, then top)
        _poly(draw, _face(x,y,z,w,d,h,"side", ox,oy),
              _shade(c, self.side_f), out, ow)
        _poly(draw, _face(x,y,z,w,d,h,"front",ox,oy),
              _shade(c, self.front_f), out, ow)
        _poly(draw, _face(x,y,z,w,d,h,"top",  ox,oy),
              _shade(c, self.top_f), out, ow)

    def screen_center(self, ox=_OX, oy=_OY) -> Tuple[float,float]:
        """Return 2D screen center of top face (in draw-space coords)."""
        cx = self.x + self.w / 2.0
        cy = self.y + self.d / 2.0
        cz = self.z + self.h
        sx, sy = _iso(cx, cy, cz, ox, oy)
        return sx, sy

    def top_mid(self, ox=_OX, oy=_OY) -> Tuple[float, float]:
        pts = _face(self.x, self.y, self.z, self.w, self.d, self.h, "top", ox, oy)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (sum(xs)/4, sum(ys)/4)

    def hit_rect(self, ox=_OX, oy=_OY) -> Tuple[float,float,float,float]:
        """Bounding rect in draw-space for hover detection."""
        all_pts = (
            _face(self.x,self.y,self.z,self.w,self.d,self.h,"top",  ox,oy) +
            _face(self.x,self.y,self.z,self.w,self.d,self.h,"front",ox,oy) +
            _face(self.x,self.y,self.z,self.w,self.d,self.h,"side", ox,oy)
        )
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        return (min(xs), min(ys), max(xs), max(ys))


# ─────────────────────────────────────────────────────────────────────────────
#  WORKLOAD-AWARE HEAT HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _thermal_aware_cpu_heat(cpu_pct: float, cpu_temp: float,
                            gpu_pct: float) -> float:
    """
    Returns heat 0..1 using thermal_baseline when trained.
    Falls back to the classic formula if baseline is unavailable.

    Innovation: the heat colour reflects whether a temperature is *actually*
    abnormal for the current workload - not just a fixed threshold.
    E.g. 72°C during heavy gaming is "normal" (cool colour) while 72°C at
    idle is "hot" (amber/red).
    """
    if cpu_temp > 0:
        try:
            from core.thermal_baseline import thermal_baseline
            bucket = thermal_baseline.classify(cpu_pct, gpu_pct)
            br     = thermal_baseline.get_range(bucket)
            if br.is_usable:
                z = br.z_score(cpu_temp)
                # Map z-score → heat: z≤0 = cool, z≥3 = max heat
                return max(0.0, min(1.0, z / 3.0))
        except Exception:
            pass
        # Fallback: classic weighted formula
        return max(0.0, min(1.0, cpu_pct / 100 * 0.4 + cpu_temp / 100 * 0.6))
    return max(0.0, min(1.0, cpu_pct / 100))


# ─────────────────────────────────────────────────────────────────────────────
#  DESKTOP PC SCENE DEFINITION
# ─────────────────────────────────────────────────────────────────────────────
def _desktop_scene(data: Dict, pulse: float) -> List[_Box]:
    """Return all boxes for the desktop PC, in draw order (back to front)."""

    # ── dynamic colors based on live data ──
    # CPU heat uses workload-aware thermal baseline when trained
    cpu_heat  = _thermal_aware_cpu_heat(
        data["cpu_pct"], data["cpu_temp"], data["gpu_pct"])
    gpu_heat  = max(0.0, min(1.0, data["gpu_temp"]/100 if data["gpu_temp"] else
                                   data["gpu_pct"]/100))
    ram_heat  = max(0.0, min(1.0, data["ram_pct"]/100))
    disk_heat = max(0.0, min(1.0, data["disk_pct"]/100))

    # Colors adjusted by heat
    cpu_col  = _heat(_C["cpu"],  cpu_heat)
    gpu_col  = _heat(_C["gpu"],  gpu_heat)
    ram_col  = _heat(_C["ram"],  ram_heat)
    disk_col = _heat(_C["ssd"],  disk_heat)

    # Pulse for hot components
    if cpu_heat > 0.68:
        cpu_col = _pulse(cpu_col, (220, 55, 35), pulse)
    if gpu_heat > 0.68:
        gpu_col = _pulse(gpu_col, (200, 40, 80), pulse)
    if ram_heat > 0.80:
        ram_col = _pulse(ram_col, (220, 80, 20), pulse)

    boxes: List[_Box] = []

    # ── Case outer shell ──────────────────────────────────────
    C = _C["case"]
    case_out = (50, 54, 68)   # subtle edge highlight
    # Back wall (y=4)
    boxes.append(_Box(0, 4, 0, 7.5, 0.12, 15,  _C["case_lo"], "case_back",
                      case_out, 1, 0.45, 0.35, 0.28))
    # Left wall (x=0)
    boxes.append(_Box(0, 0, 0, 0.12, 4, 15,    _C["case_lo"], "case_left",
                      case_out, 1, 0.40, 0.32, 0.25))
    # Bottom floor of case
    boxes.append(_Box(0, 0, 0, 7.5, 4, 0.12,   _C["case_lo"], "case_floor",
                      case_out, 1, 0.50, 0.38, 0.30))

    # ── PSU ───────────────────────────────────────────────────
    boxes.append(_Box(0.35, 0.3, 0.2, 4.2, 3.4, 2.5, _C["psu"], "psu",
                      (80, 96, 120), 2))

    # PSU vent lines (decorative thin boxes)
    for i in range(4):
        boxes.append(_Box(0.55+i*0.7, 0.3, 2.4, 0.3, 3.0, 0.08,
                          _shade(_C["psu"], 1.3), ""))

    # PSU fan grill on top
    boxes.append(_Box(0.5, 0.35, 2.72, 3.6, 3.0, 0.06, _shade(_C["psu"], 1.5), ""))

    # ── Motherboard PCB ───────────────────────────────────────
    boxes.append(_Box(0.5, 0.15, 3.0, 6.5, 0.18, 11.0, _C["mobo"], "mobo",
                      (28, 90, 60), 2))
    # PCB trace lines (decorative)
    for i in range(3):
        boxes.append(_Box(0.55+i*1.8, 0.14, 3.2+i*2.5, 1.2, 0.06, 0.06,
                          _shade(_C["mobo"], 1.6), ""))

    # ── SSD / Drive bay ──────────────────────────────────────
    boxes.append(_Box(0.4, 0.3, 2.85, 2.4, 1.8, 0.22, disk_col, "ssd",
                      (50, 190, 90), 2))
    # SSD connector
    boxes.append(_Box(2.5, 0.35, 2.82, 0.4, 0.5, 0.12, _C["hdd"], ""))

    # ── GPU ───────────────────────────────────────────────────
    boxes.append(_Box(0.55, 0.35, 6.2, 5.6, 2.0, 0.75, gpu_col, "gpu",
                      (140, 80, 220), 2))
    # GPU heatsink fins (small thin boxes on top of GPU)
    for i in range(6):
        boxes.append(_Box(0.7+i*0.8, 0.4, 6.95, 0.5, 1.8, 0.25,
                          _shade(gpu_col, 1.25), ""))
    # GPU fans
    for fx in (1.3, 3.1):
        boxes.append(_Box(fx, 0.38, 6.22, 1.2, 1.85, 0.6, _shade(gpu_col, 0.7), ""))
        boxes.append(_Box(fx+0.1, 0.42, 6.22, 1.0, 1.65, 0.58, _shade(gpu_col, 0.55), ""))

    # ── CPU ───────────────────────────────────────────────────
    # IHS (Integrated Heat Spreader)
    boxes.append(_Box(3.15, 0.38, 11.0, 1.9, 1.8, 0.42, cpu_col, "cpu",
                      (22, 210, 185), 2))
    # CPU socket frame
    boxes.append(_Box(3.0, 0.28, 10.85, 2.2, 2.1, 0.15, _shade(_C["mobo"], 0.8), ""))

    # ── Heatsink / AIO ───────────────────────────────────────
    hs = _C["hsink"]
    # Heatsink base
    boxes.append(_Box(3.0, 0.3, 11.42, 2.3, 2.0, 0.35, hs, "",
                      (165, 175, 188), 2))
    # Heatsink fins (many thin slices)
    for i in range(9):
        fx_off = 3.05 + i * 0.22
        fin_c  = _shade(hs, 1.1 - i*0.01)
        boxes.append(_Box(fx_off, 0.32, 11.77, 0.16, 1.85, 2.5, fin_c, "heatsink",
                          (165, 178, 195), 1))
    # Heatpipes on top
    for p_idx in range(3):
        boxes.append(_Box(3.1+p_idx*0.55, 0.33, 14.27, 0.18, 1.6, 0.18,
                          (180, 130, 50), ""))

    # ── RAM sticks ────────────────────────────────────────────
    num_ram = data.get("ram_slots", 2)
    ram_positions = [(5.3, 8.5), (5.65, 8.5), (6.0, 8.5), (6.35, 8.5)]
    for i in range(min(num_ram, 4)):
        rx, rz = ram_positions[i]
        boxes.append(_Box(rx, 0.38, rz, 0.22, 0.5, 3.9, ram_col, "ram",
                          (230, 175, 35), 2))
        # RAM spreader heat
        boxes.append(_Box(rx-0.03, 0.38, rz, 0.28, 0.5, 4.1,
                          _shade(ram_col, 0.85), ""))
        # RAM chip pads
        for chip in range(4):
            boxes.append(_Box(rx, 0.4, rz+0.3+chip*0.8, 0.15, 0.3, 0.4,
                              _shade(ram_col, 1.3), ""))

    # ── Case fans (140mm front + top) ─────────────────────────
    # Front intake fan
    boxes.append(_Box(1.8, 0.0, 9.0, 3.5, 0.22, 3.5, _C["fan"], "case_fan",
                      (48, 62, 85), 2))
    # Fan blades
    boxes.append(_Box(2.2, 0.0, 9.5, 2.7, 0.1, 2.5, _shade(_C["fan"], 1.4), ""))

    # Top exhaust fan
    boxes.append(_Box(1.5, 0.8, 14.88, 4.0, 3.2, 0.2, _C["fan"], "",
                      (48, 62, 85), 2))
    boxes.append(_Box(1.9, 1.0, 14.88, 3.2, 2.6, 0.08, _shade(_C["fan"], 1.4), ""))

    # ── Case frame (front and right side visible edges) ───────
    # The case front is intentionally open so internals remain visible.
    # Only thin structural rails are drawn at the front opening corners.
    edge_c = _C["case_hi"]
    edge_out = (60, 68, 88)
    # Right side edge (x=7.5)
    boxes.append(_Box(7.38, 0, 0, 0.12, 4, 15,  edge_c, "", edge_out, 1, 0.55, 0.42, 0.32))
    # Top lid
    boxes.append(_Box(0, 0, 14.88, 7.5, 4, 0.14, edge_c, "", edge_out, 1, 0.7, 0.55, 0.44))
    # Front opening corner rails (thin structural frame - no solid panel blocking internals)
    # Bottom-front horizontal rail
    boxes.append(_Box(0, 0, 0,     7.5, 0.1, 0.15, edge_c, "", edge_out, 1, 0.6, 0.5, 0.38))
    # Top-front horizontal rail
    boxes.append(_Box(0, 0, 14.73, 7.5, 0.1, 0.15, edge_c, "", edge_out, 1, 0.6, 0.5, 0.38))
    # Left-front vertical corner rail
    boxes.append(_Box(0,    0, 0, 0.15, 0.1, 15, edge_c, "", edge_out, 1, 0.6, 0.5, 0.38))
    # Right-front vertical corner rail
    boxes.append(_Box(7.35, 0, 0, 0.15, 0.1, 15, edge_c, "", edge_out, 1, 0.6, 0.5, 0.38))

    # LED strip (front bottom)
    led_col = _C["led_b"] if cpu_heat < 0.65 else _C["led_g"] if cpu_heat < 0.82 else (220, 50, 50)
    boxes.append(_Box(0.4, 0.0, 0.6, 6.5, 0.06, 0.12, led_col, ""))

    # ── Cable bundle ──────────────────────────────────────────
    boxes.append(_Box(1.0, 1.6, 3.1, 0.35, 1.5, 6.0, _shade(_C["wire_b"], 0.65), ""))
    boxes.append(_Box(0.6, 1.8, 2.8, 0.35, 1.2, 2.8, _shade(_C["wire_y"], 0.55), ""))

    return boxes


# ─────────────────────────────────────────────────────────────────────────────
#  LAPTOP SCENE DEFINITION
# ─────────────────────────────────────────────────────────────────────────────

# Laptop origin is shifted
_LOX = int((_CW // 2 - 40) * _SSAA)
_LOY = int((_CH - 130)      * _SSAA)   # raised 40 px to match desktop origin fix


def _laptop_scene(data: Dict, pulse: float) -> List[_Box]:
    """Return all boxes for laptop scene."""
    cpu_heat  = _thermal_aware_cpu_heat(
        data["cpu_pct"], data["cpu_temp"], data["gpu_pct"])
    gpu_heat  = max(0.0, min(1.0, data["gpu_pct"]/100))
    ram_heat  = max(0.0, min(1.0, data["ram_pct"]/100))
    disk_heat = max(0.0, min(1.0, data["disk_pct"]/100))

    cpu_col  = _heat(_C["cpu"],  cpu_heat)
    gpu_col  = _heat(_C["gpu"],  gpu_heat)
    ram_col  = _heat(_C["ram"],  ram_heat)
    disk_col = _heat(_C["ssd"],  disk_heat)

    if cpu_heat > 0.68:
        cpu_col = _pulse(cpu_col, (220, 55, 35), pulse)

    boxes: List[_Box] = []
    lo, lo2 = _LOX, _LOY

    # ── Laptop base (bottom chassis) ──────────────────────────
    base_c = (32, 36, 44)
    boxes.append(_Box(0, 0, 0, 12, 8, 0.6,  base_c,  "chassis",
                      (50, 55, 68), 2,
                      top_f=0.85, front_f=0.62, side_f=0.48))

    # Bottom vents
    for i in range(5):
        boxes.append(_Box(1.5+i*1.6, 7.5, 0.12, 1.0, 0.35, 0.35,
                          _shade(base_c, 1.5), ""))

    # Internal chassis lid (open internals view)
    boxes.append(_Box(0.2, 0.2, 0.62, 11.6, 7.6, 0.12, (20, 24, 32), ""))

    # ── Motherboard (horizontal, fills inside) ────────────────
    boxes.append(_Box(0.4, 0.4, 0.74, 11.2, 7.2, 0.18, _C["mobo"], "mobo",
                      (28, 90, 60), 2,
                      top_f=0.95, front_f=0.70, side_f=0.52))

    # ── Battery (large block at back) ─────────────────────────
    bat_c = (40, 60, 90)
    boxes.append(_Box(0.5, 4.8, 0.92, 11.0, 2.8, 0.9, bat_c, "battery",
                      (55, 80, 120), 2))
    boxes.append(_Box(0.6, 5.0, 1.82, 2.0, 0.3, 0.08, _shade(bat_c, 1.5), ""))

    # ── CPU (center-left area) ────────────────────────────────
    boxes.append(_Box(3.5, 1.5, 0.92, 2.0, 2.0, 0.45, cpu_col, "cpu",
                      (22, 210, 185), 2))
    # CPU heatsink + heatpipes
    boxes.append(_Box(3.4, 1.4, 1.37, 2.2, 2.2, 0.22, _C["hsink"], "heatsink",
                      (165, 178, 195), 2))
    for i in range(3):
        boxes.append(_Box(3.5, 1.5+i*0.55, 1.37, 4.0, 0.15, 0.12, (180, 130, 50), ""))
    boxes.append(_Box(5.5, 1.5, 1.37, 0.22, 2.0, 0.12, _C["hsink"], ""))

    # ── Cooling fan (left) ────────────────────────────────────
    boxes.append(_Box(1.0, 1.2, 0.92, 2.0, 2.0, 0.5, _C["fan"], "case_fan",
                      (48, 62, 85), 2))
    boxes.append(_Box(1.2, 1.4, 0.93, 1.6, 1.6, 0.45, _shade(_C["fan"], 1.5), ""))
    boxes.append(_Box(1.9, 1.9, 0.93, 0.2, 0.2, 0.45, _shade(_C["fan"], 0.7), ""))

    # ── GPU (dGPU, if present) ────────────────────────────────
    boxes.append(_Box(5.8, 1.5, 0.92, 3.0, 2.0, 0.38, gpu_col, "gpu",
                      (140, 80, 220), 2))

    # ── Cooling fan right ─────────────────────────────────────
    boxes.append(_Box(9.0, 1.2, 0.92, 2.0, 2.0, 0.5, _C["fan"], "",
                      (48, 62, 85), 2))
    boxes.append(_Box(9.2, 1.4, 0.93, 1.6, 1.6, 0.45, _shade(_C["fan"], 1.5), ""))

    # ── RAM sticks (soldered, shown as thin bars) ─────────────
    for i in range(2):
        boxes.append(_Box(3.6+i*1.2, 4.0, 0.92, 0.9, 0.45, 1.8, ram_col, "ram",
                          (230, 175, 35), 2))

    # ── SSD (M.2) ─────────────────────────────────────────────
    boxes.append(_Box(6.0, 4.0, 0.92, 3.0, 0.35, 0.55, disk_col, "ssd",
                      (50, 190, 90), 2))

    # ── Wireless card ─────────────────────────────────────────
    boxes.append(_Box(9.5, 3.5, 0.92, 1.5, 1.0, 0.38, (55, 65, 90), "",
                      (70, 85, 115), 1))

    # ── Screen hinge area ─────────────────────────────────────
    hinge_c = (38, 42, 52)
    boxes.append(_Box(0.4, 0, 0.3, 11.2, 0.55, 0.55, hinge_c, "",
                      (55, 60, 75), 2))

    # ── Screen (lid, slightly tilted - shown as angled box) ───
    # We approximate the screen as a slightly inclined box
    scr_base_c = (25, 28, 38)
    # Screen back shell
    boxes.append(_Box(0.3, -0.3, 0.55, 11.4, 0.5, 7.5, scr_base_c, "screen",
                      (45, 50, 65), 2,
                      top_f=0.7, front_f=0.55, side_f=0.42))
    # Screen bezel
    boxes.append(_Box(0.5, -0.35, 0.6, 11.0, 0.08, 7.2, (18, 20, 28), ""))
    # Screen display area
    boxes.append(_Box(0.65, -0.36, 0.75, 10.7, 0.06, 6.8, (15, 22, 42), ""))
    # Screen glow (simulated)
    boxes.append(_Box(0.72, -0.365, 0.82, 10.56, 0.04, 6.64, (22, 85, 120), ""))

    # ── Logo on lid ────────────────────────────────────────────
    boxes.append(_Box(5.3, -0.36, 3.8, 1.4, 0.06, 1.4, (55, 62, 78), ""))

    # ── Keyboard area on base (decorative) ────────────────────
    kb_c = (28, 32, 42)
    boxes.append(_Box(1.0, 1.0, 0.85, 10.0, 5.5, 0.06, kb_c, "", (38, 42, 55), 1,
                      top_f=0.9, front_f=0.65, side_f=0.5))
    # Key rows
    for row in range(5):
        for col in range(13):
            kx = 1.1 + col * 0.75
            ky = 1.2 + row * 0.85
            if kx < 10.8 and ky < 5.5:
                boxes.append(_Box(kx, ky, 0.91, 0.55, 0.6, 0.08, (36, 42, 56), ""))

    # ── Trackpad ───────────────────────────────────────────────
    boxes.append(_Box(4.5, 5.8, 0.82, 3.0, 1.8, 0.06, (36, 40, 52), "",
                      (50, 55, 70), 1,
                      top_f=0.92, front_f=0.68, side_f=0.52))

    return boxes


# ─────────────────────────────────────────────────────────────────────────────
#  LABEL / ANNOTATION SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
_LABEL_MAP_DESKTOP = {
    "cpu":      ("CPU",     _C["cpu"],     "right"),
    "heatsink": ("COOLER",  _C["hsink"],   "right"),
    "gpu":      ("GPU",     _C["gpu"],     "right"),
    "ram":      ("RAM",     _C["ram"],     "right"),
    "ssd":      ("SSD",     _C["ssd"],     "left"),
    "psu":      ("PSU",     _C["psu"],     "left"),
    "mobo":     ("MOBO",    _C["mobo"],    "left"),
    "case_fan": ("FAN",     _C["fan"],     "left"),
}

_LABEL_MAP_LAPTOP = {
    "cpu":     ("CPU",     _C["cpu"],     "right"),
    "gpu":     ("GPU",     _C["gpu"],     "right"),
    "ram":     ("RAM",     _C["ram"],     "right"),
    "ssd":     ("SSD",     _C["ssd"],     "right"),
    "battery": ("BATTERY", (55, 80, 120), "left"),
    "screen":  ("SCREEN",  (22, 85, 120), "left"),
    "mobo":    ("MOBO",    _C["mobo"],    "left"),
    "case_fan":("FAN",     _C["fan"],     "left"),
}


def _draw_labels(draw: "ImageDraw.ImageDraw", boxes: List[_Box],
                 label_map: dict, data: Dict, font_sm, font_xs,
                 ox=_OX, oy=_OY):
    """Draw floating labels with connecting lines for named components."""
    seen: Dict[str, bool] = {}

    for box in boxes:
        name = box.name
        if name not in label_map or name in seen:
            continue
        seen[name] = True

        label_txt, base_col, side = label_map[name]
        sx, sy = box.top_mid(ox, oy)

        # Sub-label with live data value
        sub_txt = ""
        if name == "cpu":
            pct = data.get("cpu_pct", 0)
            tmp = data.get("cpu_temp", 0)
            sub_txt = f"{pct:.0f}%  {tmp:.0f}°C" if tmp else f"{pct:.0f}%"
        elif name == "gpu":
            pct = data.get("gpu_pct", 0)
            tmp = data.get("gpu_temp", 0)
            sub_txt = f"{tmp:.0f}°C" if tmp else f"{pct:.0f}%"
        elif name == "ram":
            sub_txt = f"{data.get('ram_pct', 0):.0f}%  {data.get('ram_used', 0):.1f}GB"
        elif name == "ssd":
            sub_txt = f"{data.get('disk_pct', 0):.0f}%  {data.get('disk_free', 0):.0f}GB free"
        elif name == "heatsink":
            sub_txt = f"{data.get('cpu_temp', 0):.0f}°C" if data.get("cpu_temp") else ""

        # Label anchor
        if side == "right":
            lx = sx + 36 * _SSAA
            line_ex = sx + 28 * _SSAA
        else:
            lx = sx - 36 * _SSAA
            line_ex = sx - 28 * _SSAA

        ly = sy - 8 * _SSAA

        # Connecting dot + line
        dot_r = 3 * _SSAA
        col_t = tuple(int(c) for c in base_col)
        draw.ellipse([sx-dot_r, sy-dot_r, sx+dot_r, sy+dot_r], fill=col_t)
        draw.line([(sx, sy), (line_ex, ly)],
                  fill=_shade(col_t, 0.75), width=_SSAA)

        # Horizontal tick
        tick_len = 18 * _SSAA
        tick_end = lx + (tick_len if side == "right" else -tick_len)
        draw.line([(line_ex, ly), (tick_end, ly)],
                  fill=_shade(col_t, 0.65), width=_SSAA)

        # Label text - no `anchor` param (not supported by PIL default font)
        pad = 4 * _SSAA
        lbl_fill = tuple(int(c) for c in _shade(col_t, 1.25))
        if side == "right":
            tx = tick_end + pad
        else:
            # Right-align: estimate text width and shift left
            try:
                bbox = font_sm.getbbox(label_txt)
                tw = bbox[2] - bbox[0]
            except Exception:
                tw = len(label_txt) * 7 * _SSAA
            tx = tick_end - pad - tw
        ty = ly - 12 * _SSAA
        draw.text((tx, ty), label_txt, fill=lbl_fill, font=font_sm)

        if sub_txt:
            if side == "right":
                stx = tick_end + pad
            else:
                try:
                    sbbox = font_xs.getbbox(sub_txt)
                    stw = sbbox[2] - sbbox[0]
                except Exception:
                    stw = len(sub_txt) * 6 * _SSAA
                stx = tick_end - pad - stw
            draw.text((stx, ly + 2 * _SSAA), sub_txt, fill=(130, 145, 165), font=font_xs)


def _draw_floor(draw, img_w, img_h, ox, oy):
    """Draw a subtle isometric grid floor beneath the PC."""
    grid_col = _C["grid"]
    for gx in range(-2, 14):
        for gy in range(-1, 7):
            pts = _face(gx, gy, -0.05, 1.0, 1.0, 0.05, "top", ox, oy)
            _poly(draw, pts, _C["floor"], grid_col, 1)


def _draw_glow_ring(img: "Image.Image", cx: float, cy: float,
                    radius: float, color: Tuple, alpha: int = 60):
    """Draw a subtle radial glow ring using a temp layer + blur."""
    try:
        glow = Image.new("RGBA", img.size, (0,0,0,0))
        gd = ImageDraw.Draw(glow)
        r = int(radius)
        gd.ellipse([int(cx-r), int(cy-r), int(cx+r), int(cy+r)],
                   fill=(*color, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(radius // 2))
        img.alpha_composite(glow)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN VIEW CLASS
# ─────────────────────────────────────────────────────────────────────────────
class PCMapView(tk.Frame):
    """
    2.5D Isometric hardware map - Desktop PC + Laptop modes.
    Pillow-rendered, live-updating with hover tooltips.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#0a0e14", **kwargs)
        self._mode       = "desktop"   # "desktop" | "laptop"
        self._live_data  = _gather_live()
        self._pulse      = 0.0
        self._running    = True
        self._photo      = None
        self._hit_rects: Dict[str, Tuple] = {}   # name -> (x1,y1,x2,y2) in canvas px
        self._hovered    = None
        self._tooltip_win: Optional[tk.Toplevel] = None
        self._last_render_time = 0.0
        # Cached PIL fonts - loaded once, reused every frame
        self._font_sm = None
        self._font_xs = None

        if not _HAS_PIL:
            tk.Label(self, text="Pillow (PIL) not installed.\npip install Pillow",
                     font=(_BODY, 11), bg="#0a0e14", fg="#ef4444").pack(expand=True)
            return

        # Page switches destroy this widget via the PARENT's destroy() - the
        # Python-level destroy() override below is never called then, so the
        # 3 s data thread would leak (one per page visit). <Destroy> always fires.
        self.bind("<Destroy>", self._on_tk_destroy, add="+")

        self._build_ui()
        self._start_loop()

    def _on_tk_destroy(self, event=None):
        if event is None or event.widget is self:
            self._running = False

    # ── UI ────────────────────────────────────────────────────
    def _build_ui(self):
        # Top bar
        top_bar = tk.Frame(self, bg="#0f1117", height=34)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        tk.Label(top_bar, text="MAP OF COMPONENTS",
                 font=(_HDR, 9, "bold"),
                 bg="#0f1117", fg="#e2e8f0", padx=14).pack(side="left", fill="y")

        tk.Frame(top_bar, bg="#1f2937", width=1).pack(side="left", fill="y", pady=5)

        # Mode buttons
        self._btn_desktop = self._mode_btn(top_bar, "🖥  DESKTOP PC",  "desktop")
        self._btn_laptop  = self._mode_btn(top_bar, "💻  LAPTOP",      "laptop")

        # Status label (right side)
        self._status_lbl = tk.Label(top_bar, text="",
                                    font=(_MONO, 7),
                                    bg="#0f1117", fg="#8593a8", padx=12)
        self._status_lbl.pack(side="right", fill="y")

        tk.Label(top_bar, text="Hover over a component for details",
                 font=(_BODY, 7), bg="#0f1117", fg="#74839a", padx=10
                 ).pack(side="right", fill="y")

        # Canvas + vertical scrollbar so the scene never gets cut off
        _canvas_wrap = tk.Frame(self, bg="#08090f")
        _canvas_wrap.pack(fill="both", expand=True)

        _vsb = tk.Scrollbar(_canvas_wrap, orient="vertical",
                            bg="#0a0e14", troughcolor="#060911", width=6,
                            relief="flat", bd=0)
        _vsb.pack(side="right", fill="y")

        self._canvas = tk.Canvas(
            _canvas_wrap, width=_CW, height=_CH,
            bg="#08090f", highlightthickness=0, cursor="crosshair",
            yscrollcommand=_vsb.set, scrollregion=(0, 0, _CW, _CH),
        )
        self._canvas.pack(side="left", fill="both", expand=True)
        _vsb.config(command=self._canvas.yview)

        # Mouse-wheel scroll
        self._canvas.bind("<MouseWheel>",
                          lambda e: self._canvas.yview_scroll(
                              int(-1 * (e.delta / 120)), "units"))

        self._canvas.bind("<Motion>",   self._on_motion)
        self._canvas.bind("<Leave>",    self._on_leave)
        self._canvas.bind("<Button-1>", self._on_click)

        self._update_mode_buttons()

    def _mode_btn(self, parent, text, mode) -> tk.Label:
        btn = tk.Label(parent, text=text,
                       font=(_BODY, 7, "bold"),
                       bg="#0f1117", fg="#6b7280",
                       padx=12, pady=4, cursor="hand2")
        btn.pack(side="left")
        btn.bind("<Button-1>",  lambda e: self._set_mode(mode))
        btn.bind("<Enter>",
                 lambda e, b=btn, m=mode: b.config(
                     fg="#e2e8f0", bg="#1a1f2e") if self._mode != m else None)
        btn.bind("<Leave>",
                 lambda e, b=btn, m=mode: self._update_mode_buttons())
        return btn

    def _update_mode_buttons(self):
        for btn, mode in [(self._btn_desktop, "desktop"),
                          (self._btn_laptop,  "laptop")]:
            if self._mode == mode:
                btn.config(fg="#ffffff", bg="#3b82f6")
            else:
                btn.config(fg="#6b7280", bg="#0f1117")

    def _set_mode(self, mode: str):
        self._mode = mode
        self._update_mode_buttons()
        self._hide_tooltip()
        self._render_now()

    # ── Loop ──────────────────────────────────────────────────
    def _start_loop(self):
        self._data_thread()
        self._anim_tick()

    def _data_thread(self):
        """Fetch live data in background thread every 3s."""
        def _fetch():
            while self._running:
                try:
                    d = _gather_live()
                    if self._running:
                        self._live_data = d
                except Exception:
                    pass
                time.sleep(3.0)

        t = threading.Thread(target=_fetch, daemon=True)
        t.start()

    def _anim_tick(self):
        if not self._running:
            return
        self._pulse += 0.18
        self._render_now()
        if self.winfo_exists():
            self.after(120, self._anim_tick)

    # ── Render ────────────────────────────────────────────────
    def _render_now(self):
        if not _HAS_PIL:
            return
        try:
            img_w = _CW * _SSAA
            img_h = _CH * _SSAA

            # Create RGBA draw image
            img = Image.new("RGBA", (img_w, img_h), (*_C["bg"], 255))
            draw = ImageDraw.Draw(img)

            # Select scene + origin
            if self._mode == "desktop":
                ox, oy = _OX, _OY
                scene = _desktop_scene(self._live_data, self._pulse)
                label_map = _LABEL_MAP_DESKTOP
            else:
                ox, oy = _LOX, _LOY
                scene = _laptop_scene(self._live_data, self._pulse)
                label_map = _LABEL_MAP_LAPTOP

            # Floor grid
            _draw_floor(draw, img_w, img_h, ox, oy)

            # Draw all boxes in scene order
            hit: Dict[str, Tuple] = {}
            for box in scene:
                box.draw(draw, ox, oy)
                if box.name and box.name in label_map and box.name not in hit:
                    r = box.hit_rect(ox, oy)
                    # Convert to canvas coords (divide by SSAA)
                    hit[box.name] = (r[0]/_SSAA, r[1]/_SSAA,
                                     r[2]/_SSAA, r[3]/_SSAA)

            self._hit_rects = hit

            # Fonts - load once and cache; loading from disk every 120ms is expensive
            if self._font_sm is None:
                try:
                    self._font_sm = ImageFont.truetype(
                        "C:/Windows/Fonts/consola.ttf", 11 * _SSAA)
                    self._font_xs = ImageFont.truetype(
                        "C:/Windows/Fonts/consola.ttf",  9 * _SSAA)
                except Exception:
                    self._font_sm = ImageFont.load_default()
                    self._font_xs = self._font_sm
            font_sm = self._font_sm
            font_xs = self._font_xs

            # Labels - wrapped separately so label failure doesn't blank the canvas
            try:
                _draw_labels(draw, scene, label_map, self._live_data,
                             font_sm, font_xs, ox, oy)
            except Exception:
                pass

            # Mode badge (bottom-left)
            try:
                badge = "DESKTOP PC" if self._mode == "desktop" else "LAPTOP"
                draw.text((18*_SSAA, img_h - 22*_SSAA),
                          badge, fill=(40, 52, 72), font=font_sm)
            except Exception:
                pass

            # Glow under hot CPU
            try:
                if self._live_data.get("cpu_temp", 0) > 75 or self._live_data.get("cpu_pct", 0) > 75:
                    cpu_boxes = [b for b in scene if b.name == "cpu"]
                    if cpu_boxes:
                        cx, cy = cpu_boxes[0].screen_center(ox, oy)
                        alpha = int(30 + 25 * (math.sin(self._pulse) + 1) / 2)
                        _draw_glow_ring(img, cx, cy, 55 * _SSAA, (20, 200, 170), alpha)
            except Exception:
                pass

            # Downscale (SSAA anti-aliasing) - handle Pillow 9 vs 10 LANCZOS API
            _lanczos = getattr(getattr(Image, "Resampling", Image), "LANCZOS",
                               getattr(Image, "LANCZOS", 1))
            out = img.resize((_CW, _CH), _lanczos)
            self._photo = ImageTk.PhotoImage(out)

            # Put on canvas
            if self.winfo_exists():
                self._canvas.delete("all")
                self._canvas.create_image(0, 0, anchor="nw", image=self._photo)

            # Status bar
            try:
                d = self._live_data
                st = (f"CPU {d.get('cpu_pct',0):.0f}%  "
                      f"{d.get('cpu_temp',0):.0f}°C   "
                      f"GPU {d.get('gpu_temp',0):.0f}°C   "
                      f"RAM {d.get('ram_pct',0):.0f}%   "
                      f"DISK {d.get('disk_pct',0):.0f}%")
                if self.winfo_exists():
                    self._status_lbl.config(text=st)
            except Exception:
                pass

        except Exception as _e:
            import traceback as _tb
            print(f"[PCMap] render error: {_e}")
            # _tb.print_exc()  # uncomment for full traceback during debugging

    # ── Hover / Tooltip ───────────────────────────────────────
    def _on_motion(self, event):
        mx, my = event.x, event.y
        found = None
        for name, (x1, y1, x2, y2) in self._hit_rects.items():
            if x1 <= mx <= x2 and y1 <= my <= y2:
                found = name
                break

        if found != self._hovered:
            self._hovered = found
            self._hide_tooltip()
            if found:
                self._show_tooltip(found, event.x_root, event.y_root)

    def _on_leave(self, event):
        self._hovered = None
        self._hide_tooltip()

    def _on_click(self, event):
        pass   # reserved for future drill-down

    def _show_tooltip(self, comp: str, rx: int, ry: int):
        d = self._live_data
        lines = _tooltip_lines(comp, d)
        if not lines:
            return

        self._tooltip_win = tk.Toplevel(self)
        w = self._tooltip_win
        w.wm_overrideredirect(True)
        w.attributes("-topmost", True)
        w.wm_geometry(f"+{rx+16}+{ry-8}")

        outer = tk.Frame(w, bg="#151922",
                         highlightbackground="#2d3748",
                         highlightthickness=1)
        outer.pack()

        # Header
        comp_colors = {
            "cpu": "#12b09a", "gpu": "#7c3aed", "ram": "#c48f10",
            "ssd": "#22a855", "hdd": "#4d6a8a", "psu": "#4a6070",
            "mobo": "#1a6b40", "heatsink": "#9aa3ae", "case_fan": "#3a4e66",
            "battery": "#2d5a9a", "screen": "#1a5678", "chassis": "#2e3440",
        }
        hdr_col = comp_colors.get(comp, "#4b5563")
        hdr = tk.Frame(outer, bg=hdr_col)
        hdr.pack(fill="x")
        tk.Label(hdr, text=lines[0],
                 font=(_HDR, 9, "bold"),
                 bg=hdr_col, fg="#ffffff",
                 padx=10, pady=4).pack(anchor="w")

        # Body
        body = tk.Frame(outer, bg="#151922")
        body.pack(padx=8, pady=(4, 8), fill="x")
        for line in lines[1:]:
            if line == "---":
                tk.Frame(body, bg="#2d3748", height=1).pack(fill="x", pady=2)
            else:
                tk.Label(body, text=line,
                         font=(_MONO, 8),
                         bg="#151922", fg="#94a3b8",
                         anchor="w").pack(fill="x")

    def _hide_tooltip(self):
        if self._tooltip_win:
            try:
                self._tooltip_win.destroy()
            except Exception:
                pass
            self._tooltip_win = None

    def destroy(self):
        self._running = False
        self._hide_tooltip()
        super().destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  TOOLTIP CONTENT
# ─────────────────────────────────────────────────────────────────────────────
def _tooltip_lines(comp: str, d: Dict) -> List[str]:
    c_pct  = d.get("cpu_pct",  0)
    c_tmp  = d.get("cpu_temp", 0)
    c_ghz  = d.get("cpu_freq", 0)
    c_name = d.get("cpu_name", "CPU")
    g_pct  = d.get("gpu_pct",  0)
    g_tmp  = d.get("gpu_temp", 0)
    g_name = d.get("gpu_name", "GPU")
    r_pct  = d.get("ram_pct",  0)
    r_used = d.get("ram_used", 0)
    r_tot  = d.get("ram_total",0)
    dk_pct = d.get("disk_pct", 0)
    dk_fr  = d.get("disk_free",0)

    if comp == "cpu":
        status = ("OPTIMAL" if c_tmp < 70 else "WARM" if c_tmp < 83 else "HOT!")
        return [
            f"  CPU",
            f"{c_name}",
            "---",
            f"Load        {c_pct:.1f}%",
            f"Temperature {c_tmp:.1f} C" if c_tmp else f"Load  {c_pct:.1f}%",
            f"Frequency   {c_ghz:.2f} GHz" if c_ghz else "",
            "---",
            f"Status      {status}",
        ]
    elif comp == "gpu":
        status = ("OPTIMAL" if g_tmp < 80 else "WARM" if g_tmp < 90 else "HOT!")
        return [
            f"  GPU",
            f"{g_name}",
            "---",
            f"Temperature {g_tmp:.1f} C" if g_tmp else "No data",
            "---",
            f"Status      {status}",
        ]
    elif comp == "ram":
        return [
            "  RAM",
            f"Usage     {r_pct:.1f}%",
            f"Used      {r_used:.1f} / {r_tot:.1f} GB",
            "---",
            f"Free      {r_tot - r_used:.1f} GB",
        ]
    elif comp == "ssd":
        return [
            "  SSD / Storage  (C:)",
            f"Used      {dk_pct:.1f}%",
            f"Free      {dk_fr:.1f} GB",
        ]
    elif comp == "psu":
        return [
            "  PSU",
            "Power Supply Unit",
            "---",
            "No sensor data available",
        ]
    elif comp == "mobo":
        return [
            "  MOTHERBOARD",
            "System PCB",
            "---",
            "Hosts CPU, RAM, PCIe",
        ]
    elif comp == "heatsink":
        tmp = c_tmp
        return [
            "  CPU COOLER",
            f"CPU temp  {tmp:.1f} C" if tmp else "Temp sensor N/A",
            "Tower / AIO cooler",
        ]
    elif comp == "case_fan":
        return [
            "  CASE FAN",
            "System airflow",
            "Intake / Exhaust fan",
        ]
    elif comp == "battery":
        return [
            "  BATTERY",
            "Li-ion laptop battery",
            "---",
            "No sensor data",
        ]
    elif comp == "screen":
        return [
            "  DISPLAY",
            "Built-in laptop screen",
        ]
    elif comp == "chassis":
        return [
            "  CHASSIS",
            "Laptop frame / body",
        ]
    return []


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def create_pc_map_page(parent) -> PCMapView:
    """
    Build and return a PCMapView inside the given parent widget.
    Drop-in for yourpc_page tab system.
    """
    view = PCMapView(parent)
    view.pack(fill="both", expand=True)
    return view
