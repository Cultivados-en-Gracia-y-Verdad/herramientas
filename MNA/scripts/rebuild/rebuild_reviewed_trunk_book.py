#!/usr/bin/env python3
"""
MNA Rebuild — Reviewed Trunk Book

Purpose:
Recreate the reviewed-trunk layer that already works for a book such as 1corintios.

This is intentionally focused. It does not rebuild tokenization, alignments, or earlier datasets.
It assumes these already exist:
- datasets/suggested-trunk/<book>.jsonl
- datasets/review-batches/<book>-*.jsonl

It rebuilds:
1. Applies all review batches in order.
2. Audits reviewed-trunk coverage.
3. Exports Spanish reviewed-trunk Markdown.

Usage:
    python3 scripts/rebuild/rebuild_reviewed_trunk_book.py 1corintios
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def run(title: str, cmd: list[str], cwd: Path) -> int:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)
    print("$ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd)).returncode


def require(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required {label}: {path}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the existing reviewed-trunk layer for a book.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--force", action="store_true", help="Force review batch application")
    parser.add_argument("--raw-notes", action="store_true", help="Export raw canonical notes instead of Spanish notes")
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()

        suggested = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"
        review_batches_dir = root / "datasets" / "review-batches"
        review_batches = sorted(review_batches_dir.glob(f"{book}-*.jsonl"))

        require(suggested, "suggested trunk dataset")
        require(review_batches_dir, "review batch directory")
        if not review_batches:
            raise FileNotFoundError(f"No review batches found for {book} in {review_batches_dir}")

        print("MNA Rebuild — Reviewed Trunk Book")
        print(f"BOOK: {book}")
        print(f"ROOT: {root}")
        print(f"SUGGESTED TRUNK: {suggested}")
        print(f"REVIEW BATCHES: {len(review_batches)}")

        apply_cmd = [
            sys.executable,
            "scripts/stage4/apply_all_review_batches.py",
            book,
        ]
        if args.force:
            apply_cmd.append("--force")

        code = run("STEP 1 — APPLY REVIEW BATCHES", apply_cmd, root)
        if code != 0:
            return code

        audit_cmd = [
            sys.executable,
            "scripts/stage4/audit_suggested_trunk_review_coverage.py",
            book,
            "--show-unreviewed",
            "--show-gaps",
        ]
        code = run("STEP 2 — AUDIT REVIEWED COVERAGE", audit_cmd, root)
        if code != 0:
            return code

        export_cmd = [
            sys.executable,
            "scripts/stage4/export_reviewed_trunk_markdown.py",
            book,
        ]
        if args.raw_notes:
            export_cmd.append("--raw-notes")

        code = run("STEP 3 — EXPORT SPANISH REVIEWED TRUNK", export_cmd, root)
        if code != 0:
            return code

        output = root / "exports" / "reviewed-trunk" / f"{book}.md"
        print()
        print("MNA Rebuild — Reviewed Trunk Book Complete")
        print(f"OUTPUT: {output}")
        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("MNA reviewed-trunk rebuild FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
