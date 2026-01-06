from __future__ import annotations

"""Compatibility entrypoint.

The *implementation* of the interactive CLI lives in `var.apps.platform.cli`.
We keep this module as a thin wrapper so `python -m var.cli` and the
`var` console script keep working.
"""

from .apps.platform.cli import main


if __name__ == "__main__":
    main()
