#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — subject gap audit

This script audits the remaining unresolved subject cases after subject
refinement.

Purpose:
- identify unresolved subject records
- show immediate previous/next stream context
- expose why inheritance did not resolve the subject
- prepare precise rule improvements

This script does NOT:
- read Scripture text
- use semantic labels
- infer topology
- assign H0/H1/H2
- interpret discourse

Allowed input:
- MNA/data/refined-subjects/<book>-refined-subjects.jsonl

Outputs:
- MNA/data/refined-subjects/audits/<book>-subject-gaps.tsv
- MNA/data/refined-subjects/audits/<book>-subject-gaps.md

Usage:
    python3 MNA/scripts/roots_audit_subject_gaps.py 1corintios
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

WINDOW = 2


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return rows


def unresolved_subject(row: dict[str, Any]) -> bool:
    return not row.get("subject_person") or not row.get("subject_number")


def context_summary(row: dict[str, Any] | None) -> str:
    if row is None:
        return ""

    return " | ".join([
        f"idx={row.get('stream_index')}",
        f"ref={row.get('chapter')}:{row.get('verse')}",
        f"pid={row.get('predication_id')}",
        f"verb={row.get('finite_verb')}",
        f"compact={row.get('finite_compact')}",
        f"subj={row.get('subject_person') or '-'}{row.get('subject_number') or '-'}",
        f"src={row.get('subject_source')}",
        f"refine={row.get('subject_refinement_status')}",
        f"reason={row.get('subject_refinement_source')}",
        f"ind={row.get('independence_status')}",
        f"subord={row.get('subordination_status')}",
    ])


def audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []

    for i, row in enumerate(rows):
        if not unresolved_subject(row):
            continue

        previous_rows = []
        next_rows = []

        for offset in range(WINDOW, 0, -1):
            previous_rows.append(rows[i - offset] if i - offset >= 0 else None)

        for offset in range(1, WINDOW + 1):
            next_rows.append(rows[i + offset] if i + offset < len(rows) else None)

        out.append({
            "stream_index": row.get("stream_index"),
            "book": row.get("book"),
            "chapter": row.get("chapter"),
            "verse": row.get("verse"),
            "predication_id": row.get("predication_id"),
            "finite_verb": row.get("finite_verb"),
            "finite_compact": row.get("finite_compact"),
            "subject_status": row.get("subject_status"),
            "subject_source": row.get("subject_source"),
            "subject_refinement_status": row.get("subject_refinement_status"),
            "subject_refinement_source": row.get("subject_refinement_source"),
            "subject_inherited_from": row.get("subject_inherited_from"),
            "independence_status": row.get("independence_status"),
            "subordination_status": row.get("subordination_status"),
            "prev_2": context_summary(previous_rows[0]),
            "prev_1": context_summary(previous_rows[1]),
            "current": context_summary(row),
            "next_1": context_summary(next_rows[0]),
            "next_2": context_summary(next_rows[1]),
        })

    return out


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "stream_index",
        "book",
        "chapter",
        "verse",
        "predication_id",
        "finite_verb",
        "finite_compact",
        "subject_status",
        "subject_source",
        "subject_refinement_status",
        "subject_refinement_source",
        "subject_inherited_from",
        "independence_status",
        "subordination_status",
        "prev_2",
        "prev_1",
        "current",
        "next_1",
        "next_2",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_md(path: Path, rows: list[dict[str, Any]], book: str) -> None:
    lines = []
    lines.append(f"# {book} Subject Gap Audit")
    lines.append("")
    lines.append("## Source Boundary")
    lines.append("")
    lines.append("This report is generated only from refined subject JSONL records.")
    lines.append("No Scripture text, commentary, semantic labels, or external sources are used.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- unresolved_subject_records: {len(rows)}")
    lines.append("")
    lines.append("## Gaps")
    lines.append("")

    for row in rows:
        lines.append(f"### {row['predication_id']}")
        lines.append("")
        lines.append(f"- stream_index: {row['stream_index']}")
        lines.append(f"- reference: {row['chapter']}:{row['verse']}")
        lines.append(f"- finite_verb: {row['finite_verb']}")
        lines.append(f"- finite_compact: {row['finite_compact']}")
        lines.append(f"- subject_source: {row['subject_source']}")
        lines.append(f"- refinement_status: {row['subject_refinement_status']}")
        lines.append(f"- refinement_source: {row['subject_refinement_source']}")
        lines.append(f"- independence_status: {row['independence_status']}")
        lines.append(f"- subordination_status: {row['subordination_status']}")
        lines.append("- context:")
        for key in ["prev_2", "prev_1", "current", "next_1", "next_2"]:
            if row.get(key):
                lines.append(f"  - {key}: {row[key]}")
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def process_book(book: str) -> tuple[Path, Path, int]:
    in_path = (
        mna_root()
        / "data"
        / "refined-subjects"
        / f"{book}-refined-subjects.jsonl"
    )

    rows = read_jsonl(in_path)
    gaps = audit(rows)

    out_dir = mna_root() / "data" / "refined-subjects" / "audits"
    tsv_out = out_dir / f"{book}-subject-gaps.tsv"
    md_out = out_dir / f"{book}-subject-gaps.md"

    write_tsv(tsv_out, gaps)
    write_md(md_out, gaps, book)

    return tsv_out, md_out, len(gaps)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_audit_subject_gaps.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    tsv_out, md_out, count = process_book(book)

    print(f"WROTE {count} subject gap record(s): {tsv_out}")
    print(f"WROTE {count} subject gap record(s): {md_out}")


if __name__ == "__main__":
    main()
