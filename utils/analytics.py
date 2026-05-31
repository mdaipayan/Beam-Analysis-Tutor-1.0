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

import datetime
import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

import numpy as np
import pandas as pd

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_DB_PATH = os.path.join(_DB_DIR, "responses.db")
_ALLOWED_TABLES = {"quiz_scores", "quiz_items", "events"}


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

_CODEBOOK = [
    {
        "table": "quiz_scores",
        "field": "student_id",
        "description": "Anonymous 8-character session identifier; no direct personal identifiers are stored.",
    },
    {"table": "quiz_scores", "field": "phase", "description": "Assessment phase: pre or post."},
    {"table": "quiz_scores", "field": "score", "description": "Percentage score, 0–100."},
    {"table": "quiz_scores", "field": "n_questions", "description": "Number of scored quiz items."},
    {"table": "quiz_scores", "field": "timestamp", "description": "Local ISO-8601 timestamp when submitted."},
    {"table": "quiz_items", "field": "question_id", "description": "Stable item identifier from data/quiz_bank.json."},
    {"table": "quiz_items", "field": "correct", "description": "Binary item score: 1 = correct, 0 = incorrect."},
    {"table": "events", "field": "event_type", "description": "Interaction marker such as page_view, beam_solved, or template_loaded."},
    {"table": "events", "field": "detail", "description": "Short free-text or JSON-like context for the event."},
]


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


def _read_table(table: str) -> pd.DataFrame:
    """Read a whitelisted analytics table into a DataFrame."""
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Unsupported export table: {table}")
    with _connect() as conn:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)


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
        df = _read_table(table)
        if df.empty:
            return None
        return df.to_csv(index=False).encode("utf-8")
    except Exception:
        return None


def codebook() -> pd.DataFrame:
    """Return the anonymised-data codebook displayed on the research dashboard."""
    return pd.DataFrame(_CODEBOOK)


def learning_gain_summary() -> Optional[pd.DataFrame]:
    """
    Compute per-student learning gain (post − pre) — the headline CAEE metric.
    Returns a DataFrame with columns: student_id, pre, post, gain, normalized_gain.
    """
    try:
        df = _read_table("quiz_scores")
        if df.empty:
            return None
        pivot = df.pivot_table(index="student_id", columns="phase", values="score", aggfunc="last")
        if "pre" in pivot and "post" in pivot:
            pivot["gain"] = pivot["post"] - pivot["pre"]
            denominator = (100.0 - pivot["pre"]).replace(0.0, np.nan)
            pivot["normalized_gain"] = (pivot["post"] - pivot["pre"]) / denominator
        return pivot.reset_index()
    except Exception:
        return None


def assessment_summary() -> Optional[pd.DataFrame]:
    """Return publication-oriented descriptive statistics for pre/post scores."""
    try:
        df = _read_table("quiz_scores")
        if df.empty:
            return None
        latest = df.sort_values("timestamp").groupby(["student_id", "phase"], as_index=False).tail(1)
        grouped = latest.groupby("phase")["score"]
        summary = grouped.agg(n="count", mean="mean", sd="std", median="median", min="min", max="max").reset_index()
        summary["sd"] = summary["sd"].fillna(0.0)
        return summary
    except Exception:
        return None


def item_analysis() -> Optional[pd.DataFrame]:
    """Compute item difficulty and discrimination cues from recorded item responses."""
    try:
        items = _read_table("quiz_items")
        scores = _read_table("quiz_scores")
        if items.empty:
            return None

        latest_scores = scores.sort_values("timestamp").groupby(["student_id", "phase"], as_index=False).tail(1)
        merged = items.merge(latest_scores[["student_id", "phase", "score"]], on=["student_id", "phase"], how="left")
        rows = []
        for (phase, question_id), group in merged.groupby(["phase", "question_id"]):
            difficulty = float(group["correct"].mean())
            discrimination = np.nan
            if group["score"].notna().sum() >= 3 and group["correct"].nunique() > 1:
                discrimination = float(group["correct"].corr(group["score"]))
            rows.append(
                {
                    "phase": phase,
                    "question_id": question_id,
                    "n": int(len(group)),
                    "difficulty_p_correct": difficulty,
                    "point_biserial_r": discrimination,
                }
            )
        return pd.DataFrame(rows).sort_values(["phase", "question_id"])
    except Exception:
        return None


def cronbach_alpha(phase: str = "post") -> Optional[float]:
    """Estimate Cronbach's alpha for a quiz phase from binary item responses."""
    try:
        items = _read_table("quiz_items")
        items = items[items["phase"] == phase]
        if items.empty:
            return None
        matrix = items.pivot_table(index="student_id", columns="question_id", values="correct", aggfunc="last")
        matrix = matrix.dropna(axis=0)
        n_items = matrix.shape[1]
        if matrix.shape[0] < 2 or n_items < 2:
            return None
        item_variance = matrix.var(axis=0, ddof=1).sum()
        total_variance = matrix.sum(axis=1).var(ddof=1)
        if total_variance == 0:
            return None
        return float(n_items / (n_items - 1) * (1 - item_variance / total_variance))
    except Exception:
        return None


def event_summary() -> Optional[pd.DataFrame]:
    """Return counts of tracked interactions for time-on-task and usage reporting."""
    try:
        events = _read_table("events")
        if events.empty:
            return None
        return (
            events.groupby("event_type")
            .agg(events=("id", "count"), unique_students=("student_id", "nunique"))
            .reset_index()
            .sort_values("events", ascending=False)
        )
    except Exception:
        return None
