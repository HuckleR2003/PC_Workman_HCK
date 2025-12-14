# ui/system_tray.py
"""
System Tray Manager for PC Workman
Battery-style icon with CPU (red) and GPU (yellow) indicators
"""

import tkinter as tk
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item
import threading
import time


class SystemTrayManager:
    """Manages system tray icon with live CPU/GPU indicators"""

    def __init__(self, main_window_callback, stats_callback, quit_callback):
        """
        Args:
            main_window_callback: Function to show main window
            stats_callback: Function to show stats window
            quit_callback: Function to quit application
        """
        self.show_main_window = main_window_callback
        self.show_stats = stats_callback
        self.quit_app = quit_callback

        self.icon = None
        self.cpu_percent = 0.0
        self.gpu_percent = 0.0
        self._running = False
        self._update_thread = None

    def create_battery_icon(self, cpu_percent, gpu_percent):
        """
        Create vertical bar icon with CPU (blue) and RAM (yellow) indicators

        Args:
            cpu_percent: CPU usage 0-100
            gpu_percent: RAM usage 0-100 (parameter name kept for compatibility)

        Returns:
            PIL.Image: Icon image
        """
        # Icon size (64x64 for clarity)
        size = 64
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Bar dimensions
        bar_width = 12
        bar_height = 44
        bar_spacing = 8
        base_y = 50  # Bottom position
        base_x = (size - (bar_width * 2 + bar_spacing)) // 2

        # CPU Bar (left - blue)
        cpu_x = base_x
        cpu_bg_y = base_y - bar_height

        # CPU background (dark)
        draw.rectangle(
            [cpu_x, cpu_bg_y, cpu_x + bar_width, base_y],
            fill='#1a1d24',
            outline='#3b82f6',
            width=1
        )

        # CPU fill (blue, grows from bottom)
        cpu_fill_height = int((cpu_percent / 100.0) * bar_height)
        if cpu_fill_height > 0:
            cpu_color = self._get_heat_color(cpu_percent, 'cpu')
            draw.rectangle(
                [
                    cpu_x + 1,
                    base_y - cpu_fill_height,
                    cpu_x + bar_width - 1,
                    base_y - 1
                ],
                fill=cpu_color
            )

        # RAM Bar (right - yellow)
        ram_x = cpu_x + bar_width + bar_spacing
        ram_bg_y = base_y - bar_height

        # RAM background (dark)
        draw.rectangle(
            [ram_x, ram_bg_y, ram_x + bar_width, base_y],
            fill='#1a1d24',
            outline='#fbbf24',
            width=1
        )

        # RAM fill (yellow, grows from bottom)
        ram_percent = gpu_percent  # Using gpu_percent as ram_percent
        ram_fill_height = int((ram_percent / 100.0) * bar_height)
        if ram_fill_height > 0:
            ram_color = self._get_heat_color(ram_percent, 'ram')
            draw.rectangle(
                [
                    ram_x + 1,
                    base_y - ram_fill_height,
                    ram_x + bar_width - 1,
                    base_y - 1
                ],
                fill=ram_color
            )

        # Add small labels below bars
        try:
            font = ImageFont.truetype("consola.ttf", 8)
        except:
            font = ImageFont.load_default()

        # Labels
        draw.text((cpu_x + 1, base_y + 2), "CPU", fill='#3b82f6', font=font)
        draw.text((ram_x + 1, base_y + 2), "RAM", fill='#fbbf24', font=font)

        return img

    def _get_heat_color(self, percent, type='cpu'):
        """
        Get color based on usage percentage (heat map)

        Args:
            percent: Usage 0-100
            type: 'cpu', 'ram', or 'gpu'

        Returns:
            str: Hex color
        """
        if type == 'ram':
            # RAM: Yellow gradient (light to dark)
            if percent < 30:
                return '#fbbf24'  # Light Yellow
            elif percent < 60:
                return '#f59e0b'  # Orange-Yellow
            else:
                return '#d97706'  # Dark Orange-Yellow
        elif type == 'gpu':
            # GPU: Green gradient (kept for compatibility)
            if percent < 30:
                return '#10b981'  # Light Green
            elif percent < 60:
                return '#059669'  # Green
            else:
                return '#047857'  # Dark Green
        else:
            # CPU: Blue gradient (light to dark)
            if percent < 30:
                return '#3b82f6'  # Light Blue
            elif percent < 60:
                return '#2563eb'  # Blue
            else:
                return '#1d4ed8'  # Dark Blue

    def update_stats(self, cpu_percent, gpu_percent):
        """Update CPU and GPU percentages"""
        self.cpu_percent = max(0, min(100, cpu_percent))
        self.gpu_percent = max(0, min(100, gpu_percent))

        if self.icon and self._running:
            # Update icon image
            new_icon = self.create_battery_icon(self.cpu_percent, self.gpu_percent)
            self.icon.icon = new_icon

    def _create_menu(self):
        """Create system tray context menu"""
        return pystray.Menu(
            item('📊 Show Monitor', self._on_show_monitor, default=True),
            item('📈 Show Statistics', self._on_show_stats),
            pystray.Menu.SEPARATOR,
            item('❌ Exit Program', self._on_quit)
        )

    def _on_show_monitor(self, icon, item):
        """Show main monitor window"""
        self.show_main_window()

    def _on_show_stats(self, icon, item):
        """Show statistics window"""
        self.show_stats()

    def _on_quit(self, icon, item):
        """Quit application"""
        self.stop()
        self.quit_app()

    def start(self):
        """Start system tray icon"""
        if self._running:
            return

        self._running = True

        # Create initial icon
        initial_icon = self.create_battery_icon(self.cpu_percent, self.gpu_percent)

        # Create pystray icon
        self.icon = pystray.Icon(
            "pc_workman",
            initial_icon,
            "PC Workman - HCK Labs",
            menu=self._create_menu()
        )

        # Run in separate thread
        self._update_thread = threading.Thread(target=self._run_icon, daemon=True)
        self._update_thread.start()

    def _run_icon(self):
        """Run icon in separate thread"""
        try:
            self.icon.run()
        except Exception as e:
            print(f"[SystemTray] Error: {e}")

    def stop(self):
        """Stop system tray icon"""
        self._running = False
        if self.icon:
            try:
                self.icon.stop()
            except:
                pass

    def is_running(self):
        """Check if tray is running"""
        return self._running


class ToastNotification:
    """Simple toast notification for Windows"""

    @staticmethod
    def show(title, message, duration_ms=2000):
        """
        Show toast notification

        Args:
            title: Notification title
            message: Notification message
            duration_ms: Duration in milliseconds
        """
        # Create small notification window
        toast = tk.Toplevel()
        toast.withdraw()
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        toast.configure(bg='#0a1015')

        # Position in bottom right
        screen_w = toast.winfo_screenwidth()
        screen_h = toast.winfo_screenheight()

        toast_w = 320
        toast_h = 80
        x = screen_w - toast_w - 20
        y = screen_h - toast_h - 60

        toast.geometry(f"{toast_w}x{toast_h}+{x}+{y}")

        # Frame with border
        frame = tk.Frame(toast, bg='#00D9FF', bd=0)
        frame.pack(fill='both', expand=True, padx=2, pady=2)

        inner = tk.Frame(frame, bg='#0a1015', bd=0)
        inner.pack(fill='both', expand=True)

        # Title
        title_lbl = tk.Label(
            inner,
            text=title,
            font=('Consolas', 10, 'bold'),
            fg='#00D9FF',
            bg='#0a1015',
            anchor='w'
        )
        title_lbl.pack(fill='x', padx=12, pady=(8, 0))

        # Message
        msg_lbl = tk.Label(
            inner,
            text=message,
            font=('Consolas', 9),
            fg='#8899AA',
            bg='#0a1015',
            anchor='w'
        )
        msg_lbl.pack(fill='x', padx=12, pady=(2, 8))

        # Show with fade-in effect
        toast.attributes('-alpha', 0.0)
        toast.deiconify()

        # Fade in
        for i in range(1, 11):
            toast.attributes('-alpha', i / 10.0)
            toast.update()
            time.sleep(0.02)

        # Auto close after duration
        def close_toast():
            # Fade out
            try:
                for i in range(10, 0, -1):
                    toast.attributes('-alpha', i / 10.0)
                    toast.update()
                    time.sleep(0.02)
                toast.destroy()
            except:
                pass

        toast.after(duration_ms, close_toast)
