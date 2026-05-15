#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — subject continuity detector

This script follows the ROOTS pipeline:

predications
→ independent clause stream
→ [S] subject continuity

The script reads only the canonical independent clause stream and detects
mechanical continuity/interruption behavior between adjacent stream records.

It does NOT:
- read Scripture text
- use semantic labels
- infer topology
- assign H0/H1/H2
- attach connectors
- generate movement labels
- interpret discourse

Allowed input:
- MNA/data/independent-stream/<book>-independent-stream.jsonl

Outputs:
- MNA/data/subject-continuity/<book>-subject-continuity.jsonl
- MNA/data/subject-continuity/<book>-subject-continuity.tsv

Usage from repository root:
    python3 MNA/scripts/roots_detect_subject_continuity.py 1corintios

Usage from MNA directory:
    python3 scripts/roots_detect_subject_continuity.py 1corintios
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any


CONTINUITY_SAME = "same"
CONTINUITY_SHIFT = "shift"
CONTINUITY_UNRESOLVED = "unresolved"
CONTINUITY_INITIAL = "initial"


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    records: list[dict[str, Any]] = []

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


def continuity_status(previous: dict[str, Any] | None, current: dict[str, Any]) -> tuple[str, str]:
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


def build_subject_record(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    continuity: str,
    continuity_source: str,
) -> dict[str, Any]:
    previous_predication_id = previous.get("predication_id") if previous else None

    return {
        "stream_index": current.get("stream_index"),
        "book": current.get("book"),
        "chapter": current.get("chapter"),
        "verse": current.get("verse"),
        "predication_id": current.get("predication_id"),
        "previous_predication_id": previous_predication_id,
        "finite_verb": current.get("finite_verb"),
        "finite_lemma": current.get("finite_lemma"),
        "finite_compact": current.get("finite_compact"),
        "subject_person": current.get("subject_person"),
        "subject_number": current.get("subject_number"),
        "subject_status": current.get("subject_status"),
        "subject_source": current.get("subject_source"),
        "continuity_status": continuity,
        "continuity_source": continuity_source,
        "previous_subject_person": previous.get("subject_person") if previous else None,
        "previous_subject_number": previous.get("subject_number") if previous else None,
        "previous_finite_verb": previous.get("finite_verb") if previous else None,
        "independence_status": current.get("independence_status"),
        "subordination_status": current.get("subordination_status"),
    }


def build_subject_continuity(stream: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    previous: dict[str, Any] | None = None

    for current in stream:
        continuity, source = continuity_status(previous, current)

        out.append(
            build_subject_record(
                previous,
                current,
                continuity,
                source,
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
        "finite_lemma",
        "finite_compact",
        "subject_person",
        "subject_number",
        "subject_status",
        "subject_source",
        "continuity_status",
        "continuity_source",
        "previous_subject_person",
        "previous_subject_number",
        "previous_finite_verb",
        "independence_status",
        "subordination_status",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for record in records:
            writer.writerow(record)


def process_book(book: str) -> tuple[Path, Path, int]:
    stream_path = (
        mna_root()
        / "data"
        / "independent-stream"
        / f"{book}-independent-stream.jsonl"
    )

    stream = read_jsonl(stream_path)
    continuity_records = build_subject_continuity(stream)

    out_dir = mna_root() / "data" / "subject-continuity"

    jsonl_out = out_dir / f"{book}-subject-continuity.jsonl"
    tsv_out = out_dir / f"{book}-subject-continuity.tsv"

    write_jsonl(jsonl_out, continuity_records)
    write_tsv(tsv_out, continuity_records)

    return jsonl_out, tsv_out, len(continuity_records)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_detect_subject_continuity.py <book>\n"
            "\nExample:\n"
            "  python3 MNA/scripts/roots_detect_subject_continuity.py 1corintios",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    jsonl_out, tsv_out, count = process_book(book)

    print(f"WROTE {count} continuity record(s): {jsonl_out}")
    print(f"WROTE {count} continuity record(s): {tsv_out}")


if __name__ == "__main__":
    main()
