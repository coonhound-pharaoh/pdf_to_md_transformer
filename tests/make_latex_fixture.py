"""Build the LaTeX-reconstruction fixture PDF (dev-only; uses reportlab).

Real maths in a PDF is positioned glyphs, not Unicode: scripts are drawn
smaller and offset, fractions are a rule with material above and below,
radicals are a root glyph plus an overline.  This fixture reproduces that
layout so the geometric parser is exercised the way a journal PDF would
exercise it.

Symbol-font characters are drawn by their Adobe Symbol code, which is how
they appear in the wild (the extractor gets the code back, not Unicode).
"""

import os

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "latex.pdf")

W, H = LETTER

# Written as Unicode: the PDF producer converts each to its Symbol-font
# code, which is exactly what the extractor has to decode on the way back.
PARTIAL = "\u2202"
NABLA = "\u2207"
SUM = "\u2211"
RADICAL = "\u221a"
LEQ = "\u2264"
ALPHA = "\u03b1"
UNMAPPED = "\u2265"     # decodes to a non-Symbol code: must force a refusal


def _sym(c, x, y, s, size=12):
    c.setFont("Symbol", size)
    c.drawString(x, y, s)
    return x + c.stringWidth(s, "Symbol", size)


def _txt(c, x, y, s, size=12, font="Times-Italic"):
    c.setFont(font, size)
    c.drawString(x, y, s)
    return x + c.stringWidth(s, font, size)


def build(path: str = OUT) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=LETTER)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, H - 64, "Reconstruction Cases")

    c.setFont("Times-Roman", 11)
    c.drawString(72, H - 96, "The diffusion equation is written")

    # ---- 1: partial derivatives, a superscript, an equation number ----
    y = H - 130
    x = _sym(c, 180, y, PARTIAL)
    x = _txt(c, x, y, "f")
    x = _txt(c, x + 2, y, "/", font="Times-Roman")
    x = _sym(c, x + 2, y, PARTIAL)
    x = _txt(c, x, y, "t")
    x = _txt(c, x + 6, y, "=", font="Times-Roman")
    x = _txt(c, x + 6, y, "D")
    x = _sym(c, x + 4, y, NABLA)
    sup_x = x
    x = _txt(c, x, y, "f")
    c.setFont("Times-Roman", 8)
    c.drawString(sup_x, y + 6, "2")          # superscript on nabla
    c.setFont("Times-Roman", 11)
    c.drawString(500, y, "(1)")

    c.setFont("Times-Roman", 11)
    c.drawString(72, H - 170, "and the mean of the sample is")

    # ---- 2: a fraction with a real rule, inside a row ----
    y = H - 215
    _txt(c, 180, y, "m", size=12)
    _txt(c, 194, y, "=", size=12, font="Times-Roman")
    # numerator "a + b" above the rule, denominator "2" below
    c.setFont("Times-Italic", 12)
    c.drawString(214, y + 9, "a")
    c.setFont("Times-Roman", 12)
    c.drawString(223, y + 9, "+")
    c.setFont("Times-Italic", 12)
    c.drawString(234, y + 9, "b")
    c.setLineWidth(0.7)
    c.line(212, y + 5, 244, y + 5)
    c.setFont("Times-Roman", 12)
    c.drawString(224, y - 8, "2")

    c.setFont("Times-Roman", 11)
    c.drawString(72, H - 255, "Convergence requires")

    # ---- 3: sum with limits, subscript+superscript, radical, relation ----
    y = H - 300
    c.setFont("Symbol", 16)
    c.drawString(180, y, SUM)
    sum_w = c.stringWidth(SUM, "Symbol", 16)
    c.setFont("Times-Roman", 8)
    c.drawString(181, y + 18, "n")                 # upper limit
    c.drawString(179, y - 9, "i=1")                # lower limit

    x = 180 + sum_w + 4
    x2 = _txt(c, x, y, "x", size=12)
    c.setFont("Times-Roman", 8)
    c.drawString(x2, y - 3, "i")                   # subscript
    c.drawString(x2 + 4, y + 6, "2")               # superscript
    x = x2 + 12

    x = _sym(c, x + 6, y, LEQ)
    # radical with an overline covering "n"
    rx = x + 6
    c.setFont("Symbol", 14)
    c.drawString(rx, y, RADICAL)
    rw = c.stringWidth(RADICAL, "Symbol", 14)
    c.setFont("Times-Italic", 12)
    c.drawString(rx + rw + 1, y, "n")
    c.setLineWidth(0.7)
    c.line(rx + rw, y + 11, rx + rw + 10, y + 11)  # overline

    c.setFont("Times-Roman", 11)
    c.drawString(72, H - 340, "for the significance level")

    # ---- 4: an equation the parser must refuse (unmapped glyph) ----
    y = H - 380
    c.setFont("Symbol", 12)
    c.drawString(180, y, ALPHA + " " + UNMAPPED + " " + PARTIAL)
    c.setFont("Times-Roman", 12)
    c.drawString(202, y, "0.05")

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    print(build())
