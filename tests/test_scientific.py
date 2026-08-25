"""Tests for scientific-paper features: borderless (booktabs) tables in
born-digital PDFs, and the OCR path for scanned papers."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

from pdf_to_md.engine import convert_pdf_to_markdown  # noqa: E402
from pdf_to_md.ocr import ocr_available  # noqa: E402

FIX = os.path.join(HERE, "fixtures")

REQUIRE_OCR = os.environ.get("PDF2MD_REQUIRE_OCR") == "1"
needs_ocr = pytest.mark.skipif(
    not ocr_available() and not REQUIRE_OCR,
    reason="tesseract not installed (set PDF2MD_REQUIRE_OCR=1 to force)",
)


def _fixture(name: str, builder) -> str:
    path = os.path.join(FIX, name)
    if not os.path.exists(path):
        builder()
    return path


@pytest.fixture(scope="module")
def science_md() -> str:
    from make_science_fixture import build
    return convert_pdf_to_markdown(_fixture("science.pdf", build))


@pytest.fixture(scope="module")
def scanned_science_md() -> str:
    from make_scanned_fixture import build_all
    return convert_pdf_to_markdown(_fixture("scanned_science.pdf", build_all))


@pytest.fixture(scope="module")
def scanned_sample_md() -> str:
    from make_scanned_fixture import build_all
    return convert_pdf_to_markdown(_fixture("scanned_sample.pdf", build_all))


# --------------------------------------------------------------------------
# born-digital scientific paper (vector path)
# --------------------------------------------------------------------------

class TestDigitalSciencePaper:
    def test_title_is_h1(self, science_md):
        assert "# Nitrogen Rate Effects on Creeping Bentgrass" in science_md

    def test_section_headings(self, science_md):
        assert "## Abstract" in science_md
        assert "## Materials and Methods" in science_md

    def test_booktabs_table_reconstructed(self, science_md):
        assert "| N rate | Yield | Color |" in science_md
        assert "| 49 | 18.9 | 6.4 |" in science_md
        assert "| 147 | 23.1 | 7.8 |" in science_md

    def test_table_not_duplicated_as_text(self, science_md):
        assert science_md.count("18.9") == 1

    def test_two_column_reading_order(self, science_md):
        """Left column (Abstract, Results, table) before right column."""
        order = [
            science_md.index("## Abstract"),
            science_md.index("## Results"),
            science_md.index("| N rate |"),
            science_md.index("## Materials and Methods"),
            science_md.index("## Discussion"),
        ]
        assert order == sorted(order)

    def test_table_inline_within_left_column(self, science_md):
        """Table sits between the Results text and the closing sentence."""
        assert science_md.index("shown in Table 1") \
            < science_md.index("| N rate |") \
            < science_md.index("Color ratings followed")

    def test_no_metadata(self, science_md):
        assert "SECRET-METADATA" not in science_md


# --------------------------------------------------------------------------
# scanned papers (OCR path)
# --------------------------------------------------------------------------

@needs_ocr
class TestScannedSciencePaper:
    def test_ocr_provenance_note(self, scanned_science_md):
        assert "converted with OCR" in scanned_science_md

    def test_title_text_recovered(self, scanned_science_md):
        assert "Nitrogen Rate Effects" in scanned_science_md

    def test_body_text_recovered(self, scanned_science_md):
        assert "putting green" in scanned_science_md
        assert "clippings were collected" in scanned_science_md

    def test_booktabs_table_recovered_from_scan(self, scanned_science_md):
        """The rate/yield rows must come back as a pipe table."""
        table_lines = [l for l in scanned_science_md.splitlines()
                       if l.startswith("|")]
        joined = "\n".join(table_lines)
        assert "49" in joined
        assert "98" in joined
        assert "147" in joined

    def test_deterministic(self, scanned_science_md):
        again = convert_pdf_to_markdown(os.path.join(FIX, "scanned_science.pdf"))
        assert again == scanned_science_md


@needs_ocr
class TestScannedRuledTable:
    def test_ruled_grid_table_from_scan(self, scanned_sample_md):
        """The v1 sample's fully ruled table, via pixel line detection."""
        table_lines = [l for l in scanned_sample_md.splitlines()
                       if l.startswith("|")]
        joined = " ".join(table_lines)
        assert "bluegrass" in joined
        assert "fescue" in joined

    def test_text_recovered(self, scanned_sample_md):
        assert "Turf Management Field Guide" in scanned_sample_md
