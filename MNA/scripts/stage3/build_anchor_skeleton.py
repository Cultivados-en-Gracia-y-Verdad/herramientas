#!/usr/bin/env python3
"""
MNA Stage 3 — anchor skeleton only.

PURPOSE
- Read verified Stage 2A predicate anchors.
- Produce an ordered predicate-anchor skeleton.
- Preserve anchor order, identity, and source coordinates for later stages.

ABSOLUTE LIMITS
This script does NOT determine:
- independent clauses,
- dependent clauses,
- real trunk,
- subject-change markers,
- movement markers,
- connectors,
- labels,
- patterns,
- units,
- titles,
- semantic subjects,
- semantic movements,
- predicate spans,
- clause structures,
- theology.

IMPORTANT TERMINOLOGY
This output is NOT trunk.
Real trunk = independent-clause structure, which is not built here.
[S] and [M] belong only to verified trunk clauses and are not calculated here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage3-anchor-skeleton-v3"


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_anchor_dataset(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Predicate-anchor dataset not found: {path}")

    metadata = None
    anchors = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue

            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc

            record_type = obj.get("record_type")

            if record_type == "metadata":
                if metadata is not None:
                    raise ValueError("Multiple metadata rows found in anchor dataset.")
                metadata = obj
            elif record_type == "predicate_anchor":
                anchors.append(obj)
            else:
                raise ValueError(f"Unexpected record_type at line {line_number}: {record_type}")

    if metadata is None:
        raise ValueError("Anchor dataset missing metadata row.")

    expected = int(metadata.get("predicate_anchors_created", -1))
    if expected != len(anchors):
        raise ValueError(
            f"Predicate-anchor count mismatch: metadata={expected}, records={len(anchors)}"
        )

    return metadata, anchors


def build_anchor_skeleton_row(anchor: dict[str, object], anchor_order: int) -> dict[str, object]:
    return {
        "record_type": "anchor_skeleton_row",
        "predicate_anchor_id": anchor["predicate_anchor_id"],
        "book": anchor["book"],
        "chapter": anchor["chapter"],
        "verse": anchor["verse"],
        "reference": anchor["reference"],
        "source_line_number": anchor["source_line_number"],
        "token_index_in_verse": anchor["token_index_in_verse"],
        "stage1_ref_code": anchor["stage1_ref_code"],
        "anchor_order": anchor_order,
        "greek_surface": anchor["greek_surface"],
        "greek_clean": anchor["greek_clean"],
        "lemma": anchor["lemma"],
        "morphology": anchor["morphology"],
        "mood": anchor["mood"],
        "mood_code": anchor["mood_code"],
        "person": anchor["person"],
        "person_code": anchor["person_code"],
        "number": anchor["number"],
        "number_code": anchor["number_code"],
        "skeleton_status": "ordered_predicate_anchor_sequence",
        "trunk_claim": "NONE",
        "independent_clause_claim": "NONE",
        "subject_change_marker": "NOT_APPLICABLE_BEFORE_TRUNK",
        "movement_marker": "NOT_APPLICABLE_BEFORE_TRUNK",
        "connector_data": "NONE",
        "label_data": "NONE",
        "unit_data": "NONE",
        "title_data": "NONE",
    }


def build_anchor_skeleton(book: str, input_path: Path, output_path: Path, mna_root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    anchor_metadata, anchors = load_anchor_dataset(input_path)

    if str(anchor_metadata.get("book")) != book:
        raise ValueError(
            f"Requested book '{book}' but anchor dataset is '{anchor_metadata.get('book')}'."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [build_anchor_skeleton_row(anchor, idx) for idx, anchor in enumerate(anchors, start=1)]

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 3 — Anchor Skeleton Only",
        "producer_script": "scripts/stage3/build_anchor_skeleton.py",
        "producer_command": f"python3 scripts/stage3/build_anchor_skeleton.py {book}",
        "generated_at": "DETERMINISTIC-NOT-RUNTIME-STAMPED",
        "version": VERSION,
        "book": book,
        "predicate_anchor_dataset": str(input_path.relative_to(mna_root)),
        "predicate_anchors": len(anchors),
        "anchor_skeleton_rows": len(rows),
        "source_coordinates_preserved": "source_line_number + token_index_in_verse",
        "trunk_claim": "NONE: real trunk = independent-clause structure, not built by this script.",
        "subject_marker_usage": "NONE: [S] belongs only to verified trunk clauses.",
        "movement_marker_usage": "NONE: [M] belongs only to verified trunk clauses.",
        "connector_usage": "NONE",
        "label_usage": "NONE",
        "unit_usage": "NONE",
        "title_usage": "NONE",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    return metadata, rows


def print_visible_output(book: str, input_path: Path, output_path: Path, metadata: dict[str, object], rows: list[dict[str, object]], preview_lines: int) -> None:
    print("MNA Stage 3 — Anchor Skeleton Only")
    print(f"BOOK: {book}")
    print(f"INPUT: {input_path}")
    print(f"OUTPUT: {output_path}")
    print(f"PREDICATE_ANCHORS: {metadata['predicate_anchors']}")
    print(f"ANCHOR_SKELETON_ROWS: {metadata['anchor_skeleton_rows']}")
    print("TRUNK_CLAIM: NONE")
    print("S_MARKERS: NOT APPLICABLE BEFORE TRUNK")
    print("M_MARKERS: NOT APPLICABLE BEFORE TRUNK")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, row in enumerate(rows[:preview_lines], start=1):
        print(
            f"{idx:>4}. {row['predicate_anchor_id']} | {row['reference']} | "
            f"{row['greek_surface']} | token={row['token_index_in_verse']} | "
            f"anchor_order={row['anchor_order']}"
        )

    remaining = len(rows) - min(len(rows), preview_lines)
    if remaining:
        print(f"... {remaining} more anchor skeleton rows written to dataset")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build MNA Stage 3 anchor skeleton only.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--input", help="Explicit predicate-anchor JSONL path")
    parser.add_argument("--output", help="Explicit anchor-skeleton JSONL path")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    book = args.book.strip().lower()
    mna_root = mna_root_from_script()

    try:
        input_path = Path(args.input) if args.input else mna_root / "datasets" / "predicate-anchors" / f"{book}.jsonl"
        output_path = Path(args.output) if args.output else mna_root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"

        if not input_path.is_absolute():
            input_path = (Path.cwd() / input_path).resolve()

        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()

        metadata, rows = build_anchor_skeleton(book, input_path, output_path, mna_root)
        print_visible_output(book, input_path, output_path, metadata, rows, args.preview_lines)
        return 0 if len(rows) == int(metadata['predicate_anchors']) else 2
    except Exception as exc:
        print("MNA Stage 3 Anchor Skeleton FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
