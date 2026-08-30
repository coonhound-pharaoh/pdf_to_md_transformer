"""Build the equation test fixture PDF (dev-only; uses reportlab).

Exercises equation quarantining:
  * a display equation set in the Symbol font (font signal), numbered (1)
  * a display equation written with Unicode math glyphs (glyph signal)
  * a prose sentence that merely mentions a Greek letter (must stay prose)
  * a short prose line and a heading (must not be mistaken for maths)
"""

import os

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "equations.pdf")

W, H = LETTER


def build(path: str = OUT) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=LETTER)

    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, H - 72, "Diffusion Model")

    c.setFont("Helvetica", 11)
    c.drawString(72, H - 112,
                 "The concentration profile follows from the flux balance")
    c.drawString(72, H - 127,
                 "derived in the preceding section, which gives:")

    # display equation 1: Symbol font (a recognised math font), numbered
    c.setFont("Symbol", 12)
    c.drawString(180, H - 165, "¶f/¶t = D Ñ" + chr(50))
    c.setFont("Helvetica", 11)
    c.drawString(500, H - 165, "(1)")

    c.drawString(72, H - 205,
                 "Here D is the diffusion coefficient. The parameter alpha")
    c.drawString(72, H - 220,
                 "was estimated from the fitted curve in every block.")

    # display equation 2: unicode math glyphs in an ordinary font
    c.setFont("Helvetica", 12)
    c.drawString(180, H - 258, "∑ᵢ xᵢ² ≤ √(n) · ∫₀¹ f(t) ∂t")

    c.setFont("Helvetica", 11)
    c.drawString(72, H - 298,
                 "Convergence was reached after twelve iterations.")

    # prose mentioning maths: must NOT be quarantined
    c.drawString(72, H - 318,
                 "The α value exceeded the threshold in every treated plot,")
    c.drawString(72, H - 333,
                 "so the null hypothesis was rejected at the stated level.")

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    print(build())
