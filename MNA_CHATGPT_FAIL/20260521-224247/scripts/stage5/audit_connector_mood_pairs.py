#!/usr/bin/env python3
"""
MNA Stage 5 — Connector × Mood Pair Audit

Purpose:
Measure observable connector × mood distributions inside a single candidacy environment.

This script does not interpret connector meaning or assign structural certainty.
It only reports measurable morphological pairing behavior.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

ENV_DEPENDENCY_PRESSURE_WARN = "ENV-003-DEPENDENCY_PRESSURE_PRESERVE_WARN"


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def nested_to_dict(d):
    out = {}
    for k, v in sorted(d.items(), key=lambda kv: str(kv[0])):
        out[str(k)] = {
            str(inner_k): inner_v
            for inner_k, inner_v in sorted(v.items(), key=lambda kv: str(kv[0]))
        }
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("candidacy_assertions_jsonl", type=Path)
    p.add_argument("output_json", type=Path)
    args = p.parse_args()

    rows = [
        row for row in load_jsonl(args.candidacy_assertions_jsonl)
        if row.get("candidacy_environment") == ENV_DEPENDENCY_PRESSURE_WARN
    ]

    pairs = defaultdict(lambda: defaultdict(int))

    for row in rows:
        connector = row.get("connector_greek") or "NONE"
        mood = row.get("anchor_mood") or "NONE"
        pairs[connector][mood] += 1

    out = {
        "record_type": "connector_mood_pair_audit",
        "environment": ENV_DEPENDENCY_PRESSURE_WARN,
        "rows": len(rows),
        "connector_mood_distribution": nested_to_dict(pairs),
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
