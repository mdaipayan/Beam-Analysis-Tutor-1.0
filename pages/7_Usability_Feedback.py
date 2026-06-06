"""
pages/7_Usability_Feedback.py
=============================
Collect user-friendliness evidence using the standard System Usability Scale (SUS).

This page is intentionally self-contained so it does not disturb the validated beam
solver or the existing quiz workflow. It stores anonymous SUS responses in the same
local data folder used by the rest of the app and provides CSV export for CAEE-style
analysis.
"""

from __future__ import annotations

import datetime
import os
import sqlite3

import pandas as pd
import streamlit as st

from utils.session import S
from utils import analytics
from utils.ui import apply_theme, hero, metric_card

st.set_page_config(page_title="Usability Feedback · BeamEdu", page_icon="⭐", layout="wide")
S.init()
apply_theme()
analytics.log_event(S.student_id, "page_view", "usability_feedback")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "responses.db")

SUS_ITEMS = [
    "I think that I would like to use BeamEdu frequently.",
    "I found BeamEdu unnecessarily complex.",
    "I thought BeamEdu was easy to use.",
    "I think that I would need support from a teacher or technical person to use BeamEdu.",
    "I found the different functions in BeamEdu well integrated.",
    "I thought there was too much inconsistency in BeamEdu.",
    "I would imagine that most students would learn to use BeamEdu very quickly.",
    "I found BeamEdu cumbersome to use.",
    "I felt confident using BeamEdu.",
    "I needed to learn many things before I could get started with BeamEdu.",
]


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usability_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            q1 INTEGER NOT NULL,
            q2 INTEGER NOT NULL,
            q3 INTEGER NOT NULL,
            q4 INTEGER NOT NULL,
            q5 INTEGER NOT NULL,
            q6 INTEGER NOT NULL,
            q7 INTEGER NOT NULL,
            q8 INTEGER NOT NULL,
            q9 INTEGER NOT NULL,
            q10 INTEGER NOT NULL,
            sus_score REAL NOT NULL,
            comment TEXT,
            timestamp TEXT NOT NULL
        )
        """
    )
    return conn


def compute_sus_score(responses: dict[str, int]) -> float:
    """Standard SUS scoring: odd items rating-1, even items 5-rating, total × 2.5."""
    raw = 0.0
    for i in range(1, 11):
        rating = int(responses[f"q{i}"])
        raw += rating - 1 if i % 2 == 1 else 5 - rating
    return float(raw * 2.5)


def save_response(student_id: str, responses: dict[str, int], comment: str) -> float | None:
    try:
        sus_score = compute_sus_score(responses)
        values = [student_id] + [responses[f"q{i}"] for i in range(1, 11)] + [sus_score, comment, _now()]
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO usability_responses
                (student_id, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, sus_score, comment, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            conn.commit()
        return sus_score
    except Exception:
        return None


def load_usability_data() -> pd.DataFrame:
    try:
        with _connect() as conn:
            return pd.read_sql_query("SELECT * FROM usability_responses", conn)
    except Exception:
        return pd.DataFrame()


def latest_per_student(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.sort_values("timestamp").groupby("student_id", as_index=False).tail(1)


def interpret_sus(score: float) -> str:
    if score >= 80:
        return "Excellent user-friendliness"
    if score >= 68:
        return "Acceptable to good user-friendliness"
    return "Needs UI improvement"


hero(
    "Usability Feedback",
    subtitle="Rate BeamEdu after completing the learning activity. The score supports CAEE-style user-friendliness evidence.",
    kicker="SUS · User-friendliness · Classroom Study",
    icon="⭐",
)

st.markdown(
    """
    This page uses the **System Usability Scale (SUS)**. Students should complete it
    **after** using BeamEdu for the assigned beam problems. Ratings are anonymous and
    linked only to the current session code.
    """
)

st.info(
    "Use the same anonymous participant code used for the quiz. Do not type your name, roll number, email, or phone number in the comment box."
)

scale = {
    1: "1 — Strongly disagree",
    2: "2 — Disagree",
    3: "3 — Neutral",
    4: "4 — Agree",
    5: "5 — Strongly agree",
}

with st.form("sus_form"):
    responses = {}
    for i, item in enumerate(SUS_ITEMS, start=1):
        st.markdown(f"**{i}. {item}**")
        responses[f"q{i}"] = st.radio(
            f"sus_q{i}",
            options=[1, 2, 3, 4, 5],
            format_func=lambda v, labels=scale: labels[v],
            index=None,
            horizontal=True,
            label_visibility="collapsed",
            key=f"sus_q{i}_rating",
        )
        st.write("")

    comment = st.text_area(
        "Optional comment: What was easy or difficult while using BeamEdu?",
        placeholder="Example: The step solver was clear, but I needed more hints for UVL problems.",
        max_chars=600,
    )
    submitted = st.form_submit_button("✅ Submit usability feedback", type="primary")

if submitted:
    missing = [k for k, v in responses.items() if v is None]
    if missing:
        st.warning(f"Please answer all 10 SUS questions. Missing: {len(missing)}")
    else:
        score = save_response(S.student_id, responses, comment.strip())
        if score is None:
            st.error("Could not save the usability response. Please try again.")
        else:
            analytics.log_event(S.student_id, "sus_submitted", f"SUS={score:.1f}")
            st.success(f"Thank you. Your SUS score contribution was recorded: **{score:.1f}/100**")
            st.caption(interpret_sus(score))

st.divider()
st.markdown("## Instructor summary")

df = latest_per_student(load_usability_data())
if df.empty:
    st.info("No usability feedback has been submitted yet.")
else:
    scores = df["sus_score"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Responses", str(int(scores.count())), "latest response per anonymous session")
    with c2:
        metric_card("Mean SUS", f"{scores.mean():.1f}", interpret_sus(float(scores.mean())))
    with c3:
        sd = 0.0 if scores.count() < 2 else scores.std(ddof=1)
        metric_card("SD", f"{sd:.1f}", "score spread")
    with c4:
        metric_card("Median", f"{scores.median():.1f}", "central tendency")

    item_rows = []
    for i, statement in enumerate(SUS_ITEMS, start=1):
        item_rows.append(
            {
                "item": f"q{i}",
                "statement": statement,
                "mean_rating_1_to_5": round(float(df[f"q{i}"].mean()), 2),
            }
        )
    st.markdown("### Item-wise mean ratings")
    st.dataframe(pd.DataFrame(item_rows), width="stretch", hide_index=True)

    st.download_button(
        "⬇️ Download usability SUS CSV",
        data=load_usability_data().to_csv(index=False).encode("utf-8"),
        file_name="usability_sus.csv",
        mime="text/csv",
    )
