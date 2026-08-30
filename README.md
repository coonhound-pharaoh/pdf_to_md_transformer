# PDF to MD Transformer

A free, open-source (MIT) desktop tool that **converts PDF files into clean, organized Markdown** — entirely on your own machine.

- **Deterministic and mechanical.** Conversion is pure geometry and typography analysis (no cloud, no network calls, no randomness). The same PDF with the same tool version always produces byte-identical Markdown.
- **Metadata is stripped.** Only page *content* reaches the output. The PDF's Info dictionary, XMP metadata, author/producer strings, etc. are never copied.
- **Tables come through as Markdown tables**, placed inline exactly where they appear in the document flow — both fully ruled grids and the borderless *booktabs* style (horizontal rules only) used by virtually all scientific journals, reconstructed from column alignment.
- **Scanned papers are supported.** Pages with no text layer are rendered at 300 dpi, deskewed, and read with the [Tesseract](https://github.com/tesseract-ocr/tesseract) OCR engine (Apache-2.0); ruled lines are recovered by pixel analysis so tables in old scans are reconstructed too. OCR'd pages carry a provenance comment naming the engine version, page-segmentation mode, dpi and language, and every doubtful number is listed for checking (see below).
- **Figures are anchored, not dropped.** Embedded images and vector illustrations are detected and placed in reading order with their caption bound to them (`Figure 3: …` above or below); `--extract-images` writes each one as a PNG into `<name>_assets/` and links it.
- **Equations are reconstructed as LaTeX where the layout can be read with certainty** — fractions from the rule geometry, super/subscripts from baseline offsets, sums and integrals with their limits, radicals from the overline — and emitted as a `$$` block labelled as reconstructed. Where anything is uncertain (an undecodable glyph, an unexplained rule), nothing is claimed: the equation falls back to a labelled ```` ```equation ```` block holding the verbatim glyph run. Either way it stops flowing into the prose.
- **Sidebars / callout boxes** are rendered inline as blockquotes at their position in the reading order, whether they are shaded panels, boxes drawn with a border (a stroked rectangle or four separate lines), or unboxed pull quotes set inset in a different size or face.
- **Layout-aware:** two-column pages are re-flowed into natural reading order; headings are ranked by font size into `#`–`######`; bulleted and numbered lists are preserved; hyphenated line-wraps are repaired.
- **Simple UI:** pick PDFs, pick an output folder, press *Convert*. A command-line interface (`pdf2md`) is included for scripting.

## Install

Grab the installer for your platform from the [Releases](../../releases) page:

| Platform | File | OCR engine |
| --- | --- | --- |
| Windows x64 | `PDF-to-MD-Transformer-Setup-win-x64.exe` | bundled |
| macOS | `PDF-to-MD-Transformer-macOS.dmg` | `brew install tesseract` |
| Linux (Debian/Ubuntu) | `pdf-to-md-transformer_<version>_amd64.deb` | installed automatically (Recommends) |

On Linux: `sudo apt install ./pdf-to-md-transformer_<version>_amd64.deb`

Without Tesseract the app still fully converts any PDF that has a text layer; scanned pages are skipped with an explanatory comment in the output. A custom Tesseract location can be set with the `PDF2MD_TESSERACT` environment variable.

### Run from source (any platform with Python 3.9+)

```
pip install .
pdf2md-gui          # GUI
pdf2md file.pdf     # CLI -> file.md next to the PDF
```

## Use from an AI agent

The tool is fully drivable by an AI agent (Claude Code, Codex, …) as well as by
hand — same engine, same deterministic output.

**MCP server** (`pdf2md-mcp`, JSON-RPC over stdio, no extra dependencies):

```
claude mcp add pdf2md -- pdf2md-mcp
```

exposing `convert_pdf` (PDF -> Markdown text), `convert_file` (PDF -> `.md` on
disk) and `pdf_info` (page count, which pages need OCR, OCR availability).

**Scriptable CLI:** `--stdout` emits the Markdown, `--json` emits a
machine-readable per-file report (stdout carries only the payload; logs go to
stderr), and the exit code is non-zero if any file failed.

A bundled Claude skill in `.claude/skills/pdf-to-markdown/` makes the agent
reach for the tool automatically. Full interface reference: [AGENTS.md](AGENTS.md).

## How it works

For each page with a text layer, the engine:

1. Detects ruled **tables** with lattice analysis ([pdfplumber](https://github.com/jsvine/pdfplumber), MIT).
2. Detects **borderless (booktabs) tables**: stacked horizontal rules bound a candidate region, column boundaries are found as vertical strips that no line of words crosses, and the grid is rebuilt from word positions. A candidate that doesn't convincingly form a table flows back into body text, so false positives can't destroy content.
3. Detects **sidebars**: filled panels, ruled boxes (stroked rectangles or four lines meeting at the corners), and — once lines exist — unboxed blocks that are inset from both sides, separated above and below, and set in a different size or face. The unboxed case is gated hard: a line sitting on any column margin is a column, not a callout, and an indented continuation in the body face stays a paragraph.
4. Rebuilds visual **lines** from positioned words (splitting side-by-side columns that share a baseline), finds the column gutter, and orders every element — paragraphs, tables, sidebars — into a single reading order.
5. Detects **display equations** — by mathematical glyphs and fonts, or by the geometry of a fraction rule — and rebuilds the expression from the positions of its glyphs, falling back to a verbatim block whenever the layout is not fully understood. A math-heavy line that is really a sentence stays prose.
6. Detects **figures** (embedded rasters and clusters of vector drawing outside tables and sidebars), binds the nearest matching caption, and drops in-figure labels from the prose. A candidate region full of text is discarded so body copy can't be swallowed.
7. Ranks **headings** by dominant font size, folds wrapped lines into paragraphs (repairing end-of-line hyphenation), and recognizes bullet/numbered lists.
8. Emits GitHub-flavoured Markdown. Nothing but page content is written.

Pages with **no text layer** (scanned papers) are rendered at 300 dpi, deskewed by projection-profile analysis, and read with Tesseract; ruled lines are recovered from pixel runs, and the exact same table-reconstruction and reading-order pipeline runs on the OCR word boxes.

Because OCR can be wrong in ways geometry cannot detect, every numeric token is checked twice: against Tesseract's own confidence, and against a second read of the same pixels restricted to digits. Tokens that fail either check are named in a per-page comment, so verifying a scan means checking a handful of marked numbers instead of the whole page:

```
<!-- page 3: no text layer; converted with OCR (tesseract 5.3.4, psm 3, 300 dpi, lang eng) -->
<!-- page 3: 2 numeric tokens to check against the source: '12.5' (confidence 61), '1,024' (reread as '1.024') -->
```

`--no-math-latex` disables reconstruction entirely if you would rather always see the raw glyphs. `--ocr-lang`, `--ocr-dpi` (400 helps small type), `--ocr-psm` and `--no-verify-numbers` tune the OCR pass.

Limitations: output on OCR'd pages is reproducible only for a fixed Tesseract version (which the page comment records) and doubtful numbers are flagged rather than corrected -- an unflagged number is likely but not certain to be right; reconstructed LaTeX is inferred from layout and should be checked against the source (the block comment says which equations are reconstructed); equations the parser will not vouch for are preserved verbatim instead, and the glyph run inside an `equation` block is not a usable formula; fonts with no ToUnicode CMap other than Adobe `Symbol` cannot be decoded, so equations using them are always verbatim; inline maths within a paragraph is not detected; figures are anchored in place with their captions but are only exported as images with `--extract-images` (equations rendered as figures are therefore images, not text); unboxed callouts are only found when they differ typographically from the body, so a callout that is merely indented reads as an ordinary paragraph.

## Development

```
pip install -e .[dev]
python tests/make_fixture.py   # build the test PDF (reportlab)
pytest
```

Installers for all three platforms are built by [GitHub Actions](.github/workflows/build.yml) on native runners (PyInstaller + Inno Setup / hdiutil / dpkg-deb) whenever a `v*` tag is pushed.

## License

[MIT](LICENSE) © 2026 Michael Macauley. All dependencies are MIT-compatible (pdfplumber: MIT; pdfminer.six: MIT; Pillow: MIT-CMU). This project deliberately avoids AGPL-licensed PDF libraries.

## AI authorship disclosure

This repository was created and is maintained by **Claude** (specifically Claude Fable 5 via Claude Code, an AI agent made by Anthropic), **acting as the authorized agent of Michael Macauley ([@coonhound-pharaoh](https://github.com/coonhound-pharaoh)) and on his behalf**. Commits, releases, and documentation authored by the agent are labeled as such.
