# BeamEdu — Interactive SFD & BMD Teaching Tool

A Python engine for computing Shear Force and Bending Moment Diagrams 
for all standard beam types, developed for a Streamlit teaching application 
targeting publication in *Computer Applications in Engineering Education* (CAEE).

## Supported beam types
- Simply supported
- Cantilever (fixed left or right)
- Propped cantilever
- Fixed-fixed
- Overhanging

## Supported load types
- Point load
- Uniformly Distributed Load (UDL)
- Uniformly Varying Load / UVL (triangular & trapezoidal)
- Applied moment (couple)

## Quick start
```bash
pip install -r requirements.txt
python test_engine.py
```

## Engine modules
| Module | Description |
|---|---|
| `engine/beam.py` | Beam geometry & support data model |
| `engine/loads.py` | All load types |
| `engine/reactions.py` | Analytical + FEM reaction solver |
| `engine/sfd_bmd.py` | SFD/BMD computation with step-by-step output |
| `engine/plotter.py` | Matplotlib 3-panel figure |

## Author
D. Mandal, KITS Ramtek, Nagpur University
