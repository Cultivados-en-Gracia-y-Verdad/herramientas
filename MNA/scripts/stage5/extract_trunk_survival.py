#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml

DEFAULT_PRESERVE_WARN_RULE_ID = "S5-PRESERVE-WARN-UNKNOWN-001"
DEFAULT_CONDITIONAL_RULE_ID = "S5-PRESERVE-CONDITIONAL-UNIT-001"

class Stage5Error(Exception):
    pass

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

def decide_survival(record: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    connector = record.get("connector_greek") or record.get("connector")

    out = {
        "book": record.get("book"),
        "chapter": record.get("chapter"),
        "verse": record.get("verse"),
        "unit_id": record.get("unit_id"),
        "clause_id": record.get("clause_id"),
        "warnings": list(record.get("warnings") or []),
        "flags": list(record.get("flags") or []),
        "source_stage4_decision": record.get("stage4_decision"),
    }

    if connector in {"εἰ", "ἐὰν"}:
        out["survival_decision"] = "SURVIVE"
        out["survival_rule_id"] = DEFAULT_CONDITIONAL_RULE_ID
        out["survival_reason"] = "Conditional logical unit preserved."
        return out

    out["survival_decision"] = "PRESERVE_WARN"
    out["survival_rule_id"] = DEFAULT_PRESERVE_WARN_RULE_ID
    out["survival_reason"] = "Preserved pending further survivability refinement."
    return out

def write_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

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
