"""Build a deterministic two-column 'scientific paper' fixture PDF.

Mimics modern agronomy-journal typesetting: full-width title, two body
columns, and a borderless booktabs-style table (horizontal rules only)
inside the left column.  Dev-only; uses reportlab.
"""

import os

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "science.pdf")

W, H = LETTER  # 612 x 792 pt

L_X0, L_X1 = 54, 292    # left column
R_X0, R_X1 = 320, 558   # right column


def _col_text(c, x, y, lines, size=9, leading=12, font="Helvetica"):
    c.setFont(font, size)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def build(path: str = OUT) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=LETTER)
    c.setTitle("SECRET-METADATA-TITLE")
    c.setAuthor("SECRET-METADATA-AUTHOR")

    # full-width title (18pt) and byline
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(W / 2, H - 70, "Nitrogen Rate Effects on Creeping Bentgrass")
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, H - 92, "A. Researcher and B. Scientist")

    top = H - 130

    # ---- left column -----------------------------------------------------
    y = top
    c.setFont("Helvetica-Bold", 11)
    c.drawString(L_X0, y, "Abstract")
    y -= 16
    y = _col_text(c, L_X0, y, [
        "Nitrogen fertilization is the primary cultural",
        "practice governing turfgrass color, shoot density,",
        "and clipping production. This study evaluated four",
        "nitrogen rates applied to a creeping bentgrass",
        "putting green over two growing seasons.",
    ])
    y -= 10

    c.setFont("Helvetica-Bold", 11)
    c.drawString(L_X0, y, "Results")
    y -= 16
    y = _col_text(c, L_X0, y, [
        "Clipping yield increased with nitrogen rate up to",
        "98 kg per hectare and plateaued thereafter, as",
        "shown in Table 1.",
    ])
    y -= 14

    # ---- booktabs table (horizontal rules only) --------------------------
    t_x0, t_x1 = L_X0 + 2, L_X1 - 2
    col_x = [t_x0 + 4, t_x0 + 100, t_x0 + 170]  # 3 columns
    row_h = 14

    toprule = y
    c.setLineWidth(1.0)
    c.line(t_x0, toprule, t_x1, toprule)

    c.setFont("Helvetica-Bold", 8)
    hy = toprule - 11
    c.drawString(col_x[0], hy, "N rate")
    c.drawString(col_x[1], hy, "Yield")
    c.drawString(col_x[2], hy, "Color")
    midrule = hy - 5
    c.setLineWidth(0.6)
    c.line(t_x0, midrule, t_x1, midrule)

    data = [
        ["0", "12.4", "5.2"],
        ["49", "18.9", "6.4"],
        ["98", "22.3", "7.5"],
        ["147", "23.1", "7.8"],
    ]
    c.setFont("Helvetica", 8)
    ry = midrule - 11
    for row in data:
        for ci, cell in enumerate(row):
            c.drawString(col_x[ci], ry, cell)
        ry -= row_h
    bottomrule = ry + row_h - 5
    c.setLineWidth(1.0)
    c.line(t_x0, bottomrule, t_x1, bottomrule)
    y = bottomrule - 16

    _col_text(c, L_X0, y, [
        "Color ratings followed the same pattern, with",
        "acceptable color achieved at 98 kg per hectare.",
    ])

    # ---- right column ----------------------------------------------------
    y = top
    c.setFont("Helvetica-Bold", 11)
    c.drawString(R_X0, y, "Materials and Methods")
    y -= 16
    y = _col_text(c, R_X0, y, [
        "The experiment was conducted on a sand-based",
        "putting green established with creeping bentgrass.",
        "Nitrogen was applied as urea in fourteen equal",
        "applications per season. Plots were mowed six",
        "days per week at a bench setting of 3.2 mm and",
        "clippings were collected, dried, and weighed.",
        "Turf color was rated visually on a one-to-nine",
        "scale where six represents acceptable color.",
    ])
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(R_X0, y, "Discussion")
    y -= 16
    _col_text(c, R_X0, y, [
        "Responses to nitrogen were consistent across",
        "seasons. The plateau above 98 kg per hectare",
        "suggests little agronomic benefit from higher",
        "annual nitrogen totals in this environment.",
    ])

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    print(build())
