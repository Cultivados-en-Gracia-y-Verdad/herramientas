#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — predication chapter metrics

Reads generated predication JSONL files and produces objective chapter-level
metrics. This script does not infer topology, attach connectors, or create
ROOTS structure. It only counts what is already present in the predication
records.

Usage from repository root:
    python3 MNA/scripts/roots_predication_metrics.py 1corintios

Usage from MNA directory:
    python3 scripts/roots_predication_metrics.py 1corintios

Default output:
    MNA/data/predications/reports/<book>-chapter-metrics.tsv
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PERSON_KEYS = ["1S", "1P", "2S", "2P", "3S", "3P"]


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


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


def chapter_from_filename(book: str, path: Path) -> int | None:
    match = re.fullmatch(rf"{re.escape(book)}-(\d+)\.jsonl", path.name)
    if not match:
        return None
    return int(match.group(1))


def person_key(finite_compact: str | None) -> str | None:
    if not finite_compact:
        return None

    for key in PERSON_KEYS:
        if finite_compact.endswith(key):
            return key

    return None


def build_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    finite_counter: Counter[str] = Counter()
    subject_counter: Counter[str] = Counter()
    independence_counter: Counter[str] = Counter()
    subordination_counter: Counter[str] = Counter()
    finite_per_verse: defaultdict[int, int] = defaultdict(int)
    verses: set[int] = set()

    for record in records:
        verse = int(record["verse"])
        verses.add(verse)
        finite_per_verse[verse] += 1

        key = person_key(record.get("finite_compact"))
        if key:
            finite_counter[key] += 1

        subject = record.get("subject") or {}
        subject_source = subject.get("subject_source") or "unresolved"
        subject_counter[subject_source] += 1

        independence = record.get("independence") or {}
        independence_status = independence.get("independence_status") or "unresolved"
        independence_counter[independence_status] += 1

        subordination = record.get("subordination") or {}
        subordination_status = subordination.get("subordination_status") or "unresolved"
        subordination_counter[subordination_status] += 1

    total_predications = len(records)
    total_verses_with_predications = len(verses)

    metrics: dict[str, Any] = {
        "total_predications": total_predications,
        "verses_with_predications": total_verses_with_predications,
        "predications_per_verse": round(total_predications / total_verses_with_predications, 2)
        if total_verses_with_predications
        else 0,
        "max_predications_single_verse": max(finite_per_verse.values()) if finite_per_verse else 0,
    }

    for key in PERSON_KEYS:
        metrics[f"finite_{key}"] = finite_counter[key]

    metrics["subject_morphology"] = subject_counter["finite_verb_morphology"]
    metrics["subject_candidate"] = sum(
        count
        for source, count in subject_counter.items()
        if source not in {"finite_verb_morphology", "unresolved"}
    )
    metrics["subject_unresolved"] = subject_counter["unresolved"]

    metrics["independent_candidate"] = independence_counter["candidate"]
    metrics["independence_unresolved"] = independence_counter["unresolved"]

    metrics["subordination_candidate"] = subordination_counter["candidate"]
    metrics["subordination_not_detected"] = subordination_counter["not_detected"]
    metrics["subordination_unresolved"] = subordination_counter["unresolved"]

    return metrics


def process_book(book: str, output_path: Path | None = None) -> Path:
    root = mna_root()
    predications_dir = root / "data" / "predications"
    reports_dir = predications_dir / "reports"

    if not predications_dir.exists():
        raise FileNotFoundError(predications_dir)

    files: list[tuple[int, Path]] = []
    for path in predications_dir.glob(f"{book}-*.jsonl"):
        chapter = chapter_from_filename(book, path)
        if chapter is not None:
            files.append((chapter, path))

    files.sort(key=lambda item: item[0])

    if not files:
        raise FileNotFoundError(f"No chapter predication files found for {book!r} in {predications_dir}")

    if output_path is None:
        reports_dir.mkdir(parents=True, exist_ok=True)
        output_path = reports_dir / f"{book}-chapter-metrics.tsv"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "book",
        "chapter",
        "total_predications",
        "verses_with_predications",
        "predications_per_verse",
        "max_predications_single_verse",
        "finite_1S",
        "finite_1P",
        "finite_2S",
        "finite_2P",
        "finite_3S",
        "finite_3P",
        "subject_morphology",
        "subject_candidate",
        "subject_unresolved",
        "independent_candidate",
        "independence_unresolved",
        "subordination_candidate",
        "subordination_not_detected",
        "subordination_unresolved",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for chapter, path in files:
            records = read_jsonl(path)
            metrics = build_metrics(records)
            row = {"book": book, "chapter": chapter, **metrics}
            writer.writerow(row)

    return output_path


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_predication_metrics.py <book> [output.tsv]\n"
            "\nExample:\n"
            "  python3 MNA/scripts/roots_predication_metrics.py 1corintios",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    output_path = Path(sys.argv[2]) if len(sys.argv) == 3 else None

    written = process_book(book, output_path)
    print(f"WROTE: {written}")


if __name__ == "__main__":
    main()
