#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — fixed label ontology collapse

Purpose:
- collapse movement environments into a fixed ROOTS label universe
- prevent label explosion
- support ROOTS Paso 9–10 preparation
- remain strictly mechanical and auditable

Input:
- MNA/data/movements/<book>-movements.jsonl

Outputs:
- MNA/data/roots-labels/<book>-roots-labels.jsonl
- MNA/data/roots-labels/<book>-roots-labels.tsv
- MNA/data/roots-labels/<book>-roots-label-summary.tsv

Closed ontology:
- EXPONE
- RAZÓN
- CONTRASTE
- RESULTADO
- PROPÓSITO
- CONDICIÓN
- ACLARA
- AMPLÍA

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theology
- no H0/H1/H2 assignment
- no discourse reconstruction

These labels are assigned ONLY from observable mechanical behavior.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOTS_LABELS = [
    "EXPONE",
    "RAZÓN",
    "CONTRASTE",
    "RESULTADO",
    "PROPÓSITO",
    "CONDICIÓN",
    "ACLARA",
    "AMPLÍA",
]


# ---------------------------------------------------------
# IO
# ---------------------------------------------------------


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]



def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

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
# Mechanical ontology collapse
# ---------------------------------------------------------


def normalize_reason(reason: str | None) -> str:
    if not reason:
        return ""
    return str(reason).lower()



def assign_roots_label(row: dict[str, Any]) -> tuple[str, str]:
    continuity = str(row.get("continuity_status") or "")
    movement = str(row.get("movement_status") or "")
    movement_reason = normalize_reason(row.get("movement_reasons"))
    independence = str(row.get("independence_status") or "")
    subordination = str(row.get("subordination_status") or "")

    # -----------------------------------------------------
    # CONTRASTE
    # Strong structural interruption / shift.
    # -----------------------------------------------------
    if continuity == "shift" and movement == "strong":
        return "CONTRASTE", "shift+strong"

    if "person_change" in movement_reason:
        return "CONTRASTE", "person_change"

    if "subject_shift" in movement_reason:
        return "CONTRASTE", "subject_shift"

    # -----------------------------------------------------
    # RESULTADO
    # Strong movement resolving into continuity.
    # -----------------------------------------------------
    if continuity == "same" and movement == "candidate":
        return "RESULTADO", "candidate_resolution"

    # -----------------------------------------------------
    # RAZÓN
    # Candidate grounding behavior under subordination.
    # -----------------------------------------------------
    if movement == "candidate" and subordination == "candidate":
        return "RAZÓN", "candidate_subordination"

    # -----------------------------------------------------
    # PROPÓSITO
    # Forward-directed candidate movement.
    # -----------------------------------------------------
    if movement == "candidate" and independence == "candidate":
        return "PROPÓSITO", "candidate_independence"

    # -----------------------------------------------------
    # CONDICIÓN
    # Unresolved gating / unresolved continuity.
    # -----------------------------------------------------
    if continuity == "unresolved":
        return "CONDICIÓN", "unresolved_continuity"

    # -----------------------------------------------------
    # ACLARA
    # Stable continuity under candidate movement.
    # -----------------------------------------------------
    if continuity == "same" and movement == "candidate":
        return "ACLARA", "same+candidate"

    # -----------------------------------------------------
    # AMPLÍA
    # Additive non-strong movement continuity.
    # -----------------------------------------------------
    if movement == "candidate":
        return "AMPLÍA", "candidate_extension"

    # -----------------------------------------------------
    # EXPONE (default fallback)
    # Stable exposition / persistence.
    # -----------------------------------------------------
    return "EXPONE", "default_exposition"


# ---------------------------------------------------------
# Processing
# ---------------------------------------------------------


def collapse_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for row in rows:
        label, source = assign_roots_label(row)

        enriched = dict(row)

        enriched["roots_label"] = label
        enriched["roots_label_source"] = source
        enriched["roots_label_status"] = "mechanical_candidate"

        out.append(enriched)

    return out



def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter(str(row.get("roots_label")) for row in rows)

    grouped: dict[str, list[dict[str, Any]]] = {
        label: [row for row in rows if row.get("roots_label") == label]
        for label in ROOTS_LABELS
    }

    summary: list[dict[str, Any]] = []

    for label in ROOTS_LABELS:
        members = grouped[label]

        if not members:
            continue

        source_counter = Counter(
            str(row.get("roots_label_source"))
            for row in members
        )

        summary.append({
            "roots_label": label,
            "member_count": counter[label],
            "dominant_assignment_source": source_counter.most_common(1)[0][0],
            "source_distribution": json.dumps(dict(sorted(source_counter.items())), ensure_ascii=False, sort_keys=True),
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


def process_book(book: str) -> tuple[int, int, Path, Path, Path]:
    in_path = (
        mna_root()
        / "data"
        / "movements"
        / f"{book}-movements.jsonl"
    )

    rows = ordered(read_jsonl(in_path))

    collapsed = collapse_labels(rows)
    summary = build_summary(collapsed)

    out_dir = mna_root() / "data" / "roots-labels"

    jsonl_out = out_dir / f"{book}-roots-labels.jsonl"
    tsv_out = out_dir / f"{book}-roots-labels.tsv"
    summary_out = out_dir / f"{book}-roots-label-summary.tsv"

    write_jsonl(jsonl_out, collapsed)
    write_tsv(tsv_out, collapsed)
    write_tsv(summary_out, summary)

    label_count = len({row["roots_label"] for row in collapsed})

    return label_count, len(collapsed), jsonl_out, tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_collapse_label_ontology.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    label_count, record_count, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"roots_labels_used = {label_count}")
    print(f"movement_records = {record_count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
