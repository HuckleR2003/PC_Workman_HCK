"""ui.components.pc_map_scene - the PC map's geometry (2026-11-20).

No Tk here: parts, their places, the projection, the drawing order, the
colours and an off-screen check of how much of each part can be seen.

Why it was rebuilt: the old map drew the BACK faces of every box (the face
at y instead of y + d), in list order instead of depth order, so parts
showed through each other and nothing could be read. Here
  * every part has a fixed place on a board grid (CPU socket, four DIMM
    slots, the PCIe slot, M.2, the power section), nothing shares a place;
  * the visible faces are the top, the one facing +y and the one facing +x;
  * the drawing order comes from a depth sort of the boxes (A goes first
    when it lies wholly behind B on some axis);
  * tests measure that each part can actually be seen (visibility()).

Coordinates: x goes to the lower right of the screen, y to the lower left,
z up. Units are arbitrary; fit() scales the scene to the canvas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

COS30 = math.cos(math.radians(30))
SIN30 = 0.5

# ── colours ──────────────────────────────────────────────────────────────
NEUTRAL = (92, 106, 128)
STEEL = (122, 134, 152)
DARK = (34, 40, 52)
BOARD = (22, 58, 46)
BOARD_EDGE = (34, 84, 64)
FAN = (52, 62, 80)
COPPER = (176, 112, 56)
SCREEN = (24, 56, 96)
CHASSIS = (40, 45, 56)
BATTERY = (48, 66, 98)

COOL = (34, 197, 94)
WARM = (234, 179, 8)
HOT = (239, 68, 68)


def heat_color(heat: Optional[float]) -> Tuple[int, int, int]:
    """0 green, 0.5 amber, 1 red; None (no data) a neutral grey-blue."""
    if heat is None:
        return NEUTRAL
    h = max(0.0, min(1.0, heat))
    if h <= 0.5:
        a, b, t = COOL, WARM, h / 0.5
    else:
        a, b, t = WARM, HOT, (h - 0.5) / 0.5
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade(rgb, f):
    return tuple(min(255, max(0, int(c * f))) for c in rgb)


# ── parts ────────────────────────────────────────────────────────────────
@dataclass
class Part:
    key: str                  # what the hover panel describes: cpu, gpu, ram, ...
    x: float
    y: float
    z: float
    w: float
    d: float
    h: float
    role: str = "neutral"     # heat:cpu | heat:gpu | heat:ram | board | steel | dark | fan | ...
    idx: int = 0              # e.g. which RAM stick, which drive
    label: bool = False       # carries the key's label on the map
    ax: float = 0.5           # where on its top the label points (0..1 of w, d)
    ay: float = 0.5
    uid: int = field(default=0, compare=False)

    def behind(self, o: "Part") -> bool:
        """True when this box lies wholly behind o on some axis."""
        e = 1e-6
        return (self.x + self.w <= o.x + e or self.y + self.d <= o.y + e
                or self.z + self.h <= o.z + e)


def _p(x, y, z):
    return ((x - y) * COS30, (x + y) * SIN30 - z)


def faces(p: Part):
    """The three visible faces in screen units: top, +y side, +x side."""
    x, y, z, w, d, h = p.x, p.y, p.z, p.w, p.d, p.h
    top = [_p(x, y, z + h), _p(x + w, y, z + h), _p(x + w, y + d, z + h), _p(x, y + d, z + h)]
    left = [_p(x, y + d, z), _p(x + w, y + d, z), _p(x + w, y + d, z + h), _p(x, y + d, z + h)]
    right = [_p(x + w, y, z), _p(x + w, y + d, z), _p(x + w, y + d, z + h), _p(x + w, y, z + h)]
    return top, left, right


def hull(p: Part):
    """The outline of the box on screen (six corners)."""
    x, y, z, w, d, h = p.x, p.y, p.z, p.w, p.d, p.h
    return [_p(x, y, z + h), _p(x + w, y, z + h), _p(x + w, y, z),
            _p(x + w, y + d, z), _p(x, y + d, z), _p(x, y + d, z + h)]


def top_center(p: Part):
    return _p(p.x + p.w * p.ax, p.y + p.d * p.ay, p.z + p.h)


def order(parts: List[Part]) -> List[Part]:
    """Back to front. A topological sort on "behind"; ties by depth."""
    n = len(parts)
    after = [[] for _ in range(n)]
    indeg = [0] * n
    for i in range(n):
        for j in range(n):
            if i != j and parts[i].behind(parts[j]) and not parts[j].behind(parts[i]):
                after[i].append(j)
                indeg[j] += 1

    def depth(i):
        p = parts[i]
        return (p.x + p.w / 2 + p.y + p.d / 2, p.z)
    ready = sorted((i for i in range(n) if indeg[i] == 0), key=depth)
    out = []
    while ready:
        i = ready.pop(0)
        out.append(parts[i])
        for j in after[i]:
            indeg[j] -= 1
            if indeg[j] == 0:
                ready.append(j)
        ready.sort(key=depth)
    if len(out) < n:                       # a cycle: should not happen, fall back
        rest = [parts[i] for i in sorted(range(n), key=depth) if parts[i] not in out]
        out += rest
    return out


def point_in(poly, x, y) -> bool:
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi:
            inside = not inside
        j = i
    return inside


# ── the two scenes ───────────────────────────────────────────────────────
def desktop(ram_sticks: int = 2, has_gpu: bool = True, nvme: bool = True,
            sata: int = 1) -> List[Part]:
    """An ATX board seen from above at an angle, the PSU and SATA drives
    beside it. Places are fixed: nothing moves when a part is missing."""
    P = Part
    s = [
        P("mobo", 0, 0, 0, 12, 10, 0.3, "board", label=True, ax=0.6, ay=0.93),
        # rear I/O cover and the power section around the socket
        P("mobo", 0.3, 0.4, 0.3, 1.1, 4.4, 1.0, "dark"),
        P("vrm", 1.8, 1.0, 0.3, 0.8, 3.6, 0.7, "steel", label=True),
        P("vrm", 3.0, 0.3, 0.3, 3.6, 0.8, 0.7, "steel"),
        # CPU: socket, cooler base, tower, fan
        P("cpu", 3.0, 1.6, 0.3, 3.0, 3.0, 0.15, "dark"),
        P("cpu", 3.3, 1.9, 0.45, 2.4, 2.4, 0.25, "steel"),
        P("cpu", 3.5, 2.2, 0.7, 2.0, 1.6, 1.9, "heat:cpu", label=True),
        P("cpu", 3.5, 3.8, 0.7, 2.0, 0.25, 1.9, "fan"),
        # 24-pin and chipset
        P("mobo", 10.9, 1.2, 0.3, 0.7, 2.8, 0.6, "dark"),
        P("chipset", 8.8, 7.9, 0.3, 1.8, 1.6, 0.35, "steel"),
        # PCIe x16 slot
        P("pcie", 0.8, 7.4, 0.3, 7.0, 0.35, 0.15, "dark"),
        # M.2 slot right of the DIMMs (an empty slot is drawn dark)
        P("nvme" if nvme else "m2", 9.0, 4.8, 0.3, 2.6, 0.7, 0.12 if nvme else 0.05,
          "drive" if nvme else "dark", label=nvme),
    ]
    # four DIMM slots, sticks in A2/B2 first (slots 2 and 4), like the manuals say
    fill = {1: [1], 2: [1, 3], 3: [0, 1, 3], 4: [0, 1, 2, 3]}.get(max(0, min(4, ram_sticks)), [])
    for i in range(4):
        x = 7.0 + i * 0.5
        s.append(P("ram_slot", x, 0.8, 0.3, 0.26, 5.6, 0.12, "dark"))
        if i in fill:
            s.append(P("ram", x, 0.8, 0.42, 0.26, 5.6, 1.4, "heat:ram", idx=i,
                       label=(i == fill[-1])))
    if has_gpu:
        s += [P("gpu", 0.6, 7.25, 0.45, 7.4, 1.25, 1.5, "heat:gpu", label=True),
              P("gpu", 0.6, 8.5, 0.45, 7.4, 0.08, 1.5, "fan")]
    # beside the board
    s.append(P("psu", 13.4, 0.4, 0, 4.0, 3.2, 2.2, "neutral", label=True))
    for i in range(max(0, min(3, sata))):
        s.append(P("drive", 13.6, 4.4 + i * 1.9, 0, 3.0, 1.5, 0.5, "drive", idx=i, label=(i == 0)))
    return _number(s)


def laptop(has_gpu: bool = True) -> List[Part]:
    """A laptop with the bottom cover off: board, cooling, battery, and the
    screen behind it."""
    P = Part
    s = [
        P("screen", 0.4, -0.7, 0, 13.2, 0.35, 8.0, "screen"),
        P("screen", 0.9, -0.35, 0.5, 12.2, 0.03, 7.0, "display", label=True),
        P("chassis", 0, 0, 0, 14, 9.6, 0.45, "chassis"),
        P("mobo", 0.6, 0.5, 0.45, 12.8, 5.0, 0.12, "board", label=True, ax=0.92, ay=0.3),
        P("fan", 0.9, 0.8, 0.57, 2.4, 2.4, 0.35, "fan", label=True),
        P("fan", 10.7, 0.8, 0.57, 2.4, 2.4, 0.35, "fan", idx=1),
        P("cpu", 3.3, 1.4, 0.57, 7.4, 0.45, 0.18, "copper"),
        P("cpu", 4.0, 2.3, 0.57, 1.8, 1.8, 0.22, "heat:cpu", label=True),
        P("ram", 3.6, 4.4, 0.57, 2.6, 0.9, 0.16, "heat:ram", idx=0),
        P("ram", 6.5, 4.4, 0.57, 2.6, 0.9, 0.16, "heat:ram", idx=1, label=True),
        P("nvme", 9.8, 3.5, 0.57, 2.8, 0.7, 0.14, "drive", label=True),
        P("battery", 0.9, 6.0, 0.45, 12.2, 3.0, 0.45, "battery", label=True),
    ]
    if has_gpu:
        s.append(P("gpu", 7.0, 2.3, 0.57, 2.0, 1.8, 0.22, "heat:gpu", label=True))
    return _number(s)


def _number(parts):
    for i, p in enumerate(parts, 1):
        p.uid = i
    return parts


# ── colours of a part ────────────────────────────────────────────────────
_ROLE = {"neutral": NEUTRAL, "steel": STEEL, "dark": DARK, "board": BOARD, "fan": FAN,
         "copper": COPPER, "screen": SCREEN, "chassis": CHASSIS, "battery": BATTERY,
         "drive": (60, 120, 150), "display": (40, 96, 150)}


def color_of(p: Part, heat: Dict[str, Optional[float]]):
    if p.role.startswith("heat:"):
        return heat_color(heat.get(p.role[5:]))
    return _ROLE.get(p.role, NEUTRAL)


# ── fitting to a canvas ──────────────────────────────────────────────────
def bounds(parts):
    xs, ys = [], []
    for p in parts:
        for x, y in hull(p):
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def fit(parts, w, h, margin=24):
    """(scale, ox, oy) that put the scene in the middle of w x h."""
    x0, y0, x1, y1 = bounds(parts)
    sc = min((w - 2 * margin) / max(1e-6, x1 - x0), (h - 2 * margin) / max(1e-6, y1 - y0))
    ox = (w - (x1 - x0) * sc) / 2 - x0 * sc
    oy = (h - (y1 - y0) * sc) / 2 - y0 * sc
    return sc, ox, oy


def to_screen(pts, f):
    sc, ox, oy = f
    return [(ox + x * sc, oy + y * sc) for x, y in pts]


# ── drawing (Pillow) ─────────────────────────────────────────────────────
def render(parts, w, h, heat, hovered=None, ssaa=2, bg=(10, 14, 20)):
    """The scene as a Pillow image of w x h. hovered: a key to outline."""
    from PIL import Image, ImageDraw
    W, H = w * ssaa, h * ssaa
    img = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(img)
    f = fit(parts, W, H, 24 * ssaa)
    for p in order(parts):
        base = color_of(p, heat)
        hi = hovered is not None and p.key == hovered
        if hi:
            base = shade(base, 1.25)
        top, left, right = faces(p)
        edge = shade(base, 1.45) if not hi else (255, 255, 255)
        for pts, k in ((left, 0.72), (right, 0.55), (top, 1.0)):
            sp = [(int(x), int(y)) for x, y in to_screen(pts, f)]
            dr.polygon(sp, fill=shade(base, k))
            dr.line(sp + [sp[0]], fill=edge if pts is top else shade(base, 0.9 if not hi else 1.6),
                    width=max(1, ssaa if not hi else 2 * ssaa))
    if ssaa > 1:
        lz = getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)
        img = img.resize((w, h), lz)
    return img, fit(parts, w, h, 24)


def hit(parts, f, x, y) -> Optional[str]:
    """The key of the front-most part under (x, y) in canvas pixels."""
    for p in reversed(order(parts)):
        if point_in(to_screen(hull(p), f), x, y):
            return p.key
    return None


def label_points(parts, f) -> Dict[str, Tuple[float, float]]:
    """Where each labelled key's tag goes: the top centre of its labelled part."""
    out = {}
    for p in parts:
        if p.label and p.key not in out:
            out[p.key] = to_screen([top_center(p)], f)[0]
    return out


def visibility(parts, w=640, h=480) -> Dict[str, float]:
    """For each key, the share of its outline that is not covered by parts
    drawn in front of it (0..1). Off-screen, for the tests."""
    from PIL import Image, ImageDraw
    f = fit(parts, w, h)
    seen = Image.new("L", (w, h), 0)            # uids stay under 256
    ds = ImageDraw.Draw(seen)
    for p in order(parts):
        ds.polygon([(int(x), int(y)) for x, y in to_screen(hull(p), f)], fill=p.uid)
    key_of = {p.uid: p.key for p in parts}
    front: Dict[str, int] = {}
    for v, n in enumerate(seen.histogram()):
        if v and n:
            front[key_of[v]] = front.get(key_of[v], 0) + n
    out = {}
    for k in {p.key for p in parts}:
        alone = Image.new("L", (w, h), 0)
        da = ImageDraw.Draw(alone)
        for p in parts:
            if p.key == k:      # the key's own parts may cover each other
                da.polygon([(int(x), int(y)) for x, y in to_screen(hull(p), f)], fill=1)
        full = alone.histogram()[1]
        out[k] = front.get(k, 0) / full if full else 0.0
    return out
