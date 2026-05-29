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
C_BEAM     = "#25313d"
C_SUPPORT  = "#1f5673"
C_LOAD_DN  = "#b3402f"
C_LOAD_UP  = "#3f7a42"
C_MOMENT   = "#7a4ea3"
C_REACTION = "#2f8f9d"
C_SFD      = "#1f5673"
C_SFD_FILL = "rgba(31,86,115,0.18)"
C_BMD      = "#2f8f9d"
C_BMD_FILL = "rgba(47,143,157,0.20)"
C_CUT      = "#bd8b3c"
C_GRID     = "#e9e3d6"
C_PAPER    = "#fbfaf7"
C_PANEL    = "#fffdfa"


# ══════════════════════════════════════════════════════════════════════
#  Live free-body diagram
# ══════════════════════════════════════════════════════════════════════

def beam_fbd_figure(
    beam:      Beam,
    loads:     List[AnyLoad],
    reactions: Optional[Dict[float, Dict[str, float]]] = None,
    height:    int = 340,
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

    # Scale for arrow lengths. Reactions are included when available so solved
    # diagrams do not show oversized or undersized support arrows.
    forces = [abs(l.magnitude) for l in loads if isinstance(l, PointLoad)]
    forces += [abs(l.intensity) * l.span for l in loads if isinstance(l, UDL)]
    forces += [abs(0.5 * (l.intensity_start + l.intensity_end) * l.span) for l in loads if isinstance(l, UVL)]
    if reactions:
        forces += [abs(r.get("Fy", 0.0)) for r in reactions.values()]
    fmax = max(forces) if forces else 1.0

    def alen(f: float) -> float:
        return 0.38 + 0.50 * abs(f) / fmax    # arrow length in y-units

    # ── Beam line ──────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=[0, L], y=[-0.035, -0.035], mode="lines",
        line=dict(color="rgba(37,49,61,0.18)", width=14),
        hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[0, L], y=[0, 0], mode="lines",
        line=dict(color=C_BEAM, width=10),
        hovertemplate="Beam span<br>x = %{x:.2f} m<extra></extra>", showlegend=False,
    ))

    _add_dimension_line(fig, L)

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

    tick_positions = _fbd_tick_positions(beam, loads)
    fig.update_layout(
        height=height,
        margin=dict(l=26, r=26, t=44, b=38),
        plot_bgcolor=C_PANEL, paper_bgcolor=C_PAPER,
        showlegend=False,
        hovermode="closest",
        font=dict(family="Inter, system-ui, sans-serif", color="#1a2733"),
        xaxis=dict(
            range=[-0.10 * L, 1.10 * L], showgrid=True, gridcolor=C_GRID,
            zeroline=False, title="Position x (m)", fixedrange=True,
            tickmode="array", tickvals=tick_positions,
            ticktext=[_fmt_x(x) for x in tick_positions],
            ticks="outside", tickfont=dict(size=11, color="#5f6f7a"),
        ),
        yaxis=dict(range=[-1.85, 1.75], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True),
        title=dict(
            text="Beam and loads preview", x=0.02, xanchor="left",
            font=dict(size=16, color="#1f5673"),
        ),
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

def _fmt_x(x: float) -> str:
    """Compact x-position label for the FBD axis."""
    if abs(x - round(x)) < 1e-9:
        return f"{int(round(x))}"
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _fbd_tick_positions(beam: Beam, loads: List[AnyLoad]) -> List[float]:
    """Important x positions to label on the free-body diagram."""
    positions = {0.0, float(beam.length)}
    positions.update(float(s.position) for s in beam.supports)
    for ld in loads:
        if isinstance(ld, (PointLoad, AppliedMoment)):
            positions.add(float(ld.position))
        elif isinstance(ld, (UDL, UVL)):
            positions.add(float(ld.start))
            positions.add(float(ld.end))
    return sorted(positions)


def _add_dimension_line(fig: go.Figure, L: float) -> None:
    """Add a span dimension line below the beam."""
    y = -1.30
    fig.add_shape(
        type="line", x0=0, x1=L, y0=y, y1=y,
        line=dict(color="#8c9aa5", width=1.5, dash="dot"),
        layer="below",
    )
    for x in (0, L):
        fig.add_shape(
            type="line", x0=x, x1=x, y0=y - 0.12, y1=y + 0.12,
            line=dict(color="#8c9aa5", width=1.5), layer="below",
        )
    fig.add_annotation(
        x=L / 2, y=y - 0.18, text=f"L = {L:.2f} m", showarrow=False,
        font=dict(color="#667783", size=12), bgcolor="rgba(255,253,250,0.85)",
    )


def _add_support(fig: go.Figure, x: float, kind: SupportType, L: float) -> None:
    tri = min(max(0.12, 0.045 * L), 0.16 * L)
    label = kind.value.replace("_", " ").title()
    if kind in (SupportType.PIN, SupportType.ROLLER):
        fig.add_trace(go.Scatter(
            x=[x - tri, x, x + tri, x - tri], y=[-0.58, 0, -0.58, -0.58],
            mode="lines", line=dict(color=C_SUPPORT, width=2.5),
            fill="toself", fillcolor=("#ffffff" if kind == SupportType.ROLLER else "rgba(31,86,115,0.18)"),
            hovertemplate=f"{label} support<br>x = {x:.2f} m<extra></extra>", showlegend=False,
        ))
        if kind == SupportType.ROLLER:
            fig.add_trace(go.Scatter(
                x=[x - tri * 0.35, x + tri * 0.35], y=[-0.75, -0.75], mode="markers",
                marker=dict(color="#ffffff", size=8, line=dict(color=C_SUPPORT, width=1.5)),
                hoverinfo="skip", showlegend=False,
            ))
    elif kind == SupportType.FIXED:
        fig.add_trace(go.Scatter(
            x=[x, x], y=[-0.72, 0.72], mode="lines",
            line=dict(color=C_SUPPORT, width=7),
            hovertemplate=f"Fixed support<br>x = {x:.2f} m<extra></extra>", showlegend=False,
        ))
        hatch_x = [x, x - (0.035 * L if x <= L / 2 else -0.035 * L)]
        for yi in np.linspace(-0.62, 0.62, 6):
            fig.add_trace(go.Scatter(
                x=hatch_x, y=[yi - 0.08, yi + 0.08], mode="lines",
                line=dict(color=C_SUPPORT, width=1), hoverinfo="skip", showlegend=False,
            ))
    fig.add_annotation(
        x=x, y=-0.98, text=f"{label}<br>x={x:.2f} m", showarrow=False,
        align="center", font=dict(color=C_SUPPORT, size=11),
        bgcolor="rgba(255,253,250,0.88)", bordercolor="rgba(31,86,115,0.18)", borderpad=3,
    )


def _add_point_load(fig: go.Figure, ld: PointLoad, alen: float) -> None:
    down = ld.magnitude > 0
    color = C_LOAD_DN if down else C_LOAD_UP
    y0 = alen if down else -alen
    fig.add_annotation(
        x=ld.position, y=0, ax=ld.position, ay=y0, xref="x", yref="y",
        axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.25,
        arrowwidth=2.4, arrowcolor=color,
    )
    fig.add_annotation(
        x=ld.position, y=y0, text=f"{ld.label or 'P'} = {abs(ld.magnitude):.1f} kN",
        showarrow=False, yshift=(16 if down else -16), font=dict(color=color, size=12),
        bgcolor="rgba(255,253,250,0.92)", bordercolor="rgba(0,0,0,0.08)", borderpad=3,
    )


def _add_reaction_arrow(fig: go.Figure, x: float, fy: float, alen: float) -> None:
    up = fy > 0
    # reaction arrows drawn below the beam, pointing toward it
    y0 = -alen if up else alen
    fig.add_annotation(
        x=x, y=0, ax=x, ay=y0, xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=3, arrowsize=1.25, arrowwidth=2.6,
        arrowcolor=C_REACTION,
    )
    fig.add_annotation(
        x=x, y=y0, text=f"R = {fy:.1f} kN", showarrow=False,
        yshift=(-16 if up else 16), font=dict(color=C_REACTION, size=12, family="Arial Black"),
        bgcolor="rgba(255,253,250,0.92)", bordercolor="rgba(47,143,157,0.28)", borderpad=3,
    )


def _add_udl(fig: go.Figure, ld: UDL, alen: float, L: float) -> None:
    down = ld.intensity > 0
    color = C_LOAD_DN if down else C_LOAD_UP
    y0 = alen if down else -alen
    n = max(3, int((ld.end - ld.start) / (0.075 * L)) + 1)
    xs = np.linspace(ld.start, ld.end, n)
    fig.add_trace(go.Scatter(
        x=[ld.start, ld.end, ld.end, ld.start, ld.start],
        y=[0, 0, y0, y0, 0],
        mode="lines", fill="toself",
        line=dict(color="rgba(0,0,0,0)", width=0),
        fillcolor=("rgba(179,64,47,0.10)" if down else "rgba(63,122,66,0.10)"),
        hovertemplate=(
            f"UDL {ld.label or 'w'}<br>"
            f"w = {ld.intensity:.2f} kN/m<br>x = {ld.start:.2f}–{ld.end:.2f} m<extra></extra>"
        ),
        showlegend=False,
    ))
    for xi in xs:
        fig.add_annotation(x=xi, y=0, ax=xi, ay=y0, xref="x", yref="y",
                           axref="x", ayref="y", showarrow=True, arrowhead=3,
                           arrowsize=0.95, arrowwidth=1.6, arrowcolor=color)
    fig.add_trace(go.Scatter(x=[ld.start, ld.end], y=[y0, y0], mode="lines",
                             line=dict(color=color, width=2.5), hoverinfo="skip", showlegend=False))
    fig.add_annotation(x=(ld.start + ld.end) / 2, y=y0,
                       text=f"{ld.label or 'w'} = {ld.intensity:.1f} kN/m",
                       showarrow=False, yshift=(16 if down else -16),
                       font=dict(color=color, size=12),
                       bgcolor="rgba(255,253,250,0.92)", bordercolor="rgba(0,0,0,0.08)", borderpad=3)


def _add_uvl(fig: go.Figure, ld: UVL, alen_fn, L: float) -> None:
    down = (ld.intensity_start + ld.intensity_end) > 0
    color = C_LOAD_DN if down else C_LOAD_UP
    n = max(4, int((ld.end - ld.start) / (0.065 * L)) + 1)
    xs = np.linspace(ld.start, ld.end, n)
    fmax = max(abs(ld.intensity_start), abs(ld.intensity_end), 1e-9)
    ys = []
    for xi in xs:
        inten = ld.intensity_at(xi)
        a = alen_fn(abs(inten)) * (abs(inten) / fmax)
        y0 = a if down else -a
        ys.append(y0)
    fig.add_trace(go.Scatter(
        x=list(xs) + [ld.end, ld.start, ld.start],
        y=list(ys) + [0, 0, ys[0]],
        mode="lines", fill="toself",
        line=dict(color=color, width=2.5),
        fillcolor=("rgba(179,64,47,0.10)" if down else "rgba(63,122,66,0.10)"),
        hovertemplate=(
            f"UVL {ld.label or 'w'}<br>"
            f"w: {ld.intensity_start:.2f} → {ld.intensity_end:.2f} kN/m<br>"
            f"x = {ld.start:.2f}–{ld.end:.2f} m<extra></extra>"
        ),
        showlegend=False,
    ))
    for xi, y0 in zip(xs, ys):
        inten = ld.intensity_at(xi)
        if abs(inten) > 1e-9:
            fig.add_annotation(x=xi, y=0, ax=xi, ay=y0, xref="x", yref="y",
                               axref="x", ayref="y", showarrow=True, arrowhead=3,
                               arrowsize=0.9, arrowwidth=1.4, arrowcolor=color)
    fig.add_annotation(x=(ld.start + ld.end) / 2, y=max(ys + [0]) if down else min(ys + [0]),
                       text=f"{ld.label or 'w'}: {ld.intensity_start:.0f} → {ld.intensity_end:.0f} kN/m",
                       showarrow=False, yshift=(16 if down else -16), font=dict(color=color, size=12),
                       bgcolor="rgba(255,253,250,0.92)", bordercolor="rgba(0,0,0,0.08)", borderpad=3)


def _add_moment(fig: go.Figure, ld: AppliedMoment) -> None:
    cw = ld.magnitude > 0
    t = np.linspace(0, 1.5 * np.pi, 48)
    r = 0.34
    xs = ld.position + r * np.cos(t) * (1 if cw else -1)
    ys = 0.0 + r * np.sin(t)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
                             line=dict(color=C_MOMENT, width=3),
                             hovertemplate=(
                                 f"Applied moment {ld.label or 'M₀'}<br>"
                                 f"M = {ld.magnitude:.2f} kN·m<br>x = {ld.position:.2f} m<extra></extra>"
                             ), showlegend=False))
    fig.add_annotation(x=ld.position, y=r + 0.18,
                       text=f"{ld.label or 'M₀'} = {abs(ld.magnitude):.1f} kN·m {'↻' if cw else '↺'}",
                       showarrow=False, font=dict(color=C_MOMENT, size=12),
                       bgcolor="rgba(255,253,250,0.92)", bordercolor="rgba(0,0,0,0.08)", borderpad=3)
