#!/usr/bin/env python3

"""
ROOTS Greek Step 5.7
Apply a certainty gate to all current Greek-only structural layers.

INPUTS
------
MNA/roots-greek/db/{book}-verbs-connectors.tsv
MNA/roots-greek/dataset/{book}-clause-spans.tsv
MNA/roots-greek/dataset/{book}-clause-ownership.tsv
MNA/roots-greek/dataset/{book}-structure-tree.tsv
MNA/roots-greek/dataset/{book}-cross-verse-candidates.tsv

OUTPUT
------
MNA/roots-greek/dataset/{book}-certainty-gate.tsv

CORE PRINCIPLE
--------------
No suggested relationship may be used as structure unless explicitly promoted
by an audit rule.

This script does NOT promote anything.
It classifies each layer as:
- FACT
- SUGGESTION
- REVIEW
- BLOCKED

Greek-only.
No Spanish.
No interpretation.
No hidden hierarchy.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Dict, List

HEADER = [
    "BOOK",
    "CH",
    "VS",
    "LAYER",
    "ITEM_ID",
    "ITEM_TYPE",
    "SURFACE",
    "CLASSIFICATION",
    "ALLOWED_DOWNSTREAM_USE",
    "BLOCKS_PASO_RENDERING",
    "REASON",
    "SOURCE_FILE",
]


def read_tsv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def add_row(rows, book, ch, vs, layer, item_id, item_type, surface, classification, allowed, blocks, reason, source_file):
    rows.append([
        book,
        ch,
        vs,
        layer,
        item_id,
        item_type,
        surface,
        classification,
        allowed,
        blocks,
        reason,
        source_file,
    ])


def gate_step1(book: str, db_dir: Path, rows: List[List[str]]) -> None:
    path = db_dir / f"{book}-verbs-connectors.tsv"
    for r in read_tsv(path):
        rec_type = r.get("TYPE", "")
        item_id = r.get("ID", "")
        surface = r.get("GREEK", "")
        ch = r.get("CH", "")
        vs = r.get("VS", "")

        if rec_type == "verb":
            reason = "Greek verb detection from RMAC morphology"
            allowed = "verb-list; finite-anchor-input"
        elif rec_type == "connector":
            reason = "Greek connector word detected from approved inventory"
            allowed = "connector-list; connector-analysis-input"
        else:
            reason = "unknown Step 1 record type"
            allowed = "none"

        add_row(
            rows,
            book,
            ch,
            vs,
            "step1-verbs-connectors",
            item_id,
            rec_type,
            surface,
            "FACT" if rec_type in {"verb", "connector"} else "REVIEW",
            allowed,
            "no",
            reason,
            str(path),
        )


def gate_clause_spans(book: str, dataset_dir: Path, rows: List[List[str]]) -> None:
    path = dataset_dir / f"{book}-clause-spans.tsv"
    for r in read_tsv(path):
        add_row(
            rows,
            r.get("BOOK", book),
            r.get("CH", ""),
            r.get("VS", ""),
            "step3.5-clause-spans",
            r.get("CLAUSE_ID", ""),
            "clause-span",
            r.get("SPAN_TEXT", ""),
            "SUGGESTION",
            "display-as-provisional-clause-span; audit-input",
            "yes",
            "Clause boundaries are mechanically suggested, not confirmed hierarchy",
            str(path),
        )


def gate_clause_ownership(book: str, dataset_dir: Path, rows: List[List[str]]) -> None:
    path = dataset_dir / f"{book}-clause-ownership.tsv"
    for r in read_tsv(path):
        status = r.get("OWNERSHIP_STATUS", "")
        confidence = r.get("OWNERSHIP_CONFIDENCE", "")
        item_id = r.get("CONNECTOR_ID", "")
        surface = r.get("CONNECTOR_GREEK", "")

        if status == "suggested" and confidence == "medium":
            classification = "REVIEW"
            allowed = "review-only; possible-ownership-input"
            reason = "Ownership has source and target but remains suggested"
        elif status in {"cross-verse-or-missing-source", "pending", "unresolved"}:
            classification = "REVIEW"
            allowed = "review-only"
            reason = "Ownership is unresolved or cross-verse pending"
        elif status == "internal":
            classification = "SUGGESTION"
            allowed = "internal-clause-note"
            reason = "Internal relation such as negation; not clause hierarchy"
        else:
            classification = "REVIEW"
            allowed = "review-only"
            reason = "Ownership status is not a confirmed structural fact"

        add_row(
            rows,
            r.get("BOOK", book),
            r.get("CH", ""),
            r.get("VS", ""),
            "step4-clause-ownership",
            item_id,
            r.get("OWNERSHIP_TYPE", ""),
            surface,
            classification,
            allowed,
            "yes",
            reason,
            str(path),
        )


def gate_structure_tree(book: str, dataset_dir: Path, rows: List[List[str]]) -> None:
    path = dataset_dir / f"{book}-structure-tree.tsv"
    for r in read_tsv(path):
        add_row(
            rows,
            r.get("BOOK", book),
            r.get("CH", ""),
            r.get("VS", ""),
            "step5-structure-tree",
            r.get("CLAUSE_ID", ""),
            r.get("NODE_TYPE", ""),
            r.get("SPAN_TEXT", ""),
            "BLOCKED",
            "audit-only; cannot-render-final-structure",
            "yes",
            "Tree topology is built from suggested ownership and cannot be treated as confirmed hierarchy",
            str(path),
        )


def gate_cross_verse(book: str, dataset_dir: Path, rows: List[List[str]]) -> None:
    path = dataset_dir / f"{book}-cross-verse-candidates.tsv"
    for r in read_tsv(path):
        confidence = r.get("CANDIDATE_CONFIDENCE", "")
        status = r.get("STATUS", "")

        if status == "suggested-cross-verse-candidate":
            classification = "REVIEW"
            allowed = "review-only; cross-verse-evidence"
            reason = f"Cross-verse candidate remains unconfirmed; confidence={confidence}"
        else:
            classification = "BLOCKED"
            allowed = "none"
            reason = "No usable cross-verse candidate"

        add_row(
            rows,
            r.get("BOOK", book),
            r.get("CH", ""),
            r.get("VS", ""),
            "step5.5-cross-verse-candidates",
            r.get("CONNECTOR_ID", ""),
            r.get("CONNECTOR_RELATION", ""),
            r.get("CONNECTOR_GREEK", ""),
            classification,
            allowed,
            "yes",
            reason,
            str(path),
        )


def write_tsv(path: Path, rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 5.7 certainty gate")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--db-dir", default="MNA/roots-greek/db")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    args = parser.parse_args()

    rows: List[List[str]] = []
    db_dir = Path(args.db_dir)
    dataset_dir = Path(args.dataset_dir)

    gate_step1(args.book, db_dir, rows)
    gate_clause_spans(args.book, dataset_dir, rows)
    gate_clause_ownership(args.book, dataset_dir, rows)
    gate_structure_tree(args.book, dataset_dir, rows)
    gate_cross_verse(args.book, dataset_dir, rows)

    out_path = dataset_dir / f"{args.book}-certainty-gate.tsv"
    write_tsv(out_path, rows)

    counts = Counter(r[7] for r in rows)
    blocked_rendering = sum(1 for r in rows if r[9] == "yes")

    print(f"Wrote {out_path}")
    print({
        "rows": len(rows),
        "FACT": counts.get("FACT", 0),
        "SUGGESTION": counts.get("SUGGESTION", 0),
        "REVIEW": counts.get("REVIEW", 0),
        "BLOCKED": counts.get("BLOCKED", 0),
        "blocks_paso_rendering": blocked_rendering,
    })


if __name__ == "__main__":
    main()
