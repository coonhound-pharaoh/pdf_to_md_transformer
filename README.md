# PDF to MD Transformer

A free, open-source (MIT) desktop tool that **converts PDF files into clean, organized Markdown** — entirely on your own machine.

- **Deterministic and mechanical.** Conversion is pure geometry and typography analysis (no cloud, no network calls, no randomness). The same PDF with the same tool version always produces byte-identical Markdown.
- **Metadata is stripped.** Only page *content* reaches the output. The PDF's Info dictionary, XMP metadata, author/producer strings, etc. are never copied.
- **Tables come through as Markdown tables**, placed inline exactly where they appear in the document flow — both fully ruled grids and the borderless *booktabs* style (horizontal rules only) used by virtually all scientific journals, reconstructed from column alignment.
- **Scanned papers are supported.** Pages with no text layer are rendered at 300 dpi, deskewed, and read with the [Tesseract](https://github.com/tesseract-ocr/tesseract) OCR engine (Apache-2.0); ruled lines are recovered by pixel analysis so tables in old scans are reconstructed too. OCR'd pages are marked with an HTML comment (`<!-- page N: … converted with OCR … -->`) so downstream consumers know the provenance.
- **Sidebars / callout boxes** (detected as filled background rectangles containing text) are rendered inline as blockquotes at their position in the reading order.
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
3. Detects **sidebars** as filled background rectangles containing text (outside any table).
4. Rebuilds visual **lines** from positioned words (splitting side-by-side columns that share a baseline), finds the column gutter, and orders every element — paragraphs, tables, sidebars — into a single reading order.
5. Ranks **headings** by dominant font size, folds wrapped lines into paragraphs (repairing end-of-line hyphenation), and recognizes bullet/numbered lists.
6. Emits GitHub-flavoured Markdown. Nothing but page content is written.

Pages with **no text layer** (scanned papers) are rendered at 300 dpi, deskewed by projection-profile analysis, and read with Tesseract; ruled lines are recovered from pixel runs, and the exact same table-reconstruction and reading-order pipeline runs on the OCR word boxes.

Limitations: output on OCR'd pages is reproducible per Tesseract version but numbers should be spot-checked against the source (the page-level OCR comment marks where); mathematical equations have no faithful plain-text representation and will come through garbled; figures are omitted (their captions come through as text); sidebar detection requires a filled background box.

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
