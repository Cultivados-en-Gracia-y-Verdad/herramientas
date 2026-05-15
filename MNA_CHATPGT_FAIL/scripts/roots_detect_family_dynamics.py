#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

"""
ROOTS — structural family dynamics

Models observable transition behavior between consolidated structural families.
No semantic interpretation is performed.
"""


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



def ordered_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row.get("start_stream_index") or 0))



def build_transitions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = ordered_rows(rows)

    transitions: list[dict[str, Any]] = []

    previous: dict[str, Any] | None = None

    for current in ordered:
        if previous is None:
            previous = current
            continue

        transitions.append({
            "from_family": previous.get("consolidated_family_id"),
            "to_family": current.get("consolidated_family_id"),
            "from_signature": previous.get("structural_signature_id"),
            "to_signature": current.get("structural_signature_id"),
            "from_reference": previous.get("start_reference"),
            "to_reference": current.get("start_reference"),
            "stream_gap": (
                int(current.get("start_stream_index") or 0)
                - int(previous.get("end_stream_index") or 0)
            ),
        })

        previous = current

    return transitions



def build_transition_matrix(transitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    outgoing_counts: dict[str, int] = defaultdict(int)

    for transition in transitions:
        source = str(transition["from_family"])
        target = str(transition["to_family"])

        pair_counts[(source, target)] += 1
        outgoing_counts[source] += 1

    rows: list[dict[str, Any]] = []

    for (source, target), count in sorted(pair_counts.items()):
        rows.append({
            "from_family": source,
            "to_family": target,
            "transition_count": count,
            "transition_probability": round(count / outgoing_counts[source], 4),
        })

    return rows



def build_flow_summary(rows: list[dict[str, Any]], transitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        grouped[str(row.get("consolidated_family_id"))].append(row)

    incoming: dict[str, Counter[str]] = defaultdict(Counter)
    outgoing: dict[str, Counter[str]] = defaultdict(Counter)

    for transition in transitions:
        source = str(transition["from_family"])
        target = str(transition["to_family"])

        outgoing[source][target] += 1
        incoming[target][source] += 1

    summary: list[dict[str, Any]] = []

    for family_id in sorted(grouped):
        members = grouped[family_id]

        outgoing_common = outgoing[family_id].most_common(1)
        incoming_common = incoming[family_id].most_common(1)

        summary.append({
            "family_id": family_id,
            "member_count": len(members),
            "avg_structural_density": round(
                sum(float(row.get("structural_density") or 0) for row in members)
                / len(members),
                4,
            ),
            "avg_continuity_shift_density": round(
                sum(float(row.get("continuity_shift_density") or 0) for row in members)
                / len(members),
                4,
            ),
            "incoming_transition_count": sum(incoming[family_id].values()),
            "outgoing_transition_count": sum(outgoing[family_id].values()),
            "most_common_outgoing_family": outgoing_common[0][0] if outgoing_common else None,
            "most_common_outgoing_count": outgoing_common[0][1] if outgoing_common else 0,
            "most_common_incoming_family": incoming_common[0][0] if incoming_common else None,
            "most_common_incoming_count": incoming_common[0][1] if incoming_common else 0,
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
    in_path = (
        mna_root()
        / "data"
        / "structural-families"
        / f"{book}-structural-families-consolidated.jsonl"
    )

    rows = read_jsonl(in_path)

    transitions = build_transitions(rows)
    matrix = build_transition_matrix(transitions)
    summary = build_flow_summary(rows, transitions)

    out_dir = mna_root() / "data" / "family-dynamics"

    dynamics_out = out_dir / f"{book}-family-dynamics.jsonl"
    matrix_out = out_dir / f"{book}-family-transition-matrix.tsv"
    summary_out = out_dir / f"{book}-family-flow-summary.tsv"

    write_jsonl(dynamics_out, transitions)
    write_tsv(matrix_out, matrix)
    write_tsv(summary_out, summary)

    return len(transitions), len(matrix), dynamics_out, matrix_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_detect_family_dynamics.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()

    transition_count, matrix_count, dynamics_out, matrix_out, summary_out = process_book(book)

    print(f"family_transitions = {transition_count}")
    print(f"transition_matrix_rows = {matrix_count}")
    print(f"wrote: {dynamics_out}")
    print(f"wrote: {matrix_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
