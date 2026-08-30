"""LaTeX reconstruction from glyph geometry (Tier B).

The unit tests build glyph boxes directly, which is how the layout
reaches the parser; the end-to-end tests run the real fixture PDF.
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from pdf_to_md.engine import convert_pdf_to_markdown  # noqa: E402
from pdf_to_md.mathparse import Bar, reconstruct  # noqa: E402
from pdf_to_md.mathsymbols import to_latex, to_unicode  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "latex.pdf")
SAMPLE = os.path.join(HERE, "fixtures", "sample.pdf")


@pytest.fixture(scope="module")
def markdown() -> str:
    if not os.path.exists(FIXTURE):
        from make_latex_fixture import build
        build(FIXTURE)
    return convert_pdf_to_markdown(FIXTURE)


def ch(text, x0, width=6.0, baseline=100.0, size=12.0, font="Times-Roman"):
    """One character box sitting on ``baseline``."""
    return {"text": text, "x0": x0, "x1": x0 + width,
            "top": baseline - size, "bottom": baseline,
            "size": size, "fontname": font}


# --------------------------------------------------------------------------
# glyph decoding
# --------------------------------------------------------------------------

def test_symbol_font_codes_decode_to_unicode():
    assert to_unicode("¶", "Symbol") == "∂"          # 0xB6
    assert to_unicode("(cid:229)", "Symbol") == "∑"  # 0xE5
    assert to_unicode("a", "Symbol") == "α"          # 0x61


def test_unicode_fonts_pass_through():
    assert to_unicode("∑", "STIXTwoMath-Regular") == "∑"
    assert to_unicode("x", "Times-Italic") == "x"


def test_unknown_symbol_code_is_refused():
    assert to_unicode("(cid:9999)", "Symbol") is None


def test_unmapped_glyph_in_a_text_font_is_refused():
    assert to_unicode("(cid:42)", "Times-Roman") is None


def test_pictorial_fonts_are_never_read_literally():
    # ZapfDingbats "n" is a filled square; reading it as the letter n and
    # dressing the result up as LaTeX would be a confident lie
    assert to_unicode("n", "ZapfDingbats") is None
    assert to_unicode("l", "Wingdings-Regular") is None


def test_latex_names_are_correct():
    assert to_latex("∂") == r"\partial"
    assert to_latex("≤") == r"\leq"
    assert to_latex("α") == r"\alpha"
    assert to_latex("%") == r"\%"       # escaped, not emitted raw
    assert to_latex("☃") is None   # a snowman is not maths


# --------------------------------------------------------------------------
# structure
# --------------------------------------------------------------------------

def test_plain_row():
    chars = [ch("a", 10), ch("+", 20), ch("b", 30)]
    assert reconstruct(chars, []) == "a + b"


def test_superscript():
    chars = [ch("x", 10), ch("2", 17, width=4, baseline=94.0, size=8.0)]
    assert reconstruct(chars, []) == "x^{2}"


def test_subscript():
    chars = [ch("x", 10), ch("i", 17, width=4, baseline=103.0, size=8.0)]
    assert reconstruct(chars, []) == "x_{i}"


def test_multi_character_script_stays_one_group():
    chars = [ch("x", 10),
             ch("n", 17, width=4, baseline=94.0, size=8.0),
             ch("+", 21, width=4, baseline=94.0, size=8.0),
             ch("1", 25, width=4, baseline=94.0, size=8.0)]
    assert reconstruct(chars, []) == "x^{n + 1}"


def test_fraction_from_a_rule():
    chars = [ch("a", 10, baseline=90.0), ch("2", 10, baseline=110.0)]
    assert reconstruct(chars, [Bar(8, 20, 95.0)]) == r"\frac{a}{2}"


def test_fraction_inside_a_row():
    chars = [ch("m", 0), ch("=", 8),
             ch("a", 20, baseline=90.0), ch("2", 20, baseline=110.0)]
    assert reconstruct(chars, [Bar(18, 28, 95.0)]) == r"m = \frac{a}{2}"


def test_digits_group_into_one_number():
    chars = [ch("x", 0), ch("=", 8), ch("1", 20), ch("0", 26), ch("5", 32)]
    assert reconstruct(chars, []) == "x = 105"


def test_function_name_becomes_an_operator():
    chars = [ch("s", 0), ch("i", 6), ch("n", 12), ch("x", 22)]
    assert reconstruct(chars, []) == r"\sin x"


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------

def test_unmappable_glyph_refuses_the_whole_equation():
    chars = [ch("x", 0), ch("=", 8), ch("(cid:77)", 20)]
    assert reconstruct(chars, []) is None


def test_unexplained_rule_refuses():
    # a rule with nothing above it is not a fraction and not an overline;
    # the layout is not understood, so nothing is claimed
    chars = [ch("a", 10), ch("b", 20)]
    assert reconstruct(chars, [Bar(8, 30, 80.0)]) is None


def test_radical_without_an_overline_refuses():
    chars = [ch("√", 0, font="Symbol-fake"), ch("n", 10)]
    chars[0]["text"] = "√"
    chars[0]["fontname"] = "STIXMath"
    assert reconstruct(chars, []) is None


def test_empty_input_refuses():
    assert reconstruct([], []) is None


# --------------------------------------------------------------------------
# end to end
# --------------------------------------------------------------------------

def test_derivative_equation_reconstructed(markdown):
    assert r"\partial f / \partial t = D \nabla^{2} f" in markdown


def test_fraction_equation_reconstructed(markdown):
    assert r"m = \frac{a + b}{2}" in markdown


def test_sum_with_limits_scripts_and_radical_reconstructed(markdown):
    assert r"\sum_{i = 1}^{n} x_{i}^{2} \leq \sqrt{n}" in markdown


def test_reconstruction_is_labelled_as_reconstruction(markdown):
    assert "reconstructed from glyph geometry; check against the source" \
        in markdown
    assert markdown.count("$$") == 6      # three equations, opened and closed


def test_equation_number_is_bound_and_kept_out_of_the_maths(markdown):
    assert "<!-- equation 1: reconstructed" in markdown
    assert "(1)" not in markdown          # not left as a stray paragraph


def test_untrustworthy_equation_falls_back_to_verbatim(markdown):
    # the last case contains a glyph that cannot be decoded, so no LaTeX
    # is claimed for it at all
    assert "```equation" in markdown


def test_surrounding_prose_is_untouched(markdown):
    for sentence in ("The diffusion equation is written",
                     "and the mean of the sample is",
                     "Convergence requires"):
        assert sentence in markdown


def test_document_without_maths_is_unaffected():
    if not os.path.exists(SAMPLE):
        from make_fixture import build
        build(SAMPLE)
    md = convert_pdf_to_markdown(SAMPLE)
    assert "$$" not in md and "```equation" not in md
