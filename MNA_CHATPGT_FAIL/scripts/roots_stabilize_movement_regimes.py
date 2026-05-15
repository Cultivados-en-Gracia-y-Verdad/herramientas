#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — stabilized movement regimes

Purpose:
- reduce over-fragmentation in movement grouping
- distinguish local turbulence from regime breaks
- require sustained instability before splitting groups

This layer remains strictly mechanical.

Input:
- MNA/data/movements/<book>-movements.jsonl

Output:
- MNA/data/movement-regimes/<book>-movement-regimes.jsonl
- MNA/data/movement-regimes/<book>-movement-regimes.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theological labeling
- no topology reconstruction
- no H0/H1/H2 assignment
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MIN_BREAK_SCORE = 3
WINDOW = 3


BREAK_REASON_WEIGHTS = {
    "person_change": 2,
    "number_change": 2,
    "independence_transition": 1,
    "subordination_transition": 1,
    "subject_shift": 2,
}


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    return rows


def parse_reasons(row: dict[str, Any]) -> list[str]:
    value = row.get("movement_reasons")

    if value is None:
        return []

    if isinstance(value, list):
        return [str(v) for v in value]

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except json.JSONDecodeError:
            return []

    return []


def instability_score(rows: list[dict[str, Any]], idx: int) -> int:
    score = 0

    start = max(0, idx - WINDOW)
    end = min(len(rows), idx + WINDOW + 1)

    for i in range(start, end):
        row = rows[i]

        for reason in parse_reasons(row):
            score += BREAK_REASON_WEIGHTS.get(reason, 0)

        if row.get("movement_status") == "strong":
            score += 1

    return score


def should_break(rows: list[dict[str, Any]], idx: int) -> bool:
    if idx == 0:
        return True

    current = rows[idx]
    previous = rows[idx - 1]

    if current.get("chapter") != previous.get("chapter"):
        return True

    score = instability_score(rows, idx)

    return score >= MIN_BREAK_SCORE


def summarize(group_id: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[0]
    last = rows[-1]

    status_counter = Counter(row.get("movement_status") or "none" for row in rows)
    reason_counter = Counter()

    for row in rows:
        reason_counter.update(parse_reasons(row))

    return {
        "movement_regime_id": f"MR{group_id:04d}",
        "group_index": group_id,
        "book": first.get("book"),
        "start_stream_index": first.get("stream_index"),
        "end_stream_index": last.get("stream_index"),
        "start_reference": f"{first.get('chapter')}:{first.get('verse')}",
        "end_reference": f"{last.get('chapter')}:{last.get('verse')}",
        "record_count": len(rows),
        "dominant_movement_status": status_counter.most_common(1)[0][0],
        "movement_status_counts": json.dumps(dict(sorted(status_counter.items())), ensure_ascii=False),
        "movement_reason_counts": json.dumps(dict(sorted(reason_counter.items())), ensure_ascii=False),
        "first_predication_id": first.get("predication_id"),
        "last_predication_id": last.get("predication_id"),
    }


def build_regimes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    regimes = []
    current = []

    for idx, row in enumerate(rows):
        if should_break(rows, idx):
            if current:
                regimes.append(current)
            current = [row]
        else:
            current.append(row)

    if current:
        regimes.append(current)

    return [summarize(i, group) for i, group in enumerate(regimes, start=1)]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
            delimiter="\t",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(row)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_stabilize_movement_regimes.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    in_path = (
        mna_root()
        / "data"
        / "movements"
        / f"{book}-movements.jsonl"
    )

    rows = read_jsonl(in_path)
    regimes = build_regimes(rows)

    out_dir = mna_root() / "data" / "movement-regimes"

    jsonl_out = out_dir / f"{book}-movement-regimes.jsonl"
    tsv_out = out_dir / f"{book}-movement-regimes.tsv"

    write_jsonl(jsonl_out, regimes)
    write_tsv(tsv_out, regimes)

    print(f"movement_regimes = {len(regimes)}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")


if __name__ == "__main__":
    main()
