"""Deterministic PDF -> Markdown conversion engine.

Every step is mechanical geometry and typography analysis -- no ML, no
network calls, no randomness.  The same input file always produces the
same output file.

Pipeline per page:
  1. Detect ruled tables (pdfplumber lattice detection).
  2. Detect sidebars: filled background rectangles that contain text and
     are not part of a table.
  3. Bucket every remaining word into "body" text.
  4. Rebuild lines from words, detect one- vs two-column layouts, and
     order all elements (lines, tables, sidebars) into natural reading
     order, placing tables and sidebars inline where they occur.
  5. Classify headings and list items by font size / leading glyphs.
  6. Render GitHub-flavoured Markdown.

Document metadata (Info dictionary, XMP, producer strings, etc.) is never
read into the output -- only page content is emitted.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence

import pdfplumber

BULLET_CHARS = "•◦·‣⁃∙-–—*"
BULLET_RE = re.compile(r"^([•◦·‣⁃∙*]|\(cid:\d+\)|[-–—](?=\s))\s*")
NUMBERED_RE = re.compile(r"^(\d{1,3})[.)]\s+")


# --------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------

@dataclass
class Line:
    """One visual line of text."""
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float          # median glyph size on the line
    nchars: int

    kind: str = "line"   # constant; used by the ordering code


@dataclass
class TableItem:
    rows: List[List[str]]
    x0: float
    x1: float
    top: float
    bottom: float
    kind: str = "table"


@dataclass
class SidebarItem:
    lines: List[Line] = field(default_factory=list)
    x0: float = 0.0
    x1: float = 0.0
    top: float = 0.0
    bottom: float = 0.0
    kind: str = "sidebar"


@dataclass
class PageStream:
    """Ordered content items for one page."""
    items: list = field(default_factory=list)


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------

def _center_in(bbox, x, y) -> bool:
    x0, top, x1, bottom = bbox
    return x0 <= x <= x1 and top <= y <= bottom


def _word_center(w):
    return ((w["x0"] + w["x1"]) / 2.0, (w["top"] + w["bottom"]) / 2.0)


def _clean_text(s: str) -> str:
    s = s.replace("\x00", "")
    s = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s)
    return s.strip()


def _words_to_lines(words) -> List[Line]:
    """Group positioned words into visual lines (deterministic)."""
    if not words:
        return []
    words = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))
    lines: List[Line] = []
    current: List[dict] = []
    for w in words:
        if not current:
            current = [w]
            continue
        ref = current[0]
        # same line if vertical overlap of at least half the smaller height
        h = min(ref["bottom"] - ref["top"], w["bottom"] - w["top"])
        overlap = min(ref["bottom"], w["bottom"]) - max(ref["top"], w["top"])
        if h > 0 and overlap >= 0.5 * h:
            current.append(w)
        else:
            lines.append(_make_line(current))
            current = [w]
    if current:
        lines.append(_make_line(current))
    return [ln for ln in lines if ln.text]


def _make_line(ws) -> Line:
    ws = sorted(ws, key=lambda w: w["x0"])
    text = _clean_text(" ".join(w["text"] for w in ws))
    sizes = [float(w.get("size") or (w["bottom"] - w["top"])) for w in ws]
    return Line(
        text=text,
        x0=min(w["x0"] for w in ws),
        x1=max(w["x1"] for w in ws),
        top=min(w["top"] for w in ws),
        bottom=max(w["bottom"] for w in ws),
        size=statistics.median(sizes),
        nchars=sum(len(w["text"]) for w in ws),
    )


# --------------------------------------------------------------------------
# reading order
# --------------------------------------------------------------------------

def _order_items(items: list, content_x0: float, content_x1: float) -> list:
    """Order mixed items (lines / tables / sidebars) into reading order.

    Detects a two-column body via an empty vertical gutter; full-width
    items act as segment separators.  Falls back to plain top-to-bottom
    ordering for single-column pages.
    """
    if not items:
        return []
    width = max(content_x1 - content_x0, 1.0)
    fulls = [it for it in items if (it.x1 - it.x0) > 0.66 * width]
    narrow = [it for it in items if (it.x1 - it.x0) <= 0.66 * width]

    gutter = _find_gutter(narrow, content_x0, width)
    if gutter is None:
        return sorted(items, key=lambda it: (round(it.top, 1), it.x0))

    fulls.sort(key=lambda it: it.top)

    def seg_index(it) -> int:
        i = 0
        for f in fulls:
            if f.bottom - 2 <= it.top:
                i += 1
        return i

    ordered: list = []
    for i in range(len(fulls) + 1):
        if i > 0:
            ordered.append(fulls[i - 1])
        seg = [it for it in narrow if seg_index(it) == i]
        left = sorted((it for it in seg if it.x1 <= gutter + 2), key=lambda it: it.top)
        right = sorted((it for it in seg if it.x0 >= gutter - 2), key=lambda it: it.top)
        ordered.extend(left)
        ordered.extend(right)
    return ordered


def _find_gutter(narrow: list, content_x0: float, width: float) -> Optional[float]:
    """Return the x of an empty vertical gutter if the page is two-column."""
    if len(narrow) < 6:
        return None
    lo = content_x0 + 0.30 * width
    hi = content_x0 + 0.70 * width
    candidates = []
    x = lo
    while x <= hi:
        if all(not (it.x0 - 2 < x < it.x1 + 2) for it in narrow):
            candidates.append(x)
        x += 3.0
    if not candidates:
        return None
    gutter = statistics.median(candidates)
    left = [it for it in narrow if it.x1 <= gutter + 2]
    right = [it for it in narrow if it.x0 >= gutter - 2]
    if len(left) >= 3 and len(right) >= 3 and len(left) + len(right) == len(narrow):
        return gutter
    return None


# --------------------------------------------------------------------------
# per-page parsing
# --------------------------------------------------------------------------

def _detect_sidebar_regions(page, table_bboxes) -> List[tuple]:
    """Filled rectangles big enough to be callout boxes, outside tables."""
    page_area = page.width * page.height
    regions = []
    rects = sorted(
        (r for r in page.rects if r.get("fill")),
        key=lambda r: (r["x1"] - r["x0"]) * (r["bottom"] - r["top"]),
        reverse=True,
    )
    for r in rects:
        w = r["x1"] - r["x0"]
        h = r["bottom"] - r["top"]
        if w < 90 or h < 30:
            continue
        area = w * h
        if area > 0.85 * page_area or area < 0.01 * page_area:
            continue
        bbox = (r["x0"], r["top"], r["x1"], r["bottom"])
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        if any(_center_in(tb, cx, cy) for tb in table_bboxes):
            continue
        if any(_center_in(existing, cx, cy) for existing in regions):
            continue  # nested inside an already-kept region
        regions.append(bbox)
    return regions


def _extract_table_rows(table) -> List[List[str]]:
    rows = []
    for raw in table.extract():
        row = []
        for cell in raw:
            cell = "" if cell is None else str(cell)
            cell = _clean_text(re.sub(r"\s+", " ", cell))
            row.append(cell)
        rows.append(row)
    # drop fully empty rows
    rows = [r for r in rows if any(c for c in r)]
    return rows


def _parse_page(page) -> PageStream:
    stream = PageStream()

    tables = page.find_tables()
    table_bboxes = [t.bbox for t in tables]
    table_items = []
    for t in tables:
        rows = _extract_table_rows(t)
        if rows:
            x0, top, x1, bottom = t.bbox
            table_items.append(TableItem(rows=rows, x0=x0, x1=x1, top=top, bottom=bottom))

    sidebar_regions = _detect_sidebar_regions(page, table_bboxes)

    words = page.extract_words(extra_attrs=["size"], keep_blank_chars=False)

    body_words = []
    sidebar_words: List[list] = [[] for _ in sidebar_regions]
    for w in words:
        cx, cy = _word_center(w)
        if any(_center_in(tb, cx, cy) for tb in table_bboxes):
            continue  # rendered via the table item
        placed = False
        for i, region in enumerate(sidebar_regions):
            if _center_in(region, cx, cy):
                sidebar_words[i].append(w)
                placed = True
                break
        if not placed:
            body_words.append(w)

    sidebar_items = []
    for region, ws in zip(sidebar_regions, sidebar_words):
        if len(ws) < 4:
            body_words.extend(ws)  # decorative rect, not a sidebar
            continue
        lines = _words_to_lines(ws)
        lines = _order_items(lines, region[0], region[2])
        sidebar_items.append(
            SidebarItem(lines=lines, x0=region[0], x1=region[2], top=region[1], bottom=region[3])
        )

    body_lines = _words_to_lines(body_words)

    all_items = list(body_lines) + table_items + sidebar_items
    if all_items:
        content_x0 = min(it.x0 for it in all_items)
        content_x1 = max(it.x1 for it in all_items)
        stream.items = _order_items(all_items, content_x0, content_x1)
    return stream


# --------------------------------------------------------------------------
# markdown rendering
# --------------------------------------------------------------------------

def _escape_cell(s: str) -> str:
    return s.replace("|", "\\|")


def _render_table(rows: List[List[str]]) -> str:
    if not rows:
        return ""
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    out = ["| " + " | ".join(_escape_cell(c) for c in rows[0]) + " |"]
    out.append("|" + "|".join(" --- " for _ in range(ncols)) + "|")
    for r in rows[1:]:
        out.append("| " + " | ".join(_escape_cell(c) for c in r) + " |")
    return "\n".join(out)


def _join_par(lines: List[str]) -> str:
    """Join wrapped lines into one paragraph, repairing hyphenation."""
    out = ""
    for piece in lines:
        if not out:
            out = piece
            continue
        if out.endswith("-") and piece[:1].islower():
            out = out[:-1] + piece
        else:
            out += " " + piece
    return re.sub(r"\s+", " ", out).strip()


class _Renderer:
    def __init__(self, body_size: float, heading_sizes: List[float]):
        self.body_size = body_size
        self.heading_sizes = heading_sizes
        self.blocks: List[str] = []

    def _heading_level(self, size: float) -> int:
        rounded = round(size * 2) / 2
        try:
            return min(self.heading_sizes.index(rounded) + 1, 6)
        except ValueError:
            return min(len(self.heading_sizes) + 1, 6)

    def _is_heading(self, line: Line) -> bool:
        return (
            line.size >= self.body_size * 1.18
            and len(line.text.split()) <= 14
        )

    def render_lines(self, lines: List[Line], quote: bool = False) -> List[str]:
        """Fold ordered lines into markdown blocks."""
        blocks: List[str] = []
        par: List[str] = []
        par_last: Optional[Line] = None

        def flush():
            nonlocal par, par_last
            if par:
                text = _join_par(par)
                if text:
                    blocks.append(text)
            par = []
            par_last = None

        i = 0
        while i < len(lines):
            ln = lines[i]
            text = ln.text
            if not text:
                i += 1
                continue

            if self._is_heading(ln):
                flush()
                # merge immediately-following heading lines of the same size
                htexts = [text]
                j = i + 1
                while (
                    j < len(lines)
                    and self._is_heading(lines[j])
                    and abs(lines[j].size - ln.size) < 0.6
                    and lines[j].top - lines[j - 1].bottom < ln.size
                ):
                    htexts.append(lines[j].text)
                    j += 1
                level = self._heading_level(round(ln.size * 2) / 2)
                blocks.append("#" * level + " " + _join_par(htexts))
                i = j
                continue

            m = BULLET_RE.match(text)
            n = NUMBERED_RE.match(text)
            if m or n:
                flush()
                items = []
                while i < len(lines):
                    lt = lines[i].text
                    bm = BULLET_RE.match(lt)
                    nm = NUMBERED_RE.match(lt)
                    if bm:
                        items.append(("- ", bm.end(), i))
                    elif nm:
                        items.append((nm.group(1) + ". ", nm.end(), i))
                    elif items and lines[i].top - lines[i - 1].bottom < lines[i].size:
                        pass  # wrapped continuation; absorbed in _render_list
                    else:
                        break
                    i += 1
                blocks.extend(self._render_list(lines, items))
                continue

            gap_break = (
                par_last is not None
                and (ln.top - par_last.bottom) > max(ln.size, par_last.size) * 0.9
            )
            col_break = (
                par_last is not None
                and ln.top < par_last.top - 2  # jumped back up: new column
            )
            if gap_break or col_break:
                flush()
            par.append(text)
            par_last = ln
            i += 1

        flush()
        if quote:
            blocks = ["\n".join("> " + l for l in b.split("\n")) for b in blocks]
        return blocks

    def _render_list(self, lines: List[Line], items) -> List[str]:
        """Render collected list-item line indices as a markdown list."""
        out = []
        for k, (marker, end, idx) in enumerate(items):
            txt = lines[idx].text[end:].strip()
            # absorb wrapped continuation lines up to the next item
            nxt = items[k + 1][2] if k + 1 < len(items) else None
            j = idx + 1
            while j < len(lines) and (nxt is None or j < nxt):
                cont = lines[j]
                if BULLET_RE.match(cont.text) or NUMBERED_RE.match(cont.text):
                    break
                if cont.top - lines[j - 1].bottom < cont.size:
                    txt = _join_par([txt, cont.text])
                    j += 1
                else:
                    break
            out.append(marker + txt)
        return ["\n".join(out)] if out else []

    def render_stream(self, stream: PageStream) -> None:
        pending_lines: List[Line] = []

        def flush_lines():
            nonlocal pending_lines
            if pending_lines:
                self.blocks.extend(self.render_lines(pending_lines))
                pending_lines = []

        for it in stream.items:
            if it.kind == "line":
                pending_lines.append(it)
            elif it.kind == "table":
                flush_lines()
                self.blocks.append(_render_table(it.rows))
            elif it.kind == "sidebar":
                flush_lines()
                quoted = self.render_lines(it.lines, quote=True)
                if quoted:
                    self.blocks.append("\n>\n".join(quoted))
        flush_lines()


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

def convert_pdf_to_markdown(
    pdf_path: str,
    progress: Optional[Callable[[int, int], None]] = None,
) -> str:
    """Convert one PDF file to a Markdown string (content only)."""
    streams: List[PageStream] = []
    with pdfplumber.open(pdf_path) as pdf:
        npages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            streams.append(_parse_page(page))
            if progress:
                progress(i + 1, npages)

    # global typography: dominant body size weighted by character count
    size_counter: Counter = Counter()
    for st in streams:
        for it in st.items:
            if it.kind == "line":
                size_counter[round(it.size * 2) / 2] += it.nchars
            elif it.kind == "sidebar":
                for ln in it.lines:
                    size_counter[round(ln.size * 2) / 2] += ln.nchars
    body_size = size_counter.most_common(1)[0][0] if size_counter else 12.0

    heading_sizes = sorted(
        {s for s in size_counter if s >= body_size * 1.18},
        reverse=True,
    )

    renderer = _Renderer(body_size=float(body_size), heading_sizes=heading_sizes)
    for st in streams:
        renderer.render_stream(st)

    md = "\n\n".join(b for b in renderer.blocks if b.strip())
    return md + "\n" if md else ""


def convert_file(pdf_path: str, out_path: str,
                 progress: Optional[Callable[[int, int], None]] = None) -> str:
    md = convert_pdf_to_markdown(pdf_path, progress=progress)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    return out_path
