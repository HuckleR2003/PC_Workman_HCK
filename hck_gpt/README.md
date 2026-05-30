# hck_GPT

AI diagnostic assistant embedded inside PC_Workman. Answers natural language questions about your PC in Polish and English using a hybrid rule+LLM engine.

---

## Architecture

```
hck_gpt/
├── chat_handler.py          # Entry point — quick aliases, routing, help
├── panel.py                 # Chat UI panel, nav links, session display
├── insights.py              # InsightsEngine — habits, anomalies, teasers
├── process_library.py       # Process lookup from data/process_library.json
├── service_setup_wizard.py  # Windows service optimization wizard
├── services_manager.py      # Windows service stop/start manager
├── tooltip.py               # Process tooltip widget
│
├── intents/
│   ├── vocabulary.py        # 76 intents, PL+EN trigger patterns
│   ├── parser.py            # Intent parsing + confidence scoring
│   ├── lang_detect.py       # PL/EN auto-detection
│   └── ml_classifier.py     # Naive Bayes fallback classifier
│
├── engine/
│   └── hybrid_engine.py     # Routes intent → rule handler or Ollama LLM
│
├── responses/
│   └── builder.py           # All _resp_* handlers + MEGA features
│
├── context/
│   ├── system_context.py    # Builds PC context string for LLM
│   └── hardware_scanner.py  # WMI scan: CPU, GPU, RAM, disk, mobo
│
├── memory/
│   ├── session_memory.py    # In-session event log, spike tracker
│   ├── user_knowledge.py    # SQLite persistent user profile (AppData)
│   └── proactive_monitor.py # Background alerts (CPU/RAM/disk/uptime)
│
└── data/
    ├── live_sensors.py      # Real-time CPU/GPU/RAM snapshot
    └── metrics_store.py     # daily_summary() queries from hck_stats.db
```

---

## Intent Coverage (76 total)

| Category | Intents |
|---|---|
| Hardware | `hw_cpu`, `hw_gpu`, `hw_ram`, `hw_storage`, `hw_all` |
| Temperature | `temperature`, `throttle_check`, `gpu_temp_why` |
| Performance | `performance`, `stats`, `perf_change`, `session_compare`, `pc_changes` |
| Why | `why_slow`, `ram_why_high`, `processes`, `disk_usage_why` |
| Diagnostics | `health_check`, `virus_check`, `disk_health`, `uptime`, `voltage_check` |
| Gaming | `gaming_session`, `weekly_trends`, `fps_degradation`, `game_hardware_stress` |
| New (1.7.5) | `fan_noise_history`, `driver_status`, `gaming_vs_work_time`, `process_identity`, `stale_apps`, `app_behavior_change`, `startup_slowdown`, `temp_comparison`, `crash_context`, `battery_drain_rate`, `power_after_restart` |
| Optimization | `optimization`, `fan_speed`, `power_mode` |
| Security | `process_info`, `security_check` |
| Misc | `help`, `small_talk`, `unknown` + 15 others |

All intents have Polish and English trigger patterns. Language is auto-detected per message.

---

## Key Features

### Hybrid Engine
- **Rule path**: known intents → deterministic `_resp_*` handler in `builder.py`
- **LLM path**: open-ended or low-confidence → Ollama (local, no cloud)
- Per-intent temperature and system prompt hint tuning

### Context Time-Windowing
Each intent gets a history window matched to its nature:

```python
"hw_cpu": 5,          # 5 minutes — live query
"health_check": 30,   # 30 minutes — recent session
"temp_comparison": 10080,  # 7 days — historical trend
```

`build_llm_context_windowed(lang, minutes)` builds the LLM context scoped to that window — tight windows strip stale patterns, wide windows append daily metric history.

### No-AI-Slop Fallback
`_no_data(intent, lang, what_missing)` — returns a structured "data unavailable" response instead of fabricating an answer. Used when sensor data, history, or process lists are empty.

### Time-Travel Debugging
`_get_historical_comparison(metric, days, lang)` — fetches live sensor value and compares to N-day average from `metrics_store.daily_summary()`. Returns formatted delta with direction arrow.

### Micro-Benchmarking
`_trigger_micro_benchmark(bench_type)` — fires a background thread:
- `cpu_single`: 1M sqrt operations, measures ops/sec
- `disk_seq`: 32 MB sequential write+read, measures MB/s

Results stored in `session_memory` under `micro_bench` key.

### Process Library
`data/process_library.json` — **241 processes** with vendor, category, safety rating, typical CPU/RAM, and description. Used by `process_identity` and process tooltip widget.

### Session Memory
Tracks per-session events, spikes, and response data. Later handlers can reference what was discussed earlier in the same session (`discussed_this_session()`, `get_response_data(intent)`).

### Proactive Monitor
Background thread watching CPU, RAM, disk, and uptime. Fires non-intrusive alerts into the chat panel when thresholds are exceeded.

---

## Usage

```python
from hck_gpt.chat_handler import ChatHandler

handler = ChatHandler()
responses = handler.process_message("dlaczego mój komputer jest wolny?")
# returns list of formatted response strings (bilingual)
```

Quick aliases available in `chat_handler.py` — short Polish keywords map directly to intents without going through the parser (e.g. `sterowniki` → `driver_status`, `bateria` → `battery_drain_rate`).

---

## Requirements

- Python 3.9+
- `psutil` — process and sensor data
- `wmi` — hardware scanner (Windows only)
- `ollama` — optional, for LLM fallback path (local install required)
- `sqlite3` — built-in, used by `metrics_store` and `user_knowledge`

---

Part of PC Workman HCK — [github.com/HuckleR2003/PC_Workman_HCK](https://github.com/HuckleR2003/PC_Workman_HCK)  
Developed by Marcin "HCK" Firmuga
