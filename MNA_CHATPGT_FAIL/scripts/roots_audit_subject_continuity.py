#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — subject continuity audit

Purpose:
- audit subject continuity shifts without changing [M]
- separate demonstrable grammatical shifts from unresolved/noisy shifts
- preserve a conservative, evidence-first workflow

Input:
- MNA/data/movements/<book>-movements.jsonl

Outputs:
- MNA/data/subject-continuity-audit/<book>-subject-continuity-audit.jsonl
- MNA/data/subject-continuity-audit/<book>-subject-continuity-audit.tsv
- MNA/data/subject-continuity-audit/<book>-subject-continuity-audit-summary.tsv

Strict prohibitions:
- no semantics
- no theology
- no discourse reconstruction
- no [M] assignment

This layer audits continuity evidence only.
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


def audit_shift(row: dict[str, Any]) -> tuple[str, str]:
    continuity = str(row.get("continuity_status") or "")
    reasons = parse_reasons(row.get("movement_reasons"))

    if continuity != "shift":
        return "not_shift", "continuity_not_shift"

    has_person = "person_change" in reasons
    has_number = "number_change" in reasons
    has_subject = "subject_shift" in reasons

    subject_source = str(row.get("subject_refinement_source") or "")
    subject_status = str(row.get("subject_refinement_status") or "")

    if has_person and has_number:
        return "demonstrable_shift", "person_and_number_change"

    if has_person:
        return "demonstrable_shift", "person_change"

    if has_number:
        return "weak_shift", "number_change_only"

    if has_subject and subject_status == "explicit_or_morphological":
        return "demonstrable_shift", "explicit_or_morphological_subject_shift"

    if has_subject:
        return "weak_shift", "subject_shift_without_strong_source"

    if "finite_compact_person_number" in subject_source:
        return "morphological_shift", "finite_morphology_person_number"

    return "unexplained_shift", "no_shift_reason_detected"


def audit_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for row in rows:
        status, source = audit_shift(row)
        enriched = dict(row)
        enriched["continuity_audit_status"] = status
        enriched["continuity_audit_source"] = source
        out.append(enriched)

    return out


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    status_counter = Counter(str(row.get("continuity_audit_status")) for row in rows)
    source_counter = Counter(str(row.get("continuity_audit_source")) for row in rows)
    continuity_counter = Counter(str(row.get("continuity_status")) for row in rows)

    summary: list[dict[str, Any]] = []

    for summary_type, counter in [
        ("continuity_status", continuity_counter),
        ("audit_status", status_counter),
        ("audit_source", source_counter),
    ]:
        for key in sorted(counter):
            summary.append({
                "summary_type": summary_type,
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

    audited = audit_rows(rows)
    summary = build_summary(audited)

    out_dir = mna_root() / "data" / "subject-continuity-audit"
    jsonl_out = out_dir / f"{book}-subject-continuity-audit.jsonl"
    tsv_out = out_dir / f"{book}-subject-continuity-audit.tsv"
    summary_out = out_dir / f"{book}-subject-continuity-audit-summary.tsv"

    write_jsonl(jsonl_out, audited)
    write_tsv(tsv_out, audited)
    write_tsv(summary_out, summary)

    shift_count = sum(1 for row in audited if row.get("continuity_status") == "shift")
    return shift_count, jsonl_out, tsv_out, summary_out


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_audit_subject_continuity.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    shift_count, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"continuity_shifts_audited = {shift_count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
