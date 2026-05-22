#!/usr/bin/env python3
"""
MNA Stage 5 — Negative Independence Pressure

Purpose:
Emit observable pressure against independence for Stage 5 rows.

This script does not score, rank, or claim final dependency.
It only records binary observable pressure signals from the enriched Stage 5 survival row.
"""

import argparse
import json
from pathlib import Path

NEG_DEPENDENCY_PRESENT = "NEG-001-DEPENDENCY_CANDIDATE_PRESENT"
NEG_CONNECTOR_PRESENT = "NEG-002-CONNECTOR_PRESENT"
NEG_SUBORDINATOR_RULE = "NEG-003-SUBORDINATOR_RULE_PRESENT"
NEG_PRESERVE_WARN = "NEG-004-PRESERVE_WARN_SURVIVAL_STATE"


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def build_pressure(row):
    pressure = []

    if row.get("dependency_status") is not None:
        pressure.append(NEG_DEPENDENCY_PRESENT)

    if row.get("connector_greek") is not None:
        pressure.append(NEG_CONNECTOR_PRESENT)

    if row.get("connector_rule_id") is not None:
        pressure.append(NEG_SUBORDINATOR_RULE)

    if row.get("survival_decision") == "PRESERVE_WARN":
        pressure.append(NEG_PRESERVE_WARN)

    return pressure


def main():
    p = argparse.ArgumentParser()
    p.add_argument("enriched_survival_jsonl", type=Path)
    p.add_argument("output_jsonl", type=Path)
    args = p.parse_args()

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    count = 0

    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for row in load_jsonl(args.enriched_survival_jsonl):
            out = {
                "book": row.get("book"),
                "chapter": row.get("chapter"),
                "verse": row.get("verse"),
                "unit_id": row.get("unit_id"),
                "clause_id": row.get("clause_id"),
                "finite_verb": row.get("finite_verb"),
                "connector_greek": row.get("connector_greek"),
                "dependency_status": row.get("dependency_status"),
                "survival_decision": row.get("survival_decision"),
                "survival_rule_id": row.get("survival_rule_id"),
                "anchor_mood": row.get("anchor_mood"),
                "anchor_morphology": row.get("anchor_morphology"),
                "anchor_person": row.get("anchor_person"),
                "anchor_number": row.get("anchor_number"),
                "negative_pressure": build_pressure(row),
            }
            out["negative_pressure_count"] = len(out["negative_pressure"])
            f.write(json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1

    print(f"WROTE {count} records -> {args.output_jsonl}")


if __name__ == "__main__":
    main()
