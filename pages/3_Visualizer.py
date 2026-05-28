"""
pages/3_Visualizer.py
=====================
Interactive SFD / BMD visualisation.
  • Combined matplotlib figure (FBD + SFD + BMD)
  • Section probe: a slider to read V(x) and M(x) at any cut
  • Toggle for BMD convention (sagging-up vs hogging-up)
"""

import numpy as np
import streamlit as st

from engine import create_combined_figure
from utils.session import S
from utils import analytics

st.set_page_config(page_title="Visualizer · BeamEdu", page_icon="📊", layout="wide")
S.init()
analytics.log_event(S.student_id, "page_view", "visualizer")

st.title("📊 Interactive Visualizer")

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

# ── Controls ───────────────────────────────────────────────────────────
ctrl1, ctrl2 = st.columns([1, 2])
with ctrl1:
    hogging_up = st.toggle("BMD: hogging shown upward", value=False,
                           help="Switch between the two common BMD drawing conventions.")
with ctrl2:
    x_probe = st.slider("Section probe — read V and M at x =", 0.0, float(beam.length),
                        float(beam.length) / 2, step=float(beam.length) / 200)

# Interpolate V and M at the probe position
V_at = float(np.interp(x_probe, res.x, res.V))
M_at = float(np.interp(x_probe, res.x, res.M))

p1, p2, p3 = st.columns(3)
p1.metric("Section x", f"{x_probe:.3f} m")
p2.metric("Shear V(x)", f"{V_at:+.3f} kN")
p3.metric("Moment M(x)", f"{M_at:+.3f} kN·m")

# ── Combined figure ────────────────────────────────────────────────────
fig = create_combined_figure(beam, loads, rxn.reactions, res, figsize=(10, 9),
                             hogging_up=hogging_up)

# Add probe line to the figure axes (SFD and BMD are axes[1] and [2])
for ax in fig.axes[1:]:
    ax.axvline(x_probe, color="#7030A0", lw=1.0, ls="-.", alpha=0.8, zorder=10)

st.pyplot(fig, use_container_width=True)

# ── Data table & export ────────────────────────────────────────────────
with st.expander("🔢 Critical section values"):
    import pandas as pd
    rows = []
    for cs in res.critical:
        rows.append({
            "x (m)":       round(cs.x, 4),
            "V_left (kN)": round(cs.V_left, 4),
            "V_right (kN)": round(cs.V_right, 4),
            "M (kN·m)":    round(cs.M, 4),
            "Location":    cs.label,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download V & M data (CSV)",
        data=pd.DataFrame({
            "x_m": res.x, "V_kN": res.V, "M_kNm": res.M
        }).to_csv(index=False).encode("utf-8"),
        file_name="beamedu_sfd_bmd_data.csv",
        mime="text/csv",
    )

st.divider()
if st.button("📄 Generate full PDF report", type="primary"):
    st.switch_page("pages/5_Report.py")
