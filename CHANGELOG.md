# HCK_Labs - PC_Workman_HCK - Changelog
_All notable changes are documented here._

## [1.9.3] - 2026-11-22 · PC Cleanup Overhaul

Cleanup rebuilt from the ground up (28 places, disk analysis, free space history, duplicates), Stability Tests that really test, DeepMonitor that recognises false sensors, and everything the new pcworkman.dev feature pages promised. hck_GPT can now propose a change and make it after your yes, with UNDO for every decision.

### Licence: GPL-3.0-only from this version
**`LICENSE`, `TRADEMARKS.md` (new), `CONTRIBUTING.md` (new), `README.md`, `SECURITY.md`, `PRIVACY.md`, `ui/windows/main_window_expanded.py`**
- PC Workman is licensed under the GNU General Public License v3.0 only from 1.9.3. It stays open source: anyone may use, study, share and change it, and anyone who distributes it or a changed version must give the full source under the same licence. Versions up to 1.9.2 were released under MIT and stay MIT.
- The name and logo are covered by `TRADEMARKS.md`, not by the licence. Contributions are accepted under `CONTRIBUTING.md`, which keeps a commercial licence possible.

### Optimization Center, the Feature guide and the Data viewer
**`ui/pages/optimization_services.py`, `ui/components/hero_banner.py`, `ui/components/feature_tour.py` (new), `ui/guide/live_guide.py`, `ui/components/data_viewer.py` (new), `ui/pages/settings_page.py`, `hck_gpt/responses/flows.py`, `hck_gpt/responses/r_hardware.py`, `core/gpt_actions.py`, `ui/windows/main_window_expanded.py`, locales, `tests/test_feature_tour.py` (new)**
- Each category of the Optimization Center (Memory, CPU and power, Services and startup, Proof and advice) sits on a band of its own colour at about a quarter strength, behind its name and its tiles.
- Three tight buttons in the banner: **Optimize with the guide**, **Check the connection** (hck_GPT's connection test) and **Feature guide**.
- **Feature guide**: a short LIVE tour that scrolls to every tile, lights it and says what the feature does, from the tile's own description and note.
- The general **LIVE tour** has a seventh step: it opens the Optimization Center and lights the Feature guide button. All its steps now speak Polish too (they were English only).
- **Data viewer** (Settings › Data and privacy): hck_GPT's approved suggestions, the **local chat history** and hck_GPT's own messages with their entry count and a red **CLEANUP** (412 → 0), the learned temperature normals, the history database's tables and size, the startup entries that are off, and every data file; "see the file" next to each. hck_GPT answers "show / clear my chat history" with a link to it.
- The optimization guide's startup step shows the same clickable top 5 as the chat.
- **Power plans** join the actions with a card and UNDO: the power plan answer lists the other plans, one click switches, UNDO goes back to the previous one.
- The dashboard's CPU / RAM / GPU cards are three equal columns: their width followed the live status text and the row shifted a few pixels when a status changed (the test that watches the layout failed about one run in three).

### hck_GPT proposes, you decide with one click, and every decision has UNDO
**`core/gpt_actions.py` (new), `ui/components/action_card.py` (new), `ui/components/changes_window.py` (new), `hck_gpt/panel.py`, `hck_gpt/responses/r_everyday3.py`, `hck_gpt/responses/r_everyday2.py`, `hck_gpt/intents/insight_rules.py`, `ui/pages/settings_page.py`, `ui/windows/main_window_expanded.py`, locales, `tests/test_gpt_actions.py` (new)**
- "Clean up my startup" gets the top 5 entries worth turning off, each name **clickable**. Unknown programs (not in PC Workman's library) are drawn in amber.
- A click opens **hck_GPT's decision card**: what the program is, who signed it (verified on the usual background, unverified on a warm one with the company the file names), its effect on the Windows start, the suggestion and why, and **I agree / Not now / Tell me more**. A calm banner at the bottom: "hck_GPT proposed turning off at startup: Opera" and "every decision stays on the list of changes, always with UNDO". After "I agree" the card shows the result with an UNDO button right there, and the chat confirms it.
- "Turn off Opera" opens the card by itself. Unneeded running services in the services answer are clickable too (set to Manual and stopped; needs administrator).
- Startup entries are switched off the way Task Manager does it, and Startup Manager's Disabled tab shows them as turned off by hck_GPT. Services remember their start type, so UNDO puts back exactly what was there.
- **List of changes** (Settings › Data and privacy › Approved changes, or `[-> Changes]` in the chat): every hck_GPT decision by date with a big red UNDO while it is in effect, and a second tab with **every startup entry that is off, however it was switched off** (hck_GPT, Startup Manager, Task Manager, Windows Settings), each with "Turn back on". "See the .json file" shows the history in Explorer.
- hck_GPT understands "how do I undo changes", "undo the last change", "what did you change" and "what is off at startup".
- Polish "w autostarcie" was missed by every startup rule (the word stem is "autostar-"): fixed in the new rules.

### hck_GPT answers what people actually ask
**`hck_gpt/responses/r_everyday3.py` (new), `core/system_footprint.py` (new), `hck_gpt/intents/insight_rules.py`, `hck_gpt/intents/semantic_rules.py`, `core/health_score.py`, `ui/components/health_center.py`, `ui/pages/health_report.py`, `tests/test_chat_log_2026_11_22.py` (new)**
- A chat session on the release build: 90 questions, about half answered "I did not understand" or with the wrong topic. All of them route where they belong now, and stay tested.
- **Should I reinstall Windows?** An answer from this PC: the install's age, installed programs, folders in AppData and about how many look like leftovers of removed programs (an estimate), free space; a verdict (not worth it / consider / it will help), what a reinstall gives and costs, cheaper steps first, and "export PC Workman's data before".
- Windows version, Windows 11 readiness (CPU, RAM, TPM, Secure Boot), and Windows 12 called what it is: not announced, an estimate of about 8 GB of RAM, 16 GB and an NPU for the AI features.
- New answers: Linux, the program's own guide ("samouczek", "przewodnik", "czy jest poradnik programu"), stuttering films and series, what you use most (hours from Activity Memory, Windows' own helpers left out), what to play, how much runs in the background and who takes the memory, "what would you do on my PC", "turn off Opera" (the entry, its state and impact, one click away), the date, "no / not that", Scaling Laws, ":)".
- Internet questions no longer fall into "I am adding that detail to the same diagnosis" after a lag diagnosis.
- Health Report has a seventh part, **Software**: many programs, leftovers in AppData, a very old install.


### Duplicates in your folders
**`core/duplicates.py` (new), `ui/pages/duplicates_window.py` (new), `ui/pages/cleanup_page.py`, `tests/test_duplicates.py` (new)**
- Cleanup › **Duplicates…** finds the same file kept more than once in Desktop, Documents, Downloads, Pictures, Videos and Music (files from 1 MB): same size, then a hash of the first and last 64 KB, then SHA-256 of the whole file. Program folders, AppData, hidden folders and OneDrive files that are not downloaded are never read. On the author's PC: 2 948 files, 250 groups, about 4 GB, in 66 s.
- The oldest copy of each group stays and cannot be ticked, nothing is ticked by itself, ticked copies go to the Recycle Bin after a confirmation, with a receipt. If the copy that should stay has gone missing meanwhile, one ticked copy is kept instead.

### Low space: hck_GPT says it once
**`core/space_reminder.py` (new), `hck_gpt/memory/proactive_monitor.py`, `tests/test_space_reminder.py` (new)**
- A drive under 10 % free (or under 10 GB on a drive of 64 GB and up) gets one reminder: how much is left, why it matters (Windows updates fail below about 10 %), a link to Cleanup, and "I delete nothing myself". Again only after 7 days or once more under 3 GB; a new episode starts when the drive has room again. Remembered across restarts. A message hck_GPT holds back while you chat is tried again later, not lost.
- It replaces two alerts that repeated every 5 minutes for as long as the system drive had under 4 GB and pointed at a TEMP button that no longer exists.

### What each startup entry costs, and Windows start time
**`core/boot_cost.py` (new), `startup.py`, `ui/pages/startup_manager.py`, `tests/test_boot_cost.py` (new)**
- Startup Manager shows **⏱ CPU seconds** next to each entry: what the program used in the first 3 minutes after Windows started, measured by PC Workman on every start it sees within 15 minutes of boot, median of the last 12 starts.
- The header shows **Windows start time** from Windows' own Diagnostics-Performance log (event 100). Windows lets only administrators read it; without admin rights the chip says so. After PC Workman switches entries off, the start time before and after that change is shown.

### 1% and 0.1% low FPS
**`core/frame_stats.py` (new), `ui/components/ingame_overlay.py`, `hck_gpt/memory/proactive_monitor.py`, `tests/test_frame_stats.py` (new)**
- While a game runs, a sampler reads RTSS's last frame time every 10 ms. The overlay shows "1% 52 · .1% 41" of the last minute under the FPS; the hck_GPT summary after a session adds 1% and 0.1% low with the number of frames behind them. Same definition as CapFrameX. Without RTSS nothing is shown. At over ~100 FPS some frames fall between reads, so the lows are a close estimate.

### Game profiles
**`core/game_profiles.py` (new), `ui/components/game_profiles_section.py` (new), `ui/components/yourpc_page.py`, `startup.py`, `tests/test_game_profiles.py` (new)**
- My PC › Gaming › **Game profiles** lists the games PC Workman has seen, each with two switches: **Overlay** (shows the overlay with the layout saved when you switched it on) and **TURBO** (stops the TURBO services profile, with a receipt). Both happen when that game starts and are undone when it ends. TURBO needs administrator rights, and a TURBO you started by hand is never touched or restored by a profile.

### `pcworkman://open/deepmonitor`
**`utils/deep_link.py`, `ui/windows/main_window_expanded.py`**
- The DeepMonitor page on pcworkman.dev opens DeepMonitor itself (it opened Monitoring & Learning).

### Smaller things the feature pages promised
**`ui/pages/first_setup_drivers.py`, `ui/pages/startup_manager.py`, `ui/pages/services_manager.py`**
- Driver age is rated per device class: graphics old after a year, network after three, audio and USB after five. Microsoft's own audio, USB and network drivers that ship with Windows (dated 2006) show as "WINDOWS" instead of "246mo OLD" in red, and no longer lower the readiness score.
- Switching startup entries off and changing services now leave a receipt like every other optimization (the startup one says the effect shows after a restart).
- My PC's "PC Workman on this PC" card computed its facts once, when My PC was first opened, and that page lives the whole session: after five hours it still said "Learning since 20 min" while Monitoring & Learning said 5 hours (found in the test build). It now recomputes every 5 minutes, and it has more to say: the learned temperature normal of the most common workload, the CPU over the last 7 days, the program that used the most CPU this week, the usual hour of use and the last stability test. Polish plural fixed ("20 czyszczeń RAM").
- Optimization Center's "Coming soon" promised large files and duplicates, which are now in Cleanup; it lists only the old installers finder.

### Stability Tests that test something
**`core/stability_test.py` (new), `ui/pages/stability_tests.py`, `tests/test_stability_test.py` (new)**
- The page used to check PC Workman's own files and show the database status. It now runs three real tests: **CPU** (one thread per logical core hashing and compressing 1 MB buffers, which release the GIL, so all cores really work: 99 % on an i5-12400F), **memory** (zeros, ones, 0xAA, 0x55 and a fixed pseudo-random block across half of the free RAM, up to 2 GB, read back byte for byte) and **drive** (a test file in TEMP written in 4 MB chunks, flushed, read back and compared, then removed, also if the app was killed mid-run).
- Every second: load, temperature (real sensor or marked estimate), the real clock and Windows' "% Performance Limit". The run stops by itself at 95 °C on a real sensor.
- One verdict in plain words: "Stable. The CPU peaked at 75 °C and held its clock.", "Stable, but 12 °C above this PC's normal for the same load", "The clock dropped at 96 °C: the CPU slowed down to protect itself", a clock drop without heat named as a power limit, memory or drive errors as "not stable". The normal comes from Monitoring & Learning's heavy-load range when it has enough samples; without a sensor the verdict says it judges only clock and errors.
- The file check stays as step 0; missing parts are named in the verdict. Pick the tests and 1/5/10/15 minutes for the CPU; a live line shows temperature and clock. The last result is kept and shown when the page opens.

### DeepMonitor: false sensors, the board, every core
**`core/sensor_sanity.py` (new), `core/live_collector.py`, `core/thermal_baseline.py`, `ui/components/pro_info_table.py`, `hck_gpt/responses/r_sensors.py` (new), `hck_gpt/intents/semantic_rules.py`, `tests/test_sensor_sanity.py` (new)**
- **False sensors are recognised**: 110 °C and above (unconnected inputs, 127 as "no value"), readings that jump between 0 and 100+, a temperature standing still for 30 minutes while the CPU load moved, rails outside ±25 % of nominal, fans above 15 000 RPM. A flagged reading reaches live data as "missing", so alerts, the history database and the learned normal skip it; DeepMonitor shows it greyed with a ✗ and the reason. The learned normal no longer accepts 110 °C.
- New rows: CPU Vcore, the graphics card's fan (0 % at light load is marked as the card's quiet mode, a stopped fan on a hot card in red), and a Motherboard group with every temperature of the board's sensor chip, the +12/+5/+3.3 V rails and the fans. Without LibreHardwareMonitor the group says what it needs.
- Utilization shows every logical core (it stopped at 8; the 12400F has 12). Per-core temperature rows, which never filled on Windows, are gone.
- hck_GPT answers "which CPU temperature is the real one", "Tctl or Tdie" and "my board shows 118 °C": what Package, Core Max, Tctl and Tdie mean, which one PC Workman uses, where the current value comes from, and which sensors are flagged right now.

### Windows and driver changes in Activity Memory
**`core/system_changes.py` (new), `startup.py`, `hck_stats_engine/history.py`, `ui/pages/activity_memory.py`, locales, `tests/test_system_changes.py` (new)**
- PC Workman remembers the Windows build and the graphics driver (registry only). When either changes, an event goes into the history: a dashed violet line on every component's chart and a row in its list, "Graphics driver: 32.0.15.8180 → 32.0.16.1088", with the component's average load and temperature in the 14 days before and after. Clicking the row opens 30 days around it. The first start only records what is there.

### Delete my data
**`core/data_wipe.py` (new), `startup.py`, `ui/pages/profile_page.py`, `tests/test_data_wipe.py` (new)**
- Your profile › Privacy has **Delete my data…**: the confirmation says how many files and MB go (history, learned normals, notes, settings, hck_GPT's knowledge) and that it cannot be undone. The history database is open while the app runs, so the deletion happens at the next start, before anything opens it, and can be cancelled until then. The program's own files (fonts, icons, libraries, the two default settings files) stay.

### Bugs found while building the feature pages
**`utils/cpu_sampler.py` (new), `ui/components/pro_info_table.py`, `core/live_collector.py`, `core/hardware_sensors.py`, `core/opt_receipts.py`, `hck_gpt/responses/flows.py` and 11 more, `core/game_library.py`, `core/game_detect.py`, `ui/pages/startup_manager.py`, `ui/components/page_titles.py`, `tests/test_cpu_sampler.py` and `tests/test_after_domain_fixes.py` (new)**
- **CPU load read 0.0 % in DeepMonitor**, on every core, while RAM updated fine. `psutil.cpu_percent(interval=None)` keeps one "last sample" for the whole process, and 18 places called it: the collector, the sensors, the overlay, the PC Map, hck_GPT's context, the optimization receipts, the guide's before and after. Each call reset the window for the others, so whoever asked a moment after someone else measured a few milliseconds and got 0 % or noise. Every caller now has its own window (`utils.cpu_sampler`); only the dashboard monitor still uses psutil's. A test fails if anyone calls the shared one again.
- DeepMonitor's "Current" clock showed the base clock (2.5 GHz on an i5-12400F running at 4.4); it now takes the collector's measured clock.
- Games installed as "Stardew Valley.exe" did not match the library's "stardewvalley.exe": the note said "stardew valley" in lower case. Names now match without spaces, in the library and in game detection.
- Startup Manager in Polish: the rows said H/M/L under a "Duży wpływ" header (now D/Ś/M), and the tab counting all active entries was called "Do wyłączenia" next to a section of the same name counting only the recommended ones (the tab is now "Aktywne" / "Active").

### Cleanup 2.0
**`core/disk_history.py` (new), `core/disk_usage.py` (new), `core/cleanup.py`, `ui/pages/cleanup_page.py`, `hck_stats_engine/aggregator.py`, `hck_gpt/responses/r_everyday.py`, `tests/test_cleanup_v2.py` (new)**
- **What takes the space on C:** one click goes through the whole drive, read only (1.13 million files in 50 s on the test PC, 96% of the used space counted). Folders and the biggest files come with what they are and what to do: hiberfil.sys (`powercfg /h off`, and what you lose), WinSxS (never by hand, use the component cleanup), Windows\Installer (leave it), Windows.old (Windows removes it after about 10 days; where to remove it sooner), System Volume Information, Steam libraries, node_modules, virtual disks that never shrink, your own folders. Coloured tags: leave it, Windows tool, Cleanup, programs, your files. Click a folder to go inside, "Show in Explorer" next to every row. The other cleaners show sizes; none says what a folder is.
- **Free space over time:** one point a day for every fixed drive (the hourly stats aggregation writes it, three years kept, numbers only). A chart for 30 days, a year or everything, with cleanups as green dots, and one sentence: "For 21 days about 634.9 MB a day has gone. At this pace the drive is full in about 65 days." A cleanup starts a new stretch, so freeing 11 GB does not read as "the disk grows". hck_GPT gets a tip when more than 1 GB a day goes.
- **Receipt:** every cleanup notes the free space before and after on each drive it changed ("C: 41.2 GB → 52.3 GB free"), shown under Last cleanup. Moving big downloads to the Recycle Bin says that the space comes back only when the bin is emptied.
- **New places (19 → 28):** Steam game shaders in every Steam library, listed per game by name from the app manifest; Epic Games Launcher and Battle.net caches; Vivaldi; unpacked NVIDIA and AMD driver installers (C:\NVIDIA\DisplayDriver, C:\AMD, administrator); for developers npm, pip, NuGet and Gradle caches, never ticked by default. New groups: Games, For developers.
- **Clean Windows components:** `DISM /Online /Cleanup-Image /StartComponentCleanup`, administrator only, after a confirmation, with the space freed measured. Never `/ResetBase`.
- hck_GPT's free space answer adds the trend of the system drive and the three biggest folders of the last analysis.

### Found while writing the Cleanup page on pcworkman.dev
**`hck_gpt/responses/r_hardware.py`, `hck_gpt/responses/r_performance.py`**
- "jak zwolnić miejsce na dysku" and "what is using disk space" end in the disk answer, which still said "Optimization -> Clear TEMP -> Run TURBO BOOST". That button moved to Cleanup in 1.9.2. The tip now links to Cleanup, and so do the two TEMP folder lines in the disk and performance answers.

## [1.9.2] - 2026-11-21

### Phase 0 of the next update: sensors and learning
**`core/live_collector.py`, `core/hardware_sensors.py`, `core/thermal_baseline.py`, `hck_gpt/responses/r_meta.py`, `ui/pages/stability_tests.py`, `core/game_detect.py`, `ui/components/gaming_toast.py`, `ui/components/yourpc_page.py`**
- LibreHardwareMonitor on a Polish Windows writes "43,5 °C". The comma was refused, so every temperature and voltage with a fraction was dropped and only whole fan speeds got through: "the server runs and nothing is recorded". The same happened on every Windows that writes decimals with a comma (German, French, Italian, Spanish, Russian, Brazilian, Turkish and others).
- The CPU temperature on Windows was always the estimate (35 + load × 0.5), even with LHM running: the code read it from a function that only works on Linux. It now comes from LHM's "CPU Package" (Intel) or "Core (Tctl/Tdie)" (AMD), chosen by the sensor id, and is learned like the other temperatures. On the test PC the CPU temperature had 0 learned samples after 136 hours.
- Also from the LHM tree: the per-core voltages ("CPU Core #6") no longer overwrite Vcore, the "CPU System Agent" voltage is no longer stored as the motherboard temperature, a 3.3 V rail called AVCC3 is recognised, and LHM on its default port is named LHM, not OpenHardwareMonitor.
- hck_GPT says "I see it" only when temperatures or voltages actually arrive, with the CPU temperature. When the server answers with nothing, it says so and points to running LHM as administrator.
- Learning: "79% learned" after 136 hours. Workloads this PC spends under 5% of its time in (here medium 1.7% and heavy) weighed as much as idle. They are now "rare", learned along the way and shown apart; the figure counts the typical workloads (96% on the same data). When the CPU temperature starts to be measured, it learns next to the other signals instead of dropping the figure to single digits.
- Stability Tests: every file read MISSING in the exe and the Microsoft Store version, because it looked for .py files that a build does not have. It now checks that the module can be loaded. The log viewer reads the data folder of the Store install.
- Minecraft Java Edition runs as javaw.exe and was never recognised. javaw.exe with Minecraft on its command line now counts as Minecraft; any other Java program does not.
- My PC: "Cleanup" opened the Services Manager; it opens the Optimization Center. "Your account" did nothing on click; it says "coming soon" and does not invite a click.

### Phase 1: foundations for the new pages
**`ui/components/nav_history.py` (new), `ui/components/process_ref.py` (new), `ui/components/hero_banner.py` (new), `core/process_history.py` (new), `hck_stats_engine/game_sessions.py` (new), `ui/windows/main_window_expanded.py`, `ui/components/sidebar_nav.py`, `hck_stats_engine/db_manager.py`, `hck_stats_engine/aggregator.py`, `ui/pages/activity_memory.py`, `ui/pages/monitoring_alerts.py`**
- **A way back.** No page knew where the user came from: Optimization went back to the Dashboard whatever came before, Stability Tests, Startup, Services and Setup had no way back at all. The window now remembers each place shown (page, overlay, the My PC tab) and the sidebar shows "← Back: My PC" under the logo; Alt+Left does the same. Going back to My PC opens the tab the user was on. The "MY PC" title over the My PC tabs is clickable and opens the central tab, also from Stability Tests and the overlay configurator.
- **Processes have a card.** Hovering a process in Activity Memory's "heaviest processes" tints the row and shows what the process is (process library) and how it lives on this PC, from the recorded history: "every day for 12 days" or "3 of the last 7 days". One component for all process lists; the click that opens the coming Process Center is built in and waits for it. PC Workman itself was not in its own process library; it is now.
- **Every game is recorded.** Only GPU at 60% for 3 minutes left a trace, so Stardew Valley, PlateUp or Democracy never appeared in the history. Each game the watcher sees is now written with its start, end, GPU peak and average; one game running as two processes is one session; the end moves forward every minute so a crash still leaves the row. Activity Memory draws these sessions on the CPU and GPU charts in a band about 40% lighter than a busy stretch. Recent Events names the game ("BeamNG.drive · 26 min" instead of "26 min").
- **The number of processes is recorded** every minute, with the hourly average and peak, for the Process Center's chart. Existing databases get the new columns in place; older history stays without them.
- **One page header.** The gradient header of HCK_Labs and the Guide is a shared component with up to two stacked buttons on the right, for the new pages.

### Phase 2: the Process Information Center
**`ui/pages/process_center.py` (new), `core/process_center.py` (new), `core/recommendations.py` (new), `ui/pages/startup_manager.py`, `hck_gpt/responses/builder.py`, `hck_gpt/panel.py`, `ui/windows/main_window_expanded.py`, `ui/components/yourpc_page.py`, `ui/components/sidebar_nav.py`**
- A new page in the sidebar: every process on this PC in one place. Processes were shown in eight places and nowhere together.
  - Banner with buttons to the Startup Manager and Windows services.
  - Four tiles: processes now, the 7-day average (recorded from this version on), processes in the background (no window: 93% on the test PC, which is normal for Windows), and programs worth switching off (a click filters the table).
  - The number of processes over time, 1H / 24H / 7D / 30D.
  - A table sorted by a click on any heading (again to reverse): CPU and RAM now, CPU and RAM over 7 days, steady ("daily, 12 days" / "3 of 7 days" / "new"), safe, advice. Filters: all, background, steady, worth a look, games; and search.
  - The card of the selected process: what it is, its numbers now and over 7 days, how it lives on this PC, safety, advice with the reason, and buttons to ask hck_GPT, open the Startup Manager or the file's folder. A process that is not running gets its card from the history.
- Every list of processes leads here: a double click in Dashboard TOP 5, My PC's performance lists or Activity Memory, and a click on a process name in the hck_GPT chat, open the Process Center on that process. "Czym jest centrum procesów" gets an answer with a link.
- The 7-day figures add up all of a program's processes, like the "now" column. The history samples each instance: Claude's 12 processes were recorded at about 30 MB each, and the first version of the table showed 28 MB against 1.9 GB now.
- One place for advice on processes (`core/recommendations.py`): the Startup Manager's tables moved there unchanged, hck_GPT's list of background programs too (its "nvidiaSharecontainer.exe" was in mixed case and never matched). Windows, anti-cheats and PC Workman itself are always "protected". A startup rule names the program itself: steamwebhelper.exe no longer gets the advice meant for Steam.
- The shared gradient banner drew the narrow layout over the right one: a measurement inside the drawing ran a nested redraw (buttons over the title). Fixed for every page that uses it.

### Phase 3: time travel
**`ui/pages/activity_memory.py`, `ui/windows/main_window_expanded.py`, `ui/pages/monitoring_alerts.py`, `core/thermal_baseline.py`**
- **Hardware, a fourth tab in Activity Memory**: CPU, RAM and GPU as three charts on one time axis, dragged and zoomed together, with temperatures, busy stretches and game sessions. Its tiles show each part's average and peak, CPU and GPU temperature and the recorded time. The switch sits next to CPU / RAM / GPU in the top right.
- **The mouse wheel** went from 1 hour straight to 24 hours and lost the place you were looking at. It now steps through 1h, 3h, 6h, 12h, 24h, 3 days, 7 days, 14 days, 30 days, 90 days, a year, everything. Zooming out past "everything" resets the view to the whole history. The window never starts before the first record (three quarters of the chart could be empty, an easy place to get lost).
- **The Dashboard chart** lightens under the cursor and a click opens the Hardware history on the matching range (LIVE and 1H: an hour, 4H: 6 hours, 1D: 24 hours, 1W: 7 days, 1M: 30 days). The click used to pin a bar's tooltip; the tooltip now says what the click does.
- **Monitoring & Learning**: the TEMPERATURE MONITOR and VOLTAGE / LOAD MONITOR headers lighten under the cursor and open the Hardware history.
- **Learning Center**: the ring said "100% learned" from the CPU load while the bars next to it showed the GPU temperature still learning gaming. The ring follows the signal the card shows, and workloads that are rare on this PC are listed apart ("rare, learned along the way") instead of "still learning". The measured CPU temperature takes over the card after 3 hours of readings, not 15 minutes, so the figure does not fall to single digits the moment LibreHardwareMonitor starts.

### Phase 4: the sidebar and the Optimization Center
**`ui/components/sidebar_nav.py`, `ui/pages/optimization_services.py`, `ui/windows/main_window_expanded.py`, `ui/pages/settings_page.py`, `hck_gpt/responses/r_features.py`**
- **The sidebar, renewed.** My PC is the main button, at the top and in bold. The order: My PC, Dashboard, Monitoring & Learning, Process Center, Optimization, Fans, Overclock, Setup & Drivers.
  - Items with subitems are split: a click on the name opens the page and shows its subitems, the arrow on the right opens or closes the list on its own. Before, those items only opened their list.
  - Monitoring & Learning got "All statistics", the Hardware history of CPU, RAM and GPU.
  - The Monitoring icon is a clock instead of a warning sign.
- **The icon rail.** A collapsed sidebar (48 px) clipped every label and margin, leaving the icons 9 px of their 26. It now shows the icons alone, centred, with "← Back" as an arrow, and expands back exactly as it was.
- **The Optimization Center.** Marcin: "the current look really puts people off".
  - The shared gradient banner says what is armed and how full the RAM is, with one main button, "Step-by-step guide" (the 6-step guide from the chat), and a second one to Startup and services.
  - The ready features come in four groups, each with one line of what it is for and one colour: Memory, CPU and power, Services and startup, Proof and advice. There were eight colours for nine cards.
  - The action chips speak the interface language ("OCZYŚĆ RAM", "WŁĄCZ", "OTWÓRZ", "WKRÓTCE"). The left column is wider, so "Defragmentacja" no longer breaks mid-word.
  - The CPU / RAM / C: strip that repeated the "Live" box is gone. So is the "2 / 16 active" counter: it was typed in and said 2 whatever was on.
  - The live GPU value showed "-1%" without an NVIDIA card; it shows "--".
- **A navigation strip on page banners** (Marcin's idea): "MY PC · DASHBOARD │ *where you are* · the pages next to it" along the top of the gradient, the current page underlined, the rest one click away. On the Optimization Center and the Process Center; the new pages get it too.
- **The sidebar hides itself on the Optimization Center** (it slides out at the left edge) for more room, and comes back on every other page. Settings → General has a switch for it, on by default. With auto-hide on for the whole app, nothing changes.
- **hck_GPT** no longer sends people to Network Adapter Reset for slow internet: that feature is still "coming next". The step names what works today, `ipconfig /flushdns`.

### Phase 5: My PC
**`ui/components/yourpc_page.py`, `ui/components/pc_summary.py` (new), `ui/pages/gaming_home.py` (new), `ui/components/slowdown_panel.py` (new), `ui/components/health_center.py` (new), `core/health_score.py` (new), `ui/pages/stability_tests.py`, `core/live_collector.py`, `ui/components/process_ref.py`**
- **Central tab**
  - The "i" buttons are gone. Their explanation shows when the cursor rests on the button itself.
  - "SESJA: 4h 47m" (time since Windows started) is replaced by "PC Workman on this PC": a learning ring with the hours PC Workman has recorded (148 on the test PC) and facts from the history, one every 6 seconds: the game played longest, the quietest and busiest weekday, what the RAM flushes gave, since when it learns. A fact without data behind it is not shown. The ring was empty at exactly 100%, because Tk draws a 360-degree arc as nothing; the same fix went into the Learning Center ring.
- **GAMING / In-Game** is a page now; it used to open the configurator straight away.
  - A red-to-blue banner with "Start configuration" (the configurator) and the MiniOverlay switch.
  - What was learned about gaming: progress, the heaviest games with hours and GPU average, the heaviest processes with "See more · Process Center".
  - A thermal verdict from recorded gaming ("GPU in games: 66°C on average, usually up to 72°C: normal").
  - "CPU: OK · RAM: OK · GPU: OK" in their colours; hover turns red, a click opens that history.
- **Performance** starts with "What slows this PC down": the bottleneck verdict and every finding hck_GPT knows (RAM against its use, XMP, sudden restarts, programs using more than usual, drive state, driver age...), coloured by weight, in the same words as the chat. Three tiles: the CPU clock now and whether anything holds it back, virtual memory, what TURBO has armed.
- **The real CPU clock everywhere.** The live collector stored psutil's base clock, so My PC showed "Current 2500 MHz" with a false LOW badge on an i5-12400F running near 4 GHz, and Performance showed "2500 / 2500 MHz max" in red. The collector reads the "% Processor Performance" counter now; the boost comes from the model table.
- **The CPU temperature in My PC's table** was always a formula on the load, even with LibreHardwareMonitor running. It shows the sensor when there is one, and the title drops "(est.)".
- **Health** has a health centre: a score 0-100 from what is known, in six bars with a reason each.
  - Stability: the Windows event log.
  - Drives: their state and room on C:.
  - Temperatures in games, and the graphics driver's age.
  - Memory: size against use, XMP, virtual memory.
  - Startup.
  - A click on a bar opens where it is looked after. A part without data is left out of the score, not counted as fine.
  - The old "Health score" was a formula on the live load and is gone.
  - "Total (ever)" showed the session again; it shows PC Workman's recorded hours.
  - Recent events leave out program shutdowns and name the game.
- **Stability Tests**: FILE INTEGRITY CHECK has PROGRAM and OTHERS.
  - OTHERS covers the data files the program reads and whether the history database can be written.
  - A line lists what is missing.
  - TEST re-checks every part: yellow CHECKING for 0.4-3 s, uneven so the statuses do not flip together, with a console of the run.
- **Startup** opens with what is worth a look: "1 of 23 startup entries", the names and the advice, and a link to the Startup Manager.
- **The process row highlight** on the Dashboard (and every process list) is 50% stronger (Marcin's request).

### Phase 6: Cleanup, Health report, Your profile
**`core/cleanup.py` (new), `ui/pages/cleanup_page.py` (new), `ui/pages/health_report.py` (new), `ui/pages/profile_page.py` (new), `ui/components/yourpc_page.py`, `ui/windows/main_window_expanded.py`, `hck_gpt/responses/r_features.py`, `hck_gpt/responses/r_everyday.py`, `tests/test_phase6_cleanup.py` (new)**
- **Cleanup.** My PC's button had no page.
  - Two columns. On the left, what to clean in four groups with a box per item and per group:
    - Windows: temporary files, Windows Temp, Explorer thumbnails, error reports and crash dumps, system reports and minidumps, shader caches, downloaded updates, Delivery Optimization;
    - Browsers: Chrome, Edge, Brave, Opera, Opera GX and Firefox, each on its own, every profile, only the page cache (never passwords, history or cookies);
    - Apps: Discord, Steam's store browser, Spotify's streaming cache;
    - Your files: big files over 100 MB and older than 90 days in Downloads, and the Recycle Bin.
  - On the right, what the scan found, biggest first, with a bar, a line on what it is and the files on request.
  - Items whose folders do not exist on this PC are not shown. A program's cache is skipped while that program is open, and the page says which one.
  - The choice is remembered (`cleanup_selection` in the app settings), except Downloads and the Recycle Bin, which always start unticked.
  - "Flush the DNS cache" quick action (`ipconfig /flushdns`, only on click).
  - Below the list, hck_GPT tips that follow from the scan: low free space on the system drive, how big the temporary files are and that this is space rather than speed, when clearing shaders makes sense, which programs to close, what needs administrator rights. Links lead to Startup, Services and the Optimization Center, plus an "Ask hck_GPT" button.
  - Each item is removed only after a confirmation that names the amount.
  - Temporary files and caches are deleted for good, as Windows' Disk Cleanup does. Big files from Downloads go to the Recycle Bin and are never selected automatically. Emptying the Recycle Bin is never selected automatically.
  - Files younger than a day and files in use are skipped. Categories that need administrator rights say so.
  - No registry is touched. A receipt keeps the last cleanup.
- **Health report.** The health score with its parts, what changed since the last saved report, three things to do first and every finding; "Save the report" writes an HTML file to the Desktop.
- **Your profile** (was "Your account", which did nothing): a name for this PC, its kind, CPU and GPU, stats since the beginning, milestones earned from the history, and privacy in one place (what is sent, export, how to delete).
- hck_GPT knows the three pages; "what can I delete" leads to Cleanup and quotes the last scan, if it is under a week old: the total and the three biggest items. The scan is kept as `data/cache/cleanup_scan.json`, with sizes only and no file names.
- Cleanup's scan summary, its receipt and the health report history are written through `utils/prefs_io`.

### Phase 7: the PC map, rebuilt
**`ui/components/pc_map.py` (rewritten), `ui/components/pc_map_scene.py` (new), `ui/components/yourpc_page.py`, `hck_gpt/responses/r_features.py`, `tests/test_phase7_pc_map.py` (new)**
- The old map drew the back faces of its boxes, in list order, so parts showed through each other. Two thirds of the tab stayed empty, and the scene started half scrolled.
- The map is drawn from scratch: an ATX board seen at an angle, with every part in a fixed place.
  - On the board: the CPU socket with a tower cooler, four DIMM slots with the sticks in the second and fourth slots first, the PCIe x16 slot with the graphics card, M.2, the power section and the chipset.
  - Beside the board: the power supply and the SATA drives.
  - Drives are placed by their bus (NVMe or SATA, from `Get-PhysicalDisk`), not by the model name.
- The laptop has its own layout: the bottom cover off, the board, cooling, RAM, NVMe, battery, and the screen behind. It fills about 90% of the map's height.
- The three visible faces are drawn, in depth order. A test measures, off-screen, that every part the user can point at is visible for every combination of sticks, GPU, NVMe and SATA drives, and that no two parts share a place.
- Layout:
  - the map on the left;
  - on the right, this PC (kind, CPU, GPU, RAM, board, drives) and a table of temperatures and loads (now, 7-day average, 7-day peak), one unit per row;
  - "under the cursor": a card on the map, on the side away from the part, with the model and numbers.
- Colours go from green to amber to red: by temperature (40 °C to 85 °C), by load when no sensor reads the temperature, and RAM by memory in use. "Now" and "7-day average" switch the colours and the labels.
- A click on the CPU, GPU or RAM opens its history in Activity Memory.
- Labels are Tk text on the map with no font file paths. Labels that would land on the same spot move up.
- The power supply says plainly that its model is unknown, because Windows does not see it.
- The map is redrawn only when the data, the hovered part or the size changes. The tab is kept alive, and the old map redrew itself every 120 ms even while hidden. Now nothing is drawn or read while the tab is hidden, and the worker thread touches only a plain object.

### Phase 8: the game library
**`data/games.json` (new), `core/game_library.py` (new), `core/game_detect.py`, `ui/components/gaming_toast.py`, `hck_gpt/responses/r_gaming.py`, `PCWorkman.spec`, `tests/test_phase8_games.py` (new)**
- The games moved out of the toast's code into `data/games.json`: 228 games instead of 42. Each game has its `.exe` names, a genre, the Steam appid where it has one, and one to three launch messages in Polish and English. The 42 old games keep their messages.
- The games from the plan are in the library: Democracy 4, PlateUp!, Don't Starve Together, Infection Free Zone, Supermarket Together, Unturned and Minecraft.
  - The `.exe` names of PlateUp!, Infection Free Zone, Supermarket Together, Don't Starve Together, 7 Days to Die, Project Zomboid, BeamNG.drive and The Powder Toy were read from a real install and are marked `verified`.
  - Democracy 4 and Unturned were not installed, so their names are unchecked.
- Fourteen genres, each with its own pool of messages and its own accent colour. A game with no message of its own gets a line from its genre instead of "Dobrej zabawy!" for everything.
- A game seen for the first time on this PC gets a different line ("Pierwszy raz na tym komputerze"). The games already greeted are kept in `data/cache/games_seen.json`, names only.
- Steam games are found by their folder. The folder leads to `appmanifest_<appid>.acf`, which gives the appid and then the genre from the library. A new or misspelt `.exe` name still finds the right game, and an unknown Steam game is greeted by its real name.
- Names any program could have (`discovery.exe`, `fm.exe`, `human.exe`, `cod.exe`, `wow.exe` and 14 more) count as a game only when they run from a game library folder.
- Session history and hck_GPT use the proper names ("cs2.exe" → "Counter-Strike 2"). Sessions recorded before this keep their old names.
- hck_GPT's gaming session answer names the game running now and its genre.
- The launch toast sizes itself to its text, up to 460 px at 100% scaling. The old fixed 300 × 72 px cut longer titles on both sides, and more of them at 125%. The progress bar's canvas no longer sets the toast's width. A test keeps every title within 45 characters.
- `data/games.json` is added to the PyInstaller data files, so the built app and the MSIX ship it.

### Review after phase 8
**`hck_gpt/responses/flows.py`, `utils/install_kind.py` (new), `ui/pages/startup_manager.py`, `dist/msix/AppxManifest.xml`, `core/net_check.py` (new), `hck_gpt/responses/r_network.py` (new), `hck_gpt/intents/insight_rules.py`, `hck_gpt/engine/flow_engine.py`, `hck_gpt/panel.py`, `ui/windows/main_window_expanded.py`, `tests/test_review_2026_11_20.py` (new)**
- **The optimization guide's summary named entries the user had already turned off.** The Startup list was read once, on step 2, and reused on step 5. The summary now reads Startup and Services again. It says what was turned off ("Wyłączone z autostartu: …") and names only what is still on.
- **The Store version's Startup Manager disabled entries only in its own copy of the registry.**
  - An MSIX app's HKCU writes go to the package's private hive unless the manifest turns that off. A test on the installed Store package confirmed it: the key did not reach the real registry, and it was removed afterwards. PC Workman showed the entries as disabled while Windows still started them.
  - `utils/install_kind.py` now knows the install kind (Store, .exe or source) and reads the package's own manifest.
  - With the old manifest, the Startup Manager explains this on a banner and offers "Open Task Manager" (its Startup apps page) instead of a change that would not stick. Scheduled tasks still work, because they go through the Task Scheduler service.
  - The non-admin banner is in the interface language. It no longer tells Store users to right-click and run as administrator.
  - The next package's manifest turns registry write virtualization off: `desktop6:RegistryWriteVirtualization`, the restricted capability `unvirtualizedResources`, and Windows 10 1903 as the minimum. It was checked with `makeappx pack`. Notes and the Partner Center justification are in `local_notes/MSIX_NASTEPNA_PACZKA_2026-11-21.md`.
- **The Startup Manager's list could stay on "Scanning…".** The scan thread called Tk (`page.after`) from outside the main thread, and the error was swallowed. The thread now fills a plain dict, and the page polls it.
- **hck_GPT tests the internet before answering.**
  - Questions like "sprawdź internet", "czy mam internet", "jaki mam ping", "nie mam internetu", "strony się nie ładują", "zmierz prędkość internetu", "wyczyść dns", "wolny internet" and "Wi-Fi się rozłącza" (about 50 phrasings in Polish and English) start a network guide.
  - The guide's first step is a quick test, 1 to 4 seconds (`core/net_check.py`):
    - the router (default gateway);
    - google.com: DNS, ping, jitter and loss;
    - 1.1.1.1 by address, to tell a DNS fault from no internet;
    - a TCP connection to port 443, which works where ping is blocked.
  - Pings use Windows' ICMP API: no administrator rights, and no parsing of the translated `ping.exe` output.
  - The answer starts with a yellow band, "Ocena według testu połączenia z google.com" (a new `§SRC` marker in the chat). Then come the numbers, a verdict and the steps for that verdict. The verdicts are: no network, router silent, no internet past the router, DNS, loss near the router, loss, slow Wi-Fi hop, high ping, jitter, slow DNS.
  - Next, a download speed test (25 MB from Cloudflare's test endpoint), only after "tak".
  - On a DNS fault, the guide offers to flush the DNS cache, then tests again and compares before and after. With no internet at all, "tak" tests again instead of measuring speed.
  - The flow engine's confirm button can now change its label from step to step.
- **Esc:** closes the hck_GPT panel when it is open, otherwise goes to the Dashboard. On the Dashboard it does nothing. In a text field on a page, it only leaves the field.
- Tests: the version-literal rule no longer takes an IPv4 address (1.1.1.1) for a version.

### Found in the test build
**`ui/windows/main_window_expanded.py`, `startup.py`, `utils/deep_link.py`, `ui/pages/cleanup_page.py`, `ui/pages/startup_manager.py`**
- How the test build was checked:
  - every page was opened through `pcworkman://open/<page>`, in Polish, on a copy of the data with network and telemetry off;
  - the window itself was captured, not the screen;
  - the log files were read after each page;
  - a 4-minute run measured memory and CPU: 96 to 140 MB, about 3% CPU of the PC, a stable thread count, and no new errors.
- `pcworkman://open/my_pc` opened an empty "MY PC" overlay, because `my_pc` is the sidebar's id and the router's page is `your_pc`. Links now go through `open_page_from_link()`, which maps the id and marks the page in the sidebar. Before, the sidebar stayed on the Dashboard.
- "Statistics" was an empty "Detailed stats coming soon" page. The tray menu, hck_GPT's link and `pcworkman://open/statistics` led there. They now open Monitoring & Learning, where the stats and the time travel are.
- `pcworkman://` links can open the new pages too: Process Center, Cleanup, Health report and Your profile.
- Cleanup's left column was empty during a scan, which takes over 10 seconds with a big TEMP folder. It now says it is scanning.
- The Startup Manager's "Scanning startup entries…" is in the interface language.
- **The older pages' headers follow the interface language** (`ui/components/page_titles.py`, new).
  - The test build showed them in English under a Polish interface, next to the new pages' Polish banners.
  - Page titles in Polish, following the sidebar's names:
    - Menedżer Autostartu, Menedżer Usług, Kontrola wentylatorów;
    - Wentylatory: sprzęt i użycie, Statystyki wentylatorów;
    - Konfiguracja i sterowniki, Monitoring, Optymalizacja, Statystyki.
  - OVERCLOCK and Upgrade Readiness keep their feature names in both languages, as in the sidebar and hck_GPT. Their subtitles are translated.
  - Other header pieces now in both languages:
    - Startup Manager: the counters and tabs (Razem, Duży wpływ, Do sprawdzenia, Do wyłączenia, Wyłączone);
    - Services Manager: the admin warning, the counter and the search hint;
    - Setup & Drivers: the scan state and the buttons.
  - Checked at 100% and 125% scaling and in the built app.

### No worker thread calls Tk
**`ui/bg.py` (new), `ui/pages/optimization_services.py`, `hck_gpt/panel.py`, `ui/components/yourpc_page.py`, `ui/pages/first_setup_drivers.py`, `ui/pages/services_manager.py`, `ui/pages/upgrade_readiness.py`, `ui/pages/monitoring_alerts.py`, `ui/components/fan_dashboard.py`, `ui/components/gaming_toast.py`, `ui/windows/main_window_expanded.py`, `ui/windows/main_window.py`, `tests/test_no_tk_from_threads.py` (new)**
- Worker threads called Tk directly (`widget.after(0, ...)`, `widget.config(...)`) in about 40 places. These calls have two failure modes:
  - When the Tk main loop is not the one pumping, they raise "main thread is not in main loop". The error was swallowed, and the page never filled in (the Startup Manager's "Scanning…").
  - A worker holding the last reference to a widget frees the Tk interpreter from the wrong thread, and the process aborts with Tcl_AsyncDelete.
- `ui/bg.py` is the one way to work off the UI thread now:
  - `run(widget, work, done)`: `work()` runs on a thread with plain values; `done(result)` runs on the UI thread, and only if the widget still exists.
  - `later()`: "show DONE, then put the button back" without a sleeping thread.
  - `Mailbox` + `watch()`: a daemon's callbacks only fill a mailbox, and the page takes the items in order. The mailbox closes on `<Destroy>`, because Tkinter drops a destroyed widget's pending `after()` calls.
  - `post()`: code outside the window, such as a chat answer or the tray menu, queues work for the main window's pump.
- Converted:
  - **Optimization Center:** quick actions, TURBO services stop and restore, the upgrade advisor, RAM Flush and its live status, the Turbo Power Plan and its live status.
  - **hck_GPT panel:** the proactive monitor's push, banner and HOT callbacks, and the startup quip. The answer worker gets the chat handler and plain values, not the panel.
  - **My PC:** the component scan and the power plan name.
  - **Setup & Drivers:** the driver scan.
  - **Services:** applying the queue.
  - **Upgrade Readiness:** the platform.
  - **Monitoring:** rebuilding the baselines.
  - **Fan Dashboard:** the AI profile from chat.
  - **Gaming toasts and the startup/app-install watcher toasts.**
- **The system tray menu** (pystray runs it on its own thread) restored, showed and closed the window straight from that thread. It now queues the work, in both the Expanded and the minimal window.
- A test reads the sources: from every `threading.Thread(target=...)` and every `bg.run(...)` work function, it follows the functions of the same module and fails on a Tk call. The only exception is the diagnostic console, which owns its own Tk interpreter on its own thread, like the splash. Further tests cover `ui/bg.py` on a real Tk root.

## [1.9.0] - 2026-11-17

A large update of hck_GPT, started after the third long test (17 November). Marcin wrote down 63 questions a user would ask, with three conversations of several turns. Asked in 193 phrasings, 51 ended in "I did not understand" and about 40 got an answer to a different question; none ends there now. Plan and status: `local_notes/HCK_GPT_1.9.0_PLAN_2026-11-17.md`.

### hck_GPT draws conclusions from what PC Workman recorded
**`core/pc_insight.py` (new), `hck_gpt/responses/r_insight.py` (new), `hck_gpt/intents/insight_rules.py` (new), `hck_gpt/responses/builder.py`**
- A shared layer turns the recorded data into conclusions:
  - the real CPU clock from Windows performance counters (psutil reports only the base clock: "2500 MHz" on a CPU running at 4200);
  - whether heat or a power limit is holding the CPU back;
  - each drive's type (NVMe, SATA SSD, HDD) and health;
  - hardware errors, disk errors, blue screens and sudden restarts from the Windows event log;
  - how CPU and GPU behave in the minutes recorded as gaming;
  - the highest VRAM use;
  - this PC's normal load and whether the last days differ;
  - programs using more than their own normal;
  - the age of the main parts;
  - which part is the weakest, and why.
- New answers on top of it, each saying what was checked, the verdict and what to do:
  - **state of the PC:** is anything to fix or worry about; is it stable; is it worse than usual; is anything running in the background for no reason; what slows it down; why it feels slower lately; what changed;
  - **parts:** the bottleneck and what to upgrade first; is the CPU or GPU still good; is there enough RAM or VRAM; does the CPU reach its boost or hit a limit; is the GPU fully used in games; is the drive fast and does it slow game loading; SSD health; temperatures in games; which processors the motherboard takes, with a note when the BIOS is too old for them; how old the PC is; whether to buy a new one;
  - **trust:** whether hck_GPT reads files, what it stores, what it sends, what it remembers; whether it can recognise a virus; whether Windows Defender is enough; whether every svchost.exe is genuine (it checks each running one); whether a signature means safe; programs posing as Windows processes (it checks them);
  - **personality:** is the PC tired, what hck_GPT does while you are away, does it watch the PC, does it like its job, can it predict when the PC will slow down (from the RAM peaks, the busiest hours, free space and the trend).

### Conversations of several turns
**`hck_gpt/responses/r_followup.py` (new), `hck_gpt/memory/session_memory.py`, `hck_gpt/responses/r_system.py`, `hck_gpt/responses/r_gaming.py`**
- hck_GPT remembers what "it" is: the program it just named, the game, the advice it gave.
  - "A czy mogę to wyłączyć?" answers about that program, starting with a plain yes or no.
  - "Jak to zrobić?" gives the steps for that action: closing a program, startup, XMP, virtual memory, services, adding RAM, drivers.
  - "Czy to pomoże?" measures that program and says how much RAM closing it frees (on the test PC: Claude, 1.4 GB, RAM from 74% to about 55%).
- "Chcę pograć w CS2, ale mam lagi" gets the game's requirements together with what is off on this PC. "Czy komputer sobie z tym radzi?" means that game, "Co zamknąć przed grą?" lists programs to close, "A co jeśli dalej będzie zacinać?" gives the next steps.
- Game requirements: 8 GB of RAM reads as 7.85 GB in Windows and was judged "below the 8 GB minimum"; a game that is already installed is no longer failed for disk space.

### Observation note: record, change, compare
**`core/observation.py` (new), `hck_gpt/panel.py`, `hck_gpt/chat_handler.py`**
- "Zacznij nagrywanie", or the ⏺ Nagraj button in the chat, records every second:
  - CPU, RAM, GPU and GPU temperature;
  - the real CPU clock;
  - the busiest process.
- "Zakończ nagrywanie" shows the averages, peaks and the level the load stayed under 95% of the time. It compares them with the previous recording and gives a verdict: better, no clear difference or worse. A text note goes to the Desktop.
- Meant for "is it better now?": record a game before a change and again after it. "Jak sprawdzić, że jest poprawa?" explains this and offers a button that starts the recording.

### Data from the third long test
**`hck_stats_engine/load_periods.py`, `core/scheduler.py`, `core/game_detect.py`, `hck_gpt/memory/proactive_monitor.py`, `hck_gpt/memory/user_knowledge.py`**
- 1.5 hours of a game at GPU 64-75% left no busy stretch in the history: the line was 80%. It is now 60%, the same line at which learning counts gaming. While a game runs, the stretch stays open whatever the load. Stretches are rebuilt once from the minute history: 83 minutes of a game on 17 November and 105 minutes of BeamNG on 16 November on the test PC.
- Unreal Engine games (`*-Win64-Shipping.exe`) count as games wherever they are installed. A game was reported as "jumped onto the top load list, not normally here".
- Windows' own busy processes (Defender, the search indexer, updates) are explained instead of "accidental or planned?". "DeepMonitor: CPU GPU 45 C" reads "GPU 45°C".
- The test suite wrote into the same knowledge base as the user's PC Workman, so a test that says "I have a laptop" left the test PC marked as a laptop. Tests and isolated runs now get their own knowledge base.
- "Wolno działa komputer" got "CPU is not throttling"; it now gets what slows the PC down, now and all the time.

### The fourth long test: 73 questions from a real afternoon
**`hck_gpt/responses/r_meta.py` (new), `core/data_export.py` (new), `hck_gpt/intents/insight_rules.py`, `hck_gpt/responses/r_system.py`, `hck_gpt/memory/proactive_monitor.py`, `hck_gpt/insights.py`, `core/pc_insight.py`**
- 34 of 73 questions ended in "I did not understand"; replayed against this version, none does. New answers:
  - how much longer it learns, per workload in minutes;
  - LibreHardwareMonitor: what it is, where to get it, and that its web server must run for PC Workman to read the sensors;
  - whether PC Workman is still developed, and where a new version is;
  - what is new and what deserves attention;
  - "halo", "jesteś?", "rozumiesz?", "nie rozpoznajesz pytań", a compliment;
  - "mam błąd": asks for the message and checks the Windows log of the last 7 days;
  - "czy jesteś Claude" and similar;
  - "czy mam wirusy?" runs the security scan.
- Moving to a new Windows: "zrób export" packs the history, learning, settings, observation recordings and hck_GPT's knowledge into one ZIP on the Desktop, with import steps inside. The databases are copied with SQLite's online backup, so the copy is consistent while the app runs.
- Deleting data: what "reset" clears, which files hold the history and the learning, and a reminder to export first.
- "Co to teams" asked for an .exe name when Teams was not running; the process library answers from its description. After "co to searchindexer?" the next "czy mogę go wyłączyć?" now knows what "go" is.
- "Programs using more than usual" compared a day with six calendar days, so every program looked 20 times above its normal. It now compares averages over the time actually recorded and needs 12 hours of history; Windows' compressed memory is not a program.
- Proactive messages: "CPU has settled" at most once in 30 minutes (it came three times in eight minutes); each fixed tip at most once a day; "this program holds X MB" for the same program at most once in 3 hours unless it grew by half. The game session summary uses the whole PC's CPU and GPU from the history, not the game process alone ("CPU 4%" over 56 minutes of play). Launchers such as Steam are no longer "Gaming detected".

### Version, Settings, HCK_Labs and the Guide
**`utils/app_version.py`, `locales/*.json`, `ui/pages/settings_page.py`, `ui/windows/main_window_expanded.py`, `ui/pages/labs_guide_pages.py` (new)**
- Version 1.9.0. Settings showed "Version 1.7.4" from a translation file; it now reads the one version source.
- Settings opened as a 980×515 card with the dashboard visible around it. It now covers the whole content area like every other page.
- HCK_Labs, rebuilt: a gradient header with the author, live numbers from this PC (learning, recorded hours, gaming, known processes), the projects, a version timeline and the principles behind the program.
- The Guide, rebuilt: what is new in this version as cards, a three-step start, questions that ask hck_GPT on click, the map of the program and the guides on pcworkman.dev. Its "What's new" listed the previous version.
- Both pages and their headers follow the interface language.
- "Check for updates" in HCK_Labs showed v1.7.1 from April. It now shows the installed version and opens PC Workman in the Microsoft Store app, with GitHub Releases next to it. The app still never connects to check by itself.

### The fifth long test: the 1.9.0 run
**`ui/components/yourpc_page.py`, `hck_gpt/responses/r_features.py` (new), `hck_gpt/responses/r_gaming.py`, `hck_gpt/intents/insight_rules.py`, `hck_gpt/chat_handler.py`, `hck_gpt/panel.py`, `hck_gpt/memory/proactive_monitor.py`, `ui/pages/monitoring_alerts.py`**
- My PC could get stuck on the In-Game Overlay view: "← My PC" and the tabs did nothing (38 errors in the log). DeepMonitor builds a second My PC page; after it closed, the kept My PC page pointed at the destroyed one's tabs. Each My PC page now owns its tabs and content, and a second click on the chat link no longer closes My PC.
- Game requirements:
  - free space is read from the drive with the most room, not from C: alone (the answer said too little space with over 1 TB free elsewhere); disk space no longer affects the verdict;
  - GTA V had 16 GB RAM as recommended; Rockstar recommends 8 GB, and the minimum is 4 GB;
  - the settings estimate uses the graphics card's power, so an RTX 3050 gets "high" in GTA V instead of "low to medium";
  - the answer is drawn as a card.
- hck_GPT knows the program: "czym jest DeepMonitor", "deepmonitor?", "fan dashboard", "monitoring learning", "czym jest nagranie", TURBO, Process Guard, App Hibernation, RAM Flush, Upgrade Readiness, PC map, stability tests and others each get what the feature does, where it is and a link that opens it. "Co mogę robić w programie?" gets a tour of the program.
- New answers:
  - "mam wolny internet": the PC's own traffic measured for a second, downloaders that are running (Steam, OneDrive, torrent clients and others), then the steps from speed test to router to provider;
  - overclocking the graphics card (the answer talked about the CPU's locked multiplier);
  - "opowiedz żart";
  - what Recent Events counts.
- Fixed understandings:
  - "czy komputer ma wirusa" got the hardware upgrade options; it runs the security scan;
  - "co mogę robić w programie" got the background programs;
  - "nagrywaj", "kto ty jesteś", "czy dobrze działasz?", "co odinstalować?", "co usunąć?", "czy mam jakieś błędy?" and "wyłącz teams" outside the guide.
- LibreHardwareMonitor: the answer says it is optional and what works without it (everything except the CPU temperature, voltages and fan speeds). Any answer that mentions it gets a "Zobacz sam" button that opens the official GitHub releases page.
- BeamNG runs as two processes, so one session gave two "is the game smooth?" questions and two summaries. Processes of one game now make one session.
- Recent Events no longer lists "PC Workman shutdown": it was 6 of 13 entries.

### Tests
- 460 to 573. New: the 63-question library and the questions of the fourth and fifth long tests as route tables, two My PC pages that must not share tabs, the game check, the update dialog, the export ZIP staying in the test folder.

## [1.8.8] - 2026-11-16

A stability release. It came out of a full audit on Windows 11 (build 26200), of the logs the app had been writing on real machines since July, and of two long tests on one PC (16 and 17 November) in which the app ran for hours and hck_GPT was asked what a user would ask. Most changes fix something that worked in a test and failed in use.

In numbers:
- hck_GPT questions ending in "I did not understand": 28 of 71 in the first long test, 0 of 122 in a sweep of everyday questions after the fixes.
- Learning on the test PC: 14% before the fixes, 67% on the same data after them.
- Tests: 552, all passing.

### Activity Memory: the history of CPU, RAM and GPU
**`ui/pages/activity_memory.py` (new), `hck_stats_engine/history.py` (new), `ui/windows/main_window_expanded.py`, `hck_gpt/memory/proactive_monitor.py`**
- Click the CPU, RAM or GPU card on the Dashboard (it lights up bordeaux under the mouse) to open its full history: 1 hour, 24 hours, 7, 30 and 90 days, a year, or everything recorded.
- The time axis is real time. Hours when PC Workman was off stay empty instead of being joined into one line. Hovering a point shows when it was, the average, the lowest and highest reading and, where a sensor measured it, the temperature.
- Moving in time: drag the chart, use the arrows, or click the strip with the whole history under the chart to jump months back. Scroll zooms around the cursor, a double-click opens that moment closer. The chosen range is remembered.
- Under the chart: average, lowest, peak and when it happened, the level the load stayed under 95% of the time, time above 80% (85% for RAM and GPU), how much of the period was recorded, temperature, and the change against the period before.
- Heaviest processes of the period, counted over all their instances, and the recorded load spikes. A click on a spike opens the hour around it. GPU load is not recorded per process, and the page says so.
- hck_GPT notices when a component has been working clearly harder for 1 to 3 days than in the 2 weeks before (at least 15 points higher, or 10 points and 1.5 times as much), says it with both numbers once a day at most, and links to that history.

### hck_GPT after a six-hour test
**`hck_gpt/panel.py`, `hck_gpt/engine/hybrid_engine.py`, `hck_gpt/chat_handler.py`, `hck_gpt/responses/`, `hck_gpt/memory/proactive_monitor.py`, `hck_stats_engine/query_api.py`**
- hck_GPT keeps a local record of every conversation (`data/logs/hck_gpt_chat.jsonl`) and of every message it considered sending on its own, sent or held back and why (`hck_gpt_proactive.jsonl`). Nothing is deleted: at 20 MB a file is kept under its date and a new one starts. Nothing in them leaves the PC.
- Sending a message no longer freezes the window. The answer is worked out in the background with an animated "thinking" line. A security question had held the window for 18 s.
- Every question hck_GPT did not recognise cost 4 s: it looked for a local Ollama on "localhost", and Windows retries a closed port there twice. It now checks 127.0.0.1 in the background.
- Links in the first line of a message were never clickable, for example "[-> Services Manager]" in the optimization guide.
- Summaries counted an hour of history and a minute of history as equal, so 40 minutes of gaming outweighed four hours (the upgrade advisor reported CPU 57% for a day that averaged 33%). Recorded time was counted 60 times too long. Temperature summaries still included the old estimated CPU temperature.
- The answers about the program and about privacy said that nothing leaves the PC. They now say what anonymous telemetry sends, whether it is on, and link to the switch in Settings.
- "CPU back to normal - now 75%" came several times an hour while gaming. The note now comes once the CPU is below 50%, and it counts against the message limit.
- The overclock answer read the base clock as boost ("boost 2500 MHz" on an i5-12400F, which boosts to 4400) and now also says whether the CPU can be overclocked at all.
- A short reaction such as "nice" no longer repeats the previous answer.
- Messages hck_GPT sends on its own use the interface language. They switched to whatever language one chat message was detected as.

### hck_GPT understands everyday questions
**`hck_gpt/intents/semantic_rules.py`, `hck_gpt/responses/r_everyday.py` (new), `hck_gpt/responses/flows.py`, `hck_gpt/engine/flow_engine.py`, `hck_gpt/panel.py`, `ui/pages/startup_manager.py`, `ui/windows/main_window_expanded.py`**
- In the six-hour test 28 of 71 questions ended in "I did not understand". Short everyday questions without a hardware word were rejected outright. New answers, each with variants (no Polish letters, typos, short forms, English) covered by tests:
  - where the In-Game Overlay is;
  - whether everything is fine (a verdict from live values, this PC's normal levels, today's high-load periods and how much has been learned);
  - why it lags;
  - what uses the most;
  - what to upgrade;
  - whether this is the latest version (from the release date, without going online);
  - the website;
  - what can be deleted or uninstalled;
  - where to update drivers;
  - whether it has learned;
  - whether it is an AI;
  - Ollama;
  - plain reactions such as "nice".
  Of the 28 questions, 22 are now answered; the rest were attempts at a hidden scene.
- "Who makes PC Workman" tells who does: Marcin, one person, building it at night after work, also making Scaling Laws.
- A complaint about RAM ("mam duże obciążenie RAMu") reached the part-fit check and offered the CPU-motherboard guide.
- The optimization guide shows each step as a card with a coloured verdict, on real data:
  - the startup entries worth disabling, by name;
  - the unneeded services that are running;
  - the three processes holding the most memory.
  A question asked during a step gets an answer about that step, and the guide says it is waiting. "Przerwij" ends it and says whether anything was changed.
- Quick replies above SEND: the guide's choices during a guide (ZACZYNAJMY, DALEJ, Zobacz Autostart, TAK / POMIŃ, PRZERWIJ), two starters otherwise.
- The chat stays available on Services, Startup, Optimization, Monitoring, Setup & Drivers, Upgrade Readiness, Overclock, Fans and Activity Memory. A link opens the page and folds the chat down to its bar.
- Startup Manager judged every entry it had no file record of as "low impact, keep" (24 of 24 on the test PC, Teams and Driver Booster among them). Entries are now also judged by name; anti-cheat and Windows Security stay "keep".

### hck_GPT chat: layout and how answers arrive
**`hck_gpt/panel.py`, `hck_gpt/chat_handler.py`, `ui/windows/main_window_expanded.py`**
- The message box and SEND disappeared in the second long test, once when a TIP appeared and once after a link from the chat opened another page. The chat log was laid out first and took the panel's height, so the input row was the part cut off. The input row and the quick replies now get their place first and the log takes what is left. A test builds the panel with a TIP and a HOT alert shown and checks that the input row is inside it.
- TIP and HOT hang directly under the hck_GPT banner instead of above the input, so a new tip no longer pushes anything near where you type.
- Quick replies sit on the right, above SEND, slightly smaller.
- A "⚡ Optymalizacja" button, first in the chat's top bar, starts the optimization guide at any time.
- Long answers come in parts. The first part shows at once; the chat then shows its thinking line for 2 seconds (the SEND button spins too) and adds the next part. The chat takes no new question until the last part is in.
- Lines meant to be noticed have a lighter background: "Szybkie kroki do poprawy" in the RAM answer and the offer of the optimization guide. The tint of a conversation turn no longer covers these backgrounds or the guide's step cards.
- Answers about lag, high RAM, speeding up the PC and the Optimization page end with the guide offer: one empty line, the highlighted offer below the article link, and a ZACZNIJ PRZEWODNIK button among the quick replies.
- The Virtual Memory link opens the Windows window and keeps the chat open. About 2 seconds later hck_GPT says the window is opening and offers directions. A "Gdzie to znajdę?" button appears; the directions (Performance → Settings → Advanced → Virtual memory → Change) come only if the next message asks for them.
- A link to the Activity Memory history was added for answers that read the history.

### hck_GPT: the optimization guide, 6 steps
**`hck_gpt/responses/flows.py`, `hck_gpt/engine/flow_engine.py`, `core/component_check.py` (new), `core/pagefile.py` (new)**
- After the result (step 5) the guide asks whether to check the key components and their drivers, with TAK, SPRAWDŹ and POMIŃ.
- The component check thinks for 2 seconds, then shows CPU, GPU and RAM, each in its own block:
  - use right now and the average of the last 7 days;
  - how hard the part usually works: often near its limit, healthy, calm with peaks in games, or plenty of spare power;
  - temperature on its own line. The GPU is judged against its highest reading this week. The CPU temperature is shown only from a real sensor: without one hck_GPT says so instead of guessing;
  - for RAM, whether virtual memory is on, how big it is, on which drives and who sets its size, with a link to its settings on the line below.
- Step 6 offers the driver check, judged calmly:
  - the graphics driver by its date, with NVIDIA's own version number (610.88 rather than 32.0.16.1088);
  - the platform (chipset, Management Engine) by its newest real date. Intel ships chipset files dated 1968 on purpose; those dates are skipped;
  - RAM through the motherboard BIOS, since memory has no driver of its own.
  A link to Setup & Drivers closes the report.
- POMIŃ on either question ends the guide with a short closing line. A step with nothing to say is passed over.
- "Co to za aplikacje" during the startup step answered about the last TIP. Short questions that point at what a step just listed ("co to za", "które", "jakie") now get that step's answer.

### hck_GPT understands more, answers from what was recorded
**`hck_gpt/intents/semantic_rules.py`, `hck_gpt/responses/r_everyday2.py` (new), `hck_gpt/responses/builder.py`, `hck_gpt/memory/session_memory.py`, `hck_gpt/responses/r_conversation.py`, `core/game_detect.py`, `core/machine_type.py`**
- After the second long test, hck_GPT was asked 122 questions a user would ask about a slow, loud, hot or misbehaving PC, in Polish and English, with typos and without Polish letters. 30 ended in "I did not understand", and a dozen more got the wrong answer. None ends there now.
- New answers that read the recorded history, the same data as Activity Memory:
  - when the PC was busiest and what ran then;
  - whether it slept;
  - what was played and for how long;
  - how long it has been on today;
  - today against yesterday.
  "Od wczoraj wolniej działa" compares the two days when there are not yet two full daily summaries.
- New answers for everyday problems:
  - virtual memory: what it is, what is set now, how to change it;
  - which apps can be closed right now, largest first, Windows processes left out;
  - which services to turn off;
  - sudden restarts and blue screens, counted from the Windows event log over 30 days, with dates and the likely cause;
  - the refresh rate of each screen and why a 144 Hz monitor shows 60 Hz;
  - RAM speed and XMP. On the test PC RAM runs at 2133 MHz, the DDR4 base speed, so XMP is most likely off;
  - crackling sound, cleaning dust, backup, whether to turn off Windows Update, changing the language, Wi-Fi drops;
  - how much CPU and RAM PC Workman itself uses;
  - "nic nie działa" and "pomocy" ask what exactly happens.
- When a diagnosis of lag in a game has its full picture, hck_GPT now checks what it can on that PC (RAM size and what holds it, RAM speed, graphics driver age, a busy background process). It used to only ask the user to reproduce the problem.
- A clear question during an open diagnosis is answered instead of being added to it as a detail ("dysk ciągle na 100", "jak przyspieszyć gry", "czy uruchomię cyberpunka"). A short detail right after hck_GPT asked for one still joins the diagnosis. Remembered details read as words ("w grze, gra: CS2, rodzaj: spadki FPS"), not "miejsce=gaming, gra=gta 5" or "częstotliwość: consistent".
- "my pc is slow", "is my pc fine" and "what did you learn about my pc" got "Noted - this is a desktop". Only an actual statement ("mam PC", "I have a laptop") is remembered, and a message with more in it is answered as well.
- Games in the history are recognised from the installed Steam, Epic, GOG and Xbox libraries, so "w co najwięcej grałem?" finds BeamNG.drive by its file name. Bundled Java, installers and crash tools in game folders are not counted as games.
- The RAM answer counted only the first 64 processes and blamed explorer.exe at 2.2% while Opera held 1.2 GB. It now counts every process grouped by program, explains MemCompression, names the browser only when it really is the largest, compares with the 7-day average from the history (the same figure the guide shows), and after a pause lists quick steps with the virtual memory as it is set now.
- The lag answer measured CPU use without a measuring window and on the first 64 processes, so it blamed "System". It now measures every process for half a second as a share of the whole CPU.
- Fixed:
  - the power plan showed as "Zr˘wnowaľony": console tools write in the OEM code page, now read as such, also on the My PC tile;
  - "gta 6" got GTA V requirements;
  - the battery answer on a desktop listed "System Idle Process 877.9%";
  - "co zjada procesor" showed the memory list;
  - "czy mogę zamknąć operę" read one of Opera's processes (12 MB) instead of all of them, and it now works without ".exe";
  - "co to msmpeng" asked for the full file name;
  - the drivers answer led with "NVIDIA Virtual Audio Device · 33m old";
  - the speed-up plan said a browser frees "~3-4 GB" without looking;
  - startup entries showed names like "MicrosoftEdgeAutoLaunch_6BE24301AD05CA3C4A62FD6F29F2087D";
  - "co to jest throttling" did not say what throttling is;
  - "nakładka nie działa w grze" said only where the overlay is; it now lists what to check.

### Learning fixed
**`core/thermal_baseline.py`**
- Learning switched from 5-minute snapshots to minute rows on 16 November, but it continued from the time of the last snapshot. Every minute recorded before the switch was learned only as every fifth. On the test PC: 368 recorded minutes, 133 learned samples, gaming 14 instead of 68.
- On first start, if the minute history reaches back to where learning began, learning is rebuilt once from the minute rows, each minute counted once. Older installs whose minutes were already pruned keep what they learned.
- The learning percentage averaged every workload seen at least once, so two workloads seen once each held it at 14%. A workload now counts once it has 15 minutes. On the same data: 14% before, 67% after.
- What the second long test confirmed works: GPU temperature learned per workload (idle 44°C, gaming 67°C), the RAM norm told once a day, proactive messages within their limit (8 in 70 minutes).

### What PC Workman learns and records
**`hck_stats_engine/load_periods.py` (new), `core/game_detect.py` (new), `core/machine_type.py` (new), `core/scheduler.py`, `core/thermal_baseline.py`, `ui/pages/activity_memory.py`, `ui/components/gaming_toast.py`, `hck_gpt/`**
- High-load periods. The spike check compares one minute with the five before it, so a game that ramps up over a few minutes never counted: 40 minutes of GPU at 95-99% left no record. A period now starts after 3 minutes above 70% (CPU) or 80% (GPU) and ends after 3 minutes clearly below. It keeps its peak, average, measured temperature and the game or process behind it. Activity Memory shows periods as bands on the chart and in a list; a click zooms to the period.
- Games are recognised by where they are installed (Steam, Epic, GOG, Xbox, Riot, Ubisoft, EA, Battle.net), not only by a list. BeamNG.drive was on no list. hck_GPT no longer asks whether a game using the CPU is "expected", and these games now get the start note and the session recap.
- The learning engine learns from every recorded minute instead of one sample every 5 minutes, and ignores the old estimated CPU temperature. The "% learned" figure counts progress in the workloads this PC actually runs (3 hours each to "trained"), not in all five.
- RAM has a normal level per PC. On an 8 GB machine 85-92% is everyday, and the test got "RAM at 90%" nine times in two hours. With at least 3 hours recorded, hck_GPT alerts only above this PC's normal level and explains the level once a day.
- Sleep is recorded. Gaps in the history now say "the PC was asleep (3 h 13 min)" instead of nothing.
- Laptop or desktop is detected from Windows (system battery) and from what the user says ("mam PC", "I have a laptop"). The second always wins. Storage advice no longer describes laptops to desktop owners.

### Readable text
**`utils/fonts.py`, `utils/ui_scale.py`, 40 files under `ui/` and `hck_gpt/`**
- The app ships the Inter font and asked Windows for "Inter", but the file registers itself as "Inter Variable Text". Windows found no "Inter" and drew that text in Arial. Headers asked for Segoe UI by name, so every page mixed three typefaces. All text now uses Inter, from one place.
- Text below 7 pt is gone (136 places were 4 to 6 pt, among them the "All good · Standard" line under the CPU, RAM and GPU cards). All fonts are drawn 10% larger, and the default window is 12% larger on a 1080p screen (1300×645) so layouts keep their proportions. On smaller screens the window takes what fits and the text keeps its size.
- Grey text that was hard to read on the dark background is lighter: 99 places had a contrast below 4.5:1.
- My PC: the captions on the coloured tiles are readable on every colour. "N startup entries detected" showed the number minus 2. "Scanning..." stayed forever when no unnecessary service was running. The CPU panel showed "Intel64 Family 6 Model 151" instead of the model name.
- The maximize button showed an empty box: Inter has no "⤢" and Windows did not always find it elsewhere. Symbol-only buttons now use a symbol font.

### Services Manager no longer jumps
**`ui/pages/services_manager.py`, `ui/components/fit.py`**
- With Windows display scaling at 125%, the service list moved without end. The two columns split the width by what their text asked for, the text wrapped to the width it got, and every wrap moved the split again. The columns are now an even split, and text that adapts to its width ignores changes under 6 px. A test opens the page at 125% scaling and fails if anything still moves.

### Monitoring: what PC Workman has learned
**`ui/pages/monitoring_alerts.py`, `core/thermal_baseline.py`**
- "100% learned" could show while the "heavy" workload had a few minutes of data: the number counted all samples together, so a PC that is idle a lot looked fully learned. It is now the average of the five workloads.
- A card on the right shows that number, what stage the learning is at, and in the first 6 hours explains how PC Workman learns and why it needs the time. Later it lists which workloads it knows and which it is still learning.
- Links from there to the CPU, RAM and GPU history.

### History recording
**`hck_stats_engine/aggregator.py`, `core/scheduler.py`**
- Hours and days were rolled up only when the app was running at the moment the hour or day ended. Close it at 22:50 and that hour, and often the whole day, never reached the long-term history. One real database was missing 5 hours and 11 days. Every start now rolls up whatever is complete and missing, and so does every boundary crossed while running.
- Without a temperature sensor the history stored `35 + CPU load / 2` as the CPU temperature. Only measured temperatures are stored now, and old rows with that formula are not shown.
- A day's uptime is the time actually recorded, not the number of hours that had any data.

### Startup without a console window
**`utils/diag_console.py` (new), `ui/startup_error.py` (new), `ui/diag_window.py` (new), `startup.py`, `PCWorkman.spec`**
- The exe is now a windowed program. It used to be a console program that hid its console once the window was up, and on Windows 11 that never worked: Windows Terminal ignores the hide call. `errors.log` on one machine held 43 `console_hide_failed` entries.
- Everything the startup prints goes to `data/logs/startup.log`. The previous run is kept as `startup.prev.log`.
- If startup fails, a window says what happened and offers "Copy details" and "Open log". The copied text carries the version, the Windows build, the error and the end of the startup log. A part that fails while the app still starts gets the same window in amber, once.
- Settings > General > "Show diagnostic console at startup" opens a log window in the app's own style that fills while the program loads and closes 3 seconds after the main window is ready. "Keep open" stops the countdown.
- `--console` still opens a real console, for the case where no window can open at all.
- `PCW_SELFTEST=fail` or `PCW_SELFTEST=problem` shows either window on a healthy machine, so testers can check them.
- The logo now appears before the slow imports and stays until loading is done, instead of a fixed 2.5 seconds followed by a blank wait.

### Optimization engines
**`core/turbo_manager.py`, `core/auto_optimizer.py`, `core/hibernation_manager.py`, `ui/pages/optimization_services.py`**
- **Process Guard froze system services.** It suspended any idle process not on a short whitelist. `turbo_engine.log` shows MSI services, GameInput and the console host frozen within one second. It now suspends only 12 known applications (browsers, Discord, Slack, Teams, Spotify, cloud sync clients, game launchers) and never the application in front.
- **Nothing stays frozen after a crash.** Process Guard and App Hibernation write what they suspended to disk. A normal exit wakes everything; after a crash or a Task Manager kill, the next start does. A PID that Windows gave to another program in the meantime is left alone.
- **Auto RAM Flush ran in a loop.** Above 75% RAM it trimmed every process about once a minute, with no end. Measured on an 8 GB machine: +428 MB right after a flush, 267 MB less than before it 20 seconds later. It now waits 5 minutes after a flush, and up to 30 when the effect does not last.
- **Turbo Power Plan could get stuck on "Turbo PC".** After a crash it could record "Turbo PC" as the plan to return to. The previous plan is now kept on disk and restored on the next start.
- App Hibernation restores the priority a program had before, not always "normal", and reports a failure instead of marking the app as asleep.
- The Dashboard TURBO button reported "1 fired" with nothing armed. It now counts only what was armed and possible. The power plan switch moved off the UI thread.
- RAM Flush on TURBO did not work after a restart until TURBO was switched off and on again.

### The app remembers what you set
**`utils/prefs_io.py`**
- Every settings file was written by emptying it first and writing it second. A crash, a shutdown or a second writer in that moment left a broken file, and the next start read it as empty. All 29 writes now go through one writer that writes a temporary file and swaps it in, locks per file, and keeps the last good version as `.bak`. A damaged file is restored from the backup on the next read.
- Newly remembered: window size, position and maximized state (ignored if that monitor is gone), the chart range, the Process Guard threshold (now the same value as in Settings) and the App Hibernation threshold.
- In the exe, several paths pointed inside `_internal`. The language chosen in Settings was not applied after a restart, and "Export" and "Reset data" did nothing. Started by the Windows autostart, the Fan Dashboard wrote to `C:\Windows\System32` and failed. All of them now use the app folder.
- The build no longer packs the developer's own settings files (`network.json` with an install id, preferences, fan curves).

### Fans: measured values only
**`core/fan_sensors.py` (new), `ui/components/empty_state.py` (new), `ui/pages/fan_control/`, `ui/components/fan_dashboard.py`**
- "Fan Control > Hardware & Usage" showed random numbers under "Real-time fan monitoring" and cooler models that were typed into the source. Fan speed now comes from LibreHardwareMonitor or OpenHardwareMonitor. Without one, the page says so and shows what is measured.
- The usage chart draws measured history only, on a real time axis.
- Fan Dashboard cards show the plan percentage marked "plan", with the measured RPM next to it when a sensor reports it. The page says that curves are a plan and that the BIOS or the vendor tool still controls the fans; "Apply" says the same.
- My PC printed "CPU 560 RPM" and "BODYFAN 990 RPM" on every machine. Removed.
- A fan sensor named "System Fan" was stored as the motherboard temperature.

### Dashboard and layout
**`ui/components/fit.py` (new), `ui/windows/main_window_expanded.py`, pages**
- Text cut off mid-letter ("FLUSH RA", "OPE", "Disab", "l5.0%") had one cause: a long label packed before a button took its space. Controls are now packed first and text wraps. A scan of 12 pages went from 146 findings to none clipped in width.
- That also brings back controls that were not on screen at all: the third Proactivity mode, the "Run as administrator" switch, the 1D / 1W / 1M chart ranges and the Services Manager MODES bar.
- Hardware card temperatures were a formula on the load (`30 + load x 0.6`), shown even for RAM. They now show a measurement, an estimate marked with "~", or "--". RAM shows how much is in use.
- The CPU card shows the product name ("Intel Core i5-12400F") instead of "Intel64 Family 6 Model 151".
- The GPU name no longer runs `nvidia-smi` on the UI thread. `freeze_dump.txt` holds 12 stalls of 15 to 18 seconds at that call.

### Services Manager
- "Disable" ran `sc stop`, so the service came back after a restart. The buttons are now "Stop" and "Start", and the confirmation says a service may start again after a restart.
- A change Windows refused went only to the log. It is now shown.
- The service and startup scans ran on the UI thread, inside a thread that only scheduled them. Both now run in the background.

### Language
- 75 Polish strings typed into the interface showed with the English interface selected (Startup Manager, Services Manager, Drivers, Optimization). They are in `locales/` now; both files have the same 602 keys.
- The welcome toast took its language from Windows instead of the app, had no Polish letters and showed version 1.7.6.
- Quick setup questions in Services Manager were always Polish.

### Telemetry
**`core/telemetry.py`, `cloudflare/telemetry-worker.js`**
- Reports kept arriving after 1.8.0; the Cloudflare KV list sorts by key, and keys started with the install id, so the first page looked like June.
- `session_min` was always 0, because the only report went out 2 seconds after launch. A session now sends "start", an hourly "heartbeat" and an "end" with the real length. The end report waits at most 3 seconds.
- The Worker keeps the new `kind` and `session_id` fields and starts keys with the date, so a day can be found with "Search keys by prefix".

### Fixes
- "lambda missing argument 'e'" (11 entries in `errors.log`) came back on four pages. Every event handler in the interface now accepts a missing event.
- The GPU driver date showed as `/Date(1784678400000)/`, and hck_GPT could not tell how old any driver was.
- A Process Guard receipt never saved its result (a property was called as a function).
- The Settings idle threshold was written to an attribute nothing read.

### Removed
- 21 files that nothing imported (330 KB): old copies of the main window, My PC page and charts, and helpers nobody called. One of the copies no longer parsed.

### Tests
- 331 to 460, all green. The suite runs in its own data folder (`PCW_APP_DIR`, `PCW_LOG_DIR`). Before this release, tests wrote to the developer's real `errors.log`, `freeze_dump.txt`, optimization receipts, voltage baseline and TURBO profiles.
- New guards: nothing unreachable from `startup.py`, no Polish text outside the locale files, every button and label as wide as its text on the main pages, no Tk callback errors while the pages open, every settings write through `prefs_io`.

## [1.8.7] - 2026-08-08

### hck_GPT, largest rebuild so far
**`hck_gpt/engine/`, `hck_gpt/intents/`, `hck_gpt/memory/`, `hck_gpt/responses/`, `hck_gpt/context/`, `hck_gpt/data/` (new packages)**
- The assistant was split along responsibility lines instead of living in a few large files: routing engine, intent vocabulary and parsing, memory, response building, system context and metrics each own a package.
- Conversation context carries across turns, so a follow-up correction works the way people actually talk: ask about the CPU, then say "I meant the GPU", and the assistant swaps the component without losing the question.
- `QUESTION_BANK.md` added: a written bank of real user phrasings that the intent layer is tested against, instead of testing by feel.
- `hck_gpt/easter_eggs.py`, `hck_gpt/process_library.py` and `hck_gpt/tooltip.py` split out of the panel.
- Dead `hck_gpt/report_window.py` removed (640 lines) after it stopped being reachable.

### hck_GPT, guided flows
**`hck_gpt/engine/flow_engine.py` (new), `hck_gpt/responses/flows.py` (new)**
- `tuneup_guide` was the only handler that could hold a conversation across several turns. That pattern is now an engine: a flow is a list of steps, and the engine owns the navigation, so every guide understands "dalej", "tak", "pomiń" and "stop" without its author writing that code again.
- Four flows ship: **optimize**, **cooling**, **desktop_repair**, **upgrade_plan**. The optimize flow measures first, walks through startup and services, asks before it touches RAM, then verifies with the numbers it measured at the start.
- One flow can be active at a time, and starting another ends the first. Steps reuse the existing engines rather than reimplementing them.
- 13 tests in `tests/test_flow_engine.py`.

### hck_GPT, semantic routing
**`hck_gpt/intents/semantic_rules.py` (new)**
- A layer between the keyword parser and the ML classifier, for the relationships a bag of words tends to drop: process plus close plus safe means "is it safe to kill this", drive plus 100% plus background means the disk question, temperature plus a time reference means a comparison and not a reading.
- Nine route families: processes, thermals, hardware, diagnosis, history, gaming and power, upgrades, conversation control and conversation.
- Rules ask for several independent cues before they commit. They never run an action, and returning nothing is a legal answer that hands the decision back to the parser. Out-of-domain questions are rejected openly instead of being forced into the nearest intent.

### hck_GPT, conversation director
**`hck_gpt/responses/r_conversation.py` (new), `hck_gpt/responses/r_assistant.py` (new)**
- 11 handlers that keep a diagnosis coherent when a real conversation wanders: correcting the subject ("I meant the GPU"), supplying a detail that was missing a moment ago, coming back after trying the advice, comparing before and after, declining a suggestion, or asking why the assistant is confident.
- These sit on top of the category handlers and the flows, they do not replace either.
- 24 tests in `tests/test_conversation_director.py`.

### hck_GPT, proactivity that can be tested
**`hck_gpt/memory/proactive_policy.py` (new), `hck_gpt/memory/game_session.py` (new)**
- The decision "is this worth interrupting the user for" moved out of the background daemon into a pure scoring policy, so it can be tested without starting a thread or touching Tk. `ProactiveMonitor` still owns the daemon.
- Game sessions are tracked headlessly: no extra polling and no second detector, because `GamingToastWatcher` remains the one place that notices a game starting. FPS is recorded only when it genuinely came from RTSS, never estimated.
- 7 tests in `tests/test_game_session_tracker.py`.

### Guides inside the app
**`hck_gpt/guide_links.py` (new), `hck_gpt/responses/builder.py`, `hck_gpt/panel.py`, `ui/windows/main_window_expanded.py`**
- 23 guides have been published on pcworkman.dev and the app never mentioned them. Now hard questions carry an offer to the guide that answers them in full: 22 guides mapped to 54 intents, attached once in `build()` rather than in every handler.
- The offer comes after the live answer, never instead of it, and each guide is offered once per session so a repeated question does not repeat the link.
- Guide links are amber, because they open a browser. In-app navigation stays purple. Short alias intents like "cpu" or "ram" carry no offer at all.
- The Guide page gained a banner to the same library.
- `tests/test_guide_links.py` checks the target file actually exists in both languages. Two guides are Polish-first, so for them `index.html` is the Polish page and English lives at `index_en.html`, the opposite of the other 21.

### Store package: links in, shortcuts that work, a splash instead of a blank wait
**`utils/deep_link.py` (new), `utils/shortcuts.py` (new), `startup.py`, `ui/pages/settings_page.py`, `AppxManifest.xml`**
- **`pcworkman://` links.** A guide on the website can now open the page it is talking about: `pcworkman://open/startup_manager`, `pcworkman://guide/<slug>`, `pcworkman://ask?q=...`. The app already links out to the 23 guides; this closes the loop the other way.
- The parser is treated as a trust boundary, because a link arrives from a web page. Only page ids that exist in the router are accepted, a guide slug must look like a slug, and question text is capped and placed in the chat input rather than sent. **There is deliberately no verb that runs an optimisation**, so a link cannot flush RAM or suspend anything. `tests/test_deep_link.py` fails the build if that changes.
- **Desktop shortcut that actually opens the app.** The Store shortcut pointed at an Application Id that does not exist in the published manifest, so it launched nothing. Shortcut logic moved into one module with the correct AUMID, and a test pins it.
- **Optional "Run as administrator" shortcut** for portable installs, created by flipping the RunAsUser bit in the .lnk header, the same thing the Windows Advanced checkbox writes. On a Store install it is refused with a reason rather than faked, because Windows does not elevate a packaged app launched through the AppsFolder.
- **Package assets fixed.** The MSIX shipped one 32x32 image used for every tile, including the 150x150 one, which is what the June certification rejected as blurry. All sizes now ship from `branding/store`, plus a splash screen so launch is not a blank wait.

### Optimization Receipts now cover TURBO
**`core/opt_receipts.py`, `ui/pages/optimization_services.py`**
- TURBO suspended processes and stopped services without ever saying what it gained. Both now open a receipt, and the receipt panel in Optimization features shows all of them.
- `record()` takes a `delay`, because the honest measuring point differs per action. A RAM flush is finished when it returns, so 20 seconds is fair. Process suspension does nothing until something has been idle past the threshold, so its receipt waits for the threshold plus 30 seconds instead of printing a proof that nothing happened.
- Receipts carry a `detail` line saying what was touched ("12 processes suspended"), evaluated when the AFTER snapshot is taken so it reports what was true, not what was intended.
- **Fixed a receipt that could report another action's numbers.** The AFTER callback found its own entry by "timestamp within 0.5 seconds", so two receipts opened in the same instant could be matched to each other. Entries now carry a unique id. `tests/test_opt_receipts.py` pins it.

### Process library, 485 to 521 entries
**`data/process_library.json`**
- A scan on a normal machine returned 35 processes the app did not recognise, which is noise rather than information. Added the Windows components every user has (Search indexer hosts, Device Association host, Component Package server, Security Health, Settings, Defender core service, Xbox services, rundll32), motherboard vendor tools (MSI Center and Mystic Light, ASUS, Intel Management Engine) and common applications.
- **Vendors are the Authenticode signers read from the binaries, not guesses.** A first pass used plausible-looking vendor names, and that was worse than saying nothing: an expected vendor that does not match the real signer raises `publisher_mismatch`, so three processes that had merely been unrecognised turned into "caution". Every vendor string was then read from the signature.
- Same machine after the pass: 0 unrecognised, 1 caution, and that one is a tune-up suite deliberately marked worth watching.

### Fixes
- **The mini-antivirus flagged the Print Spooler.** `spoolsv.exe` and `dllhost.exe` came back as "caution" with a valid Microsoft signature and the correct System32 path, because a process-library note meaning "heavy or bloatware-class" was escalating the security verdict, and promotion to trusted only ran while the verdict was still "unknown". Advisory codes can no longer be the sole cause of a security verdict. Masquerade, homoglyph and miner detection are unchanged and pinned by `tests/test_process_guard_verdicts.py`.
- **The in-game overlay could freeze the app itself.** It refused protected processes by name only, while `hibernation_manager` also checks `is_self(pid)`. A rename or a repackage would have silently removed that protection, and suspending our own process hangs the app hard enough to need Task Manager. The overlay now checks the PID first. `auto_optimizer` also stopped trimming its own working set.
- **Ultrawide screens got a window taller than the screen.** Above 1920 px the scale formula read width only and assumed height followed. On a 3840x1080 super-ultrawide that picked the 4K tier and produced a 1150 px window on a 1080 px screen, with the bottom off-screen. Every tier is now clamped by the height that exists. 1080p, 1440p and 4K are unchanged. Checked against 14 screen sizes from 1024x768 to 5120x1440.
- **The diagnostic console could stay open with no explanation.** On Windows 11 with Windows Terminal as the default, `GetConsoleWindow()` returns a hidden proxy window, so hiding it succeeds and changes nothing on screen. The app now checks the window class, and when it cannot hide the console it says so in plain language, explains that closing it closes the app, and points at the setting that fixes it. The event is written to `errors.log` through the new `crash_log.log_event()`.
- **"CHECK UPDATE ON GITHUB" opened a 404.** It pointed at `HCK-Labs/PC-Workman`, which does not exist. Both GitHub links in the app now point at the real repository.

### Shared helpers, duplication removed
**`utils/prefs_io.py` (new), `utils/win_active.py` (new)**
- One guarded JSON read/write pair replaces six private `_load_prefs`/`_save_prefs` copies. Reads return the default instead of raising, writes return False instead of raising.
- One `foreground_pid()` replaces three private copies.
- Migrated: `core/auto_optimizer.py`, `core/hibernation_manager.py`, `core/process_guard.py`, `ui/pages/optimization_services.py`, `ui/pages/startup_manager.py`, `core/app_activity_tracker.py`, `core/fps_monitor.py`, `core/turbo_manager.py`.

### Tests
- Test count from 229 to 331, all green. `tests/test_prefs_io.py` pins the dedup contract and fails the build if a private copy comes back; `tests/test_window_scaling.py` gained a ratchet that fails if any screen size would get a window it cannot show.

## [1.8.5] - 2026-07-21

### Upgrade Readiness - Offline part compatibility
**`core/hardware_compat_db.py` (new), `core/hardware_compat.py` (new), `ui/pages/upgrade_readiness.py` (new)**
- New offline hardware library: 320 entries (174 desktop CPUs from Intel 4th gen to Core Ultra 200S and AMD FX to Ryzen 9000, 79 GPUs from GTX 700 to RTX 50 / RX 500 to RX 9000 / Arc, 58 chipsets, 9 sockets). No network calls.
- The engine knows per-chipset CPU-generation support, not just sockets: B460 cannot run 11th gen at all, Z490 needs a BIOS update, LGA1151 100/200 vs 300 boards are electrically incompatible, B550 never supported Ryzen 1000/2000, B450 runs a 5800X3D only after a BIOS flash. Cross-socket verdicts include RAM carry-over (resolved from your actual module speed on DDR4/DDR5 boards) and cooler-mount compatibility.
- New Upgrade Readiness page: type a planned purchase ("i5 11400F", "RTX 4070", "DDR5 6000"), get a green/amber/red verdict with reasons. Quick-pick chips suggest same-socket CPUs your chipset actually runs and GPU classes above your current card. Entry buttons sit at each part in My PC > Components and on First Setup & Drivers and Monitoring & Alerts.
- GPU checks report the class delta versus your current card (honest about sidegrades and downgrades), VRAM change, recommended PSU wattage and a CPU-pairing note for old platforms.
- Live autocomplete: start typing a model in the search box and a list of matching parts appears (CPU/GPU tag, socket or VRAM, year) - pick one instead of remembering the exact name. Library grew to 188 CPUs and 84 GPUs. The page opens with a colour legend explaining the green/amber/red verdicts and what the check reads.
- The My PC Efficiency tab now shows a definition tooltip when you hover a process name (the same process library the dashboard uses), and each component card in My PC > Components carries an UPGRADE READINESS link that jumps to the checker for that part.

### Optimization Center - Upgrade Advisor card
**`ui/pages/optimization_services.py`, `locales/pl.json`, `locales/en.json`**
- New expandable card. Different question than the checker: reads your own 14-day load history and says WHAT is worth upgrading (CPU-bound / GPU-bound / RAM pressure / balanced), then lists concrete same-socket picks and jumps into the full checker.

### hck_GPT v2.1.x
**`hck_gpt/responses/r_upgrade.py` (new), `hck_gpt/intents/vocabulary.py`, `hck_gpt/intents/parser.py`**
- Two new intents: `upgrade_compat` ("czy i5 11400F bedzie pasowac do mojej plyty", "will an i5 13600K fit my board") and `ram_compat` ("czy DDR5 zadziala", "what RAM fits"). Fully bilingual answers composed from engine facts, with a clickable [-> Upgrade Readiness] nav link.
- Parser gained a domain rule: a concrete part model (i5-11400F, RTX 4070, DDR5...) next to fit/swap wording routes to the upgrade intents even when the model name sits mid-sentence. Neighbouring intents (temperature, game_can_run, hw_ram, upgrade_feasibility) verified untouched.
- `r_hardware.py` was approaching the monolith limit; the Upgrade Readiness handlers live in their own `r_upgrade.py` mixin (96 intents total).

### One version source
**`utils/app_version.py` (new), `startup.py`, `core/telemetry.py`, `hck_gpt/responses/builder.py`, `ui/windows/main_window_expanded.py`, `ui/windows/main_window.py`, `PCWorkman.spec`**
- The app version now lives in exactly one file: `utils/app_version.py`. Window titles, the HCK_Labs badge, "What's new", the Build info table, the startup banner, telemetry payloads, the hck_GPT about answer and the PyInstaller dist folder name all read it. Bump one line, everything follows.
- This fixed three real bugs the audit surfaced: (1) the main window titled itself v1.8.1 while the single-instance code searched for a v1.8.2 title, so focusing the already-running app on a second launch was silently dead; (2) telemetry and the chat about-answer read `startup.py` as a file, which is not shipped inside the frozen build, so they reported a stale "1.8.0" in release builds; (3) the Build info table still said 1.7.2.
- A repo-wide test now fails if any source file hardcodes a version literal again, and fails a version bump that ships without its changelog section.

### hck_GPT - builder split into mixins
**`hck_gpt/responses/builder.py`, `r_hardware.py`, `r_thermal.py`, `r_gaming.py`, `r_system.py`, `r_performance.py`, `r_insights.py`, `r_assistant.py`, `common.py` (new files)**
- The 6,533-line builder monolith is now a facade over eight category mixins plus shared helpers; dispatch (`_resp_<intent>` via MRO) is unchanged. builder.py itself is under 600 lines.
- A guard test fired all handlers through both languages after the split and caught the one real casualty: the module-level singleton had been dropped, which switched the whole AI layer off with no crash and no log. Restored, and a permanent AI-layer-alive test guards it.
- A monolith-guard test caps every response module at 1,600 lines, so the split cannot quietly grow back.

### hck_GPT - guided flows and context memory
**`hck_gpt/engine/flow_engine.py` (new), `hck_gpt/responses/flows.py` (new), `hck_gpt/memory/session_memory.py`**
- FlowEngine: stateful multi-step guides inside the chat. "Optimize my PC" walks measure -> startup -> services -> confirmed RAM flush -> verify, and the verify step reports the measured delta ("RAM 82% -> 61%, -21 pp"). Any other question pauses the flow, gets answered, and the flow waits. PL and EN navigation words (dalej/next, pomiń/skip, stop).
- Response ledger: every data answer leaves its headline in session memory, so "ile to było?" / "what was that number" recalls any earlier answer, not just flow steps.
- Vocabulary grew to 94 intents; a self-consistency test parses every declared phrase and fails on cross-intent collisions (3,100+ phrases checked, collisions deduplicated).

### Sidebar restructure
**`ui/components/sidebar_nav.py`, `ui/windows/main_window_expanded.py`**
- FANS Hardware Info and Usage Statistics merged into one page with an internal toggle; Health / Efficiency / Statistics tabs retired; Components joined My PC with a sidebar deep-link; Optimization now points at three real destinations (Center, Startup Manager, Services Manager). Legacy sidebar ids still route.

### Stability and fixes
**`ui/windows/main_window_expanded.py`, `ui/components/yourpc_page.py`, `ui/pages/optimization_services.py`, `ui/pages/fan_control/usage_stats.py`**
- CRITICAL regression caught by a click-test and fixed the same day: a console-cleanup pass converted trace prints to a gated `_dbg()` that rejected print kwargs, and the resulting TypeError on the first line of the navigation handler sent every sidebar click back to the dashboard. Fixed, and a new test now builds the real main window and fires every navigation item, so a break of this class cannot pass CI again.
- Console de-spam: routine trace prints are silent unless debug mode is on.
- Optimization Center: expanding a right-column card no longer strands an empty slot in the grid; all card open/close combinations verified.
- Fan Usage "NOW" chart: samples arrive every 5 s but the code divided by 60, so the live window held a single point. Now 12 points.
- My PC Components: motherboard banner moved to the top with model and version side by side; clean empty-state cards when a scan returns nothing; three async loaders fixed to marshal onto the main thread before touching widgets; per-tab metric scans cached for 60 s and warmed during the splash.
- Guide page rebuilt as a 3x2 tile grid (plus a Smart Learning tile) and the Live Guide gained a 6th step; hero buttons and headers de-emojied.

### Monitoring & Learning
**`ui/pages/monitoring_alerts.py`, `core/voltage_analyzer.py`, `core/live_collector.py`, `hck_gpt/data/metrics_store.py`, `hck_gpt/memory/proactive_monitor.py`**
- Page header simplified: the duplicate gradient banner is gone, one quiet line explains the tab, the Learning Center moved from 6-7pt to readable 8pt type and every string went through locales (learning levels are translated: skalibrowany/wytrenowany/podstawowy).
- Voltage learning now covers CPU VCore and GPU core, not just the board rails (12V/5V/3.3V): unit-aware LHM tree parsing, new snapshot columns with an automatic migration for existing installs, SPC baselines per rail. Needs LibreHardwareMonitor's web server, honestly labeled when absent.
- Learned-baseline anomalies finally land in the Events log WITH context: "82°C in gaming workload (normal 57-71°C)", voltage events carry the learned band. Before, the log held only shutdowns and raw spikes.

### Fan Dashboard rebuilt
**`ui/components/fan_dashboard.py`, `hck_gpt/panel.py`, `hck_gpt/responses/r_thermal.py`**
- New curve chart: dark-to-bright-red heat gradient that follows the curve height, dual % / RPM axes, monotonic points (cannot pass neighbours), live temperature marker. Three sliders sit under the chart and visibly shape it: MIN lifts the floor, MAX rescales the RPM axis, SET draws the manual-override line.
- THE APPLY RULE: chart and sliders are a draft. Touching anything turns the fan cards amber ("FANS - values while configuring"); Apply persists the plan (reloaded on every open) and re-locks the chart behind the hover padlock; Revert discards the draft. Apply previously claimed success while saving nothing.
- Fan cards are live now (real temps, smooth 62px rings) - the old ones drew a pixelated ring once, with hardcoded someone-else's hardware names. Component tiles are vector icons drawn on canvas (the raster PNGs are gone), with a spinning rotor that follows the curve.
- The chart's hck_GPT [AI] button unfolds the chat and asks a consult question in the app's language; the answer covers temps now, the learned history, gentle tuning advice and the learned "hck_GPT - AI" profile - which chat can apply for real on request.

### TURBO armed panel + master-switch fixes
**`ui/pages/optimization_services.py`, `core/auto_optimizer.py`**
- Quick Actions shows what the master TURBO switch will actually fire: X/N armed with per-feature dots, one source of truth. The audit behind it closed three real holes: the RAM card's ON TURBO pill was never bound, hibernation turbo behaviors fired only through the power plan, and the master switch never touched the services profile. All process/service work now runs off the UI thread.

### Diagnostics that leave evidence
**`utils/freeze_watchdog.py` (new), `utils/crash_log.py` (new)**
- Freeze watchdog: a heartbeat from the UI thread plus a daemon that dumps every thread's stack to `data/logs/freeze_dump.txt` after 15 s of silence - the next hard freeze names its exact line.
- Global error log: Tk callback exceptions (previously swallowed into a hidden console), worker-thread exceptions and uncaught errors all land with full tracebacks in `data/logs/errors.log`.

### Performance - My PC opens fast
**`ui/windows/main_window_expanded.py`, `ui/components/yourpc_page.py`**
- My PC (and other full-cover overlays) no longer builds the entire dashboard underneath just to cover it. Measured ~26% of the entry cost was this wasted build; it now happens only when the overlay is closed, to reveal it.
- Removed the two blocking `wmic` calls from the My PC build path (CPU name, disk models), each with a 3-second timeout on the UI thread. On Windows 11 24H2, where `wmic` is slow and deprecated, these were the main cause of "My PC loads forever". The names now come from the hardware identity already warmed at startup.
- Keep-alive (Phase 2): My PC is built ONCE per session and then hidden/shown instead of destroyed/rebuilt. Re-entering takes 1-17 ms (was ~990 ms at the start of the day); switching back to a visited tab (Central, Components, Map) is instant. Refresh loops are visibility-aware - they idle at 3 s while the page is hidden and resume when shown. The cache is honestly invalidated on language change and window maximize (old strings/geometry never linger), and staleness-prone tabs (Startup, Health, Efficiency) still rebuild fresh every visit.
- Fixed a pre-existing animation race where a still-running overlay slide could grab and drag the WRONG overlay after a quick page switch - both animations now capture their frame.
- Startup: the sidebar built ~90 subitem widgets for every collapsed section at launch, all invisible until you expand one. They are now built lazily on first expand (deep-links still reach them). Steady-state window init dropped to roughly 190 ms.
- The splash already warms the hardware identity and the service/startup metrics off-thread, so the first My PC and hck_GPT hardware answers are instant.
- Result in profiling: central tab build ~590 -> ~160 ms, first entry ~990 -> ~350 ms, every later entry 1-17 ms. Ratchet tests guard the build path (no `wmic`), the cache lifecycle, the loop guards and the lazy sidebar.

### Diagnostics
**`utils/crash_log.py` (new)**
- Global error capture: Tk callback exceptions (previously swallowed into an auto-hidden console), worker-thread exceptions and uncaught errors all land with full tracebacks in `data/logs/errors.log`.

### Accuracy
**`core/monitor.py`, `hck_gpt/memory/proactive_monitor.py`, `data/process_library.json`**
- Per-process CPU is now on the whole-machine scale. Raw psutil values are per-core, so one busy thread on a 12-thread CPU read "100%" while the machine idled at 8% - top-process lists ranked it absurdly and the 30% proactive spike alert fired for nothing.
- Process library grew from 373 to 485 definitions: the Rockstar/Social Club family, anti-cheat services, launcher helpers, vmmem and other often-asked Windows processes, local AI runtimes, flagship games.

### Tests
- 55 -> 177 since 1.8.2. New guard families: version single-source, real-window navigation and page builds, hardware library integrity, 20+ compatibility-verdict cases including every known trap, routing matrix in both directions, phrase self-consistency, AI-layer-alive, monolith caps, voltage-rail pipeline, fan-curve math and the APPLY rule, TURBO armed wiring, CPU-scale ratchets.

## [1.8.2] - 2026-07-09

### CRITICAL - total system freeze fix
**`core/protected_processes.py`, `core/hibernation_manager.py`, `core/app_activity_tracker.py`**
- Under long sessions the app could freeze the whole system (white screen, dead desktop, restart to recover). Root cause: `sleep_app`, the single suspend/idle-priority primitive, guarded only anti-cheat, so App Hibernation could suspend an OS-critical process (dwm.exe draws the screen, explorer.exe is the desktop) or PC Workman's own process.
- The central guard now also covers ~30 OS-critical processes (dwm, explorer, csrss, lsass, services, svchost, Defender, ...) and the app itself (`is_self(pid)` via `os.getpid()`). All four process primitives (hibernation, TURBO suspension, RAM flush, overlay) consult the same guard, so one fix hardened them all. The Unused Apps list filters critical processes out entirely.
- Regression-tested: 13 critical/self processes blocked for both freeze and low-priority behaviors, 6 normal apps + 3 games still optimizable. Tests 42 -> 46.

### Run as administrator (optional)
**`startup.py`, `ui/pages/settings_page.py`, `locales/en.json`, `locales/pl.json`**
- New Settings -> General toggle. When on, startup relaunches elevated with a single UAC prompt (ShellExecuteW "runas") before the mutex/Tk init. Declining the prompt runs the app normally, no loop. Skipped on Microsoft Store installs.

### Display scaling fix (small screens, 125% DPI laptops)
**`utils/ui_scale.py`**
- The window geometry scaled with SCALE but fonts never did; on 125-150% DPI laptops Tk renders points larger while the pixel layout stays fixed, so text clipped (hck_GPT banner, panel labels). `ui_scale.init` now pins Tk's font factor to `(96/72) * SCALE`, so every point-sized font follows the window. 1080p at 100% is unchanged.

### hck_GPT
**`hck_gpt/intents/vocabulary.py`**
- 19 new warm/hot temperature phrasings (PL/EN), "dlaczego moj laptop jest cieply" / "why is my laptop hot" now route to the temperature answer.

## [1.8.1] - 2026-07-05

### One always-on data machine
**`core/live_collector.py` (new), `utils/paths.py`, `startup.py`**
- Live sensors were fed only by UI pages (My PC, Fan Dashboard). With no page open the overlay showed "--", Monitoring waited on "Collecting data..." forever and the learning engines got zero samples. New always-on collector daemon (2 s tick): psutil + nvidia-smi + OHM/LHM web sensors + CPU temp with an honesty flag (`cpu_temp_src: sensor|est`); estimated temps never enter history or learning. Pages are consumers only.
- **Microsoft Store installs could not save anything.** Under MSIX the exe lives in read-only WindowsApps, so every write silently failed (stats DB, learned baselines, prefs; hence OFFLINE badges on Store installs). `utils/paths.py` now detects WindowsApps (plus a real write probe) and redirects APP_DIR to `%LOCALAPPDATA%\PC_Workman_HCK`. Six duplicated `_base_dir()` copies unified onto one module.
- History retention 90 -> 183 days. `session_hist` writers merge instead of overwriting each other.

### Anti-cheat hard guard
**`core/protected_processes.py` (new)**
- One authoritative `is_protected()` covering ~35 anti-cheat executables and drivers (Vanguard, EasyAntiCheat, BattlEye, FACEIT, PunkBuster, GameGuard, XIGNCODE, mhyprot + keyword fallback), wired into all four process primitives: hibernation sleep, TURBO suspension, RAM-flush working-set trim and the overlay actions. Games themselves (LeagueClient.exe, VALORANT.exe) stay optimizable; only the anti-cheat engines are blocked.

### Learning engine v3 - learns on every machine
**`core/thermal_baseline.py`, `hck_gpt/responses/builder.py`, `ui/pages/monitoring_alerts.py`**
- The engine learned only CPU temperature, which needs LibreHardwareMonitor; most machines never install it, so their Learning Center sat at 0% forever. Now a Welford accumulator runs per (workload bucket, metric) for CPU temp, GPU temp and CPU load; a primary-metric fallback picks the best real signal for the Learning Center, chat and alerts, with an honest "run LibreHardwareMonitor to unlock CPU temp" hint.
- Time counter: the engine records its earliest folded snapshot and shows "Learning for X days, Yh observed" plus per-bucket observed hours.
- `classify_temp()` became a real engine entry point (previously an AttributeError swallowed by a broad except, so verdicts were always empty).
- `ai_context` ("what have you learned about my PC") rewritten to present the learned state; +45 natural PL/EN phrases across ai_context, compare_baseline, sensor_report and thermal_prediction.

### AUTO features always-on
**`core/auto_optimizer.py` (new), `startup.py`, `ui/pages/optimization_services.py`**
- The Auto RAM Flush watcher lived inside the Optimization page and ran only while the page was open; after an app restart the AUTO pill looked on but the watcher was dead. New always-on daemon started from `startup.py`, driven by saved prefs, runs with no UI open; the page is now a configurator plus status listener. TURBO coupling added (`ram_on_turbo`). The `ram_flush()` primitive moved to core with the anti-cheat and user-exclusion guard.

### Startup Manager - disables that stick
**`ui/pages/startup_manager.py`**
- Disable now writes the `StartupApproved` flag Windows itself respects (the Task Manager mechanism), so apps that re-create their Run keys on every launch (OneDrive, Advanced SystemCare) stay disabled anyway. The scan also reads that flag, so entries disabled in Task Manager display correctly.

### hck_GPT - 20 DeepMonitor handlers
**`hck_gpt/responses/builder.py`, `hck_gpt/intents/vocabulary.py`**
- 16 intents had trigger patterns but no handler: the parser matched them with full confidence and users got silence. All 16 implemented plus 4 new, reading live sensor data (voltages, fan RPM, thermal history, morning brief). First stateful multi-message coaching: `tuneup_guide` walks a 4-step plan with the machine's own numbers. Vocabulary is now 90 intents.

### Store / UI pass
- Desktop-shortcut button in Settings for Store installs, adaptive process-row count for small laptops, contrast audit (60 fixes across 11 files), subprocess output decoding hardened repo-wide (`errors="replace"`).

### Tests
- 21 -> 42: anti-cheat guard regression, intent-handler parity (the "silent intent" class cannot ship again), APP_DIR/MSIX path resolution with a real write probe, thermal baseline v3 on both LHM and no-LHM machines.

## [1.8.0] - 2026-06-22

### Post-release patch - 2026-06-28
**`ui/pages/services_manager.py`, `ui/components/operator_drawer.py` (new), `ui/pages/optimization_services.py`, `core/hardware_detector.py`, `ui/pages/startup_manager.py`, `hck_gpt/services_manager.py`**
- **Services Manager is now a configurator.** One Wyłącz/Włącz control per service queues the change into a single shared operator drawer at the bottom of the page; Zatwierdź applies the whole batch at once and marks each change as user-made. Removes the cramped per-row buttons that truncated long service names. SZCZEGÓŁY expands the queue inline.
- Fixed a crash that blanked the Features page (`'float' object is not callable`), a gradient loop variable shadowed the translation helper. Feature cards now widen into the neighbouring column when expanded, so long descriptions are readable.
- **Hardware detection works on Windows 11 24H2+** (build ≥ 26100), where `wmic.exe` no longer ships: CPU / GPU / RAM / motherboard / disk reads fall back to PowerShell `Get-CimInstance`. Fixes empty values in My PC → Components on recent builds.
- Windows `sc` / PowerShell output is now decoded with `errors="replace"`, so a service or task name with a non-ANSI byte no longer crashes a background reader thread when opening Services Manager.
- Mouse-wheel scrolling in Services Manager is scoped to the page instead of bound globally, so it no longer leaks between views.
- New `operator.*` / `optimization.*` strings localised in PL and EN.

### Smart Learning - engines wired into chat, and they accumulate
**`core/thermal_baseline.py`, `core/voltage_analyzer.py`, `hck_gpt/responses/builder.py`, `hck_gpt/memory/proactive_monitor.py`, `ui/pages/monitoring_alerts.py`**
- hck_GPT now answers temperature with the **learned, workload-aware verdict** (`thermal_baseline.format_for_chat`) instead of a fixed 85°C cutoff, 82°C reads *normal* under a gaming load but *critical* at idle. `voltage_check` got its own handler via `voltage_analyzer` (was silently aliased to the temperature handler). The chat handler imported neither engine before.
- Proactive monitor judges CPU temperature against the learned per-workload baseline (`_thermal_verdict`, z-score) with a fixed-threshold fallback until a bucket is trained, so it no longer cries wolf during normal gaming. Elevated-but-safe goes out as a 💡 TIP, not an alarm.
- **Thermal baseline is now a true Welford accumulator.** Each rebuild folds only the snapshots recorded since the last one into a per-bucket running `{n, mean, M2}`; learning accumulates over the whole life of the install (persisted to JSON) and survives even after the raw snapshots are pruned at 90 days, instead of recomputing from a fixed 14-day window. `sigma`/`p5`/`p95` derive live from `mean`+`M2`. A continuous fold tick in the proactive loop (`_learning_tick`) keeps it learning while the app runs, not only when Monitoring is open or temps are asked. A non-blocking rebuild guard prevents concurrent double-counting; `VERSION` bump discards the old windowed format.
- **Learning Center** in Monitoring & Alerts: per-workload thermal training progress + learned ranges, per-rail voltage SPC baselines, overall %, a live PSU health score, and a ↻ Rebuild self-check.
- Voltage rail health now reflects **genuine Nelson-rule anomalies** (after GPU-transient suppression + recurrence decay), not the ~1.2% Gaussian tail beyond 2.5σ, a healthy rail no longer reads "critical" once enough snapshots accumulate. `overall_health_score()` wired into the Learning Center header; dead `all_ranges()` / `_modified_z()` and unused imports removed.
- **Two new proactive learning notes** (`proactive_monitor.py`): a one-time 💡 milestone when a workload bucket reaches full calibration ("I now judge temperature against YOUR normal"), and a 💡 "new normal" note when a recurring voltage blip decays into your hardware's baseline. Both budget-gated and deduped/persisted so they never nag.

### GAMING - In-Game Overlay + visual configurator
**`ui/components/ingame_overlay.py` (new), `ui/components/yourpc_page.py`**
- New **GAMING / In-Game** tile in My PC (replaces the Device Manager / Task Manager / Export shortcuts): a translucent, always-on-top HUD that floats over **borderless / windowed** games without stealing focus (layered tool-window, `WS_EX_NOACTIVATE`). Left/right-click cycles it through the four screen corners.
- **Table layout** that mirrors a real HUD: one row per component (CPU / GPU / RAM / 12V), value cells to the right, FPS as a tall side box. Live values from `live_sensors` with a psutil fallback.
- **Form-style configurator**: three presets plus a Create-Custom builder where each field is a ▼ dropdown (native menu) to pick the metric per row, no duplicates. Live preview renders 1:1 with the overlay. **Style panel**: size (S/M/L), theme (dark / slate / contrast), opacity. Everything persists to `settings/gaming_overlay.json`.
- **Live FPS** via `core/fps_monitor.py` (new): reads the RTSS shared-memory block published by RivaTuner / MSI Afterburner, no admin, no DLL injection, no anti-cheat surface. Picks the foreground app's frame rate; falls back to "-" when RTSS isn't running. (Per-pixel transparency remains a follow-up.)
- **Game launch greetings** (`ui/components/gaming_toast.py`): rebuilt to bilingual PL/EN with random variants and grown to 40+ games (Planet Zoo, Terraria, Minecraft, Helldivers 2, GTA V, Hades, Palworld, …). A known game starting drops a one-second corner toast.
- The existing always-on **MiniOverlay** gets an on/off control in the same hub.

### Startup Manager - full source coverage
**`ui/pages/startup_manager.py`**
- Enumerate Task Scheduler logon/boot tasks (`Get-ScheduledTask`, locale-independent, unlike schtasks CSV headers) and Microsoft Store/UWP startup apps (registry `State` DWORD) next to the existing Run keys + Startup folders. Previously invisible entries (GPU Tweak, ShareX, LinkedIn, MSI Center, …) now appear.
- Reversible enable/disable per source: registry removal, `schtasks /change`, or UWP state toggle. Active/disabled split reflects real system state for tasks/UWP. New source badges (⏰ Task · ⊞ Store).

### Services Manager - mode configurator
**`ui/pages/services_manager.py`, `core/turbo_manager.py`**
- Per-service **G/E/M** chips assign each service to the Gaming / Economy / MANAGER stop-lists, replacing the orphaned single "turbo_stop" toggle that drove nothing.
- Guided recommendations strip with plain questions ("Do you use Bluetooth?") that build the MANAGER profile.
- `turbo_manager` is now the single source of truth: editable per-mode profiles persisted to `settings/turbo_services.json` (`get/set_profile_services`, `set_membership`, `reset_profile`), a white-themed `manager` profile, a `RECOMMENDED` set, and `list_all_services()`.

### Features
**`ui/pages/optimization_services.py`**
- New **MANAGER** mode chip (white) after Gaming/Economy with a clickable **ⓘ** that opens the Services Manager. Mode chips read the effective per-mode lists, so configurator edits sync live.

### hck_GPT - Process Suspect Guard (mini-AV)
**`core/process_guard.py` (new), `hck_gpt/responses/builder.py`**
- Author (Authenticode) verification + typosquat/homoglyph + masquerade detection; verdicts trusted/unknown/caution/suspicious/danger with bilingual reasons. Microsoft signers always trusted (WHCP). Wired into `virus_check` and `process_identity`.

### hck_GPT - routing & polish
- Natural-language routing overhaul across ~16 intents + an ML-blend fix (a strong keyword phrase now beats an over-confident NB guess): everyday phrasings route correctly. Hardware names (Intel, RTX, DDR5…) highlighted purple in chat.

### hck_GPT - four new data-driven intents
**`hck_gpt/responses/builder.py`, `hck_gpt/intents/vocabulary.py`**
- **`upgrade_advice`** ("what should I upgrade?") finds the real bottleneck from your own 14-day load + temperature history, CPU pinned while the GPU idles ⇒ CPU is the limit; hot but not maxed ⇒ check cooling before replacing, grounded in the actual numbers, not generic advice.
- **`privacy_data`** ("do you spy / what do you collect?") answers honestly: local-only, hardware stats only, never files or keystrokes, with a click-through to the Stability Tests.
- **`greeting` / `small_talk`** now open with your favourite app ("Fancy CS2 again today?") via `get_top_processes_lifetime`; `about_program` reads the live version (`_app_version()`) instead of a hardcoded one.
- **`startup_check`** lists your real startup entries and links to the Manager ("…or tell me what to disable") with a Disabled-tab reminder. New phrasings ("co się odpala z windowsem", "jakie mam aplikacje autostartu") route correctly. Vocabulary is now **84 intents**; the ML classifier auto-retrains on the fingerprint change.

### Fixes
- `chat_handler`: dead late-retry path (out-of-scope `_parsed_result` raised a swallowed NameError).
- `insights`: missing `Optional` import crashed the module at import on Python 3.9–3.13 (silently disabling Insights).
- `hybrid_engine._INTENT_HINTS`: 19 duplicate keys deduped. `vocabulary`: duplicate `gaming` entity key.
- `builder`: System Idle Process no longer listed as a CPU culprit; `temp_comparison` double `hck_GPT:` prefix; `hw_cpu` live model fallback.
- `query_api.get_temperature_summary`: selected non-existent `cpu_temp_max` / `gpu_temp_max` columns, so the query threw and every 7-day temperature comparison silently returned nothing. Now reads the stored `*_avg` columns (max derived from the period averages).

## [1.7.9] - 2026-06-11

### Maximized View Mode - full redesign

**`ui/windows/main_window_expanded.py`**
- Symmetric dashboard layout: TOP 8 user processes left, TOP 8 system right (280 px columns). Temperature/Voltage mini-monitors removed, their data lives in Monitoring & Alerts.
- Turbo Boost + Optimization Center buttons docked to the bottom edge, 48 px clearance for the hck_GPT banner.
- Main chart fixed at 35% of window height (was fill-everything). Session-averages section 180 → 274 px, taller bars (20 px), inset 72 px so its edges align with the chart column below.
- Hardware cards: sparkline 22 → 50 px, component name drawn inside the chart corner (`_draw_card_corner`, canvas-attr based) instead of a header row. Compact mode unchanged.

### Chart tooltip 2.0

- Hover (not click) shows a borderless Toplevel at 72% opacity next to the cursor: Segoe UI Black labels, bold mono values, live sample age.
- Click pins. Pinned tooltip docks to its bar, age keeps ticking, and the pin index follows the LIVE ring buffer (auto-unpins at the left edge). Any click while pinned unpins, in LIVE the bar drifts 1 px/s, so "click the same bar" was untargetable.
- PIN strip styled like the hck_GPT TIP/HOT strips (badge canvas + bordered frame). New locale key `dashboard.chart_unpin` (PL/EN).
- Fixed: sample age was computed ×2 (samples arrive 1/s, not every 2 s). Historical filters use real span ÷ bar count.
- Pin + tooltip cleared on every page switch.

### TOP 8 processes

- Scroll fix: the Enter/Leave `bind_all` died the moment the cursor touched a row (`<Leave>` fires with NotifyInferior), so the wheel never worked over rows. Wheel is now bound directly on the canvas + every row subtree.
- Stale-offset fix: `yview_moveto(0)` whenever content fits the viewport, kills the blank gap stuck at the top.
- Removed dead primary branch calling `data_manager.get_latest_snapshot()`, the method exists nowhere; psutil was always the real path. CPU%/RAM% math verified (raw psutil per-proc ÷ core count = machine %, Task-Manager style).
- Style: rows 36 → 40 px, names Segoe UI Semibold 8 pt, values bold mono 7 pt, `<1%` instead of a misleading `0%`.

### hck_GPT panel

**`hck_gpt/panel.py`**
- Panel width now tracks the live parent width, scales correctly in maximized mode; right-anchored banner items reposition on width change.
- `set_height_scale()`: maximized window → default open height +12%, chat-Maximize +35%; clamped to window height.
- `open()` packs the chat with `expand=True`, log fills the taller panel, no dead band under the entry.
- Visibility gate (`set_visibility_gate`): a deferred re-dock can no longer resurrect the banner on pages that must not show it.
- `frame.lift()` on every re-dock, dashboard rebuilds created siblings above the place()'d panel, leaving the banner covered and unclickable after returning from maximized.
- Banner gradient rebuilt only on width change; shimmer recolors ~350 persistent rects via `itemconfig` (was delete+create at 10 fps). Sweep idles at 2 Hz while the panel is hidden.

### hck_GPT on tabs

- Banner now rides on MY PC and FAN DASHBOARD (`_GPT_BANNER_PAGES`), lifted above the overlay; hidden everywhere else.
- Overlay slide-in/out uses the real content width, hardcoded 980 px left the overlay half-visible in maximized mode.

### Window-state bugs

- `restore_window()` (new): re-applies the tracked maximize state after `deiconify()`, Windows can bring a withdrawn window back zoomed, which broke minimal → expanded after a maximize round-trip. Used by tray restore and `startup.py → switch_to_expanded` (bare `except` there now logs).
- `_switch_to_minimal` remembers geometry; restore puts the window back exactly where it was.

### Audit (resource leaks, dead code)

- 1326 lines of dead code removed from `main_window_expanded.py`: `_REMOVED_*` chart methods, never-started glow animations, orphaned PC-2D/fan-card/advanced-dashboard cluster (zero callers, repo-wide grep + dynamic-access check).
- 8× global `<MouseWheel>` `bind_all(add="+")` leaks de-stacked (monitoring_alerts, first_setup_drivers, sensor_kb, yourpc_page ×2, services_manager, hck_labs/guide); optimization_services converted to scoped Enter/Leave binding.
- `ui/components/pc_map.py`, `ui/components/pro_info_table.py`: background loops now stop via `<Destroy>`, one leaked thread/timer per page visit before.
- `ui/overlay_widget.py`: update thread gets a stop flag; breaks instead of erroring every 2 s after the window closes.
- Nav icons load from `BUNDLE_DIR`, relative `data/icons` broke in frozen EXE when CWD differed.
- `_bar_anim_id` added to the page-switch cancel list.

## [1.7.8-monitoring] - 2026-06-05

### Bug fixes

**`ui/pages/startup_manager.py`**
- `_render()` crashes with `NameError: name 'self' is not defined` at line 930. Root cause: `host` parameter received by `build_startup_manager_page(host, parent)` was never forwarded into `_render()`. Page built the title label then died, everything below line 930 (tabs, panels, entries) was never rendered.
  - Fix: `_render()` now takes `host=None`; `_on_ready` passes `host=host`; `_full_refresh()` forwards it too.
  - `getattr(self, "_switch_to_page", None)` → `getattr(host, "_switch_to_page", None) if host else None`

**`ui/windows/main_window_expanded.py`, overlay header coverage**
- Main header "PC Workman v1.7.8 HCK Edition" remained visible for all overlay pages (MY PC, MONITORING, STATISTICS, etc.) because `_show_overlay()` placed the frame at `y=60`, deliberately below the 58px header.
  - Fix: non-settings overlays now use `y=0, relwidth=1.0, relheight=1.0` → full coverage. Settings stays at `y=60` (main header visible per spec).
  - Three prior fix attempts had treated this as a missing `pack_forget()` problem; the root cause was the hardcoded `y=60` offset in `place()`.

**`PCWorkman.spec`**
- Added `core.app_activity_tracker` and `core.hibernation_manager` to `hiddenimports` (both new modules were missing from the build manifest).

---

### New: `core/thermal_baseline.py`

Workload-aware CPU temperature baseline learning.

- Five workload buckets: `idle` (CPU<15%) / `light` / `medium` / `heavy` / `gaming` (GPU≥60%)
- Per-bucket statistics: Welford's online algorithm applied to DeepMonitor snapshots from last 14 days. Produces `mean`, `σ`, `p5`, `p95` per bucket. Fresh stats computed from DB on each `rebuild()`, not incremental EMA, avoids the "learned spike" problem.
- Training levels: `no_data` → `initializing` → `learning` → `basic` → `trained` → `calibrated` (thresholds: 5/20/60/200 samples).
- JSON persistence: `data/cache/thermal_baseline.json`. Fast startup, version-checked.
- `BaselineRange.context_label(temp)` returns `"14% above usual  (Gaming: 65–78°C, ±2.3°C)"`, used as chart tooltip and hck_GPT context.
- `thermal_baseline.maybe_rebuild(min_interval_s=300)`, self-throttled async rebuild, called on each monitoring page refresh.
- Singleton: `thermal_baseline`.

---

### New: `core/voltage_analyzer.py`

SPC-based voltage rail intelligence using Median + MAD (not mean + σ).

**Why MAD:** A spike shifts the mean toward itself, widening the "normal band" and hiding subsequent spikes. Median is unaffected by outliers. MAD (Median Absolute Deviation) inherits this property.

**Algorithm:** Modified z-score (Iglewicz & Hoaglin 1993): `M = 0.6745 × (x − median) / MAD`. Anomaly if `|M| > 3.5`, warning if `|M| > 2.5`.

**Nelson SPC rules implemented:**
- Rule 1: single point beyond `Z_ANOMALY` → `isolated_spike`
- Rule 5: 2-of-3 consecutive points beyond `Z_WARNING` (same sign) → `cluster`
- Rule 2: 9 consecutive points same side of median → `sustained_high` / `sustained_low`
- Rule 3: 6 consecutive monotonically changing points → `trend_up` / `trend_down`

**Context suppression:** 12V rail spikes during GPU load delta >25% → downgraded to `transient` (physically expected behavior).

**Anomaly decay:** Same spike magnitude (±30% tolerance) appearing ≥5 times → severity reduced one tier and flagged as "learned normal".

**hck_GPT API:**
- `format_for_chat(lang)`, formatted multi-line voltage status string, chat-ready.
- `get_anomaly_summary()`, structured dict per rail (n_crit, n_warn, health, latest reason).
- `VoltageEvent.reason_for_chat(lang)`, bilingual event description.

Persistence: `data/cache/voltage_baseline.json`. Requires LHM/OHM for real data; graceful no-data path.

---

### New: `ui/components/interactive_chart.py`

Reusable Tkinter canvas chart with full interaction model.

- **Pan:** left-drag → shift view window (data-index space)
- **Zoom:** scroll wheel → expand/contract around cursor X (factor 0.75×/1.33×)
- **Reset:** double-click or "⟲ reset" button
- **Crosshair:** dotted X+Y lines follow cursor with live value bubble
- **Pin:** single click → anchor detailed tooltip on nearest data point. Shows: timestamp, all series values, deviation from baseline (`▲ 14% vs learned baseline`), anomaly `[event_type]` + reason. Persists until click-elsewhere or double-click.
- **Minimap:** 18px strip below chart. Full data range compressed view. Darkened overlay outside selection window. Click or drag to jump/pan.
- **Baseline band:** shaded region from `set_baseline(mean, lo, hi)` (e.g. from `thermal_baseline`).
- **Anomaly markers:** colored vertical lines + dots at anomaly indices.
- **Multi-series:** `set_series([{values, color, label}, ...])`, stacked filled areas + lines.

---

### Modified: `ui/pages/monitoring_alerts.py`

- **InteractiveChart integration:** Temperature and Load sections now use `InteractiveChart` instead of static canvas when available. Fallback to existing draw functions if import fails.
- **Learning Status Bar:** compact row above Temperature section, 5 colored bucket pills (idle/light/medium/heavy/gaming) with training level color coding and sample count. Overall `%` badge + "rebuilt X min ago".
- **Workload-context temperature:** `_refresh_temp()` classifies workload from recent data, fetches `thermal_baseline.get_range(bucket)`, passes `ext_mean/lo/hi` to `_draw_adaptive_chart()`. Badge shows `"Normal (Gaming: 65–78°C)"` instead of generic `"No regular problems"`.
- **Temperature stats:** `temp_lifetime_avg` label now shows `45.2°C ±3.1` (learned baseline mean±σ) instead of `--`.
- **Voltage Rails section** (`_build_voltage_section`): Three-column SPC display (12V / 5V / 3.3V). Each column: `InteractiveChart`-compatible canvas, stats (Median / MAD / UCL / LCL / Samples), health badge. No-data path shows LHM explanation. Badge driven by `_refresh_voltage()` using `voltage_analyzer`.
- **Voltage chart** (`_draw_voltage_chart`): Tight Y-axis (nominal ±10%). Layers: ATX spec band / normal band / warn dashed lines / UCL+LCL dashed / nominal dotted / actual line / anomaly dots.
- **Auto-baseline rebuild:** `_start_refresh()` now calls `thermal_baseline.maybe_rebuild(300)` and `voltage_analyzer.maybe_rebuild(300)` on every 30s refresh cycle.

---

### Modified: `hck_gpt/memory/proactive_monitor.py`

- Two new alert message pools: `voltage_spike` and `voltage_trend` (PL + EN).
- `_volt_check_tick` counter, voltage check runs every 4 main cycles (~3 min; lighter than main checks).
- `_was_volt_anomaly` state, prevents alert spam; fires once per anomaly window, clears on resolution.
- `_check_voltage_rails()`: loads last 60 min from `voltage_analyzer.analyze_history()`, filters suppressed/decayed/info events, fires `voltage_spike` or `voltage_trend` alert through existing `_alert()` system (session budget + gap protection apply).

---

### Modified: `ui/windows/main_window_expanded.py` - dashboard chart

- `realtime_canvas` now has `<ButtonPress-1>`, `<Motion>`, `<Leave>` bindings.
- `_chart_on_click()`: pins/unpins a detail tooltip on the nearest bar (second click on same bar = unpin).
- `_chart_on_motion()`: hover tooltip when nothing is pinned (bar index → CPU/RAM/GPU% + "Xs ago").
- Tooltip is a `tk.Label` placed on `self.root` via `.place()`, appears above cursor, clamped to window bounds. Shows `[pinned]` tag when click-anchored.

---

### Code quality audit - 6 modules, 13 fixes + 8 innovations

**`core/voltage_analyzer.py`**
- Bug: `get_anomaly_summary()["latest"]` was returning the most recent event from *any* rail, filtered to `e.rail == key` per-rail now.
- Added `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000` to `_query_history()` and `snapshot_count()`, prevents `SQLITE_BUSY` under concurrent writer activity.
- New: `overall_health_score() -> int` (0–100), PSU health composite. Deducts 20pt per undecayed critical event, 10pt per warning, 15pt per sustained deviation. Independent of thermal/memory/load scores in `monitoring_alerts.py`.

**`core/thermal_baseline.py`**
- Fixed: `import sqlite3` was inside `_query_db()`, caused `NameError` on first call if no other module had imported sqlite3. Moved to top-level.
- Bug: variance used population formula `/n`. Corrected to Bessel's correction `/ max(n-1, 1)` for unbiased sample variance.
- `overall_training_pct()`: batched into single lock acquisition, was releasing between reads, risking a stale intermediate count.
- New: `format_for_chat(cpu_temp, cpu_load, gpu_load, lang)`, workload-contextualized string for hck_GPT intent handlers (PL/EN).

**`hck_gpt/intents/ml_classifier.py`**
- Removed duplicate `"moje"` in `TrainingDataBuilder` content-word stopwords set.
- Extracted `NB_SMOOTHING = 0.5` module constant, used in both `NaiveBayesClassifier.__init__` and `cross_validate` (was two independent `0.5` literals).
- New: `get_top_k(text, k=5) -> List[Tuple[str, float]]`, full probability distribution sorted by confidence. Intent routing debug + vocabulary quality review.

**`hck_stats_engine/query_api.py`**
- `get_summary_stats()`: removed dead code, `latest_daily_ts = max(...) if False else 0` was always 0.
- `_downsample()`: changed `int(idx)` to `round(idx)`, eliminates cumulative truncation bias across the stride sequence.
- `_query_monthly_range()`: results now passed through `_downsample(results, max_points)` before return (was skipping the step entirely).

**`ui/components/pc_map.py`**
- Font objects (`ImageFont.truetype`) moved to instance variables, cached after first load. Was re-loading from disk on every 120ms render frame, 2–4 unnecessary I/O calls per cycle.
- Fixed: `_gather_live.__call__()` → `_gather_live()` (wrong attribute access on a bound method).
- New: `_thermal_aware_cpu_heat(cpu_pct, cpu_temp, gpu_pct) -> float`, heat value for the CPU block now uses `thermal_baseline` z-score when a calibrated baseline exists (`heat = z/3.0`). Falls back to the prior blend formula when baseline is not yet usable.

**`core/hibernation_manager.py`**
- `wake_app()`: `psutil.NoSuchProcess` now returns `True`, process already gone counts as successfully woken.
- New: `cleanup_dead_pids() -> int`, removes stale entries from `_sleeping` for PIDs that have exited naturally. Updates component status. Safe to call periodically.
- New: `get_savings_estimate() -> dict`, returns `{processes, total_sleep_min, frozen_count, low_count}` from internal timestamps; no psutil query required.

---

## [1.7.7-patched] - 2026-06-03

UI/UX audit pass, 5 targeted fixes found during post-release review.
No new features. No breaking changes. Safe upgrade from v1.7.7.

### Startup Manager - UX overhaul

**`ui/pages/startup_manager.py`**

- Renamed "Needs Attention" section header to **"Startup Menu"**, matches the tab label, clearer purpose
- Removed non-functional "All entries" panel from the split layout, page now shows a single full-width list of flagged entries
- Fixed geometry manager conflict (`pack` + `grid` on same parent), admin notice moved inside `header_block`; notice now survives `_full_refresh()` calls
- Auto-refresh after restoring a disabled entry works correctly, `_full_refresh()` re-reads registry and rebuilds view immediately

### Services Manager - stop/start logic fix

**`ui/pages/services_manager.py`**

- **Both Stop and Start buttons now always visible** for every non-essential, non-disabled service
  - Active direction: full color (Stop = red, Start = green)
  - Inactive direction: muted/ghosted, makes it immediately clear both operations are available
  - Previously: only the "relevant" button was shown, which made the page look like it could only enable services
- Expand banner text changed from `∨ Show N more ∨` to **`∨ Rozwiń więcej (N) ∨`** (Polish, compact `pady=2`)

### First Setup & Drivers - readability + GHOST visibility

**`ui/pages/first_setup_drivers.py`**

- **GHOST badge now visible immediately on card header**, `card["badge"]` overridden with bordeaux `⚠ N ghost` text when ghost detected; no longer requires expanding the card
- Ghost devices in expanded panel highlighted with bordeaux background + `⚠ GHOST` badge (was plain row)
- Expand button now shows count: `▼ pokaż wszystkie (N)` / `▲ zwiń`; shows `⚠ GHOST` suffix when ghosts present
- Subcategory text ("Display / Graphics", "Sound Device" etc.): color `#5a6a80` → `#8a9db8`, clearly readable
- Expand button font: 6pt → 7pt, color `#4b5563` → `#6b7280`
- Ghost badge font: 5pt → 7pt + increased padding
- `ghost_names` set now passed from `_apply` to `_fill_expand_panel`, expand panel knows which devices are ghosts

### Page headers - compact back button

**`ui/windows/main_window_expanded.py`**

- `_build_page_header()`: height 60px → 26px; removed large title and subtitle labels (already shown inside page); kept only `← Główne Menu` in small muted style
- Applies to: Startup Manager, Services Manager, and all other sub-pages using `_build_page_header`

---

## [1.7.7] - 2026-06-02

### Ghost Driver Detection - new feature

**`ui/pages/first_setup_drivers.py`**

- Ghost drivers = driver packages left in Windows registry after replacing hardware (e.g. old GPU still installed after swap)
- Detection: `pnputil /enum-devices /class {guid} /connected` returns only physically present hardware; anything in the registry but not in connected output is flagged as ghost
- WMI (`Win32_VideoController`) was intentionally avoided, it returns phantom devices too, making it unreliable for this use case
- Ghost entries shown with bordeaux background, `⚠` marker, and `100% UNUSED` / `⚠ GHOST` badge visible on card header without expanding
- `_open_ghost_dialog()`, Toplevel popup with device age, version, explanation, and optional removal
- `pnputil /remove-device <instanceID> /subtree` for removal (admin required, confirmation dialog)
- Works across all 4 driver categories: GPU, Audio, Network, USB

### Drivers tab - SEE EVERYTHING / SEE OUTDATED views

- Two mode buttons added to DRIVER HEALTH section header
- **SEE EVERYTHING**, all detected drivers across all classes, grouped by category (GPU first), ghost entries highlighted
- **SEE OUTDATED (N)**, only drivers >= 730 days (~24 months), sorted oldest first; count badge updated after scan
- BACK button replaces mode buttons while in extended view
- `_build_see_everything_view()`, `_build_see_outdated_view()`, self-contained view builders
- Extended views show: category badge, device name, version, date, age badge, ghost marker where applicable

### Drivers tab - all devices per class

- `_read_all_class_drivers(guid)`, collects all unique devices per class (not just first entry)
- Each driver card: expand button `▼ show all (N)` reveals complete device list
- Per-device: name, version, date badge, age color (730+ days = red, 365-730 = amber)
- Devices >= 730 days marked red in expand panel

### Optimization - Auto RAM Flush process exclusion

**`ui/pages/optimization_services.py`**

- `_RAM_EXCLUDE: set`, module-level exclusion list, loaded from `user_prefs.json → optimization.ram_flush_exclude` at startup
- `_do_ram_flush()`, skips excluded processes by name; result shows `N protected` count
- `_build_exclusion_panel()`, bordeaux-styled panel inside RAM Flush card expand area:
  - Process list: excluded first (always visible even offline), then running alphabetically
  - Click to toggle protection; `↺ Refresh` reloads live process list
  - Excluded processes persist across app restarts
- `_save_exclude()`, writes sorted list to prefs immediately on toggle

### hck_GPT panel - HOT strip duplicate monitor removed

**`hck_gpt/panel.py`**

- Removed `_hot_monitor_tick()` and `_start_hot_monitor()`, they duplicated proactive_monitor's HOT logic at lower thresholds (RAM >= 85% vs proactive_monitor's 93%), causing double-triggers
- HOT strip now driven exclusively by `proactive_monitor` via `register_hot()` callback
- Also removed broken Polish strings from the panel-side monitor (missing diacritics: "duz uzuzycie", "Uwazaj", "goraca")

### hck_GPT - intent alias fix

**`hck_gpt/responses/builder.py`**

- `ram_flush` alias: `ram_why_high` → `optimization`, user asking to flush RAM gets actionable optimization response instead of a diagnosis

### MAP OF COMPONENTS - case_front fix

**`ui/components/pc_map.py`**

- Removed solid `case_front` panel (7.5×15 box drawn last, covering all internals in screen-space)
- Replaced with 4 thin structural corner rails, open-front case look, all components visible

### Admin notices

**`ui/pages/startup_manager.py`**

- Non-admin notice upgraded: amber warning matching Services Manager style, `⚠ Not running as Administrator, HKLM startup entries cannot be modified. Right-click PC Workman → Run as administrator.`

---

## [1.7.6] - 2026-05-29

### DeepMonitor - complete rewrite

**`ui/components/pro_info_table.py`** rewritten as `DeepMonitorTable` (alias `ProInfoTable` kept):
- `ttk.Treeview` with 4 aligned columns (Sensor / Value / Min / Max), no more misaligned labels
- Temperature rows: blue-night background tint; Utilization rows: indigo tint; per-row color intensifies with heat
- Sub-section headers color-coded by type (CPU temp = steel-blue, GPU = violet, Memory = slate-blue, Clocks = teal)
- Action bar: Save Data (filedialog → .txt / .csv), Pause (amber when active), Reset mins/maxes
- Popup: header bar removed, title `"DeepMonitor - PC Workman"`, size 660×760

### MAP OF COMPONENTS - new feature

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

### hck_GPT - critical bug fix

- **`panel.py`**: `lang` variable undefined in `_welcome()` caused `NameError` on every startup, propagated to `_build_hckgpt_banner()` except block, which showed the `bg="#8b5cf6"` (violet) fallback bar at the bottom of the window. Fixed: `lang = self._ui_lang` added at top of `_welcome()`.

### hck_GPT - Wave 2 community intents (6 new)

Built from community feedback (GitHub Discussions / LinkedIn). All intents have PL+EN patterns, real hardware data, and no hallucination fallback.

- `game_can_run`, checks 20-game `_GAME_DB` for RAM/VRAM/disk requirements vs installed hardware
- `gaming_ram_usage`, live game process RAM (psutil) + session peak + 7-day comparison
- `daily_ram_usage`, live psutil + 7-day `metrics_store` trend; verdict: very high / high / moderate / low
- `battery_estimate`, `psutil.sensors_battery()` + activity-based drain rate (gaming 22-35%/h, work 8-15%/h, idle 3-6%/h)
- `upgrade_feasibility`, WMI slot count + current sticks + disk partitions; reports free slots, max RAM, disk free space
- `top_resource_hog`, TOP 5 by RSS memory + TOP 5 by cumulative disk I/O; auto-detects if user asked for RAM or disk

**Vocabulary:** 76 -> **82 intents** total (68 rule handlers in builder.py)

### hck_GPT - conversation flow

New routing steps in `chat_handler.py` (before the AI parser):
- Step 3.5: greeting detection, "cześć", "hej", "hi", "hello" → warm live-data response with CPU%/RAM%
- Step 3.6: thanks detection, "dzięki", "thanks", "thx" → friendly acknowledgment (4 PL + 4 EN variants)
- Step 3.7: "more info", "więcej", "tell me more", "rozwiń" → re-runs last intent with refreshed data
- Step 3.8: "what should I do", "co zrobić", "jak naprawić" → context-aware routing based on last topic + recent events
- `_default_response` now: retries hybrid engine at confidence 0.18, detects `.exe` names → routes to `process_identity`, varies fallback text (4 PL + 4 EN phrases), shows last conversation topic
- Fixed duplicate `"bateria"`/`"battery"` keys in `_QUICK_ALIASES` (both silently resolved to `battery_estimate` only; `battery_drain_rate` was unreachable)

New `builder.py` handlers: `_resp_greeting`, `_resp_thanks`, `_resp_health_check` (rewritten, score 0-100, live CPU/GPU temps, issues list, delta vs typical, verdict badge)

Small talk pool: 5 → 11 variants PL, 5 → 11 EN.

### hck_GPT - proactive monitor - DeepMonitor integration

**`proactive_monitor.py`** new `_check_deepmonitor()` (runs every 3 main cycles ≈ 2 min 15s):
- CPU temp: warn >80°C, critical >90°C (2 consecutive readings, hysteresis)
- GPU temp: warn >82°C, critical >92°C
- Severe throttle: alert when CPU freq <55% of max (separate from normal throttle)
- Multi-drive disk: scans ALL mounted drives (not just C:), alerts any <8 GB free
- Sensor health insight: positive "all clear" message after an issue resolves
- 8 new message pools (PL + EN) for the above events

Banner status text now includes live temperatures: `CPU 34%  RAM 62%  CPU 52°C  GPU 68°C  - OK`

Polish idle tips pool: 11 → 24 entries.

### hck_GPT - system context temperature fix

**`hck_gpt/context/system_context.py`** `snapshot()` now fetches `cpu_temp` and `gpu_temp` via `core.hardware_sensors.get_cpu_temp/get_gpu_temp` (LibreHardwareMonitor-backed). Previously only used `psutil.sensors_temperatures()` which returns nothing on Windows, meaning all temperature-based proactive alerts and LLM context were silently broken.

`build_prompt_context()` now includes `cpu_temp` inline with CPU line and a `GPU temp: XX°C` line.

Ollama system prompt: added `[Recent Conversation]` section (last 3 exchanges), 3 new rules (context continuity, frustration acknowledgment, personality).

### hck_GPT - Language sync

- `panel.py`: `_ui_lang` now initialized from `i18n.get_lang()` instead of hardcoded `"en"`
- `panel.py`: `_on_i18n_lang_changed()` callback registered via `i18n.register_on_change()`, when Settings page switches language, hck_GPT panel updates language and refreshes welcome screen
- `panel.py`: `_welcome()` and `_add_startup_quip()` now bilingual (PL/EN)
- `panel.py`: Polish language option `"⚠ not stable"` badge removed
- `panel.py`: language popup `_select()` calls `i18n.set_lang()` to propagate change globally

### Process library

- **`data/process_library.json`**: 241 → **373 entries** (+82 common processes, +50 games)
- New processes: Signal, Viber, Webex, Bitwarden, KeePassXC, VeraCrypt, Mullvad/ProtonVPN, MPV, PotPlayer, Kodi, foobar2000, AutoHotkey, ShareX, PowerToys, WizTree, Krita, Godot 3/4, Unreal Editor, Obsidian, REAPER, FL Studio, HeidiSQL, RustDesk, Parsec, latencymon, kubectl, kubectl, qBittorrent, Duplicati, WinGet, Rufus, Chocolatey, and more
- New games: RDR2, Horizon ZD/FW, Helldivers 2, Palworld, Satisfactory, Rust, DayZ, Sons of the Forest, Factorio, Cities 1/2, CK3, EU4, HoI4, Stellaris, Victoria 3, TW Warhammer 3, MHW/MHR, RE4/RE8, DMC5, Dark Souls 3, Sekiro, DBD, Hunt Showdown, Phasmophobia, Alan Wake 2, and more

- **`core/process_definitions.py`**: +25 rich entries with `full_name`, `category`, `description`, `purpose`, `normal_behavior`, `warning`, `developer` fields: Brave, Vivaldi, Slack, Zoom, Telegram, WhatsApp, Skype, Signal, Windows Defender, Malwarebytes, Bitwarden, Python, Node.js, Git, Godot 3/4, Unreal Editor, VLC, OBS, GIMP, Krita, Blender, Premiere, DaVinci Resolve, and others

### import_core.py - startup registry

- Every registered component now gets a sequential `seq` number (auto-incrementing, thread-safe)
- `list_components()` now shows `[01] core.logger  [ok]`, sorted by registration order
- `STARTUP_MANIFEST`, list of 20 expected components with intended startup order
- `verify_startup()`, checks registered components vs manifest; returns `{ok, missing, extra, report}` with tick/cross table
- 5 previously unregistered components now register themselves: `hck_gpt.proactive_monitor`, `hck_stats_engine.db_manager`, `hck_stats_engine.aggregator`, `hck_stats_engine.query_api`, `core.startup_watcher`

### Dashboard UI fixes

- **Turbo Boost** frame height: `fill="both", expand=True` on inner frame caused it to stretch vertically, changed to `fill="x"`
- **Optimization Center** excess space: two empty placeholder labels (`tools_label`, `tools_count_label`) removed; `expand=True` removed from content frames
- Both fixes applied to `_build_feature_buttons()` in `main_window_expanded.py`

### Welcome Toast

**`ui/components/system_toast.py`**, new `show_welcome_toast(root, delay_ms=1800)`:
- Slides in from bottom-right 1.8 s after UI is ready
- Auto-detects Windows system language via `GetUserDefaultUILanguage` LCID + `locale` fallback
- Polish: *"Hej! Dziękujemy, że korzystasz z PC Workmana :)"* / English: *"Hey! Thanks for using PC Workman :)"*
- Body text explains the startup monitoring and proactive alerts in user's language
- Version badge: `v1.7.6 · 29.05.2026`
- Violet/indigo colour scheme with hand-drawn PC/WK canvas badge icon
- Wired into `startup.py` right after UI creation

### MAP OF COMPONENTS - display fix

**`ui/components/pc_map.py`**:
- Added vertical scrollbar to canvas wrapper, scene no longer clips at bottom of smaller tabs
- Mouse-wheel scroll support on canvas
- Desktop PC origin `_OY` raised by 40 px (`_CH - 75` -> `_CH - 115`): most of scene visible without scrolling
- Laptop origin `_LOY` raised by 40 px (`_CH - 90` -> `_CH - 130`) to match

### hck_GPT - HOT alert strip (anti-spam system alerts)

**`hck_gpt/panel.py`**, new dark-red `HOT` strip above the `TIP` strip:
- Crimson badge `HOT` + message text; visually connects to TIP section
- Monitors RAM / CPU / GPU temp every 8 s via `_hot_monitor_tick()`
- **Anti-spam logic**: strip appears once when threshold is crossed, stays silently until metrics return to normal, no repeated pop-ins while condition holds
- Thresholds: RAM ≥ 85 % warn / ≥ 92 % critical; CPU ≥ 88 % warn / ≥ 95 % critical; GPU temp ≥ 90 °C critical
- Messages bilingual PL/EN matching `_ui_lang`
- First check 12 s after startup (app settle time); cleared via `_clear_hot()` when all metrics normal
- Widget packed `before=_tip_strip` (or before input if no tip), always below HOT, above entry

### Font system - 100% UI coverage

**`utils/fonts.py`** already defined `UI` and `MONO` (Inter/Segoe UI + Consolas). Previously ~50% of the UI used it.

All remaining files now import the font system and use `_HDR` / `_BODY` / `_MONO` aliases:

- **`ui/windows/main_window_expanded.py`**, 140 hardcoded font strings replaced (largest file)
- **`ui/windows/main_window.py`**, 45 strings replaced
- **`ui/pages/monitoring_alerts.py`**, 52 strings replaced
- **`ui/pages/first_setup_drivers.py`**, 38 strings replaced
- **`ui/pages/optimization_services.py`**, `_F`/`_M` aliases upgraded to full system + `_HDR` added
- **`ui/pages/services_manager.py`**, `_F`/`_M` aliases upgraded to full system
- **`ui/pages/startup_manager.py`**, `_F`/`_M` aliases upgraded to full system
- **`ui/pages/settings_page.py`**, 40 strings replaced
- **`ui/pages/stability_tests.py`**, 14 strings replaced
- **`ui/pages/page_all_stats.py`**, 22 strings replaced
- **`ui/pages/page_day_stats.py`**, 7 strings replaced
- **`ui/pages/fan_control/hardware_info.py`**, font system added
- **`ui/pages/fan_control/usage_stats.py`**, font system added
- **`ui/components/fan_dashboard.py`**, 35 strings replaced
- **`ui/components/pc_map.py`**, font system added (new 1.7.6 file)
- **`ui/components/pro_info_table.py`**, font system added (DeepMonitor)
- **`ui/components/yourpc_page.py`**, remaining hardcoded strings replaced (had partial coverage)
- **`ui/components/fan_curve_editor.py`**, font system added
- **`ui/components/hardware_graphs.py`**, font system added
- **`ui/components/sensor_kb.py`**, font system added
- **`ui/components/sensor_tree.py`**, font system added
- **`ui/components/sidebar_nav.py`**, font system added
- **`ui/components/system_toast.py`**, font system added
- **`ui/components/led_bars.py`**, font system added
- **`ui/components/charts.py`**, font system added
- **`ui/components/process_tooltip.py`**, font system added
- **`ui/guide/live_guide.py`**, remaining strings replaced
- **`ui/overlay_widget.py`**, font system added
- **`ui/overlay_mini_monitor.py`**, `_F_*` font constants migrated to `_BODY`/`_HDR` variables
- **`ui/dialogs.py`**, font system added
- **`ui/splash_screen.py`**, font system added
- **`ui/theme.py`**, `font_family`/`font_small`/`font_base`/`font_large` now use `_UIF`/`_MONOF` variables

Result: zero hardcoded `"Segoe UI"` / `"Consolas"` strings in the UI layer (intentional weight variants `Segoe UI Light`, `Segoe UI Black`, `Segoe UI Semilight` preserved where used as design choices).

### Code quality

- Replaced all em-dashes `-` with `-` and arrows `->` / `<-` across 58 Python files (1,135 em-dashes, 367 right arrows, 44 left arrows)
- Archived `PC_Workman HCK.exe` (v1.7.5) to `build/archive_v175/`

---

## [1.7.5] - 2026-05-25

### hck_GPT - 13 new intents (community requests)

Built from 28 real responses collected on GitHub Discussions and LinkedIn.

**New intents added to `vocabulary.py` / `hybrid_engine.py` / `builder.py`:**
- `fan_noise_history`, fan speed trend over time, spike detection
- `driver_status`, installed driver ages from Windows registry
- `gaming_vs_work_time`, session split: gaming vs productivity
- `process_identity`, identify unknown process (lookup + safety rating)
- `stale_apps`, apps open but idle for 30+ min
- `fps_degradation`, FPS drop over session with thermal/CPU correlation
- `app_behavior_change`, detect if an app behaves differently than usual
- `startup_slowdown`, boot time trend across sessions
- `temp_comparison`, today's temps vs N-day average
- `crash_context`, what was running at the last crash
- `game_hardware_stress`, hardware load profile during gaming sessions
- `battery_drain_rate`, battery % loss rate, drain source identification
- `power_after_restart`, power draw comparison before/after restart

**Vocabulary:** 63 → **76 intents** total

### hck_GPT - 4 MEGA features

**Context Time-Windowing** (`hybrid_engine.py`)
- `_CONTEXT_WINDOWS` dict, 21 intents mapped to history windows (5 min → 7 days)
- `build_llm_context_windowed()` in `system_context.py`, context scoped to the intent's window; narrow windows strip stale patterns, wide windows append daily metric history

**Fallback / No-AI-Slop** (`builder.py`)
- `_no_data(intent, lang, what_missing)`, structured "data unavailable" response instead of hallucinating; wired into `stale_apps`, `startup_slowdown`, `gaming_vs_work_time`, `temp_comparison`

**Time-Travel Debugging** (`builder.py`)
- `_get_historical_comparison(metric, days, lang)`, compares live sensor value to N-day historical average from `metrics_store.daily_summary()`
- `_METRIC_COL_MAP`, maps user-facing metric names to correct SQL column aliases

**Micro-Benchmarking** (`builder.py`)
- `_trigger_micro_benchmark(bench_type)`, background thread; `cpu_single` (1M sqrt ops) or `disk_seq` (32 MB write+read); results stored in `session_memory` under `micro_bench`

### hck_GPT - session memory additions (`session_memory.py`)
- `get_events_for_window(within_minutes)`, filtered event list for time-windowed context
- `get_spike_context(within_minutes)`, structured spike summary string
- `get_time_windowed_context(intent, lang)`, intent-aware windowed context builder

### hck_GPT - chat handler (`chat_handler.py`)
- 20 new quick aliases (sterowniki, wentylatory, bateria, crash, degradacja fps, etc.)
- `_show_help()` rebuilt with 3 new sections: Time-Travel Diagnostyka, Identyfikacja i bezpieczeństwo, Nawyki i użytkowanie

### Process Library (`data/process_library.json`)
- **104 → 241 entries** (+137 processes)
- New coverage: games (CS2, Elden Ring, Cyberpunk, Tarkov, BG3, KSP, Valheim…), dev tools (PyCharm, IntelliJ, Rider, Cursor, DBeaver…), RGB/peripherals (iCUE, Synapse, Armoury Crate, OpenRGB…), diagnostics (HWiNFO64, GPU-Z, Prime95, FurMark…), VPN/network (WireGuard, Tailscale, NordVPN…), security (BattlEye, EAC, FACEIT, ESET, Bitdefender…), Windows system processes (ntoskrnl, tiworker, audiodg, wsappx, ctfmon…)

### Fixes
- `fan_dashboard.py`, fan settings export now writes to `settings/` instead of project root
- Added `.gitignore` with proper rules for build folders, user exports, and runtime reports

---

## [1.7.4] - 2026-05-14

### Optimization Center - Full Redesign

**`ui/pages/optimization_services.py`**
- Feature grid rebuilt as 2-column layout with equal-width expandable cards; each card has an inline [i] info panel that opens/collapses without leaving the page
- Snapshot strip (CPU / RAM / Disk) now renders subtle fill bars, 9% blend of accent color into surface background, drawn on Canvas to work around Tkinter's lack of alpha channel support
- **Turbo Power Plan**: actually creates a "Turbo PC" power scheme via `powercfg /duplicatescheme` instead of just activating a preset; admin detection via `ctypes.IsUserAnAdmin`; GUID parser rewritten to be language-agnostic (no longer breaks on Polish or other non-English Windows); fallback to Ultimate Performance GUID if HP plan unavailable; `atexit` handler restores original plan on exit
- **Quick Actions** fully replaced: Startup Apps Manager (nav link), Services Manager (nav link), Disk Defragmenter (run), Weekly Performance Report (opens window); removed old shortcuts (flush / telemetry / gaming mode); removed "ALL 4 run on TURBO BOOST" label; accent bars widened to 4px; RUN/OPEN buttons larger; Weekly Report row has dark-green background to distinguish it
- **Weekly Performance Report**: `Toplevel` window with 6 bar charts (3×2 grid), CPU avg, CPU peak, GPU avg, GPU peak, RAM avg, RAM peak across 4 rolling weeks; W4 = latest week rendered full-color + bold; older bars blended toward background; glow/shadow on latest bar; AI-generated text summary (trend direction, RAM pressure, spike detection); EXPORT .TXT button
- **LIVE NOW** sidebar panel: auto-refreshing CPU/RAM/GPU mini-bars, updates every 2 s via `after()`
- Typography upgraded: feature card titles `("Segoe UI Semibold", 8)`, descriptions larger and readable, Quick Actions labels in Segoe UI Semibold; fixed icon Canvas widgets being created before parent frame existed (reparenting via `configure(master=...)` is invalid in Tkinter, fixed by passing parent at creation)

**`ui/windows/main_window_expanded.py`**
- "More Optimization Tools" button replaced with a subtle dark "Optimization Center" chip (`#0c1018` bg, `#1a2235` border, muted text `#3d5070`); click navigates to My PC → Hardware & Health; glow animation removed

**`ui/components/yourpc_page.py`**
- Added `utils.fonts` import with `_HDR / _BODY / _MONO` aliases so the page uses the same Inter/Segoe UI Semibold font system as the rest of the app

---

## [1.7.3] - 2026-05-02

### Live Guide - nowy moduł

**`ui/guide/live_guide.py`**, nowy plik
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

### hck_GPT - jakość odpowiedzi

**`hck_gpt/responses/builder.py`**
- `_resp_help` przepisany, 30 linii, 8 sekcji z emoji: 🖥 Hardware / 🩺 Diagnostics & Health / 📊 Performance & Stats / 🔍 Why is it doing that? / ⚡ Optimization / 🔒 Security / 😄 Fun/Personality / 💬 Small talk; pokrywa wszystkie 37 intentów; bilingual PL/EN
- `_resp_optimization` przepisany, `system_context.snapshot()` dla live CPU/RAM, `_hw_profile()` dla flag HDD/RAM-low/few-cores; priorytetowy tip (🔴 >85% / 🟡 >70% / ✓ OK); linki [→ Optimization], [→ Startup Manager]; warunkowy [→ Virtual Memory] i nota o HDD
- `_FOLLOWUPS` rozszerzony 3 → 8 kluczy: dodano `security`, `disk`, `why`, `process`, `session`; istniejące klucze `hw`/`health`/`perf` dostały dodatkowe pozycje
- `_followup()` dodany do 9 handlerów: `_resp_virus_check` (oba paths), `_resp_disk_health`, `_resp_disk_usage_why`, `_resp_battery_drain`, `_resp_uptime`, `_resp_process_info` (oba paths), `_resp_throttle_check` (OK path), `_resp_perf_change`, `_resp_session_compare`
- `record_response_data` dodany do: `_resp_hw_gpu` (`model`, `vram_gb`), `_resp_perf_change` (`cpu_today/yest`, `ram_today/yest`), `_resp_session_compare` (`cpu/ram today/yest`)

### hck_GPT - hardware scanner & session data

**`hck_gpt/context/hardware_scanner.py`**
- WMI scan uzupełniony o RAM speed (MHz) i part number (`Win32_PhysicalMemory`)
- Skanowanie modelu dysku głównego (`Win32_DiskDrive`, pierwszy wpis)

**`hck_gpt/memory/session_memory.py`**
- Session data store: `record_response_data(intent, data)`, `get_response_data(intent)`, `discussed_this_session()`, pozwala późniejszym handlerom referować dane raportowane wcześniej w sesji

**`hck_gpt/panel.py`**
- `_apply_nav_links(widget, text)`, renderuje `[→ Page]` tokeny jako klikalny link (kolor akcentu, podkreślenie on-hover), wywołuje zarejestrowany callback nawigacyjny
- `register_nav_callback(page_id, fn)`, API do rejestracji callbacków nawigacji z main window
- `_open_virtual_memory()`, helper otwierający Virtual Memory przez `subprocess` (SystemPropertiesAdvanced)

**`hck_gpt/intents/vocabulary.py`**
- Dodano multi-word patterns dla `hw_storage` i `hw_all` dla pewniejszego routingu powyżej progu confidence

---

## [1.7.2] - 2026-04-27

### My PC - Central tab redesign

**Optimization Hub** (`ui/components/yourpc_page.py`)
- Zastąpiono pojedynczy przycisk "Optimization & Services" widgetem trójstrefowym na jednym Canvas:
  - **Lewa strefa (57%)**, *Optimization Center*, gradient amber→ciemna czerwień
  - **Prawa-górna**, *Startup Manager*, gradient navy→niebieski + live liczba wpisów
  - **Prawa-dolna**, *Services Manager*, gradient zielony→emerald + live liczba usług
- Zone detection via `_zone(x, y)` (podział `sp = int(w * 0.57)` + `HEIGHT // 2`)
- Hover brightening 1.25× aktywnej strefy
- Metryki odczytywane w daemon thread, aktualizacja przez `canvas.after(0, _draw)`
- Usunięto baner hck_GPT z zakładki Central

**Startup Manager** (`ui/pages/startup_manager.py`), nowy plik
- Odczyt wpisów startowych z `HKCU`, `HKLM`, `HKLM32` Run via `winreg`
- Baza wiedzy 30 programów: impact (high/medium/low) + rekomendacja (disable/delay/keep)
- Trzy panele: *Optimize at startup* / *Safe to disable* / *All entries*
- Disable = prawdziwe usunięcie z rejestru (`winreg.DeleteValue`) + dialog potwierdzenia
- Preferencje zapisywane do `data/cache/startup_prefs.json`

**Services Manager** (`ui/pages/services_manager.py`), nowy plik
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

### My PC - UI & fonts

- Dodano etykietę **MY PC** (Inter Bold) + separator do paska nawigacyjnego
- Zakładki: czcionka `Segoe UI 7` → `Inter 7 bold`; nagłówki sekcji: `Segoe UI 6` → `Inter 7 bold`
- Przeniesiono Stability Tests + Your Account na dół zakładki (side by side)
- Dodano pasek **SESSION** (`#1e3a5f`): `SESSION: Xh Ym` + `● LIVE`
- Zwiększono wysokość panelu hck_GPT o ~18px (`expanded_h` 280→298)

### hck_GPT - naprawy logiki

- Naprawiono błąd językowy w `_show_help()`, używał `self._last_lang` przed detekcją; zmieniono na `ui_lang`
- Przepisano `_show_help()`, nagłówki `◈`, układ dwukolumnowy, wersje PL i EN
- Naprawiono `_resp_temperature()`, fallback do bazy `minute_stats` gdy `psutil.sensors_temperatures()` puste (Windows)
- Naprawiono `_resp_speed_up_pc()`, usunięto bezwarunkowe TURBO BOOST + FPS tips

### hck_stats_engine - nowe metody query_api

- `get_temperature_history(minutes)`, cpu_temp/gpu_temp z `minute_stats`, current/avg/max
- `get_temperature_summary(days)`, dane z `daily_stats`/`hourly_stats`
- `get_top_processes_lifetime(top_n)`, TOP procesy wg avg CPU ze wszystkich dni
- `get_weekly_summary()`, porównanie bieżących 7 dni vs poprzednie 7 z trendem

### Release 1.7.2 - EXE & packaging

- Wersja ujednolicona we wszystkich plikach (`setup.py`, `startup.py`, `README.md`, spec)
- `requirements.txt` uzupełniony o `numpy>=1.24.0`, `requests>=2.28.0`, `pywin32>=305`
- `PCWorkman.spec` przepisany, 25+ brakujących `hiddenimports` (`hck_gpt.*` submoduły, `ui.components.yourpc_page`, `utils.fonts`, `import_core`), katalog `settings/` dodany do `datas`, `COLLECT(name='PC_Workman_HCK_1.7.2')`
- Build: `dist/PC_Workman_HCK_1.7.2/PC Workman HCK.exe` (10.3 MB launcher, ~94 MB total) ✅

### Codebase cleanup

- Usunięto komentarze `"Apple flat design"`, `"Apple inspired"`, `"Inspired by HWMonitor but BETTER"`
- Usunięto docstring `"MSI Afterburner / Apple inspired"` z `main_window_expanded.py`
- Usunięto `TODO: close overlay...` (zastąpione sensownym komentarzem)

---

## [1.7.2] - 2026-04-22

### hck_GPT - AI Layer & Hybrid Engine

**Panel, Bordeaux Noir redesign** (`hck_gpt/panel.py`)
- Gradient banner redrawn every frame with 5-anchor black→crimson interpolation and sine-wave shimmer per strip
- Left accent bar pulses between `#8b0000` and `#ff2040`; ONLINE badge text pulses between `#ff5566` and `#cc2030`
- `AI` badge rendered as vector rectangle (`#5c0f1a` fill, white 7pt Consolas text), no image file
- ONLINE badge: dark rect `#1e0508` + crimson outline, pulsing text; no moving line across banner
- Banner sweep at 100 ms; gradient redraw uses `tags="grad"` / `tag_raise("ui")` to keep UI elements on top
- Proactive monitor wired in `__init__`: `register_push` schedules alert messages on main thread via `after(0, ...)`; `register_banner` updates status text when panel is closed

**Chat handler** (`hck_gpt/chat_handler.py`)
- Language detected per message (`detect_language`) → `proactive_monitor.set_language(lang)` → `hybrid_engine.process(msg, result, lang)`
- `_LEGACY_ONLY_KEYWORDS` expanded to cover all `_ROUTES` keys (`alerts`, `insights`, `teaser`, `raport`, etc.), prevents Ollama from intercepting InsightsEngine commands

**Response builder** (`hck_gpt/responses/builder.py`)
- Full bilingual rewrite: `_t(lang, pl, en)`, `_pick(lang, pl_pool, en_pool)`, `_followup(key, lang)` helpers
- 20+ handlers updated: CPU, GPU, RAM, health check, temperature, throttle, performance, greeting, thanks, help, small talk, processes, storage, optimization, uptime, power plan, stats, motherboard, service wizard
- Response variety via `random.choice()` pools: 4+4 greetings, 4+4 thanks, 3+3 health intros, 3+3 perf intros
- `_resp_hw_storage()`: skips `remote` drives, caps at 5 drives, uses `all=False` partitions (no network-drive freeze)
- `_resp_processes()`: capped at 128 process iterations

**Intent vocabulary** (`hck_gpt/intents/vocabulary.py`)
- All diagnostic intents enriched with multi-word phrases (`"health check"`, `"system health"`, `"pc health"` etc.), confidence now reaches 1.00 for direct queries
- New `small_talk` intent (low-scoring tokens → Ollama preferred)
- Pattern tuning: diagnostic intents score ≥ 0.60 to route through rule engine

**Intent parser** (`hck_gpt/intents/parser.py`)
- Added `_ascii_fold()`, `_normalize_accents()`, `_ACCENT_MAP` for Polish accent normalization
- Dual scoring: scores against original text AND ASCII-folded version, takes `max()`, fixes "dzieki"→thanks, "wydajnosc"→performance, "specyfikacja"→hw_all
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
- `OllamaClient`: `is_available()`, `list_models()`, `generate()`, stdlib `http.client` only, `try/finally conn.close()` in all three methods
- `HybridEngine` routing: `RULE_THRESHOLD=0.60` → rule engine; `_OLLAMA_PREFERRED_INTENTS={"small_talk","unknown"}` → Ollama first; low-confidence fallback chain
- Temporary unavailability: 60s cooldown after timeout, 30s after empty response (not a full blacklist)
- `_build_system_prompt(lang)`: 4-section prompt, Identity, Rules (9 hard rules: short, no markdown, no invented data), PC Context (`build_llm_context`), Language instruction
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

### Efficiency Tab - Fixes & Per-Core Stats (`ui/components/yourpc_page.py`)
- Fixed C11 bug: `cpu_count(logical=True)=12` was used on 6-core CPU; switched to `cpu_count(logical=False)` → correct physical core count
- Fixed invisible avg text: `fg="#6366f1"` on dark bg → `fg="#a5b4fc"` (light lavender, clearly visible)
- Module-level `_CORE_SESSION` dict tracks min/max/sum/cnt per physical core across refresh ticks
- Core card now shows min / max / avg per core below the bar
- Side-by-side TOP CPU and TOP RAM consumers (separate `consumers_row` frame, both packed left)
- Process rank tracker (`_PROC_SESSION`): rank badge, name, NOW%, session AVG%, time-in-rank duration

### HCK_Labs Globe Icon (`ui/windows/main_window_expanded.py`)
- Replaced filled square with vector globe: circle (sphere outline) + meridian oval + equator line + N/S parallels, drawn with `create_oval` / `create_line`, no image file

### Stability Fixes
- `process_iter()` capped at 128 entries in both `system_context.py` and `responses/builder.py` (prevents UI hang on loaded systems)
- Network drive freeze: `disk_usage()` skips `remote` drives, uses `all=False`, capped at 5
- `None`/`NaN` guard before `session_memory.push_metric()`
- `_auto_summarize()` exceptions swallowed via `_auto_summarize_impl()`, `add_message()` never raises
- Null bytes sanitized in `add_message()`
- Connection leaks fixed: `try/finally conn.close()` in all three `OllamaClient` methods
- Ollama hijack of InsightsEngine commands fixed via expanded `_LEGACY_ONLY_KEYWORDS`

---

## [1.7.2] - 2026-04-21

### Dashboard Nav Buttons - Full Redesign
- New dark-gradient canvas buttons: deep navy `#080b18`→`#101626`, 3px accent stripe on left edge
- Bordeaux/crimson L-corner brackets (`|_` + `_|`) on bottom of each button
- Hover fills button with darkened version of each button's accent colour (72% blend)
- Vector icons drawn programmatically per page (no PNG files): monitor, `!`, bar chart, bolt, fan, flask, book
- Removed "QUICK ACCESS" / "EXPLORE" section labels, more vertical space for buttons
- Button labels updated: "Sensors" → "MONITORING / Centrum", "Live Graphs" → "AllMonitor", "Advanced Dashboard" → "FAN Dashboard, Central"

### Navigation Routing Fixes
- "MONITORING, Centrum" now correctly loads `build_monitoring_alerts_page` (fixed wrong import name)
- "AllMonitor" click opens `My PC, Hardware & Health` overlay + auto-triggers ProInfoTable popup (180ms delay)
- Overlay title for `live_graphs` fixed to show "My PC - Hardware & Health"
- `_launch_hw_table_window_root` helper added for root-anchored popup calls

### HCK_Labs & Guide Pages - Blog Redesign
- HCK_Labs: hero section, 3-col About cards, 6-item features grid, comparison table, build info footer
- Guide: full-width blog with 5 article sections, Quick Tips row, "▶ Guide on program LIVE" placeholder button

### Turbo Boost - Coming Soon State
- Turbo Boost button in main dashboard set to grayed-out state (all colours #374151/muted)
- Hover shows floating tooltip: "Coming soon… Check Optimization Center for features"
- Toggle/launch bindings removed until feature is fully implemented

## [1.7.2] - 2026-04-20

### Optimization & Services - Full Redesign
- New "OPTIMIZATION CENTER" hero header with TURBO BOOST gradient button (amber pulse animation via `math.sin`)
- Rectangular emerald badge showing `1 / 14 active` features count
- TURBO BOOST flashes individual Quick Action button backgrounds green/red for 2.5s on run
- Columns swapped: Features list (with coming-soon rows) on left, Quick Actions on right
- Left column fixed at 280px width; right column expands freely
- AUTO RAM Flush settings persisted to `settings/user_prefs.json`, survives restarts
- Compact RAM flush card: removed live RAM % display, cleaner RUN canvas button (72×28px, bordeaux→emerald gradient)
- RAM monitor daemon auto-restarts on launch if `ram_auto=True` was last saved state

### Font System
- New `utils/fonts.py`, loads Inter font family via Windows GDI32 (`AddFontResourceW`)
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
- Driver data sourced directly from Windows registry, no admin rights required
- Background scan via `threading.Thread`; UI updates on main thread via `after(0, ...)`
- Health score computed from driver ages and startup count; color-coded green/amber/red
- Each driver card: left accent bar, freshness bar (age ratio), status badge (CURRENT / 6+ MONTHS / Xmo OLD), Device Manager shortcut
- Pulsing scan dot animation while scan is in progress; Re-Scan button refreshes all data
- Canvas width auto-bound to parent via `<Configure>`, no horizontal overflow
- Setup Checklist: 6 items, persisted to `data/cache/setup_checklist.json`, animated progress bar
- Sidebar entry "Setup & Drivers" placed after My PC as a simple (no-dropdown) button
- Fixed `yourpc_page.py`: "First Setup & Drivers" button now navigates to `first_setup` (was incorrectly routed to `optimization/wizard`)
- Badge on My PC button shows live checklist completion `X/6 done` loaded from JSON

### hck_GPT Chat - Time Badge
- New `_make_time_badge()` in `panel.py`: inline `tk.Canvas` badge (62×14px) embedded in the chat Text widget via `window_create`
- Badge design: red left/right bars, dark centre, current time in `HH:MM` format (Consolas 7 bold, silver `#94a3b8`)
- Inserted automatically before every `hck_GPT:` message

### Process Library Expansion (`data/process_library.json`)
- Added 8 new entries: `claude.exe`, `datatransfer.exe`, `wmiprvse.exe`, `msmpeng.exe`, `registry`, `hitman.exe`, `hitman2.exe`, `hitman3.exe`

### TOP 5 Dashboard - Process Tooltips
- Imported `ProcessTooltip` + `process_library` in `main_window_expanded.py`
- `<Enter>` / `<Leave>` bindings on both name label and row frame in user and system TOP 5 panels
- `proc_name` stored in widget_data, updated each render cycle, tooltip always reflects current process

---

## [1.7.1] - 2026-04-10

### Code Cleanup
- `core/monitor.py`, removed redundant inline comments, unused `import platform`, `### HCK_Labs` header
- `core/analyzer.py`, removed `### HCK_Labs` header
- `core/hardware_sensors.py`, rephrased GPU clock comment, removed "Note:" prefix
- `ui/windows/main_window_expanded.py`, deleted dead `_build_yourpc_page_OLD_REMOVED` (~130 lines), stale module-moved comment, "innovative" docstring wording

### Versioning & Packaging
- Bumped version to `1.7.1` across `setup.py`, `startup.py`, `main_window.py`, `main_window_expanded.py`, `README.md`
- `requirements.txt`, removed `tkinter` and `tk>=0.1.0` (both stdlib, not pip-installable)
- Release date updated to `2026-04-10`

### Test Coverage
- `tests/test_monitor.py`, rewritten: 7 test cases; fixed broken `monitor.read()` call → `read_snapshot()`; covers snapshot keys, value types, process parsing, CPU/RAM sort, n-limit, cache hit, background thread
- `tests/test_analyzer.py`, rewritten: 7 test cases; logger injected via `COMPONENTS` mock; covers averages, spike detection, empty buffer, old-sample filtering, threshold edge cases
- `tests/test_avg_calculator.py`, rewritten: 4 test cases; uses `tempfile` + patched `HOURLY` path; covers missing file, single-day avg, multi-day split, result key presence

### UI - TOP 5 Process Panels
- Row height `22px → 36px`; layout changed from single-line to 2-line: name on top, CPU+RAM bars below
- Labels `C` / `R` replaced with `CPU` (blue) / `RAM` (amber) with accent color matching bar fill
- Max visible process name length `14 → 20` characters
- Thin vertical divider between CPU and RAM halves

### AnimatedBar - Reusable Animated Progress Bar
- New class `AnimatedBar` in `ui/components/led_bars.py`
- Ease-out interpolation: `EASE = 0.18`, `~60fps` via `after(16ms)`, snaps at `< 0.4%` delta
- API: `bar.bg_frame` for layout placement, `bar.set_target(pct)` to animate
- Applied to: TOP 5 user process rows, TOP 5 system process rows, Session Averages (CPU/GPU/RAM)

### Dashboard Chart - Bug Fixes & Colors
- Fixed blank chart on startup: `<Configure>` binding detects when canvas has real dimensions and triggers first draw
- Added `_schedule_chart_update()` with `after_cancel()`, prevents duplicate update loops
- Filter buttons `LIVE / 1H / 4H / 1D / 1W / 1M` now trigger immediate redraw (`after(50ms)`) instead of waiting for 2s timer
- Fixed bar colors: CPU `#3b82f6`, RAM `#fbbf24`, GPU `#10b981` (replaced dark/brown placeholders)
- Placeholder text `"Collecting data..."` shown while buffer is empty instead of silent no-op

---

## [1.7.0] - 2026-03-XX

### hck_GPT - Process Knowledge Base
- New file `hck_gpt/process_library.py`, static knowledge base with definitions for 80+ common Windows processes and applications
- Each entry includes: publisher/author, short description, security classification, energy profile, expected CPU/RAM usage ranges, and contextual notes (e.g. "Heavy load during library updates" for Epic Games Launcher, Steam)
- Categories covered: gaming launchers, browsers, development tools, communication apps, Windows system processes, media players, security software
- Used by hck_GPT tooltip system: hovering a process name in any TOP 5 panel shows a rich popup with the above data
- Graceful fallback: unknown processes display raw psutil data without crashing

---

## [1.6.8] - 2026-02-17

### hck_GPT Intelligence System
Full local intelligence layer, no external AI, all rule-based logic on Stats Engine data.

**New modules** (`hck_gpt/`):
- `insights.py`, `InsightsEngine` singleton: habit tracking, anomaly awareness, personalized teasers
- `report_window.py`, "Today Report" Toplevel window with canvas chart, colored sections, process breakdown

**InsightsEngine capabilities:**
- `get_greeting()`, time-of-day + yesterday's summary + recurring app teaser (cached 30min)
- `get_current_insight()`, real-time spike alerts, gaming/browser detection, session milestones (dedup: won't repeat same message)
- `get_habit_summary()`, top 5 apps, browser/game/dev highlights, weekly CPU trend, recurring patterns list
- `get_health_check()`, quick diagnostics: session uptime, current load, today's averages, alert count, data collection status
- `get_anomaly_report()`, 24h events grouped by severity with timestamps + summary insight
- `get_teaser()`, 7-day recurring pattern detection, 15+ template variants per category (Gaming, Browser, Dev, Media, etc.)
- `get_banner_status()`, compact one-liner with session uptime fallback
- `_detect_recurring_patterns()`, finds apps used on 50%+ of last 7 days (>5% CPU or >100MB RAM)
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
- Scoped mousewheel binding (only when hovering report window, no leak to main app)

### HCK Stats Engine v2 - SQLite Long-Term Storage
Replaced empty CSV aggregation files with a proper SQLite pipeline.

**New modules** (`hck_stats_engine/`):
- `constants.py`, retention config (7d minute, 90d hourly, forever daily+)
- `db_manager.py`, WAL-mode SQLite, thread-local connections, auto-schema
- `aggregator.py`, minute/hourly/daily/weekly/monthly aggregation + CSV pruning
- `process_aggregator.py`, per-process CPU/RAM accumulator (in-memory dict → hourly/daily flush to SQLite)
- `query_api.py`, range queries with automatic granularity selection
- `events.py`, spike/anomaly detection with rate-limiting, severity levels

**Data pipeline:**
- `accumulate_second()`, lightweight dict update every 1s
- `on_minute_tick()`, INSERT into `minute_stats` every 60s
- Hourly/daily boundary detection → aggregation + pruning
- `flush_on_shutdown()`, graceful save on exit

**Stability guarantees:**
- Every call wrapped in try/except, scheduler never crashes
- Writes only on scheduler thread, UI reads via separate connection
- WAL mode, concurrent read/write without locks
- Atomic transactions, crash mid-aggregation → rollback
- Graceful degradation, SQLite failure → app runs on CSV as before
- Zero new dependencies (sqlite3 in stdlib)

**Integration:** `scheduler.py` (~15 lines), `startup.py` (~10 lines), `__init__.py` (imports)

### MONITORING & ALERTS - Time-Travel Statistics Center
- Temperature area chart: 1D / 3D / 1W / 1M scale, spike detection (mean + 1.5*std), yellow glow regions, hover tooltips
- Voltage/Load multi-line chart: CPU (blue) / RAM (green) / GPU (orange), anomaly highlighting
- Stats panels per metric: Today AVG, Lifetime AVG, Max Safe, Current, Today MAX, Spikes count
- AI learning status badges (green/yellow) with "PC Workman learns your patterns" messaging
- Events log section pulling from SQLite `events` table
- Auto-refresh every 30s with `winfo_exists()` guard
- New file: `ui/pages/monitoring_alerts.py` (~520 lines)

### Overlay CPU/RAM/GPU - External Desktop Widget
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
- `_update_hardware_cards` and `_update_top5_processes` now guarded by `current_view == "dashboard"`, eliminates "bad window path name" errors when on other pages
- `winfo_exists()` checks added to: `_update_hardware_card`, `_render_expanded_user_processes`, `_render_expanded_system_processes`, `_update_session_bar`, `_update_live_metrics`, `_draw_sparkline`
- Routing IDs updated: `temperature`, `voltage`, `alerts` (replaced stale `realtime`, `processes`)
- Sidebar subitem renamed: "Events Log" → "Centrum & Alerts"

### Performance Optimization - Zero-Lag Dashboard
Heavy profiling and iterative optimization to eliminate all UI stutter.

**Background-threaded monitoring:**
- `Monitor.start_background_collection()`, `psutil.process_iter()` moved off GUI thread to a daemon thread
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
- Removed dead `_animate_button_shimmer()` (was 30 FPS / 33ms, ~800 canvas items redrawn per frame)

**Realtime chart rewrite:**
- Replaced PhotoImage pixel-by-pixel rendering (70,000 Python iterations/frame) with canvas rectangle pool
- Items created once, only `canvas.coords()` updated per tick, near-zero overhead

### Dashboard Chart - Historical Data Integration
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

## [v1.5.7] - 2025-12-17
### Architectural Evolution - Dual-Mode System & UX Refinement Phase
**Summary:**
Transition from single-window architecture to dual-mode system. Minimal mode becomes the primary interface, while expanded mode serves power users. Complete navigation redesign with animated RGB gradients, professional splash screen, and full project reorganization. Foundation laid for next-generation "My PC" UX redesign.

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
- Full system management tools
- Hardware health monitoring
- Service optimization wizards
- Historical data analytics

**Design Philosophy:**
- Minimal mode for "always there" monitoring
- Expanded mode for "when you need control"
- Instant switching between modes
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
- Static gradient (drawn once, no animation, optimized in v1.6.8)

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

### 📐 UX Refinement Phase - "My PC" Redesign Preparation
**Design specification created:**
- Document: `docs/MY_PC_UX_REDESIGN_MASTERPIECE.md`
- 500+ lines of detailed UX specifications
- Principal UX architect level design thinking

**Key Innovation, Minesweeper-Style Disk Health:**
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
- Verified all module connections with full testing

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
- `docs/MY_PC_UX_REDESIGN_MASTERPIECE.md` - UX specification
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

## [v1.5.0] - 2025-12-07
### Major UI/UX Overhaul - Sprint 3: Modern Dashboard & Hardware Monitoring
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

## [v1.4.0] - 2025-12-06
### Major Update - System Tray, Enhanced Process Tracking & Interactive UI
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

## [v1.0.6] - 2025-11-08  
### Major Update - Core System and UI Prototype  
**Summary:**  
Full reconstruction of the project architecture. Transitioned from simulated data to real-time monitoring using `psutil`. Implemented the first functional UI with live charts and process analytics.

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
- Added reliable startup and shutdown handling.  
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

## [v1.0.4] - 2025-10-31
### Core , Stats Engine, UI - critical error (6)
**Summary**
- Expanded liblaries for Core,Engine
- Create 3_way `QICKlogic` for Engine (helpfuly but bugs)
- Prepare `demo_UI`
- Connecting fake-data transfer from `Core`, `Engine` to `demo_ui` and basic values ​​in `monitor.py`
*main objective, place real data*
---
## [v1.0.1] - 2025-10-31
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
## [v1.0.0] - 2025-10-27
### Alpha Demo - “Diagnostics Foundation” - critical error (3)
- Implemented registry system (`import_core`).
- Created Tkinter-based UI showing mock CPU/GPU/RAM usage.
- Added logging and average calculator modules.
- Packaged project with `setup.py`.
- Verified architecture for HCK_Labs integration.

---
