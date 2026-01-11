# PC_Workman 1.6.1 🖥️

**Real-time PC monitoring + AI diagnostics.**
![Status](https://img.shields.io/badge/Status-Active%20Development-green) 
![Version](https://img.shields.io/badge/Version-1.5.7-blue) 
![Python](https://img.shields.io/badge/Python-3.9+-brightgreen) 
![License](https://img.shields.io/badge/License-MIT-blue)
-
## Overview
PC_Workman is a real-time system monitoring tool built in Python. It combines live performance diagnostics, AI-assisted analysis, and a modular architecture designed for intelligent system optimization.

**What it does:**
- Real-time CPU, GPU, RAM, and network monitoring
- Process intelligence (identifies what's consuming resources)
- AI-powered diagnostics via hck_GPT integration
- Historical trend analysis (see patterns over time)
- Gaming analytics with bottleneck detection

**Why it's different:**
- Traditional tools show "CPU: 87%" → PC_Workman explains *why*
- Time-travel diagnostics → click any historical point to see what was running
- Voltage spike detection → unique feature nobody else has
- Built for understanding, not just watching
-
## 🚀 Quick Start

### Windows Users (Easiest)
```
1. Download PC_Workman.exe from Releases
2. Double-click
3. Done ✅
```

**[Get Latest Release](https://github.com/HuckleR2003/PC_Workman_HCK/releases)**

### Developers
```bash
git clone https://github.com/HuckleR2003/PC_Workman_HCK.git
cd PC_Workman_HCK
pip install -r requirements.txt
python startup.py
```

Full setup guide: **[GETTING_STARTED.md](./GETTING_STARTED.md)**
-
## Features

### Core Monitoring
- ✅ Real-time CPU, GPU, RAM tracking
- ✅ Network bandwidth per-application
- ✅ Process identification and labeling
- ✅ Temperature monitoring with trends
- ✅ Historical data logging (daily, weekly, monthly)

### Intelligence
- ✅ hck_GPT AI-powered analysis
- ✅ Gaming analytics with FPS tracking
- ✅ Bottleneck detection (CPU vs GPU limited)
- ✅ Pattern detection and recommendations
- ✅ Safe system optimization with rollback

### Interface
- ✅ Modern dashboard (Apple-inspired design)
- ✅ Ultra-compact information density
- ✅ Color-coded process lists
- ✅ Interactive charts and metrics
- ✅ Click-to-investigate functionality

### Coming Soon
- Official .exe installer (v1.6.0)
- Voltage spike correlation (v1.6.0)
- Real temperature sensors (v1.5.1)
- ML pattern detection (v2.0)
- Predictive maintenance alerts (v2.0)
-
## Architecture
Modular, scalable design:
```
PC_Workman/
├── core/              # Real-time data collection & analysis
├── hck_gpt/           # AI diagnostics engine
├── ui/                # Tkinter + Matplotlib interface
├── hck_stats_engine/  # Statistical aggregation & trends
├── settings/          # Configuration files
├── data/
│   ├── logs/          # CSV logs (raw, hourly, daily, weekly, monthly)
│   └── cache/         # Runtime cache & process patterns
└── utils/             # System utilities & helpers
```

**Design principles:**
- Dynamic component registry (auto-registration)
- Seamless inter-module communication
- Designed for future expansion
- Educational value (demonstrates Python best practices)
-

## What's New (1.6.1) - CURRENT
Fan Dashboard Evolution - Complete overhaul (3 iterations in one night!) - General fixes
### Others
-Redesigned from scratch with high market tools research - inspired UI.
-Beautiful purple gradient fan curve graph with interactive drag-and-drop points
-Compact 2x2 fan status cards with real-time RPM monitoring & connection status
-Streamlined profile system (Default, Silent, AI, P1, P2)
-Smart profile saving to data/profiles/ with JSON export/import
-Removed clutter - deleted right panel, focused on what matters
-40% smaller graph height for better space utilization
### ✪ Main Window UX Polish
-Fixed process CPU/RAM calculations (now shows system-relative %, not per-core)
Removed padding between navigation tabs for cleaner look
Killed animated gradients for better performance
Stripped unnecessary descriptive texts
### ! ✪ NEW: Floating System Monitor Widget ✪
Always-on-top overlay in top-right corner (outside main window!)
Real-time CPU/RAM/GPU usage with color-coded alerts
Draggable, minimizable, frameless design
Runs independently - keep it visible while working
Launch from Navigation menu → "Floating Monitor"
### ✪ Codebase Cleanup
Removed deprecated fan dashboard versions (ai, pro, ultra)
Consolidated to single fan_dashboard.py - 3 files deleted, ~100KB saved
Purged all __pycache__ and .pyc files
Fixed broken imports after cleanup

## What's New (v1.5.7)
### Modern Dashboard Redesign
- Apple-inspired flat design with gradient accents
- Ultra-compact TOP 5 process lists
- Side-by-side CPU/RAM indicators
- Color-coded visual hierarchy
- 40% more information density
### Hardware Health Monitoring
- Three-column layout (CPU | RAM | GPU)
- Real hardware names (actual Intel/AMD/NVIDIA)
- Intelligent load classification (Normal → Critical)
- Temperature bars with heat-based coloring
### Gaming Analytics
- Per-game performance tracking
- FPS correlation with system load
- Bottleneck detection
- Thermal signature per game
### Optimization Tools
- Windows services management
- Gaming mode toggle
- Startup programs cleanup
- Safe system optimizations with rollback


## 📁 Project Structure
```
HCK_Labs/PC_Workman_HCK/
├── core/
│   ├── __init__.py
│   ├── analyzer.py      # Data analysis & trends
│   ├── logger.py        # File logging system
│   ├── monitor.py       # Real-time data collection
│   └── scheduler.py     # Background scheduler
├── hck_gpt/
│   ├── __init__.py
│   ├── ai_logic.py      # AI analysis algorithms
│   ├── detector.py      # Pattern detection
│   ├── hck_gpt.py       # Main AI module
│   └── model_cache/     # Cached AI models
├── ui/
│   ├── main_window.py   # Main interface
│   ├── charts.py        # Matplotlib charts
│   ├── dialogs.py       # Popup dialogs
│   └── theme.py         # UI theming
├── hck_stats_engine/
│   ├── avg_calculator.py    # Statistical calculations
│   ├── time_utils.py        # Time handling
│   └── trend_analysis.py    # Trend detection
├── settings/
│   ├── config.json      # Main configuration
│   ├── paths.json       # Path definitions
│   └── user_prefs.json  # User preferences
├── data/
│   ├── logs/            # CSV data files
│   │   ├── raw_usage.csv
│   │   ├── minute_avg.csv
│   │   ├── hourly_usage.csv
│   │   ├── daily_usage.csv
│   │   ├── weekly_usage.csv
│   │   └── monthly_usage.csv
│   └── cache/           # Runtime cache
├── tests/
│   ├── test_analyzer.py
│   ├── test_monitor.py
│   └── test_avg_calculator.py
├── docs/
│   ├── TECHNICAL.md
│   └── screenshots/
├── CHANGELOG.md
├── GETTING_STARTED.md
├── requirements.txt
├── setup.py
├── startup.py
└── import_core.py
```
-
## 🛠️ Installation

### Requirements
- **Python 3.9+** (or use .exe)
- **Windows 10+** (Linux/Mac support coming)
- **RAM:** 200MB minimum
- **Disk:** 300MB (if using .exe installer)

### From Source
```bash
# Clone repository
git clone https://github.com/HuckleR2003/PC_Workman_HCK.git
cd PC_Workman_HCK

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
python startup.py
```

### From .exe
[Download from Releases](https://github.com/HuckleR2003/PC_Workman_HCK/releases) → Double-click → Done
-
## 📖 Usage
### First Launch
1. Dashboard opens showing real-time metrics
2. Give it 5 seconds to collect initial data
3. CPU/RAM/GPU bars populate
4. Click tabs to explore features

### Main Tabs
- **Dashboard** - Real-time overview
- **Your PC** - Hardware health & component status
- **Fan Control** - Custom fan curves (advanced)
- **Network** - Per-app bandwidth usage
- **Gaming** - Game-specific analytics

### Understanding the Data
- **Green (0-30%)** - Normal operation
- **Yellow (30-60%)** - Moderate load
- **Orange (60-85%)** - Heavy load
- **Red (85%+)** - Critical

Click any process to see more details.
-
## 📈 Data & Privacy

### What's Collected
- CPU/GPU/RAM usage (on your device only)
- Process names (to identify running applications)
- Temperature readings (from hardware sensors)
- Network usage (local tracking)

### Where It's Stored
- **Local only:** `/data/logs/` directory
- **No cloud:** Everything stays on your PC
- **No telemetry:** Zero tracking or analytics
- **You control it:** Delete anytime

### Privacy Assurance
- 100% local operation
- No data transmission
- No user tracking
- Open source (code is auditable)
-
## 🗂️ Versioning

| Version | Status | Key Features |
|---------|--------|--------------|
| v1.0.0 | Released | Basic architecture |
| v1.0.6 | Stable | First working UI |
| v1.3.3 | Released | hck_GPT integration |
| v1.4.0 | Released | System tray, enhanced UI |
| **v1.5.7** | **Current** | **Modern dashboard, hardware monitoring** |
| v1.6.0 | **Q1 2026** | Stable release, .exe installer |
| v2.0.0 | **Q2 2026** | ML patterns, advanced gaming |

**[Full Changelog](./CHANGELOG.md)**
-
## 🤝 Contributing

### For Users
- Found a bug? [Open Issue](https://github.com/HuckleR2003/PC_Workman_HCK/issues)
- Have an idea? [Start Discussion](https://github.com/HuckleR2003/PC_Workman_HCK/discussions)
- Want to help? [See CONTRIBUTING.md](./CONTRIBUTING.md)

### For Developers
- We welcome pull requests
- Follow existing code style
- Include tests for new features
- Update documentation
-
## 💻 System Requirements

**Minimum:**
- Python 3.9+
- Windows 10
- 200MB RAM
- 300MB disk space

**Recommended:**
- Python 3.11+
- Windows 11
- 500MB+ RAM
- SSD storage

**For Gaming Analytics:**
- NVIDIA/AMD GPU drivers updated
- DirectX 12 compatible system
-
## 📚 Documentation

- **[GETTING_STARTED.md](./GETTING_STARTED.md)** - Installation & setup guide
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history & updates
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - How to contribute
- **[docs/TECHNICAL.md](./docs/TECHNICAL.md)** - Architecture deep dive (coming)
-
## 👤 About

**Marcin Firmuga** | Software Engineer

Order picker by day, programmer by night.

- **GitHub:** [HuckleR2003](https://github.com/HuckleR2003)
- **LinkedIn:** [Marcin Firmuga](https://linkedin.com/in/marcinfirmuga/)
- **Email:** firmuga.marcin.s@gmail.com

Part of **[HCK_Labs](https://github.com/HuckleR2003/HCK_Labs)** initiative.
-
## 📄 License

**MIT License** © 2025 HCK_Labs / Marcin Firmuga
Free for personal and commercial use. Attribution appreciated.
-
**Ship what you have. Improve it later.** 💙