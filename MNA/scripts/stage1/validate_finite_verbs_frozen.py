#!/usr/bin/env python3
"""
MNA Stage 1 — Frozen Finite Verbs Validator

Stage 1 is an absolute-fact data layer.
It validates finite verb extraction only.

Allowed claims:
- finite form existence
- Greek form
- lemma
- morphology
- tense / voice / mood / person / number
- token location

Forbidden claims:
- structure
- continuity
- movement
- independency
- trunk
- connectors
- grouping
- units
- titles
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "stage1-frozen-finite-verbs-validator-v1"
RECORD_TYPE = "finite_verb"

REQUIRED_FIELDS = {
    "record_type",
    "book",
    "chapter",
    "verse",
    "token_index",
    "greek_form",
    "lemma",
    "morphology",
    "is_finite",
    "tense",
    "voice",
    "mood",
    "person",
    "number",
}

FORBIDDEN_FIELDS = {
    "anchor_id",
    "previous_anchor",
    "next_anchor",
    "adjacency_distance",
    "connector",
    "explicit_connector_before",
    "subject",
    "explicit_subject_before",
    "subject_continuity",
    "movement",
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
        raise FileNotFoundError(f"Missing Stage 1 dataset: {path}")
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
                rows.append(obj)
    return rows


def sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(row.get("chapter") or 0),
        int(row.get("verse") or 0),
        int(row.get("token_index") or 0),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate frozen MNA Stage 1 finite verbs.")
    parser.add_argument("book", help="Book slug, e.g. filipenses")
    args = parser.parse_args()

    root = mna_root_from_script()
    book = args.book.strip().lower()

    dataset_path = root / "datasets" / "finite-verbs" / f"{book}.jsonl"
    audit_path = root / "audits" / "stage1" / book / "finite-verbs-frozen-audit.json"

    rows = load_jsonl(dataset_path)
    failures: list[dict[str, Any]] = []

    seen_locations: set[tuple[int, int, int]] = set()
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

        if row.get("is_finite") is not True:
            failures.append({"row": index, "type": "IS_FINITE_NOT_TRUE", "value": row.get("is_finite")})

        for field in ["greek_form", "lemma", "morphology", "tense", "voice", "mood", "person", "number"]:
            if field in row and (row.get(field) is None or str(row.get(field)).strip() == ""):
                failures.append({"row": index, "type": "EMPTY_REQUIRED_VALUE", "field": field})

        key = sort_key(row)
        if key in seen_locations:
            failures.append({"row": index, "type": "DUPLICATE_TOKEN_LOCATION", "location": key})
        seen_locations.add(key)

        if previous_key is not None and key < previous_key:
            failures.append({"row": index, "type": "SOURCE_ORDER_ERROR", "previous": previous_key, "current": key})
        previous_key = key

    audit = {
        "record_type": "stage1_frozen_finite_verbs_audit",
        "validator_version": VERSION,
        "book": book,
        "dataset": str(dataset_path.relative_to(root)),
        "rows": len(rows),
        "failures": len(failures),
        "audit_pass": len(failures) == 0,
        "allowed_claims": [
            "finite form existence",
            "Greek form",
            "lemma",
            "morphology",
            "tense/voice/mood/person/number",
            "token location",
        ],
        "forbidden_claims": sorted(FORBIDDEN_FIELDS),
        "failure_details": failures,
    }

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2, sort_keys=True)

    print("MNA Stage 1 — Frozen Finite Verbs Validator")
    print(f"BOOK: {book}")
    print(f"ROWS: {len(rows)}")
    print(f"FAILURES: {len(failures)}")
    print(f"AUDIT_PASS: {len(failures) == 0}")
    print(f"WROTE -> {audit_path}")
    return 0 if len(failures) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
