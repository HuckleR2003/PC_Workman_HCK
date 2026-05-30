# HCK_Labs — PC_Workman_HCK — Changelog
_All notable changes are documented here._

## [1.7.6] - 2026-05-29

### DeepMonitor — complete rewrite

**`ui/components/pro_info_table.py`** rewritten as `DeepMonitorTable` (alias `ProInfoTable` kept):
- `ttk.Treeview` with 4 aligned columns (Sensor / Value / Min / Max) — no more misaligned labels
- Temperature rows: blue-night background tint; Utilization rows: indigo tint; per-row color intensifies with heat
- Sub-section headers color-coded by type (CPU temp = steel-blue, GPU = violet, Memory = slate-blue, Clocks = teal)
- Action bar: Save Data (filedialog → .txt / .csv), Pause (amber when active), Reset mins/maxes
- Popup: header bar removed, title `"DeepMonitor - PC Workman"`, size 660×760

### MAP OF COMPONENTS — new feature

New file **`ui/components/pc_map.py`**:
- `PCMapView(tk.Frame)` renders a 2.5D isometric PC scene via Pillow at 2× SSAA (1360×1080 → LANCZOS → 680×540)
- Desktop PC mode: case frame, motherboard PCB, CPU + heatsink fins + heatpipes, GPU with fans, RAM sticks (×2/4), SSD, PSU, case fans, cable bundle, LED strip
- Laptop mode: open chassis with horizontal mobo, dual fans, GPU, RAM, M.2 SSD, battery, hinged screen, keyboard grid, trackpad
- Live data: CPU%/temp, GPU temp, RAM%, disk% sourced from psutil + `get_cpu_temp/get_gpu_temp`
- Component colors shift green → amber → red based on heat; hot components pulse via sine-wave animation
- Glow ring under CPU when temp >75°C (GaussianBlur alpha composite)
- Floating labels with connecting lines; live values (e.g. "CPU 34% 52°C")
- Hover bounding-box detection → Toplevel tooltip with component details
- Status bar: CPU%/temp GPU/temp RAM% Disk%
- Wired into My PC as new "MAP" tab (PL: "MAPA", with " PC" superscript badge)
- Data refresh thread every 3s (background, non-blocking)

### hck_GPT — critical bug fix

- **`panel.py`**: `lang` variable undefined in `_welcome()` caused `NameError` on every startup — propagated to `_build_hckgpt_banner()` except block, which showed the `bg="#8b5cf6"` (violet) fallback bar at the bottom of the window. Fixed: `lang = self._ui_lang` added at top of `_welcome()`.

### hck_GPT — Wave 2 community intents (6 new)

Built from community feedback (GitHub Discussions / LinkedIn). All intents have PL+EN patterns, real hardware data, and no hallucination fallback.

- `game_can_run` — checks 20-game `_GAME_DB` for RAM/VRAM/disk requirements vs installed hardware
- `gaming_ram_usage` — live game process RAM (psutil) + session peak + 7-day comparison
- `daily_ram_usage` — live psutil + 7-day `metrics_store` trend; verdict: very high / high / moderate / low
- `battery_estimate` — `psutil.sensors_battery()` + activity-based drain rate (gaming 22-35%/h, work 8-15%/h, idle 3-6%/h)
- `upgrade_feasibility` — WMI slot count + current sticks + disk partitions; reports free slots, max RAM, disk free space
- `top_resource_hog` — TOP 5 by RSS memory + TOP 5 by cumulative disk I/O; auto-detects if user asked for RAM or disk

**Vocabulary:** 76 -> **82 intents** total (68 rule handlers in builder.py)

### hck_GPT — conversation flow

New routing steps in `chat_handler.py` (before the AI parser):
- Step 3.5: greeting detection — "cześć", "hej", "hi", "hello" → warm live-data response with CPU%/RAM%
- Step 3.6: thanks detection — "dzięki", "thanks", "thx" → friendly acknowledgment (4 PL + 4 EN variants)
- Step 3.7: "more info" — "więcej", "tell me more", "rozwiń" → re-runs last intent with refreshed data
- Step 3.8: "what should I do" — "co zrobić", "jak naprawić" → context-aware routing based on last topic + recent events
- `_default_response` now: retries hybrid engine at confidence 0.18, detects `.exe` names → routes to `process_identity`, varies fallback text (4 PL + 4 EN phrases), shows last conversation topic
- Fixed duplicate `"bateria"`/`"battery"` keys in `_QUICK_ALIASES` (both silently resolved to `battery_estimate` only; `battery_drain_rate` was unreachable)

New `builder.py` handlers: `_resp_greeting`, `_resp_thanks`, `_resp_health_check` (rewritten — score 0-100, live CPU/GPU temps, issues list, delta vs typical, verdict badge)

Small talk pool: 5 → 11 variants PL, 5 → 11 EN.

### hck_GPT — proactive monitor — DeepMonitor integration

**`proactive_monitor.py`** new `_check_deepmonitor()` (runs every 3 main cycles ≈ 2 min 15s):
- CPU temp: warn >80°C, critical >90°C (2 consecutive readings, hysteresis)
- GPU temp: warn >82°C, critical >92°C
- Severe throttle: alert when CPU freq <55% of max (separate from normal throttle)
- Multi-drive disk: scans ALL mounted drives (not just C:), alerts any <8 GB free
- Sensor health insight: positive "all clear" message after an issue resolves
- 8 new message pools (PL + EN) for the above events

Banner status text now includes live temperatures: `CPU 34%  RAM 62%  CPU 52°C  GPU 68°C  - OK`

Polish idle tips pool: 11 → 24 entries.

### hck_GPT — system context temperature fix

**`hck_gpt/context/system_context.py`** `snapshot()` now fetches `cpu_temp` and `gpu_temp` via `core.hardware_sensors.get_cpu_temp/get_gpu_temp` (LibreHardwareMonitor-backed). Previously only used `psutil.sensors_temperatures()` which returns nothing on Windows — meaning all temperature-based proactive alerts and LLM context were silently broken.

`build_prompt_context()` now includes `cpu_temp` inline with CPU line and a `GPU temp: XX°C` line.

Ollama system prompt: added `[Recent Conversation]` section (last 3 exchanges), 3 new rules (context continuity, frustration acknowledgment, personality).

### hck_GPT — Language sync

- `panel.py`: `_ui_lang` now initialized from `i18n.get_lang()` instead of hardcoded `"en"`
- `panel.py`: `_on_i18n_lang_changed()` callback registered via `i18n.register_on_change()` — when Settings page switches language, hck_GPT panel updates language and refreshes welcome screen
- `panel.py`: `_welcome()` and `_add_startup_quip()` now bilingual (PL/EN)
- `panel.py`: Polish language option `"⚠ not stable"` badge removed
- `panel.py`: language popup `_select()` calls `i18n.set_lang()` to propagate change globally

### Process library

- **`data/process_library.json`**: 241 → **373 entries** (+82 common processes, +50 games)
- New processes: Signal, Viber, Webex, Bitwarden, KeePassXC, VeraCrypt, Mullvad/ProtonVPN, MPV, PotPlayer, Kodi, foobar2000, AutoHotkey, ShareX, PowerToys, WizTree, Krita, Godot 3/4, Unreal Editor, Obsidian, REAPER, FL Studio, HeidiSQL, RustDesk, Parsec, latencymon, kubectl, kubectl, qBittorrent, Duplicati, WinGet, Rufus, Chocolatey, and more
- New games: RDR2, Horizon ZD/FW, Helldivers 2, Palworld, Satisfactory, Rust, DayZ, Sons of the Forest, Factorio, Cities 1/2, CK3, EU4, HoI4, Stellaris, Victoria 3, TW Warhammer 3, MHW/MHR, RE4/RE8, DMC5, Dark Souls 3, Sekiro, DBD, Hunt Showdown, Phasmophobia, Alan Wake 2, and more

- **`core/process_definitions.py`**: +25 rich entries with `full_name`, `category`, `description`, `purpose`, `normal_behavior`, `warning`, `developer` fields: Brave, Vivaldi, Slack, Zoom, Telegram, WhatsApp, Skype, Signal, Windows Defender, Malwarebytes, Bitwarden, Python, Node.js, Git, Godot 3/4, Unreal Editor, VLC, OBS, GIMP, Krita, Blender, Premiere, DaVinci Resolve, and others

### import_core.py — startup registry

- Every registered component now gets a sequential `seq` number (auto-incrementing, thread-safe)
- `list_components()` now shows `[01] core.logger  [ok]` — sorted by registration order
- `STARTUP_MANIFEST` — list of 20 expected components with intended startup order
- `verify_startup()` — checks registered components vs manifest; returns `{ok, missing, extra, report}` with tick/cross table
- 5 previously unregistered components now register themselves: `hck_gpt.proactive_monitor`, `hck_stats_engine.db_manager`, `hck_stats_engine.aggregator`, `hck_stats_engine.query_api`, `core.startup_watcher`

### Dashboard UI fixes

- **Turbo Boost** frame height: `fill="both", expand=True` on inner frame caused it to stretch vertically — changed to `fill="x"`
- **Optimization Center** excess space: two empty placeholder labels (`tools_label`, `tools_count_label`) removed; `expand=True` removed from content frames
- Both fixes applied to `_build_feature_buttons()` in `main_window_expanded.py`

### Welcome Toast

**`ui/components/system_toast.py`** — new `show_welcome_toast(root, delay_ms=1800)`:
- Slides in from bottom-right 1.8 s after UI is ready
- Auto-detects Windows system language via `GetUserDefaultUILanguage` LCID + `locale` fallback
- Polish: *"Hej! Dziękujemy, że korzystasz z PC Workmana :)"* / English: *"Hey! Thanks for using PC Workman :)"*
- Body text explains the startup monitoring and proactive alerts in user's language
- Version badge: `v1.7.6 · 29.05.2026`
- Violet/indigo colour scheme with hand-drawn PC/WK canvas badge icon
- Wired into `startup.py` right after UI creation

### MAP OF COMPONENTS — display fix

**`ui/components/pc_map.py`**:
- Added vertical scrollbar to canvas wrapper — scene no longer clips at bottom of smaller tabs
- Mouse-wheel scroll support on canvas
- Desktop PC origin `_OY` raised by 40 px (`_CH - 75` -> `_CH - 115`): most of scene visible without scrolling
- Laptop origin `_LOY` raised by 40 px (`_CH - 90` -> `_CH - 130`) to match

### hck_GPT — HOT alert strip (anti-spam system alerts)

**`hck_gpt/panel.py`** — new dark-red `HOT` strip above the `TIP` strip:
- Crimson badge `HOT` + message text; visually connects to TIP section
- Monitors RAM / CPU / GPU temp every 8 s via `_hot_monitor_tick()`
- **Anti-spam logic**: strip appears once when threshold is crossed, stays silently until metrics return to normal — no repeated pop-ins while condition holds
- Thresholds: RAM ≥ 85 % warn / ≥ 92 % critical; CPU ≥ 88 % warn / ≥ 95 % critical; GPU temp ≥ 90 °C critical
- Messages bilingual PL/EN matching `_ui_lang`
- First check 12 s after startup (app settle time); cleared via `_clear_hot()` when all metrics normal
- Widget packed `before=_tip_strip` (or before input if no tip) — always below HOT, above entry

### Font system — 100% UI coverage

**`utils/fonts.py`** already defined `UI` and `MONO` (Inter/Segoe UI + Consolas). Previously ~50% of the UI used it.

All remaining files now import the font system and use `_HDR` / `_BODY` / `_MONO` aliases:

- **`ui/windows/main_window_expanded.py`** — 140 hardcoded font strings replaced (largest file)
- **`ui/windows/main_window.py`** — 45 strings replaced
- **`ui/pages/monitoring_alerts.py`** — 52 strings replaced
- **`ui/pages/first_setup_drivers.py`** — 38 strings replaced
- **`ui/pages/optimization_services.py`** — `_F`/`_M` aliases upgraded to full system + `_HDR` added
- **`ui/pages/services_manager.py`** — `_F`/`_M` aliases upgraded to full system
- **`ui/pages/startup_manager.py`** — `_F`/`_M` aliases upgraded to full system
- **`ui/pages/settings_page.py`** — 40 strings replaced
- **`ui/pages/stability_tests.py`** — 14 strings replaced
- **`ui/pages/page_all_stats.py`** — 22 strings replaced
- **`ui/pages/page_day_stats.py`** — 7 strings replaced
- **`ui/pages/fan_control/hardware_info.py`** — font system added
- **`ui/pages/fan_control/usage_stats.py`** — font system added
- **`ui/components/fan_dashboard.py`** — 35 strings replaced
- **`ui/components/pc_map.py`** — font system added (new 1.7.6 file)
- **`ui/components/pro_info_table.py`** — font system added (DeepMonitor)
- **`ui/components/yourpc_page.py`** — remaining hardcoded strings replaced (had partial coverage)
- **`ui/components/fan_curve_editor.py`** — font system added
- **`ui/components/hardware_graphs.py`** — font system added
- **`ui/components/sensor_kb.py`** — font system added
- **`ui/components/sensor_tree.py`** — font system added
- **`ui/components/sidebar_nav.py`** — font system added
- **`ui/components/system_toast.py`** — font system added
- **`ui/components/led_bars.py`** — font system added
- **`ui/components/charts.py`** — font system added
- **`ui/components/process_tooltip.py`** — font system added
- **`ui/guide/live_guide.py`** — remaining strings replaced
- **`ui/overlay_widget.py`** — font system added
- **`ui/overlay_mini_monitor.py`** — `_F_*` font constants migrated to `_BODY`/`_HDR` variables
- **`ui/dialogs.py`** — font system added
- **`ui/splash_screen.py`** — font system added
- **`ui/theme.py`** — `font_family`/`font_small`/`font_base`/`font_large` now use `_UIF`/`_MONOF` variables

Result: zero hardcoded `"Segoe UI"` / `"Consolas"` strings in the UI layer (intentional weight variants `Segoe UI Light`, `Segoe UI Black`, `Segoe UI Semilight` preserved where used as design choices).

### Code quality

- Replaced all em-dashes `—` with `-` and arrows `->` / `<-` across 58 Python files (1,135 em-dashes, 367 right arrows, 44 left arrows)
- Archived `PC_Workman HCK.exe` (v1.7.5) to `build/archive_v175/`

---

## [1.7.5] - 2026-05-25

### hck_GPT — 13 new intents (community requests)

Built from 28 real responses collected on GitHub Discussions and LinkedIn.

**New intents added to `vocabulary.py` / `hybrid_engine.py` / `builder.py`:**
- `fan_noise_history` — fan speed trend over time, spike detection
- `driver_status` — installed driver ages from Windows registry
- `gaming_vs_work_time` — session split: gaming vs productivity
- `process_identity` — identify unknown process (lookup + safety rating)
- `stale_apps` — apps open but idle for 30+ min
- `fps_degradation` — FPS drop over session with thermal/CPU correlation
- `app_behavior_change` — detect if an app behaves differently than usual
- `startup_slowdown` — boot time trend across sessions
- `temp_comparison` — today's temps vs N-day average
- `crash_context` — what was running at the last crash
- `game_hardware_stress` — hardware load profile during gaming sessions
- `battery_drain_rate` — battery % loss rate, drain source identification
- `power_after_restart` — power draw comparison before/after restart

**Vocabulary:** 63 → **76 intents** total

### hck_GPT — 4 MEGA features

**Context Time-Windowing** (`hybrid_engine.py`)
- `_CONTEXT_WINDOWS` dict — 21 intents mapped to history windows (5 min → 7 days)
- `build_llm_context_windowed()` in `system_context.py` — context scoped to the intent's window; narrow windows strip stale patterns, wide windows append daily metric history

**Fallback / No-AI-Slop** (`builder.py`)
- `_no_data(intent, lang, what_missing)` — structured "data unavailable" response instead of hallucinating; wired into `stale_apps`, `startup_slowdown`, `gaming_vs_work_time`, `temp_comparison`

**Time-Travel Debugging** (`builder.py`)
- `_get_historical_comparison(metric, days, lang)` — compares live sensor value to N-day historical average from `metrics_store.daily_summary()`
- `_METRIC_COL_MAP` — maps user-facing metric names to correct SQL column aliases

**Micro-Benchmarking** (`builder.py`)
- `_trigger_micro_benchmark(bench_type)` — background thread; `cpu_single` (1M sqrt ops) or `disk_seq` (32 MB write+read); results stored in `session_memory` under `micro_bench`

### hck_GPT — session memory additions (`session_memory.py`)
- `get_events_for_window(within_minutes)` — filtered event list for time-windowed context
- `get_spike_context(within_minutes)` — structured spike summary string
- `get_time_windowed_context(intent, lang)` — intent-aware windowed context builder

### hck_GPT — chat handler (`chat_handler.py`)
- 20 new quick aliases (sterowniki, wentylatory, bateria, crash, degradacja fps, etc.)
- `_show_help()` rebuilt with 3 new sections: Time-Travel Diagnostyka, Identyfikacja i bezpieczeństwo, Nawyki i użytkowanie

### Process Library (`data/process_library.json`)
- **104 → 241 entries** (+137 processes)
- New coverage: games (CS2, Elden Ring, Cyberpunk, Tarkov, BG3, KSP, Valheim…), dev tools (PyCharm, IntelliJ, Rider, Cursor, DBeaver…), RGB/peripherals (iCUE, Synapse, Armoury Crate, OpenRGB…), diagnostics (HWiNFO64, GPU-Z, Prime95, FurMark…), VPN/network (WireGuard, Tailscale, NordVPN…), security (BattlEye, EAC, FACEIT, ESET, Bitdefender…), Windows system processes (ntoskrnl, tiworker, audiodg, wsappx, ctfmon…)

### Fixes
- `fan_dashboard.py` — fan settings export now writes to `settings/` instead of project root
- Added `.gitignore` with proper rules for build folders, user exports, and runtime reports

---

## [1.7.4] - 2026-05-14

### Optimization Center — Full Redesign

**`ui/pages/optimization_services.py`**
- Feature grid rebuilt as 2-column layout with equal-width expandable cards; each card has an inline [i] info panel that opens/collapses without leaving the page
- Snapshot strip (CPU / RAM / Disk) now renders subtle fill bars — 9% blend of accent color into surface background, drawn on Canvas to work around Tkinter's lack of alpha channel support
- **Turbo Power Plan**: actually creates a "Turbo PC" power scheme via `powercfg /duplicatescheme` instead of just activating a preset; admin detection via `ctypes.IsUserAnAdmin`; GUID parser rewritten to be language-agnostic (no longer breaks on Polish or other non-English Windows); fallback to Ultimate Performance GUID if HP plan unavailable; `atexit` handler restores original plan on exit
- **Quick Actions** fully replaced: Startup Apps Manager (nav link), Services Manager (nav link), Disk Defragmenter (run), Weekly Performance Report (opens window); removed old shortcuts (flush / telemetry / gaming mode); removed "ALL 4 run on TURBO BOOST" label; accent bars widened to 4px; RUN/OPEN buttons larger; Weekly Report row has dark-green background to distinguish it
- **Weekly Performance Report**: `Toplevel` window with 6 bar charts (3×2 grid) — CPU avg, CPU peak, GPU avg, GPU peak, RAM avg, RAM peak across 4 rolling weeks; W4 = latest week rendered full-color + bold; older bars blended toward background; glow/shadow on latest bar; AI-generated text summary (trend direction, RAM pressure, spike detection); EXPORT .TXT button
- **LIVE NOW** sidebar panel: auto-refreshing CPU/RAM/GPU mini-bars, updates every 2 s via `after()`
- Typography upgraded: feature card titles `("Segoe UI Semibold", 8)`, descriptions larger and readable, Quick Actions labels in Segoe UI Semibold; fixed icon Canvas widgets being created before parent frame existed (reparenting via `configure(master=...)` is invalid in Tkinter — fixed by passing parent at creation)

**`ui/windows/main_window_expanded.py`**
- "More Optimization Tools" button replaced with a subtle dark "Optimization Center" chip (`#0c1018` bg, `#1a2235` border, muted text `#3d5070`); click navigates to My PC → Hardware & Health; glow animation removed

**`ui/components/yourpc_page.py`**
- Added `utils.fonts` import with `_HDR / _BODY / _MONO` aliases so the page uses the same Inter/Segoe UI Semibold font system as the rest of the app

---

## [1.7.3] - 2026-05-02

### Live Guide — nowy moduł

**`ui/guide/live_guide.py`** — nowy plik
- Klasa `LiveGuide`: interaktywna nakładka spotlight na dashboard
- Windows-only technika: `Toplevel` z `wm_attributes("-transparentcolor", "#ffffff")` + `-alpha 0.82`; białe prostokąty canvas = przeźroczyste "dziury", ciemny `#030610` przyciemnia resztę ekranu
- 3 kroki: (1) realtime chart + przyciski filtrów LIVE/1H/4H/1D/1W/1M → (2) lewa/prawa nawigacja z opisem każdego przycisku → (3) karty hardware CPU/RAM/GPU + słupki Session Averages
- Pływająca karta info: pasek akcentu `#8b5cf6`, badge kroku, tytuł, separator, treść, kropki postępu, przycisk DALEJ/Zakończ, ✕ zamknięcie; ESC zamyka overlay
- `_get_spotlight(key)` oblicza bounds celu via `winfo_rootx/y/width/height` relative do `content_area`
- Pozycjonowanie karty: bottom/top/right/center z flip-fallback gdy za blisko krawędzi
- Package marker: `ui/guide/__init__.py`

**`ui/windows/main_window_expanded.py`**
- Dodano `self.guide_left_nav`, `self.guide_middle_center`, `self.guide_right_nav` jako widget refs w `_build_middle_section()`
- `_live_guide_click`: `_close_overlay()` + 280ms delay → `_start_live_guide()`
- `_start_live_guide()`: guard na `current_view == "dashboard"`, guard na `realtime_canvas`, zamknięcie poprzedniej instancji; tworzy i uruchamia `LiveGuide(self)`
- Import blok z graceful fallback gdy `ui.guide.live_guide` niedostępny

### hck_GPT — jakość odpowiedzi

**`hck_gpt/responses/builder.py`**
- `_resp_help` przepisany — 30 linii, 8 sekcji z emoji: 🖥 Hardware / 🩺 Diagnostics & Health / 📊 Performance & Stats / 🔍 Why is it doing that? / ⚡ Optimization / 🔒 Security / 😄 Fun/Personality / 💬 Small talk; pokrywa wszystkie 37 intentów; bilingual PL/EN
- `_resp_optimization` przepisany — `system_context.snapshot()` dla live CPU/RAM, `_hw_profile()` dla flag HDD/RAM-low/few-cores; priorytetowy tip (🔴 >85% / 🟡 >70% / ✓ OK); linki [→ Optimization], [→ Startup Manager]; warunkowy [→ Virtual Memory] i nota o HDD
- `_FOLLOWUPS` rozszerzony 3 → 8 kluczy: dodano `security`, `disk`, `why`, `process`, `session`; istniejące klucze `hw`/`health`/`perf` dostały dodatkowe pozycje
- `_followup()` dodany do 9 handlerów: `_resp_virus_check` (oba paths), `_resp_disk_health`, `_resp_disk_usage_why`, `_resp_battery_drain`, `_resp_uptime`, `_resp_process_info` (oba paths), `_resp_throttle_check` (OK path), `_resp_perf_change`, `_resp_session_compare`
- `record_response_data` dodany do: `_resp_hw_gpu` (`model`, `vram_gb`), `_resp_perf_change` (`cpu_today/yest`, `ram_today/yest`), `_resp_session_compare` (`cpu/ram today/yest`)

### hck_GPT — hardware scanner & session data

**`hck_gpt/context/hardware_scanner.py`**
- WMI scan uzupełniony o RAM speed (MHz) i part number (`Win32_PhysicalMemory`)
- Skanowanie modelu dysku głównego (`Win32_DiskDrive`, pierwszy wpis)

**`hck_gpt/memory/session_memory.py`**
- Session data store: `record_response_data(intent, data)`, `get_response_data(intent)`, `discussed_this_session()` — pozwala późniejszym handlerom referować dane raportowane wcześniej w sesji

**`hck_gpt/panel.py`**
- `_apply_nav_links(widget, text)` — renderuje `[→ Page]` tokeny jako klikalny link (kolor akcentu, podkreślenie on-hover), wywołuje zarejestrowany callback nawigacyjny
- `register_nav_callback(page_id, fn)` — API do rejestracji callbacków nawigacji z main window
- `_open_virtual_memory()` — helper otwierający Virtual Memory przez `subprocess` (SystemPropertiesAdvanced)

**`hck_gpt/intents/vocabulary.py`**
- Dodano multi-word patterns dla `hw_storage` i `hw_all` dla pewniejszego routingu powyżej progu confidence

---

## [1.7.2] - 2026-04-27

### My PC — Central tab redesign

**Optimization Hub** (`ui/components/yourpc_page.py`)
- Zastąpiono pojedynczy przycisk "Optimization & Services" widgetem trójstrefowym na jednym Canvas:
  - **Lewa strefa (57%)** — *Optimization Center*, gradient amber→ciemna czerwień
  - **Prawa-górna** — *Startup Manager*, gradient navy→niebieski + live liczba wpisów
  - **Prawa-dolna** — *Services Manager*, gradient zielony→emerald + live liczba usług
- Zone detection via `_zone(x, y)` (podział `sp = int(w * 0.57)` + `HEIGHT // 2`)
- Hover brightening 1.25× aktywnej strefy
- Metryki odczytywane w daemon thread, aktualizacja przez `canvas.after(0, _draw)`
- Usunięto baner hck_GPT z zakładki Central

**Startup Manager** (`ui/pages/startup_manager.py`) — nowy plik
- Odczyt wpisów startowych z `HKCU`, `HKLM`, `HKLM32` Run via `winreg`
- Baza wiedzy 30 programów: impact (high/medium/low) + rekomendacja (disable/delay/keep)
- Trzy panele: *Optimize at startup* / *Safe to disable* / *All entries*
- Disable = prawdziwe usunięcie z rejestru (`winreg.DeleteValue`) + dialog potwierdzenia
- Preferencje zapisywane do `data/cache/startup_prefs.json`

**Services Manager** (`ui/pages/services_manager.py`) — nowy plik
- Katalog 40+ usług Windows w 4 kategoriach: Essential (🔒) / Recommended / Optional / Likely Unnecessary
- Batch query statusów jednym `sc query type= all state= all`
- Stop / Start / Restart per wiersz; wykrywanie admina (`IsUserAnAdmin`), ostrzeżenie jeśli brak
- **TURBO Mode**: checkboxy na Optional/Unneeded kolejkują usługi do auto-stop; zapis do `settings/turbo_services.json`
- Logi zmian → `data/logs/service_changes.log`

**Navigation wiring** (`ui/windows/main_window_expanded.py`)
- Dodano `_build_startup_manager_view()` i `_build_services_manager_view()`
- `elif page_id == "startup_manager"` / `"services_manager"` w `_switch_to_page()`
- Obie strony dodane do `direct_pages` w `_handle_sidebar_navigation()`

**PCWorkman.spec**
- Dodano `ui.pages.startup_manager` i `ui.pages.services_manager` do `hiddenimports`

### My PC — UI & fonts

- Dodano etykietę **MY PC** (Inter Bold) + separator do paska nawigacyjnego
- Zakładki: czcionka `Segoe UI 7` → `Inter 7 bold`; nagłówki sekcji: `Segoe UI 6` → `Inter 7 bold`
- Przeniesiono Stability Tests + Your Account na dół zakładki (side by side)
- Dodano pasek **SESSION** (`#1e3a5f`): `SESSION: Xh Ym` + `● LIVE`
- Zwiększono wysokość panelu hck_GPT o ~18px (`expanded_h` 280→298)

### hck_GPT — naprawy logiki

- Naprawiono błąd językowy w `_show_help()` — używał `self._last_lang` przed detekcją; zmieniono na `ui_lang`
- Przepisano `_show_help()` — nagłówki `◈`, układ dwukolumnowy, wersje PL i EN
- Naprawiono `_resp_temperature()` — fallback do bazy `minute_stats` gdy `psutil.sensors_temperatures()` puste (Windows)
- Naprawiono `_resp_speed_up_pc()` — usunięto bezwarunkowe TURBO BOOST + FPS tips

### hck_stats_engine — nowe metody query_api

- `get_temperature_history(minutes)` — cpu_temp/gpu_temp z `minute_stats`, current/avg/max
- `get_temperature_summary(days)` — dane z `daily_stats`/`hourly_stats`
- `get_top_processes_lifetime(top_n)` — TOP procesy wg avg CPU ze wszystkich dni
- `get_weekly_summary()` — porównanie bieżących 7 dni vs poprzednie 7 z trendem

### Release 1.7.2 — EXE & packaging

- Wersja ujednolicona we wszystkich plikach (`setup.py`, `startup.py`, `README.md`, spec)
- `requirements.txt` uzupełniony o `numpy>=1.24.0`, `requests>=2.28.0`, `pywin32>=305`
- `PCWorkman.spec` przepisany — 25+ brakujących `hiddenimports` (`hck_gpt.*` submoduły, `ui.components.yourpc_page`, `utils.fonts`, `import_core`), katalog `settings/` dodany do `datas`, `COLLECT(name='PC_Workman_HCK_1.7.2')`
- Build: `dist/PC_Workman_HCK_1.7.2/PC Workman HCK.exe` (10.3 MB launcher, ~94 MB total) ✅

### Codebase cleanup

- Usunięto komentarze `"Apple flat design"`, `"Apple inspired"`, `"Inspired by HWMonitor but BETTER"`
- Usunięto docstring `"MSI Afterburner / Apple inspired"` z `main_window_expanded.py`
- Usunięto `TODO: close overlay...` (zastąpione sensownym komentarzem)

---

## [1.7.2] - 2026-04-22

### hck_GPT — AI Layer & Hybrid Engine

**Panel — Bordeaux Noir redesign** (`hck_gpt/panel.py`)
- Gradient banner redrawn every frame with 5-anchor black→crimson interpolation and sine-wave shimmer per strip
- Left accent bar pulses between `#8b0000` and `#ff2040`; ONLINE badge text pulses between `#ff5566` and `#cc2030`
- `AI` badge rendered as vector rectangle (`#5c0f1a` fill, white 7pt Consolas text) — no image file
- ONLINE badge: dark rect `#1e0508` + crimson outline, pulsing text; no moving line across banner
- Banner sweep at 100 ms; gradient redraw uses `tags="grad"` / `tag_raise("ui")` to keep UI elements on top
- Proactive monitor wired in `__init__`: `register_push` schedules alert messages on main thread via `after(0, ...)`; `register_banner` updates status text when panel is closed

**Chat handler** (`hck_gpt/chat_handler.py`)
- Language detected per message (`detect_language`) → `proactive_monitor.set_language(lang)` → `hybrid_engine.process(msg, result, lang)`
- `_LEGACY_ONLY_KEYWORDS` expanded to cover all `_ROUTES` keys (`alerts`, `insights`, `teaser`, `raport`, etc.) — prevents Ollama from intercepting InsightsEngine commands

**Response builder** (`hck_gpt/responses/builder.py`)
- Full bilingual rewrite: `_t(lang, pl, en)`, `_pick(lang, pl_pool, en_pool)`, `_followup(key, lang)` helpers
- 20+ handlers updated: CPU, GPU, RAM, health check, temperature, throttle, performance, greeting, thanks, help, small talk, processes, storage, optimization, uptime, power plan, stats, motherboard, service wizard
- Response variety via `random.choice()` pools: 4+4 greetings, 4+4 thanks, 3+3 health intros, 3+3 perf intros
- `_resp_hw_storage()`: skips `remote` drives, caps at 5 drives, uses `all=False` partitions (no network-drive freeze)
- `_resp_processes()`: capped at 128 process iterations

**Intent vocabulary** (`hck_gpt/intents/vocabulary.py`)
- All diagnostic intents enriched with multi-word phrases (`"health check"`, `"system health"`, `"pc health"` etc.) — confidence now reaches 1.00 for direct queries
- New `small_talk` intent (low-scoring tokens → Ollama preferred)
- Pattern tuning: diagnostic intents score ≥ 0.60 to route through rule engine

**Intent parser** (`hck_gpt/intents/parser.py`)
- Added `_ascii_fold()`, `_normalize_accents()`, `_ACCENT_MAP` for Polish accent normalization
- Dual scoring: scores against original text AND ASCII-folded version, takes `max()` — fixes "dzieki"→thanks, "wydajnosc"→performance, "specyfikacja"→hw_all
- `folded_patterns_cache` built once per `parse()` call (not per intent)

**Session memory** (`hck_gpt/memory/session_memory.py`)
- CPU/RAM trend buffers (`deque` maxlen=8): `push_metric()`, `get_trend()` (compares first/second half averages, delta > 5 = rising/falling), `trend_summary()`
- Auto-conversation-summary every 6 user messages: `_auto_summarize_impl()` extracts topic stack labels
- `get_context_for_llm()` → compact multi-section string: current topic + summary + last 3 exchanges + recent events + trends
- `add_message()`: strips null bytes, wraps auto-summarize in try/except
- `recent_exchange_text()`: strips `"hck_GPT:"` prefix, formats as `User:` / `hck_GPT:` pairs

**System context** (`hck_gpt/context/system_context.py`)
- Top 3 processes: capped at 128 iterations, stored as `{name, cpu, ram_mb}`
- Temperature reading: `sensors_temperatures()` → up to 6 readings
- Windows-safe disk: `os.environ.get("SystemDrive","C:") + "\\"`
- Trend push rate-limited to 30s; `math.isnan()` guard before `session_memory.push_metric()`
- `build_llm_context(lang)` → 6 sections: Live State, Today's Averages, Top Processes, Temperatures, Hardware Profile, Conversation Context

**Proactive monitor** (`hck_gpt/memory/proactive_monitor.py`)
- CPU counter resets to 0 immediately when CPU drops 10 % below threshold (was slow decrement)
- `cpu_percent(interval=1)` (reduced from 2s blocking)
- Windows disk path: `SystemDrive` env var with partition fallback
- `freq.max > 0` guard in throttle check; empty tips guard in `_maybe_idle_tip()`

**New: Hybrid Engine** (`hck_gpt/engine/hybrid_engine.py`, `hck_gpt/engine/__init__.py`)
- `OllamaClient`: `is_available()`, `list_models()`, `generate()` — stdlib `http.client` only, `try/finally conn.close()` in all three methods
- `HybridEngine` routing: `RULE_THRESHOLD=0.60` → rule engine; `_OLLAMA_PREFERRED_INTENTS={"small_talk","unknown"}` → Ollama first; low-confidence fallback chain
- Temporary unavailability: 60s cooldown after timeout, 30s after empty response (not a full blacklist)
- `_build_system_prompt(lang)`: 4-section prompt — Identity, Rules (9 hard rules: short, no markdown, no invented data), PC Context (`build_llm_context`), Language instruction
- Model preference: `llama3.2` > `mistral` > `phi3` > `gemma2` > `qwen2.5`
- `get_status()` → diagnostic dict

**New: Language detection** (`hck_gpt/intents/lang_detect.py`)
- `detect_language(text) → "pl" | "en"`; instant PL on diacritic detection; word-frequency scoring fallback; default PL

**New: User knowledge base** (`hck_gpt/memory/user_knowledge.py`)
- SQLite at `AppData/Local/PC_Workman_HCK/user_knowledge.db`, WAL mode, per-call connection with `try/finally`
- Tables: `hardware_profile`, `usage_patterns`, `user_facts`, `conversation_log`
- `hardware_is_fresh(max_age_hours=24)`, `build_knowledge_summary()`

**New: Hardware scanner** (`hck_gpt/context/hardware_scanner.py`)
- `scan_and_store(force=False)`: skips if fresh (24h); runs in background daemon thread on import
- `_scan_psutil()`: cores, freq, RAM, partitions; `_scan_wmi()`: CPU model, GPU + VRAM, mobo, RAM speed; `_scan_os()`: Windows version

### Efficiency Tab — Fixes & Per-Core Stats (`ui/components/yourpc_page.py`)
- Fixed C11 bug: `cpu_count(logical=True)=12` was used on 6-core CPU; switched to `cpu_count(logical=False)` → correct physical core count
- Fixed invisible avg text: `fg="#6366f1"` on dark bg → `fg="#a5b4fc"` (light lavender, clearly visible)
- Module-level `_CORE_SESSION` dict tracks min/max/sum/cnt per physical core across refresh ticks
- Core card now shows min / max / avg per core below the bar
- Side-by-side TOP CPU and TOP RAM consumers (separate `consumers_row` frame, both packed left)
- Process rank tracker (`_PROC_SESSION`): rank badge, name, NOW%, session AVG%, time-in-rank duration

### HCK_Labs Globe Icon (`ui/windows/main_window_expanded.py`)
- Replaced filled square with vector globe: circle (sphere outline) + meridian oval + equator line + N/S parallels, drawn with `create_oval` / `create_line` — no image file

### Stability Fixes
- `process_iter()` capped at 128 entries in both `system_context.py` and `responses/builder.py` (prevents UI hang on loaded systems)
- Network drive freeze: `disk_usage()` skips `remote` drives, uses `all=False`, capped at 5
- `None`/`NaN` guard before `session_memory.push_metric()`
- `_auto_summarize()` exceptions swallowed via `_auto_summarize_impl()` — `add_message()` never raises
- Null bytes sanitized in `add_message()`
- Connection leaks fixed: `try/finally conn.close()` in all three `OllamaClient` methods
- Ollama hijack of InsightsEngine commands fixed via expanded `_LEGACY_ONLY_KEYWORDS`

---

## [1.7.2] - 2026-04-21

### Dashboard Nav Buttons — Full Redesign
- New dark-gradient canvas buttons: deep navy `#080b18`→`#101626`, 3px accent stripe on left edge
- Bordeaux/crimson L-corner brackets (`|_` + `_|`) on bottom of each button
- Hover fills button with darkened version of each button's accent colour (72% blend)
- Vector icons drawn programmatically per page (no PNG files): monitor, `!`, bar chart, bolt, fan, flask, book
- Removed "QUICK ACCESS" / "EXPLORE" section labels — more vertical space for buttons
- Button labels updated: "Sensors" → "MONITORING / Centrum", "Live Graphs" → "AllMonitor", "Advanced Dashboard" → "FAN Dashboard — Central"

### Navigation Routing Fixes
- "MONITORING — Centrum" now correctly loads `build_monitoring_alerts_page` (fixed wrong import name)
- "AllMonitor" click opens `My PC — Hardware & Health` overlay + auto-triggers ProInfoTable popup (180ms delay)
- Overlay title for `live_graphs` fixed to show "My PC - Hardware & Health"
- `_launch_hw_table_window_root` helper added for root-anchored popup calls

### HCK_Labs & Guide Pages — Blog Redesign
- HCK_Labs: hero section, 3-col About cards, 6-item features grid, comparison table, build info footer
- Guide: full-width blog with 5 article sections, Quick Tips row, "▶ Guide on program LIVE" placeholder button

### Turbo Boost — Coming Soon State
- Turbo Boost button in main dashboard set to grayed-out state (all colours #374151/muted)
- Hover shows floating tooltip: "Coming soon… Check Optimization Center for features"
- Toggle/launch bindings removed until feature is fully implemented

## [1.7.2] - 2026-04-20

### Optimization & Services — Full Redesign
- New "OPTIMIZATION CENTER" hero header with TURBO BOOST gradient button (amber pulse animation via `math.sin`)
- Rectangular emerald badge showing `1 / 14 active` features count
- TURBO BOOST flashes individual Quick Action button backgrounds green/red for 2.5s on run
- Columns swapped: Features list (with coming-soon rows) on left, Quick Actions on right
- Left column fixed at 280px width; right column expands freely
- AUTO RAM Flush settings persisted to `settings/user_prefs.json` — survives restarts
- Compact RAM flush card: removed live RAM % display, cleaner RUN canvas button (72×28px, bordeaux→emerald gradient)
- RAM monitor daemon auto-restarts on launch if `ram_auto=True` was last saved state

### Font System
- New `utils/fonts.py` — loads Inter font family via Windows GDI32 (`AddFontResourceW`)
- Falls back to Segoe UI if `data/fonts/InterVariable.ttf` not present
- Font loaded once at startup, available to all tkinter widgets by name

### Repository Cleanup (pre-release)
- `.gitignore.txt` → replaced with proper `.gitignore` (added `data/logs/`, `settings/user_prefs.json`, `assets/fonts/*.ttf`)
- Removed `docs/backup/`, `docs/1.5.0_official_annouce_screens/`, `docs/google9bc8246e2e876106.html`
- Removed orphaned `utils/file_utils.py`, `utils/net_utils.py`, `utils/system_info.py` (never imported)
- Removed `hck_gpt/report_window.py` (640 lines, unused)
- Removed `ui/hck_gpt_panel.py` (backward-compat shim, no longer needed)
- Removed `hck_stats_engine/trend_analysis.py` (dead code, never called)
- Fixed broken import paths in `main_window.py`: `ui.page_day_stats` → `ui.pages.page_day_stats`
- Cleared all `__pycache__/` directories

## [1.7.2] - 2026-04-13

### New: First Setup & Drivers page (`ui/pages/first_setup_drivers.py`)
- Full system readiness page: health score gauge (0–100 arc), 4 driver health cards (GPU / Audio / Network / USB), startup program list, setup checklist
- Driver data sourced directly from Windows registry — no admin rights required
- Background scan via `threading.Thread`; UI updates on main thread via `after(0, ...)`
- Health score computed from driver ages and startup count; color-coded green/amber/red
- Each driver card: left accent bar, freshness bar (age ratio), status badge (CURRENT / 6+ MONTHS / Xmo OLD), Device Manager shortcut
- Pulsing scan dot animation while scan is in progress; Re-Scan button refreshes all data
- Canvas width auto-bound to parent via `<Configure>` — no horizontal overflow
- Setup Checklist: 6 items, persisted to `data/cache/setup_checklist.json`, animated progress bar
- Sidebar entry "Setup & Drivers" placed after My PC as a simple (no-dropdown) button
- Fixed `yourpc_page.py`: "First Setup & Drivers" button now navigates to `first_setup` (was incorrectly routed to `optimization/wizard`)
- Badge on My PC button shows live checklist completion `X/6 done` loaded from JSON

### hck_GPT Chat — Time Badge
- New `_make_time_badge()` in `panel.py`: inline `tk.Canvas` badge (62×14px) embedded in the chat Text widget via `window_create`
- Badge design: red left/right bars, dark centre, current time in `HH:MM` format (Consolas 7 bold, silver `#94a3b8`)
- Inserted automatically before every `hck_GPT:` message

### Process Library Expansion (`data/process_library.json`)
- Added 8 new entries: `claude.exe`, `datatransfer.exe`, `wmiprvse.exe`, `msmpeng.exe`, `registry`, `hitman.exe`, `hitman2.exe`, `hitman3.exe`

### TOP 5 Dashboard — Process Tooltips
- Imported `ProcessTooltip` + `process_library` in `main_window_expanded.py`
- `<Enter>` / `<Leave>` bindings on both name label and row frame in user and system TOP 5 panels
- `proc_name` stored in widget_data, updated each render cycle — tooltip always reflects current process

---

## [1.7.1] - 2026-04-10

### Code Cleanup
- `core/monitor.py` — removed redundant inline comments, unused `import platform`, `### HCK_Labs` header
- `core/analyzer.py` — removed `### HCK_Labs` header
- `core/hardware_sensors.py` — rephrased GPU clock comment, removed "Note:" prefix
- `ui/windows/main_window_expanded.py` — deleted dead `_build_yourpc_page_OLD_REMOVED` (~130 lines), stale module-moved comment, "innovative" docstring wording

### Versioning & Packaging
- Bumped version to `1.7.1` across `setup.py`, `startup.py`, `main_window.py`, `main_window_expanded.py`, `README.md`
- `requirements.txt` — removed `tkinter` and `tk>=0.1.0` (both stdlib, not pip-installable)
- Release date updated to `2026-04-10`

### Test Coverage
- `tests/test_monitor.py` — rewritten: 7 test cases; fixed broken `monitor.read()` call → `read_snapshot()`; covers snapshot keys, value types, process parsing, CPU/RAM sort, n-limit, cache hit, background thread
- `tests/test_analyzer.py` — rewritten: 7 test cases; logger injected via `COMPONENTS` mock; covers averages, spike detection, empty buffer, old-sample filtering, threshold edge cases
- `tests/test_avg_calculator.py` — rewritten: 4 test cases; uses `tempfile` + patched `HOURLY` path; covers missing file, single-day avg, multi-day split, result key presence

### UI — TOP 5 Process Panels
- Row height `22px → 36px`; layout changed from single-line to 2-line: name on top, CPU+RAM bars below
- Labels `C` / `R` replaced with `CPU` (blue) / `RAM` (amber) with accent color matching bar fill
- Max visible process name length `14 → 20` characters
- Thin vertical divider between CPU and RAM halves

### AnimatedBar — Reusable Animated Progress Bar
- New class `AnimatedBar` in `ui/components/led_bars.py`
- Ease-out interpolation: `EASE = 0.18`, `~60fps` via `after(16ms)`, snaps at `< 0.4%` delta
- API: `bar.bg_frame` for layout placement, `bar.set_target(pct)` to animate
- Applied to: TOP 5 user process rows, TOP 5 system process rows, Session Averages (CPU/GPU/RAM)

### Dashboard Chart — Bug Fixes & Colors
- Fixed blank chart on startup: `<Configure>` binding detects when canvas has real dimensions and triggers first draw
- Added `_schedule_chart_update()` with `after_cancel()` — prevents duplicate update loops
- Filter buttons `LIVE / 1H / 4H / 1D / 1W / 1M` now trigger immediate redraw (`after(50ms)`) instead of waiting for 2s timer
- Fixed bar colors: CPU `#3b82f6`, RAM `#fbbf24`, GPU `#10b981` (replaced dark/brown placeholders)
- Placeholder text `"Collecting data..."` shown while buffer is empty instead of silent no-op

---

## [1.7.0] - 2026-03-XX

### hck_GPT — Process Knowledge Base
- New file `hck_gpt/process_library.py` — static knowledge base with definitions for 80+ common Windows processes and applications
- Each entry includes: publisher/author, short description, security classification, energy profile, expected CPU/RAM usage ranges, and contextual notes (e.g. "Heavy load during library updates" for Epic Games Launcher, Steam)
- Categories covered: gaming launchers, browsers, development tools, communication apps, Windows system processes, media players, security software
- Used by hck_GPT tooltip system: hovering a process name in any TOP 5 panel shows a rich popup with the above data
- Graceful fallback: unknown processes display raw psutil data without crashing

---

## [1.6.8] - 2026-02-17

### hck_GPT Intelligence System
Full local intelligence layer — no external AI, all rule-based logic on Stats Engine data.

**New modules** (`hck_gpt/`):
- `insights.py` — `InsightsEngine` singleton: habit tracking, anomaly awareness, personalized teasers
- `report_window.py` — "Today Report" Toplevel window with canvas chart, colored sections, process breakdown

**InsightsEngine capabilities:**
- `get_greeting()` — time-of-day + yesterday's summary + recurring app teaser (cached 30min)
- `get_current_insight()` — real-time spike alerts, gaming/browser detection, session milestones (dedup: won't repeat same message)
- `get_habit_summary()` — top 5 apps, browser/game/dev highlights, weekly CPU trend, recurring patterns list
- `get_health_check()` — quick diagnostics: session uptime, current load, today's averages, alert count, data collection status
- `get_anomaly_report()` — 24h events grouped by severity with timestamps + summary insight
- `get_teaser()` — 7-day recurring pattern detection, 15+ template variants per category (Gaming, Browser, Dev, Media, etc.)
- `get_banner_status()` — compact one-liner with session uptime fallback
- `_detect_recurring_patterns()` — finds apps used on 50%+ of last 7 days (>5% CPU or >100MB RAM)
- Session milestone notifications at 1h, 2h, 4h, 8h, 12h marks

**ChatHandler commands:** `stats`, `habits`, `health`, `alerts`, `insights`, `teaser`, `report`, `help`
- Polish language: `co uzywam`, `statystyki`, `co nowego`, `alerty`, `co dzis`, `zdrowie`, `raport`
- Default response now shows current insight instead of "AI not connected"
- `report` command shows text summary + points to visual Today Report button

**Panel upgrades:**
- Rainbow gradient "Today Report!" button (canvas-based, full-width, hover effect)
- Smooth pixel-level fade banner (5-anchor RGB interpolation)
- Auto-greeting on panel open (once per 30min session)
- Insight ticker: 60s interval, dedup (no repeat messages), `winfo_exists()` guards
- Banner status ticker: 30s interval with session uptime fallback

**Today Report window (Toplevel):**
- Session uptime + lifetime uptime + data collection status (days tracked, data points)
- Mini canvas chart: CPU/GPU/RAM lines with Y-axis % labels, X-axis time labels (start→end)
- Averages panel + Peaks panel side-by-side with chart
- Top 5 system processes + Top 5 user apps with active time, category badges (Gaming/Browser/Dev/etc.)
- Yellow alert banner: TEMP & VOLTAGES status (green/yellow/red based on severity)
- Refresh button for live data reload
- Singleton pattern (only one window open at a time)
- Scoped mousewheel binding (only when hovering report window — no leak to main app)

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

### Performance Optimization — Zero-Lag Dashboard
Heavy profiling and iterative optimization to eliminate all UI stutter.

**Background-threaded monitoring:**
- `Monitor.start_background_collection()` — `psutil.process_iter()` moved off GUI thread to a daemon thread
- `read_snapshot()` now returns cached data instantly (non-blocking)
- Startup: `startup.py` launches background collection before UI init

**Dashboard update cadence:**
- Main loop: 300ms → 1000ms
- Hardware cards: every 2s (was every tick)
- System tray: every 3s (was every tick)
- TOP 5 processes: every 3s (was every tick)
- Realtime chart: 2s interval with reusable canvas items (no create/delete)

**Widget reuse pattern (TOP 5 processes):**
- Previously: destroy + recreate 10 widget trees every 300ms
- Now: create once, update labels via `.config()` and `.place(relwidth=...)`

**Nav button gradient fix:**
- Removed `<Configure>` binding (fired on every window-move pixel, 8 buttons × 200 canvas lines)
- Gradient drawn once with 4px strips (window is non-resizable)
- Removed dead `_animate_button_shimmer()` (was 30 FPS / 33ms — ~800 canvas items redrawn per frame)

**Realtime chart rewrite:**
- Replaced PhotoImage pixel-by-pixel rendering (70,000 Python iterations/frame) with canvas rectangle pool
- Items created once, only `canvas.coords()` updated per tick — near-zero overhead

### Dashboard Chart — Historical Data Integration
- All time filter buttons now work: LIVE, 1H, 4H, 1D, 1W, 1M
- 1H/4H query `minute_stats`, 1D queries `hourly_stats`, 1W/1M query `daily_stats`
- Auto-refresh historical data every ~30s while on non-LIVE mode
- Chart rebuilds item pool on filter switch (handles different data sizes)

### Stats Engine Fixes
- **Lifetime uptime persistence**: `flush_on_shutdown()` now aggregates current hour into `hourly_stats`
- **Cross-session data**: `get_summary_stats()` queries all 3 tables (daily → hourly → minute) with dedup
- **System idle process filter**: filtered at source (`process_aggregator.py`) + display (`insights.py`)
- **CPU cap at 100%**: `psutil` per-core values >100% now capped in aggregator and insights

### Info Panel Restyle
- Height reduced from 100px to 50px
- Purple accent (#a78bfa), Consolas 8pt font, thin gradient line
- Typing animation with 4 rotating messages about PC Workman

### Codebase Cleanup
- Removed unused files: `utils/` package (file_utils, net_utils, system_info), `settings/` dir, `expandable_list.py`
- Removed empty artifacts: `_nul`, `nul`, `fan_settings_ultimate.json`
- Removed dead animation code (~60 lines of `_animate_button_shimmer`)
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
- Gradient color maps with RGB tuples for smooth interpolation
- Static gradient (drawn once, no animation — optimized in v1.6.8)

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