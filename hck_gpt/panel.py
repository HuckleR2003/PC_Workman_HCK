# hck_gpt/panel.py
"""
hck_GPT Panel - Sliding chat interface with service wizard.
Used in both Minimal and Expanded modes.
Features: auto-greeting, periodic insight ticker, dynamic banner status.
"""

import tkinter as tk
from tkinter import ttk
from ui.theme import THEME
import os
import time

try:
    from hck_gpt.chat_handler import ChatHandler
    HAS_CHAT_HANDLER = True
except ImportError:
    HAS_CHAT_HANDLER = False
    print("[hck_GPT] ChatHandler not available")

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

        # Initialize chat handler
        self.chat_handler = ChatHandler() if HAS_CHAT_HANDLER else None

        # MAIN PANEL with subtle shadow effect
        self.frame = tk.Frame(parent, bg=THEME["bg_panel"])
        self.frame.place(
            x=0,
            y=parent.winfo_height() - collapsed_h,
            width=self.width,
            height=collapsed_h
        )

        # ========== BANNER WITH SMOOTH GRADIENT ==========
        self.banner = tk.Canvas(
            self.frame,
            height=self.collapsed_h,
            bd=0,
            highlightthickness=0
        )
        self.banner.pack(side="top", fill="x")

        self._draw_gradient_banner()

        # Banner text with better positioning
        self.banner_text = self.banner.create_text(
            14, self.collapsed_h // 2,
            anchor="w",
            text="hck_GPT — Your PC Companion   •   Click to expand",
            font=("Segoe UI", 10, "bold"),
            fill="#ffffff"
        )

        # Arrow indicator
        self.banner_arrow = self.banner.create_text(
            self.width - 20, self.collapsed_h // 2,
            anchor="e",
            text="▼",
            font=("Arial", 10),
            fill="#ffffff"
        )

        # Hover effects
        self.banner.bind("<Enter>", self._on_banner_enter)
        self.banner.bind("<Leave>", self._on_banner_leave)
        self.banner.bind("<Button-1>", self.toggle)

        # ========== CHAT AREA ==========
        self.chat = tk.Frame(self.frame, bg=THEME["bg_panel"])

        # Control bar with buttons
        control_bar = tk.Frame(self.chat, bg=THEME["bg_panel"])
        control_bar.pack(fill="x", padx=8, pady=(8, 4))

        # Service Setup Button
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

        # Expand/Maximize button
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

        # Clear chat button
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

        # ========== TODAY REPORT BUTTON (rainbow gradient) ==========
        report_bar = tk.Frame(self.chat, bg=THEME["bg_panel"])
        report_bar.pack(fill="x", padx=8, pady=(0, 4))

        self._report_btn_canvas = tk.Canvas(
            report_bar, height=28, bg=THEME["bg_panel"],
            highlightthickness=0, cursor="hand2"
        )
        self._report_btn_canvas.pack(fill="x")
        self._report_btn_canvas.bind("<Configure>", self._draw_report_button)
        self._report_btn_canvas.bind("<Button-1>", self._open_today_report)
        self._report_btn_canvas.bind("<Enter>",
            lambda e: self._report_btn_canvas.itemconfig("btn_text", fill="#ffffff"))
        self._report_btn_canvas.bind("<Leave>",
            lambda e: self._report_btn_canvas.itemconfig("btn_text", fill="#f0f0f0"))

        # LOG with custom scrollbar
        log_container = tk.Frame(self.chat, bg=THEME["bg_panel"])
        log_container.pack(fill="both", expand=True, padx=8, pady=(4, 6))

        # Custom scrollbar
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

        # ENTRY BAR with modern design
        entry_container = tk.Frame(self.chat, bg=THEME["bg_panel"])
        entry_container.pack(fill="x", padx=8, pady=(0, 10))

        # Entry field wrapper for border effect
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

        # Focus effects
        self.entry.bind("<FocusIn>", lambda e: entry_wrapper.config(bg=THEME["accent"]))
        self.entry.bind("<FocusOut>", lambda e: entry_wrapper.config(bg=THEME["accent2"]))

        # blinking cursor start
        self._start_cursor_blink()

        # SEND BUTTON with modern design
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

        # welcome
        self._welcome()

        # Start banner status ticker
        self._start_banner_ticker()

        parent.bind("<Configure>", self._on_resize)

    # ================================================================
    # SMOOTH GRADIENT BANNER (pixel-level fade)
    # ================================================================
    def _draw_gradient_banner(self):
        w = self.width
        h = self.collapsed_h

        # Anchor colors for smooth interpolation
        anchors = [
            (0.0,  (127, 62, 245)),   # Purple
            (0.25, (193, 84, 220)),    # Pink-purple
            (0.50, (238, 118, 164)),   # Rose
            (0.75, (255, 123, 89)),    # Salmon
            (1.0,  (255, 106, 47)),    # Orange
        ]

        # Draw 2px-wide strips for smooth fade
        strip_w = 3
        for x in range(0, w, strip_w):
            t = x / max(w - 1, 1)

            # Find surrounding anchors
            c0 = anchors[0][1]
            c1 = anchors[-1][1]
            for j in range(len(anchors) - 1):
                if anchors[j][0] <= t <= anchors[j + 1][0]:
                    seg_t = (t - anchors[j][0]) / (anchors[j + 1][0] - anchors[j][0])
                    c0 = anchors[j][1]
                    c1 = anchors[j + 1][1]
                    r = int(c0[0] + (c1[0] - c0[0]) * seg_t)
                    g = int(c0[1] + (c1[1] - c0[1]) * seg_t)
                    b = int(c0[2] + (c1[2] - c0[2]) * seg_t)
                    color = f"#{r:02x}{g:02x}{b:02x}"
                    break
            else:
                color = f"#{c1[0]:02x}{c1[1]:02x}{c1[2]:02x}"

            self.banner.create_rectangle(
                x, 0, x + strip_w + 1, h,
                fill=color, outline=color
            )

    # ================================================================
    # HOVER EFFECTS
    # ================================================================
    def _on_banner_enter(self, event=None):
        self.banner.itemconfig(self.banner_text, fill=THEME["accent"])
        self.banner.itemconfig(self.banner_arrow, fill=THEME["accent"])

    def _on_banner_leave(self, event=None):
        self.banner.itemconfig(self.banner_text, fill="#ffffff")
        self.banner.itemconfig(self.banner_arrow, fill="#ffffff")

    # ================================================================
    # WELCOME MESSAGES
    # ================================================================
    def _welcome(self):
        self.add_message("hck_GPT: Welcome! I'm your Workman Manager.")
        self.add_message("hck_GPT: I monitor your system and track usage patterns.")
        self.add_message("")
        self.add_message("💡 Commands: 'stats', 'alerts', 'insights', 'teaser', 'help'")
        self.add_message("   or 'service setup' to optimize your PC!")

    # ================================================================
    # ADD MESSAGE
    # ================================================================
    def add_message(self, msg):
        try:
            if not self.log.winfo_exists():
                return
        except Exception:
            return
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    # ================================================================
    # CURSOR BLINK
    # ================================================================
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

    # ================================================================
    # TOGGLE
    # ================================================================
    def toggle(self, event=None):
        if self.animating:
            return

        if self.is_open:
            self.close()
        else:
            self.open()

    # ================================================================
    # OPEN
    # ================================================================
    def open(self):
        self.is_open = True
        self.chat.pack(side="top", fill="both")
        self.banner.itemconfig(self.banner_arrow, text="▲")
        self.banner.itemconfig(self.banner_text, text="hck_GPT — Your PC Companion   •   Click to collapse")
        self._animate(self.collapsed_h, self.total_h)

        # Auto-greeting (once per 30 min)
        self._show_auto_greeting()

        # Start insight ticker
        self._start_insight_ticker()

    # ================================================================
    # CLOSE
    # ================================================================
    def close(self):
        self.is_open = False
        self.banner.itemconfig(self.banner_arrow, text="▼")
        self.banner.itemconfig(self.banner_text, text="hck_GPT — Your PC Companion   •   Click to expand")
        self._animate(self.total_h, self.collapsed_h,
                      on_end=lambda: self.chat.pack_forget())

        # Stop insight ticker
        self._stop_insight_ticker()

    # ================================================================
    # AUTO-GREETING
    # ================================================================
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

    # ================================================================
    # INSIGHT TICKER (periodic while panel is open)
    # ================================================================
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
        """Check for notable insights and show them."""
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
                    self.add_message("")
                    self.add_message(msg)
            except Exception:
                pass

        # Schedule next tick (60 seconds)
        try:
            self._ticker_id = self.frame.after(60000, self._tick_insight)
        except Exception:
            pass

    # ================================================================
    # BANNER STATUS TICKER
    # ================================================================
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
                    text = f"hck_GPT — {status}   •   Click to expand"
                    self.banner.itemconfig(self.banner_text, text=text)
            except Exception:
                pass

        # Schedule next update (30 seconds)
        try:
            self._banner_ticker_id = self.frame.after(30000, self._update_banner_status)
        except Exception:
            pass

    # ================================================================
    # TODAY REPORT BUTTON (rainbow gradient)
    # ================================================================
    def _draw_report_button(self, event=None):
        """Draw rainbow gradient button on canvas."""
        c = self._report_btn_canvas
        c.delete("all")
        w = c.winfo_width()
        h = 28

        if w < 10:
            return

        # Rainbow gradient colors
        colors = [
            "#7f3ef5", "#9540ED", "#C154DC", "#EE76A4",
            "#FF7B59", "#FF6A2F", "#fbbf24", "#22c55e",
            "#00ffc8", "#4b9aff", "#7f3ef5"
        ]

        steps = len(colors)
        step_w = w / steps
        for i, color in enumerate(colors):
            x0 = int(i * step_w)
            x1 = int(x0 + step_w) + 1
            c.create_rectangle(x0, 0, x1, h, fill=color, outline=color)

        # Border radius effect (dark corner pixels)
        for corner_x in [0, 1, w - 1, w - 2]:
            for corner_y in [0, 1, h - 1, h - 2]:
                if (corner_x <= 1 and corner_y <= 1) or \
                   (corner_x >= w - 2 and corner_y <= 1) or \
                   (corner_x <= 1 and corner_y >= h - 2) or \
                   (corner_x >= w - 2 and corner_y >= h - 2):
                    c.create_rectangle(corner_x, corner_y, corner_x + 1,
                                       corner_y + 1, fill=THEME["bg_panel"],
                                       outline=THEME["bg_panel"])

        # Text
        c.create_text(
            w // 2, h // 2,
            text="✨  Today Report!  ✨",
            font=("Segoe UI", 10, "bold"),
            fill="#f0f0f0",
            tags="btn_text"
        )

    def _open_today_report(self, event=None):
        """Open the Today Report window."""
        try:
            from hck_gpt.report_window import open_today_report
            open_today_report(self.parent)
        except Exception as e:
            self.add_message(f"hck_GPT: Could not open report — {e}")

    # ================================================================
    # RESIZE → keep bottom docking
    # ================================================================
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

    # ================================================================
    # SMOOTH ANIMATION WITH EASING
    # ================================================================
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

    # ================================================================
    # SEND
    # ================================================================
    def _send(self):
        text = self.entry.get().strip()
        if not text:
            return

        self.entry.delete(0, "end")

        # Show user message
        self.add_message("> " + text)

        # Process with chat handler
        if self.chat_handler:
            responses = self.chat_handler.process_message(text)

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
