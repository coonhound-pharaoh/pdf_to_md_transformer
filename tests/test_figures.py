"""Figure detection, caption binding and image extraction."""

import hashlib
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from pdf_to_md.engine import convert_file, convert_pdf_to_markdown  # noqa: E402
from pdf_to_md.figures import caption_label, looks_like_caption  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "figures.pdf")
SAMPLE = os.path.join(HERE, "fixtures", "sample.pdf")


@pytest.fixture(scope="module")
def pdf() -> str:
    if not os.path.exists(FIXTURE):
        from make_figure_fixture import build
        build(FIXTURE)
    return FIXTURE


@pytest.fixture(scope="module")
def markdown(pdf) -> str:
    return convert_pdf_to_markdown(pdf)


# --------------------------------------------------------------------------
# caption recognition
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Figure 1: Mean canopy height.",
    "Fig. 12 -- detail view",
    "FIGURE 3a. Close-up.",
    "Chart 2: Revenue.",
    "Plate IV",
])
def test_caption_forms_recognised(text):
    assert looks_like_caption(text)


@pytest.mark.parametrize("text", [
    "Figures were prepared in R.",   # prose, no number
    "The figure above shows...",
    "Table 1: Mowing heights.",      # tables are handled elsewhere
    "",
])
def test_non_captions_rejected(text):
    assert not looks_like_caption(text)


def test_caption_label_normalises_abbreviation():
    assert caption_label("Fig. 4 -- detail") == "Figure 4"
    assert caption_label("Chart 2: Revenue") == "Chart 2"
    assert caption_label("not a caption") is None


# --------------------------------------------------------------------------
# placement in the document
# --------------------------------------------------------------------------

def test_vector_chart_is_marked(markdown):
    assert "<!-- figure: page 1," in markdown


def test_raster_image_is_marked(markdown):
    assert "<!-- figure: page 2," in markdown


def test_caption_below_the_figure_is_bound_not_duplicated(markdown):
    assert markdown.count("Figure 1: Mean canopy height by week.") == 1
    assert "*Figure 1: Mean canopy height by week.*" in markdown


def test_caption_above_the_figure_is_bound(markdown):
    assert "*Figure 2: Sampling grid layout.*" in markdown


def test_figure_sits_in_reading_order(markdown):
    body = markdown.index("chart below summarises")
    fig = markdown.index("<!-- figure: page 1,")
    after = markdown.index("Treatment effects were consistent")
    assert body < fig < after


def test_surrounding_body_text_survives(markdown):
    assert "Plots were measured weekly" in markdown
    assert "Grid cells were sampled in a fixed order" in markdown


def test_short_decorative_rule_is_not_a_figure(markdown):
    assert markdown.count("<!-- figure:") == 2


def test_page_without_figures_is_unaffected():
    if not os.path.exists(SAMPLE):
        from make_fixture import build
        build(SAMPLE)
    assert "<!-- figure:" not in convert_pdf_to_markdown(SAMPLE)


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------

def test_extract_images_writes_and_links_assets(pdf, tmp_path):
    out = str(tmp_path / "figures.md")
    convert_file(pdf, out, extract_images=True)
    md = open(out, encoding="utf-8").read()

    assert "![Figure 1: Mean canopy height by week.](figures_assets/p1-fig1.png)" in md
    assert "<!-- figure:" not in md
    for name in ("p1-fig1.png", "p2-fig1.png"):
        asset = tmp_path / "figures_assets" / name
        assert asset.is_file() and asset.stat().st_size > 0


def test_extraction_is_deterministic(pdf, tmp_path):
    def run(sub):
        d = tmp_path / sub
        d.mkdir()
        convert_file(pdf, str(d / "figures.md"), extract_images=True)
        png = (d / "figures_assets" / "p2-fig1.png").read_bytes()
        return hashlib.sha256(png).hexdigest()

    assert run("a") == run("b")
