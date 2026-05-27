#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — macro-flow segmentation

Purpose:
- detect large-scale structural ecology shifts
- segment the consolidated family stream into macro-flow spans
- remain strictly mechanical and non-semantic

Input:
- MNA/data/structural-families/<book>-structural-families-consolidated.jsonl

Outputs:
- MNA/data/macro-flow/<book>-macro-flow-segments.jsonl
- MNA/data/macro-flow/<book>-macro-flow-segments.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theology
- no H0/H1/H2 assignment
- no topology reconstruction

This layer models ONLY large-scale structural family distribution shifts.
"""

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

WINDOW = 6
SHIFT_THRESHOLD = 0.72
MIN_SEGMENT_SIZE = 4

FEATURES = [
    "structural_density",
    "turbulence_density",
    "stable_density",
    "continuity_same_density",
    "continuity_shift_density",
    "continuity_unresolved_density",
    "weight_per_record",
]


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def ordered_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row.get("start_stream_index") or 0))


def vector(row: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for feature in FEATURES:
        try:
            values.append(float(row.get(feature) or 0))
        except (TypeError, ValueError):
            values.append(0.0)
    return values


def centroid(rows: list[dict[str, Any]]) -> list[float]:
    if not rows:
        return [0.0 for _ in FEATURES]
    vectors = [vector(row) for row in rows]
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(len(FEATURES))]


def distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def family_distribution(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(row.get("consolidated_family_id")) for row in rows)


def distribution_distance(left: Counter[str], right: Counter[str]) -> float:
    keys = set(left) | set(right)
    left_total = sum(left.values()) or 1
    right_total = sum(right.values()) or 1

    return sum(abs((left[k] / left_total) - (right[k] / right_total)) for k in keys) / 2


def shift_score(rows: list[dict[str, Any]], idx: int) -> float:
    left = rows[max(0, idx - WINDOW):idx]
    right = rows[idx:min(len(rows), idx + WINDOW)]

    if len(left) < 2 or len(right) < 2:
        return 0.0

    centroid_score = distance(centroid(left), centroid(right))
    distribution_score = distribution_distance(family_distribution(left), family_distribution(right))

    return round((centroid_score + distribution_score) / 2, 6)


def candidate_breaks(rows: list[dict[str, Any]]) -> list[tuple[int, float]]:
    candidates: list[tuple[int, float]] = []

    for idx in range(1, len(rows)):
        score = shift_score(rows, idx)
        if score >= SHIFT_THRESHOLD:
            candidates.append((idx, score))

    return candidates


def select_breaks(rows: list[dict[str, Any]]) -> list[tuple[int, float]]:
    selected: list[tuple[int, float]] = []

    for idx, score in sorted(candidate_breaks(rows), key=lambda item: item[1], reverse=True):
        if any(abs(idx - existing_idx) < MIN_SEGMENT_SIZE for existing_idx, _ in selected):
            continue
        selected.append((idx, score))

    selected.sort(key=lambda item: item[0])
    return selected


def summarize_segment(segment_id: int, rows: list[dict[str, Any]], break_score: float | None) -> dict[str, Any]:
    first = rows[0]
    last = rows[-1]
    family_counts = family_distribution(rows)

    return {
        "macro_segment_id": f"MF{segment_id:03d}",
        "segment_index": segment_id,
        "start_stream_index": first.get("start_stream_index"),
        "end_stream_index": last.get("end_stream_index"),
        "start_reference": first.get("start_reference"),
        "end_reference": last.get("end_reference"),
        "regime_count": len(rows),
        "record_count_total": sum(int(row.get("record_count") or 0) for row in rows),
        "dominant_family": family_counts.most_common(1)[0][0] if family_counts else None,
        "family_counts": json.dumps(dict(sorted(family_counts.items())), ensure_ascii=False, sort_keys=True),
        "avg_structural_density": round(sum(float(row.get("structural_density") or 0) for row in rows) / len(rows), 4),
        "avg_turbulence_density": round(sum(float(row.get("turbulence_density") or 0) for row in rows) / len(rows), 4),
        "avg_stable_density": round(sum(float(row.get("stable_density") or 0) for row in rows) / len(rows), 4),
        "avg_continuity_same_density": round(sum(float(row.get("continuity_same_density") or 0) for row in rows) / len(rows), 4),
        "avg_continuity_shift_density": round(sum(float(row.get("continuity_shift_density") or 0) for row in rows) / len(rows), 4),
        "avg_weight_per_record": round(sum(float(row.get("weight_per_record") or 0) for row in rows) / len(rows), 4),
        "incoming_break_score": break_score,
    }


def build_segments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    breaks = select_breaks(rows)
    break_map = {idx: score for idx, score in breaks}

    segments_raw: list[tuple[list[dict[str, Any]], float | None]] = []
    start = 0
    incoming_score: float | None = None

    for idx, score in breaks:
        segment = rows[start:idx]
        if segment:
            segments_raw.append((segment, incoming_score))
        start = idx
        incoming_score = score

    final_segment = rows[start:]
    if final_segment:
        segments_raw.append((final_segment, incoming_score))

    return [summarize_segment(i, segment, score) for i, (segment, score) in enumerate(segments_raw, start=1)]


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


def process_book(book: str) -> tuple[int, Path, Path]:
    in_path = (
        mna_root()
        / "data"
        / "structural-families"
        / f"{book}-structural-families-consolidated.jsonl"
    )
    rows = ordered_rows(read_jsonl(in_path))
    segments = build_segments(rows)

    out_dir = mna_root() / "data" / "macro-flow"
    jsonl_out = out_dir / f"{book}-macro-flow-segments.jsonl"
    tsv_out = out_dir / f"{book}-macro-flow-segments.tsv"

    write_jsonl(jsonl_out, segments)
    write_tsv(tsv_out, segments)

    return len(segments), jsonl_out, tsv_out


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_detect_macro_flow_segments.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    count, jsonl_out, tsv_out = process_book(book)

    print(f"macro_flow_segments = {count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")


if __name__ == "__main__":
    main()
