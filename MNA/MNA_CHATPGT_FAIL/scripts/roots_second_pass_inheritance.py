#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — second-pass bounded subject inheritance

Purpose:
- reduce remaining unresolved subject continuity cases
- use ONLY collected grammatical metadata
- preserve auditability and mechanical traceability

Strict prohibitions:
- no Scripture interpretation
- no semantic labeling
- no discourse topology
- no theological inference
- no external data sources

Input:
- refined-subjects/<book>-refined-subjects.jsonl

Output:
- refined-subjects/<book>-refined-subjects-pass2.jsonl
- refined-subjects/<book>-refined-subjects-pass2.tsv

Core principle:
Allow inheritance ONLY inside tightly bounded continuity windows.
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
    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    return rows


def unresolved(row: dict[str, Any]) -> bool:
    return (
        not row.get("subject_person")
        or not row.get("subject_number")
    )


def has_explicit_subject(row: dict[str, Any]) -> bool:
    return row.get("subject_refinement_status") in {
        "explicit_or_morphological",
        "inherited",
    }


def same_local_frame(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a.get("chapter") == b.get("chapter")
        and a.get("verse") == b.get("verse")
    )


def same_morphology(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a.get("finite_compact") == b.get("finite_compact")


def compatible_person_number(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a.get("subject_person") == b.get("subject_person")
        and a.get("subject_number") == b.get("subject_number")
    )


def no_visible_boundary(row: dict[str, Any]) -> bool:
    return (
        row.get("independence_status") != "candidate"
        and row.get("subordination_status") != "candidate"
    )


def safe_source(row: dict[str, Any]) -> bool:
    return row.get("subject_refinement_status") in {
        "explicit_or_morphological",
        "inherited",
    }


def try_local_inheritance(
    rows: list[dict[str, Any]],
    idx: int,
) -> bool:
    row = rows[idx]

    for offset in range(1, WINDOW + 1):
        prev_idx = idx - offset

        if prev_idx < 0:
            break

        prev = rows[prev_idx]

        if not safe_source(prev):
            continue

        if not same_local_frame(prev, row):
            continue

        if not same_morphology(prev, row):
            continue

        if not prev.get("subject_person"):
            continue

        if not prev.get("subject_number"):
            continue

        row["subject_person"] = prev["subject_person"]
        row["subject_number"] = prev["subject_number"]
        row["subject_refinement_status"] = "bounded_inheritance"
        row["subject_refinement_source"] = "same_local_frame_same_morphology"
        row["subject_inherited_from"] = prev.get("predication_id")

        return True

    return False


def process(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    resolved = 0

    for idx, row in enumerate(rows):
        if not unresolved(row):
            continue

        if try_local_inheritance(rows, idx):
            resolved += 1

    return rows, resolved


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
            delimiter="\t",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_second_pass_inheritance.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    in_path = (
        mna_root()
        / "data"
        / "refined-subjects"
        / f"{book}-refined-subjects.jsonl"
    )

    rows = read_jsonl(in_path)
    rows, resolved = process(rows)

    out_jsonl = (
        mna_root()
        / "data"
        / "refined-subjects"
        / f"{book}-refined-subjects-pass2.jsonl"
    )

    out_tsv = (
        mna_root()
        / "data"
        / "refined-subjects"
        / f"{book}-refined-subjects-pass2.tsv"
    )

    write_jsonl(out_jsonl, rows)
    write_tsv(out_tsv, rows)

    print(f"resolved_second_pass_subjects = {resolved}")
    print(f"wrote: {out_jsonl}")
    print(f"wrote: {out_tsv}")


if __name__ == "__main__":
    main()
