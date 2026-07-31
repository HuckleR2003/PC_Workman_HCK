# hck_GPT

**v2.1.0** · Part of [PC Workman HCK](https://github.com/HuckleR2003/PC_Workman_HCK)

AI diagnostic assistant for Windows system monitoring. Answers natural language questions about your PC in Polish and English using real hardware data. No cloud. No API key.

---

## What it does

You ask. It checks your actual hardware. It answers.

```
"Why is my PC slow right now?"
"Is cs2.exe a virus or a normal process?"
"Which game pushes my GPU the hardest?"
"RAM na 91% - co powinienem zamknąć?"
```

109 built-in intents covering hardware diagnostics, performance analysis, process identity,
driver status, gaming analytics, battery, startup programs, and system health.

---

## Architecture

```
hck_gpt/
├── engine/
│   └── hybrid_engine.py     # Routes messages: rule engine first, Ollama LLM fallback
├── intents/
│   ├── parser.py            # Intent parser with Polish diacritic normalization
│   ├── semantic_rules.py    # Conservative PL/EN relationship and OOD rules
│   ├── vocabulary.py        # 109 intents, PL+EN patterns, confidence scoring
│   └── lang_detect.py       # Auto-detects Polish vs English per message
├── responses/
│   ├── builder.py           # Small dispatch facade over category mixins
│   ├── r_*.py               # 109 bilingual, intent-specific handlers
│   └── flows.py             # Guided optimization, cooling, desktop and upgrade flows
├── memory/
│   ├── session_memory.py    # References, bounded diagnostic frame, advice state
│   ├── proactive_policy.py  # Quiet/balanced/companion value scoring
│   ├── game_session.py      # Bounded measurements, RTSS-only FPS evidence
│   ├── proactive_monitor.py # One daemon for alerts, check-ins and recaps
│   └── user_knowledge.py    # SQLite user profile (hardware, usage patterns)
├── context/
│   ├── system_context.py    # Live snapshot: processes, temps, averages
│   └── hardware_scanner.py  # WMI scan: CPU model, GPU, VRAM, mobo, RAM speed
├── data/
│   ├── live_sensors.py      # LibreHardwareMonitor bridge
│   └── metrics_store.py     # DeepMonitor 5-min snapshots
├── chat_handler.py          # Message routing + quick aliases
├── panel.py                 # Tkinter UI: Bordeaux Noir panel, TIP/HOT strips
└── insights.py              # Habit tracking, anomaly detection, teasers
```

---

## How the hybrid engine works

Every message hits the **intent parser** first. Known intents (109 total) go to the **rule engine**. This path is deterministic and needs no GPU.

The parser combines exact vocabulary phrases, keyword scoring, the local
Naive Bayes classifier and conservative semantic rules. Exact existing phrases
keep priority. Semantic rules resolve relationships such as process + close +
safe or temperature + comparison. Explicit non-PC tasks route to `unknown`.

Low-confidence or open-ended messages get routed to **Ollama** (local LLM). The engine injects a 6-section system context into the prompt: live CPU/RAM/GPU, today's averages, top processes, temperatures, hardware profile, and conversation history.

The session memory also keeps one expiring diagnostic frame. It records the
current subject, symptom, confirmed details, missing evidence, advice state and
before/after verification. Short replies such as "in game", "after 20 minutes"
and "more like stutter" continue the same diagnosis.

Proactive messages use a value score, a 3-per-30-minute budget and duplicate
suppression. Quiet mode keeps critical safety messages. Balanced mode adds
useful changes. Companion mode may add one game check-in and a measured recap.
FPS appears only when RTSS provides a real reading.

Ollama unavailable? Deterministic handlers remain available. A failed local
model call enters a short cooldown instead of blocking the chat.

```
User message
     │
     ▼
Intent parser  (confidence 0.0–1.0)
     │
     ├─ >= 0.65 ──► Rule engine handler ──► bilingual response + live hardware data
     │
     └─ < 0.65  ──► Ollama LLM (local, port 11434)
                     + 6-section system context injected
                     │
                     └─ unavailable ──► structured fallback
```

---

## Intent categories

| Category | Example questions | Count |
|---|---|---|
| Hardware info | "What GPU do I have?", "How much RAM?" | 6 |
| Diagnostics | "Is my PC healthy?", "Check temperatures" | 4 |
| Performance | "Why is it slow?", "Compare today vs yesterday" | 6 |
| Process identity | "Is svchost.exe a virus?" | 3 |
| Gaming | "Can I run Cyberpunk?", "Which game stresses hardware most?" | 5 |
| Startup / drivers | "What starts with Windows?", "Are drivers updated?" | 4 |
| Resource analysis | "Why is RAM high?", "What's the top memory hog?" | 6 |
| Time-travel | "What changed since last week?", "Crash context?" | 7 |
| Battery / power | "How fast is battery draining?" | 4 |
| Small talk | Greetings, thanks, follow-up questions | 4 |
| + more | optimization, security, disk, network, context, guided repair | 49 |

---

## Proactive monitor

Background daemon that watches your system and pushes alerts without being asked:

- CPU sustained >85%
- RAM critical >93% → HOT strip (red, not chat spam)
- CPU/GPU temperature spikes
- Disk <4 GB free on the system drive
- Session uptime >8h reminder
- New heavy process detected
- Calm-system context tips that can name a real app or game with current metrics

Alerts go to the HOT strip (red) or TIP strip (yellow) depending on severity.
RAM critical never appears as a chat message — only in the dedicated HOT indicator.

---

## Bilingual design

Language is detected per message. A one-word follow-up such as `cpu` keeps the
current conversation language instead of flipping languages.

One expiring conversation frame keeps a diagnosis attached to its goal. Short
answers can supply context, timing, symptom type, frequency, scope or a recent
change without restarting the parser. Corrections keep a bounded revision
record. Missing questions are selected by the lowest attempt count, so the
assistant does not keep repeating one broad prompt while another useful detail
is still unanswered.

Polish diacritic normalization via ASCII-fold dual scoring:
`"dzieki"` matches `"dzięki"`, `"wydajnosc"` matches `"wydajność"`.

Release routing checks:

```bash
python -B scripts/audit_hck_gpt.py
python -B scripts/audit_hck_gpt_human_queries.py
python -B -m unittest discover tests
```

---

## Dependencies

hck_GPT is designed as part of PC Workman HCK and uses its data pipeline:

| Dependency | Used for |
|---|---|
| `psutil` | Live process list, CPU/RAM/disk |
| `pywin32` (WMI) | CPU model, GPU name, VRAM, mobo, RAM speed |
| `sqlite3` stdlib | User knowledge base, historical stats |
| `tkinter` stdlib | Chat panel UI |
| `requests` optional | Ollama LLM API (local) |

Standalone extraction as a pip-installable library is planned for a future milestone.

---

## Version history

| Version | What changed |
|---|---|
| **2.1.0** | HOT strip for RAM alerts (no chat spam), tip_green advisory background, welcome_bg table styling, register_hot/clear callbacks, UZYTKOWNIK action tracking |
| 2.0.4 | Wave 2: 6 new intents (game_can_run, upgrade_feasibility, top_resource_hog, daily_ram_usage, battery_estimate, gaming_ram_usage). 82 intents total |
| 2.0.0 | Wave 1: 13 community-requested intents, Context Time-Windowing, No-AI-Slop fallback, Time-Travel Debugging, Micro-Benchmarking |
| 1.7.x | DeepMonitor integration, language sync, conversation flow, process library 373 entries |
| 1.0.0 | Initial: Hybrid Engine, 63 intents, Bordeaux Noir panel, proactive monitor, session memory |

---

## Part of PC Workman HCK

hck_GPT is the AI brain inside [PC Workman HCK](https://github.com/HuckleR2003/PC_Workman_HCK) — a real-time Windows system monitor with 2.5D hardware map, DeepMonitor sensor table, startup/services manager, and time-travel diagnostics.

**Marcin "HCK" Firmuga** · [pcworkman.dev](https://pcworkman.dev) · [GitHub](https://github.com/HuckleR2003) · [LinkedIn](https://linkedin.com/in/marcinfirmuga) · MIT License
