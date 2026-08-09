# PC Workman HCK

> **Your PC finally has someone who speaks its language.**

[![Get it from the Microsoft Store](https://img.shields.io/badge/Microsoft%20Store-Available-0067b8?style=flat-square&logo=microsoft&logoColor=white)](https://apps.microsoft.com/detail/9PGW6WS2N50V)
![Version](https://img.shields.io/badge/Version-1.8.7-7c3aed?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active%20Development-10b981?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.9+-3b82f6?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-64748b?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2B-0ea5e9?style=flat-square)

### After 12 months of work: on the Microsoft Store. Just click **Install**.

[<img alt="Get it from Microsoft" src="https://get.microsoft.com/images/en-us%20dark.svg" width="200" />](https://apps.microsoft.com/detail/9PGW6WS2N50V)

**[Or download the latest release](https://github.com/HuckleR2003/PC_Workman_HCK/releases)**, one ZIP, no installer, no account.

**[pcworkman.dev](https://pcworkman.dev)** - website, [guides](https://pcworkman.dev/guides/), and the build-in-public [blog](https://pcworkman.dev/blog/) (Monday / Wednesday / Friday).

---

Most monitoring tools give you numbers. PC Workman gives you **answers**.

Ask *"why is my PC slow right now?"*, and get a real explanation, not just a percentage.  
Ask *"is cs2.exe a virus?"*, get an instant process identity check.  
Ask *"which game pushes my hardware the hardest?"*, get a thermal signature breakdown.

**127 AI intents. The assistant runs 100% on your machine, no API key, no cloud LLM. Just your PC talking to you.**

It learns *your* machine: 82°C is normal while you game but critical at idle, judged against your own history, not a generic 85°C line. Drop an in-game overlay that shows only what you choose, hit ⤢ for a full-screen control center, and watch the Learning Center fill up as it gets to know your hardware. Built by one person, in public, on real hardware.

---

## What makes it different

| Traditional tools | PC Workman HCK |
|---|---|
| `CPU: 87%` | *"CPU at 87% - Chrome and Electron processes, consider closing Discord"* |
| Static charts | Pan/zoom charts: click any point, see pinned tooltip with baseline context |
| Dumb thresholds | Learns your hardware's normal temperatures per workload - gaming vs idle |
| Voltage: raw numbers | SPC control limits - flags deviations, not just ATX spec crossings |
| No context | Remembers patterns, compares today vs your 7-day average |
| Manual checks | Proactive alerts: voltage anomaly? temperature spike? process appeared? Auto-pushed |
| English only | Polish + English, auto-detected per message |

---
## Quick Start

### Windows Users (Easiest)
```
1. Download PC_Workman_HCK_1.8.5.zip from Releases
2. Extract the folder anywhere
3. Run "PC Workman HCK.exe" and you are done.
   (keep the _internal folder next to it - that's the runtime)
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

### Maximized View Mode *(redesigned in 1.7.9)*
- One click (⤢) turns the compact 1160×575 dashboard into a full-screen control center
- Symmetric layout: TOP 8 user processes left, TOP 8 system processes right, chart hub in the middle
- Hardware cards grow into mini-charts with the component name drawn inside the chart corner
- hck_GPT chat scales with the window: +12% default height, +35% in chat-Maximize
- Gaming-HUD chart tooltip: hover to inspect any bar at 72% opacity, click to pin, the pin follows the live buffer and its age keeps ticking

### Upgrade Readiness *(new in 1.8.5)*
- Type a planned purchase ("i5 11400F", "RTX 4070", "DDR5 6000") and get a clear verdict: fits, fits after a BIOS update, or wrong socket with what a swap costs you (board, RAM, cooler mount)
- 320-entry offline hardware library: 174 desktop CPUs, 79 GPUs, 58 chipsets with per-generation support - it knows the traps (B460 cannot run 11th gen, LGA1151 v1 vs v2, B550 blocks Ryzen 1000/2000)
- Quick-pick suggestions filtered to what YOUR chipset actually runs; entry buttons at each part in My PC > Components
- Ask it in chat too: "will a 5800X3D work on my board?", "what RAM fits?" - and the Optimization Center's Upgrade Advisor reads your own 14-day load history to say what is worth buying first

### Fan Dashboard *(rebuilt in 1.8.5)*
- Curve chart with a heat gradient that brightens to red as you raise values, dual % / RPM axes, monotonic drag-safe points and a live temperature marker
- The APPLY rule: chart and sliders are a draft (cards preview in amber); Apply persists the plan and re-locks the chart behind a hover padlock
- hck_GPT [AI] button on the chart: a temperature health check from your learned history, then the learned "hck_GPT - AI" profile chat can apply for you

### Intelligence (hck_GPT)
- **127 intents** across 8 categories (hardware, diagnostics, performance, why, optimization, security, fun, small talk) + gaming/battery/upgrade/privacy
- **Hybrid Engine**: rule-based responses for known intents, Ollama LLM for open-ended questions, 100% offline, no API key needed
- **Bilingual**: Polish and English, auto-detected per message
- **Session memory**: conversation context, CPU/RAM trend buffers, cross-response data store
- **Proactive monitor with DeepMonitor integration**: background daemon watches CPU/GPU temps, RAM, throttle, disk on all drives; pushes alerts automatically; banner shows live temps
- **Conversation flow**: greeting, thanks, "more info", "what should I do" all handled naturally with context-aware routing
- Local insights engine, habit tracking, anomaly awareness, teasers from Stats Engine
- SQLite user knowledge base (hardware profile, usage patterns) at `AppData/Local/`
- Background hardware scanner (psutil + WMI, CPU model, GPU, VRAM, mobo, RAM speed, disk model)
- Chat panel nav links: clickable `[→ Page]` tokens route directly to app pages
- `_followup()` pool system: 8 keys, every response ends with a contextual next-question hint

### Monitoring & Alerts *(significantly extended in 1.7.8)*

- **Interactive charts** (`ui/components/interactive_chart.py`): pan (drag), zoom (scroll wheel around cursor), reset (double-click), crosshair + live value bubble, click-pin persistent tooltip with anomaly reason and baseline deviation
- **Minimap strip** below each chart, full data range with drag-to-navigate selection window
- **Thermal Baseline Engine** (`core/thermal_baseline.py`): learns CPU temperature norms per workload context (idle / light / medium / heavy / gaming) with a true **Welford online accumulator**, running per-bucket stats that accumulate over the whole install life and survive 90-day snapshot pruning, not a fixed window. Chart baseline band shows the learned range, not a window average.
- **Voltage Rail Analyzer** (`core/voltage_analyzer.py`): SPC on 12V / 5V / 3.3V rails using Median + MAD. Nelson Rules 1/2/3/5 (isolated spike, cluster, sustained deviation, trend). 12V GPU-transient suppression. Anomaly decay: pattern repeats ≥5× → "your normal".
- **Learning Center**: per-workload thermal training progress + learned ranges, per-rail voltage SPC baselines, overall %, live PSU health score, and a ↻ Rebuild self-check.
- **hck_GPT integration**: `_check_voltage_rails()` fires `voltage_spike` / `voltage_trend` proactive alerts (bilingual, budget-controlled). `format_for_chat(lang)` on VoltageAnalyzer.
- **Dashboard chart tooltip**: hover any bar → translucent detail box (CPU/RAM/GPU% + sample age) next to the cursor. Click to pin, the tooltip docks to its bar, the age ticks live, and the PIN strip mirrors the hck_GPT TIP/HOT style. Click anywhere to unpin.

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
- Health score gauge (0–100 arc), computed from driver ages and startup count
- 4 driver health cards: GPU, Audio, Network, USB, real data from Windows registry
- Driver freshness bar per card; status badges: CURRENT / 6+ MONTHS / Xmo OLD
- Startup program list (registry HKCU/HKLM Run keys), 6-item setup checklist with persistent state
- Quick Actions: Windows Update, Device Manager, Services, Task Scheduler, System Info, MSConfig

### Startup Manager
- Reads **every** startup source: HKCU/HKLM/HKLM32 Run keys, Startup folders, **Task Scheduler** logon/boot tasks, and **Microsoft Store (UWP)** startup apps, so GPU Tweak, ShareX, LinkedIn, MSI Center and the like finally show up
- Knowledge base of common programs with impact rating (High/Medium/Low) and recommendation
- Reversible enable/disable per source (registry removal · `schtasks` · UWP state); locale-independent task scan works on non-English Windows; choices persist to `data/cache/startup_prefs.json`

### Services Manager - mode configurator
- Catalogue of 40+ Windows services in 4 categories (Essential locked / Recommended / Optional / Likely Unnecessary), plus enumeration of every installed service
- Guided **Quick setup** strip: plain questions ("Do you use Bluetooth?") build your custom profile
- Per-service **G / E / M** chips assign each service to the **Gaming · Economy · MANAGER** modes, one source of truth, synced live with the Features mode buttons (`settings/turbo_services.json`)
- Stop / Start / Restart per service; admin detection; all changes logged to `data/logs/service_changes.log`

### Interface
- Modern dashboard (Apple-inspired design)
- Ultra-compact information density
- Color-coded process lists
- Interactive charts and metrics
- Click-to-investigate functionality
- Process tooltips on TOP 5 panels, hover any process name for instant library lookup

### On the roadmap
- Monitoring & Alerts layout polish pass
- Per-rail voltage history export (CSV)

## Architecture
Modular, scalable design:
```
PC_Workman/
├── core/
│   ├── monitor.py             # psutil snapshot every 1s (background thread)
│   ├── scheduler.py           # drives aggregation ticks
│   ├── thermal_baseline.py    # workload-aware temp learning - Welford accumulator, 5 buckets
│   ├── voltage_analyzer.py    # SPC on 12V/5V/3.3V - Median+MAD, Nelson rules 1/2/3/5
│   └── hibernation_manager.py # SetPriorityClass + NtSuspendProcess for Turbo Mode
├── hck_gpt/
│   ├── engine/        # Hybrid Engine: rule routing + Ollama LLM client
│   ├── intents/       # Intent parser, ML classifier (Naive Bayes), vocabulary, lang detect
│   ├── memory/        # Session memory, user knowledge (SQLite), proactive monitor
│   ├── context/       # System context builder, hardware scanner
│   ├── responses/     # Bilingual response builder (facade + 9 mixins, 109 handlers)
│   ├── chat_handler.py
│   ├── insights.py    # InsightsEngine (habits, anomalies, teasers)
│   └── panel.py       # Chat panel UI
├── hck_stats_engine/  # SQLite pipeline: minute/hourly/daily/monthly stats
├── ui/
│   ├── windows/       # Main window modes (expanded, minimal)
│   ├── guide/         # Interactive spotlight guide (LiveGuide, 3-step tour)
│   ├── components/    # interactive_chart.py, pc_map.py (2.5D isometric), LED bars, tooltips
│   └── pages/         # Full-page views (monitoring, fan control, startup, services)
├── data/
│   ├── logs/          # CSV logs (raw, hourly, daily, weekly, monthly)
│   ├── cache/         # Runtime cache & process patterns
│   └── hck_stats.db   # SQLite long-term storage (WAL mode)
└── tests/             # Unit tests
```

**Design principles:**
- Dynamic component registry (auto-registration)
- Direct inter-module communication
- Designed for future expansion
- Educational value (demonstrates Python best practices)
-

## What's New [1.8.7] - `2026-08-08` - CURRENT

### hck_GPT - guided flows and a conversation that holds together
- Multi-step guides are now an engine rather than one hand-written handler, so every flow understands "next", "yes", "skip" and "stop" for free. Four ship: optimize, cooling, desktop repair and upgrade planning. The optimize flow measures first, walks startup and services, asks before touching RAM, then verifies against the numbers it took at the start.
- A conversation director (11 handlers) keeps a diagnosis coherent when a real person wanders: correcting the subject ("I meant the GPU"), supplying a detail that was missing a moment ago, coming back after trying the advice, or asking why the assistant is confident.
- A semantic routing layer covers the relationships a keyword parser drops: process plus close plus safe is a different question from process plus memory. Out-of-domain questions are refused openly instead of being forced into the nearest intent.

### The 23 published guides are reachable from inside the app
- Hard questions now end with an offer to the guide that answers them in full: 22 guides mapped to 54 intents, offered once per guide per session, after the live answer and never instead of it. Guide links are amber because they open a browser; in-app navigation stays purple.
- The Guide page carries a banner to the same library. Every target is checked by a test against the real files in both languages.

### Optimization Receipts cover TURBO
- TURBO suspended processes and stopped services without ever saying what it gained. Both now print a before and after receipt with the count of what was touched, measured after the action has had time to work rather than 20 seconds in.

### Safety and accuracy
- The mini-antivirus stopped flagging the Print Spooler. A process-library note meaning "heavy or bloatware-class" was escalating the security verdict, so `spoolsv.exe` and `dllhost.exe` read as "caution" despite a valid Microsoft signature. Masquerade, homoglyph and miner detection are unchanged and now pinned by tests.
- The in-game overlay checks the PID before the name, so the app can no longer be asked to freeze itself. Ultrawide screens no longer get a window taller than the screen. The diagnostic console explains itself when Windows Terminal will not let it hide.
- Process library grew from 485 to 521 entries, with vendors read from the Authenticode signature rather than assumed. Test suite from 229 to 316.


## What's New [1.8.5] - `2026-07-21` *(previous)*

### Upgrade Readiness - part compatibility before you buy
- Type a planned purchase (a CPU, GPU or RAM kit) and get a clear verdict: fits, fits after a BIOS update, or wrong socket with what the swap actually costs you (board, RAM, cooler mount). Fully offline, 188 CPUs and 84 GPUs, 58 chipsets with per-generation support - it knows the traps a spec sheet hides, like a B460 board refusing an 11th-gen chip that shares its exact socket.
- Live autocomplete: start typing a model and pick it from a list. Entry buttons sit at each part in My PC > Components, and hck_GPT answers the same questions in chat ("will a 5800X3D work on my board?").

### Fan Dashboard - rebuilt
- Heat-gradient curve that brightens to red as you raise it, dual % and RPM axes, drag-safe points that cannot cross, live fan rings that follow real sensors, and an APPLY rule so the chart draft and the applied plan are two clear states. The hck_GPT [AI] button runs a temperature health check from your learned history and can apply a learned fan profile.

### Monitoring & Learning
- Voltage learning now covers CPU VCore and GPU core, not just the board rails. Learned-baseline anomalies land in the Events log with context ("82°C in gaming workload, normal 57-71°C"). The Learning Center type and layout were cleaned up and fully localized.

### Performance - the app is faster and leaner
- My PC used to take about 2 seconds to open. It is now built once and kept alive, so re-entry is 1-17 ms. The real cause was two blocking `wmic` calls on the UI thread; both now read the hardware identity warmed at startup. The sidebar builds its subitems lazily, cutting steady-state window init to roughly 190 ms.
- One version source (`utils/app_version.py`) drives every title, badge and the build name, guarded by a test. A freeze watchdog and a global error log now leave evidence when something stalls. Per-process CPU is on the whole-machine scale (one busy thread no longer reads "100%" on a 12-thread PC). The process library grew from 373 to 485 definitions.

### Under the hood
- The 6,533-line hck_GPT response builder is now a facade over eight mixins, guided flows and a response ledger were added (96 intents), and the sidebar was restructured. Test suite grew from 21 in June to 194.

## What's New [1.8.0] - `2026-06-22`

### Patched - `2026-06-28`
- **Services Manager rebuilt as a real configurator**: one Wyłącz/Włącz per service feeds a single operator drawer at the bottom of the page, and Zatwierdź applies the whole batch at once, no more per-row dialogs or truncated service names. SZCZEGÓŁY expands the queued list inline.
- **Hardware detection fixed for Windows 11 24H2+** (build ≥ 26100), where `wmic.exe` was removed, My PC → Components now fills in CPU / GPU / RAM / motherboard / disks via a PowerShell CIM fallback.
- Fixed a Features-page crash, made expanded feature cards widen for readability, scoped Services Manager scrolling to the page, and hardened `sc` / PowerShell output decoding so unusual service names can't crash a reader thread.

### Smart Learning - engines wired in, and they accumulate
- hck_GPT now answers temperature with the **learned, workload-aware verdict** instead of a fixed 85°C cutoff: 82°C reads *normal* under a gaming load but *critical* at idle. "voltage check" got its own real handler (was silently aliased to the temperature one). The chat handler imported neither learning engine before, months of learning it couldn't reach.
- The proactive monitor judges CPU temperature against the learned per-workload baseline (z-score), falling back to fixed thresholds until a bucket is trained, so it stops crying wolf during normal gaming. Elevated-but-safe goes out as a 💡 TIP, not an alarm.
- **Thermal baseline is a real Welford accumulator now**: each pass folds only the newest snapshots into a running per-bucket `{n, mean, M2}`, so learning accumulates for the life of the install and survives 90-day pruning, and a continuous tick in the proactive loop keeps it learning while the app runs.
- **Learning Center** in Monitoring & Alerts shows live what was learned: per-workload thermal progress + ranges, per-rail voltage SPC baselines, overall %, PSU health score, and a ↻ Rebuild self-check.
- Voltage rail health now counts **genuine Nelson-rule anomalies** (after GPU-transient suppression + recurrence decay), not the ~1.2% Gaussian tail, a healthy rail no longer reads "critical" once enough samples pile up.
- hck_GPT volunteers two positive learning notes: a one-time 💡 when a workload reaches full calibration ("I now judge temperature against YOUR normal"), and a 💡 "new normal" when a recurring voltage blip becomes your baseline. Both deduped so they never nag.

### GAMING - In-Game Overlay
- New **GAMING / In-Game** tile in My PC: a translucent always-on-top HUD that floats over borderless / windowed games without stealing focus. Left/right-click moves it between the four corners.
- Real HUD table, one row per component (CPU / GPU / RAM / 12V), FPS as a side box, with live values.
- A form-style configurator: 3 presets, or Create Custom where each field is a ▼ dropdown to pick the metric per row, plus a style panel (size / theme / opacity). Live preview matches the overlay 1:1.
- **Live FPS** read from RTSS (RivaTuner / MSI Afterburner), no admin, no DLL injection; shows "-" when RTSS isn't running. Per-pixel transparency is on the way.
- **Game launch greetings**: a one-second corner toast when a known game starts, now bilingual (PL/EN) with random variants across 40+ games (Planet Zoo, Terraria, Minecraft, Helldivers 2, GTA V, Hades…).

### Startup Manager - sees everything
- Now enumerates Task Scheduler logon/boot tasks and Microsoft Store (UWP) startup apps, not just Run keys + Startup folders. GPU Tweak, ShareX, LinkedIn, MSI Center and others finally appear, each with a reversible enable/disable and a source badge (⏰ Task · ⊞ Store).

### Services Manager - configurator + MANAGER mode
- Rebuilt as a configurator: per-service **G/E/M** chips assign services to Gaming, Economy or the new custom **MANAGER** mode, plus a guided question strip. All modes share one config, synced live with the Features buttons.
- New **MANAGER** mode in Features (white chip) with a click-through **ⓘ** that jumps to the Services Manager.

### hck_GPT
- **Process Suspect Guard** mini-AV: author (Authenticode) verification, typosquat/homoglyph detection (svhost, ciaude…) and masquerade checks, wired into "virus check" and process identity.
- Natural-language routing overhaul (everyday phrasings hit the right intent) and purple highlighting of hardware names in chat.
- **Four new data-driven answers:** *"what should I upgrade?"* (the real bottleneck from your own load + temperature history), *"do you spy / what do you collect?"* (honest, local-only, links to Stability Tests), greetings that name your favourite app (*"Fancy CS2 again today?"*), and *"what starts with Windows?"* (your real startup list, links straight to the Manager). Vocabulary now **92 intents**.

## Earlier releases

Every release from v1.5.7 onward is documented in [CHANGELOG.md](CHANGELOG.md), including v1.8.5 (Upgrade Readiness, Fan Dashboard rebuild), v1.8.0 (Smart Learning, Microsoft Store) and the full v1.7.x line.


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
- **Local only:** `/data/logs/hck_stats.db` (SQLite) + learned baselines in `/data/cache/`
- **Never personal:** no files, keystrokes, browsing, or content, ever
- **You control the network:** every outbound connection goes through one gate in Settings; turn it off and the app makes zero connections
- **You control the data:** delete `/data/` anytime to start fresh

### Privacy Assurance
- All monitoring runs locally on your machine
- Open source, the code is auditable
- Network access is optional and off-able in Settings (off = firewall-verifiable zero traffic)
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
| v1.7.7-patched | Released | UI/UX fixes: Startup Manager redesign, Services Manager stop/start logic, Drivers page readability, compact headers |
| v1.7.8-monitoring | Released | Thermal Baseline Engine, Voltage Rail Analyzer (SPC + Nelson rules), interactive pan/zoom charts, proactive voltage alerts, 6-module code-quality pass |
| v1.7.9 | Released | Maximized View Mode redesign, gaming-HUD chart tooltip, hck_GPT on MY PC / Fan tabs, 1326 dead lines removed, 10+ resource leaks fixed |
| **v1.8.0** | Released | **Smart Learning (Welford accumulator, workload-aware temps, voltage SPC), GAMING in-game overlay + configurator, live FPS via RTSS, 40+ game greetings, 4 new hck_GPT intents, Process Suspect Guard** |
| **v1.8.1** | Released | Data machine, anti-cheat guard, learning v3, always-on AUTO |
| **v1.8.2** | Released | Critical freeze fix, admin elevation, scaling, hck_GPT expansion |
| **v1.8.5** | **Current** | **Upgrade Readiness (offline part compatibility), Fan Dashboard rebuild, My PC 2s -> 17ms keep-alive, voltage learning (VCore/GPU), one version source, builder split, 21 -> 194 tests** |
| v2.0.0 | Q4 2026 | Long-term drift, Smart User Activity, Tools & Utils |

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
## Documentation

- **[GETTING_STARTED.md](./GETTING_STARTED.md)** - Installation & setup guide
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history & updates
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - How to contribute
- **[docs/TECHNICAL.md](./docs/TECHNICAL.md)** - Architecture deep dive (coming)
-
## About

**Marcin Firmuga** | Software Engineer

Building PC Workman in public, physical work by day, code by night.

- **Website:** [pcworkman.dev](https://pcworkman.dev)
- **Blog:** [Build-in-public series](https://pcworkman.dev/blog/), Monday / Wednesday / Friday
- **GitHub:** [HuckleR2003](https://github.com/HuckleR2003)
- **LinkedIn:** [Marcin Firmuga](https://linkedin.com/in/marcinfirmuga/)
- **X:** [@hck_lab](https://x.com/hck_lab)
- **Email:** firmuga.marcin.s@gmail.com

Part of **[HCK_Labs](https://github.com/HuckleR2003/HCK_Labs)** initiative.
-
## License

**MIT License** © 2025 HCK_Labs / Marcin Firmuga
Free for personal and commercial use. Attribution appreciated.
-

**Ship what you have. Improve it later.** 💙
