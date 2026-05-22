#!/usr/bin/env python3
"""
MNA Stage 4 — Export Review Batch Candidate

Purpose:
Convert promoted suggested-trunk rows into review-ready candidate rows.

This script does NOT create reviewed trunk rows.
It only creates review material that a human can inspect and copy/edit into
`datasets/review-batches/` when genuinely reviewed.

Input:
    datasets/suggested-trunk/<book>.jsonl

Output:
    datasets/review-batch-candidates/<book>-batch-01.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

PROMOTABLE_STATUS = "AI_REVIEWED"
CANDIDATE_STATUS = "REVIEW_CANDIDATE_ONLY"
REVIEW_RESULT = "UNREVIEWED"


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if obj.get("record_type") != "metadata":
                yield obj


def ref_key(row: dict) -> tuple[int, int, str]:
    return (
        int(row.get("chapter", 0)),
        int(row.get("verse", 0)),
        str(row.get("predicate_anchor_id") or row.get("reference") or ""),
    )


def export_row(row: dict) -> dict:
    return {
        "reference": row.get("reference"),
        "review_result": REVIEW_RESULT,
        "status": CANDIDATE_STATUS,
        "confidence": row.get("confidence"),
        "trunk_greek": row.get("trunk_greek"),
        "notes": "Exported from promoted suggested-trunk AI_REVIEWED row. Human review still required before use as a review batch.",
        "manual_use": False,
        "reviewer": None,
        "source_status": row.get("status"),
        "source_trunk_claim": row.get("trunk_claim"),
        "source_predicate_anchor_id": row.get("predicate_anchor_id"),
        "source_promotion_guard_reasons": row.get("promotion_guard_reasons", []),
        "candidate_policy": "REVIEW_MATERIAL_ONLY_NOT_REVIEWED",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export review-batch candidates from promoted suggested-trunk rows.")
    parser.add_argument("book", help="Book slug, e.g. filipenses")
    parser.add_argument("--batch", default="01", help="Batch suffix, default: 01")
    parser.add_argument("--include-needs-review", action="store_true", help="Include guarded NEEDS_EXTERNAL_GREEK_REVIEW rows as candidates too")
    args = parser.parse_args(argv)

    root = mna_root_from_script()
    book = args.book.strip().lower()
    source_path = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"
    output_path = root / "datasets" / "review-batch-candidates" / f"{book}-batch-{args.batch}.jsonl"

    if not source_path.is_file():
        raise FileNotFoundError(f"Suggested trunk dataset not found: {source_path}")

    rows = []
    skipped = 0

    for row in load_jsonl(source_path):
        status = row.get("status")
        if status != PROMOTABLE_STATUS and not args.include_needs_review:
            skipped += 1
            continue
        rows.append(row)

    rows = sorted(rows, key=ref_key)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(export_row(row), ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 4 — Review Batch Candidate Export")
    print(f"BOOK: {book}")
    print(f"SOURCE: {source_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS EXPORTED: {len(rows)}")
    print(f"ROWS SKIPPED: {skipped}")
    print("POLICY: REVIEW MATERIAL ONLY — NOT A REVIEW BATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
