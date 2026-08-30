"""OCR provenance markers and numeric-token flagging.

Most of this runs without Tesseract installed: the classification, the
flagging policy and the note formatting are pure functions over word
dicts.  Only the end-to-end scan test needs the engine.
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from pdf_to_md import ocr  # noqa: E402
from pdf_to_md.engine import _suspect_note, convert_pdf_to_markdown  # noqa: E402
from pdf_to_md.ocr import (  # noqa: E402
    OcrOptions,
    is_numeric_token,
    normalise_number,
    ocr_available,
)

REQUIRE_OCR = os.environ.get("PDF2MD_REQUIRE_OCR") == "1"
needs_ocr = pytest.mark.skipif(
    not ocr_available() and not REQUIRE_OCR,
    reason="tesseract not installed (set PDF2MD_REQUIRE_OCR=1 to force)",
)


def _word(text, conf=99.0):
    return {"text": text, "conf": conf,
            "x0": 10.0, "x1": 40.0, "top": 10.0, "bottom": 20.0}


# --------------------------------------------------------------------------
# which tokens are worth checking
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["12.5", "1,024", "98%", "(3)", "45.6,",
                                  "$1,024.50", "12/2024", "-7"])
def test_numeric_tokens_recognised(text):
    assert is_numeric_token(text)


@pytest.mark.parametrize("text", ["Kentucky", "Fig.3b", "H2O", "", "n=",
                                  "bluegrass"])
def test_non_numeric_tokens_ignored(text):
    assert not is_numeric_token(text)


def test_normalise_number_ignores_separator_disagreement():
    assert normalise_number("1,024.50") == normalise_number("1.024,50")


# --------------------------------------------------------------------------
# flagging policy
# --------------------------------------------------------------------------

def test_low_confidence_number_is_flagged(monkeypatch):
    monkeypatch.setattr(ocr, "_reread_digits", lambda *a, **k: None)
    words = [_word("12.5", conf=61.0), _word("Kentucky", conf=40.0)]
    ocr._flag_numbers(None, words, 1 / 300.0, OcrOptions())
    assert "confidence 61" in words[0]["suspect"]
    assert "suspect" not in words[1]  # words aren't numbers


def test_confident_number_is_not_flagged(monkeypatch):
    monkeypatch.setattr(ocr, "_reread_digits", lambda *a, **k: "12.5")
    words = [_word("12.5", conf=97.0)]
    ocr._flag_numbers(None, words, 1 / 300.0, OcrOptions())
    assert "suspect" not in words[0]


def test_disagreeing_reread_flags_even_a_confident_number(monkeypatch):
    monkeypatch.setattr(ocr, "_reread_digits", lambda *a, **k: "72.5")
    words = [_word("12.5", conf=99.0)]
    ocr._flag_numbers(None, words, 1 / 300.0, OcrOptions())
    assert "reread as '72.5'" in words[0]["suspect"]


def test_reread_pass_can_be_switched_off(monkeypatch):
    called = []
    monkeypatch.setattr(ocr, "_reread_digits",
                        lambda *a, **k: called.append(1) or "999")
    words = [_word("12.5", conf=99.0)]
    ocr._flag_numbers(None, words, 1 / 300.0,
                      OcrOptions(verify_numbers=False))
    assert not called and "suspect" not in words[0]


def test_recheck_budget_is_capped_but_confidence_still_applies(monkeypatch):
    calls = []
    monkeypatch.setattr(ocr, "_reread_digits",
                        lambda *a, **k: calls.append(1) or "5")
    words = [_word("5", conf=50.0) for _ in range(ocr.MAX_RECHECKS + 5)]
    ocr._flag_numbers(None, words, 1 / 300.0, OcrOptions())
    assert len(calls) == ocr.MAX_RECHECKS
    assert "not re-read" in words[-1]["suspect"]


# --------------------------------------------------------------------------
# the note the reader actually sees
# --------------------------------------------------------------------------

def test_no_note_when_nothing_is_doubtful():
    assert _suspect_note(3, [_word("12.5")]) is None


def test_note_lists_tokens_and_reasons():
    words = [_word("12.5"), _word("1,024")]
    words[0]["suspect"] = "confidence 61"
    words[1]["suspect"] = "reread as '1.024'"
    note = _suspect_note(3, words)
    assert note.startswith("<!-- page 3: 2 numeric tokens to check")
    assert "'12.5' (confidence 61)" in note
    assert "'1,024' (reread as '1.024')" in note
    assert note.endswith("-->")


def test_note_truncates_a_long_list():
    words = []
    for i in range(20):
        w = _word(str(i))
        w["suspect"] = "confidence 50"
        words.append(w)
    note = _suspect_note(1, words)
    assert "20 numeric tokens" in note
    assert f"and {20 - ocr_max()} more" in note


def ocr_max():
    from pdf_to_md.engine import MAX_LISTED_SUSPECTS
    return MAX_LISTED_SUSPECTS


# --------------------------------------------------------------------------
# provenance
# --------------------------------------------------------------------------

def test_version_probe_returns_none_without_an_engine(monkeypatch):
    monkeypatch.setattr(ocr, "_version", None)
    monkeypatch.setattr(ocr, "find_tesseract", lambda: None)
    assert ocr.tesseract_version() is None


def test_version_is_parsed_from_engine_banner(monkeypatch):
    import subprocess
    monkeypatch.setattr(ocr, "_version", None)
    monkeypatch.setattr(ocr, "find_tesseract", lambda: "/usr/bin/tesseract")

    class R:
        stdout = "tesseract 5.3.4\n leptonica-1.84.1\n"
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: R())
    assert ocr.tesseract_version() == "5.3.4"


@needs_ocr
def test_scanned_page_marker_records_provenance():
    fixture = os.path.join(HERE, "fixtures", "scanned.pdf")
    if not os.path.exists(fixture):
        from make_scanned_fixture import build
        build(fixture)
    md = convert_pdf_to_markdown(
        fixture, ocr_options=OcrOptions(verify_numbers=False))
    assert "converted with OCR (tesseract " in md
    assert "psm 3, 300 dpi, lang eng" in md
