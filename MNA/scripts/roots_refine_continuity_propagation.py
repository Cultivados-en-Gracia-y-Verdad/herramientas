#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — continuity propagation refinement

Purpose:
- refine subject continuity recoverability
- reduce false subject-shift inflation
- preserve mechanical grammatical observability

Input:
- MNA/data/movements/<book>-movements.jsonl

Outputs:
- MNA/data/continuity-refined/<book>-continuity-refined.jsonl
- MNA/data/continuity-refined/<book>-continuity-refined.tsv
- MNA/data/continuity-refined/<book>-continuity-summary.tsv

Strict prohibitions:
- no semantics
- no theology
- no discourse reconstruction
- no topology inference

This layer refines ONLY continuity propagation behavior.
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
# Continuity refinement
# ---------------------------------------------------------


def normalize_reason(value: Any) -> str:
    if not value:
        return ""

    if isinstance(value, list):
        return " ".join(str(v).lower() for v in value)

    return str(value).lower()



def continuity_signature(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("subject_person") or ""),
        str(row.get("subject_number") or ""),
        str(row.get("verb_tense_voice_mood") or ""),
    )



def explicit_shift(row: dict[str, Any]) -> bool:
    reasons = normalize_reason(row.get("movement_reasons"))

    return any(token in reasons for token in [
        "subject_shift",
        "person_change",
        "explicit_subject_change",
    ])



def coordinated_environment(row: dict[str, Any]) -> bool:
    reasons = normalize_reason(row.get("movement_reasons"))

    return any(token in reasons for token in [
        "coordination",
        "coordinated_clause",
        "parallel_chain",
    ])



def refine_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        refined = dict(row)

        base_continuity = str(row.get("continuity_status") or "")
        signature = continuity_signature(row)

        propagated = False
        propagation_source = None

        if base_continuity == "shift" and not explicit_shift(row):
            start = max(0, idx - WINDOW)

            for prev_idx in range(idx - 1, start - 1, -1):
                prev = rows[prev_idx]
                prev_signature = continuity_signature(prev)

                if prev_signature == signature:
                    propagated = True
                    propagation_source = "signature_window_match"
                    break

                if coordinated_environment(prev):
                    propagated = True
                    propagation_source = "coordinated_environment"
                    break

        if propagated:
            refined["continuity_status_refined"] = "propagated_same"
            refined["continuity_refinement"] = propagation_source
        else:
            refined["continuity_status_refined"] = base_continuity
            refined["continuity_refinement"] = "none"

        out.append(refined)

    return out


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    continuity_counter = Counter(
        str(row.get("continuity_status_refined"))
        for row in rows
    )

    refinement_counter = Counter(
        str(row.get("continuity_refinement"))
        for row in rows
    )

    out: list[dict[str, Any]] = []

    for key in sorted(continuity_counter):
        out.append({
            "summary_type": "continuity_distribution",
            "name": key,
            "count": continuity_counter[key],
        })

    for key in sorted(refinement_counter):
        out.append({
            "summary_type": "refinement_distribution",
            "name": key,
            "count": refinement_counter[key],
        })

    return out


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
        / "movements"
        / f"{book}-movements.jsonl"
    )

    rows = ordered(read_jsonl(in_path))

    refined = refine_rows(rows)
    summary = build_summary(refined)

    out_dir = mna_root() / "data" / "continuity-refined"

    jsonl_out = out_dir / f"{book}-continuity-refined.jsonl"
    tsv_out = out_dir / f"{book}-continuity-refined.tsv"
    summary_out = out_dir / f"{book}-continuity-summary.tsv"

    write_jsonl(jsonl_out, refined)
    write_tsv(tsv_out, refined)
    write_tsv(summary_out, summary)

    propagated_count = sum(
        1
        for row in refined
        if row.get("continuity_status_refined") == "propagated_same"
    )

    return propagated_count, jsonl_out, tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_refine_continuity_propagation.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    propagated_count, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"propagated_same_count = {propagated_count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
