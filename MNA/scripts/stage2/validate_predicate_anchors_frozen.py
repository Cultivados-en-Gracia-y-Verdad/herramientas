#!/usr/bin/env python3
"""
MNA Stage 2 — Frozen Predicate Anchors Validator

Stage 2 is an absolute-fact data layer.
It validates predicate anchors only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "stage2-frozen-predicate-anchors-validator-v1"
RECORD_TYPE = "predicate_anchor"

REQUIRED_FIELDS = {
    "record_type",
    "anchor_id",
    "book",
    "chapter",
    "verse",
    "token_index",
    "greek_form",
    "lemma",
    "morphology",
    "previous_anchor",
    "next_anchor",
    "adjacency_distance",
    "explicit_connector_before",
    "explicit_subject_before",
}

FORBIDDEN_FIELDS = {
    "movement",
    "subject_continuity",
    "lexical_subject_change",
    "independency",
    "trunk",
    "unit",
    "label",
    "title",
    "structure",
    "discourse",
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        raise FileNotFoundError(f"Missing Stage 2 dataset: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(row.get("chapter") or 0),
        int(row.get("verse") or 0),
        int(row.get("token_index") or 0),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate frozen MNA Stage 2 predicate anchors.")
    parser.add_argument("book", help="Book slug")
    args = parser.parse_args()

    root = mna_root_from_script()
    book = args.book.strip().lower()

    dataset_path = root / "datasets" / "predicate-anchors" / f"{book}.jsonl"
    stage1_path = root / "datasets" / "finite-verbs" / f"{book}.jsonl"
    audit_path = root / "audits" / "stage2" / book / "predicate-anchors-frozen-audit.json"

    rows = load_jsonl(dataset_path)
    stage1_rows = load_jsonl(stage1_path)

    failures: list[dict[str, Any]] = []

    anchor_ids: set[str] = set()
    previous_key: tuple[int, int, int] | None = None

    for index, row in enumerate(rows, start=1):
        missing = sorted(REQUIRED_FIELDS - set(row.keys()))
        if missing:
            failures.append({"row": index, "type": "MISSING_REQUIRED_FIELDS", "fields": missing})

        for field in FORBIDDEN_FIELDS:
            if field in row:
                failures.append({"row": index, "type": "FORBIDDEN_FIELD_PRESENT", "field": field})

        if row.get("record_type") != RECORD_TYPE:
            failures.append({"row": index, "type": "INVALID_RECORD_TYPE", "value": row.get("record_type")})

        anchor_id = str(row.get("anchor_id") or "")
        if not anchor_id:
            failures.append({"row": index, "type": "EMPTY_ANCHOR_ID"})
        elif anchor_id in anchor_ids:
            failures.append({"row": index, "type": "DUPLICATE_ANCHOR_ID", "anchor_id": anchor_id})
        anchor_ids.add(anchor_id)

        key = sort_key(row)
        if previous_key is not None and key < previous_key:
            failures.append({"row": index, "type": "SOURCE_ORDER_ERROR", "previous": previous_key, "current": key})
        previous_key = key

        try:
            adjacency = int(row.get("adjacency_distance"))
            if adjacency < 0:
                failures.append({"row": index, "type": "NEGATIVE_ADJACENCY_DISTANCE"})
        except Exception:
            failures.append({"row": index, "type": "INVALID_ADJACENCY_DISTANCE"})

    if len(rows) != len(stage1_rows):
        failures.append({
            "type": "ANCHOR_COUNT_MISMATCH",
            "stage1_count": len(stage1_rows),
            "stage2_count": len(rows),
        })

    audit = {
        "record_type": "stage2_frozen_predicate_anchors_audit",
        "validator_version": VERSION,
        "book": book,
        "dataset": str(dataset_path.relative_to(root)),
        "rows": len(rows),
        "stage1_rows": len(stage1_rows),
        "failures": len(failures),
        "audit_pass": len(failures) == 0,
        "failure_details": failures,
    }

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2, sort_keys=True)

    print("MNA Stage 2 — Frozen Predicate Anchors Validator")
    print(f"BOOK: {book}")
    print(f"ROWS: {len(rows)}")
    print(f"FAILURES: {len(failures)}")
    print(f"AUDIT_PASS: {len(failures) == 0}")
    print(f"WROTE -> {audit_path}")
    return 0 if len(failures) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
