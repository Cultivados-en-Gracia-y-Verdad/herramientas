#!/usr/bin/env python3
"""
MNA Stage 5 — Dependency Pressure Subclass Audit

Purpose:
Audit observable subclasses inside ENV-003 dependency-pressure rows.

This script does not interpret connector meaning, score rows, or change candidacy labels.
It only reports measurable distributions inside an existing environment class.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

ENV_DEPENDENCY_PRESSURE_WARN = "ENV-003-DEPENDENCY_PRESSURE_PRESERVE_WARN"


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def profile_key(items):
    if not items:
        return "NONE"
    return " + ".join(sorted(items))


def counter_to_sorted_dict(counter):
    return {str(k): v for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("candidacy_assertions_jsonl", type=Path)
    p.add_argument("output_json", type=Path)
    args = p.parse_args()

    rows = [
        row for row in load_jsonl(args.candidacy_assertions_jsonl)
        if row.get("candidacy_environment") == ENV_DEPENDENCY_PRESSURE_WARN
    ]

    connector_counts = Counter()
    mood_counts = Counter()
    pressure_profiles = Counter()
    signal_profiles = Counter()
    survival_rule_counts = Counter()
    assertion_profiles = Counter()

    for row in rows:
        connector_counts[row.get("connector_greek")] += 1
        mood_counts[row.get("anchor_mood")] += 1
        pressure_profiles[profile_key(row.get("negative_pressure") or [])] += 1
        signal_profiles[profile_key(row.get("signals") or [])] += 1
        survival_rule_counts[row.get("survival_rule_id")] += 1
        assertion_profiles[profile_key(row.get("assertions") or [])] += 1

    out = {
        "record_type": "dependency_pressure_subclass_audit",
        "environment": ENV_DEPENDENCY_PRESSURE_WARN,
        "rows": len(rows),
        "connector_distribution": counter_to_sorted_dict(connector_counts),
        "mood_distribution": counter_to_sorted_dict(mood_counts),
        "negative_pressure_profile_distribution": counter_to_sorted_dict(pressure_profiles),
        "signal_profile_distribution": counter_to_sorted_dict(signal_profiles),
        "survival_rule_distribution": counter_to_sorted_dict(survival_rule_counts),
        "assertion_profile_distribution": counter_to_sorted_dict(assertion_profiles),
        "final_trunk_status_claimed": False,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"ROWS: {len(rows)}")
    print(f"WROTE -> {args.output_json}")


if __name__ == "__main__":
    main()
