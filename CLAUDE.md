# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project overview

**PC Workman HCK** — real-time Windows system monitor with an embedded AI assistant (hck_GPT v2.1.0). Python 3.9+ / Tkinter / Windows 10+ only. Active development, current source version **1.8.0**, app version in `startup.py → APP_VERSION`.

---

## Commands

```bash
# Run the app (dev mode — no .exe needed)
python startup.py

# Run all tests
python -m unittest discover tests

# Run a single test file
python -m unittest tests.test_monitor

# Build .exe (onedir, ~95 MB)
python -m PyInstaller PCWorkman.spec --noconfirm

# Syntax-check a module without running it
python -m py_compile ui/windows/main_window_expanded.py
```

> **Note:** Tests mock `psutil` — they run without a live Windows system. The app itself requires Windows (WMI, winreg, LibreHardwareMonitor).

---

## Architecture

### Startup sequence (`startup.py`)

1. Load `import_core` (component registry)
2. Import `core.*` modules — each self-registers via `register_component(name, obj)`
3. Start `hck_stats_engine` (SQLite pipeline)
4. Start `hck_gpt.intents.ml_classifier` (background train/load)
5. Start `hck_gpt.data.metrics_store` (DeepMonitor snapshots)
6. Import UI modules, create `ExpandedMainWindow`
7. Show welcome toast, start `gaming_watcher`, run `root.mainloop()`

Single-instance enforcement via Windows Named Mutex (`Global\PC_Workman_HCK_SingleInstance`).

### Component registry (`import_core.py`)

Global singleton store. Every module that needs to be accessible elsewhere does:
```python
from import_core import register_component, COMPONENTS
register_component("core.monitor", self)
# elsewhere:
monitor = COMPONENTS.get("core.monitor")
```
`verify_startup()` checks registered set against `STARTUP_MANIFEST`.

### Core data pipeline

```
core/monitor.py          — psutil snapshot every 1s (background thread)
core/scheduler.py        — drives aggregation ticks
hck_stats_engine/        — minute→hour→day→week→month SQLite aggregation
  db_manager.py          — WAL-mode SQLite, thread-local connections
  aggregator.py          — time-boundary detection, pruning
  query_api.py           — range queries with auto-granularity selection
  events.py              — spike/anomaly detection with rate-limiting
```

Database lives at `APP_DIR/data/logs/hck_stats.db` (next to `.exe` in frozen mode, project root in dev).

### Path resolution (`utils/paths.py`)

Always use `APP_DIR` for **writable** data (logs, DB, cache, prefs) and `BUNDLE_DIR` for **read-only** bundled assets (icons, JSON). In dev both point to project root; in frozen EXE they diverge.

### UI structure

```
ui/windows/main_window_expanded.py   — main 1160×575 window (sidebar 180px + content 980px)
ui/components/sidebar_nav.py         — left navigation (SidebarNav)
ui/windows/main_window.py            — minimal floating overlay mode
```

`ExpandedMainWindow._switch_to_page(page_id)` is the central router — destroys current `content_area` children and builds the new page. Dashboard is rebuilt with `_build_dashboard_view()`.

**All `after()` callbacks and canvas operations must guard with:**
```python
try:
    if not widget.winfo_exists():
        return
except Exception:
    return
```
Errors matching `"bad window path"` or `"invalid command name"` are expected during view switches and are filtered in catch blocks — do not re-add `print()` for those.

### Font system

All UI files must use the shared font aliases:
```python
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF
```
Never hardcode `"Segoe UI"` or `"Consolas"` directly in widget font tuples. Exception: intentional weight variants like `"Segoe UI Light"` / `"Segoe UI Black"`.

### Internationalisation (`utils/i18n.py`)

```python
from utils.i18n import t, get_lang, set_lang, register_on_change
t("dashboard.session_averages")   # -> localized string
```
Locale files: `locales/pl.json`, `locales/en.json`. When adding a new string, add it to both files. Use `default=` kwarg on `t()` as fallback when a key may be missing.

### hck_GPT (v2.1.0)

```
hck_gpt/engine/hybrid_engine.py    — routes messages: rule engine (≥0.65 confidence) or Ollama LLM
hck_gpt/intents/                   — parser, 90-intent vocabulary, lang_detect (per-message PL/EN)
hck_gpt/responses/builder.py       — 5700+ lines, one handler per intent, always uses live data
hck_gpt/memory/proactive_monitor.py — background daemon, CHECK_INTERVAL_S=45s
hck_gpt/panel.py                   — Tkinter chat UI with TIP strip (yellow 💡) and HOT strip (red)
```

**Adding an intent:** add the key + trigger phrases to `INTENT_PATTERNS` (vocabulary.py) and a `_resp_<intent>` handler in builder.py — dispatch is dynamic (`getattr(self, f"_resp_{intent}")`). Changing `INTENT_PATTERNS` shifts its MD5 fingerprint, so `ml_classifier` auto-retrains on next start; the keyword parser routes distinctive multi-word phrases immediately. Clickable `[-> Name]` markers in a response become nav links if `panel.register_nav_callback("Name", cb)` is wired (main_window_expanded.py registers Optimization / Startup Manager / Stability Tests). Data-driven intents pull live: `upgrade_advice` from `query_api.get_summary_stats`/`get_temperature_summary`, greetings from `get_top_processes_lifetime`, `startup_check` from `startup_manager._read_startup_entries`.

**Alert routing rule:** RAM critical (`ram_crit`) → HOT strip only via `_push_hot_ram()`. Never send RAM critical as a chat message. Advisory tips with 💡 → TIP strip + `tip_green` tag in chat. The `register_hot()` / `register_hot_clear()` callbacks on `proactive_monitor` wire to `panel._set_hot()` / `panel._clear_hot()`.

**Welcome block** in `panel._welcome()` uses `welcome_bg` tag (`#060810`) applied over both the greeting message and the Commands/Quick check/OPERATIONS table.

### Settings persistence

```
settings/app_settings.json   — language, sidebar, launch_at_startup, gaming_launch_toast, etc.
settings/user_prefs.json     — optimization toggles (RAM auto, TPP)
settings/turbo_services.json — TURBO mode service queue
data/cache/startup_prefs.json  — startup manager disabled entries (includes disabled_by, disabled_at)
data/cache/service_prefs.json  — service action history (changed_by: "UŻYTKOWNIK", last_change)
```

Always call `os.makedirs(os.path.dirname(path), exist_ok=True)` before writing any settings file.

### Proactive gaming toast (`ui/components/gaming_toast.py`)

`GamingToastWatcher` polls running processes every 4s. When a known game `.exe` appears for the first time in the session, it fires a `_GamingToast` (no buttons, 2.2s auto-dismiss, progress bar). Controlled by `app_settings["gaming_launch_toast"]`. Game database in `_GAME_DB` (exe → `{"pl": [(title, subtitle), …], "en": […]}`, bilingual with random variants via `_pick()`); alternate exe spellings map through `_ALIASES`. Add new games to `_GAME_DB` (+ an accent fragment in `_ACCENT_MAP`).

### In-Game overlay (`ui/components/ingame_overlay.py`)

GAMING / In-Game tile in My PC (`ui/components/yourpc_page.py`) opens a translucent always-on-top HUD over borderless games (`overrideredirect` + `-topmost` + `WS_EX_NOACTIVATE`). Config persists to `settings/gaming_overlay.json` (preset / custom_metrics / style). Bind corner-cycling on the overlay's **own** widget tree, never `bind_all` (that leaks clicks from the whole app — the overlay would jump on any PC Workman click). FPS comes from `core/fps_monitor.py`, which reads **RTSS shared memory** (RivaTuner/MSI Afterburner) — no admin, returns `None`/"—" when RTSS isn't running.

### Build notes (`PCWorkman.spec`)

- `excludes=['pytest', '_pytest']` — `unittest` is intentionally **kept** (do not re-add it to excludes)
- `console=True` — diagnostic console auto-hides on successful UI launch via `ctypes.windll.user32.ShowWindow(hwnd, 0)`
- All new UI subpackages (`ui.components.*`, `ui.pages.*`, `ui.guide.*`) must be added to `hiddenimports`
- Settings/fonts/locales directories are conditionally included with `*([...] if os.path.isdir(...) else [])`
- Output: `dist/PC_Workman_HCK_1.8.0/` — copy to desktop, reset `_internal/settings/user_prefs.json` to `{}` before zipping

---

## Key conventions

- **System Idle Process** (PID 0) is filtered at `core/monitor.py` source — never appears in process lists.
- `hck_stats_engine` writes **only** on the scheduler thread; UI reads use separate thread-local SQLite connections.
- Windows 11 detection: check `CurrentBuildNumber >= 22000`, do not trust `ProductName` from registry.
- `_on_confirm` in `startup_manager.py` saves full entry data to prefs (`disabled_by`, `disabled_at`, `value`) so disabled entries survive registry deletion and appear in the Disabled tab as ghost entries reconstructed from prefs.
- Services with `sc qc` returning `START_TYPE=DISABLED` get a grey badge with no Stop/Start buttons — do not show them as actionable.
