#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — Paso 10 mechanical label pattern detection

Purpose:
- detect repeated contiguous label sequences
- support ROOTS Paso 10 preparation
- remain strictly mechanical and auditable

Input:
- MNA/data/label-candidates/<book>-label-candidates.jsonl

Outputs:
- MNA/data/label-patterns/<book>-label-patterns.jsonl
- MNA/data/label-patterns/<book>-label-patterns.tsv
- MNA/data/label-patterns/<book>-pattern-occurrences.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theology
- no H0/H1/H2 assignment
- no unit boundary assignment
- no discourse reconstruction

This layer detects ONLY repeated mechanical label sequences.
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MIN_PATTERN_LENGTH = 2
MAX_PATTERN_LENGTH = 6
MIN_PATTERN_FREQUENCY = 3


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[dict[str, Any]] = []
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


def ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row.get("stream_index") or 0))


def label_for(row: dict[str, Any]) -> str:
    label = row.get("label_candidate")
    if label:
        return str(label)
    return "UNLABELED"


def pattern_key(labels: list[str]) -> str:
    return " > ".join(labels)


def collect_patterns(rows: list[dict[str, Any]]) -> tuple[Counter[str], dict[str, list[dict[str, Any]]]]:
    counts: Counter[str] = Counter()
    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)

    labels = [label_for(row) for row in rows]

    for start in range(len(rows)):
        for length in range(MIN_PATTERN_LENGTH, MAX_PATTERN_LENGTH + 1):
            end = start + length
            if end > len(rows):
                continue

            seq = labels[start:end]

            # Patterns made entirely of UNLABELED are not useful as Paso 10 candidates.
            if all(label == "UNLABELED" for label in seq):
                continue

            key = pattern_key(seq)
            counts[key] += 1
            occurrences[key].append({
                "pattern_key": key,
                "pattern_length": length,
                "start_stream_index": rows[start].get("stream_index"),
                "end_stream_index": rows[end - 1].get("stream_index"),
                "start_reference": f"{rows[start].get('chapter')}:{rows[start].get('verse')}",
                "end_reference": f"{rows[end - 1].get('chapter')}:{rows[end - 1].get('verse')}",
                "start_predication_id": rows[start].get("predication_id"),
                "end_predication_id": rows[end - 1].get("predication_id"),
            })

    return counts, occurrences


def build_pattern_records(
    counts: Counter[str],
    occurrences: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = [
        (key, count)
        for key, count in counts.items()
        if count >= MIN_PATTERN_FREQUENCY
    ]

    eligible.sort(key=lambda item: (-item[1], item[0]))

    pattern_rows: list[dict[str, Any]] = []
    occurrence_rows: list[dict[str, Any]] = []

    for idx, (key, count) in enumerate(eligible, start=1):
        pattern_id = f"P{idx:03d}"
        labels = key.split(" > ")
        occs = occurrences[key]

        pattern_rows.append({
            "pattern_candidate_id": pattern_id,
            "pattern_key": key,
            "pattern_length": len(labels),
            "frequency": count,
            "first_start_reference": occs[0].get("start_reference"),
            "first_end_reference": occs[0].get("end_reference"),
            "label_sequence": json.dumps(labels, ensure_ascii=False),
            "pattern_status": "candidate",
        })

        for occ_idx, occurrence in enumerate(occs, start=1):
            out = dict(occurrence)
            out["pattern_candidate_id"] = pattern_id
            out["occurrence_index"] = occ_idx
            occurrence_rows.append(out)

    return pattern_rows, occurrence_rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def process_book(book: str) -> tuple[int, int, Path, Path, Path]:
    in_path = mna_root() / "data" / "label-candidates" / f"{book}-label-candidates.jsonl"
    rows = ordered(read_jsonl(in_path))

    counts, occurrences = collect_patterns(rows)
    pattern_rows, occurrence_rows = build_pattern_records(counts, occurrences)

    out_dir = mna_root() / "data" / "label-patterns"
    jsonl_out = out_dir / f"{book}-label-patterns.jsonl"
    tsv_out = out_dir / f"{book}-label-patterns.tsv"
    occurrences_out = out_dir / f"{book}-pattern-occurrences.tsv"

    write_jsonl(jsonl_out, pattern_rows)
    write_tsv(tsv_out, pattern_rows)
    write_tsv(occurrences_out, occurrence_rows)

    return len(pattern_rows), len(occurrence_rows), jsonl_out, tsv_out, occurrences_out


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_detect_label_patterns.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    pattern_count, occurrence_count, jsonl_out, tsv_out, occurrences_out = process_book(book)

    print(f"pattern_candidates = {pattern_count}")
    print(f"pattern_occurrences = {occurrence_count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {occurrences_out}")


if __name__ == "__main__":
    main()
