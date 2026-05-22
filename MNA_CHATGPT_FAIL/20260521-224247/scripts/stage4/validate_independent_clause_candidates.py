#!/usr/bin/env python3
"""
MNA Stage 4 Validator — independent clause candidates.

PURPOSE
- Validate datasets/independent-clause-candidates/<book>.jsonl.
- Verify inheritance from predicate-completeness rows.
- Verify allowed Stage 4 candidate statuses.
- Verify anti-drift claims remain NONE.

IMPORTANT
This validator does NOT validate trunk.
It does NOT validate [S] or [M].
It only validates the mechanical Stage 4 independent-clause-candidate layer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage4-independent-clause-candidate-validator-v1"

ALLOWED_STATUSES = {
    "NO",
    "UNRESOLVED_CANDIDATE",
}

ANTI_DRIFT_FIELDS = {
    "trunk_claim": "NONE",
    "subject_marker_claim": "NONE",
    "movement_marker_claim": "NONE",
    "connector_relationship_claim": "NONE",
    "label_claim": "NONE",
    "unit_claim": "NONE",
    "title_claim": "NONE",
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
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
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc

            if obj.get("record_type") == "metadata":
                if metadata is not None:
                    raise ValueError(f"Multiple metadata rows found in {path}")
                metadata = obj
            else:
                rows.append(obj)

    if metadata is None:
        raise ValueError(f"Missing metadata row: {path}")

    return metadata, rows


def validate(book: str, root: Path) -> dict[str, object]:
    completeness_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
    candidate_path = root / "datasets" / "independent-clause-candidates" / f"{book}.jsonl"

    completeness_metadata, completeness_rows = load_jsonl(completeness_path)
    candidate_metadata, candidate_rows = load_jsonl(candidate_path)

    errors = {
        "book_mismatches": 0,
        "row_count_mismatches": 0,
        "record_type_errors": 0,
        "duplicate_anchor_ids": 0,
        "ordering_errors": 0,
        "inheritance_errors": 0,
        "invalid_statuses": 0,
        "status_field_mismatches": 0,
        "dependency_source_errors": 0,
        "anti_drift_errors": 0,
        "metadata_count_errors": 0,
    }

    if completeness_metadata.get("book") != book:
        errors["book_mismatches"] += 1

    if candidate_metadata.get("book") != book:
        errors["book_mismatches"] += 1

    if len(completeness_rows) != len(candidate_rows):
        errors["row_count_mismatches"] += 1

    expected_ids = [str(row.get("predicate_anchor_id")) for row in completeness_rows]
    actual_ids = [str(row.get("predicate_anchor_id")) for row in candidate_rows]

    if expected_ids != actual_ids:
        errors["inheritance_errors"] += 1

    seen = set()
    previous_order = 0
    no_count = 0
    unresolved_count = 0

    for row in candidate_rows:
        if row.get("record_type") != "independent_clause_candidate_row":
            errors["record_type_errors"] += 1

        anchor_id = str(row.get("predicate_anchor_id"))
        if anchor_id in seen:
            errors["duplicate_anchor_ids"] += 1
        seen.add(anchor_id)

        try:
            order = int(row.get("anchor_order"))
        except Exception:
            errors["ordering_errors"] += 1
            order = previous_order

        if order <= previous_order:
            errors["ordering_errors"] += 1
        previous_order = order

        status = row.get("independent_clause_candidate")
        stage4_status = row.get("stage4_status")

        if status not in ALLOWED_STATUSES:
            errors["invalid_statuses"] += 1

        if status != stage4_status:
            errors["status_field_mismatches"] += 1

        sources = row.get("dependency_candidate_sources")
        if not isinstance(sources, list):
            errors["dependency_source_errors"] += 1
        else:
            if status == "NO" and not sources:
                errors["dependency_source_errors"] += 1
            if status == "UNRESOLVED_CANDIDATE" and sources:
                errors["dependency_source_errors"] += 1

        if status == "NO":
            no_count += 1
        elif status == "UNRESOLVED_CANDIDATE":
            unresolved_count += 1

        for field, expected_value in ANTI_DRIFT_FIELDS.items():
            if row.get(field) != expected_value:
                errors["anti_drift_errors"] += 1

    if int(candidate_metadata.get("rows", -1)) != len(candidate_rows):
        errors["metadata_count_errors"] += 1

    if int(candidate_metadata.get("independent_clause_candidate_NO", -1)) != no_count:
        errors["metadata_count_errors"] += 1

    if int(candidate_metadata.get("independent_clause_candidate_UNRESOLVED", -1)) != unresolved_count:
        errors["metadata_count_errors"] += 1

    status = "PASS"
    if any(errors.values()):
        status = "FAIL"

    return {
        "version": VERSION,
        "book": book,
        "predicate_completeness_rows": len(completeness_rows),
        "independent_clause_candidate_rows": len(candidate_rows),
        "no_count": no_count,
        "unresolved_candidate_count": unresolved_count,
        **errors,
        "status": status,
    }


def print_visible_output(book: str, root: Path, result: dict[str, object]) -> None:
    candidate_path = root / "datasets" / "independent-clause-candidates" / f"{book}.jsonl"
    completeness_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"

    print("MNA Stage 4 Validation — Independent Clause Candidates")
    print(f"BOOK: {book}")
    print(f"PREDICATE COMPLETENESS DATASET: {completeness_path}")
    print(f"INDEPENDENT CLAUSE CANDIDATE DATASET: {candidate_path}")
    print(f"PREDICATE_COMPLETENESS_ROWS: {result['predicate_completeness_rows']}")
    print(f"INDEPENDENT_CLAUSE_CANDIDATE_ROWS: {result['independent_clause_candidate_rows']}")
    print(f"NO: {result['no_count']}")
    print(f"UNRESOLVED_CANDIDATE: {result['unresolved_candidate_count']}")

    error_keys = [
        "book_mismatches",
        "row_count_mismatches",
        "record_type_errors",
        "duplicate_anchor_ids",
        "ordering_errors",
        "inheritance_errors",
        "invalid_statuses",
        "status_field_mismatches",
        "dependency_source_errors",
        "anti_drift_errors",
        "metadata_count_errors",
    ]

    for key in error_keys:
        print(f"{key.upper()}: {result[key]}")

    print(f"STATUS: {result['status']}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Stage 4 independent clause candidate dataset."
    )
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = mna_root_from_script()
        result = validate(book, root)
        print_visible_output(book, root, result)
        return 0 if result["status"] == "PASS" else 2
    except Exception as exc:
        print("MNA Stage 4 independent clause candidate validation FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
