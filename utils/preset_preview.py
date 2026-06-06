"""
utils/preset_preview.py
=======================
Clean textbook-style SVG thumbnails for BeamEdu preset cards.

The full Plotly FBD remains available for detailed work. These thumbnails are
for quick visual problem recognition in the preset selector.
"""

from __future__ import annotations

import html

from engine import PointLoad, UDL, UVL, AppliedMoment


def preset_preview_svg(beam, loads) -> str:
    """Return a compact SVG preview of a beam problem."""
    w, h = 420, 142
    left, right = 34, 386
    yb = 82
    L = max(float(beam.length), 1e-9)

    def sx(x: float) -> float:
        return left + (float(x) / L) * (right - left)

    def esc(value) -> str:
        return html.escape(str(value), quote=True)

    def text(x, y, value, color="#25313d", size=11, weight=700, anchor="middle") -> str:
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-family="Inter, Segoe UI, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}">{esc(value)}</text>'
        )

    def arrow_head(x, y, color, direction="down") -> str:
        if direction == "down":
            pts = f"{x-5:.1f},{y-7:.1f} {x+5:.1f},{y-7:.1f} {x:.1f},{y:.1f}"
        elif direction == "up":
            pts = f"{x-5:.1f},{y+7:.1f} {x+5:.1f},{y+7:.1f} {x:.1f},{y:.1f}"
        elif direction == "right":
            pts = f"{x-7:.1f},{y-5:.1f} {x-7:.1f},{y+5:.1f} {x:.1f},{y:.1f}"
        else:
            pts = f"{x+7:.1f},{y-5:.1f} {x+7:.1f},{y+5:.1f} {x:.1f},{y:.1f}"
        return f'<polygon points="{pts}" fill="{color}" />'

    parts = [
        f'<rect x="0" y="0" width="{w}" height="{h}" rx="14" fill="#fffdfa"/>',
        f'<line x1="{left}" y1="{yb+3}" x2="{right}" y2="{yb+3}" stroke="rgba(37,49,61,0.12)" stroke-width="12" stroke-linecap="round"/>',
        f'<line x1="{left}" y1="{yb}" x2="{right}" y2="{yb}" stroke="#25313d" stroke-width="7" stroke-linecap="round"/>',
    ]

    def support_svg(x_pos, kind) -> str:
        x = sx(x_pos)
        k = str(kind.value if hasattr(kind, "value") else kind).lower()
        if "fixed" in k:
            side = -1 if x <= (left + right) / 2 else 1
            segs = [f'<line x1="{x:.1f}" y1="{yb-34}" x2="{x:.1f}" y2="{yb+34}" stroke="#1f5673" stroke-width="8" stroke-linecap="round"/>']
            for yy in range(yb - 28, yb + 31, 12):
                segs.append(f'<line x1="{x:.1f}" y1="{yy}" x2="{x + side*18:.1f}" y2="{yy-9}" stroke="#1f5673" stroke-width="1.4" opacity="0.75"/>')
            return "".join(segs)
        fill = "#ffffff" if "roller" in k else "rgba(31,86,115,0.18)"
        tri = 15
        segs = [
            f'<polygon points="{x-tri:.1f},{yb+31} {x:.1f},{yb+5} {x+tri:.1f},{yb+31}" fill="{fill}" stroke="#1f5673" stroke-width="2.2"/>'
        ]
        if "roller" in k:
            segs.append(f'<circle cx="{x-7:.1f}" cy="{yb+38}" r="4" fill="#fffdfa" stroke="#1f5673" stroke-width="1.6"/>')
            segs.append(f'<circle cx="{x+7:.1f}" cy="{yb+38}" r="4" fill="#fffdfa" stroke="#1f5673" stroke-width="1.6"/>')
        return "".join(segs)

    for support in beam.supports:
        parts.append(support_svg(support.position, support.support_type))

    def point_load_svg(ld) -> str:
        x = sx(ld.position)
        down = ld.magnitude > 0
        color = "#b3402f" if down else "#3f7a42"
        if down:
            y1, y2, label_y, direction = 18, yb - 11, 15, "down"
        else:
            y1, y2, label_y, direction = h - 15, yb + 13, h - 5, "up"
        return (
            f'<line x1="{x:.1f}" y1="{y1}" x2="{x:.1f}" y2="{y2}" stroke="{color}" stroke-width="2.8"/>'
            + arrow_head(x, y2, color, direction)
            + text(x, label_y, ld.label or "P", color=color, size=12, weight=800)
        )

    def udl_svg(ld) -> str:
        down = ld.intensity > 0
        color = "#b3402f" if down else "#3f7a42"
        x0, x1 = sx(ld.start), sx(ld.end)
        n = max(4, min(9, int((x1 - x0) / 36) + 1))
        xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
        if down:
            ytop, ytip, label_y, direction = 27, yb - 11, 20, "down"
            fy0, fy1 = ytop, yb - 5
        else:
            ytop, ytip, label_y, direction = h - 22, yb + 13, h - 6, "up"
            fy0, fy1 = yb + 5, ytop
        segs = [
            f'<rect x="{x0:.1f}" y="{min(fy0, fy1):.1f}" width="{x1-x0:.1f}" height="{abs(fy1-fy0):.1f}" fill="{color}" opacity="0.10" rx="4"/>',
            f'<line x1="{x0:.1f}" y1="{ytop}" x2="{x1:.1f}" y2="{ytop}" stroke="{color}" stroke-width="2.2"/>',
        ]
        for xi in xs:
            segs.append(f'<line x1="{xi:.1f}" y1="{ytop}" x2="{xi:.1f}" y2="{ytip}" stroke="{color}" stroke-width="1.9"/>')
            segs.append(arrow_head(xi, ytip, color, direction))
        segs.append(text((x0 + x1) / 2, label_y, ld.label or "w", color=color, size=12, weight=800))
        return "".join(segs)

    def uvl_svg(ld) -> str:
        down = (ld.intensity_start + ld.intensity_end) >= 0
        color = "#b3402f" if down else "#3f7a42"
        direction = "down" if down else "up"
        x0, x1 = sx(ld.start), sx(ld.end)
        max_w = max(abs(ld.intensity_start), abs(ld.intensity_end), 1e-9)
        n = 6
        xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
        tops = []
        segs = []
        for i, xi in enumerate(xs):
            ratio = i / (n - 1)
            val = ld.intensity_start + (ld.intensity_end - ld.intensity_start) * ratio
            height = 16 + 44 * abs(val) / max_w if abs(val) > 1e-9 else 0
            ytop = yb - height if down else yb + height
            ytip = yb - 11 if down else yb + 13
            tops.append((xi, ytop))
            if abs(val) > 1e-9:
                segs.append(f'<line x1="{xi:.1f}" y1="{ytop:.1f}" x2="{xi:.1f}" y2="{ytip}" stroke="{color}" stroke-width="1.7"/>')
                segs.append(arrow_head(xi, ytip, color, direction))
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in tops) + f" {x1:.1f},{yb:.1f} {x0:.1f},{yb:.1f}"
        label_y = min(y for _, y in tops) - 5 if down else max(y for _, y in tops) + 13
        return f'<polygon points="{poly}" fill="{color}" opacity="0.10" stroke="{color}" stroke-width="2"/>' + "".join(segs) + text((x0 + x1) / 2, label_y, ld.label or "w", color=color, size=12, weight=800)

    def moment_svg(ld) -> str:
        x = sx(ld.position)
        y = yb - 8
        r = 24
        # Draw a clean semicircular moment symbol.
        path = f'M {x-r:.1f},{y:.1f} C {x-r:.1f},{y-32:.1f} {x+r:.1f},{y-32:.1f} {x+r:.1f},{y:.1f}'
        head_x = x + r
        head_y = y
        return (
            f'<path d="{path}" fill="none" stroke="#7a4ea3" stroke-width="3"/>'
            + arrow_head(head_x, head_y, "#7a4ea3", "right")
            + text(x, y - 34, ld.label or "M", color="#7a4ea3", size=12, weight=800)
        )

    for load in loads:
        if isinstance(load, PointLoad):
            parts.append(point_load_svg(load))
        elif isinstance(load, UDL):
            parts.append(udl_svg(load))
        elif isinstance(load, UVL):
            parts.append(uvl_svg(load))
        elif isinstance(load, AppliedMoment):
            parts.append(moment_svg(load))

    parts.append(text(left, h - 7, "0", color="#7a8791", size=9, weight=600))
    parts.append(text(right, h - 7, f"L={L:g} m", color="#7a8791", size=9, weight=600))

    svg = f'<svg viewBox="0 0 {w} {h}" width="100%" height="150" role="img" aria-label="Beam problem preview">{"".join(parts)}</svg>'
    return f'<div style="border:1px solid rgba(228,222,210,.9); border-radius:14px; background:#fffdfa; margin:.55rem 0 .65rem; overflow:hidden;">{svg}</div>'
