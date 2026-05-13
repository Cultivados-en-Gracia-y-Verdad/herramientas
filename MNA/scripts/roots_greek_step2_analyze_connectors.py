#!/usr/bin/env python3

"""
ROOTS Greek Step 2
Analyze connector records produced by Step 1.

Input:
  MNA/roots-greek/db/{book}-verbs-connectors.tsv

Output:
  MNA/roots-greek/db/{book}-connector-analysis.tsv

This layer separates:
- lexical detection: certain
- connector category: high/certain by inventory
- suggested contextual function: suggested
- suggested clause connection: suggested/pending

No Spanish.
No interpretation.
No confirmed ownership yet.
"""

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HEADER = [
    "BOOK", "CH", "VS", "CN_ID", "G_IDX", "GREEK", "LEMMA", "RMAC",
    "DETECTED_CERTAINTY", "CONNECTOR_KIND", "DEFAULT_RELATION",
    "LEVEL1_DETECTED", "LEVEL2_CATEGORY_CERTAINTY",
    "LEVEL3_SUGGESTED_FUNCTION", "LEVEL3_CONFIDENCE",
    "LEVEL4_SUGGESTED_SOURCE", "LEVEL4_SUGGESTED_TARGET", "LEVEL4_CONFIDENCE",
    "STATUS", "NOTES",
]

FUNCTION_BY_RELATION = {
    "coordination": "coordinate/add",
    "negative coordination": "coordinate/negative",
    "contrast": "contrast",
    "contrast/exception": "contrast/exception",
    "cause/ground": "ground/explanation",
    "inference": "inference/result",
    "result/inference": "result/inference",
    "purpose/result": "purpose/result",
    "purpose": "purpose",
    "content/cause": "content-or-cause",
    "condition": "condition",
    "cause/temporal": "cause-or-temporal",
    "temporal/condition": "temporal-or-condition",
    "temporal": "temporal",
    "comparison/manner": "comparison/manner",
    "alternative/comparison": "alternative/comparison",
    "alternative": "alternative",
    "negation": "negation",
}

LOW_CONTEXT_RELATIONS = {
    "content/cause",
    "cause/temporal",
    "temporal/condition",
    "comparison/manner",
    "alternative/comparison",
    "purpose/result",
    "result/inference",
}

NON_CLAUSE_CONNECTOR_KINDS = {"negation"}


@dataclass
class Record:
    book: str
    ch: str
    vs: str
    g_idx: int
    rec_type: str
    rec_id: str
    greek: str
    lemma: str
    rmac: str
    finite: str
    connector_kind: str
    default_relation: str
    certainty: str


def read_step1(path: Path) -> List[Record]:
    records: List[Record] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                g_idx = int(row["G_IDX"])
            except Exception:
                g_idx = 999999
            records.append(
                Record(
                    book=row.get("BOOK", ""),
                    ch=row.get("CH", ""),
                    vs=row.get("VS", ""),
                    g_idx=g_idx,
                    rec_type=row.get("TYPE", ""),
                    rec_id=row.get("ID", ""),
                    greek=row.get("GREEK", ""),
                    lemma=row.get("LEMMA", ""),
                    rmac=row.get("RMAC", ""),
                    finite=row.get("FINITE", ""),
                    connector_kind=row.get("CONNECTOR_KIND", ""),
                    default_relation=row.get("DEFAULT_RELATION", ""),
                    certainty=row.get("CERTAINTY", ""),
                )
            )
    return records


def group_by_verse(records: List[Record]) -> Dict[Tuple[str, str, str], List[Record]]:
    grouped: Dict[Tuple[str, str, str], List[Record]] = defaultdict(list)
    for rec in records:
        grouped[(rec.book, rec.ch, rec.vs)].append(rec)
    for key in grouped:
        grouped[key].sort(key=lambda r: (r.g_idx, r.rec_type))
    return grouped


def finite_positions(verse_records: List[Record]) -> List[int]:
    return sorted(r.g_idx for r in verse_records if r.rec_type == "verb" and r.finite == "F")


def nearest_previous_finite(connector_idx: int, finite_idxs: List[int]) -> Optional[int]:
    prev = [idx for idx in finite_idxs if idx < connector_idx]
    return prev[-1] if prev else None


def nearest_next_finite(connector_idx: int, finite_idxs: List[int]) -> Optional[int]:
    nxt = [idx for idx in finite_idxs if idx > connector_idx]
    return nxt[0] if nxt else None


def clause_label_from_index(finite_idxs: List[int], finite_idx: Optional[int]) -> str:
    if finite_idx is None:
        return ""
    try:
        return f"C{finite_idxs.index(finite_idx) + 1}"
    except ValueError:
        return ""


def suggested_function(default_relation: str) -> Tuple[str, str, str]:
    function = FUNCTION_BY_RELATION.get(default_relation, default_relation or "unknown")
    if default_relation in LOW_CONTEXT_RELATIONS:
        return function, "medium", "context-sensitive function; keep as suggested"
    if not default_relation:
        return "unknown", "low", "missing default relation"
    return function, "high", "function follows connector inventory"


def suggested_connection(rec: Record, finite_idxs: List[int]) -> Tuple[str, str, str, str]:
    """
    Suggest source/target using only finite positions.

    This is intentionally conservative:
    - subordinating connectors usually point forward to the next finite clause as target
      and back to previous finite clause as source if present.
    - coordinating connectors suggest previous finite source + next finite target.
    - negators usually do not connect clauses, so ownership remains blank.
    """

    if rec.connector_kind in NON_CLAUSE_CONNECTOR_KINDS:
        return "", "", "none", "negation detected; no clause connection suggested"

    prev_idx = nearest_previous_finite(rec.g_idx, finite_idxs)
    next_idx = nearest_next_finite(rec.g_idx, finite_idxs)

    source = clause_label_from_index(finite_idxs, prev_idx)
    target = clause_label_from_index(finite_idxs, next_idx)

    if rec.connector_kind == "subordinating":
        if target and source:
            return source, target, "medium", "subordinating connector before/near target finite clause"
        if target:
            return "", target, "low", "target finite clause found; source not available in verse"
        return "", "", "low", "no target finite clause found in verse"

    if rec.connector_kind == "coordinating":
        if source and target:
            return source, target, "medium", "coordinating connector between finite clauses"
        if target:
            return "", target, "low", "connector before first finite clause or source outside verse"
        if source:
            return source, "", "low", "connector after last finite clause or target outside verse"
        return "", "", "low", "no finite clause anchor found in verse"

    if target:
        return source, target, "low", "connector word detected; structural role pending"

    return source, "", "low", "connector word detected; no forward finite target found"


def analyze(records: List[Record]) -> List[List[str]]:
    rows: List[List[str]] = []
    grouped = group_by_verse(records)

    for (_book, _ch, _vs), verse_records in sorted(grouped.items(), key=lambda x: (x[0][0], int(x[0][1]), int(x[0][2]))):
        finite_idxs = finite_positions(verse_records)

        for rec in verse_records:
            if rec.rec_type != "connector":
                continue

            function, function_confidence, function_note = suggested_function(rec.default_relation)
            source, target, connection_confidence, connection_note = suggested_connection(rec, finite_idxs)

            notes = "; ".join(note for note in [function_note, connection_note] if note)

            rows.append([
                rec.book, rec.ch, rec.vs, rec.rec_id, f"{rec.g_idx:02d}", rec.greek, rec.lemma, rec.rmac,
                rec.certainty or "certain", rec.connector_kind, rec.default_relation,
                "yes", "high",
                function, function_confidence,
                source, target, connection_confidence,
                "suggested", notes,
            ])

    return rows


def write_tsv(path: Path, rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 2: analyze connector words.")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--db-dir", default="MNA/roots-greek/db")
    args = parser.parse_args()

    in_path = Path(args.db_dir) / f"{args.book}-verbs-connectors.tsv"
    out_path = Path(args.db_dir) / f"{args.book}-connector-analysis.tsv"

    records = read_step1(in_path)
    rows = analyze(records)
    write_tsv(out_path, rows)

    counts = defaultdict(int)
    for row in rows:
        counts[row[18]] += 1
        counts[f"function:{row[14]}"] += 1
        counts[f"connection:{row[17]}"] += 1

    print(f"Wrote {out_path}")
    print({"connectors": len(rows), "status_suggested": counts["suggested"], "connection_medium": counts["connection:medium"], "connection_low": counts["connection:low"], "connection_none": counts["connection:none"]})


if __name__ == "__main__":
    main()
