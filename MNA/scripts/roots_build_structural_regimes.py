#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — structural regime builder

Purpose:
- construct persistent structural environments
- ignore turbulence-only fluctuations
- create regime boundaries only from sustained structural pressure

Input:
- MNA/data/movement-strata/<book>-movement-strata.jsonl

Output:
- MNA/data/structural-regimes/<book>-structural-regimes.jsonl
- MNA/data/structural-regimes/<book>-structural-regimes.tsv

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
from collections import Counter
from pathlib import Path
from typing import Any

PERSISTENCE_WINDOW = 4
REGIME_THRESHOLD = 6


STRUCTURAL_CLASSES = {"structural"}


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



def structural_pressure(rows: list[dict[str, Any]], idx: int) -> int:
    start = max(0, idx - PERSISTENCE_WINDOW)
    end = min(len(rows), idx + PERSISTENCE_WINDOW + 1)

    pressure = 0

    for i in range(start, end):
        row = rows[i]

        if row.get("movement_class") in STRUCTURAL_CLASSES:
            pressure += int(row.get("structural_weight") or 0)

    return pressure



def should_break(rows: list[dict[str, Any]], idx: int) -> bool:
    if idx == 0:
        return True

    current = rows[idx]
    previous = rows[idx - 1]

    if current.get("chapter") != previous.get("chapter"):
        return True

    if current.get("movement_class") != "structural":
        return False

    pressure = structural_pressure(rows, idx)

    return pressure >= REGIME_THRESHOLD



def summarize(regime_id: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[0]
    last = rows[-1]

    class_counter = Counter(row.get("movement_class") for row in rows)
    status_counter = Counter(row.get("movement_status") for row in rows)

    total_weight = sum(int(row.get("structural_weight") or 0) for row in rows)

    return {
        "structural_regime_id": f"SR{regime_id:04d}",
        "group_index": regime_id,
        "book": first.get("book"),
        "start_stream_index": first.get("stream_index"),
        "end_stream_index": last.get("stream_index"),
        "start_reference": f"{first.get('chapter')}:{first.get('verse')}",
        "end_reference": f"{last.get('chapter')}:{last.get('verse')}",
        "record_count": len(rows),
        "total_structural_weight": total_weight,
        "movement_class_counts": json.dumps(dict(sorted(class_counter.items())), ensure_ascii=False),
        "movement_status_counts": json.dumps(dict(sorted(status_counter.items())), ensure_ascii=False),
        "first_predication_id": first.get("predication_id"),
        "last_predication_id": last.get("predication_id"),
        "first_finite_verb": first.get("finite_verb"),
        "last_finite_verb": last.get("finite_verb"),
    }



def build_regimes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = []
    current = []

    for idx, row in enumerate(rows):
        if should_break(rows, idx):
            if current:
                groups.append(current)
            current = [row]
        else:
            current.append(row)

    if current:
        groups.append(current)

    return [summarize(i, group) for i, group in enumerate(groups, start=1)]



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
            "Usage: python3 MNA/scripts/roots_build_structural_regimes.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    in_path = (
        mna_root()
        / "data"
        / "movement-strata"
        / f"{book}-movement-strata.jsonl"
    )

    rows = read_jsonl(in_path)
    regimes = build_regimes(rows)

    out_dir = mna_root() / "data" / "structural-regimes"

    jsonl_out = out_dir / f"{book}-structural-regimes.jsonl"
    tsv_out = out_dir / f"{book}-structural-regimes.tsv"

    write_jsonl(jsonl_out, regimes)
    write_tsv(tsv_out, regimes)

    print(f"structural_regimes = {len(regimes)}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")


if __name__ == "__main__":
    main()
