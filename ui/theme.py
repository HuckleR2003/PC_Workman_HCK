# ui/theme.py
# Afterburner Neon theme for PC_Workman_HCK UI (v1.0.7 Guardian UI)

THEME = {
    # Window
    "win_width": 750,
    "win_height": 500,
    # Backgrounds
    "bg_main": "#0b0d10",
    "bg_panel": "#0f1114",
    "bg_sidebar": "#071013",
    # Accents
    "accent": "#00ffc8",     # neon mint (headers)
    "accent2": "#00a3ff",    # neon blue
    "cpu": "#d94545",        # bordowy-red (slightly muted)
    "gpu": "#4b9aff",
    "ram": "#ffd24a",        # warm yellow
    "text": "#e6eef6",
    "muted": "#91a1ab",
    # Sizes and fonts
    "panel_radius": 8,
    "font_family": "Consolas",
    "font_small": ("Consolas", 9),
    "font_base": ("Consolas", 11),
    "font_large": ("Consolas", 13, "bold"),
    # Sidebar dimensions (collapsed/expanded)
    "sidebar_collapsed": 24,
    "sidebar_expanded": 120,
    # Animation
    "sidebar_anim_step": 8,
    "sidebar_anim_delay": 12,  # ms between steps
    "font_family": "Inter"
}

# LED gradient maps for CPU/GPU/RAM
LED_CPU_MAP = [
    "#14345c", "#1a4d80", "#2067a5", "#2780ca",
    "#2d98ef", "#28d3df", "#22f0b0", "#1bff6a",
    "#d6ff48", "#ffcf3a", "#ff9c2b", "#ff5c22",
    "#ff2a1a", "#e10f0f", "#c1000f", "#a2000c"
]

LED_GPU_MAP = [
    "#14224c", "#1b3782", "#214db6", "#2b63e9",
    "#2fc4ef", "#26fffa"
]

LED_RAM_MAP = [
    "#403500", "#6d5200", "#a67a00", "#dca100",
    "#ffd24a", "#ffe77b"
]
