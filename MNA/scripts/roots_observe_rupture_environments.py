#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — rupture environment observation

Purpose:
- observe candidate rupture environments WITHOUT theorizing
- inspect actual grammatical behavior surrounding possible [M]
- help identify what truly recurs near structural rupture

This script does NOT:
- assign [M]
- infer discourse topology
- infer semantic structure
- force movement theory

It ONLY surfaces observable environments.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

WINDOW = 2


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
# Observation extraction
# ---------------------------------------------------------


def parse_reasons(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(v) for v in value]

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except json.JSONDecodeError:
            return [value]

    return []



def candidate_environment(row: dict[str, Any]) -> bool:
    movement = str(row.get("movement_status") or "")
    continuity = str(row.get("continuity_status") or "")

    reasons = set(parse_reasons(row.get("movement_reasons")))

    if movement == "strong":
        return True

    if continuity == "unresolved":
        return True

    if {
        "subject_shift",
        "person_change",
        "independence_transition",
        "subordination_transition",
    } & reasons:
        return True

    return False



def summarize_window(rows: list[dict[str, Any]], center: int) -> dict[str, Any]:
    start = max(0, center - WINDOW)
    end = min(len(rows), center + WINDOW + 1)

    window = rows[start:end]

    return {
        "center_stream_index": rows[center].get("stream_index"),
        "center_reference": f"{rows[center].get('chapter')}:{rows[center].get('verse')}",
        "window_size": len(window),
        "movement_sequence": json.dumps([
            str(r.get("movement_status") or "")
            for r in window
        ], ensure_ascii=False),
        "continuity_sequence": json.dumps([
            str(r.get("continuity_status") or "")
            for r in window
        ], ensure_ascii=False),
        "reason_sequence": json.dumps([
            parse_reasons(r.get("movement_reasons"))
            for r in window
        ], ensure_ascii=False),
    }



def observe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        if candidate_environment(row):
            out.append(summarize_window(rows, idx))

    return out


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    movement_counter = Counter()
    continuity_counter = Counter()
    reason_counter = Counter()

    for row in rows:
        movement_seq = json.loads(row["movement_sequence"])
        continuity_seq = json.loads(row["continuity_sequence"])
        reason_seq = json.loads(row["reason_sequence"])

        for item in movement_seq:
            movement_counter[item] += 1

        for item in continuity_seq:
            continuity_counter[item] += 1

        for group in reason_seq:
            for reason in group:
                reason_counter[reason] += 1

    summary: list[dict[str, Any]] = []

    for key, count in sorted(movement_counter.items()):
        summary.append({
            "summary_type": "movement",
            "name": key,
            "count": count,
        })

    for key, count in sorted(continuity_counter.items()):
        summary.append({
            "summary_type": "continuity",
            "name": key,
            "count": count,
        })

    for key, count in sorted(reason_counter.items()):
        summary.append({
            "summary_type": "reason",
            "name": key,
            "count": count,
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
    in_path = mna_root() / "data" / "movements" / f"{book}-movements.jsonl"

    rows = ordered(read_jsonl(in_path))

    observed = observe(rows)
    summary = build_summary(observed)

    out_dir = mna_root() / "data" / "rupture-observation"

    jsonl_out = out_dir / f"{book}-rupture-observation.jsonl"
    tsv_out = out_dir / f"{book}-rupture-observation.tsv"
    summary_out = out_dir / f"{book}-rupture-observation-summary.tsv"

    write_jsonl(jsonl_out, observed)
    write_tsv(tsv_out, observed)
    write_tsv(summary_out, summary)

    return len(observed), jsonl_out, tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_observe_rupture_environments.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    count, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"candidate_environments = {count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
