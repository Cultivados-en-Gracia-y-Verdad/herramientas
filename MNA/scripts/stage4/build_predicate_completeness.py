#!/usr/bin/env python3
"""
MNA Stage 4 — Predicate Completeness / Independency Testing.

PURPOSE
- Read verified Stage 3 anchor skeleton rows.
- Preserve ordered predicate-anchor inheritance.
- Generate Stage 4 predicate completeness rows.

CURRENT IMPLEMENTATION STATUS
This implementation is intentionally conservative.
No formal independency rules are implemented yet.
Therefore all rows are currently classified as:

UNCERTAIN

ABSOLUTE LIMITS
This script does NOT:
- create trunk,
- create [S],
- create [M],
- generate connector networks,
- generate labels,
- generate units,
- generate titles,
- reconstruct predicate spans.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage4-predicate-completeness-v1"

VALID_CLASSIFICATIONS = {
    "INDEPENDENT",
    "DEPENDENT",
    "UNCERTAIN",
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_anchor_skeleton(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Anchor skeleton dataset not found: {path}")

    metadata = None
    rows = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()

            if not stripped:
                continue

            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_number}: {exc}"
                ) from exc

            record_type = obj.get("record_type")

            if record_type == "metadata":
                metadata = obj
            elif record_type == "anchor_skeleton_row":
                rows.append(obj)
            else:
                raise ValueError(
                    f"Unexpected record_type at line {line_number}: {record_type}"
                )

    if metadata is None:
        raise ValueError("Anchor skeleton dataset missing metadata row.")

    return metadata, rows


def classify_predicate_completeness(anchor_row: dict):
    """
    Conservative placeholder implementation.

    No formal independency rules exist yet.
    Therefore:
    - no independency is forced,
    - no dependency is forced,
    - all rows remain UNCERTAIN.
    """

    return {
        "predicate_completeness_status": "UNCERTAIN",
        "independency_status": "UNCERTAIN",
        "rule_id": "PC-UNRESOLVED-001",
        "reason": "No formal predicate-completeness rule applied yet.",
        "evidence_status": "unresolved",
    }


def build_predicate_completeness_row(anchor_row: dict):
    classification = classify_predicate_completeness(anchor_row)

    status = classification["predicate_completeness_status"]

    if status not in VALID_CLASSIFICATIONS:
        raise ValueError(f"Invalid classification: {status}")

    return {
        "record_type": "predicate_completeness_row",
        "predicate_anchor_id": anchor_row["predicate_anchor_id"],
        "book": anchor_row["book"],
        "chapter": anchor_row["chapter"],
        "verse": anchor_row["verse"],
        "reference": anchor_row["reference"],
        "anchor_order": anchor_row["anchor_order"],
        "greek_surface": anchor_row["greek_surface"],
        "greek_clean": anchor_row["greek_clean"],
        "lemma": anchor_row["lemma"],
        "morphology": anchor_row["morphology"],
        "mood": anchor_row["mood"],
        "person": anchor_row["person"],
        "number": anchor_row["number"],
        "predicate_completeness_status": classification[
            "predicate_completeness_status"
        ],
        "independency_status": classification["independency_status"],
        "rule_id": classification["rule_id"],
        "reason": classification["reason"],
        "evidence_status": classification["evidence_status"],
        "connector_dependency_used": "NO",
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
    }


def build_dataset(book: str, input_path: Path, output_path: Path, mna_root: Path):
    metadata, anchor_rows = load_anchor_skeleton(input_path)

    if metadata.get("book") != book:
        raise ValueError(
            f"Requested book '{book}' but anchor skeleton dataset is '{metadata.get('book')}'."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    for anchor_row in anchor_rows:
        rows.append(build_predicate_completeness_row(anchor_row))

    out_metadata = {
        "record_type": "metadata",
        "stage": "Stage 4 — Predicate Completeness / Independency Testing",
        "producer_script": "scripts/stage4/build_predicate_completeness.py",
        "producer_command": (
            f"python3 scripts/stage4/build_predicate_completeness.py {book}"
        ),
        "version": VERSION,
        "book": book,
        "source_dataset": str(input_path.relative_to(mna_root)),
        "predicate_completeness_rows": len(rows),
        "classification_policy": "Conservative unresolved placeholder state.",
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(out_metadata, ensure_ascii=False, sort_keys=True) + "\n"
        )

        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )

    return out_metadata, rows


def print_visible_output(
    book,
    input_path,
    output_path,
    metadata,
    rows,
    preview_lines,
):
    print("MNA Stage 4 — Predicate Completeness / Independency Testing")
    print(f"BOOK: {book}")
    print(f"INPUT: {input_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS: {len(rows)}")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, row in enumerate(rows[:preview_lines], start=1):
        print(
            f"{idx:>4}. "
            f"{row['predicate_anchor_id']} | "
            f"{row['reference']} | "
            f"{row['greek_surface']} | "
            f"{row['predicate_completeness_status']}"
        )

    remaining = len(rows) - min(len(rows), preview_lines)

    if remaining:
        print(f"... {remaining} more predicate completeness rows written")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Stage 4 predicate completeness dataset."
    )

    parser.add_argument("book")
    parser.add_argument("--preview-lines", type=int, default=40)

    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = mna_root_from_script()

        input_path = root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"
        output_path = (
            root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
        )

        metadata, rows = build_dataset(book, input_path, output_path, root)

        print_visible_output(
            book,
            input_path,
            output_path,
            metadata,
            rows,
            args.preview_lines,
        )

        return 0

    except Exception as exc:
        print("MNA Stage 4 FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
