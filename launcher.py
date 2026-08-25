"""PyInstaller entry point: GUI by default, CLI when arguments are given."""

import sys

sys.path.insert(0, "src")

if len(sys.argv) > 1:
    from pdf_to_md.cli import main
else:
    from pdf_to_md.gui import main

raise SystemExit(main())
