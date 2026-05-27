#!/usr/bin/env python3

"""
ROOTS Greek Step 3
Build the canonical ROOTS-GREEK structural dataset.

INPUTS
------
1. verbs/connectors database
2. connector analysis database

OUTPUT
------
MNA/roots-greek/dataset/{book}-roots-greek.tsv

CORE PRINCIPLE
--------------
This script NEVER upgrades suggestions into confirmed structure.

The dataset distinguishes:
- certain facts
- suggested relationships
- unresolved relationships

The goal is certainty, traceability, and auditability.

No Spanish.
No interpretation.
No hidden inference.
"""

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


HEADER = [
    "BOOK",
    "CH",
    "VS",
    "CLAUSE_ID",
    "CLAUSE_TYPE",
    "FINITE_G_IDX",
    "FINITE_GREEK",
    "FINITE_LEMMA",
    "FINITE_RMAC",
    "FINITE_CERTAINTY",
    "CONNECTOR_ID",
    "CONNECTOR_GREEK",
    "CONNECTOR_KIND",
    "CONNECTOR_RELATION",
    "CONNECTOR_FUNCTION_STATUS",
    "CONNECTOR_FUNCTION",
    "SOURCE_CLAUSE",
    "TARGET_CLAUSE",
    "CONNECTION_CONFIDENCE",
    "STATUS",
    "NOTES",
]


@dataclass
class VerbRecord:
    book: str
    ch: str
    vs: str
    g_idx: int
    rec_id: str
    greek: str
    lemma: str
    rmac: str
    finite: str


@dataclass
class ConnectorRecord:
    book: str
    ch: str
    vs: str
    cn_id: str
    g_idx: int
    greek: str
    kind: str
    relation: str
    function: str
    function_confidence: str
    source_clause: str
    target_clause: str
    connection_confidence: str
    status: str
    notes: str


@dataclass
class Clause:
    clause_id: str
    finite_g_idx: int
    finite_greek: str
    finite_lemma: str
    finite_rmac: str
    clause_type: str


def read_step1(path: Path) -> List[VerbRecord]:
    out: List[VerbRecord] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            if row.get("TYPE") != "verb":
                continue

            if row.get("FINITE") != "F":
                continue

            try:
                g_idx = int(row.get("G_IDX", "999999"))
            except Exception:
                g_idx = 999999

            out.append(
                VerbRecord(
                    book=row.get("BOOK", ""),
                    ch=row.get("CH", ""),
                    vs=row.get("VS", ""),
                    g_idx=g_idx,
                    rec_id=row.get("ID", ""),
                    greek=row.get("GREEK", ""),
                    lemma=row.get("LEMMA", ""),
                    rmac=row.get("RMAC", ""),
                    finite=row.get("FINITE", ""),
                )
            )

    return out


def read_step2(path: Path) -> List[ConnectorRecord]:
    out: List[ConnectorRecord] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            try:
                g_idx = int(row.get("G_IDX", "999999"))
            except Exception:
                g_idx = 999999

            out.append(
                ConnectorRecord(
                    book=row.get("BOOK", ""),
                    ch=row.get("CH", ""),
                    vs=row.get("VS", ""),
                    cn_id=row.get("CN_ID", ""),
                    g_idx=g_idx,
                    greek=row.get("GREEK", ""),
                    kind=row.get("CONNECTOR_KIND", ""),
                    relation=row.get("DEFAULT_RELATION", ""),
                    function=row.get("LEVEL3_SUGGESTED_FUNCTION", ""),
                    function_confidence=row.get("LEVEL3_CONFIDENCE", ""),
                    source_clause=row.get("LEVEL4_SUGGESTED_SOURCE", ""),
                    target_clause=row.get("LEVEL4_SUGGESTED_TARGET", ""),
                    connection_confidence=row.get("LEVEL4_CONFIDENCE", ""),
                    status=row.get("STATUS", ""),
                    notes=row.get("NOTES", ""),
                )
            )

    return out


def group_verbs(records: List[VerbRecord]) -> Dict[Tuple[str, str, str], List[VerbRecord]]:
    grouped = defaultdict(list)

    for rec in records:
        grouped[(rec.book, rec.ch, rec.vs)].append(rec)

    for key in grouped:
        grouped[key].sort(key=lambda r: r.g_idx)

    return grouped


def group_connectors(records: List[ConnectorRecord]) -> Dict[Tuple[str, str, str], List[ConnectorRecord]]:
    grouped = defaultdict(list)

    for rec in records:
        grouped[(rec.book, rec.ch, rec.vs)].append(rec)

    for key in grouped:
        grouped[key].sort(key=lambda r: r.g_idx)

    return grouped


def build_clauses(verbs: List[VerbRecord]) -> List[Clause]:
    """
    Objective clause layer.

    RULE:
    Each finite verb creates a clause anchor.

    This does NOT yet attempt:
    - full clause boundaries
    - hierarchy
    - indentation
    - discourse ownership

    It creates only confirmed finite clause anchors.
    """

    clauses: List[Clause] = []

    for idx, verb in enumerate(verbs, start=1):
        clauses.append(
            Clause(
                clause_id=f"C{idx}",
                finite_g_idx=verb.g_idx,
                finite_greek=verb.greek,
                finite_lemma=verb.lemma,
                finite_rmac=verb.rmac,
                clause_type="finite-anchor",
            )
        )

    return clauses


def build_dataset(
    verb_groups: Dict[Tuple[str, str, str], List[VerbRecord]],
    connector_groups: Dict[Tuple[str, str, str], List[ConnectorRecord]],
) -> List[List[str]]:

    rows: List[List[str]] = []

    all_keys = sorted(
        set(verb_groups) | set(connector_groups),
        key=lambda x: (x[0], int(x[1]), int(x[2]))
    )

    for key in all_keys:
        book, ch, vs = key

        verbs = verb_groups.get(key, [])
        connectors = connector_groups.get(key, [])

        clauses = build_clauses(verbs)

        clause_lookup = {c.clause_id: c for c in clauses}

        if not connectors:
            for clause in clauses:
                rows.append([
                    book,
                    ch,
                    vs,
                    clause.clause_id,
                    clause.clause_type,
                    f"{clause.finite_g_idx:02d}",
                    clause.finite_greek,
                    clause.finite_lemma,
                    clause.finite_rmac,
                    "certain",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "confirmed-finite-anchor",
                    "finite clause anchor with no connector relationship",
                ])

            continue

        for clause in clauses:
            related = [
                cn for cn in connectors
                if cn.source_clause == clause.clause_id
                or cn.target_clause == clause.clause_id
            ]

            if not related:
                rows.append([
                    book,
                    ch,
                    vs,
                    clause.clause_id,
                    clause.clause_type,
                    f"{clause.finite_g_idx:02d}",
                    clause.finite_greek,
                    clause.finite_lemma,
                    clause.finite_rmac,
                    "certain",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "confirmed-finite-anchor",
                    "finite clause anchor with unresolved connector relationship",
                ])

                continue

            for cn in related:
                rows.append([
                    book,
                    ch,
                    vs,
                    clause.clause_id,
                    clause.clause_type,
                    f"{clause.finite_g_idx:02d}",
                    clause.finite_greek,
                    clause.finite_lemma,
                    clause.finite_rmac,
                    "certain",
                    cn.cn_id,
                    cn.greek,
                    cn.kind,
                    cn.relation,
                    cn.status,
                    cn.function,
                    cn.source_clause,
                    cn.target_clause,
                    cn.connection_confidence,
                    "suggested-relationship",
                    cn.notes,
                ])

    return rows


def write_tsv(path: Path, rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 3 dataset builder")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--db-dir", default="MNA/roots-greek/db")
    parser.add_argument("--out-dir", default="MNA/roots-greek/dataset")
    args = parser.parse_args()

    step1 = Path(args.db_dir) / f"{args.book}-verbs-connectors.tsv"
    step2 = Path(args.db_dir) / f"{args.book}-connector-analysis.tsv"

    verbs = read_step1(step1)
    connectors = read_step2(step2)

    verb_groups = group_verbs(verbs)
    connector_groups = group_connectors(connectors)

    rows = build_dataset(verb_groups, connector_groups)

    out_path = Path(args.out_dir) / f"{args.book}-roots-greek.tsv"

    write_tsv(out_path, rows)

    confirmed = sum(1 for r in rows if r[19] == "confirmed-finite-anchor")
    suggested = sum(1 for r in rows if r[19] == "suggested-relationship")

    print(f"Wrote {out_path}")
    print({
        "rows": len(rows),
        "confirmed_finite_anchors": confirmed,
        "suggested_relationships": suggested,
    })


if __name__ == "__main__":
    main()
