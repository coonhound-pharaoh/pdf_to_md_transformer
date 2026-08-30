"""Equation detection and quarantining (Tier A)."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from pdf_to_md.engine import convert_pdf_to_markdown  # noqa: E402
from pdf_to_md.equations import (  # noqa: E402
    bare_tag,
    equation_tag,
    is_equation_line,
    is_math_font,
    math_evidence,
    render_equation,
)

FIXTURE = os.path.join(HERE, "fixtures", "equations.pdf")
SAMPLE = os.path.join(HERE, "fixtures", "sample.pdf")


@pytest.fixture(scope="module")
def markdown() -> str:
    if not os.path.exists(FIXTURE):
        from make_equation_fixture import build
        build(FIXTURE)
    return convert_pdf_to_markdown(FIXTURE)


def _w(text, font=None):
    w = {"text": text, "x0": 0.0, "x1": 10.0, "top": 0.0, "bottom": 10.0}
    if font:
        w["fontname"] = font
    return w


# --------------------------------------------------------------------------
# the two signals
# --------------------------------------------------------------------------

@pytest.mark.parametrize("font", [
    "ABCDEF+CMMI10", "GHIJKL+CMSY7", "CMEX10", "STIXTwoMath-Regular",
    "XITSMath-Regular", "Symbol", "MSBM10", "CambriaMath",
])
def test_math_fonts_recognised(font):
    assert is_math_font(font)


@pytest.mark.parametrize("font", [
    "ABCDEF+Times-Roman", "Helvetica-Bold", "ArialMT", "NimbusRomNo9L-Regu",
    None, "",
])
def test_text_fonts_not_treated_as_math(font):
    assert not is_math_font(font)


def test_glyph_signal_works_without_font_information():
    # the OCR path has no fontname; unicode alone must carry the decision
    words = [_w("∑ᵢ"), _w("xᵢ²"), _w("≤"), _w("√n")]
    assert math_evidence(words) >= 0.30


def test_prose_scores_near_zero():
    words = [_w(t) for t in "the null hypothesis was rejected".split()]
    assert math_evidence(words) == 0.0


def test_font_signal_marks_every_glyph_of_the_word():
    assert math_evidence([_w("abc", "ABCDEF+CMMI10")]) == 1.0


# --------------------------------------------------------------------------
# the decision
# --------------------------------------------------------------------------

def test_display_equation_is_quarantined():
    assert is_equation_line("∂f/∂t = D ∇²f", 0.55)


def test_sentence_mentioning_greek_stays_prose():
    text = "The α value exceeded the threshold in every treated plot"
    assert not is_equation_line(text, 0.02)


def test_math_heavy_line_with_too_much_prose_stays_prose():
    # high evidence alone must not tear a sentence out of a paragraph
    text = "where sigma denotes the standard deviation of the sample mean"
    assert not is_equation_line(text, 0.90)


def test_very_short_fragment_is_not_judged():
    assert not is_equation_line("x²", 1.0)


# --------------------------------------------------------------------------
# equation numbers
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("∂f/∂t = 0 (1)", "1"),
    ("x = y (3.1)", "3.1"),
    ("z = 1 [12]", "12"),
    ("no number here", None),
])
def test_trailing_tag_extracted(text, expected):
    assert equation_tag(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("(1)", "1"), ("[A.2]", "A.2"), ("(4b)", "4b"),
    ("(see below)", None), ("x = (1)", None),
])
def test_bare_tag_recognised(text, expected):
    assert bare_tag(text) == expected


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def test_rendered_block_is_labelled_and_not_claimed_as_latex():
    out = render_equation(["a = b"], "2")
    assert out.startswith("<!-- equation 2:")
    assert "not a faithful transcription" in out
    assert "```equation" in out      # NOT ```math: renderers typeset that
    assert "$$" not in out


def test_rendered_block_keeps_multi_line_equations_together():
    out = render_equation(["a = b +", "c + d"], None)
    assert "a = b +\nc + d" in out


# --------------------------------------------------------------------------
# end to end
# --------------------------------------------------------------------------

def test_both_equations_are_quarantined(markdown):
    assert markdown.count("```equation") == 2


def test_equation_number_is_bound_not_left_as_a_paragraph(markdown):
    assert "<!-- equation 1:" in markdown
    assert "\n(1)\n" not in markdown


def test_surrounding_prose_is_unbroken(markdown):
    assert "The concentration profile follows from the flux balance derived" \
        in markdown
    assert "Convergence was reached after twelve iterations." in markdown


def test_prose_with_a_greek_letter_is_not_quarantined(markdown):
    body = markdown.split("```")[-1]
    assert "null hypothesis was rejected" in body


def test_equations_sit_in_reading_order(markdown):
    intro = markdown.index("which gives:")
    eq = markdown.index("```equation")
    after = markdown.index("Here D is the diffusion coefficient")
    assert intro < eq < after


def test_document_without_maths_is_unaffected():
    if not os.path.exists(SAMPLE):
        from make_fixture import build
        build(SAMPLE)
    assert "```equation" not in convert_pdf_to_markdown(SAMPLE)
