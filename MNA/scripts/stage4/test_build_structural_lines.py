#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "stage4-structural-line-test-v1"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Required input not found: {path}")
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def line_break_reasons(row):
    reasons = []
    if row.get("s_marker") == "[S]":
        reasons.append("S")
    if row.get("m_marker") == "[M]":
        reasons.append("M")
    if row.get("explicit_connector_before"):
        reasons.append("CONNECTOR")
    return reasons


def main() -> int:
    ap = argparse.ArgumentParser(description="TEMP Stage 4 test: build structural lines from Stage 3 markers.")
    ap.add_argument("book")
    args = ap.parse_args()

    book = args.book.strip().lower()
    mna = root()

    in_path = mna / "datasets" / "stage3" / book / "subject-movement-markers.jsonl"
    out_path = mna / "datasets" / "stage4-test" / book / "structural-lines.jsonl"

    rows = load_jsonl(in_path)

    output = []
    current_line = 1

    for idx, row in enumerate(rows, start=1):
        reasons = line_break_reasons(row)
        if idx > 1 and reasons:
            current_line += 1
        output.append({
            "record_type": "stage4_structural_line_test",
            "book": book,
            "line_id": f"{book}-L{current_line:04d}",
            "order": row["order"],
            "anchor_id": row["anchor_id"],
            "chapter": row["chapter"],
            "verse": row["verse"],
            "token_index": row["token_index"],
            "greek_form": row["greek_form"],
            "lemma": row["lemma"],
            "morphology": row["morphology"],
            "subject_signal": row["subject_signal"],
            "s_marker": row["s_marker"],
            "m_marker": row["m_marker"],
            "explicit_connector_before": row["explicit_connector_before"],
            "line_break_before": bool(idx > 1 and reasons),
            "line_break_reasons": reasons,
            "policy": "TEMP_TEST_ONLY_STAGE3_MARKERS_PLUS_EXPLICIT_CONNECTOR",
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({
            "record_type": "metadata",
            "builder_version": VERSION,
            "book": book,
            "source": str(in_path.relative_to(mna)),
            "rows_written": len(output),
            "line_count": current_line if output else 0,
            "policy": "TEMP_TEST_NOT_CANONICAL",
        }, ensure_ascii=False, sort_keys=True) + "\n")
        for row in output:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 4 TEST — Structural Lines")
    print(f"BOOK: {book}")
    print(f"ROWS WRITTEN: {len(output)}")
    print(f"LINES: {current_line if output else 0}")
    print(f"OUTPUT: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
