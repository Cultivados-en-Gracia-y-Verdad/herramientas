#!/usr/bin/env python3
"""
MNA Stage 4 — Suggested Trunk Draft Builder

PURPOSE
- Produce a reviewable suggested-trunk draft.
- Use existing Stage 4 audit evidence without claiming proof.
- Write only to datasets/suggested-trunk-drafts/.

IMPORTANT
This script does NOT:
- prove independent clauses,
- create accepted trunk,
- overwrite human-reviewed rows,
- create [S],
- create [M],
- create labels,
- create sections.

This is a disposable draft generator.
Accepted trunk must be reviewed separately.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

VERSION = "stage4-suggested-trunk-draft-v1"

APPROVED_DEPENDENCY_SOURCES = {
    "absolute-dependency-candidates",
    "relative-dependency-candidates",
    "content-clause-dependency-candidates",
}

STATUS_SUGGESTED = "SUGGESTED"
STATUS_NEEDS_REVIEW = "NEEDS_REVIEW"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    metadata = None
    rows = []

    if not path.is_file():
        return metadata, rows

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)

    return metadata, rows


def group_by_reference(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row.get("reference"))].append(row)
    for ref_rows in grouped.values():
        ref_rows.sort(key=lambda r: int(r.get("anchor_order", 0)))
    return dict(grouped)


def load_dependency_sources(root: Path, book: str) -> dict[str, set[str]]:
    source_paths = {
        "absolute-dependency-candidates": root / "audits" / "stage4" / "absolute-dependency-candidates" / f"{book}.jsonl",
        "relative-dependency-candidates": root / "audits" / "stage4" / "relative-dependency-candidates" / f"{book}.jsonl",
        "content-clause-dependency-candidates": root / "audits" / "stage4" / "content-clause-dependency-candidates" / f"{book}.jsonl",
    }

    anchor_sources: dict[str, set[str]] = defaultdict(set)

    for source_name, path in source_paths.items():
        _metadata, rows = load_jsonl(path)
        for row in rows:
            anchor_id = row.get("predicate_anchor_id")
            if anchor_id:
                anchor_sources[str(anchor_id)].add(source_name)

    return anchor_sources


def load_span_lookup(root: Path, book: str) -> dict[str, dict]:
    path = root / "audits" / "stage4" / "local-clause-span-audit" / f"{book}.jsonl"
    _metadata, rows = load_jsonl(path)
    return {str(row.get("predicate_anchor_id")): row for row in rows}


def choose_suggested_anchor(ref_rows: list[dict], dependency_sources: dict[str, set[str]]):
    """
    First-pass conservative heuristic:
    - skip anchors with approved dependency evidence;
    - prefer the earliest surviving predicate in the verse;
    - mark confidence low/medium depending on how many unresolved anchors remain.

    This is intentionally simple and reviewable.
    """

    surviving = []
    removed = []

    for row in ref_rows:
        anchor_id = str(row.get("predicate_anchor_id"))
        sources = dependency_sources.get(anchor_id, set())
        if sources:
            removed.append((row, sorted(sources)))
        else:
            surviving.append(row)

    if not surviving:
        return None, removed, STATUS_NEEDS_REVIEW, CONFIDENCE_LOW, "No predicate survives approved dependency filters in this verse."

    suggested = surviving[0]

    if len(surviving) == 1:
        confidence = CONFIDENCE_MEDIUM
        status = STATUS_SUGGESTED
        reason = "Only one predicate in this verse currently survives approved dependency filters."
    else:
        confidence = CONFIDENCE_LOW
        status = STATUS_NEEDS_REVIEW
        reason = "Multiple predicates survive approved dependency filters; earliest survivor selected as draft only."

    return suggested, removed, status, confidence, reason


def build_draft_row(reference: str, ref_rows: list[dict], dependency_sources: dict[str, set[str]], span_lookup: dict[str, dict]) -> dict:
    suggested, removed, status, confidence, reason = choose_suggested_anchor(ref_rows, dependency_sources)

    if suggested is None:
        trunk_greek = ""
        predicate_anchor_id = None
        span = None
    else:
        predicate_anchor_id = suggested.get("predicate_anchor_id")
        span = span_lookup.get(str(predicate_anchor_id), {})
        trunk_greek = span.get("estimated_clause_span") or suggested.get("greek_surface") or ""

    removed_items = []
    for row, sources in removed:
        removed_items.append({
            "predicate_anchor_id": row.get("predicate_anchor_id"),
            "greek_surface": row.get("greek_surface"),
            "dependency_sources": sources,
        })

    surviving_items = []
    for row in ref_rows:
        anchor_id = str(row.get("predicate_anchor_id"))
        if dependency_sources.get(anchor_id):
            continue
        surviving_items.append({
            "predicate_anchor_id": row.get("predicate_anchor_id"),
            "greek_surface": row.get("greek_surface"),
        })

    return {
        "record_type": "suggested_trunk_draft_row",
        "stage": "Stage 4 — Suggested Trunk Draft",
        "version": VERSION,
        "book": ref_rows[0].get("book") if ref_rows else None,
        "chapter": ref_rows[0].get("chapter") if ref_rows else None,
        "verse": ref_rows[0].get("verse") if ref_rows else None,
        "reference": reference,
        "status": status,
        "confidence": confidence,
        "predicate_anchor_id": predicate_anchor_id,
        "trunk_greek": trunk_greek,
        "trunk_translation": "",
        "selected_span_method": span.get("span_method") if span else None,
        "surviving_predicates": surviving_items,
        "removed_or_subordinate": removed_items,
        "reason": reason,
        "needs_review": status == STATUS_NEEDS_REVIEW or confidence == CONFIDENCE_LOW,
        "human_override": False,
        "source_audits": [
            "predicate-completeness",
            "independent-clause-candidates",
            "local-clause-span-audit",
            "approved-dependency-candidates",
        ],
        "official_stage4_classification_changed": "NO",
        "trunk_claim": "SUGGESTED_DRAFT_ONLY",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Stage 4 suggested trunk draft dataset.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    book = args.book.strip().lower()
    root = mna_root_from_script()

    predicate_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
    output_path = root / "datasets" / "suggested-trunk-drafts" / f"{book}.jsonl"

    _metadata, predicate_rows = load_jsonl(predicate_path)
    dependency_sources = load_dependency_sources(root, book)
    span_lookup = load_span_lookup(root, book)

    by_reference = group_by_reference(predicate_rows)

    draft_rows = []
    for reference, ref_rows in sorted(
        by_reference.items(),
        key=lambda item: (
            int(item[1][0].get("chapter", 0)),
            int(item[1][0].get("verse", 0)),
        ),
    ):
        draft_rows.append(build_draft_row(reference, ref_rows, dependency_sources, span_lookup))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    status_counts = defaultdict(int)
    confidence_counts = defaultdict(int)
    for row in draft_rows:
        status_counts[row["status"]] += 1
        confidence_counts[row["confidence"]] += 1

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 4 — Suggested Trunk Draft",
        "version": VERSION,
        "book": book,
        "producer_script": "scripts/stage4/build_suggested_trunk_draft.py",
        "producer_command": f"python3 scripts/stage4/build_suggested_trunk_draft.py {book}",
        "source_dataset": str(predicate_path.relative_to(root)),
        "output_policy": "DRAFT_ONLY_DO_NOT_USE_AS_ACCEPTED_TRUNK_WITHOUT_HUMAN_REVIEW",
        "rows_written": len(draft_rows),
        "status_counts": dict(status_counts),
        "confidence_counts": dict(confidence_counts),
        "official_stage4_classification_changed": "NO",
        "trunk_claim": "SUGGESTED_DRAFT_ONLY",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
        for row in draft_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 4 — Suggested Trunk Draft Builder")
    print(f"BOOK: {book}")
    print(f"INPUT: {predicate_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS WRITTEN: {len(draft_rows)}")
    print(f"STATUS COUNTS: {dict(status_counts)}")
    print(f"CONFIDENCE COUNTS: {dict(confidence_counts)}")
    print("OUTPUT POLICY: DRAFT ONLY — HUMAN REVIEW REQUIRED")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, row in enumerate(draft_rows[: args.preview_lines], start=1):
        print(
            f"{idx:>4}. {row['reference']} | {row['status']} | {row['confidence']} | "
            f"anchor={row['predicate_anchor_id']} | trunk={row['trunk_greek']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
