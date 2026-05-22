#!/usr/bin/env python3
"""
MNA Stage 7 — Persistence Region Builder

Purpose
-------
Observe persistence regions across adjacent surviving constrained environments.

Input:
    datasets/unified-observable-environments/<book>.jsonl

Output:
    datasets/stage7/<book>/persistence-regions.jsonl

This script does NOT:
- assign movements,
- assign labels,
- assign sections,
- create hierarchy,
- claim discourse structure,
- infer authorial outline.

A persistence region is only an observable span where a selected field remains
stable across adjacent unified observable environments.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

VERSION = "stage7-persistence-region-builder-v1"
RECORD_TYPE = "persistence_region"

PERSISTENCE_FIELDS = [
    "stage6_signal_category",
    "stage6_signal_status",
    "stage5_candidacy_environment",
    "stage5_survival_decision",
    "connector_surface",
    "mood",
    "person",
    "number",
]


def root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        raise FileNotFoundError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def stable_value(value: object) -> str:
    if value is None:
        return "None"
    return str(value)


def build_regions_for_field(rows: list[dict], field: str) -> list[dict]:
    regions = []
    if not rows:
        return regions

    start_idx = 0
    current_value = stable_value(rows[0].get(field))

    for idx in range(1, len(rows)):
        value = stable_value(rows[idx].get(field))
        if value != current_value:
            regions.append(make_region(rows, field, current_value, start_idx, idx - 1))
            start_idx = idx
            current_value = value

    regions.append(make_region(rows, field, current_value, start_idx, len(rows) - 1))
    return regions


def make_region(rows: list[dict], field: str, value: str, start_idx: int, end_idx: int) -> dict:
    start = rows[start_idx]
    end = rows[end_idx]
    region_length = end_idx - start_idx + 1

    return {
        "record_type": RECORD_TYPE,
        "version": VERSION,
        "book": start.get("book"),
        "persistence_field": field,
        "persistence_value": value,
        "region_length": region_length,
        "start_sequence_index": start.get("sequence_index"),
        "end_sequence_index": end.get("sequence_index"),
        "start_reference": start.get("reference"),
        "end_reference": end.get("reference"),
        "start_clause_id": start.get("clause_id"),
        "end_clause_id": end.get("clause_id"),
        "clause_ids": [row.get("clause_id") for row in rows[start_idx:end_idx + 1]],
        "finite_verbs": [row.get("finite_verb") for row in rows[start_idx:end_idx + 1]],
        "region_status": "OBSERVED_PERSISTENCE_REGION" if region_length > 1 else "SINGLE_ENVIRONMENT_REGION",
        "claim_policy": "OBSERVATIONAL_PERSISTENCE_ONLY_NO_MOVEMENT_LABEL_OR_SECTION_CLAIM",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Stage 7 persistence regions.")
    parser.add_argument("book", help="Book slug, e.g. filipenses")
    parser.add_argument("--min-length", type=int, default=2, help="Minimum region length to write; default 2")
    parser.add_argument("--include-singletons", action="store_true", help="Also write single-environment regions")
    args = parser.parse_args(argv)

    root = root_from_script()
    book = args.book.strip().lower()

    input_path = root / "datasets" / "unified-observable-environments" / f"{book}.jsonl"
    output_path = root / "datasets" / "stage7" / book / "persistence-regions.jsonl"

    rows = sorted(load_jsonl(input_path), key=lambda row: int(row.get("sequence_index") or 0))

    all_regions = []
    for field in PERSISTENCE_FIELDS:
        all_regions.extend(build_regions_for_field(rows, field))

    filtered = []
    for region in all_regions:
        if args.include_singletons:
            filtered.append(region)
        elif int(region.get("region_length") or 0) >= args.min_length:
            filtered.append(region)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for region in filtered:
            handle.write(json.dumps(region, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 7 — Persistence Region Builder")
    print(f"VERSION: {VERSION}")
    print(f"BOOK: {book}")
    print(f"INPUT: {input_path}")
    print(f"OUTPUT: {output_path}")
    print(f"SOURCE ROWS: {len(rows)}")
    print(f"REGIONS WRITTEN: {len(filtered)}")
    print("POLICY: OBSERVATIONAL PERSISTENCE ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())