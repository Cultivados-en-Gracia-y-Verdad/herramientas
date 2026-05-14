#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — structural regime calibration sweep

Purpose:
- test multiple structural regime thresholds
- measure fragmentation vs. over-smoothing
- help select a stable regime sensitivity setting

Input:
- MNA/data/movement-strata/<book>-movement-strata.jsonl

Outputs:
- MNA/data/structural-regimes/calibration/<book>-regime-calibration.tsv
- MNA/data/structural-regimes/calibration/<book>-regime-calibration.md

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

DEFAULT_THRESHOLDS = [6, 8, 10, 12, 14, 16, 18, 20]
DEFAULT_WINDOWS = [3, 4, 5]
STRUCTURAL_CLASSES = {"structural"}


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def structural_pressure(rows: list[dict[str, Any]], idx: int, window: int) -> int:
    start = max(0, idx - window)
    end = min(len(rows), idx + window + 1)
    pressure = 0
    for i in range(start, end):
        row = rows[i]
        if row.get("movement_class") in STRUCTURAL_CLASSES:
            pressure += int(row.get("structural_weight") or 0)
    return pressure


def should_break(rows: list[dict[str, Any]], idx: int, threshold: int, window: int) -> bool:
    if idx == 0:
        return True

    current = rows[idx]
    previous = rows[idx - 1]

    if current.get("chapter") != previous.get("chapter"):
        return True

    if current.get("movement_class") != "structural":
        return False

    return structural_pressure(rows, idx, window) >= threshold


def build_group_lengths(rows: list[dict[str, Any]], threshold: int, window: int) -> list[int]:
    lengths: list[int] = []
    current_len = 0

    for idx, _row in enumerate(rows):
        if should_break(rows, idx, threshold, window):
            if current_len:
                lengths.append(current_len)
            current_len = 1
        else:
            current_len += 1

    if current_len:
        lengths.append(current_len)

    return lengths


def summarize(rows: list[dict[str, Any]], threshold: int, window: int) -> dict[str, Any]:
    lengths = build_group_lengths(rows, threshold, window)
    total_records = len(rows)
    group_count = len(lengths)
    single_record = sum(1 for length in lengths if length == 1)
    small_groups = sum(1 for length in lengths if length <= 2)
    large_groups = sum(1 for length in lengths if length >= 20)

    sorted_lengths = sorted(lengths)
    median = sorted_lengths[len(sorted_lengths) // 2] if sorted_lengths else 0

    return {
        "threshold": threshold,
        "window": window,
        "total_records": total_records,
        "regime_count": group_count,
        "single_record_regimes": single_record,
        "single_record_pct": round(single_record / group_count, 4) if group_count else 0,
        "small_regimes_le_2": small_groups,
        "small_regimes_le_2_pct": round(small_groups / group_count, 4) if group_count else 0,
        "large_regimes_ge_20": large_groups,
        "avg_regime_length": round(total_records / group_count, 2) if group_count else 0,
        "median_regime_length": median,
        "max_regime_length": max(lengths) if lengths else 0,
        "min_regime_length": min(lengths) if lengths else 0,
    }


def score(row: dict[str, Any]) -> float:
    """Lower score is better: penalize both fragmentation and oversmoothing."""
    single_penalty = float(row["single_record_pct"]) * 3
    small_penalty = float(row["small_regimes_le_2_pct"]) * 2
    oversmooth_penalty = max(0, float(row["max_regime_length"]) - 80) / 80
    group_count_penalty = abs(float(row["regime_count"]) - 120) / 120
    return round(single_penalty + small_penalty + oversmooth_penalty + group_count_penalty, 4)


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_md(path: Path, rows: list[dict[str, Any]], book: str) -> None:
    best = sorted(rows, key=lambda r: r["calibration_score"])[:10]
    lines: list[str] = []
    lines.append(f"# {book} Structural Regime Calibration")
    lines.append("")
    lines.append("## Source Boundary")
    lines.append("")
    lines.append("This report is generated only from movement-strata JSONL records.")
    lines.append("No Scripture text, commentary, semantic labels, or external sources are used.")
    lines.append("")
    lines.append("## Best Candidate Settings")
    lines.append("")
    for row in best:
        lines.append(
            f"- threshold={row['threshold']} window={row['window']} | regimes={row['regime_count']} | avg={row['avg_regime_length']} | median={row['median_regime_length']} | singles={row['single_record_pct']} | max={row['max_regime_length']} | score={row['calibration_score']}"
        )
    lines.append("")
    lines.append("## Full Sweep")
    lines.append("")
    for row in rows:
        lines.append(
            f"- threshold={row['threshold']} window={row['window']} | regimes={row['regime_count']} | singles={row['single_record_regimes']} | avg={row['avg_regime_length']} | median={row['median_regime_length']} | max={row['max_regime_length']} | score={row['calibration_score']}"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) not in {2, 3, 4}:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_calibrate_structural_regimes.py <book> [thresholds] [windows]\n"
            "\nExamples:\n"
            "  python3 MNA/scripts/roots_calibrate_structural_regimes.py 1corintios\n"
            "  python3 MNA/scripts/roots_calibrate_structural_regimes.py 1corintios 8,10,12 3,4,5",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    thresholds = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) >= 3 else DEFAULT_THRESHOLDS
    windows = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) == 4 else DEFAULT_WINDOWS

    in_path = mna_root() / "data" / "movement-strata" / f"{book}-movement-strata.jsonl"
    rows = read_jsonl(in_path)

    results: list[dict[str, Any]] = []
    for window in windows:
        for threshold in thresholds:
            row = summarize(rows, threshold, window)
            row["calibration_score"] = score(row)
            results.append(row)

    results.sort(key=lambda r: (r["calibration_score"], r["threshold"], r["window"]))

    out_dir = mna_root() / "data" / "structural-regimes" / "calibration"
    tsv_out = out_dir / f"{book}-regime-calibration.tsv"
    md_out = out_dir / f"{book}-regime-calibration.md"

    write_tsv(tsv_out, results)
    write_md(md_out, results, book)

    print(f"wrote: {tsv_out}")
    print(f"wrote: {md_out}")
    print("best:")
    for row in results[:5]:
        print(
            f"  threshold={row['threshold']} window={row['window']} regimes={row['regime_count']} avg={row['avg_regime_length']} median={row['median_regime_length']} singles={row['single_record_pct']} max={row['max_regime_length']} score={row['calibration_score']}"
        )


if __name__ == "__main__":
    main()
