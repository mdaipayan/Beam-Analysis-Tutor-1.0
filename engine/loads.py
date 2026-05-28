"""
engine/loads.py
===============
Load data models for BeamEdu.

Supported load types
--------------------
  PointLoad      — Concentrated force at a single position (kN).
  UDL            — Uniformly Distributed Load over a span (kN/m).
  UVL            — Uniformly Varying Load; intensity varies linearly
                   from w₁ at start to w₂ at end (triangular or trapezoidal).
  AppliedMoment  — Concentrated couple / moment at a single position (kN·m).

Sign convention
---------------
  • Force magnitudes: positive = DOWNWARD (gravity direction).
  • Applied moment magnitude: positive = CLOCKWISE.
  • Position: measured from the LEFT end of the beam (m).

Helper functions
----------------
  total_vertical_force(loads)         → sum of all downward forces (kN)
  moment_about(loads, pivot)          → net clockwise moment about pivot (kN·m)
  intensity_at(load, x)               → distributed load intensity at position x
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Union
import numpy as np


# ──────────────────────────────────────────────
#  Enumeration
# ──────────────────────────────────────────────

class LoadType(str, Enum):
    POINT_LOAD     = "point_load"
    UDL            = "udl"
    UVL            = "uvl"
    APPLIED_MOMENT = "applied_moment"


# ──────────────────────────────────────────────
#  Load data classes
# ──────────────────────────────────────────────

@dataclass
class PointLoad:
    """
    Concentrated (point) load.

    Parameters
    ----------
    position : float
        Distance from left end (m).
    magnitude : float
        Force in kN.  Positive = downward.
    label : str, optional
        Display label (e.g. 'P₁').
    """
    position:  float
    magnitude: float         # kN, +ve downward
    label:     str = ""
    load_type: LoadType = field(default=LoadType.POINT_LOAD, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError(f"PointLoad position ({self.position}) cannot be negative.")


@dataclass
class UDL:
    """
    Uniformly Distributed Load.

    Parameters
    ----------
    start : float
        Start position from left end (m).
    end : float
        End position from left end (m).  Must satisfy start < end.
    intensity : float
        Load intensity in kN/m.  Positive = downward.
    label : str, optional
        Display label.
    """
    start:     float
    end:       float
    intensity: float         # kN/m, +ve downward
    label:     str = ""
    load_type: LoadType = field(default=LoadType.UDL, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("UDL start position cannot be negative.")
        if self.start >= self.end:
            raise ValueError(f"UDL: start ({self.start}) must be less than end ({self.end}).")

    @property
    def span(self) -> float:
        """Length of the loaded region (m)."""
        return self.end - self.start

    @property
    def total_force(self) -> float:
        """Resultant downward force (kN)."""
        return self.intensity * self.span

    @property
    def centroid(self) -> float:
        """Position of resultant from left end (m)."""
        return (self.start + self.end) / 2.0

    def intensity_at(self, x: float) -> float:
        """Intensity at position x (kN/m). Returns 0 outside the load span."""
        return self.intensity if self.start <= x <= self.end else 0.0


@dataclass
class UVL:
    """
    Uniformly Varying Load (triangular or trapezoidal).
    Intensity varies linearly from `intensity_start` at `start` to
    `intensity_end` at `end`.

    Parameters
    ----------
    start : float
        Start position from left end (m).
    end : float
        End position from left end (m).
    intensity_start : float
        Intensity at the start position (kN/m).  Positive = downward.
    intensity_end : float
        Intensity at the end position (kN/m).  Positive = downward.
    label : str, optional
        Display label.

    Notes
    -----
    • Triangular load: set one intensity to 0.
    • A UVL with intensity_start == intensity_end is a UDL; use the UDL class instead.
    """
    start:            float
    end:              float
    intensity_start:  float    # kN/m at start, +ve downward
    intensity_end:    float    # kN/m at end, +ve downward
    label:            str = ""
    load_type: LoadType = field(default=LoadType.UVL, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("UVL start position cannot be negative.")
        if self.start >= self.end:
            raise ValueError(f"UVL: start ({self.start}) must be less than end ({self.end}).")

    @property
    def span(self) -> float:
        return self.end - self.start

    @property
    def total_force(self) -> float:
        """Resultant downward force (kN) — area of the trapezoid."""
        return 0.5 * (self.intensity_start + self.intensity_end) * self.span

    @property
    def centroid(self) -> float:
        """
        Position of resultant from left end (m).

        Derivation (distance c̄ from `start`):
            c̄ = span × (w₁ + 2w₂) / (3(w₁ + w₂))
        where w₁ = intensity_start, w₂ = intensity_end.
        Reduces to span/3 for triangle (w₁=0) and span/2 for rectangle.
        """
        w1, w2 = self.intensity_start, self.intensity_end
        span   = self.span
        if abs(w1 + w2) < 1e-12:
            return self.start + span / 2.0
        dist_from_start = span * (w1 + 2.0 * w2) / (3.0 * (w1 + w2))
        return self.start + dist_from_start

    def intensity_at(self, x: float) -> float:
        """Linearly interpolated intensity at position x (kN/m)."""
        if x < self.start or x > self.end:
            return 0.0
        t = (x - self.start) / self.span
        return self.intensity_start + t * (self.intensity_end - self.intensity_start)


@dataclass
class AppliedMoment:
    """
    Concentrated external moment / couple applied to the beam.

    Parameters
    ----------
    position : float
        Distance from left end (m).
    magnitude : float
        Moment in kN·m.  Positive = clockwise.
    label : str, optional
        Display label.
    """
    position:  float
    magnitude: float         # kN·m, +ve clockwise
    label:     str = ""
    load_type: LoadType = field(default=LoadType.APPLIED_MOMENT, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError(f"AppliedMoment position ({self.position}) cannot be negative.")


# ──────────────────────────────────────────────
#  Union type alias
# ──────────────────────────────────────────────

AnyLoad = Union[PointLoad, UDL, UVL, AppliedMoment]


# ──────────────────────────────────────────────
#  Helper functions
# ──────────────────────────────────────────────

def total_vertical_force(loads: List[AnyLoad]) -> float:
    """
    Sum of all downward vertical forces from the load list (kN).
    Applied moments do not contribute to vertical force.
    """
    total = 0.0
    for load in loads:
        if isinstance(load, PointLoad):
            total += load.magnitude
        elif isinstance(load, (UDL, UVL)):
            total += load.total_force
    return total


def moment_about(loads: List[AnyLoad], pivot: float) -> float:
    """
    Net CLOCKWISE moment of all applied loads about a pivot point (kN·m).

    Used in equilibrium equations:
        ΣM_pivot = 0  →  moment_about(loads, pivot) − R_other × arm = 0

    Convention (positive = clockwise):
    • Downward force  at x > pivot  →  positive (CW)
    • Downward force  at x < pivot  →  negative (CCW)
    • CW applied moment             →  +magnitude  (independent of pivot)
    • CCW applied moment            →  −magnitude

    Parameters
    ----------
    loads : list of AnyLoad
        Applied loads only (NOT reactions).
    pivot : float
        x-coordinate of the pivot point (m).
    """
    M = 0.0
    for load in loads:
        if isinstance(load, PointLoad):
            arm = load.position - pivot       # +ve if load is to the right of pivot
            M  += load.magnitude * arm        # +ve force × +ve arm = CW
        elif isinstance(load, UDL):
            arm = load.centroid - pivot
            M  += load.total_force * arm
        elif isinstance(load, UVL):
            arm = load.centroid - pivot
            M  += load.total_force * arm
        elif isinstance(load, AppliedMoment):
            M  += load.magnitude              # CW moment adds directly, pivot-independent
    return M


def load_positions(loads: List[AnyLoad]) -> List[float]:
    """
    Collect all significant x-coordinates from the load list.
    Used by sfd_bmd.py to place critical sections.
    """
    positions = []
    for load in loads:
        if isinstance(load, PointLoad):
            positions.append(load.position)
        elif isinstance(load, (UDL, UVL)):
            positions.append(load.start)
            positions.append(load.end)
        elif isinstance(load, AppliedMoment):
            positions.append(load.position)
    return positions
