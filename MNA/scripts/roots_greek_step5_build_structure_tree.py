#!/usr/bin/env python3

"""
ROOTS Greek Step 5
Build a structural topology tree from clause ownership relationships.

INPUTS
------
1. Clause ownership:
   MNA/roots-greek/dataset/{book}-clause-ownership.tsv

2. Clause spans:
   MNA/roots-greek/dataset/{book}-clause-spans.tsv

OUTPUT
------
MNA/roots-greek/dataset/{book}-structure-tree.tsv

CORE PRINCIPLE
--------------
This layer builds structural topology only.

It does NOT:
- create final PASO rendering
- force hierarchy certainty
- hide unresolved branches
- collapse cross-verse ambiguity

The tree preserves:
- confidence
- unresolved ownership
- coordinate structures
- subordinate structures
- disconnected roots

Greek-only.
No Spanish.
"""

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

HEADER = [
    "BOOK",
    "CH",
    "VS",
    "CLAUSE_ID",
    "FINITE_GREEK",
    "NODE_TYPE",
    "PARENT_CLAUSE",
    "RELATIONSHIP_TYPE",
    "TREE_DEPTH",
    "OWNERSHIP_CONFIDENCE",
    "TREE_STATUS",
    "SPAN_TEXT",
    "NOTES",
]


@dataclass
class Span:
    clause_id: str
    finite_greek: str
    span_text: str


@dataclass
class Ownership:
    connector_id: str
    connector_greek: str
    source_clause: str
    target_clause: str
    ownership_type: str
    confidence: str
    status: str
    notes: str


@dataclass
class Node:
    clause_id: str
    finite_greek: str
    node_type: str
    parent_clause: str
    relationship_type: str
    depth: int
    confidence: str
    status: str
    span_text: str
    notes: str


def read_spans(path: Path) -> Dict[Tuple[str, str, str], Dict[str, Span]]:
    grouped: Dict[Tuple[str, str, str], Dict[str, Span]] = defaultdict(dict)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            key = (row["BOOK"], row["CH"], row["VS"])
            grouped[key][row["CLAUSE_ID"]] = Span(
                clause_id=row["CLAUSE_ID"],
                finite_greek=row["FINITE_GREEK"],
                span_text=row["SPAN_TEXT"],
            )

    return grouped


def read_ownership(path: Path) -> Dict[Tuple[str, str, str], List[Ownership]]:
    grouped: Dict[Tuple[str, str, str], List[Ownership]] = defaultdict(list)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            grouped[(row["BOOK"], row["CH"], row["VS"])] .append(
                Ownership(
                    connector_id=row["CONNECTOR_ID"],
                    connector_greek=row["CONNECTOR_GREEK"],
                    source_clause=row["SOURCE_CLAUSE"],
                    target_clause=row["TARGET_CLAUSE"],
                    ownership_type=row["OWNERSHIP_TYPE"],
                    confidence=row["OWNERSHIP_CONFIDENCE"],
                    status=row["OWNERSHIP_STATUS"],
                    notes=row["NOTES"],
                )
            )

    return grouped


def build_parent_map(relationships: List[Ownership]) -> Dict[str, Ownership]:
    """
    Conservative parent resolution.

    RULES:
    - only 'suggested' relationships may create parent links
    - target clause receives parent source clause
    - first structurally valid ownership wins
    - conflicting ownership remains unresolved via notes
    """

    parent_map: Dict[str, Ownership] = {}

    for rel in relationships:
        if rel.status != "suggested":
            continue

        if not rel.source_clause or not rel.target_clause:
            continue

        if rel.target_clause in parent_map:
            # preserve first ownership; ambiguity remains unresolved
            continue

        parent_map[rel.target_clause] = rel

    return parent_map


def compute_depth(clause_id: str, parent_map: Dict[str, Ownership]) -> Tuple[int, List[str]]:
    visited: Set[str] = set()
    current = clause_id
    depth = 0
    notes: List[str] = []

    while current in parent_map:
        if current in visited:
            notes.append("cycle detected")
            break

        visited.add(current)

        rel = parent_map[current]
        parent = rel.source_clause

        if not parent:
            break

        depth += 1
        current = parent

        if depth > 50:
            notes.append("depth overflow protection triggered")
            break

    return depth, notes


def node_type(clause_id: str, parent_map: Dict[str, Ownership], children: Dict[str, List[str]]) -> str:
    if clause_id not in parent_map and clause_id in children:
        return "root-parent"

    if clause_id not in parent_map:
        return "root-or-unresolved"

    if clause_id in children:
        return "internal-node"

    return "leaf"


def build_tree_rows(
    spans: Dict[Tuple[str, str, str], Dict[str, Span]],
    ownership: Dict[Tuple[str, str, str], List[Ownership]],
) -> List[List[str]]:

    rows: List[List[str]] = []

    keys = sorted(
        set(spans.keys()) | set(ownership.keys()),
        key=lambda x: (x[0], int(x[1]), int(x[2]))
    )

    for key in keys:
        book, ch, vs = key

        verse_spans = spans.get(key, {})
        relationships = ownership.get(key, [])

        parent_map = build_parent_map(relationships)

        children: Dict[str, List[str]] = defaultdict(list)
        for target, rel in parent_map.items():
            if rel.source_clause:
                children[rel.source_clause].append(target)

        for clause_id, span in sorted(verse_spans.items(), key=lambda x: x[0]):
            rel = parent_map.get(clause_id)

            parent_clause = rel.source_clause if rel else ""
            relationship_type = rel.ownership_type if rel else ""
            confidence = rel.confidence if rel else ""
            status = rel.status if rel else "unresolved-root"
            note = rel.notes if rel else "no ownership relationship resolved"

            depth, depth_notes = compute_depth(clause_id, parent_map)
            if depth_notes:
                note = f"{note}; {'; '.join(depth_notes)}".strip("; ")

            ntype = node_type(clause_id, parent_map, children)

            rows.append([
                book,
                ch,
                vs,
                clause_id,
                span.finite_greek,
                ntype,
                parent_clause,
                relationship_type,
                str(depth),
                confidence,
                status,
                span.span_text,
                note,
            ])

    return rows


def write_tsv(path: Path, rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 5 structural tree builder")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    args = parser.parse_args()

    spans_path = Path(args.dataset_dir) / f"{args.book}-clause-spans.tsv"
    ownership_path = Path(args.dataset_dir) / f"{args.book}-clause-ownership.tsv"

    spans = read_spans(spans_path)
    ownership = read_ownership(ownership_path)

    rows = build_tree_rows(spans, ownership)

    out_path = Path(args.dataset_dir) / f"{args.book}-structure-tree.tsv"

    write_tsv(out_path, rows)

    node_counts = Counter(r[5] for r in rows)

    print(f"Wrote {out_path}")
    print({
        "rows": len(rows),
        "root_parent": node_counts.get("root-parent", 0),
        "root_or_unresolved": node_counts.get("root-or-unresolved", 0),
        "internal_node": node_counts.get("internal-node", 0),
        "leaf": node_counts.get("leaf", 0),
    })


if __name__ == "__main__":
    main()
