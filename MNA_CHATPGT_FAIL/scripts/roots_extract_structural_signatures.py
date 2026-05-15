#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — structural signature extraction

Purpose:
- extract repeatable grammatical behavior profiles from stabilized regimes
- prepare later mechanical label emergence
- preserve a strict non-semantic boundary

Inputs:
- MNA/data/structural-regimes/<book>-structural-regimes-merged.jsonl
- MNA/data/movement-strata/<book>-movement-strata.jsonl

Outputs:
- MNA/data/structural-signatures/<book>-structural-signatures.jsonl
- MNA/data/structural-signatures/<book>-structural-signatures.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic interpretation
- no theology
- no H0/H1/H2 assignment
- no topology reconstruction

This layer describes HOW a regime behaves grammatically, not WHAT it means.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

VALID_CONTINUITY = {"initial", "same", "shift", "unresolved"}


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


def normalize_continuity(value: Any) -> str:
    if value is None:
        return "unresolved"

    normalized = str(value).strip().lower()

    if normalized in VALID_CONTINUITY:
        return normalized

    if normalized in {"", "none", "null", "missing", "unknown"}:
        return "unresolved"

    return "unresolved"


def rows_for_regime(strata_rows: list[dict[str, Any]], regime: dict[str, Any]) -> list[dict[str, Any]]:
    start = int(regime["start_stream_index"])
    end = int(regime["end_stream_index"])
    return [row for row in strata_rows if start <= int(row["stream_index"]) <= end]


def ratio(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def dominant(counter: Counter[str]) -> str:
    if not counter:
        return "none"
    return counter.most_common(1)[0][0]


def signature_band(value: float) -> str:
    if value == 0:
        return "none"
    if value < 0.25:
        return "low"
    if value < 0.50:
        return "medium"
    if value < 0.75:
        return "high"
    return "very_high"


def extract_signature(regime: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    record_count = len(rows)

    movement_class_counter = Counter(str(row.get("movement_class") or "unknown") for row in rows)
    movement_status_counter = Counter(str(row.get("movement_status") or "unknown") for row in rows)

    normalized_continuity = [
        normalize_continuity(row.get("continuity_status"))
        for row in rows
    ]

    continuity_counter = Counter(normalized_continuity)

    person_counter = Counter(
        f"{row.get('subject_person') or '-'}{row.get('subject_number') or '-'}"
        for row in rows
    )

    structural_count = movement_class_counter["structural"]
    turbulence_count = movement_class_counter["turbulence"]
    stable_count = movement_class_counter["stable"]

    total_weight = sum(int(row.get("structural_weight") or 0) for row in rows)
    max_weight = max((int(row.get("structural_weight") or 0) for row in rows), default=0)

    structural_density = ratio(structural_count, record_count)
    turbulence_density = ratio(turbulence_count, record_count)
    stable_density = ratio(stable_count, record_count)

    same_density = ratio(continuity_counter["same"], record_count)
    shift_density = ratio(continuity_counter["shift"], record_count)
    unresolved_density = ratio(continuity_counter["unresolved"], record_count)
    initial_density = ratio(continuity_counter["initial"], record_count)

    weight_per_record = round(total_weight / record_count, 4) if record_count else 0

    signature_parts = [
        f"structural={signature_band(structural_density)}",
        f"turbulence={signature_band(turbulence_density)}",
        f"stable={signature_band(stable_density)}",
        f"continuity_same={signature_band(same_density)}",
        f"continuity_shift={signature_band(shift_density)}",
        f"continuity_unresolved={signature_band(unresolved_density)}",
        f"weight={signature_band(min(weight_per_record / 4, 1))}",
    ]

    return {
        "structural_signature_id": regime.get("merged_regime_id") or regime.get("structural_regime_id"),
        "source_regime_id": regime.get("structural_regime_id"),
        "merged_regime_id": regime.get("merged_regime_id"),
        "book": regime.get("book"),
        "start_stream_index": regime.get("start_stream_index"),
        "end_stream_index": regime.get("end_stream_index"),
        "start_reference": regime.get("start_reference"),
        "end_reference": regime.get("end_reference"),
        "record_count": record_count,
        "total_structural_weight": total_weight,
        "max_structural_weight": max_weight,
        "weight_per_record": weight_per_record,
        "structural_density": structural_density,
        "turbulence_density": turbulence_density,
        "stable_density": stable_density,
        "continuity_same_density": same_density,
        "continuity_shift_density": shift_density,
        "continuity_unresolved_density": unresolved_density,
        "continuity_initial_density": initial_density,
        "dominant_movement_class": dominant(movement_class_counter),
        "dominant_movement_status": dominant(movement_status_counter),
        "dominant_continuity_status": dominant(continuity_counter),
        "dominant_subject_profile": dominant(person_counter),
        "movement_class_counts": json.dumps(dict(sorted(movement_class_counter.items())), ensure_ascii=False, sort_keys=True),
        "movement_status_counts": json.dumps(dict(sorted(movement_status_counter.items())), ensure_ascii=False, sort_keys=True),
        "continuity_counts": json.dumps(dict(sorted(continuity_counter.items())), ensure_ascii=False, sort_keys=True),
        "subject_profile_counts": json.dumps(dict(sorted(person_counter.items())), ensure_ascii=False, sort_keys=True),
        "signature_code": "|".join(signature_parts),
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def process_book(book: str) -> tuple[Path, Path, int]:
    root = mna_root()
    regimes_path = root / "data" / "structural-regimes" / f"{book}-structural-regimes-merged.jsonl"
    strata_path = root / "data" / "movement-strata" / f"{book}-movement-strata.jsonl"

    regimes = read_jsonl(regimes_path)
    strata_rows = read_jsonl(strata_path)

    signatures = [extract_signature(regime, rows_for_regime(strata_rows, regime)) for regime in regimes]

    out_dir = root / "data" / "structural-signatures"
    jsonl_out = out_dir / f"{book}-structural-signatures.jsonl"
    tsv_out = out_dir / f"{book}-structural-signatures.tsv"

    write_jsonl(jsonl_out, signatures)
    write_tsv(tsv_out, signatures)

    return jsonl_out, tsv_out, len(signatures)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_extract_structural_signatures.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    jsonl_out, tsv_out, count = process_book(book)

    print(f"structural_signatures = {count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")


if __name__ == "__main__":
    main()
