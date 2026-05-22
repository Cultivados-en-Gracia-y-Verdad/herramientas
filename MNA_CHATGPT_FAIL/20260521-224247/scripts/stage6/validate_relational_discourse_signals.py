#!/usr/bin/env python3
"""
MNA Stage 6 — Relational Discourse Signal Validator
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

VERSION = "stage6-relational-discourse-signal-validator-v1"

APPROVED_SIGNAL_CATEGORIES = {
    "continuity_signal",
    "development_signal",
    "contrast_signal",
    "inferential_signal",
    "explanatory_signal",
    "result_signal",
    "alternative_signal",
    "emphasis_signal",
    "unknown_signal",
    "no_connector_signal",
}

APPROVED_SIGNAL_STATUS = {
    "SIGNAL_OBSERVED",
    "NO_CONNECTOR_OBSERVED",
    "SIGNAL_PRESENT_CATEGORY_UNRESOLVED",
}

FORBIDDEN_FIELDS = {
    "parent_clause",
    "child_clause",
    "governing_clause",
    "subordinate_clause",
    "structural_parent",
    "structural_child",
    "hierarchy",
    "attachment_target",
}


def root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            yield json.loads(stripped)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Stage 6 relational discourse signals.")
    parser.add_argument("book", help="Book slug")
    args = parser.parse_args(argv)

    root = root_from_script()
    book = args.book.strip().lower()

    dataset_path = root / "datasets" / "stage6" / book / "relational-discourse-signals.jsonl"
    audit_path = root / "audits" / "stage6" / book / "relational-discourse-signal-audit.json"

    rows = list(load_jsonl(dataset_path))

    failures = []

    for idx, row in enumerate(rows, start=1):
        category = row.get("signal_category")
        status = row.get("signal_status")

        if category not in APPROVED_SIGNAL_CATEGORIES:
            failures.append({
                "row": idx,
                "type": "INVALID_SIGNAL_CATEGORY",
                "value": category,
            })

        if status not in APPROVED_SIGNAL_STATUS:
            failures.append({
                "row": idx,
                "type": "INVALID_SIGNAL_STATUS",
                "value": status,
            })

        for forbidden in FORBIDDEN_FIELDS:
            if forbidden in row:
                failures.append({
                    "row": idx,
                    "type": "FORBIDDEN_FIELD_PRESENT",
                    "field": forbidden,
                })

    audit = {
        "record_type": "stage6_relational_discourse_signal_audit",
        "book": book,
        "rows": len(rows),
        "failures": len(failures),
        "audit_pass": len(failures) == 0,
        "validator_version": VERSION,
        "policy": "NO_DEPENDENCY_OR_HIERARCHY_CLAIMS_ALLOWED",
        "failure_details": failures,
    }

    audit_path.parent.mkdir(parents=True, exist_ok=True)

    with audit_path.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2, sort_keys=True)

    print("MNA Stage 6 — Relational Discourse Signal Validator")
    print(f"VERSION: {VERSION}")
    print(f"BOOK: {book}")
    print(f"ROWS: {len(rows)}")
    print(f"FAILURES: {len(failures)}")
    print(f"AUDIT_PASS: {len(failures) == 0}")
    print(f"WROTE -> {audit_path}")

    return 0 if len(failures) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())