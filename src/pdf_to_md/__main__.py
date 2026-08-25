"""`python -m pdf_to_md` launches the GUI; pass args to use the CLI."""

import sys

if len(sys.argv) > 1:
    from .cli import main
else:
    from .gui import main

raise SystemExit(main())
