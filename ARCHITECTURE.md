# PC Workman - Architecture & Mechanisms Map

One page that answers: "does a mechanism for this already exist?"
Read it BEFORE building anything new. Extend an existing mechanism instead of
creating a second one - that rule is how this codebase stays maintainable.

Updated: 2026-07-17 (v1.8.4 source). App version lives ONLY in
`utils/app_version.py` (APP_VERSION + MAIN_WINDOW_TITLE) - everything else,
including the PyInstaller dist name, reads it. Guarded by tests/test_version.py.

---

## Folder map

| Folder | Role |
|---|---|
| `startup.py` | Entry point. Boot order: import_core -> core modules -> stats engine -> ml_classifier -> live_collector -> metrics_store -> auto_optimizer -> hardware warm-up -> UI -> mainloop. Single instance via named mutex. Optional UAC elevation (`run_as_admin`). |
| `import_core.py` | Component registry (see Mechanism 1). |
| `core/` | Headless engines. No Tk imports allowed here. |
| `hck_stats_engine/` | SQLite pipeline: minute -> hour -> day -> week -> month aggregation, events, query API. DB: `data/logs/hck_stats.db` (WAL). |
| `hck_gpt/` | The offline assistant: intents (parser/vocabulary/ML), responses (see Mechanism 7), context, memory, panel UI. |
| `ui/windows/` | `main_window_expanded.py` (main 1160x575 app), `main_window.py` (minimal overlay mode). |
| `ui/pages/` | Full pages routed by `_switch_to_page` (destroyed + rebuilt on every visit). |
| `ui/components/` | Reusable widgets (sidebar, charts, drawer, toasts, overlays). |
| `utils/` | Cross-cutting helpers: `paths` (APP_DIR/BUNDLE_DIR, MSIX-aware), `i18n`, `fonts`, `ui_scale`, `admin`. |
| `tests/` | unittest suite (63). psutil mocked - runs headless. |
| `locales/` | `pl.json` / `en.json`. Every new string goes to BOTH. |
| `settings/`, `data/` | Writable state - always under APP_DIR (never BUNDLE_DIR). |

Dev tools (not imported by the app): `hck_gpt/intents/train_classifier.py`
(CLI: retrain the NB classifier), `branding/generate_icons.py`.

---

## Mechanism 1 - Component registry (`import_core.py`)

Global singleton store. A module that others need does
`register_component("core.monitor", self)`; consumers do
`COMPONENTS.get("core.monitor")` (never import the module directly if a
registered instance exists). `STARTUP_MANIFEST` is the expected-keys list;
`verify_startup()` reports missing/extra. **Add every new always-on component
to the manifest.**

## Mechanism 2 - THE data machine (single producer rule)

```
core/live_collector.py  ->  hck_gpt/data/live_sensors.py (the bus)
        |                        ^ consumers ONLY: UI pages, overlay, chat
        v
hck_gpt/data/metrics_store.py -> SQLite deepmonitor_snapshots (5 min)
        |
        v
core/thermal_baseline.py + core/voltage_analyzer.py (learning)
hck_stats_engine/query_api.py (history queries)
```

- `live_collector` is the ONLY writer of live metric keys (cpu_load,
  cpu_temp + `cpu_temp_src` honesty flag, gpu_*, mb_*, disks). 2 s tick.
- Shared cached fetchers: `fetch_gpu_smi()` (nvidia-smi, 1.5 s cache),
  `fetch_mb_sensors()` (OHM/LHM web, 4 s cache). **Never spawn your own
  nvidia-smi** - import these.
- Honesty rule: estimated CPU temps are flagged `cpu_temp_src="est"` and
  NEVER enter history or learning (metrics_store writes -1 instead).
- Allowed bus enrichment (merge, never overwrite): metrics_store's
  `session_hist` + 7-day baselines; My PC page's KB specs (cpu_tdp/pl2/name,
  gpu_tdp).
- Guarded by `tests/test_data_pipeline.py`.

## Mechanism 3 - Hardware identity (one source)

`core/hardware_detector.py` singleton (`get_hardware_detector()`), registered
as `core.hardware_detector`. PowerShell CIM based (works on Win11 24H2 where
wmic is gone), cached after first scan; `ensure_data()` scans synchronously
off-thread, `scan_async()` for background. Warmed at startup during the
splash. Consumers: My PC Components, hck_GPT
(`hck_gpt/context/hardware_scanner.py` copies identity into UserKnowledge).
**Any new feature needing CPU/GPU/board/RAM/disk identity reads this - no new
WMI code.**

### 3b - Upgrade Readiness (one compatibility engine)

`core/hardware_compat.py` is the ONE "will this part fit" engine; its data
lives in `core/hardware_compat_db.py` (320 entries: 174 CPUs, 79 GPUs,
58 chipsets with per-generation native/bios/vendor/blocked support, 9 sockets).
It reads the machine through Mechanism 3 (`current_platform()`), resolves
DDR4-vs-DDR5 on dual-gen sockets from module speed, and knows the real traps
(B460 blocks 11th gen, LGA1151 v1/v2, B550 blocks Zen/Zen+, BIOS-flash cases).
Consumers: `ui/pages/upgrade_readiness.py` (checker page, entry buttons in
Components / First Setup / Monitoring), the Optimization Center's Upgrade
Advisor card, and hck_GPT (`r_upgrade.py`: `upgrade_compat` / `ram_compat`
+ a part-model override rule in the parser). **Extend the db file's tables -
never start a second hardware library.**

## Mechanism 4 - Process safety guard (one gate)

`core/protected_processes.py` - `is_protected(name, exe)` + `is_self(pid)`.
Covers anti-cheat (Vanguard/EAC/BattlEye/...), ~30 OS-critical processes
(dwm, explorer, csrss, lsass, Defender...) and PC Workman itself.
**Every primitive that suspends / kills / re-prioritises / memory-trims a
process MUST call it first.** Already wired: hibernation `sleep_app`, TURBO
suspension, RAM-flush trim, overlay actions, Unused Apps candidate list.
Games themselves are intentionally NOT protected - only anti-cheat engines.

## Mechanism 5 - Always-on daemons (never page-bound!)

Background work lives in core, started from `startup.py`, prefs-driven,
running with zero UI. Pages are configurators + status listeners.
- `core/live_collector` - sensors (Mechanism 2).
- `core/auto_optimizer` - AUTO RAM Flush watcher, Turbo Power Plan reconcile
  (`_tpp_tick`), `ram_flush()` primitive, master-TURBO coupling
  (`set_turbo()`), atexit power-plan restore. Status listeners are
  kind-routed: `register_status_listener(cb, kind="ram"|"tpp")`, unhook on
  widget `<Destroy>`.
- `hck_gpt/memory/proactive_monitor` - chat tips/alerts (45 s).
- `core/app_activity_tracker` - foreground/idle app tracking.
- History lesson: a loop inside a page file runs only while the page exists
  and can accumulate one thread per visit (two shipped freezes came from
  this). If you're writing `while True` in `ui/`, stop.

## Mechanism 6 - Learning engines

- `core/thermal_baseline.py` (VERSION 3): Welford accumulator per
  (workload bucket, metric) for cpu_temp / gpu_temp / cpu_load; 5 buckets
  (idle/light/medium/heavy/gaming); `primary_metric()` picks the best real
  signal so every machine learns; `classify_temp()` gives the verdict;
  `learning_since_str()` / observed-hours for the time counter.
- `core/voltage_analyzer.py`: median+MAD baselines per rail, Nelson rules,
  GPU-transient suppression, recurrence decay.
- Both rebuild incrementally from `deepmonitor_snapshots`; learned state
  persists as JSON under APP_DIR and survives raw-data pruning (183 days).
- Consumers: Learning Center (Monitoring & Alerts), hck_GPT handlers,
  proactive monitor. **New "learn X over time" features belong here, not in
  a new engine.**

## Mechanism 7 - hck_GPT response pipeline

```
panel.py -> chat_handler -> hybrid_engine (rule >=0.65 conf | Ollama)
             -> intents/parser + vocabulary (90 intents, PL/EN per message)
             -> responses/builder.ResponseBuilder  (facade)
                 = 7 mixins: r_hardware, r_thermal, r_gaming, r_system,
                   r_performance, r_insights, r_assistant (+ common.py)
```
- Adding an intent: phrases into `INTENT_PATTERNS` (both languages) + a
  `_resp_<intent>` method in the matching `r_*.py`. Dispatch is
  `getattr(self, f"_resp_{intent}")` - nothing else to wire. The ML
  classifier retrains automatically on the vocabulary fingerprint change.
- Guards: parity test (every intent has a handler), no-duplicate-handler
  test, monolith guard (no responses module may exceed 1,600 lines), and the
  180-call harness pattern (fire every handler PL+EN) used before releases.
- Alert routing: RAM critical -> HOT strip only; advisory tips -> TIP strip.
  Clickable `[-> Name]` markers become nav links via
  `panel.register_nav_callback`.

## Mechanism 8 - The confirm drawer (Services / Startup pattern)

`ui/components/operator_drawer.py` - ONE shared bottom drawer: user toggles
queue changes, the drawer shows the pending list ("SZCZEGÓŁY" expands), and a
single Zatwierdź applies the batch and records who/when
(`changed_by`, `disabled_by`, `disabled_at` in the prefs JSON).
Used by Services Manager and Startup Manager. **Any future "stage changes,
then apply" UI reuses this drawer - do not build a second confirm bar.**

## Mechanism 9 - Prefs & persisted state (who owns which file)

| File (under APP_DIR) | Owner |
|---|---|
| `settings/app_settings.json` | settings_page (language, sidebar, launch_at_startup, run_as_admin, gaming_launch_toast) |
| `settings/user_prefs.json` | optimization: ram_auto/threshold/exclude, tpp_auto/tpp_on_turbo, turbo_active (master flag) - read by auto_optimizer |
| `settings/turbo_services.json` | turbo_manager per-mode service profiles |
| `settings/gaming_overlay.json` | in-game overlay config |
| `data/cache/hibernation_prefs.json` | hibernation ignore-list + turbo behaviors |
| `data/cache/startup_prefs.json` | startup manager disabled entries (ghost-entry reconstruction) |
| `data/cache/service_prefs.json` | service action history |

Pattern: `os.makedirs(dirname, exist_ok=True)` before every write; readers
tolerate a missing file. Writable = APP_DIR (MSIX-safe), bundled read-only
assets = BUNDLE_DIR - both from `utils/paths`, never hand-rolled.

## Mechanism 10 - UI conventions

- Routing: `ExpandedMainWindow._switch_to_page(page_id)` destroys
  content_area children and rebuilds; overlay pages slide in
  (`_animate_overlay_slide`). after-timers stored on self are cancelled on
  switch.
- Wheel: each page binds ONE `bind_all("<MouseWheel>")` handler WITHOUT
  add="+" (overwrites the previous page's). If the widget under the cursor
  has its own wheel binding (interactive charts zoom), the page handler must
  yield - see monitoring_alerts `_wheel`.
- Charts: `ui/components/interactive_chart.py` is THE chart (pan/zoom/pin/
  minimap). `charts.py` is legacy static; bespoke dashboard canvases exist -
  unification is an open pillar. New chart features go into
  interactive_chart.
- Fonts: `utils/fonts` aliases (`UI`, `MONO`) - never hardcode "Segoe UI" /
  "Consolas" in widget tuples. DPI: `utils/ui_scale.init` pins Tk font
  scaling to the window SCALE.
- i18n: `utils/i18n.t(key, default=)`; strings added to BOTH locale files;
  `register_on_change` to rebuild on language switch.
- Every `after()` callback and canvas op guards
  `if not widget.winfo_exists(): return`; "bad window path" /
  "invalid command name" during switches are expected and filtered.
- Toasts: `ui/components/system_toast.py` (general),
  `gaming_toast.py` (game-launch greetings, `_GAME_DB`). Overlays:
  `ingame_overlay.py` (HUD, bind on own widget tree - never bind_all),
  `overlay_mini_monitor.py` (always-on mini).

## Mechanism 11 - Error-handling convention

- `except Exception:` (broad but NEVER bare `except:`) is the deliberate
  norm at (1) Tk teardown paths, (2) per-machine probes (sensors, registry,
  subprocess) where graceful degradation beats crashing a monitor tool.
- Handlers answer with an honest "data unavailable" (`_no_data`) instead of
  guessing when a probe fails.
- Rule of thumb for NEW code: swallow reads, never swallow writes silently -
  log persisted-state write failures via `core.logger`.

## Mechanism 12 - Build & release

`PCWorkman.spec` (onedir). New UI subpackages -> `hiddenimports`. unittest
stays bundled (intentionally NOT excluded). Output `dist/PC_Workman_HCK_x.y.z/`;
scrub before zip/MSIX: reset `user_prefs.json` -> `{}`, reset
`data/process_info/process_statistics.json` -> `{}`, remove machine-local
state. MSIX: version `x.y.z.0` must increment, Identity/Publisher must match
Partner Center, payload = the whole onedir folder.

## Test & verification toolkit

- `python -m unittest discover tests` (63, headless).
- Handler harness: fire all 90 intents PL+EN via `getattr(rb, "_resp_...")`
  - the pre-release gate for hck_GPT.
- Guards encode past incidents: protected-process regression, intent parity,
  monolith guard, data-pipeline invariants, MSIX path resolution,
  auto-optimizer reconcile. **When you fix a root cause, add a guard test so
  the bug class cannot return.**
