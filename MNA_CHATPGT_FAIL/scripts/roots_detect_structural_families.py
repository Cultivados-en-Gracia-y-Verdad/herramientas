#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — structural family detection

Purpose:
- detect recurring structural behavior families
- cluster regimes mechanically by grammatical behavior
- prepare later objective ROOTS emergence

Input:
- MNA/data/structural-signatures/<book>-structural-signatures.jsonl

Outputs:
- MNA/data/structural-families/<book>-structural-families.jsonl
- MNA/data/structural-families/<book>-structural-families.tsv
- MNA/data/structural-families/<book>-family-summary.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theology
- no H0/H1/H2 assignment
- no topology reconstruction

This layer groups regimes ONLY by recurring structural behavior.
"""

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

FEATURES = [
    "structural_density",
    "turbulence_density",
    "stable_density",
    "continuity_same_density",
    "continuity_shift_density",
    "continuity_unresolved_density",
    "weight_per_record",
]

DISTANCE_THRESHOLD = 0.35



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



def feature_vector(row: dict[str, Any]) -> list[float]:
    vector: list[float] = []

    for feature in FEATURES:
        value = row.get(feature, 0)
        try:
            vector.append(float(value))
        except (TypeError, ValueError):
            vector.append(0.0)

    return vector



def euclidean_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))



def assign_families(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    families: list[dict[str, Any]] = []

    for row in rows:
        vector = feature_vector(row)

        assigned_family = None
        assigned_distance = None

        for family in families:
            centroid = family["centroid"]
            distance = euclidean_distance(vector, centroid)

            if distance <= DISTANCE_THRESHOLD:
                assigned_family = family
                assigned_distance = distance
                break

        if assigned_family is None:
            family_id = f"SF{len(families)+1:03d}"

            new_family = {
                "family_id": family_id,
                "centroid": vector,
                "members": [],
            }

            families.append(new_family)
            assigned_family = new_family
            assigned_distance = 0.0

        assigned_family["members"].append(row)

        member_count = len(assigned_family["members"])

        assigned_family["centroid"] = [
            (
                (assigned_family["centroid"][i] * (member_count - 1))
                + vector[i]
            ) / member_count
            for i in range(len(vector))
        ]

        row["structural_family_id"] = assigned_family["family_id"]
        row["family_distance"] = round(float(assigned_distance), 6)

    return rows



def build_family_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        grouped[row["structural_family_id"]].append(row)

    summary: list[dict[str, Any]] = []

    for family_id in sorted(grouped):
        members = grouped[family_id]

        movement_counter = Counter(
            row.get("dominant_movement_class") or "unknown"
            for row in members
        )

        summary.append({
            "structural_family_id": family_id,
            "member_count": len(members),
            "avg_structural_density": round(
                sum(float(row.get("structural_density") or 0) for row in members)
                / len(members),
                4,
            ),
            "avg_turbulence_density": round(
                sum(float(row.get("turbulence_density") or 0) for row in members)
                / len(members),
                4,
            ),
            "avg_stable_density": round(
                sum(float(row.get("stable_density") or 0) for row in members)
                / len(members),
                4,
            ),
            "avg_continuity_same_density": round(
                sum(float(row.get("continuity_same_density") or 0) for row in members)
                / len(members),
                4,
            ),
            "avg_continuity_shift_density": round(
                sum(float(row.get("continuity_shift_density") or 0) for row in members)
                / len(members),
                4,
            ),
            "avg_weight_per_record": round(
                sum(float(row.get("weight_per_record") or 0) for row in members)
                / len(members),
                4,
            ),
            "dominant_movement_profile": movement_counter.most_common(1)[0][0],
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

    fieldnames = list(rows[0].keys())

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for row in rows:
            writer.writerow(row)



def process_book(book: str) -> tuple[int, int, Path, Path, Path]:
    in_path = (
        mna_root()
        / "data"
        / "structural-signatures"
        / f"{book}-structural-signatures.jsonl"
    )

    rows = read_jsonl(in_path)
    rows = assign_families(rows)
    summary = build_family_summary(rows)

    out_dir = mna_root() / "data" / "structural-families"

    jsonl_out = out_dir / f"{book}-structural-families.jsonl"
    tsv_out = out_dir / f"{book}-structural-families.tsv"
    summary_out = out_dir / f"{book}-family-summary.tsv"

    write_jsonl(jsonl_out, rows)
    write_tsv(tsv_out, rows)
    write_tsv(summary_out, summary)

    family_count = len({row["structural_family_id"] for row in rows})

    return family_count, len(rows), jsonl_out, tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_detect_structural_families.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    family_count, record_count, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"structural_families = {family_count}")
    print(f"signature_records = {record_count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
