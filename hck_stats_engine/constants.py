"""
HCK Stats Engine v2 - Constants and Configuration
Central configuration for retention periods, thresholds, and paths
"""

import os

# ============================================================
# PATHS
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
DB_FILENAME = "hck_stats.db"
DB_PATH = os.path.join(LOGS_DIR, DB_FILENAME)

# ============================================================
# RETENTION PERIODS (in seconds)
# ============================================================
RETENTION_RAW_CSV = 24 * 3600          # 24 hours - raw_usage.csv pruning
RETENTION_MINUTES = 7 * 24 * 3600      # 7 days - minute_stats
RETENTION_HOURLY = 90 * 24 * 3600      # 90 days - hourly_stats
RETENTION_PROCESS_HOURLY = 90 * 24 * 3600  # 90 days - process_hourly_stats
# daily, weekly, monthly: kept forever (no pruning)

# ============================================================
# AGGREGATION
# ============================================================
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
SECONDS_PER_WEEK = 7 * 86400

# ============================================================
# SPIKE DETECTION THRESHOLDS (percentage points above baseline)
# ============================================================
SPIKE_THRESHOLD_CPU = 40.0
SPIKE_THRESHOLD_RAM = 20.0
SPIKE_THRESHOLD_GPU = 50.0
SPIKE_THRESHOLD_TEMP = 15.0    # degrees above baseline
SPIKE_COOLDOWN = 300           # seconds between duplicate events per metric
SPIKE_BASELINE_WINDOW = 300    # 5 minutes baseline for comparison

# ============================================================
# PRUNING
# ============================================================
PRUNING_INTERVAL = 3600        # Run pruning once per hour

# ============================================================
# SCHEMA VERSION
# ============================================================
SCHEMA_VERSION = 1
