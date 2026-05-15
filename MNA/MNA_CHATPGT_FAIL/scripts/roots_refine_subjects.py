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
- finite verb morphology may supply grammatical subject person/number
- inheritance is local and mechanical
- inheritance stops at competing subject evidence
- explicit subject evidence outranks inherited evidence
- all recovery remains traceable
"""

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

MAX_INHERIT_DISTANCE = 3

CONTINUITY_INITIAL = "initial"
CONTINUITY_SAME = "same"
CONTINUITY_SHIFT = "shift"
CONTINUITY_UNRESOLVED = "unresolved"

FINITE_COMPACT_PERSON_NUMBER = re.compile(r"^V-[A-Z]+-([123])([SP])$")


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


def finite_person_number(record: dict[str, Any]) -> tuple[str | None, str | None]:
    compact = str(record.get("finite_compact") or "")
    match = FINITE_COMPACT_PERSON_NUMBER.match(compact)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def apply_finite_morphology_fallback(record: dict[str, Any]) -> bool:
    """Fill only grammatical person/number from finite morphology.

    This does not identify a lexical/semantic subject. It only records the
    grammatical subject features already encoded in the finite verb.
    """
    if record.get("subject_person") and record.get("subject_number"):
        return False

    person, number = finite_person_number(record)
    if not person or not number:
        return False

    record["subject_person"] = person
    record["subject_number"] = number
    record["subject_refinement_status"] = "finite_morphology_fallback"
    record["subject_refinement_source"] = "finite_compact_person_number"
    record["subject_inherited_from"] = None
    return True


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


def compute_continuity(previous: dict[str, Any] | None, current: dict[str, Any]) -> tuple[str, str]:
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

        if resolved_person_number(record):
            output["subject_refinement_status"] = "explicit_or_morphological"
            output["subject_refinement_source"] = output.get("subject_source")

        elif apply_finite_morphology_fallback(output):
            pass

        else:
            inherited = False

            for distance, previous in enumerate(reversed(recent_resolved), start=1):
                allowed, reason = can_inherit(previous, output, distance)

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
                output["subject_refinement_source"] = "no_valid_inheritance_or_finite_fallback"

        refined.append(output)

        if resolved_person_number(output):
            recent_resolved.append(output)
            recent_resolved = recent_resolved[-MAX_INHERIT_DISTANCE:]

    previous: dict[str, Any] | None = None
    for row in refined:
        continuity_status, continuity_source = compute_continuity(previous, row)
        row["continuity_status"] = continuity_status
        row["continuity_source"] = continuity_source
        previous = row

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
        "continuity_status",
        "continuity_source",
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
