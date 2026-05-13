#!/usr/bin/env python3

"""
ROOTS Greek Step 5.5
Find cross-verse ownership candidates.

INPUTS
------
1. Clause ownership:
   MNA/roots-greek/dataset/{book}-clause-ownership.tsv

2. Clause spans:
   MNA/roots-greek/dataset/{book}-clause-spans.tsv

OUTPUT
------
MNA/roots-greek/dataset/{book}-cross-verse-candidates.tsv

CORE PRINCIPLE
--------------
This script finds candidates only.

It does NOT:
- modify clause ownership
- modify the structure tree
- confirm cross-verse ownership
- create hierarchy
- render PASO 6-8 output

It only identifies connectors whose source clause is missing in the current
verse and suggests a previous-verse clause as a possible source.

Greek-only.
No Spanish.
"""

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HEADER = [
    "BOOK",
    "CH",
    "VS",
    "CONNECTOR_ID",
    "CONNECTOR_GREEK",
    "CONNECTOR_KIND",
    "CONNECTOR_RELATION",
    "CURRENT_TARGET_CLAUSE",
    "CURRENT_TARGET_SPAN",
    "CANDIDATE_SOURCE_REF",
    "CANDIDATE_SOURCE_CLAUSE",
    "CANDIDATE_SOURCE_SPAN",
    "CANDIDATE_DISTANCE",
    "CANDIDATE_CONFIDENCE",
    "STATUS",
    "NOTES",
]

# These connectors frequently continue, ground, contrast, or develop the
# previous clause or previous verse. This list does not confirm ownership.
BACKWARD_LOOKING_RELATIONS = {
    "cause/ground",
    "inference",
    "contrast",
    "contrast/exception",
    "coordination",
    "negative coordination",
    "content/cause",
    "comparison/manner",
    "purpose/result",
    "purpose",
    "condition",
    "result/inference",
    "alternative",
    "alternative/comparison",
}

STRONG_BACKWARD_RELATIONS = {
    "cause/ground",
    "inference",
    "contrast",
    "contrast/exception",
    "result/inference",
}


@dataclass
class Span:
    book: str
    ch: str
    vs: str
    clause_id: str
    finite_g_idx: int
    span_text: str


@dataclass
class Ownership:
    book: str
    ch: str
    vs: str
    connector_id: str
    connector_greek: str
    connector_kind: str
    connector_relation: str
    source_clause: str
    target_clause: str
    ownership_type: str
    confidence: str
    status: str
    target_span: str
    notes: str


def parse_int(value: str, default: int = -1) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def verse_sort_key(book: str, ch: str, vs: str) -> Tuple[str, int, int]:
    return book, parse_int(ch, 999999), parse_int(vs, 999999)


def read_spans(path: Path) -> Dict[Tuple[str, str, str], Dict[str, Span]]:
    grouped: Dict[Tuple[str, str, str], Dict[str, Span]] = defaultdict(dict)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            key = (row["BOOK"], row["CH"], row["VS"])
            grouped[key][row["CLAUSE_ID"]] = Span(
                book=row["BOOK"],
                ch=row["CH"],
                vs=row["VS"],
                clause_id=row["CLAUSE_ID"],
                finite_g_idx=parse_int(row.get("FINITE_G_IDX"), 999999),
                span_text=row.get("SPAN_TEXT", ""),
            )

    return grouped


def read_ownership(path: Path) -> List[Ownership]:
    rows: List[Ownership] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(
                Ownership(
                    book=row.get("BOOK", ""),
                    ch=row.get("CH", ""),
                    vs=row.get("VS", ""),
                    connector_id=row.get("CONNECTOR_ID", ""),
                    connector_greek=row.get("CONNECTOR_GREEK", ""),
                    connector_kind=row.get("CONNECTOR_KIND", ""),
                    connector_relation=row.get("CONNECTOR_RELATION", ""),
                    source_clause=row.get("SOURCE_CLAUSE", ""),
                    target_clause=row.get("TARGET_CLAUSE", ""),
                    ownership_type=row.get("OWNERSHIP_TYPE", ""),
                    confidence=row.get("OWNERSHIP_CONFIDENCE", ""),
                    status=row.get("OWNERSHIP_STATUS", ""),
                    target_span=row.get("TARGET_SPAN", ""),
                    notes=row.get("NOTES", ""),
                )
            )

    return rows


def sorted_verse_keys(spans: Dict[Tuple[str, str, str], Dict[str, Span]]) -> List[Tuple[str, str, str]]:
    return sorted(spans.keys(), key=lambda k: verse_sort_key(*k))


def previous_verse_key(
    current: Tuple[str, str, str],
    verse_keys: List[Tuple[str, str, str]],
) -> Optional[Tuple[str, str, str]]:
    try:
        idx = verse_keys.index(current)
    except ValueError:
        return None

    if idx <= 0:
        return None

    return verse_keys[idx - 1]


def last_clause(spans_for_verse: Dict[str, Span]) -> Optional[Span]:
    if not spans_for_verse:
        return None

    def clause_num(item: Tuple[str, Span]) -> int:
        cid = item[0]
        try:
            return int(cid.lstrip("C"))
        except Exception:
            return 999999

    return sorted(spans_for_verse.items(), key=clause_num)[-1][1]


def should_consider_cross_verse(row: Ownership) -> bool:
    if row.source_clause:
        return False

    if not row.target_clause:
        return False

    if row.status not in {"cross-verse-or-missing-source", "suggested", "pending", "unresolved"}:
        return False

    if row.connector_relation not in BACKWARD_LOOKING_RELATIONS:
        return False

    # Focus first on cases like ? -> C1. Later we can expand cautiously.
    return row.target_clause == "C1"


def confidence_for(row: Ownership, previous_key: Optional[Tuple[str, str, str]], candidate: Optional[Span]) -> Tuple[str, str]:
    if previous_key is None or candidate is None:
        return "none", "no previous verse candidate available"

    if row.connector_relation in STRONG_BACKWARD_RELATIONS:
        return "medium", "strong backward-looking relation; previous verse final clause available"

    if row.connector_kind == "coordinating":
        return "low", "coordinating connector may continue previous verse; keep low confidence"

    return "low", "possible cross-verse source; requires review"


def build_candidates(
    ownership_rows: List[Ownership],
    spans: Dict[Tuple[str, str, str], Dict[str, Span]],
) -> List[List[str]]:
    rows: List[List[str]] = []
    verse_keys = sorted_verse_keys(spans)

    for own in ownership_rows:
        if not should_consider_cross_verse(own):
            continue

        current_key = (own.book, own.ch, own.vs)
        prev_key = previous_verse_key(current_key, verse_keys)
        candidate = last_clause(spans.get(prev_key, {})) if prev_key else None

        confidence, note = confidence_for(own, prev_key, candidate)

        candidate_ref = ""
        candidate_clause = ""
        candidate_span = ""
        distance = ""

        if prev_key and candidate:
            candidate_ref = f"{candidate.book} {candidate.ch}:{candidate.vs}"
            candidate_clause = candidate.clause_id
            candidate_span = candidate.span_text
            distance = "previous-verse-final-clause"

        rows.append([
            own.book,
            own.ch,
            own.vs,
            own.connector_id,
            own.connector_greek,
            own.connector_kind,
            own.connector_relation,
            own.target_clause,
            own.target_span,
            candidate_ref,
            candidate_clause,
            candidate_span,
            distance,
            confidence,
            "suggested-cross-verse-candidate" if confidence != "none" else "no-candidate",
            f"{own.notes}; {note}".strip("; "),
        ])

    return rows


def write_tsv(path: Path, rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 5.5 cross-verse candidate finder")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    args = parser.parse_args()

    ownership_path = Path(args.dataset_dir) / f"{args.book}-clause-ownership.tsv"
    spans_path = Path(args.dataset_dir) / f"{args.book}-clause-spans.tsv"
    out_path = Path(args.dataset_dir) / f"{args.book}-cross-verse-candidates.tsv"

    ownership_rows = read_ownership(ownership_path)
    spans = read_spans(spans_path)

    rows = build_candidates(ownership_rows, spans)
    write_tsv(out_path, rows)

    counts = Counter(r[14] for r in rows)
    confidence_counts = Counter(r[13] for r in rows)

    print(f"Wrote {out_path}")
    print({
        "rows": len(rows),
        "suggested_cross_verse_candidate": counts.get("suggested-cross-verse-candidate", 0),
        "no_candidate": counts.get("no-candidate", 0),
        "medium": confidence_counts.get("medium", 0),
        "low": confidence_counts.get("low", 0),
        "none": confidence_counts.get("none", 0),
    })


if __name__ == "__main__":
    main()
