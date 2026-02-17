# HCK_Labs — PC_Workman_HCK — Changelog
_All notable changes are documented here._

## [1.6.8] - 2026-02-17

### hck_GPT Intelligence System
Full local intelligence layer — no external AI, all rule-based logic on Stats Engine data.

**New modules** (`hck_gpt/`):
- `insights.py` — `InsightsEngine` singleton: habit tracking, anomaly awareness, personalized teasers
- `report_window.py` — "Today Report" Toplevel window with canvas chart, colored sections, process breakdown

**InsightsEngine capabilities:**
- `get_greeting()` — time-of-day + yesterday's summary + recurring app teaser (cached 30min)
- `get_current_insight()` — real-time spike alerts, gaming/browser detection (rate-limited 30s)
- `get_habit_summary()` — top 5 apps, browser/game/dev highlights, weekly CPU trend comparison
- `get_anomaly_report()` — 24h events grouped by severity with timestamps
- `get_teaser()` — 7-day recurring pattern detection, personality-driven messages per category
- `get_banner_status()` — compact one-liner for collapsed panel banner
- `_detect_recurring_patterns()` — finds apps used on 50%+ of last 7 days (>5% CPU or >100MB RAM)

**ChatHandler new commands:** `stats`, `habits`, `alerts`, `insights`, `teaser`, `help` (updated)
- Polish language support: `co uzywam`, `statystyki`, `co nowego`, `alerty`, `co dzis`
- Default response now shows current insight instead of "AI not connected"

**Panel upgrades:**
- Rainbow gradient "Today Report!" button (canvas-based, full-width)
- Smooth pixel-level fade banner (5-anchor RGB interpolation replacing discrete color blocks)
- Auto-greeting on panel open (once per 30min session)
- Insight ticker: checks every 60s while panel is open, shows notable events
- Banner status ticker: updates collapsed banner with live system status every 30s

**Today Report window:**
- Session uptime + lifetime uptime (from `daily_stats.uptime_minutes`)
- Mini usage chart: CPU (red) / GPU (blue) / RAM (yellow) lines with averages panel
- Top 5 system processes with CPU/RAM stats
- Top 5 user apps with category badges (Gaming, Browser, Development, etc.)
- Yellow alert banner: TEMP & VOLTAGES status

### HCK Stats Engine v2 — SQLite Long-Term Storage
Replaced empty CSV aggregation files with a proper SQLite pipeline.

**New modules** (`hck_stats_engine/`):
- `constants.py` — retention config (7d minute, 90d hourly, forever daily+)
- `db_manager.py` — WAL-mode SQLite, thread-local connections, auto-schema
- `aggregator.py` — minute/hourly/daily/weekly/monthly aggregation + CSV pruning
- `process_aggregator.py` — per-process CPU/RAM accumulator (in-memory dict → hourly/daily flush to SQLite)
- `query_api.py` — range queries with automatic granularity selection
- `events.py` — spike/anomaly detection with rate-limiting, severity levels

**Data pipeline:**
- `accumulate_second()` — lightweight dict update every 1s
- `on_minute_tick()` — INSERT into `minute_stats` every 60s
- Hourly/daily boundary detection → aggregation + pruning
- `flush_on_shutdown()` — graceful save on exit

**Stability guarantees:**
- Every call wrapped in try/except — scheduler never crashes
- Writes only on scheduler thread, UI reads via separate connection
- WAL mode — concurrent read/write without locks
- Atomic transactions — crash mid-aggregation → rollback
- Graceful degradation — SQLite failure → app runs on CSV as before
- Zero new dependencies (sqlite3 in stdlib)

**Integration:** `scheduler.py` (~15 lines), `startup.py` (~10 lines), `__init__.py` (imports)

### MONITORING & ALERTS — Time-Travel Statistics Center
- Temperature area chart: 1D / 3D / 1W / 1M scale, spike detection (mean + 1.5*std), yellow glow regions, hover tooltips
- Voltage/Load multi-line chart: CPU (blue) / RAM (green) / GPU (orange), anomaly highlighting
- Stats panels per metric: Today AVG, Lifetime AVG, Max Safe, Current, Today MAX, Spikes count
- AI learning status badges (green/yellow) with "PC Workman learns your patterns" messaging
- Events log section pulling from SQLite `events` table
- Auto-refresh every 30s with `winfo_exists()` guard
- New file: `ui/pages/monitoring_alerts.py` (~520 lines)

### Overlay CPU/RAM/GPU — External Desktop Widget
- Redefined as `Toplevel` with `-topmost`, `-toolwindow`, `overrideredirect`
- Positioned top-right of desktop, draggable, hidden from taskbar
- Auto-launch on startup: `root.after(1500, _launch_overlay_monitor)`
- Removed old in-app mini-monitor from header (~100 lines deleted)

### My PC Section
- Hey-USER table: replaced with cropped ProInfoTable (MOTHERBOARD + CPU sections, same style as Full Hardware Table)
- Quick action buttons wired to sidebar navigation (Stats & Alerts → Monitoring, Health Report → My PC, etc.)
- New Stability Tests page: real diagnostics (file integrity checks, HCK Stats Engine status, error logs)
- Thicker font on action buttons + 6-button layout

### Sidebar Navigation Stability Fix
- `_update_hardware_cards` and `_update_top5_processes` now guarded by `current_view == "dashboard"` — eliminates "bad window path name" errors when on other pages
- `winfo_exists()` checks added to: `_update_hardware_card`, `_render_expanded_user_processes`, `_render_expanded_system_processes`, `_update_session_bar`, `_update_live_metrics`, `_draw_sparkline`
- Routing IDs updated: `temperature`, `voltage`, `alerts` (replaced stale `realtime`, `processes`)
- Sidebar subitem renamed: "Events Log" → "Centrum & Alerts"

### Codebase Cleanup
- Removed AI-style comments (CYBERPUNK, MEGA, Apple style, SystemCare, personal reminders)
- Temperature data pipeline: scheduler reads `cpu_temp`/`gpu_temp` from snapshot → passes to aggregator → stored in `minute_stats`
- Replaced temporary chart placeholders with real data-driven charts

---

## [1.6.3+] - 2026-01-19
### PC Workman first `.exe`!

## [1.6.3] - 2026-01-12

### Fan Dashboard Overhaul
- Complete visual redesign with purple gradient temperature graph
- Improved data density and readability
- Enhanced visual hierarchy with gradient-based design language

### Your PC Section - UI Compression
- **PRO INFO TABLE optimization** (~25% size reduction)
  - Removed redundant MOTHERBOARD voltage parameters (CPU, CPU SA, CPU AUX)
  - Simplified TEMPERATURE monitoring (removed GPU, MOS, PCH, TZ00 sensors)
  - Consolidated DISK SPACE and BODY FANS into vertical layout
  - Reduced padding throughout (5px → 1px, 2px → 1px)
  - Adjusted section headers (pady: 2px → 1px)
  - Model badge optimization (padx: 10px → 8px, pady: 3px → 2px)

### New Menu System
- Replaced hardware cards with feature-focused navigation menu
- Five interactive menu buttons with background graphics:
  1. **YOUR PC - Health Report** - Component health monitoring with session history
  2. **Statistics & Monitoring** - Monthly statistics with spike detection
  3. **Optimization Dashboard** - Automated optimization for legacy hardware
  4. **Daily Advanced System Cleanup** - Consolidated cleanup utilities
  5. **First Device Setup** - Driver updates and service management
- Ultra-compact text rendering (6pt Consolas, 9px line spacing)
- Title overlays positioned at 25% image height
- Description text placed below images for improved readability

### Technical Improvements
- Custom black scrollbar for PRO INFO TABLE (10px width)
- Canvas-based gradient rendering
- PIL image manipulation for button backgrounds
- Optimized frame padding across all sections
- Maintained 980x575 window size (reverted experimental enlargement)

### Notes
- Menu buttons are currently placeholders - functionality to be implemented in future releases
- Focus on UI density and information hierarchy
- No breaking changes to existing features


## What's New [1.6.1] - `10.01.2026`
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

## [v1.5.7] — 2025-12-17
### Architectural Evolution — Dual-Mode System & UX Refinement Phase
**Summary:**
Revolutionary transition from single-window architecture to intelligent dual-mode system. Minimal mode becomes the primary interface, while expanded mode serves power users. Complete navigation redesign with animated RGB gradients, professional splash screen, and comprehensive project reorganization. Foundation laid for next-generation "My PC" UX redesign.

### 🏗️ Dual-Mode Architecture Innovation
**Minimal Mode (Primary Interface):**
- Compact, always-accessible monitoring dashboard
- Live CPU/RAM/GPU metrics with LED-style bars
- TOP 5 process lists (user + system)
- Interactive real-time chart (NOW/1H/4H modes)
- System tray integration for background operation
- Bottom-right corner positioning (lockable)
- Designed for continuous monitoring without screen clutter

**Expanded Mode (Power User Interface):**
- Full-featured tabbed interface
- Five main sections: Dashboard, Optimization, Your PC, Statistics, Day Stats
- Navigation via modern gradient buttons with animations
- Comprehensive system management tools
- Hardware health monitoring
- Service optimization wizards
- Historical data analytics

**Design Philosophy:**
- Minimal mode for "always there" monitoring
- Expanded mode for "when you need control"
- Seamless switching between modes
- No feature duplication - each mode serves distinct purpose

### 🎨 Navigation System Redesign
**Ultra-Modern Gradient Buttons:**
- Canvas-based rendering with RGB color interpolation
- Animated gradient cycling (60 FPS smooth animation)
- Three-color gradient stops (dark → mid → light)
- Icon section (40px) with transparent background
- Gradient text section with shadow effects
- Color-coded by function:
  - Dashboard: Blue gradient (#1e3a8a → #3b82f6 → #60a5fa)
  - Optimization: Green gradient (#047857 → #10b981 → #34d399)
  - Your PC: Purple gradient (#6b21a8 → #8b5cf6 → #a78bfa)
  - Statistics: Orange gradient (#c2410c → #f97316 → #fb923c)
  - Day Stats: Pink gradient (#be185d → #ec4899 → #f472b6)
- Continuous RGB offset animation (0.005 per frame)
- Removed all unnecessary visual clutter (no diagonal separators, no shimmer)

**Technical Implementation:**
- `_create_nav_button()` - Canvas-based gradient renderer
- `_animate_button_shimmer()` - RGB gradient cycling loop
- Gradient color maps with RGB tuples for smooth interpolation
- Frame-based animation system (33ms interval = 30 FPS)

### 🌟 Startup Experience Enhancement
**Professional Splash Screen:**
- Animated intro with HCK_Labs logo
- Fade-in animation (0.8s) using cubic easing
- Hold at full opacity (0.9s)
- Fade-out animation (0.8s) using cubic easing
- Total duration: 2.5 seconds
- Threading-based non-blocking display
- Graceful fallback if splash fails
- Logo location: `data/icons/HCKintro.png`

**Technical Details:**
- New file: `ui/splash_screen.py`
- Alpha channel animation (0.0 → 1.0 → 0.0)
- Ease-in/ease-out curves for smooth transitions
- Integrated into `startup.py` with threading

### 📁 Project Structure Reorganization
**New UI Architecture:**
```
ui/
├── windows/          (Main window modules)
│   ├── main_window.py              (Minimal mode)
│   └── main_window_expanded.py     (Expanded mode)
├── components/       (Reusable UI components)
│   ├── charts.py                   (Enhanced chart system)
│   ├── expandable_list.py          (Process list with expand)
│   ├── led_bars.py                 (LED-style usage bars)
│   ├── process_tooltip.py          (Process info tooltips)
│   └── yourpc_page.py              (Hardware monitoring page)
├── pages/            (Full-page views)
│   ├── page_all_stats.py           (Statistics page)
│   └── page_day_stats.py           (Daily analytics page)
└── (support modules)
    ├── dialogs.py                  (Modal dialogs)
    ├── hck_gpt_panel.py            (AI assistant panel)
    ├── system_tray.py              (Tray icon system)
    ├── theme.py                    (Color schemes)
    └── splash_screen.py            (Startup animation)
```

**Import System Updates:**
- All imports updated to new structure
- `ui.windows.main_window` for minimal mode
- `ui.windows.main_window_expanded` for expanded mode
- `ui.components.*` for reusable elements
- `ui.pages.*` for full-page views
- Added `__init__.py` files for proper Python packages

### 📐 UX Refinement Phase — "My PC" Redesign Preparation
**Comprehensive Design Specification Created:**
- Document: `docs/MY_PC_UX_REDESIGN_MASTERPIECE.md`
- 500+ lines of detailed UX specifications
- Principal UX architect level design thinking

**Key Innovation — Minesweeper-Style Disk Health:**
- 10×5 grid visualization of disk sectors
- Color-coded health indicators:
  - #d4f4dd (Very light green) → Excellent
  - #86efac (Light green) → Good
  - #fbbf24 (Yellow) → Attention
  - #f87171 (Red) → Risk
  - #1a1a1a (Black) → Critical/Unreadable
- Instant visual understanding without technical jargon
- Hover tooltips for sector details
- Calm explanatory text (no panic language)

**Design Language Defined:**
- Signature "Hello! /" header system with gradients
- Five main sections: Central, Efficiency, Health Check, Components, Startup & Services
- Apple-level clarity + Engineering honesty + Power-user depth
- Visual 2D PC hardware map
- Guided decision flows (not just toggles)
- "Nothing to do" states as feature (not emptiness)
- Trust-building tone throughout

**Competitive Positioning:**
- Cleaner than MSI Afterburner
- Calmer than HWMonitor
- Smarter than Windows Task Manager
- More innovative than all combined

### 🔧 Technical Improvements
**Updated Files:**
- `ui/windows/main_window_expanded.py`
  - Complete navigation button system rebuild
  - Canvas-based gradient rendering
  - RGB animation system
  - Removed shimmer and diagonal separators
- `ui/splash_screen.py` (NEW)
  - Professional startup animation
  - Cubic easing functions
  - Fade-in/hold/fade-out sequence
- `startup.py`
  - Integrated splash screen with threading
  - Updated imports for new structure
  - Graceful error handling

**Bug Fixes:**
- Fixed `NameError: name 'btn_data' is not defined` (line 631)
- Corrected import paths after reorganization
- Verified all module connections with comprehensive testing

**Code Quality:**
- Thorough 2-pass testing protocol
- Import verification scripts
- Full program startup validation
- Connection integrity checks

### 🎯 Current Development Phase
**Focus: UX Refinement for Main Tabs**
- Researching best practices from industry leaders
- Designing calm, intelligent interfaces
- Preparing for "My PC" section implementation
- Building foundation for next-generation system monitoring

**Design Principles Being Applied:**
- Maximum clarity, minimum cognitive load
- Visual innovation without gimmicks
- Trust-building through calm communication
- Actionable insights, not just data dumps
- "Show me what matters, when it matters"

### 📊 Architecture Summary
**Before v1.5.7:**
- Single window with multiple pages
- All features in one interface
- Limited animation and polish

**After v1.5.7:**
- Dual-mode system (minimal + expanded)
- Specialized interfaces for different use cases
- Professional animations and transitions
- Organized component architecture
- Foundation for advanced UX features

### 📚 Documentation Updates
**New Documents:**
- `docs/MY_PC_UX_REDESIGN_MASTERPIECE.md` - Comprehensive UX specification
- Social media content templates (LinkedIn, Reddit, Twitter, Dev.to, Hacker News)

### Known Improvements
- Removed diagonal "/" separator from navigation buttons (created visual noise)
- Removed shimmer animation (looked unprofessional)
- Replaced with smooth RGB gradient cycling
- Made icon backgrounds transparent
- Enhanced text section with gradients and shadows
- Verified all imports work after reorganization

### Next Steps (v1.5.8)
- Implement "My PC" UX redesign from specification
- Build signature "Hello! /" header system
- Create Minesweeper-style disk health visualization
- Implement visual 2D PC hardware map
- Add guided decision flows for system optimization
- Integrate calm, trust-building language throughout

**Maintainer:** Marcin Firmuga
**Lab:** HCK_Labs / Educational AI-Engineering Project
**Date:** 2025-12-17

---

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