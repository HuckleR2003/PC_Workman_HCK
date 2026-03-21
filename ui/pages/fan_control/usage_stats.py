# ui/components/fans_usage_stats_page.py
"""
PC Workman - FANS Usage Statistics Page
Wykresy intensywności użycia wentylatorów z wyborem przedziału czasowego
"""

import tkinter as tk
from tkinter import ttk
import random
import time
from collections import deque

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class FansUsageStatsPage:
    """
    Strona Usage Statistics - wykresy intensywności wentylatorów
    - Wybór przedziału: NOW (1 min), 1Hr, 3Hrs, 12Hrs
    - Wykresy dla CPU Fan, GPU Fan, Case Fans
    """

    COLORS = {
        "bg": "#0a0e14",
        "card_bg": "#111827",
        "card_border": "#1f2937",
        "text": "#e5e7eb",
        "text_muted": "#6b7280",
        "accent_green": "#10b981",
        "accent_blue": "#3b82f6",
        "accent_purple": "#8b5cf6",
        "accent_orange": "#f59e0b",
        "btn_active": "#1f2937",
        "btn_inactive": "#0d1117",
        "chart_bg": "#0d1117",
        "grid_color": "#1f2937",
    }

    TIME_RANGES = {
        "NOW": {"label": "NOW", "seconds": 60, "description": "Last 1 minute"},
        "1HR": {"label": "1Hr", "seconds": 3600, "description": "Last 1 hour"},
        "3HRS": {"label": "3Hrs", "seconds": 10800, "description": "Last 3 hours"},
        "12HRS": {"label": "12Hrs", "seconds": 43200, "description": "Last 12 hours"},
    }

    def __init__(self, parent, monitor=None):
        self.parent = parent
        self.monitor = monitor
        self.current_range = "NOW"
        self.range_buttons = {}
        self.charts = {}
        self.chart_canvases = {}

        # Dane historyczne (symulowane)
        self.history_data = {
            "cpu": deque(maxlen=720),     # 12h * 60 samples/hr
            "gpu": deque(maxlen=720),
            "case_avg": deque(maxlen=720),
        }

        # Wypełnij początkowe dane
        self._generate_initial_data()

        self._build_page()
        self._start_updates()

    def _generate_initial_data(self):
        """Generuje początkowe dane historyczne"""
        # Symulacja danych z ostatnich 12 godzin
        for i in range(720):
            self.history_data["cpu"].append(random.randint(800, 2200))
            self.history_data["gpu"].append(random.randint(1200, 2800))
            self.history_data["case_avg"].append(random.randint(600, 1200))

    def _build_page(self):
        """Buduje główną stronę"""
        # Header z tytułem
        header = tk.Frame(self.parent, bg=self.COLORS["bg"])
        header.pack(fill="x", padx=20, pady=(15, 5))

        tk.Label(
            header,
            text="USAGE STATISTICS",
            font=("Segoe UI Semibold", 16, "bold"),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"]
        ).pack(side="left")

        tk.Label(
            header,
            text="Fan intensity over time",
            font=("Segoe UI", 10),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text_muted"]
        ).pack(side="left", padx=(15, 0))

        # Time range selector
        self._build_time_selector()

        # Charts container
        charts_frame = tk.Frame(self.parent, bg=self.COLORS["bg"])
        charts_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Dwie kolumny wykresów
        left_charts = tk.Frame(charts_frame, bg=self.COLORS["bg"])
        left_charts.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_charts = tk.Frame(charts_frame, bg=self.COLORS["bg"])
        right_charts.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # CPU Fan chart (lewa góra)
        self._create_chart(left_charts, "cpu", "CPU Fan Intensity", self.COLORS["accent_blue"])

        # GPU Fan chart (lewa dół)
        self._create_chart(left_charts, "gpu", "GPU Fan Intensity", self.COLORS["accent_orange"])

        # Case Fans Average chart (prawa)
        self._create_chart(right_charts, "case_avg", "Case Fans Average", self.COLORS["accent_purple"], tall=True)

    def _build_time_selector(self):
        """Buduje selektor przedziału czasowego"""
        selector_frame = tk.Frame(self.parent, bg=self.COLORS["bg"])
        selector_frame.pack(fill="x", padx=20, pady=(10, 5))

        tk.Label(
            selector_frame,
            text="TIME RANGE:",
            font=("Segoe UI Semibold", 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text_muted"]
        ).pack(side="left", padx=(0, 15))

        # Przyciski wyboru
        buttons_frame = tk.Frame(selector_frame, bg=self.COLORS["bg"])
        buttons_frame.pack(side="left")

        for range_id, range_data in self.TIME_RANGES.items():
            btn = tk.Label(
                buttons_frame,
                text=range_data["label"],
                font=("Segoe UI Semibold", 10),
                bg=self.COLORS["btn_active"] if range_id == self.current_range else self.COLORS["btn_inactive"],
                fg=self.COLORS["accent_green"] if range_id == self.current_range else self.COLORS["text_muted"],
                padx=15,
                pady=6,
                cursor="hand2"
            )
            btn.pack(side="left", padx=2)

            self.range_buttons[range_id] = btn

            # Bind click
            btn.bind("<Button-1>", lambda e, rid=range_id: self._select_range(rid))

            # Hover effects
            def on_enter(e, b=btn, rid=range_id):
                if rid != self.current_range:
                    b.config(bg=self.COLORS["card_border"])

            def on_leave(e, b=btn, rid=range_id):
                if rid != self.current_range:
                    b.config(bg=self.COLORS["btn_inactive"])

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

        # Opis aktualnego zakresu
        self.range_description = tk.Label(
            selector_frame,
            text=self.TIME_RANGES[self.current_range]["description"],
            font=("Segoe UI", 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text_muted"]
        )
        self.range_description.pack(side="left", padx=(20, 0))

    def _select_range(self, range_id):
        """Zmienia wybrany przedział czasowy"""
        if range_id == self.current_range:
            return

        # Aktualizuj przyciski
        for rid, btn in self.range_buttons.items():
            if rid == range_id:
                btn.config(
                    bg=self.COLORS["btn_active"],
                    fg=self.COLORS["accent_green"]
                )
            else:
                btn.config(
                    bg=self.COLORS["btn_inactive"],
                    fg=self.COLORS["text_muted"]
                )

        self.current_range = range_id
        self.range_description.config(text=self.TIME_RANGES[range_id]["description"])

        # Odśwież wykresy
        self._update_all_charts()

    def _create_chart(self, parent, chart_id, title, color, tall=False):
        """Tworzy pojedynczy wykres"""
        card = tk.Frame(parent, bg=self.COLORS["card_bg"])
        card.pack(fill="both", expand=True, pady=5)

        # Tytuł
        header = tk.Frame(card, bg=self.COLORS["card_bg"])
        header.pack(fill="x", padx=15, pady=(10, 5))

        tk.Label(
            header,
            text=title,
            font=("Segoe UI Semibold", 10),
            bg=self.COLORS["card_bg"],
            fg=self.COLORS["text"]
        ).pack(side="left")

        # Aktualne RPM
        current_rpm = list(self.history_data[chart_id])[-1] if self.history_data[chart_id] else 0
        rpm_label = tk.Label(
            header,
            text=f"{current_rpm} RPM",
            font=("Consolas", 11, "bold"),
            bg=self.COLORS["card_bg"],
            fg=color
        )
        rpm_label.pack(side="right")

        # Chart area
        if HAS_MATPLOTLIB:
            chart_height = 2.0 if tall else 1.2
            fig = Figure(figsize=(4, chart_height), dpi=100, facecolor=self.COLORS["chart_bg"])
            ax = fig.add_subplot(111)

            # Stylizacja wykresu
            ax.set_facecolor(self.COLORS["chart_bg"])
            ax.tick_params(colors=self.COLORS["text_muted"], labelsize=7)
            ax.spines['bottom'].set_color(self.COLORS["grid_color"])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color(self.COLORS["grid_color"])
            ax.grid(True, alpha=0.2, color=self.COLORS["grid_color"])

            fig.tight_layout(pad=0.5)

            canvas = FigureCanvasTkAgg(fig, card)
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

            self.charts[chart_id] = {
                "fig": fig,
                "ax": ax,
                "color": color,
                "rpm_label": rpm_label
            }
            self.chart_canvases[chart_id] = canvas

            # Rysuj początkowy wykres
            self._update_chart(chart_id)
        else:
            # Fallback bez matplotlib
            tk.Label(
                card,
                text="(Matplotlib required for charts)",
                font=("Segoe UI", 9),
                bg=self.COLORS["card_bg"],
                fg=self.COLORS["text_muted"]
            ).pack(pady=20)

    def _update_chart(self, chart_id):
        """Aktualizuje pojedynczy wykres"""
        if chart_id not in self.charts:
            return

        chart = self.charts[chart_id]
        ax = chart["ax"]
        color = chart["color"]

        ax.clear()

        # Pobierz dane dla wybranego zakresu
        range_seconds = self.TIME_RANGES[self.current_range]["seconds"]

        # Konwertuj sekundy na liczbę próbek (1 próbka / minutę)
        samples_needed = min(range_seconds // 60, len(self.history_data[chart_id]))

        data = list(self.history_data[chart_id])[-samples_needed:] if samples_needed > 0 else []

        if data:
            x = range(len(data))

            # Wypełniony wykres (area chart)
            ax.fill_between(x, data, alpha=0.3, color=color)
            ax.plot(x, data, color=color, linewidth=1.5)

            # Aktualne RPM
            current_rpm = data[-1]
            chart["rpm_label"].config(text=f"{current_rpm} RPM")

        # Stylizacja
        ax.set_facecolor(self.COLORS["chart_bg"])
        ax.tick_params(colors=self.COLORS["text_muted"], labelsize=7)
        ax.spines['bottom'].set_color(self.COLORS["grid_color"])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(self.COLORS["grid_color"])
        ax.grid(True, alpha=0.2, color=self.COLORS["grid_color"])

        # Odśwież canvas
        if chart_id in self.chart_canvases:
            self.chart_canvases[chart_id].draw()

    def _update_all_charts(self):
        """Aktualizuje wszystkie wykresy"""
        for chart_id in self.charts:
            self._update_chart(chart_id)

    def _start_updates(self):
        """Uruchamia cykliczne aktualizacje"""
        self._add_new_data()

    def _add_new_data(self):
        """Dodaje nowe dane i aktualizuje wykresy"""
        try:
            # Dodaj nowe próbki (symulacja)
            cpu_rpm = list(self.history_data["cpu"])[-1] if self.history_data["cpu"] else 1500
            gpu_rpm = list(self.history_data["gpu"])[-1] if self.history_data["gpu"] else 2000
            case_rpm = list(self.history_data["case_avg"])[-1] if self.history_data["case_avg"] else 900

            # Losowe zmiany
            self.history_data["cpu"].append(max(500, min(2500, cpu_rpm + random.randint(-100, 100))))
            self.history_data["gpu"].append(max(800, min(3000, gpu_rpm + random.randint(-150, 150))))
            self.history_data["case_avg"].append(max(400, min(1500, case_rpm + random.randint(-50, 50))))

            # Aktualizuj wykresy co 5 sekund
            self._update_all_charts()

            # Następna aktualizacja
            self.parent.after(5000, self._add_new_data)
        except tk.TclError:
            # Widget zniszczony
            pass


def create_fans_usage_stats_page(parent, monitor=None):
    """Factory function do tworzenia strony Usage Statistics"""
    return FansUsageStatsPage(parent, monitor)
