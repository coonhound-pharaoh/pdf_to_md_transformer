"""Command-line interface: pdf2md input.pdf [input2.pdf ...] [-o OUTDIR]"""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .engine import convert_file


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
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    failures = 0
    for pdf in args.pdfs:
        if not os.path.isfile(pdf):
            print(f"ERROR: not found: {pdf}", file=sys.stderr)
            failures += 1
            continue
        base = os.path.splitext(os.path.basename(pdf))[0] + ".md"
        outdir = args.outdir or os.path.dirname(os.path.abspath(pdf))
        os.makedirs(outdir, exist_ok=True)
        out = os.path.join(outdir, base)
        try:
            convert_file(pdf, out)
            print(f"OK  {pdf} -> {out}")
        except Exception as exc:  # surface, keep batch going
            print(f"ERROR converting {pdf}: {exc}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
