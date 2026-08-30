# Changelog

All notable changes to this project are documented here. The project follows
[semantic versioning](https://semver.org/): the Python API is stable within a
major version, while the *Markdown output* for a given PDF may change between
minor versions as the converter learns to represent more of the page.

## [1.2.0] — 2026-08-30

Conversion now covers the parts of a page it previously dropped, and marks the
parts it cannot vouch for. Every addition follows the same rule as the existing
table detector: where the layout is not understood, fall back to the previous
behaviour rather than guess.

### Added

**Drivable by an AI agent.** New `pdf2md-mcp` command speaks the Model Context
Protocol over stdio (JSON-RPC 2.0, no third-party dependencies), exposing
`convert_pdf`, `convert_file` and `pdf_info`. The CLI gained `--stdout` and
`--json` machine-readable modes, in which stdout carries only the payload and
logs go to stderr. [AGENTS.md](AGENTS.md) documents both surfaces, and a bundled
skill lives in `.claude/skills/pdf-to-markdown/`.

**Figures.** Embedded images and clusters of vector artwork are detected,
anchored in reading order, and bound to their caption (`Figure 3: …`, above or
below). In-figure labels no longer leak into the prose. `--extract-images`
writes each figure as a PNG into `<name>_assets/` and links it; without it a
figure is marked with an HTML comment and its caption is kept in place.

**Equations.** Display equations are detected by mathematical fonts and glyphs,
or by the geometry of a fraction rule, and rebuilt as LaTeX from the positions
of their glyphs — fractions from the rule, super/subscripts from baseline
offsets, sums and integrals with their limits, radicals from the overline. The
result is emitted as a `$$` block labelled as reconstructed. Where anything is
uncertain the parser refuses and the equation is preserved verbatim in an
` ```equation ` block instead. `--no-math-latex` disables reconstruction.

**Callouts.** Sidebars are now recognised as ruled boxes (a stroked rectangle or
four separate lines) and as unboxed pull quotes — inset from both sides,
separated above and below, and set in a different size or face — as well as the
shaded panels supported before.

**OCR provenance and number checking.** Every OCR'd page records the engine
version, page-segmentation mode, dpi and language. Numeric tokens are checked
against Tesseract's confidence *and* against a second read of the same pixels
restricted to digits; doubtful ones are listed per page so verifying a scan
means checking a handful of marked numbers rather than the whole page. New
`--ocr-lang`, `--ocr-dpi`, `--ocr-psm` and `--no-verify-numbers` options.

### Changed

- Markdown output changes for documents containing figures, display equations or
  ruled/unboxed callouts: material that was previously dropped or flattened now
  appears, marked. Documents without those features convert as before.
- The OCR page marker text changed to carry provenance.

### Notes

- Conversion remains offline, deterministic and metadata-free.
- Equation reconstruction is inference from layout and should be checked against
  the source; the comment above each block says whether it was reconstructed or
  left verbatim.
- Fonts with no ToUnicode CMap other than Adobe `Symbol` cannot be decoded, so
  equations set in them are always emitted verbatim.
- Inline maths inside a paragraph is still not detected.

## [1.1.0]

Scientific-paper support: borderless (booktabs) tables and OCR for scanned
pages.

## [1.0.0]

Initial release: deterministic offline PDF-to-Markdown conversion with ruled
tables, shaded sidebars, two-column reflow and heading ranking.
