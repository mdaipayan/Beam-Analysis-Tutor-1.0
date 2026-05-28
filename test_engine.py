"""
test_engine.py
==============
Validation suite for the BeamEdu core engine.

Each test function checks:
  1. Reactions (ΣFy = 0, ΣM = 0)
  2. Boundary conditions of V and M (zero at free ends, correct jumps)
  3. Spot-check values against known textbook solutions

Run:  python test_engine.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from engine import (
    simply_supported, cantilever, propped_cantilever, fixed_fixed, overhanging,
    PointLoad, UDL, UVL, AppliedMoment,
    solve_reactions, compute_sfd_bmd,
)

TOL = 1e-3   # kN or kN·m tolerance for all checks

PASS = "  ✓"
FAIL = "  ✗"

results = []


def check(name: str, computed: float, expected: float, tol: float = TOL) -> bool:
    ok = abs(computed - expected) <= tol
    tag = PASS if ok else FAIL
    status = f"{tag}  {name}: computed={computed:.5f}, expected={expected:.5f}"
    results.append((ok, status))
    print(status)
    return ok


def section(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ═══════════════════════════════════════════════════════════════
#  SIMPLY SUPPORTED — Point Load at centre
#  L=6 m, P=12 kN at x=3  → R_A = R_B = 6 kN
#  V(3-) = 6, V(3+) = -6, M(3) = 18 kN·m
# ═══════════════════════════════════════════════════════════════
section("SS beam — central point load (L=6, P=12 at x=3)")
beam  = simply_supported(6.0)
loads = [PointLoad(3.0, 12.0, label="P")]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

check("R_A",    rxn.reactions[0.0]["Fy"], 6.0)
check("R_B",    rxn.reactions[6.0]["Fy"], 6.0)
check("ΣFy",    sum(r["Fy"] for r in rxn.reactions.values()) - 12.0, 0.0)
check("V(0+)",  res.V[1],                  6.0)
check("V(3-)",  res.V[np.searchsorted(res.x, 2.9999)],  6.0)
check("V(3+)",  res.V[np.searchsorted(res.x, 3.0001)], -6.0)
check("V(6-)",  res.V[-2],                -6.0)
check("M(3)",   res.M[np.searchsorted(res.x, 3.0)],   18.0)
check("M(0)",   res.M[0],                  0.0)
check("M(6)",   res.M[-1],                 0.0)


# ═══════════════════════════════════════════════════════════════
#  SIMPLY SUPPORTED — Full-span UDL
#  L=8 m, w=10 kN/m → R_A = R_B = 40 kN
#  M(4) = 40×4 − 10×4²/2 = 160 − 80 = 80 kN·m
# ═══════════════════════════════════════════════════════════════
section("SS beam — full-span UDL (L=8, w=10 kN/m)")
beam  = simply_supported(8.0)
loads = [UDL(0.0, 8.0, 10.0)]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

check("R_A",   rxn.reactions[0.0]["Fy"], 40.0)
check("R_B",   rxn.reactions[8.0]["Fy"], 40.0)
check("M(4)",  res.M[np.searchsorted(res.x, 4.0)], 80.0)
check("M(0)",  res.M[0],  0.0)
check("M(8)",  res.M[-1], 0.0)
check("V(0+)", res.V[1],  40.0)
check("V(8-)", res.V[-2], -40.0)


# ═══════════════════════════════════════════════════════════════
#  SIMPLY SUPPORTED — Triangular UVL (0 at A, w₂ at B)
#  L=6, w₂=12 kN/m → total F=36 kN, centroid at x=4
#  R_A = 36×(6−4)/6 = 12, R_B = 36×4/6 = 24
# ═══════════════════════════════════════════════════════════════
section("SS beam — triangular UVL from 0 to 12 kN/m (L=6)")
beam  = simply_supported(6.0)
loads = [UVL(0.0, 6.0, 0.0, 12.0)]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

check("R_A",  rxn.reactions[0.0]["Fy"], 12.0)
check("R_B",  rxn.reactions[6.0]["Fy"], 24.0)
check("ΣFy",  sum(r["Fy"] for r in rxn.reactions.values()) - 36.0, 0.0)
check("M(0)", res.M[0],  0.0)
check("M(6)", res.M[-1], 0.0)


# ═══════════════════════════════════════════════════════════════
#  SIMPLY SUPPORTED — Applied CW moment at midspan
#  L=10, M₀=10 kN·m at x=5 → R_A = −1, R_B = +1 (from ΣM)
#  M(5−) = R_A×5 = −5,  M(5+) = −5 + 10 = +5
# ═══════════════════════════════════════════════════════════════
section("SS beam — applied CW moment at midspan (L=10, M₀=10)")
beam  = simply_supported(10.0)
loads = [AppliedMoment(5.0, 10.0, label="M₀")]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

check("R_B",    rxn.reactions[10.0]["Fy"],  1.0)
check("R_A",    rxn.reactions[0.0]["Fy"],  -1.0)
check("M(5−)", res.M[np.searchsorted(res.x, 4.9999)], -5.0)
check("M(5+)", res.M[np.searchsorted(res.x, 5.0001)],  5.0)
check("M(0)",  res.M[0],  0.0)
check("M(10)", res.M[-1], 0.0)


# ═══════════════════════════════════════════════════════════════
#  CANTILEVER — Point load at free end
#  L=4, P=10 at x=4 → R_A=10, M_A=−40 kN·m
#  M(0) = −40, M(4) = 0
# ═══════════════════════════════════════════════════════════════
section("Cantilever (fixed left) — point load at free end (L=4, P=10)")
beam  = cantilever(4.0, fixed_at="left")
loads = [PointLoad(4.0, 10.0, label="P")]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

check("R_A",   rxn.reactions[0.0]["Fy"],  10.0)
check("M_A",   rxn.reactions[0.0]["M"],  -40.0)   # CCW reaction = negative CW
check("M(0+)", res.M[1],                 -40.0)
check("M(4)",  res.M[-1],                  0.0)
check("V(0+)", res.V[1],                  10.0)
check("V(4-)", res.V[-2],                 10.0)


# ═══════════════════════════════════════════════════════════════
#  CANTILEVER — Full UDL
#  L=5, w=8 kN/m → R_A=40, M_A=−100 kN·m
#  M(5) = 0, M(0) = −100 kN·m
# ═══════════════════════════════════════════════════════════════
section("Cantilever — full-span UDL (L=5, w=8 kN/m)")
beam  = cantilever(5.0, fixed_at="left")
loads = [UDL(0.0, 5.0, 8.0)]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

check("R_A",   rxn.reactions[0.0]["Fy"],  40.0)
check("M_A",   rxn.reactions[0.0]["M"],  -100.0)
check("M(0+)", res.M[1],                 -100.0, tol=0.05)   # near-zero x; small numerical offset
check("M(5)",  res.M[-1],                  0.0)


# ═══════════════════════════════════════════════════════════════
#  CANTILEVER (fixed right) — Point load at free (left) end
#  L=3, P=6 at x=0 → R=6 (upward at x=3), M_fix=−18 (CCW)
# ═══════════════════════════════════════════════════════════════
section("Cantilever (fixed RIGHT) — point load at free end (L=3, P=6)")
beam  = cantilever(3.0, fixed_at="right")
loads = [PointLoad(0.0, 6.0, label="P")]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

check("R(x=3)", rxn.reactions[3.0]["Fy"],  6.0)
check("M(x=3)", rxn.reactions[3.0]["M"],  18.0)    # CW reaction at right fixed end
check("M(0)",   res.M[0],                  0.0)
# M at section just left of right fixed end = -P*L = -6*3 = -18 (hogging, negative sagging)
check("M(3-)",  res.M[-2],               -18.0, tol=0.05)


# ═══════════════════════════════════════════════════════════════
#  OVERHANGING — Point load on overhang
#  L=10, pin@2, roller@8, P=15 at x=10
#  ΣM about pin: R_roller×6 = 15×8 → R_roller = 20
#  R_pin = 15 − 20 = −5  (downward)
# ═══════════════════════════════════════════════════════════════
section("Overhanging — point load on right overhang (L=10, pin@2, roller@8, P=15@10)")
beam  = overhanging(10.0, pin_pos=2.0, roller_pos=8.0)
loads = [PointLoad(10.0, 15.0, label="P")]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

check("R_pin",    rxn.reactions[2.0]["Fy"],  -5.0)
check("R_roller", rxn.reactions[8.0]["Fy"],  20.0)
check("ΣFy",      sum(r["Fy"] for r in rxn.reactions.values()) - 15.0, 0.0)
check("M(0)",     res.M[0],   0.0)
check("M(10)",    res.M[-1],  0.0)


# ═══════════════════════════════════════════════════════════════
#  OVERHANGING — UDL on full span + point load on overhang
#  L=12, pin@0, roller@9, UDL w=5 from 0 to 9, P=20 at x=12
# ═══════════════════════════════════════════════════════════════
section("Overhanging — UDL on span + point load on overhang")
beam  = overhanging(12.0, pin_pos=0.0, roller_pos=9.0)
loads = [UDL(0.0, 9.0, 5.0), PointLoad(12.0, 20.0, label="P")]
rxn   = solve_reactions(beam, loads)

# Manual check: ΣM_A = 5×9×4.5 + 20×12 = 202.5 + 240 = 442.5 → R_B = 442.5/9 = 49.17
# R_A = 45 + 20 - 49.17 = 15.83
R_B_exp = (5 * 9 * 4.5 + 20 * 12) / 9
R_A_exp = 5 * 9 + 20 - R_B_exp
check("R_pin",    rxn.reactions[0.0]["Fy"],  R_A_exp, tol=0.01)
check("R_roller", rxn.reactions[9.0]["Fy"],  R_B_exp, tol=0.01)
check("ΣFy",      sum(r["Fy"] for r in rxn.reactions.values()) - (5*9 + 20), 0.0, tol=0.01)


# ═══════════════════════════════════════════════════════════════
#  PROPPED CANTILEVER — Central point load (FEM solver)
#  L=6, P=10 at x=3
#  Standard formula: R_B = 5P/16 = 3.125 kN (propped end)
#  R_A = 11P/16 = 6.875 kN, M_A = −3PL/16 = −11.25 kN·m
# ═══════════════════════════════════════════════════════════════
section("Propped cantilever (FEM) — central point load (L=6, P=10)")
beam  = propped_cantilever(6.0, fixed_at="left")
loads = [PointLoad(3.0, 10.0, label="P")]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

R_B_exp = 5 * 10 / 16      # 3.125
R_A_exp = 11 * 10 / 16     # 6.875
M_A_exp = -3 * 10 * 6 / 16 # −11.25

check("R_B (roller)",  rxn.reactions[6.0]["Fy"],  R_B_exp, tol=0.02)
check("R_A (fixed)",   rxn.reactions[0.0]["Fy"],  R_A_exp, tol=0.02)
check("M_A (fixed)",   rxn.reactions[0.0]["M"],   M_A_exp, tol=0.05)
check("ΣFy",           sum(r["Fy"] for r in rxn.reactions.values()) - 10.0, 0.0, tol=0.01)
check("M(6)=0",        res.M[-1], 0.0, tol=0.05)


# ═══════════════════════════════════════════════════════════════
#  PROPPED CANTILEVER — Full UDL (FEM solver)
#  L=8, w=6 kN/m
#  Standard: R_B = 3wL/8 = 18 kN, R_A = 5wL/8 = 30 kN
#  M_A = −wL²/8 = −48 kN·m
# ═══════════════════════════════════════════════════════════════
section("Propped cantilever (FEM) — full UDL (L=8, w=6 kN/m)")
beam  = propped_cantilever(8.0, fixed_at="left")
loads = [UDL(0.0, 8.0, 6.0)]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

R_B_exp = 3 * 6 * 8 / 8    # 18.0
R_A_exp = 5 * 6 * 8 / 8    # 30.0
M_A_exp = -6 * 64 / 8      # −48.0

check("R_B",  rxn.reactions[8.0]["Fy"], R_B_exp, tol=0.05)
check("R_A",  rxn.reactions[0.0]["Fy"], R_A_exp, tol=0.05)
check("M_A",  rxn.reactions[0.0]["M"],  M_A_exp, tol=0.20)
check("M(8)", res.M[-1], 0.0, tol=0.05)


# ═══════════════════════════════════════════════════════════════
#  FIXED-FIXED — Central point load (FEM solver)
#  L=8, P=24 at x=4
#  Standard: R_A = R_B = 12, M_A = −M_B = PL/8 = 24 kN·m
# ═══════════════════════════════════════════════════════════════
section("Fixed-Fixed (FEM) — central point load (L=8, P=24)")
beam  = fixed_fixed(8.0)
loads = [PointLoad(4.0, 24.0, label="P")]
rxn   = solve_reactions(beam, loads)
res   = compute_sfd_bmd(beam, rxn.reactions, loads)

FEM_exp  = 24 / 2         # 12.0
M_fix_exp = -24 * 8 / 8   # −24.0 at left end, +24 at right

check("R_A",    rxn.reactions[0.0]["Fy"],  FEM_exp, tol=0.05)
check("R_B",    rxn.reactions[8.0]["Fy"],  FEM_exp, tol=0.05)
check("M_A",    rxn.reactions[0.0]["M"],   M_fix_exp, tol=0.10)
check("M_B",    rxn.reactions[8.0]["M"],   24.0,      tol=0.10)   # CW at right = +24
check("ΣFy",    sum(r["Fy"] for r in rxn.reactions.values()) - 24.0, 0.0, tol=0.01)


# ═══════════════════════════════════════════════════════════════
#  FIXED-FIXED — Full UDL (FEM solver)
#  L=6, w=10 kN/m
#  Standard: R_A = R_B = 30, M_A = −M_B = −wL²/12 = −30 kN·m
# ═══════════════════════════════════════════════════════════════
section("Fixed-Fixed (FEM) — full UDL (L=6, w=10 kN/m)")
beam  = fixed_fixed(6.0)
loads = [UDL(0.0, 6.0, 10.0)]
rxn   = solve_reactions(beam, loads)

R_exp  = 10 * 6 / 2          # 30.0
M_exp  = -10 * 36 / 12       # −30.0

check("R_A",  rxn.reactions[0.0]["Fy"],  R_exp,  tol=0.05)
check("R_B",  rxn.reactions[6.0]["Fy"],  R_exp,  tol=0.05)
check("M_A",  rxn.reactions[0.0]["M"],   M_exp,  tol=0.20)
check("M_B",  rxn.reactions[6.0]["M"],   -M_exp, tol=0.20)   # opposite sign at right


# ═══════════════════════════════════════════════════════════════
#  COMBINED LOADS — SS beam: UDL + point load + applied moment
#  L=10, w=5 from 0-10, P=20 at x=3, M₀=30 (CW) at x=7
# ═══════════════════════════════════════════════════════════════
section("SS beam — UDL + PointLoad + AppliedMoment (combined)")
beam  = simply_supported(10.0)
loads = [
    UDL(0.0, 10.0, 5.0),
    PointLoad(3.0, 20.0, label="P"),
    AppliedMoment(7.0, 30.0, label="M₀"),
]
rxn   = solve_reactions(beam, loads)

# ΣM_A: 5×10×5 + 20×3 + 30 − R_B×10 = 0
#       250 + 60 + 30 = 340  → R_B = 34
# R_A  = 50 + 20 − 34 = 36
R_B_exp = (5*10*5 + 20*3 + 30) / 10
R_A_exp = 5*10 + 20 - R_B_exp

check("R_B",  rxn.reactions[10.0]["Fy"], R_B_exp, tol=0.01)
check("R_A",  rxn.reactions[0.0]["Fy"],  R_A_exp, tol=0.01)
check("ΣFy",  sum(r["Fy"] for r in rxn.reactions.values()) - (5*10 + 20), 0.0, tol=0.01)


# ═══════════════════════════════════════════════════════════════
#  UVL ONLY — SS beam with trapezoidal load
#  L=6, w₁=4 at x=0, w₂=10 at x=6
#  F_total = (4+10)/2 × 6 = 42 kN
#  centroid from A = 6×(4+2×10)/(3×14) = 6×24/42 = 144/42 = 3.4286 m
#  R_B = 42×3.4286/6 = 24.0, R_A = 42−24 = 18
# ═══════════════════════════════════════════════════════════════
section("SS beam — trapezoidal UVL (w₁=4 → w₂=10, L=6)")
beam  = simply_supported(6.0)
loads = [UVL(0.0, 6.0, 4.0, 10.0)]
rxn   = solve_reactions(beam, loads)

F_total  = (4 + 10) / 2 * 6    # 42.0
centroid = 6 * (4 + 2*10) / (3 * (4 + 10))
R_B_exp  = F_total * centroid / 6
R_A_exp  = F_total - R_B_exp

check("Centroid", centroid, 144/42, tol=1e-6)
check("R_A",  rxn.reactions[0.0]["Fy"], R_A_exp, tol=0.01)
check("R_B",  rxn.reactions[6.0]["Fy"], R_B_exp, tol=0.01)
check("ΣFy",  sum(r["Fy"] for r in rxn.reactions.values()) - F_total, 0.0, tol=0.01)


# ═══════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
passed = sum(1 for ok, _ in results if ok)
total  = len(results)
rate   = 100 * passed / total if total else 0
print(f"  RESULTS:  {passed}/{total} checks passed  ({rate:.1f}%)")
if passed == total:
    print("  ALL CHECKS PASSED ✓")
else:
    print("\n  FAILED CHECKS:")
    for ok, msg in results:
        if not ok:
            print(" ", msg)
print(f"{'═'*60}\n")
