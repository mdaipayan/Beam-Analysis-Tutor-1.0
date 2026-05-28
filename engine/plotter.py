"""
engine/plotter.py
=================
Matplotlib visualisation for BeamEdu.

Public API
----------
  plot_beam_diagram(ax, beam, loads, reactions)
      Free-body diagram: beam line, support symbols, load arrows, reaction labels.

  plot_sfd(ax, result, beam)
      Shear Force Diagram with hatch fill, zero-crossing markers, and key labels.

  plot_bmd(ax, result, beam)
      Bending Moment Diagram with hatch fill (sagging up / hogging down convention),
      key labels, and zero-moment markers.

  create_combined_figure(beam, loads, reactions, result)
      Returns a matplotlib Figure with three stacked axes:
      [0] Beam diagram, [1] SFD, [2] BMD.

Colour / style guide
--------------------
  Beam:           dark grey  (#2d2d2d)
  Supports:       steel blue (#4472C4)
  Downward loads: crimson    (#C00000)
  Upward loads:   dark green (#375623)
  Moments:        purple     (#7030A0)
  SFD fill:       cornflower (#6baed6)  positive / light salmon (#fc8d59) negative
  BMD fill:       mint green (#74c476)  sagging / light coral   (#fb6a4a) hogging
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")          # non-interactive backend; Streamlit handles display
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms
import numpy as np

from .beam import Beam, SupportType
from .loads import AnyLoad, PointLoad, UDL, UVL, AppliedMoment
from .sfd_bmd import SFDBMDResult


# ──────────────────────────────────────────────
#  Style constants
# ──────────────────────────────────────────────

_C_BEAM      = "#2d2d2d"
_C_SUPPORT   = "#4472C4"
_C_LOAD_DN   = "#C00000"
_C_LOAD_UP   = "#375623"
_C_MOMENT    = "#7030A0"
_C_REACTION  = "#215868"
_C_SFD_POS   = "#6baed6"
_C_SFD_NEG   = "#fc8d59"
_C_BMD_SAG   = "#74c476"
_C_BMD_HOG   = "#fb6a4a"
_C_GRID      = "#e0e0e0"
_C_ZERO      = "#555555"

_LW_BEAM  = 3.0
_LW_DIAG  = 1.8
_FONTSIZE = 9


# ──────────────────────────────────────────────
#  Beam free-body diagram
# ──────────────────────────────────────────────

def plot_beam_diagram(
    ax:        plt.Axes,
    beam:      Beam,
    loads:     List[AnyLoad],
    reactions: Dict[float, Dict[str, float]],
    y_beam:    float = 0.0,
) -> None:
    """
    Draw the beam, supports, applied loads, and reaction labels on `ax`.

    Parameters
    ----------
    ax        : Matplotlib Axes (already created).
    beam      : Beam object.
    loads     : Applied loads list.
    reactions : Reaction dict from solve_reactions().
    y_beam    : Vertical position of beam centreline (default 0).
    """
    L   = beam.length
    ax.set_xlim(-0.05 * L, 1.05 * L)
    ax.set_ylim(-0.55, 0.55)
    ax.set_aspect("auto")
    ax.axis("off")

    # Determine arrow scale based on maximum load
    all_forces = [abs(ld.magnitude) for ld in loads if isinstance(ld, PointLoad)]
    all_forces += [abs(ld.intensity) * ld.span for ld in loads if isinstance(ld, (UDL, UVL))]
    all_forces += [abs(r.get("Fy", 0)) for r in reactions.values()]
    max_force  = max(all_forces) if all_forces else 1.0
    arrow_h    = 0.28   # fraction of y-range per unit force → scale to max

    def _force_len(f: float) -> float:
        return 0.12 + 0.18 * abs(f) / max_force

    # ── Beam line ────────────────────────────────────────────────────────
    ax.plot([0, L], [y_beam, y_beam], color=_C_BEAM, lw=_LW_BEAM, zorder=3, solid_capstyle="butt")

    # ── Supports ─────────────────────────────────────────────────────────
    for s in beam.supports:
        xp = s.position
        if s.support_type in (SupportType.PIN, SupportType.ROLLER):
            _draw_triangle_support(ax, xp, y_beam, roller=(s.support_type == SupportType.ROLLER))
        elif s.support_type == SupportType.FIXED:
            _draw_fixed_support(ax, xp, y_beam, beam.length)

    # ── Applied loads ─────────────────────────────────────────────────────
    for ld in loads:
        if isinstance(ld, PointLoad):
            _draw_point_load(ax, ld, y_beam, _force_len(ld.magnitude))
        elif isinstance(ld, UDL):
            _draw_udl(ax, ld, y_beam, _force_len(ld.intensity))
        elif isinstance(ld, UVL):
            _draw_uvl(ax, ld, y_beam, _force_len)
        elif isinstance(ld, AppliedMoment):
            _draw_moment_arrow(ax, ld, y_beam)

    # ── Reaction labels ───────────────────────────────────────────────────
    for xr, r in sorted(reactions.items()):
        fy  = r.get("Fy", 0.0)
        m   = r.get("M",  0.0)
        if abs(fy) > 1e-9:
            direction  = "up" if fy > 0 else "down"
            arrow_dir  = 1 if fy > 0 else -1
            sign_str   = "↑" if fy > 0 else "↓"
            arr_len    = _force_len(fy) * arrow_dir
            ax.annotate(
                "",
                xy=(xr, y_beam),
                xytext=(xr, y_beam - arr_len),
                arrowprops=dict(arrowstyle="-|>", color=_C_REACTION, lw=1.4),
            )
            ax.text(
                xr, y_beam - arr_len - 0.05 * arrow_dir,
                f"R={fy:.2f} kN {sign_str}",
                ha="center", va="top" if fy > 0 else "bottom",
                fontsize=_FONTSIZE - 1, color=_C_REACTION, fontweight="bold",
            )
        if abs(m) > 1e-9:
            direction = "CW" if m > 0 else "CCW"
            ax.text(
                xr, y_beam + 0.33,
                f"M={m:.2f} kN·m ({direction})",
                ha="center", va="bottom",
                fontsize=_FONTSIZE - 1, color=_C_REACTION, style="italic",
            )

    ax.set_title("Free Body Diagram", fontsize=_FONTSIZE + 1, pad=4)


# ──────────────────────────────────────────────
#  SFD
# ──────────────────────────────────────────────

def plot_sfd(
    ax:     plt.Axes,
    result: SFDBMDResult,
    beam:   Beam,
) -> None:
    """
    Draw the Shear Force Diagram on `ax`.
    Positive area filled blue, negative area filled orange.
    """
    x, V = result.x, result.V
    _setup_diagram_axes(ax, beam.length, "Shear Force Diagram (kN)", "V (kN)")

    # Fill regions
    ax.fill_between(x, V, 0, where=(V >= 0), color=_C_SFD_POS, alpha=0.35,
                    hatch="////", label="Positive V")
    ax.fill_between(x, V, 0, where=(V <= 0), color=_C_SFD_NEG, alpha=0.35,
                    hatch="\\\\\\\\", label="Negative V")
    ax.plot(x, V, color=_C_SFD_POS, lw=_LW_DIAG, zorder=4)
    ax.axhline(0, color=_C_ZERO, lw=0.8, ls="--")

    # Label critical values
    for cs in result.critical:
        _label_value(ax, cs.x, cs.V_right, f"{cs.V_right:.2f}", _C_SFD_POS)

    # Zero crossings
    for xz in result.zero_shear_positions:
        ax.axvline(xz, color=_C_ZERO, lw=0.7, ls=":", alpha=0.7)
        ax.text(xz, 0, f"  x={xz:.2f}", va="bottom", fontsize=7, color=_C_ZERO)

    ax.legend(fontsize=7, loc="upper right", framealpha=0.6)


# ──────────────────────────────────────────────
#  BMD
# ──────────────────────────────────────────────

def plot_bmd(
    ax:     plt.Axes,
    result: SFDBMDResult,
    beam:   Beam,
    hogging_up: bool = False,
) -> None:
    """
    Draw the Bending Moment Diagram on `ax`.

    By default sagging (positive M) is drawn upward and hogging downward —
    the standard structural engineering convention.
    Set `hogging_up=True` to invert (used in some textbook traditions).

    Sagging area is filled green; hogging area filled coral.
    """
    x, M = result.x, result.M
    if hogging_up:
        M = -M   # invert for alternate convention
        title = "Bending Moment Diagram (kN·m)  [hogging +ve shown up]"
    else:
        title = "Bending Moment Diagram (kN·m)  [sagging shown up]"

    _setup_diagram_axes(ax, beam.length, title, "M (kN·m)")

    ax.fill_between(x, M, 0, where=(M >= 0), color=_C_BMD_SAG, alpha=0.35,
                    hatch="////", label="Sagging (+ve)")
    ax.fill_between(x, M, 0, where=(M <= 0), color=_C_BMD_HOG, alpha=0.35,
                    hatch="\\\\\\\\", label="Hogging (−ve)")
    ax.plot(x, M, color=_C_BMD_SAG, lw=_LW_DIAG, zorder=4)
    ax.axhline(0, color=_C_ZERO, lw=0.8, ls="--")

    for cs in result.critical:
        _label_value(ax, cs.x, cs.M, f"{cs.M:.2f}", _C_BMD_SAG)

    ax.legend(fontsize=7, loc="upper right", framealpha=0.6)


# ──────────────────────────────────────────────
#  Combined 3-panel figure
# ──────────────────────────────────────────────

def create_combined_figure(
    beam:      Beam,
    loads:     List[AnyLoad],
    reactions: Dict[float, Dict[str, float]],
    result:    SFDBMDResult,
    figsize:   Tuple[float, float] = (10.0, 9.0),
    hogging_up: bool = False,
) -> plt.Figure:
    """
    Create a 3-panel figure:
      [0] Free Body Diagram
      [1] Shear Force Diagram
      [2] Bending Moment Diagram

    Parameters
    ----------
    beam, loads, reactions, result : engine outputs.
    figsize       : (width, height) in inches.
    hogging_up    : If True, draws BMD with hogging convention upward.

    Returns
    -------
    matplotlib.figure.Figure  — ready to display in Streamlit via st.pyplot(fig)
                                 or save to PDF via fig.savefig().
    """
    fig, axes = plt.subplots(
        3, 1,
        figsize=figsize,
        gridspec_kw={"height_ratios": [1, 1.4, 1.4]},
    )
    fig.subplots_adjust(hspace=0.45)

    plot_beam_diagram(axes[0], beam, loads, reactions)
    plot_sfd(axes[1], result, beam)
    plot_bmd(axes[2], result, beam, hogging_up=hogging_up)

    # Shared x-axis label
    axes[2].set_xlabel("Position along beam  x (m)", fontsize=_FONTSIZE)

    # Beam info annotation
    dsi   = beam.degree_of_indeterminacy()
    det   = "Statically determinate" if dsi == 0 else f"Statically indeterminate (DSI = {dsi})"
    sup_desc = "  |  ".join(
        f"{s.support_type.value} @ x = {s.position:.2f} m" for s in beam.supports
    )
    fig.suptitle(
        f"BeamEdu  ·  {beam.beam_type.value.replace('_', ' ').title()}  ·  L = {beam.length:.2f} m\n"
        f"{det}  ·  {sup_desc}",
        fontsize=_FONTSIZE + 1,
        y=0.99,
    )
    return fig


# ──────────────────────────────────────────────
#  Internal drawing helpers
# ──────────────────────────────────────────────

def _setup_diagram_axes(ax: plt.Axes, length: float, title: str, ylabel: str) -> None:
    ax.set_xlim(-0.03 * length, 1.03 * length)
    ax.set_title(title, fontsize=_FONTSIZE + 1, pad=4)
    ax.set_ylabel(ylabel, fontsize=_FONTSIZE)
    ax.tick_params(labelsize=_FONTSIZE - 1)
    ax.grid(True, color=_C_GRID, lw=0.5, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _label_value(ax: plt.Axes, x: float, y: float, text: str, color: str) -> None:
    """Place a small value label near a critical point, avoiding y=0 clutter."""
    if abs(y) < 1e-6:
        return
    va  = "bottom" if y >= 0 else "top"
    off = 0.02 * (ax.get_ylim()[1] - ax.get_ylim()[0])
    ax.plot(x, y, "o", ms=3.5, color=color, zorder=5)
    ax.text(x, y + (off if y >= 0 else -off), text,
            ha="center", va=va, fontsize=7, color=color)


def _draw_triangle_support(
    ax: plt.Axes, x: float, y: float, roller: bool = False
) -> None:
    """Draw a pin (solid triangle) or roller (open triangle + dots) support."""
    h, hw = 0.10, 0.07
    triangle = plt.Polygon(
        [[x, y], [x - hw, y - h], [x + hw, y - h]],
        closed=True,
        facecolor=("white" if roller else _C_SUPPORT),
        edgecolor=_C_SUPPORT,
        lw=1.5,
        zorder=5,
    )
    ax.add_patch(triangle)
    if roller:
        # Two small circles below the triangle
        for dx in (-0.04, 0.04):
            c = plt.Circle((x + dx, y - h - 0.025), 0.018,
                            facecolor="white", edgecolor=_C_SUPPORT, lw=1.2, zorder=6)
            ax.add_patch(c)
        # Horizontal ground line
        ax.plot([x - hw - 0.02, x + hw + 0.02], [y - h - 0.05, y - h - 0.05],
                color=_C_SUPPORT, lw=1.5, zorder=4)
    else:
        ax.plot([x - hw - 0.02, x + hw + 0.02], [y - h, y - h],
                color=_C_SUPPORT, lw=1.5, zorder=4)
        # Hatch lines below
        for i in range(5):
            bx = x - hw + i * (2 * hw / 4)
            ax.plot([bx, bx - 0.025], [y - h, y - h - 0.045],
                    color=_C_SUPPORT, lw=1.0, zorder=3)


def _draw_fixed_support(
    ax: plt.Axes, x: float, y: float, beam_length: float
) -> None:
    """Draw a fixed support as a hatched wall at x = 0 or x = L."""
    wall_h = 0.30
    right_wall = (x < beam_length / 2)    # wall on the left side of beam
    xw = x - 0.025 if right_wall else x + 0.025
    ax.plot([x, x], [y - wall_h / 2, y + wall_h / 2],
            color=_C_SUPPORT, lw=3.5, solid_capstyle="butt", zorder=5)
    for i in range(6):
        yh = y - wall_h / 2 + i * (wall_h / 5)
        dx = -0.04 if right_wall else 0.04
        ax.plot([x, x + dx], [yh, yh - 0.04],
                color=_C_SUPPORT, lw=1.0, zorder=4)


def _draw_point_load(ax: plt.Axes, ld: PointLoad, y: float, arr_len: float) -> None:
    """Arrow for a concentrated load. Downward loads point down, upward up."""
    down   = ld.magnitude > 0
    color  = _C_LOAD_DN if down else _C_LOAD_UP
    y_tail = y + arr_len if down else y - arr_len
    y_head = y

    ax.annotate(
        "",
        xy=(ld.position, y_head),
        xytext=(ld.position, y_tail),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6, mutation_scale=12),
        zorder=6,
    )
    label = f"{ld.label or 'P'}\n{abs(ld.magnitude):.2f} kN"
    ax.text(
        ld.position, y_tail + (0.04 if down else -0.04),
        label,
        ha="center", va="bottom" if down else "top",
        fontsize=_FONTSIZE - 1, color=color,
    )


def _draw_udl(ax: plt.Axes, ld: UDL, y: float, arr_len: float) -> None:
    """Distributed load block with multiple arrows and a top bar."""
    down  = ld.intensity > 0
    color = _C_LOAD_DN if down else _C_LOAD_UP
    dy    = arr_len if down else -arr_len
    span  = ld.end - ld.start
    n_arr = max(3, int(span / (0.1 * (ax.get_xlim()[1] - ax.get_xlim()[0])) + 1))
    xs    = np.linspace(ld.start, ld.end, n_arr)

    for xi in xs:
        ax.annotate(
            "",
            xy=(xi, y),
            xytext=(xi, y + dy),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2, mutation_scale=9),
            zorder=5,
        )
    # Top bar
    ax.plot([ld.start, ld.end], [y + dy, y + dy], color=color, lw=1.5, zorder=5)
    ax.text(
        (ld.start + ld.end) / 2, y + dy + (0.04 if down else -0.04),
        f"{ld.label or 'w'} = {ld.intensity:.2f} kN/m",
        ha="center", va="bottom" if down else "top",
        fontsize=_FONTSIZE - 1, color=color,
    )


def _draw_uvl(ax: plt.Axes, ld: UVL, y: float, force_len_fn) -> None:
    """Triangular / trapezoidal load with varying arrow heights."""
    down  = (ld.intensity_start + ld.intensity_end) > 0
    color = _C_LOAD_DN if down else _C_LOAD_UP
    span  = ld.end - ld.start
    n_arr = max(4, int(span / (0.08 * (ax.get_xlim()[1] - ax.get_xlim()[0])) + 1))
    xs    = np.linspace(ld.start, ld.end, n_arr)
    max_intensity = max(abs(ld.intensity_start), abs(ld.intensity_end))
    if max_intensity < 1e-12:
        return

    for xi in xs:
        intensity_here = ld.intensity_at(xi)
        if abs(intensity_here) < 1e-9:
            continue
        dy = force_len_fn(intensity_here) * (1 if down else -1)
        ax.annotate(
            "",
            xy=(xi, y),
            xytext=(xi, y + dy),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=1.0, mutation_scale=8),
            zorder=5,
        )

    # Slanted top boundary
    y_start = y + force_len_fn(ld.intensity_start) * (1 if down else -1)
    y_end   = y + force_len_fn(ld.intensity_end)   * (1 if down else -1)
    ax.plot([ld.start, ld.end], [y_start, y_end], color=color, lw=1.5, zorder=5)
    ax.text(
        (ld.start + ld.end) / 2,
        max(y_start, y_end) + (0.04 if down else -0.04),
        f"{ld.label or 'w'}: {ld.intensity_start:.1f}→{ld.intensity_end:.1f} kN/m",
        ha="center", va="bottom" if down else "top",
        fontsize=_FONTSIZE - 1, color=color,
    )


def _draw_moment_arrow(ax: plt.Axes, ld: AppliedMoment, y: float) -> None:
    """Curved arrow for an applied moment."""
    cw    = ld.magnitude > 0
    color = _C_MOMENT
    theta = np.linspace(0, 1.6 * np.pi, 80)
    r     = 0.08
    xs    = ld.position + r * np.cos(theta)
    ys    = y + r * np.sin(theta) * (0.6)
    ax.plot(xs, ys, color=color, lw=1.8, zorder=6)
    # Arrowhead at the end
    end_ang = theta[-1] + (0.1 if cw else -0.1)
    ax.annotate(
        "",
        xy=(ld.position + r * np.cos(end_ang), y + r * 0.6 * np.sin(end_ang)),
        xytext=(xs[-2], ys[-2]),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4, mutation_scale=10),
        zorder=7,
    )
    direction = "↻" if cw else "↺"
    ax.text(
        ld.position, y + r * 0.6 + 0.06,
        f"{ld.label or 'M₀'} = {abs(ld.magnitude):.2f} kN·m {direction}",
        ha="center", va="bottom",
        fontsize=_FONTSIZE - 1, color=color,
    )
