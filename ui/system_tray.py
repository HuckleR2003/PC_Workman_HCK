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
    """Manages system tray icon with live CPU/GPU/RAM indicators - ENHANCED! 💎"""

    def __init__(self, main_window_callback, stats_callback, quit_callback, sensors_callback=None):
        """
        Args:
            main_window_callback: Function to show main window
            stats_callback: Function to show stats window
            quit_callback: Function to quit application
            sensors_callback: Function to show sensors window (NEW!)
        """
        self.show_main_window = main_window_callback
        self.show_stats = stats_callback
        self.show_sensors = sensors_callback
        self.quit_app = quit_callback

        self.icon = None
        self.cpu_percent = 0.0
        self.ram_percent = 0.0  # Changed from gpu_percent
        self.gpu_percent = 0.0  # NEW: actual GPU tracking
        self.cpu_temp = 0.0     # NEW: CPU temperature
        self.gpu_temp = 0.0     # NEW: GPU temperature
        self._running = False
        self._update_thread = None

    def create_battery_icon(self, cpu_percent=None, ram_percent=None, gpu_percent=None):
        """
        Create TRIPLE vertical bar icon with CPU (blue), GPU (green), and RAM (yellow) - MSI Afterburner style! 💎

        Args:
            cpu_percent: CPU usage 0-100
            ram_percent: RAM usage 0-100 (NEW!)
            gpu_percent: GPU usage 0-100 (NEW!)

        Returns:
            PIL.Image: Icon image
        """
        # Use instance values if not provided
        if cpu_percent is None:
            cpu_percent = self.cpu_percent
        if ram_percent is None:
            ram_percent = self.ram_percent
        if gpu_percent is None:
            gpu_percent = self.gpu_percent

        # Icon size (64x64 for clarity)
        size = 64
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Bar dimensions (3 bars now!)
        bar_width = 10
        bar_height = 42
        bar_spacing = 4
        base_y = 48  # Bottom position
        total_width = bar_width * 3 + bar_spacing * 2
        base_x = (size - total_width) // 2

        # === CPU Bar (left - blue) ===
        cpu_x = base_x
        cpu_bg_y = base_y - bar_height

        draw.rectangle(
            [cpu_x, cpu_bg_y, cpu_x + bar_width, base_y],
            fill='#1a1d24',
            outline='#3b82f6',
            width=1
        )

        cpu_fill_height = int((cpu_percent / 100.0) * bar_height)
        if cpu_fill_height > 0:
            cpu_color = self._get_heat_color(cpu_percent, 'cpu')
            draw.rectangle(
                [cpu_x + 1, base_y - cpu_fill_height, cpu_x + bar_width - 1, base_y - 1],
                fill=cpu_color
            )

        # === GPU Bar (middle - green) ===
        gpu_x = cpu_x + bar_width + bar_spacing
        gpu_bg_y = base_y - bar_height

        draw.rectangle(
            [gpu_x, gpu_bg_y, gpu_x + bar_width, base_y],
            fill='#1a1d24',
            outline='#10b981',
            width=1
        )

        gpu_fill_height = int((gpu_percent / 100.0) * bar_height)
        if gpu_fill_height > 0:
            gpu_color = self._get_heat_color(gpu_percent, 'gpu')
            draw.rectangle(
                [gpu_x + 1, base_y - gpu_fill_height, gpu_x + bar_width - 1, base_y - 1],
                fill=gpu_color
            )

        # === RAM Bar (right - yellow) ===
        ram_x = gpu_x + bar_width + bar_spacing
        ram_bg_y = base_y - bar_height

        draw.rectangle(
            [ram_x, ram_bg_y, ram_x + bar_width, base_y],
            fill='#1a1d24',
            outline='#fbbf24',
            width=1
        )

        ram_fill_height = int((ram_percent / 100.0) * bar_height)
        if ram_fill_height > 0:
            ram_color = self._get_heat_color(ram_percent, 'ram')
            draw.rectangle(
                [ram_x + 1, base_y - ram_fill_height, ram_x + bar_width - 1, base_y - 1],
                fill=ram_color
            )

        # Add small labels below bars
        try:
            font = ImageFont.truetype("consola.ttf", 7)
        except:
            font = ImageFont.load_default()

        # Labels
        draw.text((cpu_x, base_y + 2), "CPU", fill='#3b82f6', font=font)
        draw.text((gpu_x, base_y + 2), "GPU", fill='#10b981', font=font)
        draw.text((ram_x, base_y + 2), "RAM", fill='#fbbf24', font=font)

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

    def update_stats(self, cpu_percent, ram_percent, gpu_percent=0, cpu_temp=0, gpu_temp=0):
        """
        Update CPU/RAM/GPU percentages and temperatures - ENHANCED! 💎

        Args:
            cpu_percent: CPU usage 0-100
            ram_percent: RAM usage 0-100
            gpu_percent: GPU usage 0-100 (optional)
            cpu_temp: CPU temperature in °C (optional)
            gpu_temp: GPU temperature in °C (optional)
        """
        self.cpu_percent = max(0, min(100, cpu_percent))
        self.ram_percent = max(0, min(100, ram_percent))
        self.gpu_percent = max(0, min(100, gpu_percent))
        self.cpu_temp = cpu_temp
        self.gpu_temp = gpu_temp

        if self.icon and self._running:
            # Update icon image with all 3 metrics
            new_icon = self.create_battery_icon(self.cpu_percent, self.ram_percent, self.gpu_percent)
            self.icon.icon = new_icon

            # Update tooltip with detailed stats
            tooltip = f"PC Workman - HCK Labs\n"
            tooltip += f"CPU: {int(self.cpu_percent)}%"
            if self.cpu_temp > 0:
                tooltip += f" ({int(self.cpu_temp)}°C)"
            tooltip += f"\nGPU: {int(self.gpu_percent)}%"
            if self.gpu_temp > 0:
                tooltip += f" ({int(self.gpu_temp)}°C)"
            tooltip += f"\nRAM: {int(self.ram_percent)}%"

            self.icon.title = tooltip

    def _create_menu(self):
        """Create ENHANCED system tray context menu - MSI Afterburner style! 💎"""
        menu_items = [
            item('💻 Show Main Window', self._on_show_monitor, default=True),
            pystray.Menu.SEPARATOR,
            item('🌲 Hardware Sensors', self._on_show_sensors, enabled=self.show_sensors is not None),
            item('📈 Statistics', self._on_show_stats),
            pystray.Menu.SEPARATOR,
            item(f'CPU: {int(self.cpu_percent)}%', lambda: None, enabled=False),
            item(f'GPU: {int(self.gpu_percent)}%', lambda: None, enabled=False),
            item(f'RAM: {int(self.ram_percent)}%', lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item('❌ Exit Program', self._on_quit)
        ]
        return pystray.Menu(*menu_items)

    def _on_show_monitor(self, icon, item):
        """Show main monitor window"""
        self.show_main_window()

    def _on_show_sensors(self, icon, item):
        """Show hardware sensors window - NEW! 🌲"""
        if self.show_sensors:
            self.show_sensors()

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

        # Create initial icon with all 3 metrics
        initial_icon = self.create_battery_icon(self.cpu_percent, self.ram_percent, self.gpu_percent)

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
