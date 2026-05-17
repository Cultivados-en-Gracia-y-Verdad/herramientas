#!/usr/bin/env python3
"""
MNA Stage 4 — Local Clause Span Audit

PURPOSE
- Estimate local clause spans around predicate anchors conservatively.
- Reconstruct token spans from the anchor skeleton token stream.
- Provide auditable local clause environments for survivability inspection.

IMPORTANT
This script does NOT:
- prove independent clauses,
- create the trunk,
- create [S],
- create [M],
- create labels,
- create sections.

This is an audit-only reconstruction layer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

VERSION = "stage4-local-clause-span-audit-v3-anchor-skeleton-token-stream"

FINITE_STOPPING_MOODS = {"I", "S", "O", "M"}


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


def is_finite_anchor(row: dict) -> bool:
    morphology = str(row.get("morphology", ""))

    if len(morphology) < 4:
        return False

    return morphology[3] in FINITE_STOPPING_MOODS


def build_verse_index(rows: list[dict]):
    verses = {}

    for row in rows:
        key = (
            row.get("book"),
            row.get("chapter"),
            row.get("verse"),
        )

        verses.setdefault(key, []).append(row)

    for value in verses.values():
        value.sort(key=lambda r: int(r.get("token_index_in_verse", 0)))

    return verses


def estimate_clause_span(anchor_position: int, verse_rows: list[dict]):
    left = anchor_position
    right = anchor_position

    idx = anchor_position - 1

    while idx >= 0:
        row = verse_rows[idx]

        if is_finite_anchor(row):
            break

        left = idx
        idx -= 1

    idx = anchor_position + 1

    while idx < len(verse_rows):
        row = verse_rows[idx]

        if is_finite_anchor(row):
            break

        right = idx
        idx += 1

    return left, right


def build_span_text(rows: list[dict], left: int, right: int) -> str:
    return " ".join(
        str(r.get("greek_surface", ""))
        for r in rows[left:right + 1]
    )


def build_row(anchor_row, span_text, left_row, right_row):
    return {
        "record_type": "local_clause_span_audit_row",
        "predicate_anchor_id": anchor_row.get("predicate_anchor_id"),
        "book": anchor_row.get("book"),
        "chapter": anchor_row.get("chapter"),
        "verse": anchor_row.get("verse"),
        "reference": anchor_row.get("reference"),
        "anchor_order": anchor_row.get("anchor_order"),
        "anchor_token_index_in_verse": anchor_row.get("token_index_in_verse"),
        "anchor_greek_surface": anchor_row.get("greek_surface"),
        "estimated_clause_span": span_text,
        "span_left_token_index": left_row.get("token_index_in_verse"),
        "span_right_token_index": right_row.get("token_index_in_verse"),
        "span_method": "anchor_skeleton_local_walk_v3",
        "official_stage4_classification_changed": "NO",
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

    predicate_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
    skeleton_path = root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"

    output_path = root / "audits" / "stage4" / "local-clause-span-audit" / f"{book}.jsonl"

    _predicate_metadata, predicate_rows = load_jsonl(predicate_path)
    _skeleton_metadata, skeleton_rows = load_jsonl(skeleton_path)

    verses = build_verse_index(skeleton_rows)

    audit_rows = []

    for anchor_row in predicate_rows:
        key = (
            anchor_row.get("book"),
            anchor_row.get("chapter"),
            anchor_row.get("verse"),
        )

        verse_rows = verses.get(key, [])

        anchor_token_index = int(anchor_row.get("token_index_in_verse", 0))

        anchor_position = None

        for idx, row in enumerate(verse_rows):
            token_index = int(row.get("token_index_in_verse", 0))

            if token_index == anchor_token_index:
                anchor_position = idx
                break

        if anchor_position is None:
            continue

        left, right = estimate_clause_span(anchor_position, verse_rows)

        span_text = build_span_text(verse_rows, left, right)

        audit_rows.append(
            build_row(
                anchor_row,
                span_text,
                verse_rows[left],
                verse_rows[right],
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 4 — Local Clause Span Audit",
        "version": VERSION,
        "book": book,
        "predicate_dataset": str(predicate_path.relative_to(root)),
        "anchor_skeleton_dataset": str(skeleton_path.relative_to(root)),
        "rows_inspected": len(predicate_rows),
        "rows_written": len(audit_rows),
        "span_method": "anchor_skeleton_local_walk_v3",
        "official_stage4_classification_changed": "NO",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")

        for row in audit_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 4 — Local Clause Span Audit")
    print(f"BOOK: {book}")
    print(f"PREDICATE DATASET: {predicate_path}")
    print(f"ANCHOR SKELETON: {skeleton_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS INSPECTED: {len(predicate_rows)}")
    print(f"ROWS WRITTEN: {len(audit_rows)}")
    print("SPAN METHOD: anchor_skeleton_local_walk_v3")
    print("OFFICIAL STAGE 4 CLASSIFICATION CHANGED: NO")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, row in enumerate(audit_rows[:args.preview_lines], start=1):
        print(
            f"{idx:>4}. "
            f"{row['predicate_anchor_id']} | "
            f"{row['reference']} | "
            f"anchor={row['anchor_greek_surface']} | "
            f"span={row['estimated_clause_span']}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
