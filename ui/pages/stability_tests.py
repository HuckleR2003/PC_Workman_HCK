"""
PC Workman Stability Tests Page
Real-time diagnostics: file integrity, HCK Stats Engine status, log viewer
"""

from utils.fonts import UI as _FONT_UI, HDR as _FONT_HDR, HEAVY as _FONT_HEAVY, LIGHT as _FONT_LIGHT  # noqa: F401
import tkinter as tk
import os
import time
import threading
from datetime import datetime

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = _FONT_UI, "Consolas"
_HDR  = _FONT_HDR
_BODY = _UIF
_MONO = _MONOF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BG = "#0a0e14"
PANEL = "#0f1117"
BORDER = "#1a1d24"


def build_stability_tests_page(self, parent):
    main = tk.Frame(parent, bg=BG)
    main.pack(fill="both", expand=True)

    header = tk.Frame(main, bg="#10b981", height=32)
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(header, text="PC Workman Stability Tests",
             font=(_BODY, 10, "bold"), bg="#10b981", fg="#000000",
             padx=10).pack(side="left", pady=4)

    back_btn = tk.Label(header, text="Back", font=(_BODY, 8, "bold"),
                        bg="#065f46", fg="#ffffff", padx=8, cursor="hand2")
    back_btn.pack(side="right", padx=10, pady=4)
    back_btn.bind("<Button-1>", lambda e=None: _go_back(self, parent))
    back_btn.bind("<Enter>", lambda e=None: back_btn.config(bg="#047857"))
    back_btn.bind("<Leave>", lambda e=None: back_btn.config(bg="#065f46"))

    content = tk.Frame(main, bg=BG)
    content.pack(fill="both", expand=True, padx=10, pady=5)

    left = tk.Frame(content, bg=BG)
    left.pack(side="left", fill="both", expand=True, padx=(0, 5))

    right = tk.Frame(content, bg=BG)
    right.pack(side="right", fill="both", expand=True, padx=(5, 0))

    _build_file_integrity_panel(left)
    _build_log_viewer_panel(left)
    _build_engine_status_panel(right)


def _go_back(self, parent):
    for w in parent.winfo_children():
        w.destroy()
    from ui.components.yourpc_page import _build_central
    _build_central(self, parent)


def _data_dir() -> str:
    """Where the program writes: next to the exe, or %LOCALAPPDATA% for the
    Microsoft Store install (WindowsApps is read-only)."""
    try:
        from utils.paths import APP_DIR
        return APP_DIR
    except Exception:
        return BASE_DIR


def module_status(filepath: str):
    """(present, size in bytes or None) for one part of the program.

    In the exe and the Microsoft Store package the modules live inside the
    bundle, not as .py files, so checking for the file said MISSING for
    everything while all of it worked (2026-11-20). A module counts as
    present when Python can find it; the size is shown when a file exists."""
    import importlib.util
    full = os.path.join(BASE_DIR, filepath)
    if os.path.isfile(full):
        return True, os.path.getsize(full)
    if filepath.endswith(".py"):
        mod = filepath[:-3].replace("\\", "/").replace("/", ".")
        try:
            if importlib.util.find_spec(mod) is not None:
                return True, None
        except Exception:
            pass
    return False, None


PROGRAM_PARTS = [
    ("startup.py", "Entry point"),
    ("core/monitor.py", "System monitor"),
    ("core/scheduler.py", "Data scheduler"),
    ("core/logger.py", "CSV logger"),
    ("core/process_data_manager.py", "Process tracker"),
    ("hck_stats_engine/db_manager.py", "SQLite manager"),
    ("hck_stats_engine/aggregator.py", "Aggregation pipeline"),
    ("hck_stats_engine/process_aggregator.py", "Process aggregator"),
    ("hck_stats_engine/query_api.py", "Query API"),
    ("hck_stats_engine/events.py", "Event detector"),
    ("hck_stats_engine/constants.py", "Configuration"),
    ("ui/windows/main_window_expanded.py", "Main UI"),
]

# What the program reads besides its code (2026-11-20, "OTHERS")
OTHER_PARTS = [
    ("data/process_library.json", "Process library"),
    ("data/services_config.json", "Services config"),
    ("data/fonts/InterVariable.ttf", "Interface font"),
    ("data/icons/app_icon.png", "App icon"),
    ("locales/pl.json", "Polish texts"),
    ("locales/en.json", "English texts"),
    ("@db", "History database (writable)"),
]


def other_status(rel: str):
    """(present, size or None) for a data file; '@db' = the history
    database exists and its folder can be written."""
    if rel == "@db":
        try:
            folder = os.path.join(_data_dir(), "data", "logs")
            db = os.path.join(folder, "hck_stats.db")
            ok = os.path.isfile(db) and os.access(folder, os.W_OK)
            return ok, os.path.getsize(db) if ok else None
        except Exception:
            return False, None
    for base in _resource_dirs():
        full = os.path.join(base, rel)
        if os.path.isfile(full):
            return True, os.path.getsize(full)
    return False, None


def _resource_dirs():
    dirs = []
    try:
        from utils.paths import BUNDLE_DIR
        dirs.append(BUNDLE_DIR)
    except Exception:
        pass
    dirs.append(BASE_DIR)
    return dirs


def check_all():
    """[(group, path, present, size)] for every part, plus the missing ones."""
    rows = []
    for rel, _d in PROGRAM_PARTS:
        ok, size = module_status(rel)
        rows.append(("PROGRAM", rel, ok, size))
    for rel, _d in OTHER_PARTS:
        ok, size = other_status(rel)
        rows.append(("OTHERS", rel, ok, size))
    return rows


def _size_str(size):
    if size is None:
        return "bundled"
    return f"{size:,}B" if size < 10000 else f"{size // 1024}KB"


def _build_file_integrity_panel(parent):
    """FILE INTEGRITY CHECK with PROGRAM and OTHERS, a TEST button that
    re-checks each part (yellow CHECKING for 0.4-3 s, uneven on purpose so
    the statuses do not flip together) and a console with the run."""
    import random
    panel = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                     highlightbackground=BORDER)
    panel.pack(fill="x", pady=(0, 5))

    hdr = tk.Frame(panel, bg="#1e293b")
    hdr.pack(fill="x")
    tk.Label(hdr, text="FILE INTEGRITY CHECK", font=(_MONO, 8, "bold"),
             bg="#1e293b", fg="#10b981", padx=8, pady=4).pack(side="left")
    test_btn = tk.Label(hdr, text="TEST", font=(_MONO, 8, "bold"), bg="#065f46",
                        fg="#ffffff", padx=10, cursor="hand2")
    test_btn.pack(side="right", padx=6, pady=3)

    container = tk.Frame(panel, bg=PANEL)
    container.pack(fill="x", padx=6, pady=4)
    rows = {}
    for group, parts in (("PROGRAM", PROGRAM_PARTS), ("OTHERS", OTHER_PARTS)):
        tk.Label(container, text=group, font=(_MONO, 7, "bold"), bg=PANEL,
                 fg="#64748b", anchor="w").pack(fill="x", pady=(4, 1))
        for rel, desc in parts:
            row = tk.Frame(container, bg=PANEL)
            row.pack(fill="x")
            st = tk.Label(row, text="", font=(_MONO, 7, "bold"), width=8, padx=2)
            st.pack(side="left", padx=(0, 4))
            tk.Label(row, text=desc if rel == "@db" else rel.replace("\\", "/"),
                     font=(_MONO, 7), bg=PANEL, fg="#94a3b8", anchor="w").pack(side="left")
            sz = tk.Label(row, text="", font=(_MONO, 7), bg=PANEL, fg="#74839a")
            sz.pack(side="right", padx=4)
            rows[(group, rel)] = (st, sz)

    missing_lbl = tk.Label(panel, text="", font=(_MONO, 7, "bold"), bg=PANEL,
                           anchor="w", justify="left", wraplength=420)
    missing_lbl.pack(fill="x", padx=8, pady=(2, 2))
    console = tk.Text(panel, height=5, bg="#050810", fg="#94a3b8", font=(_MONO, 7),
                      bd=0, state="disabled", wrap="none")
    console.pack(fill="x", padx=6, pady=(0, 6))

    def _log(line):
        try:
            console.config(state="normal")
            console.insert("end", line + "\n")
            console.see("end")
            console.config(state="disabled")
        except Exception:
            pass

    def _paint(key, ok, size):
        st, sz = rows[key]
        st.config(text="OK" if ok else "MISSING", bg="#10b981" if ok else "#ef4444", fg="#000000")
        sz.config(text=_size_str(size) if ok else "")

    def _summary(results):
        missing = [rel for _g, rel, ok, _s in results if not ok]
        if missing:
            missing_lbl.config(text="Missing: " + ", ".join(
                ("history database" if m == "@db" else m) for m in missing), fg="#f87171")
        else:
            missing_lbl.config(text="All parts in place.", fg="#10b981")

    state = {"running": False}

    def _run_test(e=None):
        if state["running"]:
            return
        state["running"] = True
        test_btn.config(bg="#374151", cursor="arrow")
        results = check_all()
        t0 = time.time()
        _log(f"[{datetime.now():%H:%M:%S}] test started: {len(results)} parts")
        for _st, _sz in rows.values():
            _st.config(text="CHECKING", bg="#fbbf24", fg="#000000")
            _sz.config(text="")
        pending = {"n": len(results)}

        def _done_one(res):
            group, rel, ok, size = res
            _paint((group, rel), ok, size)
            name = "history database" if rel == "@db" else rel
            _log(f"  {'OK     ' if ok else 'MISSING'}  {name}  ({time.time() - t0:.1f} s)")
            pending["n"] -= 1
            if pending["n"] == 0:
                _summary(results)
                bad = sum(1 for r in results if not r[2])
                _log(f"[{datetime.now():%H:%M:%S}] done: {len(results) - bad} OK, {bad} missing")
                state["running"] = False
                test_btn.config(bg="#065f46", cursor="hand2")
        for res in results:
            panel.after(int(random.uniform(400, 3000)), lambda r=res: _done_one(r))

    test_btn.bind("<Button-1>", _run_test)
    first = check_all()
    for group, rel, ok, size in first:
        _paint((group, rel), ok, size)
    _summary(first)
    _log(f"[{datetime.now():%H:%M:%S}] {sum(1 for r in first if r[2])} of {len(first)} parts in place. TEST checks again.")


def _build_log_viewer_panel(parent):
    panel = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                     highlightbackground=BORDER)
    panel.pack(fill="both", expand=True, pady=(0, 0))

    hdr = tk.Frame(panel, bg="#1e293b")
    hdr.pack(fill="x")
    tk.Label(hdr, text="VIEW LOGS", font=(_MONO, 8, "bold"),
             bg="#1e293b", fg="#f59e0b", padx=8, pady=4).pack(side="left")

    log_text = tk.Text(panel, bg="#050810", fg="#94a3b8", font=(_MONO, 7),
                       bd=0, wrap="word", height=8, state="disabled",
                       insertbackground="#ffffff", selectbackground="#1e3a5f")
    log_text.pack(fill="both", expand=True, padx=4, pady=4)

    btn_frame = tk.Frame(panel, bg=PANEL)
    btn_frame.pack(fill="x", padx=4, pady=(0, 4))

    def load_raw_log():
        log_path = os.path.join(_data_dir(), "data", "logs", "raw_usage.csv")
        _load_log_file(log_text, log_path, tail=30)

    def load_minute_log():
        log_path = os.path.join(_data_dir(), "data", "logs", "minute_avg.csv")
        _load_log_file(log_text, log_path, tail=30)

    for text, cmd, color in [
        ("Raw CSV", load_raw_log, "#1e293b"),
        ("Minute AVG", load_minute_log, "#1e293b"),
    ]:
        btn = tk.Label(btn_frame, text=text, font=(_MONO, 7, "bold"),
                       bg=color, fg="#94a3b8", padx=8, pady=2, cursor="hand2")
        btn.pack(side="left", padx=2)
        btn.bind("<Button-1>", lambda e=None, c=cmd: c())
        btn.bind("<Enter>", lambda e=None, b=btn: b.config(bg="#334155"))
        btn.bind("<Leave>", lambda e=None, b=btn: b.config(bg="#1e293b"))


def _load_log_file(text_widget, filepath, tail=30):
    text_widget.config(state="normal")
    text_widget.delete("1.0", "end")

    if not os.path.isfile(filepath):
        text_widget.insert("end", f"File not found: {filepath}")
        text_widget.config(state="disabled")
        return

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        if len(lines) > tail:
            text_widget.insert("end", f"--- Showing last {tail} of {len(lines)} lines ---\n\n")
            lines = lines[-tail:]

        for line in lines:
            text_widget.insert("end", line)
    except Exception as e:
        text_widget.insert("end", f"Error reading file: {e}")

    text_widget.config(state="disabled")
    text_widget.see("end")


def _build_engine_status_panel(parent):
    panel = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                     highlightbackground=BORDER)
    panel.pack(fill="both", expand=True)

    hdr = tk.Frame(panel, bg="#1e293b")
    hdr.pack(fill="x")
    tk.Label(hdr, text="HCK STATS ENGINE STATUS", font=(_MONO, 8, "bold"),
             bg="#1e293b", fg="#3b82f6", padx=8, pady=4).pack(side="left")

    container = tk.Frame(panel, bg=PANEL)
    container.pack(fill="both", expand=True, padx=6, pady=4)

    db_ready = False
    db_path = ""
    db_size = 0
    minute_count = 0
    hourly_count = 0
    daily_count = 0
    process_hourly_count = 0
    event_count = 0
    last_minute_ts = None
    errors = []

    try:
        from hck_stats_engine.db_manager import db_manager
        db_ready = db_manager.is_ready
        db_path = db_manager._db_path

        if db_ready and os.path.isfile(db_path):
            db_size = os.path.getsize(db_path)

            conn = db_manager.get_connection()
            if conn:
                try:
                    minute_count = conn.execute("SELECT COUNT(*) FROM minute_stats").fetchone()[0]
                    hourly_count = conn.execute("SELECT COUNT(*) FROM hourly_stats").fetchone()[0]
                    daily_count = conn.execute("SELECT COUNT(*) FROM daily_stats").fetchone()[0]
                    process_hourly_count = conn.execute("SELECT COUNT(*) FROM process_hourly_stats").fetchone()[0]
                    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

                    row = conn.execute("SELECT MAX(timestamp) FROM minute_stats").fetchone()
                    if row and row[0]:
                        last_minute_ts = row[0]
                except Exception as e:
                    errors.append(str(e))
    except Exception as e:
        errors.append(f"Import error: {e}")

    _status_row(container, "Database", "READY" if db_ready else "OFFLINE",
                "#10b981" if db_ready else "#ef4444")

    if db_path:
        size_str = f"{db_size:,} bytes" if db_size < 100000 else f"{db_size // 1024} KB"
        _status_row(container, "DB Size", size_str, "#94a3b8")

    total_records = minute_count + hourly_count + daily_count + process_hourly_count + event_count
    _status_row(container, "Total Records", f"{total_records:,}", "#3b82f6")

    tk.Frame(container, bg=BORDER, height=1).pack(fill="x", pady=3)

    _status_row(container, "minute_stats", str(minute_count), "#94a3b8")
    _status_row(container, "hourly_stats", str(hourly_count), "#94a3b8")
    _status_row(container, "daily_stats", str(daily_count), "#94a3b8")
    _status_row(container, "process_hourly", str(process_hourly_count), "#94a3b8")
    _status_row(container, "events", str(event_count), "#94a3b8")

    tk.Frame(container, bg=BORDER, height=1).pack(fill="x", pady=3)

    if last_minute_ts:
        last_dt = datetime.fromtimestamp(last_minute_ts)
        elapsed = time.time() - last_minute_ts
        time_str = last_dt.strftime("%H:%M:%S")

        if elapsed < 120:
            write_status = "WORKS"
            write_color = "#10b981"
        elif elapsed < 600:
            write_status = "DELAYED"
            write_color = "#f59e0b"
        else:
            write_status = "STALE"
            write_color = "#ef4444"

        _status_row(container, "Last Write", time_str, "#94a3b8")
        _status_row(container, "Write Status", write_status, write_color)
    else:
        _status_row(container, "Last Write", "No data yet", "#6b7280")
        _status_row(container, "Write Status", "WAITING", "#f59e0b")

    if errors:
        tk.Frame(container, bg=BORDER, height=1).pack(fill="x", pady=3)
        tk.Label(container, text="ERRORS:", font=(_MONO, 7, "bold"),
                 bg=PANEL, fg="#ef4444", anchor="w").pack(fill="x")
        for err in errors[:3]:
            tk.Label(container, text=err[:60], font=(_MONO, 7),
                     bg=PANEL, fg="#ef4444", anchor="w", wraplength=250).pack(fill="x")


def _status_row(parent, label, value, value_color):
    row = tk.Frame(parent, bg=PANEL)
    row.pack(fill="x", pady=0)

    tk.Label(row, text=label, font=(_MONO, 7),
             bg=PANEL, fg="#8a97ab", anchor="w", width=16).pack(side="left")
    tk.Label(row, text=value, font=(_MONO, 7, "bold"),
             bg=PANEL, fg=value_color, anchor="e").pack(side="right")
