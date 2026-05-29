"""
utils/ui.py
===========
Shared visual identity for BeamEdu — a polished, journal-ready academic theme.

One import, one call: `from utils.ui import apply_theme; apply_theme()` at the
top of every page (after st.set_page_config). It injects a cohesive navy/teal
palette, a serif display face (Fraunces) paired with a clean grotesque body
(Schibsted Grotesk), and a set of reusable helpers (hero, section_header,
metric_card, pill) so the pages stay consistent and free of inline CSS.

Palette
-------
  ink      #14202b   near-black navy, body text
  navy     #1f5673   primary brand
  teal     #2f8f9d   secondary accent (reactions, highlights)
  gold     #c08a2d   warm accent for callouts
  paper    #fbfaf7   warm off-white background
  sand     #f1ede4   secondary surface
"""

from __future__ import annotations
import streamlit as st

INK   = "#14202b"
NAVY  = "#1f5673"
TEAL  = "#2f8f9d"
GOLD  = "#c08a2d"
PAPER = "#fbfaf7"
SAND  = "#f1ede4"
LINE  = "#ddd6c8"

# Plotly palette (imported by plotly_plotter via these names if desired)
PLOT = dict(
    beam="#2b2b2b", support=NAVY, load_dn="#b3402f", load_up="#3a6b35",
    moment="#7a4ea3", reaction=TEAL, sfd=NAVY, sfd_fill="rgba(31,86,115,0.18)",
    bmd=TEAL, bmd_fill="rgba(47,143,157,0.20)", cut=GOLD, grid="#e9e3d6",
)

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Schibsted+Grotesk:wght@400;500;600;700&display=swap');

:root {{
  --ink:{INK}; --navy:{NAVY}; --teal:{TEAL}; --gold:{GOLD};
  --paper:{PAPER}; --sand:{SAND}; --line:{LINE};
}}

/* ---- Base typography ---- */
html, body, [class*="css"], .stMarkdown, p, li, span, label, div {{
  font-family:'Schibsted Grotesk', system-ui, sans-serif;
  color:var(--ink);
}}
h1,h2,h3,h4,.be-display {{
  font-family:'Fraunces', Georgia, serif !important;
  letter-spacing:-0.01em; color:var(--navy); font-weight:600;
}}
.stApp {{ background:
  radial-gradient(1200px 600px at 85% -5%, rgba(47,143,157,0.06), transparent 60%),
  radial-gradient(900px 500px at -5% 110%, rgba(31,86,115,0.05), transparent 55%),
  var(--paper); }}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {{
  background:linear-gradient(180deg,#16303f 0%, #1f5673 100%);
  border-right:1px solid rgba(0,0,0,0.1);
}}
section[data-testid="stSidebar"] * {{ color:#eef3f4 !important; }}
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stTextInput label {{ color:#cfe0e4 !important; }}

/* ---- Hero band ---- */
.be-hero {{
  position:relative; border-radius:18px; padding:30px 34px; margin:4px 0 22px;
  background:linear-gradient(120deg,#16303f 0%, #1f5673 55%, #2f8f9d 130%);
  color:#fff; overflow:hidden; box-shadow:0 18px 40px -22px rgba(20,32,43,0.6);
}}
.be-hero:before {{
  content:""; position:absolute; inset:0;
  background-image:repeating-linear-gradient(90deg,rgba(255,255,255,0.05) 0 1px,transparent 1px 46px);
  opacity:.5;
}}
.be-hero h1 {{ color:#fff !important; font-size:2.4rem; margin:0 0 6px; line-height:1.04; }}
.be-hero p {{ color:#dbe9ec; font-size:1.04rem; margin:0; max-width:60ch; position:relative; }}
.be-hero .be-kicker {{
  display:inline-block; font-family:'Schibsted Grotesk'; font-weight:600;
  text-transform:uppercase; letter-spacing:.16em; font-size:.72rem;
  color:#9fd3da; margin-bottom:10px; position:relative;
}}

/* ---- Section header ---- */
.be-sec {{ display:flex; align-items:baseline; gap:12px; margin:8px 0 4px; }}
.be-sec .n {{ font-family:'Fraunces',serif; font-weight:700; color:var(--teal);
  font-size:1.05rem; border:1.5px solid var(--teal); border-radius:50%;
  width:30px; height:30px; display:grid; place-items:center; flex:none; }}
.be-sec h3 {{ margin:0; }}

/* ---- Cards / pills ---- */
.be-card {{ background:#fff; border:1px solid var(--line); border-radius:14px;
  padding:16px 18px; box-shadow:0 8px 24px -20px rgba(20,32,43,0.5); }}
.be-pill {{ display:inline-block; padding:3px 11px; border-radius:999px;
  font-size:.78rem; font-weight:600; letter-spacing:.02em; }}
.be-pill.det  {{ background:#e6f0ec; color:#2f6d4f; border:1px solid #bcdcc9; }}
.be-pill.ind  {{ background:#f6ecd9; color:#8a5b16; border:1px solid #e4cd9c; }}
.be-pill.teal {{ background:#e3f0f2; color:#1f5673; border:1px solid #b9dde2; }}

/* ---- Metric polish ---- */
[data-testid="stMetric"] {{
  background:#fff; border:1px solid var(--line); border-radius:12px;
  padding:12px 14px; box-shadow:0 6px 18px -16px rgba(20,32,43,0.5);
}}
[data-testid="stMetricValue"] {{ font-family:'Fraunces',serif; color:var(--navy); }}
[data-testid="stMetricLabel"] p {{ color:#5b6b78 !important; font-weight:600;
  text-transform:uppercase; letter-spacing:.05em; font-size:.7rem; }}

/* ---- Buttons ---- */
.stButton>button, .stDownloadButton>button {{
  border-radius:10px; font-weight:600; border:1px solid var(--line);
  transition:transform .08s ease, box-shadow .15s ease;
}}
.stButton>button:hover, .stDownloadButton>button:hover {{
  transform:translateY(-1px); box-shadow:0 10px 22px -16px rgba(20,32,43,.7);
}}
.stButton>button[kind="primary"] {{
  background:linear-gradient(120deg,var(--navy),var(--teal)); border:none; color:#fff;
}}

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"] {{ gap:6px; }}
.stTabs [data-baseweb="tab"] {{
  background:var(--sand); border-radius:10px 10px 0 0; padding:8px 16px;
  font-weight:600;
}}
.stTabs [aria-selected="true"] {{ background:#fff; color:var(--navy); border-bottom:2px solid var(--teal); }}

/* ---- Misc ---- */
hr {{ border-color:var(--line); }}
.be-foot {{ color:#7d8a93; font-size:.8rem; }}
.stAlert {{ border-radius:12px; }}
[data-testid="stExpander"] {{ border-radius:12px; border:1px solid var(--line); }}
</style>
"""


def apply_theme() -> None:
    """Inject the BeamEdu theme. Call once per page, after set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str = "", kicker: str = "BeamEdu") -> None:
    st.markdown(
        f"""<div class="be-hero">
              <span class="be-kicker">{kicker}</span>
              <h1>{title}</h1>
              {f'<p>{subtitle}</p>' if subtitle else ''}
            </div>""",
        unsafe_allow_html=True,
    )


def section_header(num, title: str) -> None:
    st.markdown(
        f"""<div class="be-sec"><span class="n">{num}</span><h3>{title}</h3></div>""",
        unsafe_allow_html=True,
    )


def pill(text: str, kind: str = "teal") -> str:
    """Return HTML for an inline status pill (use inside st.markdown)."""
    return f'<span class="be-pill {kind}">{text}</span>'


def determinacy_pill(dsi: int) -> str:
    if dsi == 0:
        return pill("Statically determinate", "det")
    return pill(f"Indeterminate · DSI {dsi}", "ind")
