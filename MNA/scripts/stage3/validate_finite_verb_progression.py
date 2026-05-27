#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "stage3-finite-verb-progression-validator-v1"

REQUIRED_FIELDS = {
    "record_type",
    "book",
    "progression_order",
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
    "explicit_connector_before",
    "explicit_subject_before",
    "subject_signal",
    "s_marker",
    "m_marker",
    "marker_policy",
}

FORBIDDEN_FIELDS = {
    "trunk",
    "unit",
    "label",
    "title",
    "semantic_group",
    "discourse_structure",
}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
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
    ap = argparse.ArgumentParser(description="Validate Stage 3 finite-verb progression observations.")
    ap.add_argument("book")
    args = ap.parse_args()

    book = args.book.strip().lower()
    mna = root()

    dataset = mna / "datasets" / "stage3" / book / "finite-verb-progression.jsonl"
    audit = mna / "audits" / "stage3" / book / "finite-verb-progression-audit.json"

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

        order = row.get("progression_order")
        if order in seen_orders:
            failures.append({"row": idx, "type": "DUPLICATE_PROGRESSION_ORDER", "value": order})
        seen_orders.add(order)

        s = row.get("s_marker")
        m = row.get("m_marker")

        if s not in {"", "[S]"}:
            failures.append({"row": idx, "type": "INVALID_S_MARKER", "value": s})

        if m not in {"", "[M]"}:
            failures.append({"row": idx, "type": "INVALID_M_MARKER", "value": m})

    audit.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "record_type": "stage3_finite_verb_progression_audit",
        "validator_version": VERSION,
        "book": book,
        "rows": len(rows),
        "failures": len(failures),
        "audit_pass": len(failures) == 0,
        "failure_details": failures,
    }

    with audit.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)

    print("MNA Stage 3 — Finite Verb Progression Validator")
    print(f"BOOK: {book}")
    print(f"ROWS: {len(rows)}")
    print(f"FAILURES: {len(failures)}")
    print(f"AUDIT_PASS: {len(failures) == 0}")
    print(f"WROTE -> {audit}")
    return 0 if len(failures) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
