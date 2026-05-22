#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "stage3-subject-movement-marking-validator-v1"

REQUIRED_FIELDS = {
    "record_type",
    "book",
    "order",
    "anchor_id",
    "chapter",
    "verse",
    "token_index",
    "greek_form",
    "lemma",
    "morphology",
    "tense",
    "voice",
    "mood",
    "person",
    "number",
    "explicit_subject_before",
    "subject_signal",
    "s_marker",
    "m_marker",
}

FORBIDDEN_FIELDS = {
    "trunk",
    "unit",
    "label",
    "title",
    "semantic_group",
    "discourse_structure",
    "progression",
}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Required dataset not found: {path}")
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate Stage 3 subject and movement markers.")
    ap.add_argument("book")
    args = ap.parse_args()

    book = args.book.strip().lower()
    mna = root()

    dataset = mna / "datasets" / "stage3" / book / "subject-movement-markers.jsonl"
    audit = mna / "audits" / "stage3" / book / "subject-movement-markers-audit.json"

    rows = load_jsonl(dataset)
    failures = []

    seen_orders = set()

    for idx, row in enumerate(rows, start=1):
        missing = sorted(REQUIRED_FIELDS - set(row.keys()))
        if missing:
            failures.append({"row": idx, "type": "MISSING_REQUIRED_FIELDS", "fields": missing})

        for field in FORBIDDEN_FIELDS:
            if field in row:
                failures.append({"row": idx, "type": "FORBIDDEN_FIELD_PRESENT", "field": field})

        order = row.get("order")
        if order in seen_orders:
            failures.append({"row": idx, "type": "DUPLICATE_ORDER", "value": order})
        seen_orders.add(order)

        if row.get("s_marker") not in {"", "[S]"}:
            failures.append({"row": idx, "type": "INVALID_S_MARKER"})

        if row.get("m_marker") not in {"", "[M]"}:
            failures.append({"row": idx, "type": "INVALID_M_MARKER"})

    audit.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "record_type": "subject_movement_marking_audit",
        "validator_version": VERSION,
        "book": book,
        "rows": len(rows),
        "failures": len(failures),
        "audit_pass": len(failures) == 0,
        "failure_details": failures,
    }

    with audit.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)

    print("MNA Stage 3 — Subject and Movement Marker Validator")
    print(f"BOOK: {book}")
    print(f"ROWS: {len(rows)}")
    print(f"FAILURES: {len(failures)}")
    print(f"AUDIT_PASS: {len(failures) == 0}")
    print(f"WROTE -> {audit}")
    return 0 if len(failures) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
