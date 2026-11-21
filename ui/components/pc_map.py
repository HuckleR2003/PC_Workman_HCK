"""ui.components.pc_map - My PC → Map (rebuilt 2026-11-20).

The map on the left (ui/components/pc_map_scene.py draws it), this PC and
its temperatures on the right, and below them "under the cursor": the model
and numbers of the part the mouse points at.

  * colours: green → amber → red from the temperature (or the load when no
    sensor reads it), now or as a 7-day average, switched at the top;
  * a click on the CPU, GPU or RAM opens its history (Activity Memory);
  * nothing is drawn while the tab is hidden (the tab is kept alive, and the
    old map redrew itself every 120 ms even then); it redraws when the data
    changes, the mouse moves to another part or the size changes;
  * the worker thread only touches a plain object (_Shared), never Tk.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from typing import Dict, List, Optional

from utils.fonts import UI as _BODY, HDR as _HDR

try:
    from PIL import ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

from ui.components import pc_map_scene as S

BG = "#0a0e14"
BAR = "#0f1117"
PANEL = "#0f141c"
PANEL2 = "#131a24"
LINE = "#1f2937"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
DIM = "#64748b"
BLUE = "#3b82f6"
CANVAS_BG = (10, 14, 20)
RIGHT_W = 330

_TX = {
    "desktop": {"pl": "Komputer stacjonarny", "en": "Desktop PC"},
    "laptop": {"pl": "Laptop", "en": "Laptop"},
    "colors": {"pl": "Kolory:", "en": "Colours:"},
    "now": {"pl": "Teraz", "en": "Now"},
    "week": {"pl": "Średnio 7 dni", "en": "7-day average"},
    "cool": {"pl": "chłodno", "en": "cool"},
    "hot": {"pl": "gorąco", "en": "hot"},
    "this_pc": {"pl": "TEN KOMPUTER", "en": "THIS PC"},
    "thermal": {"pl": "TEMPERATURY I OBCIĄŻENIE", "en": "TEMPERATURES AND LOAD"},
    "under": {"pl": "POD KURSOREM", "en": "UNDER THE CURSOR"},
    "hint": {"pl": "Najedź na część na mapie: tu pojawi się jej model i liczby.",
             "en": "Point at a part on the map: its model and numbers show here."},
    "click_hist": {"pl": "Kliknij, aby otworzyć jej historię.", "en": "Click to open its history."},
    "kind": {"pl": "Rodzaj", "en": "Kind"},
    "kind_desktop": {"pl": "komputer stacjonarny", "en": "desktop PC"},
    "kind_laptop": {"pl": "laptop", "en": "laptop"},
    "board": {"pl": "Płyta", "en": "Board"},
    "drives": {"pl": "Dyski", "en": "Drives"},
    "unknown": {"pl": "nieznany", "en": "unknown"},
    "loading": {"pl": "wczytuję…", "en": "loading…"},
    "col_now": {"pl": "teraz", "en": "now"},
    "col_avg": {"pl": "śr. 7 dni", "en": "7-day avg"},
    "col_max": {"pl": "maks. 7 dni", "en": "7-day max"},
    "no_cpu_sensor": {"pl": "Temperatury CPU Windows nie podaje: czyta ją LibreHardwareMonitor (Ustawienia). Do tego czasu kolor CPU to obciążenie.",
                      "en": "Windows does not give the CPU temperature: LibreHardwareMonitor reads it (Settings). Until then the CPU colour is its load."},
    "load": {"pl": "Obciążenie", "en": "Load"},
    "temp": {"pl": "Temperatura", "en": "Temperature"},
    "avg7": {"pl": "Średnio 7 dni", "en": "7-day average"},
    "max7": {"pl": "Najwyżej 7 dni", "en": "7-day peak"},
    "cores": {"pl": "Rdzenie / wątki", "en": "Cores / threads"},
    "clock": {"pl": "Zegar maks.", "en": "Max clock"},
    "vram": {"pl": "Pamięć karty", "en": "Video memory"},
    "driver": {"pl": "Sterownik", "en": "Driver"},
    "used": {"pl": "Zajęte", "en": "In use"},
    "sticks": {"pl": "Kości", "en": "Sticks"},
    "size": {"pl": "Pojemność", "en": "Size"},
    "bus": {"pl": "Złącze", "en": "Interface"},
    "c_drive": {"pl": "Dysk C:", "en": "Drive C:"},
    "free": {"pl": "{f} wolne z {t}", "en": "{f} free of {t}"},
    "battery_lv": {"pl": "Naładowanie", "en": "Charge"},
    "plugged": {"pl": "podłączony do prądu", "en": "plugged in"},
    "on_batt": {"pl": "na baterii", "en": "on battery"},
    "heat_by_temp": {"pl": "Kolor: temperatura.", "en": "Colour: temperature."},
    "heat_by_load": {"pl": "Kolor: obciążenie (brak czujnika temperatury).", "en": "Colour: load (no temperature sensor)."},
    "heat_by_use": {"pl": "Kolor: zajęta pamięć.", "en": "Colour: memory in use."},
    "no_data": {"pl": "brak danych", "en": "no data"},
}

# name of each part, and one line about what it is
_PART = {
    "cpu": ({"pl": "Procesor (CPU)", "en": "Processor (CPU)"}, None),
    "gpu": ({"pl": "Karta graficzna (GPU)", "en": "Graphics card (GPU)"}, None),
    "ram": ({"pl": "Pamięć RAM", "en": "Memory (RAM)"}, None),
    "nvme": ({"pl": "Dysk M.2 (NVMe)", "en": "M.2 drive (NVMe)"}, None),
    "m2": ({"pl": "Gniazdo M.2", "en": "M.2 slot"},
           {"pl": "Wolne gniazdo na szybki dysk NVMe.", "en": "A free slot for a fast NVMe drive."}),
    "drive": ({"pl": "Dyski SATA", "en": "SATA drives"}, None),
    "mobo": ({"pl": "Płyta główna", "en": "Motherboard"}, None),
    "chipset": ({"pl": "Chipset", "en": "Chipset"},
                {"pl": "Łączy procesor z dyskami SATA, USB i resztą płyty.", "en": "Connects the CPU with SATA drives, USB and the rest of the board."}),
    "vrm": ({"pl": "Sekcja zasilania CPU", "en": "CPU power section"},
            {"pl": "Zamienia 12 V z zasilacza na napięcie procesora. Windows nie ma tu czujnika.",
             "en": "Turns the PSU's 12 V into the CPU's voltage. Windows has no sensor here."}),
    "pcie": ({"pl": "Gniazdo PCIe x16", "en": "PCIe x16 slot"},
             {"pl": "Tu siedzi karta graficzna.", "en": "The graphics card sits here."}),
    "ram_slot": ({"pl": "Gniazda RAM", "en": "RAM slots"},
                 {"pl": "Cztery gniazda DIMM; dwie kości siedzą zwykle w drugim i czwartym.",
                  "en": "Four DIMM slots; two sticks usually go in the second and the fourth."}),
    "psu": ({"pl": "Zasilacz", "en": "Power supply"},
            {"pl": "Model nieznany: Windows nie widzi zasilacza ani jego mocy. Sprawdzisz go na naklejce z boku.",
             "en": "Model unknown: Windows does not see the power supply or its wattage. The label on its side has it."}),
    "screen": ({"pl": "Ekran", "en": "Screen"}, None),
    "battery": ({"pl": "Bateria", "en": "Battery"}, None),
    "fan": ({"pl": "Wentylatory", "en": "Fans"},
            {"pl": "Wyciągają ciepło z radiatora procesora i karty. Windows nie podaje ich obrotów.",
             "en": "They pull heat off the CPU and GPU heatsink. Windows does not report their speed."}),
    "chassis": ({"pl": "Obudowa", "en": "Chassis"}, None),
}

_LABEL = {
    "cpu": "CPU", "gpu": "GPU", "ram": "RAM", "nvme": "NVMe", "drive": "SATA",
    "psu": {"pl": "Zasilacz", "en": "PSU"}, "mobo": {"pl": "Płyta", "en": "Board"},
    "vrm": "VRM", "screen": {"pl": "Ekran", "en": "Screen"},
    "battery": {"pl": "Bateria", "en": "Battery"}, "fan": {"pl": "Wentylator", "en": "Fan"},
}


def _lang():
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def _tx(k, lang=None, **kw):
    s = _TX[k][lang or _lang()]
    return s.format(**kw) if kw else s


# ── data ─────────────────────────────────────────────────────────────────
def gather_live() -> Dict:
    d = {"cpu_pct": None, "cpu_temp": None, "gpu_pct": None, "gpu_temp": None,
         "ram_pct": None, "ram_used": None, "ram_total": None, "c_free": None, "c_total": None,
         "battery": None, "plugged": None}
    try:
        import psutil
        d["cpu_pct"] = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        d["ram_pct"], d["ram_used"], d["ram_total"] = vm.percent, vm.used, vm.total
        du = psutil.disk_usage("C:\\")
        d["c_free"], d["c_total"] = du.free, du.total
        b = psutil.sensors_battery()
        if b is not None:
            d["battery"], d["plugged"] = b.percent, b.power_plugged
    except Exception:
        pass
    try:
        from core.hardware_sensors import get_cpu_temp, get_gpu_temp, get_gpu_usage
        d["cpu_temp"] = get_cpu_temp() or None
        d["gpu_temp"] = get_gpu_temp() or None
        g = get_gpu_usage()
        d["gpu_pct"] = g if g or d["gpu_temp"] else None
    except Exception:
        pass
    return d


def gather_week(days: int = 7) -> Dict:
    out = {}
    try:
        from hck_stats_engine import history
        now = time.time()
        for comp in ("cpu", "gpu", "ram"):
            st = history.stats(comp, now - days * 86400, now)
            if st.get("has_data"):
                out[comp] = {"avg": st["avg"], "max": st["max"],
                             "temp_avg": st.get("temp_avg"), "temp_max": st.get("temp_max")}
    except Exception:
        pass
    return out


def disk_buses() -> List[Dict]:
    """[{"name", "bus", "media", "size"}] from Get-PhysicalDisk (no admin
    rights needed). The model name alone does not say NVMe or SATA."""
    try:
        import json
        import subprocess
        ps = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-PhysicalDisk | "
              "Select-Object FriendlyName, @{n='Bus';e={\"$($_.BusType)\"}}, "
              "@{n='Media';e={\"$($_.MediaType)\"}}, Size | ConvertTo-Json -Compress")
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        data = json.loads((r.stdout or "").strip() or "[]")
        if isinstance(data, dict):
            data = [data]
        return [{"name": str(x.get("FriendlyName") or "").strip(), "bus": str(x.get("Bus") or ""),
                 "media": str(x.get("Media") or ""), "size": float(x.get("Size") or 0)}
                for x in data if isinstance(x, dict)]
    except Exception:
        return []


def gather_hw() -> Dict:
    hw = {}
    try:
        from core.hardware_detector import get_hardware_detector
        det = get_hardware_detector()
        hw = dict(det.ensure_data() if hasattr(det, "ensure_data") else det.get_data())
    except Exception:
        pass
    hw["disks"] = disk_buses()
    try:
        from core import machine_type
        hw["kind"] = machine_type.get()
    except Exception:
        hw["kind"] = None
    return hw


def layout_args(hw: Dict) -> Dict:
    """What the scene needs to know: sticks, a GPU, NVMe, SATA drives."""
    mods = ((hw.get("ram") or {}).get("modules") or [])
    gpu = (hw.get("gpu") or {}).get("name", "")
    disks = hw.get("disks") or []
    nvme = [x for x in disks if x["bus"].lower() == "nvme"]
    other = [x for x in disks if x["bus"].lower() not in ("nvme", "usb")]
    return {"ram_sticks": len(mods) or 2,
            "has_gpu": bool(gpu) and gpu != "Not detected",
            "nvme": bool(nvme) or not disks,
            "sata": len(other)}


def _norm(v, lo, hi):
    if v is None:
        return None
    return max(0.0, min(1.0, (float(v) - lo) / (hi - lo)))


def heat_values(live: Dict, week: Dict, mode: str = "now") -> Dict[str, Optional[float]]:
    """0..1 per coloured part. Temperature first (40 °C cool, 85 °C hot),
    the load when nothing reads the temperature; RAM by memory in use."""
    if mode == "week":
        c, g, r = week.get("cpu") or {}, week.get("gpu") or {}, week.get("ram") or {}
        ct, cl, gt, gl, rp = c.get("temp_avg"), c.get("avg"), g.get("temp_avg"), g.get("avg"), r.get("avg")
    else:
        ct, cl = live.get("cpu_temp"), live.get("cpu_pct")
        gt, gl = live.get("gpu_temp"), live.get("gpu_pct")
        rp = live.get("ram_pct")
    return {"cpu": _norm(ct, 40, 85) if ct else _norm(cl, 0, 100),
            "gpu": _norm(gt, 40, 85) if gt else _norm(gl, 0, 100),
            "ram": _norm(rp, 40, 95)}


def _gb(n):
    return f"{n / 1024 ** 3:.0f} GB" if n else "-"


def _num(v, unit, nd=0):
    if v is None:
        return "-"
    return f"{v:.{nd}f}{unit}".replace(".", ",") if _lang() == "pl" else f"{v:.{nd}f}{unit}"


def _pair(w):
    """ "12 %  ·  41 °C", without the part nothing measured."""
    return "  ·  ".join(v for v in (_num(w.get("avg"), " %"), _num(w.get("temp_avg"), " °C")) if v != "-") or "-"


def details(key: str, live: Dict, week: Dict, hw: Dict, lang: str = "pl"):
    """(title, [(caption, value)], note) for the panel under the cursor."""
    lang = "en" if lang == "en" else "pl"
    name, about = _PART.get(key, ({"pl": key, "en": key}, None))
    rows = []
    note = about[lang] if about else ""
    T = lambda k: _TX[k][lang]                       # noqa: E731
    wk = week or {}
    if key == "cpu":
        cpu = hw.get("cpu") or {}
        rows += [("", cpu.get("name") or T("unknown"))]
        if cpu.get("cores_physical"):
            rows.append((T("cores"), f"{cpu['cores_physical']} / {cpu.get('cores_logical') or '-'}"))
        if cpu.get("freq_max_mhz"):
            rows.append((T("clock"), f"{cpu['freq_max_mhz'] / 1000:.2f} GHz"))
        rows += [(T("load"), _num(live.get("cpu_pct"), " %")),
                 (T("temp"), _num(live.get("cpu_temp"), " °C"))]
        w = wk.get("cpu") or {}
        if w:
            rows.append((T("avg7"), _pair(w)))
        note = T("heat_by_temp") if live.get("cpu_temp") else T("no_cpu_sensor")
        note += " " + T("click_hist")
    elif key == "gpu":
        gpu = hw.get("gpu") or {}
        rows += [("", gpu.get("name") or T("unknown"))]
        if gpu.get("vram_mb"):
            rows.append((T("vram"), f"{gpu['vram_mb'] / 1024:.0f} GB"))
        if gpu.get("driver_version"):
            rows.append((T("driver"), f"{gpu['driver_version']}  ({gpu.get('driver_date') or '-'})"))
        rows += [(T("load"), _num(live.get("gpu_pct"), " %")),
                 (T("temp"), _num(live.get("gpu_temp"), " °C"))]
        w = wk.get("gpu") or {}
        if w:
            rows.append((T("avg7"), _pair(w)))
        note = (T("heat_by_temp") if live.get("gpu_temp") else T("heat_by_load")) + " " + T("click_hist")
    elif key == "ram":
        ram = hw.get("ram") or {}
        mods = ram.get("modules") or []
        if mods:
            sizes = sorted({m.get("capacity_gb") for m in mods if m.get("capacity_gb")})
            speed = max((m.get("speed_mhz") or 0) for m in mods)
            sz = "/".join(f"{s:g}" for s in sizes) + " GB" if sizes else ""
            rows.append((T("sticks"), f"{len(mods)} × {sz}" + (f", {speed} MHz" if speed else "")))
        rows.append((T("used"), f"{_gb(live.get('ram_used'))} / {_gb(live.get('ram_total'))}  ({_num(live.get('ram_pct'), ' %')})"))
        w = wk.get("ram") or {}
        if w:
            rows.append((T("avg7"), _num(w.get("avg"), " %")))
        note = T("heat_by_use") + " " + T("click_hist")
    elif key in ("nvme", "drive"):
        disks = hw.get("disks") or []
        want = [x for x in disks if (x["bus"].lower() == "nvme") == (key == "nvme")
                and x["bus"].lower() != "usb"]
        for x in want:
            rows.append(("", f"{x['name']}"))
            rows.append((T("size"), f"{x['size'] / 1e9:.0f} GB  ·  {x['bus'] or '-'} {x['media'] or ''}".rstrip()))
        if key == "nvme" and live.get("c_total"):
            rows.append((T("c_drive"), T("free").format(f=_gb(live["c_free"]), t=_gb(live["c_total"]))))
        if not want:
            rows.append(("", T("no_data")))
    elif key == "mobo":
        mb = hw.get("motherboard") or {}
        nm = " ".join(x for x in (mb.get("manufacturer"), mb.get("product")) if x)
        rows.append(("", nm or T("unknown")))
        if mb.get("version"):
            rows.append(("", mb["version"]))
    elif key == "battery":
        rows.append((T("battery_lv"), _num(live.get("battery"), " %")))
        if live.get("plugged") is not None:
            rows.append(("", T("plugged") if live["plugged"] else T("on_batt")))
    elif key == "screen":
        try:
            import ctypes
            u = ctypes.windll.user32
            rows.append(("", f"{u.GetSystemMetrics(0)} × {u.GetSystemMetrics(1)}"))
        except Exception:
            pass
    return name[lang], rows, note


# ── the view ─────────────────────────────────────────────────────────────
class _Shared:
    """Plain data between the worker and the window (no Tk objects)."""
    def __init__(self):
        self.live: Dict = {}
        self.week: Dict = {}
        self.hw: Dict = {}
        self.version = 0
        self.want = True          # the tab is on screen
        self.alive = True


def _worker(sh: _Shared):
    week_at = 0.0
    if not sh.hw:
        sh.hw = gather_hw()
        sh.version += 1
    while sh.alive:
        if sh.want:
            sh.live = gather_live()
            if time.time() - week_at > 300:
                sh.week = gather_week()
                week_at = time.time()
            sh.version += 1
        for _ in range(30):
            if not sh.alive:
                return
            time.sleep(0.1)


class PCMapView(tk.Frame):

    def __init__(self, parent, app=None, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.app = app
        self.sh = _Shared()
        self._seen = -1
        self._mode = None             # desktop | laptop, from the machine once known
        self._colors = "now"
        self._hover = None
        self._photo = None
        self._parts: List = []
        self._fit = None
        self._job = None
        self._lang = _lang()
        if not _HAS_PIL:
            tk.Label(self, text="Pillow", font=(_BODY, 11), bg=BG, fg="#ef4444").pack(expand=True)
            return
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._build()
        threading.Thread(target=_worker, args=(self.sh,), daemon=True, name="pc-map").start()
        self._tick()

    # ── layout ───────────────────────────────────────────────────────────
    def _build(self):
        bar = tk.Frame(self, bg=BAR, height=36)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        self._b_mode = {m: self._btn(bar, _tx(m), lambda m=m: self._set_mode(m)) for m in ("desktop", "laptop")}
        tk.Frame(bar, bg=LINE, width=1).pack(side="left", fill="y", pady=7, padx=8)
        tk.Label(bar, text=_tx("colors"), font=(_BODY, 8), bg=BAR, fg=MUTED).pack(side="left")
        self._b_col = {m: self._btn(bar, _tx(m), lambda m=m: self._set_colors(m)) for m in ("now", "week")}
        leg = tk.Frame(bar, bg=BAR)
        leg.pack(side="right", padx=12)
        tk.Label(leg, text=_tx("cool"), font=(_BODY, 7), bg=BAR, fg=MUTED).pack(side="left")
        g = tk.Canvas(leg, width=90, height=8, bg=BAR, highlightthickness=0)
        g.pack(side="left", padx=6)
        for i in range(90):
            g.create_line(i, 0, i, 8, fill="#%02x%02x%02x" % S.heat_color(i / 89))
        tk.Label(leg, text=_tx("hot"), font=(_BODY, 7), bg=BAR, fg=MUTED).pack(side="left")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        right = tk.Frame(body, bg=BG, width=RIGHT_W)
        right.pack(side="right", fill="y", padx=(0, 12), pady=10)
        right.pack_propagate(False)
        self.cv = tk.Canvas(body, bg="#%02x%02x%02x" % CANVAS_BG, highlightthickness=0, cursor="crosshair")
        self.cv.pack(side="left", fill="both", expand=True, padx=(12, 10), pady=10)
        self.cv.bind("<Configure>", lambda e=None: self._schedule())
        self.cv.bind("<Motion>", self._on_motion)
        self.cv.bind("<Leave>", self._on_leave)
        self.cv.bind("<Button-1>", self._on_click)

        self.c_pc = self._card(right, _tx("this_pc"))
        self.c_th = self._card(right, _tx("thermal"))
        self.under = tk.Frame(self.cv, bg=PANEL, highlightthickness=1, highlightbackground="#3b4a63")
        tk.Label(self.under, text=_tx("under"), font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED,
                 anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        self.c_under = tk.Frame(self.under, bg=PANEL)
        self.c_under.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self._fill_under(None)
        self._fill_pc()
        self._fill_thermal()
        self._paint_buttons()

    def _btn(self, parent, text, cmd):
        b = tk.Label(parent, text=text, font=(_BODY, 8, "bold"), bg=BAR, fg=MUTED, padx=10, pady=3,
                     cursor="hand2")
        b.pack(side="left", padx=(4, 0), pady=6)
        b.bind("<Button-1>", lambda e=None: cmd())
        return b

    def _paint_buttons(self):
        for m, b in self._b_mode.items():
            b.config(bg=BLUE if m == (self._mode or "desktop") else BAR,
                     fg="#ffffff" if m == (self._mode or "desktop") else MUTED)
        for m, b in self._b_col.items():
            b.config(bg="#6d28d9" if m == self._colors else BAR,
                     fg="#ffffff" if m == self._colors else MUTED)

    def _card(self, parent, title, expand=False):
        f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        f.pack(fill="both" if expand else "x", expand=expand, pady=(0, 8))
        tk.Label(f, text=title, font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED, anchor="w").pack(
            fill="x", padx=12, pady=(8, 2))
        inner = tk.Frame(f, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        return inner

    def _rows(self, parent, rows, wrap=RIGHT_W - 40):
        for cap, val in rows:
            r = tk.Frame(parent, bg=PANEL)
            r.pack(fill="x", pady=1)
            if cap:
                tk.Label(r, text=cap, font=(_BODY, 8), bg=PANEL, fg=MUTED, width=13, anchor="w").pack(side="left")
                tk.Label(r, text=val, font=(_BODY, 8, "bold"), bg=PANEL, fg=TEXT, anchor="w", justify="left",
                         wraplength=wrap - 100).pack(side="left", fill="x", expand=True)
            else:
                tk.Label(r, text=val, font=(_BODY, 9, "bold"), bg=PANEL, fg=TEXT, anchor="w", justify="left",
                         wraplength=wrap).pack(fill="x")

    # ── panels ───────────────────────────────────────────────────────────
    def _clear(self, f):
        for w in f.winfo_children():
            w.destroy()

    def _fill_pc(self):
        self._clear(self.c_pc)
        hw, lang = self.sh.hw, self._lang
        if not hw:
            self._rows(self.c_pc, [("", _tx("loading"))])
            return
        kind = hw.get("kind")
        mods = (hw.get("ram") or {}).get("modules") or []
        total = sum(m.get("capacity_gb") or 0 for m in mods)
        mb = hw.get("motherboard") or {}
        disks = hw.get("disks") or []
        rows = [(_tx("kind"), _tx("kind_laptop" if kind == "laptop" else "kind_desktop") if kind else _tx("unknown")),
                ("CPU", (hw.get("cpu") or {}).get("name") or "-"),
                ("GPU", (hw.get("gpu") or {}).get("name") or "-"),
                ("RAM", f"{total:g} GB ({len(mods)} × {mods[0].get('capacity_gb') or '?'} GB)" if mods else "-"),
                (_tx("board"), " ".join(x for x in (mb.get("manufacturer"), mb.get("product")) if x) or "-"),
                (_tx("drives"), ", ".join(f"{d['bus'] or '?'} {d['size'] / 1e9:.0f} GB" for d in disks) or "-")]
        self._rows(self.c_pc, rows)

    def _fill_thermal(self):
        self._clear(self.c_th)
        lv, wk = self.sh.live, self.sh.week
        head = tk.Frame(self.c_th, bg=PANEL)
        head.pack(fill="x")
        for i, t in enumerate(("", _tx("col_now"), _tx("col_avg"), _tx("col_max"))):
            tk.Label(head, text=t, font=(_BODY, 7), bg=PANEL, fg=DIM, width=10 if i == 0 else 9,
                     anchor="w").pack(side="left")

        # one unit per row: a temperature next to a load read as one number
        def line(name, now, comp, temp):
            w = wk.get(comp) or {}
            r = tk.Frame(self.c_th, bg=PANEL)
            r.pack(fill="x", pady=1)
            unit = "°C" if temp else "%"
            vals = [name, _num(now, unit),
                    _num(w.get("temp_avg" if temp else "avg"), unit),
                    _num(w.get("temp_max" if temp else "max"), unit)]
            for i, v in enumerate(vals):
                tk.Label(r, text=v, font=(_BODY, 8, "bold" if i else "normal"), bg=PANEL,
                         fg=(TEXT if v != "-" else DIM) if i else MUTED,
                         width=10 if i == 0 else 9, anchor="w").pack(side="left")
        line("CPU °C", lv.get("cpu_temp"), "cpu", True)
        line("GPU °C", lv.get("gpu_temp"), "gpu", True)
        line("CPU %", lv.get("cpu_pct"), "cpu", False)
        line("GPU %", lv.get("gpu_pct"), "gpu", False)
        line("RAM %", lv.get("ram_pct"), "ram", False)
        if lv and not lv.get("cpu_temp"):
            tk.Label(self.c_th, text=_tx("no_cpu_sensor"), font=(_BODY, 7), bg=PANEL, fg=DIM, anchor="w",
                     justify="left", wraplength=RIGHT_W - 40).pack(fill="x", pady=(4, 0))

    def _fill_under(self, key):
        """The card under the cursor sits on the map's empty top-left corner:
        the right column has no room left for it at 645 px."""
        self._clear(self.c_under)
        if not key:
            self.under.place_forget()
            return
        # on the side of the map away from the part, so it never covers it
        x = 12
        try:
            pt = S.label_points(self._parts, self._fit).get(key)
            if pt is None:
                pt = next((S.to_screen([S.top_center(p)], self._fit)[0]
                           for p in self._parts if p.key == key), None)
            cw = self.cv.winfo_width()
            if pt is not None and pt[0] < cw / 2:
                x = cw - (RIGHT_W - 20) - 12
        except Exception:
            pass
        self.under.place(x=x, y=12, width=RIGHT_W - 20)
        title, rows, note = details(key, self.sh.live, self.sh.week, self.sh.hw, self._lang)
        tk.Label(self.c_under, text=title, font=(_HDR, 11, "bold"), bg=PANEL, fg=TEXT, anchor="w").pack(fill="x")
        self._rows(self.c_under, rows)
        if note:
            tk.Label(self.c_under, text=note, font=(_BODY, 7), bg=PANEL, fg=MUTED, anchor="w",
                     justify="left", wraplength=RIGHT_W - 40).pack(fill="x", pady=(6, 0))

    # ── drawing ──────────────────────────────────────────────────────────
    def _scene(self):
        a = layout_args(self.sh.hw) if self.sh.hw else {"ram_sticks": 2, "has_gpu": True, "nvme": True, "sata": 0}
        if (self._mode or "desktop") == "laptop":
            return S.laptop(a["has_gpu"])
        return S.desktop(a["ram_sticks"], a["has_gpu"], a["nvme"], a["sata"])

    def _schedule(self, delay=60):
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self._job = self.after(delay, self._render)

    def _render(self):
        self._job = None
        try:
            w, h = self.cv.winfo_width(), self.cv.winfo_height()
            if w < 50 or h < 50:
                return
            self._parts = self._scene()
            heat = heat_values(self.sh.live, self.sh.week, self._colors)
            img, self._fit = S.render(self._parts, w, h, heat, self._hover, bg=CANVAS_BG)
            self._photo = ImageTk.PhotoImage(img)
            self.cv.delete("all")
            self.cv.create_image(0, 0, anchor="nw", image=self._photo)
            self._labels()
            if not self._hover:
                self.cv.create_text(14, h - 12, text=_tx("hint"), anchor="sw", font=(_BODY, 8),
                                    fill=DIM)
        except Exception as e:
            print(f"[PCMap] render: {e}")

    def _label_text(self, key):
        lv = self.sh.live
        base = _LABEL.get(key, key)
        if isinstance(base, dict):
            base = base[self._lang]
        if self._colors == "week" and key in ("cpu", "gpu", "ram"):
            # the labels say what the colours say: the 7-day average
            w = self.sh.week.get(key) or {}
            v = _num(w.get("temp_avg"), "°C") if w.get("temp_avg") else _num(w.get("avg"), "%")
            return f"{base}  Ø {v}" if v != "-" else base
        if key == "cpu":
            v = _num(lv.get("cpu_temp"), "°C") if lv.get("cpu_temp") else _num(lv.get("cpu_pct"), "%")
        elif key == "gpu":
            v = _num(lv.get("gpu_temp"), "°C") if lv.get("gpu_temp") else _num(lv.get("gpu_pct"), "%")
        elif key == "ram":
            v = _num(lv.get("ram_pct"), "%")
        elif key == "battery":
            v = _num(lv.get("battery"), "%")
        else:
            v = ""
        return f"{base}  {v}" if v and v != "-" else base

    def _labels(self):
        placed = []
        for key, (x, y) in S.label_points(self._parts, self._fit).items():
            t = self.cv.create_text(0, 0, text=self._label_text(key), font=(_BODY, 8, "bold"),
                                    fill="#ffffff", anchor="s")
            bb = self.cv.bbox(t)
            tw, th = bb[2] - bb[0] + 12, bb[3] - bb[1] + 4
            ly = y - 18
            for _ in range(6):
                rect = (x - tw / 2, ly - th, x + tw / 2, ly)
                if not any(rect[0] < r[2] and r[0] < rect[2] and rect[1] < r[3] and r[1] < rect[3] for r in placed):
                    break
                ly -= th + 3
            placed.append(rect)
            self.cv.create_line(x, y, x, ly, fill="#cbd5e1", width=1)
            self.cv.create_oval(x - 2.5, y - 2.5, x + 2.5, y + 2.5, fill="#ffffff", outline="")
            box = self.cv.create_rectangle(*rect, fill="#111827", outline="#475569")
            self.cv.coords(t, x, ly - 2)
            self.cv.tag_raise(t, box)

    # ── events ───────────────────────────────────────────────────────────
    def _on_motion(self, e=None):
        if e is None or not self._fit:
            return
        self._set_hover(S.hit(self._parts, self._fit, e.x, e.y))

    def _on_leave(self, e=None):
        # the card on the map is a child of the canvas: entering it is a
        # <Leave> too, and must not hide it
        try:
            px, py = self.cv.winfo_pointerxy()
            x0, y0 = self.cv.winfo_rootx(), self.cv.winfo_rooty()
            if x0 <= px < x0 + self.cv.winfo_width() and y0 <= py < y0 + self.cv.winfo_height():
                return
        except Exception:
            pass
        self._set_hover(None)

    def _set_hover(self, key):
        if key == self._hover:
            return
        self._hover = key
        self.cv.config(cursor="hand2" if key in ("cpu", "gpu", "ram") else "crosshair")
        self._fill_under(key)
        self._schedule(10)

    def _on_click(self, e=None):
        if self._hover in ("cpu", "gpu", "ram") and self.app is not None:
            try:
                self.app.open_activity_memory(self._hover)
            except Exception:
                pass

    def _set_mode(self, m):
        self._mode = m
        self._paint_buttons()
        self._set_hover(None)
        self._schedule(10)

    def _set_colors(self, m):
        self._colors = m
        self._paint_buttons()
        self._schedule(10)

    def _tick(self):
        """Every half second: is the tab on screen, did the data change."""
        try:
            if not self.winfo_exists():
                return
            shown = bool(self.winfo_ismapped())
            self.sh.want = shown
            if shown and self.sh.version != self._seen:
                first_hw = self._mode is None and bool(self.sh.hw)
                self._seen = self.sh.version
                if first_hw:
                    self._mode = "laptop" if self.sh.hw.get("kind") == "laptop" else "desktop"
                    self._paint_buttons()
                    self._fill_pc()
                self._fill_thermal()
                if self._hover:
                    self._fill_under(self._hover)
                self._schedule(10)
            self.after(500, self._tick)
        except Exception:
            pass

    def _on_destroy(self, e=None):
        if e is None or e.widget is self:
            self.sh.alive = False


def create_pc_map_page(parent, app=None) -> PCMapView:
    view = PCMapView(parent, app=app)
    view.pack(fill="both", expand=True)
    return view
