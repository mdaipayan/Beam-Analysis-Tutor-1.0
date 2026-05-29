"""
pages/4_Quiz.py
===============
Conceptual assessment for the CAEE study.
  • Pre-test (before using the tool) and Post-test (after).
  • Questions drawn from data/quiz_bank.json.
  • Scores and per-item results logged to SQLite via utils.analytics.
"""

import json
import os
import random

import streamlit as st

from utils.session import S
from utils import analytics
from utils.ui import apply_theme

st.set_page_config(page_title="Quiz · BeamEdu", page_icon="📝", layout="wide")
S.init()
apply_theme()
analytics.log_event(S.student_id, "page_view", "quiz")

st.title("📝 Concept Quiz")
st.caption("Test your understanding of SFD & BMD fundamentals.")

_BANK = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "quiz_bank.json")


@st.cache_data
def _load_questions():
    with open(_BANK, "r") as f:
        return json.load(f)["questions"]


questions = _load_questions()

# ── Phase selection ────────────────────────────────────────────────────
phase = st.radio(
    "Which assessment are you taking?",
    ["pre", "post"],
    format_func=lambda p: "Pre-test (before learning)" if p == "pre" else "Post-test (after learning)",
    horizontal=True,
)

prev = S.get_quiz_score(phase)
if prev is not None:
    st.info(f"You previously scored **{prev:.0f}%** on the {phase}-test. You can retake it below.")

st.divider()

# ── Quiz form ──────────────────────────────────────────────────────────
with st.form(f"quizform_{phase}"):
    responses = {}
    for i, q in enumerate(questions, 1):
        st.markdown(f"**Q{i}. {q['question']}**")
        responses[q["id"]] = st.radio(
            f"q_{q['id']}",
            options=list(range(len(q["options"]))),
            format_func=lambda idx, opts=q["options"]: opts[idx],
            index=None,
            label_visibility="collapsed",
            key=f"{phase}_{q['id']}",
        )
        st.write("")

    submitted = st.form_submit_button("✅ Submit answers", type="primary")

if submitted:
    unanswered = [qid for qid, r in responses.items() if r is None]
    if unanswered:
        st.warning(f"Please answer all questions ({len(unanswered)} remaining).")
    else:
        correct = 0
        for q in questions:
            is_correct = (responses[q["id"]] == q["answer"])
            correct += int(is_correct)
            analytics.log_quiz_item(S.student_id, phase, q["id"], is_correct)
        score = 100.0 * correct / len(questions)
        S.set_quiz_score(phase, score)
        analytics.log_quiz_score(S.student_id, phase, score, len(questions))
        S.log_quiz_attempt({"phase": phase, "score": score, "correct": correct, "total": len(questions)})

        st.success(f"You scored **{correct}/{len(questions)}**  ({score:.0f}%)")

        # Show learning gain if both phases done
        pre  = S.get_quiz_score("pre")
        post = S.get_quiz_score("post")
        if pre is not None and post is not None:
            gain = post - pre
            st.metric("Learning gain (post − pre)", f"{gain:+.0f} percentage points")

        # Feedback per question
        with st.expander("📖 Review answers & explanations", expanded=True):
            for i, q in enumerate(questions, 1):
                chosen = responses[q["id"]]
                ok = (chosen == q["answer"])
                icon = "✅" if ok else "❌"
                st.markdown(f"{icon} **Q{i}. {q['question']}**")
                st.write(f"Your answer: _{q['options'][chosen]}_")
                if not ok:
                    st.write(f"Correct answer: **{q['options'][q['answer']]}**")
                st.caption(q["explanation"])
                st.divider()
