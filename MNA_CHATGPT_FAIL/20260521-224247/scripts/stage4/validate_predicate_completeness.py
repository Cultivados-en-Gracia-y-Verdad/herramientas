#!/usr/bin/env python3
"""
MNA Stage 4 Validator — Predicate Completeness.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

VALID_CLASSIFICATIONS = {
    "INDEPENDENT",
    "DEPENDENT",
    "UNCERTAIN",
}


def load_jsonl(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    metadata = None
    rows = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()

            if not stripped:
                continue

            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_number}: {exc}"
                ) from exc

            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)

    if metadata is None:
        raise ValueError(f"Metadata row missing: {path}")

    return metadata, rows


def validate(book: str, skeleton_path: Path, completeness_path: Path):
    skeleton_metadata, skeleton_rows = load_jsonl(skeleton_path)
    completeness_metadata, completeness_rows = load_jsonl(completeness_path)

    expected_ids = [
        row["predicate_anchor_id"]
        for row in skeleton_rows
    ]

    actual_ids = []

    duplicate_anchor_ids = 0
    ordering_errors = 0
    invalid_classifications = 0
    connector_dependency_errors = 0
    trunk_claim_errors = 0
    subject_marker_claim_errors = 0
    movement_marker_claim_errors = 0

    seen_ids = set()
    previous_order = 0

    for row in completeness_rows:
        anchor_id = row["predicate_anchor_id"]
        actual_ids.append(anchor_id)

        if anchor_id in seen_ids:
            duplicate_anchor_ids += 1

        seen_ids.add(anchor_id)

        order = row["anchor_order"]

        if order <= previous_order:
            ordering_errors += 1

        previous_order = order

        classification = row["predicate_completeness_status"]

        if classification not in VALID_CLASSIFICATIONS:
            invalid_classifications += 1

        if row["connector_dependency_used"] != "NO":
            connector_dependency_errors += 1

        if row["trunk_claim"] != "NONE":
            trunk_claim_errors += 1

        if row["subject_marker_claim"] != "NONE":
            subject_marker_claim_errors += 1

        if row["movement_marker_claim"] != "NONE":
            movement_marker_claim_errors += 1

    inheritance_errors = 0

    if expected_ids != actual_ids:
        inheritance_errors = 1

    status = "PASS"

    if any([
        duplicate_anchor_ids,
        ordering_errors,
        invalid_classifications,
        connector_dependency_errors,
        trunk_claim_errors,
        subject_marker_claim_errors,
        movement_marker_claim_errors,
        inheritance_errors,
    ]):
        status = "FAIL"

    return {
        "rows": len(completeness_rows),
        "duplicate_anchor_ids": duplicate_anchor_ids,
        "ordering_errors": ordering_errors,
        "invalid_classifications": invalid_classifications,
        "connector_dependency_errors": connector_dependency_errors,
        "trunk_claim_errors": trunk_claim_errors,
        "subject_marker_claim_errors": subject_marker_claim_errors,
        "movement_marker_claim_errors": movement_marker_claim_errors,
        "inheritance_errors": inheritance_errors,
        "status": status,
    }


def print_visible_output(book, skeleton_path, completeness_path, result):
    print("MNA Stage 4 Validation — Predicate Completeness")
    print(f"BOOK: {book}")
    print(f"SKELETON DATASET: {skeleton_path}")
    print(f"PREDICATE COMPLETENESS DATASET: {completeness_path}")

    for key, value in result.items():
        print(f"{key.upper()}: {value}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Stage 4 predicate completeness dataset."
    )

    parser.add_argument("book")

    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = Path(__file__).resolve().parents[2]

        skeleton_path = (
            root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"
        )

        completeness_path = (
            root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
        )

        result = validate(
            book,
            skeleton_path,
            completeness_path,
        )

        print_visible_output(
            book,
            skeleton_path,
            completeness_path,
            result,
        )

        return 0 if result["status"] == "PASS" else 2

    except Exception as exc:
        print("MNA Stage 4 Validation FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
