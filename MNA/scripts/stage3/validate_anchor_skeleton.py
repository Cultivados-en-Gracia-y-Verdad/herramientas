#!/usr/bin/env python3
"""
MNA Stage 3 validator — anchor skeleton only.

PURPOSE
- Validate Stage 3 anchor skeleton datasets.
- Verify ordered inheritance from predicate anchors.
- Verify Stage 3 remains free of trunk-only markers.

ABSOLUTE LIMITS
This validator does NOT validate:
- independent clauses,
- dependent clauses,
- real trunk,
- [S],
- [M],
- connectors,
- labels,
- patterns,
- units,
- titles,
- semantic structure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage3-anchor-skeleton-validator-v2"


def load_jsonl(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    metadata = None
    records = []

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
                if metadata is not None:
                    raise ValueError("Multiple metadata rows found.")
                metadata = obj
            else:
                records.append(obj)

    if metadata is None:
        raise ValueError("Missing metadata row.")

    return metadata, records


def validate(book: str, anchor_path: Path, skeleton_path: Path) -> dict[str, object]:
    anchor_metadata, anchor_records = load_jsonl(anchor_path)
    skeleton_metadata, skeleton_records = load_jsonl(skeleton_path)

    if anchor_metadata.get("book") != book:
        raise ValueError("Predicate-anchor dataset book mismatch.")

    if skeleton_metadata.get("book") != book:
        raise ValueError("Anchor-skeleton dataset book mismatch.")

    predicate_anchors = [r for r in anchor_records if r.get("record_type") == "predicate_anchor"]
    skeleton_rows = [r for r in skeleton_records if r.get("record_type") == "anchor_skeleton_row"]

    anchor_count = len(predicate_anchors)
    skeleton_count = len(skeleton_rows)

    duplicate_anchor_ids = 0
    ordering_errors = 0
    trunk_claim_errors = 0
    subject_marker_errors = 0
    movement_marker_errors = 0
    connector_data_errors = 0
    label_data_errors = 0
    unit_data_errors = 0
    title_data_errors = 0
    inheritance_errors = 0

    expected_anchor_ids = [str(row["predicate_anchor_id"]) for row in predicate_anchors]
    actual_anchor_ids = []

    seen_ids = set()
    previous_anchor_order = 0

    for row in skeleton_rows:
        anchor_id = str(row.get("predicate_anchor_id"))
        actual_anchor_ids.append(anchor_id)

        if anchor_id in seen_ids:
            duplicate_anchor_ids += 1
        seen_ids.add(anchor_id)

        anchor_order = int(row.get("anchor_order", 0))
        if anchor_order <= previous_anchor_order:
            ordering_errors += 1
        previous_anchor_order = anchor_order

        if row.get("trunk_claim") != "NONE":
            trunk_claim_errors += 1

        if row.get("subject_change_marker") != "NOT_APPLICABLE_BEFORE_TRUNK":
            subject_marker_errors += 1

        if row.get("movement_marker") != "NOT_APPLICABLE_BEFORE_TRUNK":
            movement_marker_errors += 1

        if row.get("connector_data") != "NONE":
            connector_data_errors += 1

        if row.get("label_data") != "NONE":
            label_data_errors += 1

        if row.get("unit_data") != "NONE":
            unit_data_errors += 1

        if row.get("title_data") != "NONE":
            title_data_errors += 1

    if expected_anchor_ids != actual_anchor_ids:
        inheritance_errors += 1

    status = "PASS"

    failure_values = [
        anchor_count != skeleton_count,
        duplicate_anchor_ids,
        ordering_errors,
        trunk_claim_errors,
        subject_marker_errors,
        movement_marker_errors,
        connector_data_errors,
        label_data_errors,
        unit_data_errors,
        title_data_errors,
        inheritance_errors,
    ]

    if any(failure_values):
        status = "FAIL"

    return {
        "predicate_anchors": anchor_count,
        "anchor_skeleton_rows": skeleton_count,
        "duplicate_anchor_ids": duplicate_anchor_ids,
        "ordering_errors": ordering_errors,
        "trunk_claim_errors": trunk_claim_errors,
        "subject_marker_errors": subject_marker_errors,
        "movement_marker_errors": movement_marker_errors,
        "connector_data_errors": connector_data_errors,
        "label_data_errors": label_data_errors,
        "unit_data_errors": unit_data_errors,
        "title_data_errors": title_data_errors,
        "inheritance_errors": inheritance_errors,
        "status": status,
    }


def print_visible_output(book: str, anchor_path: Path, skeleton_path: Path, result: dict[str, object]) -> None:
    print("MNA Stage 3 Validation — Anchor Skeleton Only")
    print(f"BOOK: {book}")
    print(f"ANCHOR DATASET: {anchor_path}")
    print(f"ANCHOR SKELETON DATASET: {skeleton_path}")
    print(f"PREDICATE_ANCHORS: {result['predicate_anchors']}")
    print(f"ANCHOR_SKELETON_ROWS: {result['anchor_skeleton_rows']}")
    print(f"DUPLICATE_ANCHOR_IDS: {result['duplicate_anchor_ids']}")
    print(f"ORDERING_ERRORS: {result['ordering_errors']}")
    print(f"TRUNK_CLAIM_ERRORS: {result['trunk_claim_errors']}")
    print(f"SUBJECT_MARKER_ERRORS: {result['subject_marker_errors']}")
    print(f"MOVEMENT_MARKER_ERRORS: {result['movement_marker_errors']}")
    print(f"CONNECTOR_DATA_ERRORS: {result['connector_data_errors']}")
    print(f"LABEL_DATA_ERRORS: {result['label_data_errors']}")
    print(f"UNIT_DATA_ERRORS: {result['unit_data_errors']}")
    print(f"TITLE_DATA_ERRORS: {result['title_data_errors']}")
    print(f"INHERITANCE_ERRORS: {result['inheritance_errors']}")
    print(f"STATUS: {result['status']}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Stage 3 anchor skeleton datasets.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--anchors", help="Explicit predicate-anchor JSONL path")
    parser.add_argument("--skeleton", help="Explicit anchor-skeleton JSONL path")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = Path(__file__).resolve().parents[2]

        anchor_path = Path(args.anchors) if args.anchors else root / "datasets" / "predicate-anchors" / f"{book}.jsonl"
        skeleton_path = Path(args.skeleton) if args.skeleton else root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"

        if not anchor_path.is_absolute():
            anchor_path = (Path.cwd() / anchor_path).resolve()

        if not skeleton_path.is_absolute():
            skeleton_path = (Path.cwd() / skeleton_path).resolve()

        result = validate(book, anchor_path, skeleton_path)
        print_visible_output(book, anchor_path, skeleton_path, result)
        return 0 if result["status"] == "PASS" else 2
    except Exception as exc:
        print("MNA Stage 3 Anchor Skeleton Validation FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
