#!/usr/bin/env python3
"""
MNA Stage 4 — Suggested Trunk Review Coverage Audit

PURPOSE
- Report coverage of datasets/suggested-trunk/<book>.jsonl.
- Count reviewed rows by chapter.
- Surface rows that are not reviewed for manual use.
- Surface likely gaps compared to predicate-completeness verse references.

This script does not change data.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    metadata = None
    rows = []

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc

            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)

    return metadata, rows


def ref_sort_key(reference: str) -> tuple[int, int]:
    try:
        _book, cv = reference.rsplit(" ", 1)
        chapter, verse = cv.split(":", 1)
        return int(chapter), int(verse)
    except Exception:
        return 0, 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit reviewed suggested trunk coverage.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--show-gaps", action="store_true", help="Print references with predicate rows but no suggested-trunk row")
    parser.add_argument("--show-unreviewed", action="store_true", help="Print suggested-trunk rows not marked reviewed_for_manual_use=true")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()

        accepted_path = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"
        predicate_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"

        _accepted_metadata, accepted_rows = load_jsonl(accepted_path)
        _predicate_metadata, predicate_rows = load_jsonl(predicate_path)

        accepted_refs = {str(row.get("reference")) for row in accepted_rows}
        predicate_refs = {str(row.get("reference")) for row in predicate_rows}

        status_counts = Counter(str(row.get("status")) for row in accepted_rows)
        confidence_counts = Counter(str(row.get("confidence")) for row in accepted_rows)
        chapter_counts = defaultdict(Counter)

        reviewed_rows = []
        unreviewed_rows = []

        for row in accepted_rows:
            chapter = str(row.get("chapter"))
            if row.get("reviewed_for_manual_use") is True:
                reviewed_rows.append(row)
                chapter_counts[chapter]["reviewed_for_manual_use"] += 1
            else:
                unreviewed_rows.append(row)
                chapter_counts[chapter]["not_reviewed_for_manual_use"] += 1
            chapter_counts[chapter]["total"] += 1

        gaps = sorted(predicate_refs - accepted_refs, key=ref_sort_key)

        print("MNA Stage 4 — Suggested Trunk Review Coverage Audit")
        print(f"BOOK: {book}")
        print(f"ACCEPTED DATASET: {accepted_path}")
        print(f"PREDICATE DATASET: {predicate_path}")
        print(f"ACCEPTED ROWS: {len(accepted_rows)}")
        print(f"REVIEWED FOR MANUAL USE: {len(reviewed_rows)}")
        print(f"NOT REVIEWED FOR MANUAL USE: {len(unreviewed_rows)}")
        print(f"PREDICATE VERSE REFS: {len(predicate_refs)}")
        print(f"PREDICATE REFS WITHOUT ACCEPTED ROW: {len(gaps)}")
        print()
        print("STATUS COUNTS:")
        for key, value in sorted(status_counts.items()):
            print(f"  - {key}: {value}")
        print()
        print("CONFIDENCE COUNTS:")
        for key, value in sorted(confidence_counts.items()):
            print(f"  - {key}: {value}")
        print()
        print("CHAPTER COUNTS:")
        for chapter in sorted(chapter_counts, key=lambda c: int(c) if c.isdigit() else 0):
            counts = chapter_counts[chapter]
            print(
                f"  - chapter {chapter}: total={counts['total']} "
                f"reviewed={counts['reviewed_for_manual_use']} "
                f"not_reviewed={counts['not_reviewed_for_manual_use']}"
            )

        if args.show_unreviewed:
            print()
            print("UNREVIEWED ROWS:")
            shown = 0
            for row in sorted(unreviewed_rows, key=lambda r: (int(r.get("chapter", 0)), int(r.get("verse", 0)))):
                shown += 1
                print(f"  - {row.get('reference')} | {row.get('status')} | {row.get('confidence')} | {row.get('trunk_greek')}")
                if shown >= args.limit:
                    break

        if args.show_gaps:
            print()
            print("PREDICATE REFS WITHOUT ACCEPTED ROW:")
            for idx, reference in enumerate(gaps[: args.limit], start=1):
                print(f"  {idx:>4}. {reference}")

        print()
        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("MNA Stage 4 suggested trunk review coverage audit FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
