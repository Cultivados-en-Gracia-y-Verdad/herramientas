#!/usr/bin/env python3

"""
ROOTS Greek Step 6
Controlled PASO 6 renderer.

INPUTS
------
MNA/roots-greek/dataset/{book}-certainty-gate.tsv
MNA/roots-greek/dataset/{book}-clause-spans.tsv
MNA/roots-greek/dataset/{book}-structure-tree.tsv

OUTPUT
------
MNA/roots-greek/output/{book}-paso6.md

CORE PRINCIPLE
--------------
This renderer NEVER hides certainty boundaries.

It does NOT:
- promote suggestions to facts
- confirm hierarchy
- suppress unresolved structures
- render BLOCKED topology as final structure

It visibly marks:
- FACT
- SUGGESTION
- REVIEW
- BLOCKED-TOPOLOGY

Greek-only.
No Spanish.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


CERTAINTY_SYMBOLS = {
    "FACT": "[FACT]",
    "SUGGESTION": "[SUGGESTION]",
    "REVIEW": "[REVIEW]",
    "BLOCKED": "[BLOCKED]",
}

TOPOLOGY_SYMBOL = "[BLOCKED-TOPOLOGY]"


def read_tsv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def build_certainty_lookup(rows: List[Dict[str, str]]) -> Dict[Tuple[str, str, str], str]:
    lookup = {}

    for row in rows:
        layer = row.get("LAYER", "")

        if layer != "step3.5-clause-spans":
            continue

        key = (
            row.get("BOOK", ""),
            row.get("CH", ""),
            row.get("VS", ""),
            row.get("ITEM_ID", ""),
        )

        lookup[key] = row.get("CLASSIFICATION", "REVIEW")

    return lookup


def group_spans(rows: List[Dict[str, str]]) -> Dict[Tuple[str, str, str], List[Dict[str, str]]]:
    grouped = defaultdict(list)

    for row in rows:
        grouped[(
            row.get("BOOK", ""),
            row.get("CH", ""),
            row.get("VS", ""),
        )].append(row)

    return grouped


def build_tree_lookup(rows: List[Dict[str, str]]) -> Dict[Tuple[str, str, str, str], Dict[str, str]]:
    lookup = {}

    for row in rows:
        key = (
            row.get("BOOK", ""),
            row.get("CH", ""),
            row.get("VS", ""),
            row.get("CLAUSE_ID", ""),
        )

        lookup[key] = row

    return lookup


def render_clause(
    span_row: Dict[str, str],
    certainty_lookup: Dict[Tuple[str, str, str, str], str],
    tree_lookup: Dict[Tuple[str, str, str, str], Dict[str, str]],
) -> List[str]:

    book = span_row.get("BOOK", "")
    ch = span_row.get("CH", "")
    vs = span_row.get("VS", "")
    clause_id = span_row.get("CLAUSE_ID", "")

    key = (book, ch, vs, clause_id)

    certainty = certainty_lookup.get(key, "REVIEW")
    certainty_symbol = CERTAINTY_SYMBOLS.get(certainty, "[REVIEW]")

    tree = tree_lookup.get(key, {})

    depth = int(tree.get("TREE_DEPTH", "0") or "0")
    node_type = tree.get("NODE_TYPE", "unknown")
    parent = tree.get("PARENT_CLAUSE", "")

    # Indentation is drawn from Step 5 topology. The certainty gate classifies
    # that topology as BLOCKED, so indentation is disclosed as visual evidence,
    # not confirmed hierarchy.
    indent = "    " * depth

    lines = []

    meta = f"{certainty_symbol} {TOPOLOGY_SYMBOL} {clause_id}"

    if parent:
        meta += f" ← {parent}"

    meta += f" | {node_type}"

    if depth > 0:
        meta += f" | visual-depth={depth}"

    lines.append(f"{indent}{meta}")
    lines.append(f"{indent}{span_row.get('SPAN_TEXT', '')}")

    return lines


def render_book(
    grouped_spans,
    certainty_lookup,
    tree_lookup,
) -> str:

    lines = []

    verse_keys = sorted(
        grouped_spans.keys(),
        key=lambda x: (x[0], int(x[1]), int(x[2]))
    )

    for book, ch, vs in verse_keys:
        lines.append(f"# {book} {ch}:{vs}")
        lines.append("")
        lines.append("## PASO 6 — MOSTRAR LA ESTRUCTURA")
        lines.append("")
        lines.append("[DISCLOSURE] Clause spans are provisional. Topology/indentation is BLOCKED evidence, not confirmed hierarchy.")
        lines.append("")

        spans = sorted(
            grouped_spans[(book, ch, vs)],
            key=lambda r: int(r.get("CLAUSE_ID", "C999").replace("C", ""))
        )

        for span in spans:
            lines.extend(render_clause(span, certainty_lookup, tree_lookup))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 6 controlled PASO 6 renderer")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    parser.add_argument("--out-dir", default="MNA/roots-greek/output")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)

    certainty_rows = read_tsv(dataset_dir / f"{args.book}-certainty-gate.tsv")
    span_rows = read_tsv(dataset_dir / f"{args.book}-clause-spans.tsv")
    tree_rows = read_tsv(dataset_dir / f"{args.book}-structure-tree.tsv")

    certainty_lookup = build_certainty_lookup(certainty_rows)
    grouped_spans = group_spans(span_rows)
    tree_lookup = build_tree_lookup(tree_rows)

    rendered = render_book(
        grouped_spans,
        certainty_lookup,
        tree_lookup,
    )

    out_path = Path(args.out_dir) / f"{args.book}-paso6.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")

    print(f"Wrote {out_path}")
    print({
        "verses": len(grouped_spans),
        "clauses": len(span_rows),
    })


if __name__ == "__main__":
    main()
