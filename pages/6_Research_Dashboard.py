"""
pages/6_Research_Dashboard.py
=============================
Publication-oriented research dashboard for instructors preparing a CAEE study.

The page surfaces the instructional design, anonymised data codebook, learning
outcome alignment, and psychometric checks needed to document BeamEdu as a
journal-grade computer application in engineering education.
"""

import streamlit as st

from utils import analytics
from utils.session import S
from utils.ui import apply_theme, hero, metric_card, pill

st.set_page_config(page_title="Research Dashboard · BeamEdu", page_icon="🎓", layout="wide")
S.init()
apply_theme()
analytics.log_event(S.student_id, "page_view", "research_dashboard")

hero(
    "Research Dashboard",
    subtitle="CAEE-ready evidence, ethics notes, codebook, and assessment diagnostics in one instructor view.",
    kicker="Publication · Evaluation · Replication",
    icon="🎓",
)

st.markdown(
    """
    This dashboard turns BeamEdu from a classroom demonstrator into a **publication-grade**
    engineering-education application by making the study design, learning analytics,
    and replication artefacts explicit. It is intended for instructors and researchers
    preparing a manuscript for *Computer Applications in Engineering Education* or a
    similar journal.
    """
)

# ──────────────────────────────────────────────
#  Manuscript-readiness checklist
# ──────────────────────────────────────────────
st.markdown("## Journal-readiness checklist")
checks = [
    ("Constructive alignment", "Learning objectives map to tool activities, quiz items, and exported measures."),
    ("Anonymised analytics", "Only the 8-character session ID and interaction traces are stored."),
    ("Pre/post evidence", "Learning gain and normalized gain are calculated for matched sessions."),
    ("Psychometrics", "Item difficulty, point-biserial discrimination, and Cronbach's alpha are reported when data permit."),
    ("Replication artefacts", "CSV exports, codebook, solver equations, and report generation support independent review."),
    ("Accessibility", "Plain-language prompts, high-contrast academic theme, and downloadable reports support diverse learners."),
]
cols = st.columns(3)
for i, (title, body) in enumerate(checks):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"### ✅ {title}")
            st.caption(body)

st.divider()

# ──────────────────────────────────────────────
#  Study design
# ──────────────────────────────────────────────
st.markdown("## Study design scaffold")
left, right = st.columns([1.15, 0.85])
with left:
    st.markdown(
        """
        | Manuscript element | BeamEdu implementation |
        |---|---|
        | Participants | Civil/structural engineering learners using anonymous session IDs. |
        | Intervention | Interactive beam construction, free-body diagram feedback, step solver, SFD/BMD visualizer, quiz, and PDF report. |
        | Primary outcome | Post-test minus pre-test score and Hake-style normalized gain. |
        | Process measures | Page views, templates loaded, beam solves, sweep animation use, and report generation. |
        | Validity evidence | Equilibrium checks, critical-section tables, item statistics, and exportable raw data. |
        | Ethics/privacy | No names, emails, or institutional identifiers are requested by the app. |
        """
    )
with right:
    with st.container(border=True):
        st.markdown("### Recommended classroom protocol")
        st.markdown(
            "1. Assign anonymous participant codes.\n"
            "2. Students complete the **pre-test** before using solver pages.\n"
            "3. Students solve at least one beginner, one intermediate, and one custom beam.\n"
            "4. Students export a PDF solution report for review.\n"
            "5. Students complete the **post-test**.\n"
            "6. Instructor exports CSVs and reports the dashboard diagnostics."
        )

st.divider()

# ──────────────────────────────────────────────
#  Outcomes alignment
# ──────────────────────────────────────────────
st.markdown("## Learning-outcome alignment")
outcomes = [
    {
        "Outcome": "LO1: Model supports and loads",
        "App evidence": "Beam Builder selections and load log",
        "Assessment evidence": "Quiz concepts on load idealisation and sign convention",
    },
    {
        "Outcome": "LO2: Apply static equilibrium",
        "App evidence": "Step Solver reaction derivation and verification residuals",
        "Assessment evidence": "Pre/post items on ΣFy and ΣM reasoning",
    },
    {
        "Outcome": "LO3: Interpret SFD/BMD relationships",
        "App evidence": "Visualizer cut-section sweep and critical-section table",
        "Assessment evidence": "Items on dV/dx = -w and dM/dx = V",
    },
    {
        "Outcome": "LO4: Communicate an engineering solution",
        "App evidence": "PDF report containing FBD, reactions, diagrams, and assumptions",
        "Assessment evidence": "Instructor review of exported solution report",
    },
]
st.dataframe(outcomes, width="stretch", hide_index=True)

st.divider()

# ──────────────────────────────────────────────
#  Live analytics
# ──────────────────────────────────────────────
st.markdown("## Live research analytics")
summary = analytics.assessment_summary()
gain = analytics.learning_gain_summary()
events = analytics.event_summary()
alpha_pre = analytics.cronbach_alpha("pre")
alpha_post = analytics.cronbach_alpha("post")

mc1, mc2, mc3, mc4 = st.columns(4)
participants = 0 if gain is None or gain.empty else len(gain)
matched = 0 if gain is None or "gain" not in gain else int(gain["gain"].notna().sum())
mean_gain = None if gain is None or "gain" not in gain or gain["gain"].dropna().empty else gain["gain"].mean()
mean_ngain = None if gain is None or "normalized_gain" not in gain or gain["normalized_gain"].dropna().empty else gain["normalized_gain"].mean()
with mc1:
    metric_card("Participants", str(participants), caption="unique anonymous sessions")
with mc2:
    metric_card("Matched pre/post", str(matched), caption="sessions with both phases")
with mc3:
    metric_card("Mean gain", "—" if mean_gain is None else f"{mean_gain:+.1f} pp", caption="post − pre")
with mc4:
    metric_card("Mean normalized gain", "—" if mean_ngain is None else f"{mean_ngain:.2f}", caption="(post − pre)/(100 − pre)")

if summary is None or summary.empty:
    st.info("No quiz score data recorded yet. Complete the pre/post quiz to populate study statistics.")
else:
    st.markdown("### Score descriptives")
    st.dataframe(summary, width="stretch", hide_index=True)

if gain is not None and not gain.empty:
    st.markdown("### Matched learning gains")
    st.dataframe(gain, width="stretch", hide_index=True)

st.markdown("### Internal-consistency cue")
ac1, ac2 = st.columns(2)
with ac1:
    st.write("Pre-test Cronbach α")
    st.markdown(pill("insufficient data" if alpha_pre is None else f"α = {alpha_pre:.2f}", kind="gold"), unsafe_allow_html=True)
with ac2:
    st.write("Post-test Cronbach α")
    st.markdown(pill("insufficient data" if alpha_post is None else f"α = {alpha_post:.2f}", kind="gold"), unsafe_allow_html=True)
st.caption("Alpha is shown only when at least two complete participant response vectors are available.")

items = analytics.item_analysis()
if items is not None and not items.empty:
    st.markdown("### Item analysis")
    st.dataframe(items, width="stretch", hide_index=True)

if events is not None and not events.empty:
    st.markdown("### Interaction-event summary")
    st.dataframe(events, width="stretch", hide_index=True)

st.divider()

# ──────────────────────────────────────────────
#  Codebook and exports
# ──────────────────────────────────────────────
st.markdown("## Replication package")
st.caption("Use these artefacts in the methods appendix, supplementary files, or institutional review documentation.")
st.dataframe(analytics.codebook(), width="stretch", hide_index=True)

c1, c2, c3 = st.columns(3)
with c1:
    data = analytics.export_csv("quiz_scores")
    st.download_button("⬇️ Quiz scores CSV", data or b"", "quiz_scores.csv", "text/csv", disabled=(data is None))
with c2:
    data = analytics.export_csv("quiz_items")
    st.download_button("⬇️ Item responses CSV", data or b"", "quiz_items.csv", "text/csv", disabled=(data is None))
with c3:
    data = analytics.export_csv("events")
    st.download_button("⬇️ Interaction events CSV", data or b"", "events.csv", "text/csv", disabled=(data is None))
