import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from pdf_to_md.engine import convert_pdf_to_markdown  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "sample.pdf")


@pytest.fixture(scope="module")
def markdown() -> str:
    if not os.path.exists(FIXTURE):
        from make_fixture import build
        build(FIXTURE)
    return convert_pdf_to_markdown(FIXTURE)


def test_title_becomes_h1(markdown):
    assert "# Turf Management Field Guide" in markdown


def test_section_heading_is_lower_level(markdown):
    assert "## Mowing Heights" in markdown


def test_body_paragraph_joined(markdown):
    assert "Cool-season grasses perform best when mowed at the correct height" in markdown
    # wrapped lines were joined into one paragraph
    assert "correct height for the species" in markdown.replace("\n", " ")


def test_table_rendered_inline_as_gfm(markdown):
    assert "| Species | Height (in) | Season |" in markdown
    assert "| Kentucky bluegrass | 2.5-3.5 | Cool |" in markdown
    # table cells must not leak into surrounding paragraphs
    assert markdown.count("Kentucky bluegrass") == 1


def test_sidebar_rendered_as_blockquote(markdown):
    assert "> " in markdown
    quoted = [l for l in markdown.splitlines() if l.startswith(">")]
    joined = " ".join(quoted)
    assert "Pro Tip" in joined
    assert "one third of the leaf blade" in joined


def test_bullets_become_list_items(markdown):
    assert "- Sharpen blades every 20 hours of use" in markdown
    assert "- Alternate mowing direction weekly" in markdown


def test_reading_order_inline(markdown):
    """Heading -> table -> sidebar -> list, in document order."""
    pos = [
        markdown.index("# Turf Management Field Guide"),
        markdown.index("## Mowing Heights"),
        markdown.index("| Species |"),
        markdown.index("Pro Tip"),
        markdown.index("- Sharpen blades"),
    ]
    assert pos == sorted(pos)


def test_no_metadata_leaks(markdown):
    for secret in ("SECRET-METADATA-TITLE",
                   "SECRET-METADATA-AUTHOR",
                   "SECRET-METADATA-SUBJECT",
                   "ReportLab", "reportlab"):
        assert secret not in markdown


def test_deterministic(markdown):
    assert convert_pdf_to_markdown(FIXTURE) == markdown
