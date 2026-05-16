#!/usr/bin/env python3
"""
MNA Stage 4 — independent clause candidate builder.

PURPOSE
- Read Stage 4 predicate-completeness rows.
- Read dependency-candidate audit datasets.
- Mechanically mark anchors as independent-clause candidates or not.

IMPORTANT
This script does NOT create trunk.
This script does NOT create [S] or [M].
This script does NOT create connector relationships, labels, units, or titles.

It only creates a mechanical Stage 4 candidate layer:

- NO: grammar-based dependency candidate found in approved audit source.
- UNRESOLVED_CANDIDATE: no approved dependency candidate found yet.

This is intentionally conservative.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

VERSION = "stage4-independent-clause-candidates-v1"

NO_STATUS = "NO"
UNRESOLVED_STATUS = "UNRESOLVED_CANDIDATE"


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

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
        raise ValueError(f"Missing metadata row: {path}")

    return metadata, rows


def collect_dependency_candidate_sources(root: Path, book: str) -> dict[str, set[str]]:
    audit_paths = {
        "absolute-dependency-candidates": root
        / "audits"
        / "stage4"
        / "absolute-dependency-candidates"
        / f"{book}.jsonl",
        "relative-dependency-candidates": root
        / "audits"
        / "stage4"
        / "relative-dependency-candidates"
        / f"{book}.jsonl",
    }

    anchor_sources: dict[str, set[str]] = defaultdict(set)

    for source_name, path in audit_paths.items():
        if not path.is_file():
            continue

        _metadata, rows = load_jsonl(path)

        for row in rows:
            anchor_id = row.get("predicate_anchor_id")
            if anchor_id:
                anchor_sources[str(anchor_id)].add(source_name)

    return anchor_sources


def build_candidate_row(
    row: dict[str, object],
    dependency_sources: set[str],
) -> dict[str, object]:
    if dependency_sources:
        status = NO_STATUS
        reason = "Grammar-based dependency candidate found in Stage 4 audit source."
        evidence_status = "dependency_candidate_detected"
    else:
        status = UNRESOLVED_STATUS
        reason = "No approved grammar-based dependency candidate detected yet."
        evidence_status = "not_yet_eliminated"

    return {
        "record_type": "independent_clause_candidate_row",
        "predicate_anchor_id": row["predicate_anchor_id"],
        "book": row["book"],
        "chapter": row["chapter"],
        "verse": row["verse"],
        "reference": row["reference"],
        "anchor_order": row["anchor_order"],
        "greek_surface": row["greek_surface"],
        "greek_clean": row["greek_clean"],
        "lemma": row["lemma"],
        "morphology": row["morphology"],
        "mood": row["mood"],
        "person": row["person"],
        "number": row["number"],
        "independent_clause_candidate": status,
        "stage4_status": status,
        "dependency_candidate_sources": sorted(list(dependency_sources)),
        "reason": reason,
        "evidence_status": evidence_status,
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
        "connector_relationship_claim": "NONE",
        "label_claim": "NONE",
        "unit_claim": "NONE",
        "title_claim": "NONE",
    }


def build_dataset(book: str, root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    completeness_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
    output_path = root / "datasets" / "independent-clause-candidates" / f"{book}.jsonl"

    completeness_metadata, completeness_rows = load_jsonl(completeness_path)

    if str(completeness_metadata.get("book")) != book:
        raise ValueError(
            f"Requested book '{book}' but predicate-completeness dataset is '{completeness_metadata.get('book')}'."
        )

    dependency_candidate_sources = collect_dependency_candidate_sources(root, book)

    rows = []
    no_count = 0
    unresolved_count = 0

    for row in completeness_rows:
        anchor_id = str(row["predicate_anchor_id"])
        sources = dependency_candidate_sources.get(anchor_id, set())
        out_row = build_candidate_row(row, sources)
        rows.append(out_row)

        if out_row["independent_clause_candidate"] == NO_STATUS:
            no_count += 1
        elif out_row["independent_clause_candidate"] == UNRESOLVED_STATUS:
            unresolved_count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 4 — Independent Clause Candidates",
        "producer_script": "scripts/stage4/build_independent_clause_candidates.py",
        "producer_command": f"python3 scripts/stage4/build_independent_clause_candidates.py {book}",
        "version": VERSION,
        "book": book,
        "source_dataset": str(completeness_path.relative_to(root)),
        "rows": len(rows),
        "independent_clause_candidate_NO": no_count,
        "independent_clause_candidate_UNRESOLVED": unresolved_count,
        "rule": "NO only when a grammar-based dependency candidate exists in an approved Stage 4 audit dataset; otherwise UNRESOLVED_CANDIDATE.",
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
        "connector_relationship_claim": "NONE",
        "label_claim": "NONE",
        "unit_claim": "NONE",
        "title_claim": "NONE",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    return metadata, rows


def print_visible_output(book: str, root: Path, metadata: dict[str, object], rows: list[dict[str, object]], preview_lines: int) -> None:
    output_path = root / "datasets" / "independent-clause-candidates" / f"{book}.jsonl"

    print("MNA Stage 4 — Independent Clause Candidates")
    print(f"BOOK: {book}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS: {metadata['rows']}")
    print(f"NO: {metadata['independent_clause_candidate_NO']}")
    print(f"UNRESOLVED_CANDIDATE: {metadata['independent_clause_candidate_UNRESOLVED']}")
    print("TRUNK_CLAIM: NONE")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, row in enumerate(rows[:preview_lines], start=1):
        sources = ",".join(row["dependency_candidate_sources"])
        if not sources:
            sources = "-"
        print(
            f"{idx:>4}. {row['predicate_anchor_id']} | {row['reference']} | "
            f"{row['greek_surface']} | {row['independent_clause_candidate']} | sources={sources}"
        )

    remaining = len(rows) - min(len(rows), preview_lines)
    if remaining:
        print(f"... {remaining} more independent clause candidate rows written")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Stage 4 independent clause candidate dataset."
    )
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = mna_root_from_script()
        metadata, rows = build_dataset(book, root)
        print_visible_output(book, root, metadata, rows, args.preview_lines)
        return 0
    except Exception as exc:
        print("MNA Stage 4 independent clause candidate build FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
