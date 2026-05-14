#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — short regime persistence merge

Purpose:
- collapse isolated structural spikes
- require minimum viable persistence for regime survival
- merge weak regimes back into neighboring continuity environments

Input:
- MNA/data/structural-regimes/<book>-structural-regimes.jsonl

Output:
- MNA/data/structural-regimes/<book>-structural-regimes-merged.jsonl
- MNA/data/structural-regimes/<book>-structural-regimes-merged.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theology
- no H0/H1/H2 assignment
- no topology reconstruction
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

MIN_VIABLE_LENGTH = 3
HIGH_WEIGHT_SURVIVAL = 16


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


def survives(row: dict[str, Any]) -> bool:
    length = int(row.get("record_count") or 0)
    weight = int(row.get("total_structural_weight") or 0)

    if length >= MIN_VIABLE_LENGTH:
        return True

    if weight >= HIGH_WEIGHT_SURVIVAL:
        return True

    return False


def compatible(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a.get("book") == b.get("book")
    )


def merge_rows(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    target["end_stream_index"] = source.get("end_stream_index")
    target["end_reference"] = source.get("end_reference")
    target["last_predication_id"] = source.get("last_predication_id")
    target["last_finite_verb"] = source.get("last_finite_verb")

    target["record_count"] = int(target.get("record_count") or 0) + int(source.get("record_count") or 0)

    target["total_structural_weight"] = (
        int(target.get("total_structural_weight") or 0)
        + int(source.get("total_structural_weight") or 0)
    )

    target.setdefault("merged_regimes", [])
    target["merged_regimes"].append(source.get("structural_regime_id"))

    return target


def process(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    output = []

    idx = 0

    while idx < len(rows):
        current = dict(rows[idx])

        if survives(current):
            output.append(current)
            idx += 1
            continue

        merged = False

        if output and compatible(output[-1], current):
            output[-1] = merge_rows(output[-1], current)
            merged = True

        elif idx + 1 < len(rows):
            next_row = dict(rows[idx + 1])

            if compatible(current, next_row):
                merged_row = merge_rows(current, next_row)
                output.append(merged_row)
                idx += 2
                merged = True

        if not merged:
            output.append(current)
            idx += 1
        else:
            idx += 1

    for i, row in enumerate(output, start=1):
        row["merged_regime_id"] = f"SMR{i:04d}"

    return output


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
            "Usage: python3 MNA/scripts/roots_merge_short_regimes.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    in_path = (
        mna_root()
        / "data"
        / "structural-regimes"
        / f"{book}-structural-regimes.jsonl"
    )

    rows = read_jsonl(in_path)
    merged = process(rows)

    out_dir = mna_root() / "data" / "structural-regimes"

    jsonl_out = out_dir / f"{book}-structural-regimes-merged.jsonl"
    tsv_out = out_dir / f"{book}-structural-regimes-merged.tsv"

    write_jsonl(jsonl_out, merged)
    write_tsv(tsv_out, merged)

    print(f"merged_structural_regimes = {len(merged)}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")


if __name__ == "__main__":
    main()
