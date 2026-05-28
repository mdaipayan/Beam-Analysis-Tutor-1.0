"""
engine/beam.py
==============
Beam geometry and support configuration for BeamEdu.

Supports all standard structural beam types:
  • Simply supported    — pin + roller at any positions
  • Cantilever          — fixed at one end, free at the other
  • Propped cantilever  — fixed at one end, roller at the other
  • Fixed-fixed         — fixed at both ends
  • Overhanging         — pin + roller with beam extending beyond one or both supports

Sign convention (used throughout the engine)
--------------------------------------------
  • x   : measured from the LEFT end of the beam (m)
  • Fy  : positive = upward
  • M   : positive = sagging (tension at bottom fibre)
  • V   : positive = upward force on left face of cut section
  • Applied moment magnitude: positive = clockwise  (loads.py convention)
  • Reaction moment magnitude: positive = clockwise (reactions.py convention)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ──────────────────────────────────────────────
#  Enumerations
# ──────────────────────────────────────────────

class BeamType(str, Enum):
    SIMPLY_SUPPORTED   = "simply_supported"
    CANTILEVER         = "cantilever"
    PROPPED_CANTILEVER = "propped_cantilever"
    FIXED_FIXED        = "fixed_fixed"
    OVERHANGING        = "overhanging"


class SupportType(str, Enum):
    PIN    = "pin"     # Horizontal + vertical reaction; no moment
    ROLLER = "roller"  # Vertical reaction only
    FIXED  = "fixed"   # Horizontal + vertical reaction + moment
    FREE   = "free"    # No reaction (free end; used implicitly for cantilever tips)


# ──────────────────────────────────────────────
#  Core data classes
# ──────────────────────────────────────────────

@dataclass
class Support:
    """A structural support at a given position along the beam axis."""
    position: float           # Distance from the LEFT end of the beam (m), ≥ 0
    support_type: SupportType

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError(f"Support position ({self.position} m) cannot be negative.")

    @property
    def n_reactions(self) -> int:
        """Number of unknown reaction components at this support."""
        return {
            SupportType.PIN:    2,
            SupportType.ROLLER: 1,
            SupportType.FIXED:  3,
            SupportType.FREE:   0,
        }[self.support_type]


@dataclass
class Beam:
    """
    Beam geometry and support configuration.

    Parameters
    ----------
    length : float
        Total beam length (m).  Must be > 0.
    beam_type : BeamType
        Structural classification.
    supports : list[Support]
        Supports sorted left-to-right.  The constructor sorts them automatically.
    E : float
        Young's modulus (Pa).  Default = 200 GPa (structural steel).
    I : float
        Second moment of area (m⁴).  Default = 1 × 10⁻⁴ m⁴.

    Notes
    -----
    E and I affect deflection calculations but do NOT affect shear forces or
    bending moments for statically determinate beams.  They matter for
    indeterminate beams (propped cantilever, fixed-fixed) where the stiffness
    method is used to find redundant reactions.
    """
    length: float
    beam_type: BeamType
    supports: List[Support] = field(default_factory=list)
    E: float = 200e9   # Pa — structural steel
    I: float = 1e-4    # m⁴

    def __post_init__(self) -> None:
        if self.length <= 0:
            raise ValueError("Beam length must be positive.")
        self.supports = sorted(self.supports, key=lambda s: s.position)

    # ── Derived properties ────────────────────────────────────────────────

    @property
    def EI(self) -> float:
        """Flexural rigidity EI (N·m²)."""
        return self.E * self.I

    @property
    def left_support(self) -> Optional[Support]:
        return self.supports[0] if self.supports else None

    @property
    def right_support(self) -> Optional[Support]:
        return self.supports[-1] if len(self.supports) >= 2 else None

    def total_reactions(self) -> int:
        """Total number of unknown reaction components across all supports."""
        return sum(s.n_reactions for s in self.supports)

    def degree_of_indeterminacy(self) -> int:
        """
        Degree of static indeterminacy (DSI).
        For a 2-D beam: DSI = total reactions − 3 equilibrium equations.
        DSI = 0 → statically determinate.
        DSI > 0 → indeterminate (redundants must be found via compatibility).
        """
        return self.total_reactions() - 3

    def is_statically_determinate(self) -> bool:
        return self.degree_of_indeterminacy() == 0

    def support_at(self, position: float, tol: float = 1e-9) -> Optional[Support]:
        """Return the support at `position`, or None if no support exists there."""
        for s in self.supports:
            if abs(s.position - position) < tol:
                return s
        return None

    def __repr__(self) -> str:  # pragma: no cover
        dsi = self.degree_of_indeterminacy()
        kind = "determinate" if dsi == 0 else f"indeterminate (DSI={dsi})"
        return (
            f"Beam(type={self.beam_type.value}, L={self.length} m, "
            f"supports={[s.support_type.value for s in self.supports]}, {kind})"
        )


# ──────────────────────────────────────────────
#  Convenience constructors
# ──────────────────────────────────────────────

def simply_supported(
    length: float,
    pin_pos: float = 0.0,
    roller_pos: float | None = None,
    E: float = 200e9,
    I: float = 1e-4,
) -> Beam:
    """
    Pin at `pin_pos`, roller at `roller_pos` (default = length).
    Supports may be at the ends or inset (creating an overhang — but use
    `overhanging()` for clarity in that case).
    """
    if roller_pos is None:
        roller_pos = length
    return Beam(
        length=length,
        beam_type=BeamType.SIMPLY_SUPPORTED,
        supports=[
            Support(pin_pos,    SupportType.PIN),
            Support(roller_pos, SupportType.ROLLER),
        ],
        E=E, I=I,
    )


def cantilever(
    length: float,
    fixed_at: str = "left",
    E: float = 200e9,
    I: float = 1e-4,
) -> Beam:
    """Fixed support at one end; free at the other.  `fixed_at` = 'left' or 'right'."""
    pos = 0.0 if fixed_at.lower() == "left" else length
    return Beam(
        length=length,
        beam_type=BeamType.CANTILEVER,
        supports=[Support(pos, SupportType.FIXED)],
        E=E, I=I,
    )


def propped_cantilever(
    length: float,
    fixed_at: str = "left",
    E: float = 200e9,
    I: float = 1e-4,
) -> Beam:
    """Fixed at one end, roller (prop) at the other.  `fixed_at` = 'left' or 'right'."""
    if fixed_at.lower() == "left":
        return Beam(
            length=length,
            beam_type=BeamType.PROPPED_CANTILEVER,
            supports=[
                Support(0.0,    SupportType.FIXED),
                Support(length, SupportType.ROLLER),
            ],
            E=E, I=I,
        )
    else:
        return Beam(
            length=length,
            beam_type=BeamType.PROPPED_CANTILEVER,
            supports=[
                Support(0.0,    SupportType.ROLLER),
                Support(length, SupportType.FIXED),
            ],
            E=E, I=I,
        )


def fixed_fixed(
    length: float,
    E: float = 200e9,
    I: float = 1e-4,
) -> Beam:
    """Fixed supports at both ends."""
    return Beam(
        length=length,
        beam_type=BeamType.FIXED_FIXED,
        supports=[
            Support(0.0,    SupportType.FIXED),
            Support(length, SupportType.FIXED),
        ],
        E=E, I=I,
    )


def overhanging(
    length: float,
    pin_pos: float,
    roller_pos: float,
    E: float = 200e9,
    I: float = 1e-4,
) -> Beam:
    """
    Overhanging beam — pin and roller at arbitrary positions, beam extends
    from x = 0 to x = length with supports interior or at edges.

    Example: length=10, pin_pos=2, roller_pos=7
        → 2 m left overhang, 3 m right overhang.

    The beam is statically determinate (same equilibrium equations as SS).
    """
    if not (0.0 <= pin_pos < roller_pos <= length):
        raise ValueError(
            f"Require 0 ≤ pin_pos ({pin_pos}) < roller_pos ({roller_pos}) ≤ length ({length})."
        )
    return Beam(
        length=length,
        beam_type=BeamType.OVERHANGING,
        supports=[
            Support(pin_pos,    SupportType.PIN),
            Support(roller_pos, SupportType.ROLLER),
        ],
        E=E, I=I,
    )
