# hck_gpt/memory/user_knowledge.py
"""
User Knowledge Base — SQLite-backed persistent store.

Tracks across ALL sessions:
  - hardware_profile  : CPU model, GPU, RAM, motherboard, OS, storage
  - usage_patterns    : avg loads, peak hours, top apps, detected use-case
  - user_facts        : things the user stated or we inferred
                        ("pc_use=gaming", "preferred_lang=pl", ...)
  - conversation_log  : message history (last 500 messages, pruned weekly)

The DB lives in the user's AppData so it survives reinstalls of the app
and is never shipped inside the exe.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

# ── DB path (AppData/Local) ───────────────────────────────────────────────────
_DB_DIR  = os.path.join(os.path.expanduser("~"),
                        "AppData", "Local", "PC_Workman_HCK")
DB_PATH  = os.path.join(_DB_DIR, "user_knowledge.db")


# ── Schema ────────────────────────────────────────────────────────────────────
_SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS hardware_profile (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL,
    updated REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_patterns (
    metric  TEXT PRIMARY KEY,
    value   TEXT NOT NULL,
    updated REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS user_facts (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT 'detected',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT    NOT NULL,
    timestamp  REAL    NOT NULL,
    role       TEXT    NOT NULL,
    message    TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conv_ts ON conversation_log(timestamp);
"""


# ── Main class ────────────────────────────────────────────────────────────────

class UserKnowledge:
    """
    Persistent knowledge about the user's PC and behaviour.
    Thread-safe via per-call connections + WAL mode.
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        cx = sqlite3.connect(self.db_path, timeout=5,
                             check_same_thread=False)
        cx.row_factory = sqlite3.Row
        return cx

    def _init_db(self) -> None:
        with self._conn() as cx:
            cx.executescript(_SCHEMA)

    # ── Hardware profile ──────────────────────────────────────────────────────

    def set_hardware(self, key: str, value: Any) -> None:
        with self._conn() as cx:
            cx.execute(
                "INSERT OR REPLACE INTO hardware_profile (key, value, updated) "
                "VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time())
            )

    def get_hardware(self, key: str, default: Any = None) -> Any:
        with self._conn() as cx:
            row = cx.execute(
                "SELECT value FROM hardware_profile WHERE key = ?", (key,)
            ).fetchone()
        return json.loads(row["value"]) if row else default

    def get_all_hardware(self) -> Dict[str, Any]:
        with self._conn() as cx:
            rows = cx.execute(
                "SELECT key, value FROM hardware_profile"
            ).fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    def hardware_is_fresh(self, max_age_hours: float = 24) -> bool:
        """True if hardware was scanned within max_age_hours."""
        with self._conn() as cx:
            row = cx.execute(
                "SELECT MAX(updated) AS t FROM hardware_profile"
            ).fetchone()
        if not row or not row["t"]:
            return False
        return (time.time() - row["t"]) < max_age_hours * 3600

    # ── Usage patterns ────────────────────────────────────────────────────────

    def set_pattern(self, metric: str, value: Any) -> None:
        with self._conn() as cx:
            cx.execute(
                "INSERT OR REPLACE INTO usage_patterns (metric, value, updated) "
                "VALUES (?, ?, ?)",
                (metric, json.dumps(value), time.time())
            )

    def get_pattern(self, metric: str, default: Any = None) -> Any:
        with self._conn() as cx:
            row = cx.execute(
                "SELECT value FROM usage_patterns WHERE metric = ?", (metric,)
            ).fetchone()
        return json.loads(row["value"]) if row else default

    def get_all_patterns(self) -> Dict[str, Any]:
        with self._conn() as cx:
            rows = cx.execute(
                "SELECT metric, value FROM usage_patterns"
            ).fetchall()
        return {r["metric"]: json.loads(r["value"]) for r in rows}

    # ── User facts ────────────────────────────────────────────────────────────

    def set_fact(self, key: str, value: str,
                 source: str = "detected",
                 confidence: float = 1.0) -> None:
        with self._conn() as cx:
            cx.execute(
                "INSERT OR REPLACE INTO user_facts "
                "(key, value, source, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, value, source, confidence, time.time())
            )

    def get_fact(self, key: str, default: str = "") -> str:
        with self._conn() as cx:
            row = cx.execute(
                "SELECT value FROM user_facts WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def get_all_facts(self) -> Dict[str, str]:
        with self._conn() as cx:
            rows = cx.execute(
                "SELECT key, value FROM user_facts ORDER BY created_at"
            ).fetchall()
        return {r["key"]: r["value"] for r in rows}

    def delete_fact(self, key: str) -> None:
        with self._conn() as cx:
            cx.execute("DELETE FROM user_facts WHERE key = ?", (key,))

    # ── Conversation log ──────────────────────────────────────────────────────

    def log_message(self, session_id: str, role: str, message: str) -> None:
        with self._conn() as cx:
            cx.execute(
                "INSERT INTO conversation_log "
                "(session_id, timestamp, role, message) VALUES (?, ?, ?, ?)",
                (session_id, time.time(), role, message)
            )

    def get_recent_log(self, n: int = 20) -> List[Tuple[str, str, float]]:
        """Returns list of (role, message, timestamp) newest-last."""
        with self._conn() as cx:
            rows = cx.execute(
                "SELECT role, message, timestamp FROM conversation_log "
                "ORDER BY timestamp DESC LIMIT ?", (n,)
            ).fetchall()
        return [(r["role"], r["message"], r["timestamp"])
                for r in reversed(rows)]

    def prune_old_logs(self, keep_days: int = 30) -> None:
        cutoff = time.time() - keep_days * 86400
        with self._conn() as cx:
            cx.execute(
                "DELETE FROM conversation_log WHERE timestamp < ?", (cutoff,)
            )

    # ── Full reset ────────────────────────────────────────────────────────────

    def reset_all(self) -> None:
        """
        Delete every row in all four tables and VACUUM the file.
        Schema is preserved — tables still exist after the call.
        """
        with self._conn() as cx:
            cx.execute("DELETE FROM hardware_profile")
            cx.execute("DELETE FROM usage_patterns")
            cx.execute("DELETE FROM user_facts")
            cx.execute("DELETE FROM conversation_log")
        # VACUUM outside the transaction (WAL mode requires it)
        conn = self._conn()
        try:
            conn.execute("VACUUM")
        finally:
            conn.close()

    # ── Knowledge summary (for chatbot context) ───────────────────────────────

    def build_knowledge_summary(self) -> str:
        """
        Returns a concise human-readable summary of known PC data.
        Used as context prefix for the chatbot response builder.
        """
        hw     = self.get_all_hardware()
        facts  = self.get_all_facts()
        lines: List[str] = []

        _HW_LABELS = [
            ("cpu_model",       "CPU"),
            ("cpu_cores",       "Cores (physical)"),
            ("cpu_threads",     "Threads"),
            ("cpu_boost_ghz",   "CPU Boost"),
            ("gpu_model",       "GPU"),
            ("gpu_vram_gb",     "VRAM"),
            ("ram_total_gb",    "RAM"),
            ("ram_speed_mhz",   "RAM Speed"),
            ("motherboard_model", "Motherboard"),
            ("storage_summary", "Storage"),
            ("os_version",      "OS"),
        ]
        if hw:
            lines.append("Hardware:")
            for key, label in _HW_LABELS:
                if key in hw and hw[key] is not None:
                    lines.append(f"  {label}: {hw[key]}")

        if facts:
            lines.append("User facts:")
            for k, v in list(facts.items())[:8]:
                lines.append(f"  {k}: {v}")

        patterns = self.get_all_patterns()
        if patterns:
            lines.append("Usage patterns:")
            for k, v in list(patterns.items())[:5]:
                lines.append(f"  {k}: {v}")

        return "\n".join(lines) if lines else "(knowledge base empty — run a hardware scan)"


# ── Singleton ─────────────────────────────────────────────────────────────────
user_knowledge = UserKnowledge()
