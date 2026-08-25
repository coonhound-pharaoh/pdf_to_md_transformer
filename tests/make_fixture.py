"""Build the deterministic test fixture PDF (dev-only; uses reportlab).

The fixture exercises everything the engine claims to handle:
  * a large title and a smaller section heading
  * body paragraphs
  * a shaded sidebar box with its own text
  * a ruled table
  * a bulleted list
  * document metadata (which must NOT appear in the output)
"""

import os

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "sample.pdf")

W, H = LETTER  # 612 x 792 pt


def build(path: str = OUT) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=LETTER)

    # metadata that must never leak into the markdown output
    c.setTitle("SECRET-METADATA-TITLE")
    c.setAuthor("SECRET-METADATA-AUTHOR")
    c.setSubject("SECRET-METADATA-SUBJECT")

    y = H - 72

    # H1 title (20pt vs 11pt body)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, y, "Turf Management Field Guide")
    y -= 40

    # body paragraph
    c.setFont("Helvetica", 11)
    for line in (
        "Cool-season grasses perform best when mowed at the correct height",
        "for the species. Mowing too low stresses the plant and invites",
        "weed encroachment during the summer months.",
    ):
        c.drawString(72, y, line)
        y -= 15

    y -= 10

    # section heading (15pt)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(72, y, "Mowing Heights")
    y -= 24

    # ruled table: grid lines + cell text (lattice-detectable)
    rows = [
        ["Species", "Height (in)", "Season"],
        ["Kentucky bluegrass", "2.5-3.5", "Cool"],
        ["Tall fescue", "3.0-4.0", "Cool"],
        ["Bermudagrass", "1.0-2.0", "Warm"],
    ]
    col_x = [72, 240, 340, 440]
    row_h = 20
    table_top = y
    c.setFont("Helvetica", 10)
    for ri, row in enumerate(rows):
        cy = table_top - ri * row_h
        for ci, cell in enumerate(row):
            c.drawString(col_x[ci] + 4, cy - 14, cell)
    # grid
    c.setStrokeColor(black)
    c.setLineWidth(0.75)
    n = len(rows)
    for ri in range(n + 1):
        cy = table_top - ri * row_h
        c.line(col_x[0], cy, col_x[-1], cy)
    for x in col_x:
        c.line(x, table_top, x, table_top - n * row_h)
    y = table_top - n * row_h - 30

    # sidebar: filled rectangle with its own text
    sb_x0, sb_y1 = 72, y
    sb_w, sb_h = 300, 70
    c.setFillColor(HexColor("#DDE8F0"))
    c.rect(sb_x0, sb_y1 - sb_h, sb_w, sb_h, stroke=0, fill=1)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(sb_x0 + 10, sb_y1 - 20, "Pro Tip")
    c.setFont("Helvetica", 10)
    c.drawString(sb_x0 + 10, sb_y1 - 36, "Never remove more than one third of the")
    c.drawString(sb_x0 + 10, sb_y1 - 50, "leaf blade in a single mowing pass.")
    y = sb_y1 - sb_h - 30

    # bulleted list
    c.setFont("Helvetica", 11)
    for item in (
        "• Sharpen blades every 20 hours of use",
        "• Alternate mowing direction weekly",
        "• Mow when the turf is dry",
    ):
        c.drawString(72, y, item)
        y -= 16

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    print(build())
