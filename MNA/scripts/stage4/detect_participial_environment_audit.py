#!/usr/bin/env python3
"""
MNA Stage 4 — Participial Environment Audit

PURPOSE
- Surface participial environments for structural review.
- Explore possible dependency environments conservatively.

IMPORTANT
This script is AUDIT ONLY.
It is NOT an approved Stage 4 eliminator.

It does NOT:
- eliminate independent clause candidates,
- modify predicate completeness,
- create trunk,
- create [S],
- create [M],
- create labels,
- create sections.

All output rows are quarantined review environments only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage4-participial-environment-audit-v1"


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


def is_participle(morphology: str) -> bool:
    if not morphology:
        return False

    # conservative heuristic only
    return bool(re.search(r"P", morphology))


def classify_environment(row: dict) -> str:
    morphology = str(row.get("morphology", ""))

    if is_participle(morphology):
        return "PARTICIPIAL_ENVIRONMENT_REVIEW_ONLY"

    return "UNSAFE_PARTICIPIAL_PROXIMITY_NOT_APPROVED"


def main(argv: Optional[list[str]] = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("book")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    root = mna_root_from_script()

    skeleton_path = root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"
    output_path = root / "audits" / "stage4" / "participial-environment-audit" / f"{book}.jsonl"

    _, rows = load_jsonl(skeleton_path)

    audit_rows = []

    for row in rows:
        status = classify_environment(row)

        if status == "UNSAFE_PARTICIPIAL_PROXIMITY_NOT_APPROVED":
            continue

        audit_rows.append({
            "record_type": "participial_environment_audit_row",
            "audit_status": status,
            "approved_for_official_elimination": "NO",
            "official_stage4_classification_changed": "NO",
            "predicate_anchor_id": row["predicate_anchor_id"],
            "book": row["book"],
            "chapter": row["chapter"],
            "verse": row["verse"],
            "reference": row["reference"],
            "anchor_order": row["anchor_order"],
            "greek_surface": row["greek_surface"],
            "lemma": row["lemma"],
            "morphology": row["morphology"],
            "trunk_claim": "NONE",
            "subject_marker_claim": "NONE",
            "movement_marker_claim": "NONE",
            "connector_relationship_claim": "NONE",
            "label_claim": "NONE",
            "unit_claim": "NONE",
            "title_claim": "NONE",
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 4 — Participial Environment Audit",
        "version": VERSION,
        "book": book,
        "anchors_inspected": len(rows),
        "participial_environment_rows_found": len(audit_rows),
        "approved_for_official_elimination": "NO",
        "official_stage4_classification_changed": "NO",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")

        for row in audit_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 4 — Participial Environment Audit")
    print(f"BOOK: {book}")
    print(f"ANCHOR SKELETON: {skeleton_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ANCHORS INSPECTED: {len(rows)}")
    print(f"PARTICIPIAL ENVIRONMENT ROWS FOUND: {len(audit_rows)}")
    print("APPROVED FOR OFFICIAL ELIMINATION: NO")
    print("OFFICIAL STAGE 4 CLASSIFICATION CHANGED: NO")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, row in enumerate(audit_rows[:25], start=1):
        print(
            f"{idx:>4}. "
            f"{row['predicate_anchor_id']} | "
            f"{row['reference']} | "
            f"anchor={row['greek_surface']} | "
            f"{row['audit_status']}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
