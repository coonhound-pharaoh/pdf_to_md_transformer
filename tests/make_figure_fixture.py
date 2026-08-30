"""Build the figure test fixture PDF (dev-only; uses reportlab).

Exercises figure handling:
  * page 1: a vector line chart with a caption BELOW it
  * page 1: body text that must not be swallowed by figure detection
  * page 2: an embedded raster image with a caption ABOVE it
  * page 2: a small decorative rule that must NOT count as a figure
"""

import os

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "figures.pdf")

W, H = LETTER


def _raster():
    """A deterministic 64x48 checkerboard as an in-memory PNG."""
    from PIL import Image
    img = Image.new("RGB", (64, 48), "white")
    px = img.load()
    for x in range(64):
        for y in range(48):
            if (x // 8 + y // 8) % 2 == 0:
                px[x, y] = (30, 90, 160)
    return ImageReader(img)


def build(path: str = OUT) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=LETTER)

    # ---------------- page 1: vector chart, caption below ----------------
    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, H - 72, "Growth Trials")

    c.setFont("Helvetica", 11)
    for i, line in enumerate((
        "Plots were measured weekly through the growing season. The",
        "chart below summarises mean canopy height by treatment.",
    )):
        c.drawString(72, H - 112 - i * 15, line)

    # vector "chart": axes plus a polyline plus tick marks -> many curves
    c.setStrokeColor(black)
    c.setLineWidth(1)
    x0, y0, cw, ch = 96, H - 380, 300, 190
    c.line(x0, y0, x0, y0 + ch)             # y axis
    c.line(x0, y0, x0 + cw, y0)             # x axis
    for k in range(1, 6):                   # tick marks
        c.line(x0 + k * 50, y0, x0 + k * 50, y0 + 6)
        c.line(x0, y0 + k * 30, x0 + 6, y0 + k * 30)
    c.setStrokeColor(HexColor("#1E5AA0"))
    c.setLineWidth(2)
    pts = [(x0 + 10, y0 + 20), (x0 + 70, y0 + 65), (x0 + 130, y0 + 60),
           (x0 + 190, y0 + 120), (x0 + 250, y0 + 155)]
    for a, b in zip(pts, pts[1:]):
        c.line(a[0], a[1], b[0], b[1])
    c.setStrokeColor(black)

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(96, y0 - 18, "Figure 1: Mean canopy height by week.")

    c.setFont("Helvetica", 11)
    c.drawString(72, y0 - 56,
                 "Treatment effects were consistent across all blocks.")

    c.showPage()

    # ---------------- page 2: raster image, caption above ----------------
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(96, H - 120, "Figure 2: Sampling grid layout.")
    c.drawImage(_raster(), 96, H - 300, width=256, height=168)

    c.setFont("Helvetica", 11)
    c.drawString(72, H - 340,
                 "Grid cells were sampled in a fixed order each visit.")

    # a short decorative rule: too small to be a figure
    c.setLineWidth(0.5)
    c.line(72, H - 370, 160, H - 370)

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    print(build())
