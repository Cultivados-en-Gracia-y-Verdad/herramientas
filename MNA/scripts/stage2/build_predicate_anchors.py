#!/usr/bin/env python3
"""
MNA Stage 2A — predicate anchor builder.

PURPOSE
- Read the verified Stage 1 finite-verb dataset.
- Transform each finite verb record into one immutable predicate anchor.
- Write deterministic JSONL predicate-anchor records.
- Print visible whole-book output.

ABSOLUTE LIMITS
This script does NOT determine:
- full predicates,
- predicate spans,
- subjects,
- objects,
- complements,
- clause boundaries,
- connectors,
- trunk,
- movement,
- interpretation,
- theology.

MECHANICAL RULE
One verified Stage 1 finite verb record creates exactly one predicate anchor.

This script does not discover new anchors.
It only transforms Stage 1 finite-verb records into Stage 2A anchor records.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage2a-predicate-anchors-v1"
STAGE1_VERSION_PREFIX = "stage1-finite-verbs-"


def mna_root_from_script() -> Path:
    # MNA/scripts/stage2/build_predicate_anchors.py -> MNA
    return Path(__file__).resolve().parents[2]


def clean_greek_surface(surface: str) -> str:
    """Remove visible punctuation/critical marks from the Greek surface token.

    greek_surface preserves the exact MorphGNT token.
    greek_clean gives a practical analysis token without punctuation marks.
    This cleaning does not change lemma or morphology and does not create claims.
    """
    return re.sub(r"^[^\w\u0370-\u03ff\u1f00-\u1fff]+|[^\w\u0370-\u03ff\u1f00-\u1fff]+$", "", surface)


def load_stage1_records(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Stage 1 finite-verb dataset not found: {path}")

    metadata: Optional[dict[str, object]] = None
    records: list[dict[str, object]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc

            record_type = obj.get("record_type")
            if record_type == "metadata":
                if metadata is not None:
                    raise ValueError("Stage 1 dataset contains multiple metadata records.")
                metadata = obj
            elif record_type == "finite_verb":
                records.append(obj)
            else:
                raise ValueError(f"Unexpected Stage 1 record_type at line {line_number}: {record_type}")

    if metadata is None:
        raise ValueError("Stage 1 dataset has no metadata record.")

    version = str(metadata.get("version", ""))
    if not version.startswith(STAGE1_VERSION_PREFIX):
        raise ValueError(f"Stage 1 dataset version is not recognized: {version}")

    expected_count = int(metadata.get("finite_verbs_extracted", -1))
    if expected_count != len(records):
        raise ValueError(
            f"Stage 1 finite count mismatch: metadata={expected_count}, records={len(records)}"
        )

    return metadata, records


def anchor_id_for(record: dict[str, object], occurrence_index: int) -> str:
    book = str(record["book"])
    chapter = int(record["chapter"])
    verse = int(record["verse"])
    token_index = int(record["token_index_in_verse"])
    return f"{book}-{chapter}-{verse}-pa-{token_index}-{occurrence_index}"


def build_anchor_record(record: dict[str, object], occurrence_index: int, stage1_dataset: Path) -> dict[str, object]:
    finite_detection = record["finite_detection"]
    greek_surface = str(record["greek"])

    return {
        "record_type": "predicate_anchor",
        "predicate_anchor_id": anchor_id_for(record, occurrence_index),
        "book": record["book"],
        "chapter": record["chapter"],
        "verse": record["verse"],
        "reference": record["reference"],
        "source_line_number": record["source_line_number"],
        "token_index_in_verse": record["token_index_in_verse"],
        "greek_surface": greek_surface,
        "greek_clean": clean_greek_surface(greek_surface),
        "lemma": record["lemma"],
        "morphology": record["morph_code"],
        "mood": finite_detection["mood"],
        "mood_code": finite_detection["mood_code"],
        "person": finite_detection["person"],
        "person_code": finite_detection["person_code"],
        "number": finite_detection["number"],
        "number_code": finite_detection["number_code"],
        "stage1_ref_code": record["ref_code"],
        "stage1_token_index_in_verse": record["token_index_in_verse"],
        "stage1_source_line_number": record["source_line_number"],
        "stage1_dataset": str(stage1_dataset),
        "anchor_status": "finite_anchor",
        "downstream_claims": "NONE",
    }


def build_predicate_anchors(book: str, input_path: Path, output_path: Path, mna_root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    stage1_metadata, stage1_records = load_stage1_records(input_path)

    if str(stage1_metadata.get("book")) != book:
        raise ValueError(
            f"Requested book '{book}' but Stage 1 dataset book is '{stage1_metadata.get('book')}'."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    anchors: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    for occurrence_index, record in enumerate(stage1_records, start=1):
        anchor = build_anchor_record(record, occurrence_index, input_path.relative_to(mna_root))
        anchor_id = str(anchor["predicate_anchor_id"])
        if anchor_id in seen_ids:
            raise ValueError(f"Duplicate predicate_anchor_id generated: {anchor_id}")
        seen_ids.add(anchor_id)
        anchors.append(anchor)

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 2A — Predicate Anchors",
        "producer_script": "scripts/stage2/build_predicate_anchors.py",
        "producer_command": f"python3 scripts/stage2/build_predicate_anchors.py {book}",
        "generated_at": "DETERMINISTIC-NOT-RUNTIME-STAMPED",
        "version": VERSION,
        "book": book,
        "stage1_dataset": str(input_path.relative_to(mna_root)),
        "stage1_version": stage1_metadata.get("version"),
        "finite_verbs_inherited": len(stage1_records),
        "predicate_anchors_created": len(anchors),
        "rule": "One verified Stage 1 finite verb record creates exactly one immutable predicate anchor.",
        "downstream_claims": "NONE: no spans, subjects, objects, complements, clauses, connectors, trunk, or movement are produced here.",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
        for anchor in anchors:
            handle.write(json.dumps(anchor, ensure_ascii=False, sort_keys=True) + "\n")

    return metadata, anchors


def print_visible_output(book: str, input_path: Path, output_path: Path, metadata: dict[str, object], anchors: list[dict[str, object]], preview_lines: int) -> None:
    print("MNA Stage 2A — Predicate Anchors")
    print(f"BOOK: {book}")
    print(f"INPUT: {input_path}")
    print(f"OUTPUT: {output_path}")
    print(f"FINITE VERBS INHERITED: {metadata['finite_verbs_inherited']}")
    print(f"PREDICATE ANCHORS CREATED: {metadata['predicate_anchors_created']}")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, anchor in enumerate(anchors[:preview_lines], start=1):
        print(
            f"{idx:>4}. {anchor['predicate_anchor_id']} | {anchor['reference']} | "
            f"{anchor['greek_surface']} | lemma={anchor['lemma']} | "
            f"morph={anchor['morphology']} | {anchor['person_code']}{anchor['number_code']} {anchor['mood']}"
        )

    remaining = len(anchors) - min(len(anchors), preview_lines)
    if remaining:
        print(f"... {remaining} more predicate anchors written to dataset")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build MNA Stage 2A predicate anchors from Stage 1 finite verbs.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--input", help="Explicit Stage 1 finite-verb JSONL path")
    parser.add_argument("--output", help="Explicit predicate-anchor JSONL path")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    book = args.book.strip().lower()
    mna_root = mna_root_from_script()

    try:
        input_path = Path(args.input) if args.input else mna_root / "datasets" / "finite-verbs" / f"{book}.jsonl"
        output_path = Path(args.output) if args.output else mna_root / "datasets" / "predicate-anchors" / f"{book}.jsonl"
        if not input_path.is_absolute():
            input_path = (Path.cwd() / input_path).resolve()
        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()

        metadata, anchors = build_predicate_anchors(book, input_path, output_path, mna_root)
        print_visible_output(book, input_path, output_path, metadata, anchors, args.preview_lines)
        return 0 if len(anchors) == int(metadata["finite_verbs_inherited"]) else 2
    except Exception as exc:
        print("MNA Stage 2A — Predicate Anchors FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
