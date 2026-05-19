#!/usr/bin/env python3
"""
MNA Stage 4 — Export ROOTS Constraint Failures

Purpose:
- Read the Stage 4 ROOTS constraint audit JSONL.
- Join failures to current suggested-trunk rows.
- Export a focused Markdown review file for mechanical correction.

This script does not modify datasets.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            if obj.get("record_type") == "metadata":
                continue
            rows.append(obj)
    return rows


def ref_key(reference: str) -> tuple[int, int]:
    _book, cv = reference.rsplit(" ", 1)
    chapter, verse = cv.split(":", 1)
    return int(chapter), int(verse)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export Stage 4 ROOTS constraint failures for review.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)

    root = mna_root_from_script()
    book = args.book.strip().lower()

    audit_path = root / "exports" / "audits" / f"{book}-stage4-roots-constraint-audit.jsonl"
    trunk_path = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"
    output_path = root / "exports" / "audits" / f"{book}-stage4-roots-failures.md"

    audit_rows = load_jsonl(audit_path)
    trunk_rows = load_jsonl(trunk_path)
    trunk_by_ref = {row.get("reference"): row for row in trunk_rows}

    failures_by_ref: dict[str, list[dict]] = defaultdict(list)
    for row in audit_rows:
        if row.get("severity") == "FAIL":
            failures_by_ref[str(row.get("reference"))].append(row)

    refs = sorted(failures_by_ref, key=ref_key)
    if args.limit:
        refs = refs[: args.limit]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# Stage 4 ROOTS Constraint Failures — {book}")
    lines.append("")
    lines.append(f"Total failure references shown: {len(refs)}")
    lines.append("")

    for reference in refs:
        trunk_row = trunk_by_ref.get(reference, {})
        trunk = trunk_row.get("trunk_greek") or ""
        confidence = trunk_row.get("confidence") or ""
        status = trunk_row.get("status") or ""
        notes = trunk_row.get("review_notes") or trunk_row.get("notes") or ""

        lines.append(f"## {reference}")
        lines.append("")
        lines.append(f"- Status: `{status}`")
        lines.append(f"- Confidence: `{confidence}`")
        lines.append("")
        lines.append("### Failures")
        for failure in failures_by_ref[reference]:
            lines.append(f"- `{failure.get('code')}` — {failure.get('detail')}")
        lines.append("")
        lines.append("### Current trunk")
        lines.append("```text")
        lines.append(str(trunk))
        lines.append("```")
        if notes:
            lines.append("")
            lines.append("### Current notes")
            lines.append(str(notes))
        lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print("MNA Stage 4 — Export ROOTS Constraint Failures")
    print(f"BOOK: {book}")
    print(f"AUDIT: {audit_path}")
    print(f"TRUNK: {trunk_path}")
    print(f"OUTPUT: {output_path}")
    print(f"REFERENCES: {len(refs)}")
    print("STATUS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
