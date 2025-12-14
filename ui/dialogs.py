# ui/dialogs.py
"""
Modern About pages with card-based design.
"""

import tkinter as tk
from ui.theme import THEME

def create_about_page(parent):
    """Create modern About page with card layout"""
    frame = tk.Frame(parent, bg=THEME["bg_main"])

    # Container for centered content
    container = tk.Frame(frame, bg=THEME["bg_main"])
    container.place(relx=0.5, rely=0.5, anchor="center", width=500, height=380)

    # Title with neon accent
    title_frame = tk.Frame(container, bg=THEME["bg_main"])
    title_frame.pack(pady=(0, 30))

    title = tk.Label(title_frame, text="About",
                     font=("Consolas", 24, "bold"),
                     bg=THEME["bg_main"],
                     fg=THEME["accent"])
    title.pack()

    # Main info card with border
    card = tk.Frame(container, bg=THEME["bg_panel"], highlightbackground=THEME["accent2"],
                   highlightthickness=1)
    card.pack(fill="both", expand=True, padx=20)

    # App name with gradient-like effect (using accent color)
    app_name = tk.Label(card, text="PC Workman",
                       font=("Consolas", 20, "bold"),
                       bg=THEME["bg_panel"],
                       fg=THEME["accent"])
    app_name.pack(pady=(30, 5))

    # Subtitle
    subtitle = tk.Label(card, text="HCK_Labs",
                       font=("Consolas", 12),
                       bg=THEME["bg_panel"],
                       fg=THEME["muted"])
    subtitle.pack(pady=(0, 25))

    # Description
    desc = tk.Label(card, text="AI-ready system monitor prototype",
                   font=("Consolas", 11),
                   bg=THEME["bg_panel"],
                   fg=THEME["text"])
    desc.pack(pady=(0, 8))

    # Version badge
    version_frame = tk.Frame(card, bg="#1a1d21", highlightbackground=THEME["accent"],
                            highlightthickness=1)
    version_frame.pack(pady=(15, 10))

    version = tk.Label(version_frame, text="v1.0.7 (Guardian UI)",
                      font=("Consolas", 10, "bold"),
                      bg="#1a1d21",
                      fg=THEME["accent"],
                      padx=15, pady=5)
    version.pack()

    # Footer info
    footer = tk.Label(card, text="Monitoring • Analysis • Intelligence",
                     font=("Consolas", 9),
                     bg=THEME["bg_panel"],
                     fg=THEME["muted"])
    footer.pack(pady=(20, 30))

    return frame

def create_about_ai_page(parent):
    """Create modern About AI page with card layout"""
    frame = tk.Frame(parent, bg=THEME["bg_main"])

    # Container for centered content
    container = tk.Frame(frame, bg=THEME["bg_main"])
    container.place(relx=0.5, rely=0.5, anchor="center", width=520, height=400)

    # Title with neon accent
    title_frame = tk.Frame(container, bg=THEME["bg_main"])
    title_frame.pack(pady=(0, 25))

    title = tk.Label(title_frame, text="AI Assistant",
                     font=("Consolas", 24, "bold"),
                     bg=THEME["bg_main"],
                     fg=THEME["accent2"])
    title.pack()

    # Main card
    card = tk.Frame(container, bg=THEME["bg_panel"], highlightbackground=THEME["accent2"],
                   highlightthickness=1)
    card.pack(fill="both", expand=True, padx=20)

    # AI Icon/Name
    ai_name = tk.Label(card, text="🧠 hck_GPT",
                      font=("Consolas", 18, "bold"),
                      bg=THEME["bg_panel"],
                      fg=THEME["accent2"])
    ai_name.pack(pady=(25, 5))

    # Status badge
    status_frame = tk.Frame(card, bg="#0a1f1a", highlightbackground="#00ffc8",
                           highlightthickness=1)
    status_frame.pack(pady=(10, 20))

    status = tk.Label(status_frame, text="● IN DEVELOPMENT",
                     font=("Consolas", 9, "bold"),
                     bg="#0a1f1a",
                     fg="#00ffc8",
                     padx=12, pady=4)
    status.pack()

    # Description
    desc_title = tk.Label(card, text="Local AI Assistant",
                         font=("Consolas", 11, "bold"),
                         bg=THEME["bg_panel"],
                         fg=THEME["text"])
    desc_title.pack(pady=(10, 8))

    # Features list
    features_frame = tk.Frame(card, bg=THEME["bg_panel"])
    features_frame.pack(pady=(0, 10))

    features = [
        "⚡ Real-time system analysis",
        "📊 Performance insights & alerts",
        "💡 Intelligent suggestions",
        "🔮 Predictive monitoring"
    ]

    for feature in features:
        feat_lbl = tk.Label(features_frame, text=feature,
                           font=("Consolas", 10),
                           bg=THEME["bg_panel"],
                           fg=THEME["muted"],
                           anchor="w")
        feat_lbl.pack(pady=3)

    # Coming soon note
    note = tk.Label(card, text="Coming in next releases",
                   font=("Consolas", 9, "italic"),
                   bg=THEME["bg_panel"],
                   fg=THEME["muted"])
    note.pack(pady=(15, 25))

    return frame
