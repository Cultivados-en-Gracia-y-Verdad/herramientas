#!/usr/bin/env python3
"""Convert a Windows e-Sword .bblx module to macOS .bbli (schema only; same verses)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from esword_lib import convert_bblx_to_bbli  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert .bblx → .bbli for e-Sword X.")
    parser.add_argument("source", type=Path, help="input .bblx file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output .bbli path (default: same name with .bbli extension)",
    )
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"error: not found: {args.source}", file=sys.stderr)
        return 1

    dest = args.output or args.source.with_suffix(".bbli")
    count = convert_bblx_to_bbli(args.source, dest)
    print(f"wrote {dest} ({count} verses)")
    print("Import in e-Sword X: File → Resources → Import…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
