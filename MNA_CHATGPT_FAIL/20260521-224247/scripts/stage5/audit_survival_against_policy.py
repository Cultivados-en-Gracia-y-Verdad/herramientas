#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from connector_normalization import normalize_connector


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def load_policy(path):
    policy = {}
    for row in load_jsonl(path):
        connector = normalize_connector(row.get("connector"))
        if connector:
            policy[connector] = row
    return policy


def make_issue(category, code, message, record, policy_row=None):
    return {
        "category": category,
        "code": code,
        "message": message,
        "book": record.get("book"),
        "chapter": record.get("chapter"),
        "verse": record.get("verse"),
        "unit_id": record.get("unit_id"),
        "clause_id": record.get("clause_id"),
        "connector": normalize_connector(record.get("connector_greek") or record.get("connector")),
        "survival_decision": record.get("survival_decision"),
        "survival_rule_id": record.get("survival_rule_id"),
        "policy_state": None if policy_row is None else policy_row.get("policy_state"),
        "structural_state": None if policy_row is None else policy_row.get("structural_state"),
    }


def audit_record(record, policy):
    issues = []
    connector = normalize_connector(record.get("connector_greek") or record.get("connector"))

    if not connector:
        return issues

    policy_row = policy.get(connector)

    if policy_row is None:
        issues.append(make_issue(
            "WARN",
            "S5_POLICY_MISSING_FOR_CONNECTOR",
            "Connector appears in survival output but has no policy row.",
            record,
            None,
        ))
        return issues

    policy_state = policy_row.get("policy_state")
    decision = record.get("survival_decision")

    if policy_state == "SUBCLASS_REQUIRED" and decision == "SURVIVE":
        issues.append(make_issue(
            "FAIL",
            "S5_SUBCLASS_REQUIRED_BUT_SURVIVED",
            "Connector requires subclassing before global survival preservation.",
            record,
            policy_row,
        ))

    if policy_state == "INSUFFICIENT_DATA" and decision == "SURVIVE":
        issues.append(make_issue(
            "FAIL",
            "S5_INSUFFICIENT_DATA_BUT_SURVIVED",
            "Connector has insufficient data and may not be globally preserved.",
            record,
            policy_row,
        ))

    if policy_state == "PRESERVE_WITH_ANOMALY_MONITORING" and decision == "SURVIVE":
        issues.append(make_issue(
            "WARN",
            "S5_SURVIVE_REQUIRES_ANOMALY_MONITORING",
            "Connector is preserved but requires anomaly monitoring.",
            record,
            policy_row,
        ))

    return issues


def main():
    p = argparse.ArgumentParser()
    p.add_argument("survival_jsonl", type=Path)
    p.add_argument("policy_jsonl", type=Path)
    p.add_argument("--jsonl", action="store_true")
    args = p.parse_args()

    policy = load_policy(args.policy_jsonl)
    issues = []

    for record in load_jsonl(args.survival_jsonl):
        issues.extend(audit_record(record, policy))

    if args.jsonl:
        for issue in issues:
            print(json.dumps(issue, ensure_ascii=False, sort_keys=True))
        return

    counts = {"FAIL": 0, "WARN": 0, "FLAG": 0}
    for issue in issues:
        counts[issue["category"]] = counts.get(issue["category"], 0) + 1

    print(f"FAILURES: {counts.get('FAIL', 0)}")
    print(f"WARNINGS: {counts.get('WARN', 0)}")
    print(f"FLAGS: {counts.get('FLAG', 0)}")


if __name__ == "__main__":
    main()
