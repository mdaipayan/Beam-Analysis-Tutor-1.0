"""
pages/3_Visualizer.py
=====================
Fully interactive SFD / BMD exploration with Plotly.
  • Live FBD with reactions.
  • Combined SFD + BMD with hover, zoom, and a draggable section cut.
  • Optional auto-play sweep and progressive fill.
  • Critical-section table + CSV/PNG export.
"""

import time

import numpy as np
import streamlit as st

from engine import beam_fbd_figure, sfd_bmd_figure, create_combined_figure
from utils.session import S
from utils import analytics
from utils.ui import apply_theme, hero

st.set_page_config(page_title="Visualizer · BeamEdu", page_icon="📊", layout="wide")
S.init()
apply_theme()
analytics.log_event(S.student_id, "page_view", "visualizer")

hero(
    "Interactive Visualizer",
    subtitle="Explore the free-body diagram, SFD, and BMD with live readings and export-ready data.",
    kicker="Inspect · Animate · Export",
)

beam  = S.get_beam()
loads = S.get_loads()
if beam is None or not loads:
    st.info("⬅️ Configure a beam and loads in **Beam Builder** first.")
    if st.button("Go to Beam Builder"):
        st.switch_page("pages/1_Beam_Builder.py")
    st.stop()

if not S.is_solved:
    S.solve()

rxn = S.get_reactions()
res = S.get_sfdbmd()

# ── Free body diagram (with reactions) ─────────────────────────────────
st.markdown("### Free body diagram")
st.plotly_chart(beam_fbd_figure(beam, loads, reactions=rxn.reactions),
                width="stretch", config={"displayModeBar": False})

st.divider()
st.markdown("### Shear force & bending moment")

# ── Controls ───────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    cut = st.slider("Section cut  x (m)", 0.0, float(beam.length),
                    float(beam.length) / 2, step=float(beam.length) / 200)
with c2:
    fill = st.toggle("Progressive fill", value=False,
                     help="Shade only up to the cut.")
with c3:
    hog = st.toggle("Hogging up", value=False)

play = st.button("▶ Play sweep")

V_at = float(np.interp(cut, res.x, res.V))
M_at = float(np.interp(cut, res.x, res.M))
p1, p2, p3 = st.columns(3)
p1.metric("Section x", f"{cut:.3f} m")
p2.metric("Shear V(x)", f"{V_at:+.3f} kN")
p3.metric("Moment M(x)", f"{M_at:+.3f} kN·m")

area = st.empty()
if play:
    analytics.log_event(S.student_id, "sweep_played", S.beam_label)
    N = 60
    for i in range(N + 1):
        cx = beam.length * i / N
        area.plotly_chart(sfd_bmd_figure(beam, res, cut_x=cx, fill_to_cut=fill, hogging_up=hog),
                          width="stretch", config={"displayModeBar": False},
                          key=f"vsweep_{i}")
        time.sleep(0.03)
    area.plotly_chart(sfd_bmd_figure(beam, res, cut_x=cut, fill_to_cut=fill, hogging_up=hog),
                      width="stretch", config={"displayModeBar": False}, key="vsweep_final")
else:
    area.plotly_chart(sfd_bmd_figure(beam, res, cut_x=cut, fill_to_cut=fill, hogging_up=hog),
                      width="stretch", config={"displayModeBar": False}, key="vstatic")

# ── Data table & export ────────────────────────────────────────────────
with st.expander("🔢 Critical section values"):
    import pandas as pd
    rows = [{
        "x (m)": round(cs.x, 4),
        "V_left (kN)": round(cs.V_left, 4),
        "V_right (kN)": round(cs.V_right, 4),
        "M (kN·m)": round(cs.M, 4),
        "Location": cs.label,
    } for cs in res.critical]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Download V & M data (CSV)",
        data=pd.DataFrame({"x_m": res.x, "V_kN": res.V, "M_kNm": res.M}).to_csv(index=False).encode("utf-8"),
        file_name="beamedu_sfd_bmd_data.csv", mime="text/csv",
    )

with st.expander("🖼️ Static print-quality figure (for notes)"):
    fig_mpl = create_combined_figure(beam, loads, rxn.reactions, res, figsize=(9, 8), hogging_up=hog)
    st.pyplot(fig_mpl, width="stretch")

st.divider()
if st.button("📄 Generate full PDF report", type="primary"):
    st.switch_page("pages/5_Report.py")
