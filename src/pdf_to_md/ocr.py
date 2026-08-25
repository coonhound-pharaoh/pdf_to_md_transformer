"""OCR support for scanned (image-only) PDF pages.

Uses the Tesseract engine (Apache-2.0) through pytesseract.  All
post-processing is deterministic; Tesseract itself is deterministic for
a fixed version + traineddata, so output is reproducible per install.

Provides:
  * find_tesseract()      -- locate the tesseract binary (bundled, PATH,
                             or well-known install locations)
  * page_needs_ocr(page)  -- True when the page has no usable text layer
  * ocr_page(page)        -- render @300dpi, deskew, OCR -> word boxes in
                             PDF points, plus detected horizontal and
                             vertical rule lines from pixel analysis
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

DPI = 300
MIN_WORD_CONF = 30.0        # tesseract confidence floor; below is noise
BINARIZE_THRESHOLD = 160    # gray level; darker = ink
LINE_DARK_FRAC = 0.62       # windowed dark fraction that counts as "line"
LINE_WINDOW_PX = 31         # smoothing window along the line direction
H_LINE_MIN_FRAC = 0.10      # min h-line length as fraction of page width
V_LINE_MIN_PX = 110         # min v-line length in pixels (@300dpi ~ 26pt)
MAX_LINE_THICKNESS_PX = 14  # thicker dark bands are images, not rules

_tesseract_cmd: Optional[str] = None
_checked = False


def find_tesseract() -> Optional[str]:
    """Locate tesseract: env var, bundled copy, PATH, standard installs."""
    global _tesseract_cmd, _checked
    if _checked:
        return _tesseract_cmd
    _checked = True

    exe = "tesseract.exe" if os.name == "nt" else "tesseract"
    candidates = []
    env = os.environ.get("PDF2MD_TESSERACT")
    if env:
        candidates.append(env)
    # bundled next to the frozen executable (Windows installer layout)
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable),
                                       "Tesseract-OCR", exe))
    which = shutil.which("tesseract")
    if which:
        candidates.append(which)
    candidates += [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/usr/bin/tesseract",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            _tesseract_cmd = c
            tessdata = os.path.join(os.path.dirname(c), "tessdata")
            if os.path.isdir(tessdata) and "TESSDATA_PREFIX" not in os.environ:
                os.environ["TESSDATA_PREFIX"] = tessdata
            break
    return _tesseract_cmd


def ocr_available() -> bool:
    return find_tesseract() is not None


def page_needs_ocr(page) -> bool:
    """True when the page has essentially no extractable text layer."""
    return len(page.chars) < 5


# --------------------------------------------------------------------------
# image processing (deterministic, numpy only)
# --------------------------------------------------------------------------

def _deskew(img: Image.Image) -> Image.Image:
    """Small-angle deskew by maximizing row-projection variance."""
    small = img.resize((max(1, img.width // 4), max(1, img.height // 4)))
    best_angle, best_score = 0.0, -1.0
    for q in range(-12, 13):                       # -3.0 .. +3.0 in 0.25 steps
        angle = q / 4.0
        rot = small.rotate(angle, fillcolor=255) if angle else small
        arr = np.asarray(rot) < BINARIZE_THRESHOLD
        score = float(np.var(arr.sum(axis=1)))
        if score > best_score + 1e-6:
            best_angle, best_score = angle, score
    if abs(best_angle) >= 0.3:
        return img.rotate(best_angle, fillcolor=255, resample=Image.BICUBIC)
    return img


def _windowed_mean(mat: np.ndarray, win: int, axis: int) -> np.ndarray:
    """Centered moving average along an axis (same shape, edge-padded)."""
    kernel_shape = [1, 1]
    kernel_shape[axis] = win
    pad = [(0, 0), (0, 0)]
    pad[axis] = (win // 2, win - win // 2 - 1)
    padded = np.pad(mat.astype(np.float32), pad, mode="edge")
    cs = np.cumsum(padded, axis=axis)
    if axis == 0:
        out = (cs[win - 1:, :] - np.vstack([np.zeros((1, cs.shape[1]), np.float32),
                                            cs[:-win, :]]))
    else:
        out = (cs[:, win - 1:] - np.hstack([np.zeros((cs.shape[0], 1), np.float32),
                                            cs[:, :-win]]))
    return out / win


def _detect_rules_px(binary: np.ndarray) -> Tuple[List[dict], List[dict]]:
    """Find horizontal and vertical ruled lines in a binarized page image.

    Returns (h_lines, v_lines) in pixel coordinates:
      h_lines: {x0, x1, top}
      v_lines: {top, bottom, x}
    """
    H, W = binary.shape

    def scan(mat, min_len):
        """Rows of `mat` whose smoothed dark runs exceed min_len."""
        smooth = _windowed_mean(mat, LINE_WINDOW_PX, axis=1)
        mask = smooth >= LINE_DARK_FRAC
        hits = []
        for y in range(mat.shape[0]):
            row = mask[y]
            if not row.any():
                continue
            xs = np.flatnonzero(row)
            # longest consecutive run
            splits = np.flatnonzero(np.diff(xs) > 1)
            runs = np.split(xs, splits + 1)
            run = max(runs, key=len)
            if len(run) >= min_len:
                hits.append((y, int(run[0]), int(run[-1])))
        # group consecutive hit-rows into physical lines
        lines = []
        cur = []
        for h in hits:
            if cur and h[0] - cur[-1][0] <= 2:
                cur.append(h)
            else:
                if cur:
                    lines.append(cur)
                cur = [h]
        if cur:
            lines.append(cur)
        out = []
        for grp in lines:
            if len(grp) > MAX_LINE_THICKNESS_PX:
                continue  # image block, not a rule
            ys = [g[0] for g in grp]
            out.append({
                "pos": sum(ys) / len(ys),
                "lo": min(g[1] for g in grp),
                "hi": max(g[2] for g in grp),
            })
        return out

    h_raw = scan(binary, max(int(H_LINE_MIN_FRAC * W), 60))
    v_raw = scan(binary.T, V_LINE_MIN_PX)

    h_lines = [{"x0": float(l["lo"]), "x1": float(l["hi"]), "top": float(l["pos"])}
               for l in h_raw]
    v_lines = [{"top": float(l["lo"]), "bottom": float(l["hi"]), "x": float(l["pos"])}
               for l in v_raw]
    return h_lines, v_lines


# --------------------------------------------------------------------------
# main entry
# --------------------------------------------------------------------------

def ocr_page(page) -> Tuple[List[dict], List[dict], List[dict]]:
    """OCR one pdfplumber page.

    Returns (words, h_rules, v_rules) with all coordinates in PDF points
    (same space the vector pipeline uses).  Raises RuntimeError when no
    tesseract binary can be found.
    """
    cmd = find_tesseract()
    if cmd is None:
        raise RuntimeError(
            "This page is a scanned image and requires the Tesseract OCR "
            "engine, which was not found. Install it (Windows: bundled "
            "with the installer; macOS: brew install tesseract; Linux: "
            "apt install tesseract-ocr) or set PDF2MD_TESSERACT."
        )
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = cmd

    img = page.to_image(resolution=DPI).original.convert("L")
    img = _deskew(img)
    k = 72.0 / DPI  # px -> pt

    data = pytesseract.image_to_data(
        img, output_type=pytesseract.Output.DICT, config="--psm 3"
    )
    words = []
    for i in range(len(data["text"])):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < MIN_WORD_CONF:
            continue
        x, y = data["left"][i], data["top"][i]
        w, h = data["width"][i], data["height"][i]
        if w <= 0 or h <= 0:
            continue
        words.append({
            "text": text,
            "x0": x * k, "x1": (x + w) * k,
            "top": y * k, "bottom": (y + h) * k,
            "size": h * k,
            "conf": conf,
        })

    binary = np.asarray(img) < BINARIZE_THRESHOLD
    h_px, v_px = _detect_rules_px(binary)
    h_rules = [{"x0": l["x0"] * k, "x1": l["x1"] * k, "top": l["top"] * k}
               for l in h_px]
    v_rules = [{"top": l["top"] * k, "bottom": l["bottom"] * k, "x": l["x"] * k}
               for l in v_px]
    return words, h_rules, v_rules
