# ui/charts.py
"""
Enhanced Interactive Chart with Click Events v1.4.0
- Click to select time point
- Shows vertical marker at selected time
- Displays CPU/GPU/RAM info in tooltip
- Exposes selected timestamp for detail view
- Supports Data View modes (1H, 4H, SESSION)
"""

import time
from matplotlib.figure import Figure
from matplotlib import ticker as mticker
from matplotlib.lines import Line2D
from ui.theme import THEME


class EnhancedMainChart:
    """Interactive chart with click event support"""

    def __init__(self, width=6.4, height=1.6, dpi=90, click_callback=None):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor=THEME["bg_panel"])
        self.ax = self.fig.add_subplot(111)

        # Click callback
        self.click_callback = click_callback

        # Store samples for click detection
        self.samples = []

        # Selected timestamp and data
        self.selected_timestamp = None
        self.selected_data = None
        self.selection_marker = None

        # Info annotation (tooltip)
        self.info_annotation = None

        # Crosshair elements (for hover)
        self.crosshair_vline = None
        self.crosshair_annotation = None

        # Data view mode: 'SESSION', '1H', '4H'
        self.data_view_mode = 'SESSION'

        self._init_style()

        # Create lines
        self.line_cpu, = self.ax.plot([], [], lw=2.6, label="CPU", color=THEME["cpu"])
        self.line_ram, = self.ax.plot([], [], lw=2.2, label="RAM", color=THEME["ram"])
        self.line_gpu, = self.ax.plot([], [], lw=2.2, label="GPU", color=THEME["gpu"])

    def _init_style(self):
        self.ax.set_facecolor(THEME["bg_panel"])
        # Grid
        self.ax.grid(True, color="#111416", linestyle="-", linewidth=0.7)

        # Spines
        for spine in self.ax.spines.values():
            spine.set_color("#16181b")

        self.ax.tick_params(colors=THEME["muted"], labelsize=8)
        self.ax.set_ylim(0, 100)

        # Y axis - percentage
        self.ax.yaxis.set_major_locator(mticker.MultipleLocator(25))
        self.ax.yaxis.set_major_formatter(lambda x, pos: f"{int(x)}%")

        # X axis - time formatting (handle invalid timestamps)
        def format_time(x, pos):
            try:
                if x > 0:
                    return time.strftime("%H:%M:%S", time.localtime(x))
                else:
                    return ""
            except (OSError, ValueError):
                return ""
        self.ax.xaxis.set_major_formatter(format_time)

        self.ax.set_title("", color=THEME["text"], fontsize=10)

    def set_data_view_mode(self, mode):
        """Set data view mode: 'SESSION', '1H', '4H'"""
        self.data_view_mode = mode

    def _filter_samples_by_mode(self, samples):
        """Filter samples based on current data view mode"""
        if not samples or self.data_view_mode == 'SESSION':
            return samples

        current_time = time.time()

        if self.data_view_mode == '1H':
            cutoff = current_time - 3600  # 1 hour
        elif self.data_view_mode == '4H':
            cutoff = current_time - 14400  # 4 hours
        else:
            return samples

        return [s for s in samples if s['timestamp'] >= cutoff]

    def update(self, samples):
        """
        Update chart with new samples

        Args:
            samples: list of dicts with keys timestamp, cpu_percent, ram_percent, gpu_percent
        """
        if not samples:
            return

        self.samples = samples

        # Filter by data view mode
        filtered_samples = self._filter_samples_by_mode(samples)

        if not filtered_samples:
            return

        x = [s["timestamp"] for s in filtered_samples]
        cpu = [s.get("cpu_percent", 0.0) for s in filtered_samples]
        ram = [s.get("ram_percent", 0.0) for s in filtered_samples]
        gpu = [s.get("gpu_percent", 0.0) for s in filtered_samples]

        # Smoothing
        if len(cpu) > 3:
            cpu = self._smooth(cpu)
            ram = self._smooth(ram)
            gpu = self._smooth(gpu)

        # Update lines
        self.line_cpu.set_data(x, cpu)
        self.line_ram.set_data(x, ram)
        self.line_gpu.set_data(x, gpu)

        # Adjust xlim
        try:
            self.ax.set_xlim(min(x), max(x))
        except:
            pass

        # Redraw selection marker if exists
        if self.selected_timestamp is not None:
            self._update_selection_marker()
            self._update_info_display()

    def _smooth(self, arr, k=1):
        """Simple moving average smoothing"""
        out = []
        n = len(arr)
        for i in range(n):
            lo = max(0, i - k)
            hi = min(n, i + k + 1)
            out.append(sum(arr[lo:hi]) / (hi - lo))
        return out

    def on_click(self, event):
        """Handle mouse click on chart"""
        if event.inaxes != self.ax:
            return

        if event.xdata is None:
            return

        # Find closest timestamp
        clicked_time = event.xdata
        closest_sample = self._find_closest_sample(clicked_time)

        if closest_sample:
            self.selected_timestamp = closest_sample['timestamp']
            self.selected_data = closest_sample
            self._update_selection_marker()
            self._update_info_display()

            # Call callback if provided
            if self.click_callback:
                self.click_callback(closest_sample)

    def _find_closest_sample(self, clicked_time):
        """Find sample closest to clicked time"""
        if not self.samples:
            return None

        closest = min(
            self.samples,
            key=lambda s: abs(s['timestamp'] - clicked_time)
        )

        return closest

    def _update_selection_marker(self):
        """Draw vertical line at selected timestamp"""
        # Remove old marker
        if self.selection_marker:
            try:
                self.selection_marker.remove()
            except:
                pass

        if self.selected_timestamp is None:
            return

        # Draw new marker
        self.selection_marker = self.ax.axvline(
            x=self.selected_timestamp,
            color=THEME["accent"],
            linestyle="--",
            linewidth=1.5,
            alpha=0.8,
            label="Selected"
        )

    def _update_info_display(self):
        """Display info box with CPU/GPU/RAM at selected time - MSI Afterburner style"""
        # Remove old annotation
        if self.info_annotation:
            try:
                self.info_annotation.remove()
            except:
                pass
            self.info_annotation = None

        if not self.selected_data:
            return

        # Format time - compact
        timestamp_str = time.strftime("%H:%M:%S", time.localtime(self.selected_data['timestamp']))

        # Get values
        cpu = self.selected_data.get('cpu_percent', 0)
        ram = self.selected_data.get('ram_percent', 0)
        gpu = self.selected_data.get('gpu_percent', 0)

        # Create ultra-compact info text (MSI Afterburner style)
        info_text = f"{timestamp_str} | CPU {cpu:.0f}% | RAM {ram:.0f}% | GPU {gpu:.0f}%"

        # Add annotation at top-right corner (like MSI Afterburner)
        self.info_annotation = self.ax.text(
            0.98, 0.98,
            info_text,
            transform=self.ax.transAxes,
            fontsize=7,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=dict(
                boxstyle='round,pad=0.3',
                facecolor='#0a0c0e',
                edgecolor='#FF6B35',
                alpha=0.92,
                linewidth=1.2
            ),
            color='#FFB84D',
            weight='bold',
            family='Consolas'
        )

    def clear_selection(self):
        """Clear selected timestamp"""
        self.selected_timestamp = None
        self.selected_data = None

        if self.selection_marker:
            try:
                self.selection_marker.remove()
                self.selection_marker = None
            except:
                pass

        if self.info_annotation:
            try:
                self.info_annotation.remove()
                self.info_annotation = None
            except:
                pass

    def get_selected_data(self):
        """Get data for selected timestamp"""
        if self.selected_timestamp is None or not self.samples:
            return None

        # Find exact sample
        for sample in self.samples:
            if abs(sample['timestamp'] - self.selected_timestamp) < 0.5:
                return sample

        return None


# Alias for compatibility
MainChart = EnhancedMainChart
