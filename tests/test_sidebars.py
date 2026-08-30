"""Callout detection: filled boxes, ruled boxes and unboxed pull quotes."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from pdf_to_md.engine import convert_pdf_to_markdown  # noqa: E402
from pdf_to_md.geometry import Line  # noqa: E402
from pdf_to_md.sidebars import detect_typographic_blocks  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "sidebars.pdf")
SAMPLE = os.path.join(HERE, "fixtures", "sample.pdf")


@pytest.fixture(scope="module")
def markdown() -> str:
    if not os.path.exists(FIXTURE):
        from make_sidebar_fixture import build
        build(FIXTURE)
    return convert_pdf_to_markdown(FIXTURE)


def _line(text, x0=72.0, x1=400.0, top=100.0, size=11.0, font="Body"):
    return Line(text=text, x0=x0, x1=x1, top=top, bottom=top + 11.0,
                size=size, nchars=len(text), font=font)


def _body_lines(n, start_top=100.0, step=15.0):
    return [_line(f"ordinary body line number {i}", top=start_top + i * step)
            for i in range(n)]


# --------------------------------------------------------------------------
# end to end: the three styles
# --------------------------------------------------------------------------

def test_box_drawn_with_four_lines_becomes_a_blockquote(markdown):
    assert "> Note: soil probes give a far better reading" in markdown


def test_stroked_unfilled_rectangle_becomes_a_blockquote(markdown):
    assert "> Warning: never apply nitrogen to frozen ground" in markdown


def test_unboxed_pull_quote_becomes_a_blockquote(markdown):
    assert "> A soil test is the cheapest input you will ever buy" in markdown


def test_filled_box_still_works():
    if not os.path.exists(SAMPLE):
        from make_fixture import build
        build(SAMPLE)
    md = convert_pdf_to_markdown(SAMPLE)
    assert "> " in md  # the shaded sidebar in the original fixture


# --------------------------------------------------------------------------
# end to end: the traps
# --------------------------------------------------------------------------

def test_indented_continuation_is_not_a_callout(markdown):
    assert "> Rooting depth" not in markdown
    assert "> expect several weeks" not in markdown
    # and it stays joined to the paragraph it belongs to
    assert "expect several weeks before the effect is measurable" in markdown


def test_second_column_is_not_a_callout(markdown):
    assert "> Sharp blades matter" not in markdown
    assert "Sharp blades matter as much as the height setting" in markdown


def test_callout_text_is_not_duplicated_in_the_body(markdown):
    assert markdown.count("soil probes give a far better reading") == 1
    assert markdown.count("cheapest input you will") == 1


# --------------------------------------------------------------------------
# the typographic gate, in isolation
# --------------------------------------------------------------------------

def test_inset_block_in_a_smaller_face_is_detected():
    lines = _body_lines(3)
    quote = [_line("a quoted claim", x0=130.0, x1=330.0, top=200.0, size=9.0),
             _line("that runs on", x0=130.0, x1=320.0, top=213.0, size=9.0)]
    lines += quote + _body_lines(3, start_top=280.0)
    assert detect_typographic_blocks(lines, 11.0) == [(3, 5)]


def test_inset_block_in_the_body_face_is_left_alone():
    lines = _body_lines(3)
    lines += [_line("indented but ordinary", x0=130.0, x1=330.0, top=200.0),
              _line("still ordinary", x0=130.0, x1=320.0, top=213.0)]
    lines += _body_lines(3, start_top=280.0)
    assert detect_typographic_blocks(lines, 11.0) == []


def test_block_without_space_around_it_is_left_alone():
    lines = _body_lines(3)
    lines += [_line("tight above", x0=130.0, x1=330.0, top=145.0, size=9.0),
              _line("tight below", x0=130.0, x1=320.0, top=158.0, size=9.0)]
    lines += _body_lines(3, start_top=171.0)
    assert detect_typographic_blocks(lines, 11.0) == []


def test_single_inset_line_is_not_a_block():
    lines = _body_lines(3)
    lines += [_line("one line only", x0=130.0, x1=330.0, top=200.0, size=9.0)]
    lines += _body_lines(3, start_top=280.0)
    assert detect_typographic_blocks(lines, 11.0) == []


def test_a_run_reaching_the_right_edge_is_not_inset():
    lines = _body_lines(3)
    lines += [_line("wide", x0=130.0, x1=400.0, top=200.0, size=9.0),
              _line("also wide", x0=130.0, x1=400.0, top=213.0, size=9.0)]
    lines += _body_lines(3, start_top=280.0)
    assert detect_typographic_blocks(lines, 11.0) == []


def test_block_at_the_very_end_has_no_separation_below():
    lines = _body_lines(3)
    lines += [_line("trailing", x0=130.0, x1=330.0, top=200.0, size=9.0),
              _line("block", x0=130.0, x1=320.0, top=213.0, size=9.0)]
    assert detect_typographic_blocks(lines, 11.0) == []


def test_face_change_alone_is_enough():
    lines = _body_lines(3)
    lines += [_line("quoted", x0=130.0, x1=330.0, top=200.0, font="Italic"),
              _line("claim", x0=130.0, x1=320.0, top=213.0, font="Italic")]
    lines += _body_lines(3, start_top=280.0)
    assert detect_typographic_blocks(lines, 11.0) == [(3, 5)]
