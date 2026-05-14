#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — data-only chapter metric observations

This script produces observations ONLY from collected ROOTS predication metric
files. It does not read Scripture text, commentary, headings, external sources,
or semantic labels.

Allowed inputs:
- MNA/data/predications/reports/<book>-chapter-metrics.tsv
- MNA/data/predications/reports/<book>-chapter-similarity.tsv
- MNA/data/predications/reports/<book>-chapter-shifts.tsv
- MNA/data/predications/reports/<book>-chapter-ranked-metrics.tsv

It does NOT:
- infer themes
- assign H0/H1/H2
- attach connectors
- reconstruct topology
- use chapter titles
- use external sources
- use Bible text content

Outputs:
- MNA/data/predications/reports/<book>-chapter-observations.md
- MNA/data/predications/reports/<book>-chapter-observations.tsv

Usage from repository root:
    python3 MNA/scripts/roots_observe_chapter_metrics.py 1corintios

Usage from MNA directory:
    python3 scripts/roots_observe_chapter_metrics.py 1corintios
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

TOP_N = 5
HIGH_SHIFT_THRESHOLD = 20.0
SIMILARITY_TOP_N = 15

METRIC_FIELDS = [
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


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def reports_dir() -> Path:
    return mna_root() / "data" / "predications" / "reports"


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def numeric(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return 0.0


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["observation_type", "rank", "chapter", "chapter_b", "metric", "value", "delta", "note"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def top_ranked_observations(ranked_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in ranked_rows:
        rank = int(row["rank"])
        if rank > TOP_N:
            continue
        out.append({
            "observation_type": "metric_top_rank",
            "rank": rank,
            "chapter": row["chapter"],
            "metric": row["metric"],
            "value": row["value"],
            "note": f"chapter {row['chapter']} ranks {rank} for {row['metric']}",
        })
    return out


def strongest_similarity_observations(similarity_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    sorted_rows = sorted(similarity_rows, key=lambda row: numeric(row["similarity"]), reverse=True)
    out: list[dict[str, Any]] = []
    for rank, row in enumerate(sorted_rows[:SIMILARITY_TOP_N], start=1):
        out.append({
            "observation_type": "chapter_similarity",
            "rank": rank,
            "chapter": row["chapter_a"],
            "chapter_b": row["chapter_b"],
            "metric": "similarity",
            "value": row["similarity"],
            "delta": row["distance"],
            "note": f"chapters {row['chapter_a']} and {row['chapter_b']} have similarity {row['similarity']}",
        })
    return out


def largest_shift_observations(shifts_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    filtered = [
        row for row in shifts_rows
        if abs(numeric(row["delta"])) >= HIGH_SHIFT_THRESHOLD
    ]
    sorted_rows = sorted(filtered, key=lambda row: abs(numeric(row["delta"])), reverse=True)
    out: list[dict[str, Any]] = []
    for rank, row in enumerate(sorted_rows, start=1):
        out.append({
            "observation_type": "adjacent_chapter_shift",
            "rank": rank,
            "chapter": row["from_chapter"],
            "chapter_b": row["to_chapter"],
            "metric": row["field"],
            "value": row["to_value"],
            "delta": row["delta"],
            "note": f"{row['field']} changes from {row['from_value']} to {row['to_value']} between chapters {row['from_chapter']} and {row['to_chapter']}",
        })
    return out


def zero_field_observations(metrics_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    watched_fields = [
        "finite_1S", "finite_1P", "finite_2S", "finite_2P", "finite_3S", "finite_3P",
        "subject_unresolved", "subordination_unresolved",
    ]
    for row in metrics_rows:
        chapter = row["chapter"]
        for field in watched_fields:
            if numeric(row[field]) == 0:
                out.append({
                    "observation_type": "zero_metric",
                    "chapter": chapter,
                    "metric": field,
                    "value": 0,
                    "note": f"chapter {chapter} has zero count for {field}",
                })
    return out


def build_markdown(book: str, observations: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        grouped[row["observation_type"]].append(row)

    lines: list[str] = []
    lines.append(f"# {book} Chapter Metric Observations")
    lines.append("")
    lines.append("## Source Boundary")
    lines.append("")
    lines.append("This report is generated only from collected predication metric TSV files.")
    lines.append("It does not use Bible text, commentary, headings, semantic labels, or external sources.")
    lines.append("")

    for section in ["chapter_similarity", "metric_top_rank", "adjacent_chapter_shift", "zero_metric"]:
        rows = grouped.get(section, [])
        lines.append(f"## {section}")
        lines.append("")
        if not rows:
            lines.append("- none")
            lines.append("")
            continue
        for row in rows:
            if row.get("chapter_b"):
                lines.append(
                    f"- {row.get('note')} | metric={row.get('metric')} | value={row.get('value')} | delta={row.get('delta', '')}"
                )
            else:
                lines.append(
                    f"- {row.get('note')} | metric={row.get('metric')} | value={row.get('value')}"
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def process_book(book: str) -> tuple[Path, Path]:
    base = reports_dir()
    metrics_path = base / f"{book}-chapter-metrics.tsv"
    similarity_path = base / f"{book}-chapter-similarity.tsv"
    shifts_path = base / f"{book}-chapter-shifts.tsv"
    ranked_path = base / f"{book}-chapter-ranked-metrics.tsv"

    metrics_rows = read_tsv(metrics_path)
    similarity_rows = read_tsv(similarity_path)
    shifts_rows = read_tsv(shifts_path)
    ranked_rows = read_tsv(ranked_path)

    observations: list[dict[str, Any]] = []
    observations.extend(strongest_similarity_observations(similarity_rows))
    observations.extend(top_ranked_observations(ranked_rows))
    observations.extend(largest_shift_observations(shifts_rows))
    observations.extend(zero_field_observations(metrics_rows))

    tsv_out = base / f"{book}-chapter-observations.tsv"
    md_out = base / f"{book}-chapter-observations.md"

    write_tsv(tsv_out, observations)
    md_out.write_text(build_markdown(book, observations), encoding="utf-8")

    return tsv_out, md_out


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_observe_chapter_metrics.py <book>\n"
            "\nExample:\n"
            "  python3 MNA/scripts/roots_observe_chapter_metrics.py 1corintios",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    outputs = process_book(book)
    for path in outputs:
        print(f"WROTE: {path}")


if __name__ == "__main__":
    main()
