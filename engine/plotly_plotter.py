"""
engine/plotly_plotter.py
========================
Interactive Plotly figures for BeamEdu's live, student-facing pages.

These complement the static matplotlib plotter (used for the PDF report).
Plotly gives smooth hover, zoom, and a draggable/animatable section cut.

Public API
----------
  beam_fbd_figure(beam, loads, reactions=None)
      Live free-body diagram. Redraws instantly as loads are added.
      Reactions are optional — pass None while still building.

  sfd_bmd_figure(beam, result, cut_x=None, fill_to_cut=False, hogging_up=False)
      Combined 3-row figure (FBD strip + SFD + BMD) with an optional
      vertical "cut" line. When fill_to_cut is True, the V and M areas are
      shaded only up to cut_x — the progressive-reveal teaching effect.

  single_diagram_figure(...)
      One SFD or BMD panel on its own (used for staged step display).

All figures use the BeamEdu palette and a clean, education-friendly layout.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .beam import Beam, SupportType
from .loads import AnyLoad, PointLoad, UDL, UVL, AppliedMoment
from .sfd_bmd import SFDBMDResult

# ── Palette (matches matplotlib plotter + config.toml accent) ──────────
C_BEAM     = "#2d2d2d"
C_SUPPORT  = "#4472C4"
C_LOAD_DN  = "#C00000"
C_LOAD_UP  = "#375623"
C_MOMENT   = "#7030A0"
C_REACTION = "#215868"
C_SFD      = "#1f77b4"
C_SFD_FILL = "rgba(107,174,214,0.45)"
C_BMD      = "#2ca02c"
C_BMD_FILL = "rgba(116,196,118,0.45)"
C_CUT      = "#7030A0"
C_GRID     = "#e8e8e8"


# ══════════════════════════════════════════════════════════════════════
#  Live free-body diagram
# ══════════════════════════════════════════════════════════════════════

def beam_fbd_figure(
    beam:      Beam,
    loads:     List[AnyLoad],
    reactions: Optional[Dict[float, Dict[str, float]]] = None,
    height:    int = 280,
) -> go.Figure:
    """
    Build an interactive free-body diagram.

    Parameters
    ----------
    beam      : Beam geometry.
    loads     : Applied loads (may be empty — draws bare beam).
    reactions : Optional reaction dict; if given, reaction arrows are drawn.
    height    : Figure height in px.
    """
    L = beam.length
    fig = go.Figure()

    # Scale for arrow lengths
    forces = [abs(l.magnitude) for l in loads if isinstance(l, PointLoad)]
    forces += [abs(l.intensity) * l.span for l in loads if isinstance(l, UDL)]
    forces += [abs(0.5 * (l.intensity_start + l.intensity_end) * l.span) for l in loads if isinstance(l, UVL)]
    fmax = max(forces) if forces else 1.0

    def alen(f: float) -> float:
        return 0.35 + 0.45 * abs(f) / fmax    # arrow length in y-units

    # ── Beam line ──────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=[0, L], y=[0, 0], mode="lines",
        line=dict(color=C_BEAM, width=8),
        hoverinfo="skip", showlegend=False,
    ))

    # ── Supports ───────────────────────────────────────────────────────
    for s in beam.supports:
        _add_support(fig, s.position, s.support_type, L)

    # ── Loads ──────────────────────────────────────────────────────────
    for ld in loads:
        if isinstance(ld, PointLoad):
            _add_point_load(fig, ld, alen(ld.magnitude))
        elif isinstance(ld, UDL):
            _add_udl(fig, ld, alen(ld.intensity * ld.span), L)
        elif isinstance(ld, UVL):
            _add_uvl(fig, ld, alen, L)
        elif isinstance(ld, AppliedMoment):
            _add_moment(fig, ld)

    # ── Reactions (optional) ───────────────────────────────────────────
    if reactions:
        for xr, r in reactions.items():
            fy = r.get("Fy", 0.0)
            if abs(fy) > 1e-9:
                _add_reaction_arrow(fig, xr, fy, alen(fy))
            if abs(r.get("M", 0.0)) > 1e-9:
                fig.add_annotation(
                    x=xr, y=0.95, text=f"M={r['M']:.1f} kN·m",
                    showarrow=False, font=dict(color=C_REACTION, size=11),
                )

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False,
        xaxis=dict(range=[-0.08 * L, 1.08 * L], showgrid=False,
                   zeroline=False, title="x (m)", fixedrange=True),
        yaxis=dict(range=[-1.6, 1.6], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True),
        title=dict(text="Free Body Diagram", x=0.5, font=dict(size=14)),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════
#  Combined SFD + BMD with optional progressive fill to a cut
# ══════════════════════════════════════════════════════════════════════

def sfd_bmd_figure(
    beam:        Beam,
    result:      SFDBMDResult,
    cut_x:       Optional[float] = None,
    fill_to_cut: bool = False,
    hogging_up:  bool = False,
    height:      int  = 620,
) -> go.Figure:
    """
    Two-row interactive figure: SFD (top) and BMD (bottom).

    Parameters
    ----------
    cut_x       : if given, draws a vertical cut line on both panels and a
                  marker dot with the V / M value at that section.
    fill_to_cut : if True, only shade the diagram up to cut_x (progressive
                  reveal); otherwise shade the whole diagram.
    hogging_up  : invert BMD sign (alternate convention).
    """
    x = result.x
    V = result.V
    M = -result.M if hogging_up else result.M

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
        subplot_titles=("Shear Force Diagram  V(x)", "Bending Moment Diagram  M(x)"),
    )

    # Decide fill mask
    if fill_to_cut and cut_x is not None:
        mask = x <= cut_x
        xf = x[mask]
        Vf = V[mask]
        Mf = M[mask]
    else:
        xf, Vf, Mf = x, V, M

    # ── SFD ────────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=xf, y=Vf, mode="lines", line=dict(color=C_SFD, width=2),
        fill="tozeroy", fillcolor=C_SFD_FILL, name="V(x)",
        hovertemplate="x=%{x:.2f} m<br>V=%{y:.2f} kN<extra></extra>",
    ), row=1, col=1)
    # full outline (faint) when filling progressively, for context
    if fill_to_cut and cut_x is not None:
        fig.add_trace(go.Scatter(
            x=x, y=V, mode="lines", line=dict(color=C_SFD, width=1, dash="dot"),
            opacity=0.35, hoverinfo="skip", showlegend=False,
        ), row=1, col=1)
    fig.add_hline(y=0, line=dict(color="#555", width=1, dash="dash"), row=1, col=1)

    # ── BMD ────────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=xf, y=Mf, mode="lines", line=dict(color=C_BMD, width=2),
        fill="tozeroy", fillcolor=C_BMD_FILL, name="M(x)",
        hovertemplate="x=%{x:.2f} m<br>M=%{y:.2f} kN·m<extra></extra>",
    ), row=2, col=1)
    if fill_to_cut and cut_x is not None:
        fig.add_trace(go.Scatter(
            x=x, y=M, mode="lines", line=dict(color=C_BMD, width=1, dash="dot"),
            opacity=0.35, hoverinfo="skip", showlegend=False,
        ), row=2, col=1)
    fig.add_hline(y=0, line=dict(color="#555", width=1, dash="dash"), row=2, col=1)

    # ── Cut line + markers ─────────────────────────────────────────────
    if cut_x is not None:
        V_cut = float(np.interp(cut_x, x, V))
        M_cut = float(np.interp(cut_x, x, M))
        for row in (1, 2):
            fig.add_vline(x=cut_x, line=dict(color=C_CUT, width=1.5, dash="dashdot"),
                          row=row, col=1)
        fig.add_trace(go.Scatter(
            x=[cut_x], y=[V_cut], mode="markers+text",
            marker=dict(color=C_CUT, size=10),
            text=[f" {V_cut:.2f}"], textposition="top right",
            hoverinfo="skip", showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=[cut_x], y=[M_cut], mode="markers+text",
            marker=dict(color=C_CUT, size=10),
            text=[f" {M_cut:.2f}"], textposition="top right",
            hoverinfo="skip", showlegend=False,
        ), row=2, col=1)

    # ── Mark critical values ───────────────────────────────────────────
    for cs in result.critical:
        if abs(cs.M) > 1e-6:
            my = -cs.M if hogging_up else cs.M
            fig.add_trace(go.Scatter(
                x=[cs.x], y=[my], mode="markers",
                marker=dict(color=C_BMD, size=5),
                hovertemplate=f"{cs.label}<br>M=%{{y:.2f}} kN·m<extra></extra>",
                showlegend=False,
            ), row=2, col=1)

    fig.update_layout(
        height=height, margin=dict(l=50, r=20, t=40, b=40),
        plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=C_GRID, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=C_GRID, title_text="V (kN)", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=C_GRID, title_text="M (kN·m)", row=2, col=1)
    fig.update_xaxes(title_text="x (m)", row=2, col=1)
    return fig


def single_diagram_figure(
    result: SFDBMDResult,
    which:  str = "V",
    cut_x:  Optional[float] = None,
    fill_to_cut: bool = False,
    hogging_up: bool = False,
    height: int = 320,
) -> go.Figure:
    """One SFD ('V') or BMD ('M') panel — used for staged single-diagram display."""
    x = result.x
    if which == "V":
        y = result.V; color = C_SFD; fillc = C_SFD_FILL; ylab = "V (kN)"; title = "Shear Force V(x)"
    else:
        y = -result.M if hogging_up else result.M
        color = C_BMD; fillc = C_BMD_FILL; ylab = "M (kN·m)"; title = "Bending Moment M(x)"

    if fill_to_cut and cut_x is not None:
        mask = x <= cut_x; xf, yf = x[mask], y[mask]
    else:
        xf, yf = x, y

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xf, y=yf, mode="lines", line=dict(color=color, width=2),
                             fill="tozeroy", fillcolor=fillc,
                             hovertemplate="x=%{x:.2f}<br>%{y:.2f}<extra></extra>"))
    if fill_to_cut and cut_x is not None:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines",
                                 line=dict(color=color, width=1, dash="dot"),
                                 opacity=0.35, hoverinfo="skip"))
    fig.add_hline(y=0, line=dict(color="#555", width=1, dash="dash"))
    if cut_x is not None:
        fig.add_vline(x=cut_x, line=dict(color=C_CUT, width=1.5, dash="dashdot"))
        yc = float(np.interp(cut_x, x, y))
        fig.add_trace(go.Scatter(x=[cut_x], y=[yc], mode="markers+text",
                                 marker=dict(color=C_CUT, size=10),
                                 text=[f" {yc:.2f}"], textposition="top right",
                                 hoverinfo="skip"))
    fig.update_layout(height=height, margin=dict(l=50, r=20, t=36, b=36),
                      plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
                      title=dict(text=title, x=0.5, font=dict(size=13)))
    fig.update_xaxes(showgrid=True, gridcolor=C_GRID, title_text="x (m)")
    fig.update_yaxes(showgrid=True, gridcolor=C_GRID, title_text=ylab)
    return fig


# ══════════════════════════════════════════════════════════════════════
#  Internal shape helpers (annotations & traces)
# ══════════════════════════════════════════════════════════════════════

def _add_support(fig: go.Figure, x: float, kind: SupportType, L: float) -> None:
    tri = 0.045 * L
    if kind in (SupportType.PIN, SupportType.ROLLER):
        fig.add_trace(go.Scatter(
            x=[x - tri, x, x + tri, x - tri], y=[-0.55, 0, -0.55, -0.55],
            mode="lines", line=dict(color=C_SUPPORT, width=2),
            fill="toself", fillcolor=("white" if kind == SupportType.ROLLER else "rgba(68,114,196,0.3)"),
            hoverinfo="text", text=kind.value, showlegend=False,
        ))
        if kind == SupportType.ROLLER:
            fig.add_trace(go.Scatter(
                x=[x], y=[-0.72], mode="markers",
                marker=dict(color="white", size=8, line=dict(color=C_SUPPORT, width=1.5)),
                hoverinfo="skip", showlegend=False,
            ))
    elif kind == SupportType.FIXED:
        fig.add_trace(go.Scatter(
            x=[x, x], y=[-0.7, 0.7], mode="lines",
            line=dict(color=C_SUPPORT, width=6),
            hoverinfo="text", text="fixed", showlegend=False,
        ))


def _add_point_load(fig: go.Figure, ld: PointLoad, alen: float) -> None:
    down = ld.magnitude > 0
    color = C_LOAD_DN if down else C_LOAD_UP
    y0 = alen if down else -alen
    fig.add_annotation(
        x=ld.position, y=0, ax=ld.position, ay=y0, xref="x", yref="y",
        axref="x", ayref="y", showarrow=True, arrowhead=2, arrowsize=1.3,
        arrowwidth=2, arrowcolor=color,
    )
    fig.add_annotation(
        x=ld.position, y=y0, text=f"{ld.label or 'P'}={abs(ld.magnitude):.1f} kN",
        showarrow=False, yshift=(14 if down else -14), font=dict(color=color, size=11),
    )


def _add_reaction_arrow(fig: go.Figure, x: float, fy: float, alen: float) -> None:
    up = fy > 0
    # reaction arrows drawn below the beam, pointing toward it
    y0 = -alen if up else alen
    fig.add_annotation(
        x=x, y=0, ax=x, ay=y0, xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowsize=1.3, arrowwidth=2.2,
        arrowcolor=C_REACTION,
    )
    fig.add_annotation(
        x=x, y=y0, text=f"R={fy:.1f} kN", showarrow=False,
        yshift=(-14 if up else 14), font=dict(color=C_REACTION, size=11, family="Arial Black"),
    )


def _add_udl(fig: go.Figure, ld: UDL, alen: float, L: float) -> None:
    down = ld.intensity > 0
    color = C_LOAD_DN if down else C_LOAD_UP
    y0 = alen if down else -alen
    n = max(3, int((ld.end - ld.start) / (0.06 * L)) + 1)
    xs = np.linspace(ld.start, ld.end, n)
    for xi in xs:
        fig.add_annotation(x=xi, y=0, ax=xi, ay=y0, xref="x", yref="y",
                           axref="x", ayref="y", showarrow=True, arrowhead=2,
                           arrowsize=1, arrowwidth=1.3, arrowcolor=color)
    fig.add_trace(go.Scatter(x=[ld.start, ld.end], y=[y0, y0], mode="lines",
                             line=dict(color=color, width=2), hoverinfo="skip", showlegend=False))
    fig.add_annotation(x=(ld.start + ld.end) / 2, y=y0,
                       text=f"{ld.label or 'w'}={ld.intensity:.1f} kN/m",
                       showarrow=False, yshift=(14 if down else -14),
                       font=dict(color=color, size=11))


def _add_uvl(fig: go.Figure, ld: UVL, alen_fn, L: float) -> None:
    down = (ld.intensity_start + ld.intensity_end) > 0
    color = C_LOAD_DN if down else C_LOAD_UP
    n = max(4, int((ld.end - ld.start) / (0.05 * L)) + 1)
    xs = np.linspace(ld.start, ld.end, n)
    fmax = max(abs(ld.intensity_start), abs(ld.intensity_end), 1e-9)
    ys = []
    for xi in xs:
        inten = ld.intensity_at(xi)
        a = alen_fn(abs(inten) / fmax * fmax) * (abs(inten) / fmax)
        y0 = a if down else -a
        ys.append(y0)
        if abs(inten) > 1e-9:
            fig.add_annotation(x=xi, y=0, ax=xi, ay=y0, xref="x", yref="y",
                               axref="x", ayref="y", showarrow=True, arrowhead=2,
                               arrowsize=0.9, arrowwidth=1.2, arrowcolor=color)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=2),
                             hoverinfo="skip", showlegend=False))
    fig.add_annotation(x=(ld.start + ld.end) / 2, y=max(ys + [0]) if down else min(ys + [0]),
                       text=f"{ld.label or 'w'}:{ld.intensity_start:.0f}→{ld.intensity_end:.0f} kN/m",
                       showarrow=False, yshift=(16 if down else -16), font=dict(color=color, size=10))


def _add_moment(fig: go.Figure, ld: AppliedMoment) -> None:
    cw = ld.magnitude > 0
    t = np.linspace(0, 1.5 * np.pi, 40)
    r = 0.30
    xs = ld.position + r * np.cos(t) * (1 if cw else -1)
    ys = 0.0 + r * np.sin(t)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
                             line=dict(color=C_MOMENT, width=2.5),
                             hoverinfo="skip", showlegend=False))
    fig.add_annotation(x=ld.position, y=r + 0.15,
                       text=f"{ld.label or 'M₀'}={abs(ld.magnitude):.1f} kN·m {'↻' if cw else '↺'}",
                       showarrow=False, font=dict(color=C_MOMENT, size=11))
