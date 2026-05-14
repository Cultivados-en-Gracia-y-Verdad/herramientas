#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — structural family consolidation

Purpose:
- reduce over-fragmented structural families
- merge singleton / weak families into compatible larger families
- preserve mechanical auditability

Inputs:
- MNA/data/structural-families/<book>-structural-families.jsonl

Outputs:
- MNA/data/structural-families/<book>-structural-families-consolidated.jsonl
- MNA/data/structural-families/<book>-consolidated-family-summary.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theology
- no H0/H1/H2 assignment
- no topology reconstruction

This layer consolidates ONLY by structural feature distance.
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

SINGLETON_MAX_DISTANCE = 0.55
SMALL_FAMILY_MAX_DISTANCE = 0.45
SMALL_FAMILY_SIZE = 2


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


def vector(row: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for feature in FEATURES:
        try:
            values.append(float(row.get(feature) or 0))
        except (TypeError, ValueError):
            values.append(0.0)
    return values


def distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def centroid(rows: list[dict[str, Any]]) -> list[float]:
    if not rows:
        return [0.0 for _ in FEATURES]
    vectors = [vector(row) for row in rows]
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(len(FEATURES))]


def grouped_by_family(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("structural_family_id"))].append(row)
    return grouped


def build_family_state(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped = grouped_by_family(rows)
    state: dict[str, dict[str, Any]] = {}
    for family_id, members in grouped.items():
        state[family_id] = {
            "family_id": family_id,
            "members": members,
            "centroid": centroid(members),
        }
    return state


def nearest_large_family(
    family_id: str,
    family_state: dict[str, dict[str, Any]],
    min_size: int,
) -> tuple[str | None, float | None]:
    source = family_state[family_id]
    source_centroid = source["centroid"]

    best_id: str | None = None
    best_distance: float | None = None

    for target_id, target in family_state.items():
        if target_id == family_id:
            continue
        if len(target["members"]) < min_size:
            continue
        d = distance(source_centroid, target["centroid"])
        if best_distance is None or d < best_distance:
            best_distance = d
            best_id = target_id

    return best_id, best_distance


def consolidate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family_state = build_family_state(rows)
    mapping: dict[str, tuple[str, float, str]] = {}

    for family_id, family in sorted(family_state.items()):
        size = len(family["members"])

        if size == 1:
            target_id, d = nearest_large_family(family_id, family_state, min_size=2)
            if target_id is not None and d is not None and d <= SINGLETON_MAX_DISTANCE:
                mapping[family_id] = (target_id, d, "singleton_nearest_compatible_family")
            else:
                mapping[family_id] = (family_id, 0.0, "retained_singleton_no_compatible_family")

        elif size <= SMALL_FAMILY_SIZE:
            target_id, d = nearest_large_family(family_id, family_state, min_size=3)
            if target_id is not None and d is not None and d <= SMALL_FAMILY_MAX_DISTANCE:
                mapping[family_id] = (target_id, d, "small_family_nearest_compatible_family")
            else:
                mapping[family_id] = (family_id, 0.0, "retained_small_family_no_compatible_family")

        else:
            mapping[family_id] = (family_id, 0.0, "retained_large_family")

    consolidated_rows: list[dict[str, Any]] = []
    for row in rows:
        original = str(row.get("structural_family_id"))
        target, d, reason = mapping[original]
        out = dict(row)
        out["original_structural_family_id"] = original
        out["consolidated_family_id"] = target
        out["consolidation_distance"] = round(float(d), 6)
        out["consolidation_reason"] = reason
        consolidated_rows.append(out)

    # Renumber consolidated families into stable compact IDs.
    ordered_targets = sorted({row["consolidated_family_id"] for row in consolidated_rows})
    renumber = {target: f"CSF{i:03d}" for i, target in enumerate(ordered_targets, start=1)}
    for row in consolidated_rows:
        row["consolidated_family_id"] = renumber[row["consolidated_family_id"]]

    return consolidated_rows


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["consolidated_family_id"]].append(row)

    summary: list[dict[str, Any]] = []
    for family_id in sorted(grouped):
        members = grouped[family_id]
        movement_counter = Counter(row.get("dominant_movement_class") or "unknown" for row in members)
        source_counter = Counter(row.get("original_structural_family_id") or "unknown" for row in members)
        summary.append({
            "consolidated_family_id": family_id,
            "member_count": len(members),
            "source_family_count": len(source_counter),
            "source_family_ids": ",".join(sorted(source_counter)),
            "avg_structural_density": round(sum(float(row.get("structural_density") or 0) for row in members) / len(members), 4),
            "avg_turbulence_density": round(sum(float(row.get("turbulence_density") or 0) for row in members) / len(members), 4),
            "avg_stable_density": round(sum(float(row.get("stable_density") or 0) for row in members) / len(members), 4),
            "avg_continuity_same_density": round(sum(float(row.get("continuity_same_density") or 0) for row in members) / len(members), 4),
            "avg_continuity_shift_density": round(sum(float(row.get("continuity_shift_density") or 0) for row in members) / len(members), 4),
            "avg_continuity_unresolved_density": round(sum(float(row.get("continuity_unresolved_density") or 0) for row in members) / len(members), 4),
            "avg_weight_per_record": round(sum(float(row.get("weight_per_record") or 0) for row in members) / len(members), 4),
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
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def process_book(book: str) -> tuple[int, int, Path, Path]:
    in_path = mna_root() / "data" / "structural-families" / f"{book}-structural-families.jsonl"
    rows = read_jsonl(in_path)
    consolidated = consolidate(rows)
    summary = build_summary(consolidated)

    out_dir = mna_root() / "data" / "structural-families"
    jsonl_out = out_dir / f"{book}-structural-families-consolidated.jsonl"
    summary_out = out_dir / f"{book}-consolidated-family-summary.tsv"

    write_jsonl(jsonl_out, consolidated)
    write_tsv(summary_out, summary)

    return len({row["consolidated_family_id"] for row in consolidated}), len(rows), jsonl_out, summary_out


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_consolidate_structural_families.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    family_count, record_count, jsonl_out, summary_out = process_book(book)

    print(f"consolidated_families = {family_count}")
    print(f"signature_records = {record_count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
