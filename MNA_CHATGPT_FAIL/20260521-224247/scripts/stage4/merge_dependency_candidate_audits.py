#!/usr/bin/env python3
"""
MNA Stage 4 — dependency candidate audit merger.

PURPOSE
- Read approved Stage 4 dependency-candidate audit datasets.
- Merge candidate predicate_anchor_id values.
- Report unique candidate counts.
- Report overlaps across approved detectors.

IMPORTANT
This script:
- does NOT classify Stage 4 officially,
- does NOT modify datasets,
- does NOT create trunk,
- does NOT create [S] or [M].

It only reports current approved audit reduction coverage.

QUARANTINE NOTE
The broad subordinator detector is intentionally excluded here because audit review
showed it mixes true dependency with possible independent matrix clauses.
It must be split into narrower hard-rule detectors before it can become an approved
elimination source.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

VERSION = "stage4-dependency-audit-merger-v4-quarantine-broad-subordinator"

APPROVED_AUDIT_DATASETS = {
    "absolute-dependency-candidates": (
        "audits/stage4/absolute-dependency-candidates/{book}.jsonl"
    ),
    "relative-dependency-candidates": (
        "audits/stage4/relative-dependency-candidates/{book}.jsonl"
    ),
    "content-clause-dependency-candidates": (
        "audits/stage4/content-clause-dependency-candidates/{book}.jsonl"
    ),
}

QUARANTINED_AUDIT_DATASETS = {
    "subordinator-dependency-candidates": (
        "audits/stage4/subordinator-dependency-candidates/{book}.jsonl"
    ),
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    metadata = None
    rows = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue

            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc

            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)

    if metadata is None:
        raise ValueError(f"Missing metadata row in {path}")

    return metadata, rows


def collect_candidates(
    dataset_name: str,
    path: Path,
    anchor_sources: dict[str, set[str]],
    detector_counts: dict[str, int],
) -> None:
    _metadata, rows = load_jsonl(path)

    count = 0

    for row in rows:
        anchor_id = row.get("predicate_anchor_id")
        if not anchor_id:
            continue

        anchor_sources[str(anchor_id)].add(dataset_name)
        count += 1

    detector_counts[dataset_name] = count


def dataset_path(root: Path, template: str, book: str) -> Path:
    return root / template.format(book=book)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Merge approved Stage 4 dependency candidate audits."
    )
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()

        anchor_sources: dict[str, set[str]] = defaultdict(set)
        detector_counts: dict[str, int] = {}
        datasets_loaded = []
        quarantined_present = []

        for dataset_name, relative_template in APPROVED_AUDIT_DATASETS.items():
            path = dataset_path(root, relative_template, book)
            if not path.is_file():
                continue

            collect_candidates(
                dataset_name,
                path,
                anchor_sources,
                detector_counts,
            )
            datasets_loaded.append(path)

        for dataset_name, relative_template in QUARANTINED_AUDIT_DATASETS.items():
            path = dataset_path(root, relative_template, book)
            if path.is_file():
                quarantined_present.append((dataset_name, path))

        if not datasets_loaded:
            raise FileNotFoundError(
                "No approved Stage 4 dependency audit datasets found."
            )

        total_unique = len(anchor_sources)

        overlaps = {
            anchor_id: sorted(list(sources))
            for anchor_id, sources in anchor_sources.items()
            if len(sources) > 1
        }

        overlap_count = len(overlaps)

        print("MNA Stage 4 — Dependency Audit Merger")
        print(f"BOOK: {book}")
        print(f"VERSION: {VERSION}")
        print()

        print("APPROVED AUDIT DATASETS LOADED:")
        for dataset in datasets_loaded:
            print(f"  - {dataset}")

        print()
        print("QUARANTINED AUDIT DATASETS PRESENT BUT EXCLUDED:")
        if not quarantined_present:
            print("  - (none)")
        else:
            for dataset_name, path in quarantined_present:
                print(f"  - {dataset_name}: {path}")

        print()
        print("RAW APPROVED DETECTOR COUNTS:")
        for detector_name in sorted(detector_counts):
            print(f"  - {detector_name}: {detector_counts[detector_name]}")

        print()
        print(f"UNIQUE APPROVED PREDICATE ANCHOR IDS: {total_unique}")
        print(f"APPROVED OVERLAPPING ANCHOR IDS: {overlap_count}")

        print()
        print("APPROVED OVERLAP PREVIEW:")

        preview = list(sorted(overlaps.items()))[:25]
        if not preview:
            print("  (none)")
        else:
            for idx, (anchor_id, sources) in enumerate(preview, start=1):
                joined = ", ".join(sources)
                print(f"  {idx:>2}. {anchor_id} | {joined}")

        remaining = overlap_count - len(preview)
        if remaining > 0:
            print(f"  ... {remaining} more overlaps")

        print()
        print("OFFICIAL STAGE 4 CLASSIFICATION CHANGED: NO")

        return 0

    except Exception as exc:
        print("MNA Stage 4 dependency audit merge FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
