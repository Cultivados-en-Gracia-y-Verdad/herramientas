#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

"""
ROOTS — restricted [M] movement marker layer

Purpose:
- separate general movement detection from restricted ROOTS [M] marking
- prevent every continuity fluctuation from becoming rupture
- support ROOTS Paso 10 section delimitation

[M] must remain:
- restricted
- conservative
- convergence-based
- grammatically recoverable
"""


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


# ---------------------------------------------------------
# Rupture convergence grouping
# ---------------------------------------------------------


def reason_group_count(reasons: set[str]) -> int:
    """
    Closely related turbulence signals should not
    artificially inflate rupture legitimacy.
    """

    groups = set()

    if {"subject_shift", "person_change", "number_change"} & reasons:
        groups.add("participant")

    if {"independence_transition", "subordination_transition"} & reasons:
        groups.add("boundary")

    if {"coordination_break", "parallel_break"} & reasons:
        groups.add("coordination")

    if {"tense_transition", "mood_transition"} & reasons:
        groups.add("verbal")

    return len(groups)


# ---------------------------------------------------------
# Restricted [M] logic
# ---------------------------------------------------------


def restricted_m_decision(row: dict[str, Any]) -> tuple[bool, str, str]:
    """
    [M] must represent strong structural rupture.

    A single fluctuation is insufficient.
    Local turbulence accumulation is insufficient.
    Subject shift alone is insufficient.
    """

    reasons = parse_reasons(row.get("movement_reasons"))

    movement_status = str(row.get("movement_status") or "")
    continuity_status = str(row.get("continuity_status") or "")

    if "stream_start" in reasons:
        return False, "none", "stream_start_not_rupture"

    participant_shift = bool({
        "subject_shift",
        "person_change",
        "number_change",
    } & reasons)

    boundary_transition = bool({
        "independence_transition",
        "subordination_transition",
    } & reasons)

    coordination_break = bool({
        "coordination_break",
        "parallel_break",
    } & reasons)

    verbal_transition = bool({
        "tense_transition",
        "mood_transition",
    } & reasons)

    grouped = reason_group_count(reasons)

    # -----------------------------------------------------
    # HIGH CONFIDENCE RUPTURE
    # participant + boundary + another rupture layer
    # -----------------------------------------------------

    if (
        movement_status == "strong"
        and participant_shift
        and boundary_transition
        and (coordination_break or verbal_transition)
    ):
        return True, "high", "compound_structural_rupture"

    # -----------------------------------------------------
    # MEDIUM CONFIDENCE RUPTURE
    # unresolved continuity + multi-layer rupture
    # -----------------------------------------------------

    if (
        continuity_status == "unresolved"
        and grouped >= 3
        and participant_shift
        and boundary_transition
    ):
        return True, "medium", "unresolved_multi_layer_rupture"

    # -----------------------------------------------------
    # CONSERVATIVE DEFAULT
    # -----------------------------------------------------

    return False, "none", "insufficient_rupture_convergence"


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
    summary: list[dict[str, Any]] = []

    counters = {
        "m_marker_bool": Counter(str(row.get("m_marker_bool")) for row in rows),
        "m_marker_confidence": Counter(str(row.get("m_marker_confidence")) for row in rows),
        "m_marker_source": Counter(str(row.get("m_marker_source")) for row in rows),
    }

    for summary_type, counter in counters.items():
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
        print(
            "Usage: python3 MNA/scripts/roots_mark_restricted_movements.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    m_count, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"restricted_m_markers = {m_count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
