#!/usr/bin/env python3

"""
Audit the ROOTS-GREEK structural dataset.

Input:
  MNA/roots-greek/dataset/{book}-roots-greek.tsv

Output:
  MNA/roots-greek/reports/{book}-roots-greek-audit.md

This audit does not modify data.
It reports certainty, suggested relationships, unresolved structure, and places
where the dataset must remain pending.
"""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def verse_key(row: Dict[str, str]) -> Tuple[str, int, int]:
    try:
        ch = int(row.get("CH", "0"))
        vs = int(row.get("VS", "0"))
    except Exception:
        ch, vs = 0, 0
    return row.get("BOOK", ""), ch, vs


def unique_clause_key(row: Dict[str, str]) -> Tuple[str, str, str, str]:
    return (
        row.get("BOOK", ""),
        row.get("CH", ""),
        row.get("VS", ""),
        row.get("CLAUSE_ID", ""),
    )


def summarize(rows: List[Dict[str, str]]) -> Dict[str, object]:
    status_counts = Counter(row.get("STATUS", "") for row in rows)
    connection_counts = Counter(row.get("CONNECTION_CONFIDENCE", "") or "blank" for row in rows)
    function_status_counts = Counter(row.get("CONNECTOR_FUNCTION_STATUS", "") or "blank" for row in rows)
    connector_kind_counts = Counter(row.get("CONNECTOR_KIND", "") or "blank" for row in rows)
    connector_relation_counts = Counter(row.get("CONNECTOR_RELATION", "") or "blank" for row in rows)

    clause_keys = {unique_clause_key(row) for row in rows}
    verses = {verse_key(row) for row in rows}

    clauses_with_suggestions = {
        unique_clause_key(row)
        for row in rows
        if row.get("STATUS") == "suggested-relationship"
    }

    clauses_confirmed_only = {
        unique_clause_key(row)
        for row in rows
        if row.get("STATUS") == "confirmed-finite-anchor"
    }

    unresolved_clauses = clauses_confirmed_only - clauses_with_suggestions

    suggested_rows = [row for row in rows if row.get("STATUS") == "suggested-relationship"]
    medium_rows = [row for row in suggested_rows if row.get("CONNECTION_CONFIDENCE") == "medium"]
    low_rows = [row for row in suggested_rows if row.get("CONNECTION_CONFIDENCE") == "low"]
    none_rows = [row for row in suggested_rows if row.get("CONNECTION_CONFIDENCE") == "none"]

    source_blank = [row for row in suggested_rows if not row.get("SOURCE_CLAUSE")]
    target_blank = [row for row in suggested_rows if not row.get("TARGET_CLAUSE")]

    return {
        "status_counts": status_counts,
        "connection_counts": connection_counts,
        "function_status_counts": function_status_counts,
        "connector_kind_counts": connector_kind_counts,
        "connector_relation_counts": connector_relation_counts,
        "total_rows": len(rows),
        "total_verses": len(verses),
        "total_clause_anchors": len(clause_keys),
        "clauses_with_suggestions": len(clauses_with_suggestions),
        "unresolved_clauses": len(unresolved_clauses),
        "medium_rows": medium_rows,
        "low_rows": low_rows,
        "none_rows": none_rows,
        "source_blank": source_blank,
        "target_blank": target_blank,
    }


def row_ref(row: Dict[str, str]) -> str:
    return f"{row.get('BOOK')} {row.get('CH')}:{row.get('VS')} {row.get('CLAUSE_ID')}"


def connector_ref(row: Dict[str, str]) -> str:
    cn = row.get("CONNECTOR_ID") or "-"
    greek = row.get("CONNECTOR_GREEK") or "-"
    rel = row.get("CONNECTOR_RELATION") or "-"
    conf = row.get("CONNECTION_CONFIDENCE") or "-"
    src = row.get("SOURCE_CLAUSE") or "?"
    tgt = row.get("TARGET_CLAUSE") or "?"
    return f"- {row_ref(row)} | {cn} {greek} | {rel} | {src} → {tgt} | confidence: {conf}"


def render_counter(title: str, counter: Counter) -> List[str]:
    lines = [f"## {title}", ""]
    if not counter:
        lines.append("- none")
        lines.append("")
        return lines
    for key, value in counter.most_common():
        lines.append(f"- {key}: {value}")
    lines.append("")
    return lines


def render_sample(title: str, rows: List[Dict[str, str]], limit: int = 25) -> List[str]:
    lines = [f"## {title}", ""]
    if not rows:
        lines.append("- none")
        lines.append("")
        return lines
    for row in rows[:limit]:
        lines.append(connector_ref(row))
    if len(rows) > limit:
        lines.append(f"- ... {len(rows) - limit} more")
    lines.append("")
    return lines


def render_report(book: str, rows: List[Dict[str, str]], summary: Dict[str, object]) -> str:
    lines: List[str] = []

    lines.append(f"# ROOTS-GREEK Dataset Audit: {book}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- total rows: {summary['total_rows']}")
    lines.append(f"- total verses represented: {summary['total_verses']}")
    lines.append(f"- total finite clause anchors: {summary['total_clause_anchors']}")
    lines.append(f"- clause anchors with suggested connector relationships: {summary['clauses_with_suggestions']}")
    lines.append(f"- unresolved clause anchors: {summary['unresolved_clauses']}")
    lines.append("")

    lines.extend(render_counter("Status Counts", summary["status_counts"]))
    lines.extend(render_counter("Connection Confidence Counts", summary["connection_counts"]))
    lines.extend(render_counter("Connector Function Status Counts", summary["function_status_counts"]))
    lines.extend(render_counter("Connector Kind Counts", summary["connector_kind_counts"]))
    lines.extend(render_counter("Connector Relation Counts", summary["connector_relation_counts"]))

    lines.append("## Certainty Boundary")
    lines.append("")
    lines.append("- Confirmed: finite clause anchors only.")
    lines.append("- Suggested: connector function and connector clause relationships.")
    lines.append("- Not confirmed: hierarchy, indentation, source/target ownership, PASO 6–8 final structure.")
    lines.append("")

    lines.extend(render_sample("Medium-Confidence Suggested Relationships", summary["medium_rows"]))
    lines.extend(render_sample("Low-Confidence Suggested Relationships", summary["low_rows"]))
    lines.extend(render_sample("No-Clause-Connection Suggested Rows", summary["none_rows"]))
    lines.extend(render_sample("Suggested Relationships Missing Source Clause", summary["source_blank"]))
    lines.extend(render_sample("Suggested Relationships Missing Target Clause", summary["target_blank"]))

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit ROOTS-GREEK structural dataset.")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    parser.add_argument("--out-dir", default="MNA/roots-greek/reports")
    args = parser.parse_args()

    in_path = Path(args.dataset_dir) / f"{args.book}-roots-greek.tsv"
    out_path = Path(args.out_dir) / f"{args.book}-roots-greek-audit.md"

    rows = read_tsv(in_path)
    summary = summarize(rows)
    report = render_report(args.book, rows, summary)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    print(f"Wrote {out_path}")
    print({
        "rows": summary["total_rows"],
        "verses": summary["total_verses"],
        "finite_clause_anchors": summary["total_clause_anchors"],
        "unresolved_clause_anchors": summary["unresolved_clauses"],
    })


if __name__ == "__main__":
    main()
