#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

DEFAULT_PRESERVE_WARN_RULE_ID = "S5-PRESERVE-WARN-UNKNOWN-001"
DEFAULT_CONDITIONAL_RULE_ID = "S5-PRESERVE-CONDITIONAL-UNIT-001"
DEFAULT_STAGE4_SURVIVES_RULE_ID = "S5-PRESERVE-STAGE4-SURVIVES-001"


def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def load_rules(path: Path) -> Dict[str, Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {rule["id"]: rule for rule in data.get("rules", [])}


def get_rule_by_type(rules: Dict[str, Dict[str, Any]], rule_type: str) -> Optional[Dict[str, Any]]:
    for rule in rules.values():
        if rule.get("enabled", True) and rule.get("type") == rule_type:
            return rule
    return None


def decide_survival(record: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    connector = record.get("connector_greek") or record.get("connector")
    stage4_decision = record.get("stage4_decision")

    out = {
        "book": record.get("book"),
        "chapter": record.get("chapter"),
        "verse": record.get("verse"),
        "unit_id": record.get("unit_id"),
        "clause_id": record.get("clause_id"),
        "finite_verb": record.get("finite_verb"),
        "warnings": list(record.get("warnings") or []),
        "flags": list(record.get("flags") or []),
        "source_stage4_decision": stage4_decision,
    }

    stage4_rule = rules.get(DEFAULT_STAGE4_SURVIVES_RULE_ID) or get_rule_by_type(rules, "preserve_stage4_survivor")
    if stage4_rule and stage4_decision in set(stage4_rule.get("stage4_decisions") or []):
        out["survival_decision"] = "SURVIVE"
        out["survival_rule_id"] = stage4_rule["id"]
        out["survival_reason"] = "Stage 4 classified this record as structurally surviving."
        return out

    conditional_rule = rules.get(DEFAULT_CONDITIONAL_RULE_ID) or get_rule_by_type(rules, "preserve_as_unit")
    conditional_connectors = set((conditional_rule or {}).get("connectors") or ["εἰ", "ἐὰν"])
    if connector in conditional_connectors:
        out["survival_decision"] = "SURVIVE"
        out["survival_rule_id"] = (conditional_rule or {}).get("id", DEFAULT_CONDITIONAL_RULE_ID)
        out["survival_reason"] = "Conditional logical unit preserved."
        return out

    out["survival_decision"] = "PRESERVE_WARN"
    out["survival_rule_id"] = DEFAULT_PRESERVE_WARN_RULE_ID
    out["survival_reason"] = "Preserved pending further survivability refinement."
    if not out["warnings"]:
        out["warnings"].append({"code": "S5_PRESERVE_WARN_DEFAULT"})
    return out


def write_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    print(f"WROTE {count} records -> {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--rules", type=Path, required=True)
    args = parser.parse_args()

    rules = load_rules(args.rules)
    decisions = (decide_survival(record, rules) for record in load_jsonl(args.input_jsonl))
    write_jsonl(decisions, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
