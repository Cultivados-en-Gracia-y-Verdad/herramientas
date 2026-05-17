#!/usr/bin/env python3
"""
MNA Stage 4 — Clause Survivability Audit

PURPOSE
- Audit surviving finite predicate environments after approved dependency removal.
- Measure structural survivability conservatively.

IMPORTANT
This script does NOT:
- create the trunk,
- prove independent clauses,
- create [S],
- create [M],
- create labels,
- create sections.

This is an audit layer only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

VERSION = "stage4-clause-survivability-audit-v1"

APPROVED_DEPENDENCY_SOURCES = {
    "absolute-dependency-candidates",
    "relative-dependency-candidates",
    "content-clause-dependency-candidates",
}

SURVIVES = "STRUCTURALLY_SURVIVES"
BROKEN = "BROKEN_AFTER_DEPENDENCY_REMOVAL"
UNCLEAR = "GOVERNOR_DEPENDENT_REMAINS_UNCLEAR"


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    metadata = None
    rows = []

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue

            obj = json.loads(stripped)

            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)

    return metadata, rows


def classify_survivability(row: dict) -> str:
    status = row.get("candidate_status")

    if status == "NO":
        return BROKEN

    dependency_sources = set(row.get("dependency_sources", []))
    approved_overlap = dependency_sources & APPROVED_DEPENDENCY_SOURCES

    if approved_overlap:
        return UNCLEAR

    return SURVIVES


def build_row(row: dict, survivability: str) -> dict:
    return {
        "record_type": "clause_survivability_audit_row",
        "survivability_status": survivability,
        "official_stage4_classification_changed": "NO",
        "predicate_anchor_id": row.get("predicate_anchor_id"),
        "book": row.get("book"),
        "chapter": row.get("chapter"),
        "verse": row.get("verse"),
        "reference": row.get("reference"),
        "anchor_greek_surface": row.get("greek_surface"),
        "candidate_status": row.get("candidate_status"),
        "dependency_sources": row.get("dependency_sources", []),
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
    }


def main(argv: Optional[list[str]] = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("book")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    root = mna_root_from_script()
    book = args.book.strip().lower()

    input_path = root / "datasets" / "independent-clause-candidates" / f"{book}.jsonl"
    output_path = root / "audits" / "stage4" / "clause-survivability-audit" / f"{book}.jsonl"

    _, rows = load_jsonl(input_path)

    audit_rows = []

    for row in rows:
        survivability = classify_survivability(row)
        audit_rows.append(build_row(row, survivability))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 4 — Clause Survivability Audit",
        "version": VERSION,
        "book": book,
        "rows_inspected": len(rows),
        "approved_dependency_sources": sorted(APPROVED_DEPENDENCY_SOURCES),
        "official_stage4_classification_changed": "NO",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")

        for row in audit_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 4 — Clause Survivability Audit")
    print(f"BOOK: {book}")
    print(f"INPUT: {input_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS INSPECTED: {len(rows)}")
    print("OFFICIAL STAGE 4 CLASSIFICATION CHANGED: NO")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, row in enumerate(audit_rows[:args.preview_lines], start=1):
        print(
            f"{idx:>4}. "
            f"{row['predicate_anchor_id']} | "
            f"{row['reference']} | "
            f"anchor={row['anchor_greek_surface']} | "
            f"{row['survivability_status']}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
