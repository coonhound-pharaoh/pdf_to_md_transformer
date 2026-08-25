# PDF to MD Transformer

A free, open-source (MIT) desktop tool that **converts PDF files into clean, organized Markdown** — entirely on your own machine.

- **Deterministic and mechanical.** Conversion is pure geometry and typography analysis (no AI, no cloud, no network calls, no randomness). The same PDF always produces byte-identical Markdown.
- **Metadata is stripped.** Only page *content* reaches the output. The PDF's Info dictionary, XMP metadata, author/producer strings, etc. are never copied.
- **Tables come through as Markdown tables**, placed inline exactly where they appear in the document flow.
- **Sidebars / callout boxes** (detected as filled background rectangles containing text) are rendered inline as blockquotes at their position in the reading order.
- **Layout-aware:** two-column pages are re-flowed into natural reading order; headings are ranked by font size into `#`–`######`; bulleted and numbered lists are preserved; hyphenated line-wraps are repaired.
- **Simple UI:** pick PDFs, pick an output folder, press *Convert*. A command-line interface (`pdf2md`) is included for scripting.

## Install

Grab the installer for your platform from the [Releases](../../releases) page:

| Platform | File |
| --- | --- |
| Windows x64 | `PDF-to-MD-Transformer-Setup-win-x64.exe` |
| macOS | `PDF-to-MD-Transformer-macOS.dmg` |
| Linux (Debian/Ubuntu) | `pdf-to-md-transformer_<version>_amd64.deb` |

On Linux: `sudo apt install ./pdf-to-md-transformer_<version>_amd64.deb`

### Run from source (any platform with Python 3.9+)

```
pip install .
pdf2md-gui          # GUI
pdf2md file.pdf     # CLI -> file.md next to the PDF
```

## How it works

For each page, the engine:

1. Detects ruled **tables** with lattice analysis ([pdfplumber](https://github.com/jsvine/pdfplumber), MIT).
2. Detects **sidebars** as filled background rectangles containing text (outside any table).
3. Rebuilds visual **lines** from positioned words, finds the column gutter on two-column pages, and orders every element — paragraphs, tables, sidebars — into a single reading order.
4. Ranks **headings** by dominant font size, folds wrapped lines into paragraphs (repairing end-of-line hyphenation), and recognizes bullet/numbered lists.
5. Emits GitHub-flavoured Markdown. Nothing but page content is written.

Limitations (by design of a deterministic v1): scanned/image-only PDFs contain no text layer and produce no output (no OCR); borderless tables are treated as text; sidebar detection requires a filled background box.

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
