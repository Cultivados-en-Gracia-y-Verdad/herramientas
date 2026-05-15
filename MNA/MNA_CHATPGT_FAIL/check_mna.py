#!/usr/bin/env python3
"""
Run the standard MNA cleanup + validation workflow.

Usage:
  python3 MNA/check_mna.py MNA/data/output/mna-1cor-1-2.md
  python3 MNA/check_mna.py MNA/data/output/mna-1cor-1-2.md --write --verbose
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_step(args: list[str]) -> int:
    print("$ " + " ".join(args), flush=True)
    return subprocess.run(args).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean and validate an MNA Markdown file.")
    parser.add_argument("path", type=Path, help="Path to MNA Markdown file")
    parser.add_argument("--write", action="store_true", help="Remove redundant Extra lines before validating")
    parser.add_argument("--verbose", action="store_true", help="Print per-verse pass summaries")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    cleaner = script_dir / "clean_mna_extras.py"
    validator = script_dir / "validate_mna.py"

    clean_cmd = [sys.executable, str(cleaner), str(args.path)]
    if args.write:
        clean_cmd.append("--write")

    clean_status = run_step(clean_cmd)
    if clean_status != 0:
        return clean_status

    validate_cmd = [sys.executable, str(validator), str(args.path)]
    if args.verbose:
        validate_cmd.append("--verbose")

    return run_step(validate_cmd)


if __name__ == "__main__":
    raise SystemExit(main())
