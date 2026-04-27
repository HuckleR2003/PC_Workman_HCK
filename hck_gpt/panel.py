# hck_gpt/panel.py

import tkinter as tk
from tkinter import ttk
from ui.theme import THEME
import os
import time
import re 

try:
    from hck_gpt.chat_handler import ChatHandler
    HAS_CHAT_HANDLER = True
except ImportError:
    HAS_CHAT_HANDLER = False
    print("[hck_GPT] ChatHandler not available")

try:
    from hck_gpt.memory.proactive_monitor import proactive_monitor
    HAS_PROACTIVE = True
except Exception:
    HAS_PROACTIVE = False

# process library and tooltip
try:
    from hck_gpt.process_library import process_library
    from hck_gpt.tooltip import ProcessTooltip
    HAS_PROCESS_LIBRARY = True
except ImportError:
    HAS_PROCESS_LIBRARY = False
    print("[hck_GPT] Process library not available")

SEND_ICON = "data/icons/send_hck.png"


class HCKGPTPanel:
    def __init__(self, parent, width, collapsed_h=34, expanded_h=280, max_h=420):
        self.parent = parent
        self.width = width
        self.collapsed_h = collapsed_h
        self.expanded_h = expanded_h
        self.max_h = max_h
        self.total_h = collapsed_h + expanded_h
        self.current_mode = "normal"  # normal, maximized

        self.is_open = False
        self.animating = False
        self.after_id = None
        self.cursor_visible = True

        # Insight ticker state
        self._ticker_id = None
        self._last_greeting_session = 0
        self._banner_ticker_id = None

        # First hck_GPT: message gets brand badge ("hck_GPT" label) instead of time
        self._brand_badge_once = True

        # UI language: "auto" | "en" | "pl"  (default = English)
        self._ui_lang = "en"

        # chat handler
        self.chat_handler = ChatHandler() if HAS_CHAT_HANDLER else None

        # tooltip system
        self.tooltip = ProcessTooltip(parent) if HAS_PROCESS_LIBRARY else None

        # Proactive monitor — register thread-safe callbacks, then start
        if HAS_PROACTIVE:
            try:
                # push: injects alert messages into chat (thread-safe via after())
                proactive_monitor.register_push(
                    lambda msg: parent.after(0, lambda m=msg: self.add_message(m))
                )
                # banner: updates the banner text silently (thread-safe via after())
                proactive_monitor.register_banner(
                    lambda status: parent.after(
                        0, lambda s=status: self._set_banner_status(s)
                    )
                )
                proactive_monitor.start()
            except Exception:
                pass

        # MAIN PANEL — starts off-screen below, slides up via _animate_initial_appearance()
        self.frame = tk.Frame(parent, bg=THEME["bg_panel"])
        self.frame.place(x=0, y=800, width=self.width, height=0)

        # ========== BANNER GRADIENT ==========
        self.banner = tk.Canvas(
            self.frame,
            height=self.collapsed_h,
            bd=0,
            highlightthickness=0
        )
        self.banner.pack(side="top", fill="x")

        self._draw_gradient_banner()

        # Left accent pulse bar (3px, UI layer — animated via itemconfig)
        self._left_bar = self.banner.create_rectangle(
            0, 0, 3, self.collapsed_h, fill="#7a0f20", outline="", tags="ui"
        )

        # AI badge (bordeaux square, left side)
        _bx = 10
        _by = self.collapsed_h // 2 - 9
        self.banner.create_rectangle(_bx, _by, _bx + 22, _by + 18,
                                      fill="#5c0f1a", outline="", tags="ui")
        self.banner.create_text(_bx + 11, _by + 9, text="AI",
                                 font=("Segoe UI Black", 7),
                                 fill="#ffffff", anchor="center", tags="ui")

        # Main text
        self.banner_text = self.banner.create_text(
            42, self.collapsed_h // 2,
            anchor="w",
            text="hck_GPT  —  Your PC Companion",
            font=("Segoe UI", 9, "bold"),
            fill="#f0dde0",
            tags="ui"
        )

        # ONLINE badge: dark bordeaux rect + pulsing light-red text (right side)
        _oy = self.collapsed_h // 2
        _obx1 = self.width - 64
        _obx2 = self.width - 22
        self._online_rect = self.banner.create_rectangle(
            _obx1, _oy - 7, _obx2, _oy + 7,
            fill="#1e0508", outline="#5c0f1a", tags="ui"
        )
        self._online_lbl = self.banner.create_text(
            (_obx1 + _obx2) // 2, _oy,
            anchor="center",
            text="ONLINE",
            font=("Segoe UI", 7, "bold"),
            fill="#ff5566",
            tags="ui"
        )

        # Arrow indicator
        self.banner_arrow = self.banner.create_text(
            self.width - 8, self.collapsed_h // 2,
            anchor="e",
            text="▼",
            font=("Arial", 9),
            fill="#c0182a",
            tags="ui"
        )

        # Hover effects
        self.banner.bind("<Enter>", self._on_banner_enter)
        self.banner.bind("<Leave>", self._on_banner_leave)
        self.banner.bind("<Button-1>", self.toggle)

        # Start Bordeaux living animation
        self._start_banner_sweep()

        # Slide panel up from bottom on startup (0.7 s ease-out, 350 ms delay)
        parent.after(350, lambda: self._animate(0, self.collapsed_h, duration_ms=700))

        # ========== CHAT AREA ==========
        self.chat = tk.Frame(self.frame, bg=THEME["bg_panel"])

        control_bar = tk.Frame(self.chat, bg=THEME["bg_panel"])
        control_bar.pack(fill="x", padx=8, pady=(8, 4))

        service_btn = tk.Button(
            control_bar,
            text="🔧 Service Setup",
            bg=THEME["bg_main"],
            fg=THEME["accent"],
            activebackground=THEME["accent2"],
            activeforeground=THEME["text"],
            font=("Consolas", 9, "bold"),
            bd=0,
            padx=10,
            pady=4,
            command=self._start_service_setup,
            cursor="hand2"
        )
        service_btn.pack(side="left", padx=(0, 4))

        self.expand_btn = tk.Button(
            control_bar,
            text="⬜ Maximize",
            bg=THEME["bg_main"],
            fg=THEME["muted"],
            activebackground=THEME["accent2"],
            activeforeground=THEME["text"],
            font=("Consolas", 9),
            bd=0,
            padx=10,
            pady=4,
            command=self._toggle_maximize,
            cursor="hand2"
        )
        self.expand_btn.pack(side="left", padx=(0, 4))

        clear_btn = tk.Button(
            control_bar,
            text="🗑 Clear",
            bg=THEME["bg_main"],
            fg=THEME["muted"],
            activebackground=THEME["accent2"],
            activeforeground=THEME["text"],
            font=("Consolas", 9),
            bd=0,
            padx=8,
            pady=4,
            command=self.clear_chat,
            cursor="hand2"
        )
        clear_btn.pack(side="right")

        lang_btn = tk.Button(
            control_bar,
            text="Languages",
            bg="#111520",
            fg="#6b7280",
            activebackground="#1a1d28",
            activeforeground="#9ca3af",
            font=("Consolas", 9),
            bd=0,
            padx=10,
            pady=4,
            command=self._show_language_popup,
            cursor="hand2",
            highlightbackground="#2a3040",
            highlightthickness=1,
        )
        lang_btn.pack(side="right", padx=(0, 6))

        report_btn = tk.Button(
            control_bar,
            text="Today Report",
            bg=THEME["bg_main"],
            fg=THEME["accent2"],
            activebackground=THEME["accent2"],
            activeforeground=THEME["text"],
            font=("Consolas", 9, "bold"),
            bd=0,
            padx=10,
            pady=4,
            command=self._run_today_report,
            cursor="hand2"
        )
        report_btn.pack(side="left", padx=(0, 4))

        log_container = tk.Frame(self.chat, bg=THEME["bg_panel"])
        log_container.pack(fill="both", expand=True, padx=8, pady=(4, 6))

        scrollbar = tk.Scrollbar(log_container, bg=THEME["bg_main"],
                                troughcolor=THEME["bg_panel"],
                                activebackground=THEME["accent2"],
                                width=8, bd=0)
        scrollbar.pack(side="right", fill="y")

        self.log = tk.Text(
            log_container,
            bg=THEME["bg_panel"],
            fg=THEME["text"],
            bd=0,
            wrap="word",
            font=("Consolas", 10),
            height=10,
            yscrollcommand=scrollbar.set
        )
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log.yview)
        self.log.config(state="disabled")
        self._bind_process_tooltips()

        self.log.tag_configure("accent", foreground=THEME["accent"])
        self.log.tag_configure("accent_bold", foreground=THEME["accent"],
                               font=("Consolas", 10, "bold"))
        self.log.tag_configure("cpu", foreground="#d94545")
        self.log.tag_configure("gpu", foreground="#4b9aff")
        self.log.tag_configure("ram", foreground="#ffd24a")
        self.log.tag_configure("purple", foreground="#a855f7")
        self.log.tag_configure("green", foreground="#22c55e")
        self.log.tag_configure("red", foreground="#ef4444")
        self.log.tag_configure("yellow", foreground="#fbbf24")
        self.log.tag_configure("yellow_bold", foreground="#fbbf24",
                               font=("Consolas", 10, "bold"))
        self.log.tag_configure("muted", foreground=THEME["muted"])
        self.log.tag_configure("bold", foreground=THEME["text"],
                               font=("Consolas", 10, "bold"))
        self.log.tag_configure("header", foreground=THEME["accent"],
                               font=("Consolas", 10, "bold"),
                               underline=True)
        self.log.tag_configure("divider", foreground="#2a2d34")
        self.log.tag_configure("teal", foreground="#2dd4bf")
        self.log.tag_configure("orange", foreground="#f97316")
        self.log.tag_configure("light_purple", foreground="#c084fc")
        self.log.tag_configure("tip_block")  # tracking tag — no visual change

        entry_container = tk.Frame(self.chat, bg=THEME["bg_panel"])
        entry_container.pack(fill="x", padx=8, pady=(0, 10))

        entry_wrapper = tk.Frame(entry_container, bg=THEME["accent2"], bd=0)
        entry_wrapper.pack(fill="x", side="left", expand=True)

        entry_inner = tk.Frame(entry_wrapper, bg=THEME["bg_main"])
        entry_inner.pack(fill="both", expand=True, padx=1, pady=1)

        self.entry = tk.Entry(
            entry_inner,
            bg=THEME["bg_main"],
            fg=THEME["accent"],
            bd=0,
            insertbackground=THEME["accent"],
            font=("Consolas", 11)
        )
        self.entry.pack(fill="both", expand=True, padx=8, pady=6)
        self.entry.bind("<Return>", lambda e: self._send())

        self.entry.bind("<FocusIn>", lambda e: entry_wrapper.config(bg=THEME["accent"]))
        self.entry.bind("<FocusOut>", lambda e: entry_wrapper.config(bg=THEME["accent2"]))

        self._start_cursor_blink()

        send_wrapper = tk.Frame(entry_container, bg=THEME["accent2"])
        send_wrapper.pack(side="right", padx=(8, 0))

        try:
            self.send_img = tk.PhotoImage(file=SEND_ICON)
            self.send_btn = tk.Button(
                send_wrapper,
                image=self.send_img,
                bg=THEME["bg_main"],
                activebackground=THEME["accent2"],
                bd=0,
                command=self._send,
                cursor="hand2"
            )
        except:
            self.send_btn = tk.Button(
                send_wrapper,
                text="⬆",
                bg=THEME["bg_main"],
                fg=THEME["accent"],
                activebackground=THEME["accent2"],
                activeforeground=THEME["text"],
                font=("Arial", 12, "bold"),
                bd=0,
                padx=12,
                pady=4,
                command=self._send,
                cursor="hand2"
            )
        self.send_btn.pack(padx=1, pady=1)

        self._welcome()

        self._start_banner_ticker()

        parent.bind("<Configure>", self._on_resize)

    # BORDEAUX NOIR GRADIENT BANNER (black → deep crimson, living shimmer)
    def _draw_gradient_banner(self, phase=0.0):
        """Redraws gradient strips with sine-wave shimmer. Tagged 'grad' — UI layer raised on top."""
        import math
        w = self.width
        h = self.collapsed_h

        self.banner.delete("grad")

        anchors = [
            (0.00, (0,   0,   0)),    # Pure black
            (0.18, (10,  1,   3)),    # Black with crimson ghost
            (0.45, (42,  6,   14)),   # Very dark bordeaux
            (0.75, (85,  11,  22)),   # Dark crimson
            (1.00, (118, 16,  32)),   # Deep bordeaux
        ]

        strip_w = 5
        for x in range(0, w, strip_w):
            t = x / max(w - 1, 1)
            r, g, b = anchors[-1][1]
            for j in range(len(anchors) - 1):
                if anchors[j][0] <= t <= anchors[j + 1][0]:
                    seg_t = (t - anchors[j][0]) / (anchors[j + 1][0] - anchors[j][0])
                    c0, c1 = anchors[j][1], anchors[j + 1][1]
                    r = int(c0[0] + (c1[0] - c0[0]) * seg_t)
                    g = int(c0[1] + (c1[1] - c0[1]) * seg_t)
                    b = int(c0[2] + (c1[2] - c0[2]) * seg_t)
                    break

            # Living shimmer: broad sine wave travelling across the gradient
            shimmer = (math.sin(t * 5.0 + phase) + 1) / 2 * 0.16
            r = min(255, int(r + shimmer * 90))
            g = min(255, int(g + shimmer * 9))
            b = min(255, int(b + shimmer * 14))

            self.banner.create_rectangle(x, 0, x + strip_w + 1, h,
                                          fill=f"#{r:02x}{g:02x}{b:02x}",
                                          outline=f"#{r:02x}{g:02x}{b:02x}",
                                          tags="grad")

        # Bottom crimson border (1px)
        self.banner.create_rectangle(0, h - 1, w, h, fill="#9b1630", outline="", tags="grad")

        # Keep UI items (badge, text, arrow) on top of fresh gradient
        self.banner.tag_raise("ui")

    # BORDEAUX LIVING ANIMATION (shimmer + pulse, no moving lines)
    def _start_banner_sweep(self):
        """Initialize Bordeaux Noir living animation."""
        self._sweep_phase = 0.0
        self._left_bar_phase = 0.0
        self._online_pulse_phase = 0.0
        self._do_banner_sweep()

    def _do_banner_sweep(self):
        """Animation tick: gradient shimmer wave, left bar pulse, ONLINE text pulse."""
        import math
        try:
            if not self.banner.winfo_exists():
                return
        except Exception:
            return

        # Advance shimmer phase — sine wave travels across gradient (~6 s full cycle)
        self._sweep_phase = (self._sweep_phase + 0.105) % (math.pi * 20)
        self._draw_gradient_banner(phase=self._sweep_phase)

        # Left accent bar pulse (dark bordeaux ↔ medium crimson)
        self._left_bar_phase = (self._left_bar_phase + 0.09) % (2 * math.pi)
        p = (math.sin(self._left_bar_phase) + 1) / 2
        br = int(0x7a + p * (0xc0 - 0x7a))
        bg_ = int(0x0f + p * (0x18 - 0x0f))
        bb = int(0x20 + p * (0x2a - 0x20))
        self.banner.itemconfig(self._left_bar, fill=f"#{br:02x}{bg_:02x}{bb:02x}")

        # ONLINE text pulse (dark red ↔ bright crimson)
        self._online_pulse_phase = (self._online_pulse_phase + 0.07) % (2 * math.pi)
        op = (math.sin(self._online_pulse_phase) + 1) / 2
        o_r = int(0xcc + op * (0xff - 0xcc))
        o_g = int(0x20 + op * (0x66 - 0x20))
        o_b = int(0x30 + op * (0x55 - 0x30))
        self.banner.itemconfig(self._online_lbl, fill=f"#{o_r:02x}{o_g:02x}{o_b:02x}")

        try:
            self.banner.after(100, self._do_banner_sweep)
        except Exception:
            pass

    # HOVER EFFECTS
    def _on_banner_enter(self, event=None):
        self.banner.itemconfig(self.banner_text, fill="#ffffff")
        self.banner.itemconfig(self.banner_arrow, fill="#e8253f")

    def _on_banner_leave(self, event=None):
        self.banner.itemconfig(self.banner_text, fill="#f0dde0")
        self.banner.itemconfig(self.banner_arrow, fill="#c0182a")

    # WELCOME MESSAGES
    def _welcome(self):
        import threading as _threading

        # ── Session hours (quick sync read — DB is ready before panel init) ──
        session_suffix = ""
        try:
            from hck_stats_engine.query_api import query_api as _qapi
            _s = _qapi.get_summary_stats(days=9999)
            _hrs = _s.get("total_uptime_hours", 0) if _s else 0
            if _hrs >= 1:
                session_suffix = f"  Session: {_hrs:.0f}h"
            elif _hrs > 0:
                session_suffix = f"  Session: {int(_hrs * 60)}m"
        except Exception:
            pass

        # ── First message: brand badge ("hck_GPT") + welcome + session ──
        self.add_message(
            f"hck_GPT: Welcome back \u2014 PC Workman is armed and ready.{session_suffix}"
        )
        self.add_message("")
        # ── 3-column table (Commands | Quick check | OPERATIONS) ──────────
        self._add_welcome_tables()

        # Prevent auto-greeting from firing when panel first opens
        self._last_greeting_session = time.time()

        # ── Async: time-of-day greeting + yesterday's stats ──
        _threading.Thread(target=self._add_startup_quip, daemon=True).start()

    def _add_welcome_tables(self):
        """
        3-column welcome table rendered directly in the log widget
        so each title gets its own color tag:
          Commands     → teal
          Quick check  → orange
          OPERATIONS   → light_purple

        Column widths (chars):
          Commands:    outer=28  inner=26
          Quick check: outer=22  inner=20
          OPERATIONS:  outer=28  inner=26
          Separator:   2 spaces each
          Total:       82 chars / line
        """
        try:
            if not self.log.winfo_exists():
                return
        except Exception:
            return

        # ── content rows (inner widths: 26 | 20 | 26) ─────────────────────
        rows = [
            ("  stats · alerts · report ", "  cpu · ram · gpu   ", "  reset         wipe db   "),
            ("  temp  · health · uptime ", "  disk  ·  mb       ", "  svc reset   restore svcs"),
            ("  optimization  · commands", "                    ", "  turbo           [soon]  "),
        ]

        def _w(text, tag=None):
            if tag:
                self.log.insert("end", text, tag)
            else:
                self.log.insert("end", text)

        self.log.config(state="normal")

        # ── top border with colored titles ────────────────────────────────
        _w("┌─ ");           _w("Commands",    "teal")
        _w(" ───────────────┐  ┌─ ")
        _w("Quick check",   "orange")
        _w(" ──────┐  ┌─ ")
        _w("OPERATIONS",    "light_purple")
        _w(" ─────────────┐\n")

        # ── content rows ──────────────────────────────────────────────────
        for cmd, qc, ops in rows:
            _w(f"│{cmd}│  │{qc}│  │{ops}│\n")

        # ── bottom border ─────────────────────────────────────────────────
        _w("└──────────────────────────┘  └────────────────────┘  └──────────────────────────┘\n")

        self.log.see("end")
        self.log.config(state="disabled")

    def _add_startup_quip(self):
        """
        Background thread:
          1) Time-of-day greeting  → hck_GPT: Good morning! / Good afternoon! / Good evening!
          2) Yesterday summary     → CPU avg % + heaviest long-running app
        """
        from datetime import datetime as _dt, timedelta as _td

        # ── Greeting by hour ──────────────────────────────────────────────────
        hour = _dt.now().hour
        if 5 <= hour < 12:
            greeting = "Good morning!"
        elif 12 <= hour < 18:
            greeting = "Good afternoon!"
        elif 18 <= hour < 22:
            greeting = "Good evening!"
        else:
            greeting = "Late night session — respect."

        # ── Yesterday's data ─────────────────────────────────────────────────
        cpu_avg  = None
        top_app  = None

        try:
            from hck_stats_engine.query_api import query_api as _qapi

            # Overall avg for the last 24 h
            summary = _qapi.get_summary_stats(days=1)
            if summary:
                cpu_avg = summary.get("cpu_avg")

            # Yesterday's heaviest + longest process
            # Score = cpu_avg × total_active_seconds (impact × duration)
            yesterday_str = (_dt.now() - _td(days=1)).strftime("%Y-%m-%d")
            rows = _qapi.get_process_daily_breakdown(yesterday_str, top_n=10)
            if rows:
                def _score(r):
                    return (r.get("cpu_avg") or 0) * (r.get("total_active_seconds") or 0)
                best = max(rows, key=_score)
                raw = best.get("display_name") or best.get("process_name") or ""
                top_app = raw.replace(".exe", "").strip() or None
        except Exception:
            pass

        # ── Build messages ────────────────────────────────────────────────────
        msg1 = f"hck_GPT: {greeting}"

        if cpu_avg is not None and top_app:
            msg2 = (
                f"hck_GPT: Yesterday \u2014 CPU averaged {cpu_avg:.0f}%. "
                f"Longest & heaviest: {top_app}."
            )
        elif cpu_avg is not None:
            msg2 = f"hck_GPT: Yesterday \u2014 CPU averaged {cpu_avg:.0f}%. Clean run."
        elif top_app:
            msg2 = f"hck_GPT: Yesterday's top offender: {top_app}."
        else:
            msg2 = "hck_GPT: No data from yesterday yet \u2014 still collecting."

        try:
            self.parent.after(0, lambda: self.add_message(""))
            self.parent.after(0, lambda m=msg1: self.add_message(m))
            self.parent.after(0, lambda m=msg2: self.add_message(m))
        except Exception:
            pass

    # TIME BADGE
    def _make_time_badge(self):
        """Create a small inline canvas badge: |R| HH:MM |R|  (red bars, dark center)."""
        badge = tk.Canvas(
            self.log,
            width=62, height=14,
            bg=THEME["bg_panel"],
            highlightthickness=0,
            cursor="arrow",
        )
        # Center dark background
        badge.create_rectangle(0, 0, 62, 14, fill="#0d0f14", outline="")
        # Left red bar
        badge.create_rectangle(0, 0, 3, 14, fill="#dc2626", outline="")
        # Right red bar
        badge.create_rectangle(59, 0, 62, 14, fill="#dc2626", outline="")
        # Thin inner accent lines (silver border)
        badge.create_line(3, 0, 3, 14, fill="#374151")
        badge.create_line(59, 0, 59, 14, fill="#374151")
        t = time.strftime("%H:%M")
        badge.create_text(31, 7, text=t, fill="#94a3b8",
                          font=("Consolas", 7, "bold"), anchor="center")
        return badge

    # BRAND BADGE (first welcome message only)
    def _make_brand_badge(self):
        """Inline badge showing 'hck_GPT' label — used for the first message only."""
        badge = tk.Canvas(
            self.log,
            width=62, height=14,
            bg=THEME["bg_panel"],
            highlightthickness=0,
            cursor="arrow",
        )
        badge.create_rectangle(0, 0, 62, 14, fill="#0d0f14", outline="")
        badge.create_rectangle(0,  0, 3,  14, fill="#dc2626", outline="")
        badge.create_rectangle(59, 0, 62, 14, fill="#dc2626", outline="")
        badge.create_line(3,  0, 3,  14, fill="#374151")
        badge.create_line(59, 0, 59, 14, fill="#374151")
        badge.create_text(31, 7, text="hck_GPT", fill="#c0182a",
                          font=("Consolas", 6, "bold"), anchor="center")
        return badge

    # ADD MESSAGE
    def add_message(self, msg):
        try:
            if not self.log.winfo_exists():
                return
        except Exception:
            return
        self.log.config(state="normal")
        if msg.startswith("hck_GPT:"):
            if self._brand_badge_once:
                # First ever hck_GPT message → brand badge + strip "hck_GPT:" prefix
                badge = self._make_brand_badge()
                self._brand_badge_once = False
                msg = msg[len("hck_GPT:"):].lstrip()
            else:
                badge = self._make_time_badge()
            self.log.window_create("end", window=badge, padx=2, pady=1)
            self.log.insert("end", " ")
        start_pos = self.log.index("end")
        self.log.insert("end", msg + "\n")
        self._apply_inline_colors(start_pos)
        self.log.see("end")
        self.log.config(state="disabled")

        self._bind_process_tooltips()

    # INLINE COLOR TAGGER
    def _apply_inline_colors(self, start_pos: str):
        """Colorize keywords in the just-inserted text range [start_pos … end]."""
        end_pos = self.log.index("end")
        # (pattern, tag)  — applied in order; first match wins for overlapping
        patterns = [
            (r'\d+\.?\d*\s*°C',          "orange"),        # temperatures   → orange
            (r'\d+\.?\d*\s*(?:MB|GB)',    "light_purple"),  # sizes          → light purple
            (r'\d+\.?\d*%',              "teal"),           # percentages    → teal
            (r'⚠\S*',                    "yellow"),         # warning symbol → yellow
            (r'◈\s+\S[^\n]*',            "teal"),           # ◈ section headers → teal
        ]
        for pattern, tag in patterns:
            idx = start_pos
            while True:
                pos = self.log.search(pattern, idx, stopindex=end_pos, regexp=True)
                if not pos:
                    break
                line_text = self.log.get(pos, f"{pos} lineend")
                m = re.match(pattern, line_text)
                if not m:
                    idx = f"{pos}+1c"
                    continue
                match_end = f"{pos}+{len(m.group(0))}c"
                self.log.tag_add(tag, pos, match_end)
                idx = match_end

    def add_colored(self, text, tag=None):
        """Add text with a color tag (no newline — caller controls layout)."""
        try:
            if not self.log.winfo_exists():
                return
        except Exception:
            return
        self.log.config(state="normal")
        if tag:
            self.log.insert("end", text, tag)
        else:
            self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def add_line(self):
        """Add a newline."""
        self.add_colored("\n")

    # CURSOR BLINK
    def _start_cursor_blink(self):
        def toggle():
            try:
                if not self.entry.winfo_exists():
                    return
            except Exception:
                return
            if self.cursor_visible:
                self.entry.config(insertbackground=THEME["accent"])
            else:
                self.entry.config(insertbackground="#000000")
            self.cursor_visible = not self.cursor_visible
            self.entry.after(500, toggle)

        toggle()

    # TOGGLE
    def toggle(self, event=None):
        if self.animating:
            return

        if self.is_open:
            self.close()
        else:
            self.open()

    # OPEN
    def open(self):
        self.is_open = True
        self.chat.pack(side="top", fill="both")
        self.banner.itemconfig(self.banner_arrow, text="▲")
        self.banner.itemconfig(self.banner_text, text="hck_GPT  —  Your PC Companion")
        self._animate(self.collapsed_h, self.total_h)

        self._show_auto_greeting()

        self._start_insight_ticker()

    # CLOSE
    def close(self):
        self.is_open = False
        self.banner.itemconfig(self.banner_arrow, text="▼")
        self.banner.itemconfig(self.banner_text, text="hck_GPT  —  Your PC Companion")
        self._animate(self.total_h, self.collapsed_h,
                      on_end=lambda: self.chat.pack_forget())

        self._stop_insight_ticker()

    # AUTO-GREETING
    def _show_auto_greeting(self):
        """Show personalized greeting when panel opens (max once per 30 min)."""
        now = time.time()
        if (now - self._last_greeting_session) < 1800:
            return

        if self.chat_handler and self.chat_handler.insights:
            try:
                greeting_lines = self.chat_handler.insights.get_greeting()
                if greeting_lines:
                    self.add_message("")
                    for line in greeting_lines:
                        self.add_message(line)
                    self._last_greeting_session = now
            except Exception:
                pass

    # INSIGHT TICKER (periodic while panel is open)
    def _start_insight_ticker(self):
        """Schedule periodic insight checks while panel is open."""
        self._stop_insight_ticker()
        self._tick_insight()

    def _stop_insight_ticker(self):
        """Cancel the insight ticker."""
        if self._ticker_id is not None:
            try:
                self.frame.after_cancel(self._ticker_id)
            except Exception:
                pass
            self._ticker_id = None

    def _tick_insight(self):
        """Show one rotating tip every 6 minutes — replaces the previous tip (no spam)."""
        if not self.is_open:
            return

        try:
            if not self.frame.winfo_exists():
                return
        except Exception:
            return

        if self.chat_handler and self.chat_handler.insights:
            try:
                msg = self.chat_handler.insights.get_current_insight()
                if msg:
                    # ── Delete previous tip block if it still exists ──────────
                    try:
                        ranges = self.log.tag_ranges("tip_block")
                        if ranges:
                            self.log.config(state="normal")
                            # Iterate in reverse so earlier deletions don't shift later indices
                            for i in range(len(ranges) - 2, -1, -2):
                                self.log.delete(ranges[i], ranges[i + 1])
                            self.log.config(state="disabled")
                    except Exception:
                        pass

                    # ── Insert new tip, tag the full range ───────────────────
                    tip_start = self.log.index("end")
                    self.add_message("")
                    self.add_message(msg)
                    tip_end = self.log.index("end")
                    self.log.config(state="normal")
                    self.log.tag_add("tip_block", tip_start, tip_end)
                    self.log.config(state="disabled")
            except Exception:
                pass

        try:
            self._ticker_id = self.frame.after(360000, self._tick_insight)  # 6 minutes
        except Exception:
            pass

    # PROACTIVE MONITOR — silent banner update
    def _set_banner_status(self, status: str) -> None:
        """Called by proactive_monitor (via after()) to update banner text silently."""
        try:
            if not self.is_open and self.banner.winfo_exists():
                self.banner.itemconfig(
                    self.banner_text,
                    text=f"hck_GPT  —  {status}"
                )
        except Exception:
            pass

    # BANNER STATUS TICKER
    def _start_banner_ticker(self):
        """Update banner text with live status every 30 seconds."""
        self._update_banner_status()

    def _update_banner_status(self):
        """Refresh the banner with dynamic status info."""
        try:
            if not self.banner.winfo_exists():
                return
        except Exception:
            return

        if not self.is_open and self.chat_handler and self.chat_handler.insights:
            try:
                status = self.chat_handler.insights.get_banner_status()
                if status:
                    text = f"hck_GPT  —  {status}"
                    self.banner.itemconfig(self.banner_text, text=text)
            except Exception:
                pass

        try:
            self._banner_ticker_id = self.frame.after(30000, self._update_banner_status)
        except Exception:
            pass

    # TODAY REPORT (in-chat, colored)
    # ── LANGUAGE POPUP ────────────────────────────────────────────────────────
    def _show_language_popup(self):
        """Small language-selection popup anchored above the panel."""
        # Build the popup window
        pop = tk.Toplevel(self.parent)
        pop.overrideredirect(True)
        pop.configure(bg="#0d0f14",
                      highlightbackground="#2a3040", highlightthickness=1)
        pop.resizable(False, False)

        # Position: above the panel, right-aligned
        pop.update_idletasks()
        fx = self.frame.winfo_rootx()
        fy = self.frame.winfo_rooty()
        fw = self.frame.winfo_width()
        pop_w, pop_h = 188, 148
        px = fx + fw - pop_w - 4
        py = fy - pop_h - 4
        pop.geometry(f"{pop_w}x{pop_h}+{px}+{py}")

        # Title bar (thin crimson strip + label)
        tk.Frame(pop, bg="#7a0f20", height=2).pack(fill="x")
        hdr = tk.Frame(pop, bg="#0d0f14")
        hdr.pack(fill="x", padx=10, pady=(6, 4))
        tk.Label(hdr, text="UI Language",
                 font=("Consolas", 8, "bold"),
                 bg="#0d0f14", fg="#6b7280", anchor="w").pack(side="left")
        tk.Label(hdr, text="✕",
                 font=("Consolas", 9), bg="#0d0f14", fg="#374151",
                 cursor="hand2").pack(side="right")
        hdr.winfo_children()[-1].bind("<Button-1>", lambda e: pop.destroy())

        tk.Frame(pop, bg="#1a1d28", height=1).pack(fill="x")

        # Language options: (label, code, available, badge_text)
        _LANGS = [
            ("Default (auto)",  "auto", True,  ""),
            ("English",         "en",   True,  ""),
            ("Polski",          "pl",   True,  "⚠ not stable"),
            ("Deutsch",         "de",   False, "soon"),
        ]

        for label, code, available, badge in _LANGS:
            is_sel = getattr(self, '_ui_lang', 'en') == code

            row = tk.Frame(pop, bg="#111520" if is_sel else "#0d0f14",
                           cursor="hand2" if available else "arrow")
            row.pack(fill="x", padx=5, pady=1)

            # Accent bar (left edge — visible when selected)
            tk.Frame(row, bg="#c0182a" if is_sel else "#0d0f14",
                     width=2).pack(side="left", fill="y")

            # Label
            fg = "#e2e8f0" if is_sel else ("#9ca3af" if available else "#2a3040")
            tk.Label(row, text=label,
                     font=("Consolas", 8, "bold" if is_sel else "normal"),
                     bg="#111520" if is_sel else "#0d0f14",
                     fg=fg, anchor="w", padx=7, pady=5).pack(side="left", fill="x", expand=True)

            # Badge (right side)
            if badge:
                bc = "#f59e0b" if badge.startswith("⚠") else "#374151"
                tk.Label(row, text=badge,
                         font=("Consolas", 6),
                         bg="#111520" if is_sel else "#0d0f14",
                         fg=bc, padx=5).pack(side="right")

            if available and not is_sel:
                def _select(c=code):
                    self._ui_lang = c
                    pop.destroy()
                row.bind("<Button-1>", lambda e, c=code: _select(c))
                for child in row.winfo_children():
                    child.bind("<Button-1>", lambda e, c=code: _select(c))

                row.bind("<Enter>", lambda e, r=row: r.config(bg="#161922"))
                row.bind("<Leave>", lambda e, r=row: r.config(bg="#0d0f14"))

        # Close when focus leaves the popup
        pop.bind("<FocusOut>", lambda e: pop.destroy() if pop.winfo_exists() else None)
        pop.focus_set()

    def _run_today_report(self):
        """Generate Today Report directly in the chat with colored text."""
        self.clear_chat()

        try:
            data = self._gather_report_data()
        except Exception:
            data = None

        # Header
        self.add_colored("=" * 44 + "\n", "divider")
        self.add_colored("  TODAY REPORT", "header")
        self.add_colored("  " + time.strftime("%A, %B %d  %H:%M") + "\n", "muted")
        self.add_colored("=" * 44 + "\n", "divider")

        if not data:
            self.add_colored("\nData not available yet.\n", "muted")
            return

        # SECTION 1: UPTIME
        self.add_line()
        self.add_colored("  UPTIME\n", "accent_bold")

        session_str = self._fmt_short(data.get("session_uptime", 0))
        self.add_colored("  Session:  ", "muted")
        self.add_colored(session_str + "\n", "accent")

        total_h = data.get("total_uptime_hours", 0)
        if total_h >= 24:
            total_str = f"{total_h / 24:.1f} days ({total_h:.0f}h)"
        elif total_h >= 1:
            total_str = f"{total_h:.1f}h"
        elif total_h > 0:
            total_str = f"{total_h * 60:.0f}min"
        else:
            total_str = "< 1 min"
        self.add_colored("  Lifetime: ", "muted")
        self.add_colored(total_str + "\n", "purple")

        days = data.get("days_tracked", 0)
        if days > 0:
            self.add_colored(f"  Tracked:  {days} day{'s' if days != 1 else ''}", "muted")
            pts = data.get("data_points", 0)
            if pts:
                self.add_colored(f" / {pts} points today", "muted")
            self.add_line()

        # SECTION 2: AVERAGES
        self.add_line()
        self.add_colored("  TODAY AVERAGES", "accent_bold")
        self.add_colored("               ", "muted")
        self.add_colored("avg    ", "bold")
        self.add_colored("peak\n", "bold")

        cpu_avg = data.get("cpu_avg", 0)
        cpu_max = data.get("cpu_max", 0)
        self.add_colored("  CPU  ", "muted")
        self.add_colored(f"{cpu_avg:5.1f}%", "cpu")
        self.add_colored("  ", "muted")
        self.add_colored(f"{cpu_max:5.1f}%\n", "cpu")

        gpu_avg = data.get("gpu_avg", 0)
        gpu_max = data.get("gpu_max", 0)
        self.add_colored("  GPU  ", "muted")
        self.add_colored(f"{gpu_avg:5.1f}%", "gpu")
        self.add_colored("  ", "muted")
        self.add_colored(f"{gpu_max:5.1f}%\n", "gpu")

        ram_avg = data.get("ram_avg", 0)
        ram_max = data.get("ram_max", 0)
        self.add_colored("  RAM  ", "muted")
        self.add_colored(f"{ram_avg:5.1f}%", "ram")
        self.add_colored("  ", "muted")
        self.add_colored(f"{ram_max:5.1f}%\n", "ram")

        # SECTION 3: TOP SYSTEM PROCESSES
        if data.get("top_system"):
            self.add_line()
            self.add_colored("  TOP SYSTEM PROCESSES\n", "accent_bold")
            for i, p in enumerate(data["top_system"][:5], 1):
                name = p.get("_display", p.get("process_name", "?"))
                if len(name) > 20:
                    name = name[:18] + ".."
                cpu = p.get("cpu_avg", 0)
                ram = p.get("ram_avg_mb", 0)
                rank_tag = "accent" if i == 1 else "muted"
                self.add_colored(f"  {i}. ", rank_tag)
                self.add_colored(f"{name:<20s}", "bold")
                self.add_colored(f" CPU ", "muted")
                self.add_colored(f"{cpu:4.1f}%", "cpu")
                self.add_colored(f"  RAM ", "muted")
                self.add_colored(f"{ram:.0f}MB\n", "ram")

        # SECTION 4: TOP APPS
        if data.get("top_apps"):
            self.add_line()
            self.add_colored("  TOP APPS / GAMES / BROWSERS\n", "accent_bold")
            for i, p in enumerate(data["top_apps"][:5], 1):
                name = p.get("_display", p.get("process_name", "?"))
                if len(name) > 20:
                    name = name[:18] + ".."
                cpu = p.get("cpu_avg", 0)
                ram = p.get("ram_avg_mb", 0)
                cat = p.get("_category", "")
                rank_tag = "accent" if i == 1 else "muted"
                self.add_colored(f"  {i}. ", rank_tag)
                self.add_colored(f"{name:<20s}", "bold")

                # Category tag
                cat_tags = {
                    "Gaming": "red", "Browser": "gpu",
                    "Development": "green", "Media": "ram",
                }
                if cat and cat not in ("Unknown", "System"):
                    ctag = cat_tags.get(cat, "muted")
                    self.add_colored(f" [{cat}]", ctag)

                self.add_colored(f" {cpu:.1f}%", "cpu")
                self.add_colored(f" {ram:.0f}MB\n", "muted")

        # SECTION 5: ALERTS
        self.add_line()
        alerts = data.get("alerts_count", {})
        total = alerts.get("total", 0)
        critical = alerts.get("critical", 0)

        if total == 0:
            self.add_colored("  TEMP & VOLTAGES: NO ALERTS\n", "yellow_bold")
        elif critical > 0:
            self.add_colored(f"  TEMP & VOLTAGES: {critical} CRITICAL\n", "red")
        else:
            self.add_colored(f"  TEMP & VOLTAGES: {total} WARNING(S)\n", "yellow_bold")

        self.add_colored("=" * 44 + "\n", "divider")

    def _gather_report_data(self):
        """Gather data for the in-chat report."""
        import traceback
        data = {
            "session_uptime": 0,
            "total_uptime_hours": 0,
            "days_tracked": 0,
            "cpu_avg": 0, "gpu_avg": 0, "ram_avg": 0,
            "cpu_max": 0, "gpu_max": 0, "ram_max": 0,
            "top_system": [],
            "top_apps": [],
            "alerts_count": {"total": 0, "critical": 0, "warning": 0, "info": 0},
            "data_points": 0,
        }

        try:
            from hck_gpt.insights import insights_engine
            data["session_uptime"] = insights_engine.get_session_uptime()
        except Exception:
            pass

        try:
            from hck_stats_engine.query_api import query_api
            from hck_stats_engine.events import event_detector
            from datetime import datetime

            now = time.time()
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0).timestamp()

            usage = query_api.get_usage_for_range(today_start, now, max_points=60)
            if usage:
                data["data_points"] = len(usage)
                cpu_vals = [d.get("cpu_avg", 0) or 0 for d in usage]
                gpu_vals = [d.get("gpu_avg", 0) or 0 for d in usage]
                ram_vals = [d.get("ram_avg", 0) or 0 for d in usage]

                if cpu_vals:
                    data["cpu_avg"] = sum(cpu_vals) / len(cpu_vals)
                    data["cpu_max"] = max(cpu_vals)
                if gpu_vals:
                    data["gpu_avg"] = sum(gpu_vals) / len(gpu_vals)
                    data["gpu_max"] = max(gpu_vals)
                if ram_vals:
                    data["ram_avg"] = sum(ram_vals) / len(ram_vals)
                    data["ram_max"] = max(ram_vals)

            summary = query_api.get_summary_stats(days=9999)
            if summary:
                data["total_uptime_hours"] = summary.get("total_uptime_hours", 0)

            date_range = query_api.get_available_date_range()
            if date_range:
                data["days_tracked"] = date_range.get("total_days", 0)

            today_str = datetime.now().strftime("%Y-%m-%d")
            procs = query_api.get_process_daily_breakdown(today_str, top_n=20)

            try:
                from core.process_classifier import classifier
                for p in procs:
                    name = p.get("process_name", "")
                    info = classifier.classify_process(name)
                    p["_type"] = info.get("type", "unknown")
                    p["_display"] = info.get("display_name", name)
                    p["_category"] = info.get("category", "")
            except Exception:
                for p in procs:
                    p["_type"] = "unknown"
                    p["_display"] = p.get("display_name", p.get("process_name", "?"))
                    p["_category"] = p.get("category", "")

            data["top_system"] = [p for p in procs if p["_type"] == "system"][:5]
            data["top_apps"] = [
                p for p in procs
                if p["_type"] in ("browser", "program", "unknown")
                and p.get("cpu_avg", 0) > 0.5
            ][:5]

            data["alerts_count"] = event_detector.get_active_alerts_count()

        except Exception:
            traceback.print_exc()

        return data

    def _fmt_short(self, seconds):
        """Short duration format."""
        if not seconds:
            return "0s"
        seconds = float(seconds)
        if seconds < 60:
            return f"{int(seconds)}s"
        m = int(seconds // 60)
        h = m // 60
        mins = m % 60
        if h > 0:
            return f"{h}h {mins}min"
        return f"{mins}min"

    def _bind_process_tooltips(self):
        if not HAS_PROCESS_LIBRARY or not self.tooltip:
            return
        content = self.log.get("1.0", "end-1c")
        for match in re.finditer(r'\b\w+\.exe\b', content, re.IGNORECASE):
            pname = match.group(0)
            start_idx = match.start()
            line_num = content[:start_idx].count('\n') + 1
            col_num = start_idx - content[:start_idx].rfind('\n') - 1
            start_pos = f"{line_num}.{col_num}"
            end_pos = f"{line_num}.{col_num + len(pname)}"
            info = process_library.get_process_info(pname)
            if info:
                tag = f"process_{pname}_{start_idx}"
                self.log.tag_add(tag, start_pos, end_pos)
                self.log.tag_config(tag, foreground=THEME["accent2"], underline=True)
                tt = process_library.format_tooltip_text(pname)
                self.log.tag_bind(tag, "<Enter>",
                                  lambda e, n=pname, t=tt: self.tooltip.show(e, n, t))
                self.log.tag_bind(tag, "<Leave>", lambda e: self.tooltip.hide())

    # RESIZE -> keep bottom docking
    def _on_resize(self, event=None):
        parent_h = self.parent.winfo_height()
        target_h = self.total_h if self.is_open else self.collapsed_h
        new_y = parent_h - target_h
        if new_y < 0:
            new_y = 0

        self.frame.place_configure(
            x=0,
            y=new_y,
            width=self.width,
            height=target_h
        )

    # SMOOTH ANIMATION WITH EASING
    def _animate(self, start_h, end_h, duration_ms=200, on_end=None):
        if self.after_id:
            self.frame.after_cancel(self.after_id)

        import time as _time
        start_time = _time.time()
        diff = end_h - start_h
        parent_h = self.parent.winfo_height()

        def ease_out_cubic(t):
            return 1 - pow(1 - t, 3)

        def anim():
            elapsed = (_time.time() - start_time) * 1000
            progress = min(elapsed / duration_ms, 1.0)

            eased_progress = ease_out_cubic(progress)
            current_h = start_h + (diff * eased_progress)

            y = parent_h - current_h
            if y < 0:
                y = 0

            self.frame.place_configure(height=int(current_h), y=int(y))

            if progress >= 1.0:
                self.frame.place_configure(height=end_h, y=parent_h - end_h)
                if on_end:
                    on_end()
                self.animating = False
                return

            self.after_id = self.frame.after(16, anim)

        self.animating = True
        anim()

    # SEND
    def _send(self):
        text = self.entry.get().strip()
        if not text:
            return

        self.entry.delete(0, "end")

        # Show user message
        self.add_message("> " + text)

        # Process with chat handler
        if self.chat_handler:
            responses = self.chat_handler.process_message(
                text, ui_lang=getattr(self, '_ui_lang', 'auto')
            )

            # Check if we need to clear chat (wizard starting)
            if text.lower() in ["yes", "y", "yeah", "ok", "sure", "tak", "t"]:
                if self.chat_handler.wizard.state == "questions":
                    self.clear_chat()

            # Add response messages
            for response in responses:
                self.add_message(response)
        else:
            self.add_message("hck_GPT: (Chat handler not available)")

    def clear_chat(self):
        """Clear the chat log"""
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _start_service_setup(self):
        """Start the Service Setup wizard via button"""
        if self.chat_handler:
            self.clear_chat()
            responses = self.chat_handler.wizard.start()
            for response in responses:
                self.add_message(response)
        else:
            self.add_message("hck_GPT: Service Setup not available")

    def _toggle_maximize(self):
        """Toggle between normal and maximized chat log height"""
        if self.current_mode == "normal":
            self.current_mode = "maximized"
            self.log.config(height=18)
            self.expand_btn.config(text="⬛ Normal")

            if self.is_open:
                target_h = self.collapsed_h + self.max_h
                self._animate(self.total_h, target_h, on_end=lambda: setattr(self, 'total_h', target_h))
        else:
            self.current_mode = "normal"
            self.log.config(height=10)
            self.expand_btn.config(text="⬜ Maximize")

            if self.is_open:
                target_h = self.collapsed_h + self.expanded_h
                self._animate(self.total_h, target_h, on_end=lambda: setattr(self, 'total_h', target_h))
