#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — subject refinement layer

This script refines subject continuity over the canonical independent clause
stream.

Purpose:
- reduce unresolved continuity states
- preserve auditability
- preserve certainty boundaries
- improve subject continuity precision mechanically

This layer does NOT:
- read Scripture text
- use semantics
- infer topology
- assign H0/H1/H2
- interpret discourse

Allowed input:
- MNA/data/independent-stream/<book>-independent-stream.jsonl

Outputs:
- MNA/data/refined-subjects/<book>-refined-subjects.jsonl
- MNA/data/refined-subjects/<book>-refined-subjects.tsv

Core principles:
- inheritance is local and mechanical
- inheritance stops at competing subject evidence
- explicit subject evidence outranks inherited evidence
- all inheritance remains traceable
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

MAX_INHERIT_DISTANCE = 3


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc

    return rows


def has_explicit_subject(record: dict[str, Any]) -> bool:
    source = record.get("subject_source") or ""
    return "explicit" in source


def resolved_person_number(record: dict[str, Any]) -> bool:
    return bool(record.get("subject_person") and record.get("subject_number"))


def same_person_number(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a.get("subject_person") == b.get("subject_person")
        and a.get("subject_number") == b.get("subject_number")
    )


def can_inherit(previous: dict[str, Any], current: dict[str, Any], distance: int) -> tuple[bool, str]:
    if distance > MAX_INHERIT_DISTANCE:
        return False, "inherit_distance_exceeded"

    if not resolved_person_number(previous):
        return False, "previous_subject_unresolved"

    if has_explicit_subject(current):
        return False, "current_has_explicit_subject"

    if current.get("subject_person") and current.get("subject_number"):
        if not same_person_number(previous, current):
            return False, "person_number_conflict"

    prev_independence = previous.get("independence_status")
    curr_independence = current.get("independence_status")

    if prev_independence != curr_independence:
        return False, "independence_transition"

    return True, "inheritance_allowed"


def refine_subjects(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refined = []

    recent_resolved: list[dict[str, Any]] = []

    for record in records:
        output = dict(record)

        output["subject_refinement_status"] = "unchanged"
        output["subject_refinement_source"] = None
        output["subject_inherited_from"] = None

        if not resolved_person_number(record):
            inherited = False

            for distance, previous in enumerate(reversed(recent_resolved), start=1):
                allowed, reason = can_inherit(previous, record, distance)

                if not allowed:
                    continue

                output["subject_person"] = previous.get("subject_person")
                output["subject_number"] = previous.get("subject_number")

                output["subject_refinement_status"] = "inherited"
                output["subject_refinement_source"] = reason
                output["subject_inherited_from"] = previous.get("predication_id")

                inherited = True
                break

            if not inherited:
                output["subject_refinement_status"] = "unresolved"
                output["subject_refinement_source"] = "no_valid_inheritance"

        else:
            output["subject_refinement_status"] = "explicit_or_morphological"
            output["subject_refinement_source"] = output.get("subject_source")

        refined.append(output)

        if resolved_person_number(output):
            recent_resolved.append(output)
            recent_resolved = recent_resolved[-MAX_INHERIT_DISTANCE:]

    return refined


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "stream_index",
        "book",
        "chapter",
        "verse",
        "predication_id",
        "finite_verb",
        "finite_compact",
        "subject_person",
        "subject_number",
        "subject_status",
        "subject_source",
        "subject_refinement_status",
        "subject_refinement_source",
        "subject_inherited_from",
        "independence_status",
        "subordination_status",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def process_book(book: str) -> tuple[Path, Path, int]:
    stream_path = (
        mna_root()
        / "data"
        / "independent-stream"
        / f"{book}-independent-stream.jsonl"
    )

    stream_rows = read_jsonl(stream_path)
    refined_rows = refine_subjects(stream_rows)

    out_dir = mna_root() / "data" / "refined-subjects"

    jsonl_out = out_dir / f"{book}-refined-subjects.jsonl"
    tsv_out = out_dir / f"{book}-refined-subjects.tsv"

    write_jsonl(jsonl_out, refined_rows)
    write_tsv(tsv_out, refined_rows)

    return jsonl_out, tsv_out, len(refined_rows)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_refine_subjects.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    jsonl_out, tsv_out, count = process_book(book)

    print(f"WROTE {count} refined subject record(s): {jsonl_out}")
    print(f"WROTE {count} refined subject record(s): {tsv_out}")


if __name__ == "__main__":
    main()
