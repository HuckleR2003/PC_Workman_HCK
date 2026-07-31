"""
ui/pages/overclock_lab.py
OVERCLOCK - Headroom Lab (v2, 2026-07).

Read-only by design. PC Workman NEVER writes clocks, voltages or power
limits - the whole page is measurement and explanation:

  - Afterburner-style segmented load bars (lime at low fill, through amber,
    into brand bordeaux near the limit)
  - 6 stats per component: clock vs boost, power vs budget, temp vs throttle
    territory, live load, plus voltage / session-peak text stats
  - LIMITING FACTOR verdict (thermal / power / headroom / idle)
  - "WHAT PC WORKMAN LEARNS" - per-workload averages (Idle / Medium / Heavy /
    Gaming) computed from the DeepMonitor history (metrics_store), the same
    5-bucket classification the learning engine uses
  - an efficiency corner that reads live FPS from RTSS when it runs

Every live value comes from the existing live_sensors pipeline (single
producer: core/live_collector.py); history comes from metrics_store. This
page is a consumer only, never a producer. Refresh loop follows the app
conventions: winfo_exists guard, stops when the user navigates away.
"""

import tkinter as tk

try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

try:
    from utils.i18n import get_lang
except ImportError:
    def get_lang():
        return "en"

_BG      = "#0a0e14"
_CARD    = "#101624"
_EDGE    = "#1d2738"
_ACCENT  = "#ef4444"     # overclock red
_OK      = "#22c55e"
_WARN    = "#f59e0b"
_IDLEYEL = "#fde047"     # light yellow - idle verdict
_DIM     = "#6f86a3"
_TXT     = "#d4dce6"

# Segmented-bar palette: lime at low fill -> amber -> brand bordeaux at limit
_SEG_LOW  = (163, 230, 53)    # #a3e635 lime
_SEG_MID  = (245, 158, 11)    # #f59e0b amber
_SEG_HIGH = (192, 24, 42)     # #c0182a brand bordeaux
_SEG_OFF  = "#222b3b"

# Throttle-territory reference points (advisory display only, not alarms):
# consumer CPUs throttle around 95-100°C, GPUs start pulling clocks ~83-84°C.
_CPU_THROTTLE_C = 95.0
_GPU_HOT_C      = 83.0

_REFRESH_MS   = 2000
_LEARN_EVERY  = 30        # recompute bucket table every N refreshes (~60 s)
_LEARN_HOURS  = 14 * 24   # 14-day window for the LEARNS table


def _t(pl: str, en: str) -> str:
    return pl if get_lang() == "pl" else en


def _snap() -> dict:
    """Live sensor snapshot ({} on any failure) - consumer only."""
    try:
        from hck_gpt.data import live_sensors
        return live_sensors.snapshot() or {}
    except Exception:
        return {}


def _val(v, suffix="", nd=0):
    """Format a sensor value; '-' when the pipeline reports -1/None."""
    try:
        if v is None or float(v) < 0:
            return "-"
        return f"{float(v):.{nd}f}{suffix}"
    except Exception:
        return "-"


def _ratio(cur, ceiling) -> float:
    """0.0-1.0 pressure ratio; -1 when either side is unknown."""
    try:
        cur, ceiling = float(cur), float(ceiling)
        if cur < 0 or ceiling <= 0:
            return -1.0
        return max(0.0, min(cur / ceiling, 1.0))
    except Exception:
        return -1.0


def _cpu_model_name(s: dict) -> str:
    """CPU marketing name: live profile first, registry fallback (the live
    key is empty on machines without a matched profile)."""
    name = (s.get("cpu_name") or "").strip()
    if name:
        return name
    global _CPU_NAME_CACHE
    if _CPU_NAME_CACHE is not None:
        return _CPU_NAME_CACHE
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
            v, _ = winreg.QueryValueEx(k, "ProcessorNameString")
            _CPU_NAME_CACHE = str(v).strip()
    except Exception:
        _CPU_NAME_CACHE = ""
    return _CPU_NAME_CACHE


_CPU_NAME_CACHE = None


# ── Workload bucketing (same 5-context classification the learning uses) ──────

def _bucket(cpu_load, gpu_load) -> str:
    try:
        if gpu_load is not None and float(gpu_load) >= 60:
            return "gaming"
        c = float(cpu_load)
        if c < 15:
            return "idle"
        if c < 35:
            return "light"
        if c < 65:
            return "medium"
        return "heavy"
    except Exception:
        return "light"


def _bucket_stats() -> dict:
    """Per-workload averages from DeepMonitor history (metrics_store).

    Returns {bucket: {metric: avg}} for idle/medium/heavy/gaming; the
    'light' bucket is folded into 'medium' so no learning is hidden.
    {} when the store has nothing yet."""
    try:
        from hck_gpt.data.metrics_store import metrics_store
        rows = metrics_store.get_history(hours=_LEARN_HOURS) or []
    except Exception:
        return {}
    acc: dict = {}
    for r in rows:
        cl = r.get("cpu_load")
        if cl is None or cl < 0:
            continue
        b = _bucket(cl, r.get("gpu_load"))
        if b == "light":
            b = "medium"
        slot = acc.setdefault(b, {})
        for key in ("cpu_load", "cpu_temp", "cpu_power",
                    "gpu_load", "gpu_temp", "gpu_power", "gpu_vram_pct"):
            v = r.get(key)
            if v is None or v < 0:
                continue
            s, n = slot.get(key, (0.0, 0))
            slot[key] = (s + float(v), n + 1)
    out: dict = {}
    for b, metrics in acc.items():
        out[b] = {k: (s / n) for k, (s, n) in metrics.items() if n > 0}
        out[b]["_n"] = max((n for (_, n) in metrics.values()), default=0)
    return out


# ── Afterburner-style segmented bar ───────────────────────────────────────────

def _seg_color(frac: float) -> str:
    """Color at position frac (0..1) along lime -> amber -> bordeaux."""
    if frac <= 0.55:
        t = frac / 0.55
        a, b = _SEG_LOW, _SEG_MID
    else:
        t = (frac - 0.55) / 0.45
        a, b = _SEG_MID, _SEG_HIGH
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class _SegBar:
    """Slim segmented meter - dashes fill left to right, colored by level."""

    def __init__(self, parent, bg=_CARD):
        self.cv = tk.Canvas(parent, height=9, bg=bg, highlightthickness=0)
        self.ratio = -1.0
        self.cv.bind("<Configure>", lambda e: self._draw())

    def set(self, ratio: float):
        self.ratio = ratio if ratio is not None else -1.0
        self._draw()

    def _draw(self):
        cv = self.cv
        try:
            if not cv.winfo_exists():
                return
        except Exception:
            return
        cv.delete("all")
        W = cv.winfo_width()
        if W < 20:
            return
        seg_w, gap, h = 9, 4, 7
        n = max(10, (W - 4) // (seg_w + gap))
        filled = 0 if self.ratio < 0 else int(round(self.ratio * n))
        for i in range(n):
            x = 2 + i * (seg_w + gap)
            if i < filled:
                col = _seg_color(i / max(n - 1, 1))
            else:
                col = _SEG_OFF
            cv.create_rectangle(x, 1, x + seg_w, 1 + h, fill=col, outline="")


# ── Verdict ───────────────────────────────────────────────────────────────────

def _verdict(s: dict) -> tuple:
    """Rule-based LIMITING FACTOR verdict -> (headline, detail, color)."""
    cpu_load = s.get("cpu_load", -1)
    gpu_load = s.get("gpu_load", -1)
    r_cpu_t  = _ratio(s.get("cpu_temp"), _CPU_THROTTLE_C)
    r_gpu_t  = _ratio(s.get("gpu_temp"), _GPU_HOT_C)
    r_cpu_p  = _ratio(s.get("cpu_power"), s.get("cpu_pl2") if float(s.get("cpu_pl2", -1) or -1) > 0 else s.get("cpu_tdp"))
    r_gpu_p  = _ratio(s.get("gpu_power"), s.get("gpu_tdp"))

    busy = (isinstance(cpu_load, (int, float)) and cpu_load >= 35) or \
           (isinstance(gpu_load, (int, float)) and gpu_load >= 35)
    if not busy:
        return (_t("BEZCZYNNOŚĆ - brak danych pod obciążeniem",
                   "IDLE - nothing under load to measure"),
                _t("Uruchom grę lub render i wróć tutaj: headroom mierzy się pod presją.",
                   "Start a game or a render and come back: headroom is measured under pressure."),
                _IDLEYEL)
    if r_cpu_t >= 0.93 or r_gpu_t >= 0.96:
        side = "CPU" if r_cpu_t >= r_gpu_t else "GPU"
        return (_t(f"LIMIT TERMICZNY - {side}", f"THERMAL-LIMITED - {side}"),
                _t("Zegary trzyma temperatura, nie krzem. Lepsze chłodzenie/krzywa wentylatorów da więcej niż jakikolwiek OC.",
                   "Temperature is holding the clocks back, not the silicon. Better cooling or a better fan curve beats any OC here."),
                _ACCENT)
    if r_cpu_p >= 0.95 or r_gpu_p >= 0.95:
        side = "CPU" if r_cpu_p >= r_gpu_p else "GPU"
        return (_t(f"LIMIT MOCY - {side}", f"POWER-LIMITED - {side}"),
                _t("Układ dobija do budżetu mocy (TDP/PL2). To limit fabryczny, nie usterka.",
                   "The chip is riding its power budget (TDP/PL2). That is a factory limit, not a fault."),
                _WARN)
    return (_t("JEST HEADROOM", "HEADROOM AVAILABLE"),
            _t("Ani temperatura, ani budżet mocy nie dławią zegarów przy obecnym obciążeniu.",
               "Neither temperature nor the power budget is choking the clocks at this load."),
            _OK)


# ── Small UI builders ─────────────────────────────────────────────────────────

def _stat_row(parent, label_txt):
    """Label + value + segmented bar. Returns (value_label, segbar)."""
    row = tk.Frame(parent, bg=_CARD)
    row.pack(fill="x", padx=12, pady=(2, 0))
    top = tk.Frame(row, bg=_CARD)
    top.pack(fill="x")
    tk.Label(top, text=label_txt, font=(_BODY, 8), bg=_CARD, fg=_DIM
             ).pack(side="left")
    val = tk.Label(top, text="-", font=(_MONO, 8, "bold"), bg=_CARD, fg=_TXT)
    val.pack(side="right")
    bar = _SegBar(row)
    bar.cv.pack(fill="x", pady=(1, 1))
    return val, bar


def _text_stat(parent, label_txt):
    """Compact text-only stat (no bar). Returns value label."""
    f = tk.Frame(parent, bg=_CARD)
    f.pack(side="left", expand=True, fill="x")
    tk.Label(f, text=label_txt, font=(_BODY, 7), bg=_CARD, fg=_DIM
             ).pack(anchor="w")
    val = tk.Label(f, text="-", font=(_MONO, 9, "bold"), bg=_CARD, fg=_TXT)
    val.pack(anchor="w")
    return val


_BUCKET_ORDER = ("idle", "medium", "heavy", "gaming")
_BUCKET_STYLE = {
    "idle":   ("#8b98ab", "IDLE"),
    "medium": ("#38bdf8", "MEDIUM"),
    "heavy":  ("#f59e0b", "HEAVY"),
    "gaming": ("#8b5cf6", "GAMING"),
}


def _learn_table(parent, cols):
    """'WHAT PC WORKMAN LEARNS' mini table. cols = [(header, metric_key,
    suffix, nd)]. Returns {(bucket, metric_key): value_label} + status label."""
    box = tk.Frame(parent, bg=_CARD)
    box.pack(fill="x", padx=12, pady=(6, 8))
    head = tk.Frame(box, bg=_CARD)
    head.pack(fill="x")
    status = tk.Label(head, text="◌ OFFLINE", font=(_MONO, 8, "bold"),
                      bg=_CARD, fg=_DIM)
    status.pack(side="left")
    tk.Label(head, text=" WHAT PC WORKMAN LEARNS",
             font=(_HDR, 8, "bold"), bg=_CARD, fg="#9aa8bd").pack(side="left")

    grid = tk.Frame(box, bg=_CARD)
    grid.pack(fill="x", pady=(3, 0))
    # header row
    tk.Label(grid, text="", bg=_CARD, width=7).grid(row=0, column=0, sticky="w")
    for ci, (hdr, _k, _s, _nd) in enumerate(cols):
        tk.Label(grid, text=hdr, font=(_BODY, 7), bg=_CARD, fg=_DIM
                 ).grid(row=0, column=ci + 1, padx=2)
    cells = {}
    for ri, b in enumerate(_BUCKET_ORDER):
        color, label = _BUCKET_STYLE[b]
        row_bg = _CARD if ri % 2 == 0 else "#0d1320"
        tk.Label(grid, text=label, font=(_MONO, 7, "bold"), bg=row_bg,
                 fg=color, width=7, anchor="w"
                 ).grid(row=ri + 1, column=0, sticky="ew")
        for ci, (_hdr, key, _s, _nd) in enumerate(cols):
            c = tk.Label(grid, text="·", font=(_MONO, 8), bg=row_bg, fg=_TXT,
                         width=7)
            c.grid(row=ri + 1, column=ci + 1, sticky="ew", padx=1)
            cells[(b, key)] = c
    for ci in range(len(cols) + 1):
        grid.columnconfigure(ci, weight=1)
    return cells, status


def _fill_learn(cells, status, stats, cols, online):
    status.config(text="◉ ONLINE" if online else "◌ OFFLINE",
                  fg=_OK if online else _DIM)
    for b in _BUCKET_ORDER:
        bs = stats.get(b, {})
        for (_hdr, key, suffix, nd) in cols:
            v = bs.get(key)
            cells[(b, key)].config(
                text=_val(v, suffix, nd) if v is not None else "·")


# ── Page build ────────────────────────────────────────────────────────────────

def build(win):
    """Build the OVERCLOCK page into win.content_area."""
    area = win.content_area
    body = tk.Frame(area, bg=_BG)
    body.pack(fill="both", expand=True, padx=14, pady=(6, 8))

    # ── Verdict panel ─────────────────────────────────────────────────────────
    verdict_card = tk.Frame(body, bg=_CARD, highlightthickness=1,
                            highlightbackground=_EDGE)
    verdict_card.pack(fill="x", pady=(0, 8))
    vrow = tk.Frame(verdict_card, bg=_CARD)
    vrow.pack(fill="x", padx=14, pady=(7, 8))
    tk.Label(vrow, text=_t("CZYNNIK OGRANICZAJĄCY", "LIMITING FACTOR"),
             font=(_HDR, 8), bg=_CARD, fg=_DIM).pack(anchor="w")
    v_head = tk.Label(vrow, text="…", font=(_HDR, 13, "bold"),
                      bg=_CARD, fg=_TXT, anchor="w")
    v_head.pack(fill="x")
    v_sub = tk.Label(vrow, text="", font=(_BODY, 8), bg=_CARD, fg=_DIM,
                     anchor="w", wraplength=880, justify="left")
    v_sub.pack(fill="x")

    # ── Two headroom columns: CPU | GPU ───────────────────────────────────────
    cols_f = tk.Frame(body, bg=_BG)
    cols_f.pack(fill="both", expand=True)
    cols_f.columnconfigure(0, weight=1, uniform="oc")
    cols_f.columnconfigure(1, weight=1, uniform="oc")
    cols_f.rowconfigure(0, weight=1)

    def _card(col, title):
        c = tk.Frame(cols_f, bg=_CARD, highlightthickness=1,
                     highlightbackground=_EDGE)
        c.grid(row=0, column=col, sticky="nsew", padx=(0, 8) if col == 0 else 0)
        trow = tk.Frame(c, bg=_CARD)
        trow.pack(fill="x", padx=12, pady=(7, 1))
        tk.Label(trow, text=title, font=(_HDR, 10, "bold"), bg=_CARD, fg=_TXT
                 ).pack(side="left")
        name = tk.Label(trow, text="", font=(_MONO, 7), bg=_CARD, fg=_DIM,
                        anchor="e")
        name.pack(side="right")
        return c, name

    cpu_card, cpu_name = _card(0, "CPU HEADROOM")
    gpu_card, gpu_name = _card(1, "GPU HEADROOM")

    # CPU: 4 segmented bars + 2 text stats = 6
    cpu_clk_v,  cpu_clk_b  = _stat_row(cpu_card, _t("Zegar vs boost", "Clock vs boost"))
    cpu_pwr_v,  cpu_pwr_b  = _stat_row(cpu_card, _t("Moc vs budżet (TDP/PL2)", "Power vs budget (TDP/PL2)"))
    cpu_tmp_v,  cpu_tmp_b  = _stat_row(cpu_card, _t("Temp. vs strefa throttle", "Temp vs throttle territory"))
    cpu_load_v, cpu_load_b = _stat_row(cpu_card, _t("Obciążenie", "Load"))
    cpu_txt = tk.Frame(cpu_card, bg=_CARD)
    cpu_txt.pack(fill="x", padx=12, pady=(4, 0))
    cpu_vcore_v = _text_stat(cpu_txt, "VCORE")
    cpu_peak_v  = _text_stat(cpu_txt, _t("SZCZYT SESJI", "SESSION PEAK"))

    _CPU_COLS = [("LOAD", "cpu_load", "%", 0),
                 ("PWR",  "cpu_power", "W", 0),
                 ("TEMP", "cpu_temp", "°", 0)]
    cpu_cells, cpu_status = _learn_table(cpu_card, _CPU_COLS)

    # GPU: 4 segmented bars + 2 text stats = 6
    gpu_load_v, gpu_load_b = _stat_row(gpu_card, _t("Obciążenie", "Load"))
    gpu_pwr_v,  gpu_pwr_b  = _stat_row(gpu_card, _t("Moc vs TDP", "Power vs TDP"))
    gpu_tmp_v,  gpu_tmp_b  = _stat_row(gpu_card, _t("Temp. vs zrzucanie zegarów", "Temp vs clock-pull territory"))
    gpu_vram_v, gpu_vram_b = _stat_row(gpu_card, "VRAM")
    gpu_txt = tk.Frame(gpu_card, bg=_CARD)
    gpu_txt.pack(fill="x", padx=12, pady=(4, 0))
    gpu_core_v = _text_stat(gpu_txt, _t("ZEGAR RDZENIA", "CORE CLOCK"))
    gpu_mem_v  = _text_stat(gpu_txt, _t("ZEGAR PAMIĘCI", "MEMORY CLOCK"))

    _GPU_COLS = [("LOAD", "gpu_load", "%", 0),
                 ("PWR",  "gpu_power", "W", 0),
                 ("TEMP", "gpu_temp", "°", 0),
                 ("VRAM", "gpu_vram_pct", "%", 0)]
    gpu_cells, gpu_status = _learn_table(gpu_card, _GPU_COLS)

    # ── Efficiency corner (RTSS) ──────────────────────────────────────────────
    eff = tk.Frame(body, bg=_CARD, highlightthickness=1, highlightbackground=_EDGE)
    eff.pack(fill="x", pady=(8, 0))
    eff_lbl = tk.Label(eff, text="", font=(_BODY, 8), bg=_CARD, fg=_DIM,
                       anchor="w", wraplength=880, justify="left")
    eff_lbl.pack(fill="x", padx=14, pady=7)

    state = {"tick": 0, "learn": None}

    def _session_peak(s, key):
        try:
            hist = s.get("session_hist") or {}
            mm = hist.get(key)
            if mm and float(mm[1]) > 0:
                return f"{float(mm[1]):.0f} MHz"
        except Exception:
            pass
        return "-"

    # ── Refresh loop (page-conventional guards) ───────────────────────────────
    def _refresh():
        try:
            if not body.winfo_exists():
                return
        except Exception:
            return
        if getattr(win, "current_view", None) != "overclock":
            return          # user left - loop dies with the page

        s = _snap()

        head, sub, color = _verdict(s)
        v_head.config(text=head, fg=color)
        v_sub.config(text=sub)

        # CPU
        cpu_name.config(text=_cpu_model_name(s)[:44])
        mhz, boost = s.get("cpu_mhz", -1), s.get("cpu_boost", -1)
        cpu_clk_v.config(text=f"{_val(mhz,' MHz')} / {_val(boost,' MHz')}")
        cpu_clk_b.set(_ratio(mhz, boost))
        pcap = s.get("cpu_pl2", -1) if float(s.get("cpu_pl2", -1) or -1) > 0 else s.get("cpu_tdp", -1)
        pwr = s.get("cpu_power", -1)
        cpu_pwr_v.config(text=f"{_val(pwr,' W')} / {_val(pcap,' W')}")
        cpu_pwr_b.set(_ratio(pwr, pcap))
        ct = s.get("cpu_temp", -1)
        cpu_tmp_v.config(text=f"{_val(ct,'°C')} / {_CPU_THROTTLE_C:.0f}°C")
        cpu_tmp_b.set(_ratio(ct, _CPU_THROTTLE_C))
        cl = s.get("cpu_load", -1)
        cpu_load_v.config(text=_val(cl, "%"))
        cpu_load_b.set(_ratio(cl, 100))
        cpu_vcore_v.config(text=_val(s.get("mb_volt_vcore"), " V", 3))
        cpu_peak_v.config(text=_session_peak(s, "cpu_mhz"))

        # GPU
        gpu_name.config(text=(s.get("gpu_name") or "-")[:44])
        if s.get("gpu_ok"):
            gl = s.get("gpu_load", -1)
            gpu_load_v.config(text=_val(gl, "%"))
            gpu_load_b.set(_ratio(gl, 100))
            gpu_pwr_v.config(text=f"{_val(s.get('gpu_power'),' W')} / {_val(s.get('gpu_tdp'),' W')}")
            gpu_pwr_b.set(_ratio(s.get("gpu_power"), s.get("gpu_tdp")))
            gt = s.get("gpu_temp", -1)
            gpu_tmp_v.config(text=f"{_val(gt,'°C')} / {_GPU_HOT_C:.0f}°C")
            gpu_tmp_b.set(_ratio(gt, _GPU_HOT_C))
            gv = s.get("gpu_vram_pct", -1)
            gpu_vram_v.config(text=_val(gv, "%"))
            gpu_vram_b.set(_ratio(gv, 100))
            gpu_core_v.config(text=_val(s.get("gpu_clk_gr"), " MHz"))
            gpu_mem_v.config(text=_val(s.get("gpu_clk_mem"), " MHz"))
        else:
            gpu_load_v.config(text="-"); gpu_load_b.set(-1)
            gpu_pwr_v.config(text="-");  gpu_pwr_b.set(-1)
            gpu_tmp_v.config(text="-");  gpu_tmp_b.set(-1)
            gpu_vram_v.config(text="-"); gpu_vram_b.set(-1)
            gpu_core_v.config(text="-"); gpu_mem_v.config(text="-")

        # LEARNS table - recompute every _LEARN_EVERY ticks (history moves
        # every 5 min anyway); live feed freshness drives ONLINE/OFFLINE.
        if state["learn"] is None or state["tick"] % _LEARN_EVERY == 0:
            try:
                state["learn"] = _bucket_stats()
            except Exception:
                state["learn"] = {}
        import time as _time
        online = bool(state["learn"]) and (_time.time() - float(s.get("ts") or 0) < 15)
        _fill_learn(cpu_cells, cpu_status, state["learn"], _CPU_COLS, online)
        _fill_learn(gpu_cells, gpu_status, state["learn"], _GPU_COLS, online)
        state["tick"] += 1

        # Efficiency corner
        fps = None
        try:
            from core.fps_monitor import read_fps
            fps = read_fps()
        except Exception:
            fps = None
        gl = s.get("gpu_load", -1)
        if fps:
            if isinstance(gl, (int, float)) and gl >= 95:
                eff_lbl.config(text=_t(
                    f"EFEKTYWNOŚĆ: {fps:.0f} FPS przy GPU {gl:.0f}%. Karta pracuje na ścianie - limit FPS odrobinę poniżej średniej zwykle obniża temperatury i hałas przy niemal tej samej płynności.",
                    f"EFFICIENCY: {fps:.0f} FPS at {gl:.0f}% GPU. The card is riding its limit - an FPS cap slightly below average usually cuts temps and noise at nearly the same smoothness."))
            else:
                eff_lbl.config(text=_t(
                    f"EFEKTYWNOŚĆ: {fps:.0f} FPS przy GPU {_val(gl,'%')}. Jest zapas - limit FPS nie jest tu potrzebny.",
                    f"EFFICIENCY: {fps:.0f} FPS at {_val(gl,'%')} GPU. There is slack - an FPS cap is not needed here."))
        else:
            eff_lbl.config(text=_t(
                "EFEKTYWNOŚĆ: brak RTSS (RivaTuner / MSI Afterburner) - z nim ta sekcja pokaże żywe FPS i podpowie sensowny limit.",
                "EFFICIENCY: RTSS not running (RivaTuner / MSI Afterburner) - with it, this section shows live FPS and suggests a sensible cap."))

        try:
            body.after(_REFRESH_MS, _refresh)
        except Exception:
            pass

    _refresh()
