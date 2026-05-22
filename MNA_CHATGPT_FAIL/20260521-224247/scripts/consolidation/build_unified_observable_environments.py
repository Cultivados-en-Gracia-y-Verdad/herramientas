#!/usr/bin/env python3
"""
MNA Consolidation — Unified Observable Environments

Purpose
-------
Assemble observable information from Stages 1–6 into one continuity-ready
environment layer.

This script does NOT:
- create hierarchy,
- create movement markers,
- create labels,
- create sections,
- create dependency claims,
- create discourse structure.

It only consolidates already-observed data and adds sequence/adjacency fields.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

VERSION = "unified-observable-environments-v1"
RECORD_TYPE = "unified_observable_environment"


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


def index_by_keys(rows: list[dict], keys: list[str]) -> dict[str, dict]:
    indexed = {}
    for row in rows:
        for key in keys:
            value = row.get(key)
            if value:
                indexed[str(value)] = row
    return indexed


def first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def row_sort_key(row: dict) -> tuple[int, int, int, str]:
    return (
        int(row.get("chapter") or 0),
        int(row.get("verse") or 0),
        int(row.get("anchor_order") or row.get("sequence_index") or 0),
        str(row.get("clause_id") or row.get("unit_id") or ""),
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build unified observable environments from Stages 1–6.")
    parser.add_argument("book", help="Book slug, e.g. santiago")
    args = parser.parse_args(argv)

    root = root_from_script()
    book = args.book.strip().lower()

    finite_path = root / "datasets" / "finite-verbs" / f"{book}.jsonl"
    anchors_path = root / "datasets" / "predicate-anchors" / f"{book}.jsonl"
    skeleton_path = root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"
    completeness_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
    stage5_path = root / "datasets" / "stage5" / book / "trunk-candidacy-environments.jsonl"
    stage6_path = root / "datasets" / "stage6" / book / "relational-discourse-signals.jsonl"

    output_path = root / "datasets" / "unified-observable-environments" / f"{book}.jsonl"

    finite_rows = load_jsonl(finite_path)
    anchor_rows = load_jsonl(anchors_path)
    skeleton_rows = load_jsonl(skeleton_path)
    completeness_rows = load_jsonl(completeness_path)
    stage5_rows = load_jsonl(stage5_path)
    stage6_rows = load_jsonl(stage6_path)

    finite_by_refverb = {
        f"{r.get('reference')}::{r.get('finite_verb') or r.get('surface') or r.get('greek_surface')}": r
        for r in finite_rows
    }
    anchors_by_id = index_by_keys(anchor_rows, ["predicate_anchor_id", "anchor_id", "clause_id", "unit_id"])
    skeleton_by_id = index_by_keys(skeleton_rows, ["predicate_anchor_id", "anchor_id", "clause_id", "unit_id"])
    completeness_by_id = index_by_keys(completeness_rows, ["predicate_anchor_id", "anchor_id", "clause_id", "unit_id"])
    stage6_by_clause = index_by_keys(stage6_rows, ["clause_id", "unit_id"])

    consolidated = []

    for stage5 in sorted(stage5_rows, key=row_sort_key):
        clause_id = stage5.get("clause_id") or stage5.get("unit_id")
        unit_id = stage5.get("unit_id") or clause_id

        anchor = anchors_by_id.get(str(clause_id)) or anchors_by_id.get(str(unit_id)) or {}
        skeleton = skeleton_by_id.get(str(clause_id)) or skeleton_by_id.get(str(unit_id)) or {}
        completeness = completeness_by_id.get(str(clause_id)) or completeness_by_id.get(str(unit_id)) or {}
        stage6 = stage6_by_clause.get(str(clause_id)) or stage6_by_clause.get(str(unit_id)) or {}

        reference = stage5.get("reference") or stage6.get("reference") or anchor.get("reference")
        finite_key = f"{reference}::{stage5.get('finite_verb')}"
        finite = finite_by_refverb.get(finite_key, {})

        consolidated.append({
            "record_type": RECORD_TYPE,
            "version": VERSION,
            "book": book,
            "chapter": first_present(stage5.get("chapter"), stage6.get("chapter"), anchor.get("chapter")),
            "verse": first_present(stage5.get("verse"), stage6.get("verse"), anchor.get("verse")),
            "reference": reference,
            "sequence_index": len(consolidated) + 1,
            "unit_id": unit_id,
            "clause_id": clause_id,
            "predicate_anchor_id": first_present(stage5.get("predicate_anchor_id"), anchor.get("predicate_anchor_id"), skeleton.get("predicate_anchor_id"), clause_id),
            "anchor_order": first_present(skeleton.get("anchor_order"), anchor.get("anchor_order")),
            "finite_verb": first_present(stage5.get("finite_verb"), stage6.get("finite_verb"), anchor.get("finite_verb"), finite.get("finite_verb")),
            "lemma": first_present(anchor.get("lemma"), finite.get("lemma")),
            "morphology": first_present(stage5.get("anchor_morphology"), anchor.get("morphology"), finite.get("morphology"), finite.get("morph")),
            "person": first_present(stage5.get("anchor_person"), anchor.get("person"), finite.get("person")),
            "number": first_present(stage5.get("anchor_number"), anchor.get("number"), finite.get("number")),
            "mood": first_present(stage5.get("anchor_mood"), anchor.get("mood"), finite.get("mood")),
            "stage4_classification": completeness.get("classification"),
            "stage4_trunk_claim": completeness.get("trunk_claim"),
            "stage5_candidacy_environment": stage5.get("candidacy_environment"),
            "stage5_survival_decision": stage5.get("survival_decision"),
            "stage5_survival_rule_id": stage5.get("survival_rule_id"),
            "stage5_signals": stage5.get("signals", []),
            "stage5_negative_pressure": stage5.get("negative_pressure", []),
            "connector_surface": first_present(stage6.get("connector_surface"), stage5.get("connector_greek")),
            "connector_lemma": first_present(stage6.get("connector_lemma"), stage5.get("connector_lemma"), stage5.get("connector_greek")),
            "stage6_signal_category": stage6.get("signal_category"),
            "stage6_signal_status": stage6.get("signal_status"),
            "previous_clause_id": None,
            "next_clause_id": None,
            "source_stage_lineage": [
                "stage1:finite-verbs",
                "stage2:predicate-anchors",
                "stage3:anchor-skeleton",
                "stage4:predicate-completeness",
                "stage5:trunk-candidacy-environments",
                "stage6:relational-discourse-signals",
            ],
            "consolidation_policy": "OBSERVATIONAL_FIELDS_ONLY_NO_STRUCTURE_CLAIMS",
        })

    for idx, row in enumerate(consolidated):
        row["previous_clause_id"] = consolidated[idx - 1]["clause_id"] if idx > 0 else None
        row["next_clause_id"] = consolidated[idx + 1]["clause_id"] if idx + 1 < len(consolidated) else None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in consolidated:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Consolidation — Unified Observable Environments")
    print(f"VERSION: {VERSION}")
    print(f"BOOK: {book}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS WRITTEN: {len(consolidated)}")
    print("POLICY: OBSERVATIONAL CONSOLIDATION ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())