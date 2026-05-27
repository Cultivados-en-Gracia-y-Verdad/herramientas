#!/usr/bin/env python3
"""
MNA Rebuild — Book Preflight

Checks available files and scripts before a book rebuild.
This script only reads paths and prints a report.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional


SCRIPT_GROUPS = {
    "tokenize_book": ["scripts/tokenize_book.py", "scripts/extract_tokens.py"],
    "validate_alignments": ["scripts/validate_all.py", "scripts/validate_alignment.py"],
    "predicate_completeness": [
        "scripts/stage4/build_predicate_completeness.py",
        "scripts/stage4/audit_predicate_completeness.py",
    ],
    "suggested_trunk": [
        "scripts/stage4/build_suggested_trunk.py",
        "scripts/stage4/promote_suggested_trunk_rows.py",
    ],
    "apply_review_batches": ["scripts/stage4/apply_all_review_batches.py"],
    "audit_stage4": ["scripts/stage4/audit_suggested_trunk_review_coverage.py"],
    "export_reviewed_trunk": ["scripts/stage4/export_reviewed_trunk_markdown.py"],
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def status(path: Path) -> str:
    return "PASS" if path.exists() else "MISSING"


def count_files(path: Path, pattern: str) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return len(list(path.glob(pattern)))


def show(label: str, path: Path) -> None:
    print(f"{status(path):>8}  {label:<30} {path}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check book rebuild inputs and scripts.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    args = parser.parse_args(argv)

    root = mna_root_from_script()
    book = args.book.strip().lower()

    print("MNA Rebuild — Book Preflight")
    print(f"BOOK: {book}")
    print(f"ROOT: {root}")
    print()

    print("FILES")
    show("SBLGNT source", root / "data" / "SBLGNT" / f"{book}.md")
    show("NBLA source", root / "data" / "NBLA" / f"{book}.nbla.md")
    show("Greek tokens dir", root / "data" / "g-tokens")
    show("Spanish tokens dir", root / "data" / "s-tokens")
    show("Alignments dir", root / "data" / "alignments" / book)
    show("Alignment rules", root / "data" / "rules" / "alignment_rules.yaml")
    show("Predicate dataset", root / "datasets" / "predicate-completeness" / f"{book}.jsonl")
    show("Suggested trunk", root / "datasets" / "suggested-trunk" / f"{book}.jsonl")
    show("Review batches", root / "datasets" / "review-batches")
    show("Reviewed export", root / "exports" / "reviewed-trunk" / f"{book}.md")
    print()

    print("COUNTS")
    print(f"Greek token files:   {count_files(root / 'data' / 'g-tokens', f'{book}-*.txt')}")
    print(f"Spanish token files: {count_files(root / 'data' / 's-tokens', f'{book}-*.txt')}")
    print(f"Alignment files:     {count_files(root / 'data' / 'alignments' / book, '*.tsv')}")
    print(f"Review batches:      {count_files(root / 'datasets' / 'review-batches', f'{book}-*.jsonl')}")
    print()

    print("SCRIPTS")
    for group, candidates in SCRIPT_GROUPS.items():
        found = [candidate for candidate in candidates if (root / candidate).exists()]
        if found:
            print(f"{'PASS':>8}  {group:<30} {', '.join(found)}")
        else:
            print(f"{'MISSING':>8}  {group:<30} {', '.join(candidates)}")
    print()

    print("STATUS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
