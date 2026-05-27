#!/usr/bin/env python3

"""
ROOTS Greek Step 4
Resolve suggested clause ownership relationships.

INPUTS
------
1. Clause spans:
   MNA/roots-greek/dataset/{book}-clause-spans.tsv

2. Connector analysis:
   MNA/roots-greek/db/{book}-connector-analysis.tsv

OUTPUT
------
MNA/roots-greek/dataset/{book}-clause-ownership.tsv

CORE PRINCIPLE
--------------
This layer resolves ONLY suggested ownership relationships.

It does NOT:
- create final hierarchy
- indent clauses
- build PASO 6-8 structure
- force ownership certainty

It preserves:
- confidence
- unresolved relationships
- cross-verse ambiguity
- competing ownership possibilities

Greek-only.
No Spanish.
"""

import argparse
import csv
from collections import defaultdict, Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

HEADER = [
    "BOOK",
    "CH",
    "VS",
    "CONNECTOR_ID",
    "CONNECTOR_GREEK",
    "CONNECTOR_KIND",
    "CONNECTOR_RELATION",
    "SOURCE_CLAUSE",
    "TARGET_CLAUSE",
    "OWNERSHIP_TYPE",
    "OWNERSHIP_CONFIDENCE",
    "OWNERSHIP_STATUS",
    "SOURCE_SPAN",
    "TARGET_SPAN",
    "NOTES",
]

SUBORDINATING_RELATIONS = {
    "purpose/result",
    "purpose",
    "condition",
    "content/cause",
    "cause/ground",
    "comparison/manner",
    "temporal/condition",
    "cause/temporal",
    "temporal",
    "result/inference",
}

COORDINATING_RELATIONS = {
    "coordination",
    "negative coordination",
    "contrast",
    "contrast/exception",
    "alternative",
    "alternative/comparison",
    "inference",
}


@dataclass
class Span:
    clause_id: str
    span_text: str
    finite_greek: str


@dataclass
class Connector:
    book: str
    ch: str
    vs: str
    connector_id: str
    greek: str
    kind: str
    relation: str
    source_clause: str
    target_clause: str
    confidence: str
    status: str
    notes: str


def read_clause_spans(path: Path) -> Dict[Tuple[str, str, str], Dict[str, Span]]:
    grouped: Dict[Tuple[str, str, str], Dict[str, Span]] = defaultdict(dict)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            key = (row["BOOK"], row["CH"], row["VS"])
            grouped[key][row["CLAUSE_ID"]] = Span(
                clause_id=row["CLAUSE_ID"],
                span_text=row["SPAN_TEXT"],
                finite_greek=row["FINITE_GREEK"],
            )

    return grouped


def read_connector_analysis(path: Path) -> Dict[Tuple[str, str, str], List[Connector]]:
    grouped: Dict[Tuple[str, str, str], List[Connector]] = defaultdict(list)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            grouped[(row["BOOK"], row["CH"], row["VS"])] .append(
                Connector(
                    book=row["BOOK"],
                    ch=row["CH"],
                    vs=row["VS"],
                    connector_id=row["CN_ID"],
                    greek=row["GREEK"],
                    kind=row["CONNECTOR_KIND"],
                    relation=row["DEFAULT_RELATION"],
                    source_clause=row["LEVEL4_SUGGESTED_SOURCE"],
                    target_clause=row["LEVEL4_SUGGESTED_TARGET"],
                    confidence=row["LEVEL4_CONFIDENCE"],
                    status=row["STATUS"],
                    notes=row["NOTES"],
                )
            )

    return grouped


def ownership_type(connector: Connector) -> str:
    if connector.relation in SUBORDINATING_RELATIONS:
        return "subordinate"

    if connector.relation in COORDINATING_RELATIONS:
        return "coordinate"

    if connector.kind == "negation":
        return "internal-negation"

    return "unresolved"


def resolve_relationship(connector: Connector) -> Tuple[str, str]:
    """
    Conservative ownership resolution.

    NEVER upgrades suggestions to confirmed.
    """

    if not connector.target_clause:
        return "pending", "missing target clause"

    if connector.kind == "negation":
        return "internal", "negation modifies internal clause content"

    if connector.source_clause and connector.target_clause:
        return "suggested", "source and target clauses available"

    if connector.target_clause and not connector.source_clause:
        return "cross-verse-or-missing-source", "target clause found but source clause unresolved"

    return "unresolved", "insufficient structural evidence"


def build_rows(
    spans: Dict[Tuple[str, str, str], Dict[str, Span]],
    connectors: Dict[Tuple[str, str, str], List[Connector]],
) -> List[List[str]]:

    rows: List[List[str]] = []

    keys = sorted(
        set(spans.keys()) | set(connectors.keys()),
        key=lambda x: (x[0], int(x[1]), int(x[2]))
    )

    for key in keys:
        verse_spans = spans.get(key, {})
        verse_connectors = connectors.get(key, [])

        for cn in verse_connectors:
            ownership = ownership_type(cn)
            status, note = resolve_relationship(cn)

            source_span = ""
            target_span = ""

            if cn.source_clause in verse_spans:
                source_span = verse_spans[cn.source_clause].span_text

            if cn.target_clause in verse_spans:
                target_span = verse_spans[cn.target_clause].span_text

            rows.append([
                cn.book,
                cn.ch,
                cn.vs,
                cn.connector_id,
                cn.greek,
                cn.kind,
                cn.relation,
                cn.source_clause,
                cn.target_clause,
                ownership,
                cn.confidence,
                status,
                source_span,
                target_span,
                f"{cn.notes}; {note}".strip("; "),
            ])

    return rows


def write_tsv(path: Path, rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 4 clause ownership resolver")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    parser.add_argument("--db-dir", default="MNA/roots-greek/db")
    args = parser.parse_args()

    spans_path = Path(args.dataset_dir) / f"{args.book}-clause-spans.tsv"
    connectors_path = Path(args.db_dir) / f"{args.book}-connector-analysis.tsv"

    spans = read_clause_spans(spans_path)
    connectors = read_connector_analysis(connectors_path)

    rows = build_rows(spans, connectors)

    out_path = Path(args.dataset_dir) / f"{args.book}-clause-ownership.tsv"

    write_tsv(out_path, rows)

    status_counts = Counter(r[11] for r in rows)

    print(f"Wrote {out_path}")
    print({
        "rows": len(rows),
        "suggested": status_counts.get("suggested", 0),
        "cross_verse_or_missing_source": status_counts.get("cross-verse-or-missing-source", 0),
        "internal": status_counts.get("internal", 0),
        "unresolved": status_counts.get("unresolved", 0),
        "pending": status_counts.get("pending", 0),
    })


if __name__ == "__main__":
    main()
