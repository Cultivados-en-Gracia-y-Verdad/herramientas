#!/usr/bin/env python3
"""Export Greek NT interlinear (markdown tables + compact .txt)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Export NT interlinear reader + txt files.")
    parser.add_argument("book", nargs="?", help="book slug (e.g. mateo)")
    parser.add_argument("--all", action="store_true", help="export all 27 NT books")
    parser.add_argument(
        "--format",
        choices=("reader", "txt", "both"),
        default="both",
        help="output format (default: both)",
    )
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="one .reader.md per book (reader format only)",
    )
    parser.add_argument(
        "--to-mna",
        action="store_true",
        help="also write compact .txt into MNA/datasets/interlinear/NT/",
    )
    args, extra = parser.parse_known_args()

    book_args = ["--all"] if args.all else ([args.book] if args.book else [])
    if not book_args:
        parser.error("provide a book slug or --all")

    cmds: list[list[str]] = []
    if args.format in ("reader", "both"):
        cmd = [sys.executable, str(SCRIPTS / "tokens_to_reader.py"), *book_args]
        if args.single_file:
            cmd.append("--single-file")
        cmds.append(cmd)
    if args.format in ("txt", "both"):
        cmd = [sys.executable, str(SCRIPTS / "tokens_to_interlinear_txt.py"), *book_args]
        if args.to_mna:
            cmd.append("--to-mna")
        cmds.append(cmd)

    for cmd in cmds:
        result = subprocess.run(cmd + extra, cwd=ROOT)
        if result.returncode != 0:
            return result.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
