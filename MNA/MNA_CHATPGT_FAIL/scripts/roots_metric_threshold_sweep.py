#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — metric threshold sweep / drift report

Data-only observation layer.

This script reads only the collected chapter similarity report and tests how
chapter clusters change as the similarity threshold rises or falls.

Allowed input:
- MNA/data/predications/reports/<book>-chapter-similarity.tsv

Outputs:
- MNA/data/predications/reports/<book>-threshold-sweep.tsv
- MNA/data/predications/reports/<book>-threshold-sweep.md

This script does NOT:
- read Scripture text
- use commentary
- use headings
- use semantic labels
- assign H0/H1/H2
- infer topology
- attach connectors

The purpose is to observe cluster persistence and structural drift strictly
from collected predication-metric similarity data.

Usage from repository root:
    python3 MNA/scripts/roots_metric_threshold_sweep.py 1corintios

Usage from MNA directory:
    python3 scripts/roots_metric_threshold_sweep.py 1corintios

Optional custom thresholds:
    python3 MNA/scripts/roots_metric_threshold_sweep.py 1corintios 0.20,0.25,0.30,0.35,0.40
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLDS = [0.20, 0.25, 0.30, 0.35, 0.40]


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def reports_dir() -> Path:
    return mna_root() / "data" / "predications" / "reports"


def read_similarity(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"chapter_a", "chapter_b", "distance", "similarity"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")

        for row in reader:
            rows.append({
                "chapter_a": int(row["chapter_a"]),
                "chapter_b": int(row["chapter_b"]),
                "distance": float(row["distance"]),
                "similarity": float(row["similarity"]),
            })
    return rows


class UnionFind:
    def __init__(self, nodes: set[int]) -> None:
        self.parent = {node: node for node in nodes}

    def find(self, node: int) -> int:
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, a: int, b: int) -> None:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a != root_b:
            self.parent[root_b] = root_a

    def groups(self) -> list[list[int]]:
        grouped: defaultdict[int, list[int]] = defaultdict(list)
        for node in sorted(self.parent):
            grouped[self.find(node)].append(node)
        return sorted((sorted(values) for values in grouped.values()), key=lambda group: (len(group), group), reverse=True)


def clusters_for_threshold(rows: list[dict[str, Any]], threshold: float) -> tuple[list[list[int]], list[dict[str, Any]]]:
    chapters: set[int] = set()
    edges: list[dict[str, Any]] = []

    for row in rows:
        chapters.add(row["chapter_a"])
        chapters.add(row["chapter_b"])
        if row["similarity"] >= threshold:
            edges.append(row)

    uf = UnionFind(chapters)
    for edge in edges:
        uf.union(edge["chapter_a"], edge["chapter_b"])

    return uf.groups(), edges


def cluster_label(cluster: list[int]) -> str:
    return ",".join(str(chapter) for chapter in cluster)


def build_sweep(rows: list[dict[str, Any]], thresholds: list[float]) -> list[dict[str, Any]]:
    sweep_rows: list[dict[str, Any]] = []

    for threshold in sorted(thresholds):
        clusters, edges = clusters_for_threshold(rows, threshold)
        for cluster_id, cluster in enumerate(clusters, start=1):
            internal_edges = []
            for edge in edges:
                if edge["chapter_a"] in cluster and edge["chapter_b"] in cluster:
                    internal_edges.append(edge)

            similarities = [edge["similarity"] for edge in internal_edges]
            avg_similarity = round(sum(similarities) / len(similarities), 4) if similarities else 0
            max_similarity = round(max(similarities), 4) if similarities else 0
            min_similarity = round(min(similarities), 4) if similarities else 0

            sweep_rows.append({
                "threshold": threshold,
                "cluster_id": cluster_id,
                "cluster_size": len(cluster),
                "chapters": cluster_label(cluster),
                "edge_count": len(internal_edges),
                "avg_similarity": avg_similarity,
                "max_similarity": max_similarity,
                "min_similarity": min_similarity,
            })

    return sweep_rows


def build_edge_persistence(rows: list[dict[str, Any]], thresholds: list[float]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    sorted_thresholds = sorted(thresholds)

    for row in sorted(rows, key=lambda r: r["similarity"], reverse=True):
        survives = [threshold for threshold in sorted_thresholds if row["similarity"] >= threshold]
        if not survives:
            continue
        out.append({
            "chapter_a": row["chapter_a"],
            "chapter_b": row["chapter_b"],
            "similarity": row["similarity"],
            "distance": row["distance"],
            "survives_thresholds": ",".join(f"{threshold:.2f}" for threshold in survives),
            "max_survived_threshold": max(survives),
            "persistence_count": len(survives),
        })
    return out


def write_sweep_tsv(path: Path, sweep_rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "threshold",
        "cluster_id",
        "cluster_size",
        "chapters",
        "edge_count",
        "avg_similarity",
        "max_similarity",
        "min_similarity",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in sweep_rows:
            writer.writerow(row)


def write_edge_persistence_tsv(path: Path, edge_rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "chapter_a",
        "chapter_b",
        "similarity",
        "distance",
        "survives_thresholds",
        "max_survived_threshold",
        "persistence_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in edge_rows:
            writer.writerow(row)


def write_markdown(path: Path, book: str, sweep_rows: list[dict[str, Any]], edge_rows: list[dict[str, Any]], thresholds: list[float]) -> None:
    lines: list[str] = []
    lines.append(f"# {book} Metric Threshold Sweep")
    lines.append("")
    lines.append("## Source Boundary")
    lines.append("")
    lines.append("This report is generated only from the collected chapter similarity TSV file.")
    lines.append("It does not use Bible text, commentary, headings, semantic labels, or external sources.")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append("Chapters are connected when similarity is greater than or equal to the tested threshold.")
    lines.append("Clusters are connected components at each threshold.")
    lines.append("This report observes cluster drift only; it does not assign H0/H1/H2 and does not infer topology.")
    lines.append("")
    lines.append("## Thresholds")
    lines.append("")
    lines.append("- " + ", ".join(f"{threshold:.2f}" for threshold in sorted(thresholds)))
    lines.append("")
    lines.append("## Cluster Sweep")
    lines.append("")

    rows_by_threshold: defaultdict[float, list[dict[str, Any]]] = defaultdict(list)
    for row in sweep_rows:
        rows_by_threshold[float(row["threshold"])].append(row)

    for threshold in sorted(rows_by_threshold):
        lines.append(f"### Threshold {threshold:.2f}")
        lines.append("")
        for row in rows_by_threshold[threshold]:
            lines.append(
                f"- cluster {row['cluster_id']}: chapters={row['chapters']} | size={row['cluster_size']} | edges={row['edge_count']} | avg_similarity={row['avg_similarity']}"
            )
        lines.append("")

    lines.append("## Most Persistent Chapter Pairs")
    lines.append("")
    for row in edge_rows[:20]:
        lines.append(
            f"- {row['chapter_a']} ↔ {row['chapter_b']}: similarity={row['similarity']} | survives={row['survives_thresholds']}"
        )
    lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_thresholds(raw: str | None) -> list[float]:
    if not raw:
        return DEFAULT_THRESHOLDS
    thresholds = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if not thresholds:
        raise ValueError("No thresholds supplied")
    return sorted(set(thresholds))


def process_book(book: str, thresholds: list[float]) -> tuple[Path, Path, Path]:
    base = reports_dir()
    similarity_path = base / f"{book}-chapter-similarity.tsv"
    rows = read_similarity(similarity_path)

    sweep_rows = build_sweep(rows, thresholds)
    edge_rows = build_edge_persistence(rows, thresholds)

    sweep_tsv = base / f"{book}-threshold-sweep.tsv"
    edge_tsv = base / f"{book}-threshold-edge-persistence.tsv"
    md_out = base / f"{book}-threshold-sweep.md"

    write_sweep_tsv(sweep_tsv, sweep_rows)
    write_edge_persistence_tsv(edge_tsv, edge_rows)
    write_markdown(md_out, book, sweep_rows, edge_rows, thresholds)

    return sweep_tsv, edge_tsv, md_out


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_metric_threshold_sweep.py <book> [thresholds]\n"
            "\nExample:\n"
            "  python3 MNA/scripts/roots_metric_threshold_sweep.py 1corintios\n"
            "  python3 MNA/scripts/roots_metric_threshold_sweep.py 1corintios 0.20,0.25,0.30,0.35,0.40",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    thresholds = parse_thresholds(sys.argv[2] if len(sys.argv) == 3 else None)
    outputs = process_book(book, thresholds)
    for path in outputs:
        print(f"WROTE: {path}")


if __name__ == "__main__":
    main()
