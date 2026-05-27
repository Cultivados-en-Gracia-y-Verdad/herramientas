#!/usr/bin/env python3
"""
MNA Stage 2A — predicate anchor validator.

PURPOSE
- Validate predicate-anchor datasets.
- Verify one-to-one inheritance from Stage 1 finite verbs.
- Verify deterministic anchor integrity.

ABSOLUTE LIMITS
This validator does NOT validate:
- predicate spans,
- subjects,
- objects,
- complements,
- connectors,
- clauses,
- trunk,
- movement,
- interpretation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage2a-predicate-anchor-validator-v1"


def load_jsonl(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"JSONL dataset not found: {path}")

    metadata: Optional[dict[str, object]] = None
    records: list[dict[str, object]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc

            record_type = obj.get("record_type")
            if record_type == "metadata":
                if metadata is not None:
                    raise ValueError("Multiple metadata records found.")
                metadata = obj
            else:
                records.append(obj)

    if metadata is None:
        raise ValueError("Dataset has no metadata record.")

    return metadata, records


def validate(book: str, finite_path: Path, anchor_path: Path) -> dict[str, object]:
    finite_metadata, finite_records = load_jsonl(finite_path)
    anchor_metadata, anchor_records = load_jsonl(anchor_path)

    if finite_metadata.get("book") != book:
        raise ValueError("Finite-verb dataset book mismatch.")

    if anchor_metadata.get("book") != book:
        raise ValueError("Predicate-anchor dataset book mismatch.")

    finite_count = len([r for r in finite_records if r.get("record_type") == "finite_verb"])
    anchor_count = len([r for r in anchor_records if r.get("record_type") == "predicate_anchor"])

    duplicate_ids = set()
    seen_ids = set()

    non_anchor_status = 0
    missing_required = 0

    required_fields = {
        "predicate_anchor_id",
        "book",
        "chapter",
        "verse",
        "reference",
        "source_line_number",
        "token_index_in_verse",
        "greek_surface",
        "greek_clean",
        "lemma",
        "morphology",
        "mood",
        "person",
        "number",
        "anchor_status",
    }

    for record in anchor_records:
        if record.get("record_type") != "predicate_anchor":
            continue

        missing = required_fields - set(record.keys())
        if missing:
            missing_required += 1

        anchor_id = record.get("predicate_anchor_id")
        if anchor_id in seen_ids:
            duplicate_ids.add(str(anchor_id))
        seen_ids.add(str(anchor_id))

        if record.get("anchor_status") != "finite_anchor":
            non_anchor_status += 1

    status = "PASS"

    if finite_count != anchor_count:
        status = "FAIL"

    if duplicate_ids:
        status = "FAIL"

    if non_anchor_status:
        status = "FAIL"

    if missing_required:
        status = "FAIL"

    return {
        "finite_verbs": finite_count,
        "predicate_anchors": anchor_count,
        "duplicate_anchor_ids": len(duplicate_ids),
        "invalid_anchor_status": non_anchor_status,
        "records_missing_required_fields": missing_required,
        "status": status,
    }


def print_visible_output(book: str, finite_path: Path, anchor_path: Path, result: dict[str, object]) -> None:
    print("MNA Stage 2A Validation — Predicate Anchors")
    print(f"BOOK: {book}")
    print(f"FINITE DATASET: {finite_path}")
    print(f"ANCHOR DATASET: {anchor_path}")
    print(f"FINITE_VERBS: {result['finite_verbs']}")
    print(f"PREDICATE_ANCHORS: {result['predicate_anchors']}")
    print(f"DUPLICATE_ANCHOR_IDS: {result['duplicate_anchor_ids']}")
    print(f"INVALID_ANCHOR_STATUS: {result['invalid_anchor_status']}")
    print(f"RECORDS_MISSING_REQUIRED_FIELDS: {result['records_missing_required_fields']}")
    print(f"STATUS: {result['status']}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate MNA Stage 2A predicate anchors.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--finite", help="Explicit Stage 1 finite-verb JSONL path")
    parser.add_argument("--anchors", help="Explicit predicate-anchor JSONL path")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = Path(__file__).resolve().parents[2]

        finite_path = Path(args.finite) if args.finite else root / "datasets" / "finite-verbs" / f"{book}.jsonl"
        anchor_path = Path(args.anchors) if args.anchors else root / "datasets" / "predicate-anchors" / f"{book}.jsonl"

        if not finite_path.is_absolute():
            finite_path = (Path.cwd() / finite_path).resolve()

        if not anchor_path.is_absolute():
            anchor_path = (Path.cwd() / anchor_path).resolve()

        result = validate(book, finite_path, anchor_path)
        print_visible_output(book, finite_path, anchor_path, result)
        return 0 if result["status"] == "PASS" else 2
    except Exception as exc:
        print("MNA Stage 2A Validation FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
