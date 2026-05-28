"""
pages/2_Step_Solver.py
======================
Displays the full worked solution:
  • Reaction calculation steps (analytical or stiffness method)
  • Segment-by-segment SFD / BMD analysis
Each step is expandable, with LaTeX equations and numerical values.
"""

import streamlit as st

from utils.session import S
from utils import analytics

st.set_page_config(page_title="Step Solver · BeamEdu", page_icon="🧮", layout="wide")
S.init()
analytics.log_event(S.student_id, "page_view", "step_solver")

st.title("🧮 Step-by-Step Solver")

beam  = S.get_beam()
loads = S.get_loads()

if beam is None or not loads:
    st.info("⬅️ Configure a beam and at least one load in **Beam Builder** first.")
    if st.button("Go to Beam Builder"):
        st.switch_page("pages/1_Beam_Builder.py")
    st.stop()

# Solve (cached if already done)
if not S.is_solved:
    if not S.solve():
        st.error("Could not solve — check the beam and loads.")
        st.stop()

rxn = S.get_reactions()
res = S.get_sfdbmd()

# ── Header summary ─────────────────────────────────────────────────────
dsi = beam.degree_of_indeterminacy()
det = "Statically determinate" if dsi == 0 else f"Statically indeterminate (DSI = {dsi})"
st.markdown(
    f"**{S.beam_label or beam.beam_type.value.replace('_',' ').title()}** · "
    f"L = {beam.length:.2f} m · {det} · "
    f"Method: **{rxn.method.replace('_', ' ')}**"
)
st.divider()

# ── Part A: Reactions ──────────────────────────────────────────────────
st.markdown("## Part A — Support reactions")

# Quick result chips
rcols = st.columns(max(len(rxn.reactions), 1))
for col, pos in zip(rcols, sorted(rxn.reactions)):
    r = rxn.reactions[pos]
    with col:
        st.metric(f"R @ x={pos:.2f} m", f"{r.get('Fy', 0):+.3f} kN")
        if "M" in r:
            st.caption(f"M = {r['M']:+.3f} kN·m")

st.markdown("#### Worked steps")
for step in rxn.steps:
    with st.expander(f"Step {step['number']}: {step['title']}", expanded=(step['number'] <= 2)):
        st.text(step["description"])
        if step.get("latex"):
            try:
                st.latex(step["latex"].replace("$", ""))
            except Exception:
                st.code(step["latex"])
        if step.get("value"):
            st.success(step["value"])

st.divider()

# ── Part B: SFD / BMD ──────────────────────────────────────────────────
st.markdown("## Part B — Shear force & bending moment")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Max +V", f"{res.V_max:+.2f} kN")
m2.metric("Max −V", f"{res.V_min:+.2f} kN")
m3.metric("Max +M", f"{res.M_max:+.2f} kN·m")
m4.metric("Max −M", f"{res.M_min:+.2f} kN·m")

zsp = res.zero_shear_positions
if zsp:
    st.caption("Zero-shear (max-moment) locations: " + ", ".join(f"x = {z:.3f} m" for z in zsp))

st.markdown("#### Segment analysis")
for step in res.steps:
    title = step.get("title", f"Step {step.get('number','')}")
    with st.expander(title, expanded=False):
        st.text(step["description"])
        if step.get("latex"):
            try:
                st.latex(step["latex"].replace("$", ""))
            except Exception:
                st.code(step["latex"])
        if step.get("value"):
            st.info(step["value"])

st.divider()
cc1, cc2 = st.columns(2)
if cc1.button("📊 View interactive diagrams", type="primary"):
    st.switch_page("pages/3_Visualizer.py")
if cc2.button("📄 Generate report"):
    st.switch_page("pages/5_Report.py")
