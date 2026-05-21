#!/usr/bin/env python3
"""
MNA Stage 5 — Trunk Candidacy Assertions

Purpose:
Convert observable candidacy environments into mechanically constrained assertions.

This script does not score, rank, or claim final trunk status.
It only states what the current observable evidence justifies asserting.
"""

import argparse
import json
from pathlib import Path

ENV_STRONG_POSITIVE = "ENV-001-STRONG_POSITIVE_INDEPENDENCE_SIGNAL_SET"
ENV_CONDITIONAL_PRESSURE = "ENV-002-CONDITIONAL_SURVIVAL_UNDER_DEPENDENCY_PRESSURE"
ENV_DEPENDENCY_PRESSURE_WARN = "ENV-003-DEPENDENCY_PRESSURE_PRESERVE_WARN"

ASSERT_INDEPENDENCE_CLUSTER = "ASSERT-001-OBSERVABLE_INDEPENDENCE_SIGNAL_CLUSTER_PRESENT"
ASSERT_CONDITIONAL_PRESSURE = "ASSERT-002-CONDITIONAL_SURVIVAL_UNDER_DEPENDENCY_PRESSURE_PRESENT"
ASSERT_UNRESOLVED_DEPENDENCY = "ASSERT-003-DEPENDENCY_PRESSURE_REMAINS_UNRESOLVED"
ASSERT_NO_FINAL_TRUNK_CLAIM = "ASSERT-900-NO_FINAL_TRUNK_STATUS_CLAIMED"

ASSERTIONS_BY_ENVIRONMENT = {
    ENV_STRONG_POSITIVE: [
        ASSERT_INDEPENDENCE_CLUSTER,
        ASSERT_NO_FINAL_TRUNK_CLAIM,
    ],
    ENV_CONDITIONAL_PRESSURE: [
        ASSERT_CONDITIONAL_PRESSURE,
        ASSERT_NO_FINAL_TRUNK_CLAIM,
    ],
    ENV_DEPENDENCY_PRESSURE_WARN: [
        ASSERT_UNRESOLVED_DEPENDENCY,
        ASSERT_NO_FINAL_TRUNK_CLAIM,
    ],
}


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("candidacy_environments_jsonl", type=Path)
    p.add_argument("output_jsonl", type=Path)
    args = p.parse_args()

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    unrecognized = 0

    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for row in load_jsonl(args.candidacy_environments_jsonl):
            env = row.get("candidacy_environment")
            assertions = ASSERTIONS_BY_ENVIRONMENT.get(env)

            if assertions is None:
                assertions = [ASSERT_NO_FINAL_TRUNK_CLAIM]
                unrecognized += 1

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
                "candidacy_environment": env,
                "assertions": assertions,
                "assertion_count": len(assertions),
                "signals": row.get("signals", []),
                "negative_pressure": row.get("negative_pressure", []),
            }
            f.write(json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1

    print(f"WROTE {count} records -> {args.output_jsonl}")
    print(f"UNRECOGNIZED_ENVIRONMENTS: {unrecognized}")


if __name__ == "__main__":
    main()
