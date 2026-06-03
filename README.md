# PC Workman HCK

> **Your PC finally has someone who speaks its language.**

![Version](https://img.shields.io/badge/Version-1.7.7-7c3aed?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active%20Development-10b981?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.9+-3b82f6?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-64748b?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2B-0ea5e9?style=flat-square)

---

Most monitoring tools give you numbers. PC Workman gives you **answers**.

Ask *"why is my PC slow right now?"* — and get a real explanation, not just a percentage.  
Ask *"is cs2.exe a virus?"* — get an instant process identity check.  
Ask *"which game pushes my hardware the hardest?"* — get a thermal signature breakdown.

**82 AI intents. 100% offline. No API key. No cloud. Just your PC talking to you.**

---

## What makes it different

| Traditional tools | PC Workman HCK |
|---|---|
| `CPU: 87%` | *"CPU at 87% — Chrome and Electron processes, consider closing Discord"* |
| Static charts | Time-travel: click any point in history to see what was running |
| No context | Remembers patterns, compares today vs your 7-day average |
| Manual checks | Proactive alerts: RAM spike? Fan noise? Crash context? Auto-detected |
| English only | Polish + English, auto-detected per message |

---
## Quick Start

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
- Real-time CPU, GPU, RAM tracking
- Network bandwidth per-application
- Process identification and labeling
- Temperature monitoring with trends
- Historical data logging (daily, weekly, monthly)

### Intelligence (hck_GPT)
- **82 intents** across 8 categories (hardware, diagnostics, performance, why, optimization, security, fun, small talk) + gaming/battery/upgrade
- **Hybrid Engine**: rule-based responses for known intents, Ollama LLM for open-ended questions — 100% offline, no API key needed
- **Bilingual**: Polish and English, auto-detected per message
- **Session memory**: conversation context, CPU/RAM trend buffers, cross-response data store
- **Proactive monitor with DeepMonitor integration**: background daemon watches CPU/GPU temps, RAM, throttle, disk on all drives; pushes alerts automatically; banner shows live temps
- **Conversation flow**: greeting, thanks, "more info", "what should I do" all handled naturally with context-aware routing
- Local insights engine — habit tracking, anomaly awareness, teasers from Stats Engine
- SQLite user knowledge base (hardware profile, usage patterns) at `AppData/Local/`
- Background hardware scanner (psutil + WMI — CPU model, GPU, VRAM, mobo, RAM speed, disk model)
- Chat panel nav links: clickable `[→ Page]` tokens route directly to app pages
- `_followup()` pool system: 8 keys, every response ends with a contextual next-question hint

### DeepMonitor *(new in 1.7.6)*
- `ttk.Treeview` sensor table with 4 aligned columns (Sensor / Value / Min / Max)
- Type-specific row background tints: temperature = blue-night, utilization = indigo
- Action bar: Save Data (.txt/.csv), Pause, Reset min/max
- Sub-section headers color-coded by metric type

### MAP OF COMPONENTS *(new in 1.7.6)*
- 2.5D isometric view of your PC rendered via Pillow (2× SSAA, LANCZOS downscale)
- Desktop PC mode: case, mobo, CPU + heatsink, GPU, RAM, SSD, PSU, fans, cables
- Laptop mode: open chassis with mobo, fans, GPU, battery, screen, keyboard
- Components color-shift green → amber → red based on live heat/load; hot components pulse
- Hover over any component for a tooltip with live stats
- Auto-refresh every 3 seconds via background thread

### Live Guide *(new in 1.7.2)*
- Interactive 3-step spotlight overlay (`ui/guide/live_guide.py`) launched from Guide page
- Windows `-transparentcolor` technique: dim full screen, punch transparent hole over target widget
- Step 1: main realtime chart + time-filter buttons; Step 2: left/right nav buttons with per-button descriptions; Step 3: hardware cards + session averages
- Floating info card with accent bar, step dots, DALEJ / Zakończ button; ESC or ✕ to dismiss

### First Setup & Drivers *(new in 1.7.2)*
- Health score gauge (0–100 arc) — computed from driver ages and startup count
- 4 driver health cards: GPU, Audio, Network, USB — real data from Windows registry
- Driver freshness bar per card; status badges: CURRENT / 6+ MONTHS / Xmo OLD
- Startup program list (registry HKCU/HKLM Run keys), 6-item setup checklist with persistent state
- Quick Actions: Windows Update, Device Manager, Services, Task Scheduler, System Info, MSConfig

### Startup Manager *(new in 1.7.2)*
- Reads HKCU + HKLM + HKLM32 Run registry keys — no admin required
- Knowledge base of 30 common programs with impact rating (High/Medium/Low) and recommendation
- Three panels: Optimize at startup / Safe to disable / All entries
- Disable = real registry removal with confirmation dialog; choices persist to `data/cache/startup_prefs.json`

### Services Manager *(new in 1.7.2)*
- Catalogue of 40+ Windows services in 4 categories: Essential (locked) / Recommended / Optional / Likely Unnecessary
- Stop / Start / Restart per service; admin detection with warning banner
- **TURBO Mode integration**: queue services for auto-stop when TURBO activates; saved to `settings/turbo_services.json`
- All changes logged to `data/logs/service_changes.log`

### Interface
- Modern dashboard (Apple-inspired design)
- Ultra-compact information density
- Color-coded process lists
- Interactive charts and metrics
- Click-to-investigate functionality
- Process tooltips on TOP 5 panels — hover any process name for instant library lookup

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
├── core/              # Real-time data collection (background-threaded monitor)
├── hck_gpt/
│   ├── engine/        # Hybrid Engine: rule routing + Ollama LLM client
│   ├── intents/       # Intent parser, vocabulary, language detection
│   ├── memory/        # Session memory, user knowledge (SQLite), proactive monitor
│   ├── context/       # System context builder, hardware scanner
│   ├── responses/     # Bilingual response builder
│   ├── chat_handler.py
│   ├── insights.py    # InsightsEngine (habits, anomalies, teasers)
│   └── panel.py       # Chat panel UI
├── hck_stats_engine/  # SQLite pipeline: minute/hourly/daily/monthly stats
├── ui/
│   ├── windows/       # Main window modes (expanded, minimal)
│   ├── guide/         # Interactive spotlight guide (LiveGuide, 3-step tour)
│   ├── components/    # Reusable widgets (charts, LED bars, tooltips)
│   └── pages/         # Full-page views (monitoring, fan control, startup, services)
├── data/
│   ├── logs/          # CSV logs (raw, hourly, daily, weekly, monthly)
│   ├── cache/         # Runtime cache & process patterns
│   └── hck_stats.db   # SQLite long-term storage (WAL mode)
└── tests/             # Unit tests
```

**Design principles:**
- Dynamic component registry (auto-registration)
- Seamless inter-module communication
- Designed for future expansion
- Educational value (demonstrates Python best practices)
-

## What's New [1.7.7-patched] - `2026-06-03` - CURRENT

### Ghost Driver Detection *(new in 1.7.7)*
- Detects driver packages left in Windows after replacing hardware (e.g. old GT 1030 after upgrading to RTX 3050)
- Uses `pnputil /enum-devices /connected` — only physically present hardware, not phantom registry entries
- Ghost entries shown on driver cards with bordeaux background and `⚠ GHOST` / `100% UNUSED` badge — visible without expanding
- Dialog: device age, version, explanation; option to remove via `pnputil /remove-device` (admin + confirmation)
- Works across GPU, Audio, Network, USB driver classes

### Drivers Tab — SEE EVERYTHING / SEE OUTDATED *(new in 1.7.7)*
- Two mode buttons in DRIVER HEALTH header: **SEE EVERYTHING** (all devices by category) and **SEE OUTDATED (N)** (drivers 24+ months old, sorted oldest first)
- Expand button per card: `▼ pokaż wszystkie (N)` reveals every device found in that class, ghost devices highlighted in bordeaux
- Drivers >= 730 days (~24 months) marked red

### Auto RAM Flush — Process Exclusion *(new in 1.7.7)*
- Bordeaux exclusion panel inside RAM Flush card: click any process to protect it from flush
- Protected processes persist across restarts via `user_prefs.json`
- Flush result shows protected count: `Freed 420 MB (87 procs · 3 protected)`

### Stability & Bug Fixes *(new in 1.7.7)*
- MAP OF COMPONENTS: case_front panel removed (was covering internals in screen-space); replaced with thin corner rails
- hck_GPT HOT strip: removed duplicate panel-side monitor that conflicted with proactive_monitor and had broken Polish strings
- Startup Manager: admin notice now amber and prominent, matching Services Manager style
- `ram_flush` intent alias fixed: routes to `optimization` (actionable) instead of `ram_why_high` (diagnosis)

### UI & UX Patch *(new in 1.7.7-patched)*
- **Startup Manager**: renamed "Needs Attention" → "Startup Menu"; removed non-functional "All entries" panel; auto-refresh after restoring a disabled entry
- **Services Manager**: always shows both **Stop** and **Start** buttons for every non-essential service — active button is colored, inactive is muted (was showing only one direction)
- **Services Manager**: expand banner now says `∨ Rozwiń więcej (N) ∨` and is more compact
- **First Setup & Drivers**: GHOST badge now visible immediately on card header (not only inside expanded panel); subcategory labels and expand buttons are clearly readable; ghost devices highlighted bordeaux inside expand panel
- **Page headers**: compact `← Główne Menu` only — removed redundant large title/subtitle duplication below the title bar

---

## What's New [1.7.6] - `2026-05-29` *(previous)*

### DeepMonitor *(new in 1.7.6)*
- `ttk.Treeview` sensor table with 4 aligned columns (Sensor / Value / Min / Max)
- Type-specific row background tints: temperature = blue-night, utilization = indigo
- Action bar: Save Data (.txt/.csv), Pause, Reset min/max
- Sub-section headers color-coded by metric type

### MAP OF COMPONENTS *(new in 1.7.6)*
- 2.5D isometric view of your PC rendered via Pillow (2x SSAA, LANCZOS downscale)
- Desktop PC mode: case, mobo, CPU + heatsink, GPU, RAM, SSD, PSU, fans, cables
- Laptop mode: open chassis with mobo, fans, GPU, battery, screen, keyboard
- Components color-shift green -> amber -> red based on live heat/load; hot components pulse
- Hover over any component for a tooltip with live stats
- Auto-refresh every 3 seconds via background thread

### hck_GPT Wave 2 *(new in 1.7.6)*
- 6 new intents: `game_can_run`, `gaming_ram_usage`, `daily_ram_usage`, `battery_estimate`, `upgrade_feasibility`, `top_resource_hog`
- Conversation flow: greeting/thanks/more-info/what-should-I-do routing
- **82 intents** total (up from 76)
- Language sync: panel language now follows Settings page in real-time

### Font System - 100% Coverage *(new in 1.7.6)*
- All UI files now use the shared `_HDR` / `_BODY` / `_MONO` system from `utils/fonts.py`
- Inter font (if available) applied consistently across all 30+ UI files
- Zero hardcoded `"Segoe UI"` / `"Consolas"` strings remaining in UI layer

### Process Library *(new in 1.7.6)*
- **241 -> 373 entries** (+132 entries: Signal, Viber, Bitwarden, Godot 3/4, Unreal Editor, RDR2, Horizon ZD/FW, Helldivers 2, and many more)

---

## What's New [1.7.5] - `2026-05-25` *(previous)*

### hck_GPT — 13 new intents + 4 MEGA features
Built from 28 real community requests (GitHub Discussions + LinkedIn).

- **13 new intents**: fan noise history, driver status, gaming vs work time, process identity, stale apps, FPS degradation, app behavior change, startup slowdown, temp comparison, crash context, game hardware stress, battery drain rate, power after restart — **63 → 76 intents total**
- **Context Time-Windowing**: each intent gets a history window (5 min → 7 days); LLM context is scoped to what's actually relevant for that question
- **No-AI-Slop fallback**: when data is missing, the AI says so instead of making things up
- **Time-Travel Debugging**: compare any live metric to its N-day historical average
- **Micro-Benchmarking**: background cpu/disk benchmarks triggered on demand, stored in session memory

### Process Library
- **104 → 241 entries** — games (CS2, Elden Ring, Cyberpunk, BG3, KSP…), dev tools (JetBrains suite, Cursor, DBeaver…), RGB software, diagnostics, VPN/network, Windows system processes

---

## What's New [1.7.4] - `2026-05-14` *(previous)*

### Optimization Center — Full Redesign
- Feature grid rebuilt as 2-column expandable card layout — each card has an inline info panel, no separate overlay
- Snapshot strip (CPU / RAM / Disk) now shows subtle fill bars behind the percentage values
- **Turbo Power Plan** now actually creates a "Turbo PC" power scheme via `powercfg`; handles non-English Windows, detects missing admin rights, restores original plan on exit
- **Quick Actions** replaced: Startup Manager (nav), Services Manager (nav), Disk Defragmenter (run), Weekly Performance Report (window)
- **Weekly Performance Report**: 6 bar charts (CPU/GPU/RAM avg + peak over 4 rolling weeks), AI text summary, TXT export
- **LIVE NOW** sidebar: CPU/RAM/GPU mini-bars, refreshes every 2 s
- Typography upgrade: Segoe UI Semibold throughout; fixed icon widget parenting bug

### Dashboard
- "More Optimization Tools" button replaced with a subtle dark "Optimization Center" chip — navigates to My PC → Hardware & Health; glow animation removed

### My PC
- `yourpc_page.py` now uses the shared `utils.fonts` font system (`_HDR / _BODY / _MONO`)

---

## What's New [1.7.3] - `2026-05-02` *(previous)*

### Live Guide
- New `ui/guide/live_guide.py` — `LiveGuide` class: interactive spotlight overlay with Windows `-transparentcolor` dim technique
- 3-step dashboard tour: chart + filters → nav buttons (left/right) with per-button descriptions → hardware cards + session averages
- Floating info card: accent bar, badge, step dots, DALEJ/Zakończ; ESC or ✕ to dismiss
- Wired to "▶ Guide on program LIVE" button in Guide page; auto-returns to dashboard and waits for widgets

### hck_GPT — AI quality & coverage
- `_resp_help` fully rewritten: 8 sections with emoji headers covering all 37 intents (hardware, diagnostics, performance, why, optimization, security, fun, small talk) — bilingual PL/EN
- `_resp_optimization` rewritten with live data: real CPU/RAM snapshot, hardware-profile flags (HDD, low RAM, few cores), priority tip (🔴/🟡/✓), conditional virtual-memory and HDD notes
- `_FOLLOWUPS` pool expanded 3 → 8 keys (`hw`, `health`, `perf`, `security`, `disk`, `why`, `process`, `session`); `_followup()` wired into 9 handlers (`virus_check`, `disk_health`, `disk_usage_why`, `battery_drain`, `uptime`, `process_info`, `throttle_check`, `perf_change`, `session_compare`)
- `record_response_data` added to `hw_gpu`, `perf_change`, `session_compare` — AI can now reference GPU model/VRAM and yesterday's stats in follow-up answers

### hck_GPT — hardware & session data
- WMI hardware scanner: RAM speed + part number, primary disk model added to user knowledge base
- Session data store (`session_memory.record_response_data` / `get_response_data` / `discussed_this_session`) — cross-response referencing system
- Chat panel nav links (`_apply_nav_links`): `[→ Page]` tokens in AI responses are clickable and route directly to app pages; `register_nav_callback()` API; `_open_virtual_memory()` helper

---

## What's New [1.7.2] - `2026-04-27` *(previous)*

### My PC — Startup & Services Manager
- New **Startup Manager** page: reads registry Run keys, rates impact (High/Medium/Low), three panels (Optimize / Safe to disable / All), confirm-before-remove, prefs persisted
- New **Services Manager** page: 40+ services catalogued, Stop/Start/Restart, admin detection, TURBO Mode integration (queue services for auto-stop), change log
- Replaced single "Optimization & Services" button with **3-zone Optimization Hub**: Optimization Center (left), Startup Manager (top-right), Services Manager (bottom-right) — single Canvas with zone detection, hover brightening, live metrics in daemon thread
- Removed hck_GPT banner from Central tab; added SESSION bar (`SESSION: Xh Ym` + `● LIVE`)
- Nav bar: **MY PC** label (Inter Bold), tab/section fonts upgraded to Inter
- Stability Tests + Your Account moved to bottom row (side by side)

### hck_GPT — Bug fixes
- Fixed `_show_help()` always responding in wrong language (used pre-detection `self._last_lang`)
- Redesigned `_show_help()` with `◈` category headers, bilingual PL/EN
- Fixed `_resp_temperature()` — DB fallback via `query_api` when `psutil.sensors_temperatures()` empty on Windows
- Fixed `_resp_speed_up_pc()` — removed unconditional TURBO BOOST + FPS tips regardless of system state

### hck_stats_engine — new query_api methods
- `get_temperature_history()`, `get_temperature_summary()`, `get_top_processes_lifetime()`, `get_weekly_summary()`

### Release packaging
- All versions aligned to 1.7.2; `requirements.txt` completed; `PCWorkman.spec` fully rewritten (25+ hidden imports, `settings/` bundled); EXE build: `dist/PC_Workman_HCK_1.7.2/` (~94 MB) ✅
- Codebase cleaned: removed all "Apple style", "Inspired by", TODO comments

---

### hck_GPT — AI Layer & Hybrid Engine *(2026-04-22)*
- **Bordeaux Noir panel**: animated black→crimson gradient banner with sine-wave shimmer, `AI` vector badge, pulsing `ONLINE` badge — no image files
- **Hybrid Engine** (`hck_gpt/engine/`): routes low-confidence / open-ended messages to Ollama LLM (local), rule engine handles everything else; graceful 60s cooldown on Ollama unavailability
- **Bilingual responses**: every handler now replies in Polish or English based on auto-detected language; `random.choice()` pools for variety
- **Proactive monitor**: background daemon watches CPU, RAM, throttling, disk, session uptime; pushes alerts to chat panel and banner status bar
- **Session memory extended**: CPU/RAM trend buffers, auto conversation summary every 6 messages, `get_context_for_llm()` injected into Ollama system prompt
- **Rich system context**: top 3 processes, temperature readings, 6-section LLM context string (live state, today's averages, processes, temps, hardware profile, conversation)
- **User knowledge base**: SQLite at AppData — hardware profile, facts, usage patterns; background hardware scan via psutil + WMI (CPU model, GPU, VRAM, motherboard, RAM speed)
- **Parser improvements**: ASCII-fold dual scoring for Polish accent normalization; vocabulary enriched with multi-word phrases for reliable confidence above routing threshold
- **Efficiency tab**: fixed physical core count (was showing logical count); fixed invisible avg text color; per-core session min/max/avg; side-by-side TOP CPU/RAM consumers
- **HCK_Labs globe icon**: vector globe drawn with canvas primitives — sphere + meridian + equator + parallels

### Earlier in 1.7.2 — dashboard & nav (`2026-04-21`)
- Dashboard nav buttons full redesign (dark-gradient, accent stripe, bordeaux L-brackets, vector icons)
- HCK_Labs and Guide pages full blog-style redesign
- Navigation routing fixes (MONITORING, AllMonitor, overlay title)
- Turbo Boost set to coming-soon state with tooltip

### Earlier in 1.7.2 — optimization & fonts (`2026-04-20`)
- Optimization Center redesign: TURBO BOOST button, feature count badge, column layout, RAM Flush card
- `utils/fonts.py` — Inter font via GDI32 with Segoe UI fallback
- Repository cleanup: proper `.gitignore`, 7 dead files removed, broken imports fixed, `__pycache__` cleared

### Earlier in 1.7.2 — first setup & drivers (`2026-04-13`)
- First Setup & Drivers page: health score gauge, 4 driver health cards (registry data), setup checklist with persistent state
- hck_GPT chat time badge (inline canvas, per-message `HH:MM`)
- Process library expanded (+8 entries); process tooltips on TOP 5 panels

---

## What's New [1.7.1] - `2026-04-10`

### hck_GPT Intelligence System
- Local insights engine: habit tracking, anomaly awareness, personalized teasers
- "Today Report!" button — rainbow gradient, opens detailed report window
- Today Report: session/lifetime uptime, CPU/GPU/RAM chart, top processes, alert status
- 7-day recurring pattern detection with personality-driven messages
- New commands: `stats`, `alerts`, `insights`, `teaser` (+ Polish language)
- Smooth fade gradient banner, auto-greeting, periodic insight ticker

### HCK Stats Engine v2 (SQLite Long-Term Storage)
- SQLite-based pipeline: minute/hourly/daily/weekly/monthly aggregation
- Process tracking: per-hour and per-day CPU/RAM breakdown per process
- WAL mode for concurrent UI reads + scheduler writes
- Automatic pruning (7d minutes, 90d hourly, forever daily+)
- Graceful degradation: SQLite failure falls back to CSV
- New modules: `db_manager`, `aggregator`, `process_aggregator`, `query_api`, `events`

### MONITORING & ALERTS - Time-Travel Statistics Center
- Temperature area chart with 1D/3D/1W/1M scale selection
- Spike detection (mean + 1.5*std) with yellow glow highlighting
- Hover tooltips with CPU/RAM/GPU values at each time point
- Voltage/Load multi-line chart with anomaly detection
- Stats panels: Today AVG, Lifetime AVG, Max Safe, Current, Spikes count
- AI learning status badges per metric
- Events log from SQLite database

### Overlay CPU/RAM/GPU
- Redefined as always-on-top Toplevel window (outside program, on desktop)
- Auto-launches on startup via `root.after(1500, ...)`
- Draggable, frameless, hidden from taskbar (`-toolwindow`)

### My PC Improvements
- Hey-USER table: replaced with cropped ProInfoTable (MOTHERBOARD + CPU sections)
- Quick action buttons now navigate to actual pages (Stats & Alerts -> Monitoring, etc.)
- Stability Tests page with real diagnostics (file integrity, engine status, logs)

### Sidebar Navigation Stability
- Dashboard-only updates: `_update_hardware_cards` and `_update_top5_processes` guarded by `current_view == "dashboard"`
- `winfo_exists()` guards on all widget update methods
- Fixed routing IDs for new subitems (temperature, voltage, alerts)

### Performance Optimization
- Background-threaded `psutil.process_iter()` — GUI thread never blocks on system calls
- Dashboard update cadence: 300ms → 1000ms, hardware cards every 2s, tray every 3s
- Widget reuse pattern for TOP 5 processes (no destroy/recreate)
- Nav button gradients drawn once (removed per-pixel `<Configure>` redraw on window move)
- Realtime chart: reusable canvas rectangles, 2s interval

### Dashboard Chart
- All time filters working: LIVE, 1H, 4H, 1D, 1W, 1M
- Pulls real data from `hck_stats_engine` SQLite (minute/hourly/daily tables)
- Auto-refresh historical data every ~30s

### Stats Engine Fixes
- Lifetime uptime persists across sessions (shutdown flush + multi-table query)
- System idle process filtered at source (no more "1012% CPU" messages)

### Codebase Cleanup
- Removed unused: `utils/`, `settings/`, `expandable_list.py`, dead animation code
- Removed in-app mini-monitor overlay (kept external one)
- Integrated temperature data pipeline: scheduler -> aggregator -> SQLite

---

## What's New [1.6.3] - `2026-01-12`

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

## What's New [v1.5.7] - `23.12.2025`
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
│       ├── fan_control/             # Fan curves & hardware
│       ├── startup_manager.py       # Startup programs manager (new)
│       ├── services_manager.py      # Windows services + TURBO (new)
│       ├── optimization_services.py # Optimization Center
│       └── first_setup_drivers.py  # Driver health & checklist
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
-
## Installation

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
## Usage
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
## Data & Privacy

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
## Versioning

| Version | Status | Key Features |
|---------|--------|--------------|
| v1.0.0 | Released | Basic architecture |
| v1.0.6 | Stable | First working UI |
| v1.3.3 | Released | hck_GPT integration |
| v1.4.0 | Released | System tray, enhanced UI |
| v1.5.7 | Released | Modern dashboard, hardware monitoring |
| v1.6.3 | Released | Fan dashboard, menu system, .exe |
| v1.7.1 | Released | Stats Engine v2, Time-Travel, Monitoring |
| v1.7.2 | Released | Startup/Services Manager, Optimization Hub, hck_GPT AI layer, Hybrid Engine (Ollama), bilingual, EXE build |
| v1.7.3 | Released | Live Guide, hck_GPT AI quality (followups, help rewrite, optimization live), session data store, WMI scan, nav links |
| v1.7.4 | Released | Optimization Center redesign (2-col grid, expandable cards, Turbo PP creation, Weekly Report, LIVE NOW), dashboard button restyle |
| v1.7.5 | Released | hck_GPT 13 new intents (community requests), 4 MEGA features (Time-Windowing, No-AI-Slop, Time-Travel Debug, Micro-Bench), process library 104->241 |
| v1.7.6 | Released | DeepMonitor rewrite (Treeview), MAP OF COMPONENTS (2.5D isometric), hck_GPT Wave 2 (6 intents, 82 total), font system 100% coverage |
| v1.7.7 | Released | Ghost Driver Detection (pnputil), RAM Flush exclusion menu, SEE EVERYTHING/OUTDATED driver views, HOT strip stability, MAP fix |
| **v1.7.7-patched** | **Current** | **UI/UX fixes: Startup Manager redesign, Services Manager stop/start logic, Drivers page readability, compact headers** |
| v2.0.0 | **Q2 2026** | ML patterns, advanced gaming |

**[Full Changelog](./CHANGELOG.md)**
-
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
-
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
-
## 📚 Documentation

- **[GETTING_STARTED.md](./GETTING_STARTED.md)** - Installation & setup guide
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history & updates
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - How to contribute
- **[docs/TECHNICAL.md](./docs/TECHNICAL.md)** - Architecture deep dive (coming)
-
## About

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

