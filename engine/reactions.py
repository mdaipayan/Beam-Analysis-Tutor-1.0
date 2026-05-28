"""
engine/reactions.py
===================
Support reaction solver for all beam types.

Strategy
--------
  Statically determinate beams (DSI = 0)
    Simply supported, cantilever, overhanging:
    Solved analytically using ΣFy = 0 and ΣM = 0.
    Full step-by-step LaTeX output is generated for the teaching display.

  Statically indeterminate beams (DSI > 0)
    Propped cantilever (DSI = 1), Fixed-Fixed (DSI = 2):
    Solved using the Euler-Bernoulli beam stiffness method (FEM).
    Nodes are placed at every support, load-application point, and load boundary.
    A brief explanation of the method is included in the steps output.

Return value
------------
  reactions : dict
      { position (float): {'Fy': float,         # vertical reaction, +ve upward (kN)
                            'M':  float} }        # moment reaction, +ve clockwise (kN·m)
                                                  # 'M' key present only for fixed supports
  steps : list[dict]
      Each step dict has keys:
        'number'      : int
        'title'       : str
        'description' : str
        'latex'       : str   (LaTeX math string, wrapped in $ ... $)
        'value'       : str   (formatted numerical result, e.g. '12.5 kN')

  method : str  ('analytical' | 'stiffness_fem')
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from .beam import Beam, BeamType, SupportType, Support
from .loads import (
    AnyLoad, PointLoad, UDL, UVL, AppliedMoment,
    total_vertical_force, moment_about,
)


# ──────────────────────────────────────────────
#  Return type
# ──────────────────────────────────────────────

@dataclass
class ReactionResult:
    """
    Container for support reactions and step-by-step solution.

    reactions : dict
        Keys are support positions (float).
        Values are dicts with 'Fy' (kN, +ve upward) and optionally 'M' (kN·m, +ve CW).
    steps : list[dict]
        Step-by-step solution for display in the Solver page.
    method : str
        'analytical' or 'stiffness_fem'.
    """
    reactions: Dict[float, Dict[str, float]]
    steps:     List[dict]
    method:    str

    def __repr__(self) -> str:  # pragma: no cover
        lines = [f"ReactionResult (method={self.method}):"]
        for pos, r in sorted(self.reactions.items()):
            fy = r.get('Fy', 0.0)
            m  = r.get('M',  0.0)
            line = f"  x = {pos:.3f} m  →  Fy = {fy:+.4f} kN"
            if 'M' in r:
                line += f",  M = {m:+.4f} kN·m"
            lines.append(line)
        return "\n".join(lines)


# ──────────────────────────────────────────────
#  Public entry point
# ──────────────────────────────────────────────

def solve_reactions(beam: Beam, loads: List[AnyLoad]) -> ReactionResult:
    """
    Solve for support reactions given a beam configuration and applied loads.

    Parameters
    ----------
    beam : Beam
        Fully configured beam (supports, length, EI).
    loads : list[AnyLoad]
        All applied loads (PointLoad, UDL, UVL, AppliedMoment).

    Returns
    -------
    ReactionResult
        reactions dict, step-by-step solution, and method name.
    """
    if beam.is_statically_determinate():
        return _solve_determinate(beam, loads)
    else:
        return _solve_indeterminate_fem(beam, loads)


# ──────────────────────────────────────────────
#  Analytical solver for determinate beams
# ──────────────────────────────────────────────

def _solve_determinate(beam: Beam, loads: List[AnyLoad]) -> ReactionResult:
    """
    Analytical solution using ΣFy = 0 and ΣM = 0.
    Handles: simply supported, cantilever, overhanging.
    """
    steps: List[dict] = []
    reactions: Dict[float, Dict[str, float]] = {}
    step_num = 1

    # ── Step 1: Identify loads ───────────────────────────────────────────
    W = total_vertical_force(loads)

    load_summary_lines = []
    for ld in loads:
        if isinstance(ld, PointLoad):
            load_summary_lines.append(
                f"Point load {ld.label or 'P'} = {ld.magnitude:.2f} kN at x = {ld.position:.2f} m"
            )
        elif isinstance(ld, UDL):
            load_summary_lines.append(
                f"UDL {ld.label or 'w'} = {ld.intensity:.2f} kN/m from x = {ld.start:.2f} m "
                f"to x = {ld.end:.2f} m  (resultant = {ld.total_force:.2f} kN at x = {ld.centroid:.2f} m)"
            )
        elif isinstance(ld, UVL):
            load_summary_lines.append(
                f"UVL {ld.label or 'w'}: {ld.intensity_start:.2f} kN/m at x = {ld.start:.2f} m "
                f"→ {ld.intensity_end:.2f} kN/m at x = {ld.end:.2f} m  "
                f"(resultant = {ld.total_force:.2f} kN at x = {ld.centroid:.2f} m)"
            )
        elif isinstance(ld, AppliedMoment):
            direction = "clockwise" if ld.magnitude >= 0 else "counter-clockwise"
            load_summary_lines.append(
                f"Applied moment {ld.label or 'M₀'} = {abs(ld.magnitude):.2f} kN·m "
                f"({direction}) at x = {ld.position:.2f} m"
            )

    steps.append({
        "number":      step_num,
        "title":       "Identify applied loads and draw free body diagram",
        "description": "\n".join(load_summary_lines) + f"\n\nTotal downward force W = {W:.3f} kN",
        "latex":       rf"W = {W:.3f}\ \text{{kN}}",
        "value":       f"W = {W:.3f} kN",
    })
    step_num += 1

    # ── Determine beam configuration ─────────────────────────────────────
    fixed_supports  = [s for s in beam.supports if s.support_type == SupportType.FIXED]
    pinroller_supports = [s for s in beam.supports
                          if s.support_type in (SupportType.PIN, SupportType.ROLLER)]

    if fixed_supports:
        # Cantilever: one fixed support, no pinroller
        _solve_cantilever(beam, loads, reactions, steps, step_num, W)
    else:
        # Simply supported or overhanging: two pin/roller supports
        _solve_two_support(beam, loads, reactions, steps, step_num, W)

    return ReactionResult(reactions=reactions, steps=steps, method="analytical")


def _solve_two_support(
    beam: Beam,
    loads: List[AnyLoad],
    reactions: Dict,
    steps: List[dict],
    step_num: int,
    W: float,
) -> None:
    """
    ΣM and ΣFy for simply supported / overhanging beams.
    """
    sA = beam.supports[0]   # left support (pin)
    sB = beam.supports[1]   # right support (roller)
    xA, xB = sA.position, sB.position
    span = xB - xA

    # ΣM about A → R_B
    M_loads_about_A = moment_about(loads, xA)
    R_B = M_loads_about_A / span

    steps.append({
        "number":      step_num,
        "title":       f"Apply ΣM_A = 0 to find R_B at x = {xB:.2f} m",
        "description": (
            f"Taking moments about support A (x = {xA:.2f} m), clockwise positive:\n"
            f"  Sum of load moments about A = {M_loads_about_A:.4f} kN·m\n"
            f"  Span between supports = {span:.4f} m\n"
            f"  R_B × {span:.4f} = {M_loads_about_A:.4f}"
        ),
        "latex":  (
            rf"\sum M_A = 0 \implies R_B = "
            rf"\frac{{{M_loads_about_A:.4f}}}{{{span:.4f}}} = {R_B:.4f}\ \text{{kN}}"
        ),
        "value":  f"R_B = {R_B:.4f} kN {'(↑ upward)' if R_B >= 0 else '(↓ downward)'}",
    })

    # ΣFy → R_A
    R_A = W - R_B

    steps.append({
        "number":      step_num + 1,
        "title":       f"Apply ΣFy = 0 to find R_A at x = {xA:.2f} m",
        "description": (
            f"  Total downward load W = {W:.4f} kN\n"
            f"  R_A + R_B = W  →  R_A = W − R_B = {W:.4f} − {R_B:.4f}"
        ),
        "latex":  (
            rf"\sum F_y = 0 \implies R_A = W - R_B = "
            rf"{W:.4f} - {R_B:.4f} = {R_A:.4f}\ \text{{kN}}"
        ),
        "value":  f"R_A = {R_A:.4f} kN {'(↑ upward)' if R_A >= 0 else '(↓ downward)'}",
    })

    # Verification: ΣM_B = 0
    M_check = R_A * (xA - xB) + moment_about(loads, xB)
    _append_verification_step(steps, step_num + 2, M_check, "B", xB)

    reactions[xA] = {'Fy': R_A}
    reactions[xB] = {'Fy': R_B}


def _solve_cantilever(
    beam: Beam,
    loads: List[AnyLoad],
    reactions: Dict,
    steps: List[dict],
    step_num: int,
    W: float,
) -> None:
    """
    ΣFy and ΣM for cantilever (single fixed support).
    """
    fixed = beam.supports[0]
    xA    = fixed.position

    # ΣFy = 0
    R_A = W

    steps.append({
        "number":      step_num,
        "title":       f"Apply ΣFy = 0 to find vertical reaction R_A at x = {xA:.2f} m",
        "description": (
            f"  The fixed support must carry all the applied vertical load.\n"
            f"  R_A = W = {W:.4f} kN"
        ),
        "latex":  rf"\sum F_y = 0 \implies R_A = W = {R_A:.4f}\ \text{{kN}}",
        "value":  f"R_A = {R_A:.4f} kN",
    })

    # ΣM about A = 0  →  M_A (reaction moment)
    M_loads_about_A = moment_about(loads, xA)
    M_A = -M_loads_about_A    # reaction CW moment; negative = CCW reaction

    direction_desc  = "counter-clockwise" if M_A < 0 else "clockwise"
    steps.append({
        "number":      step_num + 1,
        "title":       f"Apply ΣM_A = 0 to find fixing moment M_A at x = {xA:.2f} m",
        "description": (
            f"  Sum of CW moments from applied loads about A = {M_loads_about_A:.4f} kN·m\n"
            f"  M_A (reaction) = −({M_loads_about_A:.4f}) = {M_A:.4f} kN·m  [{direction_desc}]"
        ),
        "latex":  (
            rf"\sum M_A = 0 \implies M_A = -\sum M_{{loads}} = "
            rf"{M_A:.4f}\ \text{{kN·m}}"
        ),
        "value":  f"M_A = {M_A:.4f} kN·m ({direction_desc})",
    })

    reactions[xA] = {'Fy': R_A, 'M': M_A}


def _append_verification_step(steps, num, residual, label, pos):
    ok = abs(residual) < 1e-6
    verdict = "✓ VERIFIED" if ok else f"✗ RESIDUAL = {residual:.6f} kN·m (check loads!)"
    steps.append({
        "number":      num,
        "title":       f"Verification: ΣM_{label} = 0",
        "description": (
            f"  Check equilibrium by taking moments about support {label} (x = {pos:.2f} m).\n"
            f"  Residual = {residual:.2e} kN·m  →  {verdict}"
        ),
        "latex":  rf"\sum M_{{{label}}} = {residual:.4f} \approx 0\ \checkmark",
        "value":  verdict,
    })


# ──────────────────────────────────────────────
#  FEM solver for indeterminate beams
# ──────────────────────────────────────────────

def _solve_indeterminate_fem(beam: Beam, loads: List[AnyLoad]) -> ReactionResult:
    """
    Stiffness (FEM) solution for propped cantilever and fixed-fixed beams.

    Mesh: nodes at every support position AND every significant load
    boundary (start/end of distributed loads, position of point loads and
    moments).  Euler-Bernoulli beam elements connect adjacent nodes.

    DOFs per node: [v (vertical displacement), θ (rotation)]
         +ve v = upward, +ve θ = counter-clockwise.
    """
    steps: List[dict] = []
    reactions: Dict[float, Dict[str, float]] = {}

    dsi = beam.degree_of_indeterminacy()
    steps.append({
        "number":      1,
        "title":       "Identify degree of static indeterminacy",
        "description": (
            f"  Number of support reactions = {beam.total_reactions()}\n"
            f"  Equilibrium equations available = 3\n"
            f"  Degree of static indeterminacy (DSI) = {dsi}\n"
            f"  → Cannot be solved by statics alone.  Using the stiffness (FEM) method."
        ),
        "latex":  rf"\text{{DSI}} = r - 3 = {beam.total_reactions()} - 3 = {dsi}",
        "value":  f"DSI = {dsi}",
    })

    # ── Build node mesh ───────────────────────────────────────────────────
    node_positions = sorted(set(
        [0.0, beam.length]
        + [s.position for s in beam.supports]
        + [ld.position  for ld in loads if isinstance(ld, (PointLoad, AppliedMoment))]
        + [ld.start     for ld in loads if isinstance(ld, (UDL, UVL))]
        + [ld.end       for ld in loads if isinstance(ld, (UDL, UVL))]
    ))
    node_positions = [p for p in node_positions if 0.0 <= p <= beam.length]
    n_nodes = len(node_positions)
    n_dof   = 2 * n_nodes          # [v₁, θ₁, v₂, θ₂, …]

    node_index = {p: i for i, p in enumerate(node_positions)}

    steps.append({
        "number":      2,
        "title":       "Discretise beam into Euler-Bernoulli elements",
        "description": (
            f"  Nodes placed at: {[f'{p:.3f}' for p in node_positions]}\n"
            f"  Number of nodes = {n_nodes},  elements = {n_nodes - 1}\n"
            f"  DOFs per node: vertical displacement v and rotation θ\n"
            f"  Total DOFs = {n_dof}"
        ),
        "latex":  rf"\text{{Elements}} = {n_nodes - 1},\quad n_{{DOF}} = {n_dof}",
        "value":  f"{n_nodes - 1} elements, {n_dof} DOFs",
    })

    EI = beam.EI

    # ── Assemble global stiffness matrix K and load vector F ──────────────
    K = np.zeros((n_dof, n_dof))
    F = np.zeros(n_dof)

    for elem_idx in range(n_nodes - 1):
        x1 = node_positions[elem_idx]
        x2 = node_positions[elem_idx + 1]
        L_e = x2 - x1
        i1, i2 = node_index[x1], node_index[x2]
        dofs = [2*i1, 2*i1+1, 2*i2, 2*i2+1]

        k_e = _element_stiffness(EI, L_e)
        for a in range(4):
            for b in range(4):
                K[dofs[a], dofs[b]] += k_e[a, b]

        f_e = _element_load_vector(loads, x1, x2)
        for a in range(4):
            F[dofs[a]] += f_e[a]

    # Add point loads and moments directly to nodal force vector
    for ld in loads:
        if isinstance(ld, PointLoad):
            if ld.position in node_index:
                idx = node_index[ld.position]
                F[2*idx] -= ld.magnitude        # downward = negative Fy DOF direction
        elif isinstance(ld, AppliedMoment):
            if ld.position in node_index:
                idx = node_index[ld.position]
                F[2*idx + 1] -= ld.magnitude    # CW = negative θ DOF direction (θ +ve CCW)

    # ── Apply boundary conditions ─────────────────────────────────────────
    constrained_dofs: List[int] = []
    for s in beam.supports:
        ni = node_index[s.position]
        if s.support_type in (SupportType.PIN, SupportType.ROLLER):
            constrained_dofs.append(2*ni)           # constrain v
        elif s.support_type == SupportType.FIXED:
            constrained_dofs.extend([2*ni, 2*ni+1]) # constrain v and θ

    free_dofs = [i for i in range(n_dof) if i not in constrained_dofs]

    # ── Solve: K_ff * d_f = F_f  (d_c = 0 at constrained DOFs) ──────────
    K_ff = K[np.ix_(free_dofs, free_dofs)]
    F_f  = F[np.ix_(free_dofs,)]

    try:
        d_f = np.linalg.solve(K_ff, F_f)
    except np.linalg.LinAlgError as exc:
        raise RuntimeError("FEM stiffness matrix is singular.  Check beam supports.") from exc

    d = np.zeros(n_dof)
    for i, dof in enumerate(free_dofs):
        d[dof] = d_f[i]

    # ── Extract reactions: R = K·d − F at constrained DOFs ───────────────
    residual = K @ d - F
    for s in beam.supports:
        ni  = node_index[s.position]
        rxn: Dict[str, float] = {}
        if s.support_type in (SupportType.PIN, SupportType.ROLLER):
            rxn['Fy'] = float(residual[2*ni])        # +ve = upward
        elif s.support_type == SupportType.FIXED:
            rxn['Fy'] = float(residual[2*ni])
            rxn['M']  = float(-residual[2*ni + 1])   # convert: FEM θ CCW +ve → M CW +ve
        reactions[s.position] = rxn

    # ── Summary step ─────────────────────────────────────────────────────
    summary_lines = ["Reactions from stiffness solution:"]
    for pos in sorted(reactions):
        r = reactions[pos]
        summary_lines.append(
            f"  x = {pos:.3f} m:  Fy = {r.get('Fy',0):.4f} kN"
            + (f",  M = {r.get('M',0):.4f} kN·m" if 'M' in r else "")
        )

    # Verification: ΣFy
    sum_fy  = sum(r.get('Fy', 0) for r in reactions.values()) - total_vertical_force(loads)
    verdict = "✓ VERIFIED" if abs(sum_fy) < 1e-4 else f"✗ Residual ΣFy = {sum_fy:.2e}"
    summary_lines.append(f"\nEquilibrium check:  ΣFy = {sum_fy:.2e}  → {verdict}")

    steps.append({
        "number":      3,
        "title":       "Solve stiffness equations and extract reactions",
        "description": "\n".join(summary_lines),
        "latex":       r"[K]\{d\} = \{F\} \implies \{R\} = [K]\{d\} - \{F\}_{\text{external}}",
        "value":       verdict,
    })

    return ReactionResult(reactions=reactions, steps=steps, method="stiffness_fem")


# ──────────────────────────────────────────────
#  FEM element helper functions
# ──────────────────────────────────────────────

def _element_stiffness(EI: float, L: float) -> np.ndarray:
    """
    4×4 Euler-Bernoulli beam element stiffness matrix.
    DOF order: [v₁, θ₁, v₂, θ₂]  (+ve v upward, +ve θ counter-clockwise).

        K = (EI/L³) × ⎡  12    6L   −12    6L ⎤
                       ⎢  6L   4L²   −6L   2L² ⎥
                       ⎢ −12  −6L    12   −6L  ⎥
                       ⎣  6L   2L²  −6L   4L²  ⎦
    """
    c = EI / (L ** 3)
    k = np.array([
        [ 12,    6*L,   -12,   6*L  ],
        [  6*L,  4*L**2, -6*L,  2*L**2],
        [-12,   -6*L,   12,   -6*L  ],
        [  6*L,  2*L**2, -6*L,  4*L**2],
    ], dtype=float)
    return c * k


def _element_load_vector(loads: List[AnyLoad], x1: float, x2: float) -> np.ndarray:
    """
    Consistent nodal load vector for distributed loads that overlap element [x1, x2].
    DOF order: [F₁ (+ve up), M₁ (+ve CCW), F₂ (+ve up), M₂ (+ve CCW)].
    Point loads and applied moments are handled separately (added at nodes).
    """
    f = np.zeros(4)
    L_e = x2 - x1

    for ld in loads:
        if isinstance(ld, UDL):
            # Clip to element span
            a = max(ld.start, x1)
            b = min(ld.end,   x2)
            if b <= a:
                continue
            w = ld.intensity        # kN/m, downward = positive in loads convention
            span = b - a
            mid  = (a + b) / 2.0

            # Equivalent nodal forces using Hermite shape functions (uniform load on sub-span)
            # For partial-span UDL: use equivalent point load at centroid weighted by shape fns
            xi_a = (a - x1) / L_e  # normalised start (0 to 1)
            xi_b = (b - x1) / L_e  # normalised end
            xi_m = (mid - x1) / L_e

            # Full element: [wL/2, wL²/12, wL/2, -wL²/12] (standard result)
            # For sub-span, integrate shape functions analytically
            f_sub = _consistent_udl(w, L_e, xi_a, xi_b)
            f -= f_sub              # subtract because downward load = -ve Fy DOF

        elif isinstance(ld, UVL):
            a = max(ld.start, x1)
            b = min(ld.end,   x2)
            if b <= a:
                continue
            # Sample at start and end of the overlapping segment
            wa = ld.intensity_at(a)
            wb = ld.intensity_at(b)
            # Split into UDL (min) + triangular (difference), integrate on sub-span
            xi_a = (a - x1) / L_e
            xi_b = (b - x1) / L_e
            f_sub = _consistent_uvl(wa, wb, L_e, xi_a, xi_b)
            f -= f_sub

    return f


def _consistent_udl(
    w: float, L: float, xi_a: float, xi_b: float
) -> np.ndarray:
    """
    Consistent nodal forces for a UDL of intensity w (downward +ve)
    acting over the normalised sub-span [xi_a, xi_b] of element length L.
    Returns [F1, M1, F2, M2] with +ve = upward / CCW.

    Integral of w × N_i over [xi_a, xi_b] analytically.
    """
    # Hermite shape functions in terms of ξ ∈ [0,1]:
    #   N1 = 1 - 3ξ² + 2ξ³
    #   N2 = Lξ(1-ξ)²
    #   N3 = 3ξ² - 2ξ³
    #   N4 = Lξ²(ξ-1)
    # Integral from a to b: ∫w·Ni dξ × L  (dξ = dx/L)
    def _intN1(x): return x - x**3 + 0.5*x**4
    def _intN2(x): return L * (0.5*x**2 - 2*x**3/3 + 0.25*x**4)
    def _intN3(x): return x**3 - 0.5*x**4
    def _intN4(x): return L * (x**3/3 - 0.25*x**4)

    a, b = xi_a, xi_b
    f    = np.array([
        w * L * (_intN1(b) - _intN1(a)),
        w * L * (_intN2(b) - _intN2(a)) / L,   # M DOF scale
        w * L * (_intN3(b) - _intN3(a)),
        w * L * (_intN4(b) - _intN4(a)) / L,
    ])
    # Correct moment DOFs for L factor in shape functions
    # N2 = Lξ(1−ξ)²  →  ∫N2 dξ = L(ξ²/2 − 2ξ³/3 + ξ⁴/4)
    f[1] = w * L * (
        L * (0.5*b**2 - 2*b**3/3 + 0.25*b**4)
        - L * (0.5*a**2 - 2*a**3/3 + 0.25*a**4)
    )
    # N4 = Lξ²(ξ−1)  →  ∫N4 dξ = L(ξ⁴/4 − ξ³/3)   ← sign fixed (was ξ³/3 − ξ⁴/4)
    f[3] = w * L * (
        L * (0.25*b**4 - b**3/3)
        - L * (0.25*a**4 - a**3/3)
    )
    # Force DOFs
    f[0] = w * L * (_intN1(b) - _intN1(a))
    f[2] = w * L * (_intN3(b) - _intN3(a))
    return f


def _consistent_uvl(
    wa: float, wb: float, L: float, xi_a: float, xi_b: float
) -> np.ndarray:
    """
    Consistent nodal forces for a linearly varying load (wa at xi_a → wb at xi_b)
    over the normalised sub-span [xi_a, xi_b].
    Superpose UDL (intensity = wa) + triangular (0 → wb-wa).
    """
    f_udl  = _consistent_udl(wa,        L, xi_a, xi_b)
    # Triangular: integrate N_i × (wb-wa)×(ξ-xi_a)/(xi_b-xi_a) over [xi_a, xi_b]
    # Approximate via 5-point Gauss quadrature over the sub-span
    span  = xi_b - xi_a
    dw    = wb - wa
    xi_g  = np.array([-0.90618, -0.53847, 0.0, 0.53847, 0.90618])
    w_g   = np.array([ 0.23693,  0.47863, 0.56889, 0.47863, 0.23693])
    f_tri = np.zeros(4)
    for xi_pt, wt in zip(xi_g, w_g):
        xi    = xi_a + 0.5 * span * (1.0 + xi_pt)   # map to [xi_a, xi_b]
        t     = (xi - xi_a) / span if span > 1e-12 else 0.0
        q     = dw * t                                # triangular intensity at xi
        N     = _hermite_N(xi, L)
        f_tri += 0.5 * span * L * q * wt * N
    return f_udl + f_tri


def _hermite_N(xi: float, L: float) -> np.ndarray:
    """Hermite shape function vector at normalised coordinate xi ∈ [0,1]."""
    return np.array([
        1 - 3*xi**2 + 2*xi**3,
        L * xi * (1 - xi)**2,
        3*xi**2 - 2*xi**3,
        L * xi**2 * (xi - 1),
    ])
