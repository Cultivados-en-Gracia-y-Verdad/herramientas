#!/usr/bin/env python3
"""
MNA Stage 4 — Local Clause Span Audit

PURPOSE
- Estimate local clause spans around predicate-completeness anchors conservatively.
- Provide auditable span reconstruction for survivability inspection.

IMPORTANT
This script does NOT:
- prove independent clauses,
- create the trunk,
- create [S],
- create [M],
- create labels,
- create sections.

This is an audit-only reconstruction layer.

CRITICAL DESIGN NOTE
- Every row in predicate-completeness is already a predicate anchor.
- This script must NOT re-decide finiteness from the morphology string.
- It uses predicate-completeness row order as the authoritative anchor stream.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

VERSION = "stage4-local-clause-span-audit-v2-anchor-stream"


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


def estimate_clause_span(current_index: int, verse_rows: list[dict]):
    """
    Primitive predicate-anchor span estimate.

    Since predicate-completeness already contains predicate anchors only,
    the nearest previous/next predicate anchor becomes the hard stopping point.

    This is intentionally conservative and primitive:
    - it does not claim trunk,
    - it does not prove independence,
    - it only exposes the local predicate-to-predicate span for audit.
    """

    left = current_index
    right = current_index

    idx = current_index - 1
    while idx >= 0:
        # Previous predicate anchor stops the span.
        break

    idx = current_index + 1
    while idx < len(verse_rows):
        # Next predicate anchor stops the span.
        break

    return left, right


def build_span_text(rows: list[dict], left: int, right: int) -> str:
    return " ".join(
        str(r.get("greek_surface", ""))
        for r in rows[left:right + 1]
    )


def build_row(row: dict, span_text: str, left_row: dict, right_row: dict):
    return {
        "record_type": "local_clause_span_audit_row",
        "predicate_anchor_id": row.get("predicate_anchor_id"),
        "book": row.get("book"),
        "chapter": row.get("chapter"),
        "verse": row.get("verse"),
        "reference": row.get("reference"),
        "anchor_order": row.get("anchor_order"),
        "anchor_token_index_in_verse": row.get("token_index_in_verse"),
        "anchor_greek_surface": row.get("greek_surface"),
        "estimated_clause_span": span_text,
        "span_left_token_index": left_row.get("token_index_in_verse"),
        "span_right_token_index": right_row.get("token_index_in_verse"),
        "span_method": "predicate_completeness_anchor_stream_v2_single_anchor_primitive",
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

    input_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
    output_path = root / "audits" / "stage4" / "local-clause-span-audit" / f"{book}.jsonl"

    _metadata, rows = load_jsonl(input_path)
    verses = build_verse_index(rows)

    audit_rows = []

    for verse_rows in verses.values():
        for current_index, row in enumerate(verse_rows):
            left, right = estimate_clause_span(current_index, verse_rows)
            span_text = build_span_text(verse_rows, left, right)

            audit_rows.append(
                build_row(
                    row,
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
        "source_dataset": str(input_path.relative_to(root)),
        "rows_inspected": len(rows),
        "rows_written": len(audit_rows),
        "span_method": "predicate_completeness_anchor_stream_v2_single_anchor_primitive",
        "official_stage4_classification_changed": "NO",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")

        for row in audit_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 4 — Local Clause Span Audit")
    print(f"BOOK: {book}")
    print(f"INPUT: {input_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS INSPECTED: {len(rows)}")
    print(f"ROWS WRITTEN: {len(audit_rows)}")
    print("SPAN METHOD: predicate_completeness_anchor_stream_v2_single_anchor_primitive")
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
