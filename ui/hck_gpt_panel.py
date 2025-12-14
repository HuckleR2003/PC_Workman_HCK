# ui/hck_gpt_panel.py
"""
Modern smooth hck_GPT panel with:
- Smooth gradient banner
- Buttery smooth animations
- Modern scrollbar
- Sleek entry field design
- Hover effects
- Integrated Service Setup wizard
"""

import tkinter as tk
from tkinter import ttk
from ui.theme import THEME
import os
import sys

# Add hck_gpt to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from hck_gpt.chat_handler import ChatHandler
    HAS_CHAT_HANDLER = True
except ImportError:
    HAS_CHAT_HANDLER = False
    print("Warning: ChatHandler not available")

SEND_ICON = "data/icons/send_hck.png"


class HCKGPTPanel:
    def __init__(self, parent, width, collapsed_h=34, expanded_h=280, max_h=420):
        self.parent = parent
        self.width = width
        self.collapsed_h = collapsed_h
        self.expanded_h = expanded_h  # Normal expanded height (increased)
        self.max_h = max_h  # Maximum expanded height (increased)
        self.total_h = collapsed_h + expanded_h
        self.current_mode = "normal"  # normal, maximized

        self.is_open = False
        self.animating = False
        self.after_id = None
        self.cursor_visible = True

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
            height=10,  # Increased default height
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

        parent.bind("<Configure>", self._on_resize)

    # ================================================================
    # SMOOTH GRADIENT BANNER
    # ================================================================
    def _draw_gradient_banner(self):
        w = self.width
        h = self.collapsed_h

        # More gradient steps for smoother transition
        colors = [
            "#7f3ef5",  # Purple
            "#9540ED",
            "#AB45E8",
            "#C154DC",
            "#D865C0",
            "#EE76A4",
            "#FF7B89",
            "#FF7B59",
            "#FF6A2F"   # Orange
        ]

        steps = len(colors)
        step_w = w / steps

        for i, color in enumerate(colors):
            x0 = int(i * step_w)
            x1 = int(x0 + step_w) + 1  # +1 to avoid gaps
            self.banner.create_rectangle(x0, 0, x1, h, fill=color, outline=color)

    # ================================================================
    # HOVER EFFECTS
    # ================================================================
    def _on_banner_enter(self, event=None):
        """Banner hover enter - subtle highlight"""
        self.banner.itemconfig(self.banner_text, fill=THEME["accent"])
        self.banner.itemconfig(self.banner_arrow, fill=THEME["accent"])

    def _on_banner_leave(self, event=None):
        """Banner hover leave - restore"""
        self.banner.itemconfig(self.banner_text, fill="#ffffff")
        self.banner.itemconfig(self.banner_arrow, fill="#ffffff")

    # ================================================================
    # WELCOME MESSAGES
    # ================================================================
    def _welcome(self):
        self.add_message("hck_GPT: Welcome! I'm your Workman Manager.")
        self.add_message("hck_GPT: I'm in early-access — but I'm here to help you.")
        self.add_message("")
        self.add_message("💡 Try typing 'service setup' to optimize your PC!")
        self.add_message("   or 'help' to see all commands.")

    # ================================================================
    # ADD MESSAGE
    # ================================================================
    def add_message(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    # ================================================================
    # CURSOR BLINK
    # ================================================================
    def _start_cursor_blink(self):
        def toggle():
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

    # ================================================================
    # CLOSE
    # ================================================================
    def close(self):
        self.is_open = False
        self.banner.itemconfig(self.banner_arrow, text="▼")
        self.banner.itemconfig(self.banner_text, text="hck_GPT — Your PC Companion   •   Click to expand")
        self._animate(self.total_h, self.collapsed_h,
                      on_end=lambda: self.chat.pack_forget())

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
        """Smooth animation with easing for buttery transitions"""
        if self.after_id:
            self.frame.after_cancel(self.after_id)

        import time
        start_time = time.time()
        diff = end_h - start_h
        parent_h = self.parent.winfo_height()

        def ease_out_cubic(t):
            """Easing function for smooth deceleration"""
            return 1 - pow(1 - t, 3)

        def anim():
            elapsed = (time.time() - start_time) * 1000  # ms
            progress = min(elapsed / duration_ms, 1.0)

            # Apply easing
            eased_progress = ease_out_cubic(progress)
            current_h = start_h + (diff * eased_progress)

            y = parent_h - current_h
            if y < 0:
                y = 0

            self.frame.place_configure(height=int(current_h), y=int(y))

            if progress >= 1.0:
                # Animation complete
                self.frame.place_configure(height=end_h, y=parent_h - end_h)
                if on_end:
                    on_end()
                self.animating = False
                return

            # Continue animation (60 FPS target)
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
                    # User said yes to intro, clear chat
                    self.clear_chat()

            # Add response messages
            for response in responses:
                self.add_message(response)
        else:
            self.add_message("hck_GPT: (AI not connected yet)")

    def clear_chat(self):
        """Clear the chat log"""
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _start_service_setup(self):
        """Start the Service Setup wizard via button"""
        if self.chat_handler:
            # Clear chat first
            self.clear_chat()

            # Start wizard
            responses = self.chat_handler.wizard.start()
            for response in responses:
                self.add_message(response)
        else:
            self.add_message("hck_GPT: Service Setup not available")

    def _toggle_maximize(self):
        """Toggle between normal and maximized chat log height"""
        if self.current_mode == "normal":
            # Maximize - increase text height
            self.current_mode = "maximized"
            self.log.config(height=18)  # Bigger text area (reduced from 22 to fit input)
            self.expand_btn.config(text="⬛ Normal")

            # Expand panel to accommodate
            if self.is_open:
                target_h = self.collapsed_h + self.max_h
                self._animate(self.total_h, target_h, on_end=lambda: setattr(self, 'total_h', target_h))
        else:
            # Back to normal - decrease text height
            self.current_mode = "normal"
            self.log.config(height=10)  # Normal text area
            self.expand_btn.config(text="⬜ Maximize")

            # Shrink panel back
            if self.is_open:
                target_h = self.collapsed_h + self.expanded_h
                self._animate(self.total_h, target_h, on_end=lambda: setattr(self, 'total_h', target_h))
