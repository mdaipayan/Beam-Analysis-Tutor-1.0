"""
utils/pdf_report.py
==================
ReportLab PDF generator for BeamEdu solutions.

Produces a professional, multi-section report:
  1. Title + problem statement (beam type, loads)
  2. Support reactions with method
  3. Step-by-step reaction solution
  4. Step-by-step SFD/BMD segment analysis
  5. Combined diagram figure (FBD + SFD + BMD)
  6. Key results summary table

Returns the PDF as bytes for use with st.download_button.
"""

from __future__ import annotations

import io
from typing import List, Dict

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

from engine import (
    Beam, AnyLoad, PointLoad, UDL, UVL, AppliedMoment,
    ReactionResult, SFDBMDResult, create_combined_figure,
)

_ACCENT      = colors.HexColor("#215868")
_ACCENT_LITE = colors.HexColor("#d5e3e8")
_PASS_GREEN  = colors.HexColor("#2e7d32")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(
        "BeamTitle", parent=ss["Title"], fontSize=20, textColor=_ACCENT,
        spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        "Sub", parent=ss["Normal"], fontSize=10, textColor=colors.grey,
        spaceAfter=12,
    ))
    ss.add(ParagraphStyle(
        "H2", parent=ss["Heading2"], fontSize=13, textColor=_ACCENT,
        spaceBefore=12, spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        "StepTitle", parent=ss["Normal"], fontSize=10.5, textColor=colors.black,
        fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        "StepBody", parent=ss["Normal"], fontSize=9.5, leading=13,
        leftIndent=12, textColor=colors.HexColor("#333333"),
    ))
    return ss


def _load_description(loads: List[AnyLoad]) -> List[str]:
    lines = []
    for ld in loads:
        if isinstance(ld, PointLoad):
            lines.append(f"Point load {ld.label or 'P'} = {ld.magnitude:.2f} kN at x = {ld.position:.2f} m")
        elif isinstance(ld, UDL):
            lines.append(f"UDL {ld.label or 'w'} = {ld.intensity:.2f} kN/m over x = {ld.start:.2f}-{ld.end:.2f} m")
        elif isinstance(ld, UVL):
            lines.append(f"UVL {ld.label or 'w'}: {ld.intensity_start:.2f} to {ld.intensity_end:.2f} kN/m over x = {ld.start:.2f}-{ld.end:.2f} m")
        elif isinstance(ld, AppliedMoment):
            d = "CW" if ld.magnitude >= 0 else "CCW"
            lines.append(f"Applied moment {ld.label or 'M0'} = {abs(ld.magnitude):.2f} kN·m ({d}) at x = {ld.position:.2f} m")
    return lines


def build_pdf(
    beam:      Beam,
    loads:     List[AnyLoad],
    reactions: ReactionResult,
    result:    SFDBMDResult,
    student_id: str = "",
) -> bytes:
    """
    Build the full solution PDF and return it as bytes.
    """
    ss     = _styles()
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=1.8*cm, bottomMargin=1.8*cm,
        title="BeamEdu Solution Report",
    )
    story = []

    # ── Title ──────────────────────────────────────────────────────────
    story.append(Paragraph("BeamEdu — Solution Report", ss["BeamTitle"]))
    beam_name = beam.beam_type.value.replace("_", " ").title()
    dsi = beam.degree_of_indeterminacy()
    det = "Statically determinate" if dsi == 0 else f"Statically indeterminate (DSI = {dsi})"
    story.append(Paragraph(
        f"{beam_name} &nbsp;|&nbsp; L = {beam.length:.2f} m &nbsp;|&nbsp; {det}"
        + (f" &nbsp;|&nbsp; ID: {student_id}" if student_id else ""),
        ss["Sub"],
    ))

    # ── Problem statement ───────────────────────────────────────────────
    story.append(Paragraph("1. Problem statement", ss["H2"]))
    sup_lines = [f"{s.support_type.value.title()} support at x = {s.position:.2f} m" for s in beam.supports]
    for line in sup_lines + _load_description(loads):
        story.append(Paragraph(f"• {line}", ss["StepBody"]))

    # ── Reactions ──────────────────────────────────────────────────────
    story.append(Paragraph(f"2. Support reactions  (method: {reactions.method})", ss["H2"]))
    rxn_rows = [["Position (m)", "Vertical R (kN)", "Moment (kN·m)"]]
    for pos in sorted(reactions.reactions):
        r = reactions.reactions[pos]
        rxn_rows.append([
            f"{pos:.2f}",
            f"{r.get('Fy', 0):+.3f}",
            f"{r.get('M', 0):+.3f}" if "M" in r else "—",
        ])
    t = Table(rxn_rows, colWidths=[5*cm, 5*cm, 5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9.5),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ACCENT_LITE]),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    # ── Reaction steps ──────────────────────────────────────────────────
    story.append(Paragraph("3. Reaction calculation steps", ss["H2"]))
    for step in reactions.steps:
        story.append(Paragraph(f"Step {step['number']}: {step['title']}", ss["StepTitle"]))
        body = step["description"].replace("\n", "<br/>")
        story.append(Paragraph(body, ss["StepBody"]))

    # ── Diagram figure ─────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("4. Free body, shear force & bending moment diagrams", ss["H2"]))
    fig = create_combined_figure(beam, loads, reactions.reactions, result, figsize=(7.0, 7.0))
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    img_buf.seek(0)
    story.append(Image(img_buf, width=15*cm, height=15*cm))

    # ── SFD/BMD steps ───────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("5. SFD / BMD segment analysis", ss["H2"]))
    for step in result.steps:
        title = step.get("title", "")
        story.append(Paragraph(title, ss["StepTitle"]))
        body = step["description"].replace("\n", "<br/>")
        story.append(Paragraph(body, ss["StepBody"]))

    # ── Key results ─────────────────────────────────────────────────────
    story.append(Paragraph("6. Key results summary", ss["H2"]))
    key_rows = [
        ["Quantity", "Value", "Location"],
        ["Max +ve shear",  f"{result.V_max:+.3f} kN",   ""],
        ["Max -ve shear",  f"{result.V_min:+.3f} kN",   ""],
        ["Max +ve moment", f"{result.M_max:+.3f} kN·m", ""],
        ["Max -ve moment", f"{result.M_min:+.3f} kN·m", ""],
    ]
    # find locations
    import numpy as np
    key_rows[1][2] = f"x = {result.x[int(np.argmax(result.V))]:.3f} m"
    key_rows[2][2] = f"x = {result.x[int(np.argmin(result.V))]:.3f} m"
    key_rows[3][2] = f"x = {result.x[int(np.argmax(result.M))]:.3f} m"
    key_rows[4][2] = f"x = {result.x[int(np.argmin(result.M))]:.3f} m"
    t2 = Table(key_rows, colWidths=[5*cm, 5*cm, 5*cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9.5),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ACCENT_LITE]),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(
        "Generated by BeamEdu · Sign convention: sagging +ve, upward reaction +ve, "
        "clockwise moment +ve.",
        ss["Sub"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
