# HCK_Labs — PC_Workman_HCK — Changelog
_All notable changes are documented here._

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