"""
utils/ui.py
===========
Shared visual identity for BeamEdu — a polished, journal-ready academic theme.

One import, one call: `from utils.ui import apply_theme; apply_theme()` at the
top of every page (after st.set_page_config). It injects a cohesive navy/teal
palette, a serif display face (Fraunces) paired with a clean sans-serif body
(Inter), and a set of reusable helpers (hero, section_header, metric_card, pill)
so the pages stay consistent and free of inline CSS.

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

INK   = "#1a2733"   # near-black slate, body text
NAVY  = "#1f5673"   # primary brand
TEAL  = "#2f8f9d"   # secondary accent
GOLD  = "#bd8b3c"   # warm accent for callouts (muted)
PAPER = "#fbfaf7"   # warm, clean app background
SAND  = "#f4f1e8"   # soft secondary surface
LINE  = "#e4ded2"   # hairline borders

# Plotly palette (imported by plotly_plotter via these names if desired)
PLOT = dict(
    beam="#2b2b2b", support=NAVY, load_dn="#b3402f", load_up="#3a6b35",
    moment="#7a4ea3", reaction=TEAL, sfd=NAVY, sfd_fill="rgba(31,86,115,0.18)",
    bmd=TEAL, bmd_fill="rgba(47,143,157,0.20)", cut=GOLD, grid="#e9e3d6",
)

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

:root {{
  --ink:{INK}; --navy:{NAVY}; --teal:{TEAL}; --gold:{GOLD};
  --paper:{PAPER}; --sand:{SAND}; --line:{LINE};
}}

/* ---- Base typography ---- */
html, body, [class*="css"], .stMarkdown, p, li, span, label, div {{
  font-family:'Inter', system-ui, -apple-system, sans-serif;
  font-size:16px;
  color:var(--ink);
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
}}
.stMarkdown p, .stMarkdown li {{ line-height:1.7; color:#34424f; }}
/* Widget labels, captions, select boxes */
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stSlider label, .stRadio label, .stCheckbox label,
.stToggle label, .stMultiSelect label {{
  font-family:'Inter', system-ui, sans-serif !important;
  font-size:.88rem !important;
  font-weight:600 !important;
  color:#42505d !important;
  letter-spacing:.02em;
  text-transform:none;
}}
.stCaption, [data-testid="stCaptionContainer"] p {{
  font-family:'Inter', system-ui, sans-serif !important;
  font-size:.86rem !important;
  color:#697882 !important;
  line-height:1.55;
}}
h1,h2,h3,h4,.be-display {{
  font-family:'Fraunces', Georgia, serif !important;
  letter-spacing:-0.018em; color:var(--navy); font-weight:600;
  line-height:1.18;
}}
h2 {{ font-size:clamp(1.45rem, 2vw, 1.7rem) !important; margin-top:.4rem; }}
h3 {{ font-size:clamp(1.15rem, 1.6vw, 1.32rem) !important; }}
.stApp {{ background:
  radial-gradient(1100px 520px at 88% -8%, rgba(47,143,157,0.045), transparent 62%),
  radial-gradient(820px 460px at -6% 108%, rgba(31,86,115,0.035), transparent 58%),
  var(--paper); }}

/* ---- Elegant page rhythm: roomier, centred reading column ---- */
.block-container {{
  padding-top:3rem !important;
  padding-bottom:4rem !important;
  max-width:1180px;
}}
/* Softer, more refined dividers */
hr, [data-testid="stDivider"] {{
  border:none !important; height:1px !important;
  background:linear-gradient(90deg, transparent, var(--line) 18%, var(--line) 82%, transparent) !important;
  margin:1.6rem 0 !important;
}}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {{
  background:linear-gradient(180deg,#16303f 0%, #1f5673 100%);
  border-right:1px solid rgba(0,0,0,0.1);
}}
section[data-testid="stSidebar"] * {{
  color:#eef3f4 !important;
  font-family:'Inter', system-ui, sans-serif !important;
}}
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stTextInput label {{
  color:#cfe0e4 !important;
  font-size:.85rem !important;
}}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] .stCaption {{
  font-size:.83rem !important;
  color:#b0c8ce !important;
  line-height:1.55;
}}

/* ---- Hero band ---- */
.be-hero {{
  position:relative; border-radius:20px; padding:34px 38px; margin:2px 0 28px;
  background:linear-gradient(125deg,#14303f 0%, #1f5673 60%, #2c8593 130%);
  color:#fff; overflow:hidden;
  box-shadow:0 24px 60px -32px rgba(20,40,55,0.65);
}}
.be-hero:before {{
  content:""; position:absolute; inset:0;
  background:
    radial-gradient(620px 280px at 92% -30%, rgba(120,210,222,0.22), transparent 70%),
    radial-gradient(520px 240px at -6% 130%, rgba(255,255,255,0.08), transparent 70%),
    linear-gradient(90deg, rgba(255,255,255,0.08) 0 1px, transparent 1px 80px),
    linear-gradient(0deg, rgba(255,255,255,0.055) 0 1px, transparent 1px 80px);
}}
.be-hero:after {{
  content:""; position:absolute; left:42px; bottom:0; top:0; width:3px;
  background:linear-gradient(180deg, transparent, rgba(159,211,218,0.7), transparent);
  display:none;
}}
.be-hero-content {{
  position:relative; display:flex; align-items:center; gap:18px;
}}
.be-hero-icon {{
  flex:0 0 auto; width:58px; height:58px; border-radius:18px;
  display:grid; place-items:center;
  background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.22);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.16), 0 14px 28px -22px rgba(0,0,0,.55);
  font-family:'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji',system-ui,sans-serif !important;
  font-size:1.9rem !important; line-height:1;
}}
.be-hero-copy {{ min-width:0; }}
.be-hero h1 {{
  color:#fff !important; font-size:clamp(2rem, 4vw, 2.65rem) !important; margin:0 0 8px;
  line-height:1.06; letter-spacing:-0.02em; position:relative;
  text-shadow:0 2px 16px rgba(0,0,0,.22);
}}
.be-hero p {{
  color:#d6e7ea; font-size:clamp(1rem, 1.35vw, 1.08rem) !important; margin:0; max-width:62ch;
  position:relative; line-height:1.62;
}}
.be-hero .be-kicker {{
  display:inline-block; font-family:'Inter'; font-weight:700;
  text-transform:uppercase; letter-spacing:.18em; font-size:.76rem !important;
  color:#a7dae0; margin-bottom:12px; position:relative;
}}
@media (max-width: 640px) {{
  .be-hero {{ padding:26px 24px; }}
  .be-hero-content {{ align-items:flex-start; gap:14px; }}
  .be-hero-icon {{ width:48px; height:48px; border-radius:15px; font-size:1.55rem !important; }}
}}

/* ---- Section header ---- */
.be-sec {{ display:flex; align-items:baseline; gap:12px; margin:8px 0 4px; }}
.be-sec .n {{ font-family:'Fraunces',serif; font-weight:700; color:var(--teal);
  font-size:1.05rem; border:1.5px solid var(--teal); border-radius:50%;
  width:30px; height:30px; display:grid; place-items:center; flex:none; }}
.be-sec h3 {{ margin:0; }}

/* ---- Cards / pills ---- */
.be-card {{ background:#fff; border:1px solid var(--line); border-radius:16px;
  padding:18px 20px; box-shadow:0 12px 32px -26px rgba(20,32,43,0.45); }}
.be-pill {{ display:inline-block; padding:4px 12px; border-radius:999px;
  font-size:.76rem; font-weight:600; letter-spacing:.03em; }}
.be-pill.det  {{ background:#e8f1ec; color:#2f6d4f; border:1px solid #c4ddcc; }}
.be-pill.ind  {{ background:#f6edda; color:#8a5b16; border:1px solid #e6cf9f; }}
.be-pill.teal {{ background:#e6f1f3; color:#1f5673; border:1px solid #bedfe3; }}

/* ---- Generic bordered containers (st.container(border=True)) ---- */
[data-testid="stVerticalBlockBorderWrapper"] {{
  border-radius:18px !important;
  border:1px solid rgba(228,222,210,.9) !important;
  background:rgba(255,255,255,0.82);
  box-shadow:0 16px 42px -34px rgba(20,32,43,0.48);
  backdrop-filter:blur(6px);
}}

/* ---- Metric polish ---- */
[data-testid="stMetric"] {{
  background:linear-gradient(180deg,#fff,rgba(255,255,255,.86));
  border:1px solid var(--line); border-radius:16px;
  padding:14px 16px; box-shadow:0 10px 28px -24px rgba(20,32,43,0.45);
  transition:transform .12s ease, box-shadow .2s ease;
}}
[data-testid="stMetric"]:hover {{
  transform:translateY(-2px);
  box-shadow:0 16px 36px -26px rgba(20,32,43,0.5);
}}
[data-testid="stMetricValue"] {{
  font-family:'Fraunces',serif !important;
  font-size:1.62rem !important;
  color:var(--navy) !important;
  font-weight:600;
  letter-spacing:-0.01em;
}}
[data-testid="stMetricLabel"] p {{
  font-family:'Inter', system-ui, sans-serif !important;
  color:#6a7884 !important;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:.08em;
  font-size:.72rem !important;
}}

/* ---- Buttons ---- */
.stButton>button, .stDownloadButton>button {{
  border-radius:10px; font-weight:600; border:1px solid var(--line);
  padding:7px 18px; letter-spacing:.01em;
  transition:transform .1s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
}}
.stButton>button:hover, .stDownloadButton>button:hover {{
  transform:translateY(-1px); border-color:var(--teal);
  box-shadow:0 14px 28px -20px rgba(20,32,43,.6);
}}
.stButton>button[kind="primary"] {{
  background:linear-gradient(120deg,var(--navy),var(--teal)); border:none; color:#fff;
}}
.stButton>button[kind="primary"]:hover {{
  box-shadow:0 16px 30px -16px rgba(31,86,115,.55);
}}

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"] {{
  gap:4px; border-bottom:1px solid var(--line); padding-bottom:0;
}}
.stTabs [data-baseweb="tab"] {{
  background:transparent; border-radius:9px 9px 0 0; padding:9px 18px;
  font-weight:600; color:#6a7884; transition:color .15s ease, background .15s ease;
}}
.stTabs [data-baseweb="tab"]:hover {{ background:var(--sand); color:var(--navy); }}
.stTabs [aria-selected="true"] {{
  background:#fff; color:var(--navy);
  border-bottom:2px solid var(--teal);
}}

/* ---- Forms & inputs ---- */
.stTextInput>div>div>input,
.stNumberInput>div>div>input {{
  border-radius:8px !important;
  border:1.5px solid var(--line) !important;
  font-family:'Inter', system-ui, sans-serif !important;
  font-size:.96rem !important;
  padding:7px 11px !important;
  transition:border-color .15s ease;
}}
.stTextInput>div>div>input:focus,
.stNumberInput>div>div>input:focus {{
  border-color:var(--teal) !important;
  box-shadow:0 0 0 3px rgba(47,143,157,.12) !important;
}}
.stSelectbox>div>div {{
  border-radius:8px !important;
  border:1.5px solid var(--line) !important;
}}
.stFormSubmitButton>button {{
  border-radius:10px !important;
  font-weight:600 !important;
  background:linear-gradient(120deg,var(--navy),var(--teal)) !important;
  color:#fff !important;
  border:none !important;
  padding:8px 22px !important;
}}

/* ---- Dataframe / tables ---- */
[data-testid="stDataFrame"] {{
  border-radius:10px;
  border:1px solid var(--line);
  overflow:hidden;
}}

/* ---- Radio buttons ---- */
.stRadio>div>label {{
  font-family:'Inter', system-ui, sans-serif !important;
  font-size:.96rem !important;
}}

/* ---- Info / warning / success alerts ---- */
.stAlert {{ border-radius:14px; font-size:.96rem; border:1px solid rgba(228,222,210,.8); }}

/* ---- Plotly card surface ---- */
[data-testid="stPlotlyChart"] {{
  border-radius:16px;
  overflow:hidden;
  border:1px solid var(--line);
  box-shadow:0 16px 38px -34px rgba(20,32,43,.55);
}}

/* ---- Misc ---- */
hr {{ border-color:var(--line); }}
.be-foot {{ color:#7d8a93; font-size:.8rem; }}
[data-testid="stExpander"] {{ border-radius:12px; border:1px solid var(--line); }}
[data-testid="stExpander"] summary {{
  font-family:'Inter', system-ui, sans-serif !important;
  font-weight:600 !important;
  font-size:.98rem !important;
}}

/* ---- Page title ---- */
h1[data-testid="stHeading"] {{
  font-family:'Fraunces', Georgia, serif !important;
  font-size:clamp(1.85rem, 3vw, 2.2rem) !important;
  font-weight:600 !important;
  color:var(--navy) !important;
  letter-spacing:-0.01em;
  margin-bottom:.25rem;
}}
</style>
"""


def apply_theme() -> None:
    """Inject the BeamEdu theme. Call once per page, after set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str = "", kicker: str = "BeamEdu", icon: str = "") -> None:
    """Render a consistent hero banner with an optional page icon."""
    icon_html = f'<span class="be-hero-icon" aria-hidden="true">{icon}</span>' if icon else ""
    st.markdown(
        f"""<div class="be-hero">
              <div class="be-hero-content">
                {icon_html}
                <div class="be-hero-copy">
                  <span class="be-kicker">{kicker}</span>
                  <h1>{title}</h1>
                  {f'<p>{subtitle}</p>' if subtitle else ''}
                </div>
              </div>
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
