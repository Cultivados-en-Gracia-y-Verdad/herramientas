#!/usr/bin/env python3
"""
MNA Stage 3 validator — trunk + [S] + [M].

PURPOSE
- Validate Stage 3 trunk datasets.
- Verify ordered inheritance from predicate anchors.
- Verify mechanical [S] and [M] marker consistency.

ABSOLUTE LIMITS
This validator does NOT validate:
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

VERSION = "stage3-validator-v1"



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



def validate(book: str, anchor_path: Path, trunk_path: Path) -> dict[str, object]:
    anchor_metadata, anchor_records = load_jsonl(anchor_path)
    trunk_metadata, trunk_records = load_jsonl(trunk_path)

    anchor_count = len([r for r in anchor_records if r.get("record_type") == "predicate_anchor"])
    trunk_count = len([r for r in trunk_records if r.get("record_type") == "trunk_row"])

    duplicate_anchor_ids = 0
    missing_subject_signature = 0
    missing_movement_signature = 0
    invalid_s_markers = 0
    invalid_m_markers = 0
    ordering_errors = 0

    seen_ids = set()
    previous_anchor_order = 0
    previous_subject = None
    previous_movement = None

    for row in trunk_records:
        if row.get("record_type") != "trunk_row":
            continue

        anchor_id = row.get("predicate_anchor_id")
        if anchor_id in seen_ids:
            duplicate_anchor_ids += 1
        seen_ids.add(anchor_id)

        if not row.get("subject_signature"):
            missing_subject_signature += 1

        if not row.get("movement_signature"):
            missing_movement_signature += 1

        anchor_order = int(row.get("anchor_order", 0))
        if anchor_order <= previous_anchor_order:
            ordering_errors += 1
        previous_anchor_order = anchor_order

        current_subject = row.get("subject_signature")
        current_movement = row.get("movement_signature")

        expected_s = ""
        expected_m = ""

        if previous_subject is not None and current_subject != previous_subject:
            expected_s = "[S]"

        if previous_movement is not None and current_movement != previous_movement:
            expected_m = "[M]"

        if row.get("subject_change_marker") != expected_s:
            invalid_s_markers += 1

        if row.get("movement_marker") != expected_m:
            invalid_m_markers += 1

        previous_subject = current_subject
        previous_movement = current_movement

    status = "PASS"

    if anchor_count != trunk_count:
        status = "FAIL"

    if duplicate_anchor_ids:
        status = "FAIL"

    if missing_subject_signature:
        status = "FAIL"

    if missing_movement_signature:
        status = "FAIL"

    if invalid_s_markers:
        status = "FAIL"

    if invalid_m_markers:
        status = "FAIL"

    if ordering_errors:
        status = "FAIL"

    return {
        "predicate_anchors": anchor_count,
        "trunk_rows": trunk_count,
        "duplicate_anchor_ids": duplicate_anchor_ids,
        "missing_subject_signature": missing_subject_signature,
        "missing_movement_signature": missing_movement_signature,
        "invalid_s_markers": invalid_s_markers,
        "invalid_m_markers": invalid_m_markers,
        "ordering_errors": ordering_errors,
        "status": status,
    }



def print_visible_output(book: str, anchor_path: Path, trunk_path: Path, result: dict[str, object]) -> None:
    print("MNA Stage 3 Validation — Trunk + [S] + [M]")
    print(f"BOOK: {book}")
    print(f"ANCHOR DATASET: {anchor_path}")
    print(f"TRUNK DATASET: {trunk_path}")
    print(f"PREDICATE_ANCHORS: {result['predicate_anchors']}")
    print(f"TRUNK_ROWS: {result['trunk_rows']}")
    print(f"DUPLICATE_ANCHOR_IDS: {result['duplicate_anchor_ids']}")
    print(f"MISSING_SUBJECT_SIGNATURE: {result['missing_subject_signature']}")
    print(f"MISSING_MOVEMENT_SIGNATURE: {result['missing_movement_signature']}")
    print(f"INVALID_S_MARKERS: {result['invalid_s_markers']}")
    print(f"INVALID_M_MARKERS: {result['invalid_m_markers']}")
    print(f"ORDERING_ERRORS: {result['ordering_errors']}")
    print(f"STATUS: {result['status']}")



def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Stage 3 trunk datasets.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--anchors", help="Explicit predicate-anchor JSONL path")
    parser.add_argument("--trunk", help="Explicit trunk JSONL path")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = Path(__file__).resolve().parents[2]

        anchor_path = Path(args.anchors) if args.anchors else root / "datasets" / "predicate-anchors" / f"{book}.jsonl"
        trunk_path = Path(args.trunk) if args.trunk else root / "datasets" / "trunk" / f"{book}.jsonl"

        if not anchor_path.is_absolute():
            anchor_path = (Path.cwd() / anchor_path).resolve()

        if not trunk_path.is_absolute():
            trunk_path = (Path.cwd() / trunk_path).resolve()

        result = validate(book, anchor_path, trunk_path)
        print_visible_output(book, anchor_path, trunk_path, result)
        return 0 if result['status'] == 'PASS' else 2
    except Exception as exc:
        print("MNA Stage 3 Validation FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
