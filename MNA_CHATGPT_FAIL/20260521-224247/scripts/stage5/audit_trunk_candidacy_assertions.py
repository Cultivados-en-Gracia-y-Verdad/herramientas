#!/usr/bin/env python3
"""
MNA Stage 5 — Trunk Candidacy Assertion Audit

Purpose:
Audit internal mechanical consistency of trunk-candidacy assertions.

This script does not interpret, score, rank, or claim final trunk status.
It only checks that environment labels and assertion labels remain internally coherent.
"""

import argparse
import json
from pathlib import Path

ENV_001 = "ENV-001-STRONG_POSITIVE_INDEPENDENCE_SIGNAL_SET"
ENV_002 = "ENV-002-CONDITIONAL_SURVIVAL_UNDER_DEPENDENCY_PRESSURE"
ENV_003 = "ENV-003-DEPENDENCY_PRESSURE_PRESERVE_WARN"

ASSERT_001 = "ASSERT-001-OBSERVABLE_INDEPENDENCE_SIGNAL_CLUSTER_PRESENT"
ASSERT_002 = "ASSERT-002-CONDITIONAL_SURVIVAL_UNDER_DEPENDENCY_PRESSURE_PRESENT"
ASSERT_003 = "ASSERT-003-DEPENDENCY_PRESSURE_REMAINS_UNRESOLVED"
ASSERT_900 = "ASSERT-900-NO_FINAL_TRUNK_STATUS_CLAIMED"

ENV_REQUIRED_ASSERTION = {
    ENV_001: ASSERT_001,
    ENV_002: ASSERT_002,
    ENV_003: ASSERT_003,
}

IMPOSSIBLE_ASSERTION_PAIR = {ASSERT_001, ASSERT_003}


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def failure_row(rule_id, message, row):
    return {
        "rule_id": rule_id,
        "status": "FAIL",
        "message": message,
        "book": row.get("book"),
        "chapter": row.get("chapter"),
        "verse": row.get("verse"),
        "unit_id": row.get("unit_id"),
        "clause_id": row.get("clause_id"),
        "candidacy_environment": row.get("candidacy_environment"),
        "assertions": row.get("assertions", []),
    }


def audit_row(row):
    failures = []
    assertions = set(row.get("assertions") or [])
    env = row.get("candidacy_environment")

    if IMPOSSIBLE_ASSERTION_PAIR.issubset(assertions):
        failures.append(failure_row(
            "RULE-001",
            "ASSERT-001 and ASSERT-003 cannot coexist on the same row.",
            row,
        ))

    if ASSERT_900 not in assertions:
        failures.append(failure_row(
            "RULE-003",
            "ASSERT-900 must appear on every row to prevent final-trunk certainty drift.",
            row,
        ))

    non_900 = [a for a in assertions if a != ASSERT_900]
    if not non_900:
        failures.append(failure_row(
            "RULE-004",
            "Every row must contain at least one non-900 assertion.",
            row,
        ))

    required = ENV_REQUIRED_ASSERTION.get(env)
    if required and required not in assertions:
        failures.append(failure_row(
            "RULE-005",
            "Candidacy environment is missing its required assertion.",
            row,
        ))

    return failures


def main():
    p = argparse.ArgumentParser()
    p.add_argument("assertions_jsonl", type=Path)
    p.add_argument("output_jsonl", type=Path)
    args = p.parse_args()

    rows = list(load_jsonl(args.assertions_jsonl))
    failures = []

    for row in rows:
        failures.extend(audit_row(row))

    rule_ids = ["RULE-001", "RULE-003", "RULE-004", "RULE-005"]
    failure_counts = {rule_id: 0 for rule_id in rule_ids}
    for failure in failures:
        failure_counts[failure["rule_id"]] += 1

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for rule_id in rule_ids:
            summary = {
                "record_type": "audit_summary",
                "rule_id": rule_id,
                "status": "PASS" if failure_counts[rule_id] == 0 else "FAIL",
                "failures": failure_counts[rule_id],
            }
            f.write(json.dumps(summary, ensure_ascii=False, sort_keys=True) + "\n")

        for failure in failures:
            out = dict(failure)
            out["record_type"] = "audit_failure"
            f.write(json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"ROWS_AUDITED: {len(rows)}")
    print(f"FAILURES: {len(failures)}")
    print(f"WROTE -> {args.output_jsonl}")


if __name__ == "__main__":
    main()
