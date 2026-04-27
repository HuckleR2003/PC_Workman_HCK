"""
PC Workman Stability Tests Page
Real-time diagnostics: file integrity, HCK Stats Engine status, log viewer
"""

import tkinter as tk
import os
import time
import threading
from datetime import datetime


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
             font=("Segoe UI", 10, "bold"), bg="#10b981", fg="#000000",
             padx=10).pack(side="left", pady=4)

    back_btn = tk.Label(header, text="Back", font=("Segoe UI", 8, "bold"),
                        bg="#065f46", fg="#ffffff", padx=8, cursor="hand2")
    back_btn.pack(side="right", padx=10, pady=4)
    back_btn.bind("<Button-1>", lambda e: _go_back(self, parent))
    back_btn.bind("<Enter>", lambda e: back_btn.config(bg="#047857"))
    back_btn.bind("<Leave>", lambda e: back_btn.config(bg="#065f46"))

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


def _build_file_integrity_panel(parent):
    panel = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                     highlightbackground=BORDER)
    panel.pack(fill="x", pady=(0, 5))

    hdr = tk.Frame(panel, bg="#1e293b")
    hdr.pack(fill="x")
    tk.Label(hdr, text="FILE INTEGRITY CHECK", font=("Consolas", 8, "bold"),
             bg="#1e293b", fg="#10b981", padx=8, pady=4).pack(side="left")

    files_to_check = [
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

    container = tk.Frame(panel, bg=PANEL)
    container.pack(fill="x", padx=6, pady=4)

    for filepath, desc in files_to_check:
        full_path = os.path.join(BASE_DIR, filepath)
        exists = os.path.isfile(full_path)

        row = tk.Frame(container, bg=PANEL)
        row.pack(fill="x", pady=0)

        status_color = "#10b981" if exists else "#ef4444"
        status_text = "OK" if exists else "MISSING"

        tk.Label(row, text=status_text, font=("Consolas", 6, "bold"),
                 bg=status_color, fg="#000000", width=7, padx=2).pack(side="left", padx=(0, 4))

        name_short = filepath.replace("\\", "/")
        tk.Label(row, text=name_short, font=("Consolas", 6),
                 bg=PANEL, fg="#94a3b8", anchor="w").pack(side="left")

        if exists:
            size = os.path.getsize(full_path)
            size_str = f"{size:,}B" if size < 10000 else f"{size//1024}KB"
            tk.Label(row, text=size_str, font=("Consolas", 6),
                     bg=PANEL, fg="#475569").pack(side="right", padx=4)


def _build_log_viewer_panel(parent):
    panel = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                     highlightbackground=BORDER)
    panel.pack(fill="both", expand=True, pady=(0, 0))

    hdr = tk.Frame(panel, bg="#1e293b")
    hdr.pack(fill="x")
    tk.Label(hdr, text="VIEW LOGS", font=("Consolas", 8, "bold"),
             bg="#1e293b", fg="#f59e0b", padx=8, pady=4).pack(side="left")

    log_text = tk.Text(panel, bg="#050810", fg="#94a3b8", font=("Consolas", 7),
                       bd=0, wrap="word", height=8, state="disabled",
                       insertbackground="#ffffff", selectbackground="#1e3a5f")
    log_text.pack(fill="both", expand=True, padx=4, pady=4)

    btn_frame = tk.Frame(panel, bg=PANEL)
    btn_frame.pack(fill="x", padx=4, pady=(0, 4))

    def load_raw_log():
        log_path = os.path.join(BASE_DIR, "data", "logs", "raw_usage.csv")
        _load_log_file(log_text, log_path, tail=30)

    def load_minute_log():
        log_path = os.path.join(BASE_DIR, "data", "logs", "minute_avg.csv")
        _load_log_file(log_text, log_path, tail=30)

    for text, cmd, color in [
        ("Raw CSV", load_raw_log, "#1e293b"),
        ("Minute AVG", load_minute_log, "#1e293b"),
    ]:
        btn = tk.Label(btn_frame, text=text, font=("Consolas", 7, "bold"),
                       bg=color, fg="#94a3b8", padx=8, pady=2, cursor="hand2")
        btn.pack(side="left", padx=2)
        btn.bind("<Button-1>", lambda e, c=cmd: c())
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#334155"))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#1e293b"))


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
    tk.Label(hdr, text="HCK STATS ENGINE STATUS", font=("Consolas", 8, "bold"),
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
        tk.Label(container, text="ERRORS:", font=("Consolas", 7, "bold"),
                 bg=PANEL, fg="#ef4444", anchor="w").pack(fill="x")
        for err in errors[:3]:
            tk.Label(container, text=err[:60], font=("Consolas", 6),
                     bg=PANEL, fg="#ef4444", anchor="w", wraplength=250).pack(fill="x")


def _status_row(parent, label, value, value_color):
    row = tk.Frame(parent, bg=PANEL)
    row.pack(fill="x", pady=0)

    tk.Label(row, text=label, font=("Consolas", 7),
             bg=PANEL, fg="#64748b", anchor="w", width=16).pack(side="left")
    tk.Label(row, text=value, font=("Consolas", 7, "bold"),
             bg=PANEL, fg=value_color, anchor="e").pack(side="right")
