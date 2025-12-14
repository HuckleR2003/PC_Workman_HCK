# HCK_Labs — PC_Workman_HCK — Changelog
_All notable changes are documented here._

## [v1.5.0] — 2025-12-07
### Major UI/UX Overhaul — Sprint 3: Modern Dashboard & Hardware Monitoring
**Summary:**
Complete Dashboard redesign with Apple-inspired UI, minimalist process displays, and real-time hardware health monitoring. Two new dedicated pages for system optimization and PC diagnostics.

### 🎨 Dashboard Modernization
**Enhanced Process Lists:**
- Ultra-minimalist TOP 5 displays (User & System processes)
- Side-by-side CPU/RAM indicators with gradient bars
- Gradient row backgrounds (TOP 1-5: #1c1f26 → #24272e)
- Removed emoji clutter - clean text-only display
- Color-coded metrics: CPU (blue #3b82f6), RAM (yellow #fbbf24)
- Click-to-show process info tooltips
- 20px row height with compact 6-8pt fonts

**Apple-Style Navigation Buttons:**
- Flat design with vibrant gradient backgrounds
- 40% height reduction (51px) - sleek and modern
- Horizontal icon+text layout (MSI Afterburner inspiration)
- "Optimization" - Green gradient (#0ea56a)
- "Your PC" - Blue gradient (#2563eb)
- Live service counter on Optimization button
- Smooth click interactions

### 💻 NEW PAGE: Your PC - Hardware Health
**Real-time Component Monitoring:**
- Three-column layout: CPU | RAM | GPU
- Live usage percentage (large 16pt display)
- Real hardware names via platform/psutil/GPUtil
  - CPU: Full processor name
  - RAM: Total capacity (e.g., "7.9 GB Total")
  - GPU: Detected GPU or "Integrated / Not detected"
- Simulated temperature monitoring:
  - CPU: 35°C + (load × 0.5)
  - RAM: 30°C + (load × 0.3)
  - GPU: 40°C + (load × 0.6)
- Dynamic temperature bars (5px height)
- Ultra-compact 50% smaller panels

**Intelligent Status System:**
- Component Health: ⚙️ "Wszystko działa sprawnie" / "Wymagana inspekcja"
- Load Classification: 📊
  - "Bez aktywności" (0-30%) - Green
  - "Standardowa aktywność" (30-60%) - Yellow
  - "Nadmierne obciążenie" (60-85%) - Orange
  - "Nadzwyczajne obciążenie" (85%+) - Red

### ⚡ NEW PAGE: Optimization Options
**Windows Services Management:**
- Live active/total services counter
- "Open Services Wizard" button (prepared for hck_GPT integration)
- "Quick Disable Unnecessary" one-click optimization
- Rollback-ready architecture

**Background Process Optimization:**
- 🔇 Disable Telemetry
- 🎮 Gaming Mode
- ⚙️ Startup Programs Manager
- 🧹 Clean Temp Files

### 🔧 Technical Improvements
**Updated Files:**
- `ui/main_window.py` - Complete Dashboard reconstruction
  - `_render_user_processes()` - Minimalist process rows
  - `_render_system_processes()` - Mirror design for system procs
  - `_create_inline_bar()` - Side-by-side CPU/RAM bars
  - `_build_yourpc_page()` - Hardware monitoring page
  - `_build_optimization_page()` - System tuning interface
  - `_update_yourpc_data()` - Real-time component updates
  - `_update_yourpc_hardware_names()` - Hardware detection

**New Features:**
- Real-time data integration with `_update_loop()`
- Dynamic widget management for live updates
- Hardware info caching for performance
- Apple-inspired color palette
- MSI Afterburner-style minimalism

### 📊 Data Integration
- Connected to existing `core/monitor.py` via `read_snapshot()`
- Live updates every 0.5s for Your PC page
- Persistent hardware names (loaded once)
- Smart status calculation based on usage thresholds

### 🎯 UX Philosophy
**Inspired by:**
- Apple macOS Big Sur/Ventura flat design
- MSI Afterburner minimalist metrics
- Modern monitoring dashboards (HWiNFO, CAM)

**Design Principles:**
- Maximum information density, minimum visual clutter
- Color-coded everything for instant recognition
- Click-driven interactions (no hover dependencies)
- Gradient accents for visual hierarchy
- Readable at small sizes (6-10pt fonts)

### Known Improvements
- Removed all emoji icons from process names (performance + clarity)
- No more vertically stacked CPU/RAM bars
- Eliminated Text widgets in favor of Frame-based layouts
- Unified color scheme across all panels

### Next Steps (v1.5.1)
- Real CPU/GPU temperature sensors (OpenHardwareMonitor integration)
- Mini usage charts in Your PC panels (sparklines)
- Service wizard integration with hck_GPT
- Quick optimization presets (Gaming, Work, Eco)
- Export hardware report functionality

**Maintainer:** Marcin Firmuga
**Lab:** HCK_Labs / Educational AI-Engineering Project
**Date:** 2025-12-07

---

## [v1.4.0] — 2025-12-06
### Major Update — System Tray, Enhanced Process Tracking & Interactive UI
**Summary:**
Complete system tray integration with battery-style live monitoring icon. Advanced process classification system with intelligent categorization. Enhanced data management with persistent statistics. Interactive charts and expandable process lists.

### New Modules
**Added files:**
- `ui/system_tray.py` - Battery-style tray icon with CPU/GPU indicators
- `ui/expandable_list.py` - Expandable TOP5 process lists
- `ui/charts_enhanced.py` - Interactive chart with click events
- `core/process_classifier.py` - Intelligent process categorization
- `core/process_data_manager.py` - Advanced data tracking and statistics
- `ui/main_window_enhanced.py` - Enhanced main window with all features

### System Tray Integration
- Battery-style icon showing CPU (right, red) and GPU (left, yellow)
- Live updates every 2 seconds with heat-map colors
- Left-click to restore window from tray
- Right-click context menu: Monitor / Statistics / Exit
- Toast notification on minimize: "Hello! I'm still working in the Background"
- Runs silently in background when minimized

### Window Management
- Auto-position to bottom-right corner
- Position lock toggle (📍 Locked / 🔓 Unlocked)
- Minimize to tray instead of close
- Draggable when unlocked
- Fixed position when locked

### Enhanced Process Classification
**Categories:**
- **Browsers** - All marked as "Mocny Rywal" (Strong Rival 💪)
  - Chrome, Firefox, Edge, Opera, Brave, Safari
- **Programs** - Categorized by type:
  - Development: VS Code, PyCharm, Visual Studio, IntelliJ
  - Gaming: Steam, Epic Games, Battle.net, Origin
  - Communication: Discord, Teams, Slack, Skype
  - Media: Spotify, VLC, OBS, Photoshop
  - Utilities: WinRAR, 7-Zip, Calculator
- **System** - Windows core processes with icons:
  - ⚙️ System, 📁 Explorer, 🔧 Service Host, 🪟 DWM

### Process Data Management
- Session tracking with full statistics
- Persistent storage in JSON files
- Top processes by CPU/RAM usage time
- Process timeline data (usage over time)
- Snapshot history (last hour in memory)
- Auto-save every 5 minutes
- Files: `process_statistics.json`, `process_history.json`

### Interactive Features
**Enhanced Chart:**
- Click to select time point
- Visual marker at selected timestamp
- Prepared for detail view panel (coming soon)
- Smooth data rendering

**Expandable Lists:**
- TOP5 default view
- "▼ More" button to expand to 15 processes
- Visual 5-segment usage bars (█████)
- Color-coded CPU (orange) and RAM (blue)
- Browser highlighting with "Mocny Rywal 💪"
- Icon-based categorization

### Data Files
**New files created:**
```
data/process_info/
  ├── process_history.json      (detailed snapshots)
  ├── process_statistics.json   (aggregated stats)
  └── daily_summary.json        (daily summaries)
```

### Dependencies
- Added `pillow>=10.0.0` - Icon generation
- Added `pystray>=0.19.0` - System tray functionality

### Documentation
- `IMPLEMENTATION_v1.4.0.md` - Technical implementation guide
- `USER_GUIDE_v1.4.0.md` - User manual with screenshots
- `test_new_features.py` - Automated feature tests

### Known Issues
- Chart click detail panel not yet implemented (shows marker only)
- Statistics window menu option exists but not functional
- Custom process patterns require manual editing

### Next Steps (v1.5.0)
- Statistics window implementation
- Chart click → process detail panel
- Custom process pattern editor UI
- Historical data visualization
- Export/import functionality

**Maintainer:** Marcin Firmuga
**Lab:** HCK_Labs / Educational AI-Engineering Project
**Date:** 2025-12-06

---

## [v1.0.6] — 2025-11-08  
### Major Update — Core System and UI Prototype  
**Summary:**  
Comprehensive reconstruction of the project architecture. Transitioned from simulated data to real-time monitoring using `psutil`. Implemented the first functional UI with live charts and process analytics.

### Core System (Rewritten)  
**Updated files:**  
- `core/__init__.py`  
- `core/monitor.py`  
- `core/logger.py`  
- `core/analyzer.py`  
- `core/scheduler.py`  
**Main improvements:**  
- Added real-time CPU, RAM, and GPU usage acquisition via `psutil` and `GPUtil`.  
- Implemented per-second resource sampling and buffering (up to 4 hours).  
- Introduced per-minute average aggregation (for 1H mode).  
- Added continuous CSV logging: `raw_usage.csv`, `minute_avg.csv`.  
- Integrated background scheduler loop for live data collection.  
- Rebuilt analyzer for trend and average calculations.  
- Upgraded `import_core.py` to a fully traceable registry system with unique component IDs.  

**Registry example:**  
py001_hck | `core.monitor` | 2025-11-08 18:09:39
py002_hck | `core.logger` | 2025-11-08 18:09:39
py003_hck | `core.analyzer`| 2025-11-08 18:09:39
### User Interface (UI) – First Working Version  
**File:** `ui/main_window.py`  
**Major features:**  
- First working graphical interface (Tkinter + Matplotlib).  
- Mode selector: `NOW`, `1H`, `4H` (only NOW and 1H active).  
- NOW: 30-second live display updated every second.  
- 1H: 60 data points representing 1-minute averages.  
- Added side live-meter panel showing CPU and RAM load.  
- Display of top processes divided into:  
  - User processes (applications)  
  - System processes (Windows core tasks)  
- Basic process labeling system (browser, explorer, game launcher).  
- Added placeholder for `hck_GPT` assistant section.
### Data Flow Summary  
- `core.monitor` → live data sampling
- `core.logger` → stores raw & minute-averaged data
- `core.scheduler` → triggers aggregation & recording
- `ui.main_window` → visualizes NOW / 1H data
- `import_core` → tracks component registration
### Fixes and Improvements  
- Introduced headless mode (runs without GUI).  
- Added robust startup and shutdown handling.  
- Optimized thread management and CPU load.  
- Unified color scheme and improved UI readability.  
- Extended setup configuration and testing scripts. 
### Known Issues  
- Process classification not fully accurate (e.g., browsers sometimes misidentified).  
- Time axis on charts still uses timestamps instead of readable time labels.  
- 1H data requires at least 60 seconds before appearing.  
- Process description tooltips pending (only click-based details).

**Maintainer:** Marcin Firmuga  
**Lab:** HCK_Labs / Educational AI-Engineering Project  
**Repository Path:** `/projects/PC_Workman_HCK/`  
**Date:** 2025-11-08  



 #archive#

## [v1.0.4] — 2025-10-31
### Core , Stats Engine, UI - critical error (6)
**Summary**
- Expanded liblaries for Core,Engine
- Create 3_way `QICKlogic` for Engine (helpfuly but bugs)
- Prepare `demo_UI`
- Connecting fake-data transfer from `Core`, `Engine` to `demo_ui` and basic values ​​in `monitor.py`
*main objective, place real data*
---
## [v1.0.1] — 2025-10-31
### Diagnostic Expansion - critical error (6)
**Summary**
- Expanded diagnostic UI layout.
- Integrated new chart placeholders using matplotlib stubs.
- Added background scheduler for data refresh (bug source).
- Introduced GPU trend averaging.
- Enhanced theme colors and layout polish.

**Known Issue**
- Crash occurs during concurrent `avg_calculator` refresh events when multiple UI triggers overlap.
---
## [v1.0.0] — 2025-10-27
### Alpha Demo — “Diagnostics Foundation” - critical error (3)
- Implemented registry system (`import_core`).
- Created Tkinter-based UI showing mock CPU/GPU/RAM usage.
- Added logging and average calculator modules.
- Packaged project with `setup.py`.
- Verified architecture for HCK_Labs integration.

---