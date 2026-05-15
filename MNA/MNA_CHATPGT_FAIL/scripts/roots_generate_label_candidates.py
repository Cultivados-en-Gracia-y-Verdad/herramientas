#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — mechanical label candidate generation

Purpose:
- generate recurring structural label candidates
- support ROOTS Paso 9 preparation
- remain strictly mechanical and auditable

Inputs:
- MNA/data/movements/<book>-movements.jsonl
- MNA/data/structural-signatures/<book>-structural-signatures.jsonl

Outputs:
- MNA/data/label-candidates/<book>-label-candidates.jsonl
- MNA/data/label-candidates/<book>-label-candidates.tsv
- MNA/data/label-candidates/<book>-label-summary.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theology
- no H0/H1/H2 assignment
- no discourse reconstruction

This layer assigns ONLY recurring mechanical structural labels.
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

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
    return sorted(rows, key=lambda row: int(row.get("stream_index") or row.get("start_stream_index") or 0))



def movement_signature(row: dict[str, Any]) -> str:
    continuity = str(row.get("continuity_status") or "unknown")
    movement = str(row.get("movement_status") or "unknown")
    independence = str(row.get("independence_status") or "unknown")
    subordination = str(row.get("subordination_status") or "unknown")

    return "|".join([
        continuity,
        movement,
        independence,
        subordination,
    ])



def build_pattern_inventory(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()

    for row in rows:
        counter[movement_signature(row)] += 1

    return counter



def assign_labels(rows: list[dict[str, Any]], inventory: Counter[str]) -> list[dict[str, Any]]:
    eligible_patterns = [
        pattern
        for pattern, count in inventory.items()
        if count >= MIN_PATTERN_FREQUENCY
    ]

    eligible_patterns.sort(key=lambda p: (-inventory[p], p))

    label_map = {
        pattern: f"L{i:03d}"
        for i, pattern in enumerate(eligible_patterns, start=1)
    }

    out: list[dict[str, Any]] = []

    for row in rows:
        pattern = movement_signature(row)

        labeled = dict(row)

        labeled["movement_signature"] = pattern
        labeled["movement_signature_frequency"] = inventory[pattern]
        labeled["label_candidate"] = label_map.get(pattern)
        labeled["label_candidate_status"] = (
            "candidate"
            if pattern in label_map
            else "unlabeled_low_frequency"
        )

        out.append(labeled)

    return out



def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        label = row.get("label_candidate")
        if label:
            grouped[str(label)].append(row)

    summary: list[dict[str, Any]] = []

    for label in sorted(grouped):
        members = grouped[label]

        continuity_counter = Counter(
            str(row.get("continuity_status") or "unknown")
            for row in members
        )

        movement_counter = Counter(
            str(row.get("movement_status") or "unknown")
            for row in members
        )

        summary.append({
            "label_candidate": label,
            "member_count": len(members),
            "dominant_continuity": continuity_counter.most_common(1)[0][0],
            "dominant_movement": movement_counter.most_common(1)[0][0],
            "movement_signature": members[0].get("movement_signature"),
        })

    return summary



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
    movements_path = (
        mna_root()
        / "data"
        / "movements"
        / f"{book}-movements.jsonl"
    )

    rows = ordered(read_jsonl(movements_path))

    inventory = build_pattern_inventory(rows)
    labeled = assign_labels(rows, inventory)
    summary = build_summary(labeled)

    out_dir = mna_root() / "data" / "label-candidates"

    jsonl_out = out_dir / f"{book}-label-candidates.jsonl"
    tsv_out = out_dir / f"{book}-label-candidates.tsv"
    summary_out = out_dir / f"{book}-label-summary.tsv"

    write_jsonl(jsonl_out, labeled)
    write_tsv(tsv_out, labeled)
    write_tsv(summary_out, summary)

    label_count = len({row["label_candidate"] for row in labeled if row.get("label_candidate")})

    return label_count, len(labeled), jsonl_out, tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_generate_label_candidates.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    label_count, record_count, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"label_candidates = {label_count}")
    print(f"movement_records = {record_count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
