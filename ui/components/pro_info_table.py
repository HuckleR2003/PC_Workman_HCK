"""
pro_info_table.py -- DeepMonitor
HWMonitor-style hierarchical live sensor table.

Layout:
    [ DeepMonitor  live hardware sensors ]  [ Reset ] [ Pause ] [ Save Data ]
    +-----------+---------+---------+---------+
    | Sensor    |  Value  |   Min   |   Max   |
    +-----------+---------+---------+---------+
    | v CPU                                   |
    |   [Temperatures]  <- blue-steel tint    |
    |     Package       52.0 C  44.0 C  52.0 C|
    |   [Utilization]   <- indigo tint        |
    |     Processor     13.7 %   0.0 %  23.6 %|
    |   [Clocks]        <- teal tint          |
    |     Current    3.99 GHz        4.01 GHz |
    | v GPU / Memory / Storage                |

Min/Max track session extremes. Reset clears them.
Save Data exports snapshot as .txt or .csv.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import threading
import datetime
import subprocess

try:
    import psutil
except ImportError:
    psutil = None

try:
    from core.hardware_sensors import get_cpu_temp, get_gpu_temp, get_gpu_usage
except ImportError:
    get_cpu_temp = get_gpu_temp = get_gpu_usage = None


# ── Font system ───────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# ── Palette ───────────────────────────────────────────────────────────────────
_BG       = "#0d1017"
_BG_CAT   = "#101624"
_BG_BAR   = "#07090f"
_FG       = "#ffffff"
_FG_DIM   = "#4b5563"
_FG_HDR   = "#374151"
_ACCENT   = "#be123c"
_GREEN    = "#34d399"
_AMBER    = "#fbbf24"
_RED      = "#ef4444"
_BTN_BG   = "#111827"
_BTN_HOV  = "#1e293b"
_BTN_FG   = "#6b7280"

# Sub-section row backgrounds (very subtle tints - not distracting)
_BG_TEMP_ROW  = "#060c14"   # cool blue-night tint
_BG_UTIL_ROW  = "#08060f"   # deep indigo tint
_BG_TEMP_WARM = "#0e0b00"   # warm amber tint
_BG_UTIL_WARM = "#0c0800"
_BG_TEMP_HOT  = "#160500"   # deep red tint
_BG_UTIL_HOT  = "#120306"

# Sub-section header bg/fg per category
_SUB_TEMP = ("#060e18", "#2d6e9f")   # Temperatures: dark blue bg, steel blue text
_SUB_UTIL = ("#080610", "#5b4d8a")   # Utilization:  dark indigo, muted violet
_SUB_CLK  = ("#050f0a", "#2d7a5a")   # Clocks:       dark emerald, teal
_SUB_MEM  = ("#0a0c10", "#4b5a6e")   # Memory:       dark slate, slate-blue
_SUB_DFLT = ("#0b0f19", "#4b5563")   # Default grey


# ── Value format functions ────────────────────────────────────────────────────
def _f_temp(v):  return f"{v:.1f} C"
def _f_pct(v):   return f"{v:.1f} %"
def _f_mhz(v):   return f"{v/1000:.3f} GHz" if v >= 1000 else f"{v:.0f} MHz"
def _f_gb(v):    return f"{v:.2f} GB"
def _f_mb(v):    return f"{v:.0f} MB"

# Tag functions (return tag name for that severity)
def _t_temp(v):  return "t_ok"   if v < 70 else ("t_warm" if v < 83 else "t_hot")
def _t_util(v):  return "u_ok"   if v < 70 else ("u_warm" if v < 88 else "u_hot")
def _t_pct(v):   return "ok"     if v < 70 else ("warm"   if v < 88 else "hot")
def _t_disk(v):  return "ok"     if v < 80 else ("warm"   if v < 93 else "hot")

_FMTS = {
    "temp":  (_f_temp, _t_temp),
    "util":  (_f_pct,  _t_util),
    "pct":   (_f_pct,  _t_pct),
    "mhz":   (_f_mhz,  lambda v: "ok"),
    "gb":    (_f_gb,   lambda v: "ok"),
    "mb":    (_f_mb,   lambda v: "ok"),
    "disk":  (_f_pct,  _t_disk),
}


class DeepMonitorTable(tk.Frame):
    """HWMonitor-style hierarchical sensor table with Save / Pause / Reset."""

    def __init__(self, parent):
        super().__init__(parent, bg=_BG)
        self._paused     = False
        self._stop_ev    = threading.Event()
        self._store: dict = {}   # iid -> {current, min, max, type}
        self._pause_btn  = None

        # Parent-driven destruction skips the destroy() override below —
        # <Destroy> always fires, so the 2 s update loop can't outlive the page.
        self.bind("<Destroy>",
                  lambda e: self._stop_ev.set() if e.widget is self else None,
                  add="+")

        self._build_action_bar()
        self._build_tree()
        self._populate()
        self._sched_update()

    # ── ACTION BAR ────────────────────────────────────────────────────────────

    def _build_action_bar(self):
        bar = tk.Frame(self, bg=_BG_BAR, height=36)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="DeepMonitor", font=(_MONO, 9, "bold"),
                 bg=_BG_BAR, fg=_ACCENT).pack(side="left", padx=(12, 0))
        tk.Label(bar, text="  live hardware sensors",
                 font=(_BODY, 8), bg=_BG_BAR, fg=_FG_DIM).pack(side="left")

        def _btn(text, cmd, save_ref=None):
            b = tk.Label(bar, text=text, font=(_MONO, 8, "bold"),
                         bg=_BTN_BG, fg=_BTN_FG, padx=10, pady=3,
                         cursor="hand2", relief="flat")
            b.pack(side="right", padx=(0, 6), pady=5)
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>",    lambda e: b.config(bg=_BTN_HOV, fg=_FG))
            b.bind("<Leave>",    lambda e: b.config(bg=_BTN_BG,  fg=_BTN_FG))
            if save_ref:
                setattr(self, save_ref, b)

        _btn("Save Data", self._save_data)
        _btn("Pause",     self._toggle_pause, "_pause_btn")
        _btn("Reset",     self._reset_minmax)

    # ── TREEVIEW ─────────────────────────────────────────────────────────────

    def _build_tree(self):
        SN = "DM.Treeview"
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass

        st.configure(SN,
            background=_BG, foreground=_FG, fieldbackground=_BG,
            borderwidth=0, rowheight=21, font=(_BODY, 8),
        )
        st.configure(f"{SN}.Heading",
            background=_BG_BAR, foreground=_FG_HDR,
            font=(_BODY, 7, "bold"), relief="flat", borderwidth=0,
        )
        st.map(SN,
            background=[("selected", "#141e30"), ("!selected", _BG)],
            foreground=[("selected", _FG),       ("!selected", _FG)],
        )

        wrap = tk.Frame(self, bg=_BG)
        wrap.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(
            wrap,
            style=SN,
            columns=("value", "min", "max"),
            show="tree headings",
            selectmode="none",
        )

        self._tree.heading("#0",    text="  Sensor", anchor="w")
        self._tree.heading("value", text="Value",    anchor="center")
        self._tree.heading("min",   text="Min",      anchor="center")
        self._tree.heading("max",   text="Max",      anchor="center")

        self._tree.column("#0",    width=230, minwidth=160, stretch=True)
        self._tree.column("value", width=95,  minwidth=70,  anchor="center", stretch=False)
        self._tree.column("min",   width=95,  minwidth=70,  anchor="center", stretch=False)
        self._tree.column("max",   width=95,  minwidth=70,  anchor="center", stretch=False)

        # ── Category headers ──────────────────────────────────────────────────
        self._tree.tag_configure("cat",
            font=(_HDR, 9), foreground="#dde4ef",
            background=_BG_CAT)

        # ── Sub-section headers (per category type) ───────────────────────────
        for tag, (bg, fg) in [
            ("sub_temp", _SUB_TEMP),
            ("sub_util", _SUB_UTIL),
            ("sub_clk",  _SUB_CLK),
            ("sub_mem",  _SUB_MEM),
            ("sub",      _SUB_DFLT),
        ]:
            self._tree.tag_configure(tag,
                font=(_BODY, 8, "bold"),
                foreground=fg, background=bg)

        # ── Temperature data rows (blue-night tint, heats up to red) ──────────
        self._tree.tag_configure("t_ok",
            foreground=_FG,   background=_BG_TEMP_ROW)
        self._tree.tag_configure("t_warm",
            foreground=_AMBER, background=_BG_TEMP_WARM)
        self._tree.tag_configure("t_hot",
            foreground=_RED,   background=_BG_TEMP_HOT)

        # ── Utilization data rows (indigo tint, heats up to red) ──────────────
        self._tree.tag_configure("u_ok",
            foreground=_FG,   background=_BG_UTIL_ROW)
        self._tree.tag_configure("u_warm",
            foreground=_AMBER, background=_BG_UTIL_WARM)
        self._tree.tag_configure("u_hot",
            foreground=_RED,   background=_BG_UTIL_HOT)

        # ── Generic value rows ────────────────────────────────────────────────
        self._tree.tag_configure("ok",    foreground=_FG,    background=_BG)
        self._tree.tag_configure("green", foreground=_GREEN, background=_BG)
        self._tree.tag_configure("warm",  foreground=_AMBER, background=_BG)
        self._tree.tag_configure("hot",   foreground=_RED,   background=_BG)
        self._tree.tag_configure("na",    foreground=_FG_DIM, background=_BG)

        # Scrollbar
        sb = tk.Scrollbar(wrap, orient="vertical", command=self._tree.yview,
                          bg=_BG, troughcolor=_BG_BAR,
                          activebackground=_BTN_HOV, width=9,
                          relief="flat", bd=0)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._tree.bind("<MouseWheel>",
            lambda e: self._tree.yview_scroll(-1 * (e.delta // 120), "units"))

    # ── INSERT HELPERS ────────────────────────────────────────────────────────

    def _cat(self, label, icon=""):
        txt = f"  {icon}  {label}" if icon else f"  {label}"
        return self._tree.insert("", "end",
            text=txt, values=("", "", ""),
            open=True, tags=("cat",))

    def _sub(self, parent, label, stype=""):
        """Sub-section header. stype: 'temp' | 'util' | 'clk' | 'mem' | ''"""
        _tag_map = {
            "temp": "sub_temp",
            "util": "sub_util",
            "clk":  "sub_clk",
            "mem":  "sub_mem",
        }
        tag = _tag_map.get(stype, "sub")
        return self._tree.insert(parent, "end",
            text=f"      {label}", values=("", "", ""),
            open=True, tags=(tag,))

    def _row(self, parent, iid, label, dtype, depth=2):
        indent = "  " * (depth * 4)
        self._tree.insert(parent, "end",
            iid=iid, text=f"{indent}{label}",
            values=("...", "...", "..."),
            tags=("na",))
        self._store[iid] = {"current": None, "min": None, "max": None, "type": dtype}

    # ── POPULATE TREE ─────────────────────────────────────────────────────────

    def _populate(self):
        # ── CPU ──────────────────────────────────────────────────────────────
        cpu = self._cat("CPU", "")

        t_sub = self._sub(cpu, "Temperatures", "temp")
        self._row(t_sub, "cpu_t_pkg",      "Package",    "temp")
        self._row(t_sub, "cpu_t_core_max", "Core (Max)", "temp")
        n_log = (psutil.cpu_count(logical=True) if psutil else 0) or 0
        for i in range(min(n_log, 8)):
            self._row(t_sub, f"cpu_t_c{i}", f"Core #{i}", "temp")

        u_sub = self._sub(cpu, "Utilization", "util")
        self._row(u_sub, "cpu_util",  "Processor", "util")
        for i in range(min(n_log, 8)):
            self._row(u_sub, f"cpu_u_c{i}", f"Core #{i}", "util")

        c_sub = self._sub(cpu, "Clocks", "clk")
        self._row(c_sub, "cpu_clk_cur",  "Current",    "mhz")
        self._row(c_sub, "cpu_clk_base", "Base speed", "mhz")

        # ── GPU ──────────────────────────────────────────────────────────────
        gpu = self._cat("GPU", "")

        gt_sub = self._sub(gpu, "Temperatures", "temp")
        self._row(gt_sub, "gpu_t_core", "Core", "temp")

        gu_sub = self._sub(gpu, "Utilization", "util")
        self._row(gu_sub, "gpu_util",    "GPU Load",  "util")
        self._row(gu_sub, "gpu_mem_pct", "Mem usage", "util")

        gm_sub = self._sub(gpu, "Memory", "mem")
        self._row(gm_sub, "gpu_mem_used",  "Used",  "mb")
        self._row(gm_sub, "gpu_mem_total", "Total", "mb")

        # ── RAM ──────────────────────────────────────────────────────────────
        mem = self._cat("Memory", "")
        self._row(mem, "ram_pct",   "Load",      "util", depth=1)
        self._row(mem, "ram_used",  "Used",      "gb",   depth=1)
        self._row(mem, "ram_avail", "Available", "gb",   depth=1)
        self._row(mem, "ram_total", "Total",     "gb",   depth=1)
        self._row(mem, "swap_pct",  "Swap load", "pct",  depth=1)
        self._row(mem, "swap_used", "Swap used", "gb",   depth=1)

        # ── Storage ──────────────────────────────────────────────────────────
        disk = self._cat("Storage", "")
        if psutil:
            try:
                for p in psutil.disk_partitions():
                    if not p.fstype:
                        continue
                    dr = p.device[:2] if len(p.device) >= 2 else p.device
                    k = dr.replace(":", "").replace("\\", "").lower()
                    self._row(disk, f"disk_{k}_pct",  f"{dr}  Used", "disk", depth=1)
                    self._row(disk, f"disk_{k}_free", f"{dr}  Free", "gb",   depth=1)
            except Exception:
                self._row(disk, "disk_c_pct",  "C:  Used", "disk", depth=1)
                self._row(disk, "disk_c_free", "C:  Free", "gb",   depth=1)
        else:
            self._row(disk, "disk_c_pct",  "C:  Used", "disk", depth=1)
            self._row(disk, "disk_c_free", "C:  Free", "gb",   depth=1)

    # ── UPDATE SCHEDULER ─────────────────────────────────────────────────────

    def _sched_update(self):
        if self._stop_ev.is_set():
            return
        if not self._paused:
            try:
                self._fetch_all()
            except Exception:
                pass
        self.after(2000, self._sched_update)

    def _fetch_all(self):
        self._upd_cpu()
        self._upd_gpu()
        self._upd_memory()
        self._upd_storage()

    # ── SENSOR READS ──────────────────────────────────────────────────────────

    def _upd_cpu(self):
        # Package temp via hardware_sensors
        try:
            if get_cpu_temp:
                t = get_cpu_temp()
                if t is not None:
                    self._set("cpu_t_pkg", float(t), "temp")
        except Exception:
            pass

        # Per-core temps via psutil (Windows: requires LibreHardwareMonitor or WMI)
        try:
            if psutil and hasattr(psutil, "sensors_temperatures"):
                all_t = psutil.sensors_temperatures() or {}
                entries = (all_t.get("coretemp")
                           or all_t.get("cpu_thermal")
                           or all_t.get("k10temp") or [])
                pkg_val    = None
                core_max   = None
                cores_only = []
                for e in entries:
                    lbl = (e.label or "").lower()
                    if "package" in lbl or "tdie" in lbl:
                        pkg_val = e.current
                    if "core" in lbl:
                        cores_only.append(e)
                        core_max = max(core_max, e.current) if core_max else e.current
                if pkg_val is not None:
                    self._set("cpu_t_pkg",      pkg_val,  "temp")
                if core_max is not None:
                    self._set("cpu_t_core_max", core_max, "temp")
                for i, e in enumerate(cores_only[:8]):
                    k = f"cpu_t_c{i}"
                    if k in self._store:
                        self._set(k, e.current, "temp")
        except Exception:
            pass

        # Utilization
        try:
            if psutil:
                self._set("cpu_util", psutil.cpu_percent(), "util")
                for i, pct in enumerate((psutil.cpu_percent(percpu=True) or [])[:8]):
                    k = f"cpu_u_c{i}"
                    if k in self._store:
                        self._set(k, float(pct), "util")
        except Exception:
            pass

        # Clocks
        try:
            if psutil:
                freq = psutil.cpu_freq()
                if freq:
                    self._set("cpu_clk_cur", freq.current, "mhz")
                    base = freq.min if freq.min and freq.min > 0 else freq.max
                    if base:
                        self._set("cpu_clk_base", base, "mhz")
        except Exception:
            pass

    def _upd_gpu(self):
        try:
            if get_gpu_temp:
                t = get_gpu_temp()
                if t is not None:
                    self._set("gpu_t_core", float(t), "temp")
        except Exception:
            pass
        try:
            if get_gpu_usage:
                u = get_gpu_usage()
                if u is not None:
                    self._set("gpu_util", float(u), "util")
        except Exception:
            pass
        # VRAM via nvidia-smi
        try:
            r = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=memory.used,memory.total,utilization.memory",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, errors="replace", timeout=2,
                creationflags=0x08000000,
            )
            if r.returncode == 0:
                parts = r.stdout.strip().split(",")
                if len(parts) >= 3:
                    used_mb  = float(parts[0].strip())
                    total_mb = float(parts[1].strip())
                    mem_pct  = float(parts[2].strip())
                    self._set("gpu_mem_used",  used_mb,  "mb")
                    self._set("gpu_mem_total", total_mb, "mb")
                    self._set("gpu_mem_pct",   mem_pct,  "util")
        except Exception:
            pass

    def _upd_memory(self):
        try:
            if not psutil:
                return
            vm  = psutil.virtual_memory()
            gb  = 1024 ** 3
            self._set("ram_pct",   vm.percent,           "util")
            self._set("ram_used",  vm.used      / gb,    "gb")
            self._set("ram_avail", vm.available / gb,    "gb")
            self._set("ram_total", vm.total     / gb,    "gb")
            sw = psutil.swap_memory()
            self._set("swap_pct",  sw.percent,           "pct")
            self._set("swap_used", sw.used      / gb,    "gb")
        except Exception:
            pass

    def _upd_storage(self):
        try:
            if not psutil:
                return
            gb = 1024 ** 3
            for p in psutil.disk_partitions():
                if not p.fstype:
                    continue
                dr = p.device[:2] if len(p.device) >= 2 else p.device
                k  = dr.replace(":", "").replace("\\", "").lower()
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    self._set(f"disk_{k}_pct",  u.percent, "disk")
                    self._set(f"disk_{k}_free", u.free / gb, "gb")
                except Exception:
                    pass
        except Exception:
            pass

    # ── CORE SET ──────────────────────────────────────────────────────────────

    def _set(self, iid: str, raw: float, dtype: str):
        store = self._store.get(iid)
        if store is None:
            return
        fmt_fn, tag_fn = _FMTS.get(dtype, _FMTS["pct"])
        store["current"] = raw
        if store["min"] is None or raw < store["min"]:
            store["min"] = raw
        if store["max"] is None or raw > store["max"]:
            store["max"] = raw
        val_str = fmt_fn(raw)
        min_str = fmt_fn(store["min"])
        max_str = fmt_fn(store["max"])
        tag     = tag_fn(raw)
        try:
            self._tree.item(iid,
                values=(val_str, min_str, max_str),
                tags=(tag,))
        except Exception:
            pass

    # ── BUTTON ACTIONS ────────────────────────────────────────────────────────

    def _toggle_pause(self):
        self._paused = not self._paused
        if self._pause_btn:
            if self._paused:
                self._pause_btn.config(text="Resume", fg=_AMBER, bg=_BTN_HOV)
            else:
                self._pause_btn.config(text="Pause",  fg=_BTN_FG, bg=_BTN_BG)

    def _reset_minmax(self):
        for s in self._store.values():
            s["min"] = None
            s["max"] = None
        if not self._paused:
            try:
                self._fetch_all()
            except Exception:
                pass

    def _save_data(self):
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Save DeepMonitor snapshot",
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("CSV", "*.csv"), ("All", "*.*")],
            initialfile=f"deepmonitor_{ts}.txt",
        )
        if not path:
            return
        try:
            lines = [
                f"DeepMonitor - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                f"{'Sensor':<44} {'Value':<15} {'Min':<15} {'Max':<15}",
                "-" * 89,
            ]
            for iid in self._store:
                try:
                    vals = self._tree.item(iid, "values")
                    name = self._tree.item(iid, "text").strip()
                    if vals and any(v not in ("...", "") for v in vals):
                        lines.append(
                            f"{name:<44} {vals[0]:<15} {vals[1]:<15} {vals[2]:<15}"
                        )
                except Exception:
                    pass
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
        except Exception as exc:
            print(f"[DeepMonitor] Save failed: {exc}")

    def destroy(self):
        self._stop_ev.set()
        super().destroy()


# Compatibility alias
ProInfoTable = DeepMonitorTable


def create_pro_info_table(parent):
    return DeepMonitorTable(parent)
