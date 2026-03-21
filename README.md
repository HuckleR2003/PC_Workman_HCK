# PC_Workman 1.6.8

**Real-time PC monitoring with AI diagnostics**

![Status](https://img.shields.io/badge/Status-Active%20Development-green)
![Version](https://img.shields.io/badge/Version-1.6.8-blue)
![Python](https://img.shields.io/badge/Python-3.9+-brightgreen) 
![License](https://img.shields.io/badge/License-MIT-blue)

## Overview

PC_Workman is a real-time system monitor built over 800 hours on hardware that peaked at 94°C during development. It answers the question most monitoring tools ignore: not just WHAT is happening, but WHY.

![PC_Workman Demo](https://github.com/user-attachments/assets/fd2e9ed3-7b61-4c21-91df-7b41d66495fb)

**Core features:**
- Real-time CPU, GPU, RAM, and network monitoring
- Process intelligence (identifies what's consuming resources)
- AI-powered diagnostics via hck_GPT integration
- Historical trend analysis with time-travel capability
- Gaming analytics with bottleneck detection

**What makes it different:**

Traditional monitors show "CPU: 87%" and stop there. PC_Workman shows CPU at 87%, tells you which process caused it, when it started, and what the historical pattern looks like. Click any point in history to see what was running at that exact moment.

Features nobody else has: voltage spike detection with anomaly correlation, local pattern learning (no cloud), 7-day recurring habit detection.

Built for understanding system behavior, not just watching numbers change.

## Roadmap to Microsoft Store

PC_Workman v2.0 is being prepared for Microsoft Store publication (Q3 2026).

**Current progress:**
- v1.6.8 stable release
- [v1.7.9 roadmap](https://github.com/users/HuckleR2003/projects/3/views/1) (16 features planned)
- [Public project board](https://github.com/users/HuckleR2003/projects/3/views/1)
- [Development updates](https://github.com/HuckleR2003/PC_Workman_HCK/discussions/13)

**Why Microsoft Store:**
- Easier discovery (1B+ Windows users)
- One-click installation
- Automatic updates
- No SmartScreen warnings

**What's coming:**
- TURBO BOOST mode (16 optimization features)
- Auto-update notifications
- Enhanced UI/UX
- Local AI integration
- MSIX packaging

Read more: [Building for Microsoft Store](https://medium.com/@MarcinFirmuga/pc-workman-building-a-system-monitor-for-microsoft-store-a7e989c0e059)

Track progress: [v2.0 Milestone](https://github.com/users/HuckleR2003/projects/3/views/1)

## Quick Start

### Windows Users (Easiest)

1. Download PC_Workman.exe from [Releases](https://github.com/HuckleR2003/PC_Workman_HCK/releases)
2. Double-click
3. Done

### Developers

```bash
git clone https://github.com/HuckleR2003/PC_Workman_HCK.git
cd PC_Workman_HCK
pip install -r requirements.txt
python startup.py
```

Full setup guide: [GETTING_STARTED.md](./GETTING_STARTED.md)

## Features

### Core Monitoring
- Real-time CPU, GPU, RAM tracking
- Network bandwidth per application
- Process identification and labeling
- Temperature monitoring with trends
- Historical data logging (daily, weekly, monthly)

### Intelligence (hck_GPT)
- Local insights engine: habit tracking, anomaly awareness, personalized analysis
- "Today Report" with usage chart, top processes, and alert status
- 7-day recurring pattern detection (games, browsers, dev tools)
- Spike and anomaly reporting from Stats Engine events
- Gaming analytics with FPS tracking
- Bottleneck detection (CPU vs GPU limited)
- Safe system optimization with rollback

### Interface
- Modern dashboard (Apple-inspired design)
- Ultra-compact information density
- Color-coded process lists
- Interactive charts and metrics
- Click-to-investigate functionality

### Coming Soon
- ML pattern detection (v2.0)
- Predictive maintenance alerts (v2.0)
- Microsoft Store release (Q3 2026)

## Architecture

PC_Workman uses a modular, threaded architecture optimized for low resource usage:

```
PC_Workman/
├── core/              # Background-threaded system monitoring
├── hck_gpt/           # Local AI insights engine (no external API)
├── hck_stats_engine/  # SQLite pipeline: minute/hourly/daily/monthly aggregation
├── ui/
│   ├── windows/       # Main window modes (expanded, minimal)
│   ├── components/    # Reusable widgets (charts, LED bars, tooltips)
│   └── pages/         # Full-page views (monitoring, fan control)
├── data/
│   ├── logs/          # CSV logs (raw, hourly, daily, weekly, monthly)
│   ├── cache/         # Runtime cache & process patterns
│   └── hck_stats.db   # SQLite long-term storage (WAL mode)
└── tests/             # Unit tests
```

**Design principles:**
- Dynamic component registry with auto-registration
- Background thread isolation (GUI never blocks on system calls)
- WAL mode SQLite for concurrent read/write
- Graceful degradation (SQLite failure falls back to CSV)
- Widget reuse pattern (eliminates destroy/recreate overhead)

## What's New [1.6.8] - 2026-02-17 - CURRENT

### hck_GPT Intelligence System
- Local insights engine: habit tracking, anomaly awareness, personalized teasers
- "Today Report" button with detailed session analysis
- Today Report includes: session/lifetime uptime, CPU/GPU/RAM chart, top processes, alert status
- 7-day recurring pattern detection with context-aware messages
- New commands: `stats`, `alerts`, `insights`, `teaser` (Polish and English)
- Smooth gradient banner with auto-greeting and periodic insight ticker

### HCK Stats Engine v2 (SQLite Long-Term Storage)

**Data Pipeline:**
- SQLite-based aggregation: minute → hourly → daily → weekly → monthly
- Process tracking: per-hour and per-day CPU/RAM breakdown per process
- WAL mode for concurrent UI reads and scheduler writes
- Automatic pruning: 7 days of minute data, 90 days of hourly, forever for daily+
- Graceful degradation: SQLite failure falls back to CSV logging
- New modules: `db_manager`, `aggregator`, `process_aggregator`, `query_api`, `events`

**In-memory accumulator pattern:**
```python
{(hour_ts, process_name): {cpu_sum, cpu_max, ram_sum, count, active_secs}}
```
- `accumulate_second()`: lightweight dict updates every second
- `flush_hourly_processes()`: batch write at hour boundary
- `aggregate_daily_processes()`: daily rollup from hourly stats

**Stability guarantees:**
- Every operation wrapped in try/except (never crashes scheduler)
- Write-only on scheduler thread, read-only on UI thread (separate connections)
- Atomic transactions (crash mid-aggregation triggers rollback)
- No new dependencies (sqlite3 is Python stdlib)

### MONITORING & ALERTS - Time-Travel Statistics Center
- Temperature area chart with 1D/3D/1W/1M scale selection
- Spike detection (mean + 1.5×std) with yellow glow highlighting
- Hover tooltips with CPU/RAM/GPU values at each time point
- Voltage/Load multi-line chart with anomaly detection
- Stats panels: Today AVG, Lifetime AVG, Max Safe, Current, Spikes count
- AI learning status badges per metric
- Events log from SQLite database

### Overlay CPU/RAM/GPU
- Redefined as always-on-top Toplevel window (runs outside main program, on desktop)
- Auto-launches on startup via `root.after(1500, ...)`
- Draggable, frameless, hidden from taskbar (`-toolwindow` flag)

### My PC Improvements
- Hey-USER table replaced with cropped ProInfoTable (MOTHERBOARD + CPU sections only)
- Quick action buttons now navigate to actual pages (Stats & Alerts → Monitoring, etc.)
- Stability Tests page with real diagnostics (file integrity, engine status, log analysis)

### Sidebar Navigation Stability
- Dashboard-only updates: `_update_hardware_cards` and `_update_top5_processes` guarded by `current_view == "dashboard"`
- `winfo_exists()` guards on all widget update methods
- Fixed routing IDs for new subitems (temperature, voltage, alerts)

### Performance Optimization

**Threading model:**
- Background-threaded `psutil.process_iter()` - GUI thread never blocks on system calls
- `read_snapshot()` provides non-blocking, instant GUI updates from cached data

**Update cadence:**
- Main loop: 300ms → 1000ms (70% reduction in overhead)
- Hardware cards: 2s intervals
- System tray: 3s intervals
- Widget reuse pattern for TOP 5 processes (no destroy/recreate cycle)

**Graphics optimization:**
- Navigation button gradients drawn once (removed per-pixel `<Configure>` redraw)
- Realtime chart: reusable canvas rectangles with 2s interval
- Chart rendering refactored from pixel-by-pixel PhotoImage (70k iterations/frame) to canvas.coords() updates

**Telemetry sanitization:**
- Strict filtering excludes system noise (Idle, Interrupts, Memory Compression)
- 100% CPU cap per process prevents overflow anomalies
- `_is_system_noise()` filter prevents false "heavy app" alerts

### Dashboard Chart
- All time filters working: LIVE, 1H, 4H, 1D, 1W, 1M
- Pulls real data from `hck_stats_engine` SQLite (minute/hourly/daily tables)
- Auto-refresh for historical data every 30s
- Standardized default filter to LIVE mode

### Stats Engine Fixes
- Lifetime uptime persists across sessions (shutdown flush + multi-table query)
- Multi-tier fallback system: merges daily, hourly, minute stats without overlap
- System idle process filtered at source (eliminates "1012% CPU" display bugs)

### Codebase Cleanup
- Removed unused modules: `utils/`, `settings/`, `expandable_list.py`, dead animation code
- Removed in-app mini-monitor overlay (kept external desktop overlay)
- Integrated temperature data pipeline: scheduler → aggregator → SQLite
- Purged obsolete fan dashboard versions (ai, pro, ultra)
- Consolidated to single `fan_dashboard.py` (3 files deleted, ~100KB saved)
- Removed all `__pycache__` and `.pyc` files from repository
- Fixed broken imports after cleanup

## What's New [1.6.3] - 2026-01-12

### Fan Dashboard Overhaul
- Complete visual redesign with purple gradient temperature graph
- Improved data density and readability
- Enhanced visual hierarchy with gradient-based design language

### Your PC Section - UI Compression
- PRO INFO TABLE optimization (~25% size reduction)
- Removed redundant MOTHERBOARD voltage parameters (CPU, CPU SA, CPU AUX)
- Simplified TEMPERATURE monitoring (removed GPU, MOS, PCH, TZ00 sensors)
- Consolidated DISK SPACE and BODY FANS into vertical layout
- Reduced padding throughout (5px → 1px, 2px → 1px)
- Adjusted section headers (pady: 2px → 1px)
- Model badge optimization (padx: 10px → 8px, pady: 3px → 2px)

### New Menu System
- Replaced hardware cards with feature-focused navigation menu
- Five interactive menu buttons with background graphics:
  1. YOUR PC - Health Report: Component health monitoring with session history
  2. Statistics & Monitoring: Monthly statistics with spike detection
  3. Optimization Dashboard: Automated optimization for legacy hardware
  4. Daily Advanced System Cleanup: Consolidated cleanup utilities
  5. First Device Setup: Driver updates and service management
- Ultra-compact text rendering (6pt Consolas, 9px line spacing)
- Title overlays positioned at 25% image height
- Description text placed below images for improved readability
- Custom black scrollbar for PRO INFO TABLE (10px width)
- Canvas-based gradient rendering with PIL image manipulation
- Optimized frame padding across all sections
- Maintained 980x575 window size

### Technical Improvements
- Menu buttons are placeholders (functionality in future releases)
- Focus on UI density and information hierarchy
- No breaking changes to existing features

### Floating System Monitor Widget
- Always-on-top overlay in top-right corner (outside main window)
- Real-time CPU/RAM/GPU usage with color-coded alerts
- Draggable, minimizable, frameless design
- Runs independently - can be kept visible while working
- Launch from Navigation menu → "Floating Monitor"

### Codebase Cleanup
- Removed deprecated fan dashboard versions (ai, pro, ultra)
- Consolidated to single `fan_dashboard.py` (3 files deleted, ~100KB saved)
- Purged all `__pycache__` and `.pyc` files
- Fixed broken imports after cleanup

## What's New [v1.5.7] - 2025-12-23

### Modern Dashboard Redesign
- Apple-inspired flat design with gradient accents
- Ultra-compact TOP 5 process lists
- Side-by-side CPU/RAM indicators
- Color-coded visual hierarchy
- 40% more information density

### Hardware Health Monitoring
- Three-column layout (CPU | RAM | GPU)
- Real hardware names (actual Intel/AMD/NVIDIA models)
- Intelligent load classification (Normal → Critical)
- Temperature bars with heat-based coloring

### Gaming Analytics
- Per-game performance tracking
- FPS correlation with system load
- Bottleneck detection (CPU-limited vs GPU-limited)
- Thermal signature per game

### Optimization Tools
- Windows services management
- Gaming mode toggle
- Startup programs cleanup
- Safe system optimizations with rollback capability

## Project Structure

```
HCK_Labs/PC_Workman_HCK/
├── core/
│   ├── monitor.py           # Background-threaded system monitoring
│   ├── logger.py            # File logging system
│   ├── analyzer.py          # Data analysis & trends
│   ├── scheduler.py         # Background scheduler
│   ├── process_classifier.py # Process categorization (Gaming/Browser/Dev/etc.)
│   └── process_data_manager.py # Process tracking & statistics
├── hck_gpt/
│   ├── chat_handler.py      # Command routing (stats, alerts, insights, etc.)
│   ├── insights.py          # Local InsightsEngine (habits, anomalies, teasers)
│   ├── panel.py             # Chat panel UI (gradient banner, ticker, greeting)
│   ├── report_window.py     # Today Report Toplevel (chart, processes, alerts)
│   └── services_manager.py  # Windows services optimization
├── hck_stats_engine/
│   ├── db_manager.py        # WAL-mode SQLite, thread-local connections
│   ├── aggregator.py        # Minute/hourly/daily/monthly aggregation
│   ├── process_aggregator.py # Per-process CPU/RAM tracking
│   ├── query_api.py         # Range queries with auto-granularity
│   ├── events.py            # Spike/anomaly detection
│   └── constants.py         # Retention config (7d/90d/forever)
├── ui/
│   ├── windows/
│   │   ├── main_window_expanded.py  # Full dashboard (980x575)
│   │   └── main_window.py           # Minimal mode
│   ├── components/
│   │   ├── charts.py, led_bars.py, yourpc_page.py, ...
│   └── pages/
│       ├── monitoring_alerts.py     # Time-Travel Statistics Center
│       └── fan_control.py           # Fan curves & hardware
├── data/
│   ├── logs/                # CSV logs (raw, hourly, daily)
│   ├── cache/               # Runtime cache
│   └── hck_stats.db         # SQLite long-term storage
├── tests/
├── CHANGELOG.md
├── requirements.txt
├── startup.py
└── import_core.py
```

## Installation

### Requirements
- Python 3.9+ (or use .exe)
- Windows 10+ (Linux/Mac support coming)
- RAM: 200MB minimum
- Disk: 300MB (if using .exe installer)

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

## Usage

### First Launch

1. Dashboard opens showing real-time metrics
2. Give it 5 seconds to collect initial data
3. CPU/RAM/GPU bars populate
4. Click tabs to explore features

### Main Tabs
- **Dashboard**: Real-time overview
- **Your PC**: Hardware health & component status
- **Fan Control**: Custom fan curves (advanced)
- **Network**: Per-app bandwidth usage
- **Gaming**: Game-specific analytics

### Understanding the Data
- **Green (0-30%)**: Normal operation
- **Yellow (30-60%)**: Moderate load
- **Orange (60-85%)**: Heavy load
- **Red (85%+)**: Critical

Click any process to see more details.

## Data & Privacy

### What's Collected
- CPU/GPU/RAM usage (on your device only)
- Process names (to identify running applications)
- Temperature readings (from hardware sensors)
- Network usage (local tracking)

### Where It's Stored
- Local only: `/data/logs/` directory
- No cloud: Everything stays on your PC
- No telemetry: Zero tracking or analytics
- You control it: Delete anytime

### Privacy Assurance
- 100% local operation
- No data transmission
- No user tracking
- Open source (code is auditable)

## Versioning

| Version | Status | Key Features |
|---------|--------|--------------|
| v1.0.0 | Released | Basic architecture |
| v1.0.6 | Stable | First working UI |
| v1.3.3 | Released | hck_GPT integration |
| v1.4.0 | Released | System tray, enhanced UI |
| v1.5.7 | Released | Modern dashboard, hardware monitoring |
| v1.6.3 | Released | Fan dashboard, menu system, .exe |
| **v1.6.8** | **Current** | **Stats Engine v2, Time-Travel, Monitoring** |
| v2.0.0 | **Q3 2026** | **ML patterns, Microsoft Store** |

[Full Changelog](./CHANGELOG.md)

## Contributing

### For Users
- Found a bug? [Open Issue](https://github.com/HuckleR2003/PC_Workman_HCK/issues)
- Have an idea? [Start Discussion](https://github.com/HuckleR2003/PC_Workman_HCK/discussions)
- Want to help? [See CONTRIBUTING.md](./CONTRIBUTING.md)

### For Developers
- We welcome pull requests
- Follow existing code style
- Include tests for new features
- Update documentation

## System Requirements

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

## Documentation

- [GETTING_STARTED.md](./GETTING_STARTED.md) - Installation & setup guide
- [CHANGELOG.md](./CHANGELOG.md) - Version history & updates
- [CONTRIBUTING.md](./CONTRIBUTING.md) - How to contribute
- [docs/TECHNICAL.md](./docs/TECHNICAL.md) - Architecture deep dive (coming)

## About

**Marcin Firmuga** | Software Engineer

Built over 800 hours while working warehouse shifts in the Netherlands.

- GitHub: [HuckleR2003](https://github.com/HuckleR2003)
- LinkedIn: [Marcin Firmuga](https://linkedin.com/in/marcinfirmuga/)
- Email: firmuga.marcin.s@gmail.com

Part of [HCK_Labs](https://github.com/HuckleR2003/HCK_Labs) initiative.

## License

**MIT License** © 2025 HCK_Labs / Marcin Firmuga

Free for personal and commercial use. Attribution appreciated.

---

Ship what you have. Improve it later.
