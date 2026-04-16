import tkinter as tk
import subprocess
import threading
import os
import tempfile

BG      = "#0a0e14"
CARD_BG = "#1a1d24"
BORDER  = "#2a2d34"


def build_optimization_page(self, parent):
    main = tk.Frame(parent, bg=BG)
    main.pack(fill="both", expand=True)

    canvas = tk.Canvas(main, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(main, orient="vertical", command=canvas.yview,
                      bg="#000000", troughcolor=BG, activebackground=CARD_BG, width=6)
    sf = tk.Frame(canvas, bg=BG)
    sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    win_id = canvas.create_window((0, 0), window=sf, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width - 2))

    def _mw(event):
        try:
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
    canvas.bind_all("<MouseWheel>", _mw, add="+")

    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    _build_audit_strip(sf)
    _build_turbo_section(sf)
    _build_auto_services_section(sf)


# ─────────────────────────────────────────────────────────────────────────────
# MINI CANVAS ICONS  (14×14 each)
# ─────────────────────────────────────────────────────────────────────────────

def _icon(parent, draw_fn, bg=CARD_BG, size=14):
    c = tk.Canvas(parent, width=size, height=size, bg=bg,
                  highlightthickness=0)
    draw_fn(c, size)
    return c


def _ico_power(c, s):
    # Power symbol: arc + vertical line
    c.create_arc(2, 3, s - 2, s - 1, start=50, extent=260,
                 style="arc", outline="#f59e0b", width=2)
    c.create_line(s // 2, 1, s // 2, s // 2 + 1, fill="#f59e0b", width=2)


def _ico_globe(c, s):
    # Globe: circle + horizontal latitude lines
    c.create_oval(1, 1, s - 1, s - 1, outline="#3b82f6", width=1)
    c.create_line(2, s // 2, s - 2, s // 2, fill="#3b82f6", width=1)
    c.create_line(3, s // 3, s - 3, s // 3, fill="#3b82f6", width=1)
    c.create_line(3, s * 2 // 3, s - 3, s * 2 // 3, fill="#3b82f6", width=1)


def _ico_trash(c, s):
    # Trash can
    c.create_rectangle(2, 4, s - 2, s - 1, outline="#ef4444", width=1)
    c.create_line(0, 4, s, 4, fill="#ef4444", width=1)
    c.create_rectangle(s // 2 - 2, 1, s // 2 + 2, 4, outline="#ef4444", width=1)
    for lx in [5, s - 5]:
        c.create_line(lx, 6, lx, s - 2, fill="#ef4444", width=1)


def _ico_arrow(c, s):
    # Upward arrow
    mid = s // 2
    c.create_polygon(mid, 1, s - 1, s // 2 + 1, s * 3 // 4, s // 2 + 1,
                     s * 3 // 4, s - 1, s // 4, s - 1, s // 4, s // 2 + 1,
                     1, s // 2 + 1, fill="#10b981", outline="")


# ─────────────────────────────────────────────────────────────────────────────
# PRE-OPTIMIZATION AUDIT  (competitive differentiator)
# ─────────────────────────────────────────────────────────────────────────────

def _build_audit_strip(parent):
    outer = tk.Frame(parent, bg="#0f1117",
                     highlightbackground="#1f2937", highlightthickness=1)
    outer.pack(fill="x", padx=10, pady=(8, 0))

    hdr = tk.Frame(outer, bg="#0f1117")
    hdr.pack(fill="x", padx=8, pady=(5, 3))
    tk.Label(hdr, text="SYSTEM STATE", font=("Segoe UI", 6, "bold"),
             bg="#0f1117", fg="#4b5563").pack(side="left")
    tk.Label(hdr, text="what TURBO BOOST will fix",
             font=("Segoe UI", 6), bg="#0f1117", fg="#1f2937").pack(side="left", padx=6)

    row = tk.Frame(outer, bg="#0f1117")
    row.pack(fill="x", padx=8, pady=(0, 5))

    # 4 live metric cells
    cells = {}
    labels_cfg = [
        ("power_plan", "Power Plan",   "#f59e0b"),
        ("temp_size",  "TEMP Folder",  "#ef4444"),
        ("ram_pct",    "RAM Usage",    "#3b82f6"),
        ("startup",    "Startup Items","#6b7280"),
    ]
    for key, title, color in labels_cfg:
        cell = tk.Frame(row, bg="#111827",
                        highlightbackground="#1f2937", highlightthickness=1)
        cell.pack(side="left", fill="both", expand=True, padx=2)
        tk.Label(cell, text=title, font=("Segoe UI", 5, "bold"),
                 bg="#111827", fg="#4b5563").pack(pady=(3, 0))
        val = tk.Label(cell, text="—", font=("Segoe UI", 8, "bold"),
                       bg="#111827", fg=color)
        val.pack()
        sub = tk.Label(cell, text=" ", font=("Segoe UI", 5),
                       bg="#111827", fg="#4b5563", pady=2)
        sub.pack()
        cells[key] = (val, sub)

    def _load_audit():
        results = {}

        # Power plan
        try:
            r = subprocess.run(["powercfg", "/getactivescheme"],
                               capture_output=True, text=True, timeout=4)
            line = r.stdout.strip()
            name = line[line.rfind("(") + 1:line.rfind(")")] if "(" in line else "Unknown"
            if "High Performance" in name or "Ultimate" in name:
                results["power_plan"] = (name[:14], "ok", "#10b981")
            else:
                results["power_plan"] = (name[:14], "needs fix", "#f59e0b")
        except Exception:
            results["power_plan"] = ("N/A", "", "#4b5563")

        # TEMP size
        try:
            total = 0
            td = tempfile.gettempdir()
            for entry in os.scandir(td):
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        for sub in os.scandir(entry.path):
                            try:
                                total += sub.stat().st_size
                            except Exception:
                                pass
                except Exception:
                    pass
            mb = total / (1024 * 1024)
            color = "#ef4444" if mb > 500 else "#f59e0b" if mb > 100 else "#10b981"
            sub_txt = "clear recommended" if mb > 100 else "clean"
            results["temp_size"] = (f"{mb:.0f} MB", sub_txt, color)
        except Exception:
            results["temp_size"] = ("N/A", "", "#4b5563")

        # RAM
        try:
            import psutil
            pct = psutil.virtual_memory().percent
            color = "#ef4444" if pct >= 85 else "#f59e0b" if pct >= 70 else "#10b981"
            results["ram_pct"] = (f"{pct:.0f}%", "high" if pct >= 70 else "ok", color)
        except Exception:
            results["ram_pct"] = ("N/A", "", "#4b5563")

        # Startup count
        try:
            import winreg
            count = 0
            for hive, path in [
                (winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]:
                try:
                    key = winreg.OpenKey(hive, path)
                    i = 0
                    while True:
                        try:
                            winreg.EnumValue(key, i)
                            count += 1
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    pass
            color = "#ef4444" if count > 12 else "#f59e0b" if count > 8 else "#10b981"
            results["startup"] = (str(count), "items", color)
        except Exception:
            results["startup"] = ("N/A", "", "#4b5563")

        # Push to UI
        for key, (val_lbl, sub_lbl) in cells.items():
            if key in results:
                txt, sub, col = results[key]
                if val_lbl.winfo_exists():
                    val_lbl.after(0, lambda v=val_lbl, t=txt, c=col: v.config(text=t, fg=c))
                if sub_lbl.winfo_exists():
                    sub_lbl.after(0, lambda s=sub_lbl, t=sub: s.config(text=t))

    threading.Thread(target=_load_audit, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# TURBO BOOST
# ─────────────────────────────────────────────────────────────────────────────

def _sec_hdr(parent, text):
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x", padx=10, pady=(8, 2))
    tk.Label(row, text=text, font=("Segoe UI", 6, "bold"),
             bg=BG, fg="#4b5563").pack(side="left")
    tk.Frame(row, bg="#1f2937", height=1).pack(side="left", fill="x", expand=True, padx=6)


def _build_turbo_section(parent):
    _sec_hdr(parent, "TURBO BOOST")

    # Create status label early (packed after action cards)
    status_frame = tk.Frame(parent, bg="#0f1117",
                            highlightbackground=BORDER, highlightthickness=1)
    status_lbl = tk.Label(status_frame, text=" ", font=("Segoe UI", 7),
                          bg="#0f1117", fg="#94a3b8", pady=3, padx=8, anchor="w")
    status_lbl.pack(fill="x")

    # ── Big ACTIVATE TURBO BOOST button ──────────────────────
    turbo_outer = tk.Frame(parent, bg=BORDER,
                           highlightbackground=BORDER, highlightthickness=1)
    turbo_outer.pack(fill="x", padx=10, pady=(2, 0))

    turbo_canvas = tk.Canvas(turbo_outer, height=44, bg=CARD_BG,
                             highlightthickness=0, cursor="hand2")
    turbo_canvas.pack(fill="x")

    def _lerp(c1, c2, t):
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    def _draw_turbo(bright=1.0):
        turbo_canvas.delete("all")
        w = turbo_canvas.winfo_width() or 400
        h = 44
        for x in range(0, w, 2):
            r, g, b = _lerp((152, 72, 6), (202, 150, 7), x / max(w - 1, 1))
            r = min(255, int(r * bright))
            g = min(255, int(g * bright))
            b = min(255, int(b * bright))
            turbo_canvas.create_rectangle(x, 0, x + 2, h,
                                          fill=f"#{r:02x}{g:02x}{b:02x}", outline="")
        turbo_canvas.create_text(w // 2, h // 2,
                                 text="ACTIVATE TURBO BOOST",
                                 font=("Segoe UI", 10, "bold"),
                                 fill="#000000")

    turbo_canvas.bind("<Configure>", lambda e: _draw_turbo())
    turbo_canvas.bind("<Enter>",     lambda e: _draw_turbo(1.2))
    turbo_canvas.bind("<Leave>",     lambda e: _draw_turbo(1.0))
    turbo_canvas.bind("<Button-1>",
                      lambda e: threading.Thread(
                          target=lambda: _do_turbo_all(status_lbl), daemon=True
                      ).start())

    # Hint pills: what TURBO runs
    hint_row = tk.Frame(parent, bg=BG)
    hint_row.pack(fill="x", padx=10, pady=(3, 6))
    for label in ["Power Plan", "Flush DNS", "Clear TEMP", "Boost Priority"]:
        pill = tk.Frame(hint_row, bg="#1f2937")
        pill.pack(side="left", padx=2)
        tk.Label(pill, text=label, font=("Segoe UI", 6),
                 bg="#1f2937", fg="#4b5563", padx=5, pady=1).pack()

    # ── 4 individual action cards ─────────────────────────────
    _sec_hdr(parent, "INDIVIDUAL ACTIONS")

    actions_frame = tk.Frame(parent, bg=BG)
    actions_frame.pack(fill="x", padx=10, pady=(2, 4))

    actions = [
        (_ico_power, "High Performance\nPlan", "#f59e0b", _set_high_performance),
        (_ico_globe, "Flush DNS",              "#3b82f6", _flush_dns),
        (_ico_trash, "Clear TEMP\nFiles",      "#ef4444", _clear_temp),
        (_ico_arrow, "Boost\nPriority",        "#10b981", _boost_priority),
    ]

    for draw_fn, lbl, color, func in actions:
        col = tk.Frame(actions_frame, bg=CARD_BG,
                       highlightbackground=BORDER, highlightthickness=1)
        col.pack(side="left", fill="both", expand=True, padx=2)

        # Thin colored top bar
        tk.Frame(col, bg=color, height=2).pack(fill="x")

        ico = _icon(col, draw_fn, bg=CARD_BG, size=16)
        ico.pack(pady=(8, 2))

        tk.Label(col, text=lbl, font=("Segoe UI", 7, "bold"),
                 bg=CARD_BG, fg="#e2e8f0", justify="center").pack(pady=(0, 4))

        run_btn = tk.Label(col, text="RUN", font=("Segoe UI", 6, "bold"),
                           bg="#0f1117", fg=color, cursor="hand2",
                           padx=10, pady=2,
                           highlightbackground=color, highlightthickness=1)
        run_btn.pack(pady=(0, 8))

        def _make_handler(f, btn, col_color):
            def _h(e=None):
                btn.config(text="...", fg="#6b7280",
                           highlightbackground="#6b7280")
                def _run():
                    ok, msg = f()
                    label_text = "DONE" if ok else "FAIL"
                    label_color = "#10b981" if ok else "#ef4444"
                    if btn.winfo_exists():
                        btn.after(0, lambda: btn.config(
                            text=label_text, fg=label_color,
                            highlightbackground=label_color
                        ))
                    if status_lbl.winfo_exists():
                        status_lbl.after(0, lambda: status_lbl.config(text=msg))
                    import time
                    time.sleep(3)
                    if btn.winfo_exists():
                        btn.after(0, lambda: btn.config(
                            text="RUN", fg=col_color,
                            highlightbackground=col_color
                        ))
                threading.Thread(target=_run, daemon=True).start()
            return _h

        run_btn.bind("<Button-1>", _make_handler(func, run_btn, color))
        run_btn.bind("<Enter>",  lambda e, b=run_btn, c=color: b.config(fg="#ffffff"))
        run_btn.bind("<Leave>",  lambda e, b=run_btn, c=color: b.config(fg=c))

    # Pack status bar after action cards
    status_frame.pack(fill="x", padx=10, pady=(2, 2))


# ─────────────────────────────────────────────────────────────────────────────
# ACTION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _do_turbo_all(status_lbl):
    steps = [
        (_set_high_performance, "Power"),
        (_flush_dns,            "DNS"),
        (_clear_temp,           "TEMP"),
        (_boost_priority,       "Priority"),
    ]
    results = []
    for func, name in steps:
        ok, _ = func()
        results.append(f"{'OK' if ok else 'FAIL'}  {name}")
    summary = "   |   ".join(results)
    if status_lbl.winfo_exists():
        status_lbl.after(0, lambda: status_lbl.config(text=summary))


def _set_high_performance():
    try:
        r = subprocess.run(
            ["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            return True, "High Performance power plan activated."
        return False, f"powercfg failed: {r.stderr.strip()[:60]}"
    except Exception as ex:
        return False, str(ex)[:60]


def _flush_dns():
    try:
        r = subprocess.run(["ipconfig", "/flushdns"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return True, "DNS cache flushed."
        return False, f"ipconfig error: {r.stderr.strip()[:60]}"
    except Exception as ex:
        return False, str(ex)[:60]


def _clear_temp():
    import shutil
    removed = 0
    try:
        temp_dir = tempfile.gettempdir()
        for name in os.listdir(temp_dir):
            path = os.path.join(temp_dir, name)
            try:
                if os.path.isfile(path):
                    os.unlink(path)
                    removed += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    removed += 1
            except Exception:
                pass
        return True, f"Cleared {removed} temp items."
    except Exception as ex:
        return False, str(ex)[:60]


def _boost_priority():
    try:
        import psutil
        fg_pid = None
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            fg_pid = pid.value
        except Exception:
            pass
        if fg_pid and fg_pid > 4:
            proc = psutil.Process(fg_pid)
            proc.nice(psutil.HIGH_PRIORITY_CLASS)
            return True, f"Priority boosted: {proc.name()[:24]} (PID {fg_pid})."
        return False, "No foreground process detected."
    except Exception as ex:
        return False, str(ex)[:60]


# ─────────────────────────────────────────────────────────────────────────────
# AUTO SERVICES  —  compact strip
# ─────────────────────────────────────────────────────────────────────────────

def _build_auto_services_section(parent):
    outer = tk.Frame(parent, bg="#0d1117",
                     highlightbackground="#1f2937", highlightthickness=1)
    outer.pack(fill="x", padx=10, pady=(4, 10))

    # Header row
    hdr = tk.Frame(outer, bg="#0d1117")
    hdr.pack(fill="x", padx=8, pady=(5, 3))
    tk.Label(hdr, text="AUTO SERVICES", font=("Segoe UI", 6, "bold"),
             bg="#0d1117", fg="#374151").pack(side="left")
    tk.Label(hdr, text="—  autonomous background operations",
             font=("Segoe UI", 6), bg="#0d1117", fg="#1f2937").pack(side="left", padx=4)
    tk.Label(hdr, text="IN DEVELOPMENT", font=("Segoe UI", 6, "bold"),
             bg="#1e3a5f", fg="#3b5a8a", padx=6, pady=1).pack(side="right")

    tk.Frame(outer, bg="#1f2937", height=1).pack(fill="x", padx=8)

    # RAM Optimizer — featured, greyed
    ram_row = tk.Frame(outer, bg="#0d1117")
    ram_row.pack(fill="x", padx=8, pady=(4, 2))

    dot = tk.Frame(ram_row, bg="#1f2937", width=6, height=6)
    dot.pack(side="left", padx=(0, 6))

    tk.Label(ram_row, text="RAM Optimizer", font=("Segoe UI", 7, "bold"),
             bg="#0d1117", fg="#374151").pack(side="left")
    tk.Label(ram_row, text="auto-triggers at >75% usage",
             font=("Segoe UI", 6), bg="#0d1117", fg="#1f2937").pack(side="left", padx=6)
    tk.Label(ram_row, text="#20", font=("Segoe UI", 6),
             bg="#0d1117", fg="#1e3a5f").pack(side="right")

    tk.Frame(outer, bg="#111827", height=1).pack(fill="x", padx=8, pady=(2, 3))

    # Compact 2-column list
    coming = [
        "CPU thermal throttle prevention",
        "Browser cache auto-cleaner",
        "Startup optimizer (weekly)",
        "Background process limiter",
        "Disk fragmentation monitor",
        "Network adapter reset on timeout",
        "Registry junk cleaner",
        "GPU driver health watchdog",
        "Log file rotation & archive",
        "DNS auto-flush (nightly)",
        "Weekly performance report",
        "Windows Update checker",
        "Firewall health monitor",
        "Game mode auto-activator",
    ]

    grid = tk.Frame(outer, bg="#0d1117")
    grid.pack(fill="x", padx=8, pady=(0, 5))

    mid = len(coming) // 2
    for col_idx, items in enumerate([coming[:mid], coming[mid:]]):
        col_frame = tk.Frame(grid, bg="#0d1117")
        col_frame.pack(side="left", fill="both", expand=True)
        for item in items:
            row = tk.Frame(col_frame, bg="#0d1117")
            row.pack(fill="x", pady=0)
            tk.Frame(row, bg="#1f2937", width=4, height=4).pack(
                side="left", padx=(0, 5))
            tk.Label(row, text=item, font=("Segoe UI", 6),
                     bg="#0d1117", fg="#1f2937", anchor="w").pack(
                side="left", fill="x", expand=True)
