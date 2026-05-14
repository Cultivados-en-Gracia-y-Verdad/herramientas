#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — independent clause stream builder

This script follows the ROOTS pipeline:

Greek tokens
→ MorphGNT morphology
→ finite verbs
→ finite predication candidates
→ confirmed predications
→ independence testing
→ independent clause stream

This script starts at the generated predication JSONL layer and produces the
ordered independent clause stream.

It does NOT:
- read chapter metrics
- read similarity reports
- infer topology
- attach connectors
- assign H0/H1/H2
- generate labels
- interpret discourse

Allowed input:
- MNA/data/predications/<book>-<chapter>.jsonl

Outputs:
- MNA/data/independent-stream/<book>-independent-stream.jsonl
- MNA/data/independent-stream/<book>-independent-stream.tsv

Usage from repository root:
    python3 MNA/scripts/roots_build_independent_stream.py 1corintios

Usage from MNA directory:
    python3 scripts/roots_build_independent_stream.py 1corintios
"""

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

INCLUDED_INDEPENDENCE_STATUSES = {"confirmed", "candidate", "unresolved"}


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def chapter_from_filename(book: str, path: Path) -> int | None:
    match = re.fullmatch(rf"{re.escape(book)}-(\d+)\.jsonl", path.name)
    if not match:
        return None
    return int(match.group(1))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def predication_sort_key(record: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(record["chapter"]),
        int(record["verse"]),
        int(record["g_idx"]),
    )


def include_in_stream(record: dict[str, Any]) -> bool:
    independence = record.get("independence") or {}
    status = independence.get("independence_status") or "unresolved"
    return status in INCLUDED_INDEPENDENCE_STATUSES


def flatten_record(record: dict[str, Any], stream_index: int) -> dict[str, Any]:
    subject = record.get("subject") or {}
    independence = record.get("independence") or {}
    subordination = record.get("subordination") or {}
    certainty = record.get("certainty") or {}

    return {
        "stream_index": stream_index,
        "book": record.get("book"),
        "chapter": int(record.get("chapter")),
        "verse": int(record.get("verse")),
        "g_idx": record.get("g_idx"),
        "predication_id": record.get("predication_id"),
        "finite_verb": record.get("finite_verb"),
        "finite_lemma": record.get("finite_lemma"),
        "finite_morphgnt": record.get("finite_morphgnt"),
        "finite_compact": record.get("finite_compact"),
        "nbla_idx": record.get("nbla_idx"),
        "nbla_text": record.get("nbla_text"),
        "subject_status": subject.get("subject_status"),
        "subject_source": subject.get("subject_source"),
        "subject_token": subject.get("subject_token"),
        "subject_person": subject.get("subject_person"),
        "subject_number": subject.get("subject_number"),
        "independence_status": independence.get("independence_status"),
        "independence_source": independence.get("independence_source"),
        "subordination_status": subordination.get("subordination_status"),
        "subordination_source": subordination.get("subordination_source"),
        "subordination_markers": json.dumps(
            subordination.get("subordination_markers") or [],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "certainty_finite_verb": certainty.get("finite_verb"),
        "certainty_predication": certainty.get("predication"),
        "certainty_independence": certainty.get("independence"),
    }


def load_book_predications(book: str) -> list[dict[str, Any]]:
    predications_dir = mna_root() / "data" / "predications"
    if not predications_dir.exists():
        raise FileNotFoundError(predications_dir)

    files: list[tuple[int, Path]] = []
    for path in predications_dir.glob(f"{book}-*.jsonl"):
        chapter = chapter_from_filename(book, path)
        if chapter is not None:
            files.append((chapter, path))

    files.sort(key=lambda item: item[0])

    if not files:
        raise FileNotFoundError(f"No predication files found for {book!r} in {predications_dir}")

    records: list[dict[str, Any]] = []
    for _chapter, path in files:
        records.extend(read_jsonl(path))

    records.sort(key=predication_sort_key)
    return records


def build_stream(book: str) -> list[dict[str, Any]]:
    records = load_book_predications(book)
    stream_records: list[dict[str, Any]] = []

    for record in records:
        if not include_in_stream(record):
            continue
        stream_records.append(flatten_record(record, len(stream_records) + 1))

    return stream_records


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
        "g_idx",
        "predication_id",
        "finite_verb",
        "finite_lemma",
        "finite_morphgnt",
        "finite_compact",
        "nbla_idx",
        "nbla_text",
        "subject_status",
        "subject_source",
        "subject_token",
        "subject_person",
        "subject_number",
        "independence_status",
        "independence_source",
        "subordination_status",
        "subordination_source",
        "subordination_markers",
        "certainty_finite_verb",
        "certainty_predication",
        "certainty_independence",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def process_book(book: str) -> tuple[Path, Path, int]:
    out_dir = mna_root() / "data" / "independent-stream"
    stream = build_stream(book)

    jsonl_path = out_dir / f"{book}-independent-stream.jsonl"
    tsv_path = out_dir / f"{book}-independent-stream.tsv"

    write_jsonl(jsonl_path, stream)
    write_tsv(tsv_path, stream)

    return jsonl_path, tsv_path, len(stream)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_build_independent_stream.py <book>\n"
            "\nExample:\n"
            "  python3 MNA/scripts/roots_build_independent_stream.py 1corintios",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    jsonl_path, tsv_path, count = process_book(book)
    print(f"WROTE {count} stream record(s): {jsonl_path}")
    print(f"WROTE {count} stream record(s): {tsv_path}")


if __name__ == "__main__":
    main()
