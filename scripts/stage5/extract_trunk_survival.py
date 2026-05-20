#!/usr/bin/env python3
"""
Stage 5 — True Trunk Extraction

This script applies mechanical survivability rules to Stage 4 audited
structural records and emits JSONL survival decisions.

Stage 5 does not rank semantic importance.
Stage 5 does not extract main ideas.
Stage 5 does not summarize meaning.

It only emits structural survival decisions with explicit rule provenance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


FORBIDDEN_TERMS = [
    "main idea",
    "emphasis",
    "central",
    "important",
    "primary",
    "secondary",
    "supporting idea",
    "theological center",
    "rhetorical climax",
]

DEFAULT_PRESERVE_WARN_RULE_ID = "S5-PRESERVE-WARN-UNKNOWN-001"
DEFAULT_CONDITIONAL_RULE_ID = "S5-PRESERVE-CONDITIONAL-UNIT-001"
DEFAULT_INDEPENDENT_RULE_ID = "S5-PRESERVE-INDEPENDENT-001"
DEFAULT_REMOVE_DEPENDENT_RULE_ID = "S5-REMOVE-DEPENDENT-001"


class Stage5Error(Exception):
    """Raised for Stage 5 contract violations."""


def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise Stage5Error(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(obj, dict):
                raise Stage5Error(f"Expected JSON object at {path}:{line_no}")
            yield obj


def load_rules(path: Path) -> Dict[str, Dict[str, Any]]:
    if yaml is None:
        raise Stage5Error("PyYAML is required to read roots_survival_rules.yaml")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    rules = data.get("rules", [])
    if not isinstance(rules, list):
        raise Stage5Error("rules file must contain a top-level list named 'rules'")
    indexed: Dict[str, Dict[str, Any]] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            raise Stage5Error("each rule must be a mapping")
        rule_id = rule.get("id")
        if not rule_id:
            raise Stage5Error("each rule must include an id")
        indexed[str(rule_id)] = rule
    return indexed


def normalize_connector(record: Dict[str, Any]) -> Optional[str]:
    value = record.get("connector_greek") or record.get("connector")
    if value is None:
        return None
    return str(value).strip() or None


def has_forbidden_language(record: Dict[str, Any]) -> List[str]:
    text = json.dumps(record, ensure_ascii=False).lower()
    found = []
    for term in FORBIDDEN_TERMS:
        if term.lower() in text:
            found.append(term)
    return found


def base_output(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "book": record.get("book"),
        "chapter": record.get("chapter"),
        "verse": record.get("verse"),
        "unit_id": record.get("unit_id"),
        "clause_id": record.get("clause_id"),
        "source_stage4_decision": record.get("stage4_decision"),
        "warnings": list(record.get("warnings") or []),
        "flags": list(record.get("flags") or []),
    }


def decide_survival(record: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    out = base_output(record)

    forbidden = has_forbidden_language(record)
    if forbidden:
        out["survival_decision"] = "PRESERVE_WARN"
        out["survival_rule_id"] = DEFAULT_PRESERVE_WARN_RULE_ID
        out["survival_reason"] = "Record contains forbidden semantic-importance language; preserved for audit review."
        out["warnings"].append({
            "code": "S5_FORBIDDEN_LANGUAGE",
            "terms": forbidden,
        })
        return out

    connector = normalize_connector(record)
    dependency_status = str(record.get("dependency_status") or "").lower()
    stage4_decision = str(record.get("stage4_decision") or "").lower()

    conditional_rule = rules.get(DEFAULT_CONDITIONAL_RULE_ID, {})
    conditional_connectors = set(conditional_rule.get("connectors") or ["εἰ", "ἐὰν"])

    if connector in conditional_connectors:
        out["survival_decision"] = "SURVIVE"
        out["survival_rule_id"] = DEFAULT_CONDITIONAL_RULE_ID
        out["survival_reason"] = "Conditional connector belongs to preserved conditional logical unit policy."
        return out

    warn_rule = rules.get(DEFAULT_PRESERVE_WARN_RULE_ID, {})
    warn_connectors = set(warn_rule.get("connectors") or ["ὅτι", "ἵνα", "ὡς", "καθὼς"])

    if connector in warn_connectors:
        out["survival_decision"] = "PRESERVE_WARN"
        out["survival_rule_id"] = DEFAULT_PRESERVE_WARN_RULE_ID
        out["survival_reason"] = "Connector remains warning-sensitive; preserved until explicit survival rule resolves it."
        out["warnings"].append({
            "code": "S5_WARNING_SENSITIVE_CONNECTOR",
            "connector": connector,
        })
        return out

    if "independent" in dependency_status or "independent" in stage4_decision:
        out["survival_decision"] = "SURVIVE"
        out["survival_rule_id"] = DEFAULT_INDEPENDENT_RULE_ID
        out["survival_reason"] = "Independent structure survives unless removed by explicit survival rule."
        return out

    if "dependent" in dependency_status or "dependent" in stage4_decision:
        out["survival_decision"] = "REMOVE"
        out["survival_rule_id"] = DEFAULT_REMOVE_DEPENDENT_RULE_ID
        out["survival_reason"] = "Dependent structure removed only when no preservation rule applies."
        return out

    out["survival_decision"] = "PRESERVE_WARN"
    out["survival_rule_id"] = DEFAULT_PRESERVE_WARN_RULE_ID
    out["survival_reason"] = "Insufficient certainty for removal; preserved with warning."
    out["warnings"].append({"code": "S5_INSUFFICIENT_CERTAINTY"})
    return out


def validate_output(record: Dict[str, Any]) -> None:
    required = [
        "survival_decision",
        "survival_rule_id",
        "survival_reason",
        "source_stage4_decision",
    ]
    missing = [key for key in required if key not in record]
    if missing:
        raise Stage5Error(f"Stage 5 output missing required fields: {missing}")


def write_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            validate_output(record)
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage 5 true trunk survival extraction."
    )
    parser.add_argument("input_jsonl", type=Path, help="Stage 4 audited JSONL input")
    parser.add_argument("output_jsonl", type=Path, help="Stage 5 survival JSONL output")
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path("data/rules/roots_survival_rules.yaml"),
        help="Stage 5 survival rules YAML",
    )
    args = parser.parse_args(argv)

    try:
        rules = load_rules(args.rules)
        decisions = (decide_survival(record, rules) for record in load_jsonl(args.input_jsonl))
        write_jsonl(decisions, args.output_jsonl)
    except Stage5Error as exc:
        print(f"Stage 5 error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
