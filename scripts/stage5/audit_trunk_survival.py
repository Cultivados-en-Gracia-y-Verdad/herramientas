#!/usr/bin/env python3
"""
Stage 5 — Survivability Audit

This script audits Stage 5 survivability outputs for
mechanically demonstrable structural violations.

The audit does not evaluate semantic importance.
The audit does not evaluate theology.
The audit does not evaluate rhetorical prominence.

The audit only evaluates structural survivability consistency.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


VALID_DECISIONS = {
    "SURVIVE",
    "REMOVE",
    "PRESERVE_WARN",
}

REQUIRED_FIELDS = {
    "book",
    "chapter",
    "verse",
    "unit_id",
    "survival_decision",
    "survival_rule_id",
    "survival_reason",
    "source_stage4_decision",
}

CONDITIONAL_CONNECTORS = {
    "εἰ",
    "ἐὰν",
}


class Stage5AuditError(Exception):
    """Raised for Stage 5 audit failures."""



def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue

            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise Stage5AuditError(
                    f"Invalid JSONL at {path}:{line_no}: {exc}"
                ) from exc

            if not isinstance(obj, dict):
                raise Stage5AuditError(
                    f"Expected JSON object at {path}:{line_no}"
                )

            yield obj



def make_issue(
    category: str,
    code: str,
    message: str,
    record: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "category": category,
        "code": code,
        "message": message,
        "book": record.get("book"),
        "chapter": record.get("chapter"),
        "verse": record.get("verse"),
        "unit_id": record.get("unit_id"),
        "clause_id": record.get("clause_id"),
    }



def audit_required_fields(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []

    missing = [
        field
        for field in REQUIRED_FIELDS
        if field not in record
    ]

    if missing:
        issues.append(
            make_issue(
                "FAIL",
                "S5_MISSING_REQUIRED_FIELDS",
                f"Missing required fields: {missing}",
                record,
            )
        )

    return issues



def audit_decision_validity(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []

    decision = record.get("survival_decision")

    if decision not in VALID_DECISIONS:
        issues.append(
            make_issue(
                "FAIL",
                "S5_INVALID_DECISION",
                f"Invalid survival decision: {decision}",
                record,
            )
        )

    return issues



def audit_conditional_integrity(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []

    connector = (
        record.get("connector_greek")
        or record.get("connector")
    )

    if connector not in CONDITIONAL_CONNECTORS:
        return issues

    decision = record.get("survival_decision")

    if decision == "REMOVE":
        issues.append(
            make_issue(
                "FAIL",
                "S5_CONDITIONAL_REMOVAL",
                "Conditional logical unit removed under preserved conditional policy.",
                record,
            )
        )

    return issues



def audit_rule_provenance(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []

    if not record.get("survival_rule_id"):
        issues.append(
            make_issue(
                "FAIL",
                "S5_MISSING_RULE_PROVENANCE",
                "Missing survival_rule_id provenance.",
                record,
            )
        )

    if not record.get("survival_reason"):
        issues.append(
            make_issue(
                "FAIL",
                "S5_MISSING_SURVIVAL_REASON",
                "Missing survival_reason provenance.",
                record,
            )
        )

    return issues



def audit_warning_integrity(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []

    decision = record.get("survival_decision")
    warnings = record.get("warnings") or []

    if decision == "PRESERVE_WARN" and not warnings:
        issues.append(
            make_issue(
                "WARN",
                "S5_WARN_WITHOUT_WARNING_RECORD",
                "PRESERVE_WARN emitted without warning metadata.",
                record,
            )
        )

    return issues



def audit_record(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    issues.extend(audit_required_fields(record))
    issues.extend(audit_decision_validity(record))
    issues.extend(audit_conditional_integrity(record))
    issues.extend(audit_rule_provenance(record))
    issues.extend(audit_warning_integrity(record))

    return issues



def summarize(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(issue["category"] for issue in issues)
    return {
        "FAIL": counts.get("FAIL", 0),
        "WARN": counts.get("WARN", 0),
        "FLAG": counts.get("FLAG", 0),
    }



def write_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True)
                + "\n"
            )



def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Stage 5 survivability outputs."
    )

    parser.add_argument(
        "input_jsonl",
        type=Path,
        help="Stage 5 survivability JSONL",
    )

    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Emit audit issues as JSONL",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSONL audit output path",
    )

    args = parser.parse_args(argv)

    try:
        records = list(load_jsonl(args.input_jsonl))

        all_issues: List[Dict[str, Any]] = []

        for record in records:
            all_issues.extend(audit_record(record))

        summary = summarize(all_issues)

        if args.jsonl:
            for issue in all_issues:
                print(json.dumps(issue, ensure_ascii=False, sort_keys=True))
        else:
            print(f"FAILURES: {summary['FAIL']}")
            print(f"WARNINGS: {summary['WARN']}")
            print(f"FLAGS: {summary['FLAG']}")

        if args.output:
            write_jsonl(all_issues, args.output)

        return 1 if summary["FAIL"] else 0

    except Stage5AuditError as exc:
        print(f"Stage 5 audit error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
