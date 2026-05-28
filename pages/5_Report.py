"""
pages/5_Report.py
=================
Generate a downloadable PDF solution report, and (for the researcher) export
the accumulated SQLite data as CSV for the CAEE study.
"""

import streamlit as st

from utils.session import S
from utils import analytics
from utils.pdf_report import build_pdf

st.set_page_config(page_title="Report · BeamEdu", page_icon="📄", layout="wide")
S.init()
analytics.log_event(S.student_id, "page_view", "report")

st.title("📄 Report & Data Export")

# ──────────────────────────────────────────────
#  Student solution report
# ──────────────────────────────────────────────
st.markdown("## Solution report (PDF)")

beam  = S.get_beam()
loads = S.get_loads()

if beam is None or not loads:
    st.info("⬅️ Configure and solve a beam first in **Beam Builder**.")
else:
    if not S.is_solved:
        S.solve()
    rxn = S.get_reactions()
    res = S.get_sfdbmd()

    st.markdown(
        f"Ready to export: **{S.beam_label or beam.beam_type.value.replace('_',' ').title()}** "
        f"(L = {beam.length:.2f} m) with {len(loads)} load(s)."
    )

    if st.button("🛠️ Build PDF report", type="primary"):
        with st.spinner("Generating report…"):
            try:
                pdf_bytes = build_pdf(beam, loads, rxn, res, student_id=S.student_id)
                analytics.log_event(S.student_id, "pdf_generated", S.beam_label)
                st.success("Report ready.")
                st.download_button(
                    "⬇️ Download PDF",
                    data=pdf_bytes,
                    file_name="beamedu_solution_report.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Could not build PDF: {e}")

st.divider()

# ──────────────────────────────────────────────
#  Researcher data export
# ──────────────────────────────────────────────
st.markdown("## Research data export")
st.caption(
    "For the instructor / researcher: anonymised quiz and interaction data "
    "collected this session, for the CAEE study. Only an 8-char session ID is stored."
)

with st.expander("📈 Learning-gain summary"):
    summary = analytics.learning_gain_summary()
    if summary is None or summary.empty:
        st.write("No quiz data recorded yet.")
    else:
        st.dataframe(summary, use_container_width=True, hide_index=True)

ec1, ec2, ec3 = st.columns(3)
with ec1:
    data = analytics.export_csv("quiz_scores")
    st.download_button("⬇️ Quiz scores (CSV)", data or b"", "quiz_scores.csv",
                       "text/csv", disabled=(data is None))
with ec2:
    data = analytics.export_csv("quiz_items")
    st.download_button("⬇️ Item responses (CSV)", data or b"", "quiz_items.csv",
                       "text/csv", disabled=(data is None))
with ec3:
    data = analytics.export_csv("events")
    st.download_button("⬇️ Interaction events (CSV)", data or b"", "events.csv",
                       "text/csv", disabled=(data is None))
