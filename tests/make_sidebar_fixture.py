"""Build the sidebar test fixture PDF (dev-only; uses reportlab).

Exercises all three callout styles and the traps that must NOT become
callouts:
  * page 1: a box ruled with four separate lines
  * page 1: an indented continuation paragraph (trap: no typography change)
  * page 2: a box drawn as a stroked, unfilled rectangle
  * page 2: an inset pull quote in a smaller italic face (typographic)
  * page 3: two ordinary columns (trap: the right column is not "inset")
"""

import os

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "sidebars.pdf")

W, H = LETTER


def _para(c, x, y, lines, font="Helvetica", size=11, leading=15):
    c.setFont(font, size)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def build(path: str = OUT) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=LETTER)

    # ------------------ page 1: line-drawn box + indent trap ------------
    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, H - 72, "Irrigation Practice")

    y = _para(c, 72, H - 112, [
        "Water deeply and infrequently to encourage deep rooting in",
        "established turf during the summer months.",
    ])

    # a box drawn as four separate lines
    bx0, bx1, btop, bbot = 72, 400, H - 175, H - 265
    c.setLineWidth(1)
    c.line(bx0, btop, bx1, btop)
    c.line(bx0, bbot, bx1, bbot)
    c.line(bx0, btop, bx0, bbot)
    c.line(bx1, btop, bx1, bbot)
    _para(c, 84, btop - 20, [
        "Note: soil probes give a far better reading of available",
        "moisture than surface appearance ever will.",
    ])

    # an indented continuation: same face, same size -> NOT a callout
    _para(c, 72, H - 300, [
        "Rooting depth responds slowly to a change in schedule, so",
    ])
    _para(c, 100, H - 315, [
        "expect several weeks before the effect is measurable in",
        "the field under normal conditions.",
    ])

    c.showPage()

    # ------------------ page 2: stroked rect + pull quote ---------------
    y = _para(c, 72, H - 72, [
        "Fertility programs should be built around a soil test taken",
        "at the same point in the season each year.",
    ])

    c.setLineWidth(1.2)
    c.rect(72, H - 260, 330, 80, fill=0, stroke=1)   # unfilled, stroked
    _para(c, 84, H - 200, [
        "Warning: never apply nitrogen to frozen ground, where it",
        "will run off before the plant can take any of it up.",
    ])

    _para(c, 72, H - 300, [
        "Split applications through the season give more even growth",
        "than a single heavy feeding in the spring.",
    ])

    # inset pull quote, smaller italic face, clear space above and below
    _para(c, 130, H - 370, [
        "A soil test is the cheapest input you will",
        "ever buy for the season.",
    ], font="Helvetica-Oblique", size=9, leading=13)

    _para(c, 72, H - 430, [
        "Records from previous seasons make the next test easier to",
        "read and act on without guesswork.",
    ])

    c.showPage()

    # ------------------ page 3: two plain columns (trap) ----------------
    left = [
        "Mowing frequency should follow the",
        "one-third rule through the whole of",
        "the growing season, so that no more",
        "than a third of the leaf is removed",
        "at any single cutting of the turf.",
    ]
    right = [
        "Sharp blades matter as much as the",
        "height setting on the machine does,",
        "because a torn leaf loses more water",
        "and gives disease an easier entry to",
        "the plant than a clean cut ever will.",
    ]
    _para(c, 72, H - 100, left)
    _para(c, 330, H - 100, right)

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    print(build())
