from __future__ import annotations

"""Research harness entrypoint.

This is intentionally thin:
- the *real* research value is in `var.eval` + `var.research`.
- this script simply runs the deterministic suite and prints a quick summary.

Usage:
    python -m var.apps.research.run_bench
    python -m var.apps.research.run_bench --include-math
"""

import argparse
import json
from pathlib import Path

from ...eval.harness import run_eval_suite


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="VAR research harness")
    parser.add_argument(
        "--include-math",
        action="store_true",
        help="Also run arithmetic specs/scenarios (demonstrates multi-topic testbed).",
    )
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args(argv)

    results = run_eval_suite(include_math=bool(args.include_math))

    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)

    print("\n=== Eval summary ===")
    print(f"Scenarios: {total}")
    print(f"Passed:    {passed}")
    print(f"Failed:    {total - passed}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nWrote: {args.out}")


if __name__ == "__main__":
    main()
