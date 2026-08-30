"""Command-line interface: pdf2md input.pdf [input2.pdf ...] [-o OUTDIR]

Designed to be driven either by a human or by an AI agent:

  pdf2md paper.pdf                 write paper.md next to the PDF
  pdf2md paper.pdf --stdout        write the Markdown to stdout instead
  pdf2md *.pdf -o out --json       machine-readable result report on stdout

In ``--json`` mode nothing but a single JSON object is written to stdout,
so the output can be parsed directly; human progress lines go to stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .engine import convert_file, convert_pdf_to_markdown


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="pdf2md",
        description="Deterministically convert PDF files to Markdown "
                    "(content only -- metadata is stripped; sidebars and "
                    "tables are placed inline).",
    )
    ap.add_argument("pdfs", nargs="+", help="PDF file(s) to convert")
    ap.add_argument("-o", "--outdir", default=None,
                    help="output directory (default: alongside each PDF)")
    ap.add_argument("--stdout", action="store_true",
                    help="write Markdown to stdout instead of to .md files")
    ap.add_argument("--extract-images", action="store_true",
                    help="write figures as PNGs into <name>_assets/ next to "
                         "the Markdown and link them (ignored with --stdout)")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="print a JSON report of the conversion to stdout")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="suppress per-file progress lines")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    if args.stdout and args.as_json:
        ap.error("--stdout and --json are mutually exclusive")

    # In --json mode stdout carries only the report.
    log = sys.stderr if (args.as_json or args.stdout) else sys.stdout

    results = []
    failures = 0
    for pdf in args.pdfs:
        entry = {"input": pdf, "ok": False, "output": None, "error": None}
        if not os.path.isfile(pdf):
            entry["error"] = "not found"
            results.append(entry)
            print(f"ERROR: not found: {pdf}", file=sys.stderr)
            failures += 1
            continue
        try:
            if args.stdout:
                sys.stdout.write(convert_pdf_to_markdown(pdf))
                entry["ok"] = True
            else:
                base = os.path.splitext(os.path.basename(pdf))[0] + ".md"
                outdir = args.outdir or os.path.dirname(os.path.abspath(pdf))
                os.makedirs(outdir, exist_ok=True)
                out = os.path.join(outdir, base)
                convert_file(pdf, out,
                             extract_images=args.extract_images)
                entry.update(ok=True, output=out)
                if not args.quiet:
                    print(f"OK  {pdf} -> {out}", file=log)
        except Exception as exc:  # surface, keep batch going
            entry["error"] = f"{type(exc).__name__}: {exc}"
            print(f"ERROR converting {pdf}: {exc}", file=sys.stderr)
            failures += 1
        results.append(entry)

    if args.as_json:
        json.dump({"version": __version__,
                   "converted": len(results) - failures,
                   "failed": failures,
                   "results": results}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
