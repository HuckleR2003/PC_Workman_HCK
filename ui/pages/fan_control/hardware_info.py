# ui/components/fans_hardware_page.py
"""
PC Workman - FANS Hardware Info Page
Kompaktowe informacje o wentylatorach w stylu Snyk Evo
"""

import tkinter as tk
from tkinter import ttk
import random

try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError:
    Image = None
    ImageTk = None
    ImageDraw = None


class FansHardwarePage:
    """
    Strona FANS - Hardware Info
    Wyświetla informacje o wentylatorach:
    - Główne: CPU Fan, GPU Fan (po lewej)
    - Case Fans: 4 sloty (po prawej)
    - Pod spodem: modele CPU/GPU i info o wentylatorach
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
        "gauge_bg": "#1f2937",
        "gauge_track": "#374151",
    }

    def __init__(self, parent, monitor=None):
        self.parent = parent
        self.monitor = monitor
        self.fan_gauges = {}
        self.rpm_labels = {}
        self.info_labels = {}

        # Symulowane dane wentylatorów (w prawdziwej app - z hardware sensors)
        self.fan_data = {
            "cpu": {"name": "CPU Fan", "rpm": 1250, "max_rpm": 2500, "model": "Noctua NH-D15"},
            "gpu": {"name": "GPU Fan", "rpm": 1800, "max_rpm": 3000, "model": "Stock Cooler"},
            "case1": {"name": "Front 1", "rpm": 900, "max_rpm": 1500, "model": "Arctic P12"},
            "case2": {"name": "Front 2", "rpm": 920, "max_rpm": 1500, "model": "Arctic P12"},
            "case3": {"name": "Rear", "rpm": 850, "max_rpm": 1200, "model": "be quiet!"},
            "case4": {"name": "Top", "rpm": 0, "max_rpm": 1500, "model": "Not installed"},
        }

        self._build_page()
        self._start_updates()

    def _build_page(self):
        """Buduje główną stronę"""
        # Header
        header = tk.Frame(self.parent, bg=self.COLORS["bg"])
        header.pack(fill="x", padx=20, pady=(15, 10))

        tk.Label(
            header,
            text="FANS - Hardware Info",
            font=("Segoe UI Semibold", 16, "bold"),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"]
        ).pack(side="left")

        tk.Label(
            header,
            text="Real-time fan monitoring",
            font=("Segoe UI", 10),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text_muted"]
        ).pack(side="left", padx=(15, 0))

        # Główny kontener na karty wentylatorów
        fans_container = tk.Frame(self.parent, bg=self.COLORS["bg"])
        fans_container.pack(fill="both", expand=True, padx=20, pady=10)

        # LEWA STRONA - Główne wentylatory (CPU, GPU)
        left_frame = tk.Frame(fans_container, bg=self.COLORS["bg"])
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(
            left_frame,
            text="MAIN COOLING",
            font=("Segoe UI Semibold", 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["accent_green"]
        ).pack(anchor="w", pady=(0, 8))

        # CPU Fan gauge
        self._create_main_fan_card(left_frame, "cpu", "CPU Fan", self.COLORS["accent_blue"])

        # GPU Fan gauge
        self._create_main_fan_card(left_frame, "gpu", "GPU Fan", self.COLORS["accent_orange"])

        # PRAWA STRONA - Case Fans (4 sloty w jednej linii)
        right_frame = tk.Frame(fans_container, bg=self.COLORS["bg"])
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        tk.Label(
            right_frame,
            text="CASE FANS",
            font=("Segoe UI Semibold", 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["accent_purple"]
        ).pack(anchor="w", pady=(0, 8))

        # Kontener na 4 małe karty case fans
        case_fans_row = tk.Frame(right_frame, bg=self.COLORS["bg"])
        case_fans_row.pack(fill="x")

        for i, fan_id in enumerate(["case1", "case2", "case3", "case4"]):
            self._create_case_fan_card(case_fans_row, fan_id, self.fan_data[fan_id]["name"])

        # DOLNA SEKCJA - Modele i szczegóły
        self._build_details_section()

    def _create_main_fan_card(self, parent, fan_id, title, accent_color):
        """Tworzy kartę głównego wentylatora (CPU/GPU) z gauge"""
        card = tk.Frame(parent, bg=self.COLORS["card_bg"], relief="flat", bd=0)
        card.pack(fill="x", pady=5)

        # Wewnętrzny padding
        inner = tk.Frame(card, bg=self.COLORS["card_bg"])
        inner.pack(fill="both", expand=True, padx=15, pady=12)

        # Lewa część - gauge
        gauge_frame = tk.Frame(inner, bg=self.COLORS["card_bg"])
        gauge_frame.pack(side="left")

        # Canvas dla gauge (półkole)
        gauge_size = 80
        canvas = tk.Canvas(
            gauge_frame,
            width=gauge_size,
            height=gauge_size // 2 + 15,
            bg=self.COLORS["card_bg"],
            highlightthickness=0
        )
        canvas.pack()

        self.fan_gauges[fan_id] = {
            "canvas": canvas,
            "size": gauge_size,
            "color": accent_color
        }

        # Rysuj początkowy gauge
        self._draw_gauge(fan_id, self.fan_data[fan_id]["rpm"], self.fan_data[fan_id]["max_rpm"])

        # Prawa część - informacje
        info_frame = tk.Frame(inner, bg=self.COLORS["card_bg"])
        info_frame.pack(side="left", fill="both", expand=True, padx=(15, 0))

        # Tytuł
        tk.Label(
            info_frame,
            text=title,
            font=("Segoe UI Semibold", 11),
            bg=self.COLORS["card_bg"],
            fg=self.COLORS["text"]
        ).pack(anchor="w")

        # RPM
        rpm_label = tk.Label(
            info_frame,
            text=f"{self.fan_data[fan_id]['rpm']} RPM",
            font=("Consolas", 18, "bold"),
            bg=self.COLORS["card_bg"],
            fg=accent_color
        )
        rpm_label.pack(anchor="w")
        self.rpm_labels[fan_id] = rpm_label

        # Procent
        pct = int((self.fan_data[fan_id]["rpm"] / self.fan_data[fan_id]["max_rpm"]) * 100)
        pct_label = tk.Label(
            info_frame,
            text=f"{pct}% of max",
            font=("Segoe UI", 9),
            bg=self.COLORS["card_bg"],
            fg=self.COLORS["text_muted"]
        )
        pct_label.pack(anchor="w")

    def _create_case_fan_card(self, parent, fan_id, title):
        """Tworzy kompaktową kartę case fan"""
        card = tk.Frame(parent, bg=self.COLORS["card_bg"], relief="flat", bd=0)
        card.pack(side="left", fill="both", expand=True, padx=2, pady=2)

        inner = tk.Frame(card, bg=self.COLORS["card_bg"])
        inner.pack(fill="both", expand=True, padx=8, pady=8)

        # Mini gauge
        gauge_size = 50
        canvas = tk.Canvas(
            inner,
            width=gauge_size,
            height=gauge_size // 2 + 10,
            bg=self.COLORS["card_bg"],
            highlightthickness=0
        )
        canvas.pack()

        self.fan_gauges[fan_id] = {
            "canvas": canvas,
            "size": gauge_size,
            "color": self.COLORS["accent_purple"]
        }

        # Rysuj gauge
        self._draw_gauge(fan_id, self.fan_data[fan_id]["rpm"], self.fan_data[fan_id]["max_rpm"])

        # Nazwa
        tk.Label(
            inner,
            text=title,
            font=("Segoe UI", 8),
            bg=self.COLORS["card_bg"],
            fg=self.COLORS["text"]
        ).pack()

        # RPM (mały)
        rpm = self.fan_data[fan_id]["rpm"]
        rpm_text = f"{rpm}" if rpm > 0 else "N/A"
        rpm_label = tk.Label(
            inner,
            text=rpm_text,
            font=("Consolas", 10, "bold"),
            bg=self.COLORS["card_bg"],
            fg=self.COLORS["accent_purple"] if rpm > 0 else self.COLORS["text_muted"]
        )
        rpm_label.pack()
        self.rpm_labels[fan_id] = rpm_label

    def _draw_gauge(self, fan_id, rpm, max_rpm):
        """Rysuje gauge (półkole) dla wentylatora"""
        gauge_data = self.fan_gauges.get(fan_id)
        if not gauge_data:
            return

        canvas = gauge_data["canvas"]
        size = gauge_data["size"]
        color = gauge_data["color"]

        canvas.delete("all")

        # Parametry
        cx, cy = size // 2, size // 2 + 5
        radius = size // 2 - 5
        thickness = 6 if size > 60 else 4

        # Tło gauge (szary łuk)
        canvas.create_arc(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            start=180, extent=180,
            outline=self.COLORS["gauge_track"],
            width=thickness,
            style="arc"
        )

        # Wartość gauge (kolorowy łuk)
        if max_rpm > 0:
            pct = min(rpm / max_rpm, 1.0)
            extent = 180 * pct

            canvas.create_arc(
                cx - radius, cy - radius,
                cx + radius, cy + radius,
                start=180, extent=extent,
                outline=color,
                width=thickness,
                style="arc"
            )

        # Tekst procent (tylko dla dużych)
        if size > 60:
            pct_text = f"{int(pct * 100)}%" if max_rpm > 0 else "N/A"
            canvas.create_text(
                cx, cy - 5,
                text=pct_text,
                font=("Consolas", 11, "bold"),
                fill=color
            )

    def _build_details_section(self):
        """Buduje sekcję ze szczegółami - modele CPU/GPU i info o wentylatorach"""
        details = tk.Frame(self.parent, bg=self.COLORS["bg"])
        details.pack(fill="x", padx=20, pady=(15, 10))

        # Separator
        sep = tk.Frame(details, bg=self.COLORS["card_border"], height=1)
        sep.pack(fill="x", pady=(0, 15))

        # Dwie kolumny
        columns = tk.Frame(details, bg=self.COLORS["bg"])
        columns.pack(fill="x")

        # LEWA KOLUMNA - CPU/GPU Models
        left_col = tk.Frame(columns, bg=self.COLORS["bg"])
        left_col.pack(side="left", fill="both", expand=True)

        tk.Label(
            left_col,
            text="COMPONENT MODELS",
            font=("Segoe UI Semibold", 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["accent_green"]
        ).pack(anchor="w", pady=(0, 8))

        # CPU Model
        self._create_model_row(left_col, "CPU Cooler:", self.fan_data["cpu"]["model"])
        self._create_model_row(left_col, "GPU Cooler:", self.fan_data["gpu"]["model"])

        # PRAWA KOLUMNA - Case Fan Models
        right_col = tk.Frame(columns, bg=self.COLORS["bg"])
        right_col.pack(side="right", fill="both", expand=True)

        tk.Label(
            right_col,
            text="CASE FAN MODELS",
            font=("Segoe UI Semibold", 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["accent_purple"]
        ).pack(anchor="w", pady=(0, 8))

        for fan_id in ["case1", "case2", "case3", "case4"]:
            name = self.fan_data[fan_id]["name"]
            model = self.fan_data[fan_id]["model"]
            self._create_model_row(right_col, f"{name}:", model)

    def _create_model_row(self, parent, label, value):
        """Tworzy wiersz z etykietą i wartością modelu"""
        row = tk.Frame(parent, bg=self.COLORS["bg"])
        row.pack(fill="x", pady=2)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text_muted"],
            width=12,
            anchor="w"
        ).pack(side="left")

        tk.Label(
            row,
            text=value,
            font=("Segoe UI Semibold", 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            anchor="w"
        ).pack(side="left")

    def _start_updates(self):
        """Uruchamia cykliczne aktualizacje danych"""
        self._update_data()

    def _update_data(self):
        """Aktualizuje dane wentylatorów (symulacja)"""
        try:
            # Symulacja zmian RPM (w prawdziwej app - odczyt z hardware)
            for fan_id, data in self.fan_data.items():
                if data["max_rpm"] > 0 and data["rpm"] > 0:
                    # Losowa zmiana +/- 50 RPM
                    change = random.randint(-50, 50)
                    new_rpm = max(500, min(data["max_rpm"], data["rpm"] + change))
                    self.fan_data[fan_id]["rpm"] = new_rpm

                    # Aktualizuj gauge
                    self._draw_gauge(fan_id, new_rpm, data["max_rpm"])

                    # Aktualizuj label RPM
                    if fan_id in self.rpm_labels:
                        if fan_id.startswith("case"):
                            self.rpm_labels[fan_id].config(text=f"{new_rpm}")
                        else:
                            self.rpm_labels[fan_id].config(text=f"{new_rpm} RPM")

            # Następna aktualizacja za 2 sekundy
            self.parent.after(2000, self._update_data)
        except tk.TclError:
            # Widget został zniszczony
            pass


def create_fans_hardware_page(parent, monitor=None):
    """Factory function do tworzenia strony FANS Hardware Info"""
    return FansHardwarePage(parent, monitor)
