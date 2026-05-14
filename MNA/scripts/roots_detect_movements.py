#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — movement detector

This script follows the ROOTS pipeline:

independent clause stream
→ [S] subject continuity
→ [M] movement detection

This layer is strictly mechanical.

It detects movement candidates ONLY from:
- computed continuity interruption
- person/number change
- independence transition
- unresolved continuity transition

It does NOT:
- read Scripture text
- use semantic labels
- infer topology
- assign H0/H1/H2
- interpret discourse
- attach connectors

Preferred input:
- MNA/data/refined-subjects/<book>-refined-subjects-pass2.jsonl

Fallback inputs:
- MNA/data/refined-subjects/<book>-refined-subjects.jsonl
- MNA/data/subject-continuity/<book>-subject-continuity.jsonl

Outputs:
- MNA/data/movements/<book>-movements.jsonl
- MNA/data/movements/<book>-movements.tsv

Usage from repository root:
    python3 MNA/scripts/roots_detect_movements.py 1corintios
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

MOVEMENT_NONE = "none"
MOVEMENT_CANDIDATE = "candidate"
MOVEMENT_STRONG = "strong"

CONTINUITY_INITIAL = "initial"
CONTINUITY_SAME = "same"
CONTINUITY_SHIFT = "shift"
CONTINUITY_UNRESOLVED = "unresolved"


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    records = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    
    return records


def select_input_path(book: str) -> Path:
    root = mna_root()

    candidates = [
        root / "data" / "refined-subjects" / f"{book}-refined-subjects-pass2.jsonl",
        root / "data" / "refined-subjects" / f"{book}-refined-subjects.jsonl",
        root / "data" / "subject-continuity" / f"{book}-subject-continuity.jsonl",
    ]
    
    for path in candidates:
        if path.exists():
            return path
    
    raise FileNotFoundError(
        "No usable subject continuity input found. Tried:\n"
        + "\n".join(str(path) for path in candidates)
    )


def computed_continuity(previous: dict[str, Any] | None, current: dict[str, Any]) -> tuple[str, str]:
    existing = current.get("continuity_status")
    if existing in {CONTINUITY_INITIAL, CONTINUITY_SAME, CONTINUITY_SHIFT, CONTINUITY_UNRESOLVED}:
        return str(existing), "existing_continuity_status"

    if previous is None:
        return CONTINUITY_INITIAL, "stream_start"
    
    prev_person = previous.get("subject_person")
    prev_number = previous.get("subject_number")
    curr_person = current.get("subject_person")
    curr_number = current.get("subject_number")
    
    if not prev_person or not prev_number or not curr_person or not curr_number:
        return CONTINUITY_UNRESOLVED, "missing_subject_person_or_number"
    
    if prev_person == curr_person and prev_number == curr_number:
        return CONTINUITY_SAME, "person_number_match"
    
    return CONTINUITY_SHIFT, "person_number_change"


def detect_movement(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    continuity_status: str,
) -> tuple[str, list[str]]:
    if previous is None:
        return MOVEMENT_STRONG, ["stream_start"]

    reasons: list[str] = []
    
    if continuity_status == CONTINUITY_SHIFT:
        reasons.append("subject_shift")
    
    if continuity_status == CONTINUITY_UNRESOLVED:
        reasons.append("continuity_unresolved")
    
    prev_independence = previous.get("independence_status")
    curr_independence = current.get("independence_status")
    
    if prev_independence != curr_independence:
        reasons.append("independence_transition")
    
    prev_subordination = previous.get("subordination_status")
    curr_subordination = current.get("subordination_status")
    
    if prev_subordination != curr_subordination:
        reasons.append("subordination_transition")
    
    prev_person = previous.get("subject_person")
    curr_person = current.get("subject_person")
    
    if prev_person and curr_person and prev_person != curr_person:
        reasons.append("person_change")
    
    prev_number = previous.get("subject_number")
    curr_number = current.get("subject_number")
    
    if prev_number and curr_number and prev_number != curr_number:
        reasons.append("number_change")
    
    unique_reasons = sorted(set(reasons))
    
    if len(unique_reasons) >= 3:
        return MOVEMENT_STRONG, unique_reasons
    
    if unique_reasons:
        return MOVEMENT_CANDIDATE, unique_reasons
    
    return MOVEMENT_NONE, []


def build_record(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    continuity_status: str,
    continuity_source: str,
    movement_status: str,
    movement_reasons: list[str],
) -> dict[str, Any]:
    return {
        "stream_index": current.get("stream_index"),
        "book": current.get("book"),
        "chapter": current.get("chapter"),
        "verse": current.get("verse"),
        "predication_id": current.get("predication_id"),
        "previous_predication_id": previous.get("predication_id") if previous else None,
        "finite_verb": current.get("finite_verb"),
        "finite_compact": current.get("finite_compact"),
        "subject_person": current.get("subject_person"),
        "subject_number": current.get("subject_number"),
        "subject_refinement_status": current.get("subject_refinement_status"),
        "subject_refinement_source": current.get("subject_refinement_source"),
        "continuity_status": continuity_status,
        "continuity_source": continuity_source,
        "independence_status": current.get("independence_status"),
        "subordination_status": current.get("subordination_status"),
        "movement_status": movement_status,
        "movement_reason_count": len(movement_reasons),
        "movement_reasons": json.dumps(movement_reasons, ensure_ascii=False),
    }


def build_movements(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    previous = None

    for current in records:
        continuity_status, continuity_source = computed_continuity(previous, current)
        movement_status, reasons = detect_movement(previous, current, continuity_status)
        out.append(
            build_record(
                previous,
                current,
                continuity_status,
                continuity_source,
                movement_status,
                reasons,
            )
        )
        previous = current
    
    return out


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_tsv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "stream_index",
        "book",
        "chapter",
        "verse",
        "predication_id",
        "previous_predication_id",
        "finite_verb",
        "finite_compact",
        "subject_person",
        "subject_number",
        "subject_refinement_status",
        "subject_refinement_source",
        "continuity_status",
        "continuity_source",
        "independence_status",
        "subordination_status",
        "movement_status",
        "movement_reason_count",
        "movement_reasons",
    ]
    
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
    
        for record in records:
            writer.writerow(record)


<<<<<<< HEAD
def process_book(book: str) -> tuple[Path, Path, int]:
    continuity_path = (
        mna_root()
        / "data"
        / "refined-subjects"
        / f"{book}-refined-subjects.jsonl"
    )

    continuity_records = read_jsonl(continuity_path)
    movement_records = build_movements(continuity_records)
    def process_book(book: str) -> tuple[Path, Path, int, Path]:
        input_path = select_input_path(book)
        records = read_jsonl(input_path)
        movement_records = build_movements(records)
>>>>>>> 26bdc2ee5e541c355ac5bacc9305bb38d3524aa9

    out_dir = mna_root() / "data" / "movements"
    
    jsonl_out = out_dir / f"{book}-movements.jsonl"
    tsv_out = out_dir / f"{book}-movements.tsv"
    
    write_jsonl(jsonl_out, movement_records)
    write_tsv(tsv_out, movement_records)
    
    return jsonl_out, tsv_out, len(movement_records), input_path


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_detect_movements.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    
    jsonl_out, tsv_out, count, input_path = process_book(book)
    
    print(f"READ: {input_path}")
    print(f"WROTE {count} movement record(s): {jsonl_out}")
    print(f"WROTE {count} movement record(s): {tsv_out}")


if __name__ == "__main__":
    main()
