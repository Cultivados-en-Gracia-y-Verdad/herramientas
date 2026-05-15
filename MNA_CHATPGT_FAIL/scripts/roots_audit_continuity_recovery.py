#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — continuity recovery audit

Purpose:
- observe what happens AFTER demonstrable continuity shifts
- measure stabilization vs continued instability
- remain fully grammatical and non-interpretive

Input:
- MNA/data/subject-continuity-audit/<book>-subject-continuity-audit.jsonl

Outputs:
- MNA/data/continuity-recovery/<book>-continuity-recovery.jsonl
- MNA/data/continuity-recovery/<book>-continuity-recovery.tsv
- MNA/data/continuity-recovery/<book>-continuity-recovery-summary.tsv

This layer does NOT:
- assign [M]
- infer topology
- infer semantics
- create rupture theory
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

WINDOW = 3


# ---------------------------------------------------------
# IO
# ---------------------------------------------------------


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


# ---------------------------------------------------------
# Recovery observation
# ---------------------------------------------------------


def demonstrable_shift(row: dict[str, Any]) -> bool:
    return str(row.get("continuity_audit_status") or "") == "demonstrable_shift"



def recovery_profile(rows: list[dict[str, Any]], idx: int) -> tuple[str, str, list[str]]:
    following = rows[idx + 1 : idx + 1 + WINDOW]

    sequence = [str(r.get("continuity_status") or "") for r in following]

    if not sequence:
        return "terminal", "no_following_window", sequence

    same_count = sequence.count("same")
    shift_count = sequence.count("shift")
    unresolved_count = sequence.count("unresolved")

    if same_count >= 2:
        return "stabilized", "same_majority", sequence

    if shift_count >= 2:
        return "continued_instability", "shift_majority", sequence

    if unresolved_count >= 1:
        return "unstable", "contains_unresolved", sequence

    return "mixed", "mixed_following_behavior", sequence



def observe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        if not demonstrable_shift(row):
            continue

        profile, source, sequence = recovery_profile(rows, idx)

        out.append({
            "stream_index": row.get("stream_index"),
            "reference": f"{row.get('chapter')}:{row.get('verse')}",
            "continuity_audit_source": row.get("continuity_audit_source"),
            "recovery_profile": profile,
            "recovery_source": source,
            "following_continuity_sequence": json.dumps(sequence, ensure_ascii=False),
        })

    return out


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profile_counter = Counter(str(row.get("recovery_profile")) for row in rows)
    source_counter = Counter(str(row.get("recovery_source")) for row in rows)
    audit_source_counter = Counter(str(row.get("continuity_audit_source")) for row in rows)

    summary: list[dict[str, Any]] = []

    for summary_type, counter in [
        ("recovery_profile", profile_counter),
        ("recovery_source", source_counter),
        ("audit_source", audit_source_counter),
    ]:
        for key in sorted(counter):
            summary.append({
                "summary_type": summary_type,
                "name": key,
                "count": counter[key],
            })

    return summary


# ---------------------------------------------------------
# Output
# ---------------------------------------------------------


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


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def process_book(book: str) -> tuple[int, Path, Path, Path]:
    in_path = (
        mna_root()
        / "data"
        / "subject-continuity-audit"
        / f"{book}-subject-continuity-audit.jsonl"
    )

    rows = ordered(read_jsonl(in_path))

    observed = observe(rows)
    summary = build_summary(observed)

    out_dir = mna_root() / "data" / "continuity-recovery"

    jsonl_out = out_dir / f"{book}-continuity-recovery.jsonl"
    tsv_out = out_dir / f"{book}-continuity-recovery.tsv"
    summary_out = out_dir / f"{book}-continuity-recovery-summary.tsv"

    write_jsonl(jsonl_out, observed)
    write_tsv(tsv_out, observed)
    write_tsv(summary_out, summary)

    return len(observed), jsonl_out, tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_audit_continuity_recovery.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    count, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"demonstrable_shifts_observed = {count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
