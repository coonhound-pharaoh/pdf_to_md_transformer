# Using this tool from an AI agent

`pdf-to-md-transformer` converts PDFs to Markdown **offline and
deterministically** — no network, no randomness, no model inference (except the
deterministic Tesseract OCR engine on scanned pages). PDF metadata is never
copied into the output; only page content is.

Two ways to drive it: the **MCP server** (preferred for agents that support
MCP) and the **CLI** (works anywhere a shell is available).

## Setup

```bash
pip install .
```

## MCP server

Command: `pdf2md-mcp` (JSON-RPC 2.0 over stdio, one JSON object per line).

Claude Code:

```bash
claude mcp add pdf2md -- pdf2md-mcp
```

Any client with an `mcpServers` config block (Claude Desktop, Codex, …):

```json
{ "mcpServers": { "pdf2md": { "command": "pdf2md-mcp" } } }
```

### Tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `convert_pdf` | `path` (required), `max_chars` (default 200000) | the Markdown as text, truncated with an HTML comment if over the limit |
| `convert_file` | `path` (required), `out_path` *or* `outdir` | JSON `{output, bytes}` — the written `.md` path |
| `pdf_info` | `path` (required) | JSON `{pages, pages_needing_ocr, ocr_available}` |

Tool failures come back as a normal result with `isError: true` and the error
message as text, so a failed conversion never kills the session.

## CLI

```bash
pdf2md paper.pdf                  # -> paper.md next to the PDF
pdf2md paper.pdf --stdout         # Markdown on stdout, nothing written
pdf2md *.pdf -o out/ --json       # JSON report on stdout, logs on stderr
pdf2md paper.pdf -o out/ --quiet  # no per-file progress lines
```

- `--stdout` and `--json` are mutually exclusive.
- In `--json` and `--stdout` modes, stdout carries **only** the machine-readable
  payload; progress and errors go to stderr.
- Exit code `0` if every file converted, `1` if any failed.

`--json` report shape:

```json
{
  "version": "1.1.0",
  "converted": 2,
  "failed": 1,
  "results": [
    {"input": "a.pdf", "ok": true,  "output": "out/a.md", "error": null},
    {"input": "b.pdf", "ok": false, "output": null, "error": "not found"}
  ]
}
```

## Python API

```python
from pdf_to_md import convert_pdf_to_markdown, convert_file

md   = convert_pdf_to_markdown("paper.pdf")          # str
path = convert_file("paper.pdf", "out/paper.md")     # writes, returns path
```

Both accept `progress=lambda done, total: ...`.

## Guidance for agents

- Call `pdf_info` first on an unknown PDF. If `pages_needing_ocr` is non-empty
  and `ocr_available` is `false`, those pages are skipped and replaced by an
  explanatory HTML comment — tell the user rather than reporting a clean
  conversion. Install Tesseract (`brew install tesseract`, `apt install
  tesseract-ocr`) or set `PDF2MD_TESSERACT` to a custom binary path.
- Prefer `convert_file` / `pdf2md -o` over pulling a long document into
  context; read back only the part you need.
- OCR'd pages carry a `<!-- page N: … converted with OCR … -->` marker. Numbers
  on those pages should be spot-checked against the source before being relied
  on.
- Equations come through garbled and figures are omitted (captions survive).
  Don't present either as faithful.
- Output is byte-identical across runs for the same input and version, so
  re-running to "get a better result" is pointless.
