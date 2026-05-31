"""
app.py — BeamEdu entry point (Home / Introduction)
==================================================
Run with:  streamlit run app.py

This is the landing page.  Streamlit auto-discovers the pages/ folder and
builds the sidebar navigation.  All shared state lives in utils.session.S.
"""

import streamlit as st

from utils.session import S
from utils import analytics
from utils.ui import apply_theme, hero

st.set_page_config(
    page_title="BeamEdu — SFD & BMD Teaching Tool",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)

S.init()
apply_theme()
analytics.log_event(S.student_id, "page_view", "home")


# ──────────────────────────────────────────────
#  Header
# ──────────────────────────────────────────────
hero(
    "BeamEdu",
    subtitle=(
        "Learn Shear Force &amp; Bending Moment Diagrams — "
        "one step at a time, exactly as you'd solve them by hand."
    ),
    kicker="Civil Engineering · SFD &amp; BMD Teaching Tool",
    icon="📐",
)

st.markdown(
    """
    **BeamEdu** is an interactive tool that teaches you how to analyse beams and
    construct **Shear Force Diagrams (SFD)** and **Bending Moment Diagrams (BMD)**,
    one step at a time.

    You can build any standard beam, apply any combination of loads, and watch the
    reactions, shear, and moment unfold with full worked steps — exactly as you
    would solve them by hand.
    """
)

st.divider()

# ──────────────────────────────────────────────
#  What you can do
# ──────────────────────────────────────────────
c1, c2, c3 = st.columns(3)

with c1:
    with st.container(border=True):
        st.markdown("### 🏗️ Build any beam")
        st.markdown(
            "- Simply supported\n"
            "- Cantilever (left or right)\n"
            "- Propped cantilever\n"
            "- Fixed-fixed\n"
            "- Overhanging"
        )

with c2:
    with st.container(border=True):
        st.markdown("### ⬇️ Apply any load")
        st.markdown(
            "- Point load\n"
            "- Uniformly distributed (UDL)\n"
            "- Uniformly varying (UVL)\n"
            "- Applied moment / couple"
        )

with c3:
    with st.container(border=True):
        st.markdown("### 📊 See it solved")
        st.markdown(
            "- Step-by-step reactions\n"
            "- Segment-by-segment SFD/BMD\n"
            "- Interactive diagrams\n"
            "- PDF report export"
        )

st.markdown("### 🎓 Publication-grade research layer")
r1, r2, r3 = st.columns(3)
with r1:
    with st.container(border=True):
        st.markdown("**Constructive alignment**")
        st.caption("Learning outcomes map directly to app activities, pre/post quiz evidence, and exportable measures.")
with r2:
    with st.container(border=True):
        st.markdown("**Anonymised analytics**")
        st.caption("The app stores only an 8-character session ID plus quiz and interaction records for classroom studies.")
with r3:
    with st.container(border=True):
        st.markdown("**Research dashboard**")
        st.caption("Instructors can inspect normalized gain, item statistics, Cronbach α, event counts, and a data codebook.")

st.divider()

# ──────────────────────────────────────────────
#  Theory primer
# ──────────────────────────────────────────────
with st.expander("📖 Quick theory refresher — sign convention", expanded=False):
    st.markdown(
        """
        BeamEdu uses the standard structural engineering sign convention:

        | Quantity | Positive direction |
        |---|---|
        | Position **x** | measured from the **left** end of the beam |
        | Vertical reaction **R** | **upward** |
        | Shear force **V** | **upward** on the left face of a cut |
        | Bending moment **M** | **sagging** (tension at the bottom fibre) |
        | Applied moment | **clockwise** |

        Two fundamental relationships connect load *w*, shear *V*, and moment *M*:

        $$\\frac{dV}{dx} = -w \\qquad \\frac{dM}{dx} = V$$

        These mean:
        - The **slope of the shear** diagram equals the negative of the load intensity.
        - The **slope of the moment** diagram equals the shear force.
        - The bending moment is **maximum where the shear is zero**.
        """
    )

# ──────────────────────────────────────────────
#  Getting started + session
# ──────────────────────────────────────────────
st.markdown("### 🚀 Getting started")
st.markdown(
    "1. Go to **Beam Builder** in the sidebar to set up your beam and loads.\n"
    "2. Open **Step Solver** to see the reactions and SFD/BMD worked out step by step.\n"
    "3. Use **Visualizer** to explore the diagrams interactively.\n"
    "4. Test yourself in **Quiz**, export a **Report**, and review study evidence in **Research Dashboard**."
)

st.divider()

with st.sidebar:
    st.markdown("### 👤 Session")
    sid = st.text_input("Participant code (optional)", value=S.student_id,
                        help="A pseudonymous 8-character code is stored; raw names or emails are not retained.")
    if sid and sid != S.student_id:
        S.set_student_id(sid)
    st.caption(f"Session ID: `{S.student_id}`")
    st.divider()
    st.caption("BeamEdu · Civil Engineering, KITS Ramtek")
    st.caption("Sign convention: sagging +ve, upward +ve, CW +ve")
