---
name: pdf-to-markdown
description: Convert PDF files to clean Markdown offline and deterministically, with tables (ruled and borderless/booktabs) and sidebars placed inline and PDF metadata stripped. Use whenever the user wants a PDF turned into Markdown or text, wants a paper/report/scan extracted, asks what is in a PDF, or mentions pdf2md or pdf-to-md-transformer. Handles scanned PDFs via Tesseract OCR.
---

# PDF to Markdown

Converts PDFs to GitHub-flavoured Markdown with no network calls and no
randomness — the same file and version always produce byte-identical output.
Document metadata (Info dictionary, XMP, producer strings) is never emitted.

## Check the tool is installed

```bash
pdf2md --version || pip install /path/to/pdf_to_md_transformer
```

If the `pdf2md` MCP server is registered, use its `pdf_info`, `convert_pdf`,
and `convert_file` tools instead of the shell — same engine, same results.

## Workflow

1. **Inspect first** on an unfamiliar PDF:

   ```bash
   python3 -c "
   import json, pdfplumber
   from pdf_to_md.ocr import ocr_available, page_needs_ocr
   with pdfplumber.open('paper.pdf') as p:
       scanned = [i + 1 for i, pg in enumerate(p.pages) if page_needs_ocr(pg)]
   print(json.dumps({'pages_needing_ocr': scanned, 'ocr': ocr_available()}))"
   ```

   (Or the `pdf_info` MCP tool, which does exactly this.)

2. **Convert.** Write to a file unless the document is short:

   ```bash
   pdf2md paper.pdf -o out/ --json     # JSON report on stdout
   pdf2md paper.pdf --stdout           # Markdown on stdout (short docs)
   ```

   Batch: pass several paths; exit code is 1 if any file failed, and the
   per-file outcome is in the `--json` report.

3. **Read back** only the section you need (`grep`, `sed -n`) rather than
   pulling a whole book into context.

## Reporting results honestly

- Scanned pages with **no OCR engine available** are skipped and replaced by an
  explanatory HTML comment. Say so; don't report a clean conversion. Fix with
  `brew install tesseract` / `apt install tesseract-ocr`, or point
  `PDF2MD_TESSERACT` at a binary.
- OCR'd pages are marked `<!-- page N: … converted with OCR … -->`. Spot-check
  numbers on those pages against the source before relying on them.
- Equations come through garbled; figures are omitted (captions survive).
- Re-running never changes the output — if it is wrong, the input or the tool
  needs attention, not another attempt.

Full interface reference: [AGENTS.md](../../../AGENTS.md).
