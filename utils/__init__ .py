"""
engine/__init__.py
==================
BeamEdu core engine — public API.

Quick usage
-----------
    from engine import (
        simply_supported, cantilever, propped_cantilever, fixed_fixed, overhanging,
        PointLoad, UDL, UVL, AppliedMoment,
        solve_reactions,
        compute_sfd_bmd,
        create_combined_figure,
    )

    beam  = simply_supported(6.0)
    loads = [PointLoad(3.0, 20.0, label="P")]
    rxn   = solve_reactions(beam, loads)
    res   = compute_sfd_bmd(beam, rxn.reactions, loads)
    fig   = create_combined_figure(beam, loads, rxn.reactions, res)
"""

# Beam constructors & types
from .beam import (
    Beam,
    BeamType,
    SupportType,
    Support,
    simply_supported,
    cantilever,
    propped_cantilever,
    fixed_fixed,
    overhanging,
)

# Load types & helpers
from .loads import (
    LoadType,
    PointLoad,
    UDL,
    UVL,
    AppliedMoment,
    AnyLoad,
    total_vertical_force,
    moment_about,
    load_positions,
)

# Reaction solver
from .reactions import (
    ReactionResult,
    solve_reactions,
)

# SFD / BMD engine
from .sfd_bmd import (
    CriticalSection,
    SFDBMDResult,
    compute_sfd_bmd,
)

# Plotter (matplotlib — used by PDF report)
from .plotter import (
    plot_beam_diagram,
    plot_sfd,
    plot_bmd,
    create_combined_figure,
)

# Interactive plotter (Plotly — used by live student pages)
from .plotly_plotter import (
    beam_fbd_figure,
    sfd_bmd_figure,
    single_diagram_figure,
)

__all__ = [
    # beam
    "Beam", "BeamType", "SupportType", "Support",
    "simply_supported", "cantilever", "propped_cantilever", "fixed_fixed", "overhanging",
    # loads
    "LoadType", "PointLoad", "UDL", "UVL", "AppliedMoment", "AnyLoad",
    "total_vertical_force", "moment_about", "load_positions",
    # reactions
    "ReactionResult", "solve_reactions",
    # sfd_bmd
    "CriticalSection", "SFDBMDResult", "compute_sfd_bmd",
    # plotter
    "plot_beam_diagram", "plot_sfd", "plot_bmd", "create_combined_figure",
    # plotly plotter
    "beam_fbd_figure", "sfd_bmd_figure", "single_diagram_figure",
]
