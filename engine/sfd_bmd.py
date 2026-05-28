"""
engine/sfd_bmd.py
=================
Shear Force Diagram (SFD) and Bending Moment Diagram (BMD) computation.

Given the support reactions (from reactions.py), this module integrates the
loading functions analytically to produce V(x) and M(x) at every point across
the beam.

Sign convention (consistent with beam.py)
------------------------------------------
  V(x)  positive → upward shear on the left face of the cut section.
  M(x)  positive → sagging (tension at the bottom fibre).

  Contributions to V(x) from the LEFT of cut at position x:
    • Upward reaction Fy > 0 at x_r < x  → +Fy
    • Downward point load P at x_p < x   → −P
    • UDL intensity w from a to b         → see _udl_shear_at()
    • UVL                                 → see _uvl_shear_at()
    • Applied / fixed-end moments         → no contribution to V

  Contributions to M(x) from the LEFT of cut at position x:
    • Upward reaction Fy > 0 at x_r < x  → +Fy × (x − x_r)
    • Fixed-end moment reaction M (CW +ve) at x_f < x  → +M
    • Downward point load P at x_p < x   → −P × (x − x_p)
    • UDL / UVL distributed loads        → see helpers below
    • Applied CW moment M₀ at x_m < x   → +M₀

Returns
-------
  SFDBMDResult dataclass with:
    x        : np.ndarray  — evaluation positions (m)
    V        : np.ndarray  — shear force (kN)
    M        : np.ndarray  — bending moment (kN·m)
    critical : list[dict]  — key sections {x, V_left, V_right, M, label}
    steps    : list[dict]  — segment-by-segment explanation for teaching
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

from .beam import Beam
from .loads import AnyLoad, PointLoad, UDL, UVL, AppliedMoment, load_positions


# ──────────────────────────────────────────────
#  Return type
# ──────────────────────────────────────────────

@dataclass
class CriticalSection:
    """A position where V or M has a known exact value or discontinuity."""
    x:       float
    V_left:  float   # V just to the left  of x
    V_right: float   # V just to the right of x  (equal to V_left if no jump)
    M:       float   # M at x  (continuous across point loads, jumps at moments)
    label:   str     # e.g. 'Support A', 'Point load P₁', 'Max M'


@dataclass
class SFDBMDResult:
    """
    Computed SFD and BMD arrays plus teaching steps.

    Attributes
    ----------
    x        : positions along beam (m).
    V        : shear force at each x (kN).
    M        : bending moment at each x (kN·m).
    critical : list of CriticalSection objects at supports, load points, and extrema.
    steps    : step-by-step LaTeX solution for each beam segment.
    """
    x:        np.ndarray
    V:        np.ndarray
    M:        np.ndarray
    critical: List[CriticalSection] = field(default_factory=list)
    steps:    List[dict]            = field(default_factory=list)

    @property
    def V_max(self) -> float:
        return float(np.max(self.V))

    @property
    def V_min(self) -> float:
        return float(np.min(self.V))

    @property
    def M_max(self) -> float:
        return float(np.max(self.M))

    @property
    def M_min(self) -> float:
        return float(np.min(self.M))

    @property
    def zero_shear_positions(self) -> List[float]:
        """Positions where V crosses zero (approximate, for max-M locations)."""
        sign_changes = np.where(np.diff(np.sign(self.V)))[0]
        positions = []
        for i in sign_changes:
            if abs(self.V[i+1] - self.V[i]) > 1e-10:
                x_zero = self.x[i] - self.V[i] * (self.x[i+1] - self.x[i]) / (self.V[i+1] - self.V[i])
                positions.append(float(x_zero))
        return positions


# ──────────────────────────────────────────────
#  Public entry point
# ──────────────────────────────────────────────

def compute_sfd_bmd(
    beam:      Beam,
    reactions: Dict[float, Dict[str, float]],
    loads:     List[AnyLoad],
    n_points:  int = 800,
) -> SFDBMDResult:
    """
    Compute V(x) and M(x) across the full beam length.

    Parameters
    ----------
    beam : Beam
        Beam geometry.
    reactions : dict
        Output from reactions.solve_reactions(), keyed by position.
    loads : list[AnyLoad]
        Applied loads.
    n_points : int
        Number of uniformly spaced evaluation points (default 800).
        Extra points are inserted at every critical section automatically.

    Returns
    -------
    SFDBMDResult
    """
    # ── Build evaluation array (uniform + critical positions) ────────────
    x_uniform   = np.linspace(0.0, beam.length, n_points)
    x_critical  = _critical_x_positions(beam, reactions, loads)

    # For each critical x, add x−ε and x+ε to capture jumps
    eps = beam.length * 1e-5
    extra = []
    for xc in x_critical:
        extra += [xc - eps, xc, xc + eps]
    x_all = np.unique(np.concatenate([x_uniform, extra]))
    x_all = x_all[(x_all >= 0.0) & (x_all <= beam.length)]

    # ── Evaluate V and M ─────────────────────────────────────────────────
    V_arr = np.array([_shear_at(x,    reactions, loads) for x in x_all])
    M_arr = np.array([_moment_at(x,   reactions, loads) for x in x_all])

    # ── Build critical sections list ──────────────────────────────────────
    critical = _build_critical_sections(x_critical, reactions, loads, beam)

    # ── Generate step-by-step segment solution ────────────────────────────
    steps = _generate_steps(beam, reactions, loads, x_critical)

    return SFDBMDResult(x=x_all, V=V_arr, M=M_arr, critical=critical, steps=steps)


# ──────────────────────────────────────────────
#  V(x) and M(x) evaluation at a single point
# ──────────────────────────────────────────────

def _shear_at(x: float, reactions: Dict, loads: List[AnyLoad]) -> float:
    """
    V(x) from all forces to the LEFT of cut at position x.
    Point loads / reactions exactly at x are NOT included (left convention).
    """
    V = 0.0
    # Reactions
    for xr, r in reactions.items():
        if xr < x:
            V += r.get('Fy', 0.0)    # +ve = upward
    # Loads
    for ld in loads:
        if isinstance(ld, PointLoad) and ld.position < x:
            V -= ld.magnitude
        elif isinstance(ld, UDL):
            V += _udl_shear_at(ld, x)
        elif isinstance(ld, UVL):
            V += _uvl_shear_at(ld, x)
        # Applied moments and fixed-end moment reactions do not affect V
    return V


def _moment_at(x: float, reactions: Dict, loads: List[AnyLoad]) -> float:
    """
    M(x) from all forces and moments to the LEFT of cut at position x.
    Positive = sagging.
    """
    M = 0.0
    # Reactions
    for xr, r in reactions.items():
        if xr < x:
            M += r.get('Fy', 0.0) * (x - xr)   # upward reaction → +ve sagging
            M += r.get('M',  0.0)               # fixed-end CW moment → +M contribution
    # Loads
    for ld in loads:
        if isinstance(ld, PointLoad) and ld.position < x:
            M -= ld.magnitude * (x - ld.position)
        elif isinstance(ld, UDL):
            M += _udl_moment_at(ld, x)
        elif isinstance(ld, UVL):
            M += _uvl_moment_at(ld, x)
        elif isinstance(ld, AppliedMoment) and ld.position < x:
            M += ld.magnitude                   # CW applied moment → +ve contribution
    return M


# ──────────────────────────────────────────────
#  Distributed load contribution functions
# ──────────────────────────────────────────────

def _udl_shear_at(ld: UDL, x: float) -> float:
    """Contribution of a UDL to V(x).  Negative (reduces upward V)."""
    if x <= ld.start:
        return 0.0
    elif x <= ld.end:
        return -ld.intensity * (x - ld.start)
    else:
        return -ld.intensity * ld.span   # full UDL to the left


def _udl_moment_at(ld: UDL, x: float) -> float:
    """Contribution of a UDL to M(x).  Negative (causes hogging effect on left span)."""
    if x <= ld.start:
        return 0.0
    elif x <= ld.end:
        c = x - ld.start
        return -ld.intensity * c**2 / 2.0
    else:
        # Full UDL is to the left; use resultant at centroid
        return -ld.total_force * (x - ld.centroid)


def _uvl_shear_at(ld: UVL, x: float) -> float:
    """
    Contribution of a UVL to V(x).
    For a < x ≤ b:  −∫_a^x q(t) dt  where q(t) = w₁ + (w₂-w₁)(t-a)/(b-a)
    = −[ w₁(x−a) + (w₂−w₁)(x−a)²/(2(b−a)) ]
    """
    if x <= ld.start:
        return 0.0
    w1, w2 = ld.intensity_start, ld.intensity_end
    a, b   = ld.start, ld.end
    if x <= b:
        c = x - a
        return -(w1 * c + (w2 - w1) * c**2 / (2.0 * ld.span))
    else:
        return -ld.total_force   # full resultant to the left


def _uvl_moment_at(ld: UVL, x: float) -> float:
    """
    Contribution of a UVL to M(x).
    For a < x ≤ b:  −∫_a^x q(t)(x−t) dt
    = −[ w₁(x−a)²/2 + (w₂−w₁)(x−a)³/(6(b−a)) ]
    For x > b:  −F_total × (x − x_centroid)
    """
    if x <= ld.start:
        return 0.0
    w1, w2 = ld.intensity_start, ld.intensity_end
    a, b   = ld.start, ld.end
    if x <= b:
        c = x - a
        return -(w1 * c**2 / 2.0 + (w2 - w1) * c**3 / (6.0 * ld.span))
    else:
        return -ld.total_force * (x - ld.centroid)


# ──────────────────────────────────────────────
#  Critical sections
# ──────────────────────────────────────────────

def _critical_x_positions(
    beam: Beam,
    reactions: Dict,
    loads: List[AnyLoad],
) -> List[float]:
    """Collect all x positions where V or M may have a known value, jump, or extremum."""
    positions = (
        [0.0, beam.length]
        + [s.position for s in beam.supports]
        + load_positions(loads)
    )
    # Remove duplicates and clamp to beam
    seen = set()
    result = []
    for p in positions:
        p = float(p)
        if p < 0.0 or p > beam.length:
            continue
        if p not in seen:
            seen.add(p)
            result.append(p)
    return sorted(result)


def _build_critical_sections(
    x_crits:   List[float],
    reactions: Dict,
    loads:     List[AnyLoad],
    beam:      Beam,
) -> List[CriticalSection]:
    eps = beam.length * 1e-5
    sections = []
    for xc in x_crits:
        V_l = _shear_at(xc - eps, reactions, loads)
        V_r = _shear_at(xc + eps, reactions, loads)
        M_v = _moment_at(xc,      reactions, loads)

        # Label
        label = f"x = {xc:.3f} m"
        if xc == 0.0:
            label = "Left end (x = 0)"
        elif xc == beam.length:
            label = f"Right end (x = {beam.length:.3f} m)"
        for s in beam.supports:
            if abs(s.position - xc) < 1e-9:
                label = f"Support ({s.support_type.value}) at x = {xc:.3f} m"
        for ld in loads:
            if isinstance(ld, PointLoad) and abs(ld.position - xc) < 1e-9:
                label = f"Point load {ld.label or 'P'} at x = {xc:.3f} m"
            elif isinstance(ld, AppliedMoment) and abs(ld.position - xc) < 1e-9:
                label = f"Applied moment {ld.label or 'M₀'} at x = {xc:.3f} m"
            elif isinstance(ld, (UDL, UVL)):
                if abs(ld.start - xc) < 1e-9:
                    label = f"Start of {type(ld).__name__} {ld.label} at x = {xc:.3f} m"
                elif abs(ld.end - xc) < 1e-9:
                    label = f"End of {type(ld).__name__} {ld.label} at x = {xc:.3f} m"

        sections.append(CriticalSection(x=xc, V_left=V_l, V_right=V_r, M=M_v, label=label))

    return sections


# ──────────────────────────────────────────────
#  Step-by-step segment explanation
# ──────────────────────────────────────────────

def _generate_steps(
    beam:      Beam,
    reactions: Dict,
    loads:     List[AnyLoad],
    x_crits:   List[float],
) -> List[dict]:
    """
    Generate one step per segment between consecutive critical sections.
    Each step describes the V and M expressions and their boundary values.
    """
    steps = []
    step_num = 1

    # Step 0: reactions summary
    rxn_lines = ["Support reactions:"]
    for pos in sorted(reactions):
        r = reactions[pos]
        line = f"  x = {pos:.3f} m:  R_y = {r.get('Fy', 0):.4f} kN"
        if 'M' in r:
            line += f",  M_fix = {r.get('M', 0):.4f} kN·m"
        rxn_lines.append(line)
    steps.append({
        "number":      0,
        "title":       "Support reactions (input to SFD/BMD)",
        "description": "\n".join(rxn_lines),
        "latex":       r"\text{From equilibrium / stiffness method}",
        "value":       "",
    })

    for i in range(len(x_crits) - 1):
        xa = x_crits[i]
        xb = x_crits[i + 1]
        xm = (xa + xb) / 2.0     # mid-point of segment

        Va = _shear_at(xa + 1e-9 * (xb - xa), reactions, loads)
        Vb = _shear_at(xb - 1e-9 * (xb - xa), reactions, loads)
        Ma = _moment_at(xa, reactions, loads)
        Mb = _moment_at(xb, reactions, loads)

        # Shape description of V in this segment
        # Determine dominant load type between xa and xb
        seg_loads = [ld for ld in loads if _load_active_in_segment(ld, xa, xb)]
        v_shape = "constant (no distributed load in this segment)"
        m_shape = "linear"
        if any(isinstance(ld, UDL) for ld in seg_loads):
            v_shape = "linearly varying (UDL present)"
            m_shape = "parabolic (2nd degree)"
        if any(isinstance(ld, UVL) for ld in seg_loads):
            v_shape = "parabolically varying (UVL present)"
            m_shape = "cubic (3rd degree)"

        desc = (
            f"Segment {i+1}: x ∈ [{xa:.3f}, {xb:.3f}] m\n"
            f"  V at x = {xa:.3f} m : {Va:+.4f} kN\n"
            f"  V at x = {xb:.3f} m : {Vb:+.4f} kN\n"
            f"  Shear profile: {v_shape}\n\n"
            f"  M at x = {xa:.3f} m : {Ma:+.4f} kN·m\n"
            f"  M at x = {xb:.3f} m : {Mb:+.4f} kN·m\n"
            f"  Moment profile: {m_shape}"
        )

        # Build a symbolic-style latex for M(x)
        latex = _segment_latex(xa, xb, reactions, loads)

        steps.append({
            "number":      step_num,
            "title":       f"Segment {step_num}: x ∈ [{xa:.2f}, {xb:.2f}] m",
            "description": desc,
            "latex":       latex,
            "value":       f"V: {Va:+.3f} → {Vb:+.3f} kN  |  M: {Ma:+.3f} → {Mb:+.3f} kN·m",
        })
        step_num += 1

    # Final step: identify key values
    eps = beam.length * 1e-5
    x_eval = np.linspace(0, beam.length, 2000)
    V_eval  = np.array([_shear_at(xi,  reactions, loads) for xi in x_eval])
    M_eval  = np.array([_moment_at(xi, reactions, loads) for xi in x_eval])
    i_Vmax  = int(np.argmax(np.abs(V_eval)))
    i_Mmax  = int(np.argmax(np.abs(M_eval)))
    steps.append({
        "number":      step_num,
        "title":       "Key values summary",
        "description": (
            f"  Maximum |V| = {abs(V_eval[i_Vmax]):.4f} kN  at x ≈ {x_eval[i_Vmax]:.3f} m\n"
            f"  Maximum |M| = {abs(M_eval[i_Mmax]):.4f} kN·m at x ≈ {x_eval[i_Mmax]:.3f} m\n"
            f"  (Sagging positive, Hogging negative convention)"
        ),
        "latex":       (
            rf"V_{{max}} = {abs(V_eval[i_Vmax]):.4f}\ \text{{kN}},\quad "
            rf"M_{{max}} = {abs(M_eval[i_Mmax]):.4f}\ \text{{kN·m}}"
        ),
        "value":       f"|V|_max = {abs(V_eval[i_Vmax]):.4f} kN, |M|_max = {abs(M_eval[i_Mmax]):.4f} kN·m",
    })

    return steps


def _load_active_in_segment(ld: AnyLoad, xa: float, xb: float) -> bool:
    """Return True if the load has any effect in the segment (xa, xb)."""
    if isinstance(ld, PointLoad):
        return xa <= ld.position <= xb
    elif isinstance(ld, (UDL, UVL)):
        return ld.start < xb and ld.end > xa
    elif isinstance(ld, AppliedMoment):
        return xa <= ld.position <= xb
    return False


def _segment_latex(
    xa: float, xb: float, reactions: Dict, loads: List[AnyLoad]
) -> str:
    """Build a compact LaTeX representation of V(x) and M(x) for a segment."""
    terms_v: List[str] = []
    terms_m: List[str] = []

    for xr, r in sorted(reactions.items()):
        if xr < xa + 1e-9:
            fy = r.get('Fy', 0.0)
            if abs(fy) > 1e-9:
                sign = "+" if fy >= 0 else ""
                terms_v.append(f"{sign}{fy:.3f}")
                terms_m.append(f"{sign}{fy:.3f}(x-{xr:.2f})")
            m_fix = r.get('M', 0.0)
            if abs(m_fix) > 1e-9:
                sign = "+" if m_fix >= 0 else ""
                terms_m.append(f"{sign}{m_fix:.3f}")

    for ld in loads:
        if isinstance(ld, PointLoad) and ld.position < xa + 1e-9:
            p = ld.magnitude
            if abs(p) > 1e-9:
                sign = "-" if p >= 0 else "+"
                terms_v.append(f"{sign}{abs(p):.3f}")
                terms_m.append(f"{sign}{abs(p):.3f}(x-{ld.position:.2f})")
        elif isinstance(ld, UDL) and ld.start <= xa + 1e-9:
            w = ld.intensity
            a = ld.start
            if ld.end <= xa + 1e-9:
                # full UDL to the left
                terms_v.append(f"-{ld.total_force:.3f}")
                terms_m.append(f"-{ld.total_force:.3f}(x-{ld.centroid:.2f})")
            else:
                terms_v.append(f"-{w:.3f}(x-{a:.2f})")
                terms_m.append(rf"-\frac{{{w:.3f}}}{2}(x-{a:.2f})^2")

    v_expr = "".join(terms_v).lstrip("+") or "0"
    m_expr = "".join(terms_m).lstrip("+") or "0"

    return (
        rf"V(x) = {v_expr}\ \text{{kN}}, \quad "
        rf"M(x) = {m_expr}\ \text{{kN·m}} \quad "
        rf"\text{{for }}x \in [{xa:.2f},\, {xb:.2f}]"
    )
