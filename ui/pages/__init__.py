# ui/pages/__init__.py
"""
PC Workman - Pages Module
Profesjonalna struktura zakładek aplikacji

Struktura:
    pages/
    ├── __init__.py
    ├── base_page.py          # Bazowa klasa dla wszystkich stron
    ├── fan_control/          # Zakładki Fan Control
    │   ├── __init__.py
    │   ├── dashboard.py      # Fan Dashboard
    │   ├── hardware_info.py  # FANS - Hardware Info
    │   └── usage_stats.py    # Usage Statistics
    ├── my_pc/                # Zakładki My PC
    │   ├── __init__.py
    │   ├── central.py
    │   ├── efficiency.py
    │   ├── sensors.py
    │   └── health.py
    ├── monitoring/           # Zakładki Monitoring
    ├── optimization/         # Zakładki Optimization
    └── statistics/           # Zakładki Statistics
"""
