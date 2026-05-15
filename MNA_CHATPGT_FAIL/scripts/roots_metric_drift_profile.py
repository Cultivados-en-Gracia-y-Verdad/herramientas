#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — metric drift profile

Data-only observation layer.

This script analyzes threshold sweep persistence behavior using only generated
threshold sweep TSV files.

Allowed inputs:
- MNA/data/predications/reports/<book>-threshold-sweep.tsv
- MNA/data/predications/reports/<book>-threshold-edge-persistence.tsv

Outputs:
- MNA/data/predications/reports/<book>-drift-profile.tsv
- MNA/data/predications/reports/<book>-drift-profile.md

This script does NOT:
- read Scripture text
- use semantic labels
- use commentary
- infer topology
- assign H0/H1/H2
- attach connectors
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


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
    return float(value)


def build_persistent_pairs(edge_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    ranked = sorted(
        edge_rows,
        key=lambda row: (
            int(row["persistence_count"]),
            numeric(row["similarity"]),
        ),
        reverse=True,
    )

    for rank, row in enumerate(ranked, start=1):
        out.append({
            "profile_type": "persistent_pair",
            "rank": rank,
            "chapter_a": row["chapter_a"],
            "chapter_b": row["chapter_b"],
            "persistence_count": row["persistence_count"],
            "max_threshold": row["max_survived_threshold"],
            "similarity": row["similarity"],
            "note": (
                f"{row['chapter_a']} ↔ {row['chapter_b']} survives through "
                f"{row['survives_thresholds']}"
            ),
        })

    return out


def build_singularity_profiles(sweep_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    chapter_states: defaultdict[str, list[tuple[float, int]]] = defaultdict(list)

    for row in sweep_rows:
        threshold = numeric(row["threshold"])
        cluster_size = int(row["cluster_size"])

        for chapter in row["chapters"].split(","):
            chapter_states[chapter].append((threshold, cluster_size))

    out = []

    for chapter, states in sorted(chapter_states.items(), key=lambda item: int(item[0])):
        states.sort()

        isolated_thresholds = [
            threshold
            for threshold, size in states
            if size == 1
        ]

        grouped_thresholds = [
            threshold
            for threshold, size in states
            if size > 1
        ]

        isolation_ratio = round(
            len(isolated_thresholds) / len(states),
            4,
        )

        if isolation_ratio == 1.0:
            profile = "persistent_singularity"
        elif isolation_ratio >= 0.5:
            profile = "partial_singularity"
        else:
            profile = "integrated"

        out.append({
            "profile_type": profile,
            "chapter_a": chapter,
            "chapter_b": "",
            "persistence_count": len(isolated_thresholds),
            "max_threshold": max(isolated_thresholds) if isolated_thresholds else "",
            "similarity": "",
            "note": (
                f"chapter {chapter} isolated at "
                f"{','.join(f'{t:.2f}' for t in isolated_thresholds)}"
                if isolated_thresholds
                else f"chapter {chapter} never isolated"
            ),
        })

    return out


def build_fragmentation_profiles(sweep_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    threshold_clusters: defaultdict[float, list[int]] = defaultdict(list)

    for row in sweep_rows:
        threshold = numeric(row["threshold"])
        threshold_clusters[threshold].append(int(row["cluster_size"]))

    out = []

    for threshold in sorted(threshold_clusters):
        sizes = threshold_clusters[threshold]
        largest = max(sizes)
        isolated = sum(1 for size in sizes if size == 1)
        total_clusters = len(sizes)

        out.append({
            "profile_type": "threshold_fragmentation",
            "chapter_a": "",
            "chapter_b": "",
            "persistence_count": isolated,
            "max_threshold": threshold,
            "similarity": largest,
            "note": (
                f"threshold {threshold:.2f}: "
                f"clusters={total_clusters} largest_cluster={largest} isolated_clusters={isolated}"
            ),
        })

    return out


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "profile_type",
        "rank",
        "chapter_a",
        "chapter_b",
        "persistence_count",
        "max_threshold",
        "similarity",
        "note",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_markdown(path: Path, book: str, rows: list[dict[str, Any]]) -> None:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        grouped[row["profile_type"]].append(row)

    lines = []
    lines.append(f"# {book} Drift Profile")
    lines.append("")
    lines.append("## Source Boundary")
    lines.append("")
    lines.append("This report is generated only from threshold sweep TSV files.")
    lines.append("No Scripture text, commentary, semantic labels, or external sources are used.")
    lines.append("")

    for section in [
        "persistent_pair",
        "persistent_singularity",
        "partial_singularity",
        "integrated",
        "threshold_fragmentation",
    ]:
        lines.append(f"## {section}")
        lines.append("")

        section_rows = grouped.get(section, [])

        if not section_rows:
            lines.append("- none")
            lines.append("")
            continue

        for row in section_rows:
            lines.append(f"- {row['note']}")

        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def process_book(book: str) -> tuple[Path, Path]:
    base = reports_dir()

    sweep_path = base / f"{book}-threshold-sweep.tsv"
    edge_path = base / f"{book}-threshold-edge-persistence.tsv"

    sweep_rows = read_tsv(sweep_path)
    edge_rows = read_tsv(edge_path)

    rows = []
    rows.extend(build_persistent_pairs(edge_rows))
    rows.extend(build_singularity_profiles(sweep_rows))
    rows.extend(build_fragmentation_profiles(sweep_rows))

    tsv_out = base / f"{book}-drift-profile.tsv"
    md_out = base / f"{book}-drift-profile.md"

    write_tsv(tsv_out, rows)
    write_markdown(md_out, book, rows)

    return tsv_out, md_out


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_metric_drift_profile.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    outputs = process_book(book)

    for path in outputs:
        print(f"WROTE: {path}")


if __name__ == "__main__":
    main()
