#!/usr/bin/env python3
"""
MNA Stage 7 — Persistence Region Validator

Validates that Stage 7 persistence regions remain observational and do not
introduce movement, label, section, hierarchy, or dependency claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

VERSION = "stage7-persistence-region-validator-v1"
RECORD_TYPE = "persistence_region"
CLAIM_POLICY = "OBSERVATIONAL_PERSISTENCE_ONLY_NO_MOVEMENT_LABEL_OR_SECTION_CLAIM"

REQUIRED_FIELDS = {
    "record_type",
    "book",
    "persistence_field",
    "persistence_value",
    "region_length",
    "start_sequence_index",
    "end_sequence_index",
    "start_reference",
    "end_reference",
    "start_clause_id",
    "end_clause_id",
    "clause_ids",
    "finite_verbs",
    "region_status",
    "claim_policy",
}

APPROVED_REGION_STATUS = {
    "OBSERVED_PERSISTENCE_REGION",
    "SINGLE_ENVIRONMENT_REGION",
}

FORBIDDEN_FIELDS = {
    "movement",
    "movement_id",
    "movement_label",
    "label",
    "section",
    "section_id",
    "section_label",
    "hierarchy",
    "parent_clause",
    "child_clause",
    "governing_clause",
    "subordinate_clause",
    "structural_parent",
    "structural_child",
    "attachment_target",
    "authorial_outline",
}


def root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        raise FileNotFoundError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            rows.append(obj)
    return rows


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Stage 7 persistence regions.")
    parser.add_argument("book", help="Book slug, e.g. filipenses")
    args = parser.parse_args(argv)

    root = root_from_script()
    book = args.book.strip().lower()

    dataset_path = root / "datasets" / "stage7" / book / "persistence-regions.jsonl"
    audit_path = root / "audits" / "stage7" / book / "persistence-region-audit.json"

    rows = load_jsonl(dataset_path)
    failures = []

    for idx, row in enumerate(rows, start=1):
        if row.get("record_type") != RECORD_TYPE:
            failures.append({"row": idx, "type": "INVALID_RECORD_TYPE", "value": row.get("record_type")})

        missing = sorted(field for field in REQUIRED_FIELDS if field not in row)
        if missing:
            failures.append({"row": idx, "type": "MISSING_REQUIRED_FIELDS", "fields": missing})

        if row.get("claim_policy") != CLAIM_POLICY:
            failures.append({"row": idx, "type": "INVALID_CLAIM_POLICY", "value": row.get("claim_policy")})

        if row.get("region_status") not in APPROVED_REGION_STATUS:
            failures.append({"row": idx, "type": "INVALID_REGION_STATUS", "value": row.get("region_status")})

        for forbidden in FORBIDDEN_FIELDS:
            if forbidden in row:
                failures.append({"row": idx, "type": "FORBIDDEN_FIELD_PRESENT", "field": forbidden})

        clause_ids = row.get("clause_ids")
        finite_verbs = row.get("finite_verbs")
        region_length = row.get("region_length")

        if isinstance(clause_ids, list) and isinstance(region_length, int):
            if len(clause_ids) != region_length:
                failures.append({
                    "row": idx,
                    "type": "REGION_LENGTH_CLAUSE_ID_MISMATCH",
                    "region_length": region_length,
                    "clause_ids_count": len(clause_ids),
                })

        if isinstance(finite_verbs, list) and isinstance(region_length, int):
            if len(finite_verbs) != region_length:
                failures.append({
                    "row": idx,
                    "type": "REGION_LENGTH_FINITE_VERB_MISMATCH",
                    "region_length": region_length,
                    "finite_verbs_count": len(finite_verbs),
                })

        start_seq = row.get("start_sequence_index")
        end_seq = row.get("end_sequence_index")
        if isinstance(start_seq, int) and isinstance(end_seq, int):
            if end_seq < start_seq:
                failures.append({
                    "row": idx,
                    "type": "INVALID_SEQUENCE_RANGE",
                    "start_sequence_index": start_seq,
                    "end_sequence_index": end_seq,
                })

    audit = {
        "record_type": "stage7_persistence_region_audit",
        "validator_version": VERSION,
        "book": book,
        "rows": len(rows),
        "failures": len(failures),
        "audit_pass": len(failures) == 0,
        "policy": "OBSERVATIONAL_PERSISTENCE_ONLY_NO_MOVEMENT_LABEL_SECTION_OR_HIERARCHY_CLAIMS",
        "failure_details": failures,
    }

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2, sort_keys=True)

    print("MNA Stage 7 — Persistence Region Validator")
    print(f"VERSION: {VERSION}")
    print(f"BOOK: {book}")
    print(f"ROWS: {len(rows)}")
    print(f"FAILURES: {len(failures)}")
    print(f"AUDIT_PASS: {len(failures) == 0}")
    print(f"WROTE -> {audit_path}")

    return 0 if len(failures) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())