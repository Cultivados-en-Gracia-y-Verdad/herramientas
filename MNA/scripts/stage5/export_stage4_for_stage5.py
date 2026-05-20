#!/usr/bin/env python3
"""Stage 4 to Stage 5 contract exporter."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

class ExportError(Exception):
    pass

def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ExportError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ExportError(f"Expected JSON object at {path}:{line_no}")
            yield obj

def iter_stage4_rows(path: Path) -> Iterable[Dict[str, Any]]:
    for record in load_jsonl(path):
        if record.get("record_type") == "metadata":
            continue
        yield record

def load_subordinator_candidates(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if path is None:
        return {}
    indexed: Dict[str, Dict[str, Any]] = {}
    for record in iter_stage4_rows(path):
        anchor_id = record.get("predicate_anchor_id")
        if not anchor_id:
            continue
        indexed[anchor_id] = record
    return indexed

def normalize_record(record: Dict[str, Any], subordinator_by_anchor: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    anchor_id = record.get("predicate_anchor_id") or record.get("unit_id") or record.get("structure_id") or record.get("id")
    sub = subordinator_by_anchor.get(anchor_id, {})

    dependency_sources = list(record.get("dependency_sources") or [])
    if sub:
        dependency_sources.append("subordinator-dependency-candidates")

    normalized = {
        "book": record.get("book"),
        "chapter": record.get("chapter"),
        "verse": record.get("verse"),
        "reference": record.get("reference"),
        "unit_id": anchor_id,
        "clause_id": record.get("clause_id") or anchor_id,
        "finite_verb": record.get("finite_verb") or record.get("anchor_greek_surface"),
        "connector": record.get("connector"),
        "connector_greek": record.get("connector_greek") or sub.get("subordinator_greek_surface"),
        "connector_lemma": sub.get("subordinator_lemma"),
        "connector_rule_id": sub.get("rule_id"),
        "dependency_status": record.get("dependency_status") or record.get("independency_status") or sub.get("candidate_status"),
        "stage4_decision": record.get("stage4_decision") or record.get("decision") or record.get("survivability_status"),
        "stage4_reason": record.get("stage4_reason") or record.get("reason"),
        "dependency_sources": dependency_sources,
        "warnings": list(record.get("warnings") or []),
        "flags": list(record.get("flags") or []),
        "stage4_claims": {
            "trunk_claim": record.get("trunk_claim"),
            "subject_marker_claim": record.get("subject_marker_claim"),
            "movement_marker_claim": record.get("movement_marker_claim"),
            "official_stage4_classification_changed": record.get("official_stage4_classification_changed"),
        },
        "audit_provenance": {"source_stage": 4, "exporter": "export_stage4_for_stage5.py"},
    }
    validate_contract(normalized)
    return normalized

def validate_contract(record: Dict[str, Any]) -> None:
    missing = [field for field in ["book", "chapter", "verse", "unit_id"] if record.get(field) in (None, "")]
    if missing:
        raise ExportError(f"Missing required Stage 5 contract fields: {missing}; record={record}")

def write_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    print(f"WROTE {count} records -> {path}")

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export Stage 4 records into Stage 5 contract format.")
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--subordinator-candidates", type=Path)
    args = parser.parse_args(argv)
    try:
        subordinator_by_anchor = load_subordinator_candidates(args.subordinator_candidates)
        records = (normalize_record(record, subordinator_by_anchor) for record in iter_stage4_rows(args.input_jsonl))
        write_jsonl(records, args.output_jsonl)
    except ExportError as exc:
        print(f"Stage 5 export error: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
