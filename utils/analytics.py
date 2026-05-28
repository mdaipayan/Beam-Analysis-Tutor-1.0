"""
utils/analytics.py
==================
Lightweight SQLite logger for BeamEdu research data.

Captures the quantitative dataset needed for the CAEE paper:
  • Pre / post quiz scores (learning gain — the primary dependent variable)
  • Per-question quiz attempts (item analysis)
  • Interaction events (which beam types / loads students explored, time-on-task)

All logging is silent and fault-tolerant — a logging failure must never break
the student-facing app, so every DB call is wrapped in try/except.

Database file: data/responses.db  (created automatically on first use)

Privacy note for ethics approval
---------------------------------
Only an anonymised 8-char session ID is stored — no names, emails, or PII.
Export to CSV for analysis via export_csv().
"""

from __future__ import annotations

import os
import sqlite3
import datetime
from contextlib import contextmanager
from typing import Optional

import pandas as pd

_DB_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_DB_PATH = os.path.join(_DB_DIR, "responses.db")


# ──────────────────────────────────────────────
#  Schema
# ──────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS quiz_scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  TEXT    NOT NULL,
    phase       TEXT    NOT NULL,           -- 'pre' or 'post'
    score       REAL    NOT NULL,           -- percentage 0-100
    n_questions INTEGER NOT NULL,
    timestamp   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  TEXT    NOT NULL,
    phase       TEXT    NOT NULL,
    question_id TEXT    NOT NULL,
    correct     INTEGER NOT NULL,           -- 1 = correct, 0 = wrong
    timestamp   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,           -- e.g. 'beam_solved', 'page_view'
    detail      TEXT,                       -- JSON / free text
    timestamp   TEXT    NOT NULL
);
"""


@contextmanager
def _connect():
    """Context-managed SQLite connection; ensures the data dir + schema exist."""
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ──────────────────────────────────────────────
#  Logging functions (fault-tolerant)
# ──────────────────────────────────────────────

def log_quiz_score(student_id: str, phase: str, score: float, n_questions: int) -> None:
    """Record an overall pre/post quiz score."""
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO quiz_scores (student_id, phase, score, n_questions, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (student_id, phase, float(score), int(n_questions), _now()),
            )
    except Exception:
        pass


def log_quiz_item(student_id: str, phase: str, question_id: str, correct: bool) -> None:
    """Record a single question result for item analysis."""
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO quiz_items (student_id, phase, question_id, correct, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (student_id, phase, question_id, int(bool(correct)), _now()),
            )
    except Exception:
        pass


def log_event(student_id: str, event_type: str, detail: str = "") -> None:
    """Record a generic interaction event (page view, beam solved, etc.)."""
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO events (student_id, event_type, detail, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (student_id, event_type, detail, _now()),
            )
    except Exception:
        pass


# ──────────────────────────────────────────────
#  Researcher export / summary
# ──────────────────────────────────────────────

def export_csv(table: str = "quiz_scores") -> Optional[bytes]:
    """
    Return the requested table as CSV bytes (for st.download_button).
    table ∈ {'quiz_scores', 'quiz_items', 'events'}.
    Returns None on error or if the table is empty.
    """
    try:
        with _connect() as conn:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        if df.empty:
            return None
        return df.to_csv(index=False).encode("utf-8")
    except Exception:
        return None


def learning_gain_summary() -> Optional[pd.DataFrame]:
    """
    Compute per-student learning gain (post − pre) — the headline CAEE metric.
    Returns a DataFrame with columns: student_id, pre, post, gain.
    """
    try:
        with _connect() as conn:
            df = pd.read_sql_query(
                "SELECT student_id, phase, score FROM quiz_scores", conn
            )
        if df.empty:
            return None
        pivot = df.pivot_table(index="student_id", columns="phase",
                               values="score", aggfunc="last")
        if "pre" in pivot and "post" in pivot:
            pivot["gain"] = pivot["post"] - pivot["pre"]
        return pivot.reset_index()
    except Exception:
        return None
