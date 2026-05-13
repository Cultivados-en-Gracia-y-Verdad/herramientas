#!/usr/bin/env python3

"""ROOTS Greek Step 5
Mechanical topology proposal engine.

PURPOSE
-------
This layer proposes visual topology only.

It does NOT:
- confirm hierarchy
- confirm subordination
- force every clause into a tree
- hide unresolved structures

INPUTS
------
1. clause ownership
2. clause spans

OUTPUT
------
structure-tree.tsv

CORE PRINCIPLE
--------------
Topology must remain epistemologically conservative.
Parallel structures should not be forced into false nesting.
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

PARALLEL_CONDITIONAL_STARTERS = {
    "εἰ",
    "εἴ",
}

PARALLEL_PAIR_MARKERS = {
    "δὲ",
    "δέ",
    "μέν",
    "μὲν",
}


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
    parent_clause: str
    relationship_type: str
    depth: int
    node_type: str
    notes: str


def read_spans(path: Path):
    grouped = defaultdict(dict)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            grouped[(row["BOOK"], row["CH"], row["VS"])] [row["CLAUSE_ID"]] = Span(
                clause_id=row["CLAUSE_ID"],
                finite_greek=row["FINITE_GREEK"],
                span_text=row["SPAN_TEXT"],
            )

    return grouped


def read_ownership(path: Path):
    grouped = defaultdict(list)

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


def is_parallel_conditional(span_text: str) -> bool:
    text = span_text.strip()

    return (
        any(text.startswith(x) for x in PARALLEL_CONDITIONAL_STARTERS)
        and any(x in text for x in PARALLEL_PAIR_MARKERS)
    )


def build_parent_map(spans, relationships):
    parent_map = {}

    span_lookup = {s.clause_id: s for s in spans.values()}

    for rel in relationships:

        if rel.status != "suggested":
            continue

        if not rel.source_clause or not rel.target_clause:
            continue

        target_span = span_lookup.get(rel.target_clause)

        if target_span:
            if is_parallel_conditional(target_span.span_text):
                continue

        if rel.target_clause in parent_map:
            continue

        parent_map[rel.target_clause] = rel

    return parent_map


def compute_depth(clause_id, parent_map):
    visited = set()
    current = clause_id
    depth = 0
    notes = []

    while current in parent_map:

        if current in visited:
            notes.append("cycle-detected")
            break

        visited.add(current)

        rel = parent_map[current]
        parent = rel.source_clause

        if not parent:
            break

        depth += 1
        current = parent

        if depth > 50:
            notes.append("depth-overflow-protection")
            break

    return depth, notes


def node_type(clause_id, parent_map, children):

    if clause_id not in parent_map and clause_id in children:
        return "root-parent"

    if clause_id not in parent_map:
        return "root-or-unresolved"

    if clause_id in children:
        return "internal-node"

    return "leaf"


def build_rows(spans_grouped, ownership_grouped):

    rows = []

    keys = sorted(
        set(spans_grouped.keys()) | set(ownership_grouped.keys()),
        key=lambda x: (x[0], int(x[1]), int(x[2]))
    )

    for key in keys:

        book, ch, vs = key

        spans = spans_grouped.get(key, {})
        relationships = ownership_grouped.get(key, [])

        parent_map = build_parent_map(spans, relationships)

        children = defaultdict(list)

        for target, rel in parent_map.items():
            children[rel.source_clause].append(target)

        for clause_id, span in sorted(spans.items()):

            rel = parent_map.get(clause_id)

            parent_clause = rel.source_clause if rel else ""
            relationship_type = rel.ownership_type if rel else ""
            confidence = rel.confidence if rel else ""
            status = rel.status if rel else "unresolved-root"
            notes = rel.notes if rel else "no-confirmed-topology"

            if is_parallel_conditional(span.span_text):
                notes = f"{notes}; parallel-conditional-structure-detected"

            depth, depth_notes = compute_depth(clause_id, parent_map)

            if depth_notes:
                notes = f"{notes}; {'; '.join(depth_notes)}"

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
                notes,
            ])

    return rows


def write_tsv(path, rows):

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main():

    parser = argparse.ArgumentParser(description="ROOTS Greek Step 5 topology proposal engine")

    parser.add_argument("book")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")

    args = parser.parse_args()

    spans = read_spans(
        Path(args.dataset_dir) / f"{args.book}-clause-spans.tsv"
    )

    ownership = read_ownership(
        Path(args.dataset_dir) / f"{args.book}-clause-ownership.tsv"
    )

    rows = build_rows(spans, ownership)

    out_path = Path(args.dataset_dir) / f"{args.book}-structure-tree.tsv"

    write_tsv(out_path, rows)

    counts = Counter(r[5] for r in rows)

    print(f"Wrote {out_path}")
    print({
        "rows": len(rows),
        "root_parent": counts.get("root-parent", 0),
        "root_or_unresolved": counts.get("root-or-unresolved", 0),
        "internal_node": counts.get("internal-node", 0),
        "leaf": counts.get("leaf", 0),
    })


if __name__ == "__main__":
    main()
