"""
pages/1_Beam_Builder.py
=======================
Configure the beam (type, length, supports) and add loads.
Supports loading from preset templates or building from scratch.
"""

import json
import os

import streamlit as st

from engine import (
    simply_supported, cantilever, propped_cantilever, fixed_fixed, overhanging,
    PointLoad, UDL, UVL, AppliedMoment,
    beam_fbd_figure,
)
from utils.session import S
from utils import analytics
from utils.ui import apply_theme, determinacy_pill, hero

st.set_page_config(page_title="Beam Builder · BeamEdu", page_icon="🏗️", layout="wide")
S.init()
apply_theme()
analytics.log_event(S.student_id, "page_view", "beam_builder")

hero(
    "Beam Builder",
    subtitle="Set the support conditions, add loads, and keep an always-live free-body diagram in view.",
    kicker="Build · Validate · Solve",
    icon="🏗️",
    size="large",
)

_DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "templates.json")


# ──────────────────────────────────────────────
#  LIVE DIAGRAM — pinned at the top, redraws on every change
# ──────────────────────────────────────────────
def _render_live_fbd():
    beam = S.get_beam()
    if beam is None:
        st.info("👇 Choose a beam type below and the free-body diagram will appear here, updating live as you add loads.")
        return
    loads = S.get_loads()
    # Show reactions on the diagram once solved, otherwise just the applied loads
    reactions = None
    if S.is_solved:
        rxn = S.get_reactions()
        reactions = rxn.reactions if rxn else None
    fig = beam_fbd_figure(beam, loads, reactions=reactions)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    if loads and not S.is_solved:
        st.caption("🔵 Arrows above the beam are applied loads. Solve to see the reactions (in teal) appear.")
    elif S.is_solved:
        st.caption("🟦 Teal arrows are the support reactions found from equilibrium.")

with st.container(border=True):
    _render_live_fbd()


# ──────────────────────────────────────────────
#  Preset loader
# ──────────────────────────────────────────────
def _load_templates():
    try:
        with open(_DATA, "r") as f:
            return json.load(f)["templates"]
    except Exception:
        st.warning("Could not load preset templates. You can still build a custom beam below.")
        return []


def _apply_template(tpl: dict):
    bt = tpl["beam_type"]
    L  = tpl["length"]
    p  = tpl.get("params", {})

    if bt == "simply_supported":
        beam = simply_supported(L, p.get("pin_pos", 0.0), p.get("roller_pos", L))
    elif bt == "cantilever":
        beam = cantilever(L, p.get("fixed_at", "left"))
    elif bt == "propped_cantilever":
        beam = propped_cantilever(L, p.get("fixed_at", "left"))
    elif bt == "fixed_fixed":
        beam = fixed_fixed(L)
    elif bt == "overhanging":
        beam = overhanging(L, p["pin_pos"], p["roller_pos"])
    else:
        return

    S.set_beam(beam, label=tpl["name"])
    S.clear_loads()
    for ld in tpl["loads"]:
        S.add_load(_make_load(ld))
    analytics.log_event(S.student_id, "template_loaded", tpl["id"])


def _make_load(ld: dict):
    t = ld["type"]
    if t == "point":
        return PointLoad(ld["position"], ld["magnitude"], ld.get("label", "P"))
    if t == "udl":
        return UDL(ld["start"], ld["end"], ld["intensity"], ld.get("label", "w"))
    if t == "uvl":
        return UVL(ld["start"], ld["end"], ld["intensity_start"], ld["intensity_end"], ld.get("label", "w"))
    if t == "moment":
        return AppliedMoment(ld["position"], ld["magnitude"], ld.get("label", "M0"))
    raise ValueError(f"Unknown load type {t}")


# ──────────────────────────────────────────────
#  Tab layout
# ──────────────────────────────────────────────
tab_preset, tab_custom = st.tabs(["📚 Start from a preset", "🔧 Build from scratch"])

with tab_preset:
    templates = _load_templates()
    if not templates:
        st.warning("No templates found.")
    else:
        diff = st.radio("Filter by difficulty",
                        ["all", "beginner", "intermediate", "advanced"],
                        horizontal=True)
        shown = [t for t in templates if diff == "all" or t.get("difficulty") == diff]
        cols = st.columns(2)
        for i, tpl in enumerate(shown):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{tpl['name']}**")
                    st.caption(f"_{tpl.get('difficulty','')}_ · {tpl.get('note','')}")
                    if st.button("Load this problem", key=f"tpl_{tpl['id']}", width="stretch"):
                        _apply_template(tpl)
                        st.success(f"Loaded: {tpl['name']}")
                        st.rerun()

with tab_custom:
    st.markdown("#### 1. Choose beam type and length")
    bc1, bc2 = st.columns([3, 1])
    with bc1:
        beam_type = st.selectbox(
            "Beam type",
            ["Simply supported", "Cantilever", "Propped cantilever", "Fixed-fixed", "Overhanging"],
        )
    with bc2:
        length = st.number_input("Length L (m)", min_value=0.5, max_value=100.0, value=6.0, step=0.5)

    # Type-specific support inputs
    extra = {}
    if beam_type == "Simply supported":
        sc1, sc2 = st.columns(2)
        extra["pin_pos"]    = sc1.number_input("Pin position (m)", 0.0, float(length), 0.0, 0.25)
        extra["roller_pos"] = sc2.number_input("Roller position (m)", 0.0, float(length), float(length), 0.25)
    elif beam_type in ("Cantilever", "Propped cantilever"):
        extra["fixed_at"] = st.radio("Fixed end", ["left", "right"], horizontal=True)
    elif beam_type == "Overhanging":
        sc1, sc2 = st.columns(2)
        extra["pin_pos"]    = sc1.number_input("Pin position (m)",    0.0, float(length), float(length)*0.2, 0.25)
        extra["roller_pos"] = sc2.number_input("Roller position (m)", 0.0, float(length), float(length)*0.8, 0.25)

    if st.button("✅ Create / update beam", type="primary"):
        try:
            if beam_type == "Simply supported":
                beam = simply_supported(length, extra["pin_pos"], extra["roller_pos"])
            elif beam_type == "Cantilever":
                beam = cantilever(length, extra["fixed_at"])
            elif beam_type == "Propped cantilever":
                beam = propped_cantilever(length, extra["fixed_at"])
            elif beam_type == "Fixed-fixed":
                beam = fixed_fixed(length)
            else:
                beam = overhanging(length, extra["pin_pos"], extra["roller_pos"])
            S.set_beam(beam, label=f"Custom {beam_type}")
            S.clear_loads()
            analytics.log_event(S.student_id, "beam_created", beam_type)
            st.success(f"{beam_type} beam created (L = {length} m). Existing loads were cleared so they cannot fall outside the new span.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not create beam: {e}")

    # ── Add loads (only if a beam exists) ─────────────────────────────
    beam = S.get_beam()
    if beam is not None:
        st.divider()
        st.markdown("#### 2. Add loads")
        load_kind = st.selectbox("Load type", ["Point load", "UDL", "UVL", "Applied moment"])

        with st.form("add_load_form", clear_on_submit=True):
            if load_kind == "Point load":
                lc1, lc2, lc3 = st.columns([1.5, 1.5, 1])
                pos = lc1.number_input("Position x (m)", 0.0, float(beam.length), float(beam.length)/2, 0.25)
                mag = lc2.number_input("Magnitude (kN, +down)", value=10.0, step=1.0)
                lbl = lc3.text_input("Label", "P")
            elif load_kind == "UDL":
                lc1, lc2, lc3, lc4 = st.columns([1, 1, 1, 1])
                start = lc1.number_input("Start x (m)", 0.0, float(beam.length), 0.0, 0.25)
                end   = lc2.number_input("End x (m)",   0.0, float(beam.length), float(beam.length), 0.25)
                inten = lc3.number_input("Intensity (kN/m)", value=10.0, step=1.0)
                lbl   = lc4.text_input("Label", "w")
            elif load_kind == "UVL":
                lc1, lc2, lc3, lc4, lc5 = st.columns([1, 1, 1, 1, 1])
                start = lc1.number_input("Start x (m)", 0.0, float(beam.length), 0.0, 0.25)
                end   = lc2.number_input("End x (m)",   0.0, float(beam.length), float(beam.length), 0.25)
                w1    = lc3.number_input("w at start (kN/m)", value=0.0, step=1.0)
                w2    = lc4.number_input("w at end (kN/m)",   value=12.0, step=1.0)
                lbl   = lc5.text_input("Label", "w")
            else:  # Applied moment
                lc1, lc2, lc3 = st.columns([1.5, 1.5, 1])
                pos = lc1.number_input("Position x (m)", 0.0, float(beam.length), float(beam.length)/2, 0.25)
                mag = lc2.number_input("Magnitude (kN·m, +CW)", value=20.0, step=1.0)
                lbl = lc3.text_input("Label", "M0")

            submitted = st.form_submit_button("➕ Add load")
            if submitted:
                try:
                    if load_kind == "Point load":
                        S.add_load(PointLoad(pos, mag, lbl))
                    elif load_kind == "UDL":
                        S.add_load(UDL(start, end, inten, lbl))
                    elif load_kind == "UVL":
                        S.add_load(UVL(start, end, w1, w2, lbl))
                    else:
                        S.add_load(AppliedMoment(pos, mag, lbl))
                    st.success(f"Added {load_kind}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Invalid load: {e}")


# ──────────────────────────────────────────────
#  Current configuration summary (always visible)
# ──────────────────────────────────────────────
st.divider()
st.markdown("### 📋 Current configuration")

beam = S.get_beam()
if beam is None:
    st.info("No beam configured yet. Pick a preset or build one above.")
else:
    dsi = beam.degree_of_indeterminacy()
    st.markdown(
        f"**{S.beam_label or beam.beam_type.value.replace('_',' ').title()}** · "
        f"L = {beam.length:.2f} m · {determinacy_pill(dsi)}",
        unsafe_allow_html=True,
    )
    sup_txt = " · ".join(f"{s.support_type.value} @ {s.position:.2f} m" for s in beam.supports)
    st.caption(f"Supports: {sup_txt}")

    loads = S.get_loads()
    if not loads:
        st.warning("No loads added yet.")
    else:
        for i, ld in enumerate(loads):
            lc1, lc2 = st.columns([6, 1])
            with lc1:
                with st.container(border=True):
                    if isinstance(ld, PointLoad):
                        st.write(f"**{ld.label or 'P'}** — Point load {ld.magnitude:.2f} kN @ x = {ld.position:.2f} m")
                    elif isinstance(ld, UDL):
                        st.write(f"**{ld.label or 'w'}** — UDL {ld.intensity:.2f} kN/m, x = {ld.start:.2f}–{ld.end:.2f} m")
                    elif isinstance(ld, UVL):
                        st.write(f"**{ld.label or 'w'}** — UVL {ld.intensity_start:.2f}→{ld.intensity_end:.2f} kN/m, x = {ld.start:.2f}–{ld.end:.2f} m")
                    elif isinstance(ld, AppliedMoment):
                        d = "CW" if ld.magnitude >= 0 else "CCW"
                        st.write(f"**{ld.label or 'M0'}** — Moment {abs(ld.magnitude):.2f} kN·m ({d}) @ x = {ld.position:.2f} m")
            with lc2:
                if st.button("🗑️", key=f"del_{i}", help="Remove this load"):
                    S.remove_load(i)
                    st.rerun()

        cc1, cc2, cc3 = st.columns(3)
        if cc1.button("🧹 Clear all loads"):
            S.clear_loads()
            st.rerun()
        if cc2.button("🔎 Solve & show reactions here"):
            if S.solve():
                analytics.log_event(S.student_id, "beam_solved", S.beam_label)
                st.rerun()   # live FBD at top will now show reaction arrows
            else:
                st.error(S.last_error or "Add at least one load before solving.")
        if cc3.button("➡️ Open Step Solver", type="primary"):
            if S.solve():
                analytics.log_event(S.student_id, "beam_solved", S.beam_label)
                st.switch_page("pages/2_Step_Solver.py")
            else:
                st.error(S.last_error or "Add at least one load before solving.")
