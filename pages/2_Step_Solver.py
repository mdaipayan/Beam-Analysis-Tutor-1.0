"""
pages/2_Step_Solver.py
======================
Visual, staged walkthrough of the full solution:

  Part A — Reactions, revealed in stages on a live diagram:
     Stage 0: bare beam + supports
     Stage 1: applied loads added
     Stage 2: reactions shown
   Each stage is paired with the matching worked-calculation steps.

  Part B — SFD & BMD built up by a moving cut:
     A slider (with optional auto-play) sweeps a section cut left→right.
     The V and M areas fill progressively up to the cut, and the value at the
     cut is read out live — so students see HOW the diagrams accumulate.
"""

import time

import numpy as np
import streamlit as st

from engine import beam_fbd_figure, sfd_bmd_figure
from engine import PointLoad, UDL, UVL, AppliedMoment
from utils.session import S
from utils import analytics
from utils.ui import apply_theme


def _label_for(ld) -> str:
    """One-line human description of a load for the stage list."""
    if isinstance(ld, PointLoad):
        return f"Point load **{ld.label or 'P'}** = {ld.magnitude:.2f} kN at x = {ld.position:.2f} m"
    if isinstance(ld, UDL):
        return f"UDL **{ld.label or 'w'}** = {ld.intensity:.2f} kN/m over x = {ld.start:.2f}–{ld.end:.2f} m"
    if isinstance(ld, UVL):
        return (f"UVL **{ld.label or 'w'}** {ld.intensity_start:.1f}→{ld.intensity_end:.1f} kN/m "
                f"over x = {ld.start:.2f}–{ld.end:.2f} m")
    if isinstance(ld, AppliedMoment):
        d = "CW" if ld.magnitude >= 0 else "CCW"
        return f"Applied moment **{ld.label or 'M₀'}** = {abs(ld.magnitude):.2f} kN·m ({d}) at x = {ld.position:.2f} m"
    return str(ld)

st.set_page_config(page_title="Step Solver · BeamEdu", page_icon="🧮", layout="wide")
S.init()
apply_theme()
analytics.log_event(S.student_id, "page_view", "step_solver")

st.title("🧮 Step-by-Step Solver")

beam  = S.get_beam()
loads = S.get_loads()

if beam is None or not loads:
    st.info("⬅️ Configure a beam and at least one load in **Beam Builder** first.")
    if st.button("Go to Beam Builder"):
        st.switch_page("pages/1_Beam_Builder.py")
    st.stop()

if not S.is_solved:
    if not S.solve():
        st.error("Could not solve — check the beam and loads.")
        st.stop()

rxn = S.get_reactions()
res = S.get_sfdbmd()

dsi = beam.degree_of_indeterminacy()
det = "Statically determinate" if dsi == 0 else f"Statically indeterminate (DSI = {dsi})"
st.markdown(
    f"**{S.beam_label or beam.beam_type.value.replace('_',' ').title()}** · "
    f"L = {beam.length:.2f} m · {det} · Method: **{rxn.method.replace('_', ' ')}**"
)
st.divider()

# ══════════════════════════════════════════════════════════════════════
#  PART A — Reactions revealed in stages on a live diagram
# ══════════════════════════════════════════════════════════════════════
st.markdown("## Part A — Support reactions")

stage = st.radio(
    "Reveal stage",
    options=[0, 1, 2],
    format_func=lambda s: ["1 · Bare beam & supports",
                           "2 · Apply the loads",
                           "3 · Show the reactions"][s],
    horizontal=True,
)

colL, colR = st.columns([3, 2])

with colL:
    if stage == 0:
        fig = beam_fbd_figure(beam, [], reactions=None)
    elif stage == 1:
        fig = beam_fbd_figure(beam, loads, reactions=None)
    else:
        fig = beam_fbd_figure(beam, loads, reactions=rxn.reactions)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

with colR:
    if stage == 0:
        st.markdown("#### The beam")
        st.markdown(
            "Identify the **supports** and the span. Each support type provides "
            "a known set of reactions:\n"
            "- Pin → vertical + horizontal\n"
            "- Roller → vertical only\n"
            "- Fixed → vertical + horizontal + moment"
        )
        st.metric("Degree of static indeterminacy", dsi)
    elif stage == 1:
        st.markdown("#### Applied loads")
        for ld in loads:
            st.markdown(f"- {_label_for(ld)}")
    else:
        st.markdown("#### Reactions found")
        for pos in sorted(rxn.reactions):
            r = rxn.reactions[pos]
            line = f"**x = {pos:.2f} m** → R = {r.get('Fy',0):+.3f} kN"
            if "M" in r:
                line += f", M = {r['M']:+.3f} kN·m"
            st.write(line)

# Reaction result chips
st.markdown("#### Results")
rcols = st.columns(max(len(rxn.reactions), 1))
for col, pos in zip(rcols, sorted(rxn.reactions)):
    r = rxn.reactions[pos]
    with col:
        st.metric(f"R @ x={pos:.2f} m", f"{r.get('Fy', 0):+.3f} kN")
        if "M" in r:
            st.caption(f"M = {r['M']:+.3f} kN·m")

with st.expander("📝 Show full worked reaction steps", expanded=False):
    for step in rxn.steps:
        st.markdown(f"**Step {step['number']}: {step['title']}**")
        st.text(step["description"])
        if step.get("latex"):
            try:
                st.latex(step["latex"].replace("$", ""))
            except Exception:
                st.code(step["latex"])
        if step.get("value"):
            st.success(step["value"])
        st.divider()

st.divider()

# ══════════════════════════════════════════════════════════════════════
#  PART B — SFD & BMD built up by a moving cut
# ══════════════════════════════════════════════════════════════════════
st.markdown("## Part B — Build the SFD & BMD with a moving cut")
st.caption(
    "Drag the cut along the beam (or press ▶ Play). The shear and moment areas "
    "fill in up to the cut, and the value at the cut is shown live. "
    "Notice: the moment peaks where the shear crosses zero."
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Max +V", f"{res.V_max:+.2f} kN")
m2.metric("Max −V", f"{res.V_min:+.2f} kN")
m3.metric("Max +M", f"{res.M_max:+.2f} kN·m")
m4.metric("Max −M", f"{res.M_min:+.2f} kN·m")

ctl1, ctl2, ctl3 = st.columns([2, 1, 1])
with ctl1:
    cut = st.slider("Section cut position  x (m)", 0.0, float(beam.length),
                    float(beam.length) / 2, step=float(beam.length) / 200,
                    key="solver_cut")
with ctl2:
    fill = st.toggle("Progressive fill", value=True,
                     help="Shade only up to the cut, revealing the diagram as it builds.")
with ctl3:
    hog = st.toggle("Hogging up", value=False, help="Flip the BMD sign convention.")

play = st.button("▶ Play sweep", help="Animate the cut from left to right.")

V_cut = float(np.interp(cut, res.x, res.V))
M_cut = float(np.interp(cut, res.x, res.M))
pc1, pc2, pc3 = st.columns(3)
pc1.metric("Cut at x", f"{cut:.3f} m")
pc2.metric("V at cut", f"{V_cut:+.3f} kN")
pc3.metric("M at cut", f"{M_cut:+.3f} kN·m")

chart_area = st.empty()

if play:
    analytics.log_event(S.student_id, "sweep_played", S.beam_label)
    n_frames = 60
    for i in range(n_frames + 1):
        cx = beam.length * i / n_frames
        fig = sfd_bmd_figure(beam, res, cut_x=cx, fill_to_cut=fill, hogging_up=hog)
        chart_area.plotly_chart(fig, width="stretch",
                                config={"displayModeBar": False},
                                key=f"sweep_{i}")
        time.sleep(0.03)
    # leave it at the slider position afterwards
    fig = sfd_bmd_figure(beam, res, cut_x=cut, fill_to_cut=fill, hogging_up=hog)
    chart_area.plotly_chart(fig, width="stretch",
                            config={"displayModeBar": False}, key="sweep_final")
else:
    fig = sfd_bmd_figure(beam, res, cut_x=cut, fill_to_cut=fill, hogging_up=hog)
    chart_area.plotly_chart(fig, width="stretch",
                            config={"displayModeBar": False}, key="static_cut")

zsp = res.zero_shear_positions
if zsp:
    st.info("🎯 Shear crosses zero at: " + ", ".join(f"x = {z:.3f} m" for z in zsp)
            + "  — the bending moment is maximum (or minimum) at these sections.")

with st.expander("📝 Show segment-by-segment equations", expanded=False):
    for step in res.steps:
        title = step.get("title", f"Step {step.get('number','')}")
        st.markdown(f"**{title}**")
        st.text(step["description"])
        if step.get("latex"):
            try:
                st.latex(step["latex"].replace("$", ""))
            except Exception:
                st.code(step["latex"])
        st.divider()

st.divider()
cc1, cc2 = st.columns(2)
if cc1.button("📊 Open full Visualizer", type="primary"):
    st.switch_page("pages/3_Visualizer.py")
if cc2.button("📄 Generate report"):
    st.switch_page("pages/5_Report.py")
