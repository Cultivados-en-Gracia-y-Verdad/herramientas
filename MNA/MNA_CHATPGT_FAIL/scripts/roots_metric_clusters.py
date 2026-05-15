#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — data-only metric cluster report

This script groups chapters using only the collected metric similarity report.
It does not read Scripture text, headings, commentary, semantic labels, or any
external source.

Allowed input:
- MNA/data/predications/reports/<book>-chapter-similarity.tsv

Outputs:
- MNA/data/predications/reports/<book>-metric-clusters.tsv
- MNA/data/predications/reports/<book>-metric-clusters.md

The clusters are observational only. They are not H0/H1/H2, not topology, and
not interpretation.

Usage from repository root:
    python3 MNA/scripts/roots_metric_clusters.py 1corintios

Usage from MNA directory:
    python3 scripts/roots_metric_clusters.py 1corintios
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLD = 0.25


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
        return sorted((sorted(values) for values in grouped.values()), key=lambda g: (len(g), g), reverse=True)


def build_clusters(rows: list[dict[str, Any]], threshold: float) -> tuple[list[list[int]], list[dict[str, Any]]]:
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


def write_cluster_tsv(path: Path, clusters: list[list[int]], edges: list[dict[str, Any]], threshold: float) -> None:
    edge_lookup: defaultdict[int, list[str]] = defaultdict(list)
    for edge in edges:
        label = f"{edge['chapter_a']}-{edge['chapter_b']}:{edge['similarity']}"
        edge_lookup[edge["chapter_a"]].append(label)
        edge_lookup[edge["chapter_b"]].append(label)

    with path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["threshold", "cluster_id", "cluster_size", "chapters", "supporting_edges"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for cluster_id, cluster in enumerate(clusters, start=1):
            supporting_edges = sorted({edge for chapter in cluster for edge in edge_lookup[chapter]})
            writer.writerow({
                "threshold": threshold,
                "cluster_id": cluster_id,
                "cluster_size": len(cluster),
                "chapters": ",".join(str(chapter) for chapter in cluster),
                "supporting_edges": ";".join(supporting_edges),
            })


def write_cluster_md(path: Path, book: str, clusters: list[list[int]], edges: list[dict[str, Any]], threshold: float) -> None:
    lines: list[str] = []
    lines.append(f"# {book} Metric Clusters")
    lines.append("")
    lines.append("## Source Boundary")
    lines.append("")
    lines.append("This report is generated only from the collected chapter similarity TSV file.")
    lines.append("It does not use Bible text, commentary, headings, semantic labels, or external sources.")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(f"Chapters are connected when similarity >= {threshold}.")
    lines.append("Clusters are connected components formed from those chapter-to-chapter similarities.")
    lines.append("These clusters are observational only; they are not H0/H1/H2 and not topology.")
    lines.append("")
    lines.append("## Clusters")
    lines.append("")

    edge_by_pair = {(edge["chapter_a"], edge["chapter_b"]): edge for edge in edges}

    for cluster_id, cluster in enumerate(clusters, start=1):
        lines.append(f"### Cluster {cluster_id}")
        lines.append("")
        lines.append(f"- chapters: {', '.join(str(chapter) for chapter in cluster)}")
        lines.append(f"- size: {len(cluster)}")
        lines.append("- supporting similarities:")
        supported = False
        for i, a in enumerate(cluster):
            for b in cluster[i + 1:]:
                edge = edge_by_pair.get((a, b)) or edge_by_pair.get((b, a))
                if edge and edge["similarity"] >= threshold:
                    supported = True
                    lines.append(f"  - {a} ↔ {b}: similarity={edge['similarity']} distance={edge['distance']}")
        if not supported:
            lines.append("  - none above threshold")
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def process_book(book: str, threshold: float = DEFAULT_THRESHOLD) -> tuple[Path, Path]:
    base = reports_dir()
    similarity_path = base / f"{book}-chapter-similarity.tsv"
    rows = read_similarity(similarity_path)
    clusters, edges = build_clusters(rows, threshold)

    tsv_out = base / f"{book}-metric-clusters.tsv"
    md_out = base / f"{book}-metric-clusters.md"

    write_cluster_tsv(tsv_out, clusters, edges, threshold)
    write_cluster_md(md_out, book, clusters, edges, threshold)

    return tsv_out, md_out


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_metric_clusters.py <book> [similarity_threshold]\n"
            "\nExample:\n"
            "  python3 MNA/scripts/roots_metric_clusters.py 1corintios\n"
            "  python3 MNA/scripts/roots_metric_clusters.py 1corintios 0.30",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    threshold = float(sys.argv[2]) if len(sys.argv) == 3 else DEFAULT_THRESHOLD
    outputs = process_book(book, threshold)
    for path in outputs:
        print(f"WROTE: {path}")


if __name__ == "__main__":
    main()
