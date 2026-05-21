#!/usr/bin/env python3
"""
MNA Stage 4 — Accept Review Batch Candidate

Purpose:
Convert review-batch-candidate rows into real review-batch rows ONLY after
explicit confirmation that review has occurred.

This script exists to protect the boundary:

    REVIEW_MATERIAL_ONLY_NOT_REVIEWED
    !=
    REVIEWED_FOR_MANUAL_USE

It refuses to write a review batch unless --confirm-reviewed is provided.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

CANDIDATE_STATUS = "REVIEW_CANDIDATE_ONLY"
CANDIDATE_POLICY = "REVIEW_MATERIAL_ONLY_NOT_REVIEWED"
REVIEWED_STATUS = "REVIEWED_FOR_MANUAL_USE"
REVIEW_RESULT = "GOOD"


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
            yield obj


def convert_row(row: dict, reviewer: str) -> dict:
    if row.get("status") != CANDIDATE_STATUS:
        raise ValueError(f"Refusing non-candidate row: {row.get('reference')} status={row.get('status')}")
    if row.get("candidate_policy") != CANDIDATE_POLICY:
        raise ValueError(f"Refusing row without candidate policy: {row.get('reference')}")

    return {
        "reference": row.get("reference"),
        "review_result": REVIEW_RESULT,
        "status": REVIEWED_STATUS,
        "confidence": row.get("confidence"),
        "trunk_greek": row.get("trunk_greek"),
        "notes": "Accepted from review-batch candidate after explicit review confirmation.",
        "manual_use": True,
        "reviewer": reviewer,
        "source_candidate_policy": row.get("candidate_policy"),
        "source_trunk_claim": row.get("source_trunk_claim"),
        "source_predicate_anchor_id": row.get("source_predicate_anchor_id"),
        "acceptance_policy": "EXPLICIT_CONFIRM_REVIEWED_REQUIRED",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Accept reviewed candidate rows into a Stage 4 review batch.")
    parser.add_argument("book", help="Book slug, e.g. filipenses")
    parser.add_argument("--batch", default="01", help="Batch suffix, default: 01")
    parser.add_argument("--reviewer", required=True, help="Name/label of the human reviewer")
    parser.add_argument("--confirm-reviewed", action="store_true", help="Required: confirms candidate rows have been reviewed")
    args = parser.parse_args(argv)

    if not args.confirm_reviewed:
        raise SystemExit(
            "REFUSED: pass --confirm-reviewed only after the candidate rows have genuinely been reviewed."
        )

    root = mna_root_from_script()
    book = args.book.strip().lower()
    candidate_path = root / "datasets" / "review-batch-candidates" / f"{book}-batch-{args.batch}.jsonl"
    output_path = root / "datasets" / "review-batches" / f"{book}-batch-{args.batch}.jsonl"

    if not candidate_path.is_file():
        raise FileNotFoundError(f"Review-batch candidate not found: {candidate_path}")

    rows = [convert_row(row, args.reviewer) for row in load_jsonl(candidate_path)]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 4 — Review Batch Accepted")
    print(f"BOOK: {book}")
    print(f"SOURCE: {candidate_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS ACCEPTED: {len(rows)}")
    print("POLICY: REVIEWED BATCH CREATED ONLY AFTER EXPLICIT CONFIRMATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
