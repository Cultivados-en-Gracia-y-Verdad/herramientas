#!/usr/bin/env python3
"""
MNA Stage 5 — Positive Independence Signals

Purpose:
Emit observable positive-independence evidence for Stage 5 rows.

This script does not score, rank, or claim final trunk certainty.
It only records binary observable signals from the enriched Stage 5 survival row.
"""

import argparse
import json
from pathlib import Path

SIGNAL_CONNECTORLESS = "SIGNAL-001-CONNECTORLESS_FINITE_PREDICATE"
SIGNAL_NO_DEPENDENCY = "SIGNAL-002-NO_DEPENDENCY_CANDIDATE"
SIGNAL_SURVIVED_STAGE5 = "SIGNAL-003-SURVIVED_STAGE5"
SIGNAL_NOT_SUBORDINATOR = "SIGNAL-004-NOT_SUBORDINATOR_INTRODUCED"

SURVIVAL_STATES = {"SURVIVE", "PRESERVE_WARN"}


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def build_signals(row):
    signals = []

    if row.get("connector_greek") is None:
        signals.append(SIGNAL_CONNECTORLESS)

    if row.get("dependency_status") is None:
        signals.append(SIGNAL_NO_DEPENDENCY)

    if row.get("survival_decision") in SURVIVAL_STATES:
        signals.append(SIGNAL_SURVIVED_STAGE5)

    if row.get("connector_rule_id") is None:
        signals.append(SIGNAL_NOT_SUBORDINATOR)

    return signals


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
                "signals": build_signals(row),
            }
            out["signal_count"] = len(out["signals"])
            f.write(json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1

    print(f"WROTE {count} records -> {args.output_jsonl}")


if __name__ == "__main__":
    main()
