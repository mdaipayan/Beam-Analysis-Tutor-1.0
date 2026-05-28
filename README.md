# BeamEdu — Interactive SFD & BMD Teaching Tool

An interactive Streamlit application that teaches students how to construct
**Shear Force Diagrams (SFD)** and **Bending Moment Diagrams (BMD)** from
scratch, with full step-by-step worked solutions. Built for a research study
targeting *Computer Applications in Engineering Education* (CAEE).

## Features

- **All standard beam types**: simply supported, cantilever (left/right),
  propped cantilever, fixed-fixed, overhanging.
- **All load types**: point load, UDL, UVL (triangular/trapezoidal), applied moment.
- **Step-by-step solver**: reactions (analytical for determinate beams, stiffness
  FEM for indeterminate beams) and segment-by-segment SFD/BMD with LaTeX equations.
- **Interactive visualiser**: combined FBD + SFD + BMD figure with a section probe.
- **Concept quiz**: pre/post assessment with learning-gain tracking.
- **PDF report export** (ReportLab) and **CSV research-data export** (SQLite).

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

## Validate the engine

```bash
python test_engine.py
```

Runs 75 checks across all beam and load combinations against known
textbook solutions (expected: 75/75 passed).

## Project structure

```
beamedu/
├── app.py                    # Streamlit entry point (Home)
├── pages/
│   ├── 1_Beam_Builder.py     # configure beam + loads (presets or custom)
│   ├── 2_Step_Solver.py      # worked reactions + SFD/BMD steps
│   ├── 3_Visualizer.py       # interactive diagrams + section probe
│   ├── 4_Quiz.py             # pre/post concept assessment
│   └── 5_Report.py           # PDF report + research CSV export
├── engine/                   # pure-Python calculation core (no Streamlit)
│   ├── beam.py               # beam geometry & support model
│   ├── loads.py              # load types
│   ├── reactions.py          # analytical + stiffness FEM solver
│   ├── sfd_bmd.py            # SFD/BMD computation + step generation
│   └── plotter.py            # matplotlib figures
├── utils/
│   ├── session.py            # session-state manager
│   ├── analytics.py          # SQLite logger (research data)
│   └── pdf_report.py         # ReportLab PDF generator
├── data/
│   ├── templates.json        # 21 preset problems
│   └── quiz_bank.json        # 12 concept questions
├── .streamlit/config.toml    # theme
├── requirements.txt
└── test_engine.py            # 75-check validation suite
```

## Sign convention

| Quantity | Positive |
|---|---|
| Position x | from left end |
| Reaction R | upward |
| Shear V | upward on left face of cut |
| Moment M | sagging (tension at bottom) |
| Applied moment | clockwise |

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (public).
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo.
3. Set the main file to `app.py` and deploy.

## Author

D. Mandal, Department of Civil Engineering, KITS Ramtek (RTMNU, Nagpur).
