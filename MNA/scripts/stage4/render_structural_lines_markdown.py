#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

VERSION = "stage4-structural-line-markdown-renderer-v1"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Required input not found: {path}")
    rows = []
    metadata = {}
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)
    return metadata, rows


def marker_text(row):
    markers = []
    if row.get("s_marker"):
        markers.append(row["s_marker"])
    if row.get("m_marker"):
        markers.append(row["m_marker"])
    return " ".join(markers) if markers else "—"


def reasons_text(row):
    reasons = row.get("line_break_reasons") or []
    return ", ".join(reasons) if reasons else "—"


def main() -> int:
    ap = argparse.ArgumentParser(description="Render Stage 4 structural line test as Markdown.")
    ap.add_argument("book")
    args = ap.parse_args()

    book = args.book.strip().lower()
    mna = root()
    in_path = mna / "datasets" / "stage4-test" / book / "structural-lines.jsonl"
    out_path = mna / "datasets" / "stage4-test" / book / "structural-lines.md"

    metadata, rows = load_jsonl(in_path)

    by_line = defaultdict(list)
    for row in rows:
        by_line[row["line_id"]].append(row)

    lines = []
    lines.append(f"# MNA Stage 4 TEST — Structural Lines: {book}")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("TEMPORARY TEST OUTPUT — NOT CANONICAL")
    lines.append("")
    lines.append("## Source")
    lines.append("")
    lines.append(f"- Input: `{metadata.get('source', '')}`")
    lines.append(f"- Builder: `{metadata.get('builder_version', VERSION)}`")
    lines.append(f"- Rows: `{len(rows)}`")
    lines.append(f"- Lines: `{len(by_line)}`")
    lines.append("")
    lines.append("## Rule Used")
    lines.append("")
    lines.append("A new structural line begins when a row after the first has one or more of:")
    lines.append("")
    lines.append("- `[S]` subject marker")
    lines.append("- `[M]` movement marker")
    lines.append("- explicit connector before the anchor")
    lines.append("")
    lines.append("No trunk, units, labels, titles, or semantic grouping are claimed.")
    lines.append("")
    lines.append("---")
    lines.append("")

    for line_id in sorted(by_line.keys()):
        line_rows = by_line[line_id]
        first = line_rows[0]
        refs = []
        for r in line_rows:
            ref = f"{r['chapter']}:{r['verse']}"
            if ref not in refs:
                refs.append(ref)
        lines.append(f"## {line_id} — {'; '.join(refs)}")
        lines.append("")

        if first.get("line_break_before"):
            lines.append(f"**Break before:** {reasons_text(first)}")
            lines.append("")

        lines.append("| Order | Ref | Anchor | Verb | Lemma | Morph | Subject Signal | Markers | Connector | Break Reasons |")
        lines.append("|---:|---|---|---|---|---|---|---|---|---|")
        for r in line_rows:
            ref = f"{r['chapter']}:{r['verse']}"
            lines.append(
                "| "
                + " | ".join([
                    str(r.get("order", "")),
                    ref,
                    str(r.get("anchor_id", "")),
                    str(r.get("greek_form", "")),
                    str(r.get("lemma", "")),
                    str(r.get("morphology", "")),
                    str(r.get("subject_signal", "")),
                    marker_text(r),
                    str(r.get("explicit_connector_before", "")) or "—",
                    reasons_text(r),
                ])
                + " |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")

    print("MNA Stage 4 TEST — Markdown Renderer")
    print(f"BOOK: {book}")
    print(f"OUTPUT: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
