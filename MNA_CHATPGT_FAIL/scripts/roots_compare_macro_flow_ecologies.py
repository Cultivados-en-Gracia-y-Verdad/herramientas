#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — cross-book macro-flow ecology comparison

Purpose:
- compare macro-flow ecologies across books
- detect recurring discourse-scale structural behavior
- remain strictly mechanical and non-semantic

Inputs per book:
- MNA/data/macro-flow/<book>-macro-flow-segments.jsonl
- MNA/data/family-dynamics/<book>-family-flow-summary.tsv
- MNA/data/structural-families/<book>-structural-families-consolidated.jsonl

Outputs:
- MNA/data/cross-book-ecology/cross-book-ecology-profiles.jsonl
- MNA/data/cross-book-ecology/cross-book-ecology-profiles.tsv
- MNA/data/cross-book-ecology/cross-book-ecology-comparison.jsonl
- MNA/data/cross-book-ecology/cross-book-ecology-comparison.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theology
- no H0/H1/H2 assignment
- no topology reconstruction

This layer compares ONLY observable structural ecology behavior.
"""

import csv
import json
import math
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

FEATURES = [
    "avg_structural_density",
    "avg_turbulence_density",
    "avg_stable_density",
    "avg_continuity_same_density",
    "avg_continuity_shift_density",
    "avg_weight_per_record",
    "macro_segment_density",
    "family_density",
]


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


def read_tsv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def distribution_distance(a: dict[str, int], b: dict[str, int]) -> float:
    keys = set(a) | set(b)
    total_a = sum(a.values()) or 1
    total_b = sum(b.values()) or 1
    return round(sum(abs((a.get(k, 0) / total_a) - (b.get(k, 0) / total_b)) for k in keys) / 2, 6)


def euclidean_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def book_paths(book: str) -> tuple[Path, Path, Path]:
    root = mna_root()
    macro_path = root / "data" / "macro-flow" / f"{book}-macro-flow-segments.jsonl"
    flow_path = root / "data" / "family-dynamics" / f"{book}-family-flow-summary.tsv"
    family_path = root / "data" / "structural-families" / f"{book}-structural-families-consolidated.jsonl"
    return macro_path, flow_path, family_path


def build_book_profile(book: str) -> dict[str, Any]:
    macro_path, flow_path, family_path = book_paths(book)

    macro_rows = read_jsonl(macro_path)
    flow_rows = read_tsv(flow_path)
    family_rows = read_jsonl(family_path)

    macro_segment_count = len(macro_rows)
    family_record_count = len(family_rows)

    family_counter = Counter(str(row.get("consolidated_family_id")) for row in family_rows)
    macro_dominant_counter = Counter(str(row.get("dominant_family")) for row in macro_rows if row.get("dominant_family"))

    record_total = sum(safe_int(row.get("record_count")) for row in family_rows) or 1

    profile = {
        "book": book,
        "macro_segment_count": macro_segment_count,
        "family_record_count": family_record_count,
        "structural_family_count": len(family_counter),
        "macro_segment_density": round(macro_segment_count / record_total, 6),
        "family_density": round(len(family_counter) / record_total, 6),
        "dominant_family": family_counter.most_common(1)[0][0] if family_counter else None,
        "dominant_macro_family": macro_dominant_counter.most_common(1)[0][0] if macro_dominant_counter else None,
        "family_distribution": json.dumps(dict(sorted(family_counter.items())), ensure_ascii=False, sort_keys=True),
        "macro_dominant_family_distribution": json.dumps(dict(sorted(macro_dominant_counter.items())), ensure_ascii=False, sort_keys=True),
        "avg_structural_density": avg([safe_float(row.get("avg_structural_density")) for row in macro_rows]),
        "avg_turbulence_density": avg([safe_float(row.get("avg_turbulence_density")) for row in macro_rows]),
        "avg_stable_density": avg([safe_float(row.get("avg_stable_density")) for row in macro_rows]),
        "avg_continuity_same_density": avg([safe_float(row.get("avg_continuity_same_density")) for row in macro_rows]),
        "avg_continuity_shift_density": avg([safe_float(row.get("avg_continuity_shift_density")) for row in macro_rows]),
        "avg_weight_per_record": avg([safe_float(row.get("avg_weight_per_record")) for row in macro_rows]),
        "avg_incoming_transitions": avg([safe_float(row.get("incoming_transition_count")) for row in flow_rows]),
        "avg_outgoing_transitions": avg([safe_float(row.get("outgoing_transition_count")) for row in flow_rows]),
    }

    return profile


def feature_vector(profile: dict[str, Any]) -> list[float]:
    return [safe_float(profile.get(feature)) for feature in FEATURES]


def compare_profiles(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    vector_distance = euclidean_distance(feature_vector(left), feature_vector(right))
    ecology_similarity = round(max(0.0, 1.0 - vector_distance), 6)

    left_family_distribution = {k: safe_int(v) for k, v in parse_json_dict(left.get("family_distribution")).items()}
    right_family_distribution = {k: safe_int(v) for k, v in parse_json_dict(right.get("family_distribution")).items()}
    family_distribution_distance = distribution_distance(left_family_distribution, right_family_distribution)

    combined_similarity = round(max(0.0, ecology_similarity - (family_distribution_distance * 0.25)), 6)

    return {
        "book_a": left["book"],
        "book_b": right["book"],
        "ecology_similarity": ecology_similarity,
        "family_distribution_distance": family_distribution_distance,
        "combined_similarity": combined_similarity,
        "relationship": relationship_label(combined_similarity),
        "dominant_family_a": left.get("dominant_family"),
        "dominant_family_b": right.get("dominant_family"),
        "macro_segment_count_a": left.get("macro_segment_count"),
        "macro_segment_count_b": right.get("macro_segment_count"),
        "structural_family_count_a": left.get("structural_family_count"),
        "structural_family_count_b": right.get("structural_family_count"),
    }


def relationship_label(similarity: float) -> str:
    if similarity >= 0.90:
        return "very_high_similarity"
    if similarity >= 0.75:
        return "high_similarity"
    if similarity >= 0.55:
        return "moderate_similarity"
    if similarity >= 0.35:
        return "low_similarity"
    return "very_low_similarity"


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


def process_books(books: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Path, Path, Path, Path]:
    profiles = [build_book_profile(book) for book in books]
    comparisons = [compare_profiles(a, b) for a, b in combinations(profiles, 2)]

    out_dir = mna_root() / "data" / "cross-book-ecology"
    profiles_jsonl = out_dir / "cross-book-ecology-profiles.jsonl"
    profiles_tsv = out_dir / "cross-book-ecology-profiles.tsv"
    comparison_jsonl = out_dir / "cross-book-ecology-comparison.jsonl"
    comparison_tsv = out_dir / "cross-book-ecology-comparison.tsv"

    write_jsonl(profiles_jsonl, profiles)
    write_tsv(profiles_tsv, profiles)
    write_jsonl(comparison_jsonl, comparisons)
    write_tsv(comparison_tsv, comparisons)

    return profiles, comparisons, profiles_jsonl, profiles_tsv, comparison_jsonl, comparison_tsv


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_compare_macro_flow_ecologies.py <book1> <book2> [book3 ...]",
            file=sys.stderr,
        )
        sys.exit(2)

    books = [arg.lower() for arg in sys.argv[1:]]
    profiles, comparisons, profiles_jsonl, profiles_tsv, comparison_jsonl, comparison_tsv = process_books(books)

    print(f"book_profiles = {len(profiles)}")
    print(f"book_comparisons = {len(comparisons)}")
    print(f"wrote: {profiles_jsonl}")
    print(f"wrote: {profiles_tsv}")
    print(f"wrote: {comparison_jsonl}")
    print(f"wrote: {comparison_tsv}")


if __name__ == "__main__":
    main()
