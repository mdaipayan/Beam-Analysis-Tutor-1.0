"""
pages/8_Learning_Path.py
========================
Pedagogy-oriented learning path for BeamEdu.

This page makes the teaching strategy explicit for students, instructors, and
journal reviewers: Predict → Build → Solve → Visualize → Reflect → Assess.
It supports classroom implementation and CAEE-style reporting by documenting
how the app is used as a guided learning intervention rather than only as a
calculation tool.
"""

from __future__ import annotations

import datetime
import os
import sqlite3
from contextlib import contextmanager

import pandas as pd
import streamlit as st

from utils.session import S
from utils import analytics
from utils.ui import apply_theme, hero, metric_card

st.set_page_config(page_title="Learning Path · BeamEdu", page_icon="🧭", layout="wide")
S.init()
apply_theme()
analytics.log_event(S.student_id, "page_view", "learning_path")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "responses.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS learning_reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    predicted_reactions TEXT,
    predicted_diagram_shape TEXT,
    predicted_max_moment TEXT,
    reflection TEXT,
    confidence_before INTEGER,
    confidence_after INTEGER,
    timestamp TEXT NOT NULL
)
"""


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


@contextmanager
def _connect():
    """Open the shared local SQLite database and close it cleanly."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _clean_text(text: str, limit: int) -> str:
    """Normalize free-text responses and apply a conservative length limit."""
    return (text or "").strip()[:limit]


def save_reflection(data: dict) -> bool:
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO learning_reflections
                (student_id, predicted_reactions, predicted_diagram_shape, predicted_max_moment,
                 reflection, confidence_before, confidence_after, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    S.student_id,
                    data["predicted_reactions"],
                    data["predicted_diagram_shape"],
                    data["predicted_max_moment"],
                    data["reflection"],
                    int(data["confidence_before"]),
                    int(data["confidence_after"]),
                    _now(),
                ),
            )
        return True
    except Exception:
        return False


def load_reflections() -> pd.DataFrame:
    try:
        with _connect() as conn:
            return pd.read_sql_query("SELECT * FROM learning_reflections", conn)
    except Exception:
        return pd.DataFrame()


hero(
    "Learning Path",
    subtitle="A guided pedagogy sequence for learning SFD and BMD through prediction, construction, visualization, reflection, and assessment.",
    kicker="Pedagogy · Classroom Flow · CAEE Evidence",
    icon="🧭",
)

st.markdown(
    """
    BeamEdu should be used as a **guided learning intervention**, not only as a
    calculation engine. The recommended instructional cycle is:
    """
)

steps = [
    ("1", "Predict", "Students first predict reactions, diagram shape, and the likely maximum-moment location before seeing the answer."),
    ("2", "Build", "Students model the beam, supports, and loads using either preset problems or custom inputs."),
    ("3", "Solve", "The Step Solver reveals support reactions and equations in stages."),
    ("4", "Visualize", "The moving cut and progressive fill connect load, shear, and moment relationships."),
    ("5", "Reflect", "Students compare their predictions with BeamEdu results and explain the reason for differences."),
    ("6", "Assess", "Students complete pre/post quiz and usability feedback for learning and user-friendliness evidence."),
]

cols = st.columns(3)
for i, (num, title, body) in enumerate(steps):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"### {num}. {title}")
            st.caption(body)

st.divider()
st.markdown("## Recommended student workflow")

pre = S.get_quiz_score("pre")
post = S.get_quiz_score("post")

m1, m2, m3 = st.columns(3)
with m1:
    metric_card("Pre-test", "Not done" if pre is None else f"{pre:.0f}%", "complete before solver use")
with m2:
    metric_card("Post-test", "Not done" if post is None else f"{post:.0f}%", "complete after app activity")
with m3:
    if pre is not None and post is not None:
        metric_card("Gain", f"{post - pre:+.0f} pp", "post − pre")
    else:
        metric_card("Gain", "—", "available after both tests")

st.markdown(
    """
    | Stage | Student action | App page |
    |---|---|---|
    | 1 | Take the pre-test | Quiz |
    | 2 | Load one beginner preset | Beam Builder |
    | 3 | Predict reactions and diagram shape | Learning Path |
    | 4 | Reveal reactions and equations | Step Solver |
    | 5 | Drag/play the moving cut | Visualizer |
    | 6 | Solve one intermediate or custom beam | Beam Builder + Step Solver |
    | 7 | Generate PDF report | Report |
    | 8 | Take post-test and usability feedback | Quiz + Usability Feedback |
    """
)

nav1, nav2, nav3, nav4 = st.columns(4)
with nav1:
    if st.button("📝 Open Quiz", width="stretch"):
        st.switch_page("pages/4_Quiz.py")
with nav2:
    if st.button("🏗️ Open Beam Builder", width="stretch"):
        st.switch_page("pages/1_Beam_Builder.py")
with nav3:
    if st.button("🧮 Open Step Solver", width="stretch"):
        st.switch_page("pages/2_Step_Solver.py")
with nav4:
    if st.button("📊 Open Visualizer", width="stretch"):
        st.switch_page("pages/3_Visualizer.py")

st.divider()
st.markdown("## Predict-before-reveal activity")
st.caption("Use this before opening the full worked steps. It helps students compare their mental model with the computed result.")
st.info("Use only your anonymous participant code. Do not type your name, roll number, email address, phone number, or other personal details in the prediction/reflection boxes.")

shape_options = [
    "Triangular BMD",
    "Parabolic BMD",
    "Cubic BMD",
    "BMD with sudden jump",
    "Hogging and sagging regions",
    "Not sure",
]

with st.form("prediction_reflection_form"):
    predicted_reactions = st.text_area(
        "Prediction 1: What do you expect the support reactions to be?",
        placeholder="Example: R_A and R_B may be equal because the load is symmetric.",
        max_chars=700,
    )
    predicted_diagram_shape = st.multiselect(
        "Prediction 2: What shape/features do you expect in the BMD?",
        options=shape_options,
    )
    predicted_max_moment = st.text_input(
        "Prediction 3: Where do you expect maximum bending moment to occur?",
        placeholder="Example: near midspan, under point load, or where shear becomes zero.",
        max_chars=250,
    )
    confidence_before = st.slider("Confidence before using Step Solver", 1, 5, 3)
    reflection = st.text_area(
        "Reflection: After using BeamEdu, what changed in your understanding?",
        placeholder="Example: I realized the maximum moment occurs where the SFD crosses zero, not necessarily where the load is largest.",
        max_chars=900,
    )
    confidence_after = st.slider("Confidence after using BeamEdu", 1, 5, 4)
    submitted = st.form_submit_button("✅ Save prediction and reflection", type="primary")

if submitted:
    data = {
        "predicted_reactions": _clean_text(predicted_reactions, 700),
        "predicted_diagram_shape": "; ".join(predicted_diagram_shape),
        "predicted_max_moment": _clean_text(predicted_max_moment, 250),
        "reflection": _clean_text(reflection, 900),
        "confidence_before": confidence_before,
        "confidence_after": confidence_after,
    }
    if save_reflection(data):
        analytics.log_event(S.student_id, "learning_reflection_submitted", "predict_build_solve_visualize_reflect_assess")
        st.success("Saved. Use this reflection in your classroom worksheet or learning portfolio.")
    else:
        st.error("Could not save the reflection. Please try again.")

st.divider()
st.markdown("## Common misconceptions to discuss")

misconceptions = [
    ("UDL misconception", "A UDL does not give a constant SFD; it gives a linearly varying SFD."),
    ("Point-load misconception", "A point load creates a sudden jump in SFD, not a smooth curve."),
    ("Moment misconception", "An applied couple creates a jump in BMD but does not create a jump in SFD."),
    ("Maximum moment misconception", "Maximum or minimum moment occurs where shear becomes zero or changes sign."),
    ("Sign-convention misconception", "Positive sagging moment usually means tension at the bottom fibre."),
]

for title, body in misconceptions:
    with st.expander(f"⚠️ {title}"):
        st.write(body)

st.divider()
st.markdown("## Instructor export")

reflections = load_reflections()
if reflections.empty:
    st.info("No prediction/reflection responses have been saved yet.")
else:
    latest = reflections.sort_values("timestamp").groupby("student_id", as_index=False).tail(1)
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Responses", str(len(latest)), "latest response per anonymous session")
    with c2:
        metric_card("Mean confidence before", f"{latest['confidence_before'].mean():.2f}/5", "student self-rating")
    with c3:
        metric_card("Mean confidence after", f"{latest['confidence_after'].mean():.2f}/5", "student self-rating")

    st.dataframe(latest, width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Download learning reflections CSV",
        data=reflections.to_csv(index=False).encode("utf-8"),
        file_name="learning_reflections.csv",
        mime="text/csv",
    )

st.divider()
st.markdown("## Classroom worksheet prompt")
st.code(
    """BeamEdu worksheet sequence

1. Write your prediction for support reactions.
2. Predict the SFD and BMD shape before pressing Solve.
3. Use Step Solver to compare your answer with BeamEdu.
4. Use the moving cut in Visualizer and note where V = 0.
5. Explain why maximum bending moment occurs at that location.
6. Generate the PDF report.
7. Complete post-test and usability feedback.
""",
    language="text",
)
