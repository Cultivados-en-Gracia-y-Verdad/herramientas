#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — compare chapter predication metrics

Observation-layer script only.

This script reads the chapter metrics TSV produced by
roots_predication_metrics.py and generates objective comparison reports.

It does NOT:
- infer topology
- attach connectors
- generate ROOTS structure
- assign H0/H1/H2
- interpret themes

It only compares measurable predication behavior across chapters.

Usage from repository root:
    python3 MNA/scripts/roots_compare_chapter_metrics.py 1corintios

Usage from MNA directory:
    python3 scripts/roots_compare_chapter_metrics.py 1corintios

Inputs:
    MNA/data/predications/reports/<book>-chapter-metrics.tsv

Outputs:
    MNA/data/predications/reports/<book>-chapter-similarity.tsv
    MNA/data/predications/reports/<book>-chapter-shifts.tsv
    MNA/data/predications/reports/<book>-chapter-ranked-metrics.tsv
"""

import csv
import math
import sys
from pathlib import Path
from typing import Any

NUMERIC_FIELDS = [
    "total_predications",
    "verses_with_predications",
    "predications_per_verse",
    "max_predications_single_verse",
    "finite_1S",
    "finite_1P",
    "finite_2S",
    "finite_2P",
    "finite_3S",
    "finite_3P",
    "subject_morphology",
    "subject_candidate",
    "subject_unresolved",
    "independent_candidate",
    "independence_unresolved",
    "subordination_candidate",
    "subordination_not_detected",
    "subordination_unresolved",
]

VECTOR_FIELDS = [
    "predications_per_verse",
    "max_predications_single_verse",
    "finite_1S",
    "finite_1P",
    "finite_2S",
    "finite_2P",
    "finite_3S",
    "finite_3P",
    "subject_candidate",
    "independence_unresolved",
    "subordination_candidate",
]

SHIFT_FIELDS = [
    "total_predications",
    "predications_per_verse",
    "max_predications_single_verse",
    "finite_1S",
    "finite_1P",
    "finite_2S",
    "finite_2P",
    "finite_3S",
    "finite_3P",
    "subject_candidate",
    "independence_unresolved",
    "subordination_candidate",
]

RANK_FIELDS = [
    "total_predications",
    "predications_per_verse",
    "max_predications_single_verse",
    "finite_1S",
    "finite_1P",
    "finite_2S",
    "finite_2P",
    "finite_3S",
    "finite_3P",
    "subject_candidate",
    "independence_unresolved",
    "subordination_candidate",
]


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_metrics(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"book", "chapter", *NUMERIC_FIELDS}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")

        for raw in reader:
            row: dict[str, Any] = {
                "book": raw["book"],
                "chapter": int(raw["chapter"]),
            }
            for field in NUMERIC_FIELDS:
                value = raw[field]
                row[field] = float(value) if "." in value else int(value)
            rows.append(row)

    return sorted(rows, key=lambda r: r["chapter"])


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stddev(values: list[float]) -> float:
    if not values:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def zscore(value: float, avg: float, sd: float) -> float:
    if sd == 0:
        return 0.0
    return (value - avg) / sd


def build_zscore_vectors(rows: list[dict[str, Any]], fields: list[str]) -> dict[int, list[float]]:
    stats: dict[str, tuple[float, float]] = {}
    for field in fields:
        values = [float(row[field]) for row in rows]
        stats[field] = (mean(values), stddev(values))

    vectors: dict[int, list[float]] = {}
    for row in rows:
        vectors[row["chapter"]] = [
            zscore(float(row[field]), stats[field][0], stats[field][1])
            for field in fields
        ]
    return vectors


def euclidean_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def similarity_score(distance: float) -> float:
    return round(1 / (1 + distance), 4)


def write_similarity(rows: list[dict[str, Any]], output_path: Path) -> None:
    vectors = build_zscore_vectors(rows, VECTOR_FIELDS)
    chapters = [row["chapter"] for row in rows]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["chapter_a", "chapter_b", "distance", "similarity"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for i, chapter_a in enumerate(chapters):
            for chapter_b in chapters[i + 1:]:
                distance = euclidean_distance(vectors[chapter_a], vectors[chapter_b])
                writer.writerow({
                    "chapter_a": chapter_a,
                    "chapter_b": chapter_b,
                    "distance": round(distance, 4),
                    "similarity": similarity_score(distance),
                })


def write_shifts(rows: list[dict[str, Any]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["from_chapter", "to_chapter", "field", "from_value", "to_value", "delta"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for previous, current in zip(rows, rows[1:]):
            for field in SHIFT_FIELDS:
                from_value = previous[field]
                to_value = current[field]
                delta = float(to_value) - float(from_value)
                writer.writerow({
                    "from_chapter": previous["chapter"],
                    "to_chapter": current["chapter"],
                    "field": field,
                    "from_value": from_value,
                    "to_value": to_value,
                    "delta": round(delta, 4),
                })


def write_ranked_metrics(rows: list[dict[str, Any]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["metric", "rank", "chapter", "value"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for field in RANK_FIELDS:
            ranked = sorted(rows, key=lambda row: float(row[field]), reverse=True)
            for rank, row in enumerate(ranked, start=1):
                writer.writerow({
                    "metric": field,
                    "rank": rank,
                    "chapter": row["chapter"],
                    "value": row[field],
                })


def process_book(book: str) -> tuple[Path, Path, Path]:
    reports_dir = mna_root() / "data" / "predications" / "reports"
    metrics_path = reports_dir / f"{book}-chapter-metrics.tsv"

    if not metrics_path.exists():
        raise FileNotFoundError(
            f"Missing metrics file: {metrics_path}\n"
            f"Run: python3 MNA/scripts/roots_predication_metrics.py {book}"
        )

    rows = read_metrics(metrics_path)
    if not rows:
        raise ValueError(f"No rows found in {metrics_path}")

    similarity_path = reports_dir / f"{book}-chapter-similarity.tsv"
    shifts_path = reports_dir / f"{book}-chapter-shifts.tsv"
    ranked_path = reports_dir / f"{book}-chapter-ranked-metrics.tsv"

    write_similarity(rows, similarity_path)
    write_shifts(rows, shifts_path)
    write_ranked_metrics(rows, ranked_path)

    return similarity_path, shifts_path, ranked_path


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_compare_chapter_metrics.py <book>\n"
            "\nExample:\n"
            "  python3 MNA/scripts/roots_compare_chapter_metrics.py 1corintios",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    outputs = process_book(book)
    for path in outputs:
        print(f"WROTE: {path}")


if __name__ == "__main__":
    main()
