#!/usr/bin/env python3
"""
MNA Stage 4 — Rebuild Book

PURPOSE
- Deterministically rebuild the Stage 4 reviewed-trunk layer for a book.
- Re-apply all review batches.
- Audit coverage.
- Export Spanish reviewed trunk markdown.

This is intentionally limited to Stage 4.
It does NOT yet rebuild:
- tokenization
- alignment
- predicate completeness
- suggested trunk generation
- ROOTS exports

Goal:
    python3 scripts/stage4/rebuild_stage4_book.py 1corintios
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def run_step(title: str, cmd: list[str], cwd: Path, dry_run: bool) -> int:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)
    print("$ " + " ".join(cmd))

    if dry_run:
        return 0

    completed = subprocess.run(cmd, cwd=str(cwd))
    return completed.returncode


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the Stage 4 reviewed-trunk layer for a book.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them")
    parser.add_argument("--force", action="store_true", help="Force apply review batches")
    parser.add_argument("--raw-notes", action="store_true", help="Export raw canonical notes instead of Spanish presentation notes")
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()

        apply_all_script = root / "scripts" / "stage4" / "apply_all_review_batches.py"
        audit_script = root / "scripts" / "stage4" / "audit_suggested_trunk_review_coverage.py"
        export_script = root / "scripts" / "stage4" / "export_reviewed_trunk_markdown.py"

        print("MNA Stage 4 — Rebuild Book")
        print(f"BOOK: {book}")
        print(f"ROOT: {root}")

        apply_cmd = [
            sys.executable,
            str(apply_all_script.relative_to(root)),
            book,
        ]
        if args.force:
            apply_cmd.append("--force")

        code = run_step(
            "STEP 1 — APPLY ALL REVIEW BATCHES",
            apply_cmd,
            root,
            args.dry_run,
        )
        if code != 0:
            return code

        audit_cmd = [
            sys.executable,
            str(audit_script.relative_to(root)),
            book,
        ]

        code = run_step(
            "STEP 2 — AUDIT REVIEW COVERAGE",
            audit_cmd,
            root,
            args.dry_run,
        )
        if code != 0:
            return code

        export_cmd = [
            sys.executable,
            str(export_script.relative_to(root)),
            book,
        ]
        if args.raw_notes:
            export_cmd.append("--raw-notes")

        code = run_step(
            "STEP 3 — EXPORT SPANISH REVIEWED TRUNK MARKDOWN",
            export_cmd,
            root,
            args.dry_run,
        )
        if code != 0:
            return code

        print()
        print("=" * 72)
        print("MNA STAGE 4 REBUILD COMPLETE")
        print("=" * 72)
        print(f"BOOK: {book}")
        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("MNA Stage 4 rebuild FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
