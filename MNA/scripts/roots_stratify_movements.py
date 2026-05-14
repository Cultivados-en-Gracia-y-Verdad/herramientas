#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — movement stratification

Purpose:
- classify movement events before grouping into regimes
- distinguish structural movement from local grammatical turbulence
- prevent low-weight transitions from fragmenting the stream

Input:
- MNA/data/movements/<book>-movements.jsonl

Output:
- MNA/data/movement-strata/<book>-movement-strata.jsonl
- MNA/data/movement-strata/<book>-movement-strata.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theological labeling
- no topology reconstruction
- no H0/H1/H2 assignment

This layer is mechanical and auditable.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIGH_WEIGHT_REASONS = {"person_change", "number_change", "subject_shift"}
LOW_WEIGHT_REASONS = {"independence_transition", "subordination_transition"}
NOISE_REASONS = {"continuity_unresolved"}


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


def parse_reasons(value: Any) -> list[str]:
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
            return [value]

    return []


def classify_reasons(reasons: list[str]) -> tuple[str, str, int]:
    reason_set = set(reasons)

    high = sorted(reason_set & HIGH_WEIGHT_REASONS)
    low = sorted(reason_set & LOW_WEIGHT_REASONS)
    noise = sorted(reason_set & NOISE_REASONS)

    if high and low:
        return "structural", "high_and_low_weight_reasons", len(high) * 2 + len(low)

    if high:
        return "structural", "high_weight_reason", len(high) * 2

    if low:
        return "turbulence", "low_weight_transition_only", len(low)

    if noise:
        return "uncertain", "uncertainty_noise", 0

    return "stable", "no_movement_reason", 0


def stratify(row: dict[str, Any]) -> dict[str, Any]:
    reasons = parse_reasons(row.get("movement_reasons"))
    movement_class, class_source, structural_weight = classify_reasons(reasons)

    out = dict(row)
    out["movement_class"] = movement_class
    out["movement_class_source"] = class_source
    out["structural_weight"] = structural_weight
    out["regime_capable"] = movement_class == "structural"

    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(row["movement_class"] for row in rows))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "stream_index",
        "book",
        "chapter",
        "verse",
        "predication_id",
        "previous_predication_id",
        "finite_verb",
        "finite_compact",
        "subject_person",
        "subject_number",
        "continuity_status",
        "independence_status",
        "subordination_status",
        "movement_status",
        "movement_reason_count",
        "movement_reasons",
        "movement_class",
        "movement_class_source",
        "structural_weight",
        "regime_capable",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def process_book(book: str) -> tuple[Path, Path, dict[str, int]]:
    in_path = mna_root() / "data" / "movements" / f"{book}-movements.jsonl"
    rows = read_jsonl(in_path)
    strata = [stratify(row) for row in rows]

    out_dir = mna_root() / "data" / "movement-strata"
    jsonl_out = out_dir / f"{book}-movement-strata.jsonl"
    tsv_out = out_dir / f"{book}-movement-strata.tsv"

    write_jsonl(jsonl_out, strata)
    write_tsv(tsv_out, strata)

    return jsonl_out, tsv_out, summarize(strata)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_stratify_movements.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    jsonl_out, tsv_out, summary = process_book(book)

    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print("movement_class_counts:")
    for key in sorted(summary):
        print(f"  {key}: {summary[key]}")


if __name__ == "__main__":
    main()
