#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

"""
ROOTS — fixed label ontology collapse

Closed ontology:
- EXPONE
- RAZÓN
- CONTRASTE
- RESULTADO
- PROPÓSITO
- CONDICIÓN
- ACLARA
- AMPLÍA

Mechanical assignment only.
"""

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


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    return rows


def ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row.get("stream_index") or 0))


def normalize_reason(value: Any) -> str:
    if not value:
        return ""

    if isinstance(value, list):
        return " ".join(str(v).lower() for v in value)

    return str(value).lower()


def has_reason(blob: str, token: str) -> bool:
    return token.lower() in blob


# ---------------------------------------------------------
# Refined heuristic collapse
# ---------------------------------------------------------


def assign_roots_label(row: dict[str, Any]) -> tuple[str, str]:
    continuity = str(row.get("continuity_status") or "")
    movement = str(row.get("movement_status") or "")
    independence = str(row.get("independence_status") or "")
    subordination = str(row.get("subordination_status") or "")
    reasons = normalize_reason(row.get("movement_reasons"))

    # -----------------------------------------------------
    # CONDICIÓN
    # unresolved gating environments
    # -----------------------------------------------------
    if continuity == "unresolved":
        return "CONDICIÓN", "unresolved_continuity"

    # -----------------------------------------------------
    # CONTRASTE
    # explicit interruption/opposition environments
    # -----------------------------------------------------
    if has_reason(reasons, "subject_shift"):
        return "CONTRASTE", "subject_shift"

    if has_reason(reasons, "person_change"):
        return "CONTRASTE", "person_change"

    if has_reason(reasons, "independence_transition"):
        return "CONTRASTE", "independence_transition"

    # -----------------------------------------------------
    # RESULTADO
    # movement resolved into stable continuity
    # -----------------------------------------------------
    if continuity == "same" and movement == "candidate":
        return "RESULTADO", "candidate_resolution"

    # -----------------------------------------------------
    # RAZÓN
    # subordinate support environments
    # -----------------------------------------------------
    if subordination == "candidate" and movement == "candidate":
        return "RAZÓN", "subordinate_candidate"

    # -----------------------------------------------------
    # PROPÓSITO
    # directional movement continuation
    # -----------------------------------------------------
    if continuity == "shift" and movement == "candidate":
        return "PROPÓSITO", "shift_candidate"

    # -----------------------------------------------------
    # ACLARA
    # clarification continuity environments
    # -----------------------------------------------------
    if continuity == "same" and subordination == "candidate":
        return "ACLARA", "same_subordinate"

    # -----------------------------------------------------
    # AMPLÍA
    # additive extension environments
    # -----------------------------------------------------
    if movement == "candidate":
        return "AMPLÍA", "candidate_extension"

    # -----------------------------------------------------
    # EXPONE
    # stable exposition fallback
    # -----------------------------------------------------
    return "EXPONE", "default_exposition"


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

    summary: list[dict[str, Any]] = []

    for label in ROOTS_LABELS:
        members = [row for row in rows if row.get("roots_label") == label]

        if not members:
            continue

        source_counter = Counter(str(row.get("roots_label_source")) for row in members)

        summary.append({
            "roots_label": label,
            "member_count": counter[label],
            "dominant_assignment_source": source_counter.most_common(1)[0][0],
            "source_distribution": json.dumps(dict(sorted(source_counter.items())), ensure_ascii=False, sort_keys=True),
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


def process_book(book: str) -> tuple[int, int, Path, Path, Path]:
    in_path = mna_root() / "data" / "movements" / f"{book}-movements.jsonl"

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
        print("Usage: python3 MNA/scripts/roots_collapse_label_ontology.py <book>", file=sys.stderr)
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
