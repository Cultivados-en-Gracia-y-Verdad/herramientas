#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — restricted [M] movement marker layer

Purpose:
- separate general movement detection from restricted ROOTS [M] marking
- prevent every subject/continuity shift from becoming a section rupture
- support ROOTS Paso 10, where [M] is the only valid section delimiter

Input:
- MNA/data/movements/<book>-movements.jsonl

Outputs:
- MNA/data/movement-markers/<book>-movement-markers.jsonl
- MNA/data/movement-markers/<book>-movement-markers.tsv
- MNA/data/movement-markers/<book>-movement-marker-summary.tsv

Strict prohibitions:
- no semantics
- no theology
- no discourse reconstruction
- no topology inference

This layer marks [M] ONLY when grammatical rupture is strongly demonstrated.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row.get("stream_index") or 0))


def parse_reasons(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {str(v) for v in value}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return {str(v) for v in parsed}
        except json.JSONDecodeError:
            return {value}
    return set()


def restricted_m_decision(row: dict[str, Any]) -> tuple[bool, str, str]:
    """Return (has_m, confidence, source).

    [M] is intentionally stricter than movement_status.
    A shift alone is NOT enough.
    A subject/person change alone is NOT enough.
    We require converging grammatical evidence.
    """
    reasons = parse_reasons(row.get("movement_reasons"))
    movement_status = str(row.get("movement_status") or "")
    continuity_status = str(row.get("continuity_status") or "")

    if "stream_start" in reasons:
        return False, "none", "stream_start_not_section_break"

    person_or_number_change = bool({"person_change", "number_change"} & reasons)
    boundary_transition = bool({"independence_transition", "subordination_transition"} & reasons)
    subject_shift = "subject_shift" in reasons

    if movement_status == "strong" and person_or_number_change and boundary_transition:
        return True, "high", "strong_person_number_plus_boundary_transition"

    if movement_status == "strong" and subject_shift and boundary_transition:
        return True, "high", "strong_subject_shift_plus_boundary_transition"

    if movement_status == "strong" and len(reasons - {"stream_start"}) >= 3:
        return True, "medium", "strong_three_or_more_reasons"

    if continuity_status == "unresolved" and boundary_transition and person_or_number_change:
        return True, "medium", "unresolved_plus_boundary_plus_person_number"

    return False, "none", "insufficient_converging_evidence"


def mark_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for row in rows:
        has_m, confidence, source = restricted_m_decision(row)
        enriched = dict(row)
        enriched["m_marker"] = "M" if has_m else ""
        enriched["m_marker_bool"] = has_m
        enriched["m_marker_confidence"] = confidence
        enriched["m_marker_source"] = source
        out.append(enriched)

    return out


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bool_counter = Counter(str(row.get("m_marker_bool")) for row in rows)
    confidence_counter = Counter(str(row.get("m_marker_confidence")) for row in rows)
    source_counter = Counter(str(row.get("m_marker_source")) for row in rows)

    summary: list[dict[str, Any]] = []

    for name, counter in [
        ("m_marker_bool", bool_counter),
        ("m_marker_confidence", confidence_counter),
        ("m_marker_source", source_counter),
    ]:
        for key in sorted(counter):
            summary.append({
                "summary_type": name,
                "name": key,
                "count": counter[key],
            })

    return summary


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def process_book(book: str) -> tuple[int, Path, Path, Path]:
    in_path = mna_root() / "data" / "movements" / f"{book}-movements.jsonl"
    rows = ordered(read_jsonl(in_path))

    marked = mark_rows(rows)
    summary = build_summary(marked)

    out_dir = mna_root() / "data" / "movement-markers"
    jsonl_out = out_dir / f"{book}-movement-markers.jsonl"
    tsv_out = out_dir / f"{book}-movement-markers.tsv"
    summary_out = out_dir / f"{book}-movement-marker-summary.tsv"

    write_jsonl(jsonl_out, marked)
    write_tsv(tsv_out, marked)
    write_tsv(summary_out, summary)

    m_count = sum(1 for row in marked if row.get("m_marker_bool"))
    return m_count, jsonl_out, tsv_out, summary_out


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_mark_restricted_movements.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    m_count, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"restricted_m_markers = {m_count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
