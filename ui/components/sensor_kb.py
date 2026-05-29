# ═══════════════════════════════════════════════════════════════════════════════
# Hey USER - Live Sensor Panel  (knowledge base + refresh engine)
# Color key:  light-blue = cold/low · white = normal · amber = warm · red = crit
# ═══════════════════════════════════════════════════════════════════════════════

# ── Font system ───────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# ── CPU profiles ──────────────────────────────────────────────────────────────
#   tdp   = base TDP (W)   pl2 = sustained / boost power limit (W)
#   tj    = Tj Max (°C)    base/boost = clock speed (MHz)
_CPU_KB = {
    # Intel Alder Lake 12th gen
    "i5-12400F": {"tdp": 65,  "pl2": 117, "tj": 100, "base": 2500, "boost": 4400, "cores": 6},
    "i5-12400":  {"tdp": 65,  "pl2": 117, "tj": 100, "base": 2500, "boost": 4400, "cores": 6},
    "i5-12600K": {"tdp": 125, "pl2": 150, "tj": 100, "base": 3700, "boost": 4900, "cores": 10},
    "i7-12700K": {"tdp": 125, "pl2": 190, "tj": 100, "base": 3600, "boost": 5000, "cores": 12},
    "i9-12900K": {"tdp": 125, "pl2": 241, "tj": 100, "base": 3200, "boost": 5200, "cores": 16},
    # Intel Raptor Lake 13th gen
    "i5-13600K": {"tdp": 125, "pl2": 181, "tj": 100, "base": 3500, "boost": 5100, "cores": 14},
    "i7-13700K": {"tdp": 125, "pl2": 253, "tj": 100, "base": 3400, "boost": 5400, "cores": 16},
    "i9-13900K": {"tdp": 125, "pl2": 253, "tj": 100, "base": 3000, "boost": 5800, "cores": 24},
    "i9-13900KS":{"tdp": 150, "pl2": 253, "tj": 100, "base": 3200, "boost": 6000, "cores": 24},
    # Intel Raptor Lake Refresh 14th gen
    "i5-14600K": {"tdp": 125, "pl2": 181, "tj": 100, "base": 3500, "boost": 5300, "cores": 14},
    "i7-14700K": {"tdp": 125, "pl2": 253, "tj": 100, "base": 3400, "boost": 5600, "cores": 20},
    "i9-14900K": {"tdp": 125, "pl2": 253, "tj": 100, "base": 3200, "boost": 6000, "cores": 24},
    "i9-14900KS":{"tdp": 150, "pl2": 253, "tj": 100, "base": 3200, "boost": 6200, "cores": 24},
    # AMD Ryzen 5000 (Zen 3)
    "5600X":     {"tdp": 65,  "pl2": 88,  "tj": 90,  "base": 3700, "boost": 4600, "cores": 6},
    "5600G":     {"tdp": 65,  "pl2": 88,  "tj": 90,  "base": 3900, "boost": 4400, "cores": 6},
    "5700X":     {"tdp": 65,  "pl2": 88,  "tj": 90,  "base": 3400, "boost": 4600, "cores": 8},
    "5800X":     {"tdp": 105, "pl2": 142, "tj": 90,  "base": 3800, "boost": 4700, "cores": 8},
    "5800X3D":   {"tdp": 105, "pl2": 142, "tj": 89,  "base": 3400, "boost": 4500, "cores": 8},
    "5900X":     {"tdp": 105, "pl2": 142, "tj": 90,  "base": 3700, "boost": 4800, "cores": 12},
    "5950X":     {"tdp": 105, "pl2": 142, "tj": 90,  "base": 3400, "boost": 4900, "cores": 16},
    # AMD Ryzen 7000 (Zen 4)
    "7600X":     {"tdp": 105, "pl2": 142, "tj": 95,  "base": 4700, "boost": 5300, "cores": 6},
    "7700X":     {"tdp": 105, "pl2": 142, "tj": 95,  "base": 4500, "boost": 5400, "cores": 8},
    "7900X":     {"tdp": 170, "pl2": 230, "tj": 95,  "base": 4700, "boost": 5600, "cores": 12},
    "7950X":     {"tdp": 170, "pl2": 230, "tj": 95,  "base": 4500, "boost": 5700, "cores": 16},
    "7950X3D":   {"tdp": 120, "pl2": 162, "tj": 89,  "base": 4200, "boost": 5700, "cores": 16},
    # Fallbacks
    "_intel":    {"tdp": 65,  "pl2": 117, "tj": 100, "base": 2500, "boost": 5000, "cores": 6},
    "_amd":      {"tdp": 65,  "pl2": 88,  "tj": 90,  "base": 3500, "boost": 4600, "cores": 6},
    "_default":  {"tdp": 65,  "pl2": 125, "tj": 100, "base": 2000, "boost": 4500, "cores": 4},
}

# ── GPU profiles ──────────────────────────────────────────────────────────────
#   tj  = core Tj Max (°C)   hotspot = junction limit (°C)
#   tdp = board power limit   idle_t / ok_t = reference temps
_GPU_KB = {
    # NVIDIA RTX 40-series
    "RTX 4090":    {"tj": 83, "hotspot": 110, "tdp": 450, "idle_t": 32, "ok_t": 78},
    "RTX 4080 S":  {"tj": 83, "hotspot": 110, "tdp": 320, "idle_t": 33, "ok_t": 78},
    "RTX 4080":    {"tj": 83, "hotspot": 110, "tdp": 320, "idle_t": 33, "ok_t": 78},
    "RTX 4070 Ti": {"tj": 83, "hotspot": 110, "tdp": 285, "idle_t": 35, "ok_t": 78},
    "RTX 4070 S":  {"tj": 83, "hotspot": 110, "tdp": 220, "idle_t": 35, "ok_t": 78},
    "RTX 4070":    {"tj": 83, "hotspot": 110, "tdp": 200, "idle_t": 38, "ok_t": 80},
    "RTX 4060 Ti": {"tj": 83, "hotspot": 110, "tdp": 165, "idle_t": 38, "ok_t": 80},
    "RTX 4060":    {"tj": 83, "hotspot": 110, "tdp": 115, "idle_t": 40, "ok_t": 80},
    # NVIDIA RTX 30-series
    "RTX 3090 Ti": {"tj": 83, "hotspot": 110, "tdp": 450, "idle_t": 33, "ok_t": 78},
    "RTX 3090":    {"tj": 83, "hotspot": 110, "tdp": 350, "idle_t": 33, "ok_t": 78},
    "RTX 3080 Ti": {"tj": 83, "hotspot": 110, "tdp": 350, "idle_t": 35, "ok_t": 80},
    "RTX 3080":    {"tj": 83, "hotspot": 110, "tdp": 320, "idle_t": 35, "ok_t": 80},
    "RTX 3070 Ti": {"tj": 83, "hotspot": 110, "tdp": 290, "idle_t": 38, "ok_t": 80},
    "RTX 3070":    {"tj": 83, "hotspot": 110, "tdp": 220, "idle_t": 38, "ok_t": 80},
    "RTX 3060 Ti": {"tj": 83, "hotspot": 110, "tdp": 200, "idle_t": 40, "ok_t": 82},
    "RTX 3060":    {"tj": 83, "hotspot": 110, "tdp": 170, "idle_t": 40, "ok_t": 82},
    "RTX 3050":    {"tj": 83, "hotspot": 110, "tdp": 130, "idle_t": 42, "ok_t": 83},
    # AMD RX 7000-series
    "RX 7900 XTX": {"tj": 110, "hotspot": 110, "tdp": 355, "idle_t": 38, "ok_t": 85},
    "RX 7900 XT":  {"tj": 110, "hotspot": 110, "tdp": 315, "idle_t": 38, "ok_t": 85},
    "RX 7800 XT":  {"tj": 110, "hotspot": 110, "tdp": 263, "idle_t": 40, "ok_t": 85},
    "RX 7700 XT":  {"tj": 110, "hotspot": 110, "tdp": 245, "idle_t": 40, "ok_t": 85},
    "RX 7600":     {"tj": 110, "hotspot": 110, "tdp": 165, "idle_t": 40, "ok_t": 82},
    # AMD RX 6000-series
    "RX 6950 XT":  {"tj": 110, "hotspot": 110, "tdp": 335, "idle_t": 40, "ok_t": 85},
    "RX 6900 XT":  {"tj": 110, "hotspot": 110, "tdp": 300, "idle_t": 40, "ok_t": 85},
    "RX 6800 XT":  {"tj": 110, "hotspot": 110, "tdp": 300, "idle_t": 40, "ok_t": 85},
    "RX 6800":     {"tj": 110, "hotspot": 110, "tdp": 250, "idle_t": 40, "ok_t": 82},
    "RX 6700 XT":  {"tj": 110, "hotspot": 110, "tdp": 230, "idle_t": 40, "ok_t": 82},
    "RX 6650 XT":  {"tj": 110, "hotspot": 110, "tdp": 180, "idle_t": 40, "ok_t": 82},
    "RX 6600 XT":  {"tj": 110, "hotspot": 110, "tdp": 160, "idle_t": 40, "ok_t": 82},
    # Fallback
    "_default":    {"tj": 90,  "hotspot": 110, "tdp": 200, "idle_t": 40, "ok_t": 83},
}

# ── ATX voltage spec tolerances (±5% hard, ±3% warning) ──────────────────────
_VOLT_SPEC = {
    "+12V":  {"nom": 12.0, "lo": 11.40, "hi": 12.60, "lo_w": 11.60, "hi_w": 12.40},
    "+5V":   {"nom": 5.0,  "lo": 4.750, "hi": 5.250, "lo_w": 4.850, "hi_w": 5.150},
    "+3.3V": {"nom": 3.3,  "lo": 3.135, "hi": 3.465, "lo_w": 3.200, "hi_w": 3.400},
    "DDR4":  {"nom": 1.2,  "lo": 1.100, "hi": 1.500, "lo_w": 1.150, "hi_w": 1.350},
    "DDR5":  {"nom": 1.1,  "lo": 1.000, "hi": 1.400, "lo_w": 1.050, "hi_w": 1.250},
}

# ── Session min/max tracker (persists for app lifetime) ───────────────────────
_SESSION_HIST: dict = {}  # "key" -> [min_float, max_float]

def _track_sensor(key: str, val: float):
    """Update session history. Returns (min, max)."""
    if key not in _SESSION_HIST:
        _SESSION_HIST[key] = [val, val]
    else:
        if val < _SESSION_HIST[key][0]:
            _SESSION_HIST[key][0] = val
        if val > _SESSION_HIST[key][1]:
            _SESSION_HIST[key][1] = val
    return _SESSION_HIST[key][0], _SESSION_HIST[key][1]

# ── Profile matchers ──────────────────────────────────────────────────────────
def _match_cpu(name: str) -> dict:
    n = name.upper()
    for k, v in _CPU_KB.items():
        if k.startswith("_"):
            continue
        if k.upper() in n:
            return v
    if "AMD" in n or "RYZEN" in n:
        return _CPU_KB["_amd"]
    if "INTEL" in n or "CORE" in n:
        return _CPU_KB["_intel"]
    return _CPU_KB["_default"]

def _match_gpu(name: str) -> dict:
    n = name.upper()
    for k, v in _GPU_KB.items():
        if k.startswith("_"):
            continue
        if k.upper() in n:
            return v
    return _GPU_KB["_default"]

# ── Colour constants ──────────────────────────────────────────────────────────
_CN  = "#e2e8f0"   # normal / white
_CLB = "#7dd3fc"   # light-blue - cold or below nominal
_CWN = "#fbbf24"   # amber      - warning
_CCR = "#ef4444"   # red        - critical
_CNA = "#475569"   # slate-gray - no data
_COK = "#10b981"   # green      - OK badge
_CYL = "#f59e0b"   # yellow     - WARN badge
_CBL = "#38bdf8"   # sky-blue   - COLD/LOW badge

# ── Colour logic ──────────────────────────────────────────────────────────────
def _ct(temp: float, tj: int) -> str:
    """Color for temperature vs Tj_Max."""
    if temp <= 0:          return _CNA
    if temp < 30:          return _CLB
    if temp < tj * 0.70:   return _CN
    if temp < tj * 0.85:   return _CWN
    return _CCR

def _cp(pct: float) -> str:
    """Color for percentage (load, disk %)."""
    if pct < 0:    return _CNA
    if pct < 60:   return _CN
    if pct < 85:   return _CWN
    return _CCR

def _cw(w: float, tdp: float) -> str:
    """Color for wattage vs TDP."""
    if w <= 0:              return _CNA
    if w < tdp * 0.85:     return _CN
    if w < tdp:            return _CWN
    return _CCR

def _badge_t(temp: float, tj: int) -> tuple:
    if temp <= 0:              return "N/A",     _CNA
    if temp >= tj * 0.85:      return "CRIT",    _CCR
    if temp >= tj * 0.70:      return "WARM",    _CYL
    if temp < 30:              return "COLD?",   _CBL
    return "OK", _COK

def _badge_p(pct: float) -> tuple:
    if pct < 0:    return "N/A",    _CNA
    if pct >= 85:  return "HIGH",   _CCR
    if pct >= 60:  return "BUSY",   _CYL
    return "OK", _COK

def _badge_w(w: float, tdp: float) -> tuple:
    if w <= 0:             return "N/A",  _CNA
    if w >= tdp:           return "MAX",  _CCR
    if w >= tdp * 0.85:    return "HIGH", _CYL
    return "OK", _COK

# ── nvidia-smi cache (updated every 1.5 s at most) ───────────────────────────
_GPU_SMI: dict = {}
_GPU_SMI_TS: float = 0.0

def _fetch_gpu_smi() -> dict:
    global _GPU_SMI, _GPU_SMI_TS
    import time as _t, subprocess as _sp
    if _t.time() - _GPU_SMI_TS < 1.5:
        return _GPU_SMI
    _GPU_SMI_TS = _t.time()
    try:
        r = _sp.run(
            ["nvidia-smi",
             "--query-gpu=temperature.gpu,power.draw,clocks.gr,clocks.mem,"
             "utilization.gpu,memory.used,memory.total,name",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
            creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0),
        )
        if r.returncode == 0:
            p = [x.strip() for x in r.stdout.strip().split(",")]
            _GPU_SMI = {
                "temp":      float(p[0]),
                "power":     float(p[1]),
                "clk_gr":    int(p[2]),
                "clk_mem":   int(p[3]),
                "usage":     float(p[4]),
                "mem_used":  int(p[5]),
                "mem_total": int(p[6]),
                "name":      p[7] if len(p) > 7 else "NVIDIA GPU",
                "ok":        True,
            }
    except Exception:
        _GPU_SMI.setdefault("ok", False)
    return _GPU_SMI

# ── LibreHardwareMonitor / OpenHardwareMonitor sensor probe ──────────────────
# Reads from the local HTTP/JSON server exposed by LHM (port 8086) or OHM (8085).
# Returns dict with voltage + temperature keys, or empty dict on failure.
_MB_CACHE: dict = {}
_MB_CACHE_TS: float = 0.0

def _fetch_mb_sensors() -> dict:
    """
    Probe OHM (port 8085) then LHM (port 8086) for motherboard sensor data.
    Returns keys: volt_12v, volt_5v, volt_33v, temp_sys, temp_vrm, source
    All floats, -1.0 if not found.
    """
    global _MB_CACHE, _MB_CACHE_TS
    import time as _t
    if _t.time() - _MB_CACHE_TS < 4.0:   # refresh every 4 s (slower than CPU)
        return _MB_CACHE
    _MB_CACHE_TS = _t.time()

    result = {"volt_12v": -1.0, "volt_5v": -1.0, "volt_33v": -1.0,
              "temp_sys": -1.0, "temp_vrm": -1.0, "source": ""}

    def _walk(node: dict, acc: dict):
        """Recursively walk OHM/LHM JSON node, collect named sensors."""
        text  = node.get("Text", "")
        value = node.get("Value", "")
        # Parse numeric value  e.g. "45.0 °C" or "11.9 V"
        try:
            num = float(value.split()[0])
        except Exception:
            num = None

        if num is not None:
            tl = text.lower()
            if "+12" in tl:
                acc["volt_12v"] = num
            elif "+5" in tl and "12" not in tl:
                acc["volt_5v"] = num
            elif "+3.3" in tl or "3.3v" in tl:
                acc["volt_33v"] = num
            elif "vrm" in tl and "temp" not in tl:
                acc["temp_vrm"] = num
            elif ("motherboard" in tl or "system" in tl or "systin" in tl
                  or "temp1" in tl):
                acc["temp_sys"] = num

        for child in node.get("Children", []):
            _walk(child, acc)

    try:
        import urllib.request, json
        for port, src in [(8085, "ohm"), (8086, "lhm")]:
            try:
                with urllib.request.urlopen(
                        f"http://localhost:{port}/data.json", timeout=0.8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                acc: dict = {}
                _walk(data, acc)
                if any(v > 0 for v in acc.values() if isinstance(v, float)):
                    result.update(acc)
                    result["source"] = src
                    break
            except Exception:
                continue
    except Exception:
        pass

    _MB_CACHE = result
    return result


def _build_hey_user_table(self, parent):
    """
    Live Hey-USER sensor panel.
    Sections: MB Voltage/Temp · CPU (live) · GPU (live) · Disk (live)
    Auto-refreshes every 2 s.  Session min/max tracked per key.
    Writes collected data to hck_gpt.data.live_sensors on every cycle.
    """
    import socket
    import subprocess as _sp

    BG  = "#0a0e27"
    BG2 = "#0f1420"
    DIV = "#1e2538"

    # Live sensor bridge (optional - graceful if import fails)
    try:
        from hck_gpt.data import live_sensors as _ls
        _HAS_LS = True
    except Exception:
        _ls = None
        _HAS_LS = False

    # ── Detect CPU name + profile ─────────────────────────────────────────────
    try:
        _r = _sp.run(["wmic", "cpu", "get", "name"],
                     capture_output=True, text=True, timeout=3,
                     creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        _cpu_name = _r.stdout.strip().splitlines()[-1].strip() if _r.stdout else "Unknown CPU"
    except Exception:
        import platform
        _cpu_name = platform.processor() or "Unknown CPU"

    _cpu_prof = _match_cpu(_cpu_name)

    # ── Detect GPU name + profile ─────────────────────────────────────────────
    _gpu_smi  = _fetch_gpu_smi()
    _gpu_name = _gpu_smi.get("name", "")
    _gpu_prof = _match_gpu(_gpu_name) if _gpu_name else _GPU_KB["_default"]

    # ── Scrollable container ──────────────────────────────────────────────────
    canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                      bg="#000", troughcolor=BG, activebackground="#1a1d24", width=8)
    body = tk.Frame(canvas, bg=BG)

    body.bind("<Configure>",
              lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=body, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)

    def _wheel(e):
        try:
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception:
            pass
    canvas.bind_all("<MouseWheel>", _wheel, add="+")

    # "Show Full Table" button
    btn_f = tk.Frame(parent, bg=BG)
    btn_f.pack(side="bottom", fill="x", padx=5, pady=5)
    more = tk.Label(btn_f, text="Show Full Table",
                    font=(_BODY, 8, "bold"),
                    bg="#374151", fg="#ffffff", pady=6, cursor="hand2")
    more.pack(fill="x")
    more.bind("<Enter>",    lambda e: more.config(bg="#4b5563"))
    more.bind("<Leave>",    lambda e: more.config(bg="#374151"))
    more.bind("<Button-1>", lambda e: _show_full_table_popup(self, parent))

    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    # ── Header ────────────────────────────────────────────────────────────────
    header_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "icons", "info_header.png")
    try:
        computer_name = socket.gethostname()
    except Exception:
        computer_name = "DESKTOP"

    try:
        from PIL import Image, ImageTk
        if not os.path.exists(header_path):
            raise FileNotFoundError
        img = Image.open(header_path).resize((800, 24), Image.Resampling.LANCZOS)
        hdr_cv = tk.Canvas(body, bg=BG, height=24, highlightthickness=0)
        hdr_cv.pack(fill="x", pady=(0, 1))
        photo = ImageTk.PhotoImage(img)
        hdr_cv.create_image(0, 0, image=photo, anchor="nw")
        hdr_cv.image = photo
        hdr_cv.create_text(175, 12, text="Hey - USER",
                           font=(_BODY, 9, "bold"), fill="#ffffff", anchor="center")
        hdr_cv.create_text(525, 12, text=computer_name,
                           font=(_BODY, 9, "bold"), fill="#ffffff", anchor="center")
    except Exception:
        hdr = tk.Frame(body, bg="#1e3a5f")
        hdr.pack(fill="x")
        tk.Label(hdr, text="Hey - USER",
                 font=("Segoe UI Semibold", 10),
                 bg="#1e3a5f", fg="#ffffff", pady=6).pack(side="left", padx=10)
        tk.Label(hdr, text=computer_name,
                 font=("Segoe UI Semibold", 10),
                 bg="#1e3a5f", fg="#ffffff", pady=6).pack(side="right", padx=10)

    # ─────────────────────────────────────────────────────────────────────────
    # Inner helper: build one live mini-table
    # row_specs: list of (key, label_text)
    # Returns:   (badge_lbl, [(key, cur_lbl, min_lbl, max_lbl), ...])
    # ─────────────────────────────────────────────────────────────────────────
    def _live_table(parent_frame, title, row_specs):
        # Dark steel title bar instead of amber
        title_bar = tk.Frame(parent_frame, bg="#1c2238", height=13)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text=title,
                 font=("Segoe UI Semibold", 6),
                 bg="#1c2238", fg="#b8b0bc").pack(side="left", padx=5)
        bdg = tk.Label(title_bar, text="OK",
                       font=(_BODY, 6, "bold"),
                       bg=_COK, fg="#ffffff", padx=10, pady=1)
        bdg.pack(side="right", padx=2)

        hdr = tk.Frame(parent_frame, bg="#080b18")
        hdr.pack(fill="x")
        tk.Label(hdr, text="", width=10, bg="#080b18",
                 font=(_BODY, 5)).pack(side="left")
        for col in ["CURRENT", "MIN", "MAX"]:
            tk.Label(hdr, text=col, width=7, bg="#080b18",
                     fg="#3d4e6b", font=(_BODY, 5, "bold")).pack(side="left", padx=1)

        container = tk.Frame(parent_frame, bg="#0f1117")
        container.pack(fill="x")

        cells = []
        for key, lbl_txt in row_specs:
            row = tk.Frame(container, bg="#0f1117")
            row.pack(fill="x")
            tk.Label(row, text=lbl_txt,
                     font=(_BODY, 6), bg="#0f1117", fg="#6a7a94",
                     anchor="w", width=10).pack(side="left", padx=1)
            cur_l = tk.Label(row, text="--", font=(_BODY, 6, "bold"),
                             bg="#080b18", fg=_CNA, width=7)
            cur_l.pack(side="left", padx=1)
            min_l = tk.Label(row, text="--", font=(_BODY, 6, "bold"),
                             bg="#080b18", fg=_CNA, width=7)
            min_l.pack(side="left", padx=1)
            max_l = tk.Label(row, text="--", font=(_BODY, 6, "bold"),
                             bg="#080b18", fg=_CNA, width=7)
            max_l.pack(side="left", padx=1)
            cells.append((key, cur_l, min_l, max_l))
        return bdg, cells

    # Helper: update one cell triplet with session tracking
    def _upd(key, cur_l, min_l, max_l, val_f, fmt_fn, col_fn):
        lo, hi = _track_sensor(key, val_f)
        c_col  = col_fn(val_f)
        cur_l.config(text=fmt_fn(val_f), fg=c_col)
        min_l.config(text=fmt_fn(lo),
                     fg=_CLB if lo < val_f * 0.97 else _CNA)
        max_l.config(text=fmt_fn(hi),
                     fg=(_CCR if col_fn(hi) == _CCR else
                         (_CWN if col_fn(hi) == _CWN else _CNA)))

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 1 - MOTHERBOARD
    # ═════════════════════════════════════════════════════════════════════════
    _build_trapezoid_header(body, "MOTHERBOARD", "#3b82f6")

    mb_outer = tk.Frame(body, bg="#1a1d24",
                        highlightbackground="#3b82f6", highlightthickness=2)
    mb_outer.pack(fill="x", pady=(0, 2))

    mb_l = tk.Frame(mb_outer, bg="#1a1d24")
    mb_l.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    mb_r = tk.Frame(mb_outer, bg="#1a1d24")
    mb_r.pack(side="left", fill="both", expand=True, padx=1, pady=1)

    # Voltage sub-table
    volt_bdg, volt_cells = _live_table(mb_l, "VOLTAGE", [
        ("+12V",  "+12V"), ("+5V", "+5V"), ("+3.3V", "+3.3V"), ("DDR", "DDR4/5"),
    ])
    _volt_ref = {"+12V": (11.40, 12.60), "+5V": (4.75, 5.25),
                 "+3.3V": (3.135, 3.465), "DDR": (1.10, 1.50)}
    # Pre-fill with spec reference bounds (columns MIN/MAX show safe range)
    volt_bdg.config(text="N/A", bg=_CNA)
    for key, cur_l, min_l, max_l in volt_cells:
        lo_r, hi_r = _volt_ref.get(key, (0, 0))
        cur_l.config(text="N/A", fg=_CNA)
        min_l.config(text=f"{lo_r:.2f}V" if lo_r else "--", fg="#2a3650")
        max_l.config(text=f"{hi_r:.2f}V" if hi_r else "--", fg="#2a3650")

    # Temperature sub-table - probed via LHM/OHM if running
    mb_t_bdg, mb_t_cells = _live_table(mb_r, "TEMPERATURE", [
        ("mb_sys",  "SYS"),
        ("mb_vrm",  "VRM"),
    ])
    mb_t_bdg.config(text="N/A", bg=_CNA)

    # Disk-space + fans strip (kept from original)
    _build_disk_fans_strip(body)

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 2 - CPU
    # ═════════════════════════════════════════════════════════════════════════
    _cpu_short = _cpu_name[:28] if len(_cpu_name) > 28 else _cpu_name
    _build_trapezoid_header(body, f"CPU  {_cpu_short}", "#3b82f6")

    cpu_outer = tk.Frame(body, bg="#1a1d24",
                         highlightbackground="#3b82f6", highlightthickness=2)
    cpu_outer.pack(fill="x", pady=(0, 2))

    cpu_top = tk.Frame(cpu_outer, bg="#1a1d24")
    cpu_top.pack(fill="x", padx=1, pady=1)

    cpu_tl = tk.Frame(cpu_top, bg="#1a1d24")
    cpu_tl.pack(side="left", fill="both", expand=True)
    tk.Frame(cpu_top, bg=DIV, width=3).pack(side="left", fill="y", padx=2)
    cpu_tr = tk.Frame(cpu_top, bg="#1a1d24")
    cpu_tr.pack(side="left", fill="both", expand=True)

    cpu_t_bdg, cpu_t_cells = _live_table(cpu_tl, "TEMPERATURE (est.)", [
        ("cpu_pkg", "Package"),
        ("cpu_c0",  "Core #0"),
        ("cpu_c1",  "Core #1"),
        ("cpu_c2",  "Core #2"),
    ])
    cpu_clk_bdg, cpu_clk_cells = _live_table(cpu_tr, "CLOCKS", [
        ("cpu_cur",   "Current"),
        ("cpu_boost", "Boost"),
        ("cpu_load",  "Load %"),
    ])

    cpu_bot = tk.Frame(cpu_outer, bg="#1a1d24")
    cpu_bot.pack(fill="x", padx=1, pady=(0, 1))
    cpu_bl = tk.Frame(cpu_bot, bg="#1a1d24")
    cpu_bl.pack(side="left", fill="both", expand=True, padx=(0, 2))
    cpu_br = tk.Frame(cpu_bot, bg="#1a1d24")
    cpu_br.pack(side="left", fill="both", expand=True)

    cpu_pwr_bdg, cpu_pwr_cells = _live_table(cpu_bl, "POWER (est.)", [
        ("cpu_pwr", "Package W"),
        ("cpu_pl2", "PL2 limit"),
    ])
    cpu_use_bdg, cpu_use_cells = _live_table(cpu_br, "USAGE / CORES", [
        ("cpu_pct",  "Total %"),
        ("cpu_cphy", "Phys cores"),
    ])

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 3 - GPU
    # ═════════════════════════════════════════════════════════════════════════
    _gpu_label = (_gpu_name[:28] if _gpu_name else "Not detected")
    _build_trapezoid_header(body, f"GPU  {_gpu_label}", "#7c3aed")

    gpu_outer = tk.Frame(body, bg="#1a1d24",
                         highlightbackground="#7c3aed", highlightthickness=2)
    gpu_outer.pack(fill="x", pady=(0, 2))

    gpu_top = tk.Frame(gpu_outer, bg="#1a1d24")
    gpu_top.pack(fill="x", padx=1, pady=1)
    gpu_tl = tk.Frame(gpu_top, bg="#1a1d24")
    gpu_tl.pack(side="left", fill="both", expand=True)
    tk.Frame(gpu_top, bg=DIV, width=3).pack(side="left", fill="y", padx=2)
    gpu_tr = tk.Frame(gpu_top, bg="#1a1d24")
    gpu_tr.pack(side="left", fill="both", expand=True)

    gpu_t_bdg, gpu_t_cells = _live_table(gpu_tl, "TEMPERATURE", [
        ("gpu_temp", "Core"),
    ])
    gpu_u_bdg, gpu_u_cells = _live_table(gpu_tr, "USAGE", [
        ("gpu_load",  "GPU %"),
        ("gpu_mem_p", "VRAM %"),
    ])

    gpu_bot = tk.Frame(gpu_outer, bg="#1a1d24")
    gpu_bot.pack(fill="x", padx=1, pady=(0, 1))
    gpu_bl = tk.Frame(gpu_bot, bg="#1a1d24")
    gpu_bl.pack(side="left", fill="both", expand=True, padx=(0, 2))
    gpu_br = tk.Frame(gpu_bot, bg="#1a1d24")
    gpu_br.pack(side="left", fill="both", expand=True)

    gpu_pwr_bdg, gpu_pwr_cells = _live_table(gpu_bl, "POWER", [
        ("gpu_w",   "Draw W"),
        ("gpu_tdp", "TDP W"),
    ])
    gpu_clk_bdg, gpu_clk_cells = _live_table(gpu_br, "CLOCKS", [
        ("gpu_gr",  "Core MHz"),
        ("gpu_mem", "Mem  MHz"),
    ])

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 4 - DISK  (full-width grid layout, single Overload threshold)
    # ═════════════════════════════════════════════════════════════════════════
    _build_trapezoid_header(body, "DISK", "#0d9488")

    disk_outer = tk.Frame(body, bg="#1a1d24",
                          highlightbackground="#0d9488", highlightthickness=2)
    disk_outer.pack(fill="x", pady=(0, 4))

    # Full-width column header using grid
    disk_hdr = tk.Frame(disk_outer, bg="#080b18")
    disk_hdr.pack(fill="x")
    disk_hdr.columnconfigure(0, weight=2)   # Drive letter
    disk_hdr.columnconfigure(1, weight=4)   # Used GB
    disk_hdr.columnconfigure(2, weight=4)   # Free GB
    disk_hdr.columnconfigure(3, weight=3)   # Total
    disk_hdr.columnconfigure(4, weight=2)   # %
    disk_hdr.columnconfigure(5, weight=3)   # Status
    for col_i, txt in enumerate(["Drive", "Used GB", "Free GB", "Total", "%", "Status"]):
        tk.Label(disk_hdr, text=txt, bg="#080b18",
                 fg="#3d4e6b", font=("Segoe UI Semibold", 5),
                 anchor="center").grid(row=0, column=col_i, sticky="ew", padx=1, pady=1)

    # Fetch disk models once
    _disk_models: dict = {}
    try:
        _dm = _sp.run(["wmic", "diskdrive", "get", "model,index"],
                      capture_output=True, text=True, timeout=3,
                      creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        for _ln in (_dm.stdout or "").splitlines():
            _ln = _ln.strip()
            if _ln and "Model" not in _ln and _ln:
                parts_m = _ln.split()
                if parts_m:
                    idx_s = parts_m[-1]
                    if idx_s.isdigit():
                        _disk_models[int(idx_s)] = " ".join(parts_m[:-1])[:16]
                    else:
                        _disk_models[0] = " ".join(parts_m)[:16]
    except Exception:
        pass

    # Build one row per partition - full-width grid, live label refs
    disk_rows: list = []
    if psutil:
        for _pidx, _part in enumerate(psutil.disk_partitions()):
            try:
                _u = psutil.disk_usage(_part.mountpoint)
            except (PermissionError, OSError):
                continue
            _letter = _part.device.rstrip("\\")
            _pct    = _u.percent
            # Single threshold: 88% -> Overload (orange)
            _pc  = "#f59e0b" if _pct >= 88 else "#10b981"
            _bt  = "Overload" if _pct >= 88 else "OK"
            _bb  = "#f59e0b" if _pct >= 88 else "#10b981"

            _row = tk.Frame(disk_outer, bg="#0a0d1a")
            _row.pack(fill="x")
            _row.columnconfigure(0, weight=2)
            _row.columnconfigure(1, weight=4)
            _row.columnconfigure(2, weight=4)
            _row.columnconfigure(3, weight=3)
            _row.columnconfigure(4, weight=2)
            _row.columnconfigure(5, weight=3)

            tk.Label(_row, text=_letter, bg="#0a0d1a", fg="#8896a8",
                     font=(_BODY, 6), anchor="center").grid(
                row=0, column=0, sticky="ew", padx=1, pady=1)
            _used_l = tk.Label(_row, text=f"{_u.used/1e9:.1f}",
                               bg="#080b18", fg=_CN,
                               font=(_BODY, 6, "bold"), anchor="center")
            _used_l.grid(row=0, column=1, sticky="ew", padx=1)
            _free_l = tk.Label(_row, text=f"{_u.free/1e9:.1f}",
                               bg="#080b18", fg=_CN,
                               font=(_BODY, 6, "bold"), anchor="center")
            _free_l.grid(row=0, column=2, sticky="ew", padx=1)
            _tot_l  = tk.Label(_row, text=f"{_u.total/1e9:.1f}",
                               bg="#080b18", fg=_CNA,
                               font=(_BODY, 6), anchor="center")
            _tot_l.grid(row=0, column=3, sticky="ew", padx=1)
            _pct_l  = tk.Label(_row, text=f"{_pct:.0f}%",
                               bg="#080b18", fg=_pc,
                               font=(_BODY, 6, "bold"), anchor="center")
            _pct_l.grid(row=0, column=4, sticky="ew", padx=1)
            _bdg_l  = tk.Label(_row, text=_bt,
                               font=(_BODY, 5, "bold"),
                               bg=_bb, fg="#ffffff", anchor="center")
            _bdg_l.grid(row=0, column=5, sticky="ew", padx=2, pady=1)
            disk_rows.append((_letter, _used_l, _free_l, _tot_l, _pct_l, _bdg_l))

    # ═════════════════════════════════════════════════════════════════════════
    # LIVE REFRESH  (every 2 s, main thread via after())
    # ═════════════════════════════════════════════════════════════════════════
    def _refresh():
        try:
            if not body.winfo_exists():
                return

            # ── CPU data ──────────────────────────────────────────────────
            cpu_load  = psutil.cpu_percent(interval=None)
            freq      = psutil.cpu_freq()
            cur_mhz   = freq.current if freq else _cpu_prof["base"]
            boost_mhz = _cpu_prof["boost"]
            tj        = _cpu_prof["tj"]
            pl2       = _cpu_prof["pl2"]
            tdp       = _cpu_prof["tdp"]

            # Temperature estimate (no sensor driver on most Windows systems)
            # Calibrated: idle 38°C, scales linearly to ~85% Tj at 100% load
            cpu_t = 38.0 + (cpu_load / 100.0) * (tj * 0.85 - 38.0)

            # Power estimate: idle ~8 W, scales with load up to PL2
            cpu_w = 8.0 + (cpu_load / 100.0) * (pl2 - 8.0) * 0.92

            def fmt_c(v):   return f"{v:.0f}C"
            def fmt_mhz(v): return f"{int(v)}MHz"
            def fmt_w(v):   return f"{v:.0f}W"
            def fmt_p(v):   return f"{v:.0f}%"

            col_t  = lambda v: _ct(v, tj)
            col_w  = lambda v: _cw(v, pl2)

            # Temperature rows - package + 3 cores (same estimate; no per-core sensor)
            for key, cur_l, min_l, max_l in cpu_t_cells:
                _upd(key, cur_l, min_l, max_l, cpu_t, fmt_c, col_t)
            bt, bb = _badge_t(cpu_t, tj)
            cpu_t_bdg.config(text=bt, bg=bb)

            # Clock rows
            for key, cur_l, min_l, max_l in cpu_clk_cells:
                if key == "cpu_cur":
                    _upd(key, cur_l, min_l, max_l, cur_mhz, fmt_mhz,
                         lambda v: _CN if v >= boost_mhz * 0.70 else _CWN)
                elif key == "cpu_boost":
                    cur_l.config(text=fmt_mhz(boost_mhz), fg=_CNA)
                    min_l.config(text=fmt_mhz(_cpu_prof["base"]), fg=_CNA)
                    max_l.config(text=fmt_mhz(boost_mhz), fg=_CNA)
                elif key == "cpu_load":
                    _upd(key, cur_l, min_l, max_l, cpu_load, fmt_p, _cp)
            # Clock badge: throttle warning
            ratio = cur_mhz / max(boost_mhz, 1)
            if ratio < 0.45:
                cpu_clk_bdg.config(text="THROTTLE", bg=_CCR)
            elif ratio < 0.65:
                cpu_clk_bdg.config(text="LOW", bg=_CYL)
            else:
                cpu_clk_bdg.config(text="OK", bg=_COK)

            # Power rows
            for key, cur_l, min_l, max_l in cpu_pwr_cells:
                if key == "cpu_pwr":
                    _upd(key, cur_l, min_l, max_l, cpu_w, fmt_w, col_w)
                elif key == "cpu_pl2":
                    cur_l.config(text=f"{pl2}W",  fg=_CNA)
                    min_l.config(text=f"{tdp}W",  fg=_CNA)
                    max_l.config(text=f"{pl2}W",  fg=_CNA)
            bt, bb = _badge_w(cpu_w, pl2)
            cpu_pwr_bdg.config(text=bt, bg=bb)

            # Usage rows
            for key, cur_l, min_l, max_l in cpu_use_cells:
                if key == "cpu_pct":
                    _upd(key, cur_l, min_l, max_l, cpu_load, fmt_p, _cp)
                elif key == "cpu_cphy":
                    n_p = psutil.cpu_count(logical=False) or _cpu_prof["cores"]
                    n_l = psutil.cpu_count(logical=True)  or n_p * 2
                    cur_l.config(text=str(n_p), fg=_CNA)
                    min_l.config(text=str(n_l), fg=_CNA)
                    max_l.config(text="threads", fg="#2a3650")
            bp, bb = _badge_p(cpu_load)
            cpu_use_bdg.config(text=bp, bg=bb)

            # ── GPU data ──────────────────────────────────────────────────
            smi = _fetch_gpu_smi()
            if smi.get("ok"):
                gt   = smi["temp"]
                gl   = smi["usage"]
                gmu  = smi["mem_used"]
                gmt  = smi["mem_total"]
                gmp  = (gmu / max(gmt, 1)) * 100.0
                gpw  = smi["power"]
                gcgr = smi["clk_gr"]
                gcmm = smi["clk_mem"]
                gtj  = _gpu_prof["tj"]
                gtdp = _gpu_prof["tdp"]

                for key, cur_l, min_l, max_l in gpu_t_cells:
                    _upd(key, cur_l, min_l, max_l, gt, fmt_c, lambda v: _ct(v, gtj))
                bt, bb = _badge_t(gt, gtj)
                gpu_t_bdg.config(text=bt, bg=bb)

                for key, cur_l, min_l, max_l in gpu_u_cells:
                    if key == "gpu_load":
                        _upd(key, cur_l, min_l, max_l, gl, fmt_p, _cp)
                    elif key == "gpu_mem_p":
                        lo_m, hi_m = _track_sensor("gpu_mem_p", gmp)
                        cur_l.config(text=f"{gmp:.0f}%  ({gmu}M)", fg=_cp(gmp))
                        min_l.config(text=f"{lo_m:.0f}%",          fg=_CNA)
                        max_l.config(text=f"{hi_m:.0f}%",          fg=_CNA if _cp(hi_m) == _CN else _CWN)
                bp, bb = _badge_p(max(gl, gmp))
                gpu_u_bdg.config(text=bp, bg=bb)

                for key, cur_l, min_l, max_l in gpu_pwr_cells:
                    if key == "gpu_w":
                        _upd(key, cur_l, min_l, max_l, gpw, fmt_w,
                             lambda v: _cw(v, gtdp))
                    elif key == "gpu_tdp":
                        cur_l.config(text=f"{gtdp}W", fg=_CNA)
                        min_l.config(text="TDP",       fg="#2a3650")
                        max_l.config(text=f"{gtdp}W", fg=_CNA)
                bw, bb = _badge_w(gpw, gtdp)
                gpu_pwr_bdg.config(text=bw, bg=bb)

                for key, cur_l, min_l, max_l in gpu_clk_cells:
                    if key == "gpu_gr":
                        _upd(key, cur_l, min_l, max_l, float(gcgr),
                             lambda v: f"{int(v)}MHz", lambda v: _CN)
                    elif key == "gpu_mem":
                        _upd(key, cur_l, min_l, max_l, float(gcmm),
                             lambda v: f"{int(v)}MHz", lambda v: _CN)
                gpu_clk_bdg.config(text="OK", bg=_COK)
            else:
                for _cells in [gpu_t_cells, gpu_u_cells, gpu_pwr_cells, gpu_clk_cells]:
                    for _, c, mn, mx in _cells:
                        c.config(text="N/A", fg=_CNA)
                        mn.config(text="--",  fg=_CNA)
                        mx.config(text="--",  fg=_CNA)
                for _b in [gpu_t_bdg, gpu_u_bdg, gpu_pwr_bdg, gpu_clk_bdg]:
                    _b.config(text="N/A", bg=_CNA)

            # ── Motherboard sensors (LHM/OHM probe) ──────────────────────
            mb_data = _fetch_mb_sensors()
            mb_live = mb_data.get("source", "") != ""
            _mb_src  = mb_data.get("source", "")

            # Voltage cells
            _v_map = {"+12V": "volt_12v", "+5V": "volt_5v", "+3.3V": "volt_33v"}
            any_volt_live = False
            for key, cur_l, min_l, max_l in volt_cells:
                mb_key = _v_map.get(key)
                if mb_key and mb_live:
                    v = mb_data.get(mb_key, -1.0)
                    if v > 0:
                        spec = _VOLT_SPEC.get(key, {})
                        lo_w = spec.get("lo_w", 0)
                        hi_w = spec.get("hi_w", 99)
                        lo_h = spec.get("lo", 0)
                        hi_h = spec.get("hi", 99)
                        if v < lo_h or v > hi_h:
                            vc = _CCR
                        elif v < lo_w or v > hi_w:
                            vc = _CWN
                        else:
                            vc = _CN
                        lo_s, hi_s = _track_sensor(key, v)
                        cur_l.config(text=f"{v:.2f}V", fg=vc)
                        min_l.config(text=f"{lo_s:.2f}V", fg=_CLB if lo_s < v * 0.99 else _CNA)
                        max_l.config(text=f"{hi_s:.2f}V", fg=_CWN if hi_s > v * 1.01 else _CNA)
                        any_volt_live = True

            if any_volt_live:
                # Determine overall voltage badge
                all_ok = all(
                    (mb_data.get(mk, -1) > _VOLT_SPEC.get(vk, {}).get("lo_w", 0)
                     and mb_data.get(mk, -1) < _VOLT_SPEC.get(vk, {}).get("hi_w", 99))
                    for vk, mk in _v_map.items() if mb_data.get(mk, -1) > 0
                )
                volt_bdg.config(text="OK" if all_ok else "WARN",
                                bg=_COK if all_ok else _CYL)
            # else: keep N/A shown at build time

            # Temperature cells
            _t_map = {"mb_sys": "temp_sys", "mb_vrm": "temp_vrm"}
            for key, cur_l, min_l, max_l in mb_t_cells:
                mb_key = _t_map.get(key)
                if mb_key and mb_live:
                    tv = mb_data.get(mb_key, -1.0)
                    if tv > 0:
                        tc = _ct(tv, 105)  # MB Tj ~105°C typical
                        lo_t, hi_t = _track_sensor(key, tv)
                        cur_l.config(text=f"{tv:.0f}C", fg=tc)
                        min_l.config(text=f"{lo_t:.0f}C", fg=_CLB if lo_t < tv * 0.97 else _CNA)
                        max_l.config(text=f"{hi_t:.0f}C",
                                     fg=_CCR if _ct(hi_t, 105) == _CCR else
                                        (_CWN if _ct(hi_t, 105) == _CWN else _CNA))
            if mb_live:
                tv_sys = mb_data.get("temp_sys", -1.0)
                tv_vrm = mb_data.get("temp_vrm", -1.0)
                worst_t = max(tv_sys, tv_vrm)
                bt_mb, bb_mb = _badge_t(worst_t, 105)
                mb_t_bdg.config(text=bt_mb, bg=bb_mb)

            # ── Disk data ─────────────────────────────────────────────────
            disk_snap: dict = {}
            for (letter, used_l, free_l, tot_l, pct_l, bdg_l) in disk_rows:
                try:
                    _mp = letter if letter.endswith("\\") else letter + "\\"
                    u   = psutil.disk_usage(_mp)
                    pc  = u.percent
                    # Single threshold: 88%+ = Overload (orange), else OK (green)
                    _pc  = "#f59e0b" if pc >= 88 else "#10b981"
                    used_l.config(text=f"{u.used/1e9:.1f}", fg=_CN)
                    free_l.config(text=f"{u.free/1e9:.1f}",
                                  fg="#f59e0b" if pc >= 88 else _CN)
                    tot_l.config( text=f"{u.total/1e9:.1f}", fg=_CNA)
                    pct_l.config( text=f"{pc:.0f}%",          fg=_pc)
                    bdg_t  = "Overload" if pc >= 88 else "OK"
                    bdg_bg = "#f59e0b"  if pc >= 88 else "#10b981"
                    bdg_l.config(text=bdg_t, bg=bdg_bg)
                    disk_snap[_mp] = {
                        "used_gb": round(u.used / 1e9, 1),
                        "free_gb": round(u.free / 1e9, 1),
                        "total_gb": round(u.total / 1e9, 1),
                        "pct":     round(pc, 1),
                    }
                except Exception:
                    pass

            # ── Push to live_sensors bridge ───────────────────────────────
            if _HAS_LS:
                _n_p = psutil.cpu_count(logical=False) or _cpu_prof["cores"]
                _n_l = psutil.cpu_count(logical=True) or _n_p * 2
                _gpu_ok = smi.get("ok", False) if smi else False
                _ls.update({
                    "cpu_load":    cpu_load,
                    "cpu_temp":    cpu_t,
                    "cpu_mhz":     cur_mhz,
                    "cpu_boost":   boost_mhz,
                    "cpu_power":   cpu_w,
                    "cpu_tdp":     float(tdp),
                    "cpu_pl2":     float(pl2),
                    "cpu_cores_p": _n_p,
                    "cpu_cores_l": _n_l,
                    "cpu_name":    _cpu_name,
                    "gpu_temp":    smi.get("temp",    -1.0) if _gpu_ok else -1.0,
                    "gpu_load":    smi.get("usage",   -1.0) if _gpu_ok else -1.0,
                    "gpu_vram_pct": (smi.get("mem_used", 0) / max(smi.get("mem_total", 1), 1) * 100)
                                    if _gpu_ok else -1.0,
                    "gpu_vram_mb": float(smi.get("mem_used", -1)) if _gpu_ok else -1.0,
                    "gpu_power":   smi.get("power",   -1.0) if _gpu_ok else -1.0,
                    "gpu_tdp":     float(_gpu_prof["tdp"]),
                    "gpu_clk_gr":  float(smi.get("clk_gr",  -1)) if _gpu_ok else -1.0,
                    "gpu_clk_mem": float(smi.get("clk_mem", -1)) if _gpu_ok else -1.0,
                    "gpu_name":    smi.get("name", _gpu_name),
                    "gpu_ok":      _gpu_ok,
                    "mb_volt_12v": mb_data.get("volt_12v", -1.0),
                    "mb_volt_5v":  mb_data.get("volt_5v",  -1.0),
                    "mb_volt_33v": mb_data.get("volt_33v", -1.0),
                    "mb_temp_sys": mb_data.get("temp_sys", -1.0),
                    "mb_temp_vrm": mb_data.get("temp_vrm", -1.0),
                    "mb_source":   mb_data.get("source",   ""),
                    "disks":       disk_snap,
                    "session_hist": {k: list(v) for k, v in _SESSION_HIST.items()},
                })

        except Exception:
            pass

        # Schedule next tick
        try:
            if parent.winfo_exists():
                parent.after(2000, _refresh)
        except Exception:
            pass

    # First paint after layout is ready
    body.after(150, _refresh)
